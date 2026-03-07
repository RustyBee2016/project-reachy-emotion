# Workflow JSON Changelog (ml-agentic-ai_v.2 -> ml-agentic-ai_v.3)

This document explains exactly what changed in each workflow JSON and why, with direct linkage to backend code behavior.

## Agent 1 (`01_ingest_agent.json`)
- **Endpoint update:**
  - `HTTP: media.pull` URL changed from `/api/media/pull` to `/api/v1/ingest/pull`.
  - **Why:** active ingest router exposes `POST /api/v1/ingest/pull` in `apps/api/app/routers/ingest.py`.
- **Flow simplification:**
  - Removed nodes: `Wait: 3s`, `HTTP: check.status`, `Postgres: insert.video`, `Code: increment.attempt`.
  - **Why:** `pull_video()` is synchronous and already performs DB insert + metadata extraction; polling and duplicate insert were stale behavior.
- **Condition logic update:**
  - `IF: status.done?` now passes for `done` and `duplicate`.
  - **Why:** `pull_video()` returns both statuses.
- **Event payload update:**
  - Added `duplicate` and dynamic `event_type` (`ingest.completed` vs `ingest.duplicate`).

## Agent 2 (`02_labeling_agent.json`)
- **Relabel payload fix:**
  - `HTTP: mm.relabel` body changed from `label` to `new_label`.
  - **Why:** `RelabelRequest` in `apps/api/app/routers/gateway_upstream.py` requires `new_label`.
- **Promotion endpoint update:**
  - `HTTP: mm.promote` URL changed from `/api/promote` to `/api/v1/media/promote`.
  - **Why:** canonical promotion path in `apps/api/routers/media.py`.
- **3-class policy alignment:**
  - Promotion label now sent only for `promote_train` path.

## Agent 3 (`03_promotion_agent.json`)
- **Promotion endpoint update:**
  - Dry-run and real promote URLs switched to `/api/v1/media/promote`.
- **Manifest endpoint update:**
  - Rebuild URL changed to `/api/v1/ingest/manifest/rebuild`.
  - **Why:** active route in `apps/api/app/routers/ingest.py`.
- **Event endpoint remap:**
  - Completion event moved from `/api/events/promotion` to `/api/events/pipeline`.
  - **Why:** gateway currently implements `/api/events/pipeline`, not `/api/events/promotion`.
- **Code reference fix:**
  - `Code: summarize.plan` now references real node name (`Code: validate.request`) instead of stale identifier.

## Agent 4 (`04_reconciler_agent.json`)
- **Filesystem scan robustness:**
  - SSH `find` scope changed from `{temp,train,test,dataset_all}` to `{temp,train,test}`.
  - **Why:** avoid hard failure when `dataset_all` is absent.
- **Code node reference fix:**
  - `Code: diff.fs_db` now references `Code: parse.fs_scan` and `Postgres: fetch.all_videos` by actual names.

## Agent 5 (`05_training_orchestrator_efficientnet.json`)
- **Method hardening:**
  - All `HTTP Request` nodes explicitly set to `POST`.
  - **Why:** avoid ambiguous method defaults and ensure MLflow/gateway calls are deterministic.
- **No route changes:**
  - Existing `/api/events/training` and `/api/training/status/*` contracts already matched code.

## Agent 6 (`06_evaluation_agent_efficientnet.json`)
- **Event endpoint remap:**
  - `emit.completed` and `emit.gate_failed` moved from `/api/events/evaluation` to `/api/events/pipeline`.
  - **Why:** gateway currently lacks `/api/events/evaluation`; `/api/events/pipeline` is active.
- **Payload enrichment:**
  - Added `pipeline_id={{$json.run_id}}` into event payload.
- **Method hardening:**
  - Explicit `POST` for all outbound HTTP nodes.

## Agent 7 (`07_deployment_agent_efficientnet.json`)
- **Engine naming correction:**
  - `Code: prepare.deployment` updated engine path from `emotion_resnet50.engine` to `emotion_efficientnet.engine`.
  - Backup naming updated accordingly.
  - **Why:** align with project EfficientNet deployment target in AGENTS spec.
- **Method hardening:**
  - Explicit `POST` for deployment event nodes.

## Agent 8 (`08_privacy_agent.json`)
- **Retention policy alignment:**
  - `find.old_temp` query changed from `14 days` to `7 days`.
- **Event endpoint remap:**
  - `emit.purged` moved from `/api/events/privacy` to `/api/events/pipeline`.
  - **Why:** gateway currently lacks `/api/events/privacy`.
- **Event payload update:**
  - Added `pipeline_id=privacy-retention` and `video_id` for traceability.

## Agent 9 (`09_observability_agent.json`)
- **Gateway metrics endpoint update:**
  - `HTTP: gateway.metrics` changed from fixed `http://10.0.4.140:9100/metrics` to `{{$env.GATEWAY_BASE_URL}}/metrics`.
  - **Why:** active gateway app exposes `/metrics` on API service port.
- **Code reference fix:**
  - `Code: parse.metrics` now references actual node names (`HTTP: n8n.metrics`, etc.).
- **Method hardening:**
  - All scrape nodes set to explicit `GET`.

## Cross-workflow hardening
- Explicit HTTP methods were set across all v3 workflows to avoid relying on node defaults.
- Node-reference expressions in Code nodes were normalized to actual node names present in each workflow.
- v3 workflow titles were renamed to include `v3` for visual separation in n8n imports.
