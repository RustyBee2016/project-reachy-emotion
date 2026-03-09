# n8n v3 Endpoint Alignment (Codebase vs Workflow JSON)

Last updated: 2026-03-07

## Purpose
This checklist maps current node URLs in `ml-agentic-ai_v.2` workflows to endpoints actually implemented in code.

## Canonical API rules for 08.4.2
- Promotion API: `POST /api/v1/media/promote` (canonical), with `POST /api/media/promote` legacy compatibility.
- Deprecated shims: `/api/v1/promote/stage` and `/api/v1/promote/sample` are intentionally deprecated and return validation errors via service layer.
- Training status contract: `/api/training/status/{pipeline_id}` is active for GET/POST status exchange.
- Labels must remain `happy|sad|neutral` for train data.

## Endpoint matrix
| Workflow node | Current URL in JSON | Codebase status | v3 tutorial action |
|---|---|---|---|
| Agent1 `HTTP: media.pull` | `{{$env.MEDIA_MOVER_BASE_URL}}/api/media/pull` | Not implemented in active app routers. | Switch to `{{$env.MEDIA_MOVER_BASE_URL}}/api/v1/ingest/pull`. |
| Agent1 `HTTP: emit.completed` | `{{$env.GATEWAY_BASE_URL}}/api/events/ingest` | Implemented in gateway router. | Keep. |
| Agent2 `HTTP: mm.relabel` | `{{$env.MEDIA_MOVER_BASE_URL}}/api/relabel` | Implemented in `gateway_upstream.py`. | Keep. |
| Agent2 `HTTP: mm.promote` | `{{$env.MEDIA_MOVER_BASE_URL}}/api/promote` | Not implemented on Media Mover app. | Switch to `/api/v1/media/promote` (or `/api/media/promote` fallback). |
| Agent3 `HTTP: dryrun.promote` | `{{$env.MEDIA_MOVER_BASE_URL}}/api/promote` | Not implemented on Media Mover app. | Switch to `/api/v1/media/promote` with `dry_run=true`. |
| Agent3 `HTTP: real.promote` | `{{$env.MEDIA_MOVER_BASE_URL}}/api/promote` | Not implemented on Media Mover app. | Switch to `/api/v1/media/promote` with `dry_run=false`. |
| Agent3 `HTTP: rebuild.manifest` | `{{$env.MEDIA_MOVER_BASE_URL}}/api/manifest/rebuild` | Implemented in `gateway_upstream.py`; v1 ingest route also exists at `/api/v1/ingest/manifest/rebuild`. | Keep or standardize to `/api/v1/ingest/manifest/rebuild`. |
| Agent3 `HTTP: emit.completed` | `{{$env.GATEWAY_BASE_URL}}/api/events/promotion` | Not implemented in gateway router. | Add endpoint or remap to existing `/api/events/pipeline`. |
| Agent5 `HTTP: emit.completed/gate_failed/insufficient_data` | `{{$env.GATEWAY_BASE_URL}}/api/events/training` | Implemented in gateway router. | Keep. |
| Agent6 `HTTP: emit.completed/gate_failed` | `{{$env.GATEWAY_BASE_URL}}/api/events/evaluation` | Not implemented in gateway router. | Add endpoint or remap to `/api/events/training` or `/api/events/pipeline`. |
| Agent6 `HTTP: status.blocked` | `{{$json.gateway_base}}/api/training/status/{{$json.run_id}}` | Implemented in gateway and Media Mover upstream routers. | Keep. |
| Agent7 `HTTP: emit.success/rollback` | `{{$env.GATEWAY_BASE_URL}}/api/events/deployment` | Implemented in gateway router. | Keep. |
| Agent8 `HTTP: emit.purged` | `{{$env.GATEWAY_BASE_URL}}/api/events/privacy` | Not implemented in gateway router. | Add endpoint or remap to `/api/events/pipeline`. |
| Agent9 `HTTP: gateway.metrics` | `http://10.0.4.140:9100/metrics` | Depends on external metrics exporter; gateway app itself exposes `/metrics` on API port. | Confirm infra exporter; otherwise change to `http://10.0.4.140:8000/metrics`. |

## Additional runtime mismatches found
| Area | Current JSON behavior | Code/policy expectation | Action |
|---|---|---|---|
| Deployment engine filename | Uses `emotion_resnet50.engine` in Agent 7 code node. | AGENTS policy expects EfficientNet engine naming (`emotion_efficientnet.engine`). | Update node command/path constants. |
| Privacy TTL | SQL purges records older than `14 days`. | AGENTS guidance references a 7-day temp retention default (policy-driven). | Move TTL to env/config and document default clearly. |
| Observability trigger node | Uses legacy `Cron` node (`n8n-nodes-base.cron`). | New docs emphasize `Schedule Trigger` as standard. | Migrate when workflow is next revised. |

## Files used for verification
- `apps/api/app/main.py`
- `apps/api/app/routers/ingest.py`
- `apps/api/app/routers/media_v1.py`
- `apps/api/app/routers/gateway_upstream.py`
- `apps/api/app/routers/promote.py`
- `apps/api/app/services/promote_service.py`
- `apps/api/routers/media.py`
- `apps/api/routers/gateway.py`
- `apps/gateway/main.py`
- `n8n/workflows/ml-agentic-ai_v.2/*.json`
