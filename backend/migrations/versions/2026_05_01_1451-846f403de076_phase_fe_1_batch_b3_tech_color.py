"""phase_fe_1_batch_b3_tech_color

Revision ID: 846f403de076
Revises: 5af6e7e81a01
Create Date: 2026-05-01 14:51:11.000000

B3/A18: Add display_color to user table and tech_color_palette to tenant_settings.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "846f403de076"
down_revision: str | None = "dc5b82049f97"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add display_color to user — additive nullable, no backfill required
    op.add_column("user", sa.Column("display_color", sa.String(7), nullable=True))

    # Add tech_color_palette to tenant_settings — additive nullable JSONB
    op.add_column(
        "tenant_settings",
        sa.Column("tech_color_palette", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_settings", "tech_color_palette")
    op.drop_column("user", "display_color")
