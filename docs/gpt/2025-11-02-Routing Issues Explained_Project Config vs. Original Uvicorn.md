**2025-11-02-Routing Issues Explained_Project Config vs. Original
Uvicorn**

\[MEMORY BANK: ACTIVE\]

Here's a recap of what changed and why the routes have been touchy:

• **Original layering** -- The FastAPI app has a configurable root_path
that defaults to

/api/media (@apps/api/app/settings.py#21-55,
\@apps/api/app/main.py#25-42).

Initially, the promotion router also declared its own prefix as
/api/media/promote,

so the effective public URL became /api/media/api/media/promote/\...,
which made

every request miss.

• **Fix we applied** -- We moved the router prefix to /promote and
renamed the

endpoints to /stage and /sample, letting FastAPI build the final path by
combining

root_path + router prefix + route path
(@apps/api/app/routers/promote.py#17-80).

That's why the unit tests now target /promote/\... inside the ASGI
client

(@tests/apps/api/routers/test_promote_router.py#25-218).

• **Impact when running uvicorn** -- If the service starts with the
default settings, the

real URL is still /api/media/promote/\.... The unit tests work because
their transport

injects root_path=\"/api/media\". Locally, you have two equivalent ways
to access

the endpoints:

o Keep MEDIA_MOVER_API_ROOT_PATH=/api/media and call

/api/media/promote/\....

o Export MEDIA_MOVER_API_ROOT_PATH=\"\" *before* uvicorn imports the
app,

so the live path is just /promote/\....

Because get_settings() is cached, changing the environment variable
after the module has been imported won't take effect until the
interpreter or server reload is complete. That's why we saw 404s even
after tweaking the env var mid-run.

**What to verify before hitting the endpoints again**

**1. Confirm the app's current root path**

Hit the OpenAPI document (safe, read-only) and glance for
/promote/stage:

curl http://localhost:8000/openapi.json \| jq \'.paths \| keys\'

If you see keys like \"/promote/stage\", the app is running with an
empty root path. If the keys include \"/api/media/promote/stage\", then
root_path is /api/media.

2\. **Match the curl URL to the observed root path**

a\. If the OpenAPI shows \"/promote/stage\", use:curl -X POST

http://localhost:8000/promote/stage \\

-H \"Content-Type: application/json\" \\

-d \'{\"video_ids\":\[\"550e8400-e29b-41d4-a716-

446655440000\"\],\"label\":\"happy\"}\'

b\. If it shows \"/api/media/promote/stage\", keep the prefix:curl -X
POST

http://localhost:8000/api/media/promote/stage \\

-H \"Content-Type: application/json\" \\

-d \'{\"video_ids\":\[\"550e8400-e29b-41d4-a716-

446655440000\"\],\"label\":\"happy\"}\'

3\. **Only after verifying OpenAPI** should we exercise the POST
endpoints. That way we

know which path should succeed and avoid more guesswork.

Let me know which route set the OpenAPI shows, and I can craft the exact
curl snippets (including sample payloads for both stage and sample)
tailored to that configuration.

============================== === **Prompt:** You wrote, remember
/home/rusty_admin/projects/reachy_08.4.2 refers to the project root, not
the uvicorn configuration.
/media/rusty_admin/project_data/reachy_emotion is the location of the
FastAPI/uvicorn app. This, I believe, is the source of the confusion.
**Response:**

\[MEMORY BANK: ACTIVE\]

Thanks for the clarification---now the behavior lines up:

• All of the code we've been editing (schemas, router prefix change, new
422

constant) lives under /home/rusty_admin/projects/reachy_08.4.2/\....

• The uvicorn process you're running serves an **older copy** of the app
from

/media/rusty_admin/project_data/reachy_emotion/\.... That tree still has
the original

router (prefix=\"/api/media\", routes defined as \"/promote/\...\"), so
FastAPI exposes

/api/media/promote/stage in the OpenAPI output and will never match

/promote/stage---hence the 404s.

To sanity-check, open
/media/rusty_admin/project_data/reachy_emotion/apps/api/app/routers/promote.py:
you'll see the older prefix. Until the deployment directory is updated,
the running service won't reflect the new endpoints.

You have two straightforward options:

1\. **Run uvicorn from the updated repo**

uvicorn \--app-dir /home/rusty_admin/projects/reachy_08.4.2 \\
apps.api.app.main:app \--reload \--port 8081 \\ \--env-file
/home/rusty_admin/projects/reachy_08.4.2/apps/api/.env

(Adjust \--env-file or environment variables as needed.) The OpenAPI doc
will then show \"/promote/stage\" and \"/promote/sample\", and the curl
commands on port 8081 will succeed without a prefix.

**2. Deploy the newer code to
/media/rusty_admin/project_data/reachy_emotion**

Copy the changed files (at minimum apps/api/app/routers/promote.py, plus
the new schemas) into that tree so the existing uvicorn command serves
the latest code. After restart, the live service will expose the updated
endpoints.

Either way, aligning the codebase behind uvicorn with the repository
you're modifying will clear the route mismatch and the 404s. Let me know
which path you prefer and I can walk through the file sync or startup
command.

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- -

**Prompt:**

I need to review a couple of your statements in detail. First, you wrote
the following: All of the code we've been editing (schemas, router
prefix change, new 422 constant) lives under
/home/rusty_admin/projects/reachy_08.4.2/\.... \_\_\_\_\_\_ This means
all of the promotion system is configured in the project root (under
/home/rusty_admin/projects/reachy_08.4.2/\....), correct? Next you
wrote: The uvicorn process you're running serves an older copy of the
app from /media/rusty_admin/project_data/reachy_emotion/\.... That tree
still has the original router (prefix=\"/api/media\", routes defined as
\"/promote/\...\"), so FastAPI exposes /api/media/promote/stage in the
OpenAPI output and will never match /promote/stage--- hence the 404s.
This statement is very confusing. We configured uvcorn on a separate
device for a good reason. It\'s located close to the video storage. You
mentioned that it serves an older copy of the app. Why is this copy
considered old and includes the original router? What do you mean
stating the following: FastAPI exposes /api/media/promote/stage in the
OpenAPI output and will never match /promote/stage What does it mean to
say that FastAPI exposes the endpoint in the OpenAPIOutput? What is the
OpenAPIOutput? Why will it never match /promote/stage?

**Response:**

\[MEMORY BANK: ACTIVE\]

**Where the updated code lives**

Yes---the promotion-system edits we've made (new schemas, router prefix
change, 422 constant update) are all in the workspace under
/home/rusty_admin/projects/reachy_08.4.2/.... When you run tests there,
you see the new behavior because FastAPI is created from that copy of
the code.

**Why the running service still shows "old" routes**

Your uvicorn service is launched from
/media/rusty_admin/project_data/reachy_emotion/..., which currently
contains the previous version of apps/api/app/routers/promote.py (with
the prefix=\"/api/media\" router). Unless that tree is updated or the
server is pointed at the new repo, the process will keep exporting the
old endpoints---hence the OpenAPI document lists
/api/media/promote/stage instead of /promote/stage.

**What the OpenAPI output is telling us**

curl http://localhost:8081/openapi.json returns FastAPI's automatically
generated OpenAPI specification (FastAPI calls it "OpenAPI output").
Seeing /api/media/promote/stage in that JSON means the active app is
registering a route at that exact path. Because the route is
/api/media/promote/stage, a request to /promote/stage won't match and
returns 404. Conversely, if the OpenAPI spec showed /promote/stage, that
would be the path you'd need to call.

**Bottom line**

The code and the running service are out of sync. To get the new routes
working:

1\. Either deploy the updated files from
/home/rusty_admin/projects/reachy_08.4.2/

into /media/rusty_admin/project_data/reachy_emotion/,

2\. Or run uvicorn directly against the updated workspace.

Once the service is running with the new router, the OpenAPI spec will
list /promote/stage and /promote/sample, and the curl calls to those
paths (or /api/media/promote/\... if you intentionally keep a root path)
will succeed without 404s.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ \_\_\_ You've
confirmed the unit tests pass (pytest
tests/apps/api/routers/test_promote_router.py), so the router + schema
code in the project tree is good. The 500s from the live service mean
the FastAPI process on the media drive keeps crashing while handling the
request.

The runaway trace you saw earlier blamed the synchronous psycopg2
driver; if the curl still reports "Internal Server Error" after updating
the .env, capture the new stack trace from the uvicorn console---you'll
likely see either the same async-driver complaint (meaning asyncpg isn't
installed or the env change didn't stick) or a different runtime issue.
Key checks:

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- -

The stack trace shows the failure occurs while SQLAlchemy is trying to
open a database connection---long before the repository query actually
runs. The key lines are:

asyncpg.connect(\...) → uvloop.create_unix_connection(\...) →
FileNotFoundError: \[Errno 2\]

That means the async driver can't find the Unix socket at
/var/run/postgresql.

Possible reasons:

Postgres on this host isn't exposing a socket at that path (or the
service is on a different machine).

File permissions prevent uvicorn's user from accessing the socket.

The socket lives at a different location (e.g., /run/postgresql, /tmp,
or a custom directory).

Recommended checks

Verify the socket exists and is reachable:

bash

ls -l /var/run/postgresql/

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_- \_

Prompt:

Consider the following when attempting to verify the socket exists and
is reachable: ls -l /var/run/postgresql/ total 0 \_\_\_\_\_\_\_ Note:
Postgres is not installed on the /media drive. The following path is
intended store the actual videos using the local file system
/media/rusty_admin/project_data/reachy_emotion Postgres, which is
intended to store mainly metadata (labels) and URLs, is installed at the
following location (on a different SSD):
/media/rusty_admin/postgres_db/pgdata Again, /postgres_db is a different
SSD. Is the UNIX socket simply missing or could it be located at a
different path?

**Response:**

\[MEMORY BANK: ACTIVE\] The empty /var/run/postgresql/ directory tells
us the Postgres instance isn't exposing the default socket location.

Because your cluster lives under /media/rusty_admin/postgres_db/pgdata,
it likely writes sockets somewhere else---or the service is listening
only on TCP.

**Here's how to pin it down:**

Inspect its configuration (on the host running Postgres): open
/media/rusty_admin/postgres_db/pgdata/postgresql.conf and look for
unix_socket_directories and listen_addresses.

If unix_socket_directories is set (e.g. /tmp or a custom path), point
the DSN there:
postgresql+asyncpg://reachy_dev:tweetwd4959@/reachy_emotion?host=/path/from/conf
ig

If sockets are disabled and listen_addresses includes 127.0.0.1 or
localhost, use the TCP DSN:
postgresql+asyncpg://reachy_dev:tweetwd4959@127.0.0.1:5432/reachy_emotion
(Make sure pg_hba.conf allows that connection and the server is really
listening on 5432.)

To discover the socket path without editing files, run:

sudo -u postgres psql -c \"SHOW unix_socket_directories;\"

or

sudo -u postgres pg_config \--configure \| grep unix

from the machine hosting Postgres (adjust user if you run the service as
reachy_app).

If you switch to TCP, confirm the port is open:

ss -ltnp \| grep 5432

If nothing is listening, set listen_addresses = \'localhost\' (or the
appropriate IP) in postgresql.conf, allow it in pg_hba.conf, and reload
PostgreSQL.

Once the DSN matches an actual listening address/socket, restart uvicorn
and re-run the curl smoke tests---the 500s will disappear, and the
promotion endpoints should return 202 responses.
