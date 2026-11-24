"""Redact sensitive values before they reach logs or reports."""

from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "authorization",
    "secret",
    "card_number",
    "cvv",
}
MASK = "***"


def mask(value: Any) -> Any:
    """Return a copy with sensitive keys replaced. Non-containers pass through."""
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                redacted[key] = MASK
            else:
                redacted[key] = mask(item)
        return redacted
    if isinstance(value, list):
        return [mask(item) for item in value]
    if isinstance(value, tuple):
        return tuple(mask(item) for item in value)
    return value
