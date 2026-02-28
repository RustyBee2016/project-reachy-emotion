from __future__ import annotations

from pathlib import Path

import pytest
pytest.importorskip("alembic.command")
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ALEMBIC_INI = Path(__file__).resolve().parents[4] / "apps" / "api" / "app" / "db" / "alembic.ini"
ALEMBIC_SCRIPT = Path(__file__).resolve().parents[4] / "apps" / "api" / "app" / "db" / "alembic"

# All tables expected after running the full migration chain to head.
EXPECTED_TABLES = {
    # Initial schema (202510280000)
    "video",
    "training_run",
    "training_selection",
    "promotion_log",
    # 20260223_000003
    "extracted_frame",
    # 20260227_000005
    "label_event",
    "run_link",
    "audit_log",
    "deployment_log",
    "obs_samples",
    "reconcile_report",
}

# Tables created by the initial migration (full downgrade removes only these).
INITIAL_TABLES = {"video", "training_run", "training_selection", "promotion_log"}

# Tables from migrations with no-op downgrades (persist after downgrade to base).
NOOP_DOWNGRADE_TABLES = {
    "extracted_frame",
    "label_event",
    "run_link",
    "audit_log",
    "deployment_log",
    "obs_samples",
    "reconcile_report",
}


def _alembic_config(url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_SCRIPT))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    return cfg


def _table_names(url: str) -> list[str]:
    engine = create_engine(url, future=True)
    try:
        return inspect(engine).get_table_names()
    finally:
        engine.dispose()


def _index_names(url: str, table: str) -> set[str]:
    engine = create_engine(url, future=True)
    try:
        return {idx["name"] for idx in inspect(engine).get_indexes(table) if idx["name"]}
    finally:
        engine.dispose()


@pytest.mark.parametrize("dialect", ["sqlite"])
def test_migration_upgrade_and_downgrade(tmp_path, dialect: str) -> None:
    db_path = tmp_path / "alembic_test.db"
    url = f"{dialect}:///{db_path}"

    cfg = _alembic_config(url)

    # --- Upgrade to head ---
    command.upgrade(cfg, "head")
    tables = set(_table_names(url))
    assert EXPECTED_TABLES <= tables, f"Missing tables: {EXPECTED_TABLES - tables}"

    # --- Verify backfilled single-column indexes ---
    video_indexes = _index_names(url, "video")
    assert "ix_video_split" in video_indexes
    assert "ix_video_label" in video_indexes

    tr_indexes = _index_names(url, "training_run")
    assert "ix_training_run_status" in tr_indexes
    assert "ix_training_run_created" in tr_indexes

    pl_indexes = _index_names(url, "promotion_log")
    assert "ix_promotion_log_idempotency" in pl_indexes

    # --- Verify video.zfs_snapshot column (000007) ---
    engine = create_engine(url, future=True)
    try:
        video_cols = {c["name"] for c in inspect(engine).get_columns("video")}
    finally:
        engine.dispose()
    assert "zfs_snapshot" in video_cols, "video.zfs_snapshot column missing after upgrade"

    # --- Verify new composite indexes (R3, R4) ---
    assert "ix_video_split_label" in video_indexes

    frame_indexes = _index_names(url, "extracted_frame")
    assert "ix_extracted_frame_run_label" in frame_indexes

    # --- Downgrade to base ---
    command.downgrade(cfg, "base")
    remaining_tables = set(_table_names(url))
    remaining_tables.discard("alembic_version")

    # The initial migration's downgrade removes INITIAL_TABLES.
    # Tables from no-op downgrades persist — this is by design.
    assert not (remaining_tables & INITIAL_TABLES), (
        f"Initial tables should be dropped: {remaining_tables & INITIAL_TABLES}"
    )
    assert remaining_tables <= NOOP_DOWNGRADE_TABLES, (
        f"Unexpected tables after downgrade: {remaining_tables - NOOP_DOWNGRADE_TABLES}"
    )
