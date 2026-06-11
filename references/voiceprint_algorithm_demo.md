# Voiceprint Algorithm Demo

Use this reference when a user asks the skill to run a cable voiceprint demo algorithm, generate model results, create waveform/spectrum resources, or submit algorithm output back to MySQL.

## Dependencies

Use the Python environment that has these packages:

```text
numpy
scipy
scikit-learn
matplotlib
joblib
mysql-connector-python
```

On this user's Windows/Codex setup, prefer:

```powershell
D:\conda\envs\pytorch\python.exe
```

## Commands

Train the lightweight 9-class demo classifier:

```bash
python scripts/voiceprint_algorithm_demo.py train \
  --data-dir /path/to/data \
  --model-dir /path/to/models/voiceprint_demo \
  --max-per-class 30
```

Infer one local wav and write a `submit-result` JSON:

```bash
python scripts/voiceprint_algorithm_demo.py infer-one \
  --audio /path/to/sample.wav \
  --sample-uid SAMPLE_001 \
  --model-dir /path/to/models/voiceprint_demo \
  --output-dir /path/to/outputs \
  --result-json /path/to/result.json
```

Infer a JSON payload returned by `pending-for-inference`:

```bash
python scripts/voiceprint_algorithm_demo.py infer-pending \
  --pending-json /path/to/pending_samples.json \
  --model-dir /path/to/models/voiceprint_demo \
  --output-dir /path/to/outputs \
  --result-json /path/to/results.json
```

Fetch pending samples:

```bash
python scripts/voiceprint_algorithm_demo.py fetch-pending \
  --limit 20 \
  --output /path/to/pending_samples.json
```

Validate algorithm results without writing:

```bash
python scripts/voiceprint_algorithm_demo.py submit-result /path/to/results.json
```

Commit algorithm results to MySQL:

```bash
python scripts/voiceprint_algorithm_demo.py submit-result /path/to/results.json --commit
```

Run the full pending-sample algorithm loop, with optional submit:

```bash
python scripts/voiceprint_algorithm_demo.py run-pending \
  --limit 20 \
  --model-dir /path/to/models/voiceprint_demo \
  --output-dir /path/to/outputs \
  --result-json /path/to/results.json \
  --submit
```

Add `--commit` only when the user explicitly wants to write results to MySQL.

## Result JSON Contract

The algorithm emits records compatible with `query_frontend_data.py submit-result`:

```json
{
  "sample_uid": "SAMPLE_001",
  "model_name": "voiceprint_demo_classifier",
  "model_version": "v0.1.0",
  "algorithm_result": "供水管道泄漏声纹",
  "confidence_score": 0.93,
  "topk_result_json": [
    {"label": "供水管道泄漏声纹", "score": 0.93}
  ],
  "is_fault": true,
  "fault_label": "供水管道泄漏声纹",
  "fault_type": "管廊供水管路泄漏",
  "spectrum_uri": "/path/to/SAMPLE_001_spectrum.png",
  "waveform_uri": "/path/to/SAMPLE_001_waveform.png",
  "feature_uri": "/path/to/SAMPLE_001_features.json",
  "need_review": false,
  "result_explain": "..."
}
```

## Pending JSON Input

Each pending record should include a local audio path in one of these fields:

```text
file_path
local_audio_path
audio_path
linux_save_path
channels[].channel_file_path
channels[].file_path
channels[].linux_save_path
```

The algorithm writes:

```text
waveform PNG
spectrum PNG
feature JSON
submit-result JSON
```

## Demo Labels

The bundled classifier recognizes nine demo classes:

```text
供水管道泄漏声纹
供气管道泄漏声纹
供电线路泄漏声纹
巡检脚步声纹
排风机声纹
供水管道泄漏与供气管道泄漏组合声纹
供水管道泄漏与供电线路泄漏组合声纹
供气管道泄漏与供电线路泄漏组合声纹
供水管道泄漏与供气管道泄漏与供电线路泄漏组合声纹
```
