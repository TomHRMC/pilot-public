"""
Test Suite: Task 1-B-1 — Financial FK Hard-Delete Lockdown
==========================================================
Verifies that all structural financial FKs across the full chain
  tenant → customer → site → quote → invoice → payment → job
are configured with ON DELETE RESTRICT in the live database.

These tests query pg_catalog directly so they catch constraint state
regardless of what the ORM layer declares.
"""

import pytest
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def restrict_fks(db_engine):
    """
    Query pg_catalog for all FK constraints.
    Returns a dict of {(child_table, constraint_name): delete_rule}.
    Uses db_engine (session-scoped) directly to avoid scope mismatch with
    the function-scoped db_session fixture.
    """
    with db_engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    conrelid::regclass::text AS child_table,
                    con.conname AS constraint_name,
                    confrelid::regclass::text AS parent_table,
                    a.attname AS fk_column,
                    CASE con.confdeltype
                        WHEN 'r' THEN 'RESTRICT'
                        WHEN 'a' THEN 'NO ACTION'
                        WHEN 'c' THEN 'CASCADE'
                        ELSE con.confdeltype::text
                    END AS delete_rule
                FROM pg_constraint con
                JOIN pg_attribute a
                    ON a.attrelid = con.conrelid AND a.attnum = ANY(con.conkey)
                WHERE con.contype = 'f'
                  AND con.connamespace = 'public'::regnamespace
                ORDER BY child_table, constraint_name
            """)
        )
        rows = result.fetchall()
    return {(r.child_table, r.constraint_name): r.delete_rule for r in rows}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def assert_restrict(restrict_fks, child_table: str, constraint_name: str) -> None:
    """Assert a specific FK constraint has delete_rule = RESTRICT."""
    key = (child_table, constraint_name)
    assert key in restrict_fks, (
        f"FK constraint '{constraint_name}' not found on table '{child_table}'. "
        f"Constraint may have been renamed or dropped."
    )
    assert restrict_fks[key] == "RESTRICT", (
        f"Expected ON DELETE RESTRICT for '{constraint_name}' on '{child_table}', "
        f"but got '{restrict_fks[key]}'. Migration 79d53b7fcffa may not have been applied."
    )


# ---------------------------------------------------------------------------
# Tests: CRM chain (tenant → customer → site → contact)
# ---------------------------------------------------------------------------


class TestCrmChainFkRestrict:
    """Verify ON DELETE RESTRICT for the CRM entity chain."""

    def test_customer_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "customer", "customer_tenant_id_fkey")

    def test_site_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "site", "site_tenant_id_fkey")

    def test_site_customer_id(self, restrict_fks):
        assert_restrict(restrict_fks, "site", "site_customer_id_fkey")

    def test_contact_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "contact", "fk_contact_tenant_id")

    def test_contact_customer_id(self, restrict_fks):
        assert_restrict(restrict_fks, "contact", "contact_customer_id_fkey")

    def test_psp_customer_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "psp_customer", "psp_customer_tenant_id_fkey")

    def test_psp_customer_customer_id(self, restrict_fks):
        assert_restrict(restrict_fks, "psp_customer", "psp_customer_customer_id_fkey")


# ---------------------------------------------------------------------------
# Tests: Quote chain
# ---------------------------------------------------------------------------


class TestQuoteChainFkRestrict:
    """Verify ON DELETE RESTRICT for the quote entity chain."""

    def test_quote_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote", "quote_tenant_id_fkey")

    def test_quote_customer_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote", "quote_customer_id_fkey")

    def test_quote_site_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote", "quote_site_id_fkey")

    def test_quote_version_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote_version", "fk_quote_version_tenant_id")

    def test_quote_version_quote_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote_version", "quote_version_quote_id_fkey")

    def test_quote_line_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote_line", "fk_quote_line_tenant_id")

    def test_quote_line_quote_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote_line", "quote_line_quote_id_fkey")

    def test_quote_line_tax_component_tenant_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "quote_line_tax_component",
            "fk_quote_line_tax_component_tenant_id",
        )

    def test_quote_line_tax_component_quote_line_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "quote_line_tax_component",
            "quote_line_tax_component_quote_line_id_fkey",
        )

    def test_quote_message_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote_message", "quote_message_tenant_id_fkey")

    def test_quote_message_quote_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote_message", "quote_message_quote_id_fkey")

    def test_quote_public_link_tenant_id(self, restrict_fks):
        assert_restrict(
            restrict_fks, "quote_public_link", "fk_quote_public_link_tenant_id"
        )

    def test_quote_public_link_quote_id(self, restrict_fks):
        assert_restrict(
            restrict_fks, "quote_public_link", "quote_public_link_quote_id_fkey"
        )

    def test_quote_acceptance_tenant_id(self, restrict_fks):
        assert_restrict(
            restrict_fks, "quote_acceptance", "fk_quote_acceptance_tenant_id"
        )

    def test_quote_acceptance_quote_version_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "quote_acceptance",
            "quote_acceptance_quote_version_id_fkey",
        )

    def test_quote_public_link_contact_action_tenant_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "quote_public_link_contact_action",
            "fk_quote_public_link_contact_action_tenant_id",
        )

    def test_quote_public_link_contact_action_quote_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "quote_public_link_contact_action",
            "quote_public_link_contact_action_quote_id_fkey",
        )

    def test_quote_public_link_contact_action_quote_version_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "quote_public_link_contact_action",
            "quote_public_link_contact_action_quote_version_id_fkey",
        )


# ---------------------------------------------------------------------------
# Tests: Job chain
# ---------------------------------------------------------------------------


class TestJobChainFkRestrict:
    """Verify ON DELETE RESTRICT for the job entity chain."""

    def test_job_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job", "job_tenant_id_fkey")

    def test_job_customer_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job", "job_customer_id_fkey")

    def test_job_site_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job", "job_site_id_fkey")

    def test_job_quote_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job", "job_quote_id_fkey")

    def test_job_quote_version_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job", "job_quote_version_id_fkey")

    def test_job_notes_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job_notes", "fk_job_notes_tenant_id")

    def test_job_notes_job_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job_notes", "job_notes_job_id_fkey")

    def test_job_attachment_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job_attachment", "job_attachment_tenant_id_fkey")

    def test_job_attachment_job_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job_attachment", "job_attachment_job_id_fkey")

    def test_job_time_entry_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job_time_entry", "fk_job_time_entry_tenant_id")

    def test_job_time_entry_job_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job_time_entry", "job_time_entry_job_id_fkey")

    def test_job_expense_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job_expense", "job_expense_tenant_id_fkey")

    def test_job_expense_job_id(self, restrict_fks):
        assert_restrict(restrict_fks, "job_expense", "job_expense_job_id_fkey")


# ---------------------------------------------------------------------------
# Tests: Change Order chain
# ---------------------------------------------------------------------------


class TestChangeOrderChainFkRestrict:
    """Verify ON DELETE RESTRICT for the change order entity chain."""

    def test_change_order_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "change_order", "fk_change_order_tenant_id")

    def test_change_order_job_id(self, restrict_fks):
        assert_restrict(restrict_fks, "change_order", "change_order_job_id_fkey")

    def test_change_order_line_tenant_id(self, restrict_fks):
        assert_restrict(
            restrict_fks, "change_order_line", "fk_change_order_line_tenant_id"
        )

    def test_change_order_line_change_order_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "change_order_line",
            "change_order_line_change_order_id_fkey",
        )

    def test_change_order_attachment_tenant_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "change_order_attachment",
            "fk_change_order_attachment_tenant_id",
        )

    def test_change_order_attachment_change_order_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "change_order_attachment",
            "change_order_attachment_change_order_id_fkey",
        )

    def test_change_order_line_tax_component_tenant_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "change_order_line_tax_component",
            "fk_change_order_line_tax_component_tenant_id",
        )


# ---------------------------------------------------------------------------
# Tests: Invoice & Payment chain
# ---------------------------------------------------------------------------


class TestInvoicePaymentChainFkRestrict:
    """Verify ON DELETE RESTRICT for the invoice and payment entity chain."""

    def test_invoice_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "invoice", "invoice_tenant_id_fkey")

    def test_invoice_customer_id(self, restrict_fks):
        assert_restrict(restrict_fks, "invoice", "invoice_customer_id_fkey")

    def test_invoice_site_id(self, restrict_fks):
        assert_restrict(restrict_fks, "invoice", "invoice_site_id_fkey")

    def test_invoice_job_id(self, restrict_fks):
        assert_restrict(restrict_fks, "invoice", "invoice_job_id_fkey")

    def test_invoice_quote_id(self, restrict_fks):
        assert_restrict(restrict_fks, "invoice", "invoice_quote_id_fkey")

    def test_invoice_line_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "invoice_line", "fk_invoice_line_tenant_id")

    def test_invoice_line_invoice_id(self, restrict_fks):
        assert_restrict(restrict_fks, "invoice_line", "invoice_line_invoice_id_fkey")

    def test_invoice_line_tax_component_tenant_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "invoice_line_tax_component",
            "fk_invoice_line_tax_component_tenant_id",
        )

    def test_invoice_line_tax_component_invoice_line_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "invoice_line_tax_component",
            "invoice_line_tax_component_invoice_line_id_fkey",
        )

    def test_payment_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "payment", "payment_tenant_id_fkey")

    def test_payment_invoice_id(self, restrict_fks):
        assert_restrict(restrict_fks, "payment", "payment_invoice_id_fkey")

    def test_psp_transaction_log_tenant_id(self, restrict_fks):
        assert_restrict(
            restrict_fks, "psp_transaction_log", "psp_transaction_log_tenant_id_fkey"
        )

    def test_psp_transaction_log_payment_id(self, restrict_fks):
        assert_restrict(
            restrict_fks,
            "psp_transaction_log",
            "psp_transaction_log_payment_id_fkey",
        )


# ---------------------------------------------------------------------------
# Tests: Subscription / Catalog / Misc
# ---------------------------------------------------------------------------


class TestSubscriptionCatalogFkRestrict:
    """Verify ON DELETE RESTRICT for subscription and catalog financial FKs."""

    def test_subscription_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "subscription", "subscription_tenant_id_fkey")

    def test_usage_ledger_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "usage_ledger", "usage_ledger_tenant_id_fkey")

    def test_usage_ledger_subscription_id(self, restrict_fks):
        assert_restrict(
            restrict_fks, "usage_ledger", "usage_ledger_subscription_id_fkey"
        )

    def test_pricing_cache_tenant_id(self, restrict_fks):
        """pricing_cache was previously CASCADE — must now be RESTRICT."""
        assert_restrict(restrict_fks, "pricing_cache", "pricing_cache_tenant_id_fkey")

    def test_payment_status_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "payment_status", "payment_status_tenant_id_fkey")

    def test_quote_status_tenant_id(self, restrict_fks):
        assert_restrict(restrict_fks, "quote_status", "quote_status_tenant_id_fkey")
