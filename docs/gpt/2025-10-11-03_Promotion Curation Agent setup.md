# 03_Promotion Curation Agent setup

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/10/2025 21:12:22  
**Updated:** 10/21/2025 22:06:26  
**Exported:** 10/21/2025 22:09:02  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9aef5-9ca8-8326-8e7c-b65903a08d3f](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e9aef5-9ca8-8326-8e7c-b65903a08d3f)  

## Prompt:
consider the chat titled 'ALL Agent-by-Agent Purposes.'

Provide a detailed explanation of how to develop the first AI agent 3: Promotion / Curation Agent.
At this point, you should provide all the detail you can regarding how to construct the n8n nodes, sub-nodes, parameters, etc.

Be sure to refer to the newest n8n documentation.

Thought for 30s

## Response:
Got you. This is the Promotion / Curation Agent—the one that turns a user-labeled clip into a dataset change that’s traceable, reversible, and boring-reliable. Below is a concrete, n8n-native build you can import and run today, plus why each node is there and how to set every field.

If anything feels too prescriptive, treat it as a starter you can prune. The core promises are: schema-checked inputs, dry-run first, explicit human approval, atomic promote, manifest rebuild, and clean audit trails.

* * *

What this agent does (in plain terms)
=====================================

1.  Receives a “promote this clip” request (usually from the Labeling Agent or the web app).
2.  Validates inputs + idempotency and enriches with DB/file info.
3.  Runs a **dry-run** promotion against Media Mover (`dry_run=true`) to get a plan.
4.  **Pauses for human approval** (in Slack/email or via a signed webhook).
5.  Executes the real promotion (atomic move + DB update), then rebuilds manifests.
6.  Emits events/metrics and posts status back to the UI.

* * *

n8n workflow (importable JSON)
==============================

Drop this into **n8n → Workflows → Import**. It’s intentionally minimal but production-shaped: JWT-secured inbound webhook, Code node for validation, HTTP nodes for Media Mover, an approval path (two options), and robust retry/idempotency.

> Replace the `YOUR_*` placeholders (URLs, tokens, secrets) before running.

```json
{
  "name": "Agent 3 — Promotion / Curation (08.3.3)",
  "nodes": [
    {
      "id": "webhook_in",
      "name": "Webhook: request.promotion",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 3,
      "position": [ -600, 0 ],
      "parameters": {
        "path": "promotion/v1",
        "httpMethod": "POST",
        "responseMode": "lastNode",
        "authentication": "jwt",
        "options": {
          "responseCode": 202
        }
      },
      "credentials": {
        "jwtAuth": {
          "id": "YOUR_WEBHOOK_JWT_CREDENTIAL_ID",
          "name": "JWT for Promotion Webhook"
        }
      }
    },
    {
      "id": "set_defaults",
      "name": "Set: defaults & headers",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [ -380, 0 ],
      "parameters": {
        "keepOnlySet": false,
        "options": {},
        "values": {
          "boolean": [
            { "name": "dry_run", "value": true }
          ],
          "string": [
            { "name": "target", "value": "train" },
            { "name": "mediaMoverBase", "value": "http://ubuntu1:8081/api" }
          ]
        }
      }
    },
    {
      "id": "code_validate",
      "name": "Code: validate + idempotency",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [ -160, 0 ],
      "parameters": {
        "language": "JavaScript",
        "jsCode": "const item = $json;\n// Required fields from Labeling Agent / UI\nconst required = ['video_id','label'];\nfor (const k of required) {\n  if (!item[k]) throw new Error(`Missing required field: ${k}`);\n}\n// Validate target split\nconst allowedSplits = ['train','test'];\nconst target = item.target || $json.target || 'train';\nif (!allowedSplits.includes(target)) throw new Error('Invalid target split');\n\n// Build idempotency key (stable across retries)\nconst crypto = require('crypto');\nconst idem = item.idempotency_key || crypto.createHash('sha256')\n  .update(`${item.video_id}|${target}|${item.label}`)\n  .digest('hex').slice(0, 32);\n\nreturn [{\n  ...item,\n  target,\n  idempotency_key: idem,\n  correlation_id: item.correlation_id || $now.toISO(),\n}];"
      }
    },
    {
      "id": "http_dryrun",
      "name": "HTTP: MediaMover dry-run",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [ 60, 0 ],
      "parameters": {
        "url": "={{$json.mediaMoverBase}}/promote",
        "method": "POST",
        "responseFormat": "json",
        "jsonParameters": true,
        "options": {
          "timeout": 120000
        },
        "sendQuery": false,
        "sendBody": true,
        "bodyParametersJson": "={\n  \"video_id\": $json.video_id,\n  \"dest_split\": $json.target,\n  \"label\": $json.label,\n  \"dry_run\": true\n}"
      },
      "credentials": {
        "httpBasicAuth": {
          "id": "YOUR_MEDIA_MOVER_BASIC_AUTH_ID",
          "name": "MediaMover Basic"
        }
      }
    },
    {
      "id": "code_summarize_plan",
      "name": "Code: summarize plan",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [ 300, 0 ],
      "parameters": {
        "language": "JavaScript",
        "jsCode": "const plan = $json;\n// Expect fields like { moves: [...], checksums: {...}, will_update_db: true }\nreturn [{\n  approval: {\n    title: 'Promotion request',\n    summary: {\n      video_id: $prevNode.output[0].json.video_id,\n      label: $prevNode.output[0].json.label,\n      target: $prevNode.output[0].json.target,\n      plan_preview: plan\n    }\n  }\n}];"
      }
    },

    /* === Option A: Slack/email Approval (send + wait) === */
    {
      "id": "approval_send",
      "name": "Slack: Send & wait for approval",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2,
      "position": [ 540, -120 ],
      "parameters": {
        "operation": "messagePostEphemeral",
        "channelId": "YOUR_SLACK_CHANNEL_ID",
        "text": "Promotion request: {{$json.approval.summary.video_id}} → {{$json.approval.summary.target}} (label: {{$json.approval.summary.label}})\n\nApprove?",
        "options": {
          "sendAndWait": true,
          "timeout": 600
        }
      },
      "disabled": true,
      "credentials": {
        "slackApi": {
          "id": "YOUR_SLACK_CREDENTIAL_ID",
          "name": "Slack Bot"
        }
      }
    },

    /* === Option B: Signed Webhook Approval (UI button) === */
    {
      "id": "approval_wait",
      "name": "Webhook: approval decision",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 3,
      "position": [ 540, 120 ],
      "parameters": {
        "path": "promotion/approve/v1",
        "httpMethod": "POST",
        "responseMode": "onReceived",
        "authentication": "jwt"
      },
      "credentials": {
        "jwtAuth": {
          "id": "YOUR_APPROVAL_JWT_CREDENTIAL_ID",
          "name": "JWT for Approval Webhook"
        }
      }
    },
    {
      "id": "if_approved",
      "name": "IF approved?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [ 800, 120 ],
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{$json.approved === true}}"
            }
          ]
        }
      }
    },
    {
      "id": "http_promote",
      "name": "HTTP: MediaMover promote",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [ 1040, 40 ],
      "parameters": {
        "url": "={{$items(0,0).item.mediaMoverBase}}/promote",
        "method": "POST",
        "responseFormat": "json",
        "jsonParameters": true,
        "options": {
          "timeout": 120000,
          "retryOnFail": true,
          "maxRetries": 3
        },
        "sendBody": true,
        "bodyParametersJson": "={\n  \"video_id\": $items(0,0).item.video_id,\n  \"dest_split\": $items(0,0).item.target,\n  \"label\": $items(0,0).item.label,\n  \"dry_run\": false\n}",
        "headerParametersJson": "={\n  \"Idempotency-Key\": $items(0,0).item.idempotency_key,\n  \"X-Correlation-Id\": $items(0,0).item.correlation_id\n}"
      },
      "credentials": {
        "httpBasicAuth": {
          "id": "YOUR_MEDIA_MOVER_BASIC_AUTH_ID",
          "name": "MediaMover Basic"
        }
      }
    },
    {
      "id": "http_manifest",
      "name": "HTTP: manifest rebuild",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4,
      "position": [ 1240, 40 ],
      "parameters": {
        "url": "={{$items(0,0).item.mediaMoverBase}}/manifest/rebuild",
        "method": "POST",
        "responseFormat": "json",
        "options": {
          "timeout": 300000,
          "retryOnFail": true,
          "maxRetries": 2
        },
        "jsonParameters": true,
        "sendBody": true,
        "bodyParametersJson": "={\n  \"reason\": \"promotion\",\n  \"correlation_id\": $items(0,0).item.correlation_id\n}"
      },
      "credentials": {
        "httpBasicAuth": {
          "id": "YOUR_MEDIA_MOVER_BASIC_AUTH_ID",
          "name": "MediaMover Basic"
        }
      }
    },
    {
      "id": "set_success",
      "name": "Set: success payload",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [ 1440, 40 ],
      "parameters": {
        "keepOnlySet": true,
        "values": {
          "string": [
            { "name": "status", "value": "promoted" }
          ],
          "json": [
            { "name": "dataset_hash", "value": "={{$json.dataset_hash || $prevNode.output[0].json.dataset_hash}}" }
          ]
        }
      }
    },
    {
      "id": "respond",
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [ 1640, 40 ],
      "parameters": {
        "responseBody": "={{$json}}",
        "responseCode": 200
      }
    },
    {
      "id": "set_reject",
      "name": "Set: rejected payload",
      "type": "n8n-nodes-base.set",
      "typeVersion": 2,
      "position": [ 1040, 220 ],
      "parameters": {
        "keepOnlySet": true,
        "values": {
          "string": [
            { "name": "status", "value": "rejected" }
          ],
          "json": [
            { "name": "reason", "value": "={{$json.reason || 'human_rejection'}}" }
          ]
        }
      }
    }
  ],
  "connections": {
    "Webhook: request.promotion": {
      "main": [ [ { "node": "Set: defaults & headers", "type": "main", "index": 0 } ] ]
    },
    "Set: defaults & headers": {
      "main": [ [ { "node": "Code: validate + idempotency", "type": "main", "index": 0 } ] ]
    },
    "Code: validate + idempotency": {
      "main": [ [ { "node": "HTTP: MediaMover dry-run", "type": "main", "index": 0 } ] ]
    },
    "HTTP: MediaMover dry-run": {
      "main": [ [ { "node": "Code: summarize plan", "type": "main", "index": 0 } ] ]
    },
    "Code: summarize plan": {
      "main": [ [ { "node": "Webhook: approval decision", "type": "main", "index": 0 } ] ]
    },
    "Webhook: approval decision": {
      "main": [ [ { "node": "IF approved?", "type": "main", "index": 0 } ] ]
    },
    "IF approved?": {
      "main": [
        [ { "node": "HTTP: MediaMover promote", "type": "main", "index": 0 } ],
        [ { "node": "Set: rejected payload", "type": "main", "index": 0 } ]
      ]
    },
    "HTTP: MediaMover promote": {
      "main": [ [ { "node": "HTTP: manifest rebuild", "type": "main", "index": 0 } ] ]
    },
    "HTTP: manifest rebuild": {
      "main": [ [ { "node": "Set: success payload", "type": "main", "index": 0 } ] ]
    },
    "Set: success payload": {
      "main": [ [ { "node": "Respond to Webhook", "type": "main", "index": 0 } ] ]
    },
    "Set: rejected payload": {
      "main": [ [ { "node": "Respond to Webhook", "type": "main", "index": 0 } ] ]
    }
  },
  "settings": { "executionOrder": "v1" },
  "pinData": {}
}
```

### Why these exact nodes

*   **Webhook (JWT auth)** for secure intake; n8n’s Webhook node supports JWT/basic/header auth out of the box, so you don’t have to hand-roll checks. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)
*   **Code node** for strict schema checks, idempotency-key derivation, and correlation IDs. n8n’s Code node is the right place for small, auditable transforms like this. [n8n Docs+2n8n Docs+2](https://docs.n8n.io/code/code-node/?utm_source=chatgpt.com)
*   **HTTP Request node** to call Media Mover for both the dry-run and the real promote; it’s n8n’s general REST hammer and supports retries/timeouts. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **Approval**: two patterns:
    *   **Option A**: Slack “send & wait” (or Gmail “send & wait”), which is a native n8n pattern discussed widely; you can toggle this on if you want approvals inside a chat client. [n8n Community+1](https://community.n8n.io/t/slack-wait-send-and-wait-for-approval-options/67411?utm_source=chatgpt.com)
    *   **Option B**: **signed approval webhook** (default in the JSON) so your web app can render the dry-run plan and POST `{ approved: true/false, reason }` with a JWT. This keeps UX consistent with your app and avoids chat-bot plumbing. (Webhook auth options are documented.) [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)

> If you prefer a one-click “Approve Node,” there’s a community node (`n8n-nodes-approve`) that gives you an approval URL + wait. It’s optional; I kept the core workflow stock. [n8n Community](https://community.n8n.io/t/approvenode-support-get-approval-url-and-waiting-for-approval/185592?utm_source=chatgpt.com)

* * *

Parameters & credentials (fill these in)
========================================

*   **Webhook (request.promotion)**
    *   Auth: **JWT** credential with your verification public key / secret (same issuer/audience your UI uses). [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)
*   **HTTP → Media Mover**
    *   Base: `http://ubuntu1:8081/api` (or whatever you set)
    *   Auth: basic or JWT—match your API config.
    *   Headers: set `Idempotency-Key` and `X-Correlation-Id` as shown (the JSON uses expressions to pull them through).
*   **Webhook (approval)**
    *   Path: `/promotion/approve/v1`
    *   Auth: **JWT** so approvals can’t be spoofed. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)

* * *

Event contracts (what hits the first webhook)
=============================================

**POST** `/promotion/v1` (JWT)

```json
{
  "video_id": "abc123-uuid",
  "label": "happy",
  "target": "train",          // default train if omitted
  "idempotency_key": "opt-in",// optional; will be derived if missing
  "correlation_id": "opt-in"  // optional; will be added if missing
}
```

**What we return immediately:** `202 Accepted` (final result comes when the approval path finishes and the workflow responds via the “Respond to Webhook” node).

**Approval POST** `/promotion/approve/v1` (JWT)

```json
{
  "approved": true,
  "reason": "looks good",
  "correlation_id": "match-this-if-you-pass-it-through"
}
```

* * *

How the “dry-run → approve → promote” loop works
================================================

1.  **Dry-run**: `POST /api/promote { dry_run: true }` returns a plan (moves, checksums, DB updates). We bundle that into a human-readable “summary” for your UI to show.
2.  **Approval**: Your UI posts the signed decision to `/promotion/approve/v1`. If `approved: true`, we proceed; else we return `{status: rejected}` to the original caller.
3.  **Promote (atomic)**: `POST /api/promote { dry_run: false }` with idempotency headers—safe to retry.
4.  **Manifest rebuild**: `POST /api/manifest/rebuild` (longer timeout).
5.  **Respond**: final JSON to the original webhook caller (`promoted` + `dataset_hash`), suitable for the web app to refresh state.

* * *

Extra guardrails you’ll probably want
=====================================

*   **Retries**: HTTP nodes are already set to retry; tune `maxRetries`/timeouts as needed. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   **Transform correctness**: If you need deeper item massaging, the Code node and the “Transforming data” guide cover best practices. [n8n Docs+1](https://docs.n8n.io/data/transforming-data/?utm_source=chatgpt.com)
*   **Large lists**: Item Lists node was removed; use Set/Code/Aggregate patterns instead (you’re doing that here). [n8n](https://n8n.io/integrations/item-lists/?utm_source=chatgpt.com)
*   **API-driven orchestration**: If you later want a separate workflow to be triggered programmatically (e.g., from Training Orchestrator), n8n’s public API makes that easy. [n8n Docs](https://docs.n8n.io/api/api-reference/?utm_source=chatgpt.com)

* * *

Field-by-field notes (so you don’t have to hunt)
================================================

*   **Webhook → authentication: JWT**  
    Set **Issuer**, **Audience**, and the **public key/secret** in the credential so n8n enforces the token for you. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)
*   **Code: validate + idempotency**
    *   Throws on missing `video_id` or `label`.
    *   Normalizes `target` to `train|test`.
    *   Builds a stable `idempotency_key` from `(video_id|target|label)` if the caller didn’t provide one.
    *   Sets `correlation_id` once and threads it through the whole workflow.
*   **HTTP: MediaMover dry-run / promote / manifest**
    *   Uses `jsonParameters` so you author clean JSON bodies.
    *   Adds `Idempotency-Key` and `X-Correlation-Id` headers on the **real** promote call (not needed on dry-run, but harmless).
    *   Timeouts: 120s for promote, 300s for manifest.
*   **Approval path**
    *   Default JSON enables **Webhook approval** (works with your web UI).
    *   If you prefer Slack/email with “send & wait,” enable that node and wire its output into the IF. Community threads show the pattern and timeouts. [n8n Community+1](https://community.n8n.io/t/slack-wait-send-and-wait-for-approval-options/67411?utm_source=chatgpt.com)
    *   There’s also a community Approve node if you want a built-in approval URL. [n8n Community](https://community.n8n.io/t/approvenode-support-get-approval-url-and-waiting-for-approval/185592?utm_source=chatgpt.com)

* * *

Testing the flow (quick and dirty)
==================================

1.  Create a JWT matching the Webhook credential and POST to `/promotion/v1` with a known `video_id` from your DB.
2.  Confirm the dry-run fires and your UI receives/renders the plan (or check the “Code: summarize plan” node output in n8n’s execution view).
3.  POST approval to `/promotion/approve/v1` (JWT) with `{ approved: true }`.
4.  Watch the promote → manifest nodes execute; final response comes back to the original caller.
5.  Re-run the same request—the **idempotency key** should keep the promote idempotent (your API should return a no-op/200).

* * *

When you want to get fancier
============================

*   **Multi-clip batch approvals**: Use a parent workflow that fans out to this one per clip, then a Merge node to consolidate results for a single human approval “bundle.” (Stick the dry-run plans into a single summary.)
*   **Queueing**: If you see stampedes, put a small delay/“Wait” between manifest rebuilds, or separate them into another workflow that de-duplicates rebuild requests per minute.
*   **Observability**: Add a metrics POST (or Prometheus pushgateway) with `promotion_latency_ms`, `success=1/0`, and class/label tags.

* * *

Why this matches n8n’s current best-practices
=============================================

*   Use **Webhook** auth modes (JWT, Basic, Header) rather than custom validation. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/?utm_source=chatgpt.com)
*   Keep business logic small and local in a **Code** node (JS/Python are both supported). [n8n Docs](https://docs.n8n.io/code/code-node/?utm_source=chatgpt.com)
*   Prefer **HTTP Request** for generic REST, with explicit timeouts and retries. [n8n Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/?utm_source=chatgpt.com)
*   Model “wait for human” using a **Send & Wait** pattern or a **signed approval webhook**—both are common in production n8n setups. [n8n Community+1](https://community.n8n.io/t/slack-wait-send-and-wait-for-approval-options/67411?utm_source=chatgpt.com)

* * *

If you want, I can also hand you a second JSON that wires Slack “Send & Wait” as the default and formats the dry-run plan into a Block Kit message. Or we can bolt on a Postgres node to stamp an audit row for every decision. Your call.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)