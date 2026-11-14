"""phase_6_0_1_task_8_fk_audit_supplier_catalog

Revision ID: 58bb3299550a
Revises: d50835eb4ab1
Create Date: 2026-04-13 23:17:05.956386+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58bb3299550a"
down_revision: str | None = "d50835eb4ab1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add FK constraints for tables with both created_by and updated_by
    for table_name in [
        "supplier_lifecycle_status",
        "supplier",
        "supplier_item_category",
        "supplier_item_uom",
        "supplier_item",
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
    for table_name in [
        "supplier_item_price",
        "pricing_cache",
        "tax_rate_version",
        "discount_version",
    ]:
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
    for table_name in [
        "supplier_item_price",
        "pricing_cache",
        "tax_rate_version",
        "discount_version",
    ]:
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )

    for table_name in [
        "supplier_lifecycle_status",
        "supplier",
        "supplier_item_category",
        "supplier_item_uom",
        "supplier_item",
    ]:
        op.drop_constraint(
            f"fk_{table_name}_updated_by", table_name, type_="foreignkey"
        )
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )
