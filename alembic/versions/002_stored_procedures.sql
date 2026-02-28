-- DEPRECATED: This file is retained for historical reference only.
-- Schema and stored procedures are now managed by SQLAlchemy models + Alembic migrations.
-- See: apps/api/app/db/models.py
-- See: apps/api/app/db/alembic/versions/
-- DO NOT use this file to create or modify the database schema.
-- Several stored procedures below reference the deprecated 'dataset_all' split
-- which has been removed from the active schema.
--
-- Original header:
-- Stored Procedures for Business Logic
-- Run after Alembic migration (alembic upgrade head)
--
-- Column names align with SQLAlchemy models in apps/api/app/db/models.py:
--   promotion_log.intended_label  (not "label")
--   promotion_log.actor           (not "user_id")
--   promotion_log.created_at      (not "promoted_at")
--
-- Enum types are TEXT with CHECK constraints (native_enum=False in models),
-- so function signatures use TEXT instead of native PostgreSQL enum types.

BEGIN;

-- Get class distribution with statistics
CREATE OR REPLACE FUNCTION get_class_distribution(
    p_split TEXT DEFAULT NULL
)
RETURNS TABLE(
    split TEXT,
    label TEXT,
    count BIGINT,
    percentage NUMERIC(5,2),
    avg_duration NUMERIC(10,2),
    total_size_mb NUMERIC(10,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH stats AS (
        SELECT
            v.split,
            v.label,
            COUNT(*) as cnt,
            AVG(v.duration_sec) as avg_dur,
            SUM(v.size_bytes) / 1048576.0 as size_mb
        FROM video v
        WHERE v.deleted_at IS NULL
            AND v.label IS NOT NULL
            AND (p_split IS NULL OR v.split = p_split)
        GROUP BY v.split, v.label
    ),
    totals AS (
        SELECT s.split, SUM(s.cnt) as total
        FROM stats s
        GROUP BY s.split
    )
    SELECT
        s.split,
        s.label,
        s.cnt,
        ROUND(100.0 * s.cnt / t.total, 2),
        ROUND(s.avg_dur, 2),
        ROUND(s.size_mb, 2)
    FROM stats s
    JOIN totals t ON s.split = t.split
    ORDER BY s.split, s.label;
END;
$$ LANGUAGE plpgsql;

-- Check dataset balance
CREATE OR REPLACE FUNCTION check_dataset_balance(
    min_samples INTEGER DEFAULT 100,
    max_ratio NUMERIC DEFAULT 1.5
)
RETURNS TABLE(
    balanced BOOLEAN,
    total_samples BIGINT,
    min_class TEXT,
    min_count BIGINT,
    max_class TEXT,
    max_count BIGINT,
    imbalance_ratio NUMERIC(5,2),
    recommendation TEXT
) AS $$
DECLARE
    v_min_class TEXT;
    v_min_count BIGINT;
    v_max_class TEXT;
    v_max_count BIGINT;
    v_total BIGINT;
    v_ratio NUMERIC(5,2);
    v_balanced BOOLEAN;
    v_recommendation TEXT;
BEGIN
    -- Get min class count
    SELECT v.label, COUNT(*) INTO v_min_class, v_min_count
    FROM video v
    WHERE v.split = 'dataset_all'
        AND v.label IS NOT NULL
        AND v.deleted_at IS NULL
    GROUP BY v.label
    ORDER BY COUNT(*) ASC
    LIMIT 1;

    -- Get max class count
    SELECT v.label, COUNT(*) INTO v_max_class, v_max_count
    FROM video v
    WHERE v.split = 'dataset_all'
        AND v.label IS NOT NULL
        AND v.deleted_at IS NULL
    GROUP BY v.label
    ORDER BY COUNT(*) DESC
    LIMIT 1;

    -- Get total count
    SELECT COUNT(*) INTO v_total
    FROM video v
    WHERE v.split = 'dataset_all'
        AND v.label IS NOT NULL
        AND v.deleted_at IS NULL;

    -- Handle empty dataset
    IF v_total IS NULL OR v_total = 0 THEN
        RETURN QUERY SELECT
            FALSE,
            0::BIGINT,
            NULL::TEXT,
            0::BIGINT,
            NULL::TEXT,
            0::BIGINT,
            0::NUMERIC(5,2),
            'Dataset is empty. Add labeled videos to dataset_all'::TEXT;
        RETURN;
    END IF;

    -- Calculate ratio
    IF v_min_count > 0 THEN
        v_ratio := ROUND(v_max_count::NUMERIC / v_min_count, 2);
    ELSE
        v_ratio := 999.99;
    END IF;

    -- Check balance
    v_balanced := (v_min_count >= min_samples AND v_ratio <= max_ratio);

    -- Generate recommendation
    IF NOT v_balanced THEN
        IF v_min_count < min_samples THEN
            v_recommendation := FORMAT('Need %s more samples of class "%s"',
                                      min_samples - v_min_count, v_min_class);
        ELSE
            v_recommendation := FORMAT('Class imbalance too high. Generate more "%s" samples',
                                      v_min_class);
        END IF;
    ELSE
        v_recommendation := 'Dataset is balanced and ready for training';
    END IF;

    RETURN QUERY SELECT
        v_balanced,
        v_total,
        v_min_class,
        v_min_count,
        v_max_class,
        v_max_count,
        v_ratio,
        v_recommendation;
END;
$$ LANGUAGE plpgsql;

-- Promote video with full validation and idempotency
-- Column names match SQLAlchemy PromotionLog model:
--   intended_label (not label), actor (not user_id)
CREATE OR REPLACE FUNCTION promote_video_safe(
    p_video_id UUID,
    p_dest_split TEXT,
    p_label TEXT DEFAULT NULL,
    p_actor VARCHAR DEFAULT 'system',
    p_idempotency_key VARCHAR DEFAULT NULL,
    p_dry_run BOOLEAN DEFAULT FALSE
)
RETURNS TABLE(
    success BOOLEAN,
    message TEXT,
    old_split TEXT,
    new_split TEXT
) AS $$
DECLARE
    v_current_split TEXT;
    v_current_label TEXT;
    v_exists BOOLEAN;
BEGIN
    -- Check idempotency
    IF p_idempotency_key IS NOT NULL THEN
        SELECT EXISTS(
            SELECT 1 FROM promotion_log
            WHERE idempotency_key = p_idempotency_key AND promotion_log.success = TRUE
        ) INTO v_exists;

        IF v_exists THEN
            RETURN QUERY SELECT
                TRUE,
                'Promotion already completed (idempotent)'::TEXT,
                NULL::TEXT,
                p_dest_split;
            RETURN;
        END IF;
    END IF;

    -- Get current video info
    SELECT v.split, v.label INTO v_current_split, v_current_label
    FROM video v
    WHERE v.video_id = p_video_id::TEXT AND v.deleted_at IS NULL;

    IF NOT FOUND THEN
        -- Log failed attempt
        INSERT INTO promotion_log (
            video_id, from_split, to_split, intended_label, actor,
            idempotency_key, dry_run, success, error_message
        ) VALUES (
            p_video_id::TEXT, 'temp', p_dest_split, p_label, p_actor,
            p_idempotency_key, p_dry_run, FALSE, 'Video not found'
        );

        RETURN QUERY SELECT
            FALSE,
            'Video not found'::TEXT,
            NULL::TEXT,
            NULL::TEXT;
        RETURN;
    END IF;

    -- Validate promotion rules
    IF p_dest_split = 'dataset_all' AND p_label IS NULL THEN
        INSERT INTO promotion_log (
            video_id, from_split, to_split, actor,
            idempotency_key, dry_run, success, error_message
        ) VALUES (
            p_video_id::TEXT, v_current_split, p_dest_split, p_actor,
            p_idempotency_key, p_dry_run, FALSE, 'Label required for dataset_all'
        );

        RETURN QUERY SELECT
            FALSE,
            'Label required when promoting to dataset_all'::TEXT,
            v_current_split,
            NULL::TEXT;
        RETURN;
    END IF;

    -- Check if dry run
    IF p_dry_run THEN
        INSERT INTO promotion_log (
            video_id, from_split, to_split, intended_label, actor,
            idempotency_key, dry_run, success
        ) VALUES (
            p_video_id::TEXT, v_current_split, p_dest_split, p_label, p_actor,
            p_idempotency_key, TRUE, TRUE
        );

        RETURN QUERY SELECT
            TRUE,
            'Dry run successful - no changes made'::TEXT,
            v_current_split,
            p_dest_split;
        RETURN;
    END IF;

    -- Perform promotion
    UPDATE video
    SET
        split = p_dest_split,
        label = COALESCE(p_label, video.label),
        updated_at = NOW()
    WHERE video_id = p_video_id::TEXT;

    -- Log success
    INSERT INTO promotion_log (
        video_id, from_split, to_split, intended_label, actor,
        idempotency_key, dry_run, success
    ) VALUES (
        p_video_id::TEXT, v_current_split, p_dest_split, p_label, p_actor,
        p_idempotency_key, FALSE, TRUE
    );

    RETURN QUERY SELECT
        TRUE,
        FORMAT('Video promoted from %s to %s', v_current_split, p_dest_split)::TEXT,
        v_current_split,
        p_dest_split;
END;
$$ LANGUAGE plpgsql;

-- Create training run with automatic sampling
CREATE OR REPLACE FUNCTION create_training_run_with_sampling(
    p_strategy VARCHAR DEFAULT 'balanced_random',
    p_train_fraction NUMERIC DEFAULT 0.7,
    p_seed BIGINT DEFAULT NULL
)
RETURNS TEXT AS $$
DECLARE
    v_run_id TEXT;
    v_dataset_hash VARCHAR(64);
    v_seed BIGINT;
BEGIN
    -- Generate seed if not provided
    v_seed := COALESCE(p_seed, EXTRACT(EPOCH FROM NOW())::BIGINT);

    -- Calculate dataset hash
    SELECT encode(
        digest(
            string_agg(
                v.video_id || v.file_path || COALESCE(v.label, ''),
                '|' ORDER BY v.video_id
            ),
            'sha256'
        ),
        'hex'
    ) INTO v_dataset_hash
    FROM video v
    WHERE v.split = 'dataset_all' AND v.deleted_at IS NULL;

    -- Generate a UUID as text for run_id
    v_run_id := gen_random_uuid()::TEXT;

    -- Create run
    INSERT INTO training_run (
        run_id, strategy, train_fraction, test_fraction, seed, dataset_hash, status
    ) VALUES (
        v_run_id, p_strategy, p_train_fraction, 1.0 - p_train_fraction, v_seed,
        v_dataset_hash, 'sampling'
    );

    -- Perform stratified sampling
    PERFORM setseed(v_seed::DOUBLE PRECISION / 2147483647);

    -- Insert training samples
    INSERT INTO training_selection (run_id, video_id, target_split)
    SELECT
        v_run_id,
        v.video_id,
        CASE WHEN random() < p_train_fraction THEN 'train' ELSE 'test' END
    FROM video v
    WHERE v.split = 'dataset_all'
        AND v.label IS NOT NULL
        AND v.deleted_at IS NULL
    ORDER BY v.label, random();  -- Ensures stratification

    -- Update status
    UPDATE training_run
    SET status = 'pending'
    WHERE run_id = v_run_id;

    RETURN v_run_id;
END;
$$ LANGUAGE plpgsql;

-- Get training run details
CREATE OR REPLACE FUNCTION get_training_run_details(p_run_id TEXT)
RETURNS TABLE(
    run_id TEXT,
    status TEXT,
    strategy VARCHAR,
    train_count BIGINT,
    test_count BIGINT,
    dataset_hash VARCHAR,
    created_at TIMESTAMPTZ,
    metrics JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        tr.run_id,
        tr.status,
        tr.strategy,
        (SELECT COUNT(*) FROM training_selection ts
         WHERE ts.run_id = p_run_id AND ts.target_split = 'train') as train_count,
        (SELECT COUNT(*) FROM training_selection ts
         WHERE ts.run_id = p_run_id AND ts.target_split = 'test') as test_count,
        tr.dataset_hash,
        tr.created_at,
        tr.metrics
    FROM training_run tr
    WHERE tr.run_id = p_run_id;
END;
$$ LANGUAGE plpgsql;

COMMIT;
