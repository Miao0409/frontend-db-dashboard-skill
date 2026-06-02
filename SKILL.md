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

检查数据库连接：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py health
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

兼容历史大屏：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py dashboard --top-limit 10 --recent-limit 20
```

## 工作流

1. 接到数据中心字段、JSON、接口或配置文件需求时，先读取 `references/frontend_db_schema.md`。
2. 数据中心给 JSON 后，先运行 `validate-manifest`，确认必填字段、4 通道结构和音频访问地址。
3. 入库前默认运行 `ingest-manifest` 试运行；只有用户明确要写库时才加 `--commit`。
4. 算法需要数据时，运行 `pending-for-inference`，返回音频路径、音频访问地址、采样参数、4 通道信息和现场环境。
5. 算法完成后，用 `submit-result` 校验结果；只有用户明确要写库时才加 `--commit`。
6. 甲方按样本编号查展示数据时，运行 `sample-display SAMPLE_ID`，返回音频、频谱、波形、算法结果、故障结果和前端展示摘要。

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
