"""phase_6_0_1_task_5_fk_audit_billing

Phase 6.0.1 Task 5: Add Foreign Key constraints to audit columns for Billing & Payments tables.

This migration adds FK constraints to created_by and updated_by columns for 18 billing/payment tables:
- 12 tables with BOTH created_by AND updated_by FKs (24 constraints)
- 6 tables with ONLY created_by FK (6 constraints)
- Total: 30 FK constraints

All FKs reference user.id with ON DELETE RESTRICT behavior to preserve audit trail integrity.

Revision ID: 5c579d516fc2
Revises: d25bd8d5f87e
Create Date: 2026-04-13 21:17:38.822223+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c579d516fc2"
down_revision: str | None = "d25bd8d5f87e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Tables with BOTH created_by and updated_by FK constraints (12 tables = 24 FKs)
    tables_with_both = [
        "invoice",
        "invoice_status",
        "payment",
        "payment_status",
        "payment_type",
        "payment_method",
        "psp_customer",
        "subscription",
        "subscription_status",
        "subscription_usage",
        "product_plan",
        "product_feature",
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

    # Append-only tables with ONLY created_by FK constraint (6 tables = 6 FKs)
    tables_with_created_only = [
        "invoice_line",
        "invoice_line_tax_component",
        "psp_transaction_log",
        "usage_ledger",
        "product_plan_version",
        "product_plan_product_feature_version",
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

    # Drop created_by FKs from append-only tables
    tables_with_created_only = [
        "invoice_line",
        "invoice_line_tax_component",
        "psp_transaction_log",
        "usage_ledger",
        "product_plan_version",
        "product_plan_product_feature_version",
    ]

    for table_name in tables_with_created_only:
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )

    # Drop both FKs from standard audit tables
    tables_with_both = [
        "invoice",
        "invoice_status",
        "payment",
        "payment_status",
        "payment_type",
        "payment_method",
        "psp_customer",
        "subscription",
        "subscription_status",
        "subscription_usage",
        "product_plan",
        "product_feature",
    ]

    for table_name in tables_with_both:
        op.drop_constraint(
            f"fk_{table_name}_updated_by", table_name, type_="foreignkey"
        )
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )
