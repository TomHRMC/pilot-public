"""phase_6_0_task_3_composite_indexes

Revision ID: 6d7a8b012415
Revises: cc74125f04dc
Create Date: 2026-04-13 15:51:16.757629+00:00

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "6d7a8b012415"
down_revision: str | None = "cc74125f04dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ========== DESCENDING CREATED_AT INDEXES (4) ==========

    op.create_index(
        "idx_change_order_created_at", "change_order", [text("created_at DESC")]
    )

    op.create_index(
        "idx_qpl_action_created_at",
        "quote_public_link_contact_action",
        [text("created_at DESC")],
    )

    op.create_index(
        "idx_quote_version_created_at", "quote_version", [text("created_at DESC")]
    )

    # ========== COMPOSITE INDEXES (10) ==========

    # Connector run log: Supplier sync history
    op.create_index(
        "idx_connector_run_supplier_started",
        "connector_run_log",
        ["supplier_id", text("started_at DESC")],
    )

    # Connector run log: Failed sync monitoring
    op.create_index(
        "idx_connector_run_supplier_status",
        "connector_run_log",
        ["supplier_id", "status", text("started_at DESC")],
    )

    # Invoice line: Polymorphic source lookup
    op.create_index(
        "idx_invoice_line_source", "invoice_line", ["source_type", "source_id"]
    )

    # Job assignment: User's active jobs
    op.create_index(
        "idx_job_assignment_user_active", "job_assignment", ["user_id", "is_active"]
    )

    # Quote message: Quote conversation thread
    op.create_index(
        "idx_quote_message_tenant_quote_time",
        "quote_message",
        ["tenant_id", "quote_id", text("created_at DESC")],
    )

    # Site: Customer sites list
    op.create_index("idx_site_tenant_customer", "site", ["tenant_id", "customer_id"])

    # Tenant markup version: Markup history by category
    op.create_index(
        "idx_tenant_markup_category",
        "tenant_markup_version",
        ["tenant_id", "job_expense_category_code"],
    )

    # Tenant user notification pref: User notification settings
    op.create_index(
        "idx_tenant_user_notif_pref",
        "tenant_user_notification_pref",
        ["tenant_id", "user_id"],
    )

    # User SSO identity: SSO login lookup
    op.create_index(
        "idx_user_sso_provider_id",
        "user_sso_identity",
        ["sso_provider_code", "provider_user_id"],
    )

    # Usage ledger: Usage billing aggregation
    op.create_index(
        "idx_usage_ledger_tenant_feature",
        "usage_ledger",
        ["tenant_id", "product_feature_code", "is_reported"],
    )


def downgrade() -> None:
    # Drop all indexes in reverse order

    op.drop_index("idx_usage_ledger_tenant_feature", table_name="usage_ledger")
    op.drop_index("idx_user_sso_provider_id", table_name="user_sso_identity")
    op.drop_index(
        "idx_tenant_user_notif_pref", table_name="tenant_user_notification_pref"
    )
    op.drop_index("idx_tenant_markup_category", table_name="tenant_markup_version")
    op.drop_index("idx_site_tenant_customer", table_name="site")
    op.drop_index("idx_quote_message_tenant_quote_time", table_name="quote_message")
    op.drop_index("idx_job_assignment_user_active", table_name="job_assignment")
    op.drop_index("idx_invoice_line_source", table_name="invoice_line")
    op.drop_index("idx_connector_run_supplier_status", table_name="connector_run_log")
    op.drop_index("idx_connector_run_supplier_started", table_name="connector_run_log")

    op.drop_index("idx_quote_version_created_at", table_name="quote_version")
    op.drop_index(
        "idx_qpl_action_created_at", table_name="quote_public_link_contact_action"
    )
    op.drop_index("idx_change_order_created_at", table_name="change_order")
