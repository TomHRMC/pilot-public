"""phase_fe_1_batch_b8_owner_escalation_resolution_action_expand

Revision ID: 089c57d94ed2
Revises: 48798cb37d28
Create Date: 2026-05-02 10:03:00.000000

B8/A48: Expand resolution_action CHECK constraint on mobile_sync_owner_escalation.

Old values (B7b): used_local | used_server | manual_edit | rejected
New values (B8):  use_tech | use_server | restore_and_accept | override_with_tech |
                  discard_tech | accept_authorized_at_capture | reject_unauthorized

Backward compat mapping:
  used_local  → use_tech
  used_server → use_server
  rejected    → reject_unauthorized

Existing B7b rows use old names. After migration, new rows use A48 names.
Both sets are valid in the expanded constraint to avoid breaking B7b rows.
"""

from alembic import op

revision: str = "089c57d94ed2"
down_revision: str | None = "48798cb37d28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old constraint and add expanded one including both B7b and A48 variants
    op.execute("""
        ALTER TABLE mobile_sync_owner_escalation
            DROP CONSTRAINT IF EXISTS chk_mobile_sync_escalation_resolution_action
    """)
    op.execute("""
        ALTER TABLE mobile_sync_owner_escalation
            ADD CONSTRAINT chk_mobile_sync_escalation_resolution_action
                CHECK (
                    resolution_action IS NULL OR resolution_action IN (
                        'used_local', 'used_server', 'manual_edit', 'rejected',
                        'use_tech', 'use_server', 'restore_and_accept',
                        'override_with_tech', 'discard_tech',
                        'accept_authorized_at_capture', 'reject_unauthorized'
                    )
                )
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE mobile_sync_owner_escalation
            DROP CONSTRAINT IF EXISTS chk_mobile_sync_escalation_resolution_action
    """)
    op.execute("""
        ALTER TABLE mobile_sync_owner_escalation
            ADD CONSTRAINT chk_mobile_sync_escalation_resolution_action
                CHECK (
                    resolution_action IS NULL OR resolution_action IN (
                        'used_local', 'used_server', 'manual_edit', 'rejected'
                    )
                )
    """)
