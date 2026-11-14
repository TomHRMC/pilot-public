"""phase_fe_1_batch_b9_user_setting_override

Revision ID: c9cf97fd02cf
Revises: caab6514959e
Create Date: 2026-05-02 14:04:37

B9/A53: Creates user_setting_override table — Tier 1 of the three-tier settings resolver.
One row per (tenant_id, user_id, setting_key). Includes all three mandatory triggers.
Also seeds settings.read, settings.tenant.write, settings.user_override.write RBAC permissions.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c9cf97fd02cf"
down_revision: str | None = "caab6514959e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Create user_setting_override table
    # -------------------------------------------------------------------------
    op.create_table(
        "user_setting_override",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("setting_key", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_user_setting_override_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            ondelete="CASCADE",
            name="fk_user_setting_override_user",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_user_setting_override_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_user_setting_override_updated_by",
        ),
        sa.PrimaryKeyConstraint(
            "tenant_id",
            "user_id",
            "setting_key",
            name="pk_user_setting_override",
        ),
    )
    op.create_index(
        "ix_user_setting_override_tenant_user",
        "user_setting_override",
        ["tenant_id", "user_id"],
    )
    op.create_index(
        "ix_user_setting_override_tenant_key",
        "user_setting_override",
        ["tenant_id", "setting_key"],
    )

    # -------------------------------------------------------------------------
    # Mandatory triggers (per §13.4 migration standards)
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE TRIGGER audit_user_setting_override_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.user_setting_override
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_user_setting_override_guard_created_immutable
        BEFORE UPDATE ON public.user_setting_override
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_user_setting_override_set_updated_at
        BEFORE UPDATE ON public.user_setting_override
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # -------------------------------------------------------------------------
    # Seed B9 RBAC permissions into platform_role.permissions
    # settings.read          → all roles (owner, accountant, technician, office_staff)
    # settings.tenant.write  → owner, accountant
    # settings.user_override.write → all roles
    # -------------------------------------------------------------------------
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["settings.read", "settings.user_override.write"]'::jsonb
        WHERE code IN ('owner', 'accountant', 'technician', 'office_staff')
    """)
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["settings.tenant.write"]'::jsonb
        WHERE code IN ('owner', 'accountant')
    """)


def downgrade() -> None:
    # -------------------------------------------------------------------------
    # Remove seeded permissions
    # -------------------------------------------------------------------------
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text NOT IN (
                '"settings.read"',
                '"settings.tenant.write"',
                '"settings.user_override.write"'
            )
        )
        WHERE code IN ('owner', 'accountant', 'technician', 'office_staff')
    """)

    # -------------------------------------------------------------------------
    # Drop triggers
    # -------------------------------------------------------------------------
    op.execute(
        "DROP TRIGGER IF EXISTS audit_user_setting_override_changes ON public.user_setting_override;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_setting_override_guard_created_immutable ON public.user_setting_override;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_setting_override_set_updated_at ON public.user_setting_override;"
    )

    # -------------------------------------------------------------------------
    # Drop indexes and table
    # -------------------------------------------------------------------------
    op.drop_index(
        "ix_user_setting_override_tenant_key", table_name="user_setting_override"
    )
    op.drop_index(
        "ix_user_setting_override_tenant_user", table_name="user_setting_override"
    )
    op.drop_table("user_setting_override")
