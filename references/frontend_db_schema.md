# 前端数据库展示字段参考

## 数据库连接

默认连接远程声纹检测数据库：

```text
主机：192.168.10.116
端口：3306
数据库：noise_classification
用户：remote_user
```

支持环境变量覆盖：`DB_HOST`、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`。

## 历史大屏表

历史前端大屏从 `noise_classification_db` 聚合：

| 字段 | 中文含义 |
|---|---|
| `file_path` | 文件路径 |
| `service_environment` | 一级环境/场景 |
| `noise_source` | 声纹类别 |
| `source_dataset` | 来源数据集 |
| `machine_id` | 设备编号 |
| `operation_status` | 状态或标签 |
| `sample_rate` | 采样率 |
| `duration_sec` | 音频时长 |
| `channels` | 通道数 |
| `acquisition_time` | 采集时间 |
| `node_id` | 通道或点位编号 |

## 实时企业输入表

实时采集第一版使用五张表：

1. `realtime_audio_sample`：样本主表，包含采样、存储、设备、现场、电缆工况。
2. `realtime_audio_channel`：4 通道与麦克风位置。
3. `realtime_fault_event`：故障事件和故障分类。
4. `realtime_fault_annotation`：人工标注、标注员工、复核和最终标签。
5. `realtime_model_result`：模型推理结果。

## 必要字段

第一版保留这些必要字段：

| 分类 | 字段 |
|---|---|
| 样本标识 | `sample_uid`、`batch_id`、`source_system` |
| 采样元数据 | `acquisition_start_time`、`duration_sec`、`sample_rate`、`bit_depth`、`channels` |
| 存储元数据 | `file_name`、`file_path`、`audio_uri`、`file_sha256`、`file_size_bytes` |
| 设备现场 | `device_id`、`device_name`、`site_code`、`site_name`、`province`、`city` |
| 电缆工况 | `cable_id`、`cable_name`、`voltage_level_kv`、`phase`、`is_grounded`、`is_interference` |
| 故障数据 | `is_fault`、`fault_l1`、`fault_l2`、`voiceprint_label`、`internal_fault_type`、`defect_type_id`、`fault_severity` |
| 人工标注 | `annotator_id`、`annotator_name`、`annotation_status`、`is_final_label` |
| 模型结果 | `model_name`、`model_version`、`top1_label`、`top1_prob`、`top2_label`、`top2_prob`、`top3_label`、`top3_prob`、`final_diagnosis` |

不把增益设置、灵敏度、校准状态、通道信噪比等硬件调试字段放入第一版。

## 前端接口口径

历史大屏：

```text
GET /api/frontend-dashboard
```

企业输入数据列表：

```text
GET /api/realtime-inputs
```

企业输入数据详情：

```text
GET /api/realtime-inputs/样本唯一编号
```

这些接口已经在 `/Users/a1111/mysql/process/frontend_dashboard_api.py` 中实现；skill 脚本可不启动服务直接查询数据库。
