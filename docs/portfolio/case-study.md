# Case study

## Overview

A reusable API automation framework with a deterministic ledger API. The framework is the product. The API exists so every suite can run on a laptop and in GitHub Actions without an external dependency.

## Problem

API suites often mix URLs, tokens, and assertions inside each test. Logs then store bearer tokens, retries accidentally repeat payments, and parallel runs share one balance and fail at random.

## Approach

Robot suites describe the business case. Python owns the HTTP session, token cache, schema checks, Excel and JSON data, timeout, and retry decision. RequestsLibrary performs the call. Unsafe methods are not retried unless the test marks the call idempotent. Sensitive fields are masked before Robot or the framework logger writes them.

The demo API implements login, users, accounts, and transactions with validation, authorization, pagination, and an idempotency key. State is in memory and starts from a fixed seed.

## Result of the verification run

`python scripts/run_suite.py` on 2026-11-24:

- Pytest: 23 passed, 0 failed
- Robot Framework: 18 passed, 0 failed
- Pabot with 2 processes: 18 passed, 0 failed
- `pip-audit`: no known vulnerabilities
- Secret scan: no high-risk credentials

## Business value

- New API suites start from keywords instead of a new HTTP wrapper.
- Negative and data-driven cases are already shaped for auth, validation, pagination, and money movement.
- CI publishes JUnit, Robot HTML, and Allure results as artifacts.
- Parallel execution is part of the same suite, with isolation rules that keep balances stable.

## Use cases

- Build a regression pack for an internal REST platform.
- Put schema checks on pull requests.
- Standardize masking and retry behavior across QA projects.
- Let non-developers add Excel rows for boundary amounts without editing Python.
