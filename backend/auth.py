"""Auth helpers: password hashing + JWT tokens."""
import datetime as dt
import uuid

import jwt
from flask import request
from passlib.context import CryptContext

from . import config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(Exception):
    """An authentication failure that the Flask app renders as JSON."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def hash_password(pw: str) -> str:
    return pwd_context.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    return pwd_context.verify(pw, hashed)


def new_id() -> str:
    return uuid.uuid4().hex


def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=config.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def get_current_user_id() -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, credentials = header.partition(" ")
    if scheme.lower() != "bearer" or not credentials:
        raise AuthenticationError("Not authenticated")
    try:
        payload = jwt.decode(credentials, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except Exception:
        raise AuthenticationError("Invalid token")
