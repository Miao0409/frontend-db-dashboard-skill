"""CLI for local and pending-JSON voiceprint inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from voiceprint_algorithm.audio_features import create_feature_resources
from voiceprint_algorithm.model import MODEL_NAME, MODEL_VERSION, load_model, predict_audio
from voiceprint_algorithm.result_schema import build_result_record


def infer_one(
    audio_path: str | Path,
    sample_uid: str,
    model_dir: str | Path,
    output_dir: str | Path,
    topk: int = 3,
    review_threshold: float = 0.75,
) -> dict:
    model = load_model(model_dir)
    top_predictions, audio, feature = predict_audio(model, audio_path, topk=topk)
    resources = create_feature_resources(
        audio=audio,
        feature=feature,
        sample_uid=sample_uid,
        source_path=audio_path,
        output_dir=Path(output_dir) / sample_uid,
    )
    return build_result_record(
        sample_uid=sample_uid,
        topk=top_predictions,
        resources=resources,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        review_threshold=review_threshold,
    )


def infer_pending_records(
    pending_json: str | Path,
    model_dir: str | Path,
    output_dir: str | Path,
    topk: int = 3,
    review_threshold: float = 0.75,
) -> list[dict]:
    records = _load_records(pending_json)
    results = []
    for index, record in enumerate(records, start=1):
        sample_uid = str(record.get("sample_uid") or f"PENDING_{index:04d}")
        audio_path = _audio_path_from_pending_record(record)
        results.append(
            infer_one(
                audio_path=audio_path,
                sample_uid=sample_uid,
                model_dir=model_dir,
                output_dir=output_dir,
                topk=topk,
                review_threshold=review_threshold,
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run voiceprint demo inference.")
    parser.add_argument("--audio", help="Local wav path for single-sample inference.")
    parser.add_argument("--pending-json", help="JSON list from pending-for-inference.")
    parser.add_argument("--sample-uid", default="DEMO_SAMPLE")
    parser.add_argument("--model-dir", default="models/voiceprint_demo")
    parser.add_argument("--output-dir", default="outputs/demo")
    parser.add_argument("--result-json", default=None)
    parser.add_argument("--topk", type=int, default=3)
    parser.add_argument("--review-threshold", type=float, default=0.75)
    args = parser.parse_args()

    if bool(args.audio) == bool(args.pending_json):
        raise SystemExit("Pass exactly one of --audio or --pending-json.")

    if args.audio:
        payload: dict | list[dict] = infer_one(
            audio_path=args.audio,
            sample_uid=args.sample_uid,
            model_dir=args.model_dir,
            output_dir=args.output_dir,
            topk=args.topk,
            review_threshold=args.review_threshold,
        )
    else:
        payload = infer_pending_records(
            pending_json=args.pending_json,
            model_dir=args.model_dir,
            output_dir=args.output_dir,
            topk=args.topk,
            review_threshold=args.review_threshold,
        )

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.result_json:
        path = Path(args.result_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text)


def _load_records(path: str | Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "data", "samples"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise ValueError(f"Pending JSON must be a list or contain records/data/samples: {path}")


def _audio_path_from_pending_record(record: dict[str, Any]) -> Path:
    for key in ("file_path", "local_audio_path", "audio_path", "linux_save_path"):
        value = record.get(key)
        if value and Path(value).exists():
            return Path(value)
    channels = record.get("channels") or []
    for channel in channels:
        for key in ("channel_file_path", "file_path", "linux_save_path"):
            value = channel.get(key) if isinstance(channel, dict) else None
            if value and Path(value).exists():
                return Path(value)
    raise FileNotFoundError(f"No local audio path exists for pending record: {record.get('sample_uid')}")


if __name__ == "__main__":
    main()
