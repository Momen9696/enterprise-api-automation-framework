"""Fail if high-risk secrets are present. Demo fixture passwords are not tokens."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "reports",
    ".pabot_results",
    "pabot_results",
}
SKIP_SUFFIXES = {".xlsx", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pyc", ".whl", ".zip"}
PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("aws access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("github fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("live stripe key", re.compile(r"sk_live_[A-Za-z0-9]{10,}")),
)


def gitignore_covers_sensitive_files(root: Path = ROOT) -> list[str]:
    path = root / ".gitignore"
    if not path.is_file():
        return [".gitignore is missing"]
    text = path.read_text(encoding="utf-8")
    missing = []
    for required in (".env", ".venv/", "reports/"):
        if required not in text:
            missing.append(f".gitignore does not exclude {required}")
    return missing


def scan_text(text: str) -> list[str]:
    return [name for name, pattern in PATTERNS if pattern.search(text)]


def scan_tree(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    findings.extend(gitignore_covers_sensitive_files(root))
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name in scan_text(text):
            findings.append(f"{path.relative_to(root)}: {name}")
    return findings


def main() -> int:
    findings = scan_tree()
    if findings:
        print("Secret scan failed:")
        for finding in findings:
            print(f"  {finding}")
        return 1
    print("Secret scan passed. No high-risk credentials found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
