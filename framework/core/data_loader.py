"""Load JSON and Excel rows used by data-driven tests."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import openpyxl

from framework.core.config_loader import project_root
from framework.core.exceptions import ConfigError


def resolve_data_path(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = project_root() / candidate
    if not candidate.is_file():
        raise ConfigError(f"Test data file not found: {candidate}")
    return candidate


def load_json_cases(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(resolve_data_path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ConfigError("JSON test data must be a list of objects")
    return payload


def load_excel_cases(path: str | Path, sheet: str) -> list[dict[str, str]]:
    workbook = openpyxl.load_workbook(resolve_data_path(path), data_only=True)
    if sheet not in workbook.sheetnames:
        raise ConfigError(f"Worksheet not found: {sheet}")
    rows = list(workbook[sheet].iter_rows(values_only=True))
    if not rows:
        raise ConfigError(f"Worksheet is empty: {sheet}")
    headers = [str(cell).strip() for cell in rows[0]]
    if any(not header or header == "None" for header in headers):
        raise ConfigError(f"Worksheet {sheet} is missing a header cell")
    cases: list[dict[str, str]] = []
    for raw in rows[1:]:
        if raw is None or all(cell is None or str(cell).strip() == "" for cell in raw):
            continue
        cases.append({headers[index]: _cell(raw[index] if index < len(raw) else None) for index in range(len(headers))})
    return cases


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{Decimal(str(value)).quantize(Decimal('0.01')):.2f}"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return str(value).strip()
