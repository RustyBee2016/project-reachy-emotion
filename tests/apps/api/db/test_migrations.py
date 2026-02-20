from __future__ import annotations

from pathlib import Path

import pytest
pytest.importorskip("alembic.command")
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ALEMBIC_INI = Path(__file__).resolve().parents[4] / "apps" / "api" / "app" / "db" / "alembic.ini"
ALEMBIC_SCRIPT = Path(__file__).resolve().parents[4] / "apps" / "api" / "app" / "db" / "alembic"


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


@pytest.mark.parametrize("dialect", ["sqlite"])
def test_migration_upgrade_and_downgrade(tmp_path, dialect: str) -> None:
    db_path = tmp_path / "alembic_test.db"
    url = f"{dialect}:///{db_path}"

    cfg = _alembic_config(url)

    command.upgrade(cfg, "head")
    tables = set(_table_names(url))
    assert {"video", "training_run", "training_selection", "promotion_log"} <= tables

    command.downgrade(cfg, "base")
    remaining_tables = set(_table_names(url))
    remaining_tables.discard("alembic_version")
    assert not remaining_tables
