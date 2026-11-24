"""HTTP client used by Robot keywords and pytest integration tests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol

import requests

from framework.core.config_loader import EnvironmentConfig
from framework.core.exceptions import TransportError
from framework.core.header_builder import build_headers
from framework.core.logger import configure_logging, log_exchange
from framework.core.retry_policy import RetryPolicy
from framework.core.transport import parse_json


class Transport(Protocol):
    def send(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        json_body: Any,
        params: dict[str, Any] | None,
        timeout: float,
    ) -> Any:
        """Perform one HTTP call and return a response-like object."""


@dataclass
class ApiResponse:
    status: int
    headers: dict[str, str]
    text: str
    json_body: Any
    elapsed_ms: float
    attempts: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "headers": self.headers,
            "body": self.json_body,
            "text": self.text,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "attempts": self.attempts,
        }


class HttpClient:
    def __init__(
        self,
        config: EnvironmentConfig,
        transport: Transport,
        *,
        sleeper: Any = time.sleep,
    ) -> None:
        self.config = config
        self.transport = transport
        self.retry = RetryPolicy(config.retry.max_attempts, config.retry.retry_statuses)
        self._sleep = sleeper
        self._logger = configure_logging()

    def get(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("DELETE", path, **kwargs)

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        idempotent: bool = False,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> ApiResponse:
        timeout_seconds = float(self.config.timeout_seconds if timeout is None else timeout)
        request_headers = build_headers(
            headers,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )
        url = f"{self.config.base_url}{path}"
        attempt = 1
        while True:
            log_exchange(
                self._logger,
                event="request",
                method=method.upper(),
                url=url,
                headers=request_headers,
                body=json_body,
                attempt=attempt,
            )
            started = time.perf_counter()
            try:
                raw = self.transport.send(
                    method.upper(),
                    path,
                    request_headers,
                    json_body,
                    params,
                    timeout_seconds,
                )
            except requests.RequestException as exc:
                log_exchange(
                    self._logger,
                    event="transport_error",
                    method=method.upper(),
                    url=url,
                    attempt=attempt,
                    body={"error": exc.__class__.__name__},
                )
                if self.retry.should_retry(
                    method=method,
                    status=None,
                    error=exc,
                    idempotent=idempotent,
                    attempt=attempt,
                ):
                    self._sleep(self.config.retry.backoff_seconds * attempt)
                    attempt += 1
                    continue
                raise TransportError(f"{method.upper()} {path} failed: {exc.__class__.__name__}") from exc

            response = _to_response(raw, attempt, (time.perf_counter() - started) * 1000)
            log_exchange(
                self._logger,
                event="response",
                method=method.upper(),
                url=url,
                headers=response.headers,
                body=response.json_body if response.json_body is not None else response.text,
                status=response.status,
                elapsed_ms=response.elapsed_ms,
                attempt=attempt,
            )
            if self.retry.should_retry(
                method=method,
                status=response.status,
                error=None,
                idempotent=idempotent,
                attempt=attempt,
            ):
                self._sleep(self.config.retry.backoff_seconds * attempt)
                attempt += 1
                continue
            return response


def _to_response(raw: Any, attempts: int, elapsed_ms: float) -> ApiResponse:
    text = raw.text or ""
    if hasattr(raw, "json"):
        try:
            body = raw.json()
        except ValueError:
            body = None
    else:
        body = parse_json(text)
    elapsed = raw.elapsed
    if isinstance(elapsed, timedelta):
        elapsed_ms = elapsed.total_seconds() * 1000
    headers = {str(key): str(value) for key, value in dict(raw.headers).items()}
    return ApiResponse(
        status=int(raw.status_code),
        headers=headers,
        text=text,
        json_body=body,
        elapsed_ms=elapsed_ms,
        attempts=attempts,
    )
