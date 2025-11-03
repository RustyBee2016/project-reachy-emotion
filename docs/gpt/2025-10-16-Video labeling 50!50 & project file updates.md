# Video labeling 50!50 & project file updates

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/15/2025 21:21:53  
**Updated:** 10/16/2025 10:30:52  
**Exported:** 10/21/2025 20:31:52  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f048af-4200-8324-809e-f7f7c19813de](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f048af-4200-8324-809e-f7f7c19813de)  

## Prompt:
consider the chat titled 'Video labeling workflow.'  
you wrote: so “test” is a blind hold-out: files live under videos/test/ and they must carry no label.
_________
These will be the videos used only for testing/validation.
A key concern will involve storing the appropriate number of videos depicting each emotion type.  Ideally there will be a 50/50 mixture (sad/happy) of unlabeled videos stored at the path videos/test/.
I suggest creating a script that alternates video generation prompts of each emotion type. For example, iteration 1 could be 'happy' and then iteration 2 would be 'sad', then 'happy' then 'sad,' etc.
Those videos would be reviewed by the user and evaluated for correctness.  If a video labeled 'sad' did not display a sad emotion, the user must have the ability to request another 'sad' video; for example there would be two buttons in the webpage UI:  1) generate a 'sad' video 2) generate a 'happy' video. 
A counter would display on screen showing the number of 'sad' and 'happy' videos current stored in the videos/test/ directory.  
The balance will be maintained by the user at 50/50 until the threshold is met (the minimum number of test videos stored in videos/test).  At that time (but not before), the user coulf click a button to initiate the model validation process or continue to generate new videos to be used for testing.
What do you think of this process?

## Response:
Thought for 25s

I like it. It’s simple, auditable, and—most importantly—keeps “test” truly blind. A few tweaks will make it sturdier and harder to accidentally poison your hold-out:

### Keep the spirit, tighten the edges

*   **Don’t store labels in `videos/test/`.** Store only the user’s _intent_ and generator metadata (e.g., `intended_emotion='sad'`, `generator='luma', seed=42`) in the DB. Leave `label` **NULL** for anything under `test/`. That way you can check balance without leaking the answer into training later.
*   **Alternate with guardrails, not dogma.** Alternate prompts, but also aim for a **target ratio** (e.g., 0.5±0.05). If the set drifts (user rejects a bunch of “sad”), the UI should _nudge_ the next pick toward the underrepresented class.
*   **Rejects don’t count.** Only increment counters after the user accepts and the file is moved into `videos/test/`.
*   **Prevent leakage by API.** Make the “Promote to Test” path refuse any payload that includes a `label`. (Training split can carry labels; test split cannot.)
*   **Randomize review order.** When the user audits test clips, shuffle so you don’t bias judgments by recent generation runs.
*   **Dedupe aggressively.** Hash each generated file (`sha256 + size_bytes`) to avoid near-duplicates inflating one class.

### Minimal spec you can wire today

**DB (metadata)**

```sql
-- videos table (test items have label IS NULL)
video_id UUID PK,
file_path TEXT NOT NULL,        -- e.g., videos/test/ab12.mp4
split TEXT CHECK (split IN ('temp','train','test')) NOT NULL,
label TEXT,                     -- NULL for test
intended_emotion TEXT,          -- 'happy'|'sad' (what was requested)
generator TEXT, seed BIGINT,    -- provenance
sha256 TEXT, size_bytes BIGINT, -- dedupe
created_at TIMESTAMPTZ DEFAULT now()
```

**FastAPI endpoints (mini “media mover”)**

```http
POST /api/generate
  body: { intended_emotion: "happy"|"sad", seed?: int }
  -> creates video in /videos/temp, stores intended_emotion, returns temp_id

POST /api/test/accept
  body: { video_id } 
  -> atomic move temp → test, enforce label==NULL, returns counts by intended_emotion

POST /api/test/reject
  body: { video_id, reason }
  -> deletes temp (or archives), does NOT change counters

GET  /api/test/counts
  -> { happy: 37, sad: 34, target_per_class: 100 }

POST /api/validate/run
  preconditions: for all c in {happy,sad}, count(test,intended_emotion=c) ≥ target_per_class
```

**Business rules (server-side)**

*   `accept` for test split **must fail** if `label` is present or if `split != temp`.
*   `generate` should **bias** the next `intended_emotion` toward the underfilled class when `abs(happy−sad) > tolerance`.

### Streamlit UI sketch (just the bits you asked for)

*   Two primary buttons: **Generate “Happy”**, **Generate “Sad”**  
    Beneath them: a small caption like “Auto-balance: ON (target 50/50)” and a toggle to disable if you want manual control.
*   A **counter badge** row: `Happy: 37 | Sad: 34 | Goal each: 100`
*   A **preview pane** showing the last generated clip with: **Accept to Test** / **Reject & Retry**.
*   A **Validate** button that stays disabled until `min(happy,sad) ≥ GOAL`.

**Counter polling (client)**

```python
def update_counts():
    r = requests.get(f"{API}/api/test/counts").json()
    st.metric("Happy", r["happy"])
    st.metric("Sad", r["sad"])
    st.progress(min(r["happy"], r["sad"]) / r["target_per_class"])
```

### Workflow you proposed, with tiny upgrades

1.  **User clicks** “Generate Happy/Sad.”
2.  **Server logs** `intended_emotion`, generator, seed; writes to `/videos/temp`.
3.  **User reviews** → **Accept to Test** (atomic move to `/videos/test`), counter increments; or **Reject & Retry**.
4.  **Auto-balance**: next suggested button highlights the underrepresented class.
5.  **Threshold met** (e.g., 100/100): **Validate** button lights up; click to run the offline eval (on the _labeled training/val sets_, keeping test as hold-out until the very end).

### Why this holds up later

*   You get a genuinely **unlabeled** test split while still tracking **intended class** for balancing and QA.
*   The alternation plan doesn’t collapse when the generator has a bad day for one class; the target-ratio nudge keeps you on track.
*   Everything is enforceable at the API layer, so the UI can’t accidentally write labels into `test/`.

### Optional niceties (if you’ve got the time)

*   **Per-class caps** to stop overshooting (e.g., hard-stop at 110/110).
*   **Stratified counters**: small chips for lighting/angle (morning/afternoon, front/¾ profile) so your test set stays diverse, not just balanced.
*   **One-click “Retry same intent”** on reject, reusing the previous prompt with a new seed.

Net: your process is solid. Do the label-NULL rule on `test/`, add a gentle auto-balance, and wire the counters/threshold into the UI. That’ll give you a clean, 50/50 blind set without surprises later.

## Prompt:
given the updates explained in the following chats titled 'Video labeling 50/50 workflow' and 'Video labeling workflow,' update to the requirements_08.4.2.md file and perhaps the AGENTS.md file.

## Response:
Let’s start with a clean, version-controlled delta.  
Below are two concise but complete patches—one for **requirements\_08.4.2.md** and one for **AGENTS.md**—that bring them in line with the 50/50, user-balanced, _unlabeled test-set_ workflow you just defined.

* * *

✅ Patch 1 — `requirements_08.4.2.md` (append or replace “Video Labeling and Test Split” section)
------------------------------------------------------------------------------------------------

```markdown
### 4.3  Video Labeling and Test Split Workflow

#### Overview
All video data shall be stored under the canonical media root on the SSD:
```

/media/project\_data/reachy\_emotion/videos/  
├── temp/ # newly generated, pending user review  
├── train/ # labeled, training-ready videos  
└── test/ # blind hold-out, unlabeled videos

```

#### Labeling Rules
1. **Training videos** must include an explicit `label` value (`happy` or `sad`) in the Postgres `videos` table at the moment they are accepted into `/videos/train/`.
2. **Test videos** must carry **no label** (`label IS NULL`) to preserve a true blind evaluation split.
3. Each test video retains its **intended_emotion** (what the user requested during generation) as metadata only, not as a ground-truth label.

#### 50/50 Balancing Logic
- The UI shall maintain two counters—**happy** and **sad**—representing accepted test videos.
- The generator alternates `intended_emotion` automatically to maintain a **target ratio of 0.5 ± 0.05**.
- The system must **prevent overshoot** of either class beyond the allowed tolerance.
- Only **accepted** clips (after user review) increment counters. Rejected clips are deleted or archived and do not affect balance.

#### Validation Readiness
- The “Validate Model” button in the web UI remains disabled until the test-set counters satisfy the configured threshold:
```

min(happy\_count, sad\_count) >= TEST\_MIN\_PER\_CLASS

````
- When thresholds are met, the backend may launch model evaluation on the labeled validation data; the `/videos/test/` split remains untouched until final scoring.

#### API Contract
| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/api/generate` | POST | Generate a new synthetic video with field `intended_emotion` = "happy" or "sad". |
| `/api/test/accept` | POST | Atomically move from `/temp` → `/test`. Enforces `label IS NULL`. Returns updated counts. |
| `/api/test/reject` | POST | Delete or archive the clip without incrementing counters. |
| `/api/test/counts` | GET | Return counts per `intended_emotion` and current target ratio. |
| `/api/validate/run` | POST | Trigger model validation only after balance condition is met. |

#### Database Constraints
```sql
ALTER TABLE videos ADD CONSTRAINT chk_split_label
CHECK (
  (split='train' AND label IS NOT NULL)
  OR (split='test' AND label IS NULL)
);
````

This guarantees that “test” remains unlabeled, while “train” remains labeled.

#### Audit & Dedupe

Every generated video must include `sha256`, `size_bytes`, and `generator` metadata.  
Duplicate detection occurs before acceptance into any split.

````

---

## ✅ Patch 2 — `AGENTS.md` (add/modify relevant agents)

```markdown
### Agent 2 — Labeling Agent
**Purpose:**  
Manage user-assisted classification and dataset promotion.

**Updated Responsibilities (v08.4.2):**
- Maintain training split integrity (`videos/train/`) by ensuring all accepted items carry a valid label (`happy` or `sad`).
- Enforce the **no-label rule** for the `test` split.
- Interface with the web UI to update per-class counts and 50/50 balance status.
- Coordinate with the Database API to apply the `chk_split_label` constraint and maintain per-split quotas.
- Log each promotion event (`temp → train` or `temp → test`) with `intended_emotion`, timestamp, and `sha256`.

---

### Agent 3 — Promotion / Curation Agent
**Purpose:**  
Oversee controlled movement of media between filesystem stages.

**Updated Responsibilities:**
- Allow promotion to `videos/test/` only through the Labeling Agent interface after user acceptance.
- Verify `label IS NULL` for all test items.
- Prevent class imbalance by checking counters before each move.
- Update the Postgres `split` field transactionally with the filesystem move.
- Notify the UI of the updated ratio and readiness status (via websocket or polling).

---

### Agent 6 — Evaluation Agent
**Purpose:**  
Run validation jobs once the test set is balanced.

**Updated Responsibilities:**
- Confirm `min(happy_count, sad_count) >= TEST_MIN_PER_CLASS` before triggering TAO/DeepStream validation.
- Reference test videos by file path only; never attach or infer labels internally.
- Produce final confusion matrix and accuracy metrics using the *labeled validation split*, keeping `videos/test/` untouched for the final report.

---

### Optional Future Agent — Generation Balancer (sub-module)
If automated balancing is required beyond manual UI control, a small sub-agent may monitor test-set ratios and bias subsequent generation prompts accordingly.
````

* * *

### Summary

*   `requirements_08.4.2.md` gains the **formal workflow definition, balance rule, DB constraint, and API spec**.
*   `AGENTS.md` gains refined duties for **Labeling**, **Promotion**, and **Evaluation** Agents plus an optional **Generation Balancer**.

Would you like me to add a short YAML or JSON block for `TEST_MIN_PER_CLASS` and ratio tolerance (so it can be loaded by both the FastAPI backend and n8n workflow)?



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)