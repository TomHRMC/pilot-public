"""dlc1_add_created_by_to_consent_audit

Revision ID: 94095600df2a
Revises: a3dd991809c0
Create Date: 2026-07-05 19:23:00.000000

DLC-1 fix: AppendOnlyMixin provides created_by field — add nullable column to
customer_sms_consent_audit table which was omitted from migration 1-C.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "94095600df2a"
down_revision = "a3dd991809c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE customer_sms_consent_audit
            ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES "user"(id) ON DELETE RESTRICT
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE customer_sms_consent_audit
            DROP COLUMN IF EXISTS created_by
    """)
