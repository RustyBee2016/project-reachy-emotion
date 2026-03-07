# Reconciler / Audit Agent (v3_Codex)

**Workflow JSON:** `n8n/workflows/ml-agentic-ai_v.3/04_reconciler_agent.json`

## Objective
Detect filesystem/DB drift and notify maintainers when media inventory diverges.

## Related Backend Scripts and Functionalities
- `apps/api/app/db/models.py`: `video` table is the canonical DB inventory compared against filesystem scan.
- `n8n/workflows/ml-agentic-ai_v.3/04_reconciler_agent.json`: SSH/Code/Postgres logic performs reconciliation in workflow runtime.

## What Changed vs Legacy Module
- Filesystem scan command narrowed to `/videos/{temp,train,test}` to avoid failures when `dataset_all` is absent.
- Fixed `Code: diff.fs_db` references to actual node names (`Code: parse.fs_scan`, `Postgres: fetch.all_videos`).
- Preserved dual-trigger model: daily cron + manual webhook trigger.
- Retained alerting via `Send Email` when drift summary indicates mismatch.
- No endpoint-contract change needed for this workflow.

## Node-by-Node (Official n8n Node Types)
| Workflow Node | Official n8n Node | Functionality |
|---|---|---|
| `Schedule: daily 02:15` | `Schedule Trigger` | `Schedule Trigger` executes daily reconciliation job. |
| `Webhook: manual.trigger` | `Webhook` | `Webhook` allows ad-hoc reconciliation runs. |
| `Set: config` | `Set (Edit Fields)` | `Set` (Edit Fields) stores runtime knobs for scan behavior. |
| `SSH: scan.filesystem` | `SSH` | `SSH` node emits JSONL filesystem inventory. |
| `Code: parse.fs_scan` | `Code` | `Code` parser converting raw stdout lines to structured items. |
| `Postgres: fetch.all_videos` | `Postgres` | `Postgres` query for full video inventory. |
| `Code: diff.fs_db` | `Code` | `Code` diff engine computing orphan/missing/mismatch sets. |
| `IF: drift.found?` | `If` | `If` gate for alert/no-alert path. |
| `Email: send.report` | `Send Email` | `Send Email` node dispatching drift summary. |

## How This Workflow Delivers Code-Level Functionality
1. SSH scan enumerates actual media files and emits machine-parseable JSON lines.
2. DB inventory query provides canonical metadata baseline for comparison.
3. Diff code computes orphan/missing/mismatch sets that expose data drift impacting training quality.
4. Drift gate avoids noisy alerts when filesystem and DB are already consistent.
5. Email report provides actionable reconciliation summary for maintainers.

## Notes
- This module reflects the v3 workflow JSON and active backend endpoint contracts as of 2026-03-07.
- Legacy module files in `docs/tutorials/n8n/` are preserved unchanged; this file is the updated equivalent for v3_Codex.
