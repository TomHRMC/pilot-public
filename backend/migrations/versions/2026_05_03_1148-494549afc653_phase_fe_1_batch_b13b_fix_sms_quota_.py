"""phase_fe_1_batch_b13b_fix_sms_quota_period_audit_mixin

Revision ID: 494549afc653
Revises: 6aebd9058def
Create Date: 2026-05-03 11:48:21.000000

B13b Item 4 — Gap Type 1 remediation
Table: sms_quota_period
Adds: created_by UUID NULL, updated_by UUID NULL
No trigger changes needed — triggers already installed from B11.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "494549afc653"
down_revision = "6aebd9058def"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sms_quota_period", sa.Column("created_by", sa.UUID(), nullable=True))
    op.add_column("sms_quota_period", sa.Column("updated_by", sa.UUID(), nullable=True))


def downgrade() -> None:
    op.drop_column("sms_quota_period", "updated_by")
    op.drop_column("sms_quota_period", "created_by")
