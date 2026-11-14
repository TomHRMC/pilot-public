"""phase_fe_1_batch_b13b_fix_customer_communication_message_read_state_audit_mixin

Revision ID: 6f105cb542fd
Revises: b166aa81d868
Create Date: 2026-05-03 11:43:51.000000

B13b Item 2 — Gap Type 2 remediation
Table: customer_communication_message_read_state
Adds: created_at TIMESTAMPTZ NOT NULL (backfilled from read_at), created_by UUID NULL
Installs: audit_changes trigger + guard_created_immutable trigger (AppendOnly set)
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6f105cb542fd"
down_revision = "b166aa81d868"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Add as nullable
    op.add_column(
        "customer_communication_message_read_state",
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "customer_communication_message_read_state",
        sa.Column("created_by", sa.UUID(), nullable=True),
    )

    # Part 2: Backfill created_at from read_at (semantically identical)
    op.execute("""
        UPDATE customer_communication_message_read_state
        SET created_at = read_at
    """)

    # Part 3: Lock NOT NULL
    op.alter_column(
        "customer_communication_message_read_state", "created_at", nullable=False
    )

    # Part 4: Install AppendOnly triggers
    op.execute("""
        CREATE TRIGGER audit_customer_communication_message_read_state_changes
        AFTER INSERT OR UPDATE OR DELETE ON customer_communication_message_read_state
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_customer_communication_message_read_state_guard_created_immutable
        BEFORE UPDATE ON customer_communication_message_read_state
        FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS "
        "trg_customer_communication_message_read_state_guard_created_immutable "
        "ON customer_communication_message_read_state;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS "
        "audit_customer_communication_message_read_state_changes "
        "ON customer_communication_message_read_state;"
    )
    op.drop_column("customer_communication_message_read_state", "created_by")
    op.drop_column("customer_communication_message_read_state", "created_at")
