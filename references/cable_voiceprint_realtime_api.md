# 电缆声纹 4 通道实时接口

## 接口

```text
POST http://192.168.10.116:8000/api/v1/cable-voiceprint/samples
Content-Type: application/json
```

这个接口不是网页。GET 打开会返回 `405`，调用方必须 POST JSON。

## 传输模式

第一版采用“Linux 文件路径 + JSON 元数据”：

```text
调用方先把 4 通道 wav 放到 Linux 服务器
-> JSON 里 file_path 填 Linux 上的真实路径
-> 接口读取 wav
-> 写 MySQL 中文库：电缆声纹检测库
-> 解析 4 通道波形写 TDengine 中文库：电缆声纹时序库
```

当前不直接上传 wav 二进制。如果调用方只有企业文件服务器地址，需要先同步到 Linux，或后续扩展由接口根据 `audio_uri` 自动下载。

## 使用条件

调用方需要：

- 能访问 `http://192.168.10.116:8000`。
- wav 文件已经在 Linux 服务器上，接口服务能读取。
- wav 是 4 通道。
- JSON 中 `sample_rate`、`bit_depth`、`channel_count` 和 wav 真实参数一致。
- `sample_uid` 唯一；重复样本必须保持 `file_sha256` 一致。

## 必填字段

```text
protocol_version
request_id
sample_uid
collect_time
device_id
channel_count
sample_rate
bit_depth
duration_sec
file_name
file_path
file_sha256
```

建议字段：

```text
batch_id
collect_task_id
device_name
device_location
site_code
site_name
site_environment
audio_uri
file_size_bytes
channel_map
manual_annotation
```

## curl 示例

```bash
curl -X POST "http://192.168.10.116:8000/api/v1/cable-voiceprint/samples" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol_version": "1.0",
    "request_id": "REQ_SAMPLE_001",
    "sample_uid": "SAMPLE_001",
    "collect_time": "2026-06-04T10:15:30+08:00",
    "device_id": "DEVICE_001",
    "site_code": "SITE_001",
    "site_name": "某变电站",
    "site_environment": "电缆沟",
    "channel_count": 4,
    "sample_rate": 48000,
    "bit_depth": 16,
    "duration_sec": 10,
    "audio_format": "wav",
    "channel_storage_mode": "单文件四通道",
    "file_name": "SAMPLE_001.wav",
    "file_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_001.wav",
    "audio_uri": "http://192.168.10.116:8000/audio/SAMPLE_001.wav",
    "file_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "channel_map": [
      {"channel_index": 1, "mic_id": "MIC-01", "position_label": "通道1"},
      {"channel_index": 2, "mic_id": "MIC-02", "position_label": "通道2"},
      {"channel_index": 3, "mic_id": "MIC-03", "position_label": "通道3"},
      {"channel_index": 4, "mic_id": "MIC-04", "position_label": "通道4"}
    ],
    "manual_annotation": {
      "is_labeled": true,
      "is_fault": true,
      "fault_type": "内源故障",
      "fault_label": "局部放电",
      "fault_severity": "中等",
      "labeler_id": "EMP_001",
      "labeler_name": "张三",
      "label_time": "2026-06-04T10:16:00+08:00",
      "annotation_remark": "企业人工确认该样本存在局部放电特征"
    }
  }'
```

## 成功响应

成功时 `process_status` 为 `TD_WRITTEN`，表示 MySQL 和 TDengine 都已写入：

```json
{
  "success": true,
  "sample_uid": "SAMPLE_001",
  "request_id": "REQ_SAMPLE_001",
  "process_status": "TD_WRITTEN",
  "mysql_database": "电缆声纹检测库",
  "tdengine_database": "电缆声纹时序库",
  "tdengine_stable": "sensor_waveform_4ch",
  "tdengine_tables": [
    "vp_sample_001_ch1",
    "vp_sample_001_ch2",
    "vp_sample_001_ch3",
    "vp_sample_001_ch4"
  ],
  "channel_count": 4,
  "samples_per_channel": 480000
}
```

## 测试脚本

远端 Linux 上已有端到端测试脚本：

```bash
cd /home/hzjq/ml_pipeline
python3 process/test_cable_voiceprint_protocol.py
```

脚本会生成 1 秒 4 通道 wav，调用接口，验证 MySQL 和 TDengine 写入，然后删除测试样本、TDengine 子表和测试 wav。
