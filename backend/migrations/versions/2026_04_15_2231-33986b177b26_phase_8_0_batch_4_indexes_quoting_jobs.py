"""phase_8_0_batch_4_indexes_quoting_jobs

Revision ID: 33986b177b26
Revises: cc75f4532955
Create Date: 2026-04-15 22:31:33.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "33986b177b26"
down_revision: str | None = "cc75f4532955"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- quote ---
    op.create_index("ix_quote_currency", "quote", ["currency"])

    # --- qco_line_type ---
    op.create_index("ix_qco_line_type_tenant_id", "qco_line_type", ["tenant_id"])

    # --- quote_line ---
    op.create_index(
        "ix_quote_line_qco_line_type_id", "quote_line", ["qco_line_type_id"]
    )
    op.create_index("ix_quote_line_supplier_id", "quote_line", ["supplier_id"])
    op.create_index(
        "ix_quote_line_supplier_item_id", "quote_line", ["supplier_item_id"]
    )
    op.create_index("ix_quote_line_taxability_code", "quote_line", ["taxability_code"])
    op.create_index(
        "ix_quote_line_pricebook_item_id", "quote_line", ["pricebook_item_id"]
    )

    # --- quote_public_link ---
    op.create_index(
        "ix_quote_public_link_contact_id", "quote_public_link", ["contact_id"]
    )
    op.create_index("ix_quote_public_link_quote_id", "quote_public_link", ["quote_id"])
    op.create_index(
        "ix_quote_public_link_status_id", "quote_public_link", ["status_id"]
    )

    # --- quote_message ---
    op.create_index("ix_quote_message_quote_id", "quote_message", ["quote_id"])
    op.create_index("ix_quote_message_contact_id", "quote_message", ["contact_id"])

    # --- job_attachment ---
    op.create_index("ix_job_attachment_tenant_id", "job_attachment", ["tenant_id"])

    # --- job_expense_category ---
    op.create_index(
        "ix_job_expense_category_tenant_id", "job_expense_category", ["tenant_id"]
    )

    # --- job_expense ---
    op.create_index(
        "ix_job_expense_job_expense_category_code",
        "job_expense",
        ["job_expense_category_code"],
    )
    op.create_index(
        "ix_job_expense_invoice_line_id", "job_expense", ["invoice_line_id"]
    )

    # --- job_assignment ---
    op.create_index("ix_job_assignment_tenant_id", "job_assignment", ["tenant_id"])

    # --- change_order_line ---
    op.create_index(
        "ix_change_order_line_qco_line_type_id",
        "change_order_line",
        ["qco_line_type_id"],
    )
    op.create_index(
        "ix_change_order_line_supplier_id", "change_order_line", ["supplier_id"]
    )
    op.create_index(
        "ix_change_order_line_supplier_item_id",
        "change_order_line",
        ["supplier_item_id"],
    )
    op.create_index(
        "ix_change_order_line_taxability_code", "change_order_line", ["taxability_code"]
    )
    op.create_index(
        "ix_change_order_line_pricebook_item_id",
        "change_order_line",
        ["pricebook_item_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_quote_currency", table_name="quote")
    op.drop_index("ix_qco_line_type_tenant_id", table_name="qco_line_type")
    op.drop_index("ix_quote_line_qco_line_type_id", table_name="quote_line")
    op.drop_index("ix_quote_line_supplier_id", table_name="quote_line")
    op.drop_index("ix_quote_line_supplier_item_id", table_name="quote_line")
    op.drop_index("ix_quote_line_taxability_code", table_name="quote_line")
    op.drop_index("ix_quote_line_pricebook_item_id", table_name="quote_line")
    op.drop_index("ix_quote_public_link_contact_id", table_name="quote_public_link")
    op.drop_index("ix_quote_public_link_quote_id", table_name="quote_public_link")
    op.drop_index("ix_quote_public_link_status_id", table_name="quote_public_link")
    op.drop_index("ix_quote_message_quote_id", table_name="quote_message")
    op.drop_index("ix_quote_message_contact_id", table_name="quote_message")
    op.drop_index("ix_job_attachment_tenant_id", table_name="job_attachment")
    op.drop_index(
        "ix_job_expense_category_tenant_id", table_name="job_expense_category"
    )
    op.drop_index("ix_job_expense_job_expense_category_code", table_name="job_expense")
    op.drop_index("ix_job_expense_invoice_line_id", table_name="job_expense")
    op.drop_index("ix_job_assignment_tenant_id", table_name="job_assignment")
    op.drop_index(
        "ix_change_order_line_qco_line_type_id", table_name="change_order_line"
    )
    op.drop_index("ix_change_order_line_supplier_id", table_name="change_order_line")
    op.drop_index(
        "ix_change_order_line_supplier_item_id", table_name="change_order_line"
    )
    op.drop_index(
        "ix_change_order_line_taxability_code", table_name="change_order_line"
    )
    op.drop_index(
        "ix_change_order_line_pricebook_item_id", table_name="change_order_line"
    )
