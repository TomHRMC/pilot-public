"""mob_b0_nec_calculation_log

Adds nec_calculation_log table for tracking NEC calculation results.
Unblocks MOB-B4 (Calcs Tab frontend) which requires POST /api/v1/nec/calculate.

Table: nec_calculation_log
  - Tenant-scoped (nec calculations are tenant-specific)
  - Optional job_id linkage (calc may be done outside job context)
  - inputs_json + result_json JSONB for flexible calc-type storage
  - is_offline_calc flag distinguishes client-side vs server-side
  - idempotency_key UUID for offline sync dedup (UNIQUE constraint)
  - Triggers: set_updated_at, guard_created_fields_immutable, audit.log_changes

Permission: nec.calculate (already in technician role — no new seed needed)

Revision ID: 50e2ffd2a388
Revises: 5ec7fe1e46d8
Create Date: 2026-06-05 22:43:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "50e2ffd2a388"
down_revision = "5ec7fe1e46d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # Create nec_calculation_log table
    # ---------------------------------------------------------------------------
    op.create_table(
        "nec_calculation_log",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("calc_type", sa.String(50), nullable=False),
        sa.Column(
            "nec_guide_version",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'2023'"),
        ),
        sa.Column(
            "inputs_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "result_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "is_offline_calc",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "idempotency_key",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "client_capture_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "calc_type IN ('voltage_drop', 'conduit_fill', 'ampacity')",
            name="ck_nec_calc_type",
        ),
        sa.CheckConstraint(
            "tenant_id IS NOT NULL",
            name="ck_nec_calc_log_tenant_not_null",
        ),
    )

    # ---------------------------------------------------------------------------
    # Indexes
    # ---------------------------------------------------------------------------
    op.create_index(
        "idx_nec_calc_log_tenant_created",
        "nec_calculation_log",
        ["tenant_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_nec_calc_log_job",
        "nec_calculation_log",
        ["job_id"],
        postgresql_where=sa.text("job_id IS NOT NULL"),
    )
    op.create_index(
        "idx_nec_calc_log_user",
        "nec_calculation_log",
        ["user_id", sa.text("created_at DESC")],
    )

    # ---------------------------------------------------------------------------
    # Triggers
    # ---------------------------------------------------------------------------
    op.execute(
        "CREATE TRIGGER audit_nec_calculation_log_changes "
        "AFTER INSERT OR UPDATE OR DELETE ON public.nec_calculation_log "
        "FOR EACH ROW EXECUTE FUNCTION audit.log_changes();"
    )
    op.execute(
        "CREATE TRIGGER trg_nec_calc_log_updated_at "
        "BEFORE UPDATE ON public.nec_calculation_log "
        "FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();"
    )
    op.execute(
        "CREATE TRIGGER trg_nec_calc_log_guard_created_immutable "
        "BEFORE UPDATE ON public.nec_calculation_log "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();"
    )


def downgrade() -> None:
    # Drop triggers first
    op.execute(
        "DROP TRIGGER IF EXISTS trg_nec_calc_log_guard_created_immutable "
        "ON public.nec_calculation_log;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_nec_calc_log_updated_at "
        "ON public.nec_calculation_log;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_nec_calculation_log_changes "
        "ON public.nec_calculation_log;"
    )

    # Drop indexes
    op.drop_index("idx_nec_calc_log_user", table_name="nec_calculation_log")
    op.drop_index("idx_nec_calc_log_job", table_name="nec_calculation_log")
    op.drop_index("idx_nec_calc_log_tenant_created", table_name="nec_calculation_log")

    # Drop table (cascades constraints, FKs, and the idempotency_key UNIQUE index)
    op.drop_table("nec_calculation_log")
