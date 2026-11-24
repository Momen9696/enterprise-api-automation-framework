"""JSON Schema checks against files in the schemas directory."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from framework.core.config_loader import project_root
from framework.core.exceptions import SchemaValidationError


def schema_path(schema_name: str) -> Path:
    path = project_root() / "schemas" / schema_name
    if not path.is_file():
        raise SchemaValidationError(f"Schema file not found: {schema_name}")
    return path


@lru_cache(maxsize=32)
def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads(schema_path(schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_schema(instance: object, schema_name: str) -> None:
    try:
        _validator(schema_name).validate(instance)
    except ValidationError as exc:
        raise SchemaValidationError(f"{schema_name}: {exc.message}") from exc
