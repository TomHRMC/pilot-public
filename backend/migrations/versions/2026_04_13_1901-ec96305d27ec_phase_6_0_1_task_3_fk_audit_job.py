"""phase_6_0_1_task_3_fk_audit_job

Phase 6.0.1 Task 3: Foreign Key constraints for Job Management audit columns

This migration adds FK constraints on created_by and updated_by columns
for all Job Management tables, ensuring database-level referential integrity
for audit trails.

Scope:
- 11 tables with BOTH created_by AND updated_by FK constraints
- 1 table with ONLY created_by FK constraint (append-only)
- Total: 23 FK constraints

Reference: dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md - Task 3

Revision ID: ec96305d27ec
Revises: a098b620e104
Create Date: 2026-04-13 19:01:21.071877+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec96305d27ec"
down_revision: str | None = "a098b620e104"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add FK constraints on audit columns for Job Management tables."""

    # Tables with BOTH created_by and updated_by FK constraints
    tables_with_both = [
        "job",
        "job_status",
        "job_assignment",
        "job_notes",
        "job_attachment",
        "job_expense",
        "job_expense_category",
        "job_time_entry",
        "change_order",
        "change_order_line",
        "change_order_attachment",
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

    # Append-only table with ONLY created_by FK constraint
    op.create_foreign_key(
        "fk_change_order_line_tax_component_created_by",
        "change_order_line_tax_component",
        "user",
        ["created_by"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Remove FK constraints on audit columns for Job Management tables."""

    # Drop append-only table FK constraint
    op.drop_constraint(
        "fk_change_order_line_tax_component_created_by",
        "change_order_line_tax_component",
        type_="foreignkey",
    )

    # Drop FK constraints from tables with both created_by and updated_by
    tables_with_both = [
        "change_order_attachment",
        "change_order_line",
        "change_order",
        "job_time_entry",
        "job_expense_category",
        "job_expense",
        "job_attachment",
        "job_notes",
        "job_assignment",
        "job_status",
        "job",
    ]

    for table_name in tables_with_both:
        op.drop_constraint(
            f"fk_{table_name}_updated_by", table_name, type_="foreignkey"
        )
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )
