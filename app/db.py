"""
Database connection layer.

Builds SQLAlchemy URLs for each supported DB type and provides helpers to test
connections and execute SQL statements.

The connection URL builders follow common conventions; particular deployments
may require adjustments in the `params` (e.g. driver, charset, service_name).
"""
from __future__ import annotations

import math
import re
import socket
import threading
from collections import OrderedDict
from importlib.util import find_spec
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from .db_dialects import register_dialects

# Register dm+dmpython / kingbase+ksycopg2 dialects before any URL is parsed.
register_dialects()


DriverHint = Dict[str, str]

# Every database type offered in the data-source dropdown ships a driver in the
# packaged app, so these hints are normally never shown. They remain as guidance
# for source-code runs on an unsupported platform (the domestic vendors publish
# Windows/Linux wheels only).
DRIVER_HINTS: Dict[str, DriverHint] = {
    "mysql":       {"pkg": "pymysql",    "install": "pip install pymysql"},
    "mariadb":     {"pkg": "pymysql",    "install": "pip install pymysql（MariaDB 兼容 MySQL 协议，打包版已内置）"},
    "postgresql":  {"pkg": "psycopg2",   "install": "pip install psycopg2-binary"},
    "opengauss":   {"pkg": "psycopg2",   "install": "pip install psycopg2-binary（OpenGauss 兼容 PG 协议）"},
    "highgo":      {"pkg": "psycopg2",   "install": "pip install psycopg2-binary（瀚高基于 PostgreSQL 内核，兼容 PG 协议）"},
    "vastbase":    {"pkg": "psycopg2",  "install": "pip install psycopg2-binary（海量 Vastbase 基于 openGauss/PostgreSQL 内核，兼容 PG 协议）"},
    "kingbase":    {"pkg": "ksycopg2",   "install": "pip install ksycopg2（人大金仓官方驱动，打包版已内置）或 pip install psycopg2-binary（PG 协议）"},
    "oceanbase":   {"pkg": "pymysql",   "install": "pip install pymysql（OceanBase MySQL 租户兼容 MySQL 协议，默认端口 2881；Oracle 租户请改用「自定义」）"},
    "tidb":        {"pkg": "pymysql",    "install": "pip install pymysql（TiDB 兼容 MySQL 协议）"},
    "oracle":      {"pkg": "oracledb",   "install": "pip install oracledb（纯 Python 瘦模式，无需 Oracle 客户端）"},
    "mssql":       {"pkg": "pymssql",    "install": "pip install pymssql（wheel 已内置 FreeTDS，无需安装 ODBC）"},
    "dm":          {"pkg": "dmPython",   "install": "Windows/Linux 打包版已内置达梦官方 dmpython（含达梦客户端库）；其他环境请在 Windows/Linux 上 pip install dmpython"},
    "gbase":       {"pkg": "pymysql",    "install": "pip install pymysql（GBase 8a 兼容 MySQL 协议，打包版已内置）"},
    "db2":         {"pkg": "ibm_db",     "install": "pip install ibm_db ibm-db-sa（IBM 官方 DB2 驱动，三平台 wheel 齐全）"},
    "custom":      {"pkg": "-",          "install": "请在参数中提供 SQLAlchemy 连接字符串 url，并自行安装对应驱动"},
}


def _has_module(name: str) -> bool:
    try:
        return find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def build_engine_url(ds: Dict[str, Any]) -> str:
    """Build a SQLAlchemy connection URL from a data-source dict."""
    dtype = (ds.get("type") or "").lower()
    host = ds.get("host") or "localhost"
    port = ds.get("port") or 0
    db = ds.get("database") or ""
    # quote(), not quote_plus(): SQLAlchemy decodes credentials with
    # unquote(), which leaves "+" as a literal plus — quote_plus would turn a
    # space in the username/password into "+" and break authentication.
    user = quote(ds.get("username") or "", safe="")
    pwd = quote(ds.get("password") or "", safe="")
    params: Dict[str, Any] = ds.get("params") or {}

    # Merge extra params into a query string
    def qs(extra: Dict[str, Any]) -> str:
        merged = {**params, **extra}
        pairs = [(k, v) for k, v in merged.items() if v not in (None, "")]
        if not pairs:
            return ""
        # Values are user-supplied (charset, tds_version, …) and can contain
        # spaces or '&'; percent-encode so the URL stays one valid query string.
        return "?" + "&".join(f"{k}={quote(str(v), safe='')}" for k, v in pairs)

    if dtype == "mysql":
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port or 3306}/{db}{qs({'charset': params.get('charset', 'utf8mb4')})}"
    if dtype in ("mariadb", "oceanbase", "tidb"):
        # MariaDB, OceanBase MySQL 租户, TiDB all speak the MySQL wire protocol,
        # so PyMySQL connects directly — no per-vendor driver to bundle.
        default_port = {"mariadb": 3306, "oceanbase": 2881, "tidb": 4000}[dtype]
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port or default_port}/{db}{qs({'charset': params.get('charset', 'utf8mb4')})}"
    # psycopg2 has no default connect timeout; an unreachable host would then
    # sit on the OS-level TCP timeout (~75 s on macOS, minutes on Linux). A
    # 10 s default keeps failed connects and app shutdown responsive; users
    # can override it via the connection params.
    pg_extra = {"connect_timeout": params.get("connect_timeout", 10)}
    if dtype == "postgresql":
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port or 5432}/{db}{qs(pg_extra)}"
    if dtype in ("opengauss", "highgo", "vastbase"):
        # OpenGauss / HighGo / Vastbase are all PostgreSQL-wire-compatible
        # (openGauss or PG forks), so psycopg2 connects directly.
        default_port = {"opengauss": 5432, "highgo": 5866, "vastbase": 5432}[dtype]
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port or default_port}/{db}{qs(pg_extra)}"
    if dtype == "kingbase":
        # Prefer Kingbase's own ksycopg2 (bundled in the packaged app); fall
        # back to plain psycopg2 — KingbaseES also speaks the PostgreSQL wire
        # protocol, so either driver connects.
        if _has_module("ksycopg2"):
            return f"kingbase+ksycopg2://{user}:{pwd}@{host}:{port or 54321}/{db}{qs(pg_extra)}"
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port or 54321}/{db}{qs(pg_extra)}"
    if dtype == "oracle":
        # python-oracledb thin mode is pure Python: no Oracle Instant Client
        # needed. database may be a SID or a service name; caller decides.
        service = params.get("service_name")
        if service:
            return f"oracle+oracledb://{user}:{pwd}@{host}:{port or 1521}/?service_name={quote(str(service), safe='')}"
        return f"oracle+oracledb://{user}:{pwd}@{host}:{port or 1521}/{db}"
    if dtype == "mssql":
        # pymssql wheels bundle FreeTDS: no unixODBC / msodbcsql system
        # packages, no "ODBC Driver 17" install required.
        #
        # Named instances: only the *default* instance listens on 1433. With an
        # instance name and no port we put "host\instance" into the server
        # string and let SQL Browser (UDP 1434) resolve the dynamic port.
        # A user-supplied port wins: FreeTDS then dials host:port directly,
        # which is the only workaround when UDP 1434 is blocked. pymssql
        # rejects specifying both an instance and a port at once, so the
        # instance is dropped from the server string in that case.
        instance = str(ds.get("instance") or "").strip().strip("\\")
        if "\\" in instance:
            # Tolerate "HOST\INSTANCE" pasted into the 实例名 field: the
            # instance is the last component.
            instance = instance.rsplit("\\", 1)[-1].strip()
        if "\\" in host:
            # Tolerate users typing "host\instance" into the host field.
            host, host_instance = host.split("\\", 1)
            instance = instance or host_instance.split("\\", 1)[0].strip()
        host = host.strip()
        # pymssql defaults login_timeout to 60 s; 10 s fails fast on an
        # unreachable host (user-overridable via connection params).
        extra = {
            "charset": params.get("charset"),
            "login_timeout": params.get("login_timeout", 10),
        }
        if params.get("tds_version"):
            extra["tds_version"] = params["tds_version"]
        if instance and not port:
            port_part = ""
            host = f"{host}\\{instance}"
        else:
            port_part = f":{port or 1433}"
        return f"mssql+pymssql://{user}:{pwd}@{host}{port_part}/{db}{qs(extra)}"
    if dtype == "db2":
        # IBM's official ibm_db_sa dialect; ibm_db wheels bundle the DB2
        # client (clidriver) for win/linux/mac, no separate DB2 client install.
        return f"ibm_db_sa://{user}:{pwd}@{host}:{port or 50000}/{db}"
    if dtype == "dm":
        # DmDialect is registered in app.db_dialects; the actual login goes
        # through the explicit creator in create_db_engine().
        return f"dm+dmpython://{user}:{pwd}@{host}:{port or 5236}/{db}"
    if dtype == "gbase":
        # GBase 8a speaks the MySQL protocol, so PyMySQL connects directly.
        # Users may still override via 'params.url'.
        if params.get("url"):
            return params["url"]
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port or 5258}/{db}"
    if dtype == "shentong":
        raise ValueError(
            "神通（ShenTong）官方仅提供 JDBC / ODBC 驱动，没有可随程序分发的 "
            "Python 驱动，无法开箱直连。请改用「其他（自定义）」数据源，"
            "自行安装驱动并在参数中填写 SQLAlchemy 连接字符串 url。"
        )
    if dtype == "custom":
        if params.get("url"):
            return params["url"]
        raise ValueError("自定义类型必须在 params 中提供 'url'（SQLAlchemy 连接字符串）。")

    raise ValueError(f"不支持的数据库类型: {dtype}")


def create_db_engine(ds: Dict[str, Any]) -> Engine:
    dtype = (ds.get("type") or "").lower()
    if dtype != "custom":
        # Every bundled driver resolves the host with the OS resolver; a
        # computer name Windows resolves via NetBIOS (e.g. DESKTOP-E4G0H7L)
        # fails on macOS/Linux and every driver then reports the same opaque
        # "unable to connect". Raising a user-facing ValueError here keeps the
        # test-connection message actionable and also improves the SQL and
        # schema-load failures.
        target_host = str(ds.get("host") or "localhost").split("\\", 1)[0].strip() or "localhost"
        if _host_settles(target_host) is False:
            raise ValueError(
                f"主机名「{target_host}」无法解析（DNS / hosts 查不到）。"
                "请改用服务器的 IP 地址；若必须使用计算机名，请将其加入路由器 DNS "
                "或本机 hosts 文件。"
            )
    url = build_engine_url(ds)
    engine_kwargs: Dict[str, Any] = {"pool_pre_ping": True, "future": True}

    # 自定义数据源：用户自备的驱动依赖目录先加进模块搜索路径，
    # 这样 url 里那个方言（如 jaydebeapi、jdbc+xxx）在 import 时能找到。
    lib_dir = ds.get("lib_dir")
    if lib_dir:
        import os
        import sys
        lib_dir = os.path.abspath(os.path.expanduser(str(lib_dir)))
        if os.path.isdir(lib_dir) and lib_dir not in sys.path:
            sys.path.insert(0, lib_dir)

    if dtype == "dm" and not _has_module("dmSQLAlchemy"):
        # Dameng's official dmSQLAlchemy dialect parses the URL itself when
        # installed. With only the fallback shim, log in through an explicit
        # creator (its create_connect_args is a no-op). dmPython is imported
        # lazily so merely selecting a DM data source without the
        # Windows/Linux-only wheel never raises at engine-construction time.
        host = ds.get("host") or "localhost"
        try:
            port = int(ds.get("port") or 5236)
        except (TypeError, ValueError):
            port = 5236
        username = ds.get("username") or ""
        password = ds.get("password") or ""

        def dm_creator() -> Any:
            import dmPython  # type: ignore

            return dmPython.connect(
                user=username, password=password, server=host, port=port,
            )

        engine_kwargs["creator"] = dm_creator

    return create_engine(url, **engine_kwargs)


# --- Engine cache ---
# Every schema fetch / SQL execution used to build its own Engine and dispose
# it afterwards, paying a fresh TCP + TLS + auth handshake each time. Paging
# through a result set made that noticeable on remote databases. Engines are
# cheap to keep: SQLAlchemy pools the underlying DBAPI connections and
# pool_pre_ping revalidates one before each use, so a long-idle entry is safe.
#
# The cache key includes every field that affects the connection (including the
# password), so editing a data source naturally misses into a new engine. Only
# a handful are kept so credentials from deleted/edited sources don't linger.
_MAX_CACHED_ENGINES = 4
_ENGINE_CACHE: "OrderedDict[tuple, Engine]" = OrderedDict()
_ENGINE_LOCK = threading.Lock()


def _engine_cache_key(ds: Dict[str, Any]) -> tuple:
    params = ds.get("params")
    if not isinstance(params, dict):
        params = {}
    return (
        str(ds.get("type") or "").lower(),
        str(ds.get("host") or ""),
        str(ds.get("port") or ""),
        str(ds.get("database") or ""),
        str(ds.get("username") or ""),
        str(ds.get("password") or ""),
        str(ds.get("instance") or ""),
        str(ds.get("lib_dir") or ""),
        tuple(sorted((str(k), str(v)) for k, v in params.items())),
    )


def get_engine(ds: Dict[str, Any]) -> Engine:
    """Return a cached Engine for ``ds``, creating and caching one on a miss.

    Callers must not ``dispose()`` the returned engine: it is shared with other
    workers. Use :func:`dispose_engines` once at application shutdown.
    """
    key = _engine_cache_key(ds)
    with _ENGINE_LOCK:
        engine = _ENGINE_CACHE.get(key)
        if engine is not None:
            _ENGINE_CACHE.move_to_end(key)
            return engine

    # Build outside the lock — URL construction/driver import can be slow and
    # must not block workers using other data sources.
    engine = create_db_engine(ds)

    stale: List[Engine] = []
    with _ENGINE_LOCK:
        existing = _ENGINE_CACHE.get(key)
        if existing is not None:
            # Another thread won the race; keep theirs and drop ours.
            _ENGINE_CACHE.move_to_end(key)
            stale.append(engine)
        else:
            _ENGINE_CACHE[key] = engine
            while len(_ENGINE_CACHE) > _MAX_CACHED_ENGINES:
                stale.append(_ENGINE_CACHE.popitem(last=False)[1])
    # Dispose unused engines outside the lock (closing sockets can block).
    for old in stale:
        try:
            old.dispose()
        except Exception:
            pass
    return existing if existing is not None else engine


def dispose_engines() -> None:
    """Close every pooled connection; call on application shutdown."""
    with _ENGINE_LOCK:
        engines = list(_ENGINE_CACHE.values())
        _ENGINE_CACHE.clear()
    for engine in engines:
        try:
            engine.dispose()
        except Exception:
            pass


def _connection_error_detail(e: Exception) -> str:
    """Best-effort readable text for a DBAPI / SQLAlchemy error.

    pymssql can raise ``OperationalError`` with an empty message (FreeTDS
    reports some connection failures only through side channels), which would
    otherwise render as a bare ``(pymssql.exceptions.OperationalError)``. Fall
    back to ``orig`` / ``args`` / ``repr`` so the toast always carries a clue.
    """
    orig = getattr(e, "orig", e)
    text = str(orig).strip()
    if text:
        return text
    args = getattr(orig, "args", ())
    if args:
        return ", ".join(repr(a) for a in args)
    return f"{type(orig).__name__}（驱动未提供错误信息）"


def _mssql_error_hint(ds: Dict[str, Any], detail: str) -> str:
    """Actionable next step for SQL Server connection failures."""
    host = ds.get("host") or "localhost"
    instance = str(ds.get("instance") or "").strip()
    if "\\" in host:
        host, host_instance = host.split("\\", 1)
        instance = instance or host_instance.strip()
    if "\\" in instance:
        instance = instance.rsplit("\\", 1)[-1].strip()
    try:
        port = int(ds.get("port") or 0)
    except (TypeError, ValueError):
        port = 0

    if instance and port:
        target = f"{host}:{port}（实例 {instance}）"
    elif instance:
        target = f"{host}\\{instance}（端口由 SQL Browser 解析）"
    else:
        target = f"{host}:{port or 1433}"

    if _host_settles(host) is False:
        return (f"连接目标: {target}。主机名「{host}」在本机无法解析（DNS / hosts 查不到）。"
                "请改用服务器的 IP 地址；若必须使用计算机名，请将其加入路由器 DNS 或本机 hosts 文件。")

    low = detail.lower()
    if "login failed" in low:
        step = ("若密码无误，请确认 SQL Server 已启用「SQL Server 和 Windows 身份验证」"
                "模式，且 sa 账号已启用（Navicat 可能用的是 Windows 认证）。")
    elif instance and not port:
        step = ("命名实例的端口由 SQL Server Browser 解析，连接不上通常是解析失败："
                "① 服务器上「SQL Server Browser」服务需为运行状态；"
                "② Windows 防火墙需放行 UDP 1434；"
                "③ 若无法放行，可在「端口」栏直接填写该实例的 TCP 端口"
                "（SQL Server 配置管理器 → SQL Server 网络配置 → TCP/IP → IP 地址）；"
                "④ 确认主机名可解析，必要时改用 IP 地址。"
                "SQL Server 2008 R2 等老版本还可在连接参数填 {\"tds_version\": \"7.3\"}。")
    elif (not detail or "未提供错误信息" in detail or "20009" in detail
          or "unable to connect" in low or "adaptive server" in low
          or "unknown error" in low):
        step = ("请确认主机可达、TCP/IP 协议已启用且端口可访问（必要时用 IP 代替主机名）；"
                "若该数据库是命名实例，请填写「实例名」或实例的实际端口。"
                "SQL Server 2008 R2 等老版本可在连接参数填 {\"tds_version\": \"7.3\"}。")
    else:
        step = "SQL Server 2008 R2 等老版本可尝试在连接参数填 {\"tds_version\": \"7.3\"}。"
    return f"连接目标: {target}。{step}"


def _host_settles(host: str, timeout: float = 3.0) -> Optional[bool]:
    """True / False once the OS resolver answers; None if it takes too long.

    Every bundled driver resolves the host with the OS resolver, so a computer
    name Windows resolves via NetBIOS (e.g. ``DESKTOP-E4G0H7L``) fails on
    macOS / Linux DNS with the same opaque "unable to connect" error as a
    blocked port. Checking up front lets us name the real cause. A slow
    resolver returns None and the normal connect attempt decides.
    """
    result: List[bool] = []

    def work() -> None:
        try:
            socket.getaddrinfo(host, None)
            result.append(True)
        except OSError:
            result.append(False)

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout)
    return result[0] if result else None


def test_connection(ds: Dict[str, Any]) -> Tuple[bool, str]:
    """Try connecting; returns (ok, message)."""
    dtype = (ds.get("type") or "").lower()
    try:
        engine = create_db_engine(ds)
    except ImportError as e:
        # SQLAlchemy surfaces a missing DBAPI/dialect as ImportError with
        # "No module named ..." — not always ModuleNotFoundError.
        hint = DRIVER_HINTS.get(dtype, {})
        return False, f"缺少驱动: {e}\n请安装: {hint.get('install', '')}"
    except ValueError as e:
        # Deliberate, already-user-facing guidance (e.g. ShenTong).
        return False, str(e)
    except Exception as e:
        return False, f"URL 构造失败: {e}"

    try:
        # Oracle (pre-23c) and DM require a FROM clause; DUAL exists on both.
        # DB2 has no DUAL — its single-row dummy table is SYSIBM.SYSDUMMY1.
        if dtype in ("oracle", "dm"):
            ping = "SELECT 1 FROM DUAL"
        elif dtype == "db2":
            ping = "SELECT 1 FROM SYSIBM.SYSDUMMY1"
        else:
            ping = "SELECT 1"
        with engine.connect() as conn:
            conn.execute(text(ping))
        return True, "连接成功！"
    except ImportError as e:
        hint = DRIVER_HINTS.get((ds.get("type") or "").lower(), {})
        return False, f"缺少驱动: {e}\n请安装: {hint.get('install', '')}"
    except Exception as e:
        detail = _connection_error_detail(e)
        msg = f"连接失败: {detail}" if detail else "连接失败"
        if dtype == "mssql":
            msg += f"\n{_mssql_error_hint(ds, detail)}"
        return False, msg
    finally:
        try:
            engine.dispose()
        except Exception:
            pass


# --- Schema introspection (for schema-aware text-to-SQL) ---

# Hard caps so a database with thousands of tables can't blow the prompt. When
# the schema is larger than this, tables are ranked against the user's question
# and only the most relevant ones are sent (see build_schema_section).
MAX_SCHEMA_TABLES = 200
MAX_SCHEMA_CHARS = 20000


def _multi_reflection(insp, method: str, names: List[str]) -> Dict[str, Any]:
    """Call an SQLAlchemy 2.0 ``get_multi_*`` reflection method if supported.

    Returns ``{table_name: value}`` with schema-qualified keys normalized to
    the bare table name; an empty dict means this dialect can't batch-reflect
    that kind of metadata and callers should fall back to per-table calls.
    """
    fn = getattr(insp, method, None)
    if not callable(fn):
        return {}
    try:
        raw = fn(filter_names=names)
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Any] = {}
    for key, value in raw.items():
        # Single-schema inspectors may key by (schema, table) tuples.
        name = key[-1] if isinstance(key, tuple) else str(key).rsplit(".", 1)[-1]
        out[name] = value
    return out


def introspect_schema(
    engine: Engine, limit: Optional[int] = None, query: str = ""
) -> Tuple[List[Dict[str, Any]], int]:
    """Return (tables, total_count) for the default schema.

    Uses SQLAlchemy's Inspector rather than per-dialect ``information_schema``
    SQL, so MySQL / PostgreSQL / Oracle / SQL Server / the PG-compatible
    domestic databases all go through the same code path. Anything a given
    dialect can't provide (column comments are not introspected on PostgreSQL,
    for instance) simply degrades to empty instead of failing.

    ``limit`` caps the number of tables we fetch columns/FKs for. Metadata
    queries are per table, so on a database with thousands of tables this is
    the difference between a second and minutes; ``total_count`` still reports
    how many exist so the prompt note stays accurate. When more tables exist
    than ``limit``, names are pre-ranked against ``query`` — otherwise a
    relevant table sorted past the limit would never reach the finer ranking in
    :func:`build_schema_section` (which needs columns to score).
    """
    insp = inspect(engine)

    names: List[Tuple[str, str]] = [(n, "table") for n in insp.get_table_names()]
    get_views = getattr(insp, "get_view_names", None)
    if callable(get_views):
        try:
            names += [(n, "view") for n in get_views()]
        except Exception:
            pass
    total = len(names)
    if limit is not None:
        q = _tokens(query) if query else set()
        if total > limit and q:
            order = sorted(
                range(total),
                key=lambda i: (-len(q & _tokens(names[i][0])), i),
            )
            names = [names[i] for i in order[:limit]]
        else:
            names = names[:limit]

    # Batch metadata where the dialect supports it (SQLAlchemy 2.0): one query
    # for columns, one for PKs, etc. instead of ~4 round-trips per table, which
    # dominates schema loading on a remote database. Views / dialects without
    # batch support transparently fall back to the per-table calls below.
    table_names = [n for n, _ in names]
    bulk_cols = _multi_reflection(insp, "get_multi_columns", table_names)
    bulk_pks = _multi_reflection(insp, "get_multi_pk_constraint", table_names)
    bulk_fks = _multi_reflection(insp, "get_multi_foreign_keys", table_names)
    bulk_comments = _multi_reflection(insp, "get_multi_table_comment", table_names)

    tables: List[Dict[str, Any]] = []
    for name, kind in names:
        raw_cols = bulk_cols.get(name)
        if raw_cols is None:
            try:
                raw_cols = insp.get_columns(name)
            except Exception:
                raw_cols = []
        columns = [
            {
                "name": c.get("name", ""),
                "type": str(c["type"]) if c.get("type") is not None else "",
                "nullable": c.get("nullable", True),
                # Only some dialects (notably MySQL) report column comments.
                "comment": c.get("comment") or "",
            }
            for c in raw_cols
        ]

        pk_entry = bulk_pks.get(name)
        if not isinstance(pk_entry, dict):
            try:
                pk_entry = insp.get_pk_constraint(name) or {}
            except Exception:
                pk_entry = {}
        pk = list(pk_entry.get("constrained_columns") or [])

        raw_fks = bulk_fks.get(name)
        if not isinstance(raw_fks, list):
            try:
                raw_fks = insp.get_foreign_keys(name)
            except Exception:
                raw_fks = []
        fks = [
            {
                "cols": list(fk.get("constrained_columns") or []),
                "ref_table": fk.get("referred_table") or "",
                "ref_cols": list(fk.get("referred_columns") or []),
            }
            for fk in raw_fks
            if fk.get("referred_table")
        ]

        comment_entry = bulk_comments.get(name)
        if isinstance(comment_entry, dict):
            comment = comment_entry.get("text") or ""
        else:
            comment = ""
            try:
                comment = (insp.get_table_comment(name) or {}).get("text") or ""
            except Exception:
                pass

        tables.append(
            {"name": name, "kind": kind, "comment": comment, "pk": pk,
             "columns": columns, "fks": fks}
        )
    return tables, total


def render_table(t: Dict[str, Any]) -> str:
    """Render one table/view as CREATE TABLE-style DDL for the model's context.

    This is LLM context, not something we ever execute, so comments are attached
    as trailing ``--`` lines rather than dialect-specific ``COMMENT ON`` syntax.
    Views are written to look like tables because the model only needs to know
    they can be SELECTed with these columns.
    """
    is_view = t.get("kind") == "view"
    head = f"-- 视图（可直接 SELECT）: {t['name']}" if is_view else f"-- 表: {t['name']}"
    if t.get("comment"):
        head += f"  {t['comment']}"

    pk = set(t.get("pk") or [])
    lines = []
    for c in t.get("columns", []):
        line = f"  {c['name']} {c.get('type') or 'TEXT'}"
        if c.get("nullable") is False:
            line += " NOT NULL"
        if c["name"] in pk:
            line += " PRIMARY KEY"
        if c.get("comment"):
            line += f"  -- {c['comment']}"
        lines.append(line)
    for fk in t.get("fks") or []:
        cols = ", ".join(fk["cols"])
        ref_cols = ", ".join(fk["ref_cols"]) or "id"
        lines.append(
            f"  FOREIGN KEY ({cols}) REFERENCES {fk['ref_table']}({ref_cols})"
        )

    keyword = "VIEW" if is_view else "TABLE"
    return f"{head}\nCREATE {keyword} {t['name']} (\n" + ",\n".join(lines) + "\n);"


_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}")
_CJK_RUN_RE = re.compile(r"[一-鿿]+")


def _tokens(text: str) -> set:
    """Latin/digit words plus CJK character bigrams.

    Chinese has no spaces, so for Chinese table/column comments we compare
    overlapping 2-character sequences — "数学" in the question then matches the
    "数学" bigram in a column comment like "数学成绩".
    """
    low = str(text or "").lower()
    raw = _TOKEN_RE.findall(low)
    toks = set(raw)
    # Identifier-style tokens ("student_info") also contribute their parts, so
    # an English question saying "student" matches the table name.
    toks.update(part for tok in raw for part in tok.split("_") if len(part) >= 2)
    # Bigrams only within contiguous CJK runs: joining characters across a
    # space/punctuation ("订单 明细" -> "单明") would create phantom matches.
    for run in _CJK_RUN_RE.findall(low):
        toks.update(run[i:i + 2] for i in range(len(run) - 1))
    return toks


def _table_tokens(t: Dict[str, Any]) -> set:
    parts = [t.get("name", ""), t.get("comment", "")]
    parts += [c["name"] + " " + c.get("comment", "") for c in t.get("columns", [])]
    return _tokens(" ".join(parts))


def _rank_tables(tables: List[Dict[str, Any]], query: str) -> List[float]:
    """Relevance score per table for ``query``.

    Shared tokens are weighted by inverse document frequency across the schema:
    a bigram like "数学" that names one table beats a near-universal one like
    "信息" that happens to appear in several comments.
    """
    q = _tokens(query)
    if not q:
        return [0.0] * len(tables)
    token_sets = [_table_tokens(t) for t in tables]
    doc_freq: Dict[str, int] = {}
    for s in token_sets:
        for tok in s:
            doc_freq[tok] = doc_freq.get(tok, 0) + 1
    n = len(tables)
    scores = []
    for s in token_sets:
        scores.append(
            sum(1.0 + math.log((n + 1) / (doc_freq[tok] + 1)) for tok in q & s)
        )
    return scores


def build_schema_section(
    tables: List[Dict[str, Any]], description: str = "",
    max_chars: int = MAX_SCHEMA_CHARS, max_tables: int = MAX_SCHEMA_TABLES,
    total_tables: Optional[int] = None,
) -> Tuple[str, int, int]:
    """Render the schema for the prompt, trimming if it exceeds the budget.

    Returns ``(section, shown, total)``. When every table fits, all are sent.
    Otherwise tables are scored against ``description`` (Latin words + CJK
    bigrams) and the most relevant are kept, with a note about how many were
    omitted.
    """
    all_n = len(tables) if total_tables is None else total_tables
    considered = tables[:max_tables]
    beyond_cap = max(0, all_n - max_tables)
    blocks = [render_table(t) for t in considered]

    if sum(len(b) for b in blocks) <= max_chars:
        chosen = list(range(len(blocks)))
    else:
        scores = _rank_tables(considered, description)
        if any(s > 0 for s in scores):
            order = sorted(range(len(blocks)), key=lambda i: (-scores[i], i))
        else:
            order = list(range(len(blocks)))
        chosen = []
        used = 0
        for i in order:
            extra = len(blocks[i]) + 2
            if used + extra > max_chars and chosen:
                continue
            chosen.append(i)
            used += extra
        chosen.sort()

    body = "\n\n".join(blocks[i] for i in chosen)
    omitted = (len(considered) - len(chosen)) + beyond_cap
    note = ""
    if omitted > 0:
        note = (
            f"\n\n-- 注意：数据库中还有 {omitted} 张表/视图因篇幅未列出，"
            "如确有需要请在问题中点名相关表。"
        )
    return body + note, len(chosen), all_n


def fetch_schema_text(
    ds: Dict[str, Any], description: str = "",
    max_chars: int = MAX_SCHEMA_CHARS, max_tables: int = MAX_SCHEMA_TABLES,
) -> Tuple[str, int, int]:
    """Open the data source, introspect it, and return (section, shown, total).

    Uses the shared engine cache; callers run this on a worker thread.
    """
    engine = get_engine(ds)
    # Only max_tables are ever considered below, so don't pay for metadata
    # queries on the rest; names are ranked against the question first so
    # the cap keeps the relevant tables rather than the first N by name.
    tables, total = introspect_schema(engine, limit=max_tables, query=description)
    return build_schema_section(
        tables, description, max_chars, max_tables, total_tables=total
    )


# --- SQL execution ---

_LEADING_COMMENT_RE = re.compile(
    r"^\s*(?:(?:--[^\n]*(?:\n|$))|(?:#[^\n]*(?:\n|$))|(?:/\*.*?\*/\s*))*",
    re.DOTALL,
)
_KEYWORD_RE = re.compile(r"[\(\s]*([A-Za-z_]+)")
_SELECT_KEYWORDS = {"SELECT", "WITH", "SHOW", "DESC", "DESCRIBE", "EXPLAIN"}


def leading_keyword(sql: str) -> str:
    """First significant keyword, ignoring leading comments and parentheses.

    ``-- report\\nSELECT ...`` and ``(SELECT ...) UNION ...`` must still be
    recognized as queries, otherwise they fall into the non-SELECT execution
    path and return no rows.
    """
    text = _LEADING_COMMENT_RE.sub("", sql or "")
    m = _KEYWORD_RE.match(text)
    return m.group(1).upper() if m else ""


def is_select(sql: str) -> bool:
    return leading_keyword(sql) in _SELECT_KEYWORDS


# --- SQL pre-check ---


_MYSQL_FAMILY = {"mysql", "mariadb", "oceanbase", "tidb", "gbase"}


def _delimiter_error(sql: str, hash_comments: bool, backslash_escapes: bool) -> str:
    """Scan SQL for unbalanced parens/quotes, ignoring comments and literals.

    A naive ``count("(")`` breaks on literals such as ``'销售(华东'`` and a
    ``re.sub`` for ``--`` breaks on ``'a--b'``; this single-pass scanner keeps
    string literals, quoted identifiers and comments out of the count.
    """
    depth = 0
    i, n = 0, len(sql)
    in_squote = in_dquote = in_backtick = in_bracket = False
    in_line_comment = in_block_comment = False

    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_squote:
            if backslash_escapes and ch == "\\" and nxt:
                i += 2  # MySQL backslash escape; standard SQL keeps it literal
                continue
            if ch == "'":
                if nxt == "'":
                    i += 2  # SQL doubled quote
                    continue
                in_squote = False
            i += 1
            continue
        if in_dquote:
            if ch == '"':
                if nxt == '"':
                    i += 2
                    continue
                in_dquote = False
            i += 1
            continue
        if in_backtick:
            if ch == "`":
                in_backtick = False
            i += 1
            continue
        if in_bracket:
            if ch == "]":
                in_bracket = False
            i += 1
            continue

        if ch == "-" and nxt == "-":
            in_line_comment = True
            i += 2
            continue
        if hash_comments and ch == "#":
            in_line_comment = True
            i += 1
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == "'":
            in_squote = True
        elif ch == '"':
            in_dquote = True
        elif ch == "`":
            in_backtick = True
        elif ch == "[":
            in_bracket = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return "圆括号不匹配"
        i += 1

    if in_squote:
        return "单引号不闭合"
    if in_dquote or in_backtick or in_bracket:
        return "引号不闭合"
    if in_block_comment:
        return "块注释未闭合"
    if depth != 0:
        return "圆括号不匹配"
    return ""


def precheck_sql(sql: str, db_type: str = "") -> Tuple[bool, str]:
    """Cheap syntactic sanity check on AI-generated SQL.

    Returns (ok, message). This is a fail-fast layer that catches the common
    ways AI output goes wrong (empty output, only comments, unbalanced
    delimiters). It does NOT parse SQL fully — that's the database's job at
    execute time.

    ``db_type`` only selects dialect quirks that matter for the scan: ``#`` is
    a comment in the MySQL family but starts a temp-table name in SQL Server
    (``SELECT * FROM #tmp``).
    """
    if not sql or not sql.strip():
        return False, "SQL 为空"

    stripped = sql.strip()

    # Comment-only?
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    if lines and all(ln.startswith("--") or ln.startswith("#") for ln in lines):
        return False, "SQL 只包含注释，没有可执行语句"

    # Try to parse with sqlparse - not a full validator, but catches obviously
    # broken input (e.g. AI returned prose).
    try:
        import sqlparse
        parsed = sqlparse.parse(stripped)
        if not parsed or not parsed[0].tokens:
            return False, "SQL 解析为空"
        # Look for at least one recognizable DML/DDL keyword.
        upper = stripped.upper()
        if not re.search(
            r"\b(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|"
            r"TRUNCATE|SHOW|DESC|DESCRIBE|EXPLAIN|GRANT|REVOKE|CALL|MERGE)\b",
            upper,
        ):
            return False, "未检测到 SQL 关键字（SELECT / INSERT / UPDATE / CREATE ...）"
    except Exception:
        # sqlparse is very tolerant, so this really is unusual.
        pass

    # Balanced parentheses & quotes (literals/comments excluded).
    is_mysql = db_type.lower() in _MYSQL_FAMILY or not db_type
    err = _delimiter_error(stripped, hash_comments=is_mysql,
                           backslash_escapes=is_mysql)
    if err:
        return False, err

    return True, ""



def _strip_trailing_semi(sql: str) -> str:
    return (sql or "").strip().rstrip(";").strip()


def build_paginated_sql(sql: str, dtype: str, offset: int, limit: int) -> str:
    """Wrap a SELECT with pagination that works across dialects."""
    body = _strip_trailing_semi(sql)
    dtype = (dtype or "").lower()

    if dtype in ("mysql", "mariadb", "postgresql", "opengauss", "highgo", "vastbase",
                 "kingbase", "oceanbase", "tidb", "gbase"):
        return f"SELECT * FROM ({body}) AS __t LIMIT {limit} OFFSET {offset}"
    if dtype == "mssql":
        # OFFSET/FETCH only exists on SQL Server 2012+; 2005–2008 R2 need the
        # ROW_NUMBER() form. The trailing __muask_rn column is stripped by the
        # execution worker before the rows reach the table view.
        return (
            "SELECT * FROM ("
            "SELECT __t.*, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS __muask_rn "
            f"FROM ({body}) __t"
            f") __p WHERE __p.__muask_rn > {offset} "
            f"AND __p.__muask_rn <= {offset + limit}"
        )
    if dtype in ("oracle", "db2"):
        # SQL:2008 syntax - Oracle 12c+, DB2 11+ (neither requires ORDER BY)
        return f"SELECT * FROM ({body}) __t OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
    if dtype in ("dm",):
        return f"SELECT * FROM ({body}) __t LIMIT {limit} OFFSET {offset}"
    if dtype in ("shentong", "custom"):
        # Try the SQL:2008 form
        return f"SELECT * FROM ({body}) __t OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"

    return f"SELECT * FROM ({body}) __t LIMIT {limit} OFFSET {offset}"


def build_count_sql(sql: str) -> str:
    """Build a COUNT(*) that wraps the SELECT."""
    body = _strip_trailing_semi(sql)
    return f"SELECT COUNT(*) AS __cnt FROM ({body}) __t"


def run_select(engine: Engine, sql: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        cols = list(result.keys())
        rows = [tuple(r) for r in result.fetchall()]
        return cols, rows


def run_select_slice(
    engine: Engine, sql: str, offset: int, limit: int
) -> Tuple[List[str], List[Tuple[Any, ...]], bool]:
    """Client-side pagination fallback for SQL that cannot be wrapped.

    Derived-table wrapping fails for statements starting with ``WITH`` and for
    SQL Server queries with a top-level ``ORDER BY``. Streaming the original
    statement and skipping ``offset`` rows keeps those queries usable instead
    of failing outright. Returns ``(cols, rows, has_more)``.
    """
    rows: List[Tuple[Any, ...]] = []
    with engine.connect() as conn:
        result = conn.execution_options(stream_results=True).execute(text(sql))
        cols = list(result.keys())
        for idx, row in enumerate(result):
            if idx < offset:
                continue
            if len(rows) > limit:  # fetch one extra row to detect a next page
                break
            rows.append(tuple(row))
    has_more = len(rows) > limit
    return cols, rows[:limit], has_more


def run_scalar(engine: Engine, sql: str) -> Any:
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def run_non_select(engine: Engine, sql: str) -> int:
    """Execute a non-SELECT statement in a transaction. Returns affected rowcount (-1 if unknown)."""
    with engine.begin() as conn:
        result = conn.execute(text(sql))
        try:
            return int(result.rowcount) if result.rowcount is not None else -1
        except Exception:
            return -1
