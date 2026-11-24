"""Unique synthetic values for isolated, parallel-safe cases."""

from __future__ import annotations

import random
import uuid
from decimal import Decimal


def unique_email(prefix: str = "user") -> str:
    safe_prefix = "".join(char for char in prefix.lower() if char.isalnum()) or "user"
    return f"{safe_prefix}.{uuid.uuid4().hex[:12]}@demo.local"


def idempotency_key() -> str:
    return str(uuid.uuid4())


def amount(low: str = "0.01", high: str = "100.00") -> str:
    low_cents = int((Decimal(low) * 100).to_integral_value())
    high_cents = int((Decimal(high) * 100).to_integral_value())
    if high_cents < low_cents:
        raise ValueError("high must be greater than or equal to low")
    cents = random.randint(low_cents, high_cents)
    return f"{Decimal(cents) / Decimal(100):.2f}"
