"""phase_fe_1_batch_b13b_fix_mobile_push_rate_limit_audit_mixin

Revision ID: aaf414525b7d
Revises: 494549afc653
Create Date: 2026-05-03 11:48:21.000000

B13b Item 5 — Gap Type 1 remediation
Table: mobile_push_rate_limit
Adds: created_by UUID NULL, updated_by UUID NULL
No trigger changes needed — triggers already installed from B8.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "aaf414525b7d"
down_revision = "494549afc653"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mobile_push_rate_limit", sa.Column("created_by", sa.UUID(), nullable=True)
    )
    op.add_column(
        "mobile_push_rate_limit", sa.Column("updated_by", sa.UUID(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("mobile_push_rate_limit", "updated_by")
    op.drop_column("mobile_push_rate_limit", "created_by")
