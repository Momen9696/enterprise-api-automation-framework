"""Request and response models for the demo ledger API."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_AMOUNT = Decimal("1000000.00")


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(ApiModel):
    email: str
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        if not EMAIL_RE.match(value):
            raise ValueError("invalid email")
        return value.lower()


class UserCreate(ApiModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=80)
    role: Literal["admin", "customer"] = "customer"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        if not EMAIL_RE.match(value):
            raise ValueError("invalid email")
        return value.lower()

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("full_name is required")
        return cleaned


class UserReplace(ApiModel):
    full_name: str = Field(min_length=1, max_length=80)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("full_name is required")
        return cleaned


class UserPatch(ApiModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("full_name is required")
        return cleaned


class AccountCreate(ApiModel):
    account_type: Literal["checking", "savings"] = "checking"
    currency: Literal["USD"] = "USD"


class TransactionCreate(ApiModel):
    account_id: str = Field(min_length=1)
    type: Literal["deposit", "withdraw", "transfer"]
    amount: Decimal
    destination_account_id: str | None = None

    @field_validator("amount")
    @classmethod
    def check_scale(cls, value: Decimal) -> Decimal:
        exponent = value.as_tuple().exponent
        if not isinstance(exponent, int) or exponent < -2:
            raise ValueError("amount must have at most 2 decimal places")
        return value


def money_str(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def public_user(user: Any) -> dict[str, str]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


def public_account(account: Any) -> dict[str, str]:
    return {
        "id": account.id,
        "owner_id": account.owner_id,
        "currency": account.currency,
        "account_type": account.account_type,
        "balance": money_str(account.balance),
        "status": account.status,
    }


def public_transaction(txn: Any, *, replay: bool) -> dict[str, Any]:
    return {
        "id": txn.id,
        "account_id": txn.account_id,
        "destination_account_id": txn.destination_account_id,
        "type": txn.type,
        "amount": money_str(txn.amount),
        "created_by": txn.created_by,
        "idempotent_replay": replay,
    }
