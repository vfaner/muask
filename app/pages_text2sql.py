"""Text2SQL core page: natural language -> SQL -> execute -> results."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import sqlparse
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIntValidator
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPlainTextEdit,
    QProgressBar, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from .config import DB_TYPES, KEYLESS_PROVIDERS, ConfigManager, provider_preset
from .db import precheck_sql
from .error_dialog import show_error
from .highlighter import SQLHighlighter
from . import toast
from .workers import AIGenerateWorker, SchemaFetchWorker, SQLExecuteWorker


DB_LABEL_BY_CODE = {code: label for label, code, _ in DB_TYPES}


def _ds_fingerprint(ds: Optional[Dict[str, Any]]) -> tuple:
    """Connection-relevant fields, so an in-flight worker can notice that the
    data source it was started with has since been edited (same name)."""
    if not ds:
        return ()
    params = ds.get("params") if isinstance(ds.get("params"), dict) else {}
    return (
        ds.get("type"), ds.get("host"), ds.get("port"), ds.get("database"),
        ds.get("username"), ds.get("password"), ds.get("instance"),
        ds.get("lib_dir"),
        tuple(sorted((str(k), str(v)) for k, v in params.items())),
    )


class Text2SQLPage(QWidget):
    status_message = Signal(str)

    def __init__(self, cfg: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.cfg = cfg
        self._ai_worker: Optional[AIGenerateWorker] = None
        self._sql_worker: Optional[SQLExecuteWorker] = None
        # In-flight schema loads, kept as a list so a rapid datasource switch
        # doesn't GC a QThread that's still running.
        self._schema_workers: List[SchemaFetchWorker] = []
        # ds name -> (schema section, shown count, total count); introspected
        # once per data source and reused for every generation.
        self._schema_cache: Dict[str, tuple] = {}
        # Bumped whenever data sources are reloaded; replies from an older
        # generation are dropped so an edited connection can't repopulate the
        # cache with the previous schema.
        self._schema_generation = 0
        # name -> number of in-flight introspection workers, so rapidly
        # switching back and forth doesn't introspect the same DB repeatedly.
        self._schema_inflight: Dict[str, int] = {}

        # Pagination state
        self._current_page = 1
        self._page_size = cfg.get_page_size()
        self._total_rows = 0
        # True when the COUNT(*) wrap failed: a placeholder total drives
        # pagination, but the UI shows "?" instead of claiming a number.
        self._count_unknown = False
        self._last_sql = ""
        # In-flight UI operations. Generation and execution are mutually
        # exclusive so a second worker never replaces a running QThread.
        self._gen_busy = False
        self._exec_busy = False

        self._build_ui()
        self.refresh_data_sources()
        self.refresh_ai_configs()

    # ----- UI -----
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Toolbar row
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("当前数据源:"))
        self.ds_combo = QComboBox()
        self.ds_combo.setMinimumWidth(200)
        self.ds_combo.currentIndexChanged.connect(self._on_ds_change)
        toolbar.addWidget(self.ds_combo)

        toolbar.addSpacing(12)
        toolbar.addWidget(QLabel("AI:"))
        self.ai_combo = QComboBox()
        self.ai_combo.setMinimumWidth(180)
        self.ai_combo.currentIndexChanged.connect(self._on_ai_change)
        toolbar.addWidget(self.ai_combo)

        toolbar.addSpacing(20)
        toolbar.addStretch(1)

        self.btn_generate = QPushButton("生成 SQL")
        self.btn_generate.clicked.connect(self._on_generate)
        toolbar.addWidget(self.btn_generate)

        self.btn_execute = QPushButton("执行 SQL")
        self.btn_execute.clicked.connect(self._on_execute)
        toolbar.addWidget(self.btn_execute)

        self.btn_format = QPushButton("格式化")
        self.btn_format.setProperty("flat", True)
        self.btn_format.clicked.connect(self._on_format_sql)
        toolbar.addWidget(self.btn_format)

        root.addLayout(toolbar)

        # Schema status: shows whether the connected DB's real structure has
        # been loaded for schema-aware generation.
        schema_row = QHBoxLayout()
        schema_row.setContentsMargins(0, 0, 0, 0)
        self.schema_status = QLabel("表结构：未选择数据源")
        self.schema_status.setStyleSheet("color:#7f8c8d;")
        self.schema_status.setWordWrap(False)
        schema_row.addWidget(self.schema_status, 1)
        self.btn_reload_schema = QPushButton("重新读取表结构")
        self.btn_reload_schema.setProperty("flat", True)
        self.btn_reload_schema.setEnabled(False)
        self.btn_reload_schema.clicked.connect(self._on_reload_schema)
        schema_row.addWidget(self.btn_reload_schema)
        root.addLayout(schema_row)

        # Splitter for three regions: NL input | SQL editor | Results
        splitter = QSplitter(Qt.Vertical)
        root.addWidget(splitter, 1)

        # 1. natural language
        nl_wrap = QWidget()
        nl_l = QVBoxLayout(nl_wrap)
        nl_l.setContentsMargins(0, 0, 0, 0)
        nl_title = QLabel("自然语言描述")
        nl_title.setProperty("title", True)
        nl_l.addWidget(nl_title)
        self.nl_edit = QTextEdit()
        self.nl_edit.setPlaceholderText("请输入查询需求，例如：\n查询销售额大于1000的客户名称和订单总额。")
        nl_l.addWidget(self.nl_edit, 1)
        splitter.addWidget(nl_wrap)

        # 2. SQL editor
        sql_wrap = QWidget()
        sql_l = QVBoxLayout(sql_wrap)
        sql_l.setContentsMargins(0, 0, 0, 0)
        sql_title = QLabel("SQL 语句 (可编辑)")
        sql_title.setProperty("title", True)
        sql_l.addWidget(sql_title)
        self.sql_edit = QPlainTextEdit()
        self.sql_edit.setObjectName("sqlEditor")
        self.sql_edit.setPlaceholderText("生成的 SQL 会显示在此，可手动修改后再执行。")
        # QFont takes a family *list*, not a CSS font-family string: passing
        # "Menlo, Consolas, monospace" as one name matches no installed font and
        # silently falls back to the UI font.
        mono = QFont()
        mono.setFamilies(["JetBrains Mono", "Consolas", "Menlo", "Courier New"])
        mono.setStyleHint(QFont.Monospace)
        self.sql_edit.setFont(mono)
        self._highlighter = SQLHighlighter(self.sql_edit.document())
        sql_l.addWidget(self.sql_edit, 1)
        splitter.addWidget(sql_wrap)

        # 3. Results
        result_wrap = QWidget()
        result_l = QVBoxLayout(result_wrap)
        result_l.setContentsMargins(0, 0, 0, 0)

        result_header = QHBoxLayout()
        result_title = QLabel("执行结果")
        result_title.setProperty("title", True)
        result_header.addWidget(result_title)
        result_header.addStretch(1)
        result_header.addWidget(QLabel("每页:"))
        self.page_size_edit = QLineEdit(str(self._page_size))
        self.page_size_edit.setFixedWidth(70)
        self.page_size_edit.setAlignment(Qt.AlignCenter)
        self.page_size_edit.setValidator(QIntValidator(5, 1000, self))
        self.page_size_edit.editingFinished.connect(self._on_page_size_editing_finished)
        result_header.addWidget(self.page_size_edit)

        self.btn_prev = QPushButton("上一页")
        self.btn_prev.setProperty("flat", True)
        self.btn_prev.clicked.connect(self._on_prev_page)
        result_header.addWidget(self.btn_prev)

        self.page_label = QLabel("第 0 / 0 页")
        result_header.addWidget(self.page_label)

        self.btn_next = QPushButton("下一页")
        self.btn_next.setProperty("flat", True)
        self.btn_next.clicked.connect(self._on_next_page)
        result_header.addWidget(self.btn_next)

        result_l.addLayout(result_header)

        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        header = self.result_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        # Auto-width samples at most this many rows; the default (1000) makes
        # resizeColumnsToContents crawl on a large result page.
        header.setResizeContentsPrecision(100)
        result_l.addWidget(self.result_table, 1)

        self.result_message = QLabel("")
        self.result_message.setStyleSheet("padding: 6px; color:#34495e;")
        self.result_message.setWordWrap(True)
        result_l.addWidget(self.result_message)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        result_l.addWidget(self.progress)

        splitter.addWidget(result_wrap)
        splitter.setSizes([160, 220, 380])

        self._update_pagination_ui()
        self._update_execute_enabled()

    # ----- Public: hooks from main window -----
    def refresh_data_sources(self, autoload_schema: bool = False) -> None:
        prev_current = self.cfg.get_current_data_source()
        self.ds_combo.blockSignals(True)
        self.ds_combo.clear()
        self.ds_combo.addItem("（未选择数据源）", "")
        for ds in self.cfg.get_data_sources():
            name = ds.get("name") or "(未命名)"
            self.ds_combo.addItem(
                f"{name}  [{DB_LABEL_BY_CODE.get(ds.get('type', ''), ds.get('type', ''))}]",
                name,
            )

        # Restore selection
        idx = 0
        for i in range(self.ds_combo.count()):
            if self.ds_combo.itemData(i) == prev_current:
                idx = i
                break
        self.ds_combo.setCurrentIndex(idx)
        self.ds_combo.blockSignals(False)
        self._update_execute_enabled()

        # Connection settings may have changed in the config dialog, so cached
        # schemas can't be trusted. Startup (autoload_schema=False) deliberately
        # does NOT open a connection; an explicit datasource change does.
        self._schema_generation += 1
        self._schema_cache.clear()
        # Workers from the previous generation no longer count towards dedupe;
        # their replies are discarded by the generation check above.
        self._schema_inflight.clear()
        current = self.ds_combo.currentData() or ""
        # Connection settings may have changed; previously fetched rows belong
        # to the old connection and pagination can no longer trust its total.
        self._reset_results()
        if autoload_schema and current:
            self._load_schema(current)
        else:
            self._set_schema_status("idle" if current else "none")

    def refresh_ai_configs(self) -> None:
        """Reload the AI-config dropdown from ConfigManager."""
        current = self.cfg.data.get("current_ai_config", "") or ""
        self.ai_combo.blockSignals(True)
        self.ai_combo.clear()
        self.ai_combo.addItem("（未选择 AI）", "")
        for ai in self.cfg.get_ai_configs():
            code = ai.get("provider", "")
            vendor = provider_preset(code)[0] or code or "?"
            label = f"{ai.get('name','?')}  [{vendor}]"
            self.ai_combo.addItem(label, ai.get("name", ""))
        idx = 0
        for i in range(self.ai_combo.count()):
            if self.ai_combo.itemData(i) == current:
                idx = i
                break
        if idx == 0 and self.ai_combo.count() > 1:
            # No current marked but configs exist: generation already falls
            # back to the first config, so select it here too instead of
            # showing “未选择” while the status bar reports that config.
            idx = 1
            self.cfg.set_current_ai_config(self.ai_combo.itemData(1) or "")
        self.ai_combo.setCurrentIndex(idx)
        self.ai_combo.blockSignals(False)

    # ----- helpers -----
    def _current_ai_cfg(self) -> Optional[Dict[str, Any]]:
        name = self.ai_combo.currentData()
        if not name:
            return None
        return self.cfg.find_ai_config(name)
    def _current_ds(self) -> Optional[Dict[str, Any]]:
        name = self.ds_combo.currentData()
        if not name:
            return None
        return self.cfg.find_data_source(name)

    def _update_execute_enabled(self) -> None:
        has_ds = self._current_ds() is not None
        self.btn_execute.setEnabled(has_ds and not self._gen_busy and not self._exec_busy)
        if not has_ds:
            self.btn_execute.setToolTip("请先在“数据源配置”中配置并选择数据源")
        else:
            self.btn_execute.setToolTip("")

    def _update_pagination_ui(self) -> None:
        page_size = max(1, self._page_size)
        total = max(0, self._total_rows)
        pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 0
        shown_total = "?" if self._count_unknown else total
        self.page_label.setText(f"第 {self._current_page if pages else 0} / {pages} 页  (共 {shown_total} 条)")
        busy = self._gen_busy or self._exec_busy
        self.btn_prev.setEnabled(not busy and self._current_page > 1 and total > 0)
        self.btn_next.setEnabled(not busy and self._current_page < pages)
        # Changing the page size mid-flight would desync the in-flight result
        # from the page counter, so lock the field while busy.
        self.page_size_edit.setEnabled(not busy)

    # ----- Events -----
    def _on_ds_change(self, _idx: int) -> None:
        name = self.ds_combo.currentData() or ""
        self.cfg.set_current_data_source(name)
        try:
            self.cfg.save()
        except Exception:
            pass
        self._update_execute_enabled()
        # Results and the page counter belong to the previous connection.
        self._reset_results()
        self._load_schema(name)
        if name:
            self.status_message.emit(f"已切换到数据源: {name}")

    def _set_schema_status(self, state: str, shown: int = 0, total: int = 0) -> None:
        has_ds = self._current_ds() is not None
        self.btn_reload_schema.setEnabled(has_ds and state != "loading")
        if state == "none":
            text = "表结构：未选择数据源，AI 将按通用经验猜测表名"
            color = "#7f8c8d"
        elif state == "idle":
            text = "表结构：尚未读取，点「生成 SQL」时会自动读取（或点右侧按钮）"
            color = "#7f8c8d"
        elif state == "loading":
            text = "表结构：正在读取数据库表结构…"
            color = "#3498db"
        elif state == "ok":
            if shown < total:
                text = f"表结构：已载入 {shown}/{total} 张表（表较多，已按问题相关性筛选），AI 基于真实结构生成"
            else:
                text = f"表结构：已载入 {total} 张表，AI 将基于真实表名 / 字段生成"
            color = "#27ae60"
        else:  # failed
            text = "表结构：读取失败，本次 AI 将缺少真实结构（可点右侧重试）"
            color = "#e67e22"
        self.schema_status.setText(text)
        self.schema_status.setStyleSheet(f"color:{color};")
        self.schema_status.setToolTip("")

    def _load_schema(self, name: str, force: bool = False) -> None:
        """Proactively introspect the selected DB in the background."""
        if not name:
            self._set_schema_status("none")
            return
        if not force and name in self._schema_cache:
            _, shown, total = self._schema_cache[name]
            self._set_schema_status("ok", shown, total)
            return
        # An introspection for this data source is already running (e.g. the
        # user flipped A -> B -> A quickly); its result will land in the cache.
        if not force and self._schema_inflight.get(name):
            return
        ds = self.cfg.find_data_source(name)
        if not ds:
            self._set_schema_status("none")
            return

        self._set_schema_status("loading")
        worker = SchemaFetchWorker(ds)
        gen = self._schema_generation

        def ok(section: str, shown: int, total: int) -> None:
            # Ignore results for a datasource the user navigated away from, or
            # for a schema snapshot from before the config was reloaded.
            if gen != self._schema_generation or self.ds_combo.currentData() != name:
                return
            self._schema_cache[name] = (section, shown, total)
            self._set_schema_status("ok", shown, total)

        def fail(msg: str) -> None:
            if gen != self._schema_generation or self.ds_combo.currentData() != name:
                return
            self._set_schema_status("failed")
            self.schema_status.setToolTip(msg[:500])

        def finished() -> None:
            # A worker from before a config refresh must not decrement the
            # counter of a newer in-flight load for the same name (that would
            # drop the dedupe and allow a duplicate introspection).
            if gen != self._schema_generation:
                return
            remaining = self._schema_inflight.get(name, 0) - 1
            if remaining > 0:
                self._schema_inflight[name] = remaining
            else:
                self._schema_inflight.pop(name, None)

        worker.finished_ok.connect(ok)
        worker.failed.connect(fail)
        self._schema_workers.append(worker)
        self._schema_inflight[name] = self._schema_inflight.get(name, 0) + 1
        worker.finished.connect(finished)
        worker.finished.connect(lambda w=worker: self._discard_worker(w))
        worker.start()

    def _discard_worker(self, worker: SchemaFetchWorker) -> None:
        if worker in self._schema_workers:
            self._schema_workers.remove(worker)

    def _on_reload_schema(self) -> None:
        name = self.ds_combo.currentData() or ""
        if name:
            self._load_schema(name, force=True)

    def _on_ai_change(self, _idx: int) -> None:
        name = self.ai_combo.currentData() or ""
        self.cfg.set_current_ai_config(name)
        try:
            self.cfg.save()
        except Exception:
            pass
        if name:
            self.status_message.emit(f"已切换到 AI: {name}")

    def _on_page_size_editing_finished(self) -> None:
        if self._gen_busy or self._exec_busy:
            # editingFinished can still fire on focus loss even though the
            # field is disabled mid-flight; keep the in-flight page intact.
            self.page_size_edit.setText(str(self._page_size))
            return
        text = self.page_size_edit.text().strip()
        try:
            val = int(text)
        except ValueError:
            self.page_size_edit.setText(str(self._page_size))
            return
        val = max(5, min(1000, val))
        self._page_size = val
        self.cfg.set_page_size(val)
        self.page_size_edit.setText(str(val))
        try:
            self.cfg.save()
        except Exception:
            pass
        self._current_page = 1
        self._update_pagination_ui()

    def _on_format_sql(self) -> None:
        sql = self.sql_edit.toPlainText().strip()
        if not sql:
            return
        try:
            formatted = sqlparse.format(sql, reindent=True, keyword_case="upper")
            self.sql_edit.setPlainText(formatted)
        except Exception as e:
            toast.error(self, f"格式化失败: {e}")

    def _on_generate(self) -> None:
        if self._gen_busy or self._exec_busy:
            return
        desc = self.nl_edit.toPlainText().strip()
        if not desc:
            toast.warning(self, "请先输入自然语言描述")
            return
        ai_cfg = self._current_ai_cfg() or self.cfg.get_current_ai_config()
        # 本地推理 / 自定义兼容网关通常不校验 key，允许留空
        needs_key = (ai_cfg or {}).get("provider") not in KEYLESS_PROVIDERS
        if not ai_cfg or not ai_cfg.get("api_base") or not ai_cfg.get("model") \
                or (needs_key and not ai_cfg.get("api_key")):
            toast.warning(self, "请先在“AI 配置”中新建并选中一份可用的配置")
            return

        ds = self._current_ds()
        dialect = DB_LABEL_BY_CODE.get(ds.get("type", ""), "MySQL") if ds else "MySQL"

        # Feed the AI the real schema when we've introspected it. If the
        # proactive load hasn't finished (or failed earlier), pass the data
        # source so the worker introspects inline and hands the result back to
        # cache via schema_ready.
        schema_text: Optional[str] = None
        if ds is not None:
            cached = self._schema_cache.get(ds["name"])
            if cached is not None:
                schema_text = cached[0]

        # Generation and execution are mutually exclusive: running SQL while
        # the AI thinks used to re-enable 生成 SQL mid-flight, letting a second
        # worker replace an in-flight QThread.
        self._gen_busy = True
        self.btn_generate.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self.btn_generate.setText("生成中…")
        self.progress.setVisible(True)
        self._update_pagination_ui()

        self._ai_worker = AIGenerateWorker(
            ai_cfg, desc, dialect,
            schema=schema_text,
            ds=ds if schema_text is None else None,
        )
        ds_name = ds.get("name") if ds is not None else None
        ds_fp = _ds_fingerprint(ds)

        def _ds_switched() -> bool:
            """True when the selection changed or the same-named source was
            edited while the model was thinking — its answer/schema no longer
            applies to the current connection."""
            if ds_name is None:
                return False
            if self.ds_combo.currentData() != ds_name:
                return True
            return _ds_fingerprint(self.cfg.find_data_source(ds_name)) != ds_fp

        if ds is not None:
            def cache_schema(section: str, shown: int, total: int) -> None:
                if _ds_switched():
                    return
                self._schema_cache[ds_name] = (section, shown, total)
                self._set_schema_status("ok", shown, total)
            self._ai_worker.schema_ready.connect(cache_schema)

        def ok(sql: str) -> None:
            self._gen_busy = False
            self.btn_generate.setEnabled(True)
            self.btn_generate.setText("生成 SQL")
            self.progress.setVisible(False)
            self._update_execute_enabled()
            self._update_pagination_ui()
            if _ds_switched():
                toast.warning(self, "生成期间数据源已切换或配置已修改，本次生成结果已丢弃")
                return

            # Pre-check before writing to the editor - catches AI returning prose,
            # unbalanced quotes, or empty output.
            ok_check, reason = precheck_sql(sql, (ds or {}).get("type") or "")
            if not ok_check:
                show_error(
                    self,
                    summary="AI 生成的 SQL 预检未通过",
                    detail=f"原因：{reason}\n\n模型返回内容：\n{sql[:2000]}",
                    title="预检失败",
                )
                self.status_message.emit(f"AI 生成的 SQL 预检未通过：{reason}")
                return

            self.sql_edit.setPlainText(sql)
            self.status_message.emit("SQL 已生成并通过预检，可执行或编辑")
            toast.success(self, "AI 已生成 SQL（预检通过）")

        def fail(msg: str) -> None:
            self._gen_busy = False
            self.btn_generate.setEnabled(True)
            self.btn_generate.setText("生成 SQL")
            self.progress.setVisible(False)
            self._update_execute_enabled()
            self._update_pagination_ui()
            if _ds_switched():
                return
            show_error(
                self,
                summary="AI 调用失败",
                detail=msg,
                title="AI 生成失败",
            )
            self.status_message.emit("AI 生成失败")

        self._ai_worker.finished_ok.connect(ok)
        self._ai_worker.failed.connect(fail)
        self._ai_worker.start()

    def _on_execute(self) -> None:
        ds = self._current_ds()
        if not ds:
            toast.warning(self, "请先配置并选择数据源")
            return
        sql = self.sql_edit.toPlainText().strip()
        if not sql:
            toast.warning(self, "SQL 语句不能为空")
            return

        # Only reset pagination if the SQL changed
        if sql != self._last_sql:
            self._current_page = 1
            self._total_rows = 0
        self._last_sql = sql

        self._run_sql(ds, sql, self._current_page, self._page_size)

    def _on_prev_page(self) -> None:
        if self._gen_busy or self._exec_busy or self._current_page <= 1:
            return
        ds = self._current_ds()
        if not ds or not self._last_sql:
            return
        self._current_page -= 1
        self._run_sql(ds, self._last_sql, self._current_page, self._page_size)

    def _on_next_page(self) -> None:
        if self._gen_busy or self._exec_busy:
            return
        page_size = max(1, self._page_size)
        pages = max(1, (self._total_rows + page_size - 1) // page_size) if self._total_rows > 0 else 1
        if self._current_page >= pages:
            return
        ds = self._current_ds()
        if not ds or not self._last_sql:
            return
        self._current_page += 1
        self._run_sql(ds, self._last_sql, self._current_page, self._page_size)

    # ----- SQL execution -----
    def _run_sql(self, ds: Dict[str, Any], sql: str, page: int, page_size: int) -> None:
        if self._gen_busy or self._exec_busy:
            return
        self._exec_busy = True
        self.btn_execute.setEnabled(False)
        self.btn_generate.setEnabled(False)
        self.progress.setVisible(True)
        # Second and later pages of the same statement can reuse the total from
        # page 1 instead of re-running COUNT(*), which is a full scan on big
        # tables. Only trust it when the earlier count actually succeeded.
        known_total = self._total_rows if (page > 1 and not self._count_unknown) else -1
        # Clear any stale content so the previous result never lingers
        # underneath an error message; pagination controls are disabled while
        # busy (via _update_pagination_ui).
        self._clear_result_view("正在执行…")

        self._sql_worker = SQLExecuteWorker(ds, sql, page, page_size, known_total)

        ds_name = ds.get("name") or ""
        ds_fp = _ds_fingerprint(ds)

        def _stale() -> bool:
            if self.ds_combo.currentData() != ds_name:
                return True
            return _ds_fingerprint(self.cfg.find_data_source(ds_name)) != ds_fp

        def sel_ok(cols: List[str], rows: List[Any], total: int) -> None:
            self._finish_exec()
            if _stale():
                # Rows came from a source that was switched/edited mid-query;
                # showing them under the new selection would be misleading.
                self._clear_result_view("")
                toast.warning(self, "数据源已切换或配置已修改，本次查询结果已丢弃")
                return
            total = total if isinstance(total, int) else 0
            self._count_unknown = False
            # COUNT wrapping failed (some queries don't support it). Use a
            # placeholder total so paging still works (full page → maybe a next
            # page; partial → this is the last), but display "?" not a number.
            if total < 0:
                self._count_unknown = True
                # Use the page/page_size captured for this request, not the
                # mutable UI state (which the user could change mid-flight).
                total = page * page_size
                if len(rows) >= page_size:
                    total += 1
            self._total_rows = total
            self._show_table(cols, rows)
            self._update_pagination_ui()
            msg = f"查询成功，本页 {len(rows)} 条"
            if self._count_unknown:
                if self.btn_next.isEnabled():
                    msg += "，总数未知（可继续翻页）"
                else:
                    msg += "，总数未知（已是最后一页）"
            else:
                msg += f"，共 {total} 条"
            self.result_message.setText(msg)
            self.status_message.emit(msg)
            toast.success(self, msg)

        def ns_ok(affected: int) -> None:
            self._finish_exec()
            if _stale():
                self._clear_result_view("")
                toast.warning(self, "数据源已切换或配置已修改，本次执行结果已丢弃")
                return
            self.result_table.clear()
            self.result_table.setRowCount(0)
            self.result_table.setColumnCount(0)
            self._total_rows = 0
            self._update_pagination_ui()
            if affected >= 0:
                msg = f"命令执行成功，受影响行数: {affected}"
            else:
                msg = "命令执行成功"
            self.result_message.setText(msg)
            self.status_message.emit(msg)
            toast.success(self, msg)

        def fail(msg: str) -> None:
            self._finish_exec()
            # Wipe the result view so nothing from a previous successful run
            # is left behind under the failure state.
            self._clear_result_view("")
            if _stale():
                toast.warning(self, "数据源已切换或配置已修改，本次执行结果已丢弃")
                return
            # Show a proper dialog with a Close button and scrollable detail.
            summary = self._short_error(msg)
            show_error(self, summary=summary, detail=msg, title="SQL 执行失败")
            self.result_message.setText(f"执行失败：{summary}")
            self.status_message.emit("SQL 执行失败")

        self._sql_worker.select_ok.connect(sel_ok)
        self._sql_worker.non_select_ok.connect(ns_ok)
        self._sql_worker.failed.connect(fail)
        self._sql_worker.start()

    def _reset_results(self) -> None:
        """Forget results and pagination when the connection context changes.

        Called on data-source switch / any data-source config edit so the table
        never shows rows fetched from a different (or no longer existing)
        connection, and pagination never reuses another source's total.
        """
        self._current_page = 1
        self._total_rows = 0
        self._count_unknown = False
        self._last_sql = ""
        self._clear_result_view("")

    def _clear_result_view(self, message: str) -> None:
        """Drop the table's contents and reset pagination state."""
        self.result_table.clear()
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self._total_rows = 0
        self._count_unknown = False
        self._update_pagination_ui()
        self.result_message.setText(message)

    @staticmethod
    def _short_error(msg: str) -> str:
        """Extract a concise one-liner from a long SQLAlchemy traceback-style message."""
        if not msg:
            return "未知错误"
        # SQLAlchemy typically formats as "(engine.error.SomeError) driver-message\n[SQL: ...]"
        # We want just the driver message.
        text = msg.strip()
        # Trim after [SQL: or [parameters:
        for marker in ("\n[SQL:", "\n[parameters:", " [SQL:", " [parameters:"):
            i = text.find(marker)
            if i >= 0:
                text = text[:i]
        # Take the first line
        first_line = text.splitlines()[0].strip()
        # Drop leading "(some.Error)" prefix if present
        if first_line.startswith("(") and ")" in first_line:
            close = first_line.find(")")
            first_line = first_line[close + 1:].strip()
        # Cap length
        if len(first_line) > 180:
            first_line = first_line[:180] + "…"
        return first_line or "未知错误"

    def _finish_exec(self) -> None:
        self._exec_busy = False
        # Generation is mutually exclusive with execution, so it's safe to
        # re-enable both here; _update_execute_enabled() still checks for a DS.
        self.btn_generate.setEnabled(not self._gen_busy)
        self.progress.setVisible(False)
        self._update_execute_enabled()

    def _show_table(self, cols: List[str], rows: List[Any]) -> None:
        # Repaint once after filling instead of after every setItem: with a
        # 1000-row page this is the difference between instant and seconds.
        self.result_table.setUpdatesEnabled(False)
        try:
            self.result_table.clear()
            self.result_table.setColumnCount(len(cols))
            self.result_table.setRowCount(len(rows))
            self.result_table.setHorizontalHeaderLabels(cols)

            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    item = QTableWidgetItem("" if val is None else str(val))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.result_table.setItem(r, c, item)
        finally:
            self.result_table.setUpdatesEnabled(True)

        self.result_table.resizeColumnsToContents()
        # Cap very wide cols
        for c in range(self.result_table.columnCount()):
            w = self.result_table.columnWidth(c)
            if w > 320:
                self.result_table.setColumnWidth(c, 320)
