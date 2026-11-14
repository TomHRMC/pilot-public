"""add_stripe_connect_account_id_to_tenant

Revision ID: 57475453234c
Revises: 6ed75ec73340
Create Date: 2026-07-21 12:21:02.784781+00:00

Adds stripe_connect_account_id to the tenant table.
This stores the Stripe connected account ID (acct_XXX) when a tenant
connects their Stripe account via the Payment Method settings page.
NULL = not connected (manual payment fallback).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "57475453234c"
down_revision: str | None = "6ed75ec73340"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant",
        sa.Column("stripe_connect_account_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant", "stripe_connect_account_id")
