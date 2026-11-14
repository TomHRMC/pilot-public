"""phase_4_9_normalize_connector_run_log_status_task1

Revision ID: a76bd9e685d3
Revises: d80835df1f50
Create Date: 2026-04-08 18:39:58.226456+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a76bd9e685d3"
down_revision: str | None = "d80835df1f50"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Step 1: Normalize legacy status values (safety UPDATE - table is empty but include for completeness)
    op.execute("""
        UPDATE connector_run_log
        SET status = CASE
            WHEN status = 'completed' THEN 'success'
            WHEN status = 'cancelled' THEN 'failed'
            ELSE status
        END
        WHERE status IN ('completed', 'cancelled')
    """)

    # Step 2: Drop old constraint
    op.drop_constraint(
        "connector_run_log_status_chk", "connector_run_log", type_="check"
    )

    # Step 3: Add new constraint with updated values
    op.create_check_constraint(
        "connector_run_log_status_chk",
        "connector_run_log",
        "status IN ('running', 'success', 'failed')",
    )


def downgrade() -> None:
    # Step 1: Drop new constraint
    op.drop_constraint(
        "connector_run_log_status_chk", "connector_run_log", type_="check"
    )

    # Step 2: Add old constraint with legacy values
    op.create_check_constraint(
        "connector_run_log_status_chk",
        "connector_run_log",
        "status IN ('running', 'completed', 'failed', 'cancelled')",
    )

    # Step 3: Reverse data mapping (only if needed - map 'success' back to 'completed')
    op.execute("""
        UPDATE connector_run_log
        SET status = CASE
            WHEN status = 'success' THEN 'completed'
            ELSE status
        END
        WHERE status = 'success'
    """)
