"""phase_5_0_add_final_2_server_defaults

Revision ID: 9395bb5a44fc
Revises: cfdeb13d3b22
Create Date: 2026-04-09 13:37:38.950302+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9395bb5a44fc"
down_revision: str | None = "cfdeb13d3b22"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add the final 2 server defaults to complete Phase 5.0:
    1. entity_type.is_default (Boolean, default=false)
    2. notification_delivery_attempt.retryable (Boolean, default=true)
    """
    # Add is_default column to entity_type
    op.add_column(
        "entity_type",
        sa.Column(
            "is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )

    # Add retryable column to notification_delivery_attempt
    op.add_column(
        "notification_delivery_attempt",
        sa.Column(
            "retryable", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )


def downgrade() -> None:
    """
    Remove the 2 server default columns added in Phase 5.0 final step.
    """
    # Drop retryable column from notification_delivery_attempt
    op.drop_column("notification_delivery_attempt", "retryable")

    # Drop is_default column from entity_type
    op.drop_column("entity_type", "is_default")
