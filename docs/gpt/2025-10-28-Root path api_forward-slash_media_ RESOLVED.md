**2025-10-28-Root path api_forward-slash_media\_ RESOLVED**

**Root path api/media - resolved**

\[MEMORY BANK: ACTIVE\]

**Findings**

• **Gateway app root path**

• In apps/api/main.py, we instantiate FastAPI with no root_path. When
you start

Uvicorn with \--root-path /api/media, Uvicorn passes that value to the
ASGI scope at

runtime. That's why requests must include /api/media even though the
code

doesn't mention it.

• **Media Mover app root path**

In /media/rusty_admin/project_data/reachy_emotion/apps/api/app/main.py,
FastAPI(\..., root_path=settings.api_root_path) sets the root in code,
typically via .env (e.g., API_ROOT_PATH=/api/media). No CLI flag is
needed there.

**Recommended Cleanup**

• **Define root path in code (gateway)**

Edit apps/api/main.py to read an env var (e.g., API_ROOT_PATH, default
\"\") and pass it to FastAPI(root_path=\...).

import os def create_app() -\> FastAPI: root =
os.getenv(\"API_ROOT_PATH\", \"\") app = FastAPI(title=\"Reachy Gateway
API\", version=\"0.08.3.3\", root_path=root)
app.include_router(gateway.router) app.include_router(media.router)
return app

• **Standardize router prefixes**

In apps/api/routers/media.py, set router = APIRouter(prefix=\"/media\")
(or /videos, depending on desired structure). Then define routes as
\@router.get(\"/videos/list\"), etc. Final URL = root_path + router
prefix + route.

• **Simplify Uvicorn invocation**

Once the app sets its own root path, run:

export API_ROOT_PATH=/api/media \# or \"\" if you want root-less in dev
uvicorn \--app-dir /home/rusty_admin/projects/reachy_08.4.2
apps.api.main:app \--reload - -port 8081

No \--root-path flag needed; URL is clean (/api/media/videos/list if
using the prefix above).

This removes the double /api confusion and keeps gateway and Media Mover
configurations consistent. Let me know if you want me to apply these
changes.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--
\--

Follow-up

\[MEMORY BANK: ACTIVE\]

**Purpose of the Shared API_ROOT_PATH Setting**

• **\[Unified control\]** By reading API_ROOT_PATH from .env in both
services

(apps/api/main.py for the gateway and /media/\.../apps/api/app/main.py
for Media

Mover), you control the public base path once, without rewriting code or
adjusting

command-line flags.

• **\[Deployment parity\]** When .env sets API_ROOT_PATH=/api/media,
both services

expect requests under /api/media/\..., matching the Nginx location and
your existing

Media Mover deployment. If you change the reverse proxy prefix later,
updating .env

keeps both services aligned.

**Where Routes Are Defined**

• **Gateway** routes remain in the Windsurf project
(apps/api/routers/gateway.py,

apps/api/routers/media.py). These files define paths like
\"/api/videos/list\". The

root_path from .env is just prepended at runtime; no route definitions
move into the

Uvicorn command.

• **Media Mover** routes stay in /media/\.../apps/api/app/routers/\*.py
and already

inherit the same root_path.

**Uvicorn Configuration vs. Project Code**

• **Uvicorn command**: no longer needs \--root-path. It simply starts
the app with \--envfile \... so the .env values (including
API_ROOT_PATH) are loaded. Example:

export API_ROOT_PATH=/api/media \# or rely on \--env-file

UPDATED UVICORN COMMAND WITH ABSOLUTE PATH

uvicorn \--app-dir /home/rusty_admin/projects/reachy_08.4.2
apps.api.main:app \--reload \--port 8081 \--env-file apps/api/.env

• **Project code**: picks up API_ROOT_PATH through os.getenv and sets
FastAPI(\...,

root_path=\...). Actual endpoints remain declared in the router modules.

Summary: Using the shared .env root path keeps gateway and Media Mover
in sync without changing how routes are coded. The configuration lives
in the environment; the routes stay in their respective FastAPI modules.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--
-

Prompt Take a step back and explain the purpose of API_ROOT_PATH in the
.env environment file used by both services.

Also explain why are there routes in the Windsurf project (e.g. in
apps/api/routers/gateway.py) and in the uvicorn configuration (in
/media/rusty_admin/project_data/reachy_emotion/apps/api/app/main.py).

Response:

\[MEMORY BANK: ACTIVE\]

**Findings**

• **API_ROOT_PATH purpose**

o **\[shared config\]** Stored in .env (e.g., API_ROOT_PATH=/api/media)
so both

FastAPI apps (web gateway & uvicorn) know the external URL prefix that

Nginx (or another proxy) uses.

o **\[runtime effect\]** Each app reads it (FastAPI(\...,

root_path=API_ROOT_PATH)), so every generated URL (OpenAPI docs,

redirects, static links) includes /api/media/\....

o **\[flexibility\]** If the proxy path changes later, update the .env
once and both

services adjust without code edits.

• **Why routes exist in both codebases**

o **Gateway (/home/\.../apps/api/routers/\*.py)**

▪ Defines proxy/compatibility endpoints (/api/events/emotion,

/api/relabel, /api/videos/list, etc.).

▪ Sits in front of Media Mover to enforce headers (X-API-Version,

Idempotency-Key) and provide backward-compatible aliases.

o **Media Mover (/media/\.../apps/api/app/routers/\*.py)**

▪ Implements the actual ingest, promotion, listing, stats, and health

logic that manipulates files/DB on Ubuntu 1.

o **Reason for duplication**

▪ The gateway routes act as a façade and forward to the Media Mover

routes. This separation lets you evolve client-facing contracts without

touching the underlying media mover implementation and enables

different deployment locations (gateway on Ubuntu 2, Media Mover

on Ubuntu 1).

Summary: API_ROOT_PATH keeps URL prefixes consistent across services,
while having routes in both the gateway and Media Mover preserves the
proxy pattern---gateway for exposure and policy, Media Mover for core
functionality.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--

Prompt:

Is it correct to say that by exposing the API root path (Ubuntu 1) to
the web gateway (Ubuntu 2) the web app can access to the underlying
mechanics required to transmit data (videos and metadata) back and
forth?

Replay:

\[MEMORY BANK: ACTIVE\]

**Findings**

• **API exposure**: Setting API_ROOT_PATH=/api/media in both services
ensures the

gateway on Ubuntu 2 forwards requests to the Media Mover on Ubuntu 1
using the

same public prefix.

• **Data flow**: Client (web app) → Gateway
(apps/api/routers/gateway.py) → Media

Mover (/media/\.../apps/api/app/routers/\*). The gateway adapts
requests, enforces

headers, and proxies files/metadata operations back to the Media Mover.

• **Result**: Yes---the shared root path lets the web framework on
Ubuntu 2 reach the

underlying Media Mover mechanics (video and metadata operations) on
Ubuntu 1

while keeping routing consistent and auditable.

**Completion Status**

• Clarified that exposing the shared root path allows the web app via
the gateway to

access the Media Mover's functionality across the two hosts.
