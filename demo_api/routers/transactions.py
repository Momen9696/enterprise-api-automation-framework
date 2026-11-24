"""Deposits, withdrawals, and transfers with idempotency keys."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse

from demo_api.errors import ApiError
from demo_api.models import TransactionCreate, public_transaction
from demo_api.security import get_current_user
from demo_api.store import StoreError, User, get_store

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor: User = Depends(get_current_user),
) -> dict[str, Any]:
    owner_id = None if actor.role == "admin" else actor.id
    items = [
        public_transaction(txn, replay=False)
        for txn in get_store().list_transactions(owner_id)
    ]
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": len(items),
    }


@router.post("", status_code=201)
def create_transaction(
    payload: TransactionCreate,
    actor: User = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    key = idempotency_key.strip() if idempotency_key else None
    try:
        txn, replay = get_store().apply_transaction(
            actor_id=actor.id,
            account_id=payload.account_id,
            destination_account_id=payload.destination_account_id,
            txn_type=payload.type,
            amount=payload.amount,
            idempotency_key=key or None,
        )
    except StoreError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc
    body = public_transaction(txn, replay=replay)
    return JSONResponse(status_code=200 if replay else 201, content=body)


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, actor: User = Depends(get_current_user)) -> dict[str, Any]:
    txn = get_store().get_transaction(transaction_id)
    if txn is None:
        raise ApiError(404, "not_found", "Transaction not found")
    if actor.role != "admin":
        source_owner = get_store().account_owner(txn.account_id)
        dest_owner = (
            get_store().account_owner(txn.destination_account_id)
            if txn.destination_account_id
            else None
        )
        if actor.id not in {source_owner, dest_owner}:
            raise ApiError(403, "forbidden", "Not allowed to read this transaction")
    return public_transaction(txn, replay=False)
