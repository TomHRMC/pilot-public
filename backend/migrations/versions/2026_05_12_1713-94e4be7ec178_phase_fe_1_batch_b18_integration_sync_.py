"""phase_fe_1_batch_b18_integration_sync_conflict_a49_columns

FIND-090 (S2 High) — Add conflict_subtype + financial_delta_payload to
integration_sync_conflict. These columns were declared in A49 but the migration
was never run (discovered via MCP code review 2026-05-08).

Columns added:
  - conflict_subtype VARCHAR NULL
    CHECK (conflict_subtype IS NULL OR conflict_subtype IN
           ('customer','quote','invoice','expense','deletion_local','deletion_remote'))
  - financial_delta_payload JSONB NULL
    Stores {"delta_cents": int} for financial entity conflicts; NULL for
    non-financial entities (customer).

Code change shipped with migration: quickbooks_sync.queue_conflict() now calls
compute_financial_delta() and writes conflict_subtype + financial_delta_payload
to the created conflict row.

Revision ID: 94e4be7ec178
Revises: 0953b4d8ef62
Create Date: 2026-05-12 17:13:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "94e4be7ec178"
down_revision = "0953b4d8ef62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "integration_sync_conflict",
        sa.Column("conflict_subtype", sa.String(), nullable=True),
    )
    op.create_check_constraint(
        "integration_sync_conflict_subtype_chk",
        "integration_sync_conflict",
        "conflict_subtype IS NULL OR conflict_subtype IN "
        "('customer','quote','invoice','expense','deletion_local','deletion_remote')",
    )
    op.add_column(
        "integration_sync_conflict",
        sa.Column("financial_delta_payload", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("integration_sync_conflict", "financial_delta_payload")
    op.drop_constraint(
        "integration_sync_conflict_subtype_chk",
        "integration_sync_conflict",
        type_="check",
    )
    op.drop_column("integration_sync_conflict", "conflict_subtype")
