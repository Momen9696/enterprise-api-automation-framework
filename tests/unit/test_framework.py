"""Unit tests for configuration, masking, retry, schema, and data helpers."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

import pytest
import requests

from framework.core.config_loader import load_config
from framework.core.data_generator import amount, idempotency_key, unique_email
from framework.core.data_loader import load_excel_cases, load_json_cases
from framework.core.exceptions import (
    ConfigError,
    ResponseValidationError,
    SchemaValidationError,
    TransportError,
)
from framework.core.http_client import HttpClient
from framework.core.library_log import redact_text
from framework.core.masking import mask
from framework.core.response_validator import assert_fields, assert_status
from framework.core.retry_policy import RetryPolicy
from framework.core.schema_validator import validate_schema
from scripts.scan_secrets import scan_text


class FakeResponse:
    def __init__(self, status: int, body: dict | None = None) -> None:
        self.status_code = status
        self._body = body if body is not None else {}
        self.text = json.dumps(self._body)
        self.headers = {"Content-Type": "application/json"}
        self.elapsed = timedelta(milliseconds=4)

    def json(self) -> dict:
        return self._body


class FakeTransport:
    def __init__(self, outcomes: list[FakeResponse | Exception]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []

    def send(self, method: str, path: str, headers: dict, json_body: object, params: dict | None, timeout: float):
        self.calls.append(
            {"method": method, "path": path, "headers": headers, "body": json_body, "timeout": timeout}
        )
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _client(transport: FakeTransport, max_attempts: int = 3) -> HttpClient:
    config = load_config()
    config = type(config)(
        name=config.name,
        base_url=config.base_url,
        timeout_seconds=config.timeout_seconds,
        retry=type(config.retry)(max_attempts, 0, config.retry.retry_statuses),
        users=config.users,
    )
    return HttpClient(config, transport, sleeper=lambda _seconds: None)


def test_profiles_load() -> None:
    local = load_config("local")
    staging = load_config("staging")
    assert local.base_url == "http://127.0.0.1:8000"
    assert local.timeout_seconds == 10
    assert staging.base_url == "http://127.0.0.1:8001"
    assert staging.timeout_seconds == 5
    assert local.users["admin"].email == "admin@demo.local"
    assert local.users["customer"].password == "CustomerPass123!"


def test_missing_profile() -> None:
    with pytest.raises(ConfigError):
        load_config("missing-env")


def test_masking_nested_values() -> None:
    payload = {"password": "SecretPass", "profile": {"access_token": "abc", "name": "Ada"}, "items": [{"cvv": "123"}]}
    redacted = mask(payload)
    assert redacted["password"] == "***"
    assert redacted["profile"]["access_token"] == "***"
    assert redacted["profile"]["name"] == "Ada"
    assert redacted["items"][0]["cvv"] == "***"
    assert payload["password"] == "SecretPass"


def test_redactor_hides_bearer_and_password() -> None:
    raw = '{"password": "SecretPass", "note": "Bearer eyJhbGciOi.eyJzdWI.signature"}'
    text = redact_text(raw)
    assert "SecretPass" not in text
    assert "eyJhbGciOi" not in text
    assert redact_text("Authorization: Bearer abc.def.ghi").count("***") >= 1


def test_retry_policy_refuses_unsafe_post() -> None:
    policy = RetryPolicy(3, (503,))
    assert policy.should_retry(method="GET", status=503, error=None, idempotent=False, attempt=1)
    assert not policy.should_retry(method="POST", status=503, error=None, idempotent=False, attempt=1)
    assert policy.should_retry(method="POST", status=503, error=None, idempotent=True, attempt=1)
    assert not policy.should_retry(method="GET", status=503, error=None, idempotent=False, attempt=3)
    assert not policy.should_retry(method="DELETE", status=None, error=ConnectionError("x"), idempotent=False, attempt=1)


def test_client_retries_get_and_not_plain_post() -> None:
    transport = FakeTransport([FakeResponse(503, {"code": "busy"}), FakeResponse(200, {"status": "ok"})])
    response = _client(transport).get("/health")
    assert response.status == 200
    assert response.attempts == 2
    assert len(transport.calls) == 2
    assert transport.calls[0]["timeout"] == 10

    unsafe = FakeTransport([FakeResponse(503, {"code": "busy"}), FakeResponse(200, {"ok": True})])
    denied = _client(unsafe).post("/transactions", json_body={"password": "SecretPass", "amount": "1.00"})
    assert denied.status == 503
    assert len(unsafe.calls) == 1


def test_client_retries_idempotent_post_and_connection_errors() -> None:
    transport = FakeTransport(
        [requests.ConnectionError("down"), FakeResponse(200, {"access_token": "hidden", "ok": True})]
    )
    response = _client(transport).post("/auth/login", json_body={"password": "SecretPass"}, idempotent=True)
    assert response.status == 200
    assert len(transport.calls) == 2
    with pytest.raises(TransportError):
        _client(FakeTransport([requests.ConnectionError("down")])).post("/transactions", json_body={})


def test_client_logs_are_masked(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("framework")
    logger.propagate = True
    caplog.set_level(logging.INFO, logger="framework")
    transport = FakeTransport([FakeResponse(200, {"access_token": "secret-token"})])
    _client(transport).post("/auth/login", json_body={"password": "SecretPass"}, headers={"Authorization": "Bearer secret-token"})
    assert "SecretPass" not in caplog.text
    assert "secret-token" not in caplog.text
    assert "***" in caplog.text


def test_schema_and_response_validators() -> None:
    validate_schema({"status": "ok"}, "health.schema.json")
    with pytest.raises(SchemaValidationError):
        validate_schema({"status": "ok", "extra": True}, "health.schema.json")
    assert_status(204, 204)
    with pytest.raises(ResponseValidationError):
        assert_status(404, 200, {"code": "not_found"})
    assert_fields({"code": "conflict"}, {"code": "conflict"})


def test_json_and_excel_cases_and_generator(tmp_path: Path) -> None:
    users = load_json_cases("test_data/json/users.json")
    assert len(users) == 5
    rows = load_excel_cases("test_data/excel/api_cases.xlsx", "boundaries")
    assert rows[0]["amount"] == "10.00"
    assert rows[0]["expected_status"] == "201"
    broken = tmp_path / "cases.json"
    broken.write_text('{"not": "a list"}', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_json_cases(broken)
    emails = {unique_email() for _ in range(20)}
    assert len(emails) == 20
    assert all(email.endswith("@demo.local") for email in emails)
    sample = amount("1.00", "2.00")
    assert sample[::-1][2] == "."
    assert len(sample.split(".")[1]) == 2
    assert idempotency_key() != idempotency_key()


def test_secret_scan_patterns_match_constructed_values() -> None:
    github = "ghp_" + ("a" * 36)
    private_key = "-----BEGIN " + "PRIVATE KEY-----"
    assert "github token" in scan_text(github)
    assert "private key" in scan_text(private_key)
    assert scan_text("AdminPass123!") == []
