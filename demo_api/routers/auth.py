"""Login for seeded and dynamically created users."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from demo_api.models import LoginRequest
from demo_api.security import authenticate, issue_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    user = authenticate(payload.email, payload.password)
    return issue_token(user)
