"""
TP-B6 — Labor Rates, Job Notes/LOTO & Scheduling History — Test Endpoints

Coverage:
  1. GET  /api/v1/settings/test                                 → get_active_labor_rates_test
  2. POST /api/v1/settings/test                                 → create_labor_rate_test
  3. GET  /api/v1/settings/{skill_level_code}/history/test      → get_labor_rate_history_test
  4. GET  /api/v1/jobs/{job_id}/notes/test                      → get_job_notes_test
  5. PUT  /api/v1/jobs/{job_id}/notes/test                      → upsert_job_notes_test
  6. POST /api/v1/jobs/{job_id}/loto-confirmations/test         → create_loto_confirmation_test
  7. GET  /api/v1/jobs/{job_id}/loto-confirmations/test         → list_loto_confirmations_test
  8. GET  /api/v1/scheduling/jobs/{job_id}/history/test         → get_job_schedule_history_test

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - 404 for unknown job IDs
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import status
from sqlmodel import select

from app.models.crm import Customer, Site
from app.models.fulfillment import Job, JobStatus
from core.config import settings

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

LABOR_BASE = "/api/v1/settings"
JOBS_BASE = "/api/v1/jobs"
SCHED_BASE = "/api/v1/scheduling"


# ==================== FIXTURES ====================


@pytest.fixture
def b6_customer(db_session, test_tenant):
    c = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        type="person",
        display_name=f"TP-B6 Customer {uuid.uuid4().hex[:6]}",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def b6_site(db_session, test_tenant, b6_customer):
    s = Site(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=b6_customer.id,
        address_line_1="100 B6 Blvd",
        city="Testville",
        state="TX",
        postal_code="75005",
        country="US",
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def b6_job(db_session, test_tenant, b6_customer, b6_site):
    """A minimal job for job notes and LOTO tests."""
    job_status = db_session.exec(
        select(JobStatus).where(JobStatus.tenant_id == test_tenant.id)
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
        customer_id=b6_customer.id,
        site_id=b6_site.id,
        status_id=job_status.id,
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# ==================== SECURITY GUARD TESTS ====================


class TestTpB6SecurityGuards:
    def test_labor_rates_list_blocked_when_disabled(self, client):
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{LABOR_BASE}/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_job_notes_blocked_in_production(self, client, b6_job):
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.get(f"{JOBS_BASE}/{b6_job.id}/notes/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_loto_list_blocked_when_disabled(self, client, b6_job):
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{JOBS_BASE}/{b6_job.id}/loto-confirmations/test"
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== LABOR RATES /test ====================


class TestTpB6LaborRates:
    def test_get_active_labor_rates_returns_200(self, client):
        """GET /settings/test returns active labor rates (may be empty)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{LABOR_BASE}/test")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_create_labor_rate_returns_201(self, client):
        """POST /settings/test creates a new labor rate."""
        payload = {
            "skill_level_code": f"tp_b6_{uuid.uuid4().hex[:4]}",
            "hourly_rate_cents": 9500,
            "burden_pct": 0.25,
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{LABOR_BASE}/test", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["skill_level_code"] == payload["skill_level_code"]
        assert data["hourly_rate_cents"] == 9500

    def test_create_labor_rate_validates_rate(self, client):
        """POST /settings/test returns 422 if hourly_rate_cents <= 0."""
        payload = {
            "skill_level_code": "tp_b6_invalid",
            "hourly_rate_cents": 0,
            "burden_pct": 0.25,
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(f"{LABOR_BASE}/test", json=payload)
        assert response.status_code == 422

    def test_get_labor_rate_history_returns_list(self, client):
        """GET /settings/{code}/history/test returns history list."""
        skill_code = f"tp_b6_hist_{uuid.uuid4().hex[:4]}"
        # Create a rate first
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                client.post(
                    f"{LABOR_BASE}/test",
                    json={
                        "skill_level_code": skill_code,
                        "hourly_rate_cents": 8000,
                        "burden_pct": 0.2,
                    },
                )
                response = client.get(f"{LABOR_BASE}/{skill_code}/history/test")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)


# ==================== JOB NOTES /test ====================


class TestTpB6JobNotes:
    def test_get_job_notes_204_when_empty(self, client, b6_job):
        """GET /jobs/{job_id}/notes/test returns 204 when no notes exist."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{JOBS_BASE}/{b6_job.id}/notes/test")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_upsert_job_notes_creates_notes(self, client, b6_job):
        """PUT /jobs/{job_id}/notes/test creates or updates notes."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.put(
                    f"{JOBS_BASE}/{b6_job.id}/notes/test",
                    json={"notes": "TP-B6 test notes content"},
                )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["notes"] == "TP-B6 test notes content"

    def test_get_job_notes_returns_created_notes(self, client, b6_job):
        """GET /jobs/{job_id}/notes/test returns notes after upsert."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                client.put(
                    f"{JOBS_BASE}/{b6_job.id}/notes/test",
                    json={"notes": "Notes for get test"},
                )
                response = client.get(f"{JOBS_BASE}/{b6_job.id}/notes/test")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["notes"] == "Notes for get test"

    def test_job_notes_404_for_unknown_job(self, client):
        """Returns 404 for unknown job."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{JOBS_BASE}/{uuid.uuid4()}/notes/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== LOTO CONFIRMATIONS /test ====================


class TestTpB6LotoConfirmations:
    def test_list_loto_empty_for_new_job(self, client, b6_job):
        """GET /jobs/{job_id}/loto-confirmations/test returns empty list."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{JOBS_BASE}/{b6_job.id}/loto-confirmations/test"
                )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_create_loto_confirmation_returns_201(self, client, b6_job):
        """POST /jobs/{job_id}/loto-confirmations/test creates a LOTO record."""
        payload = {
            "confirmed_at": datetime.now(UTC).isoformat(),
            "idempotency_uuid": str(uuid.uuid4()),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{JOBS_BASE}/{b6_job.id}/loto-confirmations/test",
                    json=payload,
                )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["job_id"] == str(b6_job.id)
        assert data["user_id"] == str(TEST_USER_ID)

    def test_create_loto_idempotent_returns_200(self, client, b6_job):
        """Submitting same LOTO (user_id, job_id, confirmed_at) twice returns 200."""
        confirmed_at = datetime.now(UTC).isoformat()
        idempotency_uuid = str(uuid.uuid4())
        payload = {"confirmed_at": confirmed_at, "idempotency_uuid": idempotency_uuid}
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                resp1 = client.post(
                    f"{JOBS_BASE}/{b6_job.id}/loto-confirmations/test", json=payload
                )
                resp2 = client.post(
                    f"{JOBS_BASE}/{b6_job.id}/loto-confirmations/test", json=payload
                )
        assert resp1.status_code == status.HTTP_201_CREATED
        assert resp2.status_code == status.HTTP_200_OK

    def test_list_loto_returns_created_record(self, client, b6_job):
        """After creating, list shows the record."""
        payload = {
            "confirmed_at": datetime.now(UTC).isoformat(),
            "idempotency_uuid": str(uuid.uuid4()),
        }
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                client.post(
                    f"{JOBS_BASE}/{b6_job.id}/loto-confirmations/test", json=payload
                )
                list_resp = client.get(
                    f"{JOBS_BASE}/{b6_job.id}/loto-confirmations/test"
                )
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.json()) >= 1

    def test_loto_404_for_unknown_job(self, client):
        """Returns 404 for unknown job ID."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(
                    f"{JOBS_BASE}/{uuid.uuid4()}/loto-confirmations/test"
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================== SCHEDULE HISTORY /test ====================


class TestTpB6ScheduleHistory:
    def test_get_schedule_history_returns_200(self, client, b6_job):
        """GET /scheduling/jobs/{job_id}/history/test returns schedule history."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{SCHED_BASE}/jobs/{b6_job.id}/history/test")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job_id"] == str(b6_job.id)
        assert "entries" in data
        assert isinstance(data["entries"], list)

    def test_get_schedule_history_404_for_unknown_job(self, client):
        """Returns 404 for unknown job."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{SCHED_BASE}/jobs/{uuid.uuid4()}/history/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_schedule_history_blocked_when_disabled(self, client, b6_job):
        """Returns 403 when TEST_ENDPOINT_ENABLED=false."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{SCHED_BASE}/jobs/{b6_job.id}/history/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN
