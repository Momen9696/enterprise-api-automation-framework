"""Thread-safe in-memory ledger. Seed data is synthetic and fixed."""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, replace
from decimal import Decimal

ADMIN_ID = "00000000-0000-4000-8000-000000000001"
CUSTOMER_ID = "00000000-0000-4000-8000-000000000002"
ACCOUNT_ID = "00000000-0000-4000-8000-000000000003"
MAX_AMOUNT = Decimal("1000000.00")


@dataclass
class StoreError(Exception):
    status: int
    code: str
    message: str


@dataclass
class User:
    id: str
    email: str
    password: str
    full_name: str
    role: str


@dataclass
class Account:
    id: str
    owner_id: str
    currency: str
    account_type: str
    balance: Decimal
    status: str


@dataclass
class Transaction:
    id: str
    account_id: str
    destination_account_id: str | None
    type: str
    amount: Decimal
    created_by: str


@dataclass
class IdempotencyRecord:
    request_hash: str
    transaction_id: str


class MemoryStore:
    """All mutations run under one lock so balances stay consistent."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.users: dict[str, User] = {}
        self.accounts: dict[str, Account] = {}
        self.transactions: dict[str, Transaction] = {}
        self.idempotency: dict[tuple[str, str], IdempotencyRecord] = {}
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.users = {}
            self.accounts = {}
            self.transactions = {}
            self.idempotency = {}
            self._seed()

    def _seed(self) -> None:
        self.users[ADMIN_ID] = User(
            id=ADMIN_ID,
            email="admin@demo.local",
            password="AdminPass123!",
            full_name="Demo Admin",
            role="admin",
        )
        self.users[CUSTOMER_ID] = User(
            id=CUSTOMER_ID,
            email="customer@demo.local",
            password="CustomerPass123!",
            full_name="Demo Customer",
            role="customer",
        )
        self.accounts[ACCOUNT_ID] = Account(
            id=ACCOUNT_ID,
            owner_id=CUSTOMER_ID,
            currency="USD",
            account_type="checking",
            balance=Decimal("1000.00"),
            status="open",
        )

    def find_user_by_email(self, email: str) -> User | None:
        with self._lock:
            for user in self.users.values():
                if user.email == email.lower():
                    return replace(user)
        return None

    def get_user(self, user_id: str) -> User | None:
        with self._lock:
            user = self.users.get(user_id)
            return replace(user) if user else None

    def list_users(self) -> list[User]:
        with self._lock:
            return [replace(user) for user in sorted(self.users.values(), key=lambda item: item.email)]

    def add_user(self, email: str, password: str, full_name: str, role: str) -> User:
        with self._lock:
            if any(user.email == email for user in self.users.values()):
                raise StoreError(409, "conflict", "Email already exists")
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                password=password,
                full_name=full_name,
                role=role,
            )
            self.users[user.id] = user
            return replace(user)

    def update_user_name(self, user_id: str, full_name: str) -> User:
        with self._lock:
            user = self.users.get(user_id)
            if user is None:
                raise StoreError(404, "not_found", "User not found")
            user.full_name = full_name
            return replace(user)

    def delete_user(self, user_id: str, actor_id: str) -> None:
        with self._lock:
            if user_id not in self.users:
                raise StoreError(404, "not_found", "User not found")
            if user_id == actor_id:
                raise StoreError(403, "forbidden", "You cannot delete your own user")
            del self.users[user_id]

    def add_account(self, owner_id: str, currency: str, account_type: str) -> Account:
        with self._lock:
            if owner_id not in self.users:
                raise StoreError(404, "not_found", "Owner not found")
            account = Account(
                id=str(uuid.uuid4()),
                owner_id=owner_id,
                currency=currency,
                account_type=account_type,
                balance=Decimal("0.00"),
                status="open",
            )
            self.accounts[account.id] = account
            return replace(account)

    def get_account(self, account_id: str) -> Account | None:
        with self._lock:
            account = self.accounts.get(account_id)
            return replace(account) if account else None

    def list_accounts(self, owner_id: str | None = None) -> list[Account]:
        with self._lock:
            items = list(self.accounts.values())
            if owner_id is not None:
                items = [account for account in items if account.owner_id == owner_id]
            return [replace(account) for account in sorted(items, key=lambda item: item.id)]

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        with self._lock:
            txn = self.transactions.get(transaction_id)
            return replace(txn) if txn else None

    def list_transactions(self, owner_id: str | None = None) -> list[Transaction]:
        with self._lock:
            items = list(self.transactions.values())
            if owner_id is not None:
                owned = {
                    account.id
                    for account in self.accounts.values()
                    if account.owner_id == owner_id
                }
                items = [
                    txn
                    for txn in items
                    if txn.account_id in owned or txn.destination_account_id in owned
                ]
            return [replace(txn) for txn in sorted(items, key=lambda item: item.id)]

    def account_owner(self, account_id: str) -> str | None:
        with self._lock:
            account = self.accounts.get(account_id)
            return account.owner_id if account else None

    def apply_transaction(
        self,
        *,
        actor_id: str,
        account_id: str,
        destination_account_id: str | None,
        txn_type: str,
        amount: Decimal,
        idempotency_key: str | None,
    ) -> tuple[Transaction, bool]:
        """Post a ledger entry. Replay is safe when the idempotency key and body match."""
        request_hash = _request_hash(account_id, destination_account_id, txn_type, amount)
        with self._lock:
            if idempotency_key:
                existing = self.idempotency.get((actor_id, idempotency_key))
                if existing is not None:
                    if existing.request_hash != request_hash:
                        raise StoreError(
                            409,
                            "idempotency_conflict",
                            "Idempotency key was already used with a different request",
                        )
                    return replace(self.transactions[existing.transaction_id]), True

            if amount <= 0 or amount > MAX_AMOUNT:
                raise StoreError(
                    422,
                    "invalid_amount",
                    "Amount must be from 0.01 through 1000000.00",
                )

            source = self.accounts.get(account_id)
            if source is None:
                raise StoreError(404, "not_found", "Account not found")
            if source.owner_id != actor_id:
                raise StoreError(403, "forbidden", "Not allowed to use this account")
            if source.status != "open":
                raise StoreError(422, "validation_error", "Account is not open")

            destination: Account | None = None
            if txn_type == "transfer":
                if not destination_account_id:
                    raise StoreError(
                        422,
                        "validation_error",
                        "destination_account_id is required for transfer",
                    )
                if destination_account_id == account_id:
                    raise StoreError(422, "validation_error", "Cannot transfer to the same account")
                destination = self.accounts.get(destination_account_id)
                if destination is None:
                    raise StoreError(404, "not_found", "Destination account not found")

            if txn_type in {"withdraw", "transfer"} and source.balance < amount:
                raise StoreError(422, "insufficient_funds", "Insufficient funds")

            if txn_type == "deposit":
                source.balance += amount
            elif txn_type == "withdraw":
                source.balance -= amount
            elif txn_type == "transfer" and destination is not None:
                source.balance -= amount
                destination.balance += amount
            else:
                raise StoreError(422, "validation_error", "Unsupported transaction type")

            txn = Transaction(
                id=str(uuid.uuid4()),
                account_id=account_id,
                destination_account_id=destination_account_id if txn_type == "transfer" else None,
                type=txn_type,
                amount=amount,
                created_by=actor_id,
            )
            self.transactions[txn.id] = txn
            if idempotency_key:
                self.idempotency[(actor_id, idempotency_key)] = IdempotencyRecord(
                    request_hash=request_hash,
                    transaction_id=txn.id,
                )
            return replace(txn), False


def _request_hash(
    account_id: str,
    destination_account_id: str | None,
    txn_type: str,
    amount: Decimal,
) -> str:
    payload = {
        "account_id": account_id,
        "destination_account_id": destination_account_id,
        "type": txn_type,
        "amount": f"{amount.quantize(Decimal('0.01')):.2f}",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


_STORE = MemoryStore()


def get_store() -> MemoryStore:
    return _STORE
