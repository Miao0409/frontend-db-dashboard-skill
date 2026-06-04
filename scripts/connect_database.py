#!/usr/bin/env python3
from __future__ import annotations

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
        raise SystemExit("缺少 mysql-connector-python。请先安装该依赖。") from exc


def db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "192.168.10.116"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "remote_user"),
        "password": os.getenv("DB_PASSWORD", "VoicePrint2025!"),
        "database": os.getenv("DB_NAME", "noise_classification"),
        "ssl_disabled": os.getenv("DB_SSL_DISABLED", "true").lower() != "false",
    }


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def query(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()


def connect_database() -> dict[str, Any]:
    config = db_config()
    conn = mysql.connector.connect(**config)
    try:
        health = query(conn, "SELECT VERSION() AS version, DATABASE() AS database_name")[0]
        database_rows = query(conn, "SHOW DATABASES")
        system_databases = {"information_schema", "mysql", "performance_schema", "sys"}
        visible_databases = [
            next(iter(row.values()))
            for row in database_rows
            if next(iter(row.values())) not in system_databases
        ]

        databases = []
        for database_name in visible_databases:
            table_rows = query(
                conn,
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
                "主机": config["host"],
                "端口": config["port"],
                "用户": config["user"],
                "当前数据库": health["database_name"],
                "版本": health["version"],
            },
            "可用数据库": databases,
        }
    finally:
        conn.close()


def main() -> None:
    print(json.dumps(connect_database(), ensure_ascii=False, indent=2, default=json_default))


if __name__ == "__main__":
    main()
