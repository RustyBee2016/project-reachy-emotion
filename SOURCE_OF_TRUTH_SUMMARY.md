# Source of Truth Summary for Reachy_Local_08.4.2

Rusty, this guide explains **how constraints and contracts shape system design** so the web app, gateway, database, and ML pipeline stay aligned.

---

## Why this matters

In multi-component systems (UI + API + DB + filesystem + training code), most failures happen when one layer changes names, assumptions, or validation rules without the others.

The practical fix is to define explicit **sources of truth** and then force every layer to conform.

For this project, treat these as primary:

1. Database schema + constraints
2. API request/response contracts
3. Filesystem layout contract
4. Tests that verify alignment

---

## 1) Database schema + constraints (truth for persisted state)

### What this means in general

The database defines what data is valid over time. If a value violates a constraint, the write should fail immediately.

You should rely on DB constraints for invariants that must never be broken, even if API/app code has bugs.

### How it affects design

- Your Python code should **prepare** valid data, but DB constraints should **enforce** validity.
- If the API and DB disagree, DB should reject the write and emit a clear error path.
- Naming and allowed values (enums/check constraints) should be treated as canonical dictionary terms.

### Reachy-specific examples

- `video` table has split/label policy (e.g., train requires non-null label; test/temp/purged require null label).
- `promotion_log` captures auditable transitions and idempotency keys.
- Uniqueness constraints (e.g., hash + size) prevent silent duplicate records.

### Developer workflow for Rusty

1. Add/modify schema with migration first.
2. Reflect changes in SQLAlchemy models.
3. Update repository/service code.
4. Update API schemas.
5. Update tests for expected pass/fail cases.

---

## 2) API request/response contracts (truth for service boundaries)

### What this means in general

A contract is the set of allowed fields, required fields, types, enums, defaults, and error envelopes.

When two services talk (web app -> gateway -> media mover), contracts are your compile-time-like guardrails for runtime communication.

### How it affects design

- Endpoints should validate input at boundary entry.
- Contract versioning should be explicit.
- Idempotency and correlation IDs should be mandatory for write operations in distributed flows.
- Error payloads should be structured and machine-parseable.

### Reachy-specific examples

- Promotion endpoint requires stable payload shape and enforces valid target split and class labels.
- Gateway requires `Idempotency-Key` for promotion proxy writes.
- Compatibility endpoints can exist, but active runtime contract must be clearly marked and documented.

### Developer workflow for Rusty

1. Define contract in Pydantic/OpenAPI (or equivalent schema).
2. Validate request on entry.
3. Keep one canonical response envelope for success/error.
4. Add integration tests for both valid and invalid payloads.
5. Mark deprecated endpoints as compatibility-only and test migration paths.

---

## 3) Filesystem layout contract (truth for artifact location)

### What this means in general

In ML/data pipelines, paths are part of the contract. If one component writes to a different directory than downstream expects, training silently breaks.

### How it affects design

- Directory names and run naming (`run_0001`, etc.) must be explicit and stable.
- Promotion, frame extraction, manifest generation, and training loaders should use shared path constants, not duplicated string literals.
- Path transitions should be modeled as a state machine (temp -> train/test -> run artifacts).

### Reachy-specific examples

- Promotion moves clips into class-specific train folders.
- Frame extraction samples fixed number of frames per source video.
- Run-scoped datasets and manifests should be deterministic and auditable.

### Developer workflow for Rusty

1. Document directory grammar in one markdown contract file.
2. Centralize path construction helpers in code.
3. Avoid hand-built path strings in UI or gateway handlers.
4. Validate path existence + permissions at startup/health checks.
5. Include path contract checks in CI tests.

---

## 4) Tests that assert all three stay aligned (truth for regression prevention)

### What this means in general

Tests are the executable proof that DB constraints, API contracts, and filesystem contracts agree.

Without these tests, drift reappears after any refactor.

### How it affects design

- Unit tests confirm local logic.
- Integration tests confirm cross-layer behavior.
- End-to-end tests confirm state transitions and side effects.
- Negative tests (invalid payloads, constraint violations, missing files) are as important as happy path tests.

### Reachy-specific examples

- Tests that promotion updates both file location and DB split/label state.
- Tests that frame extraction creates expected count (10/frame per video) and manifests.
- Tests that idempotent retries do not duplicate promotion or frame records.

### Developer workflow for Rusty

1. Write tests from contract requirements, not just implementation details.
2. Add one failing test when bug is discovered.
3. Fix code and keep the test as permanent regression guard.
4. Require green tests before merging schema/contract changes.

---

## Putting it together: system design control flow

Use this design sequence whenever you add a new pipeline step:

1. **State model first (DB):**
   - What entities exist?
   - What transitions are valid?
   - What must be impossible?
2. **Boundary contract second (API):**
   - What request triggers transition?
   - What fields are required?
   - How do retries behave?
3. **Artifact contract third (filesystem):**
   - Where do files move?
   - How are run IDs generated?
   - What outputs are consumed downstream?
4. **Executable checks fourth (tests):**
   - Positive + negative + idempotency + reconciliation tests.

If all four are updated together in one change set, the pipeline remains coherent.

---

## Practical checklist for future pipeline steps

Before implementing a new step (like frame sampling), verify:

- [ ] DB tables/constraints exist for required state and audit trail.
- [ ] API payload and response schemas are documented and validated.
- [ ] Filesystem paths and naming are documented and centralized in code.
- [ ] Tests cover happy path, validation failures, retries, and reconciliation.
- [ ] Deprecated behavior is explicitly marked and not used for new clients.

---

## Closing guidance

Rusty, the goal is to stop treating constraints/contracts as "extra overhead" and instead treat them as **design tools**:

- Constraints prevent invalid states.
- Contracts prevent communication ambiguity.
- Filesystem layout prevents data pipeline drift.
- Tests prevent regressions.

When those four are aligned, development gets simpler, debugging gets faster, and promotions/training become repeatable.
