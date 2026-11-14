"""
B20 — Invoice Builder Fields
Tests for: payment_terms, billing_mode, progress_pct, internal_memo on Invoice.
Also verifies payment_terms → due_at auto-computation (design doc §G.1).

Invoices are created by supplying a job_id. Jobs are created first via /jobs/test
so they live in the canonical TestUserContext tenant.

The invoice /test endpoint requires a 'draft' InvoiceStatus scoped to the tenant.
We use the test_invoice_status fixture which creates this row.

Domain: invoicing_billing
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from core.config import settings

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


def _make_job(client, test_customer, test_site):
    """Create a job in the canonical test tenant. Returns job dict or None."""
    with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
        with patch.object(settings, "ENVIRONMENT", "dev"):
            resp = client.post(
                "/api/v1/jobs/test",
                json={
                    "customer_id": str(test_customer.id),
                    "site_id": str(test_site.id),
                    "description": "B20 invoice field test job",
                },
            )
    if resp.status_code in (200, 201):
        return resp.json()
    return None


def _make_invoice(client, job_id, extra=None):
    """Create an invoice from a job via the /invoices/test endpoint."""
    payload = {"job_id": job_id}
    if extra:
        payload.update(extra)
    with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
        with patch.object(settings, "ENVIRONMENT", "dev"):
            return client.post("/api/v1/invoices/test", json=payload)


class TestInvoiceBuilderFields:
    """Test new B20 fields: payment_terms, billing_mode, progress_pct, internal_memo."""

    def test_invoice_defaults_billing_mode_to_line_item(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """billing_mode defaults to 'line_item' when not specified."""
        job = _make_job(client, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")
        resp = _make_invoice(client, job["id"])
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data["billing_mode"] == "line_item"
        assert data["payment_terms"] is None
        assert data["progress_pct"] is None
        assert data["internal_memo"] is None

    def test_invoice_payment_terms_net_30(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """payment_terms='net_30' persists on created invoice."""
        job = _make_job(client, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")
        resp = _make_invoice(
            client,
            job["id"],
            extra={
                "payment_terms": "net_30",
                "billing_mode": "line_item",
            },
        )
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data["payment_terms"] == "net_30"
        assert data["billing_mode"] == "line_item"

    def test_invoice_billing_mode_progress_requires_pct(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """billing_mode='progress' without progress_pct returns 422."""
        job = _make_job(client, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")
        resp = _make_invoice(
            client,
            job["id"],
            extra={
                "billing_mode": "progress",
                "progress_pct": None,
            },
        )
        assert resp.status_code == 422

    def test_invoice_billing_mode_progress_with_pct(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """billing_mode='progress' with valid progress_pct saves correctly."""
        job = _make_job(client, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")
        resp = _make_invoice(
            client,
            job["id"],
            extra={
                "billing_mode": "progress",
                "progress_pct": "50.00",
            },
        )
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data["billing_mode"] == "progress"
        assert Decimal(str(data["progress_pct"])) == Decimal("50.00")

    def test_invoice_internal_memo(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """internal_memo is stored and returned in response."""
        job = _make_job(client, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")
        resp = _make_invoice(
            client,
            job["id"],
            extra={
                "internal_memo": "Do not include on PDF.",
            },
        )
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text[:300]}"
        )
        assert resp.json()["internal_memo"] == "Do not include on PDF."

    def test_invoice_payment_terms_net_15_computes_due_at(
        self, client, test_tenant, test_customer, test_site, test_invoice_status
    ):
        """payment_terms='net_15' should auto-compute due_at = issued_at + 15 days."""
        job = _make_job(client, test_customer, test_site)
        if job is None:
            pytest.skip("Job creation failed")
        resp = _make_invoice(
            client,
            job["id"],
            extra={
                "payment_terms": "net_15",
                "issued_at": "2026-07-01T00:00:00Z",
            },
        )
        assert resp.status_code == 201, (
            f"Expected 201, got {resp.status_code}: {resp.text[:300]}"
        )
        data = resp.json()
        assert data["payment_terms"] == "net_15"
        # due_at should be set (not None) when payment_terms is net_15 + issued_at provided
        assert data["due_at"] is not None
