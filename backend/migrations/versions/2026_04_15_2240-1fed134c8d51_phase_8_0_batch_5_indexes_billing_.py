"""phase_8_0_batch_5_indexes_billing_subscriptions

Revision ID: 1fed134c8d51
Revises: 33986b177b26
Create Date: 2026-04-15 22:40:25.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1fed134c8d51"
down_revision: str | None = "33986b177b26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- invoice ---
    op.create_index("ix_invoice_currency", "invoice", ["currency"])

    # --- invoice_line ---
    op.create_index(
        "ix_invoice_line_qco_line_type_id", "invoice_line", ["qco_line_type_id"]
    )
    op.create_index(
        "ix_invoice_line_taxability_code", "invoice_line", ["taxability_code"]
    )
    op.create_index(
        "ix_invoice_line_pricebook_item_id", "invoice_line", ["pricebook_item_id"]
    )

    # --- payment ---
    op.create_index("ix_payment_status_id", "payment", ["status_id"])
    op.create_index("ix_payment_payment_method_id", "payment", ["payment_method_id"])
    op.create_index(
        "ix_payment_connector_config_id", "payment", ["connector_config_id"]
    )

    # --- payment_method ---
    op.create_index(
        "ix_payment_method_payment_type_id", "payment_method", ["payment_type_id"]
    )
    op.create_index(
        "ix_payment_method_billing_address_id", "payment_method", ["billing_address_id"]
    )

    # --- psp_customer ---
    op.create_index("ix_psp_customer_tenant_id", "psp_customer", ["tenant_id"])

    # --- psp_transaction_log ---
    op.create_index(
        "ix_psp_transaction_log_app_service_id",
        "psp_transaction_log",
        ["app_service_id"],
    )

    # --- subscription ---
    op.create_index(
        "ix_subscription_product_plan_code", "subscription", ["product_plan_code"]
    )
    op.create_index("ix_subscription_status_id", "subscription", ["status_id"])

    # --- subscription_usage ---
    op.create_index(
        "ix_subscription_usage_product_feature_code",
        "subscription_usage",
        ["product_feature_code"],
    )

    # --- usage_ledger ---
    op.create_index(
        "ix_usage_ledger_product_feature_code", "usage_ledger", ["product_feature_code"]
    )

    # --- product_plan_product_feature_version ---
    op.create_index(
        "ix_product_plan_product_feature_version_product_feature_code",
        "product_plan_product_feature_version",
        ["product_feature_code"],
    )

    # --- tenant_product_feature_override ---
    op.create_index(
        "ix_tenant_product_feature_override_product_feature_code",
        "tenant_product_feature_override",
        ["product_feature_code"],
    )

    # --- discount_version ---
    op.create_index("ix_discount_version_tenant_id", "discount_version", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_invoice_currency", table_name="invoice")
    op.drop_index("ix_invoice_line_qco_line_type_id", table_name="invoice_line")
    op.drop_index("ix_invoice_line_taxability_code", table_name="invoice_line")
    op.drop_index("ix_invoice_line_pricebook_item_id", table_name="invoice_line")
    op.drop_index("ix_payment_status_id", table_name="payment")
    op.drop_index("ix_payment_payment_method_id", table_name="payment")
    op.drop_index("ix_payment_connector_config_id", table_name="payment")
    op.drop_index("ix_payment_method_payment_type_id", table_name="payment_method")
    op.drop_index("ix_payment_method_billing_address_id", table_name="payment_method")
    op.drop_index("ix_psp_customer_tenant_id", table_name="psp_customer")
    op.drop_index(
        "ix_psp_transaction_log_app_service_id", table_name="psp_transaction_log"
    )
    op.drop_index("ix_subscription_product_plan_code", table_name="subscription")
    op.drop_index("ix_subscription_status_id", table_name="subscription")
    op.drop_index(
        "ix_subscription_usage_product_feature_code", table_name="subscription_usage"
    )
    op.drop_index("ix_usage_ledger_product_feature_code", table_name="usage_ledger")
    op.drop_index(
        "ix_product_plan_product_feature_version_product_feature_code",
        table_name="product_plan_product_feature_version",
    )
    op.drop_index(
        "ix_tenant_product_feature_override_product_feature_code",
        table_name="tenant_product_feature_override",
    )
    op.drop_index("ix_discount_version_tenant_id", table_name="discount_version")
