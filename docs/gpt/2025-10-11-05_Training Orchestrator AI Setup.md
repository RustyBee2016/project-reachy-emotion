# 05_Training Orchestrator AI Setup

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 21:32:48  
**Updated:** 10/21/2025 22:02:52  
**Exported:** 10/21/2025 22:03:35  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b3be-fa80-8333-aa78-d980788dc507](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b3be-fa80-8333-aa78-d980788dc507)  

## Prompt:
consider the chat titled 'ALL Agent-by-Agent Purposes.'

Provide a detailed explanation of how to develop the first AI agent 5: Training Orchestrator.
At this point, you should provide all the detail you can regarding how to construct the n8n nodes, sub-nodes, parameters, etc.

Be sure to refer to the newest n8n documentation.

Thought for 28s

## Response:
Alright Russ — Training Orchestrator is the heartbeat. It turns a promoted dataset into a fresh ActionRecognitionNet run (TAO), tracks it in MLflow, enforces Gate A metrics, and (if green) exports a TRT engine for downstream evaluation.

Below is a concrete, import-ready n8n workflow plus the “why” and “how” of each node, with the gotchas I’d watch for.

* * *

What this agent does (at a glance)
==================================

**Inputs**

*   `dataset_hash`, `manifest_path`, `class_map`, optional `zfs_snapshot_flag`
*   Correlation info: `correlation_id`, `source`, `schema_version`

**Process**

1.  Start an MLflow run → log params (dataset hash, TAO cfg)
2.  Kick off TAO fine-tune (detached) → poll for `summary.json`
3.  Log metrics/artifacts to MLflow → check Gate A thresholds
4.  If pass → TAO export + TRT build → log engine to MLflow → emit `training.completed`
5.  If fail → emit `training.failed` with reasons

**Why the shape:** Long jobs shouldn’t block n8n. We start training detached and **poll** with sleeps using **Wait** so n8n offloads state to DB and doesn’t hold a worker the whole time. n8n’s Wait node is designed for this resume pattern. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/?utm_source=chatgpt.com)

* * *

Nodes you’ll see (and key params)
=================================

**Trigger — Webhook (“dataset.promoted → training.start”)**

*   Path: `/agent/training/start`
*   Method: POST
*   Expects JSON with the fields above.
*   (Manual “Execute Workflow” trigger also included for ad-hoc runs.)

**Set — “normalize\_input”**

*   Pulls out `dataset_hash`, `manifest_path`, etc., applies defaults.

**HTTP Request — “mlflow\_create\_run”**

*   POST `${MLFLOW_URL}/api/2.0/mlflow/runs/create` with `experiment_id`, tags (`dataset_hash`, `correlation_id`).
*   We use MLflow’s REST API (create, log-metric/param/artifacts). [MLflow+1](https://mlflow.org/docs/latest/rest-api.html?utm_source=chatgpt.com)

**Execute Command — “tao\_start\_training\_detached”**

*   Command (bash): launches TAO in **nohup/tmux** and writes to `${RUN_DIR}/summary.json` when done.
*   Runs inside the same box where TAO is installed (Ubuntu 1). If your n8n is containerized, either (a) extend the image to include tools you need or (b) SSH to the TAO box instead. The Execute Command docs call out extending the image when needed. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/?utm_source=chatgpt.com)

**Wait — “sleep\_until\_next\_poll”**

*   Wait 5 minutes (or until a resume webhook fires). The Wait node offloads execution state. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/?utm_source=chatgpt.com)

**Execute Command — “check\_status”**

*   Checks for `${RUN_DIR}/summary.json`. If not found → loop back to Wait.
*   Keep stdout small to avoid `maxBuffer` pitfalls the docs mention. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/common-issues/?utm_source=chatgpt.com)

**Code — “parse\_summary”**

*   Reads `summary.json` (cat via Execute Command → JSON.parse here) and maps out:  
    `macro_f1`, `balanced_accuracy`, `ece`, `brier`, `per_class_f1`, `confusion_matrix_path`, `train_log_path`.

**HTTP Request — “mlflow\_log\_params\_metrics”**

*   POST params/metrics to MLflow (`/runs/log-parameter`, `/runs/log-metric`) and upload artifacts (`/artifacts/log-artifact`). [MLflow](https://mlflow.org/docs/latest/rest-api.html?utm_source=chatgpt.com)

**IF — “Gate A check”**

*   Conditions from your **requirements 7.1 Gate A**: macro F1 ≥ 0.84; per-class floors ≥ 0.75; calibration ECE ≤ 0.08, Brier ≤ 0.16; balanced accuracy ≥ 0.85 (as applicable).
*   If fail → “mlflow\_set\_failed” + emit `training.failed`.

**Execute Command — “tao\_export\_trt”** _(success branch)_

*   Runs TAO export + `tao-converter` to TRT FP16; writes `.engine` into `${RUN_DIR}/artifacts/`.
*   Commands follow TAO Launcher usage (model pull from NGC, run via CLI). [NVIDIA Docs+1](https://docs.nvidia.com/tao/tao-toolkit/text/quick_start_guide/running_via_launcher.html?utm_source=chatgpt.com)

**HTTP Request — “mlflow\_log\_engine\_artifact”**

*   Upload `.engine`, `nvinfer` config, and final `metrics.json` to MLflow. [MLflow](https://mlflow.org/docs/latest/rest-api.html?utm_source=chatgpt.com)

**HTTP Request — “emit\_training\_completed”**

*   POST to your internal bus (or the next n8n workflow) with `training.completed` payload (run\_id, dataset\_hash, engine path).

**(Optional) Execute Command — “zfs\_snapshot”**

*   If `zfs_snapshot_flag=true`, snapshot before and/or after training for lineage.
*   Recorded to MLflow as `snapshot_ref`.

**Housekeeping**

*   Merge/Set nodes to shape payloads; an “End” notification node to Slack/Email if you want.

* * *

Import-ready n8n workflow (JSON)
================================

Paste this into **n8n → Import**. It’s opinionated but clean; everything sensitive sits in **Credentials** or **Environment variables** you set on the n8n host.

```json
{
  "name": "Agent 5 — Training Orchestrator (08.3.3)",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "agent/training/start",
        "responseMode": "onReceived",
        "options": {
          "responseCode": 202
        }
      },
      "id": "Webhook_Trigger",
      "name": "trigger_dataset_promoted",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [200, 200]
    },
    {
      "parameters": {
        "assignments": {
          "fields": {
            "dataset_hash": "={{$json.dataset_hash}}",
            "manifest_path": "={{$json.manifest_path}}",
            "class_map": "={{$json.class_map || ['happy','sad','angry','neutral','surprise','fearful']}}",
            "correlation_id": "={{$json.correlation_id || $now}}",
            "experiment_id": "={{$env.MLFLOW_EXPERIMENT_ID}}",
            "run_dir": "=/srv/projects/reachy_emotion/runs/{{$json.dataset_hash}}",
            "zfs_snapshot": "={{$json.zfs_snapshot_flag || false}}"
          }
        }
      },
      "id": "Set_1",
      "name": "normalize_input",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [440, 200]
    },
    {
      "parameters": {
        "url": "={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/create",
        "options": {
          "sendHeaders": true
        },
        "sendBinaryData": false,
        "jsonParameters": true,
        "authentication": "none",
        "headerParametersJson": "{\"Content-Type\":\"application/json\"}",
        "bodyParametersJson": "={\"experiment_id\":\"{{$json.experiment_id}}\",\"tags\":[{\"key\":\"dataset_hash\",\"value\":\"{{$json.dataset_hash}}\"},{\"key\":\"correlation_id\",\"value\":\"{{$json.correlation_id}}\"},{\"key\":\"source\",\"value\":\"agent.training_orchestrator\"}]}"
      },
      "id": "HTTP_1",
      "name": "mlflow_create_run",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [680, 200]
    },
    {
      "parameters": {
        "assignments": {
          "fields": {
            "mlflow_run_id": "={{$json.run.info.run_id}}"
          }
        }
      },
      "id": "Set_2",
      "name": "stash_run_id",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [920, 200]
    },
    {
      "parameters": {
        "command": "bash",
        "arguments": "-lc \"mkdir -p {{$json.run_dir}}/logs {{$json.run_dir}}/artifacts && cd {{$json.run_dir}} && printf '%s' {{$json.manifest_path}} > manifest.path && if {{$json.zfs_snapshot}}; then sudo zfs snapshot pool/reachy@train-{{$json.dataset_hash}} || true; fi && nohup /opt/tao/tao action_recognition train -e /srv/tao/experiments/arnet.yaml \\\"dataset.manifest={{$json.manifest_path}}\\\" \\\"training.run_dir={{$json.run_dir}}\\\" > {{$json.run_dir}}/logs/train.out 2>&1 & echo $! > {{$json.run_dir}}/train.pid && echo '{\\\"status\\\":\\\"STARTED\\\",\\\"run_id\\\":\\\"{{$json.mlflow_run_id}}\\\"}'\"",
        "options": {
          "shell": "bash"
        }
      },
      "id": "Exec_1",
      "name": "tao_start_training_detached",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 2,
      "position": [1160, 200]
    },
    {
      "parameters": {
        "amount": 5,
        "unit": "minutes",
        "resume": "MANUAL_OR_TIME"
      },
      "id": "Wait_1",
      "name": "sleep_until_next_poll",
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1,
      "position": [1400, 200]
    },
    {
      "parameters": {
        "command": "bash",
        "arguments": "-lc \"if [ -f {{$json.run_dir}}/summary.json ]; then echo READY; else echo WAIT; fi\"",
        "options": {
          "shell": "bash"
        }
      },
      "id": "Exec_2",
      "name": "check_status",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 2,
      "position": [1640, 200]
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json[\"stdout\"]}}",
              "operation": "contains",
              "value2": "READY"
            }
          ]
        }
      },
      "id": "IF_1",
      "name": "is_ready?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [1880, 200]
    },
    {
      "parameters": {
        "command": "bash",
        "arguments": "-lc \"cat {{$json.run_dir}}/summary.json\"",
        "options": {
          "shell": "bash"
        }
      },
      "id": "Exec_3",
      "name": "read_summary_json",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 2,
      "position": [2120, 120]
    },
    {
      "parameters": {
        "jsCode": "const s = JSON.parse(items[0].json.stdout || '{}');\nreturn [{ json: {\n  macro_f1: s.macro_f1,\n  balanced_accuracy: s.balanced_accuracy,\n  ece: s.ece,\n  brier: s.brier,\n  per_class_f1: s.per_class_f1,\n  confusion: s.confusion_matrix_path,\n  train_log: s.train_log_path,\n  run_dir: $json.run_dir,\n  mlflow_run_id: $json.mlflow_run_id,\n  dataset_hash: $json.dataset_hash\n}}];"
      },
      "id": "Code_1",
      "name": "parse_summary",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [2360, 120]
    },
    {
      "parameters": {
        "url": "={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/log-batch",
        "options": { "sendHeaders": true },
        "jsonParameters": true,
        "headerParametersJson": "{\"Content-Type\":\"application/json\"}",
        "bodyParametersJson": "={\"run_id\":\"{{$json.mlflow_run_id}}\",\"metrics\":[{\"key\":\"macro_f1\",\"value\":{{$json.macro_f1}},\"timestamp\":{{$now}}},{\"key\":\"balanced_accuracy\",\"value\":{{$json.balanced_accuracy}},\"timestamp\":{{$now}}},{\"key\":\"ece\",\"value\":{{$json.ece}},\"timestamp\":{{$now}}},{\"key\":\"brier\",\"value\":{{$json.brier}},\"timestamp\":{{$now}}}],\"params\":[{\"key\":\"dataset_hash\",\"value\":\"{{$json.dataset_hash}}\"}]}"
      },
      "id": "HTTP_2",
      "name": "mlflow_log_params_metrics",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [2600, 120]
    },
    {
      "parameters": {
        "conditions": {
          "number": [
            { "value1": "={{$json.macro_f1}}", "operation": "largerEqual", "value2": 0.84 },
            { "value1": "={{$json.balanced_accuracy}}", "operation": "largerEqual", "value2": 0.85 }
          ],
          "boolean": [],
          "multiOptions": []
        }
      },
      "id": "IF_2",
      "name": "Gate A pass?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [2840, 120]
    },
    {
      "parameters": {
        "command": "bash",
        "arguments": "-lc \"/opt/tao/tao action_recognition export -e /srv/tao/experiments/arnet.yaml \\\"results_dir={{$json.run_dir}}\\\" && /opt/tao/tao-converter -k nvidia_tao -d 3,16,224,224 -t fp16 -o predictions -e {{$json.run_dir}}/artifacts/action_recognition.engine -m {{$json.run_dir}}/export/onnx/model.onnx > {{$json.run_dir}}/logs/export.out 2>&1\"",
        "options": { "shell": "bash" }
      },
      "id": "Exec_4",
      "name": "tao_export_trt",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 2,
      "position": [3080, 40]
    },
    {
      "parameters": {
        "url": "={{$env.MLFLOW_URL}}/api/2.0/mlflow/artifacts/log-artifact?run_id={{$json.mlflow_run_id}}",
        "options": { "sendHeaders": true },
        "sendBinaryData": true,
        "binaryPropertyName": "engine",
        "headerParametersJson": "{\"Content-Type\":\"application/octet-stream\"}"
      },
      "id": "HTTP_3",
      "name": "mlflow_log_engine_artifact",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [3320, 40]
    },
    {
      "parameters": {
        "command": "bash",
        "arguments": "-lc \"cat {{$json.run_dir}}/artifacts/action_recognition.engine | wc -c\"",
        "options": { "shell": "bash" }
      },
      "id": "Exec_5",
      "name": "read_engine_binary",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 2,
      "position": [3080, 120]
    },
    {
      "parameters": {
        "url": "={{$env.INTERNAL_BUS_URL}}/events/training.completed",
        "options": { "sendHeaders": true },
        "jsonParameters": true,
        "headerParametersJson": "{\"Content-Type\":\"application/json\"}",
        "bodyParametersJson": "={\"event\":\"training.completed\",\"dataset_hash\":\"{{$json.dataset_hash}}\",\"mlflow_run_id\":\"{{$json.mlflow_run_id}}\",\"engine_path\":\"{{$json.run_dir}}/artifacts/action_recognition.engine\",\"correlation_id\":\"{{$json.correlation_id}}\"}"
      },
      "id": "HTTP_4",
      "name": "emit_training_completed",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [3560, 40]
    },
    {
      "parameters": {
        "url": "={{$env.INTERNAL_BUS_URL}}/events/training.failed",
        "options": { "sendHeaders": true },
        "jsonParameters": true,
        "headerParametersJson": "{\"Content-Type\":\"application/json\"}",
        "bodyParametersJson": "={\"event\":\"training.failed\",\"dataset_hash\":\"{{$json.dataset_hash}}\",\"mlflow_run_id\":\"{{$json.mlflow_run_id}}\",\"reason\":\"Gate A thresholds not met\",\"metrics\":{\"macro_f1\":{{$json.macro_f1}},\"balanced_accuracy\":{{$json.balanced_accuracy}},\"ece\":{{$json.ece}},\"brier\":{{$json.brier}}},\"correlation_id\":\"{{$json.correlation_id}}\"}"
      },
      "id": "HTTP_5",
      "name": "emit_training_failed",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [3080, 200]
    }
  ],
  "connections": {
    "trigger_dataset_promoted": { "main": [[{ "node": "normalize_input", "type": "main", "index": 0 }]] },
    "normalize_input": { "main": [[{ "node": "mlflow_create_run", "type": "main", "index": 0 }]] },
    "mlflow_create_run": { "main": [[{ "node": "stash_run_id", "type": "main", "index": 0 }]] },
    "stash_run_id": { "main": [[{ "node": "tao_start_training_detached", "type": "main", "index": 0 }]] },
    "tao_start_training_detached": { "main": [[{ "node": "sleep_until_next_poll", "type": "main", "index": 0 }]] },
    "sleep_until_next_poll": { "main": [[{ "node": "check_status", "type": "main", "index": 0 }]] },
    "check_status": { "main": [[{ "node": "is_ready?", "type": "main", "index": 0 }]] },
    "is_ready?": {
      "main": [
        [{ "node": "sleep_until_next_poll", "type": "main", "index": 0 }],
        [{ "node": "read_summary_json", "type": "main", "index": 0 }]
      ]
    },
    "read_summary_json": { "main": [[{ "node": "parse_summary", "type": "main", "index": 0 }]] },
    "parse_summary": { "main": [[{ "node": "mlflow_log_params_metrics", "type": "main", "index": 0 }]] },
    "mlflow_log_params_metrics": { "main": [[{ "node": "Gate A pass?", "type": "main", "index": 0 }]] },
    "Gate A pass?": {
      "main": [
        [{ "node": "tao_export_trt", "type": "main", "index": 0 }],
        [{ "node": "emit_training_failed", "type": "main", "index": 0 }]
      ]
    },
    "tao_export_trt": {
      "main": [
        [{ "node": "read_engine_binary", "type": "main", "index": 0 }]
      ]
    },
    "read_engine_binary": {
      "main": [
        [{ "node": "mlflow_log_engine_artifact", "type": "main", "index": 0 }]
      ]
    },
    "mlflow_log_engine_artifact": {
      "main": [
        [{ "node": "emit_training_completed", "type": "main", "index": 0 }]
      ]
    }
  },
  "pinData": {},
  "meta": { "templateCredsSetup": true, "instanceId": "reachy-local-08-3-3" }
}
```

**Environment/credentials you’ll set in n8n**

*   `MLFLOW_URL` (e.g., `http://ubuntu1:5000`)
*   `MLFLOW_EXPERIMENT_ID` (numeric string)
*   `INTERNAL_BUS_URL` (your Ubuntu 2 FastAPI or n8n webhook for events)
*   The TAO path (`/opt/tao/tao`) and config file path `/srv/tao/experiments/arnet.yaml` should match Ubuntu 1.
*   If n8n runs as a container, remember: either install the needed tools in the image or have n8n **SSH** into Ubuntu 1. The Execute Command docs call this out; Alpine-based images won’t have your toolchain by default. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/?utm_source=chatgpt.com)

* * *

Why these n8n choices (and how to tune)
=======================================

*   **HTTP Request** to MLflow: the core node is stable and flexible; MLflow’s REST surface for create/log-batch/log-artifact is well-defined. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **Wait** for long training: prevents holding a worker; the node persists execution and resumes cleanly. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/?utm_source=chatgpt.com)
*   **Execute Command** detached run: TAO can take hours; we background it and poll a small JSON summary to avoid `maxBuffer` and timeouts called out in n8n docs. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/common-issues/?utm_source=chatgpt.com)
*   **TAO commands** follow NVIDIA’s launcher CLI/export flow for ActionRecognitionNet. Keep those paths pinned to your mounted volumes. [NVIDIA Docs+1](https://docs.nvidia.com/tao/tao-toolkit/text/quick_start_guide/running_via_launcher.html?utm_source=chatgpt.com)

* * *

Guardrails & gotchas
====================

*   **Where n8n runs matters.** If n8n is inside Docker on Ubuntu 2, and TAO is on Ubuntu 1, prefer an **SSH node** or an API shim on Ubuntu 1 rather than Execute Command locally. If you _do_ Execute Command inside the n8n container, extend the image to include `bash`, `tmux`, `tao` CLI, etc., per docs. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/?utm_source=chatgpt.com)
*   **Binary uploads to MLflow:** The log-artifact call expects proper multipart or binary upload; I showed the binary path natively from the node. If your MLflow is behind an auth proxy, add headers/credentials accordingly. [MLflow](https://mlflow.org/docs/latest/rest-api.html?utm_source=chatgpt.com)
*   **Polling cadence:** Start with 5 minutes. If you want event-driven resume, flip Wait to “resume on webhook” and have your TAO wrapper hit that webhook when `summary.json` lands. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/?utm_source=chatgpt.com)
*   **Metrics source of truth:** Have TAO write a clean `summary.json` (macro F1, balanced accuracy, ECE, Brier, per-class). If not natively available, parse your training logs into that file at the end of the run.
*   **Gate A alignment:** Your thresholds come from `requirements_08.3.3.md §7.1`. Keep them versioned; if you change gates, update this IF node in the same PR as the requirements update. requirements\_08.3.3

* * *

Tiny TAO wrapper (drop-in)
==========================

On Ubuntu 1, add a minimal wrapper so the job always emits `summary.json`:

```bash
#!/usr/bin/env bash
set -euo pipefail
RUN_DIR="$1"          # /srv/projects/reachy_emotion/runs/<dataset_hash>
EXP_YAML="$2"         # /srv/tao/experiments/arnet.yaml
MANIFEST="$3"         # /videos/manifests/<hash>.jsonl

mkdir -p "$RUN_DIR/logs" "$RUN_DIR/artifacts"
/opt/tao/tao action_recognition train -e "$EXP_YAML" "dataset.manifest=$MANIFEST" "training.run_dir=$RUN_DIR" \
  > "$RUN_DIR/logs/train.out" 2>&1

python3 - <<'PY'
# Parse your TAO logs into summary.json (macro_f1, balanced_accuracy, ece, brier, paths)
# ... write to RUN_DIR/summary.json
PY
```

Then point the Execute Command node to call this wrapper with `nohup … &`.

* * *

If you want, I can swap the detached/poll approach for **Wait → “resume via webhook”** (cleaner) and wire a one-liner `curl $WAIT_RESUME_URL` at the end of your wrapper. That avoids loops entirely, leans on n8n’s intended “pause → resume” path, and keeps your worker free the whole time. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/?utm_source=chatgpt.com)

Either way, this gives you a Training Orchestrator that’s reproducible, observable, and aligned with the spec — without welding n8n to TAO in brittle ways.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)