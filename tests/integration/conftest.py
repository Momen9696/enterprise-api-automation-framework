"""Pytest fixtures that boot an isolated demo API process."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from framework.core.config_loader import EnvironmentConfig, load_config
from framework.core.http_client import HttpClient
from framework.core.transport import RequestsLibraryTransport

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_ready(base_url: str, proc: subprocess.Popen[bytes]) -> None:
    deadline = time.time() + 20
    last_error = "not started"
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Demo API exited early with code {proc.returncode}")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc)
            time.sleep(0.2)
    raise RuntimeError(f"Demo API did not become ready: {last_error}")


def start_demo_api(port: int, *, allow_reset: bool = True) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["DEMO_ALLOW_RESET"] = "true" if allow_reset else "false"
    return subprocess.Popen(
        [sys.executable, "-m", "demo_api", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="session")
def base_url() -> Iterator[str]:
    port = _free_port()
    proc = start_demo_api(port)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_ready(url, proc)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture
def api(base_url: str) -> tuple[HttpClient, EnvironmentConfig]:
    config = load_config(base_url=base_url)
    client = HttpClient(
        config,
        RequestsLibraryTransport(config.base_url, config.timeout_seconds),
        sleeper=lambda _seconds: None,
    )
    reset = client.post("/test/reset", idempotent=True)
    assert reset.status == 204, reset.text
    return client, config
