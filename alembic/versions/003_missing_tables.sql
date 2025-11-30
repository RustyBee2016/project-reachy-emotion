-- Phase 3 Database Schema Migration
-- Missing tables required by n8n workflows (Agents 2, 7, 8, 9)
-- Run with: psql -d reachy_emotion -f 003_missing_tables.sql

BEGIN;

-- ============================================================================
-- Label Event Audit Table (Labeling Agent - Agent 2)
-- Tracks all labeling actions for audit and replay
-- ============================================================================
CREATE TABLE IF NOT EXISTS label_event (
    event_id BIGSERIAL PRIMARY KEY,
    video_id UUID REFERENCES video(video_id) ON DELETE SET NULL,
    label emotion_label NOT NULL,
    action VARCHAR(50) NOT NULL CHECK (action IN ('label_only', 'promote_train', 'promote_test', 'discard', 'relabel')),
    rater_id VARCHAR(255),
    notes TEXT,
    idempotency_key VARCHAR(64) UNIQUE,
    correlation_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_label_event_video ON label_event(video_id);
CREATE INDEX IF NOT EXISTS idx_label_event_created ON label_event(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_label_event_rater ON label_event(rater_id);
CREATE INDEX IF NOT EXISTS idx_label_event_idempotency ON label_event(idempotency_key);

COMMENT ON TABLE label_event IS 'Audit log for all labeling actions performed by human raters';
COMMENT ON COLUMN label_event.action IS 'Type of labeling action: label_only, promote_train, promote_test, discard, relabel';
COMMENT ON COLUMN label_event.idempotency_key IS 'Unique key to prevent duplicate processing of the same request';

-- ============================================================================
-- Deployment Log (Deployment Agent - Agent 7)
-- Tracks model deployments across shadow/canary/rollout stages
-- ============================================================================
CREATE TABLE IF NOT EXISTS deployment_log (
    id BIGSERIAL PRIMARY KEY,
    engine_path VARCHAR(500) NOT NULL,
    model_version VARCHAR(100),
    target_stage VARCHAR(50) NOT NULL CHECK (target_stage IN ('shadow', 'canary', 'rollout')),
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'deploying', 'success', 'failed', 'rolled_back')),
    metrics JSONB DEFAULT '{}',
    rollback_from VARCHAR(500),
    mlflow_run_id VARCHAR(255),
    gate_b_passed BOOLEAN,
    fps_measured NUMERIC(6,2),
    latency_p50_ms NUMERIC(8,2),
    latency_p95_ms NUMERIC(8,2),
    gpu_memory_gb NUMERIC(4,2),
    correlation_id UUID,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_deployment_stage ON deployment_log(target_stage);
CREATE INDEX IF NOT EXISTS idx_deployment_status ON deployment_log(status);
CREATE INDEX IF NOT EXISTS idx_deployment_time ON deployment_log(deployed_at DESC);
CREATE INDEX IF NOT EXISTS idx_deployment_mlflow ON deployment_log(mlflow_run_id);

COMMENT ON TABLE deployment_log IS 'Tracks all model deployments to Jetson across deployment stages';
COMMENT ON COLUMN deployment_log.target_stage IS 'Deployment stage: shadow (testing), canary (limited), rollout (production)';
COMMENT ON COLUMN deployment_log.gate_b_passed IS 'Whether Gate B on-device requirements were met';

-- ============================================================================
-- Audit Log (Privacy Agent - Agent 8)
-- General audit log for privacy-sensitive operations
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL DEFAULT 'video',
    entity_id UUID,
    reason TEXT,
    operator VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    correlation_id UUID
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_operator ON audit_log(operator);

COMMENT ON TABLE audit_log IS 'General audit log for privacy-sensitive operations (GDPR compliance)';
COMMENT ON COLUMN audit_log.action IS 'Action performed: purge, access, export, delete, etc.';
COMMENT ON COLUMN audit_log.entity_type IS 'Type of entity affected: video, user, model, etc.';

-- ============================================================================
-- Observability Samples (Observability Agent - Agent 9)
-- Time-series metrics storage for system monitoring
-- ============================================================================
CREATE TABLE IF NOT EXISTS obs_samples (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    src VARCHAR(100) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    value NUMERIC(15,4),
    labels JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_obs_ts ON obs_samples(ts DESC);
CREATE INDEX IF NOT EXISTS idx_obs_src_metric ON obs_samples(src, metric);
CREATE INDEX IF NOT EXISTS idx_obs_metric_ts ON obs_samples(metric, ts DESC);

-- Partition hint for future optimization (manual partitioning by month)
COMMENT ON TABLE obs_samples IS 'Time-series metrics from n8n, Media Mover, Gateway, and Jetson';
COMMENT ON COLUMN obs_samples.src IS 'Metric source: n8n, media_mover, gateway, jetson';
COMMENT ON COLUMN obs_samples.labels IS 'Additional metric labels in JSON format';

-- ============================================================================
-- Reconcile Report (Reconciler Agent - Agent 4)
-- Stores filesystem/database reconciliation reports
-- ============================================================================
CREATE TABLE IF NOT EXISTS reconcile_report (
    id BIGSERIAL PRIMARY KEY,
    run_at TIMESTAMPTZ DEFAULT NOW(),
    trigger_type VARCHAR(50) NOT NULL CHECK (trigger_type IN ('scheduled', 'manual', 'webhook')),
    orphan_count INTEGER NOT NULL DEFAULT 0,
    missing_count INTEGER NOT NULL DEFAULT 0,
    mismatch_count INTEGER NOT NULL DEFAULT 0,
    drift_detected BOOLEAN NOT NULL DEFAULT FALSE,
    auto_fixed BOOLEAN NOT NULL DEFAULT FALSE,
    details JSONB DEFAULT '{}',
    duration_ms INTEGER,
    correlation_id UUID
);

CREATE INDEX IF NOT EXISTS idx_reconcile_time ON reconcile_report(run_at DESC);
CREATE INDEX IF NOT EXISTS idx_reconcile_drift ON reconcile_report(drift_detected);

COMMENT ON TABLE reconcile_report IS 'Results of filesystem/database reconciliation runs';
COMMENT ON COLUMN reconcile_report.orphan_count IS 'Files on disk not in database';
COMMENT ON COLUMN reconcile_report.missing_count IS 'Database records with no file on disk';
COMMENT ON COLUMN reconcile_report.mismatch_count IS 'Files with mismatched metadata (size, hash)';

-- ============================================================================
-- Add 'purged' to video_split enum (required by Privacy Agent)
-- ============================================================================
DO $$
BEGIN
    -- Check if 'purged' already exists in the enum
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'purged' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'video_split')
    ) THEN
        ALTER TYPE video_split ADD VALUE 'purged';
    END IF;
EXCEPTION
    WHEN duplicate_object THEN
        -- Enum value already exists, ignore
        NULL;
END $$;

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to log label events with idempotency
CREATE OR REPLACE FUNCTION log_label_event(
    p_video_id UUID,
    p_label emotion_label,
    p_action VARCHAR,
    p_rater_id VARCHAR DEFAULT NULL,
    p_notes TEXT DEFAULT NULL,
    p_idempotency_key VARCHAR DEFAULT NULL,
    p_correlation_id UUID DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_event_id BIGINT;
BEGIN
    -- Check idempotency
    IF p_idempotency_key IS NOT NULL THEN
        SELECT event_id INTO v_event_id
        FROM label_event
        WHERE idempotency_key = p_idempotency_key;
        
        IF FOUND THEN
            RETURN v_event_id;  -- Return existing event ID
        END IF;
    END IF;
    
    -- Insert new event
    INSERT INTO label_event (
        video_id, label, action, rater_id, notes, 
        idempotency_key, correlation_id
    ) VALUES (
        p_video_id, p_label, p_action, p_rater_id, p_notes,
        p_idempotency_key, p_correlation_id
    ) RETURNING event_id INTO v_event_id;
    
    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- Function to log deployment with metrics
CREATE OR REPLACE FUNCTION log_deployment(
    p_engine_path VARCHAR,
    p_target_stage VARCHAR,
    p_model_version VARCHAR DEFAULT NULL,
    p_mlflow_run_id VARCHAR DEFAULT NULL,
    p_metrics JSONB DEFAULT '{}'
)
RETURNS BIGINT AS $$
DECLARE
    v_deployment_id BIGINT;
BEGIN
    INSERT INTO deployment_log (
        engine_path, target_stage, model_version, 
        mlflow_run_id, status, metrics
    ) VALUES (
        p_engine_path, p_target_stage, p_model_version,
        p_mlflow_run_id, 'pending', p_metrics
    ) RETURNING id INTO v_deployment_id;
    
    RETURN v_deployment_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update deployment status with Gate B metrics
CREATE OR REPLACE FUNCTION update_deployment_status(
    p_deployment_id BIGINT,
    p_status VARCHAR,
    p_fps NUMERIC DEFAULT NULL,
    p_latency_p50 NUMERIC DEFAULT NULL,
    p_latency_p95 NUMERIC DEFAULT NULL,
    p_gpu_memory NUMERIC DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_gate_b_passed BOOLEAN;
BEGIN
    -- Check Gate B requirements if metrics provided
    IF p_fps IS NOT NULL AND p_latency_p50 IS NOT NULL THEN
        v_gate_b_passed := (
            p_fps >= 25 AND 
            p_latency_p50 <= 120 AND 
            COALESCE(p_gpu_memory, 0) <= 2.5
        );
    END IF;
    
    UPDATE deployment_log SET
        status = p_status,
        fps_measured = p_fps,
        latency_p50_ms = p_latency_p50,
        latency_p95_ms = p_latency_p95,
        gpu_memory_gb = p_gpu_memory,
        gate_b_passed = v_gate_b_passed,
        error_message = p_error_message
    WHERE id = p_deployment_id;
END;
$$ LANGUAGE plpgsql;

-- Function to log audit events
CREATE OR REPLACE FUNCTION log_audit_event(
    p_action VARCHAR,
    p_entity_type VARCHAR DEFAULT 'video',
    p_entity_id UUID DEFAULT NULL,
    p_reason TEXT DEFAULT NULL,
    p_operator VARCHAR DEFAULT 'system',
    p_metadata JSONB DEFAULT '{}'
)
RETURNS BIGINT AS $$
DECLARE
    v_audit_id BIGINT;
BEGIN
    INSERT INTO audit_log (
        action, entity_type, entity_id, reason, operator, metadata
    ) VALUES (
        p_action, p_entity_type, p_entity_id, p_reason, p_operator, p_metadata
    ) RETURNING id INTO v_audit_id;
    
    RETURN v_audit_id;
END;
$$ LANGUAGE plpgsql;

-- Function to record observability sample
CREATE OR REPLACE FUNCTION record_obs_sample(
    p_src VARCHAR,
    p_metric VARCHAR,
    p_value NUMERIC,
    p_labels JSONB DEFAULT '{}'
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO obs_samples (src, metric, value, labels)
    VALUES (p_src, p_metric, p_value, p_labels);
END;
$$ LANGUAGE plpgsql;

COMMIT;
