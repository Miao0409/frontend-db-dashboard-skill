---
name: frontend-db-dashboard
description: Connect to the cable voiceprint MySQL database and retrieve frontend display data. Use when Codex needs to query the remote sound/cable voiceprint database for dashboard statistics, category rankings, time distributions, latest samples, enterprise-entered realtime data, realtime sample details, or to explain the frontend database API and required fields.
---

# 前端数据库展示

## 核心用途

使用这个 skill 时，直接连接电缆声纹检测数据库，获取前端展示所需信息：

1. 历史环境声纹大屏统计。
2. 企业输入的实时采集数据列表。
3. 单条实时样本详情，包括 4 通道、人工标注和模型结果。
4. 数据库字段和接口口径说明。

## 快速查询

默认连接：

```text
主机：192.168.10.116
端口：3306
数据库：noise_classification
用户：remote_user
```

如需覆盖连接参数，设置环境变量：

```bash
DB_HOST=192.168.10.116 DB_PORT=3306 DB_USER=remote_user DB_PASSWORD='密码' DB_NAME=noise_classification
```

## 常用命令

历史大屏统计：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py dashboard --top-limit 10 --recent-limit 20
```

企业输入数据列表：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py realtime --limit 50
```

按设备或站点筛选企业输入数据：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py realtime --device-id 设备编号 --site-code 站点编号
```

查询单条实时样本详情：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py detail 样本唯一编号
```

检查数据库连接：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py health
```

## 工作流

1. 先运行 `health` 确认能连库。
2. 用户要“大屏、统计、排行、前端展示”时，运行 `dashboard`。
3. 用户要“企业输入的数据、实时采集、上传记录、清单导入记录”时，运行 `realtime`。
4. 用户给出某个样本唯一编号时，运行 `detail`。
5. 需要解释字段或接口时，读取 `references/frontend_db_schema.md`。

## 输出口径

`dashboard` 返回：

1. `summary`：数据总量、总时长、类别数、时间范围。
2. `category_cards`：一级环境/场景统计。
3. `top_categories`：类别排行。
4. `time_distribution`：按年、月、日统计。
5. `recent_samples`：最新样本。

`realtime` 返回：

1. `summary`：企业输入数据总数、已上传数、已推理数、失败数、故障数。
2. `items`：企业输入样本列表，含采样、存储、设备、电缆工况、故障、标注、模型摘要。

`detail` 返回：

1. `item`：样本主信息。
2. `channels`：4 通道与麦克风位置。
3. `annotations`：人工标注和复核记录。
4. `model_results`：模型推理历史。
