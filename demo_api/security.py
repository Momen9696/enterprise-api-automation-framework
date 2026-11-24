"""Demo JWT issuance and bearer-token checks.

The signing key is a fixed synthetic value so local and CI runs are deterministic.
It is not a production secret.
"""

from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Header

from demo_api.errors import ApiError
from demo_api.store import User, get_store

DEMO_JWT_SECRET = "demo-only-signing-key-not-for-production"
DEMO_JWT_ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 7200


def authenticate(email: str, password: str) -> User:
    user = get_store().find_user_by_email(email)
    if user is None or not hmac.compare_digest(user.password, password):
        raise ApiError(401, "invalid_credentials", "Email or password is incorrect")
    return user


def issue_token(user: User) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "role": user.role,
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=TOKEN_TTL_SECONDS)).timestamp()),
    }
    token = jwt.encode(payload, DEMO_JWT_SECRET, algorithm=DEMO_JWT_ALGORITHM)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": TOKEN_TTL_SECONDS,
    }


def get_current_user(authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Missing bearer token")
    raw = authorization.split(" ", 1)[1].strip()
    if not raw:
        raise ApiError(401, "unauthorized", "Missing bearer token")
    try:
        payload = jwt.decode(raw, DEMO_JWT_SECRET, algorithms=[DEMO_JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ApiError(401, "unauthorized", "Invalid token") from exc
    user = get_store().get_user(str(payload.get("sub", "")))
    if user is None:
        raise ApiError(401, "unauthorized", "Unknown user")
    return user


def require_admin(user: User) -> None:
    if user.role != "admin":
        raise ApiError(403, "forbidden", "Admin role is required")
