"""HTTP calls through Robot Framework RequestsLibrary, with our retry policy on top.

RequestsLibrary's own urllib3 retries are disabled (max_retries=0). Retry decisions
live in RetryPolicy so unsafe methods are not repeated by a hidden adapter.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from framework.core.library_log import install_masked_library_logging


class RequestsLibraryTransport:
    def __init__(self, base_url: str, timeout: float) -> None:
        from RequestsLibrary import RequestsLibrary

        install_masked_library_logging()
        self._library = RequestsLibrary()
        self._alias = "framework"
        self._library.create_session(
            self._alias,
            base_url,
            timeout=timeout,
            max_retries=0,
            verify=False,
        )

    def send(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        json_body: Any,
        params: dict[str, Any] | None,
        timeout: float,
    ) -> requests.Response:
        verb = method.upper()
        senders = {
            "GET": self._library.get_on_session,
            "POST": self._library.post_on_session,
            "PUT": self._library.put_on_session,
            "PATCH": self._library.patch_on_session,
            "DELETE": self._library.delete_on_session,
        }
        try:
            sender = senders[verb]
        except KeyError as exc:
            raise ValueError(f"Unsupported method: {method}") from exc
        kwargs: dict[str, Any] = {
            "headers": headers,
            "timeout": timeout,
            "expected_status": "any",
        }
        if params is not None:
            kwargs["params"] = params
        if json_body is not None and verb != "GET":
            kwargs["json"] = json_body
        return sender(self._alias, path, **kwargs)


def parse_json(text: str) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
