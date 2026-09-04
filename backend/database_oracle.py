"""Oracle persistence implemented with Flask-SQLAlchemy and python-oracledb.

This module is loaded only when ``DB_MODE=oracle``.  The SQLite implementation
is in ``database_sqlite.py`` and is not imported in this mode.
"""
import datetime as dt
from contextlib import contextmanager
from decimal import Decimal

import oracledb  # noqa: F401 - used by SQLAlchemy's oracle+oracledb dialect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, and_, desc, func, or_, select, text
from sqlalchemy.engine import URL

from . import config


orm = SQLAlchemy()
_app = None


def _database_uri():
    """Build a SQLAlchemy URL without putting credentials in a plain string."""

    if config.ORACLE_DSN:
        return URL.create(
            "oracle+oracledb",
            username=config.ORACLE_USER,
            password=config.ORACLE_PASSWORD,
            query={"dsn": config.ORACLE_DSN},
        )

    return URL.create(
        "oracle+oracledb",
        username=config.ORACLE_USER,
        password=config.ORACLE_PASSWORD,
        host=config.ORACLE_HOST,
        port=int(config.ORACLE_PORT),
        query={"service_name": config.ORACLE_SERVICE},
    )


def configure_app(app):
    """Attach the Oracle SQLAlchemy extension to the Flask application."""

    global _app
    _app = app
    app.config.update(
        SQLALCHEMY_DATABASE_URI=_database_uri(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
    )
    if config.ORACLE_WALLET_DIR:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"] = {
            "config_dir": config.ORACLE_WALLET_DIR,
            "wallet_location": config.ORACLE_WALLET_DIR,
            "wallet_password": config.ORACLE_WALLET_PASSWORD,
        }
    if "sqlalchemy" not in app.extensions:
        orm.init_app(app)


class User(orm.Model):
    __tablename__ = "users"

    id = orm.Column(orm.String(32), primary_key=True)
    email = orm.Column(orm.String(255), nullable=False, unique=True)
    password_hash = orm.Column(orm.String(512), nullable=False)
    name = orm.Column(orm.String(120))
    created_at = orm.Column(orm.DateTime, server_default=func.current_timestamp())


class Period(orm.Model):
    __tablename__ = "periods"
    __table_args__ = (Index("ix_periods_user_start", "user_id", "start_date"),)

    id = orm.Column(orm.String(32), primary_key=True)
    user_id = orm.Column(orm.String(32), orm.ForeignKey("users.id"), nullable=False)
    start_date = orm.Column(orm.Date, nullable=False)
    end_date = orm.Column(orm.Date)
    flow_level = orm.Column(orm.Numeric(2))
    notes = orm.Column(orm.String(2000))
    created_at = orm.Column(orm.DateTime, server_default=func.current_timestamp())


class Symptom(orm.Model):
    __tablename__ = "symptoms"
    __table_args__ = (Index("ix_symptoms_user_date", "user_id", "log_date"),)

    id = orm.Column(orm.String(32), primary_key=True)
    user_id = orm.Column(orm.String(32), orm.ForeignKey("users.id"), nullable=False)
    log_date = orm.Column(orm.Date, nullable=False)
    symptom = orm.Column(orm.String(80), nullable=False)
    severity = orm.Column(orm.Numeric(2))
    notes = orm.Column(orm.String(1000))
    created_at = orm.Column(orm.DateTime, server_default=func.current_timestamp())


class Mood(orm.Model):
    __tablename__ = "moods"
    __table_args__ = (Index("ix_moods_user_date", "user_id", "log_date"),)

    id = orm.Column(orm.String(32), primary_key=True)
    user_id = orm.Column(orm.String(32), orm.ForeignKey("users.id"), nullable=False)
    log_date = orm.Column(orm.Date, nullable=False)
    mood = orm.Column(orm.String(60), nullable=False)
    energy = orm.Column(orm.Numeric(2))
    created_at = orm.Column(orm.DateTime, server_default=func.current_timestamp())


class DailyLog(orm.Model):
    __tablename__ = "daily_logs"
    __table_args__ = (Index("ix_daily_logs_user_date", "user_id", "log_date"),)

    id = orm.Column(orm.String(32), primary_key=True)
    user_id = orm.Column(orm.String(32), orm.ForeignKey("users.id"), nullable=False)
    log_date = orm.Column(orm.Date, nullable=False)
    weight_kg = orm.Column(orm.Numeric(5, 1))
    temperature_c = orm.Column(orm.Numeric(4, 1))
    discharge = orm.Column(orm.String(40))
    intercourse = orm.Column(orm.Numeric(1))
    medication = orm.Column(orm.String(500))
    cramps = orm.Column(orm.Numeric(2))
    notes = orm.Column(orm.String(2000))
    created_at = orm.Column(orm.DateTime, server_default=func.current_timestamp())


class Settings(orm.Model):
    __tablename__ = "settings"

    user_id = orm.Column(orm.String(32), orm.ForeignKey("users.id"), primary_key=True)
    avg_cycle_length = orm.Column(orm.Numeric(3), default=28, server_default=text("28"))
    avg_period_length = orm.Column(orm.Numeric(3), default=5, server_default=text("5"))
    luteal_phase_length = orm.Column(orm.Numeric(3), default=14, server_default=text("14"))
    birth_control = orm.Column(orm.String(40))
    notifications_enabled = orm.Column(orm.Numeric(1), default=1, server_default=text("1"))


ALL_LOG_MODELS = (Period, Symptom, Mood, DailyLog)


def init_db():
    """Create missing Oracle tables and indexes from the ORM metadata."""

    if _app is None:
        raise RuntimeError("Oracle database must be configured before init_db()")
    with _app.app_context():
        orm.create_all()


@contextmanager
def transaction():
    """Commit an ORM write, rolling it back if the operation fails."""

    try:
        yield orm.session
        orm.session.commit()
    except Exception:
        orm.session.rollback()
        raise


def _date(value):
    if value is None or isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def _normalise(value, column_name=None):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if column_name in {"intercourse", "notifications_enabled"} and value is not None:
        return bool(value)
    if isinstance(value, Decimal):
        number = float(value)
        return int(number) if number.is_integer() else number
    return value


def _row(model):
    return {
        column.name.lower(): _normalise(getattr(model, column.name), column.name.lower())
        for column in model.__table__.columns
    }


def _rows(models):
    return [_row(model) for model in models]


def _mapping_rows(result):
    return [
        {key.lower(): _normalise(value, key.lower()) for key, value in row._mapping.items()}
        for row in result
    ]


def _owned(model, record_id, user_id):
    record = orm.session.get(model, record_id)
    return record if record and record.user_id == user_id else None


def get_user_by_email(email):
    user = orm.session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    return _row(user) if user else None


def get_user(user_id):
    user = orm.session.get(User, user_id)
    return _row(user) if user else None


def email_exists(email, except_user_id=None):
    statement = select(User.id).where(func.lower(User.email) == email.lower())
    if except_user_id:
        statement = statement.where(User.id != except_user_id)
    return orm.session.scalar(statement) is not None


def create_user(user_id, email, password_hash, name):
    with transaction() as session:
        session.add(User(id=user_id, email=email, password_hash=password_hash, name=name or ""))
        session.add(Settings(user_id=user_id))


def get_settings(user_id):
    settings = orm.session.get(Settings, user_id)
    return _row(settings) if settings else None


def update_user(user_id, email, name):
    with transaction() as session:
        user = session.get(User, user_id)
        if user:
            user.email = email
            user.name = name or ""
    return get_user(user_id)


def delete_user(user_id):
    with transaction() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        for model in ALL_LOG_MODELS:
            for record in session.scalars(select(model).where(model.user_id == user_id)).all():
                session.delete(record)
        settings = session.get(Settings, user_id)
        if settings:
            session.delete(settings)
        session.delete(user)
    return True


def save_settings(user_id, values):
    with transaction() as session:
        settings = session.get(Settings, user_id)
        if settings is None:
            settings = Settings(user_id=user_id)
            session.add(settings)
        for field in ("avg_cycle_length", "avg_period_length", "luteal_phase_length", "birth_control"):
            value = values.get(field)
            if value is not None:
                setattr(settings, field, value)
        settings.notifications_enabled = 1 if values.get("notifications_enabled", True) else 0
    return get_settings(user_id)


def delete_settings(user_id):
    with transaction() as session:
        settings = session.get(Settings, user_id)
        if settings:
            session.delete(settings)


def list_periods(user_id):
    models = orm.session.scalars(
        select(Period).where(Period.user_id == user_id).order_by(Period.start_date.desc())
    ).all()
    return _rows(models)


def create_period(values):
    with transaction() as session:
        session.add(
            Period(
                id=values["id"], user_id=values["user_id"], start_date=_date(values["start_date"]),
                end_date=_date(values.get("end_date")), flow_level=values.get("flow_level"),
                notes=values.get("notes", ""),
            )
        )


def update_period(period_id, user_id, values):
    with transaction() as session:
        period = _owned(Period, period_id, user_id)
        if not period:
            return False
        period.start_date = _date(values["start_date"])
        period.end_date = _date(values.get("end_date"))
        period.flow_level = values.get("flow_level")
        period.notes = values.get("notes", "")
    return True


def delete_period(period_id, user_id):
    with transaction() as session:
        period = _owned(Period, period_id, user_id)
        if not period:
            return False
        session.delete(period)
    return True


def list_symptoms(user_id):
    models = orm.session.scalars(
        select(Symptom).where(Symptom.user_id == user_id).order_by(Symptom.log_date.desc())
    ).all()
    return _rows(models)


def create_symptom(values):
    with transaction() as session:
        session.add(
            Symptom(
                id=values["id"], user_id=values["user_id"], log_date=_date(values["log_date"]),
                symptom=values["symptom"], severity=values["severity"], notes=values.get("notes", ""),
            )
        )


def update_symptom(symptom_id, user_id, values):
    with transaction() as session:
        symptom = _owned(Symptom, symptom_id, user_id)
        if not symptom:
            return False
        symptom.log_date = _date(values["log_date"])
        symptom.symptom = values["symptom"]
        symptom.severity = values["severity"]
        symptom.notes = values.get("notes", "")
    return True


def delete_symptom(symptom_id, user_id):
    with transaction() as session:
        symptom = _owned(Symptom, symptom_id, user_id)
        if symptom:
            session.delete(symptom)


def list_moods(user_id):
    models = orm.session.scalars(
        select(Mood).where(Mood.user_id == user_id).order_by(Mood.log_date.desc())
    ).all()
    return _rows(models)


def create_mood(values):
    with transaction() as session:
        session.add(
            Mood(
                id=values["id"], user_id=values["user_id"], log_date=_date(values["log_date"]),
                mood=values["mood"], energy=values["energy"],
            )
        )


def update_mood(mood_id, user_id, values):
    with transaction() as session:
        mood = _owned(Mood, mood_id, user_id)
        if not mood:
            return False
        mood.log_date = _date(values["log_date"])
        mood.mood = values["mood"]
        mood.energy = values["energy"]
    return True


def delete_mood(mood_id, user_id):
    with transaction() as session:
        mood = _owned(Mood, mood_id, user_id)
        if mood:
            session.delete(mood)


def list_daily_logs(user_id):
    models = orm.session.scalars(
        select(DailyLog).where(DailyLog.user_id == user_id).order_by(DailyLog.log_date.desc())
    ).all()
    return _rows(models)


def create_daily_log(values):
    with transaction() as session:
        session.add(
            DailyLog(
                id=values["id"], user_id=values["user_id"], log_date=_date(values["log_date"]),
                weight_kg=values.get("weight_kg"), temperature_c=values.get("temperature_c"),
                discharge=values.get("discharge"), intercourse=1 if values.get("intercourse") else 0,
                medication=values.get("medication", ""), cramps=values.get("cramps"),
                notes=values.get("notes", ""),
            )
        )


def update_daily_log(daily_id, user_id, values):
    with transaction() as session:
        daily = _owned(DailyLog, daily_id, user_id)
        if not daily:
            return False
        daily.log_date = _date(values["log_date"])
        daily.weight_kg = values.get("weight_kg")
        daily.temperature_c = values.get("temperature_c")
        daily.discharge = values.get("discharge")
        daily.intercourse = 1 if values.get("intercourse") else 0
        daily.medication = values.get("medication", "")
        daily.cramps = values.get("cramps")
        daily.notes = values.get("notes", "")
    return True


def delete_daily_log(daily_id, user_id):
    with transaction() as session:
        daily = _owned(DailyLog, daily_id, user_id)
        if daily:
            session.delete(daily)


def overview_stats(user_id, today):
    symptom_count = func.count(Symptom.id).label("c")
    symptom_average = func.avg(Symptom.severity).label("sev")
    symptom_rows = _mapping_rows(
        orm.session.execute(
            select(Symptom.symptom, symptom_count, symptom_average)
            .where(Symptom.user_id == user_id)
            .group_by(Symptom.symptom)
            .order_by(desc(symptom_count))
        )
    )
    mood_count = func.count(Mood.id).label("c")
    mood_rows = _mapping_rows(
        orm.session.execute(
            select(Mood.mood, mood_count)
            .where(Mood.user_id == user_id)
            .group_by(Mood.mood)
            .order_by(desc(mood_count))
        )
    )
    counts = {
        "symptoms": orm.session.scalar(
            select(func.count(Symptom.id)).where(Symptom.user_id == user_id, Symptom.log_date == today)
        ),
        "moods": orm.session.scalar(
            select(func.count(Mood.id)).where(Mood.user_id == user_id, Mood.log_date == today)
        ),
        "daily": orm.session.scalar(
            select(func.count(DailyLog.id)).where(DailyLog.user_id == user_id, DailyLog.log_date == today)
        ),
    }
    return symptom_rows, mood_rows, counts


def report_rows(user_id):
    """Return the three related and two complex assignment queries via ORM."""

    period_settings = orm.session.execute(
        select(
            User.id.label("user_id"), User.name, Period.id.label("period_id"), Period.start_date,
            Period.end_date, Settings.avg_cycle_length, Settings.avg_period_length,
        )
        .join(Settings, Settings.user_id == User.id)
        .outerjoin(Period, Period.user_id == User.id)
        .where(User.id == user_id)
        .order_by(Period.start_date.desc())
    )

    symptom_count = func.count(Symptom.id).label("symptom_count")
    average_severity = func.coalesce(func.avg(Symptom.severity), 0).label("average_severity")
    period_symptoms = orm.session.execute(
        select(
            User.id.label("user_id"), Period.id.label("period_id"), Period.start_date,
            symptom_count, average_severity,
        )
        .join(Period, Period.user_id == User.id)
        .outerjoin(
            Symptom,
            and_(Symptom.user_id == User.id, Symptom.log_date == Period.start_date),
        )
        .where(User.id == user_id)
        .group_by(User.id, Period.id, Period.start_date)
        .order_by(Period.start_date.desc())
    )

    daily_moods = orm.session.execute(
        select(
            User.id.label("user_id"), DailyLog.log_date, DailyLog.weight_kg,
            DailyLog.temperature_c, Mood.mood, Mood.energy,
        )
        .join(DailyLog, DailyLog.user_id == User.id)
        .outerjoin(
            Mood,
            and_(Mood.user_id == User.id, Mood.log_date == DailyLog.log_date),
        )
        .where(User.id == user_id)
        .order_by(DailyLog.log_date.desc())
    )

    symptoms_by_period_count = func.count(Symptom.id).label("symptom_count")
    symptoms_by_period_average = func.round(func.avg(Symptom.severity), 2).label("average_severity")
    periods_with_symptom = func.count(func.distinct(Period.id)).label("periods_with_symptom")
    symptoms_by_period = orm.session.execute(
        select(
            Symptom.symptom, symptoms_by_period_count, symptoms_by_period_average, periods_with_symptom,
        )
        .join(User, User.id == Symptom.user_id)
        .join(Period, Period.user_id == User.id)
        .where(
            User.id == user_id,
            Symptom.log_date >= Period.start_date,
            or_(Period.end_date.is_(None), Symptom.log_date <= Period.end_date),
        )
        .group_by(Symptom.symptom)
        .order_by(desc(symptoms_by_period_count))
    )

    mood_count = func.count(Mood.id).label("mood_count")
    mood_measurements = orm.session.execute(
        select(
            Mood.mood, mood_count,
            func.round(func.avg(Mood.energy), 2).label("average_energy"),
            func.round(func.avg(DailyLog.temperature_c), 2).label("average_temperature"),
            func.round(func.avg(DailyLog.weight_kg), 2).label("average_weight"),
        )
        .join(User, User.id == Mood.user_id)
        .join(
            DailyLog,
            and_(DailyLog.user_id == User.id, DailyLog.log_date == Mood.log_date),
        )
        .where(User.id == user_id)
        .group_by(Mood.mood)
        .order_by(desc(mood_count))
    )

    return {
        "period_settings": _mapping_rows(period_settings),
        "period_symptoms": _mapping_rows(period_symptoms),
        "daily_moods": _mapping_rows(daily_moods),
        "symptoms_by_period": _mapping_rows(symptoms_by_period),
        "mood_measurements": _mapping_rows(mood_measurements),
    }
