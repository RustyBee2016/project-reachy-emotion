# Video labeling workflow

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/15/2025 20:59:37  
**Updated:** 10/15/2025 21:06:19  
**Exported:** 10/21/2025 20:34:54  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f04378-cb88-8329-aa89-d8bd61ee0d99](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f04378-cb88-8329-aa89-d8bd61ee0d99)  

## Prompt:
consider the chat titled 'DeepStream emotion classification.'
you wrote: you’ll need to attach and persist the label metadata beforehand, ideally at the video level first, and then propagate that label to every frame extracted from that video.
______________
I think this means the workflow associated local file system used to store videos must be updated as follows:
When the user classifies a video as sad or happy, a tag (i.e. the classification/category) must be written to the Postgres database as the same time the video is stored in the local file system.

## Response:
Thought for 24s

Yep—that’s the right read. The label has to live in the metadata as soon as the human picks “happy” or “sad,” and it should stick to the asset everywhere it goes. The clean way is:

*   write the label to Postgres at the exact moment the user classifies the clip,
*   keep the file in `/videos/temp` until you explicitly promote it, and
*   when you promote, move the file atomically and keep DB + filesystem in lockstep.

Here’s a tight, workable shape you can drop in.

What to change (minimal but solid)
==================================

1) DB rules that make bad states impossible
-------------------------------------------

Add checks so “train/test clips must be labeled, temp can be unlabeled.” And log every move.

```sql
-- labels you allow right now
CREATE TYPE emotion_label AS ENUM ('happy','sad');

ALTER TABLE video
  ALTER COLUMN label TYPE emotion_label USING label::emotion_label,
  ALTER COLUMN split SET NOT NULL,
  ADD CONSTRAINT chk_label_for_train
    CHECK (split <> 'train' OR label IS NOT NULL),
  ADD CONSTRAINT chk_label_for_test
    CHECK (split <> 'test' OR label IS NOT NULL);

-- optional: forbid unlabeled temp → train/test in one hop
-- (you can keep it, but the CHECKs above already catch it)

-- promotion log for audits
CREATE TABLE IF NOT EXISTS promotion_log (
  id           BIGSERIAL PRIMARY KEY,
  video_id     UUID NOT NULL,
  from_split   TEXT NOT NULL,
  to_split     TEXT NOT NULL,
  label_at_move emotion_label,
  actor        TEXT NOT NULL,
  reason       TEXT,
  ts           TIMESTAMPTZ DEFAULT now()
);
```

Policy this enforces:

*   `temp`: label optional
*   `train`/`test`: label required
*   Every move is recorded

2) Two small HTTP endpoints (Media Mover / App API)
---------------------------------------------------

### A) User sets the label (no file move yet)

Keep this idempotent and fast.

```
POST /api/relabel
Body: { "video_id": "...", "label": "happy" | "sad" }
```

Server (SQLAlchemy-ish):

```python
@router.post("/api/relabel")
def relabel(body: RelabelIn, db: Session = Depends(get_db)):
    v = db.get(Video, body.video_id)
    if not v: raise HTTPException(404, "not found")
    if v.split in ("train","test") and v.label == body.label:
        return {"ok": True}  # already set

    v.label = body.label
    v.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}
```

### B) Promote (atomic rename + metadata update + log)

You can combine “set label” and “promote” in one call if you want, but keeping them separate reduces accidental moves.

```
POST /api/promote
Body: { "video_id": "...", "dest_split": "train"|"test", "label": "happy"|"sad"?, "dry_run": false }
Headers: Idempotency-Key: <uuid>
```

Server sketch (pseudo-atomic with a single transaction and same-FS rename):

```python
@router.post("/api/promote")
def promote(body: PromoteIn, db: Session = Depends(get_db)):
    v = db.get(Video, body.video_id)
    if not v: raise HTTPException(404, "not found")

    # 1) ensure label present before leaving temp
    if body.label:
        v.label = body.label
    if body.dest_split in ("train","test") and not v.label:
        raise HTTPException(422, "train/test require label")

    if body.dry_run:
        return {"plan": {"from": v.split, "to": body.dest_split, "src": v.file_path}}

    # 2) compute new path, same filesystem (atomic rename)
    src = Path(BASE)/v.file_path
    dst_rel = f"videos/{body.dest_split}/{src.name}"
    dst = Path(BASE)/dst_rel

    with db.begin():  # single tx for metadata + move log
        # rename first so we fail before mutating DB if FS is unhappy
        src.rename(dst)

        # update DB row
        prev_split = v.split
        v.split = body.dest_split
        v.file_path = dst_rel
        v.updated_at = datetime.utcnow()

        db.add(PromotionLog(
            video_id=v.video_id,
            from_split=prev_split,
            to_split=body.dest_split,
            label_at_move=v.label,
            actor=current_user(),
            reason=body.reason or "user action",
        ))

    return {"ok": True, "new_path": dst_rel}
```

> Why this order? On a single device/partition, `rename()` is atomic. By moving first, you either succeed and then commit metadata, or you fail without touching the DB. That keeps DB ↔ FS consistent.

3) Manifest rebuild: propagate label to frames for TAO
------------------------------------------------------

When you rebuild `/videos/manifests/*.jsonl`, explode each labeled video into the samples TAO will see (e.g., N frames per video, or class folders). Even if you stick with video-level granularity, stamp the label into each record. Simple JSONL example:

```json
{"clip": "videos/train/abc123.mp4", "label": "happy", "fps": 30, "sample": "rand10@5s"}
{"clip": "videos/train/def456.mp4", "label": "sad",   "fps": 30, "sample": "rand10@5s"}
```

If you materialize frames for TAO-4 style image training:

```
/videos/frames/train/happy/abc123_f001.jpg
/videos/frames/train/happy/abc123_f047.jpg
/videos/frames/train/happy/abc123_f219.jpg
/videos/frames/train/sad/def456_f010.jpg
...
```

Or keep video files and let the training dataloader sample frames on the fly—either way, the label is carried from the `video` row into every sample record your spec reads.

4) UI flow (tiny but important)
-------------------------------

*   When the user clicks **Happy/Sad**, call `POST /api/relabel`.
*   Show the label immediately on the card (no move yet).
*   When they click **Promote to Train/Test**, call `POST /api/promote` (optionally send the label again for safety).
*   On success, drop it from the “Temp” list and have your backend kick `POST /api/manifest/rebuild` in the background so your next TAO run sees the new split/labels.

5) Guardrails that save you later
---------------------------------

*   Unique index `(sha256, size_bytes)` to dedupe ingest (you already planned this).
*   CHECKs above keep unlabeled clips out of train/test.
*   An idempotency key on `/api/promote` avoids double-moves if a client retries.
*   Append-only `promotion_log` lets you audit who moved what, when, and with which label.

TL;DR
=====

Your instinct is correct: persist the label at the moment of human classification (DB is the source of truth), and then propagate it everywhere—first to the video row, next to the manifest, and finally to every sampled frame that TAO trains on. Keep promotion as a separate, atomic step so files and rows don’t drift. This gives you clean lineage, reproducible datasets, and zero “mystery labels” later.

## Prompt:
Another key point involves storing some videos specifically used to test/validate the model.  These videos, which could be stored in the following path on the storage SSD: videos/test.
These videos must NOT include a label.  
The user must decide which of the generated videos will be used specifically for testing and store the videos accordingly.

## Response:
Thought for 9s

Got it—so “test” is a blind hold-out: files live under `videos/test/` and they must carry **no label**. Easy to lock in with a few tweaks.

DB rules (make the invariant true by construction)
==================================================

If you keep just `train` and `test`:

```sql
-- allowed labels
CREATE TYPE emotion_label AS ENUM ('happy','sad');

-- splits: temp (staging), train (labeled), test (blind, unlabeled)
ALTER TABLE video
  ADD COLUMN IF NOT EXISTS split TEXT NOT NULL DEFAULT 'temp',
  ADD COLUMN IF NOT EXISTS label emotion_label;

-- enforce: train requires a label; test forbids a label
ALTER TABLE video
  DROP CONSTRAINT IF EXISTS chk_label_for_train,
  DROP CONSTRAINT IF EXISTS chk_label_for_test,
  ADD CONSTRAINT chk_train_requires_label
    CHECK (split <> 'train' OR label IS NOT NULL),
  ADD CONSTRAINT chk_test_forbids_label
    CHECK (split <> 'test'  OR label IS NULL);
```

> If you ever want **labeled validation**, add a third split `val` and copy the `train` rule to it.

Promotion behavior (tiny adjustments)
=====================================

*   **Relabel endpoint** stays the same, but it should refuse labels for `test` rows.
*   **Promote endpoint** should:
    *   refuse a `label` field when `dest_split == "test"`,
    *   if the source row has a label, **null it** at move time (that’s your guardrail),
    *   rename the file to `videos/test/<name>.mp4`.

```python
@router.post("/api/promote")
def promote(body: PromoteIn, db: Session = Depends(get_db)):
    v = db.get(Video, body.video_id)
    if not v: raise HTTPException(404, "not found")

    if body.dest_split == "test":
        if body.label is not None:
            raise HTTPException(422, "Test split must be unlabeled.")
    else:
        # train (and val, if you add it) require labels
        v.label = body.label or v.label
        if not v.label:
            raise HTTPException(422, "Destination requires a label.")

    src = Path(BASE)/v.file_path
    dst_rel = f"videos/{body.dest_split}/{src.name}"
    dst = Path(BASE)/dst_rel

    with db.begin():
        src.rename(dst)
        prev_split = v.split
        v.split = body.dest_split
        v.file_path = dst_rel
        if v.split == "test":
            v.label = None  # hard reset to protect the invariant

        db.add(PromotionLog(
            video_id=v.video_id,
            from_split=prev_split,
            to_split=v.split,
            label_at_move=v.label,   # will be NULL for test
            actor=current_user(),
            reason=body.reason or "user action",
        ))
    return {"ok": True, "new_path": dst_rel}
```

Also block relabeling once in test:

```python
@router.post("/api/relabel")
def relabel(body: RelabelIn, db: Session = Depends(get_db)):
    v = db.get(Video, body.video_id)
    if not v: raise HTTPException(404, "not found")
    if v.split == "test":
        raise HTTPException(422, "Cannot assign labels in test split.")
    v.label = body.label
    db.commit()
    return {"ok": True}
```

Manifests (train = labeled, test = unlabeled)
=============================================

*   `train.jsonl` (used by TAO training):

```json
{"clip":"videos/train/abc123.mp4","label":"happy"}
{"clip":"videos/train/def456.mp4","label":"sad"}
```

*   `test.jsonl` (for blind evaluation / inference runs):

```json
{"clip":"videos/test/xyz999.mp4"}
{"clip":"videos/test/qwe777.mp4"}
```

If you need ground truth for metrics, store it **elsewhere** (e.g., a `test_labels` table or `test_labels.csv` kept out of the app’s normal UI/permissions) and only join it during offline evaluation.

UI guardrails (simple and obvious)
==================================

*   In **Temp** and **Train**: show the Happy/Sad toggle.
*   In **Test**:
    *   hide/disable the label picker,
    *   show a “Blind test clip” badge,
    *   promote button **“Send to Test (unlabeled)”** that auto-strips any existing label.

Edge cases you just eliminated
==============================

*   Accidentally leaking labels into test: blocked by the DB check + API resets.
*   A labeled clip sneaking into test: promotion code nulls it; the DB forbids non-null anyway.
*   Users labeling a test clip later: relabel endpoint refuses it.

That’s it. With these invariants, your storage (`videos/test/…`) and database stay in lockstep, and your test set remains truly blind.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)