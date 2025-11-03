# 06_Evaluation Agent development

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 21:38:27  
**Updated:** 10/21/2025 21:56:58  
**Exported:** 10/21/2025 22:01:37  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b511-e4f8-832b-ace4-83006d5d1ab7](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b511-e4f8-832b-ace4-83006d5d1ab7)  

## Prompt:
consider the chat titled 'ALL Agent-by-Agent Purposes.'

Provide a detailed explanation of how to develop the first AI agent 6: Evaluation Agent.
At this point, you should provide all the detail you can regarding how to construct the n8n nodes, sub-nodes, parameters, etc.

Be sure to refer to the newest n8n documentation.

Thought for 18s

## Response:
Alright Russ — time to wire up Agent 6: Evaluation. This one sits in the middle of your gates (A/B/C), pulls metrics from training, checks them against the thresholds in requirements, and decides what’s safe to promote next.

I’ll give you:

1.  what this agent’s supposed to do in your system,
2.  the exact n8n nodes and parameters (with expressions),
3.  a drop-in n8n workflow JSON you can import,
4.  error-handling and retry patterns.

I’ll also point at the relevant n8n docs as we go so nothing’s hand-wavy.

* * *

What the Evaluation Agent does (in your stack)
==============================================

*   **Input:** a `training.completed` event with where to read metrics/artifacts (typically MLflow run ID, dataset hash, confusion matrix path, latency figures from your eval script).
*   **Logic:** compare those numbers to **Gate A/B/C** thresholds (accuracy/F1, calibration, latency, GPU mem, etc.) from your spec. If it passes Gate A → publish “validated:offline”; if configured to continue, it can also request a **robot shadow** eval (Gate B), and so on. (Thresholds: see §7.1 Deployment Gates in requirements.) requirements\_08.3.3
*   **Outputs:**
    *   success → append‐only verdict object, update MLflow run tags (`evaluation_status`, `gate_reached`, `reasons`), and emit an event (e.g., `evaluation.passed` with which gate).
    *   failure → same, with reasons; route to DLQ/Slack.

Design rule: the DB/MLflow stay source-of-truth; this agent only decides and annotates, it never moves files or deploys.

* * *

Workflow shape (nodes + params)
===============================

> Trigger choices

*   If you fan everything through events: **Webhook** trigger (or your internal webhook) → **Respond to Webhook** to return the verdict synchronously when you want. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)
*   If you prefer callable subflows: call this via **Execute Workflow** from the Training Orchestrator and return a structured verdict. (Community notes on passing results back.) [n8n Community](https://community.n8n.io/t/get-output-from-execute-workflow/40460?utm_source=chatgpt.com)

### 0) **Webhook** (trigger)

*   **Path:** `/eval/gate`
*   **HTTP Method:** POST
*   **Payload (example):**

```json
{
  "mlflow_run_id": "4f4b1a2...",
  "dataset_hash": "sha256:…",
  "artifacts_base": "http://ubuntu1:5000/api/2.0/mlflow/artifacts",
  "metrics_endpoint": "http://ubuntu1:5000/api/2.0/mlflow/runs/get",
  "latency_summary_url": "http://ubuntu2:8080/api/eval/latency/4f4b1a2",
  "gate": "A", 
  "model_version_hint": "actionrecog-0.8.3-trt"
}
```

### 1) **HTTP Request — Fetch MLflow run**

Docs: n8n HTTP Request node. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)

*   **Method:** POST
*   **URL:** `{{$json["metrics_endpoint"]}}`
*   **Body (JSON):** `{"run_id": "{{$json["mlflow_run_id"]}}"}`
*   **Response Format:** JSON
*   **Name:** `get_run`

### 2) **Code — Extract core metrics**

Docs: Code node + expressions/paired items (use the modern `$()` style). [n8n Docs+3n8n Docs+3n8n Docs+3](https://docs.n8n.io/code/code-node/?utm_source=chatgpt.com)

*   **Language:** JavaScript
*   **Code (trimmed):**

```js
// Expect MLflow /runs/get payload
const run = $("get_run").first().json.run || {};
const m = (name, def=null) => {
  const kv = (run.data?.metrics || []).find(x => x.key === name);
  return kv?.value ?? def;
};
// pull metrics used in Gate A
const macroF1 = m("macro_f1");
const balAcc = m("balanced_accuracy");
const ece = m("ece");
const brier = m("brier");
const perClass = JSON.parse(
  (run.data?.tags || []).find(t => t.key === "per_class_f1")?.value || "{}"
);
// stash for later
return [{macroF1, balAcc, ece, brier, perClass}];
```

### 3) **HTTP Request — Latency & GPU summary**

*   **Method:** GET
*   **URL:** `{{$json["latency_summary_url"]}}`
*   **Name:** `get_latency`  
    This is whatever your eval job exported (p50/p95 latency, GPU mem). You can serve it via your FastAPI eval endpoint.

### 4) **Code — Compare to Gate thresholds**

*   Pull thresholds from your **requirements** (§7.1). For Gate A: Macro F1 ≥ 0.84; per-class floors ≥ 0.75; no class < 0.70; ECE ≤ 0.08; Brier ≤ 0.16. Latency gates apply in B/C. requirements\_08.3.3
*   **Code (trimmed):**

```js
const m = $("Code").first().json;           // from step 2
const lat = $("get_latency").first().json;  // {p50, p95, gpu_mem}
const gate = $json.gate || "A";

function checkGateA() {
  const floorsOk = Object.values(m.perClass).every(v => v >= 0.75) &&
                   Math.min(...Object.values(m.perClass)) >= 0.70;
  const reasons = [];
  if ((m.macroF1 ?? 0) < 0.84) reasons.push(`macroF1 ${m.macroF1} < 0.84`);
  if ((m.balAcc ?? 0) < 0.85)  reasons.push(`balAcc ${m.balAcc} < 0.85`);
  if ((m.ece ?? 1) > 0.08)     reasons.push(`ECE ${m.ece} > 0.08`);
  if ((m.brier ?? 1) > 0.16)   reasons.push(`Brier ${m.brier} > 0.16`);
  if (!floorsOk)               reasons.push(`class floors violated`);
  return {pass: reasons.length === 0, reasons};
}

function checkGateB() {
  const reasons = [];
  if ((lat.p50 ?? 1e9) > 120) reasons.push(`p50 ${lat.p50}ms > 120`);
  if ((lat.p95 ?? 1e9) > 250) reasons.push(`p95 ${lat.p95}ms > 250`);
  if ((lat.gpu_mem ?? 9) > 2.5) reasons.push(`GPU mem ${lat.gpu_mem}GB > 2.5`);
  if ((m.macroF1 ?? 0) < 0.80) reasons.push(`macroF1 ${m.macroF1} < 0.80`);
  return {pass: reasons.length === 0, reasons};
}

let result;
if (gate === "A") result = {...checkGateA(), gate};
else if (gate === "B") result = {...checkGateB(), gate};
else result = {pass:false, reasons:["Gate not implemented"], gate};

return [result];
```

### 5) **IF — Pass?**

*   **Condition:** `={{$json["pass"] === true}}`
*   **Name:** `if_pass`

### 6a) **HTTP Request — Tag MLflow run (success)**

*   **Method:** POST
*   **URL:** `http://ubuntu1:5000/api/2.0/mlflow/runs/set-tag`
*   **Body:**

```json
{
  "run_id": "={{$json["mlflow_run_id"]}}",
  "key": "evaluation_status",
  "value": "passed-{{$json["gate"]}}"
}
```

### 6b) **HTTP Request — Publish success event**

*   Post to your internal event bus (or FastAPI)—`evaluation.passed` with gate. Keep it idempotent (Idempotency-Key).
*   **Method:** POST
*   **URL:** `http://ubuntu2:8080/api/events/evaluation`
*   **Headers:** `Idempotency-Key: {{$json["mlflow_run_id"]}}-{{$json["gate"]}}`
*   **Body:** verdict JSON + useful fields (dataset\_hash, model\_version\_hint).

### 7a) **HTTP Request — Tag MLflow run (failure)**

*   Same endpoint as 6a, with `value: "failed-{{$json["gate"]}}"`.

### 7b) **HTTP Request — Publish failure to DLQ/Slack**

*   Post payload with `reasons` and correlation id.

### 8) **Respond to Webhook** (optional)

*   **Response Code:** `={{$json["pass"] ? 200 : 422}}`
*   **Response Body:** the verdict JSON. Gotchas and options are documented. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.respondtowebhook/?utm_source=chatgpt.com)

> Notes on data mapping:

*   Use **Expressions** to plumb inputs/outputs (`{{$json…}}`, `$("node").item.json…`). [n8n Docs](https://docs.n8n.io/code/expressions/?utm_source=chatgpt.com)
*   When you create/merge custom items in Code nodes, keep paired item links in mind if downstream nodes reference previous items. [n8n Docs+1](https://docs.n8n.io/integrations/creating-nodes/build/reference/paired-items/?utm_source=chatgpt.com)

* * *

Error handling & retry (n8n-native)
===================================

*   Add a **separate Error Workflow** so any failure routes to a handler that logs, increments a metric, and can auto-retry with backoff (ex: hourly scan of failed executions → retry). [n8n Docs+1](https://docs.n8n.io/flow-logic/error-handling/?utm_source=chatgpt.com)
*   For transient HTTP issues: in each HTTP Request node, enable **“Retry on Fail”** and set a sensible **Max Attempts** and **Delay** (node → Settings). (This uses per-node retry; the error-workflow can catch the rest.)

* * *

Importable n8n workflow (Evaluation Agent v0.1)
===============================================

Paste into **Import from JSON**. Update hostnames, tokens, and paths to match Ubuntu 1/2.

```json
{
  "name": "Agent 6 - Evaluation (Gate A/B)",
  "nodes": [
    {
      "parameters": {
        "path": "eval/gate",
        "responseMode": "onReceived",
        "options": {
          "responseData": "allEntries",
          "responseCode": 200
        }
      },
      "id": "Webhook",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1
    },
    {
      "parameters": {
        "authentication": "none",
        "requestMethod": "POST",
        "url": "={{$json[\"metrics_endpoint\"]}}",
        "jsonParameters": true,
        "options": { "retryOnFail": true, "maxRetries": 3, "retry": { "waitBetweenAttempts": 1000 } },
        "bodyParametersJson": "={\"run_id\":\"{{$json[\"mlflow_run_id\"]}}\"}"
      },
      "id": "get_run",
      "name": "HTTP Run → MLflow",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4
    },
    {
      "parameters": {
        "language": "JavaScript",
        "jsCode": "const run = $(\"HTTP Run → MLflow\").first().json.run || {};\nconst m = (name, def=null) => {\n  const kv = (run.data?.metrics || []).find(x => x.key === name);\n  return kv?.value ?? def;\n};\nconst macroF1 = m(\"macro_f1\");\nconst balAcc = m(\"balanced_accuracy\");\nconst ece = m(\"ece\");\nconst brier = m(\"brier\");\nconst perClass = JSON.parse((run.data?.tags || []).find(t => t.key === \"per_class_f1\")?.value || \"{}\");\nreturn [{macroF1, balAcc, ece, brier, perClass}];"
      },
      "id": "extract_core",
      "name": "Code - Extract Core Metrics",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2
    },
    {
      "parameters": {
        "authentication": "none",
        "requestMethod": "GET",
        "url": "={{$json[\"latency_summary_url\"]}}",
        "jsonParameters": false,
        "options": { "retryOnFail": true, "maxRetries": 3, "retry": { "waitBetweenAttempts": 1000 } }
      },
      "id": "get_latency",
      "name": "HTTP Latency/GPU",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4
    },
    {
      "parameters": {
        "language": "JavaScript",
        "jsCode": "const m = $(\"Code - Extract Core Metrics\").first().json;\nconst lat = $(\"HTTP Latency/GPU\").first().json; // {p50,p95,gpu_mem}\nconst gate = $json.gate || \"A\";\nfunction checkGateA(){\n  const vals = Object.values(m.perClass||{});\n  const floorsOk = vals.every(v => v >= 0.75) && (vals.length? Math.min(...vals) >= 0.70 : true);\n  const reasons = [];\n  if ((m.macroF1 ?? 0) < 0.84) reasons.push(`macroF1 ${m.macroF1} < 0.84`);\n  if ((m.balAcc ?? 0) < 0.85) reasons.push(`balAcc ${m.balAcc} < 0.85`);\n  if ((m.ece ?? 1) > 0.08) reasons.push(`ECE ${m.ece} > 0.08`);\n  if ((m.brier ?? 1) > 0.16) reasons.push(`Brier ${m.brier} > 0.16`);\n  if (!floorsOk) reasons.push(\"class floors violated\");\n  return {pass: reasons.length===0, reasons};\n}\nfunction checkGateB(){\n  const reasons = [];\n  if ((lat.p50 ?? 1e9) > 120) reasons.push(`p50 ${lat.p50}ms > 120`);\n  if ((lat.p95 ?? 1e9) > 250) reasons.push(`p95 ${lat.p95}ms > 250`);\n  if ((lat.gpu_mem ?? 9) > 2.5) reasons.push(`GPU mem ${lat.gpu_mem}GB > 2.5`);\n  if ((m.macroF1 ?? 0) < 0.80) reasons.push(`macroF1 ${m.macroF1} < 0.80`);\n  return {pass: reasons.length===0, reasons};\n}\nlet result;\nif (gate === \"A\") result = {...checkGateA(), gate};\nelse if (gate === \"B\") result = {...checkGateB(), gate};\nelse result = {pass:false, reasons:[\"Gate not implemented\"], gate};\nreturn [result];"
      },
      "id": "compare_to_gates",
      "name": "Code - Compare to Gates",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2
    },
    {
      "parameters": {
        "conditions": { "boolean": [{ "value1": "={{$json[\"pass\"]}}", "operation": "isTrue" }] }
      },
      "id": "if_pass",
      "name": "IF pass?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2
    },
    {
      "parameters": {
        "authentication": "none",
        "requestMethod": "POST",
        "url": "http://ubuntu1:5000/api/2.0/mlflow/runs/set-tag",
        "jsonParameters": true,
        "options": { "retryOnFail": true, "maxRetries": 3 },
        "bodyParametersJson": "={\"run_id\":\"{{$json[\"mlflow_run_id\"]}}\",\"key\":\"evaluation_status\",\"value\":\"passed-{{$json[\"gate\"]}}\"}"
      },
      "id": "tag_pass",
      "name": "MLflow Tag (pass)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4
    },
    {
      "parameters": {
        "authentication": "none",
        "requestMethod": "POST",
        "url": "http://ubuntu2:8080/api/events/evaluation",
        "jsonParameters": true,
        "options": { "retryOnFail": true, "maxRetries": 3 },
        "headerParametersJson": "={\"Idempotency-Key\":\"{{$json[\"mlflow_run_id\"]}}-{{$json[\"gate\"]}}\"}",
        "bodyParametersJson": "={\"type\":\"evaluation.passed\",\"gate\":\"{{$json[\"gate\"]}}\",\"mlflow_run_id\":\"{{$json[\"mlflow_run_id\"]}}\",\"dataset_hash\":\"{{$json[\"dataset_hash\"]}}\",\"reasons\":[]}"
      },
      "id": "event_pass",
      "name": "Publish Event (pass)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4
    },
    {
      "parameters": {
        "authentication": "none",
        "requestMethod": "POST",
        "url": "http://ubuntu1:5000/api/2.0/mlflow/runs/set-tag",
        "jsonParameters": true,
        "options": { "retryOnFail": true, "maxRetries": 3 },
        "bodyParametersJson": "={\"run_id\":\"{{$json[\"mlflow_run_id\"]}}\",\"key\":\"evaluation_status\",\"value\":\"failed-{{$json[\"gate\"]}}\"}"
      },
      "id": "tag_fail",
      "name": "MLflow Tag (fail)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4
    },
    {
      "parameters": {
        "authentication": "none",
        "requestMethod": "POST",
        "url": "http://ubuntu2:8080/api/events/evaluation",
        "jsonParameters": true,
        "options": { "retryOnFail": true, "maxRetries": 3 },
        "bodyParametersJson": "={\"type\":\"evaluation.failed\",\"gate\":\"{{$json[\"gate\"]}}\",\"mlflow_run_id\":\"{{$json[\"mlflow_run_id\"]}}\",\"dataset_hash\":\"{{$json[\"dataset_hash\"]}}\",\"reasons\":{{$json[\"reasons\"]}}}"
      },
      "id": "event_fail",
      "name": "Publish Event (fail)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4
    },
    {
      "parameters": {
        "responseCode": "={{$json[\"pass\"] ? 200 : 422}}",
        "responseBody": "={{$json}}",
        "options": { "responseData": "allEntries" }
      },
      "id": "respond",
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1
    }
  ],
  "connections": {
    "Webhook": { "main": [[{"node":"HTTP Run → MLflow","type":"main","index":0}]] },
    "HTTP Run → MLflow": { "main": [[{"node":"Code - Extract Core Metrics","type":"main","index":0}]] },
    "Code - Extract Core Metrics": { "main": [[{"node":"HTTP Latency/GPU","type":"main","index":0}]] },
    "HTTP Latency/GPU": { "main": [[{"node":"Code - Compare to Gates","type":"main","index":0}]] },
    "Code - Compare to Gates": { "main": [[{"node":"IF pass?","type":"main","index":0}, {"node":"Respond to Webhook","type":"main","index":0}]] },
    "IF pass?": { "main": [[{"node":"MLflow Tag (pass)","type":"main","index":0}], [{"node":"MLflow Tag (fail)","type":"main","index":0}]] },
    "MLflow Tag (pass)": { "main": [[{"node":"Publish Event (pass)","type":"main","index":0}]] },
    "MLflow Tag (fail)": { "main": [[{"node":"Publish Event (fail)","type":"main","index":0}]] },
    "Publish Event (pass)": { "main": [[{"node":"Respond to Webhook","type":"main","index":0}]] },
    "Publish Event (fail)": { "main": [[{"node":"Respond to Webhook","type":"main","index":0}]] }
  },
  "meta": { "templateCredsSetup": true }
}
```

* * *

How this lines up with your gates & roles
=========================================

*   Gate logic mirrors **§7.1 Deployment Gates** (A: offline validation; B: robot shadow; C: limited rollout). You can add a second branch to call a **Jetson shadow eval** job before running Gate B checks, then reuse the same IF/HTTP pattern. requirements\_08.3.3
*   This agent’s contract should live in your repo as `agents/evaluation.yaml`, marked **role: critic** (decider), with inputs/outputs per **AGENTS.md** template. AGENTS

* * *

Practical tips (so you don’t trip)
==================================

*   **Expressions everywhere:** prefer `$("Node Name")` over `$node[...]` in Code to preserve item linking. It saves you from “multiple matching items” headaches later. [n8n Community+1](https://community.n8n.io/t/understanding-the-differences-between-node-and-expressions-in-n8n/34384?utm_source=chatgpt.com)
*   **Responding to webhooks:** if you need to return a single aggregated object, use the **Aggregate** node first (or switch the webhook to “respond when last node finishes”). [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.respondtowebhook/?utm_source=chatgpt.com)
*   **Retries:** use per-node retries for flaky HTTPs; backstop with an **Error Workflow** that sweeps failed executions and re-queues them (n8n has a reference auto-retry example). [n8n Docs+1](https://docs.n8n.io/flow-logic/error-handling/?utm_source=chatgpt.com)
*   **Code node hygiene:** small, pure functions; return **one** item for the verdict to make downstream IFs trivial. Docs have good patterns for Code node basics. [n8n Docs](https://docs.n8n.io/data/code/?utm_source=chatgpt.com)

If you want me to add Gate C and a Jetson shadow-eval call (DeepStream probe + latency read) into that JSON, I can wire those in next pass.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)