"""phase_6_0_task_3_add_payment_created_at_index

Revision ID: 0c524bb2e266
Revises: 6d7a8b012415
Create Date: 2026-04-13 16:15:56.016822+00:00

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "0c524bb2e266"
down_revision: str | None = "6d7a8b012415"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add missing idx_payment_created_at index
    # This index was defined in the Payment model but never migrated to the database
    op.create_index("idx_payment_created_at", "payment", [text("created_at DESC")])


def downgrade() -> None:
    # Remove the payment created_at index
    op.drop_index("idx_payment_created_at", table_name="payment")
