"""task_1a2_scheduling_calendar_tables

Creates three new scheduling/calendar tables:
  - tenant_calendar_integration  (mutable, StandardAuditMixin)
  - calendar_sync_log            (append-only, immutable guard trigger)
  - calendar_sync_conflict       (mutable, StandardAuditMixin)

Revision ID: 9ba3ca034827
Revises: 3b2ac47ee8ab
Create Date: 2026-04-23 21:48:35
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "9ba3ca034827"
down_revision = "3b2ac47ee8ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. tenant_calendar_integration
    # ------------------------------------------------------------------
    op.create_table(
        "tenant_calendar_integration",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider_code", sa.Text(), nullable=False),
        sa.Column("external_calendar_id", sa.Text(), nullable=False),
        sa.Column("access_token_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_status", sa.Text(), server_default="active", nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_cursor", sa.Text(), nullable=True),
        sa.Column("connected_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider_code IN ('google', 'outlook')", name="ck_provider_code"
        ),
        sa.CheckConstraint(
            "sync_status IN ('active', 'paused', 'error')", name="ck_sync_status"
        ),
        sa.ForeignKeyConstraint(
            ["connected_by_user_id"],
            ["user.id"],
            name="fk_tci_connected_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_tci_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_tci_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_tci_updated_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tenant_calendar_integration"),
        sa.UniqueConstraint("tenant_id", name="uq_tci_tenant"),
    )
    op.create_index(
        "idx_tci_tenant",
        "tenant_calendar_integration",
        ["tenant_id"],
    )

    # Standard triggers for tenant_calendar_integration
    op.execute("""
        CREATE TRIGGER audit_tenant_calendar_integration_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.tenant_calendar_integration
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_calendar_integration_guard_created_immutable
        BEFORE UPDATE ON public.tenant_calendar_integration
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_calendar_integration_set_updated_at
        BEFORE UPDATE ON public.tenant_calendar_integration
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ------------------------------------------------------------------
    # 2. calendar_sync_log  (append-only)
    # ------------------------------------------------------------------
    op.create_table(
        "calendar_sync_log",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("external_event_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "error_detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "payload_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.CheckConstraint("direction IN ('push', 'pull')", name="ck_direction"),
        sa.CheckConstraint(
            "entity_type IN ('job', 'availability')", name="ck_entity_type"
        ),
        sa.CheckConstraint(
            "status IN ('success', 'conflict', 'error')", name="ck_status"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_csl_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_csl_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_calendar_sync_log"),
    )
    op.create_index(
        "idx_calendar_sync_log_tenant_recent",
        "calendar_sync_log",
        ["tenant_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_calendar_sync_log_entity",
        "calendar_sync_log",
        ["tenant_id", "entity_type", "entity_id", sa.text("created_at DESC")],
    )

    # Immutable guard trigger (append-only — no audit_log or set_updated_at)
    op.execute("""
        CREATE TRIGGER trg_calendar_sync_log_guard_created_immutable
        BEFORE UPDATE ON public.calendar_sync_log
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)

    # ------------------------------------------------------------------
    # 3. calendar_sync_conflict
    # ------------------------------------------------------------------
    op.create_table(
        "calendar_sync_conflict",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column(
            "local_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "remote_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "resolution IS NULL OR resolution IN ('accept_local', 'accept_remote')",
            name="ck_resolution",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_csc_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job.id"],
            name="fk_csc_job",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"],
            ["user.id"],
            name="fk_csc_resolved_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_csc_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_csc_updated_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_calendar_sync_conflict"),
    )
    op.create_index(
        "idx_calendar_sync_conflict_pending",
        "calendar_sync_conflict",
        ["tenant_id", "created_at"],
        postgresql_where=sa.text("resolution IS NULL"),
    )
    op.create_index(
        "idx_csc_tenant",
        "calendar_sync_conflict",
        ["tenant_id"],
    )

    # Standard triggers for calendar_sync_conflict
    op.execute("""
        CREATE TRIGGER audit_calendar_sync_conflict_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.calendar_sync_conflict
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_calendar_sync_conflict_guard_created_immutable
        BEFORE UPDATE ON public.calendar_sync_conflict
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_calendar_sync_conflict_set_updated_at
        BEFORE UPDATE ON public.calendar_sync_conflict
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    # ------------------------------------------------------------------
    # 3. calendar_sync_conflict
    # ------------------------------------------------------------------
    op.execute(
        "DROP TRIGGER IF EXISTS audit_calendar_sync_conflict_changes ON public.calendar_sync_conflict;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_calendar_sync_conflict_guard_created_immutable ON public.calendar_sync_conflict;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_calendar_sync_conflict_set_updated_at ON public.calendar_sync_conflict;"
    )
    op.drop_index(
        "idx_calendar_sync_conflict_pending", table_name="calendar_sync_conflict"
    )
    op.drop_index("idx_csc_tenant", table_name="calendar_sync_conflict")
    op.drop_table("calendar_sync_conflict")

    # ------------------------------------------------------------------
    # 2. calendar_sync_log
    # ------------------------------------------------------------------
    op.execute(
        "DROP TRIGGER IF EXISTS trg_calendar_sync_log_guard_created_immutable ON public.calendar_sync_log;"
    )
    op.drop_index("idx_calendar_sync_log_entity", table_name="calendar_sync_log")
    op.drop_index("idx_calendar_sync_log_tenant_recent", table_name="calendar_sync_log")
    op.drop_table("calendar_sync_log")

    # ------------------------------------------------------------------
    # 1. tenant_calendar_integration
    # ------------------------------------------------------------------
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_calendar_integration_changes ON public.tenant_calendar_integration;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_calendar_integration_guard_created_immutable ON public.tenant_calendar_integration;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_calendar_integration_set_updated_at ON public.tenant_calendar_integration;"
    )
    op.drop_index("idx_tci_tenant", table_name="tenant_calendar_integration")
    op.drop_table("tenant_calendar_integration")
