#!/usr/bin/env python3
"""Use requests to submit a cable voiceprint JSON payload."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any


DEFAULT_API_URL = "http://192.168.10.116:8000/api/v1/cable-voiceprint/samples"

EXAMPLE_PAYLOAD: dict[str, Any] = {
    "protocol_version": "1.1",
    "request_id": "REQ_SAMPLE_001",
    "sample_uid": "SAMPLE_001",
    "collect_time": "2026-06-05T10:30:00+08:00",
    "device_id": "DEVICE_001",
    "source_audio_url": "http://数据方服务器IP:端口/audio/SAMPLE_001.wav",
    "linux_save_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_001/SAMPLE_001.wav",
    "manual_annotation": {
        "is_labeled": True,
        "is_fault": True,
        "fault_type": "内源故障",
        "fault_label": "局部放电",
        "fault_severity": "中等",
        "labeler_id": "EMP_001",
        "labeler_name": "张三",
        "label_time": "2026-06-05T10:31:00+08:00",
        "annotation_remark": "数据方人工确认该样本存在局部放电特征",
    },
}


PLACEHOLDER_TEXT = ("数据方服务器IP", "端口")


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def contains_placeholder(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_placeholder(item) for item in value)
    if isinstance(value, str):
        return any(marker in value for marker in PLACEHOLDER_TEXT)
    return False


def load_payload(json_file: Path | None, use_example: bool) -> dict[str, Any]:
    if use_example:
        return EXAMPLE_PAYLOAD
    if json_file is None:
        raise ValueError("请提供 --json-file，或使用 --submit-example 提交脚本内置案例")
    with json_file.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("JSON 文件最外层必须是对象")
    return payload


def submit_payload(api_url: str, payload: dict[str, Any], timeout: int, token: str | None) -> None:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("缺少 requests，请先安装：pip install requests") from exc

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
    print(f"HTTP_STATUS {response.status_code}")
    try:
        print(json_text(response.json()))
    except ValueError:
        print(response.text)
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit cable voiceprint sample JSON with requests.")
    parser.add_argument("--url", default=os.getenv("CABLE_VOICEPRINT_API_URL", DEFAULT_API_URL), help="接口地址")
    parser.add_argument("--json-file", type=Path, help="数据方已经写好的 JSON 文件")
    parser.add_argument("--submit-example", action="store_true", help="提交脚本内置 JSON 案例")
    parser.add_argument("--print-example", action="store_true", help="打印脚本内置 JSON 案例")
    parser.add_argument("--write-example", type=Path, help="把脚本内置 JSON 案例写到指定文件")
    parser.add_argument("--timeout", type=int, default=60, help="请求超时时间，单位秒")
    parser.add_argument("--token", default=os.getenv("INGEST_TOKEN"), help="可选 Bearer token")
    args = parser.parse_args()

    if args.write_example:
        args.write_example.write_text(json_text(EXAMPLE_PAYLOAD) + "\n", encoding="utf-8")
        print(f"已写出 JSON 案例：{args.write_example}")
        return 0

    if args.print_example or (not args.json_file and not args.submit_example):
        print(json_text(EXAMPLE_PAYLOAD))
        print("\n使用方式：")
        print(f"python3 {Path(__file__).name} --json-file sample.json")
        print(f"python3 {Path(__file__).name} --write-example sample.json")
        return 0

    payload = load_payload(args.json_file, args.submit_example)
    if contains_placeholder(payload):
        print("JSON 中还有占位内容，请先替换为数据方真实服务器地址和端口。", file=sys.stderr)
        return 2

    submit_payload(args.url, payload, args.timeout, args.token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
