# 电缆声纹数据链路参考

## 1. 数据流程

```text
硬件采集端
-> 数据中心保存音频文件
-> 数据中心生成 JSON 配置文件
-> 我方接口接收 JSON
-> 数据库保存样本、文件索引、4 通道信息
-> 算法接口查询待推理样本
-> 算法读取音频并生成诊断结果、频谱图、波形图等资源
-> 算法结果写回数据库
-> 前端按 sample_uid 查询音频、频谱、特征和诊断结果
```

数据中心不直接连接 MySQL。它只需要把音频文件放到约定目录或对象存储中，并提供 JSON 配置文件。

## 2. 数据中心 JSON 字段

数据中心必须提供这些字段：

| 字段 | 中文含义 | 说明 |
| --- | --- | --- |
| `sample_uid` | 样本编号 | 每条录音唯一编号。 |
| `collect_time` | 采集时间 | 音频实际采集时间。 |
| `device_id` | 设备编号 | 采集设备或传感器主机编号。 |
| `channel_count` | 通道数 | 4 通道数据填写 4。 |
| `sample_rate` | 采样率 | 例如 48000。 |
| `bit_depth` | 位深 | 例如 16、24、32。 |
| `duration_sec` | 音频时长秒 | 用于算法输入校验和前端统计。 |
| `file_name` | 音频文件名 | 原始文件名。 |
| `file_path` | 音频文件路径 | 后端或算法读取音频使用。 |
| `file_sha256` | 文件校验值 | 用于去重和完整性校验。 |
| `audio_uri` | 音频访问地址 | 前端播放音频使用。 |
| `site_code` | 站点编号 | 现场或线路区段编号。 |
| `site_name` | 现场名称 | 前端展示名称。 |
| `site_environment` | 现场环境 | 例如电缆沟、户外、站内、实验室。 |

数据中心可以提供这些字段：

| 字段 | 中文含义 | 说明 |
| --- | --- | --- |
| `collect_task_id` | 采集任务编号 | 用于追踪同一次采集任务。 |
| `batch_id` | 批次编号 | 对应一次批量上传或配置文件批次。 |
| `device_name` | 设备名称 | 便于前端展示。 |
| `device_location` | 设备位置 | 设备安装点或采集点描述。 |
| `audio_format` | 音频格式 | 例如 wav、flac、pcm。 |
| `channel_storage_mode` | 通道存储方式 | 单文件四通道或四个单通道文件。 |
| `channel_map_json` | 通道映射 | 记录各通道对应的麦克风位置或含义。 |
| `file_size_bytes` | 文件大小字节 | 可由数据中心给，也可由后端计算。 |
| `feature_path` | 特征文件路径 | 如果数据中心已提前生成特征文件。 |
| `noise_environment_label` | 环境声音类别 | 用于统计和筛选。 |
| `weather` | 天气情况 | 户外采集时使用。 |
| `site_remark` | 现场备注 | 现场补充说明。 |

数据中心不需要提供这些字段：

```text
process_status
algorithm_result
confidence_score
fault_label
fault_type
insulation_status
manual_label
final_diagnosis
spectrum_uri
waveform_uri
```

这些字段由我方接口、算法或人工确认流程生成。

## 3. JSON 示例

单文件四通道：

```json
{
  "sample_uid": "SAMPLE_001",
  "collect_time": "2026-06-03 10:30:00",
  "collect_task_id": "TASK_20260603_001",
  "batch_id": "BATCH_20260603_001",
  "device_id": "DEV_001",
  "device_name": "电缆声纹采集设备01",
  "device_location": "1号电缆沟入口",
  "channel_count": 4,
  "sample_rate": 48000,
  "bit_depth": 24,
  "duration_sec": 10.5,
  "audio_format": "wav",
  "channel_storage_mode": "单文件四通道",
  "channel_map_json": {
    "1": "通道1",
    "2": "通道2",
    "3": "通道3",
    "4": "通道4"
  },
  "file_name": "SAMPLE_001.wav",
  "file_path": "/data/audio/SAMPLE_001.wav",
  "audio_uri": "https://example.com/audio/SAMPLE_001.wav",
  "file_sha256": "sha256-value",
  "file_size_bytes": 1024000,
  "site_code": "SITE_001",
  "site_name": "某变电站",
  "site_environment": "电缆沟"
}
```

四个单通道文件时，可增加 `channels`：

```json
{
  "sample_uid": "SAMPLE_002",
  "collect_time": "2026-06-03 10:35:00",
  "device_id": "DEV_001",
  "channel_count": 4,
  "sample_rate": 48000,
  "bit_depth": 24,
  "duration_sec": 10.5,
  "file_name": "SAMPLE_002",
  "file_path": "/data/audio/SAMPLE_002/",
  "audio_uri": "https://example.com/audio/SAMPLE_002/",
  "file_sha256": "sha256-value",
  "site_code": "SITE_001",
  "site_name": "某变电站",
  "site_environment": "电缆沟",
  "channels": [
    {
      "channel_no": 1,
      "channel_name": "通道1",
      "channel_file_path": "/data/audio/SAMPLE_002/ch1.wav",
      "channel_audio_uri": "https://example.com/audio/SAMPLE_002/ch1.wav"
    },
    {
      "channel_no": 2,
      "channel_name": "通道2",
      "channel_file_path": "/data/audio/SAMPLE_002/ch2.wav",
      "channel_audio_uri": "https://example.com/audio/SAMPLE_002/ch2.wav"
    }
  ]
}
```

## 4. 数据库表建议

实际表名可按项目规范调整，但建议至少分成这些逻辑表：

| 表 | 作用 |
| --- | --- |
| `voiceprint_sample` | 保存样本编号、采集时间、设备、采样参数、现场环境、处理状态。 |
| `voiceprint_file_index` | 保存音频文件名、文件路径、音频访问地址、校验值、文件大小。 |
| `voiceprint_channel` | 保存 4 通道编号、通道名称、通道文件地址。 |
| `voiceprint_model_result` | 保存模型名称、版本、算法结果、置信度、候选结果。 |
| `voiceprint_fault_result` | 保存是否故障、故障标签、故障类别、电气绝缘状态、最终诊断。 |
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
  "insulation_status": "疑似异常",
  "spectrum_uri": "https://example.com/features/SAMPLE_001_spectrum.png",
  "waveform_uri": "https://example.com/features/SAMPLE_001_waveform.png",
  "feature_uri": "https://example.com/features/SAMPLE_001.json",
  "final_diagnosis": "疑似局部放电，需要复核"
}
```

## 7. 前端接口口径

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
    "insulation_status": "疑似异常",
    "manual_label": null,
    "final_diagnosis": "疑似局部放电，需要复核"
  }
}
```

历史环境声纹大屏仍可使用：

```text
GET /api/frontend-dashboard
```
