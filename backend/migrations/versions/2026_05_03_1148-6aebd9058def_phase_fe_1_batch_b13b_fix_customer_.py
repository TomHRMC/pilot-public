"""phase_fe_1_batch_b13b_fix_customer_communication_unrouted_audit_mixin

Revision ID: 6aebd9058def
Revises: 6f105cb542fd
Create Date: 2026-05-03 11:48:21.000000

B13b Item 3 — Gap Type 1 remediation
Table: customer_communication_unrouted
Adds: created_by UUID NULL, updated_by UUID NULL
No trigger changes needed — triggers already installed from B11.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6aebd9058def"
down_revision = "6f105cb542fd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_communication_unrouted",
        sa.Column("created_by", sa.UUID(), nullable=True),
    )
    op.add_column(
        "customer_communication_unrouted",
        sa.Column("updated_by", sa.UUID(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customer_communication_unrouted", "updated_by")
    op.drop_column("customer_communication_unrouted", "created_by")
