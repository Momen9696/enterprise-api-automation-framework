"""Load YAML environment profiles. Credentials in these files are synthetic fixtures."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from framework.core.exceptions import ConfigError


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RetrySettings:
    max_attempts: int
    backoff_seconds: float
    retry_statuses: tuple[int, ...]


@dataclass(frozen=True)
class UserCredential:
    email: str
    password: str


@dataclass(frozen=True)
class EnvironmentConfig:
    name: str
    base_url: str
    timeout_seconds: float
    retry: RetrySettings
    users: dict[str, UserCredential]


def load_config(env_name: str | None = None, base_url: str | None = None) -> EnvironmentConfig:
    selected = env_name or os.getenv("TEST_ENV", "local")
    path = project_root() / "config" / "environments" / f"{selected}.yaml"
    if not path.is_file():
        raise ConfigError(f"Environment profile not found: {selected}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError(f"Environment profile must be a mapping: {path}")
    try:
        retry_raw: dict[str, Any] = raw["retry"]
        users_raw: dict[str, Any] = raw["users"]
        retry = RetrySettings(
            max_attempts=int(retry_raw["max_attempts"]),
            backoff_seconds=float(retry_raw["backoff_seconds"]),
            retry_statuses=tuple(int(code) for code in retry_raw["retry_statuses"]),
        )
        users = {
            role: UserCredential(email=str(value["email"]), password=str(value["password"]))
            for role, value in users_raw.items()
        }
        resolved_url = base_url or str(raw["base_url"])
        return EnvironmentConfig(
            name=str(raw.get("name", selected)),
            base_url=resolved_url.rstrip("/"),
            timeout_seconds=float(raw["timeout_seconds"]),
            retry=retry,
            users=users,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid environment profile {path.name}: {exc}") from exc
