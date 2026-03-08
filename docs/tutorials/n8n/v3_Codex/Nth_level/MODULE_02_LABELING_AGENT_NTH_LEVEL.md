# MODULE 02 — Labeling Agent (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/02_labeling_agent.json`

## Runtime Goal
Validate human labels/actions, persist label audit state, optionally relabel/promote media, and return class-balance summary.

## Node-to-Script Map

### 1) `Webhook: label.submitted` (`Webhook`)
- **Workflow role:** Entry point for label submissions.
- **Path/method:** `POST /webhook/label`.

### 2) `Code: validate.payload` (`Code`)
- **Workflow role:** strict client contract normalization.
- **Essential in-node logic:**
- enforces label in `{happy,sad,neutral}`
- enforces action in `{label_only,promote_train,promote_test,discard}`
- generates `idempotency_key` if missing
- normalizes `rater_id`, `notes`, `correlation_id`
- **Failure mode:** throws on missing `video_id`, invalid label/action.

### 3) `Postgres: fetch.video` (`Postgres`)
- **Workflow role:** verify current row state before mutation.
- **SQL target:** `video` table read by `video_id`.
- **Schema binding:** `Video` model (`apps/api/app/db/models.py:41`).

### 4) `Postgres: apply.label` (`Postgres`)
- **Workflow role:** write audit + mutate current label.
- **SQL behavior:**
- inserts into `label_event` with `ON CONFLICT (video_id, idempotency_key) DO NOTHING`
- updates `video.label` and `updated_at`
- returns current state + inserted `event_id`
- **Schema bindings:**
- `LabelEvent` (`models.py:269`)
- `Video` (`models.py:41`)
- **Constraint coupling:** `chk_video_split_label_policy` (`models.py:95`) can reject invalid split/label combinations.

### 5) `Switch: branch.action` (`Switch`)
- **Workflow role:** fan-out to action-specific integrations.
- **Branches:**
- `label_only` -> no media move
- `promote_train` -> promote with label
- `promote_test` -> promote without label
- `discard` -> skip promote/relabel; continue to balance report

### 6) `HTTP: mm.relabel` (`HTTP Request`)
- **Workflow role:** update canonical label in media backend.
- **HTTP target:** `POST {{$env.MEDIA_MOVER_BASE_URL}}/api/relabel`
- **Payload:** `schema_version`, `video_id`, `new_label`
- **Backend binding:** `apps/api/app/routers/gateway_upstream.py:395` `relabel_video(...)`
- **Function behavior:** validates label via `RelabelRequest` (`gateway_upstream.py:381`), updates `Video.label`, commits.

### 7) `HTTP: mm.promote` (`HTTP Request`)
- **Workflow role:** move media from `temp` to `train` or `test`.
- **HTTP target:** `POST {{$env.MEDIA_MOVER_BASE_URL}}/api/v1/media/promote`
- **Payload mapping:**
- `dest_split = train` for `promote_train`, else `test`
- `label` passed only for `promote_train`
- `dry_run = false`
- **Backend binding:** `apps/api/routers/media.py:60` `promote(...)`
- **Essential functions:**
- `FileMover.stage_to_train(...)` (`apps/api/app/fs/media_mover.py:40`) for train promotions
- DB promotion audit in `PromotionLog` (`models.py:213`)
- idempotency replay by `Idempotency-Key` against `PromotionLog.idempotency_key`

### 8) `Postgres: class.balance` (`Postgres`)
- **Workflow role:** compute training split label counts.
- **SQL target:** aggregate counts for `happy/sad/neutral` on `split='train'`.
- **Consumer:** webhook response body + balance heuristic.

### 9) `Respond: success` (`Respond to Webhook`)
- **Workflow role:** returns label action result and class-balance object.
- **Balanced rule used in response:** max-min <= 10.

## How This Delivers Labeling Functionality
1. Validates label policy + action semantics in n8n before DB writes.
2. Persists label audit trail in `label_event`.
3. Optionally calls relabel endpoint and promotion endpoint to sync DB + filesystem.
4. Returns updated class distribution for UI/operator decisions.

## Important Alignment Notes
- This workflow writes `video.label` directly in SQL before optional promote calls.
- `Video` policy constraint (`split='test'` => `label IS NULL`) is enforced at DB layer (`models.py:95`), so promotion to test should clear label in promote endpoint (`media.py:441`).
