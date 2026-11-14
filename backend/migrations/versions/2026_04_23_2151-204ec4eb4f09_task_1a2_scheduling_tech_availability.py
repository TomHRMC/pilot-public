"""task_1a2_scheduling_tech_availability

Creates the tech_availability table for technician working hours, PTO, and
unavailable blocks. Includes a GIST index for time-range overlap queries.

Revision ID: 204ec4eb4f09
Revises: 9ba3ca034827
Create Date: 2026-04-23 21:51:40
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "204ec4eb4f09"
down_revision = "9ba3ca034827"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tech_availability",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("availability_type", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recurrence_rrule", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.CheckConstraint(
            "availability_type IN ('working_hours', 'pto', 'unavailable')",
            name="ck_availability_type",
        ),
        sa.CheckConstraint(
            "(availability_type = 'working_hours' AND recurrence_rrule IS NOT NULL) OR "
            "(availability_type IN ('pto', 'unavailable') AND starts_at IS NOT NULL "
            "AND ends_at IS NOT NULL AND ends_at > starts_at)",
            name="ck_availability_shape",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_ta_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_ta_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_ta_updated_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_ta_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tech_availability"),
    )

    # btree partial index for active records by user
    op.create_index(
        "idx_tech_availability_user_active",
        "tech_availability",
        ["tenant_id", "user_id"],
        postgresql_where=sa.text("is_active = true"),
    )

    # GIST index for time-range overlap (requires btree_gist extension)
    op.execute("""
        CREATE INDEX idx_tech_availability_time_range
        ON public.tech_availability
        USING gist (
            tenant_id,
            user_id,
            tstzrange(starts_at, ends_at, '[)')
        )
        WHERE
            availability_type = ANY (ARRAY['pto'::text, 'unavailable'::text])
            AND is_active = true
    """)

    # Standard audit triggers
    op.execute("""
        CREATE TRIGGER audit_tech_availability_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.tech_availability
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_tech_availability_guard_created_immutable
        BEFORE UPDATE ON public.tech_availability
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_tech_availability_set_updated_at
        BEFORE UPDATE ON public.tech_availability
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tech_availability_changes ON public.tech_availability;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tech_availability_guard_created_immutable ON public.tech_availability;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tech_availability_set_updated_at ON public.tech_availability;"
    )
    op.execute("DROP INDEX IF EXISTS public.idx_tech_availability_time_range;")
    op.drop_index("idx_tech_availability_user_active", table_name="tech_availability")
    op.drop_table("tech_availability")
