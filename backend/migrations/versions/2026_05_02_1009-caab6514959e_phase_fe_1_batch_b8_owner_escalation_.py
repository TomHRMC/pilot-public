"""phase_fe_1_batch_b8_owner_escalation_status_expand

Revision ID: caab6514959e
Revises: 089c57d94ed2
Create Date: 2026-05-02 10:09:00.000000

B8/A47: Expand status CHECK constraint on mobile_sync_owner_escalation.

Old values (B7b): pending | resolved | rejected
New values (B8):  pending | resolved | rejected | auto_recovered | stale

auto_recovered: conflict was auto-resolved before owner acted
stale:          tech data too old and discarded (tech force-discarded)
"""

from alembic import op

revision: str = "caab6514959e"
down_revision: str | None = "089c57d94ed2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE mobile_sync_owner_escalation
            DROP CONSTRAINT IF EXISTS chk_mobile_sync_escalation_status
    """)
    op.execute("""
        ALTER TABLE mobile_sync_owner_escalation
            ADD CONSTRAINT chk_mobile_sync_escalation_status
                CHECK (status IN ('pending', 'resolved', 'rejected', 'auto_recovered', 'stale'))
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE mobile_sync_owner_escalation
            DROP CONSTRAINT IF EXISTS chk_mobile_sync_escalation_status
    """)
    op.execute("""
        ALTER TABLE mobile_sync_owner_escalation
            ADD CONSTRAINT chk_mobile_sync_escalation_status
                CHECK (status IN ('pending', 'resolved', 'rejected'))
    """)
