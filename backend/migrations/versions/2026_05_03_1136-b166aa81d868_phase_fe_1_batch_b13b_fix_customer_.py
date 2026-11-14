"""phase_fe_1_batch_b13b_fix_customer_communication_message_audit_mixin

Revision ID: b166aa81d868
Revises: 7a3900997daa
Create Date: 2026-05-03 11:36:23.000000

B13b Item 1 — Gap Type 1 remediation
Table: customer_communication_message
Adds: created_by UUID NULL, updated_by UUID NULL
No trigger changes needed — set_updated_at and audit_log_changes already installed from B11.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b166aa81d868"
down_revision = "7a3900997daa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_communication_message",
        sa.Column("created_by", sa.UUID(), nullable=True),
    )
    op.add_column(
        "customer_communication_message",
        sa.Column("updated_by", sa.UUID(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customer_communication_message", "updated_by")
    op.drop_column("customer_communication_message", "created_by")
