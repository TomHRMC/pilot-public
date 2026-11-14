"""b21_add_recurrence_rule_id_to_job

Revision ID: aa84a3d6afe8
Revises: ea51ca036a76
Create Date: 2026-07-12 16:45:26

B21: Add nullable recurrence_rule_id FK to the job table.
Links a generated job back to the JobRecurrenceRule that spawned it.
Nullable — manually created jobs have NULL.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "aa84a3d6afe8"
down_revision = "ea51ca036a76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job",
        sa.Column(
            "recurrence_rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_recurrence_rule.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_job_recurrence_rule_id", "job", ["recurrence_rule_id"])


def downgrade() -> None:
    op.drop_index("ix_job_recurrence_rule_id", table_name="job")
    op.drop_column("job", "recurrence_rule_id")
