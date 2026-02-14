"""Unit tests for DB-backed status handlers without pytest-asyncio plugin."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from apps.api.app.db.base import Base
from apps.api.app.routers import gateway_upstream

pytest.importorskip("aiosqlite")


def _run(coro):
    return asyncio.run(coro)


def _make_sessionmaker(tmp_path: Path):
    db_path = tmp_path / "status_test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False), engine

    return _run(_init())


def test_training_status_persists(tmp_path: Path):
    session_maker, engine = _make_sessionmaker(tmp_path)

    async def _test():
        async with session_maker() as session:
            await gateway_upstream.update_training_status(
                "run_123",
                {"status": "training", "metrics": {"epoch": 4, "f1_macro": 0.82}},
                session=session,
            )
        async with session_maker() as session:
            status_payload = await gateway_upstream.get_training_status("run_123", session=session)
            assert status_payload["status"] == "training"
            assert status_payload["metrics"]["epoch"] == 4

    _run(_test())
    _run(engine.dispose())


def test_deployment_status_persists(tmp_path: Path):
    session_maker, engine = _make_sessionmaker(tmp_path)

    async def _test():
        async with session_maker() as session:
            await gateway_upstream.update_deployment_status(
                "pipe_123",
                {
                    "status": "deploying",
                    "target_stage": "canary",
                    "engine_path": "/tmp/engine.plan",
                    "fps_measured": 28.3,
                },
                session=session,
            )
        async with session_maker() as session:
            status_payload = await gateway_upstream.get_deployment_status("pipe_123", session=session)
            assert status_payload["status"] == "deploying"
            assert status_payload["target_stage"] == "canary"
            assert status_payload["fps_measured"] == 28.3

    _run(_test())
    _run(engine.dispose())
