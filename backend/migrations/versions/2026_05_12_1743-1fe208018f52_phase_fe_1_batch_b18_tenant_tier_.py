"""phase_fe_1_batch_b18_tenant_tier_override_reason_required

FIND-103 (S2 High) — Tighten tenant_tier_override.override_reason to NOT NULL.

The override_reason is the audit trail that documents WHY a tenant received a
special billing deal. Without it, financial audits and customer support disputes
have no documented basis.

Action:
  1. Backfill existing NULL rows with a sentinel message
  2. ALTER COLUMN override_reason SET NOT NULL

Revision ID: 1fe208018f52
Revises: fca6bd403dcc
Create Date: 2026-05-12 17:43:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "1fe208018f52"
down_revision = "fca6bd403dcc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Backfill existing NULL rows
    op.execute(
        "UPDATE tenant_tier_override "
        "SET override_reason = 'Backfilled — reason not recorded at time of creation' "
        "WHERE override_reason IS NULL"
    )

    # Part 2: Tighten to NOT NULL
    op.alter_column(
        "tenant_tier_override",
        "override_reason",
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "tenant_tier_override",
        "override_reason",
        nullable=True,
    )
