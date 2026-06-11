# 电缆声纹实时接口

## 接口

```text
POST http://192.168.10.116:8000/api/v1/cable-voiceprint/samples
Content-Type: application/json
```

这个接口不是网页。GET 打开会返回 `405`，调用方必须 POST JSON。

现在推荐的数据方 4 通道 demo 是“4 个单通道 wav 分 4 次上传”。对应接口是：

```text
GET  http://192.168.10.116:8000/api/v1/cable-voiceprint/samples/{sample_uid}/channels
POST http://192.168.10.116:8000/api/v1/cable-voiceprint/samples/{sample_uid}/channels/{channel_no}
Content-Type: application/json
```

`GET` 用于查询 4 个通道哪些已经上传，`POST` 用于上传某一个通道。第 4 个通道上传完成后，服务端会自动合并样本元数据、写 MySQL 中文库 `电缆声纹检测库`，并把 4 通道波形写入 TDengine 中文库 `电缆声纹时序库`。

## 当前支持的传输模式

优先推荐数据方使用“数据方 wav 地址 + 我方 Linux 保存地址”：

```text
数据方文件服务器保存 wav
-> 数据方 POST JSON，提供 source_audio_url 和 linux_save_path
-> 接口从数据方地址下载 wav 到 Linux
-> 接口读取 wav 头，自动补 channel_count、sample_rate、bit_depth、duration_sec
-> 接口自动计算 file_sha256
-> 写 MySQL 中文库：电缆声纹检测库
-> 写 TDengine 中文库：电缆声纹时序库
```

接口同时兼容旧模式：

```text
1 个 Linux 本地四通道 wav + JSON
4 个 Linux 本地单通道 wav + JSON
```

## skill 新上传命令

查询通道状态：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py cable-channel-status SAMPLE_ID
```

上传某个通道。命令会先查询状态，如果通道已存在就跳过，避免重复上传：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py upload-channel SAMPLE_ID 1 /path/to/channel_1.json
```

一次性提交样本 JSON：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py upload-sample /path/to/sample.json
```

查询新中文库里的样本状态、通道、人工标注、算法结果和前端资源：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py cable-sample-status SAMPLE_ID
```

算法结果写回新中文库：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/query_frontend_data.py submit-cable-result /path/to/result.json --commit
```

## 数据方需要提供什么

数据方单通道 demo 最少需要提供：

```text
sample_uid               样本唯一编号
request_id               本次请求编号
collect_time             采集时间，ISO8601
device_id                采集设备编号
source_audio_url     数据方服务器上的 wav 下载地址，http/https
linux_save_path          wav 下载到我方 Linux 后的保存路径
manual_annotation        数据方人工故障打标，建议提供
```

`linux_save_path` 必须位于：

```text
/home/hzjq/ml_pipeline/data/cable_voiceprint/
```

数据方可以不提供 `file_sha256`、`sample_rate`、`bit_depth`、`duration_sec`、`channel_count`。接口会下载 wav 后自动读取和计算。如果数据方提供这些字段，接口会和 wav 真实参数校验，不一致会拒绝入库。

## 数据方单通道 demo 请求示例

Python `requests` 脚本：

```bash
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/cable_voiceprint_request_demo.py --write-example sample.json
python3 /Users/a1111/.codex/skills/frontend-db-dashboard/scripts/cable_voiceprint_request_demo.py --json-file sample.json
```

`sample.json` 内容可使用下面的 JSON 案例。数据方需要把 `source_audio_url` 替换成真实 wav 下载地址。

```bash
curl -X POST "http://192.168.10.116:8000/api/v1/cable-voiceprint/samples" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol_version": "1.1",
    "request_id": "REQ_SAMPLE_001",
    "sample_uid": "SAMPLE_001",
    "collect_time": "2026-06-05T10:30:00+08:00",
    "device_id": "DEVICE_001",
    "device_name": "电缆声纹采集设备001",
    "device_location": "数据方测试现场",
    "site_code": "SITE_001",
    "site_name": "某变电站",
    "site_environment": "电缆沟",
    "audio_format": "wav",
    "source_audio_url": "http://数据方服务器/audio/SAMPLE_001.wav",
    "linux_save_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_001/SAMPLE_001.wav",
    "manual_annotation": {
      "is_labeled": true,
      "is_fault": true,
      "fault_type": "内源故障",
      "fault_label": "局部放电",
      "fault_severity": "中等",
      "labeler_id": "EMP_001",
      "labeler_name": "张三",
      "label_time": "2026-06-05T10:31:00+08:00",
      "annotation_remark": "数据方人工确认该样本存在局部放电特征"
    }
  }'
```

## 本地四通道 wav 示例

```bash
curl -X POST "http://192.168.10.116:8000/api/v1/cable-voiceprint/samples" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol_version": "1.0",
    "request_id": "REQ_SAMPLE_4CH_001",
    "sample_uid": "SAMPLE_4CH_001",
    "collect_time": "2026-06-05T10:40:00+08:00",
    "device_id": "DEVICE_001",
    "channel_count": 4,
    "sample_rate": 48000,
    "bit_depth": 16,
    "duration_sec": 10,
    "audio_format": "wav",
    "channel_storage_mode": "单文件四通道",
    "file_name": "SAMPLE_4CH_001.wav",
    "file_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_4CH_001.wav",
    "file_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }'
```

## 四个单通道 wav 示例

如果数据方现在只有 4 个单通道 wav，优先使用分通道接口；每个通道 wav 必须是 1 通道。每个通道的 JSON 至少包含 `sample_uid`、`request_id`、`collect_time`、`device_id`、`source_audio_url`、`linux_save_path`、通道名或麦克风编号，以及人工标注信息。服务端会在 4 个通道都收到后完成最终入库。

第 1 通道请求示例：

```bash
curl -X POST "http://192.168.10.116:8000/api/v1/cable-voiceprint/samples/SAMPLE_001/channels/1" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol_version": "1.1",
    "request_id": "REQ_SAMPLE_001_CH1",
    "sample_uid": "SAMPLE_001",
    "collect_time": "2026-06-05T10:30:00+08:00",
    "device_id": "DEVICE_001",
    "channel_name": "通道1",
    "mic_id": "MIC-01",
    "source_audio_url": "http://数据方服务器/audio/SAMPLE_001/ch1.wav",
    "linux_save_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_001/ch1.wav",
    "manual_annotation": {
      "is_labeled": true,
      "is_fault": true,
      "fault_type": "内源故障",
      "fault_label": "局部放电",
      "fault_severity": "warning",
      "labeler_name": "张三"
    }
  }'
```

第 2、3、4 通道只需要把 URL 里的最后一位通道号、`request_id`、`channel_name`、`mic_id`、`source_audio_url` 和 `linux_save_path` 换成对应通道即可。

```bash
curl -X POST "http://192.168.10.116:8000/api/v1/cable-voiceprint/samples" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol_version": "1.0",
    "request_id": "REQ_SAMPLE_MONO_001",
    "sample_uid": "SAMPLE_MONO_001",
    "collect_time": "2026-06-05T10:50:00+08:00",
    "device_id": "DEVICE_001",
    "channel_count": 4,
    "sample_rate": 48000,
    "bit_depth": 16,
    "duration_sec": 10,
    "audio_format": "wav",
    "channel_storage_mode": "四个单通道文件",
    "file_name": "SAMPLE_MONO_001",
    "file_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_MONO_001/",
    "file_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "channels": [
      {"channel_index": 1, "mic_id": "MIC-01", "position_label": "通道1", "channel_file_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_MONO_001/ch1.wav"},
      {"channel_index": 2, "mic_id": "MIC-02", "position_label": "通道2", "channel_file_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_MONO_001/ch2.wav"},
      {"channel_index": 3, "mic_id": "MIC-03", "position_label": "通道3", "channel_file_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_MONO_001/ch3.wav"},
      {"channel_index": 4, "mic_id": "MIC-04", "position_label": "通道4", "channel_file_path": "/home/hzjq/ml_pipeline/data/cable_voiceprint/SAMPLE_MONO_001/ch4.wav"}
    ]
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
  "tdengine_tables": ["vp_sample_001_a1b2c3d4_ch1"],
  "channel_count": 1,
  "samples_per_channel": 8000
}
```

## file_sha256

数据方 URL 模式下可以不传 `file_sha256`，接口下载 wav 后自动计算。

本地文件模式下建议传 `file_sha256`。单文件模式直接计算 wav 文件 SHA256。四个单通道模式先分别计算 4 个通道文件 SHA256，再按通道顺序合并：

```text
file_sha256 = sha256(ch1_sha256 + "\n" + ch2_sha256 + "\n" + ch3_sha256 + "\n" + ch4_sha256)
```

## 注意事项

- `source_audio_url` 需要是接口服务能访问到的 `http` 或 `https` 地址。
- 文件名含中文时，建议数据方使用 URL 编码；接口也会自动处理 URL 路径中的中文。
- `sample_uid` 不能重复；重复样本必须保持同一个 wav 内容。
- `linux_save_path` 只能写入允许目录，防止接口被用来覆盖服务器任意文件。
- TDengine 适合存波形和频谱数值，不建议存 PNG/JPG 频谱图文件；频谱图文件应保存在 Linux 或对象存储，MySQL 保存访问地址。

## 测试脚本

远端 Linux 上已有端到端测试脚本：

```bash
cd /home/hzjq/ml_pipeline
python3 process/test_cable_voiceprint_remote_audio_url_protocol.py
python3 process/test_cable_voiceprint_protocol.py
python3 process/test_cable_voiceprint_four_mono_protocol.py
```

第一条测试会模拟数据方文件服务器提供单通道 wav 地址，接口下载到 Linux 后写入 MySQL 和 TDengine，并在测试结束后删除测试样本、TDengine 子表和测试 wav。
