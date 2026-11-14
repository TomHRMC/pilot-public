"""phase_fe_1_batch_b13b_fix_mobile_sync_event_audit_audit_mixin

Revision ID: f308a6043aec
Revises: aaf414525b7d
Create Date: 2026-05-03 11:48:21.000000

B13b Item 6 — Gap Type 2 remediation
Table: mobile_sync_event_audit
Adds: created_at TIMESTAMPTZ NOT NULL (backfilled from resolved_at), created_by UUID NULL
Installs: audit_changes trigger + guard_created_immutable trigger (AppendOnly set)
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f308a6043aec"
down_revision = "aaf414525b7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Add as nullable
    op.add_column(
        "mobile_sync_event_audit",
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "mobile_sync_event_audit", sa.Column("created_by", sa.UUID(), nullable=True)
    )

    # Part 2: Backfill created_at from resolved_at (semantically identical — row is created at resolution)
    op.execute("""
        UPDATE mobile_sync_event_audit
        SET created_at = resolved_at
    """)

    # Part 3: Lock NOT NULL
    op.alter_column("mobile_sync_event_audit", "created_at", nullable=False)

    # Part 4: Install AppendOnly triggers
    op.execute("""
        CREATE TRIGGER audit_mobile_sync_event_audit_changes
        AFTER INSERT OR UPDATE OR DELETE ON mobile_sync_event_audit
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_mobile_sync_event_audit_guard_created_immutable
        BEFORE UPDATE ON mobile_sync_event_audit
        FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_mobile_sync_event_audit_guard_created_immutable "
        "ON mobile_sync_event_audit;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_mobile_sync_event_audit_changes "
        "ON mobile_sync_event_audit;"
    )
    op.drop_column("mobile_sync_event_audit", "created_by")
    op.drop_column("mobile_sync_event_audit", "created_at")
