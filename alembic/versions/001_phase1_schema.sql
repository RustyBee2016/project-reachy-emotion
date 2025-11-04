-- Phase 1 Database Schema Migration
-- Complete schema for Reachy_Local_08.4.2
-- Run with: psql -d reachy_emotion -f 001_phase1_schema.sql

BEGIN;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create enum types
DO $$ BEGIN
    CREATE TYPE video_split AS ENUM ('temp', 'dataset_all', 'train', 'test');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE emotion_label AS ENUM ('neutral', 'happy', 'sad', 'angry', 'surprise', 'fearful');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE training_status AS ENUM ('pending', 'sampling', 'training', 'evaluating', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Main video table
CREATE TABLE IF NOT EXISTS video (
    video_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path VARCHAR(500) NOT NULL,
    split video_split NOT NULL DEFAULT 'temp',
    label emotion_label,
    sha256 CHAR(64) UNIQUE,
    duration_sec NUMERIC(10,2),
    width INTEGER,
    height INTEGER,
    fps NUMERIC(5,2),
    size_bytes BIGINT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes for video table
CREATE INDEX IF NOT EXISTS idx_video_split ON video(split);
CREATE INDEX IF NOT EXISTS idx_video_label ON video(label);
CREATE INDEX IF NOT EXISTS idx_video_created ON video(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_video_sha256 ON video(sha256);

-- Training run tracking
CREATE TABLE IF NOT EXISTS training_run (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    status training_status NOT NULL DEFAULT 'pending',
    strategy VARCHAR(100) NOT NULL,
    train_fraction NUMERIC(3,2) CHECK (train_fraction > 0 AND train_fraction < 1),
    test_fraction NUMERIC(3,2) CHECK (test_fraction > 0 AND test_fraction < 1),
    seed BIGINT,
    dataset_hash CHAR(64),
    mlflow_run_id VARCHAR(255),
    model_path VARCHAR(500),
    engine_path VARCHAR(500),
    metrics JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',
    error_message TEXT,
    CONSTRAINT valid_fractions CHECK (train_fraction + test_fraction <= 1.0)
);

-- Indexes for training_run
CREATE INDEX IF NOT EXISTS idx_training_status ON training_run(status);
CREATE INDEX IF NOT EXISTS idx_training_created ON training_run(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_training_mlflow ON training_run(mlflow_run_id);

-- Video selection for training runs
CREATE TABLE IF NOT EXISTS training_selection (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID REFERENCES training_run(run_id) ON DELETE CASCADE,
    video_id UUID REFERENCES video(video_id) ON DELETE CASCADE,
    target_split video_split CHECK (target_split IN ('train', 'test')),
    selected_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (run_id, video_id)
);

-- Indexes for training_selection
CREATE INDEX IF NOT EXISTS idx_selection_run ON training_selection(run_id);
CREATE INDEX IF NOT EXISTS idx_selection_video ON training_selection(video_id);

-- Promotion audit log
CREATE TABLE IF NOT EXISTS promotion_log (
    id BIGSERIAL PRIMARY KEY,
    video_id UUID REFERENCES video(video_id) ON DELETE SET NULL,
    from_split video_split NOT NULL,
    to_split video_split NOT NULL,
    label emotion_label,
    user_id VARCHAR(255),
    correlation_id UUID,
    idempotency_key VARCHAR(64) UNIQUE,
    dry_run BOOLEAN DEFAULT FALSE,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    promoted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for promotion_log
CREATE INDEX IF NOT EXISTS idx_promo_video ON promotion_log(video_id);
CREATE INDEX IF NOT EXISTS idx_promo_idempotency ON promotion_log(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_promo_time ON promotion_log(promoted_at DESC);

-- User sessions
CREATE TABLE IF NOT EXISTS user_session (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255),
    device_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    actions_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for user_session
CREATE INDEX IF NOT EXISTS idx_session_user ON user_session(user_id);
CREATE INDEX IF NOT EXISTS idx_session_activity ON user_session(last_activity_at DESC);

-- Video generation requests
CREATE TABLE IF NOT EXISTS generation_request (
    request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt TEXT NOT NULL,
    emotion emotion_label NOT NULL,
    duration_sec INTEGER DEFAULT 5,
    provider VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    video_id UUID REFERENCES video(video_id),
    api_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

-- Indexes for generation_request
CREATE INDEX IF NOT EXISTS idx_gen_status ON generation_request(status);
CREATE INDEX IF NOT EXISTS idx_gen_created ON generation_request(created_at DESC);

-- Emotion detection events
CREATE TABLE IF NOT EXISTS emotion_event (
    event_id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    emotion emotion_label NOT NULL,
    confidence NUMERIC(5,4) CHECK (confidence >= 0 AND confidence <= 1),
    inference_ms NUMERIC(8,2),
    frame_number BIGINT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Indexes for emotion_event
CREATE INDEX IF NOT EXISTS idx_emotion_device ON emotion_event(device_id);
CREATE INDEX IF NOT EXISTS idx_emotion_time ON emotion_event(timestamp DESC);

-- Update trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update triggers
DROP TRIGGER IF EXISTS update_video_updated_at ON video;
CREATE TRIGGER update_video_updated_at BEFORE UPDATE ON video
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS update_training_run_updated_at ON training_run;
CREATE TRIGGER update_training_run_updated_at BEFORE UPDATE ON training_run
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS update_user_session_updated_at ON user_session;
CREATE TRIGGER update_user_session_updated_at BEFORE UPDATE ON user_session
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

COMMIT;
