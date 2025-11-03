"""Dependency providers for the Media Mover API."""


from __future__ import annotations

from .db.session import get_async_sessionmaker
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .fs import FileMover
from .manifest import ManifestBackend, get_default_backend
from .services import PromoteService
from .settings import Settings, get_settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine(settings: Settings):
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def _get_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = get_async_sessionmaker(settings.database_url)
    return _session_factory
    

async def get_db(  # noqa: D401
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session tied to the application engine."""

    session_factory = _get_session_factory(settings)
    async with session_factory() as session:
        yield session


def get_settings_dep() -> Settings:
    """Expose settings as a dependency so submodules can override in tests."""

    return get_settings()


def get_manifest_backend() -> ManifestBackend:
    """Provide the manifest backend used by promotion workflows."""

    return get_default_backend()


def get_file_mover(settings: Settings = Depends(get_settings_dep)) -> FileMover:
    """Construct a FileMover rooted at the configured videos directory."""

    return FileMover(Path(settings.videos_root))


def get_promote_service(
    session: AsyncSession = Depends(get_db),
    file_mover: FileMover = Depends(get_file_mover),
    manifest_backend: ManifestBackend = Depends(get_manifest_backend),
) -> PromoteService:
    """Assemble a PromoteService with shared infrastructure dependencies."""

    return PromoteService(
        session,
        file_mover=file_mover,
        manifest_backend=manifest_backend,
    )
