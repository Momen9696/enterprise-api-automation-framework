"""Customer accounts. Balances change only through transactions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from demo_api.errors import ApiError
from demo_api.models import AccountCreate, public_account
from demo_api.security import get_current_user
from demo_api.store import StoreError, User, get_store

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor: User = Depends(get_current_user),
) -> dict[str, Any]:
    owner_id = None if actor.role == "admin" else actor.id
    items = [public_account(account) for account in get_store().list_accounts(owner_id)]
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": len(items),
    }


@router.post("", status_code=201)
def create_account(payload: AccountCreate, actor: User = Depends(get_current_user)) -> dict[str, str]:
    try:
        account = get_store().add_account(actor.id, payload.currency, payload.account_type)
    except StoreError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc
    return public_account(account)


@router.get("/{account_id}")
def get_account(account_id: str, actor: User = Depends(get_current_user)) -> dict[str, str]:
    account = get_store().get_account(account_id)
    if account is None:
        raise ApiError(404, "not_found", "Account not found")
    if actor.role != "admin" and account.owner_id != actor.id:
        raise ApiError(403, "forbidden", "Not allowed to read this account")
    return public_account(account)
