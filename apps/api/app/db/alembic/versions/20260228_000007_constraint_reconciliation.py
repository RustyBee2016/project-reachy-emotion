"""Reconcile live DB constraint drift with ORM definitions.

Gap 1 — video: Replace legacy ck_video_split (3-value) with
         chk_video_split_label_policy (4-value + label↔split policy).
Gap 2 — promotion_log: Tighten split checks to 4-value (temp|train|test|purged),
         tighten intended_label to 3-class (neutral|happy|sad).
Gap 3 — video.zfs_snapshot: ADD COLUMN IF NOT EXISTS for ORM convergence.

All constraint changes use NOT VALID + VALIDATE CONSTRAINT to avoid
full-table locks on large tables.  Preflight data checks run before
each tightening step; migration aborts with a clear message if
violating rows are found.

Revision ID: 20260228_000007
Revises: 20260227_000006
Create Date: 2026-02-28
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

revision = "20260228_000007"
down_revision = "20260227_000006"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)


def _is_postgresql(bind) -> bool:
    return bind.dialect.name == "postgresql"


def _constraint_exists(bind, table: str, constraint_name: str) -> bool:
    """Check if a named constraint exists on the given table (PostgreSQL)."""
    if not _is_postgresql(bind):
        # SQLite: introspect via inspector
        inspector = sa.inspect(bind)
        if table not in inspector.get_table_names():
            return False
        # Check constraints are not fully introspectable on SQLite;
        # return False to let IF NOT EXISTS / idempotent guards handle it.
        return False
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_constraint "
            "WHERE conrelid = CAST(:tbl AS regclass) AND conname = :name"
        ),
        {"tbl": table, "name": constraint_name},
    )
    return result.scalar() is not None


def _column_exists(bind, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


# ---------------------------------------------------------------------------
# Preflight data checks (PostgreSQL only — SQLite uses fresh test DBs)
# ---------------------------------------------------------------------------

def _preflight_video(bind) -> None:
    """Ensure no video rows violate the split↔label policy."""
    if not _is_postgresql(bind):
        return
    result = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM video "
            "WHERE NOT ("
            "  (split IN ('temp','test','purged') AND label IS NULL) "
            "  OR (split = 'train' AND label IS NOT NULL)"
            ")"
        )
    )
    count = result.scalar()
    if count:
        raise RuntimeError(
            f"Preflight FAILED: {count} video row(s) violate "
            "chk_video_split_label_policy. Fix data before migrating."
        )
    logger.info("Preflight OK: 0 video rows violate split↔label policy")


def _preflight_promotion_log(bind) -> None:
    """Ensure no promotion_log rows use deprecated split or emotion values."""
    if not _is_postgresql(bind):
        return

    # Check splits
    result = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM promotion_log "
            "WHERE from_split NOT IN ('temp','train','test','purged') "
            "   OR to_split   NOT IN ('temp','train','test','purged')"
        )
    )
    bad_splits = result.scalar()
    if bad_splits:
        raise RuntimeError(
            f"Preflight FAILED: {bad_splits} promotion_log row(s) have "
            "deprecated split values. Fix data before migrating."
        )

    # Check intended_label
    result = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM promotion_log "
            "WHERE intended_label IS NOT NULL "
            "  AND intended_label NOT IN ('neutral','happy','sad')"
        )
    )
    bad_labels = result.scalar()
    if bad_labels:
        raise RuntimeError(
            f"Preflight FAILED: {bad_labels} promotion_log row(s) have "
            "deprecated intended_label values. Fix data before migrating."
        )
    logger.info("Preflight OK: 0 promotion_log rows violate new constraints")


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def _reconcile_video_constraints(bind) -> None:
    """Gap 1: Replace ck_video_split → chk_video_split_label_policy."""
    if _is_postgresql(bind):
        # Drop legacy constraint
        if _constraint_exists(bind, "video", "ck_video_split"):
            bind.execute(sa.text(
                "ALTER TABLE video DROP CONSTRAINT ck_video_split"
            ))
            logger.info("Dropped legacy ck_video_split")

        # Add the full policy constraint (NOT VALID first, then validate)
        if not _constraint_exists(bind, "video", "chk_video_split_label_policy"):
            bind.execute(sa.text(
                "ALTER TABLE video ADD CONSTRAINT chk_video_split_label_policy "
                "CHECK ("
                "  (split IN ('temp','test','purged') AND label IS NULL) "
                "  OR (split = 'train' AND label IS NOT NULL)"
                ") NOT VALID"
            ))
            bind.execute(sa.text(
                "ALTER TABLE video VALIDATE CONSTRAINT chk_video_split_label_policy"
            ))
            logger.info("Added and validated chk_video_split_label_policy")
        else:
            logger.info("chk_video_split_label_policy already exists — skipping")
    else:
        # SQLite: constraints are baked into CREATE TABLE; no ALTER support.
        # On fresh SQLite test DBs the ORM's __table_args__ already applies
        # the correct constraint via create_all / initial migration.
        logger.info("SQLite: video constraint reconciliation skipped (handled by ORM)")


def _reconcile_promotion_log_constraints(bind) -> None:
    """Gap 2: Tighten promotion_log split and label constraints."""
    if not _is_postgresql(bind):
        logger.info("SQLite: promotion_log constraint reconciliation skipped")
        return

    # --- from_split ---
    if _constraint_exists(bind, "promotion_log", "promotion_log_from_split_check"):
        bind.execute(sa.text(
            "ALTER TABLE promotion_log DROP CONSTRAINT promotion_log_from_split_check"
        ))
    if not _constraint_exists(bind, "promotion_log", "chk_promotion_from_split"):
        bind.execute(sa.text(
            "ALTER TABLE promotion_log ADD CONSTRAINT chk_promotion_from_split "
            "CHECK (from_split IN ('temp','train','test','purged')) NOT VALID"
        ))
        bind.execute(sa.text(
            "ALTER TABLE promotion_log VALIDATE CONSTRAINT chk_promotion_from_split"
        ))
    logger.info("promotion_log.from_split constraint tightened")

    # --- to_split ---
    if _constraint_exists(bind, "promotion_log", "promotion_log_to_split_check"):
        bind.execute(sa.text(
            "ALTER TABLE promotion_log DROP CONSTRAINT promotion_log_to_split_check"
        ))
    if not _constraint_exists(bind, "promotion_log", "chk_promotion_to_split"):
        bind.execute(sa.text(
            "ALTER TABLE promotion_log ADD CONSTRAINT chk_promotion_to_split "
            "CHECK (to_split IN ('temp','train','test','purged')) NOT VALID"
        ))
        bind.execute(sa.text(
            "ALTER TABLE promotion_log VALIDATE CONSTRAINT chk_promotion_to_split"
        ))
    logger.info("promotion_log.to_split constraint tightened")

    # --- intended_label ---
    if _constraint_exists(bind, "promotion_log", "promotion_log_intended_label_check"):
        bind.execute(sa.text(
            "ALTER TABLE promotion_log "
            "DROP CONSTRAINT promotion_log_intended_label_check"
        ))
    if not _constraint_exists(bind, "promotion_log", "chk_promotion_intended_label"):
        bind.execute(sa.text(
            "ALTER TABLE promotion_log ADD CONSTRAINT chk_promotion_intended_label "
            "CHECK (intended_label IS NULL "
            "  OR intended_label IN ('neutral','happy','sad')) NOT VALID"
        ))
        bind.execute(sa.text(
            "ALTER TABLE promotion_log "
            "VALIDATE CONSTRAINT chk_promotion_intended_label"
        ))
    logger.info("promotion_log.intended_label constraint tightened to 3-class")


def _add_zfs_snapshot_column(bind) -> None:
    """Gap 3: Adopt video.zfs_snapshot into managed schema."""
    if _column_exists(bind, "video", "zfs_snapshot"):
        logger.info("video.zfs_snapshot already exists — skipping ADD COLUMN")
        return
    op.add_column("video", sa.Column("zfs_snapshot", sa.String(255), nullable=True))
    logger.info("Added video.zfs_snapshot column")


def upgrade() -> None:
    bind = op.get_bind()

    # Preflight data checks
    _preflight_video(bind)
    _preflight_promotion_log(bind)

    # Gap 1: video constraint reconciliation
    _reconcile_video_constraints(bind)

    # Gap 2: promotion_log constraint tightening
    _reconcile_promotion_log_constraints(bind)

    # Gap 3: zfs_snapshot column adoption
    _add_zfs_snapshot_column(bind)


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    bind = op.get_bind()

    if not _is_postgresql(bind):
        return

    # Reverse Gap 3: drop zfs_snapshot only if it was added by this migration.
    # On the live DB the column pre-existed so we leave it alone.
    # For safety, we do NOT drop zfs_snapshot — it may contain data.
    logger.info("Downgrade: zfs_snapshot column preserved (may contain data)")

    # Reverse Gap 2: restore legacy promotion_log constraints
    for new_name, old_name, old_def in [
        (
            "chk_promotion_from_split",
            "promotion_log_from_split_check",
            "CHECK (from_split IN ('temp','dataset_all','train','test'))",
        ),
        (
            "chk_promotion_to_split",
            "promotion_log_to_split_check",
            "CHECK (to_split IN ('temp','dataset_all','train','test'))",
        ),
        (
            "chk_promotion_intended_label",
            "promotion_log_intended_label_check",
            "CHECK (intended_label IS NULL "
            "OR intended_label IN ('neutral','happy','sad','angry','surprise'))",
        ),
    ]:
        if _constraint_exists(bind, "promotion_log", new_name):
            bind.execute(sa.text(
                f"ALTER TABLE promotion_log DROP CONSTRAINT {new_name}"
            ))
        if not _constraint_exists(bind, "promotion_log", old_name):
            bind.execute(sa.text(
                f"ALTER TABLE promotion_log ADD CONSTRAINT {old_name} {old_def}"
            ))

    # Reverse Gap 1: restore legacy ck_video_split
    if _constraint_exists(bind, "video", "chk_video_split_label_policy"):
        bind.execute(sa.text(
            "ALTER TABLE video DROP CONSTRAINT chk_video_split_label_policy"
        ))
    if not _constraint_exists(bind, "video", "ck_video_split"):
        bind.execute(sa.text(
            "ALTER TABLE video ADD CONSTRAINT ck_video_split "
            "CHECK (split IN ('temp','train','test'))"
        ))
