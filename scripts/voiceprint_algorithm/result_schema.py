"""Build database-compatible voiceprint inference result records."""

from __future__ import annotations

from voiceprint_algorithm.labels import label_info


def build_result_record(
    sample_uid: str,
    topk: list[tuple[str, float]],
    resources: dict[str, str],
    model_name: str,
    model_version: str,
    review_threshold: float = 0.75,
) -> dict:
    """Create the JSON shape accepted by the database submit-result workflow."""

    if not topk:
        raise ValueError("topk must contain at least one prediction")
    normalized = [(label, float(score)) for label, score in topk]
    top_label, top_score = normalized[0]
    info = label_info(top_label)
    need_review = top_score < review_threshold
    topk_json = [{"label": label, "score": round(score, 6)} for label, score in normalized]
    result_explain = (
        f"轻量声纹 demo 模型判定为{top_label}，置信度 {top_score:.2%}。"
        + ("低于复核阈值，建议人工复核。" if need_review else "置信度达到展示阈值。")
    )
    return {
        "sample_uid": sample_uid,
        "model_name": model_name,
        "model_version": model_version,
        "algorithm_result": top_label,
        "confidence_score": round(top_score, 6),
        "topk_result_json": topk_json,
        "is_fault": info.is_fault,
        "fault_label": top_label,
        "fault_type": info.fault_type,
        "spectrum_uri": resources.get("spectrum_uri"),
        "waveform_uri": resources.get("waveform_uri"),
        "feature_uri": resources.get("feature_uri"),
        "need_review": need_review,
        "result_explain": result_explain,
    }
