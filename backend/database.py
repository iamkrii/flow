"""Database layer: dual-mode (SQLite for local dev, Oracle Cloud for production)."""
import os
import sqlite3
import threading
from contextlib import contextmanager

from . import config


def _oracle_connect_params():
    if config.ORACLE_DSN:
        dsn = config.ORACLE_DSN
    else:
        dsn = f"{config.ORACLE_HOST}:{config.ORACLE_PORT}/{config.ORACLE_SERVICE}"
    kwargs = {
        "user": config.ORACLE_USER,
        "password": config.ORACLE_PASSWORD,
        "dsn": dsn,
    }
    if config.ORACLE_WALLET_DIR:
        kwargs["config_dir"] = config.ORACLE_WALLET_DIR
        kwargs["wallet_location"] = config.ORACLE_WALLET_DIR
        kwargs["wallet_password"] = config.ORACLE_WALLET_PASSWORD
    return kwargs


if config.DB_MODE == "oracle":
    import oracledb
    _pool = None
    _pool_lock = threading.Lock()

    def get_pool():
        global _pool
        if _pool is None:
            with _pool_lock:
                if _pool is None:
                    _pool = oracledb.create_pool(min=1, max=5, increment=1, **_oracle_connect_params())
        return _pool

    @contextmanager
    def get_conn():
        conn = get_pool().acquire()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            get_pool().release(conn)

else:

    _local = threading.local()

    @contextmanager
    def get_conn():
        conn = getattr(_local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(config.SQLITE_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            _local.conn = conn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

ORACLE_SCHEMA = """
CREATE TABLE users (
    id VARCHAR2(32) DEFAULT LOWER(RAWTOHEX(SYS_GUID())) PRIMARY KEY,
    email VARCHAR2(255) NOT NULL UNIQUE,
    password_hash VARCHAR2(512) NOT NULL,
    name VARCHAR2(120),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
)
"""

SQLITE_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        name TEXT,
        created_at TEXT NOT NULL
    )""",
]

TABLES_ORACLE = {
    "periods": """CREATE TABLE periods (
        id VARCHAR2(32) PRIMARY KEY,
        user_id VARCHAR2(32) NOT NULL REFERENCES users(id),
        start_date DATE NOT NULL,
        end_date DATE,
        flow_level NUMBER(2),
        notes VARCHAR2(2000),
        created_at TIMESTAMP DEFAULT SYSTIMESTAMP
    )""",
    "symptoms": """CREATE TABLE symptoms (
        id VARCHAR2(32) PRIMARY KEY,
        user_id VARCHAR2(32) NOT NULL REFERENCES users(id),
        log_date DATE NOT NULL,
        symptom VARCHAR2(80) NOT NULL,
        severity NUMBER(2),
        notes VARCHAR2(1000),
        created_at TIMESTAMP DEFAULT SYSTIMESTAMP
    )""",
    "moods": """CREATE TABLE moods (
        id VARCHAR2(32) PRIMARY KEY,
        user_id VARCHAR2(32) NOT NULL REFERENCES users(id),
        log_date DATE NOT NULL,
        mood VARCHAR2(60) NOT NULL,
        energy NUMBER(2),
        created_at TIMESTAMP DEFAULT SYSTIMESTAMP
    )""",
    "daily_logs": """CREATE TABLE daily_logs (
        id VARCHAR2(32) PRIMARY KEY,
        user_id VARCHAR2(32) NOT NULL REFERENCES users(id),
        log_date DATE NOT NULL,
        weight_kg NUMBER(5,1),
        temperature_c NUMBER(4,1),
        discharge VARCHAR2(40),
        intercourse NUMBER(1),
        medication VARCHAR2(500),
        cramps NUMBER(2),
        notes VARCHAR2(2000),
        created_at TIMESTAMP DEFAULT SYSTIMESTAMP
    )""",
    "settings": """CREATE TABLE settings (
        user_id VARCHAR2(32) PRIMARY KEY REFERENCES users(id),
        avg_cycle_length NUMBER(3) DEFAULT 28,
        avg_period_length NUMBER(3) DEFAULT 5,
        luteal_phase_length NUMBER(3) DEFAULT 14,
        birth_control VARCHAR2(40),
        notifications_enabled NUMBER(1) DEFAULT 1
    )""",
}

TABLES_SQLITE = {k: v.replace("VARCHAR2", "TEXT").replace("NUMBER(1)", "INTEGER")
                 for k, v in TABLES_ORACLE.items()}

# generic numeric types for sqlite
TABLES_SQLITE = {}
for k, v in TABLES_ORACLE.items():
    s = v.replace("VARCHAR2(32)", "TEXT").replace("VARCHAR2(255)", "TEXT") \
         .replace("VARCHAR2(512)", "TEXT").replace("VARCHAR2(120)", "TEXT") \
         .replace("VARCHAR2(80)", "TEXT").replace("VARCHAR2(60)", "TEXT") \
         .replace("VARCHAR2(40)", "TEXT").replace("VARCHAR2(500)", "TEXT") \
         .replace("VARCHAR2(1000)", "TEXT").replace("VARCHAR2(2000)", "TEXT") \
         .replace("TIMESTAMP", "TEXT").replace("SYSTIMESTAMP", "(datetime('now'))") \
         .replace("DATE ", "TEXT ")
    import re as _re
    s = _re.sub(r"NUMBER\(\d+(,\d+)?\)", "REAL", s)
    s = s.replace("REFERENCES users(id)", 'REFERENCES users(id)')
    TABLES_SQLITE[k] = s


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        if config.DB_MODE == "sqlite":
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='users'")
            if not cur.fetchone()[0]:
                for ddl in SQLITE_SCHEMA:
                    cur.execute(ddl)
                for ddl in TABLES_SQLITE.values():
                    cur.execute(ddl)
        else:
            # Oracle: create tables if missing
            def exists(name):
                cur.execute(
                    "SELECT COUNT(*) FROM user_tables WHERE table_name = UPPER(:n)", {"n": name}
                )
                return cur.fetchone()[0] > 0

            cur.execute(ORACLE_SCHEMA.replace("CREATE TABLE users ", "CREATE TABLE users "))
            for name, ddl in TABLES_ORACLE.items():
                if not exists(name):
                    cur.execute(ddl)


# ---------------------------------------------------------------------------
# Small query helpers that work on both engines
# ---------------------------------------------------------------------------

def q(sql_oracle: str, sql_sqlite: str, params=None, one=False):
    """Run a query with engine-specific SQL."""
    sql = sql_oracle if config.DB_MODE == "oracle" else sql_sqlite
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or {})
        cols = [d[0].lower() for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return (rows[0] if rows else None) if one else rows


def ex(sql: str, params=None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or {})
        return cur.rowcount
