# Installation

Use Python 3.13. The suite was executed with Python 3.13.2. GitHub Actions uses Python 3.13 as well.

## macOS and Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/run_suite.py
```

## Windows PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
python scripts/run_suite.py
```

The runner looks for `.venv` and puts it on `PATH` when that directory exists. Activate the environment anyway so `robot` and `pabot` resolve to the same interpreter.

No database, Docker, or external API key is required. The demo API listens on `127.0.0.1:8000` during Robot execution. Stop anything else already bound to that port before `scripts/run_suite.py`.

Optional: install the [Allure command line](https://allurereport.org/docs/install/) if you want an Allure HTML dashboard. The framework still writes Allure result files without it.
