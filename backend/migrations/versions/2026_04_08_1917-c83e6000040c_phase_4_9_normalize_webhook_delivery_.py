"""phase_4_9_normalize_webhook_delivery_status_task2

Revision ID: c83e6000040c
Revises: a76bd9e685d3
Create Date: 2026-04-08 19:17:41.900600+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c83e6000040c"
down_revision: str | None = "a76bd9e685d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Step 1: Data normalization (no-op since table is empty, but included for safety)
    op.execute("""
        UPDATE webhook_delivery_attempt
        SET status = CASE
            WHEN status = 'delivered' THEN 'success'
            WHEN status = 'retrying' THEN 'pending'
            ELSE status
        END
        WHERE status IN ('delivered', 'retrying')
    """)

    # Step 2: Drop old constraint
    op.drop_constraint(
        "webhook_delivery_attempt_status_chk", "webhook_delivery_attempt", type_="check"
    )

    # Step 3: Add new constraint with correct values
    op.create_check_constraint(
        "webhook_delivery_attempt_status_chk",
        "webhook_delivery_attempt",
        "status IN ('pending', 'success', 'failed', 'giving_up')",
    )


def downgrade() -> None:
    # Reverse order: Drop new → Add old → Reverse data
    op.drop_constraint(
        "webhook_delivery_attempt_status_chk", "webhook_delivery_attempt", type_="check"
    )

    op.create_check_constraint(
        "webhook_delivery_attempt_status_chk",
        "webhook_delivery_attempt",
        "status IN ('pending', 'delivered', 'failed', 'retrying')",
    )

    # Reverse data mapping (only if needed)
    op.execute("""
        UPDATE webhook_delivery_attempt
        SET status = CASE
            WHEN status = 'success' THEN 'delivered'
            ELSE status
        END
        WHERE status = 'success'
    """)
