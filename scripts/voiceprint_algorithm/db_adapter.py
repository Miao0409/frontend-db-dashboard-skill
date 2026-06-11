"""Dry-run friendly wrappers around the frontend-db-dashboard skill scripts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SKILL_QUERY_SCRIPT = Path(__file__).resolve().parents[1] / "query_frontend_data.py"


def pending(limit: int = 20) -> int:
    return subprocess.call([sys.executable, str(SKILL_QUERY_SCRIPT), "pending-for-inference", "--limit", str(limit)])


def submit(result_json: str | Path, commit: bool = False, target_db: str = "cable") -> int:
    submit_command = "submit-cable-result" if target_db == "cable" else "submit-result"
    command = [sys.executable, str(SKILL_QUERY_SCRIPT), submit_command, str(result_json)]
    if commit:
        command.append("--commit")
    return subprocess.call(command)


def main() -> None:
    parser = argparse.ArgumentParser(description="Database integration helper for algorithm demo.")
    sub = parser.add_subparsers(dest="command", required=True)
    pending_parser = sub.add_parser("pending")
    pending_parser.add_argument("--limit", type=int, default=20)
    submit_parser = sub.add_parser("submit")
    submit_parser.add_argument("result_json")
    submit_parser.add_argument("--commit", action="store_true")
    submit_parser.add_argument("--target-db", choices=["cable", "legacy"], default="cable")
    args = parser.parse_args()

    if args.command == "pending":
        raise SystemExit(pending(args.limit))
    raise SystemExit(submit(args.result_json, args.commit, args.target_db))


if __name__ == "__main__":
    main()
