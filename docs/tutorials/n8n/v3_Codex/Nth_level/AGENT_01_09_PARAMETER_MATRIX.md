# Agent 1-9 Parameter Matrix (Exact Node Instance Values)

Source of truth: workflow JSON files at `n8n/workflows/ml-agentic-ai_v.3` from branch `codex/n8n_tutorials_v3`.

This matrix uses official n8n node names and includes exact per-node parameter objects for the current project workflows.

## Agent 1 — Ingest

Workflow file: `n8n/workflows/ml-agentic-ai_v.3/01_ingest_agent.json`

| Node instance | Official n8n node | Credential(s) |
|---|---|---|
| 1. `Webhook: ingest.video` | Webhook | `none` |
| 2. `IF: auth.check` | If | `none` |
| 3. `Code: normalize.payload` | Code | `none` |
| 4. `HTTP: media.pull` | HTTP Request | `httpHeaderAuth` |
| 5. `IF: status.done?` | If | `none` |
| 6. `HTTP: emit.completed` | HTTP Request | `none` |
| 7. `Respond: success` | Respond to Webhook | `none` |
| 8. `Respond: 401 Unauthorized` | Respond to Webhook | `none` |

### Exact Parameter Objects by Node Instance

#### 1) `Webhook: ingest.video` (Webhook)

`parameters`
```json
{
  "httpMethod": "POST",
  "path": "video_gen_hook",
  "responseMode": "onReceived",
  "options": {
    "responseCode": 202
  }
}
```

#### 2) `IF: auth.check` (If)

`parameters`
```json
{
  "conditions": {
    "string": [
      {
        "value1": "={{$json.headers['x-ingest-key']}}",
        "operation": "equals",
        "value2": "={{$env.INGEST_TOKEN}}"
      }
    ]
  }
}
```

#### 3) `Code: normalize.payload` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Normalize incoming payload from various sources\nconst body = $json.body ?? $json;\nconst sourceUrl = body.source_url ?? body.url ?? body.asset?.url ?? body.data?.asset?.url;\n\nif (!sourceUrl) {\n  throw new Error('Missing source_url in request body');\n}\n\nconst label = body.label ?? body.emotion ?? null;\nconst meta = body.meta ?? { \n  generator: body.generator ?? body.source ?? 'unknown' \n};\nconst correlationId = $json.headers?.['x-correlation-id'] ?? `ingest-${Date.now()}`;\nconst idempotencyKey = $json.headers?.['idempotency-key'] ?? `idem-${Date.now()}`;\n\nreturn [\n  {\n    json: {\n      source_url: sourceUrl,\n      label,\n      meta,\n      correlation_id: correlationId,\n      idempotency_key: idempotencyKey,\n      timestamp: new Date().toISOString()\n    }\n  }\n];"
}
```

#### 4) `HTTP: media.pull` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/ingest/pull",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {
        "name": "Idempotency-Key",
        "value": "={{$json.idempotency_key}}"
      },
      {
        "name": "X-Correlation-ID",
        "value": "={{$json.correlation_id}}"
      }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "source_url",
        "value": "={{$json.source_url}}"
      },
      {
        "name": "correlation_id",
        "value": "={{$json.correlation_id}}"
      },
      {
        "name": "intended_emotion",
        "value": "={{$json.label}}"
      },
      {
        "name": "generator",
        "value": "={{$json.meta?.generator || 'unknown'}}"
      },
      {
        "name": "prompt",
        "value": "={{$json.meta?.prompt || ''}}"
      }
    ]
  },
  "options": {
    "timeout": 120000
  },
  "method": "POST"
}
```
`credentials`
```json
{
  "httpHeaderAuth": {
    "id": "1",
    "name": "Media Mover Auth"
  }
}
```

#### 5) `IF: status.done?` (If)

`parameters`
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{ ['done','duplicate'].includes($json.status) }}",
        "value2": true
      }
    ]
  }
}
```

#### 6) `HTTP: emit.completed` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/ingest",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "={{$json.status === 'duplicate' ? 'ingest.duplicate' : 'ingest.completed'}}"
      },
      {
        "name": "video_id",
        "value": "={{$json.video_id}}"
      },
      {
        "name": "correlation_id",
        "value": "={{$json.correlation_id}}"
      },
      {
        "name": "file_path",
        "value": "={{$json.file_path}}"
      },
      {
        "name": "sha256",
        "value": "={{$json.sha256}}"
      },
      {
        "name": "duplicate",
        "value": "={{$json.duplicate || false}}"
      }
    ]
  },
  "method": "POST"
}
```

#### 7) `Respond: success` (Respond to Webhook)

`parameters`
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\"status\": $json.status || 'unknown', \"video_id\": $json.video_id || null, \"correlation_id\": $json.correlation_id || null, \"duplicate\": $json.duplicate || false} }}"
}
```

#### 8) `Respond: 401 Unauthorized` (Respond to Webhook)

`parameters`
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\"error\": \"unauthorized\", \"message\": \"Invalid or missing X-INGEST-KEY header\"} }}",
  "options": {
    "responseCode": 401
  }
}
```

## Agent 2 — Labeling

Workflow file: `n8n/workflows/ml-agentic-ai_v.3/02_labeling_agent.json`

| Node instance | Official n8n node | Credential(s) |
|---|---|---|
| 1. `Webhook: label.submitted` | Webhook | `none` |
| 2. `Code: validate.payload` | Code | `none` |
| 3. `Postgres: fetch.video` | Postgres | `postgres` |
| 4. `Postgres: apply.label` | Postgres | `postgres` |
| 5. `Switch: branch.action` | Switch | `none` |
| 6. `HTTP: mm.relabel` | HTTP Request | `httpHeaderAuth` |
| 7. `HTTP: mm.promote` | HTTP Request | `httpHeaderAuth` |
| 8. `Postgres: class.balance` | Postgres | `postgres` |
| 9. `Respond: success` | Respond to Webhook | `none` |

### Exact Parameter Objects by Node Instance

#### 1) `Webhook: label.submitted` (Webhook)

`parameters`
```json
{
  "httpMethod": "POST",
  "path": "label",
  "responseMode": "responseNode",
  "options": {}
}
```

#### 2) `Code: validate.payload` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Validate and normalize label submission\nconst body = $json.body ?? $json;\nconst allowedLabels = new Set(['happy', 'sad', 'neutral']);\nconst allowedActions = new Set(['label_only', 'promote_train', 'promote_test', 'discard']);\n\nfunction uuidv4() {\n  return crypto.randomUUID ? crypto.randomUUID() : \n    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {\n      const r = (Math.random() * 16) | 0;\n      const v = c === 'x' ? r : (r & 0x3 | 0x8);\n      return v.toString(16);\n    });\n}\n\nconst video_id = body.video_id;\nconst label = (body.label || '').toLowerCase();\nconst action = body.action || 'label_only';\nconst rater_id = body.rater_id || 'anonymous';\nconst notes = body.notes || '';\nconst idempotency_key = body.idempotency_key || uuidv4();\n\nif (!video_id) throw new Error('video_id required');\nif (!allowedLabels.has(label)) throw new Error(`Invalid label: ${label}`);\nif (!allowedActions.has(action)) throw new Error(`Invalid action: ${action}`);\n\nreturn [{\n  json: {\n    video_id,\n    label,\n    action,\n    rater_id,\n    notes,\n    idempotency_key,\n    correlation_id: body.correlation_id || `label-${Date.now()}`\n  }\n}];"
}
```

#### 3) `Postgres: fetch.video` (Postgres)

`parameters`
```json
{
  "operation": "executeQuery",
  "query": "SELECT v.video_id, v.split, v.label AS current_label, v.file_path\nFROM video v\nWHERE v.video_id = '{{$json.video_id}}'::uuid;",
  "options": {}
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```

#### 4) `Postgres: apply.label` (Postgres)

`parameters`
```json
{
  "operation": "executeQuery",
  "query": "WITH ins AS (\n  INSERT INTO label_event (video_id, label, action, rater_id, notes, idempotency_key)\n  VALUES (\n    '{{$json.video_id}}'::uuid,\n    '{{$json.label}}',\n    '{{$json.action}}',\n    '{{$json.rater_id}}',\n    '{{$json.notes}}',\n    '{{$json.idempotency_key}}'\n  )\n  ON CONFLICT (video_id, idempotency_key) DO NOTHING\n  RETURNING event_id\n)\nUPDATE video\nSET label = '{{$json.label}}',\n    updated_at = NOW()\nWHERE video_id = '{{$json.video_id}}'::uuid\nRETURNING \n  video_id, \n  label, \n  split,\n  (SELECT event_id FROM ins) AS event_id;",
  "options": {}
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```

#### 5) `Switch: branch.action` (Switch)

`parameters`
```json
{
  "rules": {
    "values": [
      {
        "conditions": {
          "string": [
            {
              "value1": "={{$json.action}}",
              "value2": "label_only"
            }
          ]
        },
        "renameOutput": true,
        "outputKey": "label_only"
      },
      {
        "conditions": {
          "string": [
            {
              "value1": "={{$json.action}}",
              "value2": "promote_train"
            }
          ]
        },
        "renameOutput": true,
        "outputKey": "promote_train"
      },
      {
        "conditions": {
          "string": [
            {
              "value1": "={{$json.action}}",
              "value2": "promote_test"
            }
          ]
        },
        "renameOutput": true,
        "outputKey": "promote_test"
      },
      {
        "conditions": {
          "string": [
            {
              "value1": "={{$json.action}}",
              "value2": "discard"
            }
          ]
        },
        "renameOutput": true,
        "outputKey": "discard"
      }
    ]
  }
}
```

#### 6) `HTTP: mm.relabel` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/relabel",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {
        "name": "Idempotency-Key",
        "value": "={{$json.idempotency_key}}"
      }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "schema_version",
        "value": "=v1"
      },
      {
        "name": "video_id",
        "value": "={{$json.video_id}}"
      },
      {
        "name": "new_label",
        "value": "={{$json.label}}"
      }
    ]
  },
  "method": "POST"
}
```
`credentials`
```json
{
  "httpHeaderAuth": {
    "id": "1",
    "name": "Media Mover Auth"
  }
}
```

#### 7) `HTTP: mm.promote` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/media/promote",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {
        "name": "Idempotency-Key",
        "value": "={{$json.idempotency_key}}"
      }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "video_id",
        "value": "={{$json.video_id}}"
      },
      {
        "name": "dest_split",
        "value": "={{$json.action === 'promote_train' ? 'train' : 'test'}}"
      },
      {
        "name": "label",
        "value": "={{$json.action === 'promote_train' ? $json.label : null}}"
      },
      {
        "name": "correlation_id",
        "value": "={{$json.correlation_id}}"
      },
      {
        "name": "dry_run",
        "value": "=false"
      }
    ]
  },
  "method": "POST"
}
```
`credentials`
```json
{
  "httpHeaderAuth": {
    "id": "1",
    "name": "Media Mover Auth"
  }
}
```

#### 8) `Postgres: class.balance` (Postgres)

`parameters`
```json
{
  "operation": "executeQuery",
  "query": "SELECT \n  COUNT(CASE WHEN label = 'happy' AND split = 'train' THEN 1 END) AS happy_count,\n  COUNT(CASE WHEN label = 'sad' AND split = 'train' THEN 1 END) AS sad_count,\n  COUNT(CASE WHEN label = 'neutral' AND split = 'train' THEN 1 END) AS neutral_count,\n  COUNT(*) FILTER (WHERE split = 'train') AS total_train\nFROM video;",
  "options": {}
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```

#### 9) `Respond: success` (Respond to Webhook)

`parameters`
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\n  \"status\": \"success\",\n  \"video_id\": $json.video_id,\n  \"label\": $json.label,\n  \"action\": $json.action,\n  \"class_balance\": {\n    \"happy\": $json.happy_count,\n    \"sad\": $json.sad_count,\n    \"neutral\": $json.neutral_count,\n    \"total_train\": $json.total_train,\n    \"balanced\": Math.max($json.happy_count, $json.sad_count, $json.neutral_count) - Math.min($json.happy_count, $json.sad_count, $json.neutral_count) <= 10\n  },\n  \"correlation_id\": $json.correlation_id\n} }}"
}
```

## Agent 3 — Promotion

Workflow file: `n8n/workflows/ml-agentic-ai_v.3/03_promotion_agent.json`

| Node instance | Official n8n node | Credential(s) |
|---|---|---|
| 1. `Webhook: request.promotion` | Webhook | `none` |
| 2. `Code: validate.request` | Code | `none` |
| 3. `HTTP: dryrun.promote` | HTTP Request | `httpHeaderAuth` |
| 4. `Code: summarize.plan` | Code | `none` |
| 5. `Webhook: await.approval` | Webhook | `none` |
| 6. `IF: approved?` | If | `none` |
| 7. `HTTP: real.promote` | HTTP Request | `httpHeaderAuth` |
| 8. `HTTP: rebuild.manifest` | HTTP Request | `httpHeaderAuth` |
| 9. `HTTP: emit.completed` | HTTP Request | `none` |
| 10. `Respond: success` | Respond to Webhook | `none` |
| 11. `Respond: rejected` | Respond to Webhook | `none` |

### Exact Parameter Objects by Node Instance

#### 1) `Webhook: request.promotion` (Webhook)

`parameters`
```json
{
  "httpMethod": "POST",
  "path": "promotion/v1",
  "responseMode": "responseNode",
  "options": {}
}
```

#### 2) `Code: validate.request` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Validate promotion request\nconst body = $json.body ?? $json;\nconst required = ['video_id', 'label'];\n\nfor (const field of required) {\n  if (!body[field]) {\n    throw new Error(`Missing required field: ${field}`);\n  }\n}\n\nconst allowedSplits = ['train', 'test'];\nconst target = body.target || body.dest_split || 'train';\n\nif (!allowedSplits.includes(target)) {\n  throw new Error(`Invalid target split: ${target}`);\n}\n\n// Generate stable idempotency key\nconst crypto = require('crypto');\nconst idem = body.idempotency_key || crypto.createHash('sha256')\n  .update(`${body.video_id}|${target}|${body.label}`)\n  .digest('hex').slice(0, 32);\n\nreturn [{\n  json: {\n    video_id: body.video_id,\n    label: body.label,\n    target,\n    idempotency_key: idem,\n    correlation_id: body.correlation_id || `promo-${Date.now()}`,\n    dry_run: true  // Start with dry-run\n  }\n}];"
}
```

#### 3) `HTTP: dryrun.promote` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/media/promote",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {
        "name": "Idempotency-Key",
        "value": "={{$json.idempotency_key}}"
      }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "video_id",
        "value": "={{$json.video_id}}"
      },
      {
        "name": "dest_split",
        "value": "={{$json.target}}"
      },
      {
        "name": "label",
        "value": "={{$json.label}}"
      },
      {
        "name": "dry_run",
        "value": "=true"
      },
      {
        "name": "correlation_id",
        "value": "={{$json.correlation_id}}"
      }
    ]
  },
  "method": "POST"
}
```
`credentials`
```json
{
  "httpHeaderAuth": {
    "id": "1",
    "name": "Media Mover Auth"
  }
}
```

#### 4) `Code: summarize.plan` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Summarize dry-run plan for approval\nconst plan = $json;\nconst req = $('Code: validate.request').first().json;\n\nreturn [{\n  json: {\n    approval_request: {\n      title: 'Video Promotion Request',\n      video_id: req.video_id,\n      label: req.label,\n      target_split: req.target,\n      plan_summary: {\n        will_move: plan.moves || [],\n        will_update_db: plan.will_update_db !== false,\n        conflicts: plan.conflicts || [],\n        dry_run_status: plan.status\n      },\n      correlation_id: req.correlation_id,\n      idempotency_key: req.idempotency_key\n    }\n  }\n}];"
}
```

#### 5) `Webhook: await.approval` (Webhook)

`parameters`
```json
{
  "httpMethod": "POST",
  "path": "promotion/approve",
  "responseMode": "onReceived",
  "options": {}
}
```

#### 6) `IF: approved?` (If)

`parameters`
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{$json.approved}}",
        "value2": true
      }
    ]
  }
}
```

#### 7) `HTTP: real.promote` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/media/promote",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {
        "name": "Idempotency-Key",
        "value": "={{$json.idempotency_key}}"
      }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "video_id",
        "value": "={{$json.video_id}}"
      },
      {
        "name": "dest_split",
        "value": "={{$json.target_split}}"
      },
      {
        "name": "label",
        "value": "={{$json.label}}"
      },
      {
        "name": "dry_run",
        "value": "=false"
      },
      {
        "name": "correlation_id",
        "value": "={{$json.correlation_id}}"
      }
    ]
  },
  "method": "POST"
}
```
`credentials`
```json
{
  "httpHeaderAuth": {
    "id": "1",
    "name": "Media Mover Auth"
  }
}
```

#### 8) `HTTP: rebuild.manifest` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/v1/ingest/manifest/rebuild",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {
        "name": "X-Correlation-ID",
        "value": "={{$json.correlation_id}}"
      }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "splits",
        "value": "=[\"train\", \"test\"]"
      },
      {
        "name": "correlation_id",
        "value": "={{$json.correlation_id}}"
      }
    ]
  },
  "method": "POST"
}
```
`credentials`
```json
{
  "httpHeaderAuth": {
    "id": "1",
    "name": "Media Mover Auth"
  }
}
```

#### 9) `HTTP: emit.completed` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/pipeline",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "=promotion.completed"
      },
      {
        "name": "pipeline_id",
        "value": "={{$json.correlation_id}}"
      },
      {
        "name": "video_id",
        "value": "={{$json.video_id}}"
      },
      {
        "name": "dest_split",
        "value": "={{$json.target_split}}"
      },
      {
        "name": "label",
        "value": "={{$json.label}}"
      },
      {
        "name": "correlation_id",
        "value": "={{$json.correlation_id}}"
      },
      {
        "name": "dataset_hash",
        "value": "={{$('HTTP: rebuild.manifest').first().json.dataset_hash || ''}}"
      }
    ]
  },
  "method": "POST"
}
```

#### 10) `Respond: success` (Respond to Webhook)

`parameters`
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\n  \"status\": \"success\",\n  \"video_id\": $json.video_id,\n  \"dest_split\": $json.target_split,\n  \"dataset_hash\": $json.dataset_hash,\n  \"correlation_id\": $json.correlation_id\n} }}"
}
```

#### 11) `Respond: rejected` (Respond to Webhook)

`parameters`
```json
{
  "respondWith": "json",
  "responseBody": "={{ {\n  \"status\": \"rejected\",\n  \"message\": \"Promotion not approved\",\n  \"correlation_id\": $json.correlation_id\n} }}",
  "options": {
    "responseCode": 403
  }
}
```

## Agent 4 — Reconciler

Workflow file: `n8n/workflows/ml-agentic-ai_v.3/04_reconciler_agent.json`

| Node instance | Official n8n node | Credential(s) |
|---|---|---|
| 1. `Schedule: daily 02:15` | Schedule Trigger | `none` |
| 2. `Webhook: manual.trigger` | Webhook | `none` |
| 3. `Set: config` | Set (Edit Fields) | `none` |
| 4. `SSH: scan.filesystem` | SSH | `sshPassword` |
| 5. `Code: parse.fs_scan` | Code | `none` |
| 6. `Postgres: fetch.all_videos` | Postgres | `postgres` |
| 7. `Code: diff.fs_db` | Code | `none` |
| 8. `IF: drift.found?` | If | `none` |
| 9. `Email: send.report` | Send Email | `none` |

### Exact Parameter Objects by Node Instance

#### 1) `Schedule: daily 02:15` (Schedule Trigger)

`parameters`
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "15 2 * * *"
      }
    ]
  }
}
```

#### 2) `Webhook: manual.trigger` (Webhook)

`parameters`
```json
{
  "httpMethod": "GET",
  "path": "reconciler/audit",
  "responseMode": "onReceived",
  "options": {}
}
```

#### 3) `Set: config` (Set (Edit Fields))

`parameters`
```json
{
  "assignments": {
    "assignments": [
      {
        "id": "1",
        "name": "root_dir",
        "value": "/videos",
        "type": "string"
      },
      {
        "id": "2",
        "name": "safe_fix",
        "value": "=false",
        "type": "boolean"
      }
    ]
  }
}
```

#### 4) `SSH: scan.filesystem` (SSH)

`parameters`
```json
{
  "command": "find /videos/{temp,train,test} -type f -name '*.mp4' -printf '{\"file_path\":\"%P\",\"size_bytes\":%s,\"mtime\":\"%TY-%Tm-%TdT%TH:%TM:%TSZ\"}\\n'",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "3",
    "name": "SSH Ubuntu1"
  }
}
```

#### 5) `Code: parse.fs_scan` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Parse JSONL filesystem scan results\nconst output = $json.stdout || '';\nconst lines = output.split('\\n').filter(Boolean);\nconst items = [];\n\nfor (const line of lines) {\n  try {\n    const obj = JSON.parse(line);\n    const pathParts = obj.file_path.split('/');\n    const split = pathParts[0];\n    \n    items.push({\n      json: {\n        file_path: obj.file_path,\n        size_bytes: parseInt(obj.size_bytes, 10),\n        mtime: obj.mtime,\n        split,\n        source: 'fs'\n      }\n    });\n  } catch (e) {\n    // Skip malformed lines\n  }\n}\n\nreturn items;"
}
```

#### 6) `Postgres: fetch.all_videos` (Postgres)

`parameters`
```json
{
  "operation": "executeQuery",
  "query": "SELECT\n  video_id,\n  file_path,\n  split,\n  label,\n  size_bytes,\n  sha256,\n  updated_at\nFROM video;",
  "options": {}
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```

#### 7) `Code: diff.fs_db` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Diff filesystem vs database\nconst fsItems = $('Code: parse.fs_scan').all();\nconst dbItems = $('Postgres: fetch.all_videos').all();\n\n// Build maps\nconst fsMap = new Map();\nfor (const item of fsItems) {\n  fsMap.set(item.json.file_path, item.json);\n}\n\nconst dbMap = new Map();\nfor (const item of dbItems) {\n  dbMap.set(item.json.file_path, item.json);\n}\n\n// Find differences\nconst orphans_fs = [];\nconst missing_fs = [];\nconst mismatches = [];\n\n// Orphans: in FS, not in DB\nfor (const [path, fsData] of fsMap) {\n  if (!dbMap.has(path)) {\n    orphans_fs.push({ file_path: path, ...fsData });\n  }\n}\n\n// Missing: in DB, not in FS\nfor (const [path, dbData] of dbMap) {\n  if (!fsMap.has(path)) {\n    missing_fs.push({ file_path: path, video_id: dbData.video_id });\n  } else {\n    // Check for mismatches\n    const fsData = fsMap.get(path);\n    if (fsData.size_bytes !== dbData.size_bytes || fsData.split !== dbData.split) {\n      mismatches.push({\n        file_path: path,\n        fs_size: fsData.size_bytes,\n        db_size: dbData.size_bytes,\n        fs_split: fsData.split,\n        db_split: dbData.split\n      });\n    }\n  }\n}\n\nreturn [{\n  json: {\n    summary: {\n      total_fs: fsMap.size,\n      total_db: dbMap.size,\n      orphans_count: orphans_fs.length,\n      missing_count: missing_fs.length,\n      mismatch_count: mismatches.length\n    },\n    orphans_fs,\n    missing_fs,\n    mismatches,\n    timestamp: new Date().toISOString()\n  }\n}];"
}
```

#### 8) `IF: drift.found?` (If)

`parameters`
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{$json.summary.orphans_count > 0 || $json.summary.missing_count > 0 || $json.summary.mismatch_count > 0}}"
      }
    ]
  }
}
```

#### 9) `Email: send.report` (Send Email)

`parameters`
```json
{
  "fromEmail": "noreply@reachy.local",
  "toEmail": "rustybee255@gmail.com",
  "subject": "=Reconciler Report: {{$json.summary.orphans_count}} orphans, {{$json.summary.missing_count}} missing",
  "emailType": "text",
  "message": "=Reconciler completed at {{$json.timestamp}}\n\nSummary:\n- FS files: {{$json.summary.total_fs}}\n- DB records: {{$json.summary.total_db}}\n- Orphans (FS only): {{$json.summary.orphans_count}}\n- Missing (DB only): {{$json.summary.missing_count}}\n- Mismatches: {{$json.summary.mismatch_count}}\n\nReview in database or n8n execution logs."
}
```

## Agent 5 — Training

Workflow file: `n8n/workflows/ml-agentic-ai_v.3/05_training_orchestrator_efficientnet.json`

| Node instance | Official n8n node | Credential(s) |
|---|---|---|
| 1. `Webhook: training.start` | Webhook | `none` |
| 2. `Postgres: check.train_balance` | Postgres | `postgres` |
| 3. `IF: sufficient_data?` | If | `none` |
| 4. `HTTP: mlflow.create_run` | HTTP Request | `none` |
| 5. `Code: prepare.training` | Code | `none` |
| 6. `SSH: start.training` | SSH | `sshPassword` |
| 7. `Wait: 5min` | Wait | `none` |
| 8. `SSH: check.status` | SSH | `sshPassword` |
| 9. `Code: parse.results` | Code | `none` |
| 10. `IF: training.done?` | If | `none` |
| 11. `IF: Gate_A.pass?` | If | `none` |
| 12. `HTTP: mlflow.log_gate` | HTTP Request | `none` |
| 13. `HTTP: emit.completed` | HTTP Request | `none` |
| 14. `HTTP: emit.gate_failed` | HTTP Request | `none` |
| 15. `HTTP: emit.insufficient_data` | HTTP Request | `none` |

### Exact Parameter Objects by Node Instance

#### 1) `Webhook: training.start` (Webhook)

`parameters`
```json
{
  "httpMethod": "POST",
  "path": "agent/training/efficientnet/start",
  "responseMode": "onReceived",
  "options": {
    "responseCode": 202
  }
}
```

#### 2) `Postgres: check.train_balance` (Postgres)

`parameters`
```json
{
  "operation": "executeQuery",
  "query": "SELECT COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train, COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train, COUNT(*) FILTER (WHERE label='neutral' AND split='train') AS neutral_train FROM video;"
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```

#### 3) `IF: sufficient_data?` (If)

`parameters`
```json
{
  "conditions": {
    "number": [
      {
        "value1": "={{Math.min($json.happy_train, $json.sad_train, $json.neutral_train)}}",
        "operation": "largerEqual",
        "value2": 50
      }
    ]
  }
}
```

#### 4) `HTTP: mlflow.create_run` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/create",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "experiment_id",
        "value": "={{$env.MLFLOW_EXPERIMENT_ID}}"
      },
      {
        "name": "tags",
        "value": "={{[{key: 'model', value: 'efficientnet-b0-hsemotion'}, {key: 'dataset_hash', value: $json.dataset_hash}, {key: 'correlation_id', value: $json.correlation_id}]}}"
      }
    ]
  },
  "method": "POST"
}
```

#### 5) `Code: prepare.training` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Generate run ID and prepare 3-class EfficientNet pipeline command\nconst timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);\nconst runId = `efficientnet_b0_emotion_${timestamp}`;\n\nreturn [{\n  json: {\n    ...items[0].json,\n    run_id: runId,\n    config_path: '/workspace/trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml',\n    output_dir: `/workspace/experiments/${runId}`,\n    model_placeholder: 'efficientnet-b0-hsemotion',\n    model_storage_path: '/media/rusty_admin/project_data/ml_models/efficientnet_b0',\n    gateway_base: $env.GATEWAY_BASE_URL || 'http://10.0.4.140:8000'\n  }\n}];"
}
```

#### 6) `SSH: start.training` (SSH)

`parameters`
```json
{
  "command": "cd /workspace && mkdir -p {{$json.output_dir}} && source venv/bin/activate && python trainer/run_efficientnet_pipeline.py --config {{$json.config_path}} --run-id {{$json.run_id}} --output-dir {{$json.output_dir}} --gateway-base {{$json.gateway_base}} --strict-contract-updates > {{$json.output_dir}}/pipeline.log 2>&1",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "3",
    "name": "SSH Ubuntu1"
  }
}
```

#### 7) `Wait: 5min` (Wait)

`parameters`
```json
{
  "amount": 5,
  "unit": "minutes"
}
```

#### 8) `SSH: check.status` (SSH)

`parameters`
```json
{
  "command": "RUN_STATUS=$(curl -s {{$json.gateway_base}}/api/training/status/{{$json.run_id}}); LATEST_STATUS=$(curl -s {{$json.gateway_base}}/api/training/status/latest); echo \"{\\\"run_status\\\":$RUN_STATUS,\\\"latest_status\\\":$LATEST_STATUS}\"",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "3",
    "name": "SSH Ubuntu1"
  }
}
```

#### 9) `Code: parse.results` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "const payload = JSON.parse($json.stdout || '{}');\nconst runStatus = payload.run_status || {};\nconst latestStatus = payload.latest_status || {};\nconst metrics = runStatus.metrics || {};\nconst gateResults = metrics.gate_a_gates || {};\n\nif (runStatus.status === 'training' || runStatus.status === 'evaluating' || runStatus.status === 'pending' || runStatus.status === 'sampling') {\n  return [{json: {...items[0].json, status: 'running', run_status: runStatus, latest_status: latestStatus}}];\n}\n\nreturn [{\n  json: {\n    ...items[0].json,\n    status: runStatus.status || 'unknown',\n    best_metric: metrics.best_metric ?? metrics.f1_macro ?? null,\n    epochs_completed: metrics.epochs_completed ?? null,\n    gate_results: {\n      ...gateResults,\n      gate_a: metrics.gate_a_passed ?? false\n    },\n    run_status: runStatus,\n    latest_status: latestStatus\n  }\n}];"
}
```

#### 10) `IF: training.done?` (If)

`parameters`
```json
{
  "conditions": {
    "string": [
      {
        "value1": "={{$json.status}}",
        "operation": "contains",
        "value2": "completed"
      }
    ]
  }
}
```

#### 11) `IF: Gate_A.pass?` (If)

`parameters`
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{$json.gate_results.gate_a}}",
        "value2": true
      }
    ]
  }
}
```

#### 12) `HTTP: mlflow.log_gate` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/log-metric",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "run_id",
        "value": "={{$json.mlflow_run_id}}"
      },
      {
        "name": "key",
        "value": "=gate_a_passed"
      },
      {
        "name": "value",
        "value": "={{$json.gate_results.gate_a ? 1 : 0}}"
      }
    ]
  },
  "method": "POST"
}
```

#### 13) `HTTP: emit.completed` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/training",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "=training.completed"
      },
      {
        "name": "run_id",
        "value": "={{$json.run_id}}"
      },
      {
        "name": "model",
        "value": "=efficientnet-b0-hsemotion"
      },
      {
        "name": "gate_a_passed",
        "value": "={{$json.gate_results.gate_a}}"
      },
      {
        "name": "onnx_path",
        "value": "={{$json.export?.onnx || ''}}"
      },
      {
        "name": "best_f1",
        "value": "={{$json.best_metric}}"
      }
    ]
  },
  "method": "POST"
}
```

#### 14) `HTTP: emit.gate_failed` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/training",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "=training.gate_failed"
      },
      {
        "name": "run_id",
        "value": "={{$json.run_id}}"
      },
      {
        "name": "model",
        "value": "=efficientnet-b0-hsemotion"
      },
      {
        "name": "best_f1",
        "value": "={{$json.best_metric}}"
      },
      {
        "name": "message",
        "value": "=Gate A requirements not met. Need more training data or hyperparameter tuning."
      }
    ]
  },
  "method": "POST"
}
```

#### 15) `HTTP: emit.insufficient_data` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/training",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "=training.insufficient_data"
      },
      {
        "name": "happy_count",
        "value": "={{$json.happy_train}}"
      },
      {
        "name": "sad_count",
        "value": "={{$json.sad_train}}"
      },
      {
        "name": "neutral_count",
        "value": "={{$json.neutral_train}}"
      },
      {
        "name": "message",
        "value": "=Insufficient training data. Need at least 50 samples per class (happy/sad/neutral)."
      }
    ]
  },
  "method": "POST"
}
```

## Agent 6 — Evaluation

Workflow file: `n8n/workflows/ml-agentic-ai_v.3/06_evaluation_agent_efficientnet.json`

| Node instance | Official n8n node | Credential(s) |
|---|---|---|
| 1. `Webhook: evaluation.start` | Webhook | `none` |
| 2. `Postgres: check.test_balance` | Postgres | `postgres` |
| 3. `IF: test_set.balanced?` | If | `none` |
| 4. `Code: prepare.evaluation` | Code | `none` |
| 5. `SSH: run.evaluation` | SSH | `sshPassword` |
| 6. `Code: parse.results` | Code | `none` |
| 7. `HTTP: mlflow.log_metrics` | HTTP Request | `none` |
| 8. `IF: Gate_A.pass?` | If | `none` |
| 9. `HTTP: emit.completed` | HTTP Request | `none` |
| 10. `HTTP: emit.gate_failed` | HTTP Request | `none` |
| 11. `Code: prepare.blocked_status` | Code | `none` |
| 12. `HTTP: status.blocked` | HTTP Request | `none` |

### Exact Parameter Objects by Node Instance

#### 1) `Webhook: evaluation.start` (Webhook)

`parameters`
```json
{
  "httpMethod": "POST",
  "path": "agent/evaluation/efficientnet/start",
  "responseMode": "onReceived"
}
```

#### 2) `Postgres: check.test_balance` (Postgres)

`parameters`
```json
{
  "operation": "executeQuery",
  "query": "SELECT COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test, COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test, COUNT(*) FILTER (WHERE label='neutral' AND split='test') AS neutral_test FROM video;"
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```

#### 3) `IF: test_set.balanced?` (If)

`parameters`
```json
{
  "conditions": {
    "number": [
      {
        "value1": "={{Math.min($json.happy_test, $json.sad_test, $json.neutral_test)}}",
        "operation": "largerEqual",
        "value2": 20
      }
    ]
  }
}
```

#### 4) `Code: prepare.evaluation` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Prepare evaluation command using pipeline runner in skip-train mode\nconst timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);\nconst runId = $json.run_id || `efficientnet_eval_${timestamp}`;\nconst checkpointPath = $json.checkpoint_path || `/workspace/checkpoints/efficientnet_b0_emotion/best_model.pth`;\n\nreturn [{\n  json: {\n    ...items[0].json,\n    run_id: runId,\n    checkpoint_path: checkpointPath,\n    output_dir: `/workspace/experiments/${runId}`,\n    gateway_base: $env.GATEWAY_BASE_URL || 'http://10.0.4.140:8000',\n    model_placeholder: 'efficientnet-b0-hsemotion'\n  }\n}];"
}
```

#### 5) `SSH: run.evaluation` (SSH)

`parameters`
```json
{
  "command": "cd /workspace && mkdir -p {{$json.output_dir}} && source venv/bin/activate && python trainer/run_efficientnet_pipeline.py --skip-train --checkpoint {{$json.checkpoint_path}} --run-id {{$json.run_id}} --output-dir {{$json.output_dir}} --gateway-base {{$json.gateway_base}} --strict-contract-updates > {{$json.output_dir}}/evaluation.log 2>&1; RUN_STATUS=$(curl -s {{$json.gateway_base}}/api/training/status/{{$json.run_id}}); LATEST_STATUS=$(curl -s {{$json.gateway_base}}/api/training/status/latest); echo \"{\\\"run_status\\\":$RUN_STATUS,\\\"latest_status\\\":$LATEST_STATUS}\"",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "3",
    "name": "SSH Ubuntu1"
  }
}
```

#### 6) `Code: parse.results` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Parse persisted status snapshots (run-specific + latest)\nconst output = $json.stdout || '{}';\nlet payload;\ntry {\n  payload = JSON.parse(output);\n} catch (e) {\n  payload = {error: 'Failed to parse status output', raw: output};\n}\n\nconst runStatus = payload.run_status || {};\nconst latestStatus = payload.latest_status || {};\nconst metrics = runStatus.metrics?.gate_a_metrics || runStatus.metrics || {};\nconst gateGates = runStatus.metrics?.gate_a_gates || {};\nconst gateA = {\n  f1_macro: gateGates.macro_f1 ?? ((metrics.f1_macro || 0) >= 0.84),\n  balanced_accuracy: gateGates.balanced_accuracy ?? ((metrics.balanced_accuracy || 0) >= 0.85),\n  ece: gateGates.ece ?? ((metrics.ece || 1) <= 0.08),\n  brier: gateGates.brier ?? ((metrics.brier || 1) <= 0.16),\n  passed: runStatus.metrics?.gate_a_passed ?? false\n};\n\nreturn [{\n  json: {\n    ...items[0].json,\n    run_status: runStatus,\n    latest_status: latestStatus,\n    metrics,\n    gate_a: gateA\n  }\n}];"
}
```

#### 7) `HTTP: mlflow.log_metrics` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.MLFLOW_URL}}/api/2.0/mlflow/runs/log-batch",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "run_id",
        "value": "={{$json.mlflow_run_id}}"
      },
      {
        "name": "metrics",
        "value": "={{[{key: 'eval_f1_macro', value: $json.metrics.f1_macro}, {key: 'eval_accuracy', value: $json.metrics.accuracy}, {key: 'eval_ece', value: $json.metrics.ece}, {key: 'eval_brier', value: $json.metrics.brier}, {key: 'eval_balanced_accuracy', value: $json.metrics.balanced_accuracy}]}}"
      }
    ]
  },
  "method": "POST"
}
```

#### 8) `IF: Gate_A.pass?` (If)

`parameters`
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{$json.gate_a.passed}}",
        "value2": true
      }
    ]
  }
}
```

#### 9) `HTTP: emit.completed` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/pipeline",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "=evaluation.completed"
      },
      {
        "name": "pipeline_id",
        "value": "={{$json.run_id}}"
      },
      {
        "name": "run_id",
        "value": "={{$json.run_id}}"
      },
      {
        "name": "model",
        "value": "=efficientnet-b0-hsemotion"
      },
      {
        "name": "gate_a_passed",
        "value": "={{$json.gate_a.passed}}"
      },
      {
        "name": "f1_macro",
        "value": "={{$json.metrics.f1_macro}}"
      },
      {
        "name": "ece",
        "value": "={{$json.metrics.ece}}"
      },
      {
        "name": "ready_for_deployment",
        "value": "={{$json.gate_a.passed}}"
      }
    ]
  },
  "method": "POST"
}
```

#### 10) `HTTP: emit.gate_failed` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/pipeline",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "=evaluation.gate_failed"
      },
      {
        "name": "pipeline_id",
        "value": "={{$json.run_id}}"
      },
      {
        "name": "run_id",
        "value": "={{$json.run_id}}"
      },
      {
        "name": "model",
        "value": "=efficientnet-b0-hsemotion"
      },
      {
        "name": "gate_a_details",
        "value": "={{JSON.stringify($json.gate_a)}}"
      },
      {
        "name": "metrics",
        "value": "={{JSON.stringify($json.metrics)}}"
      }
    ]
  },
  "method": "POST"
}
```

#### 11) `Code: prepare.blocked_status` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);\nconst runId = $json.run_id || `efficientnet_eval_blocked_${timestamp}`;\nconst gatewayBase = $env.GATEWAY_BASE_URL || 'http://10.0.4.140:8000';\nconst happy = Number($json.happy_test || 0);\nconst sad = Number($json.sad_test || 0);\nconst neutral = Number($json.neutral_test || 0);\n\nreturn [{\n  json: {\n    ...items[0].json,\n    run_id: runId,\n    gateway_base: gatewayBase,\n    min_required_per_class: 20,\n    happy_test: happy,\n    sad_test: sad,\n    neutral_test: neutral,\n    min_count: Math.min(happy, sad, neutral),\n    blocked_reason: 'insufficient_test_data'\n  }\n}];"
}
```

#### 12) `HTTP: status.blocked` (HTTP Request)

`parameters`
```json
{
  "url": "={{$json.gateway_base}}/api/training/status/{{$json.run_id}}",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "schema_version",
        "value": "=v1"
      },
      {
        "name": "event_type",
        "value": "=evaluation.blocked_insufficient_test_data"
      },
      {
        "name": "source",
        "value": "=agent6.evaluation_agent"
      },
      {
        "name": "correlation_id",
        "value": "={{$json.run_id}}"
      },
      {
        "name": "status",
        "value": "=blocked"
      },
      {
        "name": "metrics",
        "value": "={{JSON.stringify({blocked_reason: $json.blocked_reason, min_required_per_class: $json.min_required_per_class, counts: {happy: $json.happy_test, sad: $json.sad_test, neutral: $json.neutral_test}, min_count: $json.min_count})}}"
      },
      {
        "name": "error_message",
        "value": "=Evaluation blocked: insufficient balanced test samples for happy/sad/neutral (minimum 20 per class)."
      }
    ]
  },
  "method": "POST"
}
```

## Agent 7 — Deployment

Workflow file: `n8n/workflows/ml-agentic-ai_v.3/07_deployment_agent_efficientnet.json`

| Node instance | Official n8n node | Credential(s) |
|---|---|---|
| 1. `Webhook: deployment.start` | Webhook | `none` |
| 2. `IF: gate_a.passed?` | If | `none` |
| 3. `Code: prepare.deployment` | Code | `none` |
| 4. `SSH: scp.onnx_to_jetson` | SSH | `sshPassword` |
| 5. `SSH: convert.to_tensorrt` | SSH | `sshPassword` |
| 6. `SSH: update.deepstream_config` | SSH | `sshPassword` |
| 7. `Wait: 30s` | Wait | `none` |
| 8. `SSH: verify.deployment` | SSH | `sshPassword` |
| 9. `Code: parse.verification` | Code | `none` |
| 10. `IF: Gate_B.pass?` | If | `none` |
| 11. `HTTP: emit.success` | HTTP Request | `none` |
| 12. `SSH: rollback` | SSH | `sshPassword` |
| 13. `HTTP: emit.rollback` | HTTP Request | `none` |

### Exact Parameter Objects by Node Instance

#### 1) `Webhook: deployment.start` (Webhook)

`parameters`
```json
{
  "httpMethod": "POST",
  "path": "agent/deployment/efficientnet/start",
  "responseMode": "onReceived",
  "options": {
    "responseCode": 202
  }
}
```

#### 2) `IF: gate_a.passed?` (If)

`parameters`
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{$json.gate_a_passed}}",
        "value2": true
      }
    ]
  }
}
```

#### 3) `Code: prepare.deployment` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Prepare deployment paths\nconst runId = $json.run_id;\nconst onnxPath = $json.onnx_path || `/workspace/exports/${runId}/emotion_classifier_${runId}.onnx`;\nconst enginePath = `/opt/reachy/models/emotion_efficientnet.engine`;\nconst backupPath = `/opt/reachy/models/backup/emotion_efficientnet_${Date.now()}.engine`;\n\nreturn [{\n  json: {\n    ...items[0].json,\n    onnx_path: onnxPath,\n    engine_path: enginePath,\n    backup_path: backupPath,\n    model_placeholder: 'efficientnet-b0-hsemotion',\n    deployment_stage: 'shadow'\n  }\n}];"
}
```

#### 4) `SSH: scp.onnx_to_jetson` (SSH)

`parameters`
```json
{
  "command": "scp {{$json.onnx_path}} jetson@10.0.4.150:/tmp/emotion_classifier.onnx",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "3",
    "name": "SSH Ubuntu1"
  }
}
```

#### 5) `SSH: convert.to_tensorrt` (SSH)

`parameters`
```json
{
  "command": "# Backup existing engine\nif [ -f {{$json.engine_path}} ]; then\n  mkdir -p /opt/reachy/models/backup\n  cp {{$json.engine_path}} {{$json.backup_path}}\nfi\n\n# Convert ONNX to TensorRT\n/usr/src/tensorrt/bin/trtexec \\\n  --onnx=/tmp/emotion_classifier.onnx \\\n  --saveEngine={{$json.engine_path}} \\\n  --fp16 \\\n  --workspace=2048 \\\n  --minShapes=input:1x3x224x224 \\\n  --optShapes=input:1x3x224x224 \\\n  --maxShapes=input:8x3x224x224",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "4",
    "name": "SSH Jetson"
  }
}
```

#### 6) `SSH: update.deepstream_config` (SSH)

`parameters`
```json
{
  "command": "# Update DeepStream config to use new engine\nsed -i 's|model-engine-file=.*|model-engine-file={{$json.engine_path}}|' /opt/reachy/config/emotion_inference.txt\n\n# Restart DeepStream service\nsudo systemctl restart reachy-emotion",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "4",
    "name": "SSH Jetson"
  }
}
```

#### 7) `Wait: 30s` (Wait)

`parameters`
```json
{
  "amount": 30,
  "unit": "seconds"
}
```

#### 8) `SSH: verify.deployment` (SSH)

`parameters`
```json
{
  "command": "# Check service status and get metrics\nsystemctl is-active reachy-emotion && \\\ncat /var/log/reachy/emotion_metrics.json | tail -1",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "4",
    "name": "SSH Jetson"
  }
}
```

#### 9) `Code: parse.verification` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "// Parse verification results\nconst output = $json.stdout || '';\nconst lines = output.trim().split('\\n');\nconst serviceActive = lines[0] === 'active';\n\nlet metrics = {};\ntry {\n  metrics = JSON.parse(lines[1] || '{}');\n} catch (e) {\n  metrics = {fps: 0, latency_ms: 999};\n}\n\n// Check Gate B requirements\nconst gateB = {\n  service_active: serviceActive,\n  fps_ok: metrics.fps >= 25,\n  latency_ok: metrics.latency_p50_ms <= 120,\n  passed: serviceActive && metrics.fps >= 25 && metrics.latency_p50_ms <= 120\n};\n\nreturn [{\n  json: {\n    ...items[0].json,\n    service_active: serviceActive,\n    metrics: metrics,\n    gate_b: gateB,\n    deployment_status: gateB.passed ? 'success' : 'failed'\n  }\n}];"
}
```

#### 10) `IF: Gate_B.pass?` (If)

`parameters`
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{$json.gate_b.passed}}",
        "value2": true
      }
    ]
  }
}
```

#### 11) `HTTP: emit.success` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/deployment",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "=deployment.completed"
      },
      {
        "name": "run_id",
        "value": "={{$json.run_id}}"
      },
      {
        "name": "model",
        "value": "=efficientnet-b0-hsemotion"
      },
      {
        "name": "engine_path",
        "value": "={{$json.engine_path}}"
      },
      {
        "name": "fps",
        "value": "={{$json.metrics.fps}}"
      },
      {
        "name": "latency_p50_ms",
        "value": "={{$json.metrics.latency_p50_ms}}"
      },
      {
        "name": "deployment_stage",
        "value": "=shadow"
      }
    ]
  },
  "method": "POST"
}
```

#### 12) `SSH: rollback` (SSH)

`parameters`
```json
{
  "command": "# Rollback to previous engine\nif [ -f {{$json.backup_path}} ]; then\n  cp {{$json.backup_path}} {{$json.engine_path}}\n  sudo systemctl restart reachy-emotion\nfi",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "4",
    "name": "SSH Jetson"
  }
}
```

#### 13) `HTTP: emit.rollback` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/deployment",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "=deployment.rollback"
      },
      {
        "name": "run_id",
        "value": "={{$json.run_id}}"
      },
      {
        "name": "reason",
        "value": "=Gate B failed - performance requirements not met"
      },
      {
        "name": "metrics",
        "value": "={{JSON.stringify($json.metrics)}}"
      }
    ]
  },
  "method": "POST"
}
```

## Agent 8 — Privacy

Workflow file: `n8n/workflows/ml-agentic-ai_v.3/08_privacy_agent.json`

| Node instance | Official n8n node | Credential(s) |
|---|---|---|
| 1. `Schedule: daily 03:00` | Schedule Trigger | `none` |
| 2. `Webhook: gdpr.deletion` | Webhook | `none` |
| 3. `Postgres: find.old_temp` | Postgres | `postgres` |
| 4. `Loop: batch.delete` | Split In Batches | `none` |
| 5. `SSH: delete.file` | SSH | `sshPassword` |
| 6. `Postgres: mark.purged` | Postgres | `postgres` |
| 7. `Postgres: audit.log` | Postgres | `postgres` |
| 8. `HTTP: emit.purged` | HTTP Request | `none` |

### Exact Parameter Objects by Node Instance

#### 1) `Schedule: daily 03:00` (Schedule Trigger)

`parameters`
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "0 3 * * *"
      }
    ]
  }
}
```

#### 2) `Webhook: gdpr.deletion` (Webhook)

`parameters`
```json
{
  "httpMethod": "POST",
  "path": "privacy/purge",
  "responseMode": "responseNode"
}
```

#### 3) `Postgres: find.old_temp` (Postgres)

`parameters`
```json
{
  "operation": "executeQuery",
  "query": "SELECT video_id, file_path FROM video WHERE split='temp' AND created_at < NOW() - INTERVAL '7 days';"
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```

#### 4) `Loop: batch.delete` (Split In Batches)

`parameters`
```json
{
  "batchSize": 50,
  "options": {}
}
```

#### 5) `SSH: delete.file` (SSH)

`parameters`
```json
{
  "command": "rm -f /videos/{{$json.file_path}}",
  "authentication": "password"
}
```
`credentials`
```json
{
  "sshPassword": {
    "id": "3",
    "name": "SSH Ubuntu1"
  }
}
```

#### 6) `Postgres: mark.purged` (Postgres)

`parameters`
```json
{
  "operation": "executeQuery",
  "query": "UPDATE video SET split='purged', updated_at=NOW() WHERE video_id='{{$json.video_id}}'::uuid;"
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```

#### 7) `Postgres: audit.log` (Postgres)

`parameters`
```json
{
  "operation": "insert",
  "table": "audit_log",
  "columns": "action, video_id, reason, timestamp"
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```

#### 8) `HTTP: emit.purged` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/api/events/pipeline",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "event_type",
        "value": "=privacy.purged"
      },
      {
        "name": "pipeline_id",
        "value": "=privacy-retention"
      },
      {
        "name": "count",
        "value": "=1"
      },
      {
        "name": "video_id",
        "value": "={{$json.video_id}}"
      }
    ]
  },
  "method": "POST"
}
```

## Agent 9 — Observability

Workflow file: `n8n/workflows/ml-agentic-ai_v.3/09_observability_agent.json`

| Node instance | Official n8n node | Credential(s) |
|---|---|---|
| 1. `Cron: every 30s` | Cron | `none` |
| 2. `HTTP: n8n.metrics` | HTTP Request | `none` |
| 3. `HTTP: mediamover.metrics` | HTTP Request | `none` |
| 4. `HTTP: gateway.metrics` | HTTP Request | `none` |
| 5. `Code: parse.metrics` | Code | `none` |
| 6. `Postgres: store.metrics` | Postgres | `postgres` |

### Exact Parameter Objects by Node Instance

#### 1) `Cron: every 30s` (Cron)

`parameters`
```json
{
  "rule": {
    "interval": [
      {
        "triggerAtSecond": 30
      }
    ]
  }
}
```

#### 2) `HTTP: n8n.metrics` (HTTP Request)

`parameters`
```json
{
  "url": "http://n8n:5678/metrics",
  "responseFormat": "string",
  "method": "GET"
}
```

#### 3) `HTTP: mediamover.metrics` (HTTP Request)

`parameters`
```json
{
  "url": "http://10.0.4.130:9101/metrics",
  "responseFormat": "string",
  "method": "GET"
}
```

#### 4) `HTTP: gateway.metrics` (HTTP Request)

`parameters`
```json
{
  "url": "={{$env.GATEWAY_BASE_URL}}/metrics",
  "responseFormat": "string",
  "method": "GET"
}
```

#### 5) `Code: parse.metrics` (Code)

`parameters`
```json
{
  "mode": "runOnceForAllItems",
  "jsCode": "const parseMetric = (text, name) => {\n  const m = text.match(new RegExp(`${name}\\s+(\\d+\\.?\\d*)`));\n  return m ? parseFloat(m[1]) : null;\n};\n\nconst ts = new Date().toISOString();\nconst items = [];\nconst n8n = $('HTTP: n8n.metrics').first().json.data;\nconst mm = $('HTTP: mediamover.metrics').first().json.data;\nconst gw = $('HTTP: gateway.metrics').first().json.data;\n\nitems.push({json: {ts, src: 'n8n', metric: 'active_executions', value: parseMetric(n8n, 'n8n_active_executions')}});\nitems.push({json: {ts, src: 'media_mover', metric: 'promote_total', value: parseMetric(mm, 'media_mover_promote_total')}});\nitems.push({json: {ts, src: 'gateway', metric: 'queue_depth', value: parseMetric(gw, 'gateway_queue_depth')}});\n\nreturn items.filter(i => i.json.value !== null);"
}
```

#### 6) `Postgres: store.metrics` (Postgres)

`parameters`
```json
{
  "operation": "insert",
  "table": "obs_samples",
  "columns": "ts, src, metric, value"
}
```
`credentials`
```json
{
  "postgres": {
    "id": "2",
    "name": "PostgreSQL - reachy_local"
  }
}
```
