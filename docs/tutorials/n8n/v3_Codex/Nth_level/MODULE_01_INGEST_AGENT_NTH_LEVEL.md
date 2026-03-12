# MODULE 01 — Ingest Agent (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/01_ingest_agent.json`

## Runtime Goal
Receive a new video request, normalize payload + auth, call media ingest API, and emit gateway ingest events.

## Node-to-Script Map

### 1) `Webhook: ingest.video` (`Webhook`)
- **Workflow role:** Entry point (`POST /webhook/video_gen_hook`).
- **Input contract:** Raw webhook body and headers.
- **Output contract:** n8n webhook envelope (`$json.body`, `$json.headers`) consumed by next nodes.
- **Backend binding:** none yet; this is n8n ingress.

### 2) `IF: auth.check` (`If`)
- **Workflow role:** Header token gate.
- **Expression:** `{{$json.headers['x-ingest-key']}} == {{$env.INGEST_TOKEN}}`.
- **Branching:**
- true -> continue pipeline
- false -> `Respond: 401 Unauthorized`
- **Backend binding:** protects downstream call to `POST /api/v1/ingest/pull`.

### 3) `Code: normalize.payload` (`Code`)
- **Workflow role:** Canonicalize request shape from multiple callers.
- **Essential in-node logic:**
- extracts `source_url` from `source_url | url | asset.url | data.asset.url`
- normalizes `label`
- constructs `meta.generator`
- sets `correlation_id` and `idempotency_key` fallbacks
- **Failure mode:** throws if source URL missing.
- **Backend binding:** prepares exact payload expected by `apps/api/app/routers/ingest.py:549` `pull_video(...)`.

### 4) `HTTP: media.pull` (`HTTP Request`)
- **Workflow role:** invokes ingest API.
- **HTTP target:** `POST {{$env.MEDIA_MOVER_BASE_URL}}/api/v1/ingest/pull`
- **Headers:** `Idempotency-Key`, `X-Correlation-ID`
- **Payload fields:** `source_url`, `correlation_id`, `intended_emotion`, `generator`, `prompt`
- **Backend binding:** `apps/api/app/routers/ingest.py:549` `pull_video(...)`
- **Essential functions called by endpoint:**
- `download_video(...)` (`ingest.py:213`)
- `compute_sha256(...)` (`ingest.py:221`)
- duplicate detection query on `Video.sha256 + size_bytes`
- `ffprobe_metadata(...)` (`ingest.py:226`)
- `generate_thumbnail(...)` (`ingest.py:302`)
- DB insert into `Video` model (`apps/api/app/db/models.py:41`)
- **Side effects:** writes file under `temp/`, thumbnail under `thumbs/`, inserts DB row.
- **Returned statuses used by n8n:** `done`, `duplicate`.

### 5) `IF: status.done?` (`If`)
- **Workflow role:** gates event emission to final statuses.
- **Expression:** `['done','duplicate'].includes($json.status)`.
- **Branching:**
- true -> emit event
- false -> immediate success response with current status

### 6) `HTTP: emit.completed` (`HTTP Request`)
- **Workflow role:** publishes ingest lifecycle event. 
- **HTTP target:** `POST {{$env.GATEWAY_BASE_URL}}/api/events/ingest`
- **Event fields:** `event_type` (`ingest.completed` or `ingest.duplicate`), `video_id`, `correlation_id`, `file_path`, `sha256`, `duplicate`
- **Backend binding:** `apps/api/routers/gateway.py:299` `post_ingest_event(...)`
- **Gateway behavior:** logs event and returns `202 accepted`.

### 7) `Respond: success` (`Respond to Webhook`)
- **Workflow role:** webhook response normalization.
- **Output payload:** `status`, `video_id`, `correlation_id`, `duplicate`.
- **Used by:** both direct path (non-final status) and post-event path.

### 8) `Respond: 401 Unauthorized` (`Respond to Webhook`)
- **Workflow role:** immediate auth failure response.
- **HTTP code:** `401`.

## How This Delivers Ingest Functionality
1. Node 1 captures upload/generation trigger.
2. Node 2 enforces ingest token.
3. Node 3 ensures downstream API always receives canonical fields.
4. Node 4 executes ingest mechanics (download/hash/dedupe/metadata/thumbnail/DB).
5. Node 5 checks lifecycle completion.
6. Node 6 emits an auditable ingest event to gateway.
7. Nodes 7/8 return deterministic API responses.

## Key Data Integrity Anchors
- `Video` uniqueness: `uq_video_sha256_size` (`models.py:86`) prevents duplicate binary registrations.
- `Video` split/label policy: `chk_video_split_label_policy` (`models.py:95`) enforces no label for `temp/test/purged`.
