"""phase_6_0_task_2_partial_indexes_exclusion

Revision ID: cc74125f04dc
Revises: 9c399e4369a1
Create Date: 2026-04-13 14:19:09.640993+00:00

Phase 6.0 Task 2: Partial indexes and GiST exclusion constraint

Changes:
- 4 new partial indexes for optimized filtered queries
- 1 GiST exclusion constraint for temporal overlap prevention
- 1 redundant index removal
- Replace existing supplier_item_price exclusion constraint with simplified version
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc74125f04dc"
down_revision: str | None = "9c399e4369a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Ensure btree_gist extension exists (required for exclusion constraint)
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    # Partial Index 1: JobExpense unbilled expenses (use raw SQL with IF NOT EXISTS)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_job_expense_unbilled
        ON job_expense (job_id)
        WHERE is_billable = true AND invoice_line_id IS NULL;
    """)

    # Partial Index 2: UserEndpoint primary email (unique)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_endpoint_primary_email
        ON user_endpoint (user_id)
        WHERE channel='email' AND is_primary = true;
    """)

    # Partial Index 3: UserEndpoint email value case-insensitive (unique)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_endpoint_email_value_lower
        ON user_endpoint (lower(value))
        WHERE channel='email' AND is_primary = true;
    """)

    # Partial Index 4: IntegrationCredential expiration
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_integration_cred_expires
        ON integration_credential (expires_at)
        WHERE expires_at IS NOT NULL;
    """)

    # GiST Exclusion Constraint: Replace old constraint with new standardized name
    # Keep NULL-safe COALESCE logic for multi-tenant support
    # First, drop the existing exclusion constraint
    op.execute("""
        ALTER TABLE supplier_item_price
        DROP CONSTRAINT IF EXISTS sip_no_overlap;
    """)

    # Then, create the new NULL-safe exclusion constraint with standardized name
    op.execute("""
        ALTER TABLE supplier_item_price
        ADD CONSTRAINT exclude_supplier_item_price_period_overlap
        EXCLUDE USING gist (
            supplier_item_id WITH =,
            COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid) WITH =,
            valid_period WITH &&
        );
    """)

    # Remove redundant index (covered by composite index idx_conv_msg_session_time)
    op.execute("DROP INDEX IF EXISTS ix_conversation_message_session_id;")


def downgrade() -> None:
    # Restore redundant index
    op.create_index(
        "ix_conversation_message_session_id", "conversation_message", ["session_id"]
    )

    # Drop new exclusion constraint
    op.execute("""
        ALTER TABLE supplier_item_price
        DROP CONSTRAINT IF EXISTS exclude_supplier_item_price_period_overlap;
    """)

    # Restore old NULL-safe exclusion constraint
    op.execute("""
        ALTER TABLE supplier_item_price
        ADD CONSTRAINT sip_no_overlap
        EXCLUDE USING gist (
            supplier_item_id WITH =,
            COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid) WITH =,
            valid_period WITH &&
        );
    """)

    # Drop partial indexes
    op.drop_index("idx_integration_cred_expires", table_name="integration_credential")
    op.drop_index("idx_user_endpoint_email_value_lower", table_name="user_endpoint")
    op.drop_index("idx_user_endpoint_primary_email", table_name="user_endpoint")
    op.drop_index("idx_job_expense_unbilled", table_name="job_expense")
