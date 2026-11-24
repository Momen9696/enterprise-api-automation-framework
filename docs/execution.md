# Execution

Run every gate from the repository root:

```bash
source .venv/bin/activate
python scripts/run_suite.py
```

Exit code 0 means the secret scan, Pytest, Robot Framework, and pabot all passed. The script then rewrites `docs/sample-reports/EXECUTION-RESULTS.md` from `reports/pytest/junit.xml`, `reports/robot/output.xml`, and `reports/robot-pabot/output.xml`.

## What the runner does

1. `python scripts/scan_secrets.py`
2. `pytest tests/unit tests/integration --junitxml=reports/pytest/junit.xml`
3. `python -m demo_api --port 8000`
4. `robot --listener allure_robotframework:reports/allure-results -d reports/robot tests/robot`
5. `pabot --processes 2 --no-pabotlib --listener allure_robotframework:reports/allure-results-pabot -d reports/robot-pabot tests/robot`
6. Stops the demo API.

Pytest integration starts a second API on a free port, resets it before each test, and does not use port 8000. Robot uses the server on port 8000 and does not call reset, so parallel suites stay isolated by creating their own users.

## Environment

```bash
export TEST_ENV=local
export PYTHONPATH="$PWD"
```

`TEST_ENV=staging` loads `config/environments/staging.yaml`. Do not point Robot at it unless something is listening on that base URL. The unit test `test_profiles_load` reads the file without opening a connection.

Rebuild the Excel workbook after editing `scripts/build_workbook.py`:

```bash
python scripts/build_workbook.py
```

Sheets:

| Sheet | Columns | Used by |
| --- | --- | --- |
| `users` | full_name, password_mode, role, expected_status, expected_code | `Run User Row` |
| `accounts` | full_name, account_type, currency, expected_status, expected_code | `Run Account Row` |
| `boundaries` | case_id, type, amount, expected_status, expected_code | `Run Amount Row` |

`password_mode` is `valid`, `short`, or `empty`. The real fixture password stays in Python.

## Reports

Open `reports/robot/report.html` in a browser after a run. The log is `reports/robot/log.html`. Failed keywords show the response status and body. Tokens and passwords are masked before they are written.

Allure result directories:

- `reports/allure-results` from Pytest and the serial Robot run
- `reports/allure-results-pabot` from pabot

When the Allure CLI is installed:

```bash
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report
```

## Quality commands used before publishing

```bash
pip-audit -r requirements.txt
python scripts/scan_secrets.py
python scripts/run_suite.py
```

`pip-audit` must report no known vulnerabilities. The secret scan fails on private keys, cloud tokens, and live secret-key prefixes. It does not treat the documented demo passwords as secrets. `.gitignore` excludes `.env`, `.venv/`, and `reports/`.
