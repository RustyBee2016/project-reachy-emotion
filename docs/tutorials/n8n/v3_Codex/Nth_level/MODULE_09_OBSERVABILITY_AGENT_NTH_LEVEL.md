# MODULE 09 — Observability / Telemetry Agent (Nth-Level)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/09_observability_agent.json`

## Runtime Goal
Poll metrics endpoints, parse selected Prometheus values, and store normalized time-series samples.

## Node-to-Script Map

### 1) `Cron: every 30s` (`Cron`)
- **Workflow role:** periodic collection trigger.
- **Configured interval:** every 30 seconds.

### 2) `HTTP: n8n.metrics` (`HTTP Request`)
- **Workflow role:** fetches n8n Prometheus text from `http://n8n:5678/metrics`.

### 3) `HTTP: mediamover.metrics` (`HTTP Request`)
- **Workflow role:** fetches media mover metrics text from `http://10.0.4.130:9101/metrics`.
- **Related metric definitions:** `apps/api/app/metrics.py` and registry in `apps/api/app/metrics_registry.py`.

### 4) `HTTP: gateway.metrics` (`HTTP Request`)
- **Workflow role:** fetches gateway metrics text from `{{$env.GATEWAY_BASE_URL}}/metrics`.
- **Backend binding:** `apps/api/routers/gateway.py:159` `metrics()` returns `prometheus_client.generate_latest(get_registry())`.

### 5) `Code: parse.metrics` (`Code`)
- **Workflow role:** parses Prometheus text via regex into structured rows.
- **Essential in-node logic:**
- helper `parseMetric(text, name)` regex extraction
- emits items:
- `src=n8n`, `metric=active_executions`
- `src=media_mover`, `metric=promote_total`
- `src=gateway`, `metric=queue_depth`
- drops null values

### 6) `Postgres: store.metrics` (`Postgres`)
- **Workflow role:** inserts parsed metric items into `obs_samples`.
- **Table binding:** `ObsSample` model (`apps/api/app/db/models.py:371`).

## How This Delivers Observability Functionality
1. Polls all three services on a fixed cadence.
2. Converts raw Prometheus exposition into normalized `(ts, src, metric, value)` rows.
3. Persists rows for dashboarding and alert queries.

## Metrics Alignment Notes
- Workflow parser expects `media_mover_promote_total`, while current media-mover metric name in code is `promotion_operations_total` (`apps/api/app/metrics.py:12`).
- Gateway queue depth metric name expected by workflow is `gateway_queue_depth`; ensure gateway registry exports this exact sample if you want non-null inserts.
