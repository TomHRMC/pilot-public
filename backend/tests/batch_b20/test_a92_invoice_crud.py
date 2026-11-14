"""
Test suite for FIND-076 (A92): Authenticated Invoice CRUD endpoints.

Tests cover:
- GET /api/v1/invoices (list with filters)
- POST /api/v1/invoices (create from quote or job)
- GET /api/v1/invoices/{id} (detail with lines)
- POST /api/v1/invoices/{id}/record-payment (manual payment recording)
- Router cleanup verification (no overlapping public routes)
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.billing import (
    Invoice,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
)
from app.models.crm import Customer, Site
from app.models.fulfillment import Job, JobStatus, JobTimeEntry
from app.models.quoting import QcoLineType, Quote, QuoteLine, QuoteStatus


@pytest.fixture
def test_invoice_status_draft(db_session: Session, tenant_a):
    """Ensure draft status exists for tenant_a."""
    draft = db_session.exec(
        select(InvoiceStatus).where(
            InvoiceStatus.code == "draft",
            InvoiceStatus.tenant_id == tenant_a.id,
        )
    ).first()
    if not draft:
        draft = InvoiceStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="draft",
            name="Draft",
            is_default=True,
            is_active=True,
        )
        db_session.add(draft)
        db_session.commit()
    return draft


@pytest.fixture
def test_invoice_status_paid(db_session: Session, tenant_a):
    """Ensure paid status exists for tenant_a."""
    paid = db_session.exec(
        select(InvoiceStatus).where(
            InvoiceStatus.code == "paid",
            InvoiceStatus.tenant_id == tenant_a.id,
        )
    ).first()
    if not paid:
        paid = InvoiceStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="paid",
            name="Paid",
            is_terminal=True,
            is_active=True,
        )
        db_session.add(paid)
        db_session.commit()
    return paid


@pytest.fixture
def test_payment_type(db_session: Session, tenant_a):
    """Ensure a payment type exists for tenant_a."""
    ptype = db_session.exec(
        select(PaymentType).where(
            PaymentType.code == "cash",
            PaymentType.tenant_id == tenant_a.id,
        )
    ).first()
    if not ptype:
        ptype = PaymentType(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="cash",
            name="Cash",
            is_active=True,
        )
        db_session.add(ptype)
        db_session.commit()
    return ptype


@pytest.fixture
def test_payment_method(db_session: Session, tenant_a, test_payment_type):
    """Ensure a payment method exists for tenant_a."""
    method = db_session.exec(
        select(PaymentMethod).where(
            PaymentMethod.payment_type_id == test_payment_type.id,
            PaymentMethod.tenant_id == tenant_a.id,
        )
    ).first()
    if not method:
        method = PaymentMethod(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            payment_type_id=test_payment_type.id,
            psp_provider="manual",
            psp_payment_method_id="manual_cash",
            is_active=True,
        )
        db_session.add(method)
        db_session.commit()
    return method


@pytest.fixture
def test_payment_status(db_session: Session, tenant_a):
    """Ensure a payment status exists for tenant_a."""
    status = db_session.exec(
        select(PaymentStatus).where(
            PaymentStatus.code == "completed",
            PaymentStatus.tenant_id == tenant_a.id,
        )
    ).first()
    if not status:
        status = PaymentStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="completed",
            name="Completed",
            is_active=True,
        )
        db_session.add(status)
        db_session.commit()
    return status


@pytest.fixture
def tenant_a_customer(db_session: Session, tenant_a):
    """Create a customer for tenant_a."""
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        type="person",
        display_name="Test Customer A",
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture
def tenant_a_site(db_session: Session, tenant_a, tenant_a_customer):
    """Create a site for tenant_a."""
    site = Site(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        customer_id=tenant_a_customer.id,
        display_name="Test Site A",
    )
    db_session.add(site)
    db_session.commit()
    return site


@pytest.fixture
def tenant_a_quote_status(db_session: Session, tenant_a):
    """Ensure draft quote status exists for tenant_a."""
    status = db_session.exec(
        select(QuoteStatus).where(
            QuoteStatus.code == "draft",
            QuoteStatus.tenant_id == tenant_a.id,
        )
    ).first()
    if not status:
        status = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="draft",
            name="Draft",
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.commit()
    return status


@pytest.fixture
def tenant_a_qco_line_type(db_session: Session, tenant_a):
    """Create a QCO line type for tenant_a."""
    line_type = db_session.exec(
        select(QcoLineType).where(
            QcoLineType.tenant_id == tenant_a.id,
            QcoLineType.code == "material",
        )
    ).first()
    if not line_type:
        line_type = QcoLineType(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="material",
            name="Material",
            is_default=True,
            is_active=True,
        )
        db_session.add(line_type)
        db_session.commit()
    return line_type


@pytest.fixture
def tenant_a_quote_with_lines(
    db_session: Session,
    tenant_a,
    tenant_a_customer,
    tenant_a_site,
    tenant_a_quote_status,
    tenant_a_qco_line_type,
):
    """Create a test quote with lines for tenant_a."""
    quote = Quote(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        customer_id=tenant_a_customer.id,
        site_id=tenant_a_site.id,
        status_id=tenant_a_quote_status.id,
        subtotal_cents=5000,
        tax_cents=400,
        total_cents=5400,
        currency="USD",
    )
    db_session.add(quote)
    db_session.flush()

    line = QuoteLine(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        quote_id=quote.id,
        position=0,
        qco_line_type_id=tenant_a_qco_line_type.id,
        description="Test Item",
        quantity=1,
        unit_price_cents=5000,
        subtotal_cents=5000,
        total_cents=5400,
        is_active=True,
    )
    db_session.add(line)
    db_session.commit()
    return quote


@pytest.fixture
def tenant_a_job_status(db_session: Session, tenant_a):
    """Ensure job status exists for tenant_a."""
    status = db_session.exec(
        select(JobStatus).where(JobStatus.code == "in_progress")
    ).first()
    if not status:
        status = JobStatus(
            id=uuid.uuid4(),
            code="in_progress",
            name="In Progress",
            is_active=True,
        )
        db_session.add(status)
        db_session.commit()
    return status


@pytest.fixture
def tenant_a_job_with_time_entries(
    db_session: Session,
    tenant_a,
    tenant_a_customer,
    tenant_a_site,
    tenant_a_job_status,
    test_user,
):
    """Create a test job with time entries for tenant_a."""
    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        customer_id=tenant_a_customer.id,
        site_id=tenant_a_site.id,
        status_id=tenant_a_job_status.id,
        job_number=f"JOB-{uuid.uuid4().hex[:8].upper()}",
        is_active=True,
    )
    db_session.add(job)
    db_session.flush()

    now = datetime.now(UTC)
    time_entry = JobTimeEntry(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        job_id=job.id,
        user_id=test_user.id,
        started_at=now,
        ended_at=now,
        hours=2,
        hourly_rate_cents=5000,
        total_cost_cents=10000,
        is_active=True,
    )
    db_session.add(time_entry)
    db_session.commit()
    return job


class TestA92InvoiceCRUDEndpoints:
    """Test authenticated invoice CRUD operations."""

    def test_create_invoice_from_quote_returns_201(
        self,
        client: TestClient,
        mock_cognito_jwt,
        user_tenant_a,
        tenant_a_quote_with_lines,
        test_invoice_status_draft,
    ):
        """POST /invoices with quote_id returns 201 with invoice detail."""
        mock_cognito_jwt(user_tenant_a)

        response = client.post(
            "/api/v1/invoices",
            json={"quote_id": str(tenant_a_quote_with_lines.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["quote_id"] == str(tenant_a_quote_with_lines.id)
        assert "lines" in data
        assert len(data["lines"]) > 0
        assert data["status_code"] == "draft"

    def test_create_invoice_neither_source_returns_400(
        self, client: TestClient, mock_cognito_jwt, user_tenant_a
    ):
        """POST without quote_id or job_id returns 400."""
        mock_cognito_jwt(user_tenant_a)

        response = client.post(
            "/api/v1/invoices",
            json={"customer_notes": "test"},
        )
        assert response.status_code == 400

    def test_create_invoice_both_sources_returns_400(
        self,
        client: TestClient,
        mock_cognito_jwt,
        user_tenant_a,
        tenant_a_quote_with_lines,
        tenant_a_job_with_time_entries,
    ):
        """POST with both quote_id and job_id returns 400."""
        mock_cognito_jwt(user_tenant_a)

        response = client.post(
            "/api/v1/invoices",
            json={
                "quote_id": str(tenant_a_quote_with_lines.id),
                "job_id": str(tenant_a_job_with_time_entries.id),
            },
        )
        assert response.status_code == 400

    def test_list_invoices_returns_paginated_list(
        self,
        client: TestClient,
        db_session: Session,
        mock_cognito_jwt,
        user_tenant_a,
        tenant_a,
        tenant_a_customer,
        tenant_a_site,
        test_invoice_status_draft,
    ):
        """GET /invoices returns paginated list of tenant's invoices."""
        mock_cognito_jwt(user_tenant_a)

        # Create 3 invoices for tenant_a
        for i in range(3):
            invoice = Invoice(
                id=uuid.uuid4(),
                tenant_id=tenant_a.id,
                invoice_number=f"INV-{i:03d}",
                customer_id=tenant_a_customer.id,
                site_id=tenant_a_site.id,
                status_id=test_invoice_status_draft.id,
                subtotal_cents=1000,
                tax_cents=100,
                total_cents=1100,
                balance_due_cents=1100,
            )
            db_session.add(invoice)
        db_session.commit()

        response = client.get("/api/v1/invoices")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_list_invoices_with_pagination(
        self,
        client: TestClient,
        db_session: Session,
        mock_cognito_jwt,
        user_tenant_a,
        tenant_a,
        tenant_a_customer,
        tenant_a_site,
        test_invoice_status_draft,
    ):
        """GET /invoices with limit and offset works."""
        mock_cognito_jwt(user_tenant_a)

        # Create invoices
        for i in range(3):
            invoice = Invoice(
                id=uuid.uuid4(),
                tenant_id=tenant_a.id,
                invoice_number=f"INV-P{i:03d}",
                customer_id=tenant_a_customer.id,
                site_id=tenant_a_site.id,
                status_id=test_invoice_status_draft.id,
                subtotal_cents=1000,
                tax_cents=100,
                total_cents=1100,
                balance_due_cents=1100,
            )
            db_session.add(invoice)
        db_session.commit()

        response = client.get("/api/v1/invoices?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_get_invoice_detail_returns_full_invoice(
        self,
        client: TestClient,
        db_session: Session,
        mock_cognito_jwt,
        user_tenant_a,
        tenant_a,
        tenant_a_customer,
        tenant_a_site,
        test_invoice_status_draft,
    ):
        """GET /{id} returns full invoice detail with lines."""
        mock_cognito_jwt(user_tenant_a)

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_number="INV-DETAIL",
            customer_id=tenant_a_customer.id,
            site_id=tenant_a_site.id,
            status_id=test_invoice_status_draft.id,
            subtotal_cents=1000,
            tax_cents=100,
            total_cents=1100,
            balance_due_cents=1100,
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.get(f"/api/v1/invoices/{invoice.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(invoice.id)
        assert "lines" in data
        assert data["status_code"] == "draft"

    def test_get_invoice_wrong_tenant_returns_404(
        self,
        client: TestClient,
        db_session: Session,
        mock_cognito_jwt,
        user_tenant_a,
        tenant_b,
        test_invoice_status_draft,
    ):
        """Tenant A cannot see tenant B's invoice — returns 404."""
        mock_cognito_jwt(user_tenant_a)

        # Create customer and site for tenant B
        customer_b = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            type="person",
            display_name="Customer B",
        )
        site_b = Site(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            customer_id=customer_b.id,
            display_name="Site B",
        )
        db_session.add(customer_b)
        db_session.add(site_b)
        db_session.flush()

        # Create invoice for tenant B
        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            invoice_number="HIDDEN",
            customer_id=customer_b.id,
            site_id=site_b.id,
            status_id=test_invoice_status_draft.id,
            subtotal_cents=1000,
            tax_cents=100,
            total_cents=1100,
            balance_due_cents=1100,
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.get(f"/api/v1/invoices/{invoice.id}")
        assert response.status_code == 404

    def test_record_payment_returns_201(
        self,
        client: TestClient,
        db_session: Session,
        mock_cognito_jwt,
        user_tenant_a,
        tenant_a,
        tenant_a_customer,
        tenant_a_site,
        test_invoice_status_draft,
        test_payment_method,
        test_payment_status,
    ):
        """POST /{id}/record-payment returns 201 with payment detail."""
        mock_cognito_jwt(user_tenant_a)

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_number="INV-PAY",
            customer_id=tenant_a_customer.id,
            site_id=tenant_a_site.id,
            status_id=test_invoice_status_draft.id,
            subtotal_cents=1000,
            tax_cents=100,
            total_cents=1100,
            balance_due_cents=1100,
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/record-payment",
            json={
                "amount_cents": 1100,
                "paid_via": "other",
                "payment_method_id": str(test_payment_method.id),
                "payment_status_id": str(test_payment_status.id),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["balance_due_cents"] == 0

    def test_record_payment_partial_without_comment_returns_422(
        self,
        client: TestClient,
        db_session: Session,
        mock_cognito_jwt,
        user_tenant_a,
        tenant_a,
        tenant_a_customer,
        tenant_a_site,
        test_invoice_status_draft,
        test_payment_method,
        test_payment_status,
    ):
        """Partial payment without comment returns 422."""
        mock_cognito_jwt(user_tenant_a)

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_number="INV-PARTIAL",
            customer_id=tenant_a_customer.id,
            site_id=tenant_a_site.id,
            status_id=test_invoice_status_draft.id,
            subtotal_cents=1000,
            tax_cents=100,
            total_cents=1100,
            balance_due_cents=1100,
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/record-payment",
            json={
                "amount_cents": 500,  # Partial
                "paid_via": "check",
                "payment_method_id": str(test_payment_method.id),
                "payment_status_id": str(test_payment_status.id),
            },
        )
        assert response.status_code == 422

    def test_record_payment_partial_with_comment_succeeds(
        self,
        client: TestClient,
        db_session: Session,
        mock_cognito_jwt,
        user_tenant_a,
        tenant_a,
        tenant_a_customer,
        tenant_a_site,
        test_invoice_status_draft,
        test_payment_method,
        test_payment_status,
    ):
        """Partial payment with comment succeeds."""
        mock_cognito_jwt(user_tenant_a)

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            invoice_number="INV-PARTIAL-OK",
            customer_id=tenant_a_customer.id,
            site_id=tenant_a_site.id,
            status_id=test_invoice_status_draft.id,
            subtotal_cents=1000,
            tax_cents=100,
            total_cents=1100,
            balance_due_cents=1100,
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/record-payment",
            json={
                "amount_cents": 500,
                "paid_via": "bank_transfer",
                "payment_method_id": str(test_payment_method.id),
                "payment_status_id": str(test_payment_status.id),
                "comment": "Partial payment",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["balance_due_cents"] == 600


class TestA92RouterCleanup:
    """Verify router cleanup — no double-registration of routes (INV-ROUTE-FIX)."""

    def test_public_invoice_route_is_unique_and_canonical(self):
        """/api/v1/public/invoices/{signed_token} must resolve to exactly ONE route (the canonical handler)."""
        from app.main import app

        matches = [
            r
            for r in app.routes
            if getattr(r, "path", "") == "/api/v1/public/invoices/{signed_token}"
        ]
        # Exactly one registration — no legacy shadow
        assert len(matches) == 1, (
            f"Expected 1 canonical route, found {len(matches)}: {[getattr(r, 'path', '') for r in matches]}"
        )

        # The legacy path param name must NOT be present (legacy used {token})
        legacy = [
            r
            for r in app.routes
            if getattr(r, "path", "") == "/api/v1/public/invoices/{token}"
        ]
        assert legacy == [], (
            f"Legacy public_router invoice route is still registered: {legacy}"
        )

    def test_app_boots_without_errors(self, client: TestClient):
        """FastAPI app boots successfully with cleaned up routers."""
        # If app boots, routers are properly defined
        assert client is not None
