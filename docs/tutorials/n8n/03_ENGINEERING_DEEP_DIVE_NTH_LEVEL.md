# Reachy Agentic AI System — Deep Engineering Guide (Nth-Level)

## Purpose of this document
This guide summarizes the Nth-level materials (located in `docs/tutorials/n8n/v3_Codex/Nth_level`) for engineers implementing and modifying runtime behavior.

Rusty, this version is intentionally code-centric: it explains node logic, control flow, contracts, and backend side effects.

## What Nth-level means in this project
Nth-level docs map each workflow node to:
- The exact backend router/service/script it triggers
- The key function(s) that execute business logic
- Data contracts moving between n8n and Python/FastAPI layers
- Observable side effects (filesystem, DB rows, events, SSH operations)

In practice, these docs are the bridge between "canvas wiring" and "what code actually does."

## Engineering mental model (read this before editing any node)
For every n8n node change, validate four layers in order:
1. **Input contract layer**: what `$json` shape this node expects
2. **Expression/syntax layer**: whether references (`$node[...]`, `$json.field`, `$env.VAR`) still resolve
3. **Backend binding layer**: which endpoint/function/script executes and with which payload
4. **State mutation layer**: DB/filesystem/event side effects and rollback behavior

If any one layer is wrong, the workflow can look green in n8n but still violate system policy.

## Deep control-flow by engineering domain
### 1) Ingest + Label + Promotion domain
- Ingest normalizes multi-shape payloads, enforces header auth, and submits to canonical ingest API.
- Labeling persists audit-grade label events before optional relabel/promote actions.
- Promotion runs a two-phase process: dry-run plan -> human approval -> real mutation -> manifest rebuild.

**Engineering invariant:** promotion and ingest paths must preserve `correlation_id` and idempotency semantics end-to-end.

### 2) Data integrity + privacy domain
- Reconciler computes FS-vs-DB deltas (orphans/missing/mismatches) and emits operator-facing outputs.
- Privacy agent applies TTL logic, performs deletion actions, updates DB state, and records audit trails.

**Engineering invariant:** deletion and reconciliation flows must remain auditable and deterministic (no hidden best-effort behavior).

### 3) ML lifecycle domain
- Training orchestrator gates run start by class-balance threshold checks, then launches remote pipeline via SSH.
- Evaluation agent gates by test-balance and executes `--skip-train` style evaluation flow.
- Deployment agent performs ONNX -> TensorRT deployment procedure, verifies runtime constraints, and triggers rollback on failure.

**Engineering invariant:** Gate A/B outcomes must come from measured metrics, not inferred status flags.

### 4) Telemetry domain
- Observability agent polls metrics endpoints, parses Prometheus text exposition, and stores normalized rows.

**Engineering invariant:** parser code must tolerate missing metrics without breaking storage for available metrics.

## Syntax and expression pitfalls to watch
When editing `Code` and `If` logic:
- Keep node names stable, because expressions often reference names literally.
- Prefer explicit null-safe access (`$json?.field` patterns in JS code node logic where available) and defensive checks.
- Fail fast for required fields (for example, missing `source_url`) to avoid downstream silent corruption.
- Keep HTTP method explicit in all `HTTP Request` nodes.
- Ensure branch logic includes both success and rejection/failure responses.

## Minimum engineering review checklist (before merge)
- Workflow JSON diff reviewed alongside matching Nth-level module.
- Endpoint path and payload verified against active FastAPI router model.
- DB-write nodes checked for policy constraints (split/label, audit log coverage).
- SSH command nodes verified for idempotent and rollback-safe behavior.
- Event payloads include identifiers needed for traceability (`correlation_id`, run IDs, video IDs).

## Suggested implementation workflow for engineers
1. Open workflow JSON and corresponding Nth-level module side-by-side.
2. Trace one complete path (happy path) from trigger to response/event.
3. Trace at least one failure/reject path.
4. Run smoke test with representative payload.
5. Confirm mutated state in DB/filesystem/metrics tables.
6. Update step-by-step doc if any node config changed.

## One-sentence engineering takeaway
The Nth-level guides are the authoritative runtime map: they let you reason from n8n node syntax to Python execution paths and real side effects without guessing.
