"""task_1c3_site_structured_access_fields

Revision ID: 08bbc78681fa
Revises: daa91c603bb1
Create Date: 2026-04-20 21:35:22.000000

Task 1-C-3: Add gate_code (VARCHAR(50)), access_instructions (TEXT), and
hazard_notes (TEXT) to the `site` table.

These discrete fields replace the overloaded generic `notes` field for
safety-critical information and allow Voice AI to read out precise, actionable
arrival details to field technicians rather than parsing a free-text blob.

All three columns are nullable — existing site records will simply have NULL
values and the mobile app will prompt to fill them in over time.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "08bbc78681fa"
down_revision = "daa91c603bb1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add gate_code: short VARCHAR(50) — gate/keypad codes, e.g. "#1234"
    op.add_column(
        "site",
        sa.Column("gate_code", sa.String(50), nullable=True),
    )

    # Add access_instructions: free-text arrival/access notes for field techs
    op.add_column(
        "site",
        sa.Column("access_instructions", sa.Text(), nullable=True),
    )

    # Add hazard_notes: safety-critical hazards Voice AI must read out on arrival
    op.add_column(
        "site",
        sa.Column("hazard_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("site", "hazard_notes")
    op.drop_column("site", "access_instructions")
    op.drop_column("site", "gate_code")
