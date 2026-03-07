# Observability / Telemetry Agent (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/09_observability_agent.json`

## Objective
Scrape service metrics, parse key indicators, and persist observability samples.

## Related Backend Scripts and Functionalities
- `apps/api/app/routers/metrics.py`: Media Mover exposes Prometheus at `/metrics`.
- `apps/api/routers/gateway.py`: Gateway exposes Prometheus at `/metrics` and stores event telemetry separately.
- `apps/api/app/metrics_registry.py`: Prometheus registry source for gateway metrics endpoint.

## What Changed vs Legacy Module
- Gateway metrics URL changed from hardcoded `:9100` exporter to `{{$env.GATEWAY_BASE_URL}}/metrics` endpoint exposed by gateway app.
- Updated metric parser references to actual node names (`HTTP: n8n.metrics`, etc.).
- Set explicit HTTP methods to `GET` for all scrape nodes.
- Kept parsing pattern for `active_executions`, `promote_total`, and `queue_depth` metrics.
- Retained DB sink (`obs_samples`) for long-term trend analysis and alerts.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Cron: every 30s` | `Cron` | `Cron` trigger for 30-second scrape interval. |
| `HTTP: n8n.metrics` | `HTTP Request` | `HTTP Request` scrape of n8n metrics endpoint. |
| `HTTP: mediamover.metrics` | `HTTP Request` | `HTTP Request` scrape of Media Mover metrics endpoint. |
| `HTTP: gateway.metrics` | `HTTP Request` | `HTTP Request` scrape of gateway `/metrics` endpoint. |
| `Code: parse.metrics` | `Code` | `Code` parser extracting selected Prometheus metrics. |
| `Postgres: store.metrics` | `Postgres` | `Postgres` insert of normalized metric samples. |

## How This Workflow Delivers Code-Level Functionality
1. Scrape nodes collect operational telemetry from n8n, Media Mover, and Gateway services.
2. Parser extracts key indicators into uniform records suitable for SQL storage and dashboarding.
3. Explicit gateway `/metrics` URL alignment removes dependency on external exporter-only port assumptions.
4. Postgres sink (`obs_samples`) creates a historical telemetry series for trend analysis and alerting.
5. Frequent cron interval supports near-real-time visibility for queue depth and execution pressure.

## Notes
- This module reflects the v3 workflow JSON and active backend endpoint contracts as of 2026-03-07.
- Legacy module files in `docs/tutorials/n8n/` are preserved unchanged; this file is the updated equivalent for v3_Codex.
