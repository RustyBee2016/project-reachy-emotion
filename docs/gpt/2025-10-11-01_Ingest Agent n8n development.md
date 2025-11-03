# 01_Ingest Agent n8n development

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 20:43:23  
**Updated:** 10/21/2025 22:13:59  
**Exported:** 10/21/2025 22:28:55  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9a82a-88a8-832c-83f5-b92760cbb3cb](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9a82a-88a8-832c-83f5-b92760cbb3cb)  

## Prompt:
consider the chat titled 'ALL Agent-by-Agent Purposes.'

Provide a detailed explanation of how to develop the first AI agent 1: Ingest Agent.
 
At this point, you should provide all the detail you can regarding how to construct the n8n nodes, sub-nodes, parameters, etc.

Be sure to refer to the newest n8n documentation.

## Response:
Thought for 22s

Alright Russ — let’s build Agent 1: **Ingest Agent** in n8n, soup-to-nuts. I’ll give you the exact node graph, recommended parameters/expressions, and why each choice lines up with current n8n behavior.

I’m assuming your “ingest” events are coming from:

*   the web app (user just generated or uploaded a clip),
*   or a cloud generator callback (e.g., Luma/Flow/Veo) that posts a URL to download.

We’ll keep n8n light: **don’t pipe large videos through n8n**. Have n8n tell **Media Mover** on Ubuntu 1 to pull the file by URL, compute hashes, ffprobe, and thumbnail — then n8n waits/polls and writes metadata to Postgres (through your Ubuntu 2 API), returns a webhook response.

* * *

Ingest Agent — workflow shape
=============================

**Trigger first, respond last.** We’ll start with **Webhook** and finish with **Respond to Webhook** so callers get a clean HTTP 200/4xx with details. n8n’s Webhook node is the right entry for this (it’s a trigger); Respond to Webhook lets us decouple long work from the immediate HTTP response when needed [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com).

**Core nodes (happy path)**

1.  **Webhook (trigger)** → 2) **IF (auth check)** → 3) **Code (normalize payload)** → 4) **HTTP Request (MediaMover: pull)** → 5) **Loop Over Items / Wait (poll status)** → 6) **HTTP Request (App API: write DB row)** → 7) **Respond to Webhook (success)**

**Error path**

*   Any failure → **Set (error body)** → **Respond to Webhook (error)**
*   Plus a global **Error Workflow** using **Error Trigger** so failed executions raise alerts consistently [n8n Docs+2n8n Docs+2](https://docs.n8n.io/flow-logic/error-handling/?utm_source=chatgpt.com).

* * *

Exact node-by-node
==================

Below are the **node names, key parameters, and expressions** you can click-in exactly as written. I also include n8n behaviors we’re relying on, with doc links to the latest pages.

### 1) Webhook — “ingest\_webhook”

*   **HTTP Method:** `POST`
*   **Path:** `/video_gen_hook` (adjust to your route plan)
*   **Response mode:** `On Received` (fast ACK), or we can postpone response with _Respond to Webhook_ at the end. For most generators, returning after we’ve queued the pull is fine. If they need a final success with thumb, switch to end-response pattern.
*   **Authentication:** Header token (simple, reliable).
    *   **Header Name:** `X-INGEST-KEY`
    *   We’ll validate it in the next node (n8n Webhook supports custom headers; validation is up to you). Docs recap Webhook as a trigger with dev/prod URLs and method/path controls [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com).

**Payload expectations**  
We’ll accept both:

```json
{
  "source_url": "https://…/clip.mp4",
  "label": "happy",
  "meta": { "generator": "luma", "seed": 42 }
}
```

and generator-style callbacks (e.g., nested under `data.asset.url` etc.). We normalize next.

* * *

### 2) IF — “auth\_check”

*   **Condition:** `{{$json["headers"]["x-ingest-key"]}} == {{$env.INGEST_TOKEN}}`
    *   If **false** → go to error branch: **Set (401 body)** → **Respond to Webhook (401)**.
    *   If **true** → continue.

(You could also do this in a tiny Code node; the IF keeps it declarative.)

* * *

### 3) Code (JavaScript) — “normalize\_payload”

Purpose: unify incoming shapes into a single schema for downstream nodes.

```js
// Input: Webhook JSON
// Output: one item with canonical fields
const b = $json.body ?? $json; // handle if Webhook put body at .body
const sourceUrl = b.source_url ?? b.url ?? b.asset?.url ?? b.data?.asset?.url;
if (!sourceUrl) {
  throw new Error('Missing source_url');
}
const label = b.label ?? b.emotion ?? null;
const meta  = b.meta ?? { generator: b.generator ?? b.source ?? null };
const correlationId = $json.headers?.['x-correlation-id'] ?? $now();

return [
  {
    json: {
      source_url: sourceUrl,
      label,
      meta,
      correlation_id: correlationId,
      idempotency_key: $json.headers?.['idempotency-key'] ?? $now()
    }
  }
];
```

* * *

### 4) HTTP Request — “media\_pull”

**Goal:** Tell Media Mover (Ubuntu 1) to pull the video by URL (so n8n never shuttles GBs of data). This keeps the workflow fast and resilient.

*   **Method:** `POST`
*   **URL:** `http://ubuntu1:8081/api/media/pull` _(If you don’t have this endpoint yet, add it; it matches your §14 “On-ingest” & atomic flows. Otherwise, use an existing `/api/promote` pre-ingest variant.)_
*   **Authentication:** Bearer (short-lived service token) or mTLS per your policy.
*   **Headers:**  
    `Content-Type: application/json`  
    `Idempotency-Key: {{$json.idempotency_key}}` (crucial to avoid dupes)
*   **Body (JSON):**

```json
{
  "source_url": "={{$json.source_url}}",
  "label": "={{$json.label}}",
  "correlation_id": "={{$json.correlation_id}}",
  "compute_thumb": true,
  "ffprobe": true,
  "dest_split": "temp"
}
```

**Expect:** a `202 Accepted` or `200 OK` with a job or `video_id`. We’ll assume response:

```json
{ "video_id": "uuid", "status_url": "http://ubuntu1:8081/api/media/status/uuid" }
```

Use **HTTP Request** for arbitrary REST calls; it’s the versatile workhorse in n8n and can run standalone or as a tool in agent nodes [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com).

* * *

### 5) Loop + Wait — “poll\_status”

We need to **poll** Media Mover’s status (until thumb + ffprobe ready) without busy-spinning.

**Two nice options:**

**A) Loop Over Items (Split in Batches)** + **Wait** nodes:

*   Add **Loop Over Items** (formerly Split in Batches) to iterate a fixed number of attempts (say 20), 1 per loop.
*   Inside the loop, do **HTTP Request** → `status_url` and an **IF** that checks `status=="done"`.
*   Between attempts, add a **Wait** node (2–3 seconds).  
    This aligns with n8n’s “Loop Over Items / Split in Batches” guidance, including examples on `noItemsLeft` and batch loops to avoid hammering APIs [n8n Docs+2n8n+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitinbatches/?utm_source=chatgpt.com).

**B) Simpler single-branch with a While-like pattern:**

*   Use a **Code** node to hold state + timing and call **HTTP Request** inside it.
*   I prefer (A) because it stays visual and uses native nodes.

**Concrete setup for (A):**

5.1) **Set** — “seed\_attempts”

*   **Fields:** `attempts = 20`, `delay_ms = 2000`

5.2) **Loop Over Items** — “attempt\_loop”

*   **Items per batch:** 1
*   **Reset:** Off (default)  
    Docs explain when and how to use it to pace external requests without rate-limit issues [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitinbatches/?utm_source=chatgpt.com).

5.3) **HTTP Request** — “check\_status”

*   **Method:** `GET`
*   **URL:** `={{$json.status_url}}` (coming from “media\_pull”)
*   **Expect:** `{"status":"pending|processing|done|error", "video_id":"…", "file_path":"…", "thumb_url":"…", "ffprobe": {...} }`

5.4) **IF** — “is\_done”

*   Condition: `{{$json["status"]}} == "done"`

**True branch →** proceed

**False branch →**

*   **IF** “more\_attempts?”: `{{$itemIndex}} < {{$('seed_attempts').item.json.attempts}}`
    *   **True → Wait** (delay\_ms), then **Loop Over Items → Next Batch**
    *   **False →** throw error (Set → Respond error), or return partial info

(If you need both the “true” and “false” legs to continue later, you can use **Merge** in _Append_ mode; Merge node behavior and the “append so it doesn’t wait” tip are spelled out here [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.merge/?utm_source=chatgpt.com).)

* * *

### 6) HTTP Request — “app\_db\_write”

Once `status=done`, write metadata in your **Ubuntu 2** API (so the web app sees it):

*   **Method:** `POST`
*   **URL:** `http://ubuntu2/api/videos/ingest-complete`
*   **Headers:** `Content-Type: application/json`, `Authorization: Bearer …`
*   **Body:** include the canonical fields plus what Media Mover returned:

```json
{
  "video_id": "={{$json.video_id}}",
  "file_path": "={{$json.file_path}}",
  "split": "temp",
  "label": "={{$('normalize_payload').item.json.label}}",
  "thumb_url": "={{$json.thumb_url}}",
  "sha256": "={{$json.ffprobe?.sha256}}",
  "size_bytes": "={{$json.ffprobe?.size}}",
  "duration_sec": "={{$json.ffprobe?.duration}}",
  "fps": "={{$json.ffprobe?.fps}}",
  "width": "={{$json.ffprobe?.width}}",
  "height": "={{$json.ffprobe?.height}}",
  "correlation_id": "={{$('normalize_payload').item.json.correlation_id}}"
}
```

If your gateway already exposes the **exact** DB write endpoint (per requirements), just map to it. Otherwise, use your FastAPI controller that persists to Postgres.

* * *

### 7) Respond to Webhook — “respond\_ok”

*   **Status code:** `200`
*   **Response:** JSON

```json
{
  "ok": true,
  "video_id": "={{$json.video_id}}",
  "thumb_url": "={{$json.thumb_url}}",
  "message": "Ingested and indexed."
}
```

n8n’s Respond to Webhook doc shows how it behaves if the node is missing or hit multiple times; enabling the _Response Output Branch_ can also surface what got returned into the canvas for logging/auditing [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.respondtowebhook/?utm_source=chatgpt.com).

* * *

Error handling patterns (recommended)
=====================================

**A) Inline error path**

*   On any node’s error → route to **Set** (“error\_payload”) → **Respond to Webhook (4xx/5xx)** with:

```json
{ "ok": false, "error": "…", "correlation_id": "={{$('normalize_payload').item.json.correlation_id}}" }
```

**B) Global Error Workflow**

*   Create a second workflow with **Error Trigger** as the first node; configure your main workflow’s **Workflow Settings → Error Workflow** to this flow. n8n explains how to attach and what metadata is provided (failed node, stack, JSON, etc.) so you can alert Slack/Email and save the failed items to a DLQ table/file [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.errortrigger/?utm_source=chatgpt.com).

* * *

Security & resilience choices that matter
=========================================

*   **Don’t upload video through n8n**: use pull-by-URL via Media Mover. That avoids n8n timeouts & memory pressure.
*   **Idempotency-Key**: pass it from the webhook caller into Media Mover, and use a unique key per clip (spec says writes must accept an idempotency key). This keeps retries safe.
*   **Auth**: webhook header token + service-to-service bearer (or mTLS). Keep tokens short-lived.
*   **Pagination / batching**: if your day turns into “ingest 200 URLs,” wrap them as an array and use **Loop Over Items** to batch Media Mover calls (it’s the standard rate-limit pattern) [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitinbatches/?utm_source=chatgpt.com).
*   **Merging branches**: when you branch for optional metadata or auth checks, and you need to converge, use **Merge** in the right mode (_Append_ won’t wait for a missing second branch) [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.merge/?utm_source=chatgpt.com).

* * *

Optional add-ons you’ll actually use
====================================

*   **Respond early, finish async**: If a generator insists on a fast ACK (<2s), set Webhook _Response mode = On Received_ and immediately Respond 202 + `correlation_id`. Continue the workflow to completion and ping their callback later (HTTP Request). Respond-node behavior is documented (what happens if it’s missing/duplicated) [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.respondtowebhook/?utm_source=chatgpt.com).
*   **HTTP cURL import**: When wiring external APIs (Luma/Flow/Veo), paste the provider’s cURL and let the HTTP Request node auto-fill (handy in practice) [Reddit](https://www.reddit.com/r/n8n/comments/1kkrgb1/http_node_everything_you_need_to_know_and_how_to/?utm_source=chatgpt.com).
*   **Agent/tool switch**: If you later attach an AI Agent inside n8n, the same **HTTP Request** can be mounted as a tool; current docs call that out (legacy Tool node vs standard node as tool) [n8n Docs](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolhttprequest/?utm_source=chatgpt.com).

* * *

Minimal importable workflow (skeleton)
======================================

You asked for “all the detail” — here’s a compact JSON you can import and then fill in URLs/tokens. It reflects the nodes above (names match). I’m keeping it lean so you don’t drown in canvas noise.

```json
{
  "name": "Agent 1 — Ingest",
  "nodes": [
    {
      "parameters": {
        "path": "video_gen_hook",
        "options": { "responseMode": "onReceived" }
      },
      "id": "ingest_webhook",
      "name": "ingest_webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json[\"headers\"][\"x-ingest-key\"]}}",
              "operation": "equal",
              "value2": "={{$env.INGEST_TOKEN}}"
            }
          ]
        }
      },
      "id": "auth_check",
      "name": "auth_check",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1
    },
    {
      "parameters": {
        "language": "JavaScript",
        "jsCode": "// normalize_payload (see message)"
      },
      "id": "normalize_payload",
      "name": "normalize_payload",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2
    },
    {
      "parameters": {
        "url": "http://ubuntu1:8081/api/media/pull",
        "authentication": "predefinedCredentialType",
        "options": { "responseFormat": "json" },
        "jsonParameters": true,
        "sendHeaders": true,
        "headerParametersJson": "{\"Content-Type\":\"application/json\",\"Idempotency-Key\":\"={{$json.idempotency_key}}\"}",
        "bodyParametersJson": "{\"source_url\":\"={{$json.source_url}}\",\"label\":\"={{$json.label}}\",\"correlation_id\":\"={{$json.correlation_id}}\",\"compute_thumb\":true,\"ffprobe\":true,\"dest_split\":\"temp\"}"
      },
      "id": "media_pull",
      "name": "media_pull",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "credentials": { "httpBasicAuth": { "id": "REPLACE_ME", "name": "service-token" } }
    },
    {
      "parameters": {
        "values": { "string": [{ "name": "attempts", "value": "20" }, { "name": "delay_ms", "value": "2000" }] },
        "options": {}
      },
      "id": "seed_attempts",
      "name": "seed_attempts",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2
    },
    {
      "parameters": {
        "options": { "itemsPerBatch": 1 }
      },
      "id": "attempt_loop",
      "name": "attempt_loop",
      "type": "n8n-nodes-base.splitInBatches",
      "typeVersion": 1
    },
    {
      "parameters": {
        "url": "={{$json.status_url}}",
        "options": { "responseFormat": "json" }
      },
      "id": "check_status",
      "name": "check_status",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4
    },
    {
      "parameters": {
        "conditions": { "string": [{ "value1": "={{$json[\"status\"]}}", "operation": "equal", "value2": "done" }] }
      },
      "id": "is_done",
      "name": "is_done",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1
    },
    {
      "parameters": { "amount": 2, "unit": "seconds" },
      "id": "wait_between",
      "name": "wait_between",
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1
    },
    {
      "parameters": {
        "url": "http://ubuntu2/api/videos/ingest-complete",
        "options": { "responseFormat": "json" },
        "jsonParameters": true,
        "sendHeaders": true,
        "headerParametersJson": "{\"Content-Type\":\"application/json\"}",
        "bodyParametersJson": "{\"video_id\":\"={{$json.video_id}}\",\"file_path\":\"={{$json.file_path}}\",\"split\":\"temp\",\"label\":\"={{$('normalize_payload').item.json.label}}\",\"thumb_url\":\"={{$json.thumb_url}}\",\"sha256\":\"={{$json.ffprobe?.sha256}}\",\"size_bytes\":\"={{$json.ffprobe?.size}}\",\"duration_sec\":\"={{$json.ffprobe?.duration}}\",\"fps\":\"={{$json.ffprobe?.fps}}\",\"width\":\"={{$json.ffprobe?.width}}\",\"height\":\"={{$json.ffprobe?.height}}\",\"correlation_id\":\"={{$('normalize_payload').item.json.correlation_id}}\"}"
      },
      "id": "app_db_write",
      "name": "app_db_write",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4
    },
    {
      "parameters": {
        "responseBody": "{\"ok\": true, \"video_id\": \"={{$json.video_id}}\", \"thumb_url\": \"={{$json.thumb_url}}\"}",
        "responseCode": 200
      },
      "id": "respond_ok",
      "name": "respond_ok",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1
    }
  ],
  "connections": {
    "ingest_webhook": { "main": [[{ "node": "auth_check", "type": "main", "index": 0 }]] },
    "auth_check": {
      "main": [
        [{ "node": "normalize_payload", "type": "main", "index": 0 }],
        [{ "node": "respond_ok", "type": "main", "index": 0 }]  // replace with 401 path
      ]
    },
    "normalize_payload": { "main": [[{ "node": "media_pull", "type": "main", "index": 0 }]] },
    "media_pull": { "main": [[{ "node": "seed_attempts", "type": "main", "index": 0 }]] },
    "seed_attempts": { "main": [[{ "node": "attempt_loop", "type": "main", "index": 0 }]] },
    "attempt_loop": { "main": [[{ "node": "check_status", "type": "main", "index": 0 }]] },
    "check_status": { "main": [[{ "node": "is_done", "type": "main", "index": 0 }]] },
    "is_done": {
      "main": [
        [{ "node": "app_db_write", "type": "main", "index": 0 }],
        [{ "node": "wait_between", "type": "main", "index": 0 }]
      ]
    },
    "wait_between": { "main": [[{ "node": "attempt_loop", "type": "main", "index": 0 }]] },
    "app_db_write": { "main": [[{ "node": "respond_ok", "type": "main", "index": 0 }]] }
  }
}
```

> After import, replace credential placeholders and URLs, and paste the **normalize\_payload** JS.

* * *

Why these n8n choices are “by the book”
=======================================

*   **Webhook** is the canonical entry for external events; it’s a trigger and supports method/path config, with clear doc coverage. **Respond to Webhook** defines success/error responses and can be placed anywhere in the flow depending on your timing needs [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com).
*   **HTTP Request** is the default for REST integration, including JSON, headers, auth, pagination, and adaptable as a tool if you later play with agent nodes in n8n [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com).
*   **Loop Over Items (Split in Batches)** is the sanctioned pattern for pacing and retry-style polling without tight loops; the docs and examples show batching, `noItemsLeft`, and run index patterns you can copy if needed [n8n Docs+2n8n+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitinbatches/?utm_source=chatgpt.com).
*   **Merge (Append mode)** is a handy fallback when you want to re-join branches without waiting for a missing second stream, per the Merge docs and community tip [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.merge/?utm_source=chatgpt.com).
*   **Error Trigger / Error Workflow** is how n8n wants you to wire global error handling and notifications; it’s documented in both the flow logic guide and course materials [n8n Docs+2n8n Docs+2](https://docs.n8n.io/flow-logic/error-handling/?utm_source=chatgpt.com).

* * *

Fit with your project contracts
===============================

*   **Media Mover API**: you already defined atomic ops and idempotency. The “pull” endpoint matches your “On-ingest” plan (ffprobe + thumb + hash). If the endpoint name differs, just swap the URL; the flow stays the same.
*   **DB shape**: `video(file_path, split, label, sha256, size_bytes, duration_sec, fps, width, height, …)` is covered in your requirements; that’s exactly what “app\_db\_write” sends.
*   **Idempotency**: caller → n8n → Media Mover all carry `Idempotency-Key`.

* * *

If you want, I can also drop a tiny **Error Workflow** import (Error Trigger → Slack/Email → save failed input as JSONL). But this is enough to stand the Ingest Agent up cleanly and by the docs.

## Prompt:
If possible, provide an all-encompassing JSON file for import into n8n.  If not, provide several individual JSONs

## Response:
Thought for 18s

Got you. I’m giving you two clean, import-ready JSONs:

*   one for the **Ingest Agent** workflow (full happy path + 401 branch + polling),
*   one for the **Global Error Handler** (Error Trigger → basic JSON log stub).

n8n imports one workflow per JSON, so just import both. Credentials aren’t included by design; the HTTP nodes use headers so you can paste tokens safely later.  
(If you prefer “respond immediately, finish async,” flip the Webhook node’s Response mode after import.)

* * *

### Workflow 1 — **Agent 1: Ingest**

```json
{
  "name": "Agent 1 — Ingest",
  "nodes": [
    {
      "parameters": {
        "path": "video_gen_hook",
        "httpMethod": "POST",
        "responseMode": "responseNode",
        "options": {
          "binaryData": false,
          "ignoreBots": false
        }
      },
      "id": "ingest_webhook",
      "name": "ingest_webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [200, 200]
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json[\"headers\"][\"x-ingest-key\"]}}",
              "operation": "equal",
              "value2": "={{$env.INGEST_TOKEN}}"
            }
          ]
        }
      },
      "id": "auth_check",
      "name": "auth_check",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [460, 200]
    },
    {
      "parameters": {
        "language": "JavaScript",
        "jsCode": "const b = $json.body ?? $json;\nconst sourceUrl = b.source_url ?? b.url ?? b.asset?.url ?? b.data?.asset?.url;\nif (!sourceUrl) {\n  throw new Error('Missing source_url');\n}\nconst label = b.label ?? b.emotion ?? null;\nconst meta  = b.meta ?? { generator: b.generator ?? b.source ?? null };\nconst correlationId = $json.headers?.['x-correlation-id'] ?? $now();\nconst idem = $json.headers?.['idempotency-key'] ?? $now();\nreturn [{ json: { source_url: sourceUrl, label, meta, correlation_id: correlationId, idempotency_key: idem } }];"
      },
      "id": "normalize_payload",
      "name": "normalize_payload",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [720, 200]
    },
    {
      "parameters": {
        "url": "http://ubuntu1:8081/api/media/pull",
        "options": {
          "responseFormat": "json",
          "timeout": 90000
        },
        "jsonParameters": true,
        "sendHeaders": true,
        "headerParametersJson": "{\"Content-Type\":\"application/json\",\"Idempotency-Key\":\"={{$json.idempotency_key}}\"}",
        "bodyParametersJson": "{\"source_url\":\"={{$json.source_url}}\",\"label\":\"={{$json.label}}\",\"correlation_id\":\"={{$json.correlation_id}}\",\"compute_thumb\":true,\"ffprobe\":true,\"dest_split\":\"temp\"}"
      },
      "id": "media_pull",
      "name": "media_pull",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [980, 200]
    },
    {
      "parameters": {
        "values": {
          "string": [
            { "name": "attempts", "value": "20" },
            { "name": "delay_ms", "value": "2000" }
          ]
        },
        "options": {}
      },
      "id": "seed_attempts",
      "name": "seed_attempts",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [1240, 200]
    },
    {
      "parameters": {
        "options": {
          "itemsPerBatch": 1
        }
      },
      "id": "attempt_loop",
      "name": "attempt_loop",
      "type": "n8n-nodes-base.splitInBatches",
      "typeVersion": 1,
      "position": [1500, 200]
    },
    {
      "parameters": {
        "url": "={{$json.status_url}}",
        "options": {
          "responseFormat": "json",
          "timeout": 60000
        }
      },
      "id": "check_status",
      "name": "check_status",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1740, 200]
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json[\"status\"]}}",
              "operation": "equal",
              "value2": "done"
            }
          ]
        }
      },
      "id": "is_done",
      "name": "is_done",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [1980, 200]
    },
    {
      "parameters": {
        "amount": 2,
        "unit": "seconds"
      },
      "id": "wait_between",
      "name": "wait_between",
      "type": "n8n-nodes-base.wait",
      "typeVersion": 1,
      "position": [1980, 360]
    },
    {
      "parameters": {
        "url": "http://ubuntu2/api/videos/ingest-complete",
        "options": {
          "responseFormat": "json",
          "timeout": 60000
        },
        "jsonParameters": true,
        "sendHeaders": true,
        "headerParametersJson": "{\"Content-Type\":\"application/json\"}",
        "bodyParametersJson": "{\n  \"video_id\": \"={{$json.video_id}}\",\n  \"file_path\": \"={{$json.file_path}}\",\n  \"split\": \"temp\",\n  \"label\": \"={{$('normalize_payload').item.json.label}}\",\n  \"thumb_url\": \"={{$json.thumb_url}}\",\n  \"sha256\": \"={{$json.ffprobe?.sha256}}\",\n  \"size_bytes\": \"={{$json.ffprobe?.size}}\",\n  \"duration_sec\": \"={{$json.ffprobe?.duration}}\",\n  \"fps\": \"={{$json.ffprobe?.fps}}\",\n  \"width\": \"={{$json.ffprobe?.width}}\",\n  \"height\": \"={{$json.ffprobe?.height}}\",\n  \"correlation_id\": \"={{$('normalize_payload').item.json.correlation_id}}\"\n}"
      },
      "id": "app_db_write",
      "name": "app_db_write",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [2220, 200]
    },
    {
      "parameters": {
        "responseBody": "={\"ok\":true,\"video_id\":\"{{$json.video_id}}\",\"thumb_url\":\"{{$json.thumb_url}}\",\"message\":\"Ingested and indexed.\"}",
        "responseCode": 200,
        "options": {
          "responseData": "allEntries"
        }
      },
      "id": "respond_ok",
      "name": "respond_ok",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [2460, 200]
    },
    {
      "parameters": {
        "values": {
          "string": [
            { "name": "ok", "value": "false" },
            { "name": "error", "value": "Unauthorized" }
          ]
        },
        "options": {}
      },
      "id": "set_401",
      "name": "set_401",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [720, 360]
    },
    {
      "parameters": {
        "responseBody": "={\"ok\":false,\"error\":\"Unauthorized\"}",
        "responseCode": 401,
        "options": {
          "responseData": "firstEntryJson"
        }
      },
      "id": "respond_401",
      "name": "respond_401",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [980, 360]
    },
    {
      "parameters": {
        "values": {
          "string": [
            { "name": "ok", "value": "false" },
            { "name": "error", "value": "Ingest timed out before reaching status=done" }
          ]
        },
        "options": {}
      },
      "id": "set_timeout",
      "name": "set_timeout",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [2220, 360]
    },
    {
      "parameters": {
        "responseBody": "={\"ok\":false,\"error\":\"Ingest timed out before reaching status=done\"}",
        "responseCode": 504,
        "options": {
          "responseData": "firstEntryJson"
        }
      },
      "id": "respond_timeout",
      "name": "respond_timeout",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [2460, 360]
    }
  ],
  "connections": {
    "ingest_webhook": {
      "main": [
        [
          { "node": "auth_check", "type": "main", "index": 0 }
        ]
      ]
    },
    "auth_check": {
      "main": [
        [
          { "node": "normalize_payload", "type": "main", "index": 0 }
        ],
        [
          { "node": "set_401", "type": "main", "index": 0 }
        ]
      ]
    },
    "normalize_payload": {
      "main": [
        [
          { "node": "media_pull", "type": "main", "index": 0 }
        ]
      ]
    },
    "media_pull": {
      "main": [
        [
          { "node": "seed_attempts", "type": "main", "index": 0 }
        ]
      ]
    },
    "seed_attempts": {
      "main": [
        [
          { "node": "attempt_loop", "type": "main", "index": 0 }
        ]
      ]
    },
    "attempt_loop": {
      "main": [
        [
          { "node": "check_status", "type": "main", "index": 0 }
        ]
      ]
    },
    "check_status": {
      "main": [
        [
          { "node": "is_done", "type": "main", "index": 0 }
        ]
      ]
    },
    "is_done": {
      "main": [
        [
          { "node": "app_db_write", "type": "main", "index": 0 }
        ],
        [
          { "node": "wait_between", "type": "main", "index": 0 }
        ]
      ]
    },
    "wait_between": {
      "main": [
        [
          { "node": "attempt_loop", "type": "main", "index": 0 }
        ]
      ]
    },
    "app_db_write": {
      "main": [
        [
          { "node": "respond_ok", "type": "main", "index": 0 }
        ]
      ]
    },
    "set_401": {
      "main": [
        [
          { "node": "respond_401", "type": "main", "index": 0 }
        ]
      ]
    },
    "attempt_loop": {
      "done": [
        [
          { "node": "set_timeout", "type": "main", "index": 0 }
        ]
      ]
    },
    "set_timeout": {
      "main": [
        [
          { "node": "respond_timeout", "type": "main", "index": 0 }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "timezone": "America/New_York",
    "errorWorkflow": ""
  },
  "staticData": {},
  "meta": {
    "templateCredsSetupCompleted": true
  }
}
```

**What to edit after import**

*   In **auth\_check**, set env var `INGEST_TOKEN` in n8n (Settings → Environment variables) or replace the expression with a literal.
*   In **media\_pull** and **app\_db\_write**, replace hostnames/ports and add any required auth headers.
*   If your Media Mover returns a different shape, tweak the body/paths in **app\_db\_write**.
*   If you want “respond immediately,” open the **Webhook** node → _Respond_ → set **On Received** and optionally add a separate callback step to notify the caller later.

* * *

### Workflow 2 — **Global Error Handler**

```json
{
  "name": "Error Handler — Agent 1",
  "nodes": [
    {
      "parameters": {},
      "id": "error_trigger",
      "name": "error_trigger",
      "type": "n8n-nodes-base.errorTrigger",
      "typeVersion": 1,
      "position": [220, 200]
    },
    {
      "parameters": {
        "values": {
          "string": [
            { "name": "workflow_name", "value": "={{$json.workflow.name}}"},
            { "name": "node", "value": "={{$json.execution.node?.name}}"},
            { "name": "error_message", "value": "={{$json.execution.error.message}}"},
            { "name": "timestamp", "value": "={{$now()}}"}
          ],
          "json": [
            { "name": "input_data", "value": "={{$json.execution.lastNodeExecuted?.data}}"}
          ]
        },
        "options": {}
      },
      "id": "shape_error",
      "name": "shape_error",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [500, 200]
    },
    {
      "parameters": {
        "url": "http://ubuntu2/api/internal/error-log",
        "options": {
          "responseFormat": "json",
          "timeout": 30000
        },
        "jsonParameters": true,
        "sendHeaders": true,
        "headerParametersJson": "{\"Content-Type\":\"application/json\"}",
        "bodyParametersJson": "{\"workflow\":\"={{$json.workflow_name}}\",\"node\":\"={{$json.node}}\",\"message\":\"={{$json.error_message}}\",\"timestamp\":\"={{$json.timestamp}}\",\"input_data\": {{JSON.stringify($json.input_data) ?? '{}'}}}"
      },
      "id": "send_log",
      "name": "send_log",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [760, 200]
    }
  ],
  "connections": {
    "error_trigger": {
      "main": [
        [
          { "node": "shape_error", "type": "main", "index": 0 }
        ]
      ]
    },
    "shape_error": {
      "main": [
        [
          { "node": "send_log", "type": "main", "index": 0 }
        ]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "timezone": "America/New_York"
  },
  "staticData": {},
  "meta": {
    "templateCredsSetupCompleted": true
  }
}
```

**Hook it up:** In the Ingest workflow, go to **Workflow → Settings → Error workflow** and select “Error Handler — Agent 1”.

* * *

If you want me to flip the Ingest to **“respond immediately (202) and finish async”**, I’ll hand you a second variant that swaps the Webhook response mode and adds a tiny callback step.

## Prompt:
Summarize the purpose of the ingest agent in one sentence.

## Response:
Thought for 6s

The Ingest Agent receives new video URLs/callbacks, authenticates and normalizes them, instructs Media Mover to pull and fingerprint the file (ffprobe + thumbnail), writes the resulting metadata to the app/DB, and returns a clear status to the caller.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)