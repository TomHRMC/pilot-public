"""mkt_b9_add_state_notes_to_marketing_waitlist_signup

Revision ID: 9b3f7ea49606
Revises: 8512597ab74d
Create Date: 2026-06-29 18:12:00.000000

MKT-B9-A: Add optional state (VARCHAR) and notes (TEXT) columns to
marketing_waitlist_signup. Both columns are nullable — optional form fields.
No backfill needed.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9b3f7ea49606"
down_revision = "8512597ab74d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketing_waitlist_signup",
        sa.Column("state", sa.String(), nullable=True),
    )
    op.add_column(
        "marketing_waitlist_signup",
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("marketing_waitlist_signup", "notes")
    op.drop_column("marketing_waitlist_signup", "state")
