"""phase_9_0_batch_1_hard_delete_lockdown

Revision ID: 7c973ed46561
Revises: 950d6d100365
Create Date: 2026-04-16 13:42:29.000000

Phase 9.0 Batch 1 — Hard-Delete Lockdown
Converts 23 critical FK constraints on financial and CRM-adjacent tables
from NO ACTION to ON DELETE RESTRICT to prevent accidental data destruction.

Tables covered:
  quote, quote_version, quote_line, quote_line_tax_component, quote_message,
  invoice, invoice_line, invoice_line_tax_component,
  subscription, usage_ledger,
  payment_status, quote_status,
  quote_public_link, quote_public_link_contact_action
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7c973ed46561"
down_revision = "950d6d100365"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # quote                                                                #
    # ------------------------------------------------------------------ #
    op.drop_constraint("quote_tenant_id_fkey", "quote", type_="foreignkey")
    op.create_foreign_key(
        "quote_tenant_id_fkey",
        "quote",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("quote_customer_id_fkey", "quote", type_="foreignkey")
    op.create_foreign_key(
        "quote_customer_id_fkey",
        "quote",
        "customer",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_version                                                        #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_quote_version_tenant_id", "quote_version", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_quote_version_tenant_id",
        "quote_version",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "quote_version_quote_id_fkey", "quote_version", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_version_quote_id_fkey",
        "quote_version",
        "quote",
        ["quote_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_line                                                           #
    # ------------------------------------------------------------------ #
    op.drop_constraint("fk_quote_line_tenant_id", "quote_line", type_="foreignkey")
    op.create_foreign_key(
        "fk_quote_line_tenant_id",
        "quote_line",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("quote_line_quote_id_fkey", "quote_line", type_="foreignkey")
    op.create_foreign_key(
        "quote_line_quote_id_fkey",
        "quote_line",
        "quote",
        ["quote_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_line_tax_component                                             #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_quote_line_tax_component_tenant_id",
        "quote_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_quote_line_tax_component_tenant_id",
        "quote_line_tax_component",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "quote_line_tax_component_quote_line_id_fkey",
        "quote_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "quote_line_tax_component_quote_line_id_fkey",
        "quote_line_tax_component",
        "quote_line",
        ["quote_line_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_message                                                        #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_message_tenant_id_fkey", "quote_message", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_message_tenant_id_fkey",
        "quote_message",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "quote_message_quote_id_fkey", "quote_message", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_message_quote_id_fkey",
        "quote_message",
        "quote",
        ["quote_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # invoice                                                              #
    # ------------------------------------------------------------------ #
    op.drop_constraint("invoice_tenant_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_tenant_id_fkey",
        "invoice",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("invoice_customer_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_customer_id_fkey",
        "invoice",
        "customer",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # invoice_line                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint("fk_invoice_line_tenant_id", "invoice_line", type_="foreignkey")
    op.create_foreign_key(
        "fk_invoice_line_tenant_id",
        "invoice_line",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "invoice_line_invoice_id_fkey", "invoice_line", type_="foreignkey"
    )
    op.create_foreign_key(
        "invoice_line_invoice_id_fkey",
        "invoice_line",
        "invoice",
        ["invoice_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # invoice_line_tax_component                                           #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_invoice_line_tax_component_tenant_id",
        "invoice_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_invoice_line_tax_component_tenant_id",
        "invoice_line_tax_component",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "invoice_line_tax_component_invoice_line_id_fkey",
        "invoice_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "invoice_line_tax_component_invoice_line_id_fkey",
        "invoice_line_tax_component",
        "invoice_line",
        ["invoice_line_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # subscription                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "subscription_tenant_id_fkey", "subscription", type_="foreignkey"
    )
    op.create_foreign_key(
        "subscription_tenant_id_fkey",
        "subscription",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # usage_ledger                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "usage_ledger_tenant_id_fkey", "usage_ledger", type_="foreignkey"
    )
    op.create_foreign_key(
        "usage_ledger_tenant_id_fkey",
        "usage_ledger",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "usage_ledger_subscription_id_fkey", "usage_ledger", type_="foreignkey"
    )
    op.create_foreign_key(
        "usage_ledger_subscription_id_fkey",
        "usage_ledger",
        "subscription",
        ["subscription_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # payment_status (lookup table — tenant scoped)                       #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "payment_status_tenant_id_fkey", "payment_status", type_="foreignkey"
    )
    op.create_foreign_key(
        "payment_status_tenant_id_fkey",
        "payment_status",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_status (lookup table — tenant scoped)                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_status_tenant_id_fkey", "quote_status", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_status_tenant_id_fkey",
        "quote_status",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_public_link                                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_quote_public_link_tenant_id", "quote_public_link", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_quote_public_link_tenant_id",
        "quote_public_link",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_public_link_contact_action                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_quote_public_link_contact_action_tenant_id",
        "quote_public_link_contact_action",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_quote_public_link_contact_action_tenant_id",
        "quote_public_link_contact_action",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # ------------------------------------------------------------------ #
    # quote_public_link_contact_action                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_quote_public_link_contact_action_tenant_id",
        "quote_public_link_contact_action",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_quote_public_link_contact_action_tenant_id",
        "quote_public_link_contact_action",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote_public_link                                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_quote_public_link_tenant_id", "quote_public_link", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_quote_public_link_tenant_id",
        "quote_public_link",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote_status                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_status_tenant_id_fkey", "quote_status", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_status_tenant_id_fkey",
        "quote_status",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # payment_status                                                       #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "payment_status_tenant_id_fkey", "payment_status", type_="foreignkey"
    )
    op.create_foreign_key(
        "payment_status_tenant_id_fkey",
        "payment_status",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # usage_ledger                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "usage_ledger_subscription_id_fkey", "usage_ledger", type_="foreignkey"
    )
    op.create_foreign_key(
        "usage_ledger_subscription_id_fkey",
        "usage_ledger",
        "subscription",
        ["subscription_id"],
        ["id"],
    )
    op.drop_constraint(
        "usage_ledger_tenant_id_fkey", "usage_ledger", type_="foreignkey"
    )
    op.create_foreign_key(
        "usage_ledger_tenant_id_fkey",
        "usage_ledger",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # subscription                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "subscription_tenant_id_fkey", "subscription", type_="foreignkey"
    )
    op.create_foreign_key(
        "subscription_tenant_id_fkey",
        "subscription",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # invoice_line_tax_component                                           #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "invoice_line_tax_component_invoice_line_id_fkey",
        "invoice_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "invoice_line_tax_component_invoice_line_id_fkey",
        "invoice_line_tax_component",
        "invoice_line",
        ["invoice_line_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_invoice_line_tax_component_tenant_id",
        "invoice_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_invoice_line_tax_component_tenant_id",
        "invoice_line_tax_component",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # invoice_line                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "invoice_line_invoice_id_fkey", "invoice_line", type_="foreignkey"
    )
    op.create_foreign_key(
        "invoice_line_invoice_id_fkey",
        "invoice_line",
        "invoice",
        ["invoice_id"],
        ["id"],
    )
    op.drop_constraint("fk_invoice_line_tenant_id", "invoice_line", type_="foreignkey")
    op.create_foreign_key(
        "fk_invoice_line_tenant_id",
        "invoice_line",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # invoice                                                              #
    # ------------------------------------------------------------------ #
    op.drop_constraint("invoice_customer_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_customer_id_fkey",
        "invoice",
        "customer",
        ["customer_id"],
        ["id"],
    )
    op.drop_constraint("invoice_tenant_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_tenant_id_fkey",
        "invoice",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote_message                                                        #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_message_quote_id_fkey", "quote_message", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_message_quote_id_fkey",
        "quote_message",
        "quote",
        ["quote_id"],
        ["id"],
    )
    op.drop_constraint(
        "quote_message_tenant_id_fkey", "quote_message", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_message_tenant_id_fkey",
        "quote_message",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote_line_tax_component                                             #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_line_tax_component_quote_line_id_fkey",
        "quote_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "quote_line_tax_component_quote_line_id_fkey",
        "quote_line_tax_component",
        "quote_line",
        ["quote_line_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_quote_line_tax_component_tenant_id",
        "quote_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_quote_line_tax_component_tenant_id",
        "quote_line_tax_component",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote_line                                                           #
    # ------------------------------------------------------------------ #
    op.drop_constraint("quote_line_quote_id_fkey", "quote_line", type_="foreignkey")
    op.create_foreign_key(
        "quote_line_quote_id_fkey",
        "quote_line",
        "quote",
        ["quote_id"],
        ["id"],
    )
    op.drop_constraint("fk_quote_line_tenant_id", "quote_line", type_="foreignkey")
    op.create_foreign_key(
        "fk_quote_line_tenant_id",
        "quote_line",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote_version                                                        #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_version_quote_id_fkey", "quote_version", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_version_quote_id_fkey",
        "quote_version",
        "quote",
        ["quote_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_quote_version_tenant_id", "quote_version", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_quote_version_tenant_id",
        "quote_version",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote                                                                #
    # ------------------------------------------------------------------ #
    op.drop_constraint("quote_customer_id_fkey", "quote", type_="foreignkey")
    op.create_foreign_key(
        "quote_customer_id_fkey",
        "quote",
        "customer",
        ["customer_id"],
        ["id"],
    )
    op.drop_constraint("quote_tenant_id_fkey", "quote", type_="foreignkey")
    op.create_foreign_key(
        "quote_tenant_id_fkey",
        "quote",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
