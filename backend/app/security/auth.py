"""Authentication: argon2id password hashes and a JWT session cookie.

The token lives in an httpOnly cookie, so page JavaScript cannot read it.
Role checks are FastAPI dependencies, applied per route.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import AppError
from app.models import User

ALGORITHM = "HS256"
ROLE_STUDENT = "student"
ROLE_COORDINATOR = "coordinator"

_hasher = PasswordHasher()
# Verified against when the email is unknown, so a wrong email costs the same
# time as a wrong password and the two cases cannot be told apart by timing.
_DUMMY_HASH = _hasher.hash("placemate-dummy-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email.strip().lower()).one_or_none()
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.resolve_secret_key(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.resolve_secret_key(), algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AppError(401, "not_authenticated", "Your session has expired. Please log in again.") from exc


def set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise AppError(401, "not_authenticated", "Please log in to continue.")
    payload = decode_token(token)
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError) as exc:
        raise AppError(401, "not_authenticated", "Please log in to continue.") from exc
    user = db.get(User, user_id)
    if user is None:
        raise AppError(401, "not_authenticated", "Please log in to continue.")
    return user


def require_role(*roles: str):
    """Dependency factory: allow only the given roles."""

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "forbidden", "You do not have permission to do this.")
        return user

    return _dependency


require_student = require_role(ROLE_STUDENT)
require_coordinator = require_role(ROLE_COORDINATOR)
