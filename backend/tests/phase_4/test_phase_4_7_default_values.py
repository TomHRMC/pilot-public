"""
Test Suite: Phase 4.7 Task 5 - Add Missing DEFAULT Values

Tests database-level default values for 44 columns across 18 tables.
This test suite verifies that database defaults are properly set.

Reference: phase-4.7-db-schema-sync-3-plan.md - Task 5

Note: This suite focuses on critical defaults. The migration applied 44 defaults
successfully as verified by information_schema.columns query.
"""

from sqlmodel import Session

from app.models.fulfillment import Job, JobStatus
from app.models.quoting import Quote, QuoteStatus


class TestJobFinancialDefaults:
    """Test DEFAULT values for job financial tracking (3 defaults)"""

    def test_job_financial_defaults(
        self, db_session: Session, test_tenant, test_customer, test_site
    ):
        """Test job has database defaults for actual_labor_cost_cents, actual_material_cost_cents, actual_profit_cents (all 0)"""
        status = JobStatus(tenant_id=test_tenant.id, code="scheduled", name="Scheduled")
        db_session.add(status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=status.id,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        # Verify all 3 financial tracking defaults
        assert job.actual_labor_cost_cents == 0, (
            "actual_labor_cost_cents should default to 0"
        )
        assert job.actual_material_cost_cents == 0, (
            "actual_material_cost_cents should default to 0"
        )
        assert job.actual_profit_cents == 0, "actual_profit_cents should default to 0"


class TestQuoteTotalsDefaults:
    """Test DEFAULT values for quote totals (4 defaults)"""

    def test_quote_financial_defaults(
        self, db_session: Session, test_tenant, test_customer, test_site
    ):
        """Test quote has database defaults for subtotal_cents, tax_cents, total_cents (0) and currency (USD)"""
        status = QuoteStatus(tenant_id=test_tenant.id, code="draft", name="Draft")
        db_session.add(status)
        db_session.commit()

        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=status.id,
        )
        db_session.add(quote)
        db_session.commit()
        db_session.refresh(quote)

        # Verify all 4 quote total defaults
        assert quote.subtotal_cents == 0, "subtotal_cents should default to 0"
        assert quote.tax_cents == 0, "tax_cents should default to 0"
        assert quote.total_cents == 0, "total_cents should default to 0"
        assert quote.currency == "USD", "currency should default to 'USD'"


class TestDatabaseDefaultsVerification:
    """Verify that all 44 defaults were applied at database level"""

    def test_all_defaults_exist_in_database(self, db_session: Session):
        """Query information_schema to verify all 44 column defaults exist"""
        from sqlalchemy import text

        # Query to count defaults that were set by our migration
        # FIND-086: tenant_settings table dropped; remove it from the table list.
        # The 4 tenant_settings columns (default_labor_rate_cents, default_billable_labor_rate_cents,
        # default_quote_validity_days, default_invoice_terms_days) are now in platform_setting.
        # Expected count adjusted from 44 → 40 (minus 4 tenant_settings columns).
        query = text("""
            SELECT COUNT(*) as default_count
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN (
                'job', 'quote', 'change_order',
                'invoice_line', 'quote_line', 'change_order_line',
                'job_expense', 'notification_outbox', 'webhook_delivery_attempt',
                'idempotency_key', 'integration_sync_mapping', 'integration_sync_conflict',
                'subscription', 'subscription_usage', 'usage_ledger',
                'voice_command_log', 'connector_run_log'
              )
              AND column_name IN (
                'actual_labor_cost_cents', 'actual_material_cost_cents', 'actual_profit_cents',
                'subtotal_cents', 'tax_cents', 'total_cents', 'currency',
                'quantity', 'unit_price_cents', 'is_billable',
                'attempt_count', 'priority', 'status', 'attempt_no',
                'sync_preference', 'quantity_seats', 'billing_interval',
                'cancel_at_period_end', 'used_quantity', 'is_reported',
                'is_successful', 'items_fetched'
              )
              AND column_default IS NOT NULL
        """)

        result = db_session.exec(query).first()
        default_count = result[0] if result else 0

        # FIND-086: 44 - 4 (tenant_settings columns now in platform_setting) = 40
        # CLASS-B1: +1 for job.priority column default = 41
        assert default_count == 41, (
            f"Expected 41 column defaults in database (post-CLASS-B1), found {default_count}"
        )
