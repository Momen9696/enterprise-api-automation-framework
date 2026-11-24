"""Authentication keywords. Passwords stay inside the Python auth manager."""

from __future__ import annotations

from framework.robot_libs.context import runtime


class AuthKeywords:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def login_as(self, role: str) -> str:
        runtime().auth.login(role)
        return f"signed-in:{role}"

    def use_invalid_token(self) -> str:
        runtime().auth.use_raw_token("invalid-token")
        return "invalid-token-selected"
