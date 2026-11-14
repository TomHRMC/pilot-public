"""b21_create_job_recurrence_rule

Revision ID: ea51ca036a76
Revises: f7f30492c3e4
Create Date: 2026-07-12 16:44:38

B21: Create job_recurrence_rule table for recurring job scheduling.

Stores the rule template for recurring job series (e.g., weekly electrical inspection).
A Celery Beat task runs daily at 06:00 UTC and creates job instances when due.

Trigger functions (confirmed from existing migrations):
  - audit.log_changes()                       — audit trail
  - public.guard_created_fields_immutable()   — immutability guard
  - public.set_updated_at()                   — updated_at sync
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ea51ca036a76"
down_revision = "f7f30492c3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_recurrence_rule",
        # Audit mixin columns
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        # PK
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        # Tenant / entity FKs
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customer.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("site.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Recurrence definition
        sa.Column("pattern", sa.String(20), nullable=False),
        sa.Column("interval_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("max_occurrences", sa.Integer(), nullable=True),
        sa.Column(
            "occurrences_created", sa.Integer(), server_default="0", nullable=False
        ),
        # Scheduling state
        sa.Column("next_job_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_job_created_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Job template fields
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "default_tech_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes_template", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        # CHECK constraints
        sa.CheckConstraint(
            "pattern IN ('daily','weekly','monthly','annually')",
            name="chk_recurrence_pattern",
        ),
        sa.CheckConstraint("interval_count >= 1", name="chk_interval_count_positive"),
    )

    # Indexes
    op.create_index(
        "ix_job_recurrence_rule_tenant_id", "job_recurrence_rule", ["tenant_id"]
    )
    op.create_index(
        "ix_job_recurrence_rule_next_job_at",
        "job_recurrence_rule",
        ["next_job_at"],
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        "ix_job_recurrence_rule_customer_id", "job_recurrence_rule", ["customer_id"]
    )

    # Standard 3-trigger set (matches existing migrations pattern)
    op.execute("""
        CREATE TRIGGER audit_job_recurrence_rule_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.job_recurrence_rule
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER guard_job_recurrence_rule_created_immutable
        BEFORE UPDATE ON public.job_recurrence_rule
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER set_job_recurrence_rule_updated_at
        BEFORE UPDATE ON public.job_recurrence_rule
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS set_job_recurrence_rule_updated_at ON public.job_recurrence_rule"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS guard_job_recurrence_rule_created_immutable ON public.job_recurrence_rule"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_job_recurrence_rule_changes ON public.job_recurrence_rule"
    )
    op.drop_index(
        "ix_job_recurrence_rule_customer_id", table_name="job_recurrence_rule"
    )
    op.drop_index(
        "ix_job_recurrence_rule_next_job_at", table_name="job_recurrence_rule"
    )
    op.drop_index("ix_job_recurrence_rule_tenant_id", table_name="job_recurrence_rule")
    op.drop_table("job_recurrence_rule")
