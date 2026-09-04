"""Main Flask application: auth + periods + symptoms + moods + daily logs + stats."""
import datetime as dt
import os
from typing import Optional

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
    existing = db.q(None, "SELECT id FROM users WHERE lower(email)=lower(:e)", {"e": body.email}, one=True)
    if existing:
        raise APIError(400, "An account with this email already exists")
    uid = new_id()
    db.ex(
        "INSERT INTO users (id, email, password_hash, name, created_at) VALUES (:i,:e,:p,:n,SYSTIMESTAMP)"
        if config.DB_MODE == "oracle" else
        "INSERT INTO users (id, email, password_hash, name, created_at) VALUES (:i,:e,:p,:n,datetime('now'))",
        {"i": uid, "e": body.email, "p": hash_password(body.password), "n": body.name or ""},
    )
    # default settings row
    db.ex(
        "INSERT INTO settings (user_id, avg_cycle_length, avg_period_length, luteal_phase_length, birth_control, notifications_enabled) VALUES (:u,28,5,14,NULL,1)",
        {"u": uid},
    )
    return {"token": create_token(uid), "user_id": uid, "name": body.name}


@app.post(f"{config.API_PREFIX}/auth/login")
def login():
    body = parse_body(LoginIn)
    user = db.q(None, "SELECT * FROM users WHERE lower(email)=lower(:e)", {"e": body.email}, one=True)
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
    u = db.q(None, "SELECT id, email, name, created_at FROM users WHERE id=:i", {"i": user_id}, one=True)
    if config.DB_MODE == "oracle":
        pass
    if not u:
        raise APIError(404, "User not found")
    s = db.q(None, "SELECT * FROM settings WHERE user_id=:u", {"u": user_id}, one=True) or {}
    return {"user": u, "settings": s}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@app.put(f"{config.API_PREFIX}/settings")
def update_settings():
    user_id = get_current_user_id()
    body = parse_body(SettingsIn)
    row = db.q(None, "SELECT user_id FROM settings WHERE user_id=:u", {"u": user_id}, one=True)
    if not row:
        db.ex(
            "INSERT INTO settings (user_id, avg_cycle_length, avg_period_length, luteal_phase_length, birth_control, notifications_enabled) VALUES (:u,:c,:p,:l,:b,:n)",
            {"u": user_id, "c": body.avg_cycle_length or 28, "p": body.avg_period_length or 5,
             "l": body.luteal_phase_length or 14, "b": body.birth_control,
             "n": 1 if body.notifications_enabled else 0},
        )
    else:
        sets, params = [], {"u": user_id}
        for k in ("avg_cycle_length", "avg_period_length", "luteal_phase_length", "birth_control"):
            v = getattr(body, k)
            if v is not None:
                sets.append(f"{k}=:{k}")
                params[k] = v
        sets.append("notifications_enabled=:n")
        params["n"] = 1 if body.notifications_enabled else 0
        db.ex(f"UPDATE settings SET {', '.join(sets)} WHERE user_id=:u", params)
    return db.q(None, "SELECT * FROM settings WHERE user_id=:u", {"u": user_id}, one=True)


# ---------------------------------------------------------------------------
# Periods CRUD
# ---------------------------------------------------------------------------

@app.get(f"{config.API_PREFIX}/periods")
def list_periods():
    user_id = get_current_user_id()
    rows = db.q(None, "SELECT * FROM periods WHERE user_id=:u ORDER BY start_date DESC", {"u": user_id})
    for r in rows:
        r["start_date"] = iso(r["start_date"])
        if r.get("end_date"):
            r["end_date"] = iso(r["end_date"])
    return rows


@app.post(f"{config.API_PREFIX}/periods")
def add_period():
    user_id = get_current_user_id()
    body = parse_body(PeriodIn)
    pid = new_id()
    db.ex(
        "INSERT INTO periods (id, user_id, start_date, end_date, flow_level, notes) VALUES (:i,:u,:s,:e,:f,:n)",
        {"i": pid, "u": user_id, "s": body.start_date,
         "e": body.end_date or None, "f": body.flow_level, "n": body.notes},
    )
    return {"id": pid}


@app.put(f"{config.API_PREFIX}/periods/<pid>")
def update_period(pid: str):
    user_id = get_current_user_id()
    body = parse_body(PeriodIn)
    n = db.ex(
        "UPDATE periods SET start_date=:s, end_date=:e, flow_level=:f, notes=:n2 WHERE id=:i AND user_id=:u",
        {"s": body.start_date, "e": body.end_date or None, "f": body.flow_level,
         "n2": body.notes, "i": pid, "u": user_id},
    )
    if n == 0:
        raise APIError(404, "Period entry not found")
    return {"ok": True}


@app.delete(f"{config.API_PREFIX}/periods/<pid>")
def delete_period(pid: str):
    user_id = get_current_user_id()
    n = db.ex("DELETE FROM periods WHERE id=:i AND user_id=:u", {"i": pid, "u": user_id})
    if n == 0:
        raise APIError(404, "Not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Symptoms
# ---------------------------------------------------------------------------

@app.get(f"{config.API_PREFIX}/symptoms")
def list_symptoms():
    user_id = get_current_user_id()
    rows = db.q(None, "SELECT * FROM symptoms WHERE user_id=:u ORDER BY log_date DESC", {"u": user_id})
    for r in rows:
        r["log_date"] = iso(r["log_date"])
    return rows


@app.post(f"{config.API_PREFIX}/symptoms")
def add_symptom():
    user_id = get_current_user_id()
    body = parse_body(SymptomIn)
    sid = new_id()
    db.ex(
        "INSERT INTO symptoms (id, user_id, log_date, symptom, severity, notes) VALUES (:i,:u,:d,:s,:v,:n)",
        {"i": sid, "u": user_id, "d": body.log_date, "s": body.symptom,
         "v": body.severity, "n": body.notes},
    )
    return {"id": sid}


@app.delete(f"{config.API_PREFIX}/symptoms/<sid>")
def delete_symptom(sid: str):
    user_id = get_current_user_id()
    db.ex("DELETE FROM symptoms WHERE id=:i AND user_id=:u", {"i": sid, "u": user_id})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Moods
# ---------------------------------------------------------------------------

@app.get(f"{config.API_PREFIX}/moods")
def list_moods():
    user_id = get_current_user_id()
    rows = db.q(None, "SELECT * FROM moods WHERE user_id=:u ORDER BY log_date DESC", {"u": user_id})
    for r in rows:
        r["log_date"] = iso(r["log_date"])
    return rows


@app.post(f"{config.API_PREFIX}/moods")
def add_mood():
    user_id = get_current_user_id()
    body = parse_body(MoodIn)
    mid = new_id()
    db.ex(
        "INSERT INTO moods (id, user_id, log_date, mood, energy) VALUES (:i,:u,:d,:m,:e)",
        {"i": mid, "u": user_id, "d": body.log_date, "m": body.mood, "e": body.energy},
    )
    return {"id": mid}


@app.delete(f"{config.API_PREFIX}/moods/<mid>")
def delete_mood(mid: str):
    user_id = get_current_user_id()
    db.ex("DELETE FROM moods WHERE id=:i AND user_id=:u", {"i": mid, "u": user_id})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Daily logs
# ---------------------------------------------------------------------------

@app.get(f"{config.API_PREFIX}/daily")
def list_daily():
    user_id = get_current_user_id()
    rows = db.q(None, "SELECT * FROM daily_logs WHERE user_id=:u ORDER BY log_date DESC", {"u": user_id})
    for r in rows:
        r["log_date"] = iso(r["log_date"])
    return rows


@app.post(f"{config.API_PREFIX}/daily")
def add_daily():
    user_id = get_current_user_id()
    body = parse_body(DailyLogIn)
    did = new_id()
    db.ex(
        """INSERT INTO daily_logs (id, user_id, log_date, weight_kg, temperature_c, discharge, intercourse, medication, cramps, notes)
           VALUES (:i,:u,:d,:w,:t,:dc,:ix,:md,:cr,:n)""",
        {"i": did, "u": user_id, "d": body.log_date, "w": body.weight_kg, "t": body.temperature_c,
         "dc": body.discharge, "ix": 1 if body.intercourse else 0, "md": body.medication,
         "cr": body.cramps, "n": body.notes},
    )
    return {"id": did}


@app.delete(f"{config.API_PREFIX}/daily/<did>")
def delete_daily(did: str):
    user_id = get_current_user_id()
    db.ex("DELETE FROM daily_logs WHERE id=:i AND user_id=:u", {"i": did, "u": user_id})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Insights / overview / calendar classification
# ---------------------------------------------------------------------------

def _load_all(user_id):
    periods = db.q(None, "SELECT * FROM periods WHERE user_id=:u ORDER BY start_date", {"u": user_id})
    for p in periods:
        p["start_date"] = iso(p["start_date"])
        if p.get("end_date"):
            p["end_date"] = iso(p["end_date"])
    settings = db.q(None, "SELECT * FROM settings WHERE user_id=:u", {"u": user_id}, one=True)
    return periods, settings


@app.get(f"{config.API_PREFIX}/overview")
def overview():
    user_id = get_current_user_id()
    periods, settings = _load_all(user_id)
    ov = cycle.build_overview(periods, settings)

    # extra aggregates
    today = dt.date.today()
    sym = db.q(None, "SELECT symptom, COUNT(*) c, AVG(severity) sev FROM symptoms WHERE user_id=:u GROUP BY symptom ORDER BY c DESC", {"u": user_id})
    moods = db.q(None, "SELECT mood, COUNT(*) c FROM moods WHERE user_id=:u GROUP BY mood ORDER BY c DESC", {"u": user_id})

    def _f(x):
        try:
            return round(float(x), 2)
        except Exception:
            return x

    ov["top_symptoms"] = [{"symptom": s["symptom"], "count": s["c"], "avg_severity": _f(s["sev"])} for s in sym[:8]]
    ov["mood_distribution"] = {m["mood"]: m["c"] for m in moods}
    ov["logged_today"] = {
        "symptoms": db.q(None, "SELECT COUNT(*) c FROM symptoms WHERE user_id=:u AND log_date=:d", {"u": user_id, "d": today.isoformat()}, one=True)["c"],
        "moods": db.q(None, "SELECT COUNT(*) c FROM moods WHERE user_id=:u AND log_date=:d", {"u": user_id, "d": today.isoformat()}, one=True)["c"],
        "daily": db.q(None, "SELECT COUNT(*) c FROM daily_logs WHERE user_id=:u AND log_date=:d", {"u": user_id, "d": today.isoformat()}, one=True)["c"],
    }
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
    sym = db.q(None, "SELECT * FROM symptoms WHERE user_id=:u ORDER BY log_date DESC", {"u": user_id})
    moods = db.q(None, "SELECT * FROM moods WHERE user_id=:u ORDER BY log_date DESC", {"u": user_id})
    daily = db.q(None, "SELECT * FROM daily_logs WHERE user_id=:u ORDER BY log_date DESC", {"u": user_id})
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
