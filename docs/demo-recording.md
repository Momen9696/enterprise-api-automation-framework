# Recording a demo

Capture the run that just happened. Do not stage a second edited log.

## Terminal

1. Open a terminal at the repository root.
2. Activate `.venv`.
3. Start a screen recording.
4. Run `python scripts/run_suite.py`.
5. Leave the Pytest summary and the Robot `18 tests, 18 passed` lines on screen.
6. Stop the recording after the script prints the execution table.

## Robot report

1. Open `reports/robot/report.html`.
2. Show the summary: 18 passed, 0 failed.
3. Open `log.html`, expand `Transfer Is Idempotent And A Different Body Conflicts`, and show the 201, the 200 replay, and the 409 conflict.
4. Search the log for `AdminPass`, `ValidPass`, and `eyJ`. The search should find nothing. That is the masking check.

## API

With `python -m demo_api --port 8000` running, open `http://127.0.0.1:8000/docs` and show login, accounts, and transactions. Use only the synthetic users from the README.

## Suggested length

Two to four minutes. Show one positive user flow, one 401, one insufficient-funds response, and the idempotent replay. End on the CI workflow file and the green local summary.
