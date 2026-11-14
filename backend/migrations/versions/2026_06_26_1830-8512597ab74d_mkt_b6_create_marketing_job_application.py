"""mkt_b6_create_marketing_job_application

Revision ID: 8512597ab74d
Revises: 2d243894a93a
Create Date: 2026-06-26 18:30:30.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8512597ab74d"
down_revision: str | None = "2d243894a93a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketing_job_application",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("linkedin_url", sa.String(), nullable=True),
        sa.Column("portfolio_url", sa.String(), nullable=True),
        sa.Column("why_interested", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_reviewed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_marketing_job_application_email",
        "marketing_job_application",
        ["email"],
    )
    op.create_index(
        "ix_marketing_job_application_created_at",
        "marketing_job_application",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_marketing_job_application_created_at",
        table_name="marketing_job_application",
    )
    op.drop_index(
        "ix_marketing_job_application_email",
        table_name="marketing_job_application",
    )
    op.drop_table("marketing_job_application")
