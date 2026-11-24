"""User administration and self-service profile updates."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Response

from demo_api.errors import ApiError
from demo_api.models import UserCreate, UserPatch, UserReplace, public_user
from demo_api.security import get_current_user, require_admin
from demo_api.store import MemoryStore, StoreError, User, get_store

router = APIRouter(prefix="/users", tags=["users"])


def _page(items: list[Any], page: int, page_size: int) -> dict[str, Any]:
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": len(items),
    }


@router.get("")
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor: User = Depends(get_current_user),
) -> dict[str, Any]:
    require_admin(actor)
    users = [public_user(user) for user in get_store().list_users()]
    return _page(users, page, page_size)


@router.post("", status_code=201)
def create_user(payload: UserCreate, actor: User = Depends(get_current_user)) -> dict[str, str]:
    require_admin(actor)
    try:
        user = get_store().add_user(payload.email, payload.password, payload.full_name, payload.role)
    except StoreError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc
    return public_user(user)


@router.get("/{user_id}")
def get_user(user_id: str, actor: User = Depends(get_current_user)) -> dict[str, str]:
    user = get_store().get_user(user_id)
    if user is None:
        raise ApiError(404, "not_found", "User not found")
    if actor.role != "admin" and actor.id != user.id:
        raise ApiError(403, "forbidden", "Not allowed to read this user")
    return public_user(user)


@router.put("/{user_id}")
def replace_user(
    user_id: str,
    payload: UserReplace,
    actor: User = Depends(get_current_user),
) -> dict[str, str]:
    _ensure_can_edit(actor, user_id)
    try:
        user = get_store().update_user_name(user_id, payload.full_name)
    except StoreError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc
    return public_user(user)


@router.patch("/{user_id}")
def patch_user(
    user_id: str,
    payload: UserPatch,
    actor: User = Depends(get_current_user),
) -> dict[str, str]:
    _ensure_can_edit(actor, user_id)
    if payload.full_name is None:
        user = get_store().get_user(user_id)
        if user is None:
            raise ApiError(404, "not_found", "User not found")
        return public_user(user)
    try:
        user = get_store().update_user_name(user_id, payload.full_name)
    except StoreError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc
    return public_user(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    actor: User = Depends(get_current_user),
    store: MemoryStore = Depends(get_store),
) -> Response:
    require_admin(actor)
    try:
        store.delete_user(user_id, actor.id)
    except StoreError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc
    return Response(status_code=204)


def _ensure_can_edit(actor: User, user_id: str) -> None:
    if actor.role != "admin" and actor.id != user_id:
        raise ApiError(403, "forbidden", "Not allowed to update this user")
    if get_store().get_user(user_id) is None:
        raise ApiError(404, "not_found", "User not found")
