---
name: frontend-db-dashboard
description: Work with the cable voiceprint data pipeline, bundled demo fault-diagnosis algorithm, and MySQL database. Use when Codex needs to validate data-provider JSON manifests, ingest audio index metadata, query pending samples for inference, train or run the cable voiceprint demo classifier, generate fault labels/probabilities/waveform/spectrum resources, submit algorithm results, return frontend sample display data including audio and spectrum resources, query dashboard statistics, or explain the cable voiceprint database/API field design.
---

# 电缆声纹数据链路

## 核心用途

使用这个 skill 时，围绕这条链路工作：

```text
数据方 JSON 配置文件
-> 接口服务接收和校验
-> 数据库保存样本、音频索引、4 通道信息
-> 算法获取待推理样本
-> 算法结果和故障诊断写回数据库
-> 前端按 sample_uid 获取音频、频谱、特征和诊断结果
```

这个 skill 保留历史大屏查询能力，但优先使用新的电缆声纹数据接入和前端展示口径。

数据方 4 通道 wav 实时接入使用新接口：

```text
POST http://192.168.10.116:8000/api/v1/cable-voiceprint/samples
```

该接口优先支持“数据方 wav 地址 + Linux 保存地址 + JSON 元数据”模式：JSON 里用 `source_audio_url` 提供数据方文件服务器上的 wav 地址，用 `linux_save_path` 指定下载到我方 Linux 的保存路径。接口会自动下载 wav、读取采样参数、计算 `file_sha256`，再写入 MySQL 中文库 `电缆声纹检测库`，并把波形时序数据写入 TDengine 中文库 `电缆声纹时序库`。接口也兼容旧模式：1 个 Linux 本地四通道 wav，或 4 个 Linux 本地单通道 wav。

## 快速连接

默认连接：

```text
主机：192.168.10.116
端口：3306
历史环境数据库：noise_classification
电缆声纹新数据库：电缆声纹检测库
用户：remote_user
```

可用环境变量覆盖：`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`。
电缆声纹新库名可用 `CABLE_MYSQL_DB` 覆盖，默认是 `电缆声纹检测库`。

## 常用命令

连接数据库并返回连接状态、MySQL 版本、可用数据库和表信息：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/connect_database.py
```

也可以通过综合工具运行同样的连接检查：

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

新上传分支：查询某个样本当前 4 个通道是否已经上传：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py cable-channel-status SAMPLE_ID
```

新上传分支：上传单个通道 JSON。这个命令会先查通道状态，如果该通道已经存在则跳过，避免重复上传。写入目标是 MySQL 中文库 `电缆声纹检测库` 和 TDengine 中文库 `电缆声纹时序库`：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py upload-channel SAMPLE_ID 1 /path/to/channel_1.json
```

新上传分支：一次性提交样本 JSON：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py upload-sample /path/to/sample.json
```

新上传分支：查询中文库里的样本、通道、人工标注、算法结果和前端资源：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py cable-sample-status SAMPLE_ID
```

新上传分支：算法结果回写到中文库 `voiceprint_model_result`。默认先试运行，确认写库时加 `--commit`：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py submit-cable-result /path/to/result.json
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py submit-cable-result /path/to/result.json --commit
```

旧实时表分支：展示旧实时接入样本列表。这个分支读取 `noise_classification.realtime_*`，不要用于新的电缆声纹入库：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py list-samples --limit 50
```

旧实时表分支：按设备、站点、状态筛选样本列表：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py list-samples --device-id 设备编号 --site-code 站点编号 --status 待处理
```

旧字段口径：校验数据方 JSON 配置文件。新上传分支的 JSON 以 `upload-channel` / `upload-sample` 实际接口校验为准：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py validate-manifest /path/to/manifest.json
```

旧实时表分支：试运行入库，不写数据库。这个命令写入旧库 `noise_classification.realtime_*`，新的电缆声纹上传不要使用它：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py ingest-manifest /path/to/manifest.json
```

旧实时表分支：确认入库：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py ingest-manifest /path/to/manifest.json --commit
```

给算法查询待推理样本：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py pending-for-inference --limit 20
```

旧实时表分支：试运行算法结果回写，不写数据库：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py submit-result /path/to/result.json
```

旧实时表分支：确认算法结果回写：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py submit-result /path/to/result.json --commit
```

旧实时表分支：查询数据方前端单条样本展示数据：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py sample-display SAMPLE_ID
```

数据方使用 Python `requests` 提交 JSON 文件：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/cable_voiceprint_request_demo.py --write-example sample.json
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/cable_voiceprint_request_demo.py --json-file sample.json
```

电缆声纹 4 通道新接口建库和端到端测试：

```bash
python3 /home/hzjq/ml_pipeline/process/setup_cable_voiceprint_databases.py
python3 /home/hzjq/ml_pipeline/process/test_cable_voiceprint_remote_audio_url_protocol.py
python3 /home/hzjq/ml_pipeline/process/test_cable_voiceprint_protocol.py
python3 /home/hzjq/ml_pipeline/process/test_cable_voiceprint_four_mono_protocol.py
```

## 工作流

1. 用户要连接或确认远程 MySQL 可用时，运行 `connect-db`。
2. 用户要看数据库整体内容时，运行 `database-overview`。
3. 用户要看完整历史大屏统计时，运行 `dashboard`。
4. 用户要给前端一个类似“环境声音数据库”大屏的数据源时，运行 `environment-dashboard-cn`；它只返回中文字段的环境声音数据，包含 `汇总`、`大类别`、`环境声音TOP10`、`小类别数量统计`。
5. 用户要上传新的电缆声纹数据时，优先运行 `upload-channel` 或 `upload-sample`，不要运行 `ingest-manifest`。
6. 用户要看新中文库样本状态时，运行 `cable-sample-status SAMPLE_ID`。
7. 用户要把算法诊断结果写回新中文库时，运行 `submit-cable-result`，确认写库时加 `--commit`。
8. 用户要看旧实时表样本列表时，才运行 `list-samples` 或 `realtime`。
9. 用户给出旧实时表里的 `sample_uid` 时，运行 `sample-display SAMPLE_ID`。
10. 接到数据方字段、JSON、接口或配置文件需求时，先读取 `references/frontend_db_schema.md`。
11. 只有明确处理旧实时表时，才使用 `validate-manifest`、`ingest-manifest`、`pending-for-inference`、`submit-result`。
12. 用户询问数据方如何传 wav 文件、如何从数据方文件服务器下载 wav、如何调用新中文库接口或如何构造请求 JSON 时，读取 `references/cable_voiceprint_realtime_api.md`。

## 字段口径

数据方主要提供：

```text
样本标识、采集时间、设备信息、数据方 wav 地址、Linux 保存路径、现场信息、人工故障打标
```

我方系统生成或回填：

```text
采样参数、文件校验值、Linux 实际文件路径、处理状态、算法结果、频谱图/波形图/特征资源地址
```

前端播放音频需要 `audio_uri`。数据库内部的 `created_at`、`updated_at` 可以保留，但不要作为给数据方解释的展示字段。

## 参考资料

需要字段、JSON 示例、接口返回格式和数据库表建议时，读取：

```text
/Users/a1111/.codex/skills/frontend-db-dashboard/references/frontend_db_schema.md
```

需要 4 通道实时接口的文件传输条件、curl 示例、中文库名和测试脚本时，读取：

```text
/Users/a1111/.codex/skills/frontend-db-dashboard/references/cable_voiceprint_realtime_api.md
```

## Bundled Algorithm Demo

Use `scripts/voiceprint_algorithm_demo.py` when the task requires running the cable voiceprint demo algorithm, training the 9-class lightweight classifier, generating a database-compatible result JSON, creating waveform/spectrum/feature resources, or submitting algorithm results.

Common commands:

```bash
python3 scripts/voiceprint_algorithm_demo.py train --data-dir /path/to/data --model-dir /path/to/models/voiceprint_demo --max-per-class 30
python3 scripts/voiceprint_algorithm_demo.py infer-one --audio /path/to/sample.wav --sample-uid SAMPLE_001 --model-dir /path/to/models/voiceprint_demo --output-dir /path/to/outputs --result-json /path/to/result.json
python3 scripts/voiceprint_algorithm_demo.py infer-pending --pending-json /path/to/pending_samples.json --model-dir /path/to/models/voiceprint_demo --output-dir /path/to/outputs --result-json /path/to/results.json
python3 scripts/voiceprint_algorithm_demo.py submit-result /path/to/results.json
python3 scripts/voiceprint_algorithm_demo.py submit-result /path/to/results.json --commit
```

Only add `--commit` when the user explicitly asks to write to MySQL. For full algorithm inputs, outputs, labels, and result JSON fields, read:

```text
references/voiceprint_algorithm_demo.md
```
