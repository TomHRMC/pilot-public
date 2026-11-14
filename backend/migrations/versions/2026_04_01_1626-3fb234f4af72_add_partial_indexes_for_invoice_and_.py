"""add_partial_indexes_for_invoice_and_expense_queries_task11

Revision ID: 3fb234f4af72
Revises: 3b01a0ab356f
Create Date: 2026-04-01 16:26:44.199167+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3fb234f4af72"
down_revision: str | None = "3b01a0ab356f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create partial indexes for invoice aging report and unbilled expense queries"""

    # CONCURRENTLY requires running outside transaction block
    # Get connection and commit any existing transaction
    conn = op.get_bind()

    # Close the current transaction to allow CONCURRENTLY operations
    if conn.in_transaction():
        conn.commit()

    # Set connection to autocommit mode for CONCURRENTLY operations
    conn.connection.set_isolation_level(0)  # AUTOCOMMIT

    try:
        # Gap 1: idx_invoice_balance - Speed up aging report queries
        # Only indexes invoices with outstanding balances (balance_due_cents > 0)
        # Expected performance: 50x faster (500ms → 10ms p95)
        conn.execute(
            sa.text(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_balance ON invoice (balance_due_cents) WHERE balance_due_cents > 0"
            )
        )

        # Gap 2: idx_job_expense_unbilled - Speed up unbilled expense queries
        # Only indexes billable expenses not yet invoiced
        # Expected performance: 100x faster (1s → 10ms p95)
        conn.execute(
            sa.text(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_expense_unbilled ON job_expense (job_id) WHERE is_billable = true AND invoice_line_id IS NULL"
            )
        )
    finally:
        # Restore default isolation level (READ COMMITTED)
        conn.connection.set_isolation_level(1)


def downgrade() -> None:
    """Drop partial indexes"""

    # CONCURRENTLY requires running outside transaction block
    # Get connection and commit any existing transaction
    conn = op.get_bind()

    # Close the current transaction to allow CONCURRENTLY operations
    if conn.in_transaction():
        conn.commit()

    # Set connection to autocommit mode for CONCURRENTLY operations
    conn.connection.set_isolation_level(0)  # AUTOCOMMIT

    try:
        # Drop idx_job_expense_unbilled
        conn.execute(
            sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_job_expense_unbilled")
        )

        # Drop idx_invoice_balance
        conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS idx_invoice_balance"))
    finally:
        # Restore default isolation level (READ COMMITTED)
        conn.connection.set_isolation_level(1)
