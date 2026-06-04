---
name: frontend-db-dashboard
description: Work with the cable voiceprint data pipeline and MySQL database. Use when Codex needs to validate data-center JSON manifests, ingest audio index metadata, query pending samples for inference, submit algorithm results, return frontend sample display data including audio and spectrum resources, query dashboard statistics, or explain the cable voiceprint database/API field design.
---

# 电缆声纹数据链路

## 核心用途

使用这个 skill 时，围绕这条链路工作：

```text
数据中心 JSON 配置文件
-> 接口服务接收和校验
-> 数据库保存样本、音频索引、4 通道信息
-> 算法获取待推理样本
-> 算法结果和故障诊断写回数据库
-> 前端按 sample_uid 获取音频、频谱、特征和诊断结果
```

这个 skill 保留历史大屏查询能力，但优先使用新的电缆声纹数据接入和前端展示口径。

企业 4 通道 wav 实时接入使用新接口：

```text
POST http://192.168.10.116:8000/api/v1/cable-voiceprint/samples
```

该接口使用“Linux 上的 wav 文件路径 + JSON 元数据”模式：wav 需要先放到 Linux 服务器；可以是 1 个四通道 wav，也可以是 4 个单通道 wav。JSON 里用 `file_path` 指向单文件 wav 或样本文件夹；四单通道模式再用 `channels[].channel_file_path` 指向每个通道文件。接口会写入 MySQL 中文库 `电缆声纹检测库`，并把 4 通道时序数据写入 TDengine 中文库 `电缆声纹时序库`。

## 快速连接

默认连接：

```text
主机：192.168.10.116
端口：3306
数据库：noise_classification
用户：remote_user
```

可用环境变量覆盖：`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`。

## 常用命令

连接数据库并返回连接状态、MySQL 版本、可用数据库和表信息：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py connect-db
```

检查数据库连接：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py health
```

展示数据库整体内容：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py database-overview --recent-limit 10
```

展示历史环境声纹大屏统计：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py dashboard --top-limit 10 --recent-limit 20
```

生成环境声音前端大屏精简 JSON，字段全部为中文：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py environment-dashboard-cn --output /Users/a1111/mysql/环境声音前端展示数据_20260604.json
```

展示企业实时接入样本列表：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py list-samples --limit 50
```

按设备、站点、状态筛选样本列表：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py list-samples --device-id 设备编号 --site-code 站点编号 --status 待处理
```

校验数据中心 JSON 配置文件：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py validate-manifest /path/to/manifest.json
```

试运行入库，不写数据库：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py ingest-manifest /path/to/manifest.json
```

确认入库：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py ingest-manifest /path/to/manifest.json --commit
```

给算法查询待推理样本：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py pending-for-inference --limit 20
```

试运行算法结果回写，不写数据库：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py submit-result /path/to/result.json
```

确认算法结果回写：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py submit-result /path/to/result.json --commit
```

查询甲方前端单条样本展示数据：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py sample-display SAMPLE_ID
```

电缆声纹 4 通道新接口建库和端到端测试：

```bash
python3 /home/hzjq/ml_pipeline/process/setup_cable_voiceprint_databases.py
python3 /home/hzjq/ml_pipeline/process/test_cable_voiceprint_protocol.py
python3 /home/hzjq/ml_pipeline/process/test_cable_voiceprint_four_mono_protocol.py
```

## 工作流

1. 用户要连接或确认远程 MySQL 可用时，运行 `connect-db`。
2. 用户要看数据库整体内容时，运行 `database-overview`。
3. 用户要看完整历史大屏统计时，运行 `dashboard`。
4. 用户要给前端一个类似“环境声音数据库”大屏的数据源时，运行 `environment-dashboard-cn`；它只返回中文字段的环境声音数据，包含 `汇总`、`大类别`、`环境声音TOP10`、`小类别数量统计`。
5. 用户要看企业接入样本列表时，运行 `list-samples` 或 `realtime`，不需要提供 `sample_uid`。
6. 用户给出某个 `sample_uid` 时，运行 `sample-display SAMPLE_ID`，返回音频、频谱、波形、算法结果、故障结果和前端展示摘要。
7. 接到数据中心字段、JSON、接口或配置文件需求时，先读取 `references/frontend_db_schema.md`。
8. 数据中心给 JSON 后，先运行 `validate-manifest`，确认必填字段、4 通道结构和音频访问地址。
9. 入库前默认运行 `ingest-manifest` 试运行；只有用户明确要写库时才加 `--commit`。
10. 算法需要数据时，运行 `pending-for-inference`，返回音频路径、音频访问地址、采样参数、4 通道信息和现场环境。
11. 算法完成后，用 `submit-result` 校验结果；只有用户明确要写库时才加 `--commit`。
12. 用户询问企业如何传 4 通道 wav 文件、如何调用新中文库接口或如何构造请求 JSON 时，读取 `references/cable_voiceprint_realtime_api.md`。

## 字段口径

数据中心主要提供：

```text
采集基础信息、设备与通道信息、采样参数、音频文件索引、现场环境
```

我方系统生成或回填：

```text
处理状态、算法结果、故障标签、人工确认结果、频谱图/波形图/特征资源地址
```

前端播放音频需要 `audio_uri`。数据库内部的 `created_at`、`updated_at` 可以保留，但不要作为给甲方解释的展示字段。

## 参考资料

需要字段、JSON 示例、接口返回格式和数据库表建议时，读取：

```text
/Users/a1111/.codex/skills/frontend-db-dashboard/references/frontend_db_schema.md
```

需要 4 通道实时接口的文件传输条件、curl 示例、中文库名和测试脚本时，读取：

```text
/Users/a1111/.codex/skills/frontend-db-dashboard/references/cable_voiceprint_realtime_api.md
```
