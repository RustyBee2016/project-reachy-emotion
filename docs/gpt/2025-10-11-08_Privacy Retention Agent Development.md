# 08_Privacy Retention Agent Development

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 21:50:43  
**Updated:** 10/21/2025 21:59:46  
**Exported:** 10/21/2025 22:00:16  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b7f0-fa1c-8332-a96b-7aafd1e03dc9](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9b7f0-fa1c-8332-a96b-7aafd1e03dc9)  

## Prompt:
consider the chat titled 'ALL Agent-by-Agent Purposes.'

Provide a detailed explanation of how to develop the first AI agent 8: Privacy / Retention Agent.
At this point, you should provide all the detail you can regarding how to construct the n8n nodes, sub-nodes, parameters, etc.

Be sure to refer to the newest n8n documentation.

## Response:
Thought for 31s

You’re building Agent 8 (Privacy / Retention) to be the project’s broom and shredder: it enforces TTLs, handles DSAR “forget me” requests, and keeps derived artifacts aligned with deletion rules—without touching raw video unless policy says so. Below is a concrete, n8n-first design wired to your specs (TTL on `/videos/temp`, DSAR/right-to-be-forgotten, manifests as derived views, MLflow lineage via `dataset_hash`, NAS mirroring) requirements\_08.3.3 requirements\_08.3.3 requirements\_08.3.3.

I’m giving you:

1.  the workflow breakdown (three small workflows > one mega spaghetti),
2.  exact n8n nodes + parameters (with links to the current docs), and
3.  a ready-to-import n8n JSON for all three (drop-in; edit credentials/URLs).

* * *

0) Shared conventions (so the agent behaves)
============================================

*   **Auth to Media Mover** (Ubuntu 1): short-lived JWT, Bearer header (aligns with your mutate-endpoint policy). Endpoints used: `/api/relabel`, `/api/manifest/rebuild`, and a small **/api/videos/delete** endpoint you’ll add (tiny FastAPI handler) to formalize temp purges with rationale. Mutations require JWT per your spec. requirements\_08.3.3
*   **DB is source of truth** for labels/split; manifests are derived → always rebuild manifests after deletes or relabels. requirements\_08.3.3
*   **TTL target**: `temp/` 7–14 days (we’ll parameterize). requirements\_08.3.3
*   **Lineage**: anything that changes the dataset should propagate a fresh `dataset_hash` (manifest rebuild returns it) and record into `run_link` if it’s a training run. requirements\_08.3.3
*   **No raw video egress**. Privacy defaults “local-only”; DSAR removes raw and thumbnails; derived metrics remain only if fully anonymized. AGENTS requirements\_08.3.3

* * *

1) Workflow A — Temp TTL Sweeper (daily purge)
==============================================

**Goal:** Delete expired clips in `/videos/temp`, remove their DB rows, regenerate manifests.

**Trigger & core nodes (n8n):**

*   **Schedule Trigger**: run daily 02:15 (America/New\_York). Docs (new Schedule node) [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/?utm_source=chatgpt.com)
    *   _Parameters_: Mode = “Every day”; Timezone = project tz; Time = `02:15`.
*   **Postgres**: select expired candidates. Docs [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/?utm_source=chatgpt.com)
    *   _Query example_:
        ```sql
        SELECT video_id, file_path, sha256
        FROM video
        WHERE split='temp'
          AND created_at < (NOW() AT TIME ZONE 'UTC' - INTERVAL '{{ $json.ttl_days || 10 }} days');
        ```
    *   _Credentials_: your n8n Postgres cred; set `Use SSL` if enabled.
*   **If**: branch on “any rows?” Docs [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/?utm_source=chatgpt.com)
    *   Condition: `{{$json["total"] || $items().length}} > 0`
*   **Edit Fields (Set)**: shape payload to Media Mover “bulk delete” call. Docs [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.set/?utm_source=chatgpt.com)
    *   Keep Only Set Fields = true
    *   Fields → `clips: {{$items().map(i => i.json.video_id)}}`, `reason: "ttl_expired"`
*   **HTTP Request** (Media Mover `DELETE /api/videos/bulk-delete` or POST `/api/videos/delete` per-item loop if you don’t add bulk): Docs [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
    *   Method: `POST`
    *   URL: `http://ubuntu1:8081/api/videos/delete`
    *   Auth: Bearer; Header `Authorization: Bearer {{$json.jwt}}`
    *   Body: JSON `{ "video_ids": {{$json.clips}}, "rationale": {{$json.reason}} }`
*   **HTTP Request**: `POST /api/manifest/rebuild` (returns `dataset_hash`). Docs [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
    *   Save response to `manifest` → we’ll use `manifest.dataset_hash`.
*   **Postgres**: cleanup rows (defense in depth; the API should already sync DB): [n8n Docs](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/?utm_source=chatgpt.com)
    ```sql
    DELETE FROM video WHERE video_id = ANY({{$json.clips}});
    ```
*   **Merge (pass-through)** to join success + “no-ops” branches for uniform logging. Docs [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.merge/?utm_source=chatgpt.com)

**Why this shape:** You enforce the retention policy you wrote (temp TTL 7–14 days), and keep manifests consistent; Media Mover remains the single place that touches the filesystem atomically, which matches your design (“atomic move/delete, manifests derived”). requirements\_08.3.3 requirements\_08.3.3

* * *

2) Workflow B — DSAR “Right to be Forgotten”
============================================

**Goal:** On a new DSAR record, remove a subject’s raw clips (train/test/temp), thumbnails, and any _non-essential_ linked artifacts; rebuild manifests; log an audit row.

**Trigger & core nodes:**

*   **Postgres Trigger** (listen for new row in `dsar_request` with `status='pending'`). Docs [n8n Docs](https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.postgrestrigger/?utm_source=chatgpt.com)
    *   _Filter_: table `dsar_request`; operation `INSERT`.
*   **Postgres**: resolve scope → fetch all `video_id` owned by `subject_id` (or hashed email). [n8n Docs](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/?utm_source=chatgpt.com)
    ```sql
    SELECT video_id, file_path
    FROM video
    WHERE subject_id = $1;
    ```
*   **If**: none found → Postgres update `dsar_request.status='no_data'` and exit. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/?utm_source=chatgpt.com)
*   **HTTP Request**: call Media Mover `POST /api/videos/delete` with list + `rationale: "dsar_erasure"`. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **HTTP Request**: `POST /api/manifest/rebuild` → returns `dataset_hash`. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **Postgres**: update `dsar_request` with `status='completed'`, `completed_at=now()`, `count_deleted`, `dataset_hash`. [n8n Docs](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/?utm_source=chatgpt.com)
*   **(Optional) SSH** to NAS to prune mirrored paths (if the Media Mover job doesn’t already handle NAS). Docs [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ssh/?utm_source=chatgpt.com)
    *   Command: `rsync --delete --include-from=@/tmp/paths.txt ...` or `find ... -delete`.
*   **Edit Fields (Set)**: assemble a minimal audit item: `{subject_id, count, dataset_hash, correlation_id, performed_by: "agent_privacy"}`. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.set/?utm_source=chatgpt.com)
*   **Postgres**: insert audit row `privacy_audit`.

This follows your Governance (§8.3: DSAR process) and local-first policy. requirements\_08.3.3

* * *

3) Workflow C — “Low-Disk” Retention Gate (pressure-based purge)
================================================================

**Goal:** If the video volume drops below a free-space watermark, purge _oldest, least-useful_ temp clips first; then (if still low) un-labeled or low-confidence items; finally stop ingestion (emit a circuit-breaker event).

**Trigger & nodes:**

*   **Schedule Trigger** every hour. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/?utm_source=chatgpt.com)
*   **HTTP Request** to Media Mover `/metrics` (Prometheus-style) or a tiny `/api/storage/df` endpoint; parse free% (you already expose metrics counters). [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **If** free% < threshold (e.g., 15%) → branch. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/?utm_source=chatgpt.com)
*   **Postgres**: select purge batch (ordered by `created_at`, then label null, then confidence asc).
    ```sql
    SELECT video_id FROM video
    WHERE split='temp'
    ORDER BY created_at ASC, (label IS NOT NULL) DESC, confidence DESC
    LIMIT 200;
    ```
*   **HTTP Request**: bulk delete; **HTTP Request**: manifest rebuild. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **If** still below threshold → **HTTP Request** to Ubuntu 2 gateway to set a “write throttle” flag (your circuit-breaker) until back above watermark.

This matches your ops guardrails (protect upstreams, circuit breakers). AGENTS

* * *

Node details (n8n parameters you’ll actually click)
===================================================

*   **HTTP Request**
    *   Authentication: _Generic Credential_ → Header `Authorization` with `Bearer {{$json.jwt}}` or use n8n’s **HTTP Header Auth**.
    *   Response: JSON → set “Always Output Data” = true (keep responses for logs). Docs: HTTP Request node, plus its “tool” variant note. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **Schedule Trigger**
    *   Timezone: set to America/New\_York in the node (it obeys workflow/global TZ). Docs & common issues. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/?utm_source=chatgpt.com)
*   **Postgres**
    *   Operation = “Execute Query”, “Continue On Fail” = false; set `Use UTC` in queries (n8n PG gotchas). Docs & common issues. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/?utm_source=chatgpt.com)
*   **Edit Fields (Set)**
    *   “Keep Only Set” for clean bodies; “Include in Output: All Inputs” when you need earlier fields downstream. Docs. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.set/?utm_source=chatgpt.com)
*   **If / Merge**
    *   Use `If` for branches; `Merge` (pass-through) to re-join for single logging tail. Docs. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/?utm_source=chatgpt.com)
*   **Execute Command / SSH (optional)**
    *   Prefer **SSH** for remote NAS ops (built-in); **Execute Command** runs inside n8n container (only if you extended the image). Docs & caveats. [n8n Docs+2n8n Docs+2](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ssh/?utm_source=chatgpt.com)
*   **Code node**
    *   Use sparingly (map lists, small transforms). Remember it’s CommonJS (`require`), not `import`. Docs. [n8n Docs+1](https://docs.n8n.io/code/code-node/?utm_source=chatgpt.com)

* * *

Importable n8n workflow (A+B+C together)
========================================

Paste into **n8n → Import from JSON**, then update:

*   Postgres credentials name: `PG_RechyLocal`
*   Media Mover base URL: `http://ubuntu1:8081`
*   JWT secret or token source (I made a small “Get JWT” node stub you can swap for your real one)

```json
{
  "name": "Agent 8 - Privacy & Retention (TTL, DSAR, LowDisk)",
  "nodes": [
    {
      "id": "sched-ttl",
      "name": "Schedule (Daily TTL)",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [200, 200],
      "parameters": {
        "rule": "custom",
        "timezone": "America/New_York",
        "custom": { "cronExpression": "15 2 * * *" }
      }
    },
    {
      "id": "pg-ttl-select",
      "name": "PG Select Expired",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2,
      "position": [420, 200],
      "credentials": { "postgres": { "id": "__REPLACE__", "name": "PG_ReachyLocal" } },
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT video_id, file_path, sha256 FROM video WHERE split='temp' AND created_at < (NOW() AT TIME ZONE 'UTC' - INTERVAL '10 days');"
      }
    },
    {
      "id": "if-any",
      "name": "If Any?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [640, 200],
      "parameters": {
        "conditions": {
          "number": [
            {
              "value1": "={{$items().length}}",
              "operation": "larger",
              "value2": 0
            }
          ]
        }
      }
    },
    {
      "id": "set-delete-body",
      "name": "Build Delete Body",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [860, 140],
      "parameters": {
        "keepOnlySet": true,
        "values": {
          "string": [
            { "name": "rationale", "value": "ttl_expired" }
          ],
          "json": [
            { "name": "video_ids", "value": "={{$items().map(i => i.json.video_id)}}" }
          ]
        }
      }
    },
    {
      "id": "get-jwt",
      "name": "Get JWT (stub)",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [860, 220],
      "parameters": {
        "language": "JavaScript",
        "jsCode": "return [{ json: { jwt: $json.jwt || $env.MM_JWT } }];"
      }
    },
    {
      "id": "mm-delete",
      "name": "MediaMover Delete",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1080, 180],
      "parameters": {
        "method": "POST",
        "url": "http://ubuntu1:8081/api/videos/delete",
        "authentication": "predefinedCredentialType",
        "sendHeaders": true,
        "headerParametersUi": {
          "parameter": [
            { "name": "Authorization", "value": "={{`Bearer ${$json.jwt}`}}" }
          ]
        },
        "jsonParameters": true,
        "options": { "response": { "responseFormat": "json" } },
        "bodyParametersJson": "={{$json}}"
      }
    },
    {
      "id": "mm-rebuild",
      "name": "Manifest Rebuild",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1300, 180],
      "parameters": {
        "method": "POST",
        "url": "http://ubuntu1:8081/api/manifest/rebuild",
        "authentication": "none",
        "jsonParameters": true,
        "options": { "response": { "responseFormat": "json" } }
      }
    },
    {
      "id": "pg-ttl-clean",
      "name": "PG Delete Rows",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2,
      "position": [1520, 180],
      "credentials": { "postgres": { "id": "__REPLACE__", "name": "PG_ReachyLocal" } },
      "parameters": {
        "operation": "executeQuery",
        "query": "DELETE FROM video WHERE video_id = ANY({{$json.video_ids}}::uuid[]);"
      }
    },
    {
      "id": "sched-disk",
      "name": "Schedule (Hourly Disk)",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [200, 520],
      "parameters": {
        "rule": "everyX",
        "unit": "hours",
        "value": 1,
        "timezone": "America/New_York"
      }
    },
    {
      "id": "mm-metrics",
      "name": "MediaMover Metrics",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [420, 520],
      "parameters": {
        "method": "GET",
        "url": "http://ubuntu1:8081/api/storage/df",
        "authentication": "none",
        "options": { "response": { "responseFormat": "json" } }
      }
    },
    {
      "id": "if-low",
      "name": "Low Disk?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [640, 520],
      "parameters": {
        "conditions": {
          "number": [
            { "value1": "={{$json.free_pct}}", "operation": "smaller", "value2": 15 }
          ]
        }
      }
    },
    {
      "id": "pg-purge-batch",
      "name": "PG Pick Purge Batch",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2,
      "position": [860, 480],
      "credentials": { "postgres": { "id": "__REPLACE__", "name": "PG_ReachyLocal" } },
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT video_id FROM video WHERE split='temp' ORDER BY created_at ASC, (label IS NULL) DESC, COALESCE(confidence,0) ASC LIMIT 200;"
      }
    },
    {
      "id": "set-purge-body",
      "name": "Build Purge Body",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [1080, 480],
      "parameters": {
        "keepOnlySet": true,
        "values": {
          "string": [{ "name": "rationale", "value": "low_disk_watermark" }],
          "json": [{ "name": "video_ids", "value": "={{$items().map(i => i.json.video_id)}}" }]
        }
      }
    },
    {
      "id": "mm-purge",
      "name": "MediaMover Purge",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1300, 480],
      "parameters": {
        "method": "POST",
        "url": "http://ubuntu1:8081/api/videos/delete",
        "authentication": "none",
        "jsonParameters": true,
        "bodyParametersJson": "={{$json}}",
        "options": { "response": { "responseFormat": "json" } }
      }
    },
    {
      "id": "mm-rebuild-2",
      "name": "Manifest Rebuild (Disk)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1520, 480],
      "parameters": {
        "method": "POST",
        "url": "http://ubuntu1:8081/api/manifest/rebuild",
        "authentication": "none",
        "jsonParameters": true,
        "options": { "response": { "responseFormat": "json" } }
      }
    },
    {
      "id": "pg-dsar-trigger",
      "name": "PG Trigger (DSAR)",
      "type": "n8n-nodes-base.postgresTrigger",
      "typeVersion": 1,
      "position": [200, 820],
      "credentials": { "postgres": { "id": "__REPLACE__", "name": "PG_ReachyLocal" } },
      "parameters": {
        "event": "insert",
        "schema": "public",
        "table": "dsar_request"
      }
    },
    {
      "id": "pg-dsar-select",
      "name": "PG Select Subject Clips",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2,
      "position": [420, 820],
      "credentials": { "postgres": { "id": "__REPLACE__", "name": "PG_ReachyLocal" } },
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT video_id, file_path FROM video WHERE subject_id={{$json.subject_id}};"
      }
    },
    {
      "id": "if-has-clips",
      "name": "Has Clips?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [640, 820],
      "parameters": {
        "conditions": {
          "number": [
            { "value1": "={{$items().length}}", "operation": "larger", "value2": 0 }
          ]
        }
      }
    },
    {
      "id": "set-dsar-body",
      "name": "Build DSAR Body",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [860, 760],
      "parameters": {
        "keepOnlySet": true,
        "values": {
          "string": [{ "name": "rationale", "value": "dsar_erasure" }],
          "json": [{ "name": "video_ids", "value": "={{$items().map(i => i.json.video_id)}}" }]
        }
      }
    },
    {
      "id": "mm-dsar-delete",
      "name": "MediaMover Delete (DSAR)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1080, 780],
      "parameters": {
        "method": "POST",
        "url": "http://ubuntu1:8081/api/videos/delete",
        "authentication": "none",
        "jsonParameters": true,
        "bodyParametersJson": "={{$json}}",
        "options": { "response": { "responseFormat": "json" } }
      }
    },
    {
      "id": "mm-dsar-rebuild",
      "name": "Manifest Rebuild (DSAR)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [1300, 780],
      "parameters": {
        "method": "POST",
        "url": "http://ubuntu1:8081/api/manifest/rebuild",
        "authentication": "none",
        "jsonParameters": true,
        "options": { "response": { "responseFormat": "json" } }
      }
    },
    {
      "id": "pg-dsar-update",
      "name": "PG DSAR Complete",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2,
      "position": [1520, 780],
      "credentials": { "postgres": { "id": "__REPLACE__", "name": "PG_ReachyLocal" } },
      "parameters": {
        "operation": "executeQuery",
        "query": "UPDATE dsar_request SET status='completed', completed_at=NOW(), count_deleted={{$json.video_ids.length}}, dataset_hash={{$json.dataset_hash || 'null'}} WHERE id={{$json.request_id}};"
      }
    }
  ],
  "connections": {
    "Schedule (Daily TTL)": { "main": [ [ { "node": "PG Select Expired", "type": "main", "index": 0 } ] ] },
    "PG Select Expired": { "main": [ [ { "node": "If Any?", "type": "main", "index": 0 } ] ] },
    "If Any?": {
      "main": [
        [ { "node": "Build Delete Body", "type": "main", "index": 0 } ],
        [ { "node": "Manifest Rebuild", "type": "main", "index": 0 } ]
      ]
    },
    "Build Delete Body": { "main": [ [ { "node": "Get JWT (stub)", "type": "main", "index": 0 } ] ] },
    "Get JWT (stub)": { "main": [ [ { "node": "MediaMover Delete", "type": "main", "index": 0 } ] ] },
    "MediaMover Delete": { "main": [ [ { "node": "Manifest Rebuild", "type": "main", "index": 0 } ] ] },
    "Manifest Rebuild": { "main": [ [ { "node": "PG Delete Rows", "type": "main", "index": 0 } ] ] },
    "Schedule (Hourly Disk)": { "main": [ [ { "node": "MediaMover Metrics", "type": "main", "index": 0 } ] ] },
    "MediaMover Metrics": { "main": [ [ { "node": "Low Disk?", "type": "main", "index": 0 } ] ] },
    "Low Disk?": { "main": [ [ { "node": "PG Pick Purge Batch", "type": "main", "index": 0 } ] ] },
    "PG Pick Purge Batch": { "main": [ [ { "node": "Build Purge Body", "type": "main", "index": 0 } ] ] },
    "Build Purge Body": { "main": [ [ { "node": "MediaMover Purge", "type": "main", "index": 0 } ] ] },
    "MediaMover Purge": { "main": [ [ { "node": "Manifest Rebuild (Disk)", "type": "main", "index": 0 } ] ] },
    "PG Trigger (DSAR)": { "main": [ [ { "node": "PG Select Subject Clips", "type": "main", "index": 0 } ] ] },
    "PG Select Subject Clips": { "main": [ [ { "node": "Has Clips?", "type": "main", "index": 0 } ] ] },
    "Has Clips?": {
      "main": [
        [ { "node": "Build DSAR Body", "type": "main", "index": 0 } ],
        [ { "node": "PG DSAR Complete", "type": "main", "index": 0 } ]
      ]
    },
    "Build DSAR Body": { "main": [ [ { "node": "MediaMover Delete (DSAR)", "type": "main", "index": 0 } ] ] },
    "MediaMover Delete (DSAR)": { "main": [ [ { "node": "Manifest Rebuild (DSAR)", "type": "main", "index": 0 } ] ] },
    "Manifest Rebuild (DSAR)": { "main": [ [ { "node": "PG DSAR Complete", "type": "main", "index": 0 } ] ] }
  },
  "meta": { "version": "1.1.0", "agent": "Agent8-PrivacyRetention" },
  "pinData": {}
}
```

> If you’d rather _not_ add `bulk-delete`, you can replace that node with a **Split in Batches → HTTP Request (per video)** chain. All the other wiring stays the same. Docs for node types overview here. [n8n Docs](https://docs.n8n.io/integrations/builtin/node-types/?utm_source=chatgpt.com)

* * *

Practical tweaks (less yak-shaving later)
=========================================

*   **Add `/api/videos/delete` to Media Mover** (FastAPI): accept `{video_ids:[], rationale}`; do file removal + DB delete + thumb cleanup; emit Prometheus counters; _then_ trigger manifest rebuild. That keeps n8n simpler and makes retention idempotent. Your API contract already allows mutate endpoints with JWT; this formalizes the “discard” path referenced in requirements. requirements\_08.3.3
*   **Timezone & UTC**: store timestamps UTC in Postgres; set n8n timezone and/or use `AT TIME ZONE 'UTC'` to avoid DST surprises. n8n PG node tips here. [n8n Docs](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/common-issues/?utm_source=chatgpt.com)
*   **Execution order (If + Merge)**: since n8n v1 changed some legacy behaviors, stick to simple branches and explicit joins. If you _do_ use Merge to re-join, know how it triggers downstream. [n8n Docs+1](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/?utm_source=chatgpt.com)
*   **Security**: never pass secrets in node params that get logged; store the Media Mover JWT in n8n credentials or env. Your spec already mandates short-lived JWTs and header-only secrets. requirements\_08.3.3

* * *

Why this agent design matches your specs
========================================

*   **Retention policy**: TTL on `temp` enforced daily; disk-pressure purge is a backstop; both rebuild manifests to keep training inputs deterministic. requirements\_08.3.3
*   **DSAR**: process exists, auditable, and local-only; removes raw/derived (thumbs), keeps only non-PII metrics if allowed. requirements\_08.3.3
*   **Lineage**: every purge re-materializes manifests and produces a fresh `dataset_hash`, preserving reproducibility gates for TAO/DeepStream loops. requirements\_08.3.3
*   **Agent contracts**: actions are limited (policy-as-code vibe), idempotent, and observable—aligned with your agent catalog expectations. AGENTS

* * *

If you want, I can also generate the tiny FastAPI `DELETE /api/videos/delete` handler (atomic FS remove + DB delete + thumb cleanup + log) to drop straight into Media Mover. It’ll mirror your existing auth and logging so the n8n side stays clean.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)