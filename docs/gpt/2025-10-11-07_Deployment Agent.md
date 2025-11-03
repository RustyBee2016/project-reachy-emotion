# 07_Deployment Agent

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 21:46:50  
**Updated:** 10/21/2025 21:54:59  
**Exported:** 10/21/2025 21:55:53  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b706-e748-832f-a28b-1ca0573ae53f](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b706-e748-832f-a28b-1ca0573ae53f)  

## Prompt:
consider the chat titled 'ALL Agent-by-Agent Purposes.'

Provide a detailed explanation of how to develop the first AI agent 7: Deployment Agent
At this point, you should provide all the detail you can regarding how to construct the n8n nodes, sub-nodes, parameters, etc.

Be sure to refer to the newest n8n documentation.

Thought for 16s

## Response:
You’re at Agent 7: Deployment. This one turns a “good” engine into a “safe” rollout on the Jetson—clean hand-offs, approvals, and fast rollback. I’ll lay out: (1) what the agent owns, (2) the exact n8n graph with nodes/params, and (3) a ready-to-import starter JSON you can paste into n8n and extend.

* * *

What the Deployment Agent owns
==============================

*   **Inputs (from Agent 6: Evaluation):** a signed TensorRT engine (FP16 or INT8), DeepStream `nvinfer` config, Gate evidence (A/B/C), and a version tag that cleared thresholds. (Your gates and targets live here: F1 floors, latency p50/p95, memory caps, user-visible latency, etc.) requirements\_08.3.3
*   **Stages it must enforce:**
    1.  **Shadow on robot** (load new engine in parallel; no user impact) → 2) **Canary** (limited sessions) → 3) **Rollout** (all sessions). Promotions require human approval per rules. AGENTS
*   **Targets:** Jetson DeepStream + TensorRT; update `nvinfer` config to point at the new engine, keep FP16 by default (INT8 only if verified). requirements\_08.3.3

* * *

n8n workflow: nodes, params, credentials
========================================

Below is the graph (top→down). I’m using only well-supported nodes: **Webhook / GitHub / HTTP Request / IF / SSH / FTP(SFTP) / Wait / Set / Code**. Docs linked inline.

### 0) Triggers

1.  **Webhook (POST /deploy/approve)**
    *   Purpose: receive _human_ approvals with a `stage=shadow|canary|rollout`, `approve=true/false`, `correlation_id`.
    *   Security: add a shared secret header, verify inside a **Code** node.
2.  **GitHub Trigger** (optional)
    *   Fires when a release is created or a PR is merged with label `release:engine`. Use it if you want deployments to start from GH events. [n8n Docs](https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.githubtrigger/?utm_source=chatgpt.com)
3.  **Manual Trigger**
    *   For local tests only.

### 1) Ingest & validate the artifact

3.  **HTTP Request — fetch Gate evidence**
    *   GET `https://<ubuntu2>/metrics/gates?run_id={{$json.run_id}}`
    *   Expect JSON: `{"gateA":true,"gateB":true,"gateC":false,...}` (you’ll typically arrive here with gate B passed; rollout waits on C.)
    *   Node docs: HTTP Request. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
4.  **IF — all required gates met for next stage?**
    *   For **shadow**: require Gate A.
    *   For **canary**: require Gate B.
    *   For **rollout**: require Gate C.
    *   Gate definitions per spec. requirements\_08.3.3
5.  **GitHub — download release assets** (if you store engines/configs in GH Releases)
    *   Operation: _Get Release Asset_ → asset names like `actionrecog-<ver>.engine`, `config_infer_primary.txt`.
    *   Or: pull from your artifact store/MLflow via HTTP Request.

### 2) Upload engine & config to Jetson

6.  **FTP (SFTP) — upload engine**
    *   Credentials: SFTP (host Jetson IP, key-based auth recommended). [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ftp/?utm_source=chatgpt.com)
    *   Remote path: `/opt/reachy/models/action_recognition-{{version}}.engine`
    *   Tip: use **SSH** “Upload file” if you prefer that node; both support upload. SSH supports upload/download/exec. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ssh/?utm_source=chatgpt.com)
7.  **FTP (SFTP) — upload nvinfer config**
    *   Remote path: `/opt/reachy/deepstream/config_infer_primary-{{version}}.txt`
8.  **SSH — atomically switch symlinks**
    *   Operation: _Execute a command_.
    *   Command:
        ```bash
        set -euo pipefail
        cd /opt/reachy
        ln -sfn models/action_recognition-{{version}}.engine models/current.engine
        ln -sfn deepstream/config_infer_primary-{{version}}.txt deepstream/config_infer_primary.txt
        ```
    *   SSH node supports exec and file ops; creds here: host, port 22, username, private key. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ssh/?utm_source=chatgpt.com)
9.  **SSH — restart DeepStream service**
    *   `sudo systemctl restart reachy-deepstream.service && sleep 2 && systemctl is-active --quiet reachy-deepstream.service`
10.  **Wait — warm-up period (e.g., 30–60s)**
    *   Use Wait-for-duration to let the pipeline settle. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/?utm_source=chatgpt.com)

### 3) Health + telemetry checks

11.  **HTTP Request — Jetson health probe**
    *   GET `http://<ubuntu2>/healthz/jetson/{{device_id}}` (your gateway reports DeepStream heartbeat/telemetry).
*   Expect JSON fields: `fps`, `latency_ms_p50`, `latency_ms_p95`, `gpu_mem_gb`.
*   Node docs: HTTP Request. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
    12.  **IF — meets stage thresholds?**
    *   **Shadow:** just need stable `is_active` and no crashes.
*   **Canary:** p50 ≤ 120 ms, p95 ≤ 250 ms, GPU ≤ 2.5 GB; Macro-F1 ≥ 0.80 from Eval telemetry. requirements\_08.3.3
    13.  **HTTP Request — flip routing**
    *   _Only for canary/rollout._ PATCH `https://<ubuntu2>/api/runtime/routing` body:
    ```json
    {"model_version":"{{version}}","scope":"canary","percent":10}
    ```
*   Later for rollout: `{"scope":"all","percent":100}`.
*   Use the same node pattern for rollback with the previous version.
    14.  **Wait — collect canary window** (e.g., 30–60 minutes, or until approval webhook)
    *   Use Wait-for-webhook pattern: pause until a POST hits `/deploy/approve` with `stage=canary` and `approve=true`. [n8n Docs](https://docs.n8n.io/flow-logic/waiting/?utm_source=chatgpt.com)
    15.  **HTTP Request — metrics snapshot**
    *   GET `https://<ubuntu2>/metrics/rollout?stage={{stage}}&version={{version}}`
*   Store to execution data for audit.

### 4) Human approvals & promotions

16.  **IF — approved?** (from the Webhook payload)
    *   If **false** → go to rollback branch.
*   If **true**:
    *   **Shadow → Canary:** proceed to step 13 with canary 10%.
    *   **Canary → Rollout:** proceed to step 13 with 100%.
        17.  **GitHub — create/annotate Release**
    *   Add release notes: gate evidence + metrics + canary stats.
*   GitHub node supports creating/editing releases. [n8n Docs](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.github/?utm_source=chatgpt.com)

### 5) Rollback (shared branch)

18.  **SSH — revert symlinks**
    *   Switch `models/current.engine` back to previous `-{{prev_version}}.engine` and restart service (same as step 8/9).
    19.  **HTTP Request — routing back to previous**
    *   PATCH `{"model_version":"{{prev_version}}","scope":"all","percent":100}`.
    20.  **Notify (HTTP/Slack/Email of your choice)**
    *   Use HTTP Request for your notifier (n8n’s general advice: everything can be done with HTTP when in doubt). [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)

* * *

Node credentials you’ll need (n8n)
----------------------------------

*   **SSH (Jetson):** username `reachy`, private key auth preferred. SSH node supports password or key; host/IP is your Jetson. [n8n Docs](https://docs.n8n.io/integrations/builtin/credentials/ssh/?utm_source=chatgpt.com)
*   **FTP (SFTP) (Jetson):** same host/key; use SFTP mode in the FTP node. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ftp/?utm_source=chatgpt.com)
*   **GitHub:** a token with `repo` scope for releases/assets. [n8n Docs](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.github/?utm_source=chatgpt.com)
*   **HTTP Request:** bearer JWT/mTLS to your Ubuntu 2 gateway and Media APIs (per your security section). requirements\_08.3.3

* * *

Field-by-field parameters (high-signal ones)
--------------------------------------------

*   **SSH / Execute a command**
    *   _Command:_ the script above
    *   _Timeout:_ 30–60s
    *   _Continue on fail:_ false (fail fast on bad restarts)
*   **FTP (SFTP) / Upload**
    *   _Binary Property:_ `data`
    *   Upstream “Read Binary File” or “HTTP Request (download)” to populate `data`
    *   _Remote Path:_ exact file paths under `/opt/reachy/...`
*   **HTTP Request / PATCH routing**
    *   _Method:_ PATCH
    *   _Authentication:_ Bearer
    *   _JSON/Options:_ `Send body as JSON`, `Response format: JSON`
*   **Wait (duration)**: `PT60S` for warm-up; `PT45M` for canary soak. (Swap to Wait-for-webhook for human gate.) [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/?utm_source=chatgpt.com)

* * *

Ready-to-import starter (minimal)
---------------------------------

Paste this into n8n → “Import workflow”. It sets up **shadow → canary → rollout** with approvals and SSH/SFTP stubs. You’ll only need to plug credentials and your actual URLs. (Small enough to import and extend.)

```json
{
  "name": "Agent 7 — Deployment (shadow→canary→rollout)",
  "nodes": [
    {
      "parameters": {},
      "id": "ManualTrigger",
      "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1,
      "position": [220, 200]
    },
    {
      "parameters": {
        "path": "deploy/approve",
        "responseMode": "onReceived",
        "options": { "responseCode": 200 }
      },
      "id": "ApprovalWebhook",
      "name": "Approval Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [220, 480]
    },
    {
      "parameters": {
        "url": "https://UBUNTU2/api/metrics/gates",
        "queryParametersUi": {
          "parameter": [{ "name": "run_id", "value": "={{$json.run_id}}" }]
        }
      },
      "id": "FetchGates",
      "name": "HTTP: Fetch Gates",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [460, 200],
      "credentials": { "httpBasicAuth": { "id": "", "name": "" } }
    },
    {
      "parameters": {
        "conditions": {
          "boolean": [
            { "value1": "={{$json.gateA}}", "operation": "isTrue" }
          ]
        }
      },
      "id": "IfGatesForShadow",
      "name": "IF: Gates OK for Shadow",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [700, 200]
    },
    {
      "parameters": {
        "protocol": "sftp",
        "operation": "upload",
        "path": "/opt/reachy/models/action_recognition-{{$json.version}}.engine",
        "binaryPropertyName": "data"
      },
      "id": "SFTPUploadEngine",
      "name": "SFTP: Upload Engine",
      "type": "n8n-nodes-base.ftp",
      "typeVersion": 1,
      "position": [960, 140],
      "credentials": { "sftp": { "id": "", "name": "" } }
    },
    {
      "parameters": {
        "operation": "executeCommand",
        "command": "set -euo pipefail\ncd /opt/reachy\nln -sfn models/action_recognition-{{$json.version}}.engine models/current.engine\nln -sfn deepstream/config_infer_primary-{{$json.version}}.txt deepstream/config_infer_primary.txt\nsudo systemctl restart reachy-deepstream.service && sleep 2 && systemctl is-active --quiet reachy-deepstream.service"
      },
      "id": "SSHFlipAndRestart",
      "name": "SSH: Flip & Restart",
      "type": "n8n-nodes-base.ssh",
      "typeVersion": 1,
      "position": [1180, 140],
      "credentials": { "ssh": { "id": "", "name": "" } }
    },
    {
      "parameters": { "amount": 60, "unit": "seconds" },
      "id": "WaitWarmup",
      "name": "Wait: Warm-up",
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1,
      "position": [1380, 140]
    },
    {
      "parameters": {
        "url": "https://UBUNTU2/healthz/jetson/{{$json.device_id}}"
      },
      "id": "HealthProbe",
      "name": "HTTP: Jetson Health",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1580, 140]
    },
    {
      "parameters": {
        "conditions": {
          "number": [
            { "value1": "={{$json.latency_ms_p50}}", "operation": "smaller", "value2": 120 },
            { "value1": "={{$json.latency_ms_p95}}", "operation": "smaller", "value2": 250 }
          ]
        }
      },
      "id": "IfStageThresholds",
      "name": "IF: Stage Thresholds",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [1780, 140]
    },
    {
      "parameters": {
        "url": "https://UBUNTU2/api/runtime/routing",
        "options": { "sendBody": true },
        "jsonParameters": true,
        "bodyParametersJson": "{\"model_version\":\"{{$json.version}}\",\"scope\":\"canary\",\"percent\":10}",
        "method": "PATCH"
      },
      "id": "RoutingToCanary",
      "name": "HTTP: Route 10% Canary",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [2000, 140]
    },
    {
      "parameters": { "waitTill": "webhookReceived", "webhookId": "ApprovalWebhook" },
      "id": "WaitApproval",
      "name": "Wait: Canary Approval",
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1,
      "position": [2200, 140]
    },
    {
      "parameters": {
        "url": "https://UBUNTU2/api/runtime/routing",
        "options": { "sendBody": true },
        "jsonParameters": true,
        "bodyParametersJson": "{\"model_version\":\"{{$json.version}}\",\"scope\":\"all\",\"percent\":100}",
        "method": "PATCH"
      },
      "id": "RoutingRollout",
      "name": "HTTP: Route 100% Rollout",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [2400, 140]
    }
  ],
  "connections": {
    "Manual Trigger": { "main": [[{ "node": "HTTP: Fetch Gates", "type": "main", "index": 0 }]] },
    "HTTP: Fetch Gates": { "main": [[{ "node": "IF: Gates OK for Shadow", "type": "main", "index": 0 }]] },
    "IF: Gates OK for Shadow": { "main": [[{ "node": "SFTP: Upload Engine", "type": "main", "index": 0 }], []] },
    "SFTP: Upload Engine": { "main": [[{ "node": "SSH: Flip & Restart", "type": "main", "index": 0 }]] },
    "SSH: Flip & Restart": { "main": [[{ "node": "Wait: Warm-up", "type": "main", "index": 0 }]] },
    "Wait: Warm-up": { "main": [[{ "node": "HTTP: Jetson Health", "type": "main", "index": 0 }]] },
    "HTTP: Jetson Health": { "main": [[{ "node": "IF: Stage Thresholds", "type": "main", "index": 0 }]] },
    "IF: Stage Thresholds": { "main": [[{ "node": "HTTP: Route 10% Canary", "type": "main", "index": 0 }], []] },
    "HTTP: Route 10% Canary": { "main": [[{ "node": "Wait: Canary Approval", "type": "main", "index": 0 }]] },
    "Wait: Canary Approval": { "main": [[{ "node": "HTTP: Route 100% Rollout", "type": "main", "index": 0 }]] }
  }
}
```

* * *

Why these nodes (and where the docs back it up)
-----------------------------------------------

*   **SSH** executes remote commands and can upload files; perfect for symlink swaps and service restarts on Jetson. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ssh/?utm_source=chatgpt.com)
*   **FTP (SFTP)** is the built-in way to push large binaries (engines) securely. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ftp/?utm_source=chatgpt.com)
*   **HTTP Request** is the universal Swiss-army knife for your own APIs (routing flips, metrics, health). [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **Wait** handles warm-ups, soak periods, or approval-via-webhook. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/?utm_source=chatgpt.com)
*   **GitHub nodes** (optional) let you hang releases/notes right in GH. [n8n Docs](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.github/?utm_source=chatgpt.com)

* * *

Rollback, safety, and audit
---------------------------

*   Keep `models/action_recognition-<ver>.engine` alongside `models/current.engine` and only move the **symlink**. Rollback is just switching it back and restarting the service (the SSH node already has the right shape).
*   Every promotion (shadow→canary→rollout) must attach Gate evidence and approval trails; your **Approval Webhook** records who/when (store in your DB from the webhook handler).
*   Follow your spec’s **approval rules**: both dataset and deployment promotions require explicit human approval. AGENTS

* * *

Nice-to-have add-ons (when you want polish)
-------------------------------------------

*   **IF** guard that checks GPU mem and FPS before touching traffic (values from your spec). requirements\_08.3.3
*   **GitHub** “Update Release” step that appends final metrics + model hash.
*   **HTTP Request** to your Media Mover or gateway to persist `model_version` → `device_id` mapping so the UI and audit trail stay in sync.

* * *

If you want, I can tailor the JSON to your exact hostnames and add the approval-webhook signature check. But as is, this covers the whole move: fetch → upload → switch → warm-up → probe → canary → approve → rollout, with clear off-ramps for rollback.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)