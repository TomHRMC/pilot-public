"""phase_6_0_1_task_4_fk_audit_quoting

Revision ID: d25bd8d5f87e
Revises: ec96305d27ec
Create Date: 2026-04-13 20:56:58.074824+00:00

Phase 6.0.1 Task 4: Add Foreign Key constraints for audit columns in Quoting System tables.

This migration adds FK constraints on created_by and updated_by columns for all quoting-related
tables to enforce referential integrity with the user table.

Scope:
- 7 tables with BOTH created_by AND updated_by FKs (14 constraints)
- 5 tables with ONLY created_by FK (5 constraints)
- Total: 19 Foreign Key constraints

Tables:
- quote_status, quote_link_status, pricebook_item, quote, quote_line,
  quote_public_link, quote_message (both FKs)
- pricebook_item_version, quote_version, quote_acceptance, quote_line_tax_component,
  quote_public_link_contact_action (created_by only)
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d25bd8d5f87e"
down_revision: str | None = "ec96305d27ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Tables with BOTH created_by and updated_by FK constraints
    tables_with_both_fks = [
        "quote_status",
        "quote_link_status",
        "pricebook_item",
        "quote",
        "quote_line",
        "quote_public_link",
        "quote_message",
    ]

    for table_name in tables_with_both_fks:
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
        "pricebook_item_version",
        "quote_version",
        "quote_acceptance",
        "quote_line_tax_component",
        "quote_public_link_contact_action",
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

    # Drop created_by-only FK constraints first
    tables_with_created_only = [
        "pricebook_item_version",
        "quote_version",
        "quote_acceptance",
        "quote_line_tax_component",
        "quote_public_link_contact_action",
    ]

    for table_name in tables_with_created_only:
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )

    # Drop both FK constraints
    tables_with_both_fks = [
        "quote_status",
        "quote_link_status",
        "pricebook_item",
        "quote",
        "quote_line",
        "quote_public_link",
        "quote_message",
    ]

    for table_name in tables_with_both_fks:
        op.drop_constraint(
            f"fk_{table_name}_updated_by", table_name, type_="foreignkey"
        )
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )
