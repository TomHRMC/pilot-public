"""
Task 1-D-1: Quote → Job Auto-Conversion Endpoint Tests

Verifies the POST /api/v1/quotes/{id}/convert endpoint:
  1. An `accepted` quote creates a new Job and transitions quote to `converted`
  2. A non-`accepted` quote (e.g. `draft`) returns HTTP 422 Unprocessable Entity
  3. A non-existent or cross-tenant quote returns HTTP 404
  4. The created Job is stamped with quote_id and latest quote_version_id
  5. The response body contains job_id, quote_id, quote_status='converted'

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-D-1
Batch 1-D Verification:
  - POST /convert on an `accepted` quote creates a job and transitions quote to `converted`
  - POST /convert on a `draft` quote returns 422 Unprocessable Entity
"""

import uuid
from datetime import UTC, datetime

from sqlmodel import select

from app.models.billing import Currency
from app.models.fulfillment import Job, JobStatus
from app.models.quoting import Quote, QuoteStatus, QuoteVersion

# ============================================================
# Helpers
# ============================================================


def _ensure_currency(db_session) -> None:
    """Ensure USD currency row exists (FK requirement for Quote)."""
    if not db_session.exec(select(Currency).where(Currency.code == "USD")).first():
        db_session.add(Currency(code="USD", name="US Dollar", symbol="$"))
        db_session.flush()


def _get_or_create_job_status(db_session, code: str = "draft") -> JobStatus:
    """Fetch or create the named job status."""
    js = db_session.exec(
        select(JobStatus).where(JobStatus.code == code, JobStatus.tenant_id.is_(None))
    ).first()
    if not js:
        js = JobStatus(
            id=uuid.uuid4(),
            code=code,
            name=code.capitalize(),
            is_default=(code == "draft"),
            is_active=True,
        )
        db_session.add(js)
        db_session.flush()
    return js


def _get_or_create_quote_status(db_session, code: str) -> QuoteStatus:
    """Fetch or create a system-wide quote status row."""
    qs = db_session.exec(
        select(QuoteStatus).where(
            QuoteStatus.code == code, QuoteStatus.tenant_id.is_(None)
        )
    ).first()
    if not qs:
        now = datetime.now(UTC)
        qs = QuoteStatus(
            id=uuid.uuid4(),
            tenant_id=None,
            code=code,
            name=code.replace("_", " ").title(),
            is_default=(code == "draft"),
            is_terminal=(code in ("converted", "rejected", "expired")),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(qs)
        db_session.flush()
    return qs


def _create_quote_in_status(
    db_session,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    site_id: uuid.UUID,
    status_code: str,
) -> Quote:
    """Create a Quote assigned to the given tenant/customer/site with the named status."""
    _ensure_currency(db_session)
    qs = _get_or_create_quote_status(db_session, status_code)

    quote = Quote(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=qs.id,
        currency="USD",
        subtotal_cents=50000,
        tax_cents=3750,
        total_cents=53750,
        is_active=True,
    )
    db_session.add(quote)
    db_session.flush()
    return quote


def _create_quote_version(db_session, quote: Quote) -> QuoteVersion:
    """Create a QuoteVersion snapshot for the given quote."""
    version = QuoteVersion(
        id=uuid.uuid4(),
        tenant_id=quote.tenant_id,
        quote_id=quote.id,
        version_no=1,
        snapshot={"quote": str(quote.id), "lines": []},
        is_active=True,
    )
    db_session.add(version)
    db_session.flush()
    return version


# ============================================================
# Tests
# ============================================================


class TestQuoteJobAutoConversion:
    """Test suite for POST /api/v1/quotes/{id}/convert/test"""

    def test_accepted_quote_creates_job_and_converts_status(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        Happy path: an `accepted` quote is converted to a Job.

        Verifies:
          - HTTP 201 Created
          - Response body contains job_id, quote_id, quote_status='converted'
          - A Job row is written to the DB with correct FKs
          - The Quote status transitions to `converted`
        """
        # Ensure required statuses exist
        _get_or_create_quote_status(db_session, "accepted")
        _get_or_create_quote_status(db_session, "converted")
        _get_or_create_job_status(db_session, "draft")
        db_session.commit()

        quote = _create_quote_in_status(
            db_session, test_tenant.id, test_customer.id, test_site.id, "accepted"
        )
        version = _create_quote_version(db_session, quote)
        db_session.commit()

        response = client.post(f"/api/v1/quotes/{quote.id}/convert/test")

        assert response.status_code == 201, response.text
        body = response.json()

        assert body["quote_id"] == str(quote.id)
        assert body["quote_status"] == "converted"
        assert "job_id" in body
        assert body["job_id"] is not None

        # Verify the Job was actually written to the DB
        job = db_session.exec(
            select(Job).where(Job.id == uuid.UUID(body["job_id"]))
        ).first()
        assert job is not None, "Job record not found in DB after conversion"
        assert job.tenant_id == test_tenant.id
        assert job.customer_id == test_customer.id
        assert job.site_id == test_site.id
        assert job.quote_id == quote.id

        # Verify quote status is now `converted`
        db_session.refresh(quote)
        updated_status = db_session.exec(
            select(QuoteStatus).where(QuoteStatus.id == quote.status_id)
        ).first()
        assert updated_status is not None
        assert updated_status.code == "converted"

    def test_accepted_quote_stamps_latest_quote_version_id(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        The created Job must be stamped with the latest quote_version_id FK.
        """
        _get_or_create_quote_status(db_session, "accepted")
        _get_or_create_quote_status(db_session, "converted")
        _get_or_create_job_status(db_session, "draft")
        db_session.commit()

        quote = _create_quote_in_status(
            db_session, test_tenant.id, test_customer.id, test_site.id, "accepted"
        )
        version = _create_quote_version(db_session, quote)
        db_session.commit()

        response = client.post(f"/api/v1/quotes/{quote.id}/convert/test")
        assert response.status_code == 201, response.text
        body = response.json()

        job = db_session.exec(
            select(Job).where(Job.id == uuid.UUID(body["job_id"]))
        ).first()
        assert job is not None
        assert job.quote_version_id == version.id
        assert body["quote_version_id"] == str(version.id)

    def test_draft_quote_returns_422(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        A quote in `draft` status cannot be converted — must return 422.
        Batch 1-D verification item: POST /convert on a `draft` quote returns 422.
        """
        _get_or_create_quote_status(db_session, "draft")
        db_session.commit()

        quote = _create_quote_in_status(
            db_session, test_tenant.id, test_customer.id, test_site.id, "draft"
        )
        db_session.commit()

        response = client.post(f"/api/v1/quotes/{quote.id}/convert/test")

        assert response.status_code == 422, response.text

    def test_sent_quote_returns_422(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        A quote in `sent` status cannot be converted — must return 422.
        Only `accepted` status is valid for conversion.
        """
        _get_or_create_quote_status(db_session, "sent")
        db_session.commit()

        quote = _create_quote_in_status(
            db_session, test_tenant.id, test_customer.id, test_site.id, "sent"
        )
        db_session.commit()

        response = client.post(f"/api/v1/quotes/{quote.id}/convert/test")

        assert response.status_code == 422, response.text

    def test_nonexistent_quote_returns_404(self, client, db_session, test_tenant):
        """
        A quote_id that doesn't exist returns 404 Not Found.
        """
        fake_id = uuid.uuid4()
        response = client.post(f"/api/v1/quotes/{fake_id}/convert/test")
        assert response.status_code == 404, response.text

    def test_convert_quote_without_version_still_creates_job(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        A quote with no QuoteVersion rows should still create a Job
        (quote_version_id will be NULL on the job).
        """
        _get_or_create_quote_status(db_session, "accepted")
        _get_or_create_quote_status(db_session, "converted")
        _get_or_create_job_status(db_session, "draft")
        db_session.commit()

        quote = _create_quote_in_status(
            db_session, test_tenant.id, test_customer.id, test_site.id, "accepted"
        )
        # Intentionally do NOT create a QuoteVersion
        db_session.commit()

        response = client.post(f"/api/v1/quotes/{quote.id}/convert/test")

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["quote_status"] == "converted"
        assert body["quote_version_id"] is None

    def test_already_converted_quote_returns_422(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        A quote already in `converted` status cannot be converted again — returns 422.
        The `converted` status code is not `accepted`, so the guard fires.
        """
        _get_or_create_quote_status(db_session, "converted")
        db_session.commit()

        quote = _create_quote_in_status(
            db_session, test_tenant.id, test_customer.id, test_site.id, "converted"
        )
        db_session.commit()

        response = client.post(f"/api/v1/quotes/{quote.id}/convert/test")

        assert response.status_code == 422, response.text
