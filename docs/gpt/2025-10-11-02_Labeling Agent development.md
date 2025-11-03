# 02_Labeling Agent development

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 21:04:51  
**Updated:** 10/21/2025 22:10:11  
**Exported:** 10/21/2025 22:11:21  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9ad31-c58c-832d-b0a1-7045ae01cb6b](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9ad31-c58c-832d-b0a1-7045ae01cb6b)  

## Prompt:
consider the chat titled 'ALL Agent-by-Agent Purposes.'

Provide a detailed explanation of how to develop the first AI agent 2: Labeling Agent.
At this point, you should provide all the detail you can regarding how to construct the n8n nodes, sub-nodes, parameters, etc.

Be sure to refer to the newest n8n documentation.

## Response:
Thought for 23s

Alright Russ—Labeling Agent time. This one’s your “human-in-the-loop glue”: it takes a label event from the web app, validates it, commits it to Postgres, optionally hits Media-Mover for `/relabel` or `/promote`, and hands a clean response back to the UI. It leans on Webhook → Code → Postgres → HTTP Request, with strict idempotency and audit trails to match your specs (labels, splits, idempotency, manifests) from the project docs. requirements\_08.3.3 AGENTS

I’ll give you:

1.  the node-by-node build (with exact parameters/expressions),
2.  minimal DB DDL you’ll want in place, and
3.  a ready-to-import n8n workflow JSON you can drop in and edit creds.

I’m referencing current n8n docs for each node so nothing’s guessing. [n8n Docs+5n8n Docs+5n8n Docs+5](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)

What the Labeling Agent does (in your system)
=============================================

*   **Input** (from web app): `POST /n8n/label` with `{ video_id, label, action, rater_id?, notes?, idempotency_key? }`.
*   **DB writes**: upsert into `label_event` (append-only trail) + update `video.label` (source of truth per reqs), with a uniqueness guard on `(video_id, idempotency_key)`. requirements\_08.3.3
*   **Side-effects**: call Media-Mover:
    *   `/api/relabel` when `action in {"label_only","promote_*"}`,
    *   `/api/promote` when `action startswith "promote_"`,
    *   optional `/api/manifest/rebuild` when a batch threshold is met (keep it to a separate agent if you prefer).
*   **Output**: 200 JSON to the UI, echoing persisted label + any promotion plan/outcome.

Minimal DB DDL (Postgres)
=========================

Add these tables/indexes (they align with your `video` table and idempotency conventions):

```sql
-- 1) Append-only audit of all label submissions
CREATE TABLE IF NOT EXISTS label_event (
  event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id        UUID NOT NULL REFERENCES video(video_id) ON DELETE CASCADE,
  label           TEXT NOT NULL CHECK (label IN ('happy','sad','angry','neutral','surprise','fearful')),
  action          TEXT NOT NULL CHECK (action IN ('label_only','promote_train','promote_test','discard')),
  rater_id        TEXT,
  notes           TEXT,
  idempotency_key TEXT NOT NULL,
  source          TEXT DEFAULT 'webapp',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (video_id, idempotency_key)
);

-- 2) Fast lookup to avoid double-processing within a short window
CREATE INDEX IF NOT EXISTS idx_label_event_video_time ON label_event(video_id, created_at DESC);

-- 3) Keep video table as source of truth for effective label
-- (you already have 'label' & 'split'; this just ensures it exists)
ALTER TABLE video ADD COLUMN IF NOT EXISTS label TEXT;
ALTER TABLE video ADD COLUMN IF NOT EXISTS split TEXT CHECK (split IN ('temp','train','test')) NOT NULL DEFAULT 'temp';
```

Why: your requirements say DB is the source of truth for labels/splits; manifests are derived, and promotions are atomic FS moves mirrored in metadata. This DDL keeps that tight. requirements\_08.3.3

Node-by-node build (n8n)
========================

> Workflow settings: set **Timezone** to `America/New_York` (consistent with your environment), and enable execution saving for audit. Expressions, Code, and node settings below follow current n8n docs for Webhook, HTTP, Code, Postgres, and Expressions. [n8n Docs+5n8n Docs+5n8n Docs+5](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/common-issues/?utm_source=chatgpt.com)

1.  **Webhook (trigger)**
    *   **Name:** `label.submitted`
*   **HTTP Method:** `POST`
*   **Path:** `label`
*   **Response:** “Using Respond to Webhook node” (so you return after processing).
*   **Options → Authentication:** your choice (n8n basic auth or header token), but you’ll also JWT-check inside Code.
*   **Docs:** Webhook URLs & response behavior are spelled out here. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)
    2.  **Code (validate + normalize)**
    *   **Name:** `validate.payload`
*   **Type:** Code node (JavaScript). Use it to:
    *   Verify required keys, allowed `label` set, allowed `action` set.
    *   Verify/generate `idempotency_key` (UUID v4 if missing).
    *   Optionally verify a `Bearer` JWT from `{{$json.headers.authorization}}` (use your public key).
    *   Emit a strict, minimal JSON forward.
*   **Docs:** Code node fundamentals. [n8n Docs](https://docs.n8n.io/code/code-node/?utm_source=chatgpt.com)

_Paste this (safe starter):_

```js
// Inputs: Webhook JSON body
const b = $json.body ?? $json;
const allowedLabels = new Set(['happy','sad','angry','neutral','surprise','fearful']);
const allowedActions = new Set(['label_only','promote_train','promote_test','discard']);

function uuidv4() {
  return (crypto.randomUUID && crypto.randomUUID()) ||
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = (Math.random() * 16)|0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
}

const video_id = b.video_id;
const label = (b.label || '').toLowerCase();
const action = b.action || 'label_only';
const rater_id = b.rater_id || 'anonymous';
const notes = b.notes || '';
const idempotency_key = b.idempotency_key || uuidv4();

// Basic checks
if (!video_id) throw new Error('video_id required');
if (!allowedLabels.has(label)) throw new Error(`label invalid: ${label}`);
if (!allowedActions.has(action)) throw new Error(`action invalid: ${action}`);

// Optionally: verify Authorization: Bearer <JWT> here if you want HMAC/RS256.
// Skipped here for brevity; you can add jose/jwt verification if your n8n image includes it.

return [{ json: { video_id, label, action, rater_id, notes, idempotency_key } }];
```

3.  **Postgres (SELECT guard)**
    *   **Name:** `db.fetch_video`
*   **Resource:** Postgres
*   **Operation:** `Query`
*   **Query:**
    ```sql
    SELECT v.video_id, v.split, v.label AS current_label
    FROM video v
    WHERE v.video_id = {{$json.video_id}}::uuid;
    ```
*   If zero rows, throw → handled by “Error Trigger” workflow (optional).

_Docs:_ Postgres node basics and creds. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/?utm_source=chatgpt.com)

4.  **Postgres (UPSERT label\_event + update video)**
    *   **Name:** `db.apply_label`
*   **Operation:** `Query`
*   **Query:**
    ```sql
    WITH ins AS (
      INSERT INTO label_event (video_id, label, action, rater_id, notes, idempotency_key)
      VALUES (
        {{$json.video_id}}::uuid,
        {{$json.label}},
        {{$json.action}},
        {{$json.rater_id}},
        {{$json.notes}},
        {{$json.idempotency_key}}
      )
      ON CONFLICT (video_id, idempotency_key) DO NOTHING
      RETURNING event_id
    )
    UPDATE video
       SET label = {{$json.label}},
           updated_at = NOW()
     WHERE video_id = {{$json.video_id}}::uuid
    RETURNING (SELECT event_id FROM ins) AS event_id, video_id, label;
    ```
*   **Continue On Fail:** `false` (we want atomic behavior).
    5.  **Switch (branch on action)**
    *   **Name:** `branch.action`
*   **Property to check:** `={{$json.action}}`
*   **Rules:**
    *   Case 1: Equals `label_only`
    *   Case 2: Equals `promote_train`
    *   Case 3: Equals `promote_test`
    *   Case 4: Equals `discard`
        6.  **HTTP Request — /api/relabel** (runs for label\_only, promote\_train, promote\_test)
    *   **Name:** `mm.relabel`
*   **Method:** `POST`
*   **URL:** `={{$env.MEDIA_MOVER_BASE_URL}}/api/relabel`
*   **Headers:**
    *   `Authorization: Bearer {{$env.MEDIA_MOVER_TOKEN}}`
    *   `Idempotency-Key: {{$json.idempotency_key}}`
    *   `Content-Type: application/json`
*   **Body (JSON):**
    ```json
    {
      "video_id": "={{$json.video_id}}",
      "label": "={{$json.label}}",
      "correlation_id": "={{$execution.id}}"
    }
    ```
*   **Docs:** HTTP node usage + examples, including headers and JSON bodies. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
    7.  **HTTP Request — /api/promote** (for promote\_train / promote\_test)
    *   **Name:** `mm.promote`
*   **Method:** `POST`
*   **URL:** `={{$env.MEDIA_MOVER_BASE_URL}}/api/promote`
*   **Headers:** same as above (include Idempotency-Key)
*   **Body (JSON):**
    ```json
    {
      "video_id": "={{$json.video_id}}",
      "dest_split": "={{$json.action === 'promote_train' ? 'train' : 'test'}}",
      "label": "={{$json.label}}",
      "correlation_id": "={{$execution.id}}",
      "dry_run": false
    }
    ```
*   **Retry On Fail:** enable a couple of retries (node → Options) with exponential backoff.
    8.  **HTTP Request — /api/promote (discard)** (optional)
    *   If you support deletes for discard, call a `DELETE /api/videos/{id}` or your existing cleanup—otherwise write a small `/api/discard` in Media-Mover. Skip if not implemented in this version.
    9.  **Code (compose response)**
    *   **Name:** `build.response`
*   Aggregate the DB result and any Media-Mover responses into a single JSON for the UI.
    10.  **Respond to Webhook**
    *   **Name:** `respond.ok`
*   **Response Body:** `First Entry JSON` (or your composed payload)
*   **Status Code:** `200`
*   **Docs:** Respond patterns in Webhook docs. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)

> Expressions & data-mapping tips: When you wire headers and bodies, use the n8n expressions editor (`={{...}}`) and built-ins like `$json`, `$env`, `$execution.id`. Examples here. [n8n Docs+1](https://docs.n8n.io/code/expressions/?utm_source=chatgpt.com)

Ready-to-import n8n workflow (JSON)
===================================

> Drop this into **n8n → Import**. Then: set your Postgres credentials on the two DB nodes, set environment variables (`MEDIA_MOVER_BASE_URL`, `MEDIA_MOVER_TOKEN`) in your n8n instance, and confirm the Webhook test/prod URL paths. Webhook/HTTP/Code/Postgres node schemas align with current docs. [n8n Docs+3n8n Docs+3n8n Docs+3](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)

```json
{
  "name": "Reachy 08.3.3 — Agent 2: Labeling",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "label",
        "responseMode": "responseNode",
        "options": {
          "responseData": "firstEntryJson"
        }
      },
      "id": "Webhook_Trigger",
      "name": "label.submitted",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [100, 300]
    },
    {
      "parameters": {
        "language": "JavaScript",
        "jsCode": "// see code block above"
      },
      "id": "Code_Validate",
      "name": "validate.payload",
      "type": "n8n-nodes-base.code",
      "typeVersion": 1,
      "position": [320, 300]
    },
    {
      "parameters": {
        "operation": "query",
        "query": "SELECT v.video_id, v.split, v.label AS current_label\nFROM video v\nWHERE v.video_id = {{$json.video_id}}::uuid;"
      },
      "id": "PG_SelectVideo",
      "name": "db.fetch_video",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 1,
      "position": [540, 220],
      "credentials": {
        "postgres": {
          "id": "__REPLACE__",
          "name": "Postgres (Reachy)"
        }
      }
    },
    {
      "parameters": {
        "operation": "query",
        "query": "WITH ins AS (\n  INSERT INTO label_event (video_id, label, action, rater_id, notes, idempotency_key)\n  VALUES (\n    {{$json.video_id}}::uuid,\n    {{$json.label}},\n    {{$json.action}},\n    {{$json.rater_id}},\n    {{$json.notes}},\n    {{$json.idempotency_key}}\n  )\n  ON CONFLICT (video_id, idempotency_key) DO NOTHING\n  RETURNING event_id\n)\nUPDATE video\n   SET label = {{$json.label}},\n       updated_at = NOW()\n WHERE video_id = {{$json.video_id}}::uuid\nRETURNING (SELECT event_id FROM ins) AS event_id, video_id, label;"
      },
      "id": "PG_ApplyLabel",
      "name": "db.apply_label",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 1,
      "position": [540, 380],
      "credentials": {
        "postgres": {
          "id": "__REPLACE__",
          "name": "Postgres (Reachy)"
        }
      }
    },
    {
      "parameters": {
        "property": "={{$json.action}}",
        "rules": {
          "rules": [
            { "operation": "equal", "value": "label_only" },
            { "operation": "equal", "value": "promote_train" },
            { "operation": "equal", "value": "promote_test" },
            { "operation": "equal", "value": "discard" }
          ]
        }
      },
      "id": "Switch_Action",
      "name": "branch.action",
      "type": "n8n-nodes-base.switch",
      "typeVersion": 1,
      "position": [760, 380]
    },
    {
      "parameters": {
        "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/relabel",
        "options": {
          "responseFormat": "json",
          "allowUnauthorizedCerts": false
        },
        "authentication": "none",
        "method": "POST",
        "jsonParameters": true,
        "sendHeaders": true,
        "headerParametersJson": "{\"Authorization\":\"Bearer {{$env.MEDIA_MOVER_TOKEN}}\",\"Idempotency-Key\":\"{{$json.idempotency_key}}\",\"Content-Type\":\"application/json\"}",
        "bodyParametersJson": "{\"video_id\":\"{{$json.video_id}}\",\"label\":\"{{$json.label}}\",\"correlation_id\":\"{{$execution.id}}\"}"
      },
      "id": "HTTP_Relabel",
      "name": "mm.relabel",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [980, 300]
    },
    {
      "parameters": {
        "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/promote",
        "options": {
          "responseFormat": "json",
          "retryOnFail": true,
          "maxRetries": 2,
          "allowUnauthorizedCerts": false
        },
        "authentication": "none",
        "method": "POST",
        "jsonParameters": true,
        "sendHeaders": true,
        "headerParametersJson": "{\"Authorization\":\"Bearer {{$env.MEDIA_MOVER_TOKEN}}\",\"Idempotency-Key\":\"{{$json.idempotency_key}}\",\"Content-Type\":\"application/json\"}",
        "bodyParametersJson": "{\"video_id\":\"{{$json.video_id}}\",\"dest_split\":\"{{ $json.action === 'promote_train' ? 'train' : 'test' }}\",\"label\":\"{{$json.label}}\",\"correlation_id\":\"{{$execution.id}}\",\"dry_run\":false}"
      },
      "id": "HTTP_Promote",
      "name": "mm.promote",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [980, 460]
    },
    {
      "parameters": {
        "language": "JavaScript",
        "jsCode": "const out = { ok: true, video_id: $json.video_id, label: $json.label, action: $json.action };\nreturn [{ json: out }];"
      },
      "id": "Code_Response",
      "name": "build.response",
      "type": "n8n-nodes-base.code",
      "typeVersion": 1,
      "position": [1200, 380]
    },
    {
      "parameters": {},
      "id": "Respond",
      "name": "respond.ok",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [1400, 380]
    }
  ],
  "connections": {
    "label.submitted": {
      "main": [ [ { "node": "validate.payload", "type": "main", "index": 0 } ] ]
    },
    "validate.payload": {
      "main": [ 
        [ { "node": "db.fetch_video", "type": "main", "index": 0 } ],
        [ { "node": "db.apply_label", "type": "main", "index": 0 } ]
      ]
    },
    "db.fetch_video": {
      "main": [ [ { "node": "db.apply_label", "type": "main", "index": 0 } ] ]
    },
    "db.apply_label": {
      "main": [ [ { "node": "branch.action", "type": "main", "index": 0 } ] ]
    },
    "branch.action": {
      "main": [
        [ { "node": "mm.relabel", "type": "main", "index": 0 } ],
        [ { "node": "mm.relabel", "type": "main", "index": 0 }, { "node": "mm.promote", "type": "main", "index": 0 } ],
        [ { "node": "mm.relabel", "type": "main", "index": 0 }, { "node": "mm.promote", "type": "main", "index": 0 } ],
        [ /* discard path: no HTTP calls, straight to response */ ]
      ]
    },
    "mm.relabel": {
      "main": [ [ { "node": "build.response", "type": "main", "index": 0 } ] ]
    },
    "mm.promote": {
      "main": [ [ { "node": "build.response", "type": "main", "index": 0 } ] ]
    },
    "build.response": {
      "main": [ [ { "node": "respond.ok", "type": "main", "index": 0 } ] ]
    }
  },
  "meta": {
    "instanceId": "__REPLACE__"
  },
  "active": false,
  "settings": {
    "timezone": "America/New_York"
  }
}
```

> If you’d rather break it up, you can split `mm.relabel` and `mm.promote` into sub-workflows and call them with **Execute Workflow** nodes. But the above is self-contained.

Credentials & env
=================

*   **Postgres credentials** (n8n → Credentials → Postgres): point at Ubuntu 1’s DB (least-privileged role for `video` & `label_event`).
*   **Env vars** (n8n host):
    *   `MEDIA_MOVER_BASE_URL=http://ubuntu1:8081`
    *   `MEDIA_MOVER_TOKEN=…` (short-lived JWT/Bearer you already planned) requirements\_08.3.3
*   **Webhook URL**: in the Webhook node you get **Test** and **Production** URLs and can choose response mode (we use Respond node). [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)

Optional hardening (quick wins)
===============================

*   **Postgres Trigger** workflow for _DB-first_ events (if labels were ever written straight to DB). It can fire on `INSERT` to `label_event`. [n8n Docs](https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.postgrestrigger/?utm_source=chatgpt.com)
*   **Expressions hygiene**: keep all secrets in creds/env; never interpolate raw tokens into the body text. Use the headers JSON with expressions as shown. [n8n Docs](https://docs.n8n.io/code/expressions/?utm_source=chatgpt.com)
*   **Retry policy** on the promote call (already set). n8n’s HTTP Request node supports configurable retries and response formats. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **Audit**: enable execution data save; couple it with your DLQ/alerts agent later (per AGENTS). AGENTS

How it lines up with your specs
===============================

*   Labels live in Postgres; manifests are derived; promotions are atomic and idempotent; all mutate endpoints require auth—exactly per your requirements. requirements\_08.3.3
*   The agent publishes/consumes contracts with `correlation_id`, idempotency, and human approval gates (promotion UI is the approval); the workflow keeps `Idempotency-Key` on every write. AGENTS

If you want, next pass we can add a tiny **“batch manifest”** sub-agent: it counts recent promotions and only calls `/api/manifest/rebuild` when `>= N` or every `T` minutes. Easy add with a **Code** + **HTTP Request** + **Cron Trigger**. [n8n Docs+1](https://docs.n8n.io/code/code-node/?utm_source=chatgpt.com)

Your move: import the JSON, wire creds/env, and we’ll iterate from real traffic.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)