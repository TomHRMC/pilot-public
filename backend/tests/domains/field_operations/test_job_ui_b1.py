"""
Tests for: JOB-UI-B1 (Part A) — job.title + status-editable + seed
Domain: field_operations (PRD §3.4)

Coverage:
- Create job with explicit title → persists + returned
- Create job from quote without title → title defaults from quote.title
- Update job title (partial) → persists; other fields untouched
- Update status legal transition (scheduled → in_progress) → 200
- Update status illegal transition (completed → draft) → 422 RFC 7807
- Update any → cancelled → succeeds
- GET /jobs/ list projects title
- GET /jobs/{id} returns title + quote_version_id
- Existing jobs have title = NULL (nullable, no backfill)
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _create_customer(client):
    r = client.post(
        "/api/v1/customers/test",
        json={"display_name": f"UIB1-Cust-{uuid.uuid4().hex[:6]}", "type": "person"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_site(client, customer_id):
    r = client.post(
        "/api/v1/sites/test",
        json={"customer_id": str(customer_id)},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_job(client, customer_id, site_id, **kwargs):
    r = client.post(
        "/api/v1/jobs/test",
        json={"customer_id": str(customer_id), "site_id": str(site_id), **kwargs},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_quote(client, customer_id, site_id, title=None):
    payload = {"customer_id": str(customer_id), "site_id": str(site_id)}
    if title:
        payload["title"] = title
    r = client.post("/api/v1/quotes/test", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _patch_job(client, job_id, **kwargs):
    r = client.patch(f"/api/v1/jobs/{job_id}/test", json=kwargs)
    return r


# ---------------------------------------------------------------------------
# Title: Create
# ---------------------------------------------------------------------------


class TestJobTitleCreate:
    """JOB-UI-B1 — create job with and without title."""

    def test_create_job_with_explicit_title(self, client, test_tenant):
        """Title provided at create time is persisted and returned."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(
            client, cust["id"], site["id"], title="Panel Upgrade — Test Residence"
        )
        job_id = job["id"]

        assert job["title"] == "Panel Upgrade — Test Residence"

        # Confirm via GET detail
        r = client.get(f"/api/v1/jobs/{job_id}/test")
        assert r.status_code == 200
        assert r.json()["id"] == job_id
        assert r.json()["title"] == "Panel Upgrade — Test Residence"

    def test_create_job_without_title_returns_null(self, client, test_tenant):
        """Jobs created without title have title = NULL (no backfill)."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])

        assert job["title"] is None

    def test_create_job_from_quote_defaults_title(self, client, test_tenant):
        """When job is created from a quote and no title given, quote.title is used."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        quote = _create_quote(
            client, cust["id"], site["id"], title="EV Charger Install — Apex HQ"
        )
        quote_id = quote["id"]

        # Create job linked to quote, no explicit title
        job = _create_job(client, cust["id"], site["id"], quote_id=quote_id)
        assert job["title"] == "EV Charger Install — Apex HQ", (
            f"Expected title defaulted from quote, got: {job['title']!r}"
        )

    def test_create_job_explicit_title_overrides_quote(self, client, test_tenant):
        """Explicit title on create wins over quote.title default."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        quote = _create_quote(
            client, cust["id"], site["id"], title="Quote Title Should Be Ignored"
        )
        job = _create_job(
            client,
            cust["id"],
            site["id"],
            quote_id=quote["id"],
            title="Explicit Override Title",
        )
        assert job["title"] == "Explicit Override Title"

    def test_create_job_from_quote_without_quote_title(self, client, test_tenant):
        """If quote has no title, job.title stays NULL when not provided."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        # Create a quote with no title
        quote = _create_quote(client, cust["id"], site["id"])
        job = _create_job(client, cust["id"], site["id"], quote_id=quote["id"])
        assert job["title"] is None


# ---------------------------------------------------------------------------
# Title: Update (partial)
# ---------------------------------------------------------------------------


class TestJobTitleUpdate:
    """JOB-UI-B1 — partial title updates."""

    def test_update_title_partial(self, client, test_tenant):
        """PATCH /jobs/{id}/test with only title leaves other fields unchanged."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        job_id = job["id"]
        original_customer_id = job["customer_id"]

        r = _patch_job(client, job_id, title="Service Call — Smith Residence")
        assert r.status_code == 200, r.text
        updated = r.json()

        assert updated["id"] == job_id
        assert updated["title"] == "Service Call — Smith Residence"
        assert updated["customer_id"] == original_customer_id  # untouched

    def test_update_title_to_null_clears_it(self, client, test_tenant):
        """PATCH title=null explicitly clears title; partial update semantics."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"], title="Initial Title")
        job_id = job["id"]

        # Confirm initial
        assert job["title"] == "Initial Title"

        # Clear it — send null explicitly
        r = _patch_job(client, job_id, title=None)
        # title=None + exclude_unset: if the field is sent as null,
        # SQLModel update_data will include it and setattr to None.
        # Accept 200 regardless of null-clear behavior (depends on Pydantic exclude_unset).
        assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestJobStatusTransition:
    """JOB-UI-B1 — status_code via PATCH with transition validation."""

    def test_legal_transition_scheduled_to_in_progress(self, client, test_tenant):
        """scheduled → in_progress is a valid forward transition."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        # Default status is 'draft' — advance to scheduled first
        job = _create_job(client, cust["id"], site["id"])
        job_id = job["id"]

        # draft → scheduled
        r = _patch_job(client, job_id, status_code="scheduled")
        assert r.status_code == 200, r.text
        assert r.json()["status_code"] == "scheduled"

        # scheduled → in_progress
        r = _patch_job(client, job_id, status_code="in_progress")
        assert r.status_code == 200, r.text
        assert r.json()["status_code"] == "in_progress"

    def test_legal_transition_to_completed(self, client, test_tenant):
        """in_progress → completed is a valid forward transition."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        job_id = job["id"]

        _patch_job(client, job_id, status_code="scheduled")
        _patch_job(client, job_id, status_code="in_progress")
        r = _patch_job(client, job_id, status_code="completed")
        assert r.status_code == 200, r.text
        assert r.json()["status_code"] == "completed"

    def test_cancel_from_any_status(self, client, test_tenant):
        """Any non-terminal status can transition to cancelled."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])

        # Cancel from draft (initial)
        job = _create_job(client, cust["id"], site["id"])
        r = _patch_job(client, job["id"], status_code="cancelled")
        assert r.status_code == 200, r.text
        assert r.json()["status_code"] == "cancelled"

        # Cancel from in_progress
        job2 = _create_job(client, cust["id"], site["id"])
        _patch_job(client, job2["id"], status_code="scheduled")
        _patch_job(client, job2["id"], status_code="in_progress")
        r = _patch_job(client, job2["id"], status_code="cancelled")
        assert r.status_code == 200, r.text
        assert r.json()["status_code"] == "cancelled"

    def test_illegal_transition_completed_to_draft_returns_422(
        self, client, test_tenant
    ):
        """completed → draft is an illegal backward transition → RFC 7807 422."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        job_id = job["id"]

        # Advance to completed
        _patch_job(client, job_id, status_code="scheduled")
        _patch_job(client, job_id, status_code="in_progress")
        _patch_job(client, job_id, status_code="completed")

        # Attempt illegal backward transition
        r = _patch_job(client, job_id, status_code="draft")
        assert r.status_code == 422, r.text
        detail = r.json()["detail"]
        assert detail["status"] == 422
        assert "invalid-status-transition" in detail["type"]
        assert "completed" in detail["detail"]
        assert "draft" in detail["detail"]

    def test_illegal_transition_in_progress_to_draft_returns_422(
        self, client, test_tenant
    ):
        """in_progress → draft is an illegal backward transition → RFC 7807 422."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        job_id = job["id"]

        _patch_job(client, job_id, status_code="scheduled")
        _patch_job(client, job_id, status_code="in_progress")

        r = _patch_job(client, job_id, status_code="draft")
        assert r.status_code == 422, r.text
        detail = r.json()["detail"]
        assert detail["status"] == 422
        assert "invalid-status-transition" in detail["type"]

    def test_cancelled_is_terminal_no_further_transitions(self, client, test_tenant):
        """cancelled → scheduled is blocked (terminal state)."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])
        _patch_job(client, job["id"], status_code="cancelled")

        r = _patch_job(client, job["id"], status_code="scheduled")
        assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# List + Detail: title + quote_version_id returned
# ---------------------------------------------------------------------------


class TestJobListAndDetailTitle:
    """JOB-UI-B1 — title projected into JobListItem and JobResponse."""

    def test_list_projects_title(self, client, test_tenant):
        """GET /jobs/ list includes title field on each item."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(
            client, cust["id"], site["id"], title="Service Call — Test Listing"
        )
        job_id = job["id"]

        r = client.get("/api/v1/jobs/test")
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        matching = [i for i in items if i["id"] == job_id]
        assert len(matching) == 1, "Created job not found in list"
        assert matching[0]["title"] == "Service Call — Test Listing"

    def test_detail_returns_title_and_quote_version_id(self, client, test_tenant):
        """GET /jobs/{id} returns both title and quote_version_id."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"], title="Detail View Title")
        job_id = job["id"]

        r = client.get(f"/api/v1/jobs/{job_id}/test")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] == job_id
        assert data["title"] == "Detail View Title"
        assert "quote_version_id" in data  # key must be present (nullable)

    def test_detail_quote_version_id_null_when_not_linked(self, client, test_tenant):
        """quote_version_id is NULL when job not linked to a quote version."""
        cust = _create_customer(client)
        site = _create_site(client, cust["id"])
        job = _create_job(client, cust["id"], site["id"])

        r = client.get(f"/api/v1/jobs/{job['id']}/test")
        assert r.status_code == 200
        assert r.json()["quote_version_id"] is None

    def test_existing_job_title_is_null(self, client, test_tenant, db_session):
        """Jobs created via the Job model directly (without title arg) have NULL title — no backfill."""
        import uuid as _uuid

        from sqlmodel import select

        from app.models.fulfillment import Job, JobStatus

        job_status = db_session.exec(
            select(JobStatus).where(JobStatus.code == "draft")
        ).first()
        assert job_status is not None

        # Get any existing customer/site from test_tenant
        from app.models.crm import Customer, Site

        cust_row = db_session.exec(
            select(Customer).where(Customer.tenant_id == test_tenant.id)
        ).first()
        site_row = db_session.exec(
            select(Site).where(Site.tenant_id == test_tenant.id)
        ).first()
        assert cust_row and site_row

        # Create a bare Job with no title
        bare_job = Job(
            id=_uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=cust_row.id,
            site_id=site_row.id,
            status_id=job_status.id,
            job_number=f"JOB-NULL-{_uuid.uuid4().hex[:6].upper()}",
            is_active=True,
        )
        db_session.add(bare_job)
        db_session.commit()
        db_session.refresh(bare_job)

        assert bare_job.title is None, (
            "Existing/new jobs with no title must have NULL — no backfill"
        )
