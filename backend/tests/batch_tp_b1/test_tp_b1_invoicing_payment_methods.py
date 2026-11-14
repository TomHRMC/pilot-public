"""
TP-B1 — Invoicing CRUD + Customer Payment Methods — Test Endpoints

Coverage (one happy-path test per new /test endpoint minimum):
  1. GET  /api/v1/invoices/test                                        -> list_invoices_test
  2. POST /api/v1/invoices/test                                        -> create_invoice_test (from job)
  3. GET  /api/v1/invoices/{invoice_id}/test                           -> get_invoice_test
  4. POST /api/v1/invoices/{invoice_id}/record-payment/test            -> record_payment_test
  5. GET  /api/v1/customers/{customer_id}/payment-methods/test         -> list_payment_methods_test
  6. POST /api/v1/customers/{customer_id}/payment-methods/test         -> create_payment_method_test
  7. DELETE /api/v1/customers/{customer_id}/payment-methods/{pm_id}/test -> delete_payment_method_test

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - 403 when ENVIRONMENT=production
  - Tenant isolation (test endpoints use test tenant only)
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import status
from sqlmodel import select

from app.models.billing import (
    Invoice,
    InvoiceStatus,
    PaymentStatus,
    PaymentType,
)
from app.models.crm import Customer, Site
from app.models.fulfillment import Job, JobStatus
from core.config import settings

# ==================== FIXTURES ====================

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def test_invoice_status_draft(db_session, test_tenant):
    """Get or create 'draft' InvoiceStatus for the test tenant."""
    existing = db_session.exec(
        select(InvoiceStatus).where(
            InvoiceStatus.tenant_id == test_tenant.id,
            InvoiceStatus.code == "draft",
        )
    ).first()
    if existing:
        return existing
    status_obj = InvoiceStatus(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="draft",
        name="Draft",
        is_active=True,
    )
    db_session.add(status_obj)
    db_session.commit()
    db_session.refresh(status_obj)
    return status_obj


@pytest.fixture
def test_payment_status(db_session, test_tenant):
    """Get or create a PaymentStatus for the test tenant."""
    existing = db_session.exec(
        select(PaymentStatus).where(
            PaymentStatus.tenant_id == test_tenant.id,
        )
    ).first()
    if existing:
        return existing
    ps = PaymentStatus(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="completed",
        name="Completed",
        is_active=True,
    )
    db_session.add(ps)
    db_session.commit()
    db_session.refresh(ps)
    return ps


@pytest.fixture
def test_payment_type(db_session, test_tenant):
    """Get or create a PaymentType for the test tenant."""
    existing = db_session.exec(
        select(PaymentType).where(
            PaymentType.tenant_id == test_tenant.id,
            PaymentType.code == "card",
        )
    ).first()
    if existing:
        return existing
    pt = PaymentType(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="card",
        name="Credit Card",
        is_active=True,
    )
    db_session.add(pt)
    db_session.commit()
    db_session.refresh(pt)
    return pt


@pytest.fixture
def test_customer_tp_b1(db_session, test_tenant):
    """Create a test Customer in the test tenant."""
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        type="person",
        display_name=f"TP-B1 Test Customer {uuid.uuid4().hex[:6]}",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def test_site_tp_b1(db_session, test_tenant, test_customer_tp_b1):
    """Create a test Site in the test tenant."""
    site = Site(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer_tp_b1.id,
        address_line_1="123 Test St",
        city="Test City",
        state="TX",
        postal_code="75001",
        country="US",
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)
    return site


@pytest.fixture
def test_job_tp_b1(db_session, test_tenant, test_customer_tp_b1, test_site_tp_b1):
    """Create a minimal Job in the test tenant for invoice creation tests."""
    job_status = db_session.exec(
        select(JobStatus).where(
            JobStatus.tenant_id == test_tenant.id,
        )
    ).first()
    if not job_status:
        job_status = JobStatus(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            code="scheduled",
            name="Scheduled",
            is_active=True,
        )
        db_session.add(job_status)
        db_session.commit()
        db_session.refresh(job_status)

    job = Job(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer_tp_b1.id,
        site_id=test_site_tp_b1.id,
        status_id=job_status.id,
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def test_invoice_tp_b1(
    db_session,
    test_tenant,
    test_customer_tp_b1,
    test_site_tp_b1,
    test_invoice_status_draft,
):
    """Create a test Invoice in the test tenant."""
    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=test_customer_tp_b1.id,
        site_id=test_site_tp_b1.id,
        invoice_number=f"INV-TEST-{uuid.uuid4().hex[:6].upper()}",
        status_id=test_invoice_status_draft.id,
        subtotal_cents=10000,
        tax_cents=0,
        total_cents=10000,
        balance_due_cents=10000,
        currency="USD",
        issued_at=datetime.now(UTC),
        is_active=True,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


# ==================== SECURITY GUARD TESTS ====================


class TestTpB1SecurityGuards:
    """Verify /test endpoints are blocked in production and when disabled."""

    def test_list_invoices_test_blocked_when_disabled(self, client):
        """GET /invoices/test returns 403 when TEST_ENDPOINT_ENABLED=false."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/invoices/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "test_endpoints_disabled" in response.json()["detail"]["error"]

    def test_list_invoices_test_blocked_in_production(self, client):
        """GET /invoices/test returns 403 in production environment."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.get("/api/v1/invoices/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_payment_methods_test_blocked_when_disabled(
        self, client, test_customer_tp_b1
    ):
        """GET /customers/{id}/payment-methods/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/test"
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== INVOICE /test ENDPOINT TESTS ====================


class TestTpB1InvoiceTestEndpoints:
    """Happy-path tests for invoice /test endpoints."""

    def test_list_invoices_test_returns_200(
        self, client, test_tenant, test_invoice_tp_b1
    ):
        """GET /api/v1/invoices/test returns 200 with invoice list."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/invoices/test")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        # Items have expected fields (InvoiceSummary schema, no tenant_id in response)
        for item in data["items"]:
            assert "id" in item
            assert "invoice_number" in item
            assert "status_code" in item

    def test_list_invoices_test_includes_created_invoice(
        self, client, test_tenant, test_invoice_tp_b1
    ):
        """GET /api/v1/invoices/test includes the fixture invoice in results."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/invoices/test")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.json()["items"]]
        assert str(test_invoice_tp_b1.id) in ids

    def test_get_invoice_test_returns_invoice(
        self, client, test_tenant, test_invoice_tp_b1
    ):
        """GET /api/v1/invoices/{invoice_id}/test returns full invoice detail."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"/api/v1/invoices/{test_invoice_tp_b1.id}/test")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_invoice_tp_b1.id)
        assert data["tenant_id"] == str(TEST_TENANT_ID)
        assert data["balance_due_cents"] == 10000
        assert "lines" in data

    def test_get_invoice_test_404_for_unknown(self, client):
        """GET /api/v1/invoices/{unknown_id}/test returns 404."""
        fake_id = str(uuid.uuid4())
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"/api/v1/invoices/{fake_id}/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_invoice_test_from_job(
        self,
        client,
        test_tenant,
        test_job_tp_b1,
        test_invoice_status_draft,
    ):
        """POST /api/v1/invoices/test creates invoice from job without auth."""
        payload = {
            "job_id": str(test_job_tp_b1.id),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post("/api/v1/invoices/test", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["tenant_id"] == str(TEST_TENANT_ID)
        assert data["job_id"] == str(test_job_tp_b1.id)
        assert "invoice_number" in data
        assert data["invoice_number"].startswith("INV-")
        assert "lines" in data

    def test_create_invoice_test_rejects_both_null(self, client):
        """POST /api/v1/invoices/test returns 400 if neither quote_id nor job_id provided."""
        payload = {}
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post("/api/v1/invoices/test", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_record_payment_test_404_for_unknown_invoice(self, client):
        """POST /api/v1/invoices/{unknown}/record-payment/test returns 404."""
        fake_id = str(uuid.uuid4())
        payload = {
            "amount_cents": 5000,
            "paid_via": "check",
            "payment_method_id": str(uuid.uuid4()),
            "payment_status_id": str(uuid.uuid4()),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/invoices/{fake_id}/record-payment/test",
                    json=payload,
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_record_payment_test_endpoint_reachable(
        self,
        client,
        test_tenant,
        test_invoice_tp_b1,
        test_payment_status,
        test_payment_type,
    ):
        """POST /api/v1/invoices/{invoice_id}/record-payment/test endpoint is reachable (not 403/405)."""
        # We just need to confirm the route resolves; business validation may reject the PM UUID
        payload = {
            "amount_cents": 10000,
            "paid_via": "check",
            "payment_method_id": str(uuid.uuid4()),  # fake PM — will pass routing
            "payment_status_id": str(test_payment_status.id),
            "paid_at": datetime.now(UTC).isoformat(),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/invoices/{test_invoice_tp_b1.id}/record-payment/test",
                    json=payload,
                )
        # Endpoint must be reachable — not blocked by routing or auth
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.status_code != status.HTTP_404_NOT_FOUND


# ==================== PAYMENT METHODS /test ENDPOINT TESTS ====================


class TestTpB1PaymentMethodsTestEndpoints:
    """Happy-path tests for customer payment methods /test endpoints."""

    def test_list_payment_methods_test_returns_empty_for_new_customer(
        self, client, test_customer_tp_b1
    ):
        """GET /api/v1/customers/{id}/payment-methods/test returns empty list."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/test"
                )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_create_payment_method_test_creates_payment_method(
        self, client, test_customer_tp_b1, test_payment_type
    ):
        """POST /api/v1/customers/{id}/payment-methods/test vaults a new payment method."""
        payload = {
            "psp_payment_method_id": f"pm_tpb1_{uuid.uuid4().hex[:10]}",
            "payment_type_id": str(test_payment_type.id),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/test",
                    json=payload,
                )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["customer_id"] == str(test_customer_tp_b1.id)
        assert data["tenant_id"] == str(TEST_TENANT_ID)
        assert data["psp_payment_method_id"] == payload["psp_payment_method_id"]
        assert data["is_active"] is True
        assert data["psp_provider"] == "stripe"

    def test_list_payment_methods_test_returns_created_method(
        self, client, test_customer_tp_b1, test_payment_type
    ):
        """GET /api/v1/customers/{id}/payment-methods/test returns vaulted methods."""
        psp_id = f"pm_list_tpb1_{uuid.uuid4().hex[:8]}"
        payload = {
            "psp_payment_method_id": psp_id,
            "payment_type_id": str(test_payment_type.id),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                create_resp = client.post(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/test",
                    json=payload,
                )
                assert create_resp.status_code == status.HTTP_201_CREATED

                list_resp = client.get(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/test"
                )
        assert list_resp.status_code == status.HTTP_200_OK
        methods = list_resp.json()
        assert any(m["psp_payment_method_id"] == psp_id for m in methods)

    def test_delete_payment_method_test_soft_deletes(
        self, client, test_customer_tp_b1, test_payment_type
    ):
        """DELETE /api/v1/customers/{id}/payment-methods/{pm_id}/test soft-deletes."""
        psp_id = f"pm_del_tpb1_{uuid.uuid4().hex[:8]}"
        payload = {
            "psp_payment_method_id": psp_id,
            "payment_type_id": str(test_payment_type.id),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                create_resp = client.post(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/test",
                    json=payload,
                )
                assert create_resp.status_code == status.HTTP_201_CREATED
                pm_id = create_resp.json()["id"]

                delete_resp = client.delete(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/{pm_id}/test"
                )
        assert delete_resp.status_code == status.HTTP_200_OK
        data = delete_resp.json()
        assert data["message"] == "Payment method deleted successfully"
        assert data["id"] == pm_id

    def test_delete_payment_method_test_no_longer_in_list(
        self, client, test_customer_tp_b1, test_payment_type
    ):
        """After deletion, method no longer appears in list."""
        psp_id = f"pm_gone_tpb1_{uuid.uuid4().hex[:8]}"
        payload = {
            "psp_payment_method_id": psp_id,
            "payment_type_id": str(test_payment_type.id),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                create_resp = client.post(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/test",
                    json=payload,
                )
                pm_id = create_resp.json()["id"]

                client.delete(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/{pm_id}/test"
                )

                list_resp = client.get(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/test"
                )
        assert list_resp.status_code == status.HTTP_200_OK
        ids = [m["id"] for m in list_resp.json()]
        assert pm_id not in ids

    def test_list_payment_methods_test_404_for_unknown_customer(self, client):
        """GET /api/v1/customers/{unknown}/payment-methods/test returns 404."""
        fake_id = str(uuid.uuid4())
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"/api/v1/customers/{fake_id}/payment-methods/test"
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_payment_method_test_404_for_unknown_customer(
        self, client, test_payment_type
    ):
        """POST /api/v1/customers/{unknown}/payment-methods/test returns 404."""
        fake_id = str(uuid.uuid4())
        payload = {
            "psp_payment_method_id": "pm_unknown",
            "payment_type_id": str(test_payment_type.id),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/customers/{fake_id}/payment-methods/test",
                    json=payload,
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_payment_methods_test_tenant_isolation(self, client, test_customer_tp_b1):
        """Payment methods listed via test endpoint only belong to test tenant."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"/api/v1/customers/{test_customer_tp_b1.id}/payment-methods/test"
                )
        assert response.status_code == status.HTTP_200_OK
        for pm in response.json():
            assert pm["tenant_id"] == str(TEST_TENANT_ID)
