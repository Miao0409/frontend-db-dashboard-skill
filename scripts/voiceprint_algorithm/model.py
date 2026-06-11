"""Training and prediction helpers for the lightweight demo classifier."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from voiceprint_algorithm import __version__
from voiceprint_algorithm.audio_features import extract_feature_vector, load_audio
from voiceprint_algorithm.labels import CLASS_LABELS, canonical_label


MODEL_NAME = "voiceprint_demo_classifier"
MODEL_VERSION = f"v{__version__}"


@dataclass(frozen=True)
class DatasetRecord:
    path: Path
    label: str


@dataclass(frozen=True)
class TrainedModel:
    pipeline: Pipeline
    feature_names: tuple[str, ...]
    labels: tuple[str, ...]


def discover_dataset(
    data_dir: str | Path,
    include_unknown_folders: bool = False,
    max_per_class: int | None = None,
) -> list[DatasetRecord]:
    """Discover non-empty wav files below known class folders."""

    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"Data directory does not exist: {root}")

    records: list[DatasetRecord] = []
    for class_dir in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name):
        try:
            label = canonical_label(class_dir.name)
        except KeyError as exc:
            if include_unknown_folders:
                continue
            raise ValueError(f"Unknown class folder under {root}: {class_dir.name}") from exc

        wavs = sorted(class_dir.glob("*.wav"), key=_natural_key)
        kept = 0
        for wav_path in wavs:
            if wav_path.stat().st_size <= 0:
                continue
            records.append(DatasetRecord(path=wav_path, label=label))
            kept += 1
            if max_per_class is not None and kept >= max_per_class:
                break
    if not records:
        raise ValueError(f"No usable wav files found under {root}")
    return records


def train_model(
    records: Iterable[DatasetRecord],
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[TrainedModel, dict]:
    """Train a scaled logistic regression classifier and return metrics."""

    record_list = list(records)
    features = []
    labels = []
    feature_names: tuple[str, ...] | None = None
    skipped: list[str] = []
    for record in record_list:
        try:
            audio = load_audio(record.path)
            feature = extract_feature_vector(audio)
        except Exception as exc:  # noqa: BLE001 - keep batch training robust for demo data
            skipped.append(f"{record.path}: {exc}")
            continue
        feature_names = feature.names
        features.append(feature.values)
        labels.append(record.label)

    if len(features) < 2:
        raise ValueError("Need at least two valid audio files to train the demo classifier")

    x = np.vstack(features)
    y = np.asarray(labels)
    stratify = y if _can_stratify(y, test_size) else None
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )
    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=random_state)),
        ]
    )
    pipeline.fit(x_train, y_train)
    predicted = pipeline.predict(x_test)
    metrics = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "total_records": len(record_list),
        "valid_records": int(len(features)),
        "skipped_records": skipped,
        "labels": list(CLASS_LABELS),
        "accuracy": float(accuracy_score(y_test, predicted)),
        "classification_report": classification_report(y_test, predicted, labels=list(CLASS_LABELS), zero_division=0, output_dict=True),
    }
    model = TrainedModel(pipeline=pipeline, feature_names=feature_names or (), labels=tuple(pipeline.classes_))
    return model, metrics


def save_model(model: TrainedModel, model_dir: str | Path, metrics: dict | None = None) -> None:
    """Persist the classifier and metadata."""

    out = Path(model_dir)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": model.pipeline, "feature_names": model.feature_names, "labels": model.labels}, out / "model.joblib")
    (out / "labels.json").write_text(json.dumps(list(model.labels), ensure_ascii=False, indent=2), encoding="utf-8")
    if metrics is not None:
        (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


def load_model(model_dir: str | Path) -> TrainedModel:
    """Load a persisted classifier."""

    payload = joblib.load(Path(model_dir) / "model.joblib")
    return TrainedModel(
        pipeline=payload["pipeline"],
        feature_names=tuple(payload["feature_names"]),
        labels=tuple(payload["labels"]),
    )


def predict_audio(model: TrainedModel, audio_path: str | Path, topk: int = 3) -> tuple[list[tuple[str, float]], object, object]:
    """Predict a wav file and return top-k labels with audio and feature objects."""

    audio = load_audio(audio_path)
    feature = extract_feature_vector(audio)
    probabilities = model.pipeline.predict_proba([feature.values])[0]
    classes = list(model.pipeline.classes_)
    order = np.argsort(probabilities)[::-1][:topk]
    top = [(classes[i], float(probabilities[i])) for i in order]
    return top, audio, feature


def _can_stratify(y: np.ndarray, test_size: float) -> bool:
    labels, counts = np.unique(y, return_counts=True)
    if len(labels) < 2 or np.any(counts < 2):
        return False
    test_count = max(1, int(round(len(y) * test_size)))
    return test_count >= len(labels)


def _natural_key(path: Path) -> tuple:
    stem = path.stem
    return (0, int(stem)) if stem.isdigit() else (1, stem)
