"""Contract tests for the synthetic ledger API through the framework client."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from framework.core.auth_manager import GENERATED_USER_PASSWORD
from framework.core.config_loader import EnvironmentConfig, load_config
from framework.core.data_generator import unique_email
from framework.core.header_builder import response_header
from framework.core.http_client import HttpClient
from framework.core.schema_validator import validate_schema
from framework.core.transport import RequestsLibraryTransport

Api = tuple[HttpClient, EnvironmentConfig]


def _login(client: HttpClient, email: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        json_body={"email": email, "password": password},
        idempotent=True,
    )
    assert response.status == 200, response.text
    validate_schema(response.json_body, "token.schema.json")
    return str(response.json_body["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _admin(api: Api) -> tuple[HttpClient, str]:
    client, config = api
    user = config.users["admin"]
    return client, _login(client, user.email, user.password)


def _create_customer(client: HttpClient, admin_token: str) -> dict[str, Any]:
    response = client.post(
        "/users",
        headers=_auth(admin_token),
        json_body={
            "email": unique_email("it"),
            "password": GENERATED_USER_PASSWORD,
            "full_name": "Integration Customer",
            "role": "customer",
        },
    )
    assert response.status == 201, response.text
    validate_schema(response.json_body, "user.schema.json")
    return response.json_body


def _open_account(client: HttpClient, token: str) -> dict[str, Any]:
    response = client.post(
        "/accounts",
        headers=_auth(token),
        json_body={"account_type": "checking", "currency": "USD"},
    )
    assert response.status == 201, response.text
    validate_schema(response.json_body, "account.schema.json")
    return response.json_body


def _post_txn(
    client: HttpClient,
    token: str,
    account_id: str,
    txn_type: str,
    amount: str,
    destination: str | None = None,
    key: str | None = None,
) -> Any:
    body: dict[str, Any] = {"account_id": account_id, "type": txn_type, "amount": amount}
    if destination:
        body["destination_account_id"] = destination
    return client.post(
        "/transactions",
        headers=_auth(token),
        json_body=body,
        idempotency_key=key,
        idempotent=key is not None,
    )


class TestAuth:
    def test_login_and_correlation_header(self, api: Api) -> None:
        client, config = api
        user = config.users["customer"]
        response = client.post(
            "/auth/login",
            json_body={"email": user.email, "password": user.password},
            correlation_id="cid-integration-1",
            idempotent=True,
        )
        assert response.status == 200
        assert response_header(response.headers, "x-correlation-id") == "cid-integration-1"
        assert response.attempts == 1

    def test_invalid_credentials_and_missing_field(self, api: Api) -> None:
        client, config = api
        bad = client.post(
            "/auth/login",
            json_body={"email": config.users["admin"].email, "password": "wrong-password"},
        )
        assert bad.status == 401
        assert bad.json_body["code"] == "invalid_credentials"
        validate_schema(bad.json_body, "error.schema.json")
        missing = client.post("/auth/login", json_body={"email": "admin@demo.local"})
        assert missing.status == 422
        assert missing.json_body["code"] == "validation_error"
        assert missing.attempts == 1

    def test_missing_and_invalid_token(self, api: Api) -> None:
        client, _config = api
        missing = client.get("/users")
        assert missing.status == 401
        assert missing.json_body["code"] == "unauthorized"
        invalid = client.get("/users", headers={"Authorization": "Bearer invalid-token"})
        assert invalid.status == 401
        validate_schema(invalid.json_body, "error.schema.json")


class TestUsersAndAccounts:
    def test_crud_authorization_and_pagination(self, api: Api) -> None:
        client, config = api
        admin_token = _login(client, config.users["admin"].email, config.users["admin"].password)
        customer_token = _login(
            client, config.users["customer"].email, config.users["customer"].password
        )
        forbidden = client.get("/users", headers=_auth(customer_token))
        assert forbidden.status == 403
        assert forbidden.json_body["code"] == "forbidden"

        created = _create_customer(client, admin_token)
        fetched = client.get(f"/users/{created['id']}", headers=_auth(admin_token))
        assert fetched.status == 200
        replaced = client.put(
            f"/users/{created['id']}",
            headers=_auth(admin_token),
            json_body={"full_name": "Replaced Name"},
        )
        assert replaced.status == 200
        assert replaced.json_body["full_name"] == "Replaced Name"
        patched = client.patch(
            f"/users/{created['id']}",
            headers=_auth(customer_token),
            json_body={"full_name": "Should Fail"},
        )
        assert patched.status == 403
        deleted = client.delete(f"/users/{created['id']}", headers=_auth(admin_token))
        assert deleted.status == 204
        assert deleted.json_body is None
        missing = client.get(f"/users/{created['id']}", headers=_auth(admin_token))
        assert missing.status == 404
        assert missing.json_body["code"] == "not_found"

        for _ in range(3):
            _create_customer(client, admin_token)
        page = client.get("/users", headers=_auth(admin_token), params={"page": 1, "page_size": 2})
        assert page.status == 200
        validate_schema(page.json_body, "page.schema.json")
        assert page.json_body["total"] == 5
        assert len(page.json_body["items"]) == 2
        empty = client.get("/users", headers=_auth(admin_token), params={"page": 9, "page_size": 2})
        assert empty.json_body["items"] == []
        assert empty.json_body["total"] == 5
        zero = client.get("/users", headers=_auth(admin_token), params={"page": 0, "page_size": 20})
        assert zero.status == 422
        huge = client.get("/users", headers=_auth(admin_token), params={"page": 1, "page_size": 101})
        assert huge.status == 422

    def test_account_isolation_and_wrong_method(self, api: Api) -> None:
        client, config = api
        admin_token = _login(client, config.users["admin"].email, config.users["admin"].password)
        owner = _create_customer(client, admin_token)
        owner_token = _login(client, owner["email"], GENERATED_USER_PASSWORD)
        account = _open_account(client, owner_token)
        stranger_token = _login(
            client, config.users["customer"].email, config.users["customer"].password
        )
        hidden = client.get(f"/accounts/{account['id']}", headers=_auth(stranger_token))
        assert hidden.status == 403
        visible = client.get(f"/accounts/{account['id']}", headers=_auth(admin_token))
        assert visible.status == 200
        missing = client.get(f"/accounts/{uuid.uuid4()}", headers=_auth(owner_token))
        assert missing.status == 404
        method = client.post("/health")
        assert method.status == 405
        assert method.json_body["code"] == "method_not_allowed"
        validate_schema(method.json_body, "error.schema.json")

    def test_duplicate_email_wrong_type_and_invalid_currency(self, api: Api) -> None:
        client, _config = _admin(api)
        created = _create_customer(client, _login(client, api[1].users["admin"].email, api[1].users["admin"].password))
        duplicate = client.post(
            "/users",
            headers=_auth(_login(client, api[1].users["admin"].email, api[1].users["admin"].password)),
            json_body={
                "email": created["email"],
                "password": GENERATED_USER_PASSWORD,
                "full_name": "Copy",
                "role": "customer",
            },
        )
        assert duplicate.status == 409
        numeric = client.post(
            "/users",
            headers=_auth(_login(client, api[1].users["admin"].email, api[1].users["admin"].password)),
            json_body={
                "email": unique_email("bad"),
                "password": GENERATED_USER_PASSWORD,
                "full_name": 12345,
                "role": "customer",
            },
        )
        assert numeric.status == 422
        assert numeric.json_body["code"] == "validation_error"
        owner_token = _login(client, created["email"], GENERATED_USER_PASSWORD)
        currency = client.post(
            "/accounts",
            headers=_auth(owner_token),
            json_body={"account_type": "checking", "currency": "EUR"},
        )
        assert currency.status == 422


class TestTransactions:
    def test_transfer_idempotency_and_duplicate_debits(self, api: Api) -> None:
        client, config = api
        admin = _login(client, config.users["admin"].email, config.users["admin"].password)
        first_user = _create_customer(client, admin)
        second_user = _create_customer(client, admin)
        first_token = _login(client, first_user["email"], GENERATED_USER_PASSWORD)
        second_token = _login(client, second_user["email"], GENERATED_USER_PASSWORD)
        source = _open_account(client, first_token)
        destination = _open_account(client, second_token)
        funded = _post_txn(client, first_token, source["id"], "deposit", "80.00")
        assert funded.status == 201
        validate_schema(funded.json_body, "transaction.schema.json")
        key = str(uuid.uuid4())
        sent = _post_txn(
            client, first_token, source["id"], "transfer", "30.00", destination["id"], key
        )
        replay = _post_txn(
            client, first_token, source["id"], "transfer", "30.00", destination["id"], key
        )
        assert sent.status == 201
        assert sent.json_body["idempotent_replay"] is False
        assert replay.status == 200
        assert replay.json_body["id"] == sent.json_body["id"]
        assert replay.json_body["idempotent_replay"] is True
        conflict = _post_txn(client, first_token, source["id"], "withdraw", "1.00", key=key)
        assert conflict.status == 409
        assert conflict.json_body["code"] == "idempotency_conflict"
        first_debit = _post_txn(client, first_token, source["id"], "withdraw", "10.00")
        second_debit = _post_txn(client, first_token, source["id"], "withdraw", "10.00")
        assert first_debit.status == 201
        assert second_debit.status == 201
        assert first_debit.json_body["id"] != second_debit.json_body["id"]
        source_after = client.get(f"/accounts/{source['id']}", headers=_auth(first_token))
        destination_after = client.get(
            f"/accounts/{destination['id']}", headers=_auth(second_token)
        )
        assert source_after.json_body["balance"] == "30.00"
        assert destination_after.json_body["balance"] == "30.00"
        listed = client.get("/transactions", headers=_auth(first_token), params={"page": 1, "page_size": 20})
        assert listed.status == 200
        assert listed.json_body["total"] == 4

    @pytest.mark.parametrize(
        ("amount", "code"),
        [("0.00", "invalid_amount"), ("-1.00", "invalid_amount"), ("5.00", "insufficient_funds")],
    )
    def test_amount_boundaries(self, api: Api, amount: str, code: str) -> None:
        client, config = api
        admin = _login(client, config.users["admin"].email, config.users["admin"].password)
        user = _create_customer(client, admin)
        token = _login(client, user["email"], GENERATED_USER_PASSWORD)
        account = _open_account(client, token)
        response = _post_txn(client, token, account["id"], "withdraw", amount)
        assert response.status == 422
        assert response.json_body["code"] == code
        validate_schema(response.json_body, "error.schema.json")

    def test_invalid_transfer_and_unknown_transaction(self, api: Api) -> None:
        client, config = api
        admin = _login(client, config.users["admin"].email, config.users["admin"].password)
        user = _create_customer(client, admin)
        token = _login(client, user["email"], GENERATED_USER_PASSWORD)
        account = _open_account(client, token)
        same = _post_txn(client, token, account["id"], "transfer", "5.00", account["id"])
        assert same.status == 422
        missing_destination = _post_txn(client, token, account["id"], "transfer", "5.00")
        assert missing_destination.status == 422
        too_precise = _post_txn(client, token, account["id"], "deposit", "1.001")
        assert too_precise.status == 422
        unknown = client.get(f"/transactions/{uuid.uuid4()}", headers=_auth(token))
        assert unknown.status == 404
        other = _create_customer(client, admin)
        other_token = _login(client, other["email"], GENERATED_USER_PASSWORD)
        other_account = _open_account(client, other_token)
        stolen = _post_txn(client, token, other_account["id"], "deposit", "5.00")
        assert stolen.status == 403


def test_reset_disabled() -> None:
    from tests.integration.conftest import _free_port, _wait_until_ready, start_demo_api

    port = _free_port()
    proc = start_demo_api(port, allow_reset=False)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_ready(url, proc)
        config = load_config(base_url=url)
        client = HttpClient(config, RequestsLibraryTransport(config.base_url, config.timeout_seconds))
        response = client.post("/test/reset")
        assert response.status == 404
        assert response.json_body["code"] == "not_found"
        health = client.get("/health")
        assert health.status == 200
        validate_schema(health.json_body, "health.schema.json")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
