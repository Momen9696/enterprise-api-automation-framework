"""Consistent API errors for the demo ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApiError(Exception):
    """Domain error rendered as the shared error schema."""

    status: int
    code: str
    message: str
    details: list[dict[str, Any]] = field(default_factory=list)

    def body(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}
