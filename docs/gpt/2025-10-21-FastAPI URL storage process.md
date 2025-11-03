# FastAPI URL storage process

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/18/2025 20:25:29  
**Updated:** 10/19/2025 6:23:36  
**Exported:** 10/21/2025 20:03:34  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f42ff7-af30-8323-8105-fbfe7a54d16d](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f42ff7-af30-8323-8105-fbfe7a54d16d)  

## Prompt:
consider the chat titled 'FastAPI configuration review.'
you wrote the following:
2) Filesystem/URL reality checks (Nginx + paths)
Your design is “DB = metadata, SSD = mp4/jpg, Nginx = static URLs.”
______________

My understanding is that the DB (Postgres) stores both metadata and the video (static) URLs. Correct?

What do you mean by the following statement: "Nginx = static URLs?” 

Explain the entire process of generating the URLs each time a video is received from the video generation model (Luma AI). 
Then explain the process of efficiently and accurately storing the URLs in the DB.

## Response:
Thought for 30s

Short answer: yep—Postgres holds the metadata **and** the canonical URL paths for each asset. The SSD just stores the bytes. And “Nginx = static URLs” means Nginx is the thing that turns stable, pretty paths like `/videos/…` and `/thumbs/…` into direct reads from your SSD—no Python hop in the middle. Your requirements + agents docs already lean this way: SSD under `/media/.../videos/{temp,train,test,thumbs}`; DB tracks metadata + paths; promotions are transactional; test split carries no labels. requirements\_08.4.2 AGENTS\_08.4.2

* * *

What “DB = metadata, SSD = mp4/jpg, Nginx = static URLs” really means
=====================================================================

*   **DB (Postgres):** canonical record of truth—`id`, `sha256`, `split` (`temp|train|test`), `label` (`happy|sad` or `NULL` for test), durations/fps/size, **relative file path** and/or **relative URL** (e.g., `temp/2025/10/18/ab12…cd.mp4` → `/videos/temp/2025/10/18/ab12…cd.mp4`). Promotion updates both the filesystem location and the DB row atomically. Test items must have **no label**. Balance constraints apply to `test`. requirements\_08.4.2 AGENTS\_08.4.2
*   **SSD (filesystem):** raw media bytes live here in a fixed tree:  
    `/media/project_data/reachy_emotion/videos/{temp,train,test}` and `/thumbs`. requirements\_08.4.2
*   **Nginx:** exposes **static** URL prefixes that map straight to those folders. Example:  
    `location /videos { alias /media/.../videos; }` and `location /thumbs { alias /media/.../thumbs; }`. No FastAPI request needed to fetch a file; the URL is “static” because it’s just a stable path under those prefixes. (FastAPI still creates the record; Nginx serves the bytes.)

* * *

End-to-end: how a URL is minted and stored when a new video arrives
===================================================================

Below is the happy path the **Ingest → Label/Promote → Reconcile** agents already assume. I’ll use `BASE_MEDIA_URL=/videos` and `BASE_THUMBS_URL=/thumbs` to keep things deterministic. AGENTS\_08.4.2

### 1) Receive & stage (Ingest Agent)

1.  **Pull bytes** from Luma (or upload) into a staging tmp file.
2.  **Compute `sha256`** and probe media (`ffprobe`) → `duration`, `fps`, `width`, `height`.
3.  **Choose canonical filenames** (content-addressed):
    *   `stem = {sha256[:16]}_{epochms}`
    *   `video = {stem}.mp4`, `thumb = {stem}.jpg`
    *   **Date partitioning** for sanity: `YYYY/MM/DD/`.
4.  **Place files**:
    *   `/videos/temp/YYYY/MM/DD/{video}`
    *   `/thumbs/temp/YYYY/MM/DD/{thumb}`
5.  **Make URLs** (string join, no network call):
    *   `video_url = /videos/temp/YYYY/MM/DD/{video}`
    *   `thumb_url = /thumbs/temp/YYYY/MM/DD/{thumb}`  
        These work because Nginx maps `/videos` → SSD `/videos`, `/thumbs` → SSD `/thumbs`.

### 2) Persist (transaction, idempotent UPSERT)

*   Insert into `media.video` (example columns):
    ```
    id (uuid), sha256 (unique), split='temp',
    label = NULL,
    rel_path = 'temp/YYYY/MM/DD/{video}',
    rel_thumb = 'temp/YYYY/MM/DD/{thumb}',
    duration_s, fps, width, height,
    generator='luma', prompt_json, created_at
    ```
*   Either store `rel_*` only and **derive** `url = BASE_MEDIA_URL || '/' || rel_path` when needed, **or** store the URLs as materialized strings—both work. I prefer storing **relative paths**, with the API formatting full URLs.
*   Use `ON CONFLICT (sha256) DO UPDATE SET ...` to make ingest idempotent.
*   Emit `ingest.completed` with the row `id` and the two URLs (for the UI). AGENTS\_08.4.2

### 3) Label & promote (Labeling + Promotion Agents)

*   When the user labels **train**: set `label IN ('happy','sad')`, **move** the file on disk from `/videos/temp/...` → `/videos/train/{happy|sad}/...`, and update `rel_path` & derived URL in the **same** DB txn.
*   When the user marks **test**: enforce **no label** (`label IS NULL`) and move to `/videos/test/...`.
*   Enforce 50/50 class balance **only for test** (by counts in DB before each move). Record an entry in `promotion_log`. requirements\_08.4.2 AGENTS\_08.4.2

### 4) Reconcile & manifests (Reconciler Agent)

*   Periodically (or on change) recompute counts, rebuild `train_manifest.json` from DB→FS truth, and flag any drift (missing file, stray file, wrong split). AGENTS\_08.4.2

* * *

Why this is efficient and accurate (and what to enforce)
========================================================

**Efficient**

*   **Zero copy on serve:** Nginx serves directly from disk; FastAPI stays out of the hot path.
*   **Idempotent ingest:** `sha256` unique index + UPSERT avoids dupes.
*   **Relative paths:** changing hostnames or proxies never invalidates DB rows.

**Accurate**

*   **Constraints:**
    *   `CHECK ((split='test' AND label IS NULL) OR (split='train' AND label IN ('happy','sad')))`
    *   `UNIQUE (sha256)`
*   **Transactions around promotions:** file move + DB update + quota checks happen together; on error, rollback and move the file back.
*   **Agents own the rules:** Labeling Agent maintains no-label rule and split quotas; Promotion Agent updates split + path atomically; Reconciler audits/repairs. AGENTS\_08.4.2

* * *

Minimal config and code you can drop in
=======================================

### Nginx (static mapping)

```nginx
# Video bytes
location /videos/ {
  alias /media/project_data/reachy_emotion/videos/;
  autoindex off;
  add_header Cache-Control "public, max-age=31536000, immutable";
}

# Thumbnails
location /thumbs/ {
  alias /media/project_data/reachy_emotion/thumbs/;
  autoindex off;
  add_header Cache-Control "public, max-age=31536000, immutable";
}
```

### Table constraints (sketch)

```sql
ALTER TABLE media.video
  ADD CONSTRAINT uq_video_sha UNIQUE(sha256),
  ADD CONSTRAINT chk_split_label
    CHECK (
      (split = 'test'  AND label IS NULL) OR
      (split = 'train' AND label IN ('happy','sad')) OR
      (split = 'temp'  AND label IS NULL)
    );
```

(Your agents doc explicitly calls out the **no-label test** invariant and transactional promotions.) AGENTS\_08.4.2

### FastAPI ingest (pseudo-flow)

```python
# inside POST /ingest
sha = sha256sum(tmp_path)
stem = f"{sha[:16]}_{int(time.time()*1000)}"
rel = f"temp/{today}/{stem}.mp4"
rel_jpg = f"temp/{today}/{stem}.jpg"

final_mp4 = VIDEOS_ROOT / rel   # /media/.../videos/ + rel
final_jpg = THUMBS_ROOT / rel_jpg

# move files, generate thumb
tmp_path.rename(final_mp4)
ffmpeg_thumb(final_mp4, final_jpg)

with db.begin():  # transaction
    upsert_video(
      sha256=sha, split='temp', label=None,
      rel_path=rel, rel_thumb=rel_jpg,
      duration_s=meta.dur, fps=meta.fps, width=meta.w, height=meta.h,
      generator='luma', prompt_json=req.prompt
    )

return {
  "id": video.id,
  "video_url": f"{BASE_MEDIA_URL}/{rel}",
  "thumb_url": f"{BASE_THUMBS_URL}/{rel_jpg}"
}
```

* * *

If you want, I can sketch the **promotion** transaction (file rename + DB update + 50/50 check) next. But big picture: DB tracks the truth; Nginx exposes stable paths; your agents keep the invariants tight so URLs always point to exactly one file and “test” stays unlabeled. That’s the shape. requirements\_08.4.2 AGENTS\_08.4.2



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)