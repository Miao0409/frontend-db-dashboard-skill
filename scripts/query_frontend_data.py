#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import os
import sys
from typing import Any

try:
    import mysql.connector
except ModuleNotFoundError:
    for candidate in [
        "/Users/a1111/anaconda3/lib/python3.12/site-packages",
        "/Users/a1111/.local/lib/python3.12/site-packages",
    ]:
        if candidate not in sys.path and os.path.isdir(candidate):
            sys.path.append(candidate)
    try:
        import mysql.connector
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "缺少 mysql-connector-python。请运行：python3 -m pip install mysql-connector-python"
        ) from exc


SERVICE_DISPLAY_NAMES = {
    "Industrial_Environment": "工业机械声音",
    "city_environment": "城市环境声音",
    "mountain_areas/natural environment": "自然环境声音",
    "Grounding_Box_Internal": "接地箱/设备声纹",
    "XiongAnPilot+Lab": "现场/实验声纹",
    "unknown": "未分类",
}

GRANULARITY_SQL = {
    "year": "DATE_FORMAT(acquisition_time, '%Y')",
    "month": "DATE_FORMAT(acquisition_time, '%Y-%m')",
    "day": "DATE_FORMAT(acquisition_time, '%Y-%m-%d')",
}


def db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "192.168.10.116"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "remote_user"),
        "password": os.getenv("DB_PASSWORD", "VoicePrint2025!"),
        "database": os.getenv("DB_NAME", "noise_classification"),
    }


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default))


class DbClient:
    def __init__(self) -> None:
        self.config = db_config()

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        conn = mysql.connector.connect(**self.config)
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
            return rows
        finally:
            conn.close()

    def health(self) -> dict[str, Any]:
        rows = self.query("SELECT VERSION() AS version, DATABASE() AS database_name")
        return {"ok": True, "config": {k: v for k, v in self.config.items() if k != "password"}, **rows[0]}

    def dashboard(self, top_limit: int, recent_limit: int, granularity: str) -> dict[str, Any]:
        granularity = granularity if granularity in GRANULARITY_SQL else "year"
        time_expr = GRANULARITY_SQL[granularity]
        summary = self.query(
            """
            SELECT
                COUNT(*) AS total_records,
                COALESCE(SUM(duration_sec), 0) AS total_duration_sec,
                COUNT(duration_sec) AS known_duration_records,
                COUNT(DISTINCT COALESCE(noise_source, 'unknown')) AS total_categories,
                COUNT(DISTINCT COALESCE(source_dataset, 'unknown')) AS source_dataset_count,
                COUNT(DISTINCT COALESCE(service_environment, 'unknown')) AS environment_count,
                MIN(acquisition_time) AS min_acquisition_time,
                MAX(acquisition_time) AS max_acquisition_time
            FROM noise_classification_db
            """
        )[0]
        summary["total_duration_hour"] = round(float(summary["total_duration_sec"]) / 3600, 3)

        category_cards = self.query(
            """
            SELECT
                COALESCE(service_environment, 'unknown') AS category_key,
                COUNT(*) AS record_count,
                COALESCE(SUM(duration_sec), 0) AS duration_sec
            FROM noise_classification_db
            GROUP BY COALESCE(service_environment, 'unknown')
            ORDER BY record_count DESC
            """
        )
        for item in category_cards:
            item["display_name"] = SERVICE_DISPLAY_NAMES.get(item["category_key"], item["category_key"])
            item["duration_hour"] = round(float(item["duration_sec"]) / 3600, 3)

        top_categories = self.query(
            f"""
            SELECT
                COALESCE(noise_source, operation_status, source_dataset, 'unknown') AS label,
                COUNT(*) AS record_count,
                COALESCE(SUM(duration_sec), 0) AS duration_sec
            FROM noise_classification_db
            GROUP BY COALESCE(noise_source, operation_status, source_dataset, 'unknown')
            ORDER BY record_count DESC
            LIMIT {int(top_limit)}
            """
        )

        time_distribution = self.query(
            f"""
            SELECT {time_expr} AS time_bucket, COUNT(*) AS record_count
            FROM noise_classification_db
            WHERE acquisition_time IS NOT NULL
            GROUP BY {time_expr}
            ORDER BY MIN(acquisition_time)
            """
        )

        recent_samples = self.query(
            f"""
            SELECT
                id,
                file_path,
                source_dataset,
                service_environment,
                noise_source,
                operation_status,
                sample_rate,
                duration_sec,
                channels,
                acquisition_time,
                machine_id AS device_id,
                node_id AS channel_id
            FROM noise_classification_db
            ORDER BY COALESCE(acquisition_time, '1970-01-01') DESC, id DESC
            LIMIT {int(recent_limit)}
            """
        )

        return {
            "meta": {
                "table": "noise_classification_db",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "granularity": granularity,
            },
            "summary": summary,
            "category_cards": category_cards,
            "top_categories": top_categories,
            "time_distribution": {"granularity": granularity, "items": time_distribution},
            "recent_samples": recent_samples,
        }

    def realtime(
        self,
        limit: int,
        device_id: str | None = None,
        site_code: str | None = None,
        status: str | None = None,
        sample_uid: str | None = None,
    ) -> dict[str, Any]:
        where = ["1=1"]
        params: list[Any] = []
        for col, val in [
            ("s.device_id", device_id),
            ("s.site_code", site_code),
            ("s.processing_status", status),
            ("s.sample_uid", sample_uid),
        ]:
            if val:
                where.append(f"{col} = %s")
                params.append(val)
        where_sql = " AND ".join(where)
        summary = self.query(
            f"""
            SELECT
                COUNT(*) AS total_records,
                COALESCE(SUM(CASE WHEN s.processing_status = 'UPLOADED' THEN 1 ELSE 0 END), 0) AS uploaded_count,
                COALESCE(SUM(CASE WHEN s.processing_status = 'INFERRED' THEN 1 ELSE 0 END), 0) AS inferred_count,
                COALESCE(SUM(CASE WHEN s.processing_status = 'FAILED' THEN 1 ELSE 0 END), 0) AS failed_count,
                COALESCE(SUM(CASE WHEN fe.is_fault = 1 THEN 1 ELSE 0 END), 0) AS fault_count,
                MIN(s.acquisition_start_time) AS min_acquisition_start_time,
                MAX(s.acquisition_start_time) AS max_acquisition_start_time
            FROM realtime_audio_sample s
            LEFT JOIN realtime_fault_event fe ON fe.sample_uid = s.sample_uid
            WHERE {where_sql}
            """,
            tuple(params),
        )[0]
        items = self.query(
            f"""
            SELECT
                s.sample_uid,
                s.batch_id,
                s.source_system,
                s.device_id,
                s.site_code,
                s.acquisition_start_time,
                s.duration_sec,
                s.sample_rate,
                s.channels,
                s.file_name,
                s.file_path,
                s.audio_uri,
                s.processing_status,
                s.cable_id,
                s.cable_name,
                s.phase,
                fe.is_fault,
                fe.fault_l1,
                fe.fault_l2,
                fe.voiceprint_label,
                fe.internal_fault_type,
                fe.fault_severity,
                fa.annotator_id,
                fa.annotator_name,
                fa.annotation_status,
                fa.is_final_label,
                mr.model_name,
                mr.model_version,
                mr.top1_label,
                mr.top1_prob,
                mr.final_diagnosis,
                mr.need_review
            FROM realtime_audio_sample s
            LEFT JOIN realtime_fault_event fe ON fe.sample_uid = s.sample_uid
            LEFT JOIN realtime_fault_annotation fa
                ON fa.id = (
                    SELECT fa2.id FROM realtime_fault_annotation fa2
                    WHERE fa2.sample_uid = s.sample_uid
                    ORDER BY fa2.is_final_label DESC, fa2.annotation_time DESC, fa2.id DESC
                    LIMIT 1
                )
            LEFT JOIN realtime_model_result mr
                ON mr.id = (
                    SELECT mr2.id FROM realtime_model_result mr2
                    WHERE mr2.sample_uid = s.sample_uid
                    ORDER BY mr2.inference_time DESC, mr2.id DESC
                    LIMIT 1
                )
            WHERE {where_sql}
            ORDER BY s.acquisition_start_time DESC, s.id DESC
            LIMIT {int(limit)}
            """,
            tuple(params),
        )
        return {"summary": summary, "items": items}

    def detail(self, sample_uid: str) -> dict[str, Any]:
        item = self.realtime(limit=1, sample_uid=sample_uid)["items"]
        channels = self.query(
            """
            SELECT channel_index, mic_id, mic_model, position_label, x_m, y_m, z_m, channel_role,
                   channel_file_path, channel_valid
            FROM realtime_audio_channel
            WHERE sample_uid = %s
            ORDER BY channel_index
            """,
            (sample_uid,),
        )
        annotations = self.query(
            """
            SELECT annotator_id, annotator_name, annotator_role, annotator_org, annotation_time,
                   annotation_source, annotation_status, fault_l1, fault_l2, fault_l3,
                   defect_type_id, interference_type_id, fault_severity, label_confidence,
                   annotation_text, reviewer_id, reviewer_name, review_time, review_comment,
                   is_final_label
            FROM realtime_fault_annotation
            WHERE sample_uid = %s
            ORDER BY is_final_label DESC, annotation_time DESC, id DESC
            """,
            (sample_uid,),
        )
        model_results = self.query(
            """
            SELECT model_name, model_version, inference_time, latency_ms,
                   top1_label, top1_prob, top2_label, top2_prob, top3_label, top3_prob,
                   probability_json, final_diagnosis, result_explain, feature_version,
                   feature_path, need_review
            FROM realtime_model_result
            WHERE sample_uid = %s
            ORDER BY inference_time DESC, id DESC
            """,
            (sample_uid,),
        )
        return {
            "sample_uid": sample_uid,
            "item": item[0] if item else None,
            "channels": channels,
            "annotations": annotations,
            "model_results": model_results,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="查询前端展示数据库数据")
    sub = parser.add_subparsers(dest="command", required=True)

    dash = sub.add_parser("dashboard")
    dash.add_argument("--top-limit", type=int, default=10)
    dash.add_argument("--recent-limit", type=int, default=20)
    dash.add_argument("--granularity", choices=sorted(GRANULARITY_SQL), default="year")

    real = sub.add_parser("realtime")
    real.add_argument("--limit", type=int, default=50)
    real.add_argument("--device-id")
    real.add_argument("--site-code")
    real.add_argument("--status")
    real.add_argument("--sample-uid")

    detail = sub.add_parser("detail")
    detail.add_argument("sample_uid")

    sub.add_parser("health")

    args = parser.parse_args()
    client = DbClient()
    if args.command == "health":
        print_json(client.health())
    elif args.command == "dashboard":
        print_json(client.dashboard(args.top_limit, args.recent_limit, args.granularity))
    elif args.command == "realtime":
        print_json(client.realtime(args.limit, args.device_id, args.site_code, args.status, args.sample_uid))
    elif args.command == "detail":
        print_json(client.detail(args.sample_uid))


if __name__ == "__main__":
    main()
