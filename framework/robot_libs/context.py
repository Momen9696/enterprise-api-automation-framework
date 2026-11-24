"""Process-local framework handle shared by Robot keyword libraries."""

from __future__ import annotations

from dataclasses import dataclass

from framework.core.auth_manager import AuthManager
from framework.core.config_loader import EnvironmentConfig, load_config
from framework.core.exceptions import ConfigError
from framework.core.http_client import HttpClient
from framework.core.transport import RequestsLibraryTransport


@dataclass
class Runtime:
    config: EnvironmentConfig
    client: HttpClient
    auth: AuthManager


_runtime: Runtime | None = None


def initialize_runtime() -> Runtime:
    global _runtime
    config = load_config()
    client = HttpClient(config, RequestsLibraryTransport(config.base_url, config.timeout_seconds))
    _runtime = Runtime(config=config, client=client, auth=AuthManager(client, config.users))
    return _runtime


def runtime() -> Runtime:
    if _runtime is None:
        raise ConfigError("Framework is not initialized. Run the suite setup keyword first.")
    return _runtime


def as_bool(value: object, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() not in {"false", "0", "no", "none"}
