"""task_1a2_scheduling_job_tech_assignment

Creates job_tech_assignment table.
Enforces MVP single-primary-tech constraint via partial unique index.

Revision ID: 992df63709de
Revises: 6e3c4fa8431d
Create Date: 2026-04-23 21:53:46
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "992df63709de"
down_revision = "6e3c4fa8431d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_tech_assignment",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Text(), server_default="primary", nullable=False),
        sa.Column("ordinal", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.CheckConstraint("role IN ('primary', 'helper')", name="ck_role_valid"),
        sa.CheckConstraint("ordinal >= 1", name="ck_ordinal_positive"),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"],
            ["user.id"],
            name="fk_jta_assigned_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_jta_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job.id"],
            name="fk_jta_job",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_jta_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_jta_updated_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_jta_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_tech_assignment"),
    )

    # Partial unique: only one active 'primary' per job per tenant
    op.execute("""
        CREATE UNIQUE INDEX uq_job_tech_assignment_active_primary
        ON public.job_tech_assignment
        USING btree (tenant_id, job_id)
        WHERE is_active = true AND role = 'primary'
    """)

    # Partial unique: a user can only appear once (active) per job per tenant
    op.execute("""
        CREATE UNIQUE INDEX uq_job_tech_assignment_active_user
        ON public.job_tech_assignment
        USING btree (tenant_id, job_id, user_id)
        WHERE is_active = true
    """)

    # Supporting lookup index: all active jobs for a user
    op.execute("""
        CREATE INDEX idx_job_tech_assignment_user_active
        ON public.job_tech_assignment
        USING btree (tenant_id, user_id)
        WHERE is_active = true
    """)

    # Standard audit triggers
    op.execute("""
        CREATE TRIGGER audit_job_tech_assignment_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.job_tech_assignment
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_job_tech_assignment_guard_created_immutable
        BEFORE UPDATE ON public.job_tech_assignment
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_job_tech_assignment_set_updated_at
        BEFORE UPDATE ON public.job_tech_assignment
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_job_tech_assignment_changes ON public.job_tech_assignment;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_job_tech_assignment_guard_created_immutable ON public.job_tech_assignment;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_job_tech_assignment_set_updated_at ON public.job_tech_assignment;"
    )
    op.execute("DROP INDEX IF EXISTS public.idx_job_tech_assignment_user_active;")
    op.execute("DROP INDEX IF EXISTS public.uq_job_tech_assignment_active_user;")
    op.execute("DROP INDEX IF EXISTS public.uq_job_tech_assignment_active_primary;")
    op.drop_table("job_tech_assignment")
