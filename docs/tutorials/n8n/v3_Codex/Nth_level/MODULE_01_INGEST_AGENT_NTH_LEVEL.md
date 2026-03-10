# MODULE 01 — Ingest Agent (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/01_ingest_agent.json`

## Runtime Goal
Receive a new video request, normalize payload, call media ingest API, emit gateway ingest events, and respond to the webhook caller.

## Node-to-Script Map

### 1) `Webhook: ingest.video` (`Webhook`)
- **Workflow role:** Entry point (`POST /webhook/video_gen_hook`).
- **Input contract:** Raw webhook body and headers.
- **Output contract:** n8n webhook envelope (`$json.body`, `$json.headers`).
- **Backend binding:** none; ingress into n8n.

### 2) `Code: normalize.payload` (`Code`)
- **Workflow role:** Canonicalize request shape and trace metadata.
- **Essential logic:**
- extract `source_url` from supported payload variants
- enforce allowed labels (`happy|sad|neutral`) when provided
- generate `correlation_id` and stable fallback `idempotency_key`
- stamp `schema_version` and `issued_at`
- **Failure mode:** throws if source URL missing or label invalid.
- **Backend binding:** prepares payload for `pull_video(...)`.

### 3) `HTTP: media.pull` (`HTTP Request`)
- **Workflow role:** invoke ingest API.
- **HTTP target:** `POST http://10.0.4.130:8083/api/v1/ingest/pull`
- **Headers:** `Idempotency-Key`, `X-Correlation-ID`
- **Payload fields:** `source_url`, `correlation_id`, `intended_emotion`, `generator`, `prompt`
- **Retries:** enabled (`maxTries=5`, `waitBetweenTries=1000ms`)
- **Backend binding:** `apps/api/app/routers/ingest.py:549` `pull_video(...)`
- **Returned statuses used by n8n:** `done`, `duplicate`.

### 4) `IF: status.done?` (`If`)
- **Workflow role:** gate event emission to terminal statuses.
- **Expression:** `['done','duplicate'].includes($json.status)`.
- **Branching:**
- true -> emit event
- false -> respond immediately with current status

### 5) `HTTP: emit.completed` (`HTTP Request`)
- **Workflow role:** publish ingest lifecycle event.
- **HTTP target:** `POST http://10.0.4.140:8000/api/events/ingest`
- **Event fields:** `schema_version`, `event_type`, `source`, `issued_at`, `video_id`, `correlation_id`, `file_path`, `sha256`, `duplicate`
- **Retries:** enabled (`maxTries=5`, `waitBetweenTries=1000ms`)
- **Backend binding:** `apps/api/routers/gateway.py:299` `post_ingest_event(...)`

### 6) `Respond: success` (`Respond to Webhook`)
- **Workflow role:** normalized webhook response.
- **Output payload:** `status`, `video_id`, `correlation_id`, `duplicate`.

## How This Delivers Ingest Functionality
1. Node 1 captures upload/generation trigger.
2. Node 2 normalizes payload and enforces ingest policy.
3. Node 3 executes ingest mechanics (download/hash/dedupe/metadata/thumbnail/DB).
4. Node 4 checks lifecycle completion.
5. Node 5 emits an auditable ingest event envelope.
6. Node 6 returns deterministic API response.

## Key Data Integrity Anchors
- `video` uniqueness on `(sha256, size_bytes)` prevents duplicate binary registration.
- `chk_video_split_label_policy` enforces no label for `temp/test/purged` and label required for `train`.
