"""SQLite-only persistence for local development.

SQLite is intentionally kept in its own module. It remains the simple,
zero-configuration fallback used by the local test suite and development
script.
"""
import os
import re
import sqlite3
import threading
from contextlib import contextmanager

from . import config


SCHEMA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "sql", "oracle_schema.sql")
)


def configure_app(_app):
    """Keep the backend interface consistent; SQLite needs no app setup."""


def _schema_statements():
    """Read the shared Oracle schema as individual executable statements."""

    with open(SCHEMA_PATH, encoding="utf-8") as schema_file:
        script = schema_file.read()

    # The assignment schema is intentionally a DDL-only script, so removing
    # line comments and splitting on semicolons is sufficient and readable.
    script = re.sub(r"--.*?(?=\n|$)", "", script)
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def _sqlite_statement(oracle_statement):
    """Translate the shared Oracle DDL into SQLite-compatible DDL."""

    statement = re.sub(
        r"\s+DEFAULT\s+LOWER\(RAWTOHEX\(SYS_GUID\(\)\)\)",
        "",
        oracle_statement,
        flags=re.IGNORECASE,
    )
    statement = re.sub(r"\bVARCHAR2\(\d+\)", "TEXT", statement, flags=re.IGNORECASE)
    statement = re.sub(r"\bNUMBER\(\d+(?:,\d+)?\)", "REAL", statement, flags=re.IGNORECASE)
    statement = re.sub(r"\bTIMESTAMP\b", "TEXT", statement, flags=re.IGNORECASE)
    statement = re.sub(r"\bDATE\b", "TEXT", statement, flags=re.IGNORECASE)
    statement = re.sub(r"\bSYSTIMESTAMP\b", "(datetime('now'))", statement, flags=re.IGNORECASE)
    statement = re.sub(
        r"^\s*CREATE\s+TABLE\b",
        "CREATE TABLE IF NOT EXISTS",
        statement,
        flags=re.IGNORECASE,
    )
    statement = re.sub(
        r"^\s*CREATE\s+INDEX\b",
        "CREATE INDEX IF NOT EXISTS",
        statement,
        flags=re.IGNORECASE,
    )
    return statement


_local = threading.local()


@contextmanager
def get_conn():
    """Yield the current thread's SQLite connection and commit its work."""

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


def init_db():
    """Create the local SQLite schema from the authoritative SQL file."""

    with get_conn() as conn:
        for statement in _schema_statements():
            conn.execute(_sqlite_statement(statement))


def q(sql: str, legacy_sql=None, params=None, one=False):
    """Run a SQLite query and return dictionaries instead of driver rows.

    ``legacy_sql`` preserves the old ``q(sql_oracle, sql_sqlite, ...)`` call
    shape for any external code while the application now uses backend methods.
    """

    if isinstance(legacy_sql, str):
        sql = legacy_sql
    elif legacy_sql is not None and params is None:
        # New backend methods pass q(sql, params); keep that convenient form.
        params = legacy_sql

    with get_conn() as conn:
        cur = conn.execute(sql, params or {})
        rows = [dict(row) for row in cur.fetchall()]
    return (rows[0] if rows else None) if one else rows


def ex(sql: str, params=None):
    """Run a SQLite write and return its affected-row count."""

    with get_conn() as conn:
        cur = conn.execute(sql, params or {})
        return cur.rowcount


# The route layer uses these functions through the small backend facade.
# Keeping them here makes it clear that no SQLite connection code is imported
# when the application runs in Oracle mode.
def get_user_by_email(email):
    return q("SELECT * FROM users WHERE lower(email)=lower(:email)", {"email": email}, one=True)


def get_user(user_id):
    return q("SELECT * FROM users WHERE id=:user_id", {"user_id": user_id}, one=True)


def email_exists(email, except_user_id=None):
    sql = "SELECT id FROM users WHERE lower(email)=lower(:email)"
    params = {"email": email}
    if except_user_id:
        sql += " AND id<>:user_id"
        params["user_id"] = except_user_id
    return q(sql, params, one=True) is not None


def create_user(user_id, email, password_hash, name):
    ex(
        "INSERT INTO users (id, email, password_hash, name, created_at) "
        "VALUES (:id,:email,:password_hash,:name,datetime('now'))",
        {"id": user_id, "email": email, "password_hash": password_hash, "name": name or ""},
    )
    ex(
        "INSERT INTO settings (user_id, avg_cycle_length, avg_period_length, "
        "luteal_phase_length, birth_control, notifications_enabled) "
        "VALUES (:user_id,28,5,14,NULL,1)",
        {"user_id": user_id},
    )


def get_settings(user_id):
    return q("SELECT * FROM settings WHERE user_id=:user_id", {"user_id": user_id}, one=True)


def update_user(user_id, email, name):
    ex(
        "UPDATE users SET email=:email, name=:name WHERE id=:user_id",
        {"email": email, "name": name or "", "user_id": user_id},
    )
    return get_user(user_id)


def delete_user(user_id):
    for table in ("periods", "symptoms", "moods", "daily_logs", "settings"):
        ex(f"DELETE FROM {table} WHERE user_id=:user_id", {"user_id": user_id})
    return ex("DELETE FROM users WHERE id=:user_id", {"user_id": user_id}) > 0


def save_settings(user_id, values):
    row = get_settings(user_id)
    if not row:
        ex(
            "INSERT INTO settings (user_id, avg_cycle_length, avg_period_length, "
            "luteal_phase_length, birth_control, notifications_enabled) "
            "VALUES (:user_id,:cycle,:period,:luteal,:birth_control,:notifications)",
            {
                "user_id": user_id,
                "cycle": values.get("avg_cycle_length") or 28,
                "period": values.get("avg_period_length") or 5,
                "luteal": values.get("luteal_phase_length") or 14,
                "birth_control": values.get("birth_control"),
                "notifications": 1 if values.get("notifications_enabled", True) else 0,
            },
        )
    else:
        assignments = []
        params = {"user_id": user_id, "notifications": 1 if values.get("notifications_enabled", True) else 0}
        for field in ("avg_cycle_length", "avg_period_length", "luteal_phase_length", "birth_control"):
            if values.get(field) is not None:
                assignments.append(f"{field}=:{field}")
                params[field] = values[field]
        assignments.append("notifications_enabled=:notifications")
        ex(f"UPDATE settings SET {', '.join(assignments)} WHERE user_id=:user_id", params)
    return get_settings(user_id)


def delete_settings(user_id):
    ex("DELETE FROM settings WHERE user_id=:user_id", {"user_id": user_id})


def _list(table, user_id, date_column):
    return q(
        f"SELECT * FROM {table} WHERE user_id=:user_id ORDER BY {date_column} DESC",
        {"user_id": user_id},
    )


def list_periods(user_id):
    return q("SELECT * FROM periods WHERE user_id=:user_id ORDER BY start_date DESC", {"user_id": user_id})


def create_period(values):
    ex(
        "INSERT INTO periods (id, user_id, start_date, end_date, flow_level, notes) "
        "VALUES (:id,:user_id,:start_date,:end_date,:flow_level,:notes)",
        values,
    )


def update_period(period_id, user_id, values):
    return ex(
        "UPDATE periods SET start_date=:start_date, end_date=:end_date, flow_level=:flow_level, notes=:notes "
        "WHERE id=:id AND user_id=:user_id",
        {**values, "id": period_id, "user_id": user_id},
    ) > 0


def delete_period(period_id, user_id):
    return ex("DELETE FROM periods WHERE id=:id AND user_id=:user_id", {"id": period_id, "user_id": user_id}) > 0


def list_symptoms(user_id):
    return _list("symptoms", user_id, "log_date")


def create_symptom(values):
    ex(
        "INSERT INTO symptoms (id, user_id, log_date, symptom, severity, notes) "
        "VALUES (:id,:user_id,:log_date,:symptom,:severity,:notes)",
        values,
    )


def update_symptom(symptom_id, user_id, values):
    return ex(
        "UPDATE symptoms SET log_date=:log_date, symptom=:symptom, severity=:severity, notes=:notes "
        "WHERE id=:id AND user_id=:user_id",
        {**values, "id": symptom_id, "user_id": user_id},
    ) > 0


def delete_symptom(symptom_id, user_id):
    ex("DELETE FROM symptoms WHERE id=:id AND user_id=:user_id", {"id": symptom_id, "user_id": user_id})


def list_moods(user_id):
    return _list("moods", user_id, "log_date")


def create_mood(values):
    ex(
        "INSERT INTO moods (id, user_id, log_date, mood, energy) "
        "VALUES (:id,:user_id,:log_date,:mood,:energy)",
        values,
    )


def update_mood(mood_id, user_id, values):
    return ex(
        "UPDATE moods SET log_date=:log_date, mood=:mood, energy=:energy "
        "WHERE id=:id AND user_id=:user_id",
        {**values, "id": mood_id, "user_id": user_id},
    ) > 0


def delete_mood(mood_id, user_id):
    ex("DELETE FROM moods WHERE id=:id AND user_id=:user_id", {"id": mood_id, "user_id": user_id})


def list_daily_logs(user_id):
    return _list("daily_logs", user_id, "log_date")


def create_daily_log(values):
    ex(
        "INSERT INTO daily_logs (id, user_id, log_date, weight_kg, temperature_c, discharge, intercourse, "
        "medication, cramps, notes) VALUES (:id,:user_id,:log_date,:weight_kg,:temperature_c,:discharge,"
        ":intercourse,:medication,:cramps,:notes)",
        values,
    )


def update_daily_log(daily_id, user_id, values):
    return ex(
        "UPDATE daily_logs SET log_date=:log_date, weight_kg=:weight_kg, temperature_c=:temperature_c, "
        "discharge=:discharge, intercourse=:intercourse, medication=:medication, cramps=:cramps, notes=:notes "
        "WHERE id=:id AND user_id=:user_id",
        {**values, "id": daily_id, "user_id": user_id},
    ) > 0


def delete_daily_log(daily_id, user_id):
    ex("DELETE FROM daily_logs WHERE id=:id AND user_id=:user_id", {"id": daily_id, "user_id": user_id})


def overview_stats(user_id, today):
    symptoms = q(
        "SELECT symptom, COUNT(*) c, AVG(severity) sev FROM symptoms "
        "WHERE user_id=:user_id GROUP BY symptom ORDER BY c DESC",
        {"user_id": user_id},
    )
    moods = q(
        "SELECT mood, COUNT(*) c FROM moods WHERE user_id=:user_id GROUP BY mood ORDER BY c DESC",
        {"user_id": user_id},
    )
    counts = {}
    for key, table in (("symptoms", "symptoms"), ("moods", "moods"), ("daily", "daily_logs")):
        row = q(
            f"SELECT COUNT(*) c FROM {table} WHERE user_id=:user_id AND log_date=:today",
            {"user_id": user_id, "today": today.isoformat()},
            one=True,
        )
        counts[key] = row["c"]
    return symptoms, moods, counts


def report_rows(user_id):
    """Return the assignment report queries using SQLite SQL."""

    queries = {
        "period_settings": """SELECT u.id AS user_id, u.name, p.id AS period_id, p.start_date,
                  p.end_date, s.avg_cycle_length, s.avg_period_length
           FROM users u JOIN settings s ON s.user_id = u.id
           LEFT JOIN periods p ON p.user_id = u.id
           WHERE u.id=:user_id ORDER BY p.start_date DESC""",
        "period_symptoms": """SELECT u.id AS user_id, p.id AS period_id, p.start_date,
                  COUNT(sym.id) AS symptom_count, COALESCE(AVG(sym.severity), 0) AS average_severity
           FROM users u JOIN periods p ON p.user_id = u.id
           LEFT JOIN symptoms sym ON sym.user_id = u.id AND sym.log_date = p.start_date
           WHERE u.id=:user_id GROUP BY u.id, p.id, p.start_date ORDER BY p.start_date DESC""",
        "daily_moods": """SELECT u.id AS user_id, d.log_date, d.weight_kg, d.temperature_c,
                  m.mood, m.energy FROM users u JOIN daily_logs d ON d.user_id = u.id
           LEFT JOIN moods m ON m.user_id = u.id AND m.log_date = d.log_date
           WHERE u.id=:user_id ORDER BY d.log_date DESC""",
        "symptoms_by_period": """SELECT sym.symptom, COUNT(sym.id) AS symptom_count,
                  ROUND(AVG(sym.severity), 2) AS average_severity, COUNT(DISTINCT p.id) AS periods_with_symptom
           FROM users u JOIN periods p ON p.user_id = u.id JOIN symptoms sym ON sym.user_id = u.id
            AND sym.log_date >= p.start_date AND (p.end_date IS NULL OR sym.log_date <= p.end_date)
           WHERE u.id=:user_id GROUP BY sym.symptom ORDER BY symptom_count DESC""",
        "mood_measurements": """SELECT m.mood, COUNT(m.id) AS mood_count,
                  ROUND(AVG(m.energy), 2) AS average_energy, ROUND(AVG(d.temperature_c), 2) AS average_temperature,
                  ROUND(AVG(d.weight_kg), 2) AS average_weight FROM users u JOIN moods m ON m.user_id = u.id
           JOIN daily_logs d ON d.user_id = u.id AND d.log_date = m.log_date
           WHERE u.id=:user_id GROUP BY m.mood ORDER BY mood_count DESC""",
    }
    return {name: q(sql, {"user_id": user_id}) for name, sql in queries.items()}
