**2025-11-03_Current Status and Next Steps\_**

**2025-11-03_Current Status and Next Steps\_ Reachy_Local_08.4.2**

\[MEMORY BANK: ACTIVE\]

**Current status -- Reachy_Local_08.4.2**

• Promotion system Steps 1--3 are fully landed: persistence model +
migrations,

repository/service logic, and filesystem movers with rollback all pass
the async

pytest suite, giving reliable temp→dataset_all staging and
dataset_all→train/test

sampling flows.@docs/gpt/2025-11-01-Promotion_System_Summary_of_steps_1-

3.txt#5-66

• FastAPI surface is hardened with Pydantic request/response models,
router prefix

fixes, and updated 422 handling; ASGI tests now hit

/api/media/promote/{stage\|sample} successfully.@docs/gpt/2025-11-02-

Promotion_API_surface_layer.txt#9-126

• Live promotion pipeline on Ubuntu 1 was restored by aligning
PostgreSQL 16 service

management, permissions, DSN settings, and UUID↔VARCHAR casting;

stage/sample endpoints now return HTTP 202
end‑to‑end.@docs/gpt/2025-11-02-

Postgres_and_Promotion_Challenges_and_Resolutions.txt#3-36
\@docs/gpt/2025-

11-02-Summarizing_the_Restoration_of_the_live_promotion_pipeline\_.pdf#1-15

• Repository helper layer and PromoteService now share typed errors,
logging, and

idempotent sampling behavior, giving clean separation for future
observability

hooks.@docs/gpt/2025-11-02-

Adding_repository_helper_layer_around_PromoteService.txt#1-263

• Documentation index reflects the new November 1--2 deliverables,
keeping

historical traceability for promotion and Postgres
work.@docs/gpt/INDEX.md#1-

128

**Next steps -- backend services on Ubuntu 1**

1\. Finish Step 4 deliverables: deploy the new Pydantic schemas/routers
to the running

service, confirm OpenAPI + curl smoke tests on the production tree, and
capture

regression tests for live UVicorn runs.

\@docs/gpt/2025-11-01-Promotion_System_Summary_of_steps_1-3.txt #67-80

\@docs/gpt/2025-11-02-Promotion_API_surface_layer.txt #105-126

2\. Implement observability/metrics (Step 5): wire promotion counters
and filesystem

transition logs into Prometheus-compatible exporters, ensuring
correlation IDs

propagate through service logs.@docs/gpt/2025-11-01-

Promotion_System_Summary_of_steps_1-3.txt#73-76

3\. Complete Step 6 integration: honor dry-run semantics, add httpx
end‑to‑end tests

that cover Postgres + filesystem effects, and prep manifest
rebuild/reset hooks for

training orchestration. \@docs/gpt/2025-11-01-

Promotion_System_Summary_of_steps_1-3.txt#77-81

4\. Operational polish: document filesystem permissions/rollbacks in
memory-bank

runbooks and plan cleanup jobs for per-run train/test copies, keeping
Ubuntu 1's

storage predictable.@docs/gpt/2025-11-01-

Promotion_System_Summary_of_steps_1-3.txt#82-85

5\. Monitor PostgreSQL long-term: maintain the postgresql@16-main
service, ensure

async drivers remain installed in the deployment venv, and periodically
validate role

privileges to avoid recurrence.@docs/gpt/2025-11-02-

Postgres_and_Promotion_Challenges_and_Resolutions.txt#3-36
