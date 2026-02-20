# Module 4: Stored Procedures & Business Logic

**Duration**: 3 hours
**Prerequisites**: Modules 1-3
**Goal**: Understand and use the stored procedures that implement Reachy's business logic

> **Architecture Note (v08.4.2)**
>
> - **Authoritative schema**: `apps/api/app/db/models.py`, `enums.py`, and the Alembic migration
>   `202510280000_initial_schema.py`. These files drive the production database and the Python
>   services (`PromoteService`, `VideoRepository`, etc.).
> - **Legacy helper SQL**: The stored procedures below live in
>   `alembic/versions/002_stored_procedures.sql`. They are optional utilities for ad-hoc analysis
>   and experimentation. The runtime code path does **not** call them.
>
> Recommended workflow:
>
> 1. Run Alembic so the schema defined by the ORM exists:  
>    `alembic -c apps/api/app/db/alembic/alembic.ini upgrade head`
> 2. (Optional) Load the legacy procedures for manual use:  
>    `psql -U reachy_app -d reachy_local -f alembic/versions/002_stored_procedures.sql`

---

## Learning Objectives

By the end of this module, you will be able to:
1. Explain what stored procedures are and why we use them
2. Call each of the 5 main stored procedures
3. Understand idempotency and safe retry patterns
4. Read and modify PL/pgSQL code
5. Debug stored procedure issues
6. Understand when to use stored procedures vs Python services

---

## Lesson 4.1: Introduction to Stored Procedures (30 minutes)

### What Are Stored Procedures?

A **stored procedure** (or **function** in PostgreSQL) is code that runs inside the database server:

```
┌─────────────────────────────────────────────────────────────────────┐
│                   WITHOUT STORED PROCEDURES                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Python App                              PostgreSQL                 │
│   ┌────────────┐                         ┌────────────┐             │
│   │ 1. Query   │ ──── SELECT ──────────▶ │            │             │
│   │ 2. Process │ ◀─── Results ────────── │            │             │
│   │ 3. Update  │ ──── UPDATE ──────────▶ │            │             │
│   │ 4. Log     │ ──── INSERT ──────────▶ │            │             │
│   └────────────┘                         └────────────┘             │
│         │                                                           │
│         ▼                                                           │
│   4 network round-trips = SLOW                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    WITH STORED PROCEDURES                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Python App                              PostgreSQL                 │
│   ┌────────────┐                         ┌────────────────┐         │
│   │ Call func  │ ──── CALL ────────────▶ │ 1. Query       │         │
│   │            │                         │ 2. Process     │         │
│   │            │                         │ 3. Update      │         │
│   │ Get result │ ◀─── Result ─────────── │ 4. Log         │         │
│   └────────────┘                         └────────────────┘         │
│         │                                                           │
│         ▼                                                           │
│   1 network round-trip = FAST                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Why Use Stored Procedures?

| Benefit | Explanation |
|---------|-------------|
| **Performance** | Multiple operations in one network call |
| **Consistency** | Same logic enforced regardless of caller |
| **Atomicity** | All-or-nothing execution within transaction |
| **Security** | Grant EXECUTE without granting direct table access |
| **Maintainability** | Change logic in one place |

### PL/pgSQL Basics

PostgreSQL uses **PL/pgSQL** for stored procedures:

```sql
CREATE OR REPLACE FUNCTION greet(name TEXT)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    message TEXT;
BEGIN
    message := 'Hello, ' || name || '!';
    RETURN message;
END;
$$;

-- Call it:
SELECT greet('Developer');
-- Returns: 'Hello, Developer!'
```

**Key Syntax:**
- `CREATE OR REPLACE FUNCTION` - Defines the function
- `RETURNS` - What type it returns
- `LANGUAGE plpgsql` - Which language
- `AS $$ ... $$` - Function body between dollar signs
- `DECLARE` - Variable declarations
- `BEGIN ... END;` - Code block

**Source File**: `alembic/versions/002_stored_procedures.sql` (362 lines)

---

## Lesson 4.2: The Trigger Function (20 minutes)

### touch_updated_at()

**Source**: `002_stored_procedures.sql` lines 5-17

This function automatically updates the `updated_at` column whenever a row is modified:

```sql
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;
```

**How Triggers Work:**

```sql
-- Create trigger on video table
CREATE TRIGGER trg_video_updated_at
    BEFORE UPDATE ON video
    FOR EACH ROW
    EXECUTE FUNCTION touch_updated_at();
```

When you do:
```sql
UPDATE video SET label = 'happy' WHERE video_id = 'abc';
```

PostgreSQL automatically:
1. Intercepts the UPDATE
2. Calls `touch_updated_at()`
3. Sets `NEW.updated_at = now()`
4. Proceeds with the UPDATE

**Trigger Variables:**
- `NEW` - The row being inserted/updated (new values)
- `OLD` - The row before update (old values)
- `TG_OP` - The operation: 'INSERT', 'UPDATE', 'DELETE'

---

## Lesson 4.3: get_class_distribution() (30 minutes)

> **Current workflow note**
>
> For active training runs, videos are promoted directly to `train/<label>`, then frame datasets are built per run (`train/epoch_XX/<label>`). Use `split = 'train'` for current distribution checks. `dataset_all` usage in this module reflects legacy helper SQL behavior.

### Purpose

Returns statistics about video distribution across emotion classes.

**Source**: `002_stored_procedures.sql` lines 35-80

### Signature

```sql
CREATE OR REPLACE FUNCTION get_class_distribution(
    p_split video_split DEFAULT NULL
)
RETURNS TABLE (
    split         video_split,
    label         emotion_label,
    count         BIGINT,
    percentage    NUMERIC(5,2),
    avg_duration  NUMERIC(10,2),
    total_size_mb NUMERIC(15,2)
)
```

### Usage

```sql
-- All splits
SELECT * FROM get_class_distribution();

-- Specific split
SELECT * FROM get_class_distribution('train');
```

### Example Output

```
 split | label   | count | percentage | avg_duration | total_size_mb
-------+---------+-------+------------+--------------+---------------
 train | happy   |   450 |      48.39 |         5.23 |       2340.12
 train | sad     |   480 |      51.61 |         5.18 |       2501.45
```

### Code Walkthrough

```sql
CREATE OR REPLACE FUNCTION get_class_distribution(
    p_split video_split DEFAULT NULL  -- Optional filter
)
RETURNS TABLE (
    -- Columns the function returns
    split         video_split,
    label         emotion_label,
    count         BIGINT,
    percentage    NUMERIC(5,2),
    avg_duration  NUMERIC(10,2),
    total_size_mb NUMERIC(15,2)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH counts AS (
        SELECT
            v.split,
            v.label,
            COUNT(*) AS cnt,
            AVG(v.duration_sec) AS avg_dur,
            SUM(v.size_bytes) / 1048576.0 AS total_mb
        FROM video v
        WHERE v.deleted_at IS NULL           -- Exclude soft-deleted
          AND v.label IS NOT NULL            -- Only labeled videos
          AND (p_split IS NULL OR v.split = p_split)  -- Filter if specified
        GROUP BY v.split, v.label
    ),
    totals AS (
        SELECT split, SUM(cnt) AS total_cnt
        FROM counts
        GROUP BY split
    )
    SELECT
        c.split,
        c.label,
        c.cnt,
        ROUND(c.cnt * 100.0 / t.total_cnt, 2) AS percentage,
        ROUND(c.avg_dur, 2) AS avg_duration,
        ROUND(c.total_mb, 2) AS total_size_mb
    FROM counts c
    JOIN totals t ON c.split = t.split
    ORDER BY c.split, c.label;
END;
$$;
```

**Key Concepts:**
- `RETURNS TABLE` - Returns multiple rows with defined columns
- `RETURN QUERY` - Execute query and return results
- `WITH ... AS` - Common Table Expression (CTE)
- `p_split IS NULL OR ...` - Optional parameter handling

---

## Lesson 4.4: check_dataset_balance() (30 minutes)

### Purpose

Checks if the dataset is balanced enough for training (minimum samples per class, acceptable imbalance ratio).

**Source**: `002_stored_procedures.sql` lines 85-150

### Signature

```sql
CREATE OR REPLACE FUNCTION check_dataset_balance(
    p_min_samples INTEGER DEFAULT 100,  -- Minimum per class
    p_max_ratio NUMERIC DEFAULT 1.5     -- Max imbalance ratio
)
RETURNS TABLE (
    balanced         BOOLEAN,
    total_samples    BIGINT,
    min_class        emotion_label,
    min_count        BIGINT,
    max_class        emotion_label,
    max_count        BIGINT,
    imbalance_ratio  NUMERIC(5,2),
    recommendation   TEXT
)
```

### Usage

```sql
-- Default: 100 samples min, 1.5 ratio max
SELECT * FROM check_dataset_balance();

-- Stricter requirements
SELECT * FROM check_dataset_balance(200, 1.2);

-- Lenient requirements
SELECT * FROM check_dataset_balance(50, 2.0);
```

### Example Output

```
 balanced | total_samples | min_class | min_count | max_class | max_count | imbalance_ratio | recommendation
----------+---------------+-----------+-----------+-----------+-----------+-----------------+----------------------------------
 TRUE     |           930 | happy     |       450 | sad       |       480 |            1.07 | Dataset is balanced and ready for training
```

### Code Walkthrough

```sql
CREATE OR REPLACE FUNCTION check_dataset_balance(
    p_min_samples INTEGER DEFAULT 100,
    p_max_ratio NUMERIC DEFAULT 1.5
)
RETURNS TABLE (...)
LANGUAGE plpgsql
AS $$
DECLARE
    v_min_class emotion_label;
    v_max_class emotion_label;
    v_min_count BIGINT;
    v_max_count BIGINT;
    v_total BIGINT;
    v_ratio NUMERIC;
    v_balanced BOOLEAN;
    v_recommendation TEXT;
BEGIN
    -- Find class with minimum samples
    SELECT label, COUNT(*)
    INTO v_min_class, v_min_count
    FROM video
    WHERE split = 'dataset_all' AND label IS NOT NULL AND deleted_at IS NULL
    GROUP BY label
    ORDER BY COUNT(*) ASC
    LIMIT 1;

    -- Find class with maximum samples
    SELECT label, COUNT(*)
    INTO v_max_class, v_max_count
    FROM video
    WHERE split = 'dataset_all' AND label IS NOT NULL AND deleted_at IS NULL
    GROUP BY label
    ORDER BY COUNT(*) DESC
    LIMIT 1;

    -- Calculate totals
    SELECT COUNT(*)
    INTO v_total
    FROM video
    WHERE split = 'dataset_all' AND label IS NOT NULL AND deleted_at IS NULL;

    -- Calculate imbalance ratio
    v_ratio := CASE WHEN v_min_count > 0
               THEN v_max_count::NUMERIC / v_min_count
               ELSE 999.0 END;

    -- Determine if balanced
    v_balanced := (v_min_count >= p_min_samples) AND (v_ratio <= p_max_ratio);

    -- Generate recommendation
    IF v_balanced THEN
        v_recommendation := 'Dataset is balanced and ready for training';
    ELSIF v_min_count < p_min_samples THEN
        v_recommendation := format(
            'Need at least %s samples per class. %s has only %s.',
            p_min_samples, v_min_class, v_min_count
        );
    ELSE
        v_recommendation := format(
            'Imbalance ratio %.2f exceeds %.2f. Consider augmenting %s class.',
            v_ratio, p_max_ratio, v_min_class
        );
    END IF;

    -- Return single row
    RETURN QUERY SELECT
        v_balanced,
        v_total,
        v_min_class,
        v_min_count,
        v_max_class,
        v_max_count,
        ROUND(v_ratio, 2),
        v_recommendation;
END;
$$;
```

**Key Concepts:**
- `DECLARE` - Variable declarations
- `SELECT ... INTO` - Assign query result to variables
- `IF ... ELSIF ... ELSE ... END IF;` - Conditional logic
- `format()` - String formatting with placeholders

---

## Lesson 4.5: promote_video_safe() (45 minutes)

### Purpose

Safely promotes a video from one split to another with full validation, idempotency, and audit logging.

**Source**: `002_stored_procedures.sql` lines 155-260

### Signature

```sql
CREATE OR REPLACE FUNCTION promote_video_safe(
    p_video_id        UUID,
    p_dest_split      video_split,
    p_label           emotion_label DEFAULT NULL,
    p_user_id         VARCHAR(255) DEFAULT NULL,
    p_idempotency_key VARCHAR(64) DEFAULT NULL,
    p_dry_run         BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    success       BOOLEAN,
    video_id      UUID,
    from_split    video_split,
    to_split      video_split,
    label         emotion_label,
    message       TEXT
)
```

### Usage

```sql
-- Promote video directly to train with label
SELECT * FROM promote_video_safe(
    '550e8400-e29b-41d4-a716-446655440000',  -- video_id
    'train',                                  -- destination
    'happy',                                  -- label
    'alice@example.com',                      -- user
    'promo-2025-01-05-001'                   -- idempotency key
);

-- Dry run (preview without executing)
SELECT * FROM promote_video_safe(
    '550e8400-e29b-41d4-a716-446655440000',
    'train',
    'happy',
    'alice@example.com',
    'promo-2025-01-05-001',
    TRUE  -- dry_run
);

-- Move to test split (no label required)
SELECT * FROM promote_video_safe(
    '550e8400-e29b-41d4-a716-446655440000',
    'test'
);
```

### Example Output

```
 success | video_id                             | from_split | to_split    | label | message
---------+--------------------------------------+------------+-------------+-------+---------
 TRUE    | 550e8400-e29b-41d4-a716-446655440000 | temp       | train       | happy | Video promoted successfully
```

### Idempotency Explained

**Idempotency** means: "Running the same operation multiple times has the same effect as running it once."

```sql
-- First call: Executes and returns success
SELECT * FROM promote_video_safe(..., p_idempotency_key := 'key-123');
-- success = TRUE, message = 'Video promoted successfully'

-- Second call with same key: Returns previous result without re-executing
SELECT * FROM promote_video_safe(..., p_idempotency_key := 'key-123');
-- success = TRUE, message = 'Duplicate request: already processed'
```

**Why idempotency matters:**
- Network failures may cause retries
- User may click button twice
- Prevents duplicate promotions

### Code Walkthrough (Simplified)

```sql
CREATE OR REPLACE FUNCTION promote_video_safe(
    p_video_id UUID,
    p_dest_split video_split,
    p_label emotion_label DEFAULT NULL,
    p_user_id VARCHAR(255) DEFAULT NULL,
    p_idempotency_key VARCHAR(64) DEFAULT NULL,
    p_dry_run BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (...)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_split video_split;
    v_success BOOLEAN := FALSE;
    v_message TEXT;
BEGIN
    -- 1. CHECK IDEMPOTENCY
    IF p_idempotency_key IS NOT NULL THEN
        -- Try to find existing log entry with same key
        SELECT pl.success, 'Duplicate request: already processed'
        INTO v_success, v_message
        FROM promotion_log pl
        WHERE pl.idempotency_key = p_idempotency_key;

        IF FOUND THEN
            -- Return cached result
            RETURN QUERY SELECT v_success, ...;
            RETURN;
        END IF;
    END IF;

    -- 2. VALIDATE VIDEO EXISTS
    SELECT split INTO v_current_split
    FROM video
    WHERE video.video_id = p_video_id AND deleted_at IS NULL;

    IF NOT FOUND THEN
        v_message := 'Video not found or deleted';
        -- Log failure
        INSERT INTO promotion_log (...) VALUES (...);
        RETURN QUERY SELECT FALSE, ...;
        RETURN;
    END IF;

    -- 3. VALIDATE BUSINESS RULES
    -- train (and legacy dataset_all) require label
    IF p_dest_split IN ('dataset_all', 'train') AND p_label IS NULL THEN
        v_message := 'Label required for ' || p_dest_split;
        -- Log failure
        INSERT INTO promotion_log (...) VALUES (...);
        RETURN QUERY SELECT FALSE, ...;
        RETURN;
    END IF;

    -- test, temp, purged must NOT have label
    IF p_dest_split IN ('test', 'temp', 'purged') AND p_label IS NOT NULL THEN
        v_message := 'Label not allowed for ' || p_dest_split;
        -- Log failure
        INSERT INTO promotion_log (...) VALUES (...);
        RETURN QUERY SELECT FALSE, ...;
        RETURN;
    END IF;

    -- 4. DRY RUN CHECK
    IF p_dry_run THEN
        v_message := 'Dry run: would promote to ' || p_dest_split;
        INSERT INTO promotion_log (..., dry_run := TRUE) VALUES (...);
        RETURN QUERY SELECT TRUE, ...;
        RETURN;
    END IF;

    -- 5. EXECUTE PROMOTION
    UPDATE video
    SET split = p_dest_split, label = p_label
    WHERE video.video_id = p_video_id;

    -- 6. LOG SUCCESS
    INSERT INTO promotion_log (
        video_id, from_split, to_split, label,
        user_id, idempotency_key, success
    ) VALUES (
        p_video_id, v_current_split, p_dest_split, p_label,
        p_user_id, p_idempotency_key, TRUE
    );

    -- 7. RETURN RESULT
    v_success := TRUE;
    v_message := 'Video promoted successfully';
    RETURN QUERY SELECT v_success, p_video_id, v_current_split, p_dest_split, p_label, v_message;
END;
$$;
```

**Key Concepts:**
- `IF FOUND THEN` - Check if previous query returned rows
- `RETURN QUERY SELECT ...` - Return a row
- `RETURN;` - Exit function early
- All operations in same transaction - atomic!

---

## Lesson 4.6: create_training_run_with_sampling() (30 minutes)

### Purpose

Creates a training run and automatically samples videos into train/test splits.

**Source**: `002_stored_procedures.sql` lines 265-362

### Signature

```sql
CREATE OR REPLACE FUNCTION create_training_run_with_sampling(
    p_strategy VARCHAR(100) DEFAULT 'balanced_random',
    p_train_fraction NUMERIC DEFAULT 0.7,
    p_seed BIGINT DEFAULT NULL
)
RETURNS UUID  -- Returns the new run_id
```

### Usage

```sql
-- Default: 70/30 split, random seed
SELECT create_training_run_with_sampling();

-- 80/20 split with fixed seed (reproducible)
SELECT create_training_run_with_sampling('balanced_random', 0.8, 12345);

-- Stratified sampling (preserves class proportions)
SELECT create_training_run_with_sampling('stratified', 0.75, 42);
```

### What It Does

```
Input: p_strategy = 'balanced_random', p_train_fraction = 0.7, p_seed = 42

Step 1: Calculate dataset hash (legacy helper SQL path)
        SHA256 of all video_ids in dataset_all

Step 2: Create training_run record
        run_id = new UUID
        strategy = 'balanced_random'
        train_fraction = 0.7
        test_fraction = 0.3
        seed = 42
        status = 'sampling'

Step 3: Set random seed for reproducibility
        PERFORM setseed(42 / 2147483647)

Step 4: Sample videos
        For each video in dataset_all (legacy staging split):
          - Generate random number
          - If random < 0.7 → assign to 'train'
          - Else → assign to 'test'

Step 5: Insert training_selection records
        (run_id, video_id, target_split)

Step 6: Update status
        status = 'pending' (ready for training)

Output: run_id UUID
```

### Code Walkthrough (Key Parts)

```sql
CREATE OR REPLACE FUNCTION create_training_run_with_sampling(
    p_strategy VARCHAR(100) DEFAULT 'balanced_random',
    p_train_fraction NUMERIC DEFAULT 0.7,
    p_seed BIGINT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_id UUID;
    v_seed BIGINT;
    v_dataset_hash CHAR(64);
BEGIN
    -- Generate seed if not provided
    v_seed := COALESCE(p_seed, (random() * 2147483647)::BIGINT);

    -- Calculate dataset hash for reproducibility
    SELECT encode(sha256(string_agg(video_id::TEXT, '' ORDER BY video_id)::BYTEA), 'hex')
    INTO v_dataset_hash
    FROM video
    WHERE split = 'dataset_all' AND deleted_at IS NULL;

    -- Create training run
    INSERT INTO training_run (strategy, train_fraction, test_fraction, seed, dataset_hash, status)
    VALUES (p_strategy, p_train_fraction, 1.0 - p_train_fraction, v_seed, v_dataset_hash, 'sampling')
    RETURNING run_id INTO v_run_id;

    -- Set random seed for reproducibility
    PERFORM setseed(v_seed::DOUBLE PRECISION / 2147483647);

    -- Sample videos (simplified - see note about stratification bug)
    INSERT INTO training_selection (run_id, video_id, target_split)
    SELECT
        v_run_id,
        video_id,
        CASE WHEN random() < p_train_fraction
             THEN 'train'::video_split
             ELSE 'test'::video_split
        END
    FROM video
    WHERE split = 'dataset_all'
      AND label IS NOT NULL
      AND deleted_at IS NULL;

    -- Update status
    UPDATE training_run SET status = 'pending' WHERE run_id = v_run_id;

    RETURN v_run_id;
END;
$$;
```

---

> 🟠 **Known Issue #12: Stratification Logic Bug (Open — Legacy Path)**
>
> The `create_training_run_with_sampling()` function doesn't truly stratify by class.
>
> **Current behavior**: Applies `random() < train_fraction` globally across all videos.
>
> **Expected behavior**: Apply the fraction within each label group to preserve class proportions.
>
> **Example Problem**:
> - Dataset: 100 happy, 20 sad
> - With 70/30 split applied globally: ~70 happy + ~14 sad in train
> - Class imbalance is preserved but not guaranteed per-class
>
> **Impact**: Potential class imbalance in train/test splits, especially with small datasets.
>
> **Note**: This bug exists in the **legacy SQL stored procedure** only. The active runtime
> path now prepares training datasets via frame extraction from `train/<label>` videos into
> `train/epoch_XX/<label>` plus manifests/hash metadata. This stored procedure remains for
> manual/ad-hoc compatibility only.
>
> **Fix** (if you want to correct the stored procedure): Modify the sampling logic to iterate per-label:
> ```sql
> -- Stratified sampling (per-label)
> INSERT INTO training_selection (run_id, video_id, target_split)
> SELECT
>     v_run_id,
>     video_id,
>     CASE WHEN row_num <= (label_count * p_train_fraction)
>          THEN 'train'::video_split
>          ELSE 'test'::video_split
>     END
> FROM (
>     SELECT video_id, label,
>            ROW_NUMBER() OVER (PARTITION BY label ORDER BY random()) as row_num,
>            COUNT(*) OVER (PARTITION BY label) as label_count
>     FROM video
>     WHERE split = 'dataset_all' AND label IS NOT NULL
> ) ranked;
> ```
>
> See: `docs/database/07-KNOWN-ISSUES.md` for details.

---

## Lesson 4.7: Debugging Stored Procedures (15 minutes)

### Using RAISE for Debugging

```sql
CREATE OR REPLACE FUNCTION debug_example(p_video_id UUID)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_split video_split;
BEGIN
    -- Log a notice (visible in psql)
    RAISE NOTICE 'Looking up video: %', p_video_id;

    SELECT split INTO v_split FROM video WHERE video_id = p_video_id;

    IF NOT FOUND THEN
        -- Raise an exception (aborts function)
        RAISE EXCEPTION 'Video % not found', p_video_id;
    END IF;

    RAISE NOTICE 'Found video with split: %', v_split;

    -- Different log levels:
    -- RAISE DEBUG 'detailed info';    -- Usually not shown
    -- RAISE LOG 'logged info';        -- Goes to server log
    -- RAISE INFO 'informational';     -- Shown to client
    -- RAISE NOTICE 'notice';          -- Shown to client
    -- RAISE WARNING 'warning';        -- Shown to client
    -- RAISE EXCEPTION 'error';        -- Aborts transaction!
END;
$$;
```

### Viewing Notices in psql

```bash
# Enable notices in psql
\set VERBOSITY verbose

# Run function
SELECT debug_example('550e8400-e29b-41d4-a716-446655440000');

# Output:
# NOTICE:  Looking up video: 550e8400-e29b-41d4-a716-446655440000
# NOTICE:  Found video with split: temp
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ERROR: function X does not exist` | Wrong name or parameters | Check function signature |
| `ERROR: column "X" does not exist` | Typo in column name | Check table definition |
| `ERROR: invalid input value for enum` | Invalid enum value | Check enum definition |
| `ERROR: division by zero` | Dividing by zero | Add null check |
| `ERROR: duplicate key violates unique constraint` | Idempotency key reused | Expected behavior! |

---

## Knowledge Check

1. What is the advantage of using a stored procedure instead of multiple SQL queries from Python?

2. What does `RETURNS TABLE` mean in a function definition?

3. How does `promote_video_safe()` achieve idempotency?

4. If you call `promote_video_safe()` with `p_dry_run = TRUE`, what happens to the video?

5. Why does `create_training_run_with_sampling()` use `setseed()`?

<details>
<summary>Click to see answers</summary>

1. Single network round-trip (faster), consistent logic enforcement, atomic execution within transaction.

2. The function returns multiple rows with the defined columns, like a virtual table.

3. By checking for an existing `promotion_log` entry with the same `idempotency_key` before executing. If found, returns cached result.

4. Nothing changes in the database. The function validates the operation and logs to `promotion_log` with `dry_run = TRUE`, but doesn't update the video.

5. To ensure reproducible random sampling. Given the same seed, the same random sequence is generated, so the same videos will be assigned to train/test.

</details>

---

## Hands-On Exercise 4

### Setup

```sql
-- Insert test videos
INSERT INTO video (file_path, split, label, size_bytes) VALUES
    ('videos/sp_test/happy_001.mp4', 'train', 'happy', 1000000),
    ('videos/sp_test/happy_002.mp4', 'train', 'happy', 1100000),
    ('videos/sp_test/sad_001.mp4', 'train', 'sad', 1200000),
    ('videos/sp_test/sad_002.mp4', 'train', 'sad', 1300000),
    ('videos/sp_test/temp_001.mp4', 'temp', NULL, 500000);
```

### Task 1: Check Class Distribution

```sql
-- View distribution
SELECT * FROM get_class_distribution('train');

-- Expected: 2 happy, 2 sad
```

### Task 2: Check Dataset Balance

```sql
-- Check with default requirements (100 min, 1.5 ratio)
SELECT * FROM check_dataset_balance();
-- Expected: balanced = FALSE (only 2 samples per class)

-- Check with lenient requirements
SELECT * FROM check_dataset_balance(2, 2.0);
-- Expected: balanced = TRUE
```

### Task 3: Promote a Video

```sql
-- Get the video_id of the temp video
SELECT video_id FROM video WHERE file_path = 'videos/sp_test/temp_001.mp4';

-- Dry run promotion
SELECT * FROM promote_video_safe(
    'VIDEO_ID_HERE',  -- Replace with actual UUID
    'train',
    'happy',
    'student@example.com',
    'exercise-4-001',
    TRUE  -- dry_run
);

-- Actual promotion
SELECT * FROM promote_video_safe(
    'VIDEO_ID_HERE',
    'train',
    'happy',
    'student@example.com',
    'exercise-4-001'  -- Same key, no dry_run
);

-- Verify idempotency (run again)
SELECT * FROM promote_video_safe(
    'VIDEO_ID_HERE',
    'train',
    'happy',
    'student@example.com',
    'exercise-4-001'
);
-- Should return cached result
```

### Task 4: Create Training Run

```sql
-- Create training run with 70/30 split
SELECT create_training_run_with_sampling('balanced_random', 0.7, 42);
-- Note the returned run_id

-- Check the selections
SELECT ts.target_split, v.file_path, v.label
FROM training_selection ts
JOIN video v ON ts.video_id = v.video_id
WHERE ts.run_id = 'RUN_ID_HERE'
ORDER BY ts.target_split, v.label;
```

### Task 5: View Promotion Log

```sql
SELECT video_id, from_split, to_split, label, success, dry_run, promoted_at
FROM promotion_log
ORDER BY promoted_at DESC
LIMIT 10;
```

---

## Summary

In this module, you learned:

- ✅ What stored procedures are and why we use them
- ✅ How triggers automatically update timestamps
- ✅ How to check class distribution and dataset balance
- ✅ Safe video promotion with idempotency
- ✅ Automated training run creation with sampling
- ✅ Debugging stored procedures

**Next**: [Module 5: Python ORM with SQLAlchemy](./05-MODULE-SQLALCHEMY-ORM.md)
