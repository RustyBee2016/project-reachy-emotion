from __future__ import annotations

from typing import Dict, Tuple

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_ENGINE_CACHE: Dict[Tuple[str, bool], AsyncEngine] = {}
_SESSION_FACTORY_CACHE: Dict[Tuple[str, bool], async_sessionmaker[AsyncSession]] = {}


def get_async_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Return a cached async engine for the given database URL."""
    key = (database_url, echo)
    if key not in _ENGINE_CACHE:
        _ENGINE_CACHE[key] = create_async_engine(database_url, echo=echo, future=True)
    return _ENGINE_CACHE[key]


def get_async_sessionmaker(
    database_url: str,
    *,
    echo: bool = False,
) -> async_sessionmaker[AsyncSession]:
    """Return an async session factory bound to the cached engine."""
    key = (database_url, echo)
    if key not in _SESSION_FACTORY_CACHE:
        engine = get_async_engine(database_url, echo=echo)
        _SESSION_FACTORY_CACHE[key] = async_sessionmaker(engine, expire_on_commit=False)
    return _SESSION_FACTORY_CACHE[key]