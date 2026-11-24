"""Stop RequestsLibrary from writing tokens or passwords into the Robot log."""

from __future__ import annotations

import json
import re
from typing import Any

from framework.core.masking import mask

_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+")
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
_SENSITIVE_FIELD = re.compile(
    r"(?i)(['\"]?(?:password|access_token|token|authorization|secret|card_number|cvv)['\"]?\s*[:=]\s*['\"])([^'\"]*)(['\"])"
)
_INSTALLED = False


def redact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            text = json.dumps(mask(json.loads(stripped)))
        except json.JSONDecodeError:
            pass
    text = _BEARER.sub("Bearer ***", text)
    text = _JWT.sub("***", text)
    text = _SENSITIVE_FIELD.sub(r"\1***\3", text)
    return text


def install_masked_library_logging() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from RequestsLibrary import log as library_log
    from robot.api import logger

    def log_request(response: Any) -> None:
        request = response.history[0].request if response.history else response.request
        redirected = "(redirected) " if response.history else ""
        message = (
            f"{request.method.upper()} Request : url={request.url} {redirected}\n "
            f"path_url={request.path_url} \n headers={redact_text(dict(request.headers))} \n "
            f"body={redact_text(request.body)} \n"
        )
        logger.info(message)

    def log_response(response: Any) -> None:
        message = (
            f"{response.request.method.upper()} Response : url={response.url} \n "
            f"status={response.status_code}, reason={response.reason} \n "
            f"headers={redact_text(dict(response.headers))} \n body={redact_text(response.text)} \n"
        )
        logger.info(message)

    library_log.log_request = log_request
    library_log.log_response = log_response
    _INSTALLED = True
