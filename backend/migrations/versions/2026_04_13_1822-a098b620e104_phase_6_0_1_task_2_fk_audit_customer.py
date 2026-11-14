"""phase_6_0_1_task_2_fk_audit_customer

Phase 6.0.1 Task 2: Add Foreign Key constraints for customer & site management audit columns.
This migration adds database-level referential integrity enforcement for created_by and updated_by
columns across 12 tables in the customer and site management domain.

Scope: 12 tables, 23 FK constraints total
- 11 tables with BOTH created_by AND updated_by FKs (22 constraints)
- 1 table with ONLY created_by FK (1 constraint)

Revision ID: a098b620e104
Revises: 55be0a40204a
Create Date: 2026-04-13 18:22:04.967405+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a098b620e104"
down_revision: str | None = "55be0a40204a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add FK constraints for tables with BOTH created_by AND updated_by
    for table_name in [
        "customer",
        "customer_lifecycle_status",
        "site",
        "site_lifecycle_status",
        "address",
        "contact",
        "contact_endpoint",
        "contact_notification_pref",
        "entity_address",
        "entity_contact",
        "conversation_session",
    ]:
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

    # Add FK constraints for append-only tables (created_by only)
    for table_name in ["contact_portal_invite"]:
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

    # Drop append-only table constraints
    for table_name in ["contact_portal_invite"]:
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )

    # Drop constraints for tables with both created_by and updated_by
    for table_name in [
        "customer",
        "customer_lifecycle_status",
        "site",
        "site_lifecycle_status",
        "address",
        "contact",
        "contact_endpoint",
        "contact_notification_pref",
        "entity_address",
        "entity_contact",
        "conversation_session",
    ]:
        op.drop_constraint(
            f"fk_{table_name}_updated_by", table_name, type_="foreignkey"
        )
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )
