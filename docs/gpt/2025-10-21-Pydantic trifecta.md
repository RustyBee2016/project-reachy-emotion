**Title: 2025-10-21-Pydantic trifecta**

**Pydantic trifecta**

Nice. That's the trifecta:

• Uvicorn bound where we expect (127.0.0.1:8000)

• Nginx config valid and reloaded

• Both probes return {\"status\":\"ok\"} (direct and via /api/media/...)

You've got the stack in phase.

Here's a tight wrap-up + a few guardrails so it stays that way:

**Quick hardening / hygiene**

• **Lock the unit to localhost** (you did): \--host 127.0.0.1 \--port
8000.

• **Restart policy:** in your unit, keep Restart=always and a small
RestartSec=3.

• **WorkingDirectory** = /media/\.../apps/api so .env(.api) loads
reliably.

• **Pin the venv** you actually use in ExecStart (no more path drift).

**Smoke tests to keep around**

\# local app curl -sS http://127.0.0.1:8000/healthz \# through Nginx
(root path honored) curl -k https://10.0.0.130/api/media/healthz \#
headers sanity (optional) curl -k -I
https://10.0.0.130/api/media/healthz

**CORS reality check**

From your frontend box (Ubuntu 2), open the browser devtools and hit an
API route. If you see CORS noise, confirm UI_ORIGINS matches the
**exact** origin you're visiting (scheme+host+port). You already set:

UI_ORIGINS=https://10.0.4.130,https://whi-ds,https://whi-ds:8501,http://whids:8501,http://whi-ds,http://localhost:8501,http://127.0.0.1:8501

That should cover you in dev and prod.

**Nginx upstream stays aligned**

You kept:

upstream media_mover_backend { server 127.0.0.1:8000; keepalive 32; }
location /api/media/ { proxy_pass http://media_mover_backend/; \... }

Perfect. If you ever change the FastAPI port, change it **once** in the
upstream and you're done.

**Optional: liveness/readiness (for future agents/monitors)**

• Keep /healthz as liveness.

• Add a lightweight DB check endpoint for readiness (pings Postgres and
returns 200

only if connected). Not urgent, just handy when you wire Observability
Agent.

**Paper trail**

• Update your requirements_08.4.2.md "Endpoints" section to reflect:

o **Public:** https://10.0.4.130/api/media/\* (Nginx → TLS)

o **Private:** http://127.0.0.1:8000/\* (Uvicorn)

• Note the systemd unit paths and the Nginx upstream block you
standardized on.

If you want, we can add a tiny /version route (returns git commit + app
version) and a /metrics stub next, then move on to wiring SQLAlchemy.
