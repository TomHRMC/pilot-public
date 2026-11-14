"""phase_fe_1_batch_b15_quote_customer_comment_columns

Revision ID: ada1196b8f39
Revises: 5026cc474168
Create Date: 2026-05-03 14:30:11.000000

B15/A83: Add 6 customer comment columns to quote table.
All columns are nullable additions — simple op.add_column, no backfill required.

Columns:
  customer_acceptance_comment TEXT NULL — customer's note when accepting
  customer_accepted_at TIMESTAMPTZ NULL — timestamp of acceptance
  customer_decline_comment TEXT NULL — customer's note when declining
  customer_decline_reason TEXT NULL CHECK: pricing|scope|timing|other_contractor|other
  customer_declined_at TIMESTAMPTZ NULL — timestamp of decline
  customer_email_at_action TEXT NULL — customer email captured at accept/decline time

Also adds check constraint on customer_decline_reason.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ada1196b8f39"
down_revision = "5026cc474168"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quote", sa.Column("customer_acceptance_comment", sa.Text(), nullable=True)
    )
    op.add_column(
        "quote",
        sa.Column("customer_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "quote", sa.Column("customer_decline_comment", sa.Text(), nullable=True)
    )
    op.add_column(
        "quote", sa.Column("customer_decline_reason", sa.Text(), nullable=True)
    )
    op.add_column(
        "quote",
        sa.Column("customer_declined_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "quote", sa.Column("customer_email_at_action", sa.Text(), nullable=True)
    )

    op.create_check_constraint(
        "quote_customer_decline_reason_chk",
        "quote",
        "customer_decline_reason IN ('pricing', 'scope', 'timing', 'other_contractor', 'other')",
    )


def downgrade() -> None:
    op.drop_constraint("quote_customer_decline_reason_chk", "quote", type_="check")
    op.drop_column("quote", "customer_email_at_action")
    op.drop_column("quote", "customer_declined_at")
    op.drop_column("quote", "customer_decline_reason")
    op.drop_column("quote", "customer_decline_comment")
    op.drop_column("quote", "customer_accepted_at")
    op.drop_column("quote", "customer_acceptance_comment")
