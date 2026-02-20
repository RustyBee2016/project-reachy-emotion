"""Pytest fixtures for API tests."""

import pytest
try:
    import pytest_asyncio
except ModuleNotFoundError:  # pragma: no cover - fallback for constrained envs
    class _PytestAsyncioFallback:
        fixture = staticmethod(pytest.fixture)

    pytest_asyncio = _PytestAsyncioFallback()  # type: ignore[assignment]
from pathlib import Path
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.app.main import app
from apps.api.app.db.base import Base
from apps.api.app.deps import get_db, get_config_dep
from apps.api.app.config import AppConfig, get_config


# Test database URL will be set per-test using tmp_path
# Using file-based SQLite to ensure session isolation works correctly


@pytest_asyncio.fixture
async def db_engine(tmp_path: Path):
    """Create test database engine with file-based SQLite."""
    db_path = tmp_path / "test.db"
    test_database_url = f"sqlite+aiosqlite:///{db_path}"
    
    engine = create_async_engine(
        test_database_url,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create test database session.
    
    Provides a session for test setup/teardown.
    Uses the same engine as the client fixture to ensure data visibility.
    Tests must explicitly commit data for it to be visible to endpoints.
    """
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        # Don't auto-commit or rollback - let tests control this


@pytest.fixture
def test_config(tmp_path: Path) -> AppConfig:
    """Create test configuration with temporary directories."""
    videos_root = tmp_path / "videos"
    videos_root.mkdir(parents=True, exist_ok=True)
    
    # Create required subdirectories
    for subdir in ["temp", "train", "test", "purged", "thumbs", "manifests"]:
        (videos_root / subdir).mkdir(exist_ok=True)
    
    # Use file-based database URL
    db_path = tmp_path / "test.db"
    test_database_url = f"sqlite+aiosqlite:///{db_path}"
    
    return AppConfig(
        api_root_path="/api/media",
        ui_origins=["http://testserver"],
        database_url=test_database_url,
        videos_root=videos_root,
        enable_cors=False,
        enable_legacy_endpoints=False,
    )


@pytest.fixture
def create_test_video_file(test_config):
    """Helper fixture to create physical video files for tests."""
    def _create_file(file_path: str, content: bytes = b"fake video data") -> Path:
        """Create a test video file at the given path relative to videos_root."""
        full_path = test_config.videos_root / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return full_path
    return _create_file


@pytest_asyncio.fixture
async def client(db_engine, test_config):
    """Create test HTTP client with database and config overrides.
    
    Uses shared sessionmaker to ensure test data is visible to endpoints.
    """
    # Create sessionmaker from the same engine
    sessionmaker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async def override_get_db():
        async with sessionmaker() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_config_dep] = lambda: test_config
    app.dependency_overrides[get_config] = lambda: test_config
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_video_data():
    """Provide sample video data for tests."""
    return {
        "file_path": "temp/test_video.mp4",
        "split": "temp",
        "size_bytes": 1048576,
        "sha256": "abc123def456",
        "duration_sec": 5.2,
        "fps": 30.0,
        "width": 1920,
        "height": 1080,
    }
