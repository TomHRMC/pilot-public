"""task_1c8_labor_rate_version_catalog_table

Revision ID: 3b9a777d2de9
Revises: a547f5b811b3
Create Date: 2026-04-21 13:38:00.000000

Task 1-C-8: labor_rate_version Catalog Table
=============================================
Creates a new `labor_rate_version` table for catalog-managed burdened labor
rates by skill tier with temporal versioning.

Schema:
  - bigserial PK
  - tenant_id (FK → tenant.id, RESTRICT)
  - skill_level_code (VARCHAR) — plain tier code, no lookup table
  - hourly_rate_cents (INTEGER) — base hourly rate in cents
  - burden_pct (NUMERIC(7,4)) — overhead burden percentage
  - valid_period (TSTZRANGE) — temporal effectiveness window
  - recorded_at (TIMESTAMPTZ) — when this version was recorded
  - created_at / created_by (from AppendOnlyMixin)

Constraints:
  - GiST exclusion: one active rate per (tenant_id, skill_level_code) at any moment
  - Composite index: ix_labor_rate_version_tenant_skill (tenant_id, skill_level_code)
  - guard_created_fields_immutable trigger (standard append-only pattern)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# revision identifiers, used by Alembic.
revision = "3b9a777d2de9"
down_revision = "a547f5b811b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Create the labor_rate_version table
    # -----------------------------------------------------------------------
    op.create_table(
        "labor_rate_version",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            PG_UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "skill_level_code",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "hourly_rate_cents",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "burden_pct",
            sa.Numeric(7, 4),
            nullable=False,
        ),
        sa.Column(
            "valid_period",
            sa.dialects.postgresql.TSTZRANGE(),
            server_default=sa.text("tstzrange(now(), null, '[)')"),
            nullable=False,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            PG_UUID(as_uuid=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="labor_rate_version_pkey"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_labor_rate_version_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_labor_rate_version_created_by",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "NOT isempty(valid_period)",
            name="labor_rate_version_valid_period_chk",
        ),
    )

    # -----------------------------------------------------------------------
    # Composite index: tenant + skill_level for fast rate lookups
    # -----------------------------------------------------------------------
    op.create_index(
        "ix_labor_rate_version_tenant_skill",
        "labor_rate_version",
        ["tenant_id", "skill_level_code"],
    )

    # -----------------------------------------------------------------------
    # GiST exclusion constraint: one active rate per (tenant, skill) at any time.
    # Using raw SQL because op.create_exclude_constraint() does not support
    # the btree_gist operator class syntax needed for text+uuid equality in GIST.
    # -----------------------------------------------------------------------
    op.execute("""
        ALTER TABLE labor_rate_version
        ADD CONSTRAINT labor_rate_version_no_overlap
        EXCLUDE USING GIST (
            tenant_id        WITH =,
            skill_level_code WITH =,
            valid_period     WITH &&
        )
    """)

    # -----------------------------------------------------------------------
    # guard_created_fields_immutable trigger — standard append-only pattern
    # prevents mutation of created_at / created_by after insert.
    # -----------------------------------------------------------------------
    op.execute("""
        CREATE TRIGGER trg_labor_rate_version_guard_created_immutable
        BEFORE UPDATE ON labor_rate_version
        FOR EACH ROW
        EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # Drop trigger first, then the table (CASCADE removes constraint + index)
    # -----------------------------------------------------------------------
    op.execute("""
        DROP TRIGGER IF EXISTS trg_labor_rate_version_guard_created_immutable
        ON labor_rate_version
    """)
    op.drop_index("ix_labor_rate_version_tenant_skill", table_name="labor_rate_version")
    op.drop_table("labor_rate_version")
