**2025-10-28-Backend completion plan_01**

**Backend completion plan**

Part 1

\[MEMORY BANK: ACTIVE\]

**Findings**

• **Backend gap**: src/media_mover/main.py only stubs
/api/media/promote,

/api/promote, /api/media, and /health, leaving Ubuntu 1 responsibilities
(list,

metadata, thumbnails, relabel, manifest rebuild, ingress/label helpers)

unimplemented. Cited from src/media_mover/main.py.

• **Gateway contract**: apps/api/routers/gateway.py already proxies to
Ubuntu 1

routes like /api/videos/{video_id}, /api/relabel, and
/api/manifest/rebuild; without

real handlers these calls will fail. Cited from
apps/api/routers/gateway.py.

• **Requirements alignment**: Specs in
memory-bank/requirements_08.4.2.md §§14--

16 mandate filesystem-backed promotions, manifests, logging, and
dryrun/idempotency semantics on Ubuntu 1.

**Plan**

• **Filesystem & config setup**: Add env-driven root (MEDIA_VIDEOS_ROOT)
plus

helper utilities (path validation, idempotency store, checksum helpers).

• **Data layer**: Implement lightweight file/metadata helpers;
optionally wire

SQLAlchemy models if DATABASE_URL provided, otherwise degrade gracefully

while flagging TODO.

• **Endpoint suite**:

o /api/media/ingest (metadata registration + optional checksum
validation).

o /api/videos/list and /api/media/videos/list (paged filesystem
listing).

o /api/videos/{video_id} and /api/videos/{video_id}/thumb (metadata +

file/redirect).

o /api/media/promote (adapter + dry-run + atomic move + optional DB
update

\+ audit log).

o /api/relabel (update label, enforce test split rules).

o /api/manifest/rebuild (generate JSONL manifests with dataset hash).

o /api/media/promotions/logs & /api/media health/status.

• **Observability**: Emit structured logs for every mutate path,
including correlation IDs,

as required in requirements_08.4.2.md §18.

• **Tests & wiring**: Extend unit tests (new module under tests/) to
exercise

list/promote/dry-run/manifest endpoints; ensure gateway tests can target
inprocess backend by pointing MEDIA_MOVER_URL to http://testserver.

• **Documentation**: Update README.md and relevant docs to explain
Ubuntu 1

service run command, env vars, manifests output.

**Next Steps**

• **Confirm** the above scope matches your expectations for Ubuntu 1's
media-mover.

Once confirmed, I'll begin implementing the service (helpers +
endpoints) and

associated tests.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--
-

Part 2

continue now that Media Mover is reachable by the Web gateway (Windsurf)

\[MEMORY BANK: ACTIVE\]

**Findings**

• **\[env alignment\]** .env now points DATABASE_URL to reachy_emotion,
matching the

populated tables (video, run_link) you inspected.

• **\[service launch\]** Uvicorn boots successfully with:uvicorn
\--app-dir

/media/rusty_admin/project_data/reachy_emotion \\

apps.api.app.main:app \\

\--reload \--port 8081 \\

\--env-file /media/rusty_admin/project_data/reachy_emotion/apps/api/.env

•

so the Media Mover API can run from any directory.

**Progress**

• Media Mover app (apps/api/app/main.py) is reachable and router imports
resolve

correctly at runtime.

• Backend endpoints remain mostly stubs (routers/promote.py,
routers/videos.py,

etc.), so the next work item is implementing full filesystem/DB logic
plus services.

**Next Steps**

• **Implement** real handlers (listing, promotion, relabel, manifests)
and supporting

services/models under apps/api/app/ using the already-configured
SQLAlchemy

session (get_session()).

• **Add** unit/integration tests to cover the Media Mover API workflows.

• **Document** verification commands (curl/httpx, pytest) once
functionality lands.

Feel free to call out which feature (promote, list, relabel, manifests,
ingest) you want me to tackle first, and I'll dive in.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- -

Status update after Codex extensive updates

\[MEMORY BANK: ACTIVE\]

**Findings**

• **apps/api/app/services/media_paths.py** now provides VideoFile,
list_split(),

find_video(), and related helpers for filesystem metadata.

• **apps/api/app/routers/videos.py** replaced stubs with real listing
endpoints

returning pagination plus video detail.

• **apps/api/app/routers/health.py** exposes richer diagnostics: env,
disk usage, persplit stats, and /health/db for DB connectivity.

All edits use absolute imports (apps.api.app.\*). Runtime uvicorn import
works because the project root is added via \--app-dir.

**Outstanding**

• Pyright still flags unresolved imports (e.g., apps.api.app.deps) since
that tool isn't

aware of the runtime PYTHONPATH. Either configure pyright (e.g., add
extraPaths in

pyproject.toml or .venv/lib/python3.12/site-packages/pyrightconfig.json)
or ignore

those diagnostics.

• Unit tests not yet written; pytest command failed earlier due to
missing PATH in

shell, but it's installed per your note.

• Core mutations (promotion, relabel, manifest rebuild) still pending.

**Next Steps**

• Confirm you're okay with handling/ignoring pyright import warnings.

• Decide whether to proceed with promotion/relabel endpoints or add
tests first.

Let me know which task to tackle next.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- -

Prompt:

update the path in the shell and the runtime PYTHONPATH to support
Pyright and PyTest. I want to pass all possible tests and ignore no
diagnostics.

Response:

\[MEMORY BANK: ACTIVE\]

**Findings**

• **Pyright config** now includes

extraPaths=\[\"/media/rusty_admin/project_data/reachy_emotion\"\] in

pyproject.toml, so imports like apps.api.app.deps resolve without
suppressing

diagnostics.

• **Package init**: added apps/api/app/**init**.py exporting app,
enabling both runtime

uvicorn apps.api.app:app and tooling imports.

• **Absolute imports** in apps/api/app/main.py, routers/videos.py,
routers/health.py,

and services/media_paths.py continue to work; lint should now succeed
once

Pyright reloads.

**Recommended Actions**

• **Reload editor tooling** (Pyright, pylance) so the updated
pyproject.toml takes effect.

If necessary, run pyright from the repo root to confirm clean
diagnostics.

• **Set runtime PYTHONPATH** for pytest:export

PYTHONPATH=/media/rusty_admin/project_data/reachy_emotion:\$PYTHONPATH

\# or add to shell profile if preferred

This ensures pytest can import the Media Mover modules until we add
packaging

metadata.

**Next Steps**

• Proceed with implementing the next backend feature (e.g., promotion
workflow) or

start authoring tests, now that lint/test tooling is aligned.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--

**Codex - feedback after MAJOR updates (2)**

\[MEMORY BANK: ACTIVE\]

**Findings**

• Implemented filesystem utilities in
apps/api/app/services/media_paths.py and rewrote

apps/api/app/routers/videos.py for real listing/detail responses.

• Enhanced /health endpoint in apps/api/app/routers/health.py with disk
stats, split

metadata, and DB connectivity check.

• Added apps/api/app/services/promote_service.py with PromotionPlan,
dry-run support,

filesystem moves, and DB updates; promotion router still needs to call
this service.

• Updated tooling: apps/api/app/**init**.py exposes app, and
pyproject.toml now includes

extraPaths so Pyright/Pytest resolve modules under

/media/rusty_admin/project_data/reachy_emotion.

**Recommended Actions**

• Wire apps/api/app/routers/promote.py to the new
promote_service.promote() and add

endpoints for relabel/manifest workflows.

• Implement corresponding tests (health/videos/promote) once API
surfaces are finalized.

Let me know when you're ready for the promotion router wiring or if
you'd like tests added next.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- \--

Discussion of the recent findings and recommended actions.

\[MEMORY BANK: ACTIVE\]

**Postgres setup progress**

• The .env used by Uvicorn now targets the live database reachy_emotion
via the Unix socket

DSN
postgresql+psycopg://reachy_dev:...@/reachy_emotion?host=/var/run/postgresql,
so

the service connects with the scoped **reachy_dev** account rather than
a superuser

(@apps/api/.env#9-13).

• PostgreSQL cluster 16/main was brought online after fixing directory
ownership (chown

postgres:postgres) and tightening permissions, confirming that both
legacy

(reachy_emotion) and empty (reachy_local) databases are reachable. With
the server

running, psql enumerations verified the expected video and run_link
tables under

reachy_emotion.

**Updated Python modules**

1\. apps/api/app/services/media_paths.py: Introduced reusable helpers
for filesystem

operations---validating splits, enumerating media files, computing
per-split statistics, and

producing response-ready metadata objects
(@apps/api/app/services/media_paths.py#1-

115).

2\. apps/api/app/routers/videos.py: Replaced stub handlers with real
endpoints that paginate

videos/list responses using the new service and expose per-video detail
including URLs

and ISO timestamps (@apps/api/app/routers/videos.py#1-53).

3\. apps/api/app/routers/health.py: Expanded health reporting to include
environment, disk

usage, split summaries, and an explicit /health/db probe that executes a
lightweight query

through the shared session dependency
(@apps/api/app/routers/health.py#1-48).

4\. apps/api/app/services/promote_service.py: Implemented the promotion
workflow. Key

constructs include:

a\. PromotionPlan: a dataclass that captures source/destination paths,
current/destination

splits, label overrides, and whether a conflicting file already exists

(@apps/api/app/services/promote_service.py#16-71).

b\. build_plan(): resolves the current video location and verifies
destination rules before

formulating the move (@apps/api/app/services/promote_service.py#38-71).

c\. apply_plan(): executes dry runs or real promotions, handling
filesystem moves, upserting

metadata, and recording outcomes while guarding against conflicts

(@apps/api/app/services/promote_service.py#74-161).

d\. promote(): convenience wrapper tying plan creation and execution
together

(@apps/api/app/services/promote_service.py#164-173).

This structure supports idempotency (noop when already in the target
split), optional label updates, and detailed response payloads.

**Promotion plan & related concepts**

• *Inputs*: video_id, destination split (train/test), optional label,
and a dry-run flag.

• *Planning phase*: build_plan() ensures the video exists, validates the
target split, prepares

destination directories, and records any pre-existing destination files.

• *Execution phase*: apply_plan() either describes the intended action
(dry run) or performs it:

moving the file, ensuring directories exist, and synchronizing the video
table via

UPDATE/UPSERT semantics with fresh timestamps and sizes.

• *Safety mechanisms*: prevents overwriting existing files unless
explicitly allowed (dry run

reveals conflicts) and keeps operations idempotent when a video already
resides in the

target split.

**Recommended actions, implementation path, and effects**

1\. **Wire apps/api/app/routers/promote.py to
promote_service.promote()**

a\. Implementation: inject Settings and DB session dependencies, parse
request payloads

(including dry-run & labels), call the service, and translate
PromotionError into structured

HTTP errors.

b\. Effect: enables the actual /api/media/promote endpoint to move media
between splits and

keep Postgres metadata accurate.

2\. **Add endpoints for relabel and manifest workflows**

a\. Implementation: extend routers (or create new modules) that leverage
similar service

patterns for updating labels or regenerating manifests/checksums.

b\. Effect: completes the Media Mover feature set expected by upstream
gateway routes and

operations runbooks.

3\. **Implement corresponding tests (health/videos/promote)**

a\. Implementation: use TestClient fixtures with temporary
directories/DB transactions,

covering happy paths and error cases (invalid split, missing files, DB
failures).

b\. Effect: regression coverage ensuring filesystem/database side
effects behave as expected

and future changes don't silently break core flows.

Once these actions are completed, the Media Mover backend will deliver
end-to-end promotion functionality with confidence-inspiring test
coverage and full observability via health diagnostics.
