"""Main Flask application: auth + periods + symptoms + moods + daily logs + stats."""
import datetime as dt
import os
from typing import Any, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask.json.provider import DefaultJSONProvider
from pydantic import BaseModel, EmailStr, Field, ValidationError

from . import config, database as db, cycle
from .auth import (
    AuthenticationError,
    create_token,
    get_current_user_id,
    hash_password,
    new_id,
    verify_password,
)

class FlowJSONProvider(DefaultJSONProvider):
    """Keep API date responses in the existing ISO-8601 format."""

    @staticmethod
    def default(value):
        if isinstance(value, (dt.date, dt.datetime)):
            return value.isoformat()
        return DefaultJSONProvider.default(value)


class FlowFlask(Flask):
    json_provider_class = FlowJSONProvider


FRONTEND_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")

app = FlowFlask(
    __name__,
    static_folder=os.path.join(DIST_DIR, "assets"),
    static_url_path="/assets",
)
CORS(app)


class APIError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@app.errorhandler(APIError)
def handle_api_error(exc):
    return jsonify(detail=exc.detail), exc.status_code


@app.errorhandler(AuthenticationError)
def handle_auth_error(exc):
    return jsonify(detail=exc.detail), 401


@app.errorhandler(ValidationError)
def handle_validation_error(exc):
    return jsonify(detail=exc.errors()), 422


def parse_body(schema):
    data = request.get_json(silent=True)
    if data is None:
        raise APIError(422, "Request body must be valid JSON")
    validate = getattr(schema, "model_validate", None)
    return validate(data) if validate else schema.parse_obj(data)


# Flask has no ASGI startup event; initialize once when the application loads.
# The selected backend performs its own setup. SQLite is a no-op here, while
# Oracle attaches Flask-SQLAlchemy before creating its ORM metadata.
db.configure_app(app)
db.init_db()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = ""

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class PeriodIn(BaseModel):
    start_date: str
    end_date: Optional[str] = None
    flow_level: Optional[int] = Field(default=None, ge=0, le=3)
    notes: str = ""

class SymptomIn(BaseModel):
    log_date: str
    symptom: str
    severity: int = Field(default=1, ge=1, le=5)
    notes: str = ""

class MoodIn(BaseModel):
    log_date: str
    mood: str
    energy: int = Field(default=3, ge=1, le=5)

class DailyLogIn(BaseModel):
    log_date: str
    weight_kg: Optional[float] = Field(default=None, ge=25, le=300)
    temperature_c: Optional[float] = None
    discharge: Optional[str] = None
    intercourse: bool = False
    medication: str = ""
    cramps: Optional[int] = Field(default=None, ge=0, le=3)
    notes: str = ""

class SettingsIn(BaseModel):
    avg_cycle_length: Optional[int] = Field(default=None, ge=15, le=60)
    avg_period_length: Optional[int] = Field(default=None, ge=1, le=14)
    luteal_phase_length: Optional[int] = Field(default=None, ge=7, le=21)
    birth_control: Optional[str] = None
    notifications_enabled: bool = True


class ProfileIn(BaseModel):
    """Fields a signed-in user may update on their own profile."""

    email: Optional[EmailStr] = None
    name: Optional[str] = None


# Response DTOs keep the API contract explicit without changing the existing
# field names returned to the React client.
class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    created_at: Any = None


class SettingsOut(BaseModel):
    user_id: str
    avg_cycle_length: int = 28
    avg_period_length: int = 5
    luteal_phase_length: int = 14
    birth_control: Optional[str] = None
    notifications_enabled: bool = True


class PeriodOut(BaseModel):
    id: str
    user_id: str
    start_date: str
    end_date: Optional[str] = None
    flow_level: Optional[int] = None
    notes: str = ""
    created_at: Any = None


class SymptomOut(BaseModel):
    id: str
    user_id: str
    log_date: str
    symptom: str
    severity: int
    notes: str = ""
    created_at: Any = None


class MoodOut(BaseModel):
    id: str
    user_id: str
    log_date: str
    mood: str
    energy: int
    created_at: Any = None


class DailyLogOut(BaseModel):
    id: str
    user_id: str
    log_date: str
    weight_kg: Optional[float] = None
    temperature_c: Optional[float] = None
    discharge: Optional[str] = None
    intercourse: bool = False
    medication: str = ""
    cramps: Optional[int] = None
    notes: str = ""
    created_at: Any = None


def as_dto(schema, row):
    """Validate and return one database row using an explicit response DTO."""

    return schema.model_validate(row).model_dump()


def as_dtos(schema, rows):
    return [as_dto(schema, row) for row in rows]


def serialize_report_dates(rows, *fields):
    """Normalize Oracle DATE values and SQLite text dates in report rows."""

    for row in rows:
        for field in fields:
            if row.get(field):
                row[field] = iso(row[field])
    return rows


def iso(d) -> str:
    return cycle.parse_date(d).isoformat()


# ---------------------------------------------------------------------------
# Static frontend — serves the built React app (frontend/dist)
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(DIST_DIR, "index.html")


@app.errorhandler(404)
def not_found(exc):
    # SPA fallback: unknown non-API GET paths get the app shell
    if request.method == "GET" and not request.path.startswith(config.API_PREFIX):
        return send_from_directory(DIST_DIR, "index.html")
    return jsonify(detail="Not Found"), 404


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post(f"{config.API_PREFIX}/auth/signup")
def signup():
    body = parse_body(SignupIn)
    if db.email_exists(str(body.email)):
        raise APIError(400, "An account with this email already exists")
    uid = new_id()
    db.create_user(uid, str(body.email), hash_password(body.password), body.name)
    return {"token": create_token(uid), "user_id": uid, "name": body.name}


@app.post(f"{config.API_PREFIX}/auth/login")
def login():
    body = parse_body(LoginIn)
    user = db.get_user_by_email(str(body.email))
    if not user or not verify_password(body.password, user["password_hash"]):
        raise APIError(401, "Incorrect email or password")
    return {
        "token": create_token(user["id"]),
        "user_id": user["id"],
        "name": user.get("name") or "",
    }


@app.get(f"{config.API_PREFIX}/me")
def me():
    user_id = get_current_user_id()
    u = db.get_user(user_id)
    if not u:
        raise APIError(404, "User not found")
    s = db.get_settings(user_id) or {}
    return {
        "user": as_dto(UserOut, u),
        "settings": as_dto(SettingsOut, s) if s else {},
    }


@app.put(f"{config.API_PREFIX}/me")
def update_me():
    """Update the current user's profile without exposing other accounts."""

    user_id = get_current_user_id()
    body = parse_body(ProfileIn)
    current = db.get_user(user_id)
    if not current:
        raise APIError(404, "User not found")

    email = str(body.email) if body.email is not None else current["email"]
    name = body.name if body.name is not None else current.get("name")
    if db.email_exists(email, except_user_id=user_id):
        raise APIError(400, "An account with this email already exists")

    return as_dto(UserOut, db.update_user(user_id, email, name))


@app.delete(f"{config.API_PREFIX}/me")
def delete_me():
    """Delete the current account and its dependent records."""

    user_id = get_current_user_id()
    if not db.delete_user(user_id):
        raise APIError(404, "User not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@app.put(f"{config.API_PREFIX}/settings")
def update_settings():
    user_id = get_current_user_id()
    body = parse_body(SettingsIn)
    values = body.model_dump()
    return as_dto(SettingsOut, db.save_settings(user_id, values))


@app.get(f"{config.API_PREFIX}/settings")
def get_settings():
    user_id = get_current_user_id()
    row = db.get_settings(user_id)
    if not row:
        raise APIError(404, "Settings not found")
    return as_dto(SettingsOut, row)


@app.delete(f"{config.API_PREFIX}/settings")
def delete_settings():
    user_id = get_current_user_id()
    db.delete_settings(user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Periods CRUD
# ---------------------------------------------------------------------------

@app.get(f"{config.API_PREFIX}/periods")
def list_periods():
    user_id = get_current_user_id()
    rows = db.list_periods(user_id)
    for r in rows:
        r["start_date"] = iso(r["start_date"])
        if r.get("end_date"):
            r["end_date"] = iso(r["end_date"])
    return as_dtos(PeriodOut, rows)


@app.post(f"{config.API_PREFIX}/periods")
def add_period():
    user_id = get_current_user_id()
    body = parse_body(PeriodIn)
    pid = new_id()
    db.create_period({
        "id": pid, "user_id": user_id, "start_date": body.start_date,
        "end_date": body.end_date or None, "flow_level": body.flow_level, "notes": body.notes,
    })
    return {"id": pid}


@app.put(f"{config.API_PREFIX}/periods/<pid>")
def update_period(pid: str):
    user_id = get_current_user_id()
    body = parse_body(PeriodIn)
    if not db.update_period(pid, user_id, {
        "start_date": body.start_date, "end_date": body.end_date or None,
        "flow_level": body.flow_level, "notes": body.notes,
    }):
        raise APIError(404, "Period entry not found")
    return {"ok": True}


@app.delete(f"{config.API_PREFIX}/periods/<pid>")
def delete_period(pid: str):
    user_id = get_current_user_id()
    if not db.delete_period(pid, user_id):
        raise APIError(404, "Not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Symptoms
# ---------------------------------------------------------------------------

@app.get(f"{config.API_PREFIX}/symptoms")
def list_symptoms():
    user_id = get_current_user_id()
    rows = db.list_symptoms(user_id)
    for r in rows:
        r["log_date"] = iso(r["log_date"])
    return as_dtos(SymptomOut, rows)


@app.post(f"{config.API_PREFIX}/symptoms")
def add_symptom():
    user_id = get_current_user_id()
    body = parse_body(SymptomIn)
    sid = new_id()
    db.create_symptom({
        "id": sid, "user_id": user_id, "log_date": body.log_date,
        "symptom": body.symptom, "severity": body.severity, "notes": body.notes,
    })
    return {"id": sid}


@app.put(f"{config.API_PREFIX}/symptoms/<sid>")
def update_symptom(sid: str):
    user_id = get_current_user_id()
    body = parse_body(SymptomIn)
    if not db.update_symptom(sid, user_id, {
        "log_date": body.log_date, "symptom": body.symptom,
        "severity": body.severity, "notes": body.notes,
    }):
        raise APIError(404, "Symptom entry not found")
    return {"ok": True}


@app.delete(f"{config.API_PREFIX}/symptoms/<sid>")
def delete_symptom(sid: str):
    user_id = get_current_user_id()
    db.delete_symptom(sid, user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Moods
# ---------------------------------------------------------------------------

@app.get(f"{config.API_PREFIX}/moods")
def list_moods():
    user_id = get_current_user_id()
    rows = db.list_moods(user_id)
    for r in rows:
        r["log_date"] = iso(r["log_date"])
    return as_dtos(MoodOut, rows)


@app.post(f"{config.API_PREFIX}/moods")
def add_mood():
    user_id = get_current_user_id()
    body = parse_body(MoodIn)
    mid = new_id()
    db.create_mood({
        "id": mid, "user_id": user_id, "log_date": body.log_date,
        "mood": body.mood, "energy": body.energy,
    })
    return {"id": mid}


@app.put(f"{config.API_PREFIX}/moods/<mid>")
def update_mood(mid: str):
    user_id = get_current_user_id()
    body = parse_body(MoodIn)
    if not db.update_mood(mid, user_id, {
        "log_date": body.log_date, "mood": body.mood, "energy": body.energy,
    }):
        raise APIError(404, "Mood entry not found")
    return {"ok": True}


@app.delete(f"{config.API_PREFIX}/moods/<mid>")
def delete_mood(mid: str):
    user_id = get_current_user_id()
    db.delete_mood(mid, user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Daily logs
# ---------------------------------------------------------------------------

@app.get(f"{config.API_PREFIX}/daily")
def list_daily():
    user_id = get_current_user_id()
    rows = db.list_daily_logs(user_id)
    for r in rows:
        r["log_date"] = iso(r["log_date"])
    return as_dtos(DailyLogOut, rows)


@app.post(f"{config.API_PREFIX}/daily")
def add_daily():
    user_id = get_current_user_id()
    body = parse_body(DailyLogIn)
    did = new_id()
    db.create_daily_log({
        "id": did, "user_id": user_id, "log_date": body.log_date,
        "weight_kg": body.weight_kg, "temperature_c": body.temperature_c,
        "discharge": body.discharge, "intercourse": body.intercourse,
        "medication": body.medication, "cramps": body.cramps, "notes": body.notes,
    })
    return {"id": did}


@app.put(f"{config.API_PREFIX}/daily/<did>")
def update_daily(did: str):
    user_id = get_current_user_id()
    body = parse_body(DailyLogIn)
    if not db.update_daily_log(did, user_id, {
        "log_date": body.log_date, "weight_kg": body.weight_kg,
        "temperature_c": body.temperature_c, "discharge": body.discharge,
        "intercourse": body.intercourse, "medication": body.medication,
        "cramps": body.cramps, "notes": body.notes,
    }):
        raise APIError(404, "Daily log entry not found")
    return {"ok": True}


@app.delete(f"{config.API_PREFIX}/daily/<did>")
def delete_daily(did: str):
    user_id = get_current_user_id()
    db.delete_daily_log(did, user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Insights / overview / calendar classification
# ---------------------------------------------------------------------------

def _load_all(user_id):
    periods = db.list_periods(user_id)
    periods.sort(key=lambda period: period["start_date"])
    for p in periods:
        p["start_date"] = iso(p["start_date"])
        if p.get("end_date"):
            p["end_date"] = iso(p["end_date"])
    settings = db.get_settings(user_id)
    return periods, settings


@app.get(f"{config.API_PREFIX}/overview")
def overview():
    user_id = get_current_user_id()
    periods, settings = _load_all(user_id)
    ov = cycle.build_overview(periods, settings)

    # Extra aggregates are provided by the selected backend. The Oracle
    # implementation builds these with SQLAlchemy ORM expressions.
    today = dt.date.today()
    sym, moods, logged_today = db.overview_stats(user_id, today)

    def _f(x):
        try:
            return round(float(x), 2)
        except Exception:
            return x

    ov["top_symptoms"] = [{"symptom": s["symptom"], "count": s["c"], "avg_severity": _f(s["sev"])} for s in sym[:8]]
    ov["mood_distribution"] = {m["mood"]: m["c"] for m in moods}
    ov["logged_today"] = logged_today
    return ov


@app.get(f"{config.API_PREFIX}/calendar/<int:year>/<int:month>")
def calendar(year: int, month: int):
    user_id = get_current_user_id()
    import calendar as cal
    first = dt.date(year, month, 1)
    last_day = cal.monthrange(year, month)[1]
    days = [(first + dt.timedelta(days=i)).isoformat() for i in range(last_day)]
    periods, settings = _load_all(user_id)
    tags = cycle.classify_calendar_days(days, periods, settings)
    return {"year": year, "month": month, "days": tags}


@app.get(f"{config.API_PREFIX}/history")
def history():
    """Everything logged, grouped by date — powers the History tab."""
    user_id = get_current_user_id()
    periods, _ = _load_all(user_id)
    sym = db.list_symptoms(user_id)
    moods = db.list_moods(user_id)
    daily = db.list_daily_logs(user_id)
    for r in sym:
        r["log_date"] = iso(r["log_date"])
    for r in moods:
        r["log_date"] = iso(r["log_date"])
    for r in daily:
        r["log_date"] = iso(r["log_date"])
    grouped = {}
    for p in periods:
        grouped.setdefault(p["start_date"], []).append({"type": "period", **p})
    for s in sym:
        grouped.setdefault(s["log_date"], []).append({"type": "symptom", **s})
    for m in moods:
        grouped.setdefault(m["log_date"], []).append({"type": "mood", **m})
    for d in daily:
        grouped.setdefault(d["log_date"], []).append({"type": "daily", **d})
    return dict(sorted(grouped.items(), reverse=True))


# ---------------------------------------------------------------------------
# Related and complex queries — assignment demonstration endpoints
# ---------------------------------------------------------------------------

@app.get(f"{config.API_PREFIX}/reports")
def reports():
    """Run the assignment's three related and two complex queries."""

    user_id = get_current_user_id()
    rows = db.report_rows(user_id)

    return {
        "related_queries": {
            "period_settings": serialize_report_dates(rows["period_settings"], "start_date", "end_date"),
            "period_symptoms": serialize_report_dates(rows["period_symptoms"], "start_date"),
            "daily_moods": serialize_report_dates(rows["daily_moods"], "log_date"),
        },
        "complex_queries": {
            "symptoms_by_period": rows["symptoms_by_period"],
            "mood_measurements": rows["mood_measurements"],
        },
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
