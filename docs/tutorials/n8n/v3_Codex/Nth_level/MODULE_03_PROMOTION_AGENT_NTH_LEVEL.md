# MODULE 03 — Promotion / Curation Agent (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/03_promotion_agent.json`

## Runtime Goal
Run a two-phase promotion flow: dry-run planning, human approval, real promotion, manifest rebuild, and event emission.

## Node-to-Script Map

### 1) `Webhook: request.promotion` (`Webhook`)
- **Workflow role:** receives promotion requests.
- **Path/method:** `POST /webhook/promotion/v1`.

### 2) `Code: validate.request` (`Code`)
- **Workflow role:** normalize and validate promotion intent.
- **Essential in-node logic:**
- requires `video_id` and `label`
- normalizes target split from `target|dest_split` (default `train`)
- enforces target in `{train,test}`
- generates deterministic idempotency hash when missing
- sets `dry_run: true`

### 3) `HTTP: dryrun.promote` (`HTTP Request`)
- **Workflow role:** preflight promotion.
- **HTTP target:** `POST {{$env.MEDIA_MOVER_BASE_URL}}/api/v1/media/promote` with `dry_run=true`
- **Backend binding:** `apps/api/routers/media.py:60` `promote(...)`
- **Returned plan fields consumed later:** `src`, `dst`, `status`, conflicts/metadata when available.

### 4) `Code: summarize.plan` (`Code`)
- **Workflow role:** transform dry-run output into approval packet.
- **Essential in-node logic:**
- references `Code: validate.request` output with `$('Code: validate.request').first().json`
- emits structured `approval_request` object including plan summary and idempotency context

### 5) `Webhook: await.approval` (`Webhook`)
- **Workflow role:** pause for explicit human approval callback.
- **Path/method:** `POST /webhook/promotion/approve`.

### 6) `IF: approved?` (`If`)
- **Workflow role:** approval gate.
- **Expression:** boolean `{{$json.approved}}`.
- **Branches:**
- true -> real promotion
- false -> rejection response

### 7) `HTTP: real.promote` (`HTTP Request`)
- **Workflow role:** performs filesystem + DB promotion.
- **HTTP target:** same endpoint, `dry_run=false`.
- **Backend binding:** `apps/api/routers/media.py:60` `promote(...)`
- **Essential backend mechanics:**
- validates schema/target/label
- resolves video by ID or file stem
- optional auto-register path for orphaned file on disk
- idempotency replay check via `PromotionLog`
- file transition via `FileMover` (`apps/api/app/fs/media_mover.py`)
- updates `Video.split`, `Video.label`, `Video.file_path`
- inserts `PromotionLog` row
- compensating rollback on DB commit failure

### 8) `HTTP: rebuild.manifest` (`HTTP Request`)
- **Workflow role:** refresh train/test manifests after data movement.
- **HTTP target:** `POST {{$env.MEDIA_MOVER_BASE_URL}}/api/v1/ingest/manifest/rebuild`
- **Backend binding:** `apps/api/app/routers/ingest.py:998` `rebuild_manifest(...)`
- **Essential function:** `compute_dataset_hash(...)` (`ingest.py:345`) over manifest entries.

### 9) `HTTP: emit.completed` (`HTTP Request`)
- **Workflow role:** publish promotion completion event to pipeline event sink.
- **HTTP target:** `POST {{$env.GATEWAY_BASE_URL}}/api/events/pipeline`
- **Backend binding:** `apps/api/routers/gateway.py:346` `post_pipeline_event(...)`.

### 10) `Respond: success` (`Respond to Webhook`)
- **Workflow role:** return promotion success, split, dataset hash, correlation id.

### 11) `Respond: rejected` (`Respond to Webhook`)
- **Workflow role:** return `403` when approval is denied.

## How This Delivers Promotion/Curation Functionality
1. Prevalidates request + creates deterministic idempotency key.
2. Uses dry-run to make promotion consequences explicit before mutation.
3. Requires human approval to pass gating.
4. Executes atomic move + DB update through media service.
5. Rebuilds manifests and emits pipeline event for downstream training/evaluation.

## Core Data & Reliability Controls
- `PromotionLog` unique idempotency (`models.py:227`) supports replay-safe retries.
- `FileMover` staged atomic move + rollback logic provides filesystem safety.
- `Video` split/label constraint prevents illegal final states.
