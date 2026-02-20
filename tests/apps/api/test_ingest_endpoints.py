"""Tests for ingest API endpoints (/api/v1/ingest).

Tests the video pull and manifest rebuild endpoints that support
the n8n Ingest Agent (Agent 1) and Promotion Agent (Agent 3).
"""

import hashlib
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from apps.api.app.main import app
from apps.api.app.db.base import Base
from apps.api.app.db.models import Video
from apps.api.app.deps import get_db, get_config_dep
from apps.api.app.config import AppConfig, get_config


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_video_bytes():
    """Generate fake video bytes for testing."""
    return b"fake video content for testing purposes" * 100


@pytest.fixture
def mock_video_sha256(mock_video_bytes):
    """Compute SHA256 of mock video."""
    return hashlib.sha256(mock_video_bytes).hexdigest()


# ============================================================================
# Pull Video Endpoint Tests
# ============================================================================


class TestPullVideoEndpoint:
    """Tests for POST /api/v1/ingest/pull."""

    @pytest.mark.asyncio
    async def test_pull_video_success(
        self, client, test_config, db_session, mock_video_bytes, mock_video_sha256
    ):
        """Test successful video pull from URL."""
        # Mock the HTTP download
        with patch("apps.api.app.routers.ingest.download_video", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = mock_video_bytes
            
            # Mock FFprobe (may not be available in test env)
            with patch("apps.api.app.routers.ingest.ffprobe_metadata", new_callable=AsyncMock) as mock_ffprobe:
                mock_ffprobe.return_value = MagicMock(
                    duration_sec=5.0,
                    fps=30.0,
                    width=1920,
                    height=1080,
                    codec="h264",
                    bitrate=5000000
                )
                
                # Mock thumbnail generation
                with patch("apps.api.app.routers.ingest.generate_thumbnail", new_callable=AsyncMock) as mock_thumb:
                    mock_thumb.return_value = True
                    
                    response = await client.post(
                        "/api/v1/ingest/pull",
                        json={
                            "source_url": "https://example.com/test_video.mp4",
                            "correlation_id": "test-correlation-123",
                            "intended_emotion": "happy",
                            "generator": "luma"
                        }
                    )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "done"
        assert "video_id" in data
        assert data["sha256"] == mock_video_sha256
        assert data["size_bytes"] == len(mock_video_bytes)
        assert data["correlation_id"] == "test-correlation-123"
        assert data["duplicate"] is False
        assert "temp/" in data["file_path"]

    @pytest.mark.asyncio
    async def test_pull_video_duplicate_detection(
        self, client, test_config, db_session, mock_video_bytes, mock_video_sha256, create_test_video_file
    ):
        """Test that duplicate videos are detected by SHA256."""
        # Create existing video in database
        existing_video = Video(
            video_id=str(uuid.uuid4()),
            file_path="temp/existing_video.mp4",
            split="temp",
            sha256=mock_video_sha256,
            size_bytes=len(mock_video_bytes),
        )
        db_session.add(existing_video)
        await db_session.commit()
        
        # Create the physical file
        create_test_video_file("temp/existing_video.mp4", mock_video_bytes)
        
        # Try to pull the same video
        with patch("apps.api.app.routers.ingest.download_video", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = mock_video_bytes
            
            response = await client.post(
                "/api/v1/ingest/pull",
                json={
                    "source_url": "https://example.com/duplicate.mp4",
                    "correlation_id": "test-dup-123"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "duplicate"
        assert data["video_id"] == existing_video.video_id
        assert data["duplicate"] is True

    @pytest.mark.asyncio
    async def test_pull_video_download_failure(self, client, test_config):
        """Test handling of download failures."""
        with patch("apps.api.app.routers.ingest.download_video", new_callable=AsyncMock) as mock_download:
            # Simulate HTTP error
            import httpx
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_download.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response
            )
            
            response = await client.post(
                "/api/v1/ingest/pull",
                json={
                    "source_url": "https://example.com/nonexistent.mp4"
                }
            )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "download_failed"

    @pytest.mark.asyncio
    async def test_pull_video_missing_url(self, client, test_config):
        """Test validation error for missing source_url."""
        response = await client.post(
            "/api/v1/ingest/pull",
            json={}
        )
        
        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_pull_video_creates_file(
        self, client, test_config, db_session, mock_video_bytes
    ):
        """Test that pulled video is saved to filesystem."""
        with patch("apps.api.app.routers.ingest.download_video", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = mock_video_bytes
            
            with patch("apps.api.app.routers.ingest.ffprobe_metadata", new_callable=AsyncMock) as mock_ffprobe:
                mock_ffprobe.return_value = MagicMock(
                    duration_sec=None, fps=None, width=None, height=None, codec=None, bitrate=None
                )
                
                with patch("apps.api.app.routers.ingest.generate_thumbnail", new_callable=AsyncMock) as mock_thumb:
                    mock_thumb.return_value = True
                    
                    response = await client.post(
                        "/api/v1/ingest/pull",
                        json={"source_url": "https://example.com/test.mp4"}
                    )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify file was created
        file_path = test_config.videos_root / data["file_path"]
        assert file_path.exists()
        assert file_path.read_bytes() == mock_video_bytes


# ============================================================================
# Register Local Endpoint Tests
# ============================================================================


class TestRegisterLocalEndpoint:
    """Tests for POST /api/v1/ingest/register-local."""

    @pytest.mark.asyncio
    async def test_register_local_success(
        self, client, test_config, db_session, mock_video_bytes, create_test_video_file
    ):
        """Register an existing temp file and persist metadata."""
        rel_path = "temp/local_clip.mp4"
        create_test_video_file(rel_path, mock_video_bytes)

        with patch("apps.api.app.routers.ingest.ffprobe_metadata", new_callable=AsyncMock) as mock_ffprobe:
            mock_ffprobe.return_value = MagicMock(
                duration_sec=5.0, fps=30.0, width=1280, height=720, codec="h264", bitrate=1000000
            )
            with patch("apps.api.app.routers.ingest.generate_thumbnail", new_callable=AsyncMock) as mock_thumb:
                mock_thumb.return_value = True
                response = await client.post(
                    "/api/v1/ingest/register-local",
                    json={
                        "file_path": rel_path,
                        "correlation_id": "register-local-success",
                        "file_name": "local_clip.mp4",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert data["duplicate"] is False
        assert data["file_path"] == rel_path
        assert data["file_name"] == "local_clip.mp4"

        saved = await db_session.get(Video, data["video_id"])
        assert saved is not None
        assert saved.file_path == rel_path
        assert saved.split == "temp"
        assert saved.label is None

    @pytest.mark.asyncio
    async def test_register_local_duplicate_reuses_existing_video(
        self, client, db_session, mock_video_bytes, mock_video_sha256, create_test_video_file
    ):
        """Return duplicate status when SHA+size already exists."""
        existing_id = str(uuid.uuid4())
        rel_path = "temp/already_registered.mp4"
        create_test_video_file(rel_path, mock_video_bytes)

        existing_video = Video(
            video_id=existing_id,
            file_path=rel_path,
            split="temp",
            sha256=mock_video_sha256,
            size_bytes=len(mock_video_bytes),
            duration_sec=4.0,
            fps=24.0,
            width=640,
            height=360,
        )
        db_session.add(existing_video)
        await db_session.commit()

        with patch("apps.api.app.routers.ingest.ffprobe_metadata", new_callable=AsyncMock) as mock_ffprobe:
            mock_ffprobe.return_value = MagicMock(
                duration_sec=4.0, fps=24.0, width=640, height=360, codec="h264", bitrate=800000
            )
            with patch("apps.api.app.routers.ingest.generate_thumbnail", new_callable=AsyncMock) as mock_thumb:
                mock_thumb.return_value = True
                response = await client.post(
                    "/api/v1/ingest/register-local",
                    json={"file_path": rel_path, "correlation_id": "register-local-dup"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "duplicate"
        assert data["duplicate"] is True
        assert data["video_id"] == existing_id


# ============================================================================
# Manifest Rebuild Endpoint Tests
# ============================================================================


class TestRebuildManifestEndpoint:
    """Tests for POST /api/v1/ingest/manifest/rebuild."""

    @pytest.mark.asyncio
    async def test_rebuild_manifest_empty_splits(self, client, test_config, db_session):
        """Test manifest rebuild with no videos."""
        response = await client.post(
            "/api/v1/ingest/manifest/rebuild",
            json={"splits": ["train", "test"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert "dataset_hash" in data
        assert data["train_count"] == 0
        assert data["test_count"] == 0
        assert "train" in data["manifests_rebuilt"]
        assert "test" in data["manifests_rebuilt"]

    @pytest.mark.asyncio
    async def test_rebuild_manifest_with_videos(
        self, client, test_config, db_session, create_test_video_file
    ):
        """Test manifest rebuild with existing videos."""
        # Create test videos in train split
        videos = []
        for i, label in enumerate(["happy", "sad", "happy"]):
            video = Video(
                video_id=str(uuid.uuid4()),
                file_path=f"train/video_{i}.mp4",
                split="train",
                label=label,
                sha256=f"hash{i}" + "0" * 58,
                size_bytes=1000 + i,
            )
            videos.append(video)
            db_session.add(video)
            create_test_video_file(f"train/video_{i}.mp4")
        
        await db_session.commit()
        
        response = await client.post(
            "/api/v1/ingest/manifest/rebuild",
            json={"splits": ["train"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert data["train_count"] == 3
        assert "train" in data["manifests_rebuilt"]
        
        # Verify manifest file was created
        manifest_path = test_config.manifests_path / "train_manifest.jsonl"
        assert manifest_path.exists()
        
        # Verify manifest content
        with open(manifest_path) as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        for line in lines:
            entry = json.loads(line)
            assert "video_id" in entry
            assert "path" in entry
            assert "label" in entry

    @pytest.mark.asyncio
    async def test_rebuild_manifest_invalid_split(self, client, test_config):
        """Test validation error for invalid split."""
        response = await client.post(
            "/api/v1/ingest/manifest/rebuild",
            json={"splits": ["invalid_split"]}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "validation_error"

    @pytest.mark.asyncio
    async def test_rebuild_manifest_default_splits(self, client, test_config, db_session):
        """Test manifest rebuild with default splits (train, test)."""
        response = await client.post(
            "/api/v1/ingest/manifest/rebuild",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "train" in data["manifests_rebuilt"]
        assert "test" in data["manifests_rebuilt"]

    @pytest.mark.asyncio
    async def test_rebuild_manifest_dataset_hash_deterministic(
        self, client, test_config, db_session, create_test_video_file
    ):
        """Test that dataset hash is deterministic."""
        # Create test video
        video = Video(
            video_id="fixed-uuid-for-test",
            file_path="train/fixed_video.mp4",
            split="train",
            label="happy",
            sha256="a" * 64,
            size_bytes=1000,
        )
        db_session.add(video)
        await db_session.commit()
        create_test_video_file("train/fixed_video.mp4")
        
        # Rebuild twice
        response1 = await client.post(
            "/api/v1/ingest/manifest/rebuild",
            json={"splits": ["train"]}
        )
        response2 = await client.post(
            "/api/v1/ingest/manifest/rebuild",
            json={"splits": ["train"]}
        )
        
        assert response1.json()["dataset_hash"] == response2.json()["dataset_hash"]


# ============================================================================
# Ingest Status Endpoint Tests
# ============================================================================


class TestIngestStatusEndpoint:
    """Tests for GET /api/v1/ingest/status/{video_id}."""

    @pytest.mark.asyncio
    async def test_get_status_existing_video(
        self, client, test_config, db_session, create_test_video_file
    ):
        """Test getting status of existing video."""
        video_id = str(uuid.uuid4())
        video = Video(
            video_id=video_id,
            file_path=f"temp/{video_id}.mp4",
            split="temp",
            sha256="b" * 64,
            size_bytes=2000,
            duration_sec=5.5,
            fps=30.0,
            width=1920,
            height=1080,
        )
        db_session.add(video)
        await db_session.commit()
        
        # Create physical file
        create_test_video_file(f"temp/{video_id}.mp4")
        
        response = await client.get(f"/api/v1/ingest/status/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "done"
        assert data["video_id"] == video_id
        assert data["file_exists"] is True
        assert data["duration_sec"] == 5.5

    @pytest.mark.asyncio
    async def test_get_status_nonexistent_video(self, client, test_config):
        """Test getting status of nonexistent video."""
        response = await client.get("/api/v1/ingest/status/nonexistent-video-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_status_missing_file(self, client, test_config, db_session):
        """Test status when DB record exists but file is missing."""
        video_id = str(uuid.uuid4())
        video = Video(
            video_id=video_id,
            file_path=f"temp/{video_id}.mp4",
            split="temp",
            sha256="c" * 64,
            size_bytes=3000,
        )
        db_session.add(video)
        await db_session.commit()
        
        # Don't create the physical file
        
        response = await client.get(f"/api/v1/ingest/status/{video_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "pending"  # File doesn't exist
        assert data["file_exists"] is False


# ============================================================================
# New Database Models Tests
# ============================================================================


class TestNewDatabaseModels:
    """Tests for new database models added in Phase 3."""

    @pytest.mark.asyncio
    async def test_label_event_model(self, db_session):
        """Test LabelEvent model creation."""
        from apps.api.app.db.models import LabelEvent
        
        event = LabelEvent(
            video_id=None,  # Can be null if video deleted
            label="happy",
            action="label_only",
            rater_id="test-rater",
            notes="Test labeling",
            idempotency_key="test-key-123",
            correlation_id=str(uuid.uuid4()),
        )
        db_session.add(event)
        await db_session.commit()
        
        assert event.event_id is not None
        assert event.created_at is not None

    @pytest.mark.asyncio
    async def test_deployment_log_model(self, db_session):
        """Test DeploymentLog model creation."""
        from apps.api.app.db.models import DeploymentLog
        
        deployment = DeploymentLog(
            engine_path="/opt/reachy/models/emotion_v1.engine",
            model_version="v1.0.0",
            target_stage="shadow",
            status="pending",
            mlflow_run_id="mlflow-run-123",
        )
        db_session.add(deployment)
        await db_session.commit()
        
        assert deployment.id is not None
        assert deployment.deployed_at is not None

    @pytest.mark.asyncio
    async def test_audit_log_model(self, db_session):
        """Test AuditLog model creation."""
        from apps.api.app.db.models import AuditLog
        
        audit = AuditLog(
            action="purge",
            entity_type="video",
            entity_id=str(uuid.uuid4()),
            reason="TTL expired",
            operator="privacy_agent",
            metadata={"ttl_days": 14},
        )
        db_session.add(audit)
        await db_session.commit()
        
        assert audit.id is not None
        assert audit.timestamp is not None

    @pytest.mark.asyncio
    async def test_obs_sample_model(self, db_session):
        """Test ObsSample model creation."""
        from apps.api.app.db.models import ObsSample
        
        sample = ObsSample(
            src="n8n",
            metric="active_executions",
            value=5.0,
            labels={"workflow": "ingest_agent"},
        )
        db_session.add(sample)
        await db_session.commit()
        
        assert sample.id is not None
        assert sample.ts is not None

    @pytest.mark.asyncio
    async def test_reconcile_report_model(self, db_session):
        """Test ReconcileReport model creation."""
        from apps.api.app.db.models import ReconcileReport
        
        report = ReconcileReport(
            trigger_type="scheduled",
            orphan_count=2,
            missing_count=1,
            mismatch_count=0,
            drift_detected=True,
            auto_fixed=False,
            details={"orphans": ["file1.mp4", "file2.mp4"]},
            duration_ms=1500,
        )
        db_session.add(report)
        await db_session.commit()
        
        assert report.id is not None
        assert report.run_at is not None

    @pytest.mark.asyncio
    async def test_video_purged_split(self, db_session):
        """Test that video can be set to 'purged' split."""
        video = Video(
            video_id=str(uuid.uuid4()),
            file_path="purged/old_video.mp4",
            split="purged",
            label=None,  # Purged videos have no label
            sha256="d" * 64,
            size_bytes=4000,
        )
        db_session.add(video)
        await db_session.commit()
        
        assert video.split == "purged"


# ============================================================================
# Integration Tests
# ============================================================================


class TestIngestIntegration:
    """Integration tests for the full ingest workflow."""

    @pytest.mark.asyncio
    async def test_full_ingest_workflow(
        self, client, test_config, db_session, mock_video_bytes
    ):
        """Test complete ingest → status → manifest workflow."""
        # Step 1: Pull video
        with patch("apps.api.app.routers.ingest.download_video", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = mock_video_bytes
            
            with patch("apps.api.app.routers.ingest.ffprobe_metadata", new_callable=AsyncMock) as mock_ffprobe:
                mock_ffprobe.return_value = MagicMock(
                    duration_sec=5.0, fps=30.0, width=1920, height=1080, codec=None, bitrate=None
                )
                
                with patch("apps.api.app.routers.ingest.generate_thumbnail", new_callable=AsyncMock) as mock_thumb:
                    mock_thumb.return_value = True
                    
                    pull_response = await client.post(
                        "/api/v1/ingest/pull",
                        json={"source_url": "https://example.com/workflow_test.mp4"}
                    )
        
        assert pull_response.status_code == 200
        video_id = pull_response.json()["video_id"]
        
        # Step 2: Check status
        status_response = await client.get(f"/api/v1/ingest/status/{video_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "done"
        
        # Step 3: Video is in temp, so manifest rebuild for temp should include it
        # Note: temp is not a valid manifest split, so we just verify the video exists
        assert status_response.json()["split"] == "temp"
