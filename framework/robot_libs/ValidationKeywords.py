"""Status, field, and JSON Schema assertions for Robot responses."""

from __future__ import annotations

from typing import Any

from framework.core.response_validator import assert_fields, assert_status
from framework.core.schema_validator import validate_schema


class ValidationKeywords:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def response_status_should_be(self, response: dict[str, Any], expected_status: int) -> None:
        assert_status(int(response["status"]), int(expected_status), response.get("body"))

    def response_field_should_be(self, response: dict[str, Any], field: str, expected: Any) -> None:
        assert_fields(response["body"], {field: expected})

    def response_should_match_schema(self, response: dict[str, Any], schema_name: str) -> None:
        validate_schema(response.get("body"), schema_name)

    def page_items_should_match_schema(self, response: dict[str, Any], item_schema: str) -> None:
        validate_schema(response.get("body"), "page.schema.json")
        for item in response["body"]["items"]:
            validate_schema(item, item_schema)
