"""Robot keywords for the five HTTP methods."""

from __future__ import annotations

from typing import Any

from framework.core.masking import mask
from framework.robot_libs.context import as_bool, initialize_runtime, runtime


class ApiKeywords:
    """Reusable GET, POST, PUT, PATCH, and DELETE keywords."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def initialize_api_context(self) -> str:
        initialize_runtime()
        return runtime().config.name

    def get_request(
        self,
        path: str,
        role: str | None = None,
        use_auth: object = True,
        raw_token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._call("GET", path, None, role, use_auth, raw_token, None, False, params)

    def post_request(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        role: str | None = None,
        use_auth: object = True,
        raw_token: str | None = None,
        idempotency_key: str | None = None,
        idempotent: object = False,
    ) -> dict[str, Any]:
        return self._call("POST", path, body, role, use_auth, raw_token, idempotency_key, idempotent, None)

    def put_request(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        role: str | None = None,
        use_auth: object = True,
        raw_token: str | None = None,
    ) -> dict[str, Any]:
        return self._call("PUT", path, body, role, use_auth, raw_token, None, True, None)

    def patch_request(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        role: str | None = None,
        use_auth: object = True,
    ) -> dict[str, Any]:
        return self._call("PATCH", path, body, role, use_auth, None, None, False, None)

    def delete_request(
        self,
        path: str,
        role: str | None = None,
        use_auth: object = True,
    ) -> dict[str, Any]:
        return self._call("DELETE", path, None, role, use_auth, None, None, True, None)

    def _call(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        role: str | None,
        use_auth: object,
        raw_token: str | None,
        idempotency_key: str | None,
        idempotent: object,
        params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        current = runtime()
        headers = None
        if raw_token:
            headers = {"Authorization": f"Bearer {raw_token}"}
        elif as_bool(use_auth):
            headers = current.auth.headers_for(role)
        response = current.client.request(
            method,
            path,
            headers=headers,
            json_body=body,
            params=params,
            idempotent=as_bool(idempotent, default=False),
            idempotency_key=idempotency_key or None,
        )
        payload = response.as_dict()
        payload["body"] = mask(payload["body"])
        payload["headers"] = mask(payload["headers"])
        payload["text"] = ""
        return payload
