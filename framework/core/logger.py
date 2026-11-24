"""Logger that only receives already-masked payloads."""

from __future__ import annotations

import logging
from typing import Any

from framework.core.masking import mask

_CONFIGURED = False


def configure_logging() -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger("framework")
    if not _CONFIGURED:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
        _CONFIGURED = True
    return logger


def log_exchange(
    logger: logging.Logger,
    *,
    event: str,
    method: str,
    url: str,
    headers: dict[str, Any] | None = None,
    body: Any = None,
    status: int | None = None,
    elapsed_ms: float | None = None,
    attempt: int | None = None,
) -> None:
    logger.info(
        "%s method=%s url=%s status=%s attempt=%s elapsed_ms=%s headers=%s body=%s",
        event,
        method,
        url,
        status,
        attempt,
        None if elapsed_ms is None else round(elapsed_ms, 2),
        mask(headers or {}),
        mask(body),
    )
