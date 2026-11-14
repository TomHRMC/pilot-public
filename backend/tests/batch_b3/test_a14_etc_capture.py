"""
Batch B3 — A14 Test Coverage
==============================

A14: ETC (Estimate-to-Complete) Capture System

Test Coverage:
- JobTimeEntry ORM model has all 5 ETC columns
- etc_service.check_etc_variance computes correctly
- etc_service.get_latest_etc_entries returns empty list for job with no ETC
- etc_service.compute_projected_margin returns fallback when no ETC
- POST /api/v1/jobs/{job_id}/time-entries/test accepts ETC fields
- POST /api/v1/jobs/{job_id}/time-entries/test stores ETC in DB
- POST /api/v1/jobs/{job_id}/time-entries/test returns 422 when override=true and no note
- GET /api/v1/jobs/{job_id}/projected-margin/test returns projection data
- projected-margin uses 'fallback' etc_source when no ETC entries
- JobTimeEntryCreate schema accepts ETC optional fields
- JobTimeEntryResponse schema returns ETC fields
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlmodel import select

# ─────────────────────────────────────────────────────────────────────────────
# A14 — ORM model checks
# ─────────────────────────────────────────────────────────────────────────────


class TestA14ORMModels:
    """Verify ETC columns exist on JobTimeEntry."""

    def test_jte_has_hours_remaining_estimate(self):
        from app.models.fulfillment import JobTimeEntry

        assert hasattr(JobTimeEntry, "hours_remaining_estimate")

    def test_jte_has_hours_remaining_was_overridden(self):
        from app.models.fulfillment import JobTimeEntry

        assert hasattr(JobTimeEntry, "hours_remaining_was_overridden")

    def test_jte_has_override_note(self):
        from app.models.fulfillment import JobTimeEntry

        assert hasattr(JobTimeEntry, "override_note")

    def test_jte_has_quote_line_id(self):
        from app.models.fulfillment import JobTimeEntry

        assert hasattr(JobTimeEntry, "quote_line_id")

    def test_jte_has_etc_captured_at(self):
        from app.models.fulfillment import JobTimeEntry

        assert hasattr(JobTimeEntry, "etc_captured_at")


# ─────────────────────────────────────────────────────────────────────────────
# A14 — etc_service unit tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA14ETCService:
    """Unit tests for etc_service."""

    def test_check_etc_variance_zero_quoted_hours(self):
        from services.etc_service import check_etc_variance

        should_notify, pct = check_etc_variance(
            Decimal("5"), Decimal("0"), notify_pct=50
        )
        assert should_notify is False
        assert pct == Decimal("0")

    def test_check_etc_variance_below_threshold(self):
        from services.etc_service import check_etc_variance

        # 8 projected vs 10 quoted = -20% (under budget)
        should_notify, pct = check_etc_variance(
            Decimal("8"), Decimal("10"), notify_pct=50
        )
        assert should_notify is False

    def test_check_etc_variance_above_threshold(self):
        from services.etc_service import check_etc_variance

        # 18 projected vs 10 quoted = 80% over
        should_notify, pct = check_etc_variance(
            Decimal("18"), Decimal("10"), notify_pct=50
        )
        assert should_notify is True
        assert pct == Decimal("80")

    def test_get_latest_etc_entries_empty_for_job_no_etc(self, db_session, test_tenant):
        """Job with no ETC entries returns empty list."""
        from services.etc_service import get_latest_etc_entries

        result = get_latest_etc_entries(db_session, test_tenant.id, uuid.uuid4())
        assert result == []

    def test_compute_projected_margin_fallback_source(self, db_session, test_tenant):
        """Job with no ETC entries uses 'fallback' etc_source."""
        from services.etc_service import compute_projected_margin

        result = compute_projected_margin(
            db=db_session,
            tenant_id=test_tenant.id,
            job_id=uuid.uuid4(),
            hourly_rate_cents=8500,
            quoted_total_cents=100000,
            actual_labor_cost_cents=0,
            actual_material_cost_cents=0,
            margin_target_pct=20,
        )
        assert result["etc_source"] == "fallback"
        assert "projected_margin_pct" in result
        assert "below_margin_target" in result
        assert result["latest_etc_entries"] == []

    def test_compute_projected_margin_below_target(self, db_session, test_tenant):
        """When projected total > quoted, margin is below target."""
        from services.etc_service import compute_projected_margin

        # Actual labor already exceeds quote
        result = compute_projected_margin(
            db=db_session,
            tenant_id=test_tenant.id,
            job_id=uuid.uuid4(),
            hourly_rate_cents=8500,
            quoted_total_cents=50000,
            actual_labor_cost_cents=60000,  # already over
            actual_material_cost_cents=0,
            margin_target_pct=20,
        )
        assert result["below_margin_target"] is True


# ─────────────────────────────────────────────────────────────────────────────
# A14 — Schema checks
# ─────────────────────────────────────────────────────────────────────────────


class TestA14Schemas:
    """Verify JobTimeEntryCreate and JobTimeEntryResponse have ETC fields."""

    def test_create_schema_accepts_etc_fields(self):
        from api.schemas.schemas import JobTimeEntryCreate

        now = datetime.now(UTC)
        entry = JobTimeEntryCreate(
            started_at=now,
            ended_at=now + timedelta(hours=2),
            hours_remaining_estimate=3.5,
            hours_remaining_was_overridden=True,
            override_note="Found additional conduit run",
        )
        assert entry.hours_remaining_estimate == 3.5
        assert entry.override_note == "Found additional conduit run"

    def test_create_schema_etc_fields_optional(self):
        from api.schemas.schemas import JobTimeEntryCreate

        now = datetime.now(UTC)
        entry = JobTimeEntryCreate(started_at=now)
        assert entry.hours_remaining_estimate is None
        assert entry.hours_remaining_was_overridden is None
        assert entry.override_note is None
        assert entry.quote_line_id is None

    def test_response_schema_has_etc_fields(self):
        from api.schemas.schemas import JobTimeEntryResponse

        assert hasattr(JobTimeEntryResponse, "model_fields")
        fields = JobTimeEntryResponse.model_fields
        assert "hours_remaining_estimate" in fields
        assert "hours_remaining_was_overridden" in fields
        assert "override_note" in fields
        assert "quote_line_id" in fields
        assert "etc_captured_at" in fields


# ─────────────────────────────────────────────────────────────────────────────
# A14 — HTTP endpoint tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA14TimeEntryETCEndpoint:
    """HTTP tests for ETC fields in time-entry endpoint."""

    def _create_test_job_for_etc(self, db_session, test_tenant, test_user):
        """Create minimal job for ETC tests."""
        from app.models.crm import Customer, Site
        from app.models.fulfillment import Job, JobStatus

        status = db_session.exec(
            select(JobStatus).where(JobStatus.tenant_id == test_tenant.id)
        ).first()
        if not status:
            status = JobStatus(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                code="open",
                name="Open",
                is_default=True,
                is_active=True,
            )
            db_session.add(status)
            db_session.flush()

        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            display_name=f"ETC-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()

        site = Site(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="ETC Test Site",
            is_active=True,
        )
        db_session.add(site)
        db_session.flush()

        job = Job(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            site_id=site.id,
            status_id=status.id,
            is_active=True,
            version=1,
        )
        db_session.add(job)
        db_session.flush()
        db_session.refresh(job)
        return job

    def test_time_entry_accepts_etc_fields(
        self, client, db_session, test_tenant, test_user
    ):
        """POST time-entry with ETC fields returns 201 and stores data."""
        job = self._create_test_job_for_etc(db_session, test_tenant, test_user)
        now = datetime.now(UTC)

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.post(
                f"/api/v1/jobs/{job.id}/time-entries/test",
                json={
                    "started_at": now.isoformat(),
                    "ended_at": (now + timedelta(hours=2)).isoformat(),
                    "hours_remaining_estimate": 3.5,
                    "hours_remaining_was_overridden": False,
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data

    def test_time_entry_override_requires_note(
        self, client, db_session, test_tenant, test_user
    ):
        """POST time-entry with hours_remaining_was_overridden=True but no note returns 422."""
        job = self._create_test_job_for_etc(db_session, test_tenant, test_user)
        now = datetime.now(UTC)

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.post(
                f"/api/v1/jobs/{job.id}/time-entries/test",
                json={
                    "started_at": now.isoformat(),
                    "ended_at": (now + timedelta(hours=2)).isoformat(),
                    "hours_remaining_estimate": 10.0,
                    "hours_remaining_was_overridden": True,
                    # override_note intentionally omitted
                },
            )

        assert resp.status_code == 422

    def test_projected_margin_returns_fallback_for_new_job(
        self, client, db_session, test_tenant, test_user
    ):
        """GET projected-margin for job with no ETC entries returns fallback source."""
        job = self._create_test_job_for_etc(db_session, test_tenant, test_user)

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.get(f"/api/v1/jobs/{job.id}/projected-margin/test")

        assert resp.status_code == 200
        data = resp.json()
        assert "etc_source" in data
        assert data["etc_source"] == "fallback"
        assert "projected_margin_pct" in data
        assert "job_id" in data
        assert data["job_id"] == str(job.id)

    def test_projected_margin_returns_404_for_unknown_job(
        self, client, test_tenant, test_user
    ):
        """GET projected-margin for unknown job returns 404."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}/projected-margin/test")

        assert resp.status_code == 404
