"""Assertions on status codes and JSON fields."""

from __future__ import annotations

from typing import Any

from framework.core.exceptions import ResponseValidationError


def assert_status(actual: int, expected: int, body: Any = None) -> None:
    if int(actual) != int(expected):
        raise ResponseValidationError(f"expected status {expected}, got {actual}, body={body}")


def assert_fields(body: dict[str, Any], expected: dict[str, Any]) -> None:
    if not isinstance(body, dict):
        raise ResponseValidationError(f"expected a JSON object, got {type(body).__name__}")
    for key, value in expected.items():
        actual = body.get(key)
        if actual != value:
            raise ResponseValidationError(f"field {key}: expected {value!r}, got {actual!r}")


def assert_field_present(body: dict[str, Any], *fields: str) -> None:
    missing = [field for field in fields if field not in body]
    if missing:
        raise ResponseValidationError(f"missing fields: {', '.join(missing)}")
