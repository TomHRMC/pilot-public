"""phase_6_0_task_1_constraints_audit_columns

Revision ID: 9c399e4369a1
Revises: 01bf58eed1b3
Create Date: 2026-04-13 13:31:09.119139+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9c399e4369a1"
down_revision: str | None = "01bf58eed1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add audit columns to conversation_session
    op.add_column(
        "conversation_session",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversation_session",
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Multi-tenant unique constraints (14 tables)
    op.create_unique_constraint(
        "uq_customer_lifecycle_status_tenant_code",
        "customer_lifecycle_status",
        ["tenant_id", "code"],
    )
    op.create_unique_constraint(
        "uq_invoice_status_tenant_code", "invoice_status", ["tenant_id", "code"]
    )
    op.create_unique_constraint(
        "uq_job_status_tenant_code", "job_status", ["tenant_id", "code"]
    )
    op.create_unique_constraint(
        "uq_payment_status_tenant_code", "payment_status", ["tenant_id", "code"]
    )
    op.create_unique_constraint(
        "uq_payment_type_tenant_code", "payment_type", ["tenant_id", "code"]
    )
    op.create_unique_constraint(
        "uq_qpl_contact_action_type_tenant_code",
        "qpl_contact_action_type",
        ["tenant_id", "code"],
    )
    op.create_unique_constraint(
        "uq_quote_link_status_tenant_code", "quote_link_status", ["tenant_id", "code"]
    )
    op.create_unique_constraint(
        "uq_quote_status_tenant_code", "quote_status", ["tenant_id", "code"]
    )
    op.create_unique_constraint(
        "uq_site_lifecycle_status_tenant_code",
        "site_lifecycle_status",
        ["tenant_id", "code"],
    )
    op.create_unique_constraint(
        "uq_subscription_status_tenant_code",
        "subscription_status",
        ["tenant_id", "code"],
    )
    op.create_unique_constraint(
        "uq_supplier_item_category_tenant_code",
        "supplier_item_category",
        ["tenant_id", "code"],
    )
    op.create_unique_constraint(
        "uq_supplier_item_uom_tenant_code", "supplier_item_uom", ["tenant_id", "code"]
    )
    op.create_unique_constraint(
        "uq_supplier_lifecycle_status_tenant_code",
        "supplier_lifecycle_status",
        ["tenant_id", "code"],
    )
    op.create_unique_constraint(
        "uq_tenant_user_status_tenant_code", "tenant_user_status", ["tenant_id", "code"]
    )

    # Business logic unique constraints (5 tables)
    op.create_unique_constraint(
        "uq_job_assignment_job_user", "job_assignment", ["job_id", "user_id"]
    )
    op.create_unique_constraint(
        "uq_payment_method_tenant_psp",
        "payment_method",
        ["tenant_id", "psp_provider", "psp_payment_method_id"],
    )
    op.create_unique_constraint(
        "uq_psp_customer_provider_id",
        "psp_customer",
        ["psp_provider", "psp_customer_id"],
    )
    op.create_unique_constraint(
        "uq_user_preference_user_tenant", "user_preference", ["user_id", "tenant_id"]
    )
    op.create_unique_constraint("uq_user_email", "user", ["email"])


def downgrade() -> None:
    # Drop business logic constraints
    op.drop_constraint("uq_user_email", "user", type_="unique")
    op.drop_constraint(
        "uq_user_preference_user_tenant", "user_preference", type_="unique"
    )
    op.drop_constraint("uq_psp_customer_provider_id", "psp_customer", type_="unique")
    op.drop_constraint("uq_payment_method_tenant_psp", "payment_method", type_="unique")
    op.drop_constraint("uq_job_assignment_job_user", "job_assignment", type_="unique")

    # Drop multi-tenant constraints
    op.drop_constraint(
        "uq_tenant_user_status_tenant_code", "tenant_user_status", type_="unique"
    )
    op.drop_constraint(
        "uq_supplier_lifecycle_status_tenant_code",
        "supplier_lifecycle_status",
        type_="unique",
    )
    op.drop_constraint(
        "uq_supplier_item_uom_tenant_code", "supplier_item_uom", type_="unique"
    )
    op.drop_constraint(
        "uq_supplier_item_category_tenant_code",
        "supplier_item_category",
        type_="unique",
    )
    op.drop_constraint(
        "uq_subscription_status_tenant_code", "subscription_status", type_="unique"
    )
    op.drop_constraint(
        "uq_site_lifecycle_status_tenant_code", "site_lifecycle_status", type_="unique"
    )
    op.drop_constraint("uq_quote_status_tenant_code", "quote_status", type_="unique")
    op.drop_constraint(
        "uq_quote_link_status_tenant_code", "quote_link_status", type_="unique"
    )
    op.drop_constraint(
        "uq_qpl_contact_action_type_tenant_code",
        "qpl_contact_action_type",
        type_="unique",
    )
    op.drop_constraint("uq_payment_type_tenant_code", "payment_type", type_="unique")
    op.drop_constraint(
        "uq_payment_status_tenant_code", "payment_status", type_="unique"
    )
    op.drop_constraint("uq_job_status_tenant_code", "job_status", type_="unique")
    op.drop_constraint(
        "uq_invoice_status_tenant_code", "invoice_status", type_="unique"
    )
    op.drop_constraint(
        "uq_customer_lifecycle_status_tenant_code",
        "customer_lifecycle_status",
        type_="unique",
    )

    # Drop audit columns
    op.drop_column("conversation_session", "updated_by")
    op.drop_column("conversation_session", "created_by")
