**2025-11-03-Step 4 Progress report for deliverables**

**Progress report** for Finish Step 4 deliverables: deploy the new
Pydantic schemas/routers to the running service, confirm OpenAPI + curl
smoke tests on the production tree, and capture regression tests for
live UVicorn runs.
\@docs/gpt/2025-11-01-Promotion_System_Summary_of_steps_1-3.txt #67-80
\@docs/gpt/2025-11-02-Promotion_API_surface_layer.txt #105-126

\[MEMORY BANK: ACTIVE\] Step 4 deliverables are confirmed end-to-end:
the production tree already matches the updated router/schemas, OpenAPI
on the running Uvicorn service now advertises
/api/media/promote/{stage,sample} via root_path, local smoke tests
return HTTP 202 with the new contracts, and pytest
tests/apps/api/routers/test_promote_router.py -q passes to lock in
regression coverage.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- -
