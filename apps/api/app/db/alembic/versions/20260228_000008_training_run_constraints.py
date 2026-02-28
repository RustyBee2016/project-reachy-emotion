"""Add missing CHECK constraints to training_run table.

The ORM model defines three CHECK constraints that were never applied
to the live database:
  - chk_train_fraction_range: train_fraction > 0 AND train_fraction < 1
  - chk_valid_fractions: train_fraction + test_fraction <= 1.0
  - chk_training_status: status IN (pending, sampling, training, evaluating,
                                     completed, failed, cancelled)

Uses NOT VALID + VALIDATE CONSTRAINT for safe online application.

Revision ID: 20260228_000008
Revises: 20260228_000007
Create Date: 2026-02-28
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

revision = "20260228_000008"
down_revision = "20260228_000007"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)

_TABLE = "training_run"

_CONSTRAINTS = [
    (
        "chk_train_fraction_range",
        "train_fraction > 0 AND train_fraction < 1",
    ),
    (
        "chk_valid_fractions",
        "train_fraction + test_fraction <= 1.0",
    ),
    (
        "chk_training_status",
        "status IN ('pending', 'sampling', 'training', 'evaluating', "
        "'completed', 'failed', 'cancelled')",
    ),
]


def _is_postgresql(bind) -> bool:
    return bind.dialect.name == "postgresql"


def _constraint_exists(bind, table: str, constraint_name: str) -> bool:
    if not _is_postgresql(bind):
        return False
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_constraint c "
            "JOIN pg_class r ON c.conrelid = r.oid "
            "WHERE r.relname = :table AND c.conname = :name"
        ),
        {"table": table, "name": constraint_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()
    if not _is_postgresql(bind):
        logger.info("Skipping CHECK constraints on non-PostgreSQL backend")
        return

    for name, expr in _CONSTRAINTS:
        if _constraint_exists(bind, _TABLE, name):
            logger.info("Constraint %s already exists — skipping", name)
            continue

        # Add NOT VALID first (no full-table scan)
        op.execute(
            sa.text(
                f'ALTER TABLE {_TABLE} ADD CONSTRAINT {name} '
                f'CHECK ({expr}) NOT VALID'
            )
        )
        # Then validate (concurrent-safe scan)
        op.execute(
            sa.text(f'ALTER TABLE {_TABLE} VALIDATE CONSTRAINT {name}')
        )
        logger.info("Added and validated constraint %s", name)


def downgrade() -> None:
    bind = op.get_bind()
    if not _is_postgresql(bind):
        return

    for name, _ in reversed(_CONSTRAINTS):
        if _constraint_exists(bind, _TABLE, name):
            op.execute(
                sa.text(f'ALTER TABLE {_TABLE} DROP CONSTRAINT {name}')
            )
            logger.info("Dropped constraint %s", name)
