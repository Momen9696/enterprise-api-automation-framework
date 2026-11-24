"""Login once per role and reuse bearer tokens. Passwords never leave this module."""

from __future__ import annotations

from framework.core.config_loader import UserCredential
from framework.core.exceptions import AuthError
from framework.core.http_client import HttpClient
from framework.core.schema_validator import validate_schema

GENERATED_USER_PASSWORD = "ValidPass123!"


class AuthManager:
    def __init__(self, client: HttpClient, users: dict[str, UserCredential]) -> None:
        self._client = client
        self._users = users
        self._tokens: dict[str, str] = {}
        self.active_role: str | None = None

    def login(self, role: str) -> None:
        credential = self._users.get(role)
        if credential is None:
            raise AuthError(f"Unknown role: {role}")
        response = self._client.post(
            "/auth/login",
            json_body={"email": credential.email, "password": credential.password},
            idempotent=True,
        )
        if response.status != 200 or not isinstance(response.json_body, dict):
            raise AuthError(f"Login failed for role {role} with status {response.status}")
        validate_schema(response.json_body, "token.schema.json")
        token = str(response.json_body["access_token"])
        self._tokens[role] = token
        self.active_role = role

    def headers_for(self, role: str | None = None) -> dict[str, str]:
        selected = role or self.active_role
        if selected is None:
            raise AuthError("No active role. Log in before calling an authorized endpoint.")
        if selected not in self._tokens:
            self.login(selected)
        return {"Authorization": f"Bearer {self._tokens[selected]}"}

    def login_dynamic(self, email: str, slot: str = "dynamic") -> None:
        """Sign in a user created during the run. The fixture password never crosses into Robot."""
        response = self._client.post(
            "/auth/login",
            json_body={"email": email, "password": GENERATED_USER_PASSWORD},
            idempotent=True,
        )
        if response.status != 200 or not isinstance(response.json_body, dict):
            raise AuthError(f"Dynamic login failed with status {response.status}")
        validate_schema(response.json_body, "token.schema.json")
        self._tokens[slot] = str(response.json_body["access_token"])
        self.active_role = slot

    def use_raw_token(self, token: str) -> None:
        self._tokens["raw"] = token
        self.active_role = "raw"

    def clear(self) -> None:
        self._tokens.clear()
        self.active_role = None
