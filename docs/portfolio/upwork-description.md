# Upwork portfolio description

**Enterprise API Automation Framework (Robot Framework + Python)**

I designed and built a reusable REST API automation framework for ledger-style services. Robot Framework suites cover auth, users, accounts, and transactions. A Python core provides GET, POST, PUT, PATCH, and DELETE, bearer-token management, JSON and JSON Schema checks, Excel and JSON data-driven runs, dynamic test data, timeouts, and safe retries. Passwords and tokens are masked in framework logs and in RequestsLibrary log lines.

The system under test is a local FastAPI application with synthetic users and balances, so the suite does not depend on a public API. It includes authorization, validation errors, pagination, insufficient funds, duplicate debits, and idempotency keys.

Verification on the published code:

- 23 Pytest unit and integration tests passed
- 18 Robot Framework tests passed
- The same 18 tests passed again under pabot with 2 processes
- pip-audit reported no known vulnerabilities
- GitHub Actions installs dependencies, runs the suite, and uploads the reports

The framework is structured so a new service can reuse the client, keywords, and CI workflow by changing the base URL, schemas, and test data.

**Skills:** Python, Robot Framework, RequestsLibrary, Pytest, FastAPI, JSON Schema, GitHub Actions, API test automation, CI reporting
