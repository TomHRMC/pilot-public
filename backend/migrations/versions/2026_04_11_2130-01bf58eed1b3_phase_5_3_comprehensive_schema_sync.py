"""Phase 5.3: Comprehensive schema sync (notification + idempotency + indexes + triggers)

Revision ID: 01bf58eed1b3
Revises: 3c89a793b5e4
Create Date: 2026-04-11 21:30:24.972764+00:00

CRITICAL: This migration bundles 4 phases into a single transaction to minimize
database state fragmentation per Phase 5.3 analysis requirements.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "01bf58eed1b3"
down_revision: str | None = "3c89a793b5e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ========== PHASE 1: notification_delivery_attempt ==========

    # 1.1: Rename provider_response → details (data preservation)
    op.alter_column(
        "notification_delivery_attempt", "provider_response", new_column_name="details"
    )

    # 1.2: Add new columns
    op.add_column(
        "notification_delivery_attempt",
        sa.Column("provider_code", sa.String(), nullable=True),
    )
    op.add_column(
        "notification_delivery_attempt",
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "notification_delivery_attempt",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # 1.3: Add foreign key for created_by
    op.create_foreign_key(
        "notification_delivery_attempt_created_by_fkey",
        "notification_delivery_attempt",
        "user",
        ["created_by"],
        ["id"],
    )

    # 1.4: Fix created_at server default
    op.alter_column(
        "notification_delivery_attempt", "created_at", server_default=sa.text("now()")
    )

    # 1.5: Drop old inefficient indexes
    op.drop_index(
        "ix_notification_delivery_attempt_notification_outbox_id",
        table_name="notification_delivery_attempt",
    )
    op.drop_index(
        "ix_notification_delivery_attempt_tenant_id",
        table_name="notification_delivery_attempt",
    )

    # 1.6: Create new composite index
    op.create_index(
        "idx_notif_attempt_outbox_time",
        "notification_delivery_attempt",
        ["notification_outbox_id", sa.text("attempted_at DESC")],
    )

    # ========== PHASE 2: Idempotency Unique Constraints ==========

    # 2.1: Invoice constraints
    op.create_unique_constraint(
        "uq_invoice_tenant_number", "invoice", ["tenant_id", "invoice_number"]
    )
    op.create_unique_constraint(
        "uq_invoice_tenant_idempotency", "invoice", ["tenant_id", "idempotency_key"]
    )

    # 2.2: Quote constraint
    op.create_unique_constraint(
        "uq_quote_tenant_idempotency", "quote", ["tenant_id", "idempotency_key"]
    )

    # 2.3: Payment constraint
    op.create_unique_constraint(
        "uq_payment_tenant_idempotency", "payment", ["tenant_id", "idempotency_key"]
    )

    # ========== PHASE 3: Index Naming Standardization ==========

    # 3.1: conversation_session - Add missing composite index
    op.create_index(
        "idx_conv_session_tenant_user",
        "conversation_session",
        ["tenant_id", "user_id", sa.text("updated_at DESC")],
    )

    # 3.2: job_time_entry - Drop old indexes, create new with correct names
    op.drop_index("ix_job_time_entry_job_id", table_name="job_time_entry")
    op.drop_index("ix_job_time_entry_user_id", table_name="job_time_entry")
    op.create_index("idx_jte_job", "job_time_entry", ["job_id"])
    op.create_index("idx_jte_user", "job_time_entry", ["user_id"])
    op.create_index(
        "idx_jte_started_at", "job_time_entry", [sa.text("started_at DESC")]
    )

    # 3.3: voice_command_log - Drop old index, create new with correct names
    op.drop_index(
        "ix_voice_command_log_total_latency_ms", table_name="voice_command_log"
    )
    op.create_index(
        "idx_voice_log_tenant_time",
        "voice_command_log",
        ["tenant_id", sa.text("created_at DESC")],
    )
    op.create_index("idx_voice_log_intent", "voice_command_log", ["intent_detected"])
    op.create_index("idx_voice_log_latency", "voice_command_log", ["total_latency_ms"])

    # ========== PHASE 4: discount_version Triggers ==========

    # 4.1: Attach audit trigger
    op.execute("""
        CREATE TRIGGER audit_discount_version_changes
        AFTER INSERT OR UPDATE OR DELETE ON public.discount_version
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 4.2: Attach immutability guard trigger
    op.execute("""
        CREATE TRIGGER trg_discount_version_guard_created_immutable
        BEFORE UPDATE ON public.discount_version
        FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
    """)


def downgrade() -> None:
    # ========== REVERSE PHASE 4: discount_version Triggers ==========
    op.execute(
        "DROP TRIGGER IF EXISTS trg_discount_version_guard_created_immutable ON public.discount_version;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_discount_version_changes ON public.discount_version;"
    )

    # ========== REVERSE PHASE 3: Index Naming Standardization ==========
    # voice_command_log
    op.drop_index("idx_voice_log_latency", table_name="voice_command_log")
    op.drop_index("idx_voice_log_intent", table_name="voice_command_log")
    op.drop_index("idx_voice_log_tenant_time", table_name="voice_command_log")
    op.create_index(
        "ix_voice_command_log_total_latency_ms",
        "voice_command_log",
        ["total_latency_ms"],
    )

    # job_time_entry
    op.drop_index("idx_jte_started_at", table_name="job_time_entry")
    op.drop_index("idx_jte_user", table_name="job_time_entry")
    op.drop_index("idx_jte_job", table_name="job_time_entry")
    op.create_index("ix_job_time_entry_user_id", "job_time_entry", ["user_id"])
    op.create_index("ix_job_time_entry_job_id", "job_time_entry", ["job_id"])

    # conversation_session
    op.drop_index("idx_conv_session_tenant_user", table_name="conversation_session")

    # ========== REVERSE PHASE 2: Idempotency Unique Constraints ==========
    op.drop_constraint("uq_payment_tenant_idempotency", "payment", type_="unique")
    op.drop_constraint("uq_quote_tenant_idempotency", "quote", type_="unique")
    op.drop_constraint("uq_invoice_tenant_idempotency", "invoice", type_="unique")
    op.drop_constraint("uq_invoice_tenant_number", "invoice", type_="unique")

    # ========== REVERSE PHASE 1: notification_delivery_attempt ==========
    # Drop new composite index
    op.drop_index(
        "idx_notif_attempt_outbox_time", table_name="notification_delivery_attempt"
    )

    # Restore old indexes
    op.create_index(
        "ix_notification_delivery_attempt_tenant_id",
        "notification_delivery_attempt",
        ["tenant_id"],
    )
    op.create_index(
        "ix_notification_delivery_attempt_notification_outbox_id",
        "notification_delivery_attempt",
        ["notification_outbox_id"],
    )

    # Remove server default from created_at
    op.alter_column("notification_delivery_attempt", "created_at", server_default=None)

    # Drop foreign key and new columns
    op.drop_constraint(
        "notification_delivery_attempt_created_by_fkey",
        "notification_delivery_attempt",
        type_="foreignkey",
    )
    op.drop_column("notification_delivery_attempt", "created_by")
    op.drop_column("notification_delivery_attempt", "duration_ms")
    op.drop_column("notification_delivery_attempt", "provider_code")

    # Rename column back
    op.alter_column(
        "notification_delivery_attempt", "details", new_column_name="provider_response"
    )
