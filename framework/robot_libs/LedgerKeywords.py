"""Keywords that build ledger data inside Python so secrets stay out of Robot logs."""

from __future__ import annotations

from typing import Any

from framework.core.auth_manager import GENERATED_USER_PASSWORD
from framework.core.data_generator import unique_email
from framework.core.response_validator import assert_status
from framework.robot_libs.ApiKeywords import ApiKeywords
from framework.robot_libs.context import runtime

_PASSWORD_MODES = {
    "valid": GENERATED_USER_PASSWORD,
    "empty": "",
    "short": "short",
}


class LedgerKeywords:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def provision_customer(self, full_name: str = "Synthetic Customer") -> dict[str, Any]:
        response = self._create_user(unique_email("customer"), GENERATED_USER_PASSWORD, full_name, "customer")
        assert_status(response["status"], 201, response.get("body"))
        return response["body"]

    def login_created_customer(self, email: str) -> str:
        runtime().auth.login_dynamic(email)
        return "signed-in:dynamic"

    def open_checking_account(self) -> dict[str, Any]:
        response = ApiKeywords()._call(
            "POST",
            "/accounts",
            {"account_type": "checking", "currency": "USD"},
            "dynamic",
            True,
            None,
            None,
            False,
            None,
        )
        assert_status(response["status"], 201, response.get("body"))
        return response["body"]

    def post_transaction(
        self,
        account_id: str,
        txn_type: str,
        amount: str,
        destination: str = "",
        idempotency_key: str = "",
        role: str = "dynamic",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "account_id": account_id,
            "type": txn_type,
            "amount": str(amount),
        }
        if destination:
            body["destination_account_id"] = destination
        return ApiKeywords()._call(
            "POST",
            "/transactions",
            body,
            role,
            True,
            None,
            idempotency_key or None,
            bool(idempotency_key),
            None,
        )

    def run_user_row(self, row: dict[str, Any]) -> dict[str, Any]:
        mode = str(row.get("password_mode") or "valid")
        password = _PASSWORD_MODES[mode]
        role = str(row.get("role") or "customer")
        return self._create_user(unique_email("row"), password, row.get("full_name"), role)

    def run_amount_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Deposit a known balance, then execute the row against a fresh account."""
        return self._amount_against_new_account(row)

    def post_user_with_numeric_name(self) -> dict[str, Any]:
        body = {
            "email": unique_email("type"),
            "password": GENERATED_USER_PASSWORD,
            "full_name": 12345,
            "role": "customer",
        }
        return ApiKeywords()._call("POST", "/users", body, "admin", True, None, None, False, None)

    def post_user_missing_password(self) -> dict[str, Any]:
        body = {
            "email": unique_email("missing"),
            "full_name": "Missing Password",
            "role": "customer",
        }
        return ApiKeywords()._call("POST", "/users", body, "admin", True, None, None, False, None)

    def run_account_row(self, row: dict[str, Any]) -> dict[str, Any]:
        user = self.provision_customer(str(row["full_name"]))
        self.login_created_customer(str(user["email"]))
        return ApiKeywords()._call(
            "POST",
            "/accounts",
            {"account_type": row["account_type"], "currency": row["currency"]},
            "dynamic",
            True,
            None,
            None,
            False,
            None,
        )

    def post_duplicate_email(self, email: str) -> dict[str, Any]:
        return self._create_user(email, GENERATED_USER_PASSWORD, "Duplicate User", "customer")

    def _create_user(self, email: str, password: str, full_name: Any, role: str) -> dict[str, Any]:
        return ApiKeywords()._call(
            "POST",
            "/users",
            {"email": email, "password": password, "full_name": full_name, "role": role},
            "admin",
            True,
            None,
            None,
            False,
            None,
        )

    def _amount_against_new_account(self, row: dict[str, Any]) -> dict[str, Any]:
        user = self.provision_customer("Amount Row")
        self.login_created_customer(user["email"])
        account = self.open_checking_account()
        funded = self.post_transaction(account["id"], "deposit", "100.00")
        assert_status(funded["status"], 201, funded.get("body"))
        response = self.post_transaction(account["id"], str(row.get("type") or "withdraw"), str(row["amount"]))
        return response
