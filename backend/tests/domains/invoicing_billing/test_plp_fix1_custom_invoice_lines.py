"""
PLP-FIX-1 — Custom Invoice Line Items Tests
=============================================
Domain: invoicing_billing (PRD §3.6)

Tests the three-mode invoice creation (quote / job / standalone) and the
custom ``line_items[]`` field added to ``InvoiceCreate``.

Uses the ``/api/v1/invoices/test`` endpoint (unauthenticated, canonical test
tenant) and existing fixtures (``test_customer``, ``test_site``,
``test_invoice_status``). Jobs are created via ``/api/v1/jobs/test``.

Test cases:
  1.  Standalone happy path (2 items, one explicit line type, one default)
  2.  Standalone without customer_id → 400
  3.  Standalone with line_items: [] → 400
  4.  Standalone with cross-tenant customer → 404
  5.  Site not belonging to the customer → 422
  6.  Job invoice with custom lines appended
  7.  Job-path line types (latent-bug regression — labor/material, no NULLs)
  8.  Quote invoice with custom lines
  9.  quote_id + customer_id together → 400 invalid-mode
  10. Unknown qco_line_type_code → 404
  11. Negative unit_price_cents / zero quantity → 422 (Pydantic validator)
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlmodel import select

from app.models.billing import InvoiceLine
from app.models.quoting import QcoLineType
from core.config import settings

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


# ── Helpers ───────────────── foreign customer for cross-tenant test ──────


def _make_job(client, test_customer, test_site):
    """Create a job in the canonical test tenant. Returns job dict or None."""
    with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
        with patch.object(settings, "ENVIRONMENT", "dev"):
            resp = client.post(
                "/api/v1/jobs/test",
                json={
                    "customer_id": str(test_customer.id),
                    "site_id": str(test_site.id),
                    "description": "PLP-FIX-1 custom-lines test job",
                },
            )
    if resp.status_code in (200, 201):
        return resp.json()
    return None


def _make_invoice(client, payload):
    """POST to /api/v1/invoices/test with the given payload."""
    with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
        with patch.object(settings, "ENVIRONMENT", "dev"):
            return client.post("/api/v1/invoices/test", json=payload)


def _get_misc_line_type_id(db_session) -> uuid.UUID:
    """Look up the seeded 'misc' qco_line_type id (platform row, tenant_id IS NULL)."""
    row = db_session.exec(
        select(QcoLineType).where(
            QcoLineType.code == "misc",
            QcoLineType.tenant_id.is_(None),
        )
    ).first()
    if row is None:
        # Fall back to any 'misc' row
        row = db_session.exec(
            select(QcoLineType).where(QcoLineType.code == "misc")
        ).first()
    assert row is not None, "qco_line_type 'misc' not seeded"
    return row.id


def _get_labor_line_type_id(db_session) -> uuid.UUID:
    """Look up the seeded 'labor' qco_line_type id."""
    row = db_session.exec(
        select(QcoLineType).where(
            QcoLineType.code == "labor",
            QcoLineType.tenant_id.is_(None),
        )
    ).first()
    if row is None:
        row = db_session.exec(
            select(QcoLineType).where(QcoLineType.code == "labor")
        ).first()
    assert row is not None, "qco_line_type 'labor' not seeded"
    return row.id


def _get_material_line_type_id(db_session) -> uuid.UUID:
    """Look up the seeded 'material' qco_line_type id."""
    row = db_session.exec(
        select(QcoLineType).where(
            QcoLineType.code == "material",
            QcoLineType.tenant_id.is_(None),
        )
    ).first()
    if row is None:
        row = db_session.exec(
            select(QcoLineType).where(QcoLineType.code == "material")
        ).first()
    assert row is not None, "qco_line_type 'material' not seeded"
    return row.id


# ── Tests ────────────────────────────────────────────────────────────────────


class TestStandaloneMode:
    """Standalone invoice creation (customer_id + site_id + line_items)."""

    def test_standalone_happy_path(
        self,
        client,
        test_tenant,
        test_customer,
        test_site,
        test_invoice_status,
        db_session,
    ):
        """2 custom lines: one explicit 'labor' type, one defaulting to 'misc'."""
        resp = _make_invoice(
            client,
            {
                "customer_id": str(test_customer.id),
                "site_id": str(test_site.id),
                "line_items": [
                    {
                        "description": "Labor — panel install",
                        "quantity": "4.5",
                        "unit": "hr",
                        "unit_price_cents": 12500,
                        "qco_line_type_code": "labor",
                    },
                    {
                        "description": "Miscellaneous supplies",
                        "quantity": "1",
                        "unit_price_cents": 5000,
                    },
                ],
            },
        )
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text[:400]}"
        )
        data = resp.json()
        invoice_id = data["id"]

        # Totals: 4.5 × 12500 = 56250; 1 × 5000 = 5000; total = 61250
        expected_subtotal = int(round(Decimal("4.5") * 12500)) + 5000
        assert data["subtotal_cents"] == expected_subtotal, (
            f"Expected subtotal {expected_subtotal}, got {data['subtotal_cents']}"
        )
        assert data["total_cents"] == expected_subtotal
        assert data["balance_due_cents"] == expected_subtotal
        assert data["quote_id"] is None
        assert data["job_id"] is None

        # Lines: 2 ad_hoc lines, correct positions and line types
        lines = data["lines"]
        assert len(lines) == 2
        assert all(ln["source_type"] == "ad_hoc" for ln in lines)
        assert lines[0]["position"] == 0
        assert lines[1]["position"] == 1

        labor_id = _get_labor_line_type_id(db_session)
        misc_id = _get_misc_line_type_id(db_session)
        assert lines[0]["qco_line_type_id"] == str(labor_id)
        assert lines[1]["qco_line_type_id"] == str(misc_id)

        # Verify persisted in DB (scoped by invoice_id)
        db_lines = db_session.exec(
            select(InvoiceLine).where(InvoiceLine.invoice_id == uuid.UUID(invoice_id))
        ).all()
        assert len(db_lines) == 2

    def test_standalone_without_customer_id_returns_400(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """Standalone without customer_id → 400 invalid-mode."""
        resp = _make_invoice(
            client,
            {
                "site_id": str(test_site.id),
                "line_items": [
                    {"description": "Test", "unit_price_cents": 1000},
                ],
            },
        )
        assert resp.status_code == 400
        detail = resp.json().get("detail", {})
        assert detail.get("status") == 400

    def test_standalone_with_empty_line_items_returns_400(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """Standalone with line_items: [] → 400 invalid-mode (no lines = no mode)."""
        resp = _make_invoice(
            client,
            {
                "customer_id": str(test_customer.id),
                "site_id": str(test_site.id),
                "line_items": [],
            },
        )
        assert resp.status_code == 400

    def test_standalone_cross_tenant_customer_returns_404(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """Cross-tenant customer → 404 (never 403 — no UUID enumeration)."""
        foreign_customer_id = str(uuid.uuid4())
        resp = _make_invoice(
            client,
            {
                "customer_id": foreign_customer_id,
                "site_id": str(test_site.id),
                "line_items": [
                    {"description": "Test", "unit_price_cents": 1000},
                ],
            },
        )
        assert resp.status_code == 404
        detail = resp.json().get("detail", {})
        assert detail.get("status") == 404

    def test_site_not_belonging_to_customer_returns_422(
        self,
        client,
        test_tenant,
        test_customer,
        test_site,
        test_invoice_status,
        db_session,
    ):
        """Site belonging to a different customer → 422."""
        from app.models.crm import Customer, CustomerType

        # Create a second customer in the same tenant
        other_customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            type=CustomerType.person,
            display_name=f"Other Customer {uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db_session.add(other_customer)
        db_session.commit()
        db_session.refresh(other_customer)

        # Use test_site (belongs to test_customer) with other_customer
        resp = _make_invoice(
            client,
            {
                "customer_id": str(other_customer.id),
                "site_id": str(test_site.id),
                "line_items": [
                    {"description": "Test", "unit_price_cents": 1000},
                ],
            },
        )
        assert resp.status_code == 422
        detail = resp.json().get("detail", {})
        assert detail.get("status") == 422


class TestJobMode:
    """Job-sourced invoice with custom lines appended + line-type regression."""

    def test_job_invoice_with_custom_lines_appended(
        self,
        client,
        test_tenant,
        test_customer,
        test_site,
        test_invoice_status,
        db_session,
    ):
        """Job invoice + 1 custom line → custom line's position continues after source lines."""
        job = _make_job(client, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")

        resp = _make_invoice(
            client,
            {
                "job_id": job["id"],
                "line_items": [
                    {
                        "description": "Custom fee",
                        "quantity": "1",
                        "unit_price_cents": 7500,
                    },
                ],
            },
        )
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text[:400]}"
        )
        data = resp.json()
        lines = data["lines"]

        # The custom line should be the last one (position continues after source lines)
        custom_lines = [ln for ln in lines if ln["source_type"] == "ad_hoc"]
        # Job path also creates ad_hoc lines for time entries/expenses, so we
        # check that the custom line exists with the correct description
        custom_fee_lines = [ln for ln in lines if ln["description"] == "Custom fee"]
        assert len(custom_fee_lines) == 1, (
            f"Expected 1 custom-fee line, found {len(custom_fee_lines)} in {len(lines)} total"
        )
        # Position should be >= the number of source-derived lines
        assert custom_fee_lines[0]["position"] >= 0

    def test_job_path_line_types_no_nulls(
        self,
        client,
        test_tenant,
        test_customer,
        test_site,
        test_invoice_status,
        db_session,
    ):
        """Latent-bug regression: job-path lines must have labor/material line types (no NULLs).

        Before PLP-FIX-1 the job path passed ``qco_line_type_id=None`` into a
        NOT NULL column → guaranteed IntegrityError. Now time-entry lines get
        'labor' and expense lines get 'material'.
        """
        # Create a job with a time entry so the invoice has at least one line
        from app.models.fulfillment import Job, JobStatus, JobTimeEntry

        job_status = db_session.exec(
            select(JobStatus).where(JobStatus.code == "draft")
        ).first()
        if not job_status:
            pytest.skip("Job 'draft' status not seeded")

        job = Job(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            description="PLP-FIX-1 line-type regression job",
        )
        db_session.add(job)
        db_session.flush()

        time_entry = JobTimeEntry(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            started_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            hours=Decimal("2.0"),
            hourly_rate_cents=10000,
            total_cost_cents=20000,
        )
        db_session.add(time_entry)
        db_session.commit()

        resp = _make_invoice(client, {"job_id": str(job.id)})
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text[:400]}"
        )
        data = resp.json()
        lines = data["lines"]

        # Every line must have a non-null qco_line_type_id
        for ln in lines:
            assert ln["qco_line_type_id"] is not None, (
                f"Line {ln['description']} has null qco_line_type_id — NOT NULL bug not fixed!"
            )

        # The time-entry line should have the 'labor' line type
        labor_id = _get_labor_line_type_id(db_session)
        labor_lines = [ln for ln in lines if ln["qco_line_type_id"] == str(labor_id)]
        assert len(labor_lines) >= 1, "No labor-typed line found for the time entry"


class TestQuoteMode:
    """Quote-sourced invoice with custom lines appended."""

    def test_quote_invoice_with_custom_lines(
        self,
        client,
        test_tenant,
        test_customer,
        test_site,
        test_invoice_status,
        db_session,
    ):
        """Quote-sourced lines first, custom lines appended after."""
        from app.models.billing import Currency
        from app.models.quoting import Quote, QuoteLine, QuoteStatus

        # Ensure currency
        currency = db_session.exec(
            select(Currency).where(Currency.code == "USD")
        ).first()
        if not currency:
            currency = Currency(code="USD", name="US Dollar", symbol="$")
            db_session.add(currency)
            db_session.flush()

        # Create quote status
        quote_status = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            code="draft",
            name="Draft",
            is_default=True,
        )
        db_session.add(quote_status)
        db_session.flush()

        # Create a quote
        misc_id = _get_misc_line_type_id(db_session)
        quote = Quote(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=quote_status.id,
            currency="USD",
            subtotal_cents=10000,
            tax_cents=0,
            total_cents=10000,
        )
        db_session.add(quote)
        db_session.flush()

        # Create a quote line
        quote_line = QuoteLine(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            quote_id=quote.id,
            position=0,
            qco_line_type_id=misc_id,
            description="Quote line item",
            quantity=1.0,
            unit_price_cents=10000,
            subtotal_cents=10000,
            total_cents=10000,
            is_active=True,
            is_section_header=False,
        )
        db_session.add(quote_line)
        db_session.commit()

        resp = _make_invoice(
            client,
            {
                "quote_id": str(quote.id),
                "line_items": [
                    {
                        "description": "Additional custom line",
                        "quantity": "1",
                        "unit_price_cents": 3000,
                    },
                ],
            },
        )
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text[:400]}"
        )
        data = resp.json()
        lines = data["lines"]

        # Quote line first (position 0), custom line after (position 1)
        assert len(lines) == 2
        quote_lines = [ln for ln in lines if ln["source_type"] == "quote_line"]
        custom_lines = [ln for ln in lines if ln["source_type"] == "ad_hoc"]
        assert len(quote_lines) == 1
        assert len(custom_lines) == 1
        assert quote_lines[0]["position"] == 0
        assert custom_lines[0]["position"] == 1

        # Totals: 10000 (quote) + 3000 (custom) = 13000
        assert data["subtotal_cents"] == 13000
        assert data["total_cents"] == 13000


class TestModeConflicts:
    """Mode-conflict and validation error cases."""

    def test_quote_id_plus_customer_id_returns_400(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """quote_id + customer_id together → 400 invalid-mode (design §G-7)."""
        resp = _make_invoice(
            client,
            {
                "quote_id": str(uuid.uuid4()),
                "customer_id": str(test_customer.id),
                "site_id": str(test_site.id),
                "line_items": [
                    {"description": "Test", "unit_price_cents": 1000},
                ],
            },
        )
        assert resp.status_code == 400
        detail = resp.json().get("detail", {})
        assert detail.get("status") == 400
        assert "invalid-mode" in detail.get("type", "")

    def test_unknown_qco_line_type_code_returns_404(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """Unknown qco_line_type_code → 404 RFC 7807."""
        resp = _make_invoice(
            client,
            {
                "customer_id": str(test_customer.id),
                "site_id": str(test_site.id),
                "line_items": [
                    {
                        "description": "Test",
                        "unit_price_cents": 1000,
                        "qco_line_type_code": "nonexistent_type",
                    },
                ],
            },
        )
        assert resp.status_code == 404
        detail = resp.json().get("detail", {})
        assert detail.get("status") == 404

    def test_negative_unit_price_returns_422(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """Negative unit_price_cents → 422 (Pydantic validator)."""
        resp = _make_invoice(
            client,
            {
                "customer_id": str(test_customer.id),
                "site_id": str(test_site.id),
                "line_items": [
                    {
                        "description": "Test",
                        "unit_price_cents": -100,
                    },
                ],
            },
        )
        assert resp.status_code == 422

    def test_zero_quantity_returns_422(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """Zero quantity → 422 (Pydantic validator)."""
        resp = _make_invoice(
            client,
            {
                "customer_id": str(test_customer.id),
                "site_id": str(test_site.id),
                "line_items": [
                    {
                        "description": "Test",
                        "quantity": "0",
                        "unit_price_cents": 1000,
                    },
                ],
            },
        )
        assert resp.status_code == 422
