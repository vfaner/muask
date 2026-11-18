"""Background QThread workers so UI stays responsive."""
from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import QThread, Signal

from .ai_providers import make_provider
from .db import (
    build_paginated_sql,
    build_count_sql,
    fetch_schema_text,
    get_engine,
    is_select,
    leading_keyword,
    run_non_select,
    run_scalar,
    run_select,
    run_select_slice,
    test_connection,
)


class SchemaFetchWorker(QThread):
    """Introspects a data source in the background and returns its schema text."""
    finished_ok = Signal(str, int, int)  # schema section, shown count, total count
    failed = Signal(str)

    def __init__(self, ds: Dict[str, Any]):
        super().__init__()
        self.ds = ds

    def run(self):
        try:
            section, shown, total = fetch_schema_text(self.ds, "")
            self.finished_ok.emit(section, shown, total)
        except Exception as e:
            self.failed.emit(str(e))


class AIGenerateWorker(QThread):
    """Runs AI SQL generation in the background."""
    finished_ok = Signal(str)  # sql text
    failed = Signal(str)
    # Emitted when the worker had to introspect the schema itself (the UI's
    # proactive load hadn't finished); lets the UI cache it for next time.
    schema_ready = Signal(str, int, int)

    def __init__(
        self,
        ai_cfg: Dict[str, Any],
        description: str,
        dialect: str,
        schema: Optional[str] = None,
        ds: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self.ai_cfg = ai_cfg
        self.description = description
        self.dialect = dialect
        # None means "not yet known"; empty string means "intentionally none".
        self.schema = schema
        self.ds = ds

    def run(self):
        try:
            schema_text = self.schema
            if schema_text is None and self.ds is not None:
                # Proactive cache miss (still loading, or earlier fetch failed):
                # introspect here, ranked against the actual question this time.
                # A failing database must not abort generation — fall back to
                # the generic prompt and let the AI answer from experience.
                try:
                    schema_text, shown, total = fetch_schema_text(
                        self.ds, self.description
                    )
                    self.schema_ready.emit(schema_text, shown, total)
                except Exception:
                    schema_text = ""
            provider = make_provider(self.ai_cfg)
            sql = provider.generate_sql(self.description, self.dialect, schema_text or "")
            self.finished_ok.emit(sql)
        except Exception as e:
            self.failed.emit(str(e))


class AITestWorker(QThread):
    finished_result = Signal(bool, str)

    def __init__(self, ai_cfg: Dict[str, Any]):
        super().__init__()
        self.ai_cfg = ai_cfg

    def run(self):
        try:
            provider = make_provider(self.ai_cfg)
            ok, msg = provider.test_call()
            self.finished_result.emit(ok, msg)
        except Exception as e:
            self.finished_result.emit(False, str(e))


class DBTestWorker(QThread):
    finished_result = Signal(bool, str)

    def __init__(self, ds: Dict[str, Any]):
        super().__init__()
        self.ds = ds

    def run(self):
        try:
            ok, msg = test_connection(self.ds)
        except Exception as e:
            # Never let an unexpected exception escape run(): the UI button
            # would stay stuck on "测试中…" with no result signal.
            ok, msg = False, f"连接测试异常: {e}"
        self.finished_result.emit(ok, msg)


class SQLExecuteWorker(QThread):
    """Executes a SQL statement (SELECT with pagination, or non-SELECT)."""
    select_ok = Signal(list, list, int)   # cols, rows, total_count
    non_select_ok = Signal(int)           # affected rows
    failed = Signal(str)

    def __init__(
        self, ds: Dict[str, Any], sql: str, page: int, page_size: int,
        known_total: int = -1,
    ):
        super().__init__()
        self.ds = ds
        self.sql = sql
        self.page = max(1, int(page))
        self.page_size = max(1, int(page_size))
        # >= 0 when a previous page already counted the rows for this exact
        # SQL; paging then skips the COUNT(*) (a full scan on large tables).
        self.known_total = int(known_total)

    def run(self):
        try:
            engine = get_engine(self.ds)
        except Exception as e:
            self.failed.emit(f"创建数据库连接失败: {e}")
            return

        try:
            if is_select(self.sql):
                keyword = leading_keyword(self.sql)
                if keyword in ("SHOW", "DESC", "DESCRIBE", "EXPLAIN"):
                    # Metadata statements return rows but cannot be wrapped in
                    # a derived table or COUNT(*). Run them as-is, one page.
                    cols, rows = run_select(engine, self.sql)
                    self.select_ok.emit(cols, rows, -1)
                    return
                # Count total (skipped when a previous page already did it).
                if self.known_total >= 0:
                    total = self.known_total
                else:
                    try:
                        total = int(run_scalar(engine, build_count_sql(self.sql)) or 0)
                    except Exception:
                        total = -1  # some queries don't support wrapping; still show page
                offset = (self.page - 1) * self.page_size
                dtype = (self.ds.get("type") or "").lower()
                try:
                    paged = build_paginated_sql(self.sql, dtype, offset, self.page_size)
                    cols, rows = run_select(engine, paged)
                    if dtype == "mssql" and cols and cols[-1] == "__muask_rn":
                        cols = cols[:-1]
                        rows = [r[:-1] for r in rows]
                except Exception:
                    # Statements starting with WITH and SQL Server queries
                    # with a top-level ORDER BY can't be wrapped in a derived
                    # table. Fall back to streaming the original statement and
                    # slicing rows client-side rather than failing outright.
                    cols, rows, _has_more = run_select_slice(
                        engine, self.sql, offset, self.page_size
                    )
                self.select_ok.emit(cols, rows, total)
            else:
                affected = run_non_select(engine, self.sql)
                self.non_select_ok.emit(affected)
        except Exception as e:
            self.failed.emit(str(e))
        # The engine is pooled and shared via db.get_engine(); it is disposed by
        # db.dispose_engines() when the application closes.
