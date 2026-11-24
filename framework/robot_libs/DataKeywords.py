"""Load external cases. Payloads that contain credentials are built in LedgerKeywords."""

from __future__ import annotations

from typing import Any

from framework.core.data_generator import amount, idempotency_key, unique_email
from framework.core.data_loader import load_excel_cases, load_json_cases


class DataKeywords:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def load_json_cases(self, path: str) -> list[dict[str, Any]]:
        return load_json_cases(path)

    def load_excel_cases(self, path: str, sheet: str) -> list[dict[str, str]]:
        return load_excel_cases(path, sheet)

    def unique_email(self, prefix: str = "user") -> str:
        return unique_email(prefix)

    def new_idempotency_key(self) -> str:
        return idempotency_key()

    def random_amount(self, low: str = "0.01", high: str = "25.00") -> str:
        return amount(low, high)
