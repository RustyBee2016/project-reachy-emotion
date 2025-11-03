# FastAPI SQLAlchemy config checks

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/18/2025 20:36:49  
**Updated:** 10/21/2025 20:05:09  
**Exported:** 10/21/2025 20:06:24  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f4329f-6a84-8321-b346-364de67b4942](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f4329f-6a84-8321-b346-364de67b4942)  

## Prompt:
consider the chat titled 'FastAPI URL storage process.'
you wrote the following:
What “DB = metadata, SSD = mp4/jpg, Nginx = static URLs” really means

DB (Postgres): canonical record of truth—id, sha256, split (temp|train|test), label (happy|sad or NULL for test), durations/fps/size, relative file path and/or relative URL (e.g., temp/2025/10/18/ab12…cd.mp4 → /videos/temp/2025/10/18/ab12…cd.mp4). Promotion updates both the filesystem location and the DB row atomically. Test items must have no label. Balance constraints apply to test.

SSD (filesystem): raw media bytes live here in a fixed tree:
/media/project_data/reachy_emotion/videos/{temp,train,test} and /thumbs.

Nginx: exposes static URL prefixes that map straight to those folders. Example:
location /videos { alias /media/.../videos; } and location /thumbs { alias /media/.../thumbs; }. No FastAPI request needed to fetch a file; the URL is “static” because it’s just a stable path under those prefixes. (FastAPI still creates the record; Nginx serves the bytes.)
____________

Can you assure me that all of the FastAPI configurations listed in the chat titled 'Media Mover configuration' and then confirmed in the chat titled 'chat titled 'Media Mover configuration' match up completely to all of the additional SQLAlchemy configurations recommended in the chat titled 'SQLAlchemy config guide_03?"

Thought for 20s

## Response:
Short answer: I won’t rubber-stamp “yes” without the literal configs in front of me—but if you run the checks below, you’ll know in five minutes whether FastAPI/Media-Mover is fully in lock-step with the SQLAlchemy setup I prescribed. These checks are tied to what we committed to in the requirements + agents docs (DB holds metadata + relative URLs, SSD holds bytes, Nginx serves static prefixes, promotions are atomic, test set unlabeled, 50/50 enforced). requirements\_08.4.2 AGENTS\_08.4.2

What must line up (one-glance checklist)
========================================

*   **URL shape is relative + stable**  
    SQLAlchemy models persist `rel_path` (e.g., `temp/2025/10/18/<sha>.mp4`) and never hard-code the host; the API constructs hrefs as `BASE_MEDIA_URL + "/" + rel_path` (e.g., `/videos/temp/...`). “Thumbs” mirror this with `BASE_THUMBS_URL`. requirements\_08.4.2
*   **Nginx aliases match the prefixes FastAPI emits**  
    `location /videos { alias /media/.../videos; }` and `location /thumbs { alias /media/.../thumbs; }`. No FastAPI hop needed to serve bytes. API only returns the hrefs. requirements\_08.4.2
*   **Filesystem split = {temp, train, test}**  
    The SQLAlchemy `Video.split` enum (or constrained text) only allows these; test items must have `label IS NULL`. Enforced via a DB constraint or ORM validator (`chk_split_label`). AGENTS\_08.4.2
*   **Promotion is transactional + idempotent**  
    Endpoint `/promote` moves `temp → train|test` and updates the same row inside one transaction; idempotency key prevents double-moves (ORM + unique key on `(sha256, split)` or a promotion log guard). AGENTS\_08.4.2
*   **50/50 test balance gate**  
    Before any move into `test`, the service checks per-class counters so `test` remains 50/50 (within tolerance) and blocks if the ratio would drift. (Yes, `test` rows carry no label; the gate uses intended class at time of promotion.) requirements\_08.4.2
*   **Schema fields exist and are wired in the ORM**  
    `id (uuid)`, `sha256 (unique)`, `split`, `label (nullable)`, `duration_ms`, `fps`, `width`, `height`, `rel_path_mp4`, `rel_path_jpg`, `created_at`, plus `promotion_log` table with `(video_id, from_split, to_split, ts, intended_emotion)`. AGENTS\_08.4.2
*   **Env → code parity**  
    FastAPI reads `VIDEOS_ROOT`, `THUMBS_ROOT`, `BASE_MEDIA_URL` (`/videos`), `BASE_THUMBS_URL` (`/thumbs`), and the Postgres URL; SQLAlchemy uses the same DSN and never rewrites paths. requirements\_08.4.2
*   **Session/transaction settings**  
    SQLAlchemy engine has `pool_pre_ping=True`, sensible pool size, and request-scoped sessions (dependency-injected `SessionLocal`) with `commit`/`rollback`/`close` discipline on every endpoint.
*   **Uniqueness + dedupe**  
    Unique index on `sha256`; ingest path incorporates `<sha>.mp4` so collisions are impossible; the API 409s if `sha256` already exists.
*   **Views/DTOs match the docs**  
    The GETs that the webapp uses return `href_mp4`, `href_jpg`, not raw filesystem paths; those hrefs must be the exact `/videos/...` and `/thumbs/...` Nginx prefixes. requirements\_08.4.2
*   **Manifests + reconciler alignment**  
    Rebuilds and audits use the same `rel_path` fields the API writes; no ad-hoc path joins anywhere else. AGENTS\_08.4.2
*   **Security posture**  
    JWT guard on mutating endpoints; Nginx serves static without auth (that’s intentional), while API remains behind auth/TLS. requirements\_08.4.2

Common drift I see (fix before moving on)
=========================================

*   FastAPI returning absolute URLs (`http://10.0.4.130/videos/...`) while Nginx is configured for relative paths. Make API return **relative hrefs**; let the web client resolve host.
*   ORM model uses `abs_path` while Nginx alias expects `rel_path`. Store **only** `rel_path` in DB; derive abs on the server when touching the filesystem.
*   `test` items accidentally get a label because the UI leaks it through. Add a DB check constraint and an ORM validator; block at both layers. AGENTS\_08.4.2
*   Promotion does `mv` first, then DB update. Flip it into **one transaction** with a two-phase pattern (DB row → filesystem move → finalize) and rollback on failure.

Five quick proofs (run these now)
=================================

1.  **Ingest → DB row**
    *   POST `/api/media/ingest` a tiny clip.
    *   Expect JSON with `href_mp4` like `/videos/temp/YYYY/MM/DD/<sha>.mp4` and `href_jpg` under `/thumbs/...`.
    *   `SELECT split,label,rel_path_mp4 FROM media.video WHERE sha256='<sha>';` → `split='temp'`, `label=NULL`, `rel_path_mp4` matches the href suffix. requirements\_08.4.2
2.  **Static file reality**
    *   `curl -I http://ubuntu2/videos/temp/.../<sha>.mp4` → `200` served by Nginx (no FastAPI hop).
    *   Same for `/thumbs/.../<sha>.jpg`. requirements\_08.4.2
3.  **Promotion atomicity**
    *   POST `/api/media/promote` with `{to:'train', intended_emotion:'happy'}`.
    *   Verify in one read: row `split='train'`, `label='happy'`, `rel_path_mp4` moved from `temp/...` to `train/...`, and **file** exists at the new path.
    *   `promotion_log` has a row referencing the same `video_id`. AGENTS\_08.4.2
4.  **Test set guard**
    *   Try promoting with `to:'test'` and any `label`.
    *   Expect: DB keeps `label=NULL`; API enforces 50/50 quota before allowing the move (or returns a 409/422 telling you which class is over quota). requirements\_08.4.2
5.  **Idempotency**
    *   Replay the same `/promote` with identical `Idempotency-Key`.
    *   Expect: safe no-op (same state, no duplicate `promotion_log` row). AGENTS\_08.4.2

* * *

If all five pass and your code matches the bullets up top, then yes—you’re aligned: FastAPI/Media-Mover and the SQLAlchemy plan are describing the same system, down to URL generation, storage layout, and transactional rules. If any single check fails, tell me which one tripped and I’ll hand you the smallest possible patch to close the gap.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)