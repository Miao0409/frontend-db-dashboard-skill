# 电缆声纹数据链路参考

## 1. 数据流程

```text
硬件采集端
-> 数据方保存音频文件
-> 数据方生成 JSON 配置文件
-> 我方接口接收 JSON
-> 数据库保存样本、文件索引、4 通道信息
-> 算法接口查询待推理样本
-> 算法读取音频并生成诊断结果、频谱图、波形图等资源
-> 算法结果写回数据库
-> 前端按 sample_uid 查询音频、频谱、特征和诊断结果
```

数据方不直接连接 MySQL。它只需要把 wav 放在数据方文件服务器上，并通过 JSON 提供音频源地址、Linux 保存地址和采集/打标信息；接口会下载 wav、读取采样参数、计算文件校验值并写入 MySQL 和 TDengine。

## 2. 数据方 JSON 字段

数据方必须提供这些字段：

| 字段 | 中文含义 | 说明 |
| --- | --- | --- |
| `protocol_version` | 协议版本 | 当前推荐 `1.1`。 |
| `request_id` | 请求编号 | 用于幂等、排查和日志追踪。 |
| `sample_uid` | 样本编号 | 每条录音唯一编号。 |
| `collect_time` | 采集时间 | 音频实际采集时间。 |
| `device_id` | 设备编号 | 采集设备或传感器主机编号。 |
| `source_audio_url` | 数据方音频地址 | 数据方服务器上的 wav 下载地址，必须是 `http` 或 `https`。 |
| `linux_save_path` | Linux 保存路径 | wav 下载到我方 Linux 后的保存路径。 |
| `manual_annotation` | 人工打标对象 | 数据方对采集样本的故障标签对象。 |

数据方可以提供这些字段：

| 字段 | 中文含义 | 说明 |
| --- | --- | --- |
| `collect_task_id` | 采集任务编号 | 用于追踪同一次采集任务。 |
| `batch_id` | 批次编号 | 对应一次批量上传或配置文件批次。 |
| `device_name` | 设备名称 | 便于前端展示。 |
| `device_location` | 设备位置 | 设备安装点或采集点描述。 |
| `audio_format` | 音频格式 | 例如 wav、flac、pcm。 |
| `channel_storage_mode` | 通道存储方式 | 单通道文件、单文件四通道或四个单通道文件。 |
| `channel_map` | 通道映射 | 记录各通道对应的麦克风位置或含义。 |
| `channels` | 四单通道文件列表 | 当一条样本由 4 个单通道 wav 组成时填写。 |
| `site_code` | 站点编号 | 现场或线路区段编号。 |
| `site_name` | 现场名称 | 前端展示名称。 |
| `site_environment` | 现场环境 | 例如电缆沟、户外、站内、实验室。 |
| `noise_environment_label` | 环境声音类别 | 用于统计和筛选。 |
| `weather` | 天气情况 | 户外采集时使用。 |
| `site_remark` | 现场备注 | 现场补充说明。 |

数据方不需要提供这些字段：

```text
sample_rate
bit_depth
duration_sec
channel_count
file_name
file_path
file_sha256
file_size_bytes
audio_uri
process_status
algorithm_result
confidence_score
spectrum_uri
waveform_uri
```

这些字段由我方接口、算法或数据库流程读取、生成或维护。

## 3. JSON 示例

数据方 wav 地址模式：

```json
{
  "protocol_version": "1.1",
  "request_id": "REQ_SAMPLE_001",
  "sample_uid": "SAMPLE_001",
  "collect_time": "2026-06-05T10:30:00+08:00",
  "collect_task_id": "TASK_20260603_001",
  "batch_id": "BATCH_20260603_001",
  "device_id": "DEV_001",
  "device_name": "电缆声纹采集设备01",
  "device_location": "1号电缆沟入口",
  "audio_format": "wav",
  "source_audio_url": "http://数据方服务器/audio/SAMPLE_001.wav",
  "linux_save_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_001/SAMPLE_001.wav",
  "site_code": "SITE_001",
  "site_name": "某变电站",
  "site_environment": "电缆沟",
  "manual_annotation": {
    "is_labeled": true,
    "is_fault": true,
    "fault_type": "内源故障",
    "fault_label": "局部放电",
    "fault_severity": "中等",
    "labeler_id": "EMP_001",
    "labeler_name": "张三",
    "label_time": "2026-06-05T10:31:00+08:00"
  }
}
```

四个单通道文件时，可使用 `channels`：

```json
{
  "protocol_version": "1.1",
  "request_id": "REQ_SAMPLE_002",
  "sample_uid": "SAMPLE_002",
  "collect_time": "2026-06-05T10:35:00+08:00",
  "device_id": "DEV_001",
  "channel_storage_mode": "四个单通道文件",
  "site_code": "SITE_001",
  "site_name": "某变电站",
  "site_environment": "电缆沟",
  "channels": [
    {
      "channel_no": 1,
      "channel_name": "通道1",
      "source_audio_url": "http://数据方服务器/audio/SAMPLE_002/ch1.wav",
      "linux_save_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_002/ch1.wav"
    },
    {
      "channel_no": 2,
      "channel_name": "通道2",
      "source_audio_url": "http://数据方服务器/audio/SAMPLE_002/ch2.wav",
      "linux_save_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_002/ch2.wav"
    }
  ]
}
```

## 4. 数据库表建议

实际表名可按项目规范调整，但建议至少分成这些逻辑表：

| 表 | 作用 |
| --- | --- |
| `voiceprint_sample` | 保存样本编号、采集时间、设备、采样参数、现场环境、处理状态。 |
| `voiceprint_audio_file` | 保存音频文件名、文件路径、音频访问地址、校验值、文件大小。 |
| `voiceprint_channel` | 保存 4 通道编号、通道名称、通道文件地址。 |
| `voiceprint_enterprise_annotation` | 保存数据方人工打标结果；这是当前数据库中的历史表名。 |
| `voiceprint_model_result` | 保存模型名称、版本、算法结果、置信度、候选结果。 |
| `voiceprint_feature_resource` | 保存频谱图、波形图、特征文件、特征 JSON 等前端展示资源。 |

当前远程库里已有的第一版表包括：

```text
realtime_audio_sample
realtime_audio_channel
realtime_fault_event
realtime_fault_annotation
realtime_model_result
```

skill 脚本会优先兼容这些已有表。未来如果新增 `voiceprint_feature_resource`，`sample-display` 会自动把频谱图和波形图资源一起返回。

## 5. 处理状态

推荐状态：

| 状态 | 含义 |
| --- | --- |
| `待处理` | 已接收 JSON，但算法还未处理。 |
| `处理中` | 算法正在处理。 |
| `已推理` | 算法结果已写回。 |
| `待人工复核` | 算法置信度低或业务要求人工确认。 |
| `已完成` | 最终诊断结果已确定。 |
| `处理失败` | 音频读取、预处理或推理失败。 |

旧表若使用英文状态，可映射为：

```text
待处理 -> PENDING
处理中 -> PROCESSING
已推理 -> INFERRED
处理失败 -> FAILED
```

## 6. 算法接口数据

算法查询待推理样本时，至少需要：

```json
{
  "sample_uid": "SAMPLE_001",
  "file_path": "/data/audio/SAMPLE_001.wav",
  "audio_uri": "https://example.com/audio/SAMPLE_001.wav",
  "sample_rate": 48000,
  "bit_depth": 24,
  "duration_sec": 10.5,
  "channel_count": 4,
  "channels": [
    {
      "channel_no": 1,
      "channel_name": "通道1"
    }
  ],
  "site_environment": "电缆沟"
}
```

算法回写结果时，建议使用：

```json
{
  "sample_uid": "SAMPLE_001",
  "model_name": "cable_voiceprint_fault_model",
  "model_version": "v1.0.0",
  "algorithm_result": "局部放电",
  "confidence_score": 0.93,
  "topk_result_json": [
    {
      "label": "局部放电",
      "score": 0.93
    },
    {
      "label": "外部干扰",
      "score": 0.04
    }
  ],
  "is_fault": true,
  "fault_label": "局部放电",
  "fault_type": "内源故障",
  "spectrum_uri": "https://example.com/features/SAMPLE_001_spectrum.png",
  "waveform_uri": "https://example.com/features/SAMPLE_001_waveform.png",
  "feature_uri": "https://example.com/features/SAMPLE_001.json",
  "need_review": true,
  "result_explain": "疑似局部放电，需要复核"
}
```

## 7. 前端接口口径

数据库整体概览：

```text
GET /api/database-overview
```

前端列表：

```text
GET /api/samples
```

前端单条详情：

```text
GET /api/samples/{sample_uid}
```

建议返回：

```json
{
  "sample_uid": "SAMPLE_001",
  "collect_time": "2026-06-03 10:30:00",
  "device_id": "DEV_001",
  "site_name": "某变电站",
  "site_environment": "电缆沟",
  "process_status": "已推理",
  "audio": {
    "file_name": "SAMPLE_001.wav",
    "file_path": "/data/audio/SAMPLE_001.wav",
    "audio_uri": "https://example.com/audio/SAMPLE_001.wav"
  },
  "features": {
    "spectrum_uri": "https://example.com/features/SAMPLE_001_spectrum.png",
    "waveform_uri": "https://example.com/features/SAMPLE_001_waveform.png",
    "feature_uri": "https://example.com/features/SAMPLE_001.json"
  },
  "algorithm": {
    "algorithm_result": "局部放电",
    "confidence_score": 0.93,
    "topk_result_json": []
  },
  "diagnosis": {
    "is_fault": true,
    "fault_label": "局部放电",
    "fault_type": "内源故障",
    "need_review": true,
    "result_explain": "疑似局部放电，需要复核"
  }
}
```

历史环境声纹大屏仍可使用：

```text
GET /api/frontend-dashboard
```

skill 命令对应关系：

| 需求 | 命令 |
| --- | --- |
| 展示数据库整体内容 | `database-overview` |
| 展示历史环境声纹大屏 | `dashboard` |
| 展示数据方实时接入样本列表 | `list-samples` 或 `realtime` |
| 按 `sample_uid` 展示单条样本 | `sample-display SAMPLE_ID` |
| 查询单条样本数据库原始详情 | `detail SAMPLE_ID` |
