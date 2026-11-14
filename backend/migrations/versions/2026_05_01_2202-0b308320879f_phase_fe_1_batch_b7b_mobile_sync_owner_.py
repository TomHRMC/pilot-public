"""phase_fe_1_batch_b7b_mobile_sync_owner_escalation

Revision ID: 0b308320879f
Revises: f6220c8d00ae
Create Date: 2026-05-01 22:02:18

B7b / A46 — Owner Escalation Routing & Notification
Creates mobile_sync_owner_escalation table.

This is the gate dependency for B8 (A47/A48 read from this table).
First implementation of §16.11 Mobile-to-Web Escalation Pattern.

Design doc §F.4: conflict_id FK references mobile_sync_event row with status='conflict'.
ON DELETE RESTRICT is correct — conflict event must not be deleted while escalation
references it.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0b308320879f"
down_revision = "f6220c8d00ae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Create mobile_sync_owner_escalation table                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "mobile_sync_owner_escalation",
        sa.Column(
            "id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("originating_user_id", sa.UUID(), nullable=False),
        sa.Column("conflict_id", sa.UUID(), nullable=False),
        sa.Column(
            "escalated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("escalation_reason", sa.Text(), nullable=False),
        sa.Column("escalation_reason_explainer", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("resolved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_action", sa.Text(), nullable=True),
        sa.Column("resolution_payload", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_mobile_sync_owner_escalation"),
        sa.CheckConstraint(
            "escalation_reason IN ('auto_severity', 'tech_chose')",
            name="chk_mobile_sync_escalation_reason",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'resolved', 'rejected')",
            name="chk_mobile_sync_escalation_status",
        ),
        sa.CheckConstraint(
            "resolution_action IS NULL OR resolution_action IN ('used_local', 'used_server', 'manual_edit', 'rejected')",
            name="chk_mobile_sync_escalation_resolution_action",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_mobile_sync_escalation_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["originating_user_id"],
            ["user.id"],
            name="fk_mobile_sync_escalation_originating_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["conflict_id"],
            ["mobile_sync_event.id"],
            name="fk_mobile_sync_escalation_conflict",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"],
            ["user.id"],
            name="fk_mobile_sync_escalation_resolved_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_mobile_sync_escalation_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_mobile_sync_escalation_updated_by",
            ondelete="RESTRICT",
        ),
    )

    # ------------------------------------------------------------------ #
    # 2. Indexes                                                           #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_mobile_sync_owner_escalation_tenant_status",
        "mobile_sync_owner_escalation",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_mobile_sync_owner_escalation_originating_user",
        "mobile_sync_owner_escalation",
        ["originating_user_id"],
    )
    op.create_index(
        "ix_mobile_sync_owner_escalation_conflict_id",
        "mobile_sync_owner_escalation",
        ["conflict_id"],
    )

    # ------------------------------------------------------------------ #
    # 3. Triggers (mandatory per §13.4)                                   #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TRIGGER audit_mobile_sync_owner_escalation_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.mobile_sync_owner_escalation
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER trg_mobile_sync_owner_escalation_guard_created_immutable
        BEFORE UPDATE ON public.mobile_sync_owner_escalation
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)

    op.execute("""
        CREATE TRIGGER trg_mobile_sync_owner_escalation_set_updated_at
        BEFORE UPDATE ON public.mobile_sync_owner_escalation
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_mobile_sync_owner_escalation_changes ON public.mobile_sync_owner_escalation;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_mobile_sync_owner_escalation_guard_created_immutable ON public.mobile_sync_owner_escalation;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_mobile_sync_owner_escalation_set_updated_at ON public.mobile_sync_owner_escalation;"
    )
    op.drop_index(
        "ix_mobile_sync_owner_escalation_conflict_id",
        table_name="mobile_sync_owner_escalation",
    )
    op.drop_index(
        "ix_mobile_sync_owner_escalation_originating_user",
        table_name="mobile_sync_owner_escalation",
    )
    op.drop_index(
        "ix_mobile_sync_owner_escalation_tenant_status",
        table_name="mobile_sync_owner_escalation",
    )
    op.drop_table("mobile_sync_owner_escalation")
