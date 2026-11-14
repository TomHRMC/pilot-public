"""
Tests for: CE-1 Invoice Sign-Off Capture (mobile, offline-first)
Domain: invoicing_billing (PRD §3.6)

Covers D.1 (signoff-context), D.2 (POST signoff), D.3 (GET signoff).
S3 is mocked at services.s3_service._s3_client — never hits real S3.
"""

import base64
import uuid
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]

# Minimal valid 1x1 PNG (67 bytes)
_MINIMAL_PNG = base64.b64encode(
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
).decode()


def _create_test_invoice(client, db_session, test_tenant, status_code="issued"):
    """Create a customer, site, job, and invoice in the given status via /test endpoints."""
    from datetime import UTC, datetime

    from sqlmodel import select

    from app.models.billing import Invoice, InvoiceStatus

    # Create customer
    cust = client.post(
        "/api/v1/customers/test",
        json={"display_name": "Signoff Test Co", "type": "person"},
    )
    assert cust.status_code == 201
    customer_id = cust.json()["id"]

    # Create site
    site = client.post(
        "/api/v1/sites/test",
        json={"customer_id": customer_id, "name": "Test Site"},
    )
    assert site.status_code == 201
    site_id = site.json()["id"]

    # Create job
    job = client.post(
        "/api/v1/jobs/test",
        json={"customer_id": customer_id, "site_id": site_id},
    )
    assert job.status_code == 201
    job_id = job.json()["id"]

    # Resolve invoice status by code
    inv_status = db_session.exec(
        select(InvoiceStatus).where(InvoiceStatus.code == status_code)
    ).first()

    # Create invoice directly in DB (bypassing the create endpoint which only makes draft)
    invoice = Invoice(
        tenant_id=test_tenant.id,
        invoice_number=f"INV-SIGNOFF-{uuid.uuid4().hex[:8]}",
        customer_id=uuid.UUID(customer_id),
        site_id=uuid.UUID(site_id),
        job_id=uuid.UUID(job_id),
        status_id=inv_status.id,
        subtotal_cents=10000,
        tax_cents=0,
        total_cents=10000,
        balance_due_cents=10000,
        currency="USD",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)

    return {
        "invoice_id": str(invoice.id),
        "job_id": job_id,
        "customer_id": customer_id,
    }


class TestSignoffCreate:
    """D.2 — POST /api/v1/invoices/{invoice_id}/signoff"""

    def test_create_signoff_happy_path(self, client, db_session, test_tenant):
        """Create sign-off → 200, row active, object key correct, presigned URL present."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "issued")
        invoice_id = ctx["invoice_id"]

        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {}
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"

        with patch("services.s3_service._s3_client", return_value=mock_s3):
            resp = client.post(
                f"/api/v1/invoices/{invoice_id}/signoff/test",
                json={
                    "signed_by_name": "John Customer",
                    "terms_acknowledged": True,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["signed_by_name"] == "John Customer"
        assert data["invoice_id"] == invoice_id
        assert data["signature_url"] == "https://s3.example.com/presigned"
        assert data["captured_by_user_id"] is not None

        # Verify S3 put_object was called with PNG bytes
        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["ContentType"] == "image/png"
        body_bytes = call_kwargs["Body"]
        assert body_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    def test_replay_safety_same_idempotency_key(self, client, db_session, test_tenant):
        """Same Idempotency-Key twice → second returns original row; one row for that key."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "issued")
        invoice_id = ctx["invoice_id"]
        idem_key = str(uuid.uuid4())

        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {}
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"

        with patch("services.s3_service._s3_client", return_value=mock_s3):
            resp1 = client.post(
                f"/api/v1/invoices/{invoice_id}/signoff/test",
                json={
                    "signed_by_name": "Jane Customer",
                    "terms_acknowledged": True,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": idem_key},
            )
            resp2 = client.post(
                f"/api/v1/invoices/{invoice_id}/signoff/test",
                json={
                    "signed_by_name": "Jane Customer",
                    "terms_acknowledged": True,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": idem_key},
            )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["signoff_id"] == resp2.json()["signoff_id"]

    def test_recapture_supersedes(self, client, db_session, test_tenant):
        """Second capture (new key) → first row superseded, second active; GET returns new one."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "issued")
        invoice_id = ctx["invoice_id"]

        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {}
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"

        with patch("services.s3_service._s3_client", return_value=mock_s3):
            resp1 = client.post(
                f"/api/v1/invoices/{invoice_id}/signoff/test",
                json={
                    "signed_by_name": "First Signer",
                    "terms_acknowledged": True,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
            resp2 = client.post(
                f"/api/v1/invoices/{invoice_id}/signoff/test",
                json={
                    "signed_by_name": "Second Signer",
                    "terms_acknowledged": True,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
            # GET signoff
            get_resp = client.get(f"/api/v1/invoices/{invoice_id}/signoff/test")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["signoff_id"] != resp2.json()["signoff_id"]

        get_data = get_resp.json()
        assert get_data["signoff"]["signed_by_name"] == "Second Signer"
        assert get_data["superseded_count"] == 1

    def test_validation_bad_base64(self, client, db_session, test_tenant):
        """Bad base64 → 422."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "issued")

        mock_s3 = MagicMock()
        with patch("services.s3_service._s3_client", return_value=mock_s3):
            resp = client.post(
                f"/api/v1/invoices/{ctx['invoice_id']}/signoff/test",
                json={
                    "signed_by_name": "Test",
                    "terms_acknowledged": True,
                    "signature_png_base64": "!!!not-base64!!!",
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
        assert resp.status_code == 422

    def test_validation_non_png_bytes(self, client, db_session, test_tenant):
        """Non-PNG bytes → 422."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "issued")
        bad_bytes = base64.b64encode(b"not a png file").decode()

        mock_s3 = MagicMock()
        with patch("services.s3_service._s3_client", return_value=mock_s3):
            resp = client.post(
                f"/api/v1/invoices/{ctx['invoice_id']}/signoff/test",
                json={
                    "signed_by_name": "Test",
                    "terms_acknowledged": True,
                    "signature_png_base64": bad_bytes,
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
        assert resp.status_code == 422

    def test_validation_terms_not_acknowledged(self, client, db_session, test_tenant):
        """terms_acknowledged: false → 422 (schema rejects)."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "issued")

        mock_s3 = MagicMock()
        with patch("services.s3_service._s3_client", return_value=mock_s3):
            resp = client.post(
                f"/api/v1/invoices/{ctx['invoice_id']}/signoff/test",
                json={
                    "signed_by_name": "Test",
                    "terms_acknowledged": False,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
        assert resp.status_code == 422

    def test_validation_empty_name(self, client, db_session, test_tenant):
        """Empty signed_by_name → 422."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "issued")

        mock_s3 = MagicMock()
        with patch("services.s3_service._s3_client", return_value=mock_s3):
            resp = client.post(
                f"/api/v1/invoices/{ctx['invoice_id']}/signoff/test",
                json={
                    "signed_by_name": "",
                    "terms_acknowledged": True,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
        assert resp.status_code == 422

    def test_validation_draft_status_invoice(self, client, db_session, test_tenant):
        """Draft-status invoice → 422."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "draft")

        mock_s3 = MagicMock()
        with patch("services.s3_service._s3_client", return_value=mock_s3):
            resp = client.post(
                f"/api/v1/invoices/{ctx['invoice_id']}/signoff/test",
                json={
                    "signed_by_name": "Test",
                    "terms_acknowledged": True,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
        assert resp.status_code == 422

    def test_s3_failure_no_row_written(self, client, db_session, test_tenant):
        """S3 ClientError on put → 502 and no row written."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "issued")
        invoice_id = ctx["invoice_id"]

        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "S3 down"}},
            "PutObject",
        )

        with patch("services.s3_service._s3_client", return_value=mock_s3):
            resp = client.post(
                f"/api/v1/invoices/{invoice_id}/signoff/test",
                json={
                    "signed_by_name": "Test",
                    "terms_acknowledged": True,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )

        assert resp.status_code == 502

        # Verify no signoff row was written
        from sqlmodel import select

        from app.models.billing import InvoiceSignoff

        rows = db_session.exec(
            select(InvoiceSignoff)
            .where(InvoiceSignoff.invoice_id == uuid.UUID(invoice_id))
            .where(InvoiceSignoff.tenant_id == test_tenant.id)
        ).all()
        assert len(rows) == 0

    def test_cross_tenant_invoice_404(self, client, db_session, test_tenant, tenant_b):
        """Cross-tenant invoice → 404."""
        # Create invoice in tenant_b
        ctx = _create_test_invoice(client, db_session, tenant_b, "issued")

        mock_s3 = MagicMock()
        with patch("services.s3_service._s3_client", return_value=mock_s3):
            # The /test endpoint uses test_tenant context, so tenant_b invoice → 404
            resp = client.post(
                f"/api/v1/invoices/{ctx['invoice_id']}/signoff/test",
                json={
                    "signed_by_name": "Test",
                    "terms_acknowledged": True,
                    "signature_png_base64": _MINIMAL_PNG,
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
        assert resp.status_code == 404


class TestSignoffContext:
    """D.1 — GET /api/v1/jobs/{job_id}/signoff-context"""

    def test_context_with_issued_invoice(self, client, db_session, test_tenant):
        """Job with issued invoice returns it with terms_text fallback and active_signoff null."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "issued")

        resp = client.get(f"/api/v1/jobs/{ctx['job_id']}/signoff-context/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == ctx["job_id"]
        assert len(data["invoices"]) == 1
        inv = data["invoices"][0]
        assert inv["status"] == "issued"
        assert inv["active_signoff"] is None
        # terms_text should be the default (invoice has no terms_and_conditions)
        assert "acknowledge" in inv["terms_text"].lower()

    def test_context_draft_only_empty_list(self, client, db_session, test_tenant):
        """Job with only draft invoices → empty invoices list."""
        ctx = _create_test_invoice(client, db_session, test_tenant, "draft")

        resp = client.get(f"/api/v1/jobs/{ctx['job_id']}/signoff-context/test")
        assert resp.status_code == 200
        assert len(resp.json()["invoices"]) == 0

    def test_context_job_not_found_404(self, client, test_tenant):
        """Non-existent job → 404."""
        resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}/signoff-context/test")
        assert resp.status_code == 404
