"""task_1b1_financial_fk_hard_delete_lockdown

Revision ID: 79d53b7fcffa
Revises: b2c3d4e5f6a7
Create Date: 2026-04-20 20:48:06.000000

Task 1-B-1 — Financial FK Hard-Delete Lockdown
Converts 42 structural financial FKs from NO ACTION / CASCADE to ON DELETE RESTRICT
across the full chain: tenant → customer → site → quote → invoice → payment → job.

Tables covered:
  CRM:         customer, site, contact, psp_customer
  Quoting:     quote (site_id), quote_public_link, quote_acceptance,
               quote_public_link_contact_action
  Jobs:        job, job_notes, job_attachment, job_assignment,
               job_time_entry, job_expense
  Change Ord:  change_order, change_order_line, change_order_attachment,
               change_order_line_tax_component
  Billing:     payment, psp_transaction_log,
               invoice (site_id, job_id, quote_id)
  Catalog:     pricing_cache (CASCADE → RESTRICT)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "79d53b7fcffa"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # customer                                                             #
    # ------------------------------------------------------------------ #
    op.drop_constraint("customer_tenant_id_fkey", "customer", type_="foreignkey")
    op.create_foreign_key(
        "customer_tenant_id_fkey",
        "customer",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # site                                                                 #
    # ------------------------------------------------------------------ #
    op.drop_constraint("site_tenant_id_fkey", "site", type_="foreignkey")
    op.create_foreign_key(
        "site_tenant_id_fkey",
        "site",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("site_customer_id_fkey", "site", type_="foreignkey")
    op.create_foreign_key(
        "site_customer_id_fkey",
        "site",
        "customer",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # contact                                                              #
    # ------------------------------------------------------------------ #
    op.drop_constraint("fk_contact_tenant_id", "contact", type_="foreignkey")
    op.create_foreign_key(
        "fk_contact_tenant_id",
        "contact",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("contact_customer_id_fkey", "contact", type_="foreignkey")
    op.create_foreign_key(
        "contact_customer_id_fkey",
        "contact",
        "customer",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # psp_customer                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "psp_customer_tenant_id_fkey", "psp_customer", type_="foreignkey"
    )
    op.create_foreign_key(
        "psp_customer_tenant_id_fkey",
        "psp_customer",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "psp_customer_customer_id_fkey", "psp_customer", type_="foreignkey"
    )
    op.create_foreign_key(
        "psp_customer_customer_id_fkey",
        "psp_customer",
        "customer",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote — site_id (tenant_id and customer_id already RESTRICT)       #
    # ------------------------------------------------------------------ #
    op.drop_constraint("quote_site_id_fkey", "quote", type_="foreignkey")
    op.create_foreign_key(
        "quote_site_id_fkey",
        "quote",
        "site",
        ["site_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_public_link                                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_public_link_quote_id_fkey", "quote_public_link", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_public_link_quote_id_fkey",
        "quote_public_link",
        "quote",
        ["quote_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_acceptance                                                     #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_acceptance_quote_version_id_fkey", "quote_acceptance", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_acceptance_quote_version_id_fkey",
        "quote_acceptance",
        "quote_version",
        ["quote_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "fk_quote_acceptance_tenant_id", "quote_acceptance", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_quote_acceptance_tenant_id",
        "quote_acceptance",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # quote_public_link_contact_action                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_public_link_contact_action_quote_id_fkey",
        "quote_public_link_contact_action",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "quote_public_link_contact_action_quote_id_fkey",
        "quote_public_link_contact_action",
        "quote",
        ["quote_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "quote_public_link_contact_action_quote_version_id_fkey",
        "quote_public_link_contact_action",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "quote_public_link_contact_action_quote_version_id_fkey",
        "quote_public_link_contact_action",
        "quote_version",
        ["quote_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # invoice — site_id, job_id, quote_id                                 #
    # (tenant_id and customer_id already RESTRICT from Phase 9.0 Batch 1)#
    # ------------------------------------------------------------------ #
    op.drop_constraint("invoice_site_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_site_id_fkey",
        "invoice",
        "site",
        ["site_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("invoice_job_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_job_id_fkey",
        "invoice",
        "job",
        ["job_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("invoice_quote_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_quote_id_fkey",
        "invoice",
        "quote",
        ["quote_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # payment                                                              #
    # ------------------------------------------------------------------ #
    op.drop_constraint("payment_tenant_id_fkey", "payment", type_="foreignkey")
    op.create_foreign_key(
        "payment_tenant_id_fkey",
        "payment",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("payment_invoice_id_fkey", "payment", type_="foreignkey")
    op.create_foreign_key(
        "payment_invoice_id_fkey",
        "payment",
        "invoice",
        ["invoice_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # psp_transaction_log                                                  #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "psp_transaction_log_tenant_id_fkey", "psp_transaction_log", type_="foreignkey"
    )
    op.create_foreign_key(
        "psp_transaction_log_tenant_id_fkey",
        "psp_transaction_log",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "psp_transaction_log_payment_id_fkey", "psp_transaction_log", type_="foreignkey"
    )
    op.create_foreign_key(
        "psp_transaction_log_payment_id_fkey",
        "psp_transaction_log",
        "payment",
        ["payment_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # job                                                                  #
    # ------------------------------------------------------------------ #
    op.drop_constraint("job_tenant_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_tenant_id_fkey",
        "job",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("job_customer_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_customer_id_fkey",
        "job",
        "customer",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("job_site_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_site_id_fkey",
        "job",
        "site",
        ["site_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("job_quote_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_quote_id_fkey",
        "job",
        "quote",
        ["quote_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("job_quote_version_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_quote_version_id_fkey",
        "job",
        "quote_version",
        ["quote_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # job_notes                                                            #
    # ------------------------------------------------------------------ #
    op.drop_constraint("fk_job_notes_tenant_id", "job_notes", type_="foreignkey")
    op.create_foreign_key(
        "fk_job_notes_tenant_id",
        "job_notes",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("job_notes_job_id_fkey", "job_notes", type_="foreignkey")
    op.create_foreign_key(
        "job_notes_job_id_fkey",
        "job_notes",
        "job",
        ["job_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # job_attachment                                                       #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "job_attachment_tenant_id_fkey", "job_attachment", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_attachment_tenant_id_fkey",
        "job_attachment",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "job_attachment_job_id_fkey", "job_attachment", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_attachment_job_id_fkey",
        "job_attachment",
        "job",
        ["job_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # job_assignment                                                       #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "job_assignment_tenant_id_fkey", "job_assignment", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_assignment_tenant_id_fkey",
        "job_assignment",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "job_assignment_job_id_fkey", "job_assignment", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_assignment_job_id_fkey",
        "job_assignment",
        "job",
        ["job_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # job_time_entry                                                       #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_job_time_entry_tenant_id", "job_time_entry", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_job_time_entry_tenant_id",
        "job_time_entry",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "job_time_entry_job_id_fkey", "job_time_entry", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_time_entry_job_id_fkey",
        "job_time_entry",
        "job",
        ["job_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # job_expense                                                          #
    # ------------------------------------------------------------------ #
    op.drop_constraint("job_expense_tenant_id_fkey", "job_expense", type_="foreignkey")
    op.create_foreign_key(
        "job_expense_tenant_id_fkey",
        "job_expense",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("job_expense_job_id_fkey", "job_expense", type_="foreignkey")
    op.create_foreign_key(
        "job_expense_job_id_fkey",
        "job_expense",
        "job",
        ["job_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # change_order                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint("fk_change_order_tenant_id", "change_order", type_="foreignkey")
    op.create_foreign_key(
        "fk_change_order_tenant_id",
        "change_order",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("change_order_job_id_fkey", "change_order", type_="foreignkey")
    op.create_foreign_key(
        "change_order_job_id_fkey",
        "change_order",
        "job",
        ["job_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # change_order_line                                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_change_order_line_tenant_id", "change_order_line", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_change_order_line_tenant_id",
        "change_order_line",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "change_order_line_change_order_id_fkey",
        "change_order_line",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "change_order_line_change_order_id_fkey",
        "change_order_line",
        "change_order",
        ["change_order_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # change_order_attachment                                              #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_change_order_attachment_tenant_id",
        "change_order_attachment",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_change_order_attachment_tenant_id",
        "change_order_attachment",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "change_order_attachment_change_order_id_fkey",
        "change_order_attachment",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "change_order_attachment_change_order_id_fkey",
        "change_order_attachment",
        "change_order",
        ["change_order_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # change_order_line_tax_component                                      #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_change_order_line_tax_component_tenant_id",
        "change_order_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_change_order_line_tax_component_tenant_id",
        "change_order_line_tax_component",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ------------------------------------------------------------------ #
    # pricing_cache — CASCADE → RESTRICT                                  #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "pricing_cache_tenant_id_fkey", "pricing_cache", type_="foreignkey"
    )
    op.create_foreign_key(
        "pricing_cache_tenant_id_fkey",
        "pricing_cache",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # ------------------------------------------------------------------ #
    # pricing_cache — RESTRICT → CASCADE (restore original)              #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "pricing_cache_tenant_id_fkey", "pricing_cache", type_="foreignkey"
    )
    op.create_foreign_key(
        "pricing_cache_tenant_id_fkey",
        "pricing_cache",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ------------------------------------------------------------------ #
    # change_order_line_tax_component                                      #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_change_order_line_tax_component_tenant_id",
        "change_order_line_tax_component",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_change_order_line_tax_component_tenant_id",
        "change_order_line_tax_component",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # change_order_attachment                                              #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "change_order_attachment_change_order_id_fkey",
        "change_order_attachment",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "change_order_attachment_change_order_id_fkey",
        "change_order_attachment",
        "change_order",
        ["change_order_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_change_order_attachment_tenant_id",
        "change_order_attachment",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_change_order_attachment_tenant_id",
        "change_order_attachment",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # change_order_line                                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "change_order_line_change_order_id_fkey",
        "change_order_line",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "change_order_line_change_order_id_fkey",
        "change_order_line",
        "change_order",
        ["change_order_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_change_order_line_tenant_id", "change_order_line", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_change_order_line_tenant_id",
        "change_order_line",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # change_order                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint("change_order_job_id_fkey", "change_order", type_="foreignkey")
    op.create_foreign_key(
        "change_order_job_id_fkey",
        "change_order",
        "job",
        ["job_id"],
        ["id"],
    )
    op.drop_constraint("fk_change_order_tenant_id", "change_order", type_="foreignkey")
    op.create_foreign_key(
        "fk_change_order_tenant_id",
        "change_order",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # job_expense                                                          #
    # ------------------------------------------------------------------ #
    op.drop_constraint("job_expense_job_id_fkey", "job_expense", type_="foreignkey")
    op.create_foreign_key(
        "job_expense_job_id_fkey",
        "job_expense",
        "job",
        ["job_id"],
        ["id"],
    )
    op.drop_constraint("job_expense_tenant_id_fkey", "job_expense", type_="foreignkey")
    op.create_foreign_key(
        "job_expense_tenant_id_fkey",
        "job_expense",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # job_time_entry                                                       #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "job_time_entry_job_id_fkey", "job_time_entry", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_time_entry_job_id_fkey",
        "job_time_entry",
        "job",
        ["job_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_job_time_entry_tenant_id", "job_time_entry", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_job_time_entry_tenant_id",
        "job_time_entry",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # job_assignment                                                       #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "job_assignment_job_id_fkey", "job_assignment", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_assignment_job_id_fkey",
        "job_assignment",
        "job",
        ["job_id"],
        ["id"],
    )
    op.drop_constraint(
        "job_assignment_tenant_id_fkey", "job_assignment", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_assignment_tenant_id_fkey",
        "job_assignment",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # job_attachment                                                       #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "job_attachment_job_id_fkey", "job_attachment", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_attachment_job_id_fkey",
        "job_attachment",
        "job",
        ["job_id"],
        ["id"],
    )
    op.drop_constraint(
        "job_attachment_tenant_id_fkey", "job_attachment", type_="foreignkey"
    )
    op.create_foreign_key(
        "job_attachment_tenant_id_fkey",
        "job_attachment",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # job_notes                                                            #
    # ------------------------------------------------------------------ #
    op.drop_constraint("job_notes_job_id_fkey", "job_notes", type_="foreignkey")
    op.create_foreign_key(
        "job_notes_job_id_fkey",
        "job_notes",
        "job",
        ["job_id"],
        ["id"],
    )
    op.drop_constraint("fk_job_notes_tenant_id", "job_notes", type_="foreignkey")
    op.create_foreign_key(
        "fk_job_notes_tenant_id",
        "job_notes",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # job                                                                  #
    # ------------------------------------------------------------------ #
    op.drop_constraint("job_quote_version_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_quote_version_id_fkey",
        "job",
        "quote_version",
        ["quote_version_id"],
        ["id"],
    )
    op.drop_constraint("job_quote_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_quote_id_fkey",
        "job",
        "quote",
        ["quote_id"],
        ["id"],
    )
    op.drop_constraint("job_site_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_site_id_fkey",
        "job",
        "site",
        ["site_id"],
        ["id"],
    )
    op.drop_constraint("job_customer_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_customer_id_fkey",
        "job",
        "customer",
        ["customer_id"],
        ["id"],
    )
    op.drop_constraint("job_tenant_id_fkey", "job", type_="foreignkey")
    op.create_foreign_key(
        "job_tenant_id_fkey",
        "job",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # psp_transaction_log                                                  #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "psp_transaction_log_payment_id_fkey", "psp_transaction_log", type_="foreignkey"
    )
    op.create_foreign_key(
        "psp_transaction_log_payment_id_fkey",
        "psp_transaction_log",
        "payment",
        ["payment_id"],
        ["id"],
    )
    op.drop_constraint(
        "psp_transaction_log_tenant_id_fkey", "psp_transaction_log", type_="foreignkey"
    )
    op.create_foreign_key(
        "psp_transaction_log_tenant_id_fkey",
        "psp_transaction_log",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # payment                                                              #
    # ------------------------------------------------------------------ #
    op.drop_constraint("payment_invoice_id_fkey", "payment", type_="foreignkey")
    op.create_foreign_key(
        "payment_invoice_id_fkey",
        "payment",
        "invoice",
        ["invoice_id"],
        ["id"],
    )
    op.drop_constraint("payment_tenant_id_fkey", "payment", type_="foreignkey")
    op.create_foreign_key(
        "payment_tenant_id_fkey",
        "payment",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # invoice                                                              #
    # ------------------------------------------------------------------ #
    op.drop_constraint("invoice_quote_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_quote_id_fkey",
        "invoice",
        "quote",
        ["quote_id"],
        ["id"],
    )
    op.drop_constraint("invoice_job_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_job_id_fkey",
        "invoice",
        "job",
        ["job_id"],
        ["id"],
    )
    op.drop_constraint("invoice_site_id_fkey", "invoice", type_="foreignkey")
    op.create_foreign_key(
        "invoice_site_id_fkey",
        "invoice",
        "site",
        ["site_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote_public_link_contact_action                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_public_link_contact_action_quote_version_id_fkey",
        "quote_public_link_contact_action",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "quote_public_link_contact_action_quote_version_id_fkey",
        "quote_public_link_contact_action",
        "quote_version",
        ["quote_version_id"],
        ["id"],
    )
    op.drop_constraint(
        "quote_public_link_contact_action_quote_id_fkey",
        "quote_public_link_contact_action",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "quote_public_link_contact_action_quote_id_fkey",
        "quote_public_link_contact_action",
        "quote",
        ["quote_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote_acceptance                                                     #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "fk_quote_acceptance_tenant_id", "quote_acceptance", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_quote_acceptance_tenant_id",
        "quote_acceptance",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
    op.drop_constraint(
        "quote_acceptance_quote_version_id_fkey", "quote_acceptance", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_acceptance_quote_version_id_fkey",
        "quote_acceptance",
        "quote_version",
        ["quote_version_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote_public_link                                                    #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "quote_public_link_quote_id_fkey", "quote_public_link", type_="foreignkey"
    )
    op.create_foreign_key(
        "quote_public_link_quote_id_fkey",
        "quote_public_link",
        "quote",
        ["quote_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # quote                                                                #
    # ------------------------------------------------------------------ #
    op.drop_constraint("quote_site_id_fkey", "quote", type_="foreignkey")
    op.create_foreign_key(
        "quote_site_id_fkey",
        "quote",
        "site",
        ["site_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # psp_customer                                                         #
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "psp_customer_customer_id_fkey", "psp_customer", type_="foreignkey"
    )
    op.create_foreign_key(
        "psp_customer_customer_id_fkey",
        "psp_customer",
        "customer",
        ["customer_id"],
        ["id"],
    )
    op.drop_constraint(
        "psp_customer_tenant_id_fkey", "psp_customer", type_="foreignkey"
    )
    op.create_foreign_key(
        "psp_customer_tenant_id_fkey",
        "psp_customer",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # contact                                                              #
    # ------------------------------------------------------------------ #
    op.drop_constraint("contact_customer_id_fkey", "contact", type_="foreignkey")
    op.create_foreign_key(
        "contact_customer_id_fkey",
        "contact",
        "customer",
        ["customer_id"],
        ["id"],
    )
    op.drop_constraint("fk_contact_tenant_id", "contact", type_="foreignkey")
    op.create_foreign_key(
        "fk_contact_tenant_id",
        "contact",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # site                                                                 #
    # ------------------------------------------------------------------ #
    op.drop_constraint("site_customer_id_fkey", "site", type_="foreignkey")
    op.create_foreign_key(
        "site_customer_id_fkey",
        "site",
        "customer",
        ["customer_id"],
        ["id"],
    )
    op.drop_constraint("site_tenant_id_fkey", "site", type_="foreignkey")
    op.create_foreign_key(
        "site_tenant_id_fkey",
        "site",
        "tenant",
        ["tenant_id"],
        ["id"],
    )

    # ------------------------------------------------------------------ #
    # customer                                                             #
    # ------------------------------------------------------------------ #
    op.drop_constraint("customer_tenant_id_fkey", "customer", type_="foreignkey")
    op.create_foreign_key(
        "customer_tenant_id_fkey",
        "customer",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
