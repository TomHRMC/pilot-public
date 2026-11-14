"""phase_6_0_1_task_6_fk_audit_tenant

Revision ID: 47a3ff6f3f8b
Revises: 5c579d516fc2
Create Date: 2026-04-13 21:38:31.851773+00:00

Phase 6.0.1 Task 6: Add Foreign Key constraints for Tenant & User Management audit columns

This migration adds FK constraints to created_by and updated_by columns for:
- 13 tables with BOTH created_by and updated_by FKs (26 FKs)
- 2 tables with ONLY created_by FK (2 FKs)
- Total: 28 Foreign Key constraints

Special handling for tenant table: Drops existing FK constraints with SET NULL and recreates with RESTRICT.

All FKs use ON DELETE RESTRICT to preserve audit trail integrity.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "47a3ff6f3f8b"
down_revision: str | None = "5c579d516fc2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Special handling for tenant table: Drop existing FK constraints with SET NULL behavior
    op.drop_constraint("fk_tenant_created_by", "tenant", type_="foreignkey")
    op.drop_constraint("fk_tenant_updated_by", "tenant", type_="foreignkey")

    # Recreate tenant FK constraints with RESTRICT behavior
    op.create_foreign_key(
        "fk_tenant_created_by",
        "tenant",
        "user",
        ["created_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_tenant_updated_by",
        "tenant",
        "user",
        ["updated_by"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Tables with BOTH created_by and updated_by FK constraints (excluding tenant, handled above)
    tables_with_both = [
        "tenant_settings",
        "tenant_domain",
        "tenant_user",
        "tenant_user_status",
        "tenant_user_role",
        "tenant_user_notification_pref",
        "tenant_notification_default",
        "tenant_product_feature_override",
        "user_preference",
        "user_endpoint",
        "user_sso_identity",
        "user",  # Self-referential
    ]

    for table_name in tables_with_both:
        op.create_foreign_key(
            f"fk_{table_name}_created_by",
            table_name,
            "user",
            ["created_by"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            f"fk_{table_name}_updated_by",
            table_name,
            "user",
            ["updated_by"],
            ["id"],
            ondelete="RESTRICT",
        )

    # Append-only/versioned tables with ONLY created_by FK constraint
    tables_with_created_only = [
        "tenant_user_invite",
        "tenant_markup_version",
    ]

    for table_name in tables_with_created_only:
        op.create_foreign_key(
            f"fk_{table_name}_created_by",
            table_name,
            "user",
            ["created_by"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    # Drop FK constraints in reverse order

    # Drop created_by-only constraints first
    tables_with_created_only = [
        "tenant_user_invite",
        "tenant_markup_version",
    ]

    for table_name in tables_with_created_only:
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )

    # Drop both created_by and updated_by constraints (excluding tenant, handled last)
    tables_with_both = [
        "tenant_settings",
        "tenant_domain",
        "tenant_user",
        "tenant_user_status",
        "tenant_user_role",
        "tenant_user_notification_pref",
        "tenant_notification_default",
        "tenant_product_feature_override",
        "user_preference",
        "user_endpoint",
        "user_sso_identity",
        "user",  # Self-referential
    ]

    for table_name in tables_with_both:
        op.drop_constraint(
            f"fk_{table_name}_updated_by", table_name, type_="foreignkey"
        )
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )

    # Special handling for tenant: Drop RESTRICT constraints and recreate with SET NULL
    op.drop_constraint("fk_tenant_updated_by", "tenant", type_="foreignkey")
    op.drop_constraint("fk_tenant_created_by", "tenant", type_="foreignkey")

    # Restore original tenant FK constraints with SET NULL behavior
    op.create_foreign_key(
        "fk_tenant_created_by",
        "tenant",
        "user",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_tenant_updated_by",
        "tenant",
        "user",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )
