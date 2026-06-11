"""Unified CLI for the bundled cable voiceprint demo algorithm.

This script intentionally stays thin: it exposes training, inference, pending
JSON inference, and database submission while keeping the reusable algorithm
code in the ``voiceprint_algorithm`` package next to this file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from voiceprint_algorithm.infer import infer_one, infer_pending_records
from voiceprint_algorithm.model import discover_dataset, save_model, train_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Cable voiceprint demo algorithm tools.")
    sub = parser.add_subparsers(dest="command", required=True)

    train_parser = sub.add_parser("train", help="Train the 9-class lightweight demo classifier.")
    train_parser.add_argument("--data-dir", required=True)
    train_parser.add_argument("--model-dir", required=True)
    train_parser.add_argument("--max-per-class", type=int, default=None)
    train_parser.add_argument("--test-size", type=float, default=0.2)
    train_parser.add_argument("--random-state", type=int, default=42)

    infer_parser = sub.add_parser("infer-one", help="Infer one local wav and write submit-result JSON.")
    infer_parser.add_argument("--audio", required=True)
    infer_parser.add_argument("--sample-uid", required=True)
    infer_parser.add_argument("--model-dir", required=True)
    infer_parser.add_argument("--output-dir", required=True)
    infer_parser.add_argument("--result-json", required=True)
    infer_parser.add_argument("--topk", type=int, default=3)
    infer_parser.add_argument("--review-threshold", type=float, default=0.75)

    pending_parser = sub.add_parser("infer-pending", help="Infer a pending-for-inference JSON payload.")
    pending_parser.add_argument("--pending-json", required=True)
    pending_parser.add_argument("--model-dir", required=True)
    pending_parser.add_argument("--output-dir", required=True)
    pending_parser.add_argument("--result-json", required=True)
    pending_parser.add_argument("--topk", type=int, default=3)
    pending_parser.add_argument("--review-threshold", type=float, default=0.75)

    fetch_parser = sub.add_parser("fetch-pending", help="Fetch pending samples from the database.")
    fetch_parser.add_argument("--limit", type=int, default=20)
    fetch_parser.add_argument("--output", required=True)

    submit_parser = sub.add_parser("submit-result", help="Validate or commit algorithm results to the database.")
    submit_parser.add_argument("json_path")
    submit_parser.add_argument("--commit", action="store_true")

    run_parser = sub.add_parser("run-pending", help="Fetch pending samples, infer them, and optionally submit results.")
    run_parser.add_argument("--limit", type=int, default=20)
    run_parser.add_argument("--model-dir", required=True)
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--pending-json", default=None)
    run_parser.add_argument("--result-json", required=True)
    run_parser.add_argument("--submit", action="store_true")
    run_parser.add_argument("--commit", action="store_true")

    args = parser.parse_args()
    if args.command == "train":
        records = discover_dataset(args.data_dir, max_per_class=args.max_per_class)
        model, metrics = train_model(records, test_size=args.test_size, random_state=args.random_state)
        save_model(model, args.model_dir, metrics)
        print(json.dumps({"model_dir": args.model_dir, **metrics}, ensure_ascii=False, indent=2))
    elif args.command == "infer-one":
        payload = infer_one(args.audio, args.sample_uid, args.model_dir, args.output_dir, args.topk, args.review_threshold)
        _write_json(args.result_json, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.command == "infer-pending":
        payload = infer_pending_records(args.pending_json, args.model_dir, args.output_dir, args.topk, args.review_threshold)
        _write_json(args.result_json, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.command == "fetch-pending":
        payload = _query_frontend_data(["pending-for-inference", "--limit", str(args.limit)])
        _write_text(args.output, payload)
        print(payload)
    elif args.command == "submit-result":
        command = ["submit-result", args.json_path]
        if args.commit:
            command.append("--commit")
        print(_query_frontend_data(command))
    elif args.command == "run-pending":
        pending_path = Path(args.pending_json or Path(args.output_dir) / "pending_samples.json")
        pending_text = _query_frontend_data(["pending-for-inference", "--limit", str(args.limit)])
        _write_text(pending_path, pending_text)
        payload = infer_pending_records(pending_path, args.model_dir, args.output_dir)
        _write_json(args.result_json, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if args.submit:
            command = ["submit-result", args.result_json]
            if args.commit:
                command.append("--commit")
            print(_query_frontend_data(command))


def _query_frontend_data(args: list[str]) -> str:
    script = SCRIPT_DIR / "query_frontend_data.py"
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def _write_json(path: str | Path, payload: object) -> None:
    _write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def _write_text(path: str | Path, text: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
