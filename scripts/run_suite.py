"""Run the demo API, pytest, Robot Framework, and pabot. Exit non-zero on any failure."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PYTHON = sys.executable


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["TEST_ENV"] = env.get("TEST_ENV", "local")
    venv_bin = ROOT / ".venv" / "bin"
    if venv_bin.is_dir():
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
    return env


def _run(command: list[str], env: dict[str, str]) -> int:
    print("+", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, env=env)
    return completed.returncode


def _wait_for_health(base_url: str, proc: subprocess.Popen[bytes]) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Demo API exited with code {proc.returncode}")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError("Demo API did not answer /health")


def _start_api(env: dict[str, str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [PYTHON, "-m", "demo_api", "--port", "8000"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _stop_api(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def _robot_counts(path: Path) -> tuple[int, int]:
    root = ET.parse(path).getroot()
    for stat in root.findall("./statistics/total/stat"):
        if (stat.text or "").strip() == "All Tests":
            return int(stat.attrib.get("pass", "0")), int(stat.attrib.get("fail", "0"))
    raise RuntimeError(f"Could not read Robot statistics from {path}")


def _pytest_counts(path: Path) -> tuple[int, int]:
    root = ET.parse(path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise RuntimeError(f"Could not read pytest results from {path}")
    tests = int(suite.attrib.get("tests", "0"))
    failed = int(suite.attrib.get("failures", "0")) + int(suite.attrib.get("errors", "0"))
    skipped = int(suite.attrib.get("skipped", "0"))
    return tests - failed - skipped, failed


def _write_summary(pytest_xml: Path, robot_xml: Path, pabot_xml: Path) -> None:
    pytest_passed, pytest_failed = _pytest_counts(pytest_xml)
    robot_passed, robot_failed = _robot_counts(robot_xml)
    pabot_passed, pabot_failed = _robot_counts(pabot_xml)
    target = ROOT / "docs" / "sample-reports" / "EXECUTION-RESULTS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    target.write_text(
        "\n".join(
            [
                "# Execution results",
                "",
                f"Generated {generated} by `scripts/run_suite.py` from the XML this command wrote.",
                "",
                "| Layer | Passed | Failed | Source |",
                "| --- | ---: | ---: | --- |",
                f"| Pytest unit and integration | {pytest_passed} | {pytest_failed} | `reports/pytest/junit.xml` |",
                f"| Robot Framework | {robot_passed} | {robot_failed} | `reports/robot/output.xml` |",
                f"| Pabot (2 processes) | {pabot_passed} | {pabot_failed} | `reports/robot-pabot/output.xml` |",
                "",
                "Robot HTML report: `reports/robot/report.html`.",
                "Robot log: `reports/robot/log.html`.",
                "Allure result files: `reports/allure-results` and `reports/allure-results-pabot`.",
                "",
                "These numbers are copied from the XML attributes `pass`, `fail`, `tests`, `failures`, and `errors`.",
                "They are not hand-written.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(target.read_text(encoding="utf-8"))


def main() -> int:
    env = _env()
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "pytest").mkdir(parents=True, exist_ok=True)
    codes = [
        _run([PYTHON, "scripts/scan_secrets.py"], env),
        _run(
            [
                PYTHON,
                "-m",
                "pytest",
                "tests/unit",
                "tests/integration",
                "--junitxml=reports/pytest/junit.xml",
            ],
            env,
        ),
    ]
    proc: subprocess.Popen[bytes] | None = None
    try:
        proc = _start_api(env)
        _wait_for_health("http://127.0.0.1:8000", proc)
        codes.append(
            _run(
                [
                    "robot",
                    "--listener",
                    "allure_robotframework:reports/allure-results",
                    "-d",
                    "reports/robot",
                    "tests/robot",
                ],
                env,
            )
        )
        codes.append(
            _run(
                [
                    "pabot",
                    "--processes",
                    "2",
                    "--no-pabotlib",
                    "--listener",
                    "allure_robotframework:reports/allure-results-pabot",
                    "-d",
                    "reports/robot-pabot",
                    "tests/robot",
                ],
                env,
            )
        )
    finally:
        _stop_api(proc)
    if all(code == 0 for code in codes):
        _write_summary(
            REPORTS / "pytest" / "junit.xml",
            REPORTS / "robot" / "output.xml",
            REPORTS / "robot-pabot" / "output.xml",
        )
    else:
        print("One or more commands failed:", codes)
    return 0 if all(code == 0 for code in codes) else 1


if __name__ == "__main__":
    sys.exit(main())
