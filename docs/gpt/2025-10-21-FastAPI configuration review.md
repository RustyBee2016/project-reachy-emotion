# FastAPI configuration review

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/18/2025 19:58:38  
**Updated:** 10/19/2025 6:41:41  
**Exported:** 10/21/2025 20:01:02  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f429ab-8394-8320-a49a-623fe98b4518](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f429ab-8394-8320-a49a-623fe98b4518)  

## Prompt:
consider the chat titled 'Media Mover configuration.'
We accomplished a lot configuring FastAPI/Media Mover and additional components of the backend. 
Carefully evaluate our finished product, understanding there is more important work to do on the backend (e.g. SQLAlchemy, etc).

If you are not certain FastAPI is rock solid, provide a few additional tests.
We must be absolutely certain FastAPI/Media Mover and the additional components are properly set up before configuring SQLAlchemy, etc.

## Response:
Thought for 8s

You’ve got the bones in place. Media Mover is up under systemd, Nginx is reverse-proxying, and the endpoint shape matches the project’s flow (ingest → label → promote → stats/videos) and the “promotion + balance + manifest” responsibilities we wrote into the requirements/agents docs. That’s the right skeleton to wire SQLAlchemy into next. requirements\_08.4.2 AGENTS\_08.4.2

If you want absolute confidence before you layer SQLAlchemy, run this short, surgical test set. It’s all local, fast, and catches 90% of the “oops” we see later in DB/ORM land.

0) Process & boot tests (systemd + Nginx)
=========================================

```bash
# service is enabled and restarts cleanly
sudo systemctl is-enabled fastapi-media.service
sudo systemctl restart fastapi-media.service && sleep 1 && systemctl --no-pager status fastapi-media

# health (FastAPI) through Nginx TLS path
curl -k -sS https://10.0.4.130/api/media/health | jq
# expected: {"status":"ok","service":"media","uptime":...}

# Nginx proxy sanity (headers preserved; JSON content-type)
curl -k -I https://10.0.4.130/api/media/health
```

1) Endpoint contract smoke (no DB writes yet)
=============================================

These mirror the functional spec and agents’ responsibilities. requirements\_08.4.2 AGENTS\_08.4.2

```bash
# /ingest — minimal payload (file path or presigned local ref)
curl -k -X POST https://10.0.4.130/api/media/ingest \
  -H 'Content-Type: application/json' \
  -d '{"source_path": "/media/project_data/reachy_emotion/videos/temp/testclip.mp4"}'

# /label — attach a label (training-only; test must remain unlabeled)
curl -k -X POST https://10.0.4.130/api/media/label \
  -H 'Content-Type: application/json' \
  -d '{"video_id": "VID-1", "label": "happy"}'

# /promote — move temp → train (label required) or temp → test (label must be null)
curl -k -X POST https://10.0.4.130/api/media/promote \
  -H 'Content-Type: application/json' \
  -d '{"video_id": "VID-1", "target_split": "train"}'

# /stats — check class counts and the 50/50 test rule
curl -k https://10.0.4.130/api/media/stats | jq
```

Expected behaviors tied to the docs:

*   `promote temp→train` requires a valid label; `promote temp→test` must reject if a label exists. AGENTS\_08.4.2
*   `/stats` surfaces the test split balance (enforcing 50/50 ±0.05). requirements\_08.4.2

2) Filesystem/URL reality checks (Nginx + paths)
================================================

Your design is “DB = metadata, SSD = mp4/jpg, Nginx = static URLs.” Let’s prove each hop. requirements\_08.4.2

```bash
# after /ingest, a thumbnail should exist and be web-served
ls -l /media/project_data/reachy_emotion/videos/thumbs | head

# URL from the API should be fetchable through Nginx (no auth leaks)
curl -k -I https://10.0.4.130/thumbs/<thumb>.jpg
curl -k -I https://10.0.4.130/videos/<clip>.mp4
```

Guardrails you want to see:

*   Static GETs return 200 with sane cache headers; directory listing is **disabled**.
*   No path traversal (`../`) succeeds (Nginx: `try_files`+root).

3) Idempotency + duplicate ingest
=================================

We promised idempotent writes at the agent/policy layer. Catch collisions now. AGENTS\_08.4.2

```bash
# same file twice should return the same record or a 409 with a helpful message
curl -k -X POST https://10.0.4.130/api/media/ingest -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: abc123' \
  -d '{"sha256":"<hash>", "source_path": ".../temp/dupe.mp4"}'
curl -k -X POST https://10.0.4.130/api/media/ingest -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: abc123' \
  -d '{"sha256":"<hash>", "source_path": ".../temp/dupe.mp4"}'
```

4) Label/split invariants (the “no-label test split” rule)
==========================================================

```bash
# try to set a label on a test item — should be 400
curl -k -X POST https://10.0.4.130/api/media/label \
  -H 'Content-Type: application/json' \
  -d '{"video_id":"VID-TEST-1","label":"sad"}'
# try to promote labeled → test — should be 400
curl -k -X POST https://10.0.4.130/api/media/promote \
  -H 'Content-Type: application/json' \
  -d '{"video_id":"VID-LABELED","target_split":"test"}'
```

Those behaviors are required by the requirements/agents (test = unlabeled, promotion agent enforces). requirements\_08.4.2 AGENTS\_08.4.2

5) Concurrency + basic load
===========================

You don’t need a full soak. Just make sure Uvicorn + your file ops don’t deadlock.

```bash
# 10 parallel ingests (same size, unique files)
seq 1 10 | xargs -I{} -P 10 curl -k -s -X POST https://10.0.4.130/api/media/ingest \
  -H 'Content-Type: application/json' \
  -d "{\"source_path\": \"/media/.../temp/clip_{}.mp4\"}"

# quick RPS probe (hey or wrk)
hey -z 10s -c 20 -m GET https://10.0.4.130/api/media/health
```

Expect steady 200s, no 5xx spikes, and logs free of “file exists” races.

6) Security pokes (low-drama)
=============================

```bash
# JWT required? (if you wired it already) → should return 401 without token
curl -k -i https://10.0.4.130/api/media/stats

# path traversal blocked
curl -k -i "https://10.0.4.130/videos/../../etc/passwd"
```

We wrote JWT + local-first constraints into the spec; if auth is deferred until SQLAlchemy, just note it and move on. requirements\_08.4.2

7) Readiness vs liveness (kitchen-sink but quick)
=================================================

If you’ve got both:

*   `/health` = liveness (process up).
*   `/ready` = readiness (FS root mounted, thumbs/videos writable, DB reachable).  
    Wire whichever you don’t have yet—it’s a 10-line FastAPI route that catches bad mounts before your ORM does.

8) Tiny pytest (so you can lock regressions)
============================================

Drop this under `apps/api/tests/test_media_api.py`. It uses `httpx` against your running service; swap the base URL if you mount a TestClient later.

```python
import httpx, pytest

BASE = "https://10.0.4.130/api/media"
KW = dict(verify=False, timeout=10)

@pytest.mark.parametrize("path", ["/health", "/stats"])
def test_basic_gets(path):
    r = httpx.get(BASE + path, **KW)
    assert r.status_code in (200, 401)  # allow 401 if JWT enforced

def test_ingest_idempotent():
    payload = {"source_path": "/media/.../temp/clip_dupe.mp4", "sha256": "X"*64}
    h = {"Idempotency-Key": "abc123"}
    r1 = httpx.post(f"{BASE}/ingest", json=payload, headers=h, **KW)
    r2 = httpx.post(f"{BASE}/ingest", json=payload, headers=h, **KW)
    assert r1.status_code in (200, 201)
    assert r2.status_code in (200, 201, 409)

def test_test_split_must_be_unlabeled():
    # simulate “promote to test” with a label — should fail
    bad = {"video_id": "VID_ANY", "target_split": "test"}
    r = httpx.post(f"{BASE}/promote", json=bad, **KW)
    assert r.status_code in (400, 422)
```

* * *

What I’m looking for in the outputs
-----------------------------------

*   Health and proxy are clean (200/JSON, right headers).
*   Ingest creates a thumb and a reachable URL (Nginx serves, no directory listing).
*   Idempotency behaves (second call is 200 same-object or 409).
*   The test-split rule bites exactly when it should (no labels on test, promotions reject).
*   Parallel ingest doesn’t race on filesystem moves.
*   Optional: `/ready` fails fast if the media root is missing (helps before SQLAlchemy touches DB).

If those pass, your FastAPI/Nginx/FS layer is solid enough to introduce SQLAlchemy models and transaction semantics without mystery flakiness later. It also lines up with the promotion/balance guarantees we promised in the requirements and agents files, so you’re not building the ORM against a moving target. requirements\_08.4.2 AGENTS\_08.4.2

Want me to turn the curl set into a single `make smoke` target and wire the pytest into a `ci.yml` so these checks run on every PR?



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)