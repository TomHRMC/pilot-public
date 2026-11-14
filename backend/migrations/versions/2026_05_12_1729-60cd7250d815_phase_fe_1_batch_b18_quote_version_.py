"""phase_fe_1_batch_b18_quote_version_presentation_style

FIND-095 (S2 High) — Add presentation_style column to quote_version.
Backfill existing rows to 'clean'. Add CHECK constraint.

Column: presentation_style TEXT NOT NULL DEFAULT 'clean'
CHECK: presentation_style IN ('clean','line_itemed','hybrid')

Revision ID: 60cd7250d815
Revises: 94e4be7ec178
Create Date: 2026-05-12 17:29:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "60cd7250d815"
down_revision = "94e4be7ec178"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Add as nullable first (backfill-safe pattern)
    op.add_column(
        "quote_version",
        sa.Column(
            "presentation_style",
            sa.String(),
            nullable=True,
        ),
    )

    # Part 2: Backfill existing rows
    op.execute(
        "UPDATE quote_version SET presentation_style = 'clean' "
        "WHERE presentation_style IS NULL"
    )

    # Part 3: Tighten to NOT NULL + server default
    op.alter_column(
        "quote_version",
        "presentation_style",
        nullable=False,
        server_default=sa.text("'clean'"),
    )

    # Part 4: Add CHECK constraint
    op.create_check_constraint(
        "quote_version_presentation_style_chk",
        "quote_version",
        "presentation_style IN ('clean','line_itemed','hybrid')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "quote_version_presentation_style_chk",
        "quote_version",
        type_="check",
    )
    op.drop_column("quote_version", "presentation_style")
