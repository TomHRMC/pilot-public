"""Phase 6.0.1 Task 1: FK constraints for Common & Reference audit columns

Revision ID: 55be0a40204a
Revises:
Create Date: 2026-04-13 17:30

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "55be0a40204a"
down_revision: str | None = "0c524bb2e266"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add Foreign Key constraints to audit columns (created_by, updated_by)
    for Common & Reference tables (Task 1 of Phase 6.0.1).

    Total: 38 FK constraints across 20 tables
    - 18 tables: Both created_by AND updated_by (36 constraints)
    - 2 tables: Only created_by (2 constraints)
    """

    # Tables with BOTH created_by and updated_by FK constraints
    tables_with_both = [
        "address_type",
        "contact_type",
        "entity_type",
        "currency",
        "taxability_code",
        "notification_channel",
        "notification_type",
        "notification_template",
        "notification_outbox",
        "app_service",
        "app_service_category",
        "app_service_provider",
        "sso_provider",
        "platform_role",
        "password_policy",
        "webhook_event_type",
        "qco_line_type",
        "qpl_contact_action_type",
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

    # Append-only tables with ONLY created_by FK constraint
    tables_with_created_only = [
        "notification_event",
        "jwk_status",
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
    """
    Remove Foreign Key constraints from audit columns.
    Drop in reverse order for clean rollback.
    """

    # Drop append-only table FK constraints
    tables_with_created_only = [
        "notification_event",
        "jwk_status",
    ]

    for table_name in tables_with_created_only:
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )

    # Drop both created_by and updated_by FK constraints
    tables_with_both = [
        "address_type",
        "contact_type",
        "entity_type",
        "currency",
        "taxability_code",
        "notification_channel",
        "notification_type",
        "notification_template",
        "notification_outbox",
        "app_service",
        "app_service_category",
        "app_service_provider",
        "sso_provider",
        "platform_role",
        "password_policy",
        "webhook_event_type",
        "qco_line_type",
        "qpl_contact_action_type",
    ]

    for table_name in tables_with_both:
        op.drop_constraint(
            f"fk_{table_name}_updated_by", table_name, type_="foreignkey"
        )
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )
