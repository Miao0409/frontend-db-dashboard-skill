"""CLI for training the lightweight 9-class voiceprint demo classifier."""

from __future__ import annotations

import argparse
import json

from voiceprint_algorithm.model import discover_dataset, save_model, train_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the voiceprint demo classifier.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--model-dir", default="models/voiceprint_demo")
    parser.add_argument("--max-per-class", type=int, default=None)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--include-unknown-folders", action="store_true")
    args = parser.parse_args()

    records = discover_dataset(
        args.data_dir,
        include_unknown_folders=args.include_unknown_folders,
        max_per_class=args.max_per_class,
    )
    model, metrics = train_model(records, test_size=args.test_size, random_state=args.random_state)
    save_model(model, args.model_dir, metrics)
    print(json.dumps({"model_dir": args.model_dir, **metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
