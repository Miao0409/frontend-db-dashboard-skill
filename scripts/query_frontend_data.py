#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

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

ENVIRONMENT_DASHBOARD_CATEGORIES = {
    "city_environment": "城市环境声音",
    "mountain_areas/natural environment": "乡村环境声音",
    "Industrial_Environment": "工业机械声音",
    "Grounding_Box_Internal": "智慧耳声纹",
}

NOISE_SOURCE_DISPLAY_NAMES = {
    "Alarm_Triggered": "智慧耳告警触发声",
    "air_conditioner": "空调声",
    "airplane": "飞机声",
    "breathing": "呼吸声",
    "brushing_teeth": "刷牙声",
    "can_opening": "开罐声",
    "car_horn": "汽车喇叭声",
    "cat": "猫叫声",
    "chainsaw": "电锯声",
    "children_playing": "儿童玩耍声",
    "chirping_birds": "鸟鸣声",
    "church_bells": "教堂钟声",
    "clapping": "鼓掌声",
    "clock_alarm": "闹钟声",
    "clock_tick": "钟表滴答声",
    "corona": "电晕声",
    "coughing": "咳嗽声",
    "cow": "牛叫声",
    "crackling_fire": "火焰噼啪声",
    "crickets": "蟋蟀声",
    "crow": "乌鸦叫声",
    "crying_baby": "婴儿哭声",
    "dog": "狗叫声",
    "dog_bark": "犬吠声",
    "door_wood_creaks": "木门吱呀声",
    "door_wood_knock": "木门敲击声",
    "drilling": "钻孔声",
    "drinking_sipping": "喝水声",
    "engine": "发动机声",
    "engine_idling": "发动机怠速声",
    "fan": "风扇声",
    "fireworks": "烟花声",
    "footsteps": "脚步声",
    "frog": "青蛙叫声",
    "glass_breaking": "玻璃破碎声",
    "gun_shot": "枪声",
    "hand_saw": "手锯声",
    "helicopter": "直升机声",
    "hen": "母鸡叫声",
    "insects": "昆虫声",
    "jackhammer": "风镐声",
    "keyboard_typing": "键盘敲击声",
    "laughing": "笑声",
    "mouse_click": "鼠标点击声",
    "pig": "猪叫声",
    "pouring_water": "倒水声",
    "pump": "水泵声",
    "rain": "雨声",
    "rooster": "公鸡打鸣声",
    "sea_waves": "海浪声",
    "sheep": "羊叫声",
    "siren": "警笛声",
    "slider": "滑轨声",
    "sneezing": "打喷嚏声",
    "snoring": "打鼾声",
    "street_music": "街头音乐声",
    "thunderstorm": "雷雨声",
    "toilet_flush": "冲水声",
    "train": "火车声",
    "transformer": "变压器声",
    "vacuum_cleaner": "吸尘器声",
    "valve": "阀门声",
    "washing_machine": "洗衣机声",
    "water_drops": "水滴声",
    "wind": "风声",
}

GRANULARITY_SQL = {
    "year": "DATE_FORMAT(acquisition_time, '%Y')",
    "month": "DATE_FORMAT(acquisition_time, '%Y-%m')",
    "day": "DATE_FORMAT(acquisition_time, '%Y-%m-%d')",
}

MANIFEST_REQUIRED_FIELDS = [
    "sample_uid",
    "collect_time",
    "device_id",
    "channel_count",
    "sample_rate",
    "bit_depth",
    "duration_sec",
    "file_name",
    "file_path",
    "file_sha256",
    "audio_uri",
    "site_code",
    "site_name",
    "site_environment",
]

RESULT_REQUIRED_FIELDS = [
    "sample_uid",
    "model_name",
    "model_version",
    "algorithm_result",
    "confidence_score",
]

CABLE_SAMPLE_API_BASE = os.getenv(
    "CABLE_VOICEPRINT_SAMPLE_API_BASE",
    "http://192.168.10.116:8000/api/v1/cable-voiceprint/samples",
)
CABLE_SAMPLE_API_URL = os.getenv(
    "CABLE_VOICEPRINT_API_URL",
    "http://192.168.10.116:8000/api/v1/cable-voiceprint/samples",
)
CABLE_MYSQL_DB = os.getenv("CABLE_MYSQL_DB", "电缆声纹检测库")

STATUS_TO_DB = {
    "待处理": "QUEUED",
    "已上传": "UPLOADED",
    "处理中": "PROCESSING",
    "已推理": "INFERRED",
    "已完成": "INFERRED",
    "处理失败": "FAILED",
    "待人工复核": "INFERRED",
}

STATUS_TO_DISPLAY = {
    "UPLOADED": "已上传",
    "QUEUED": "待处理",
    "PROCESSING": "处理中",
    "INFERRED": "已推理",
    "FAILED": "处理失败",
}


def db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "192.168.10.116"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "remote_user"),
        "password": os.getenv("DB_PASSWORD", "VoicePrint2025!"),
        "database": os.getenv("DB_NAME", "noise_classification"),
        "ssl_disabled": os.getenv("DB_SSL_DISABLED", "true").lower() != "false",
    }


def cable_db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "192.168.10.116"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "remote_user"),
        "password": os.getenv("DB_PASSWORD", "VoicePrint2025!"),
        "database": CABLE_MYSQL_DB,
        "ssl_disabled": os.getenv("DB_SSL_DISABLED", "true").lower() != "false",
    }


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def mysql_datetime_text(value: Any | None = None) -> str:
    if value in (None, ""):
        dt = datetime.now()
    elif isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text.replace("T", " ").split("+", 1)[0]
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt.isoformat(sep=" ", timespec="milliseconds")


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default))


def http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False, default=json_default).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=body, method=method.upper(), headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            if isinstance(data, dict):
                return {"http_status": response.status, **data}
            return {"http_status": response.status, "data": data}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"response_text": raw}
        if isinstance(data, dict):
            return {"http_status": exc.code, "success": False, **data}
        return {"http_status": exc.code, "success": False, "data": data}
    except URLError as exc:
        return {"success": False, "error": "request_failed", "message": str(exc.reason)}


def cable_channel_urls(base_url: str, sample_uid: str, channel_no: int = 1) -> tuple[str, str]:
    encoded_uid = quote(sample_uid, safe="")
    base = base_url.rstrip("/")
    return f"{base}/{encoded_uid}/channels", f"{base}/{encoded_uid}/channels/{channel_no}"


def load_json_records(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        for key in ("samples", "items", "records", "data"):
            if isinstance(data.get(key), list):
                records = data[key]
                break
        else:
            records = [data]
    else:
        raise ValueError("JSON 顶层必须是对象、对象数组，或包含 samples/items/records/data 数组的对象")
    bad = [i for i, item in enumerate(records, start=1) if not isinstance(item, dict)]
    if bad:
        raise ValueError(f"JSON 第 {bad[0]} 条不是对象")
    return records


def load_json_object(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层必须是对象")
    return data


def to_json_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=json_default)


def parse_bool(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value else 0
    if str(value).strip().lower() in {"1", "true", "yes", "y", "是", "故障"}:
        return 1
    if str(value).strip().lower() in {"0", "false", "no", "n", "否", "正常"}:
        return 0
    return None


def db_status(value: Any, default: str = "QUEUED") -> str:
    if value is None or value == "":
        return default
    text = str(value)
    return STATUS_TO_DB.get(text, text)


def display_status(value: Any) -> Any:
    if value is None:
        return None
    return STATUS_TO_DISPLAY.get(str(value), value)


def normalize_channel_storage_mode(value: Any) -> str:
    text = str(value or "单文件四通道")
    if text in {"单文件四通道", "multi_channel_audio"}:
        return "multi_channel_audio"
    if text in {"四个单通道文件", "four_mono_audio"}:
        return "four_mono_audio"
    if text in {"压缩包", "archive"}:
        return "archive"
    return "multi_channel_audio"


class DbClient:
    def __init__(self) -> None:
        self.config = db_config()
        self._column_cache: dict[str, set[str]] = {}
        self._table_cache: dict[str, bool] = {}

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

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        conn = mysql.connector.connect(**self.config)
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            rowcount = cur.rowcount
            cur.close()
            return rowcount
        finally:
            conn.close()

    def table_exists(self, table: str) -> bool:
        if table not in self._table_cache:
            rows = self.query(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                """,
                (table,),
            )
            self._table_cache[table] = bool(rows and rows[0]["count"])
        return self._table_cache[table]

    def table_columns(self, table: str) -> set[str]:
        if table not in self._column_cache:
            rows = self.query(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                """,
                (table,),
            )
            self._column_cache[table] = {row["COLUMN_NAME"] for row in rows}
        return self._column_cache[table]

    def upsert(self, table: str, row: dict[str, Any], key_columns: tuple[str, ...]) -> int:
        if not self.table_exists(table):
            raise RuntimeError(f"数据表不存在：{table}")
        columns = self.table_columns(table)
        filtered = {k: v for k, v in row.items() if k in columns and v is not None}
        if not filtered:
            return 0
        update_columns = [col for col in filtered if col not in key_columns]
        placeholders = ", ".join(["%s"] * len(filtered))
        column_sql = ", ".join(f"`{col}`" for col in filtered)
        if update_columns:
            update_sql = ", ".join(f"`{col}` = VALUES(`{col}`)" for col in update_columns)
        else:
            update_sql = f"`{key_columns[0]}` = VALUES(`{key_columns[0]}`)"
        sql = (
            f"INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {update_sql}"
        )
        return self.execute(sql, tuple(filtered.values()))

    def health(self) -> dict[str, Any]:
        rows = self.query("SELECT VERSION() AS version, DATABASE() AS database_name")
        return {"ok": True, "config": {k: v for k, v in self.config.items() if k != "password"}, **rows[0]}

    def connect_db(self) -> dict[str, Any]:
        health = self.health()
        database_rows = self.query("SHOW DATABASES")
        system_databases = {"information_schema", "mysql", "performance_schema", "sys"}
        database_names = [
            next(iter(row.values()))
            for row in database_rows
            if next(iter(row.values())) not in system_databases
        ]
        databases = []
        for database_name in database_names:
            table_rows = self.query(
                """
                SELECT TABLE_NAME, TABLE_ROWS
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
                """,
                (database_name,),
            )
            databases.append(
                {
                    "数据库名称": database_name,
                    "表数量": len(table_rows),
                    "主要表": [
                        {
                            "表名": row["TABLE_NAME"],
                            "估算行数": int(row["TABLE_ROWS"] or 0),
                        }
                        for row in table_rows[:20]
                    ],
                }
            )
        return {
            "连接状态": "成功",
            "MySQL": {
                "主机": self.config["host"],
                "端口": self.config["port"],
                "用户": self.config["user"],
                "当前数据库": health["database_name"],
                "版本": health["version"],
            },
            "可用数据库": databases,
            "常用命令": {
                "环境声音前端展示": "environment-dashboard-cn",
                "数据库整体概览": "database-overview",
                "连接检查": "connect-db",
            },
        }

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

    def environment_dashboard_cn(self, top_limit: int = 10) -> dict[str, Any]:
        category_keys = tuple(ENVIRONMENT_DASHBOARD_CATEGORIES)
        placeholders = ", ".join(["%s"] * len(category_keys))
        # Duration is corrected with the confirmed data-source rules:
        # MIMII 10s/sample, TransDKY 3s/sample, UrbanSound8K 525min total,
        # ESC-50 5s/sample, and SmartEar duration already stored in DB.
        duration_rules_sec = {
            "Industrial_Environment": 596286,
            "city_environment": 38300,
            "mountain_areas/natural environment": 3200,
            "Grounding_Box_Internal": 39714,
        }

        big_rows = self.query(
            f"""
            SELECT
                service_environment AS category_key,
                COUNT(*) AS record_count,
                COUNT(DISTINCT noise_source) AS small_category_count
            FROM noise_classification_db
            WHERE service_environment IN ({placeholders})
            GROUP BY service_environment
            """,
            category_keys,
        )
        big_by_key = {row["category_key"]: row for row in big_rows}
        big_categories = []
        for key, name in ENVIRONMENT_DASHBOARD_CATEGORIES.items():
            row = big_by_key.get(key, {})
            duration_sec = duration_rules_sec.get(key, 0)
            big_categories.append(
                {
                    "大类别名称": name,
                    "条数": int(row.get("record_count") or 0),
                    "小类别数量": int(row.get("small_category_count") or 0),
                    "总时长秒": duration_sec,
                    "总时长小时": round(duration_sec / 3600, 3),
                }
            )

        small_rows = self.query(
            f"""
            SELECT
                noise_source AS small_category_key,
                service_environment AS category_key,
                COUNT(*) AS record_count
            FROM noise_classification_db
            WHERE service_environment IN ({placeholders})
            GROUP BY noise_source, service_environment
            ORDER BY record_count DESC, small_category_key ASC
            """,
            category_keys,
        )
        small_categories = [
            {
                "大类别名称": ENVIRONMENT_DASHBOARD_CATEGORIES.get(row["category_key"], row["category_key"]),
                "小类别名称": NOISE_SOURCE_DISPLAY_NAMES.get(row["small_category_key"], row["small_category_key"]),
                "条数": int(row["record_count"]),
            }
            for row in small_rows
        ]

        total_duration_sec = sum(item["总时长秒"] for item in big_categories)
        return {
            "汇总": {
                "数据总数": sum(item["条数"] for item in big_categories),
                "总时长秒": total_duration_sec,
                "总时长小时": round(total_duration_sec / 3600, 3),
                "大类别总数": len(big_categories),
                "小类别总数": len({row["small_category_key"] for row in small_rows}),
            },
            "大类别": big_categories,
            "环境声音TOP10": small_categories[: int(top_limit)],
            "小类别数量统计": small_categories,
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
            ("s.processing_status", db_status(status, "") if status else None),
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
                COALESCE(SUM(CASE WHEN s.processing_status IN ('UPLOADED', 'QUEUED') THEN 1 ELSE 0 END), 0) AS pending_count,
                COALESCE(SUM(CASE WHEN s.processing_status = 'PROCESSING' THEN 1 ELSE 0 END), 0) AS processing_count,
                COALESCE(SUM(CASE WHEN s.processing_status = 'INFERRED' THEN 1 ELSE 0 END), 0) AS inferred_count,
                COALESCE(SUM(CASE WHEN s.processing_status = 'FAILED' THEN 1 ELSE 0 END), 0) AS failed_count,
                COALESCE(SUM(CASE WHEN fe.is_fault = 1 THEN 1 ELSE 0 END), 0) AS fault_count,
                MIN(s.acquisition_start_time) AS min_collect_time,
                MAX(s.acquisition_start_time) AS max_collect_time
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
                s.collect_task_id,
                s.device_id,
                s.device_name,
                s.site_code,
                s.site_name,
                s.service_environment AS site_environment,
                s.acquisition_start_time AS collect_time,
                s.duration_sec,
                s.sample_rate,
                s.bit_depth,
                s.channels AS channel_count,
                s.file_name,
                s.file_path,
                s.audio_uri,
                s.file_sha256,
                s.processing_status AS process_status,
                fe.is_fault,
                fe.voiceprint_label AS fault_label,
                fe.fault_l1 AS fault_type,
                fe.fault_severity,
                mr.model_name,
                mr.model_version,
                mr.top1_label AS algorithm_result,
                mr.top1_prob AS confidence_score,
                mr.probability_json AS topk_result_json,
                mr.final_diagnosis,
                mr.feature_path,
                mr.need_review
            FROM realtime_audio_sample s
            LEFT JOIN realtime_fault_event fe ON fe.sample_uid = s.sample_uid
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
        for item in items:
            item["process_status_display"] = display_status(item.get("process_status"))
        return {"summary": summary, "items": items}

    def detail(self, sample_uid: str) -> dict[str, Any]:
        item = self.realtime(limit=1, sample_uid=sample_uid)["items"]
        channels = self.query(
            """
            SELECT channel_index AS channel_no, position_label AS channel_name,
                   channel_file_path, channel_valid
            FROM realtime_audio_channel
            WHERE sample_uid = %s
            ORDER BY channel_index
            """,
            (sample_uid,),
        )
        model_results = self.query(
            """
            SELECT model_name, model_version, inference_time, latency_ms,
                   top1_label AS algorithm_result, top1_prob AS confidence_score,
                   top2_label, top2_prob, top3_label, top3_prob,
                   probability_json AS topk_result_json, final_diagnosis, result_explain,
                   feature_path, need_review
            FROM realtime_model_result
            WHERE sample_uid = %s
            ORDER BY inference_time DESC, id DESC
            """,
            (sample_uid,),
        )
        fault_results = self.query(
            """
            SELECT is_fault, voiceprint_label AS fault_label, fault_l1 AS fault_type,
                   internal_fault_type, fault_severity, diagnosis_basis
            FROM realtime_fault_event
            WHERE sample_uid = %s
            """,
            (sample_uid,),
        )
        return {
            "sample_uid": sample_uid,
            "item": item[0] if item else None,
            "channels": channels,
            "fault_results": fault_results,
            "model_results": model_results,
        }

    def validate_manifest_records(self, records: list[dict[str, Any]], check_files: bool = False) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        seen: set[str] = set()
        for idx, record in enumerate(records, start=1):
            sample_uid = record.get("sample_uid")
            missing = [field for field in MANIFEST_REQUIRED_FIELDS if record.get(field) in (None, "")]
            if missing:
                errors.append({"index": idx, "sample_uid": sample_uid, "missing_fields": missing})
            if sample_uid:
                if sample_uid in seen:
                    errors.append({"index": idx, "sample_uid": sample_uid, "error": "sample_uid 在 JSON 内重复"})
                seen.add(sample_uid)
            channel_count = int(record.get("channel_count") or 0)
            channels = record.get("channels")
            if channel_count != 4:
                warnings.append({"index": idx, "sample_uid": sample_uid, "warning": "channel_count 不是 4"})
            if isinstance(channels, list):
                channel_nos = [ch.get("channel_no") for ch in channels if isinstance(ch, dict)]
                if len(set(channel_nos)) != len(channel_nos):
                    errors.append({"index": idx, "sample_uid": sample_uid, "error": "channels 中 channel_no 重复"})
                if any(no in (None, "") for no in channel_nos):
                    errors.append({"index": idx, "sample_uid": sample_uid, "error": "channels 中存在缺失 channel_no 的通道"})
            else:
                warnings.append({"index": idx, "sample_uid": sample_uid, "warning": "未提供 channels 明细，将按 channel_count 自动生成通道记录"})
            if check_files and record.get("file_path") and not Path(str(record["file_path"])).exists():
                warnings.append({"index": idx, "sample_uid": sample_uid, "warning": "file_path 在当前机器不可访问"})
        return {
            "ok": not errors,
            "total_records": len(records),
            "required_fields": MANIFEST_REQUIRED_FIELDS,
            "errors": errors,
            "warnings": warnings,
            "preview": records[:3],
        }

    def ingest_manifest(self, records: list[dict[str, Any]], commit: bool = False) -> dict[str, Any]:
        validation = self.validate_manifest_records(records)
        actions: list[dict[str, Any]] = []
        if validation["errors"]:
            return {"ok": False, "commit": commit, "validation": validation, "actions": actions}
        for record in records:
            sample_uid = record["sample_uid"]
            sample_row = {
                "sample_uid": sample_uid,
                "batch_id": record.get("batch_id") or f"BATCH_{datetime.now().strftime('%Y%m%d')}",
                "source_system": "data_center",
                "collect_task_id": record.get("collect_task_id"),
                "acquisition_start_time": record.get("collect_time"),
                "duration_sec": record.get("duration_sec"),
                "sample_rate": record.get("sample_rate"),
                "bit_depth": record.get("bit_depth"),
                "channels": record.get("channel_count"),
                "audio_format": record.get("audio_format") or "wav",
                "channel_storage_mode": normalize_channel_storage_mode(record.get("channel_storage_mode")),
                "file_name": record.get("file_name"),
                "file_path": record.get("file_path"),
                "audio_uri": record.get("audio_uri"),
                "file_sha256": record.get("file_sha256"),
                "file_size_bytes": record.get("file_size_bytes"),
                "feature_path": record.get("feature_path"),
                "processing_status": db_status(record.get("process_status"), "QUEUED"),
                "device_id": record.get("device_id"),
                "device_name": record.get("device_name"),
                "install_location": record.get("device_location"),
                "site_code": record.get("site_code"),
                "site_name": record.get("site_name"),
                "service_environment": record.get("site_environment"),
                "weather": record.get("weather"),
                "channel_map_json": to_json_text(record.get("channel_map_json")),
                "environment_json": to_json_text(
                    {
                        "noise_environment_label": record.get("noise_environment_label"),
                        "site_remark": record.get("site_remark"),
                    }
                ),
                "raw_metadata_json": to_json_text(record),
            }
            channels = record.get("channels")
            if not isinstance(channels, list):
                channels = [
                    {"channel_no": idx, "channel_name": f"通道{idx}"}
                    for idx in range(1, int(record.get("channel_count") or 4) + 1)
                ]
            actions.append({"sample_uid": sample_uid, "action": "upsert realtime_audio_sample"})
            if commit:
                self.upsert("realtime_audio_sample", sample_row, ("sample_uid",))
            for channel in channels:
                if not isinstance(channel, dict):
                    continue
                channel_row = {
                    "sample_uid": sample_uid,
                    "channel_index": channel.get("channel_no"),
                    "position_label": channel.get("channel_name"),
                    "channel_file_path": channel.get("channel_file_path"),
                    "channel_valid": 1,
                }
                actions.append(
                    {
                        "sample_uid": sample_uid,
                        "action": "upsert realtime_audio_channel",
                        "channel_no": channel.get("channel_no"),
                    }
                )
                if commit:
                    self.upsert("realtime_audio_channel", channel_row, ("sample_uid", "channel_index"))
        return {"ok": True, "commit": commit, "total_records": len(records), "actions": actions}

    def pending_for_inference(self, limit: int) -> dict[str, Any]:
        items = self.query(
            f"""
            SELECT
                s.sample_uid,
                s.acquisition_start_time AS collect_time,
                s.device_id,
                s.device_name,
                s.site_code,
                s.site_name,
                s.service_environment AS site_environment,
                s.duration_sec,
                s.sample_rate,
                s.bit_depth,
                s.channels AS channel_count,
                s.file_name,
                s.file_path,
                s.audio_uri,
                s.file_sha256,
                s.channel_storage_mode,
                s.channel_map_json,
                s.processing_status AS process_status
            FROM realtime_audio_sample s
            WHERE s.processing_status IN ('UPLOADED', 'QUEUED')
            ORDER BY s.acquisition_start_time ASC, s.id ASC
            LIMIT {int(limit)}
            """
        )
        for item in items:
            channels = self.query(
                """
                SELECT channel_index AS channel_no, position_label AS channel_name,
                       channel_file_path, channel_valid
                FROM realtime_audio_channel
                WHERE sample_uid = %s
                ORDER BY channel_index
                """,
                (item["sample_uid"],),
            )
            item["channels"] = channels
            item["process_status_display"] = display_status(item.get("process_status"))
        return {"total_records": len(items), "items": items}

    def submit_result_records(self, records: list[dict[str, Any]], commit: bool = False) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        for idx, record in enumerate(records, start=1):
            missing = [field for field in RESULT_REQUIRED_FIELDS if record.get(field) in (None, "")]
            if missing:
                errors.append({"index": idx, "sample_uid": record.get("sample_uid"), "missing_fields": missing})
        if errors:
            return {"ok": False, "commit": commit, "errors": errors, "actions": actions}

        for record in records:
            sample_uid = record["sample_uid"]
            topk = record.get("topk_result_json")
            if isinstance(topk, list) and topk:
                top1 = topk[0] if isinstance(topk[0], dict) else {}
                top2 = topk[1] if len(topk) > 1 and isinstance(topk[1], dict) else {}
                top3 = topk[2] if len(topk) > 2 and isinstance(topk[2], dict) else {}
            else:
                top1, top2, top3 = {}, {}, {}
            result_row = {
                "sample_uid": sample_uid,
                "model_name": record.get("model_name"),
                "model_version": record.get("model_version"),
                "inference_time": record.get("inference_time") or datetime.now().isoformat(sep=" ", timespec="milliseconds"),
                "latency_ms": record.get("latency_ms"),
                "top1_label": top1.get("label") or record.get("algorithm_result"),
                "top1_prob": top1.get("score") or record.get("confidence_score"),
                "top2_label": top2.get("label"),
                "top2_prob": top2.get("score"),
                "top3_label": top3.get("label"),
                "top3_prob": top3.get("score"),
                "probability_json": to_json_text(topk),
                "final_diagnosis": record.get("final_diagnosis"),
                "result_explain": record.get("result_explain"),
                "feature_path": record.get("feature_uri") or record.get("feature_path"),
                "need_review": parse_bool(record.get("need_review")),
            }
            fault_row = {
                "sample_uid": sample_uid,
                "is_fault": parse_bool(record.get("is_fault")),
                "fault_l1": record.get("fault_type"),
                "voiceprint_label": record.get("fault_label") or record.get("algorithm_result"),
                "internal_fault_type": record.get("internal_fault_type"),
                "fault_severity": record.get("fault_severity"),
                "diagnosis_basis": record.get("final_diagnosis"),
            }
            actions.append({"sample_uid": sample_uid, "action": "insert realtime_model_result"})
            actions.append({"sample_uid": sample_uid, "action": "upsert realtime_fault_event"})
            actions.append({"sample_uid": sample_uid, "action": "update realtime_audio_sample.processing_status"})
            if commit:
                self.upsert("realtime_model_result", result_row, ("sample_uid", "model_name", "model_version"))
                self.upsert("realtime_fault_event", fault_row, ("sample_uid",))
                status = "INFERRED" if not record.get("process_status") else db_status(record.get("process_status"))
                self.execute(
                    "UPDATE realtime_audio_sample SET processing_status = %s WHERE sample_uid = %s",
                    (status, sample_uid),
                )
        return {"ok": True, "commit": commit, "total_records": len(records), "actions": actions}

    def feature_resources(self, sample_uid: str) -> dict[str, Any]:
        resources = {
            "spectrum_uri": None,
            "waveform_uri": None,
            "feature_uri": None,
            "feature_path": None,
        }
        if self.table_exists("voiceprint_feature_resource"):
            cols = self.table_columns("voiceprint_feature_resource")
            wanted = [col for col in ("spectrum_uri", "waveform_uri", "feature_uri", "feature_path") if col in cols]
            if wanted:
                rows = self.query(
                    f"""
                    SELECT {", ".join(wanted)}
                    FROM voiceprint_feature_resource
                    WHERE sample_uid = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (sample_uid,),
                )
                if rows:
                    resources.update(rows[0])
        if not resources["feature_path"]:
            rows = self.query(
                """
                SELECT feature_path
                FROM realtime_model_result
                WHERE sample_uid = %s AND feature_path IS NOT NULL
                ORDER BY inference_time DESC, id DESC
                LIMIT 1
                """,
                (sample_uid,),
            )
            if rows:
                resources["feature_path"] = rows[0]["feature_path"]
                resources["feature_uri"] = rows[0]["feature_path"]
        return resources

    def cable_channel_status(
        self,
        sample_uid: str,
        base_url: str = CABLE_SAMPLE_API_BASE,
        token: str | None = None,
        timeout: int = 60,
    ) -> dict[str, Any]:
        status_url, _ = cable_channel_urls(base_url, sample_uid)
        return http_json("GET", status_url, token=token, timeout=timeout)

    def upload_cable_channel(
        self,
        sample_uid: str,
        channel_no: int,
        payload: dict[str, Any],
        base_url: str = CABLE_SAMPLE_API_BASE,
        token: str | None = None,
        timeout: int = 60,
        force: bool = False,
        check_only: bool = False,
    ) -> dict[str, Any]:
        status = self.cable_channel_status(sample_uid, base_url, token, timeout)
        exists = False
        for channel in status.get("channels", []) if isinstance(status.get("channels"), list) else []:
            if isinstance(channel, dict) and int(channel.get("channel_no") or 0) == channel_no:
                exists = bool(channel.get("exists"))
                break
        if check_only:
            return {"ok": True, "action": "check_only", "sample_uid": sample_uid, "channel_no": channel_no, "status": status}
        if exists and not force:
            return {
                "ok": True,
                "action": "skip_existing_channel",
                "sample_uid": sample_uid,
                "channel_no": channel_no,
                "message": "该通道已经上传，未重复调用写库接口。如需覆盖请加 --force。",
                "status": status,
            }
        _, upload_url = cable_channel_urls(base_url, sample_uid, channel_no)
        result = http_json("POST", upload_url, payload=payload, token=token, timeout=timeout)
        return {
            "ok": bool(result.get("success", result.get("http_status") == 200)),
            "action": "upload_channel",
            "sample_uid": sample_uid,
            "channel_no": channel_no,
            "target_database": CABLE_MYSQL_DB,
            "response": result,
        }

    def upload_cable_sample(
        self,
        payload: dict[str, Any],
        api_url: str = CABLE_SAMPLE_API_URL,
        token: str | None = None,
        timeout: int = 60,
    ) -> dict[str, Any]:
        result = http_json("POST", api_url, payload=payload, token=token, timeout=timeout)
        return {
            "ok": bool(result.get("success", result.get("http_status") == 200)),
            "action": "upload_sample",
            "sample_uid": payload.get("sample_uid"),
            "target_database": CABLE_MYSQL_DB,
            "response": result,
        }

    def cable_sample_status(self, sample_uid: str) -> dict[str, Any]:
        conn = mysql.connector.connect(**cable_db_config())
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM voiceprint_sample WHERE sample_uid = %s", (sample_uid,))
            sample = cur.fetchone()
            cur.execute(
                """
                SELECT *
                FROM voiceprint_audio_file
                WHERE sample_uid = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (sample_uid,),
            )
            audio = cur.fetchone()
            cur.execute(
                """
                SELECT *
                FROM voiceprint_channel
                WHERE sample_uid = %s
                ORDER BY channel_no
                """,
                (sample_uid,),
            )
            channels = cur.fetchall()
            cur.execute(
                """
                SELECT *
                FROM voiceprint_enterprise_annotation
                WHERE sample_uid = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (sample_uid,),
            )
            annotation = cur.fetchone()
            cur.execute(
                """
                SELECT *
                FROM voiceprint_model_result
                WHERE sample_uid = %s
                ORDER BY inference_time DESC, id DESC
                """,
                (sample_uid,),
            )
            model_results = cur.fetchall()
            cur.execute(
                """
                SELECT *
                FROM voiceprint_feature_resource
                WHERE sample_uid = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (sample_uid,),
            )
            features = cur.fetchone()
            cur.execute(
                """
                SELECT channel_no, channel_name, mic_id, channel_file_path, upload_status,
                       sample_rate, bit_depth, duration_sec, source_audio_url
                FROM voiceprint_channel_upload
                WHERE sample_uid = %s
                ORDER BY channel_no
                """,
                (sample_uid,),
            )
            uploaded_channels = cur.fetchall()
            cur.close()
        finally:
            conn.close()

        if not sample:
            received = [int(row["channel_no"]) for row in uploaded_channels]
            return {
                "样本编号": sample_uid,
                "目标数据库": CABLE_MYSQL_DB,
                "样本状态": "未完成入库",
                "已上传通道": uploaded_channels,
                "缺失通道": [channel_no for channel_no in range(1, 5) if channel_no not in received],
            }

        return {
            "样本编号": sample_uid,
            "目标数据库": CABLE_MYSQL_DB,
            "样本状态": sample.get("process_status"),
            "样本信息": {
                "采集时间": sample.get("collect_time"),
                "设备编号": sample.get("device_id"),
                "设备名称": sample.get("device_name"),
                "设备位置": sample.get("device_location"),
                "站点编号": sample.get("site_code"),
                "站点名称": sample.get("site_name"),
                "现场环境": sample.get("site_environment"),
            },
            "采样信息": {
                "采样率": sample.get("sample_rate"),
                "位深": sample.get("bit_depth"),
                "时长秒": sample.get("duration_sec"),
                "通道数": sample.get("channel_count"),
            },
            "音频文件": {
                "文件名": audio.get("file_name") if audio else None,
                "文件路径": audio.get("file_path") if audio else None,
                "Linux文件路径": audio.get("linux_file_path") if audio else None,
                "前端播放地址": audio.get("audio_uri") if audio else None,
                "文件校验值": audio.get("file_sha256") if audio else sample.get("file_sha256"),
            },
            "四通道信息": [
                {
                    "通道号": row.get("channel_no"),
                    "通道名称": row.get("channel_name"),
                    "麦克风编号": row.get("mic_id"),
                    "通道文件路径": row.get("channel_file_path"),
                    "通道播放地址": row.get("channel_audio_uri"),
                    "TDengine表名": row.get("tdengine_table"),
                }
                for row in channels
            ],
            "人工标注": {
                "是否已标注": annotation.get("is_labeled") if annotation else None,
                "是否故障": annotation.get("is_fault") if annotation else None,
                "故障类型": annotation.get("fault_type") if annotation else None,
                "故障标签": annotation.get("fault_label") if annotation else None,
                "故障等级": annotation.get("fault_severity") if annotation else None,
                "标注人员": annotation.get("labeler_name") if annotation else None,
                "标注时间": annotation.get("label_time") if annotation else None,
                "标注备注": annotation.get("annotation_remark") if annotation else None,
            },
            "算法结果": model_results,
            "前端资源": features,
            "分通道上传缓存": uploaded_channels,
        }

    def submit_cable_result_records(self, records: list[dict[str, Any]], commit: bool = False) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        for idx, record in enumerate(records, start=1):
            missing = [field for field in RESULT_REQUIRED_FIELDS if record.get(field) in (None, "")]
            if missing:
                errors.append({"index": idx, "sample_uid": record.get("sample_uid"), "missing_fields": missing})
        if errors:
            return {"ok": False, "commit": commit, "target_database": CABLE_MYSQL_DB, "errors": errors, "actions": actions}

        conn = mysql.connector.connect(**cable_db_config())
        try:
            cur = conn.cursor(dictionary=True)
            for record in records:
                sample_uid = record["sample_uid"]
                cur.execute("SELECT id FROM voiceprint_sample WHERE sample_uid = %s", (sample_uid,))
                if not cur.fetchone():
                    errors.append({"sample_uid": sample_uid, "error": "新中文库 voiceprint_sample 中不存在该样本，请先完成样本/通道入库"})
                    continue

                topk = record.get("topk_result_json") or record.get("topk") or record.get("probabilities")
                row = {
                    "sample_uid": sample_uid,
                    "model_name": record.get("model_name"),
                    "model_version": record.get("model_version"),
                    "algorithm_result": record.get("algorithm_result"),
                    "confidence_score": record.get("confidence_score"),
                    "topk_result_json": to_json_text(topk),
                    "inference_time": mysql_datetime_text(record.get("inference_time")),
                    "need_review": parse_bool(record.get("need_review")) or 0,
                    "result_explain": record.get("result_explain"),
                }
                actions.append({"sample_uid": sample_uid, "action": "insert voiceprint_model_result"})
                actions.append({"sample_uid": sample_uid, "action": "update voiceprint_sample.process_status=INFERRED"})
                if commit:
                    cur.execute(
                        """
                        INSERT INTO voiceprint_model_result (
                            sample_uid, model_name, model_version, algorithm_result, confidence_score,
                            topk_result_json, inference_time, need_review, result_explain
                        ) VALUES (
                            %(sample_uid)s, %(model_name)s, %(model_version)s, %(algorithm_result)s, %(confidence_score)s,
                            %(topk_result_json)s, %(inference_time)s, %(need_review)s, %(result_explain)s
                        )
                        """,
                        row,
                    )
                    cur.execute(
                        """
                        UPDATE voiceprint_sample
                        SET process_status = 'INFERRED', process_stage = 'algorithm_inferred'
                        WHERE sample_uid = %s
                        """,
                        (sample_uid,),
                    )
            if errors:
                conn.rollback()
                return {"ok": False, "commit": commit, "target_database": CABLE_MYSQL_DB, "errors": errors, "actions": actions}
            if commit:
                conn.commit()
            return {"ok": True, "commit": commit, "target_database": CABLE_MYSQL_DB, "total_records": len(records), "actions": actions}
        finally:
            conn.close()

    def database_overview(self, recent_limit: int = 10) -> dict[str, Any]:
        tables = [
            "noise_classification_db",
            "realtime_audio_sample",
            "realtime_audio_channel",
            "realtime_fault_event",
            "realtime_model_result",
            "voiceprint_feature_resource",
        ]
        table_status = []
        for table in tables:
            exists = self.table_exists(table)
            count = None
            if exists:
                count = self.query(f"SELECT COUNT(*) AS count FROM `{table}`")[0]["count"]
            table_status.append({"table": table, "exists": exists, "record_count": count})

        historical = None
        if self.table_exists("noise_classification_db"):
            dash = self.dashboard(top_limit=5, recent_limit=recent_limit, granularity="year")
            historical = {
                "summary": dash["summary"],
                "category_cards": dash["category_cards"],
                "top_categories": dash["top_categories"],
                "recent_samples": dash["recent_samples"],
            }

        realtime = None
        if self.table_exists("realtime_audio_sample"):
            realtime = self.realtime(limit=recent_limit)

        return {
            "meta": {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "database": self.config["database"],
            },
            "tables": table_status,
            "historical_dashboard": historical,
            "realtime_samples": realtime,
        }

    def sample_display(self, sample_uid: str) -> dict[str, Any]:
        detail = self.detail(sample_uid)
        item = detail["item"] or {}
        latest_model = detail["model_results"][0] if detail["model_results"] else {}
        latest_fault = detail["fault_results"][0] if detail["fault_results"] else {}
        features = self.feature_resources(sample_uid)
        return {
            "sample_uid": sample_uid,
            "collect_time": item.get("collect_time"),
            "device_id": item.get("device_id"),
            "device_name": item.get("device_name"),
            "site_code": item.get("site_code"),
            "site_name": item.get("site_name"),
            "site_environment": item.get("site_environment"),
            "process_status": display_status(item.get("process_status")),
            "audio": {
                "file_name": item.get("file_name"),
                "file_path": item.get("file_path"),
                "audio_uri": item.get("audio_uri"),
                "file_sha256": item.get("file_sha256"),
            },
            "sampling": {
                "sample_rate": item.get("sample_rate"),
                "bit_depth": item.get("bit_depth"),
                "duration_sec": item.get("duration_sec"),
                "channel_count": item.get("channel_count"),
            },
            "channels": detail["channels"],
            "features": features,
            "algorithm": {
                "model_name": latest_model.get("model_name"),
                "model_version": latest_model.get("model_version"),
                "algorithm_result": latest_model.get("algorithm_result") or item.get("algorithm_result"),
                "confidence_score": latest_model.get("confidence_score") or item.get("confidence_score"),
                "topk_result_json": latest_model.get("topk_result_json") or item.get("topk_result_json"),
                "need_review": latest_model.get("need_review") or item.get("need_review"),
            },
            "diagnosis": {
                "is_fault": latest_fault.get("is_fault") if latest_fault else item.get("is_fault"),
                "fault_label": latest_fault.get("fault_label") if latest_fault else item.get("fault_label"),
                "fault_type": latest_fault.get("fault_type") if latest_fault else item.get("fault_type"),
                "fault_severity": latest_fault.get("fault_severity") if latest_fault else item.get("fault_severity"),
                "manual_label": None,
                "final_diagnosis": latest_model.get("final_diagnosis") or item.get("final_diagnosis"),
            },
            "raw_detail": detail,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="电缆声纹前端展示与数据链路工具")
    sub = parser.add_subparsers(dest="command", required=True)

    overview = sub.add_parser("database-overview", help="展示数据库整体内容概览、表数量和最新样本")
    overview.add_argument("--recent-limit", type=int, default=10)

    sub.add_parser("connect-db", help="连接 MySQL 数据库，并返回连接状态、版本、可用数据库和表信息")

    dash = sub.add_parser("dashboard", help="展示历史环境声纹大屏统计")
    dash.add_argument("--top-limit", type=int, default=10)
    dash.add_argument("--recent-limit", type=int, default=20)
    dash.add_argument("--granularity", choices=sorted(GRANULARITY_SQL), default="year")

    env_dash = sub.add_parser("environment-dashboard-cn", help="返回环境声音前端大屏精简 JSON，字段全部为中文")
    env_dash.add_argument("--top-limit", type=int, default=10)
    env_dash.add_argument("--output", help="可选：把结果保存到指定 JSON 文件")

    real = sub.add_parser("realtime", help="旧库：展示数据方实时接入样本列表")
    real.add_argument("--limit", type=int, default=50)
    real.add_argument("--device-id")
    real.add_argument("--site-code")
    real.add_argument("--status")
    real.add_argument("--sample-uid")

    list_samples = sub.add_parser("list-samples", help="旧库：展示数据库中的实时样本列表，等同 realtime")
    list_samples.add_argument("--limit", type=int, default=50)
    list_samples.add_argument("--device-id")
    list_samples.add_argument("--site-code")
    list_samples.add_argument("--status")
    list_samples.add_argument("--sample-uid")

    detail_parser = sub.add_parser("detail", help="旧库：查询单条样本数据库详情")
    detail_parser.add_argument("sample_uid")

    sample_display = sub.add_parser("sample-display", help="旧库：按 sample_uid 返回前端展示数据")
    sample_display.add_argument("sample_uid")

    validate = sub.add_parser("validate-manifest", help="校验数据中心 JSON 配置文件")
    validate.add_argument("json_path")
    validate.add_argument("--check-files", action="store_true")

    ingest = sub.add_parser("ingest-manifest", help="旧库：试运行或确认入库数据中心 JSON，会写入 noise_classification.realtime_*")
    ingest.add_argument("json_path")
    ingest.add_argument("--commit", action="store_true")

    pending = sub.add_parser("pending-for-inference", help="给算法查询待推理样本")
    pending.add_argument("--limit", type=int, default=20)

    submit = sub.add_parser("submit-result", help="旧库：试运行或确认回写算法结果，会写入 noise_classification.realtime_*")
    submit.add_argument("json_path")
    submit.add_argument("--commit", action="store_true")

    cable_channel_status = sub.add_parser("cable-channel-status", help="新中文库：查询样本 4 个通道的上传状态")
    cable_channel_status.add_argument("sample_uid")
    cable_channel_status.add_argument("--base-url", default=CABLE_SAMPLE_API_BASE)
    cable_channel_status.add_argument("--timeout", type=int, default=60)
    cable_channel_status.add_argument("--token", default=os.getenv("INGEST_TOKEN"))

    upload_channel = sub.add_parser("upload-channel", help="新中文库：上传单个通道 JSON，自动避免重复上传")
    upload_channel.add_argument("sample_uid")
    upload_channel.add_argument("channel_no", type=int, choices=[1, 2, 3, 4])
    upload_channel.add_argument("json_path")
    upload_channel.add_argument("--base-url", default=CABLE_SAMPLE_API_BASE)
    upload_channel.add_argument("--timeout", type=int, default=60)
    upload_channel.add_argument("--token", default=os.getenv("INGEST_TOKEN"))
    upload_channel.add_argument("--force", action="store_true", help="即使通道已存在，也继续调用上传接口")
    upload_channel.add_argument("--check-only", action="store_true", help="只查询状态，不上传")

    upload_sample = sub.add_parser("upload-sample", help="新中文库：一次性提交样本 JSON 到电缆声纹接口")
    upload_sample.add_argument("json_path")
    upload_sample.add_argument("--url", default=CABLE_SAMPLE_API_URL)
    upload_sample.add_argument("--timeout", type=int, default=60)
    upload_sample.add_argument("--token", default=os.getenv("INGEST_TOKEN"))

    cable_sample_status = sub.add_parser("cable-sample-status", help="新中文库：查询样本、通道、人工标注、算法结果和前端资源")
    cable_sample_status.add_argument("sample_uid")

    cable_submit = sub.add_parser("submit-cable-result", help="新中文库：试运行或确认回写算法结果到 voiceprint_model_result")
    cable_submit.add_argument("json_path")
    cable_submit.add_argument("--commit", action="store_true")

    sub.add_parser("health", help="检查数据库连接")

    args = parser.parse_args()
    client = DbClient()
    if args.command == "health":
        print_json(client.health())
    elif args.command == "connect-db":
        print_json(client.connect_db())
    elif args.command == "database-overview":
        print_json(client.database_overview(args.recent_limit))
    elif args.command == "dashboard":
        print_json(client.dashboard(args.top_limit, args.recent_limit, args.granularity))
    elif args.command == "environment-dashboard-cn":
        payload = client.environment_dashboard_cn(args.top_limit)
        if args.output:
            Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
        print_json(payload)
    elif args.command in {"realtime", "list-samples"}:
        print_json(client.realtime(args.limit, args.device_id, args.site_code, args.status, args.sample_uid))
    elif args.command == "detail":
        print_json(client.detail(args.sample_uid))
    elif args.command == "sample-display":
        print_json(client.sample_display(args.sample_uid))
    elif args.command == "validate-manifest":
        print_json(client.validate_manifest_records(load_json_records(args.json_path), args.check_files))
    elif args.command == "ingest-manifest":
        print_json(client.ingest_manifest(load_json_records(args.json_path), args.commit))
    elif args.command == "pending-for-inference":
        print_json(client.pending_for_inference(args.limit))
    elif args.command == "submit-result":
        print_json(client.submit_result_records(load_json_records(args.json_path), args.commit))
    elif args.command == "cable-channel-status":
        print_json(client.cable_channel_status(args.sample_uid, args.base_url, args.token, args.timeout))
    elif args.command == "upload-channel":
        print_json(
            client.upload_cable_channel(
                args.sample_uid,
                args.channel_no,
                load_json_object(args.json_path),
                args.base_url,
                args.token,
                args.timeout,
                args.force,
                args.check_only,
            )
        )
    elif args.command == "upload-sample":
        print_json(client.upload_cable_sample(load_json_object(args.json_path), args.url, args.token, args.timeout))
    elif args.command == "cable-sample-status":
        print_json(client.cable_sample_status(args.sample_uid))
    elif args.command == "submit-cable-result":
        print_json(client.submit_cable_result_records(load_json_records(args.json_path), args.commit))


if __name__ == "__main__":
    main()
