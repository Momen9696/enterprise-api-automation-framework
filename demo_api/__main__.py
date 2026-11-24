"""Run the demo API: python -m demo_api --port 8000"""

from __future__ import annotations

import argparse

import uvicorn

from demo_api.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the synthetic ledger API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
