"""Create the sample Excel workbook used by data-driven suites."""

from __future__ import annotations

from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "test_data" / "excel" / "api_cases.xlsx"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    users = workbook.active
    users.title = "users"
    users.append(["full_name", "password_mode", "role", "expected_status", "expected_code"])
    users.append(["Excel Customer", "valid", "customer", 201, ""])
    users.append(["", "valid", "customer", 422, "validation_error"])

    accounts = workbook.create_sheet("accounts")
    accounts.append(["full_name", "account_type", "currency", "expected_status", "expected_code"])
    accounts.append(["Excel Holder", "checking", "USD", 201, ""])
    accounts.append(["Excel Rejected", "checking", "EUR", 422, "validation_error"])

    boundaries = workbook.create_sheet("boundaries")
    boundaries.append(["case_id", "type", "amount", "expected_status", "expected_code"])
    boundaries.append(["within_balance", "withdraw", "10.00", 201, ""])
    boundaries.append(["full_balance", "withdraw", "100.00", 201, ""])
    boundaries.append(["zero", "withdraw", "0.00", 422, "invalid_amount"])
    boundaries.append(["negative", "withdraw", "-1.00", 422, "invalid_amount"])
    boundaries.append(["over_balance", "withdraw", "250.00", 422, "insufficient_funds"])
    boundaries.append(["above_max", "withdraw", "1000000.01", 422, "invalid_amount"])
    workbook.save(TARGET)


if __name__ == "__main__":
    main()
