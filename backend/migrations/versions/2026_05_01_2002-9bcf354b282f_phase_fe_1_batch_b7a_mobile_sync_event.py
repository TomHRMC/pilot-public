"""phase_fe_1_batch_b7a_mobile_sync_event

Revision ID: 9bcf354b282f
Revises: 4c1556ea2a91
Create Date: 2026-05-01 20:02:35

B7a/A38: Create mobile_sync_event append-only table and its indexes.
Also seeds mobile_sync.view permission into owner and operator roles.

Design notes:
  - Append-only log: no updated_at column, no update operations permitted
  - operation_type is free-text TEXT (no CHECK constraint per §F.4)
  - status and conflict_severity have CHECK constraints (fixed state machine)
  - idempotency_uuid stores the client's Idempotency-Key UUID v4
  - Includes standard audit_log, immutable_guard, and updated_at_sync triggers

Indexes:
  - ix_mobile_sync_event_tenant_user_status: primary queue lookup
  - ix_mobile_sync_event_created_at: retention cleanup (30-day archive)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9bcf354b282f"
down_revision = "4c1556ea2a91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mobile_sync_event",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.Text(), nullable=False),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("operation_payload_summary", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("conflict_severity", sa.Text(), nullable=True),
        sa.Column("client_capture_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_mobile_sync_event"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_mobile_sync_event_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_mobile_sync_event_user",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'syncing', 'succeeded', 'failed', 'conflict')",
            name="chk_mobile_sync_event_status",
        ),
        sa.CheckConstraint(
            "conflict_severity IS NULL OR conflict_severity IN "
            "('auto_silent', 'auto_notice', 'tech_resolvable', 'owner_escalation')",
            name="chk_mobile_sync_event_conflict_severity",
        ),
    )

    # Primary index: fast per-tech queue queries by status
    op.create_index(
        "ix_mobile_sync_event_tenant_user_status",
        "mobile_sync_event",
        ["tenant_id", "user_id", "status"],
    )
    # Secondary index: retention cleanup (archive rows > 30 days)
    op.create_index(
        "ix_mobile_sync_event_created_at",
        "mobile_sync_event",
        ["created_at"],
    )

    # Standard audit trigger
    op.execute(
        "CREATE TRIGGER audit_mobile_sync_event_changes "
        "AFTER INSERT OR DELETE OR UPDATE ON public.mobile_sync_event "
        "FOR EACH ROW EXECUTE FUNCTION audit.log_changes()"
    )
    # Immutable guard trigger (prevents backdating created_at etc.)
    op.execute(
        "CREATE TRIGGER trg_mobile_sync_event_guard_created_immutable "
        "BEFORE UPDATE ON public.mobile_sync_event "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()"
    )
    # No set_updated_at trigger — mobile_sync_event is append-only (no updated_at column)

    # Seed mobile_sync.view permission into owner and operator roles
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["mobile_sync.view"]'::jsonb
        WHERE code IN ('owner', 'operator')
          AND NOT (permissions @> '["mobile_sync.view"]'::jsonb)
    """)


def downgrade() -> None:
    # Remove mobile_sync.view permission from owner and operator roles
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(perm)
            FROM jsonb_array_elements_text(permissions) AS perm
            WHERE perm != 'mobile_sync.view'
        )
        WHERE code IN ('owner', 'operator')
    """)

    op.execute(
        "DROP TRIGGER IF EXISTS trg_mobile_sync_event_guard_created_immutable "
        "ON public.mobile_sync_event"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_mobile_sync_event_changes "
        "ON public.mobile_sync_event"
    )
    op.drop_index("ix_mobile_sync_event_created_at", table_name="mobile_sync_event")
    op.drop_index(
        "ix_mobile_sync_event_tenant_user_status", table_name="mobile_sync_event"
    )
    op.drop_table("mobile_sync_event")
