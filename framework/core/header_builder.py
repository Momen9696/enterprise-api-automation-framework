"""Build the headers every call shares."""

from __future__ import annotations

import uuid
from typing import Any


def build_headers(
    extra: dict[str, str] | None = None,
    *,
    correlation_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id or str(uuid.uuid4()),
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    if extra:
        for key, value in extra.items():
            headers[str(key)] = str(value)
    return headers


def response_header(headers: Any, name: str) -> str | None:
    target = name.lower()
    for key, value in dict(headers).items():
        if str(key).lower() == target:
            return str(value)
    return None
