# Phase 1 — Architecture

## Enterprise API Automation Framework

Status: architecture approved for implementation after explicit go-ahead.  
Scope: local, self-contained portfolio project. Synthetic data only. No external APIs.

---

## 1. Problem and outcome

Build a reusable REST API automation framework that a senior QA automation engineer would put in front of a client:

- Robot Framework suites express business scenarios.
- Python owns HTTP, auth, validation, data, logging, and retry behavior.
- A local FastAPI demo API is the system under test so every run is deterministic.
- Pytest proves the Python framework itself.
- GitHub Actions runs both layers and publishes reports.

The demo API is a banking-style sandbox (users, accounts, transactions). It is not a production banking system. Balances, tokens, and “card” fields are synthetic.

---

## 2. Architectural decisions

| ID | Decision | Why |
| --- | --- | --- |
| AD-1 | Split **framework core** (pure Python) from **Robot keyword libraries** and **`.resource` files**. | Core stays unit-testable. Suites stay readable. Nothing lives in one file. |
| AD-2 | HTTP goes through one `HttpClient` that uses `requests`. Robot keywords call that client. `RequestsLibrary` is a thin session adapter used by the same client, so the required library is real and sessions are shared. | One retry, timeout, logging, and masking path. Suites cannot bypass it. |
| AD-3 | Retry is opt-in and method-aware. Default: retry `GET`, `HEAD`, and `429`/`503`/connection errors only. `POST` retries only when the caller sets `idempotent=True` (transaction create with `Idempotency-Key`). | Safe retries are a requirement. Blind POST retry would double-charge in a real system. |
| AD-4 | Environments are YAML profiles (`local`, `staging`) selected by `TEST_ENV`. Secrets are not used. Demo usernames and passwords live in config and are labeled synthetic. | Multiple environments without a secret store. |
| AD-5 | Auth is a token manager: login once per suite (or on 401), cache bearer token, attach `Authorization`. Negative cases inject invalid, missing, or wrong-role tokens explicitly. | Dynamic auth without hiding negative tests. |
| AD-6 | The demo API keeps state in memory and resets from a fixed seed on startup and via `POST /test/reset`. | Deterministic runs. No database to install. |
| AD-7 | Parallelism uses `pabot` at **suite** level, with each suite owning its own user and account prefix. Shared mutable accounts are not used across suites. | Parallel support without flaky balance races. |
| AD-8 | Reports: Robot `log.html` / `output.xml`, Allure results from `allure-robotframework` and `allure-pytest`. CI uploads those directories as artifacts. The Allure HTML report is generated when the Allure CLI is present; results are always produced. | Detailed reports even when the Allure CLI is absent on a laptop. |
| AD-9 | Data-driven cases load from JSON and `.xlsx`. Generators fill unique emails, idempotency keys, and amounts. Schemas live beside the contract, not inside tests. | Excel and JSON are both required. Tests stay free of hard-coded payloads. |
| AD-10 | Masking runs before any log line is written. Keys: `password`, `token`, `access_token`, `authorization`, `secret`, `card_number`, `cvv`. | Request/response logging without leaking demo credentials into reports. |

---

## 3. Logical architecture

```text
                    +---------------------------+
                    |   GitHub Actions CI       |
                    |   pytest + robot + pabot  |
                    +-------------+-------------+
                                  |
          +-----------------------+------------------------+
          |                                                |
          v                                                v
+-------------------+                            +----------------------+
|  Pytest           |                            |  Robot Framework     |
|  unit + client    |                            |  suites (.robot)     |
|  integration      |                            |  resources (.resource)|
+---------+---------+                            +----------+-----------+
          |                                                 |
          |                                         keyword libraries
          v                                                 v
+-------------------------------------------------------------------+
|                     Framework core (Python)                       |
|  config | auth | http client | retry | schema | json | masking    |
|  excel/json loader | data generator | logging                      |
+-------------------------------+-----------------------------------+
                                |
                                | HTTP (localhost)
                                v
+-------------------------------------------------------------------+
|                     Demo API (FastAPI)                            |
|  auth | users | accounts | transactions | pagination | errors     |
|  in-memory store, seeded, reset endpoint                          |
+-------------------------------------------------------------------+
```

Dependency rule: Robot suites depend on resources. Resources depend on keyword libraries. Keyword libraries depend on core. Core does not import Robot or FastAPI. The demo API does not import the framework. Pytest may import core and may call the demo API over HTTP.

---

## 4. Folder structure

Repository root (published as its own public GitHub repo):

```text
01-enterprise-api-automation/
├── README.md
├── requirements.txt
├── pytest.ini
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── config/
│   ├── logging.yaml
│   └── environments/
│       ├── local.yaml
│       └── staging.yaml          # same API shape, different base URL / users
├── demo_api/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app factory + uvicorn entry
│   ├── dependencies.py           # auth dependency, role checks
│   ├── errors.py                 # consistent error body
│   ├── models.py                 # pydantic request/response models
│   ├── store.py                  # seeded in-memory store
│   └── routers/
│       ├── auth.py
│       ├── users.py
│       ├── accounts.py
│       ├── transactions.py
│       └── health.py
├── framework/
│   ├── __init__.py
│   ├── core/
│   │   ├── config_loader.py
│   │   ├── auth_manager.py
│   │   ├── http_client.py
│   │   ├── retry_policy.py
│   │   ├── header_builder.py
│   │   ├── response_validator.py
│   │   ├── schema_validator.py
│   │   ├── masking.py
│   │   ├── data_loader.py        # json + xlsx
│   │   ├── data_generator.py
│   │   ├── logger.py
│   │   └── exceptions.py
│   └── robot_libs/
│       ├── api_keywords.py       # GET POST PUT PATCH DELETE
│       ├── auth_keywords.py
│       ├── validation_keywords.py
│       └── data_keywords.py
├── resources/
│   ├── common.resource
│   ├── auth.resource
│   ├── users.resource
│   ├── accounts.resource
│   └── transactions.resource
├── schemas/
│   ├── error.schema.json
│   ├── token.schema.json
│   ├── user.schema.json
│   ├── account.schema.json
│   ├── transaction.schema.json
│   └── page.schema.json
├── test_data/
│   ├── json/
│   │   ├── users.json
│   │   ├── accounts.json
│   │   └── transactions.json
│   └── excel/
│       └── api_cases.xlsx        # sheets: users, accounts, transactions, negative
├── tests/
│   ├── unit/                     # pytest, no server
│   │   ├── test_config_loader.py
│   │   ├── test_masking.py
│   │   ├── test_retry_policy.py
│   │   ├── test_schema_validator.py
│   │   ├── test_response_validator.py
│   │   ├── test_data_loader.py
│   │   └── test_data_generator.py
│   ├── integration/              # pytest against live demo API
│   │   ├── conftest.py           # starts uvicorn on a free port
│   │   ├── test_auth_flow.py
│   │   ├── test_accounts_flow.py
│   │   └── test_transactions_flow.py
│   └── robot/
│       ├── api_positive.robot
│       ├── api_negative.robot
│       ├── api_data_driven.robot
│       └── api_transactions.robot
├── scripts/
│   ├── run_demo_api.py
│   └── run_suite.py              # env, reports dir, optional pabot
└── docs/
    ├── PHASE1-ARCHITECTURE.md
    ├── installation.md
    ├── execution.md
    ├── demo-recording.md
    ├── architecture.mmd
    └── portfolio/
        ├── overview.md
        ├── case-study.md
        ├── upwork-description.md
        └── service-offerings.md
```

Generated output (gitignored): `reports/robot/`, `reports/allure-results/`, `reports/pytest/`.

A short sample of a real run (JUnit XML summary plus a redacted log excerpt) is copied into `docs/sample-reports/` only after tests have actually been executed. Those files are evidence, not fixtures that fake a pass.

---

## 5. Component responsibilities

### Demo API

| Piece | Responsibility |
| --- | --- |
| `main.py` | App factory, router mount, seed on startup. |
| `store.py` | Users, accounts, transactions, idempotency map. Thread-safe enough for pabot (a lock around mutations). |
| `routers/auth.py` | `POST /auth/login` returns a signed JWT. `POST /auth/logout` is a no-op success for suite cleanup. |
| `routers/users.py` | CRUD-style: create, get, list with pagination, patch. Role: admin can list; a user can read self. |
| `routers/accounts.py` | Open account, get account, list by owner. Customer role cannot read another customer’s account. |
| `routers/transactions.py` | Deposit, withdraw, transfer. `Idempotency-Key` replays the original result. Insufficient funds, zero, and negative amounts return 422. |
| `errors.py` | One error shape: `code`, `message`, `details`. 400, 401, 403, 404, 405, 409, 422. |
| `POST /test/reset` | Test-only. Restores the seed. Disabled when `DEMO_ALLOW_RESET=false`. |

Seed (synthetic):

- Admin: `admin@demo.local` / `AdminPass123!`
- Customer: `customer@demo.local` / `CustomerPass123!`
- One checking account with balance `1000.00` and currency `USD`.

Pagination: `page` (1-based) and `page_size` (1–100). Response envelope: `items`, `page`, `page_size`, `total`.

Idempotency: same key + same user returns the original transaction and does not move money twice. Same key + different body returns 409.

Invalid method: `POST /health` and `DELETE /auth/login` return 405 with the error schema.

### Framework core

| Module | Responsibility |
| --- | --- |
| `config_loader.py` | Load `config/environments/{TEST_ENV}.yaml`. Expose base URL, timeouts, retry, users. Fail fast on a missing profile. |
| `auth_manager.py` | Login, cache token, `auth_headers()`, `clear()`. Accept an override token for negative tests. |
| `http_client.py` | `get/post/put/patch/delete`. Apply timeout, headers, json body, retry policy, log masked request and response. Return a small `ApiResponse` (status, json, text, headers, elapsed). |
| `retry_policy.py` | Decide retry from method, status, exception, and `idempotent` flag. Linear backoff capped by config. |
| `header_builder.py` | Merge default headers, auth, correlation id, idempotency key. |
| `response_validator.py` | Status code, JSON body, field equality, field presence, type checks. |
| `schema_validator.py` | `jsonschema` Draft 2020-12 against files in `schemas/`. |
| `masking.py` | Recursive redaction of sensitive keys and `Authorization` values. |
| `data_loader.py` | Read JSON files and Excel sheets to a list of dicts. |
| `data_generator.py` | Unique email, UUID idempotency key, decimal amount inside a caller-supplied range. |
| `logger.py` | Logger named `framework`. No credentials in format string. |
| `exceptions.py` | `ConfigError`, `AuthError`, `SchemaValidationError`, `ResponseValidationError`, `TransportError`. |

### Robot layer

Keyword libraries are thin. They convert Robot scalars into core calls and return dictionaries Robot can assert on.

Resource files group keywords by domain (`Login As Customer`, `Create Account`, `Transfer Funds`, `Response Should Match Schema`). Suites contain scenarios and documentation, not HTTP details.

### Tests

| Layer | What it proves |
| --- | --- |
| Unit | Masking, retry decisions, schema failures, Excel/JSON loading, config errors, generators. No network. |
| Integration | Client against the real demo API: login, forbidden account read, transfer, duplicate idempotency key, pagination, 405. |
| Robot | The suite a client would read: positive, negative, data-driven Excel/JSON, transaction rules. |

Robot coverage (mapped to the required scenarios):

| Scenario | Where |
| --- | --- |
| Successful GET/POST/PUT/PATCH/DELETE | `api_positive.robot` |
| Invalid authentication | `api_negative.robot` |
| Unauthorized (valid user, wrong resource) | `api_negative.robot` |
| Invalid payload, missing field, wrong type | `api_negative.robot` + data file |
| Unknown id | `api_negative.robot` |
| Boundary amounts (0, negative, over balance, max page size) | `api_transactions.robot` + Excel |
| Wrong HTTP method | `api_negative.robot` |
| Schema mismatch (asserted on a deliberately bad fixture in unit tests; live responses must match schema) | unit + every happy-path Robot case |
| Empty page | `api_positive.robot` (page far past `total`) |
| Pagination | `api_positive.robot` |
| Duplicate transaction / idempotency | `api_transactions.robot` |

---

## 6. Configuration

`config/environments/local.yaml` (shape):

```yaml
name: local
base_url: http://127.0.0.1:8000
timeout_seconds: 10
retry:
  max_attempts: 3
  backoff_seconds: 0.2
  retry_statuses: [429, 503]
users:
  admin:
    email: admin@demo.local
    password: AdminPass123!
  customer:
    email: customer@demo.local
    password: CustomerPass123!
```

`staging.yaml` uses the same contract with a different `base_url` so the loader and header path are proven against two profiles. Default CI and local runs use `local` only. Staging is not a live host.

Selection: environment variable `TEST_ENV`, default `local`.

Timeouts and retry counts are read only from the profile. Keywords may override timeout per call for a slow-path example; they may not hard-code a second global default.

---

## 7. Dependencies

Pinned in `requirements.txt` at implementation time to current compatible releases:

| Package | Use |
| --- | --- |
| `robotframework` | Suites and resources |
| `robotframework-requests` | Session adapter inside `HttpClient` |
| `robotframework-pabot` | Parallel suite execution |
| `robotframework-jsonlibrary` | JSON file variables where a keyword is clearer than Python |
| `requests` | HTTP |
| `jsonschema` | Contract checks |
| `openpyxl` | Excel data |
| `PyYAML` | Environment files |
| `fastapi` | Demo API |
| `uvicorn` | Demo API process |
| `pydantic` | Demo API models (pulled in by FastAPI) |
| `PyJWT` | Demo API tokens |
| `pytest` | Framework tests |
| `allure-pytest` | Unit/integration Allure results |
| `allure-robotframework` | Suite Allure results |

Standard library covers logging, dataclasses, pathlib, uuid, and decimal. No database, no cloud SDK, no private package index.

Dev-only scanner (not imported by tests): `pip-audit` run in CI and locally during Phase 4.

---

## 8. Demo API contract (implementation target)

| Method | Path | Auth | Success | Notable failures |
| --- | --- | --- | --- | --- |
| POST | `/auth/login` | no | 200 token | 401 bad credentials, 422 missing field |
| GET | `/users` | admin | 200 page | 403 customer |
| POST | `/users` | admin | 201 user | 409 duplicate email, 422 |
| GET | `/users/{id}` | self or admin | 200 | 404, 403 |
| PATCH | `/users/{id}` | self or admin | 200 | 422 |
| DELETE | `/users/{id}` | admin | 204 | 403, 404 |
| POST | `/accounts` | customer or admin | 201 | 422 |
| GET | `/accounts/{id}` | owner or admin | 200 | 403, 404 |
| GET | `/accounts` | bearer | 200 page of own accounts; admin sees all | 401 |
| POST | `/transactions` | owner | 201 | 422 insufficient/invalid amount, 409 idempotency conflict |
| GET | `/transactions` | bearer | 200 page | 401 |
| GET | `/transactions/{id}` | owner or admin | 200 | 404, 403 |
| GET | `/health` | no | 200 | — |
| POST | `/health` | no | 405 | method not allowed |
| POST | `/test/reset` | no, test flag | 204 | 404 when reset disabled |

Transaction body: `account_id`, `type` (`deposit` | `withdraw` | `transfer`), `amount` (string decimal), `destination_account_id` required for transfer, optional `Idempotency-Key` header.

Money uses `decimal` quantized to `0.01`. No floats.

---

## 9. CI/CD (planned)

`.github/workflows/ci.yml` on `push` and `pull_request`:

1. Python 3.12 on `ubuntu-latest`.
2. Install `requirements.txt`.
3. `pip-audit -r requirements.txt` (fail on known critical vulnerabilities; high findings fixed or documented with a reason).
4. Secret scan: `gitleaks` if available, otherwise a grep gate for private-key blocks and common token prefixes. Demo passwords in YAML are an allowlisted fixture file.
5. Start demo API, wait on `/health`.
6. `pytest tests/unit tests/integration --junitxml=reports/pytest/junit.xml`.
7. `robot --listener allure_robotframework:reports/allure-results -d reports/robot tests/robot`.
8. `pabot --processes 2` on the robot folder as a second job step to prove parallel execution. Suites must pass both serial and parallel.
9. Upload `reports/` as an artifact even when tests fail.

Workflow validity in Phase 5: `actionlint` if installed, plus a local `act` run only when `act` exists. If neither is available, validate YAML structure and run the same commands CI runs, then state that the GitHub-hosted workflow itself has not executed until the first push.

---

## 10. Implementation roadmap

Work stays inside this order. Each step ends with something executable.

| Step | Work | Done when |
| --- | --- | --- |
| 2.1 | Package skeleton, `requirements.txt`, `.gitignore`, config loader, exceptions, logging, masking | Unit tests for config and masking pass |
| 2.2 | Demo API: store, auth, errors, health, users | Login and 401 observable via curl or pytest |
| 2.3 | Accounts, transactions, pagination, idempotency, 405 | Contract table covered by integration tests |
| 2.4 | HTTP client, retry, headers, auth manager | Unit tests for retry decisions; integration tests through the client |
| 2.5 | Schema + response validators, JSON and Excel loaders, generator | Unit tests including a bad schema and a missing column |
| 2.6 | Robot keyword libraries, resources, four suites, sample Excel/JSON, schemas | `robot tests/robot` passes against the demo API |
| 2.7 | `pabot` run, script entrypoints | Parallel run passes |
| 2.8 | Allure listeners wired; one real report directory produced | Artifacts exist on disk from that run |
| 3.x | Fill gaps from the scenario table; fix failures; keep JUnit and Robot output | All required scenarios exist and pass |
| 4.x | Review, `pip-audit`, secret scan, doc check | No open critical/high issues |
| 5.x | GitHub Actions workflow; run the CI command list locally | Workflow file matches the commands that passed |
| 6.x | New public GitHub repo via `gh`, commit, push, verify the remote commit | URL and commit SHA recorded. Stop if `gh` is not authenticated |
| 7.x | README, diagram, guides, case study, Upwork text, sample report excerpt from the real run | Docs match the commands just executed |

---

## 11. Acceptance criteria

The project is complete only when every row is true and evidenced by a command that was run.

1. `GET`, `POST`, `PUT`, `PATCH`, and `DELETE` are exposed as keywords and succeed against the demo API.
2. A suite logs in, reuses a token, and a second case fails closed with a bad token.
3. `TEST_ENV=local` and a load of `staging.yaml` both resolve through the config loader. The live suite runs against `local`.
4. Headers and JSON bodies are built by the framework, including correlation id and idempotency key.
5. Happy-path responses pass status, field, and JSON Schema checks.
6. Negative cases assert status and error-schema: bad login, forbidden account, missing field, wrong type, unknown id, amount `0`, negative amount, amount above balance, wrong method, empty page.
7. At least one Excel sheet and one JSON file drive more than one Robot iteration each.
8. Generator-created email and idempotency key are used in a create-user or create-transaction case.
9. Logs show the request and response with `password` and `authorization` replaced by `***`.
10. Timeout is read from YAML. A unit test proves retry happens for a configured status on `GET` and does not happen for a normal `POST`.
11. `pabot --processes 2` finishes with the same pass result as a serial `robot` run.
12. Pytest and Robot reports are files produced by those commands, and the counts in the README match those files.
13. `pip-audit` and the secret scan have been run. Findings at critical or high are fixed.
14. CI workflow runs tests on push and pull_request and uploads `reports/`.
15. The public GitHub repository exists, the pushed SHA matches local `HEAD`, and a fresh clone list shows the project files.
16. Portfolio docs (overview, business value, Upwork description, service offerings, install, execution, recording steps, diagram) describe this repository only.

---

## 12. Risks and controls

| Risk | Control |
| --- | --- |
| Suites call `requests` directly and skip masking or retry | Keyword layer is the only HTTP entry Robot uses. Review checks for raw `Create Session` in suites. |
| Parallel tests share one balance and flake | Each suite creates its own user and account. Seed customer is read-only for auth negative tests. |
| In-memory API resets when the process dies | CI starts one server and runs pytest integration and Robot against it. `/test/reset` is for local reruns. |
| POST retry double-applies a transfer | Retry policy refuses unsafe methods unless `idempotent=True`. Covered by a unit test. |
| Demo passwords look like a leaked secret | Values are obvious fixtures. Secret scan allowlists `config/environments/*.yaml` only. README states they are synthetic. |
| Allure CLI missing locally or in CI | Listeners still write `allure-results`. HTML generation is best-effort. Robot HTML log is the required readable report. |
| Excel binary is hard to review | Sheet layout is documented in `docs/execution.md`. A JSON twin of the same cases exists so diffs stay readable. |
| `gh` is logged out or the repo name is taken | Phase 6 stops. No force-push, no delete, no “published” claim. Pick a new name if the check shows the repo exists. |
| Scope creep (UI, database, real bank APIs) | Out of scope until this project’s quality gates pass. |
| Token library vulnerability | `pip-audit` in Phase 4; pin versions. |

---

## 13. Out of scope

- Real payment networks, real PII, production credentials.
- Performance or load testing.
- Contract tests against a third-party public API.
- A web dashboard beyond Allure and Robot HTML logs.
- Docker, unless CI cannot install Python dependencies without it. It can.

---

## 14. Phase 1 exit

Architecture, structure, responsibilities, dependencies, roadmap, acceptance criteria, and risks are defined. Implementation starts only after the next instruction.
