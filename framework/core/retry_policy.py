"""Decide whether a failed call is safe to send again.

POST, PUT, PATCH, and DELETE are not retried unless the caller marks the call
idempotent. That keeps a retry from posting a second withdrawal.
"""

from __future__ import annotations

SAFE_METHODS = {"GET", "HEAD"}


class RetryPolicy:
    def __init__(self, max_attempts: int, retry_statuses: tuple[int, ...] | set[int]) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.max_attempts = max_attempts
        self.retry_statuses = {int(code) for code in retry_statuses}

    def should_retry(
        self,
        *,
        method: str,
        status: int | None,
        error: BaseException | None,
        idempotent: bool,
        attempt: int,
    ) -> bool:
        if attempt >= self.max_attempts:
            return False
        safe = method.upper() in SAFE_METHODS or idempotent
        if not safe:
            return False
        if error is not None:
            return True
        return status in self.retry_statuses
