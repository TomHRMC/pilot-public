"""
MOB-B1-BE: Job List API Enhancements — Test Suite

Coverage:
  TestJobListTechIdFilter       — ?tech_id= filter returns only assigned jobs
  TestJobListScheduledDate      — ?scheduled_date= filter returns only jobs on that date
  TestJobListCombinedFilters    — ?tech_id= + ?scheduled_date= combined
  TestJobListResponseFields     — status_code and customer_name present in response
  TestJobListMultiTenancy       — customer JOIN does not expose cross-tenant names
  TestJobListPagination         — skip/limit still work alongside new params

Endpoint under test:
  GET /api/v1/jobs/test   (no-auth test endpoint, test tenant)

Note on user_id:
  job_tech_assignment.user_id has a FK to user.id (RESTRICT).
  Only _TEST_USER_ID (00000000-0000-0000-0000-000000000002) is guaranteed
  to exist in the seeded database — never use random UUIDs as user_id.

Note on scheduled_start_at:
  The POST /api/v1/jobs/test endpoint has a Celery profitability task side-effect
  that can cause 500s when scheduled_start_at is supplied in certain environments.
  For tests that require a controlled scheduled_start_at value, Job rows are inserted
  directly via db_session. The GET /api/v1/jobs/test endpoint is still the system
  under test for all filter assertions.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

from app.models.fulfillment import Job, JobStatus
from app.models.scheduling import JobTechAssignment

pytestmark = [pytest.mark.domain_field_operations, pytest.mark.unit]

JOBS_BASE = "/api/v1/jobs"
_TEST_USER_ID = "00000000-0000-0000-0000-000000000002"
_TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_customer_and_site(client) -> tuple[str, str]:
    """Create a customer + site via test endpoints, return (customer_id, site_id)."""
    suffix = uuid.uuid4().hex[:6]
    cust_resp = client.post(
        "/api/v1/customers/test",
        json={"display_name": f"MOB-B1 Customer {suffix}", "type": "person"},
    )
    assert cust_resp.status_code == 201, cust_resp.text
    customer_id = cust_resp.json()["id"]

    site_resp = client.post(
        "/api/v1/sites/test",
        json={"customer_id": customer_id},
    )
    assert site_resp.status_code == 201, site_resp.text
    site_id = site_resp.json()["id"]

    return customer_id, site_id


def _create_job(client, customer_id: str, site_id: str) -> str:
    """Create a job via test endpoint (no scheduled_start_at) and return its id."""
    resp = client.post(
        f"{JOBS_BASE}/test",
        json={"customer_id": customer_id, "site_id": site_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_job_direct(
    db_session,
    customer_id: str,
    site_id: str,
    tenant_id: str,
    scheduled_start_at: datetime | None = None,
) -> str:
    """
    Insert a Job row directly via ORM — used when we need to control
    scheduled_start_at (HTTP endpoint has Celery side-effects that can 500
    in certain environments when a date is provided).

    DB constraint ck_job_schedule_range requires:
      - both NULL, OR
      - both NOT NULL with scheduled_end_at > scheduled_start_at
    When scheduled_start_at is provided, scheduled_end_at is auto-set to +4 hours.

    The GET /api/v1/jobs/test endpoint is still the system under test.
    """
    # Find default job status (prefer system-wide NULL tenant_id rows)
    status = db_session.exec(
        select(JobStatus)
        .where(JobStatus.is_default == True)
        .order_by(JobStatus.tenant_id.is_(None).desc())
    ).first()
    assert status is not None, "No default job_status found — check seed data"

    # DB constraint: if start is set, end must also be set and > start
    scheduled_end_at = (
        (scheduled_start_at + timedelta(hours=4)) if scheduled_start_at else None
    )

    job = Job(
        tenant_id=uuid.UUID(tenant_id),
        customer_id=uuid.UUID(customer_id),
        site_id=uuid.UUID(site_id),
        status_id=status.id,
        scheduled_start_at=scheduled_start_at,
        scheduled_end_at=scheduled_end_at,
        actual_labor_cost_cents=0,
        actual_material_cost_cents=0,
        actual_profit_cents=0,
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return str(job.id)


def _assign_tech(
    db_session, job_id: str, user_id: str, tenant_id: str
) -> JobTechAssignment:
    """Directly insert a job_tech_assignment row (no test endpoint exists)."""
    assignment = JobTechAssignment(
        tenant_id=uuid.UUID(tenant_id),
        job_id=uuid.UUID(job_id),
        user_id=uuid.UUID(user_id),
        assigned_by_user_id=uuid.UUID(user_id),
        role="primary",
        ordinal=1,
        assigned_at=datetime.now(UTC),
        is_active=True,
    )
    db_session.add(assignment)
    db_session.commit()
    db_session.refresh(assignment)
    return assignment


# ---------------------------------------------------------------------------
# Tests: tech_id filter
# ---------------------------------------------------------------------------


class TestJobListTechIdFilter:
    def test_tech_id_returns_only_assigned_jobs(
        self, client, db_session, test_tenant, test_user
    ):
        """?tech_id= returns jobs assigned to that tech, excludes unassigned jobs."""
        cid, sid = _create_customer_and_site(client)

        # Create two jobs — only one will be assigned to the test tech
        assigned_job_id = _create_job(client, cid, sid)
        _unassigned_job_id = _create_job(client, cid, sid)

        _assign_tech(db_session, assigned_job_id, _TEST_USER_ID, _TEST_TENANT_ID)

        resp = client.get(f"{JOBS_BASE}/test?tech_id={_TEST_USER_ID}")
        assert resp.status_code == 200, resp.text
        data = resp.json()["items"]  # UI-FIX-1C: paginated response

        returned_ids = {j["id"] for j in data}
        assert assigned_job_id in returned_ids, "Assigned job must be in response"
        assert _unassigned_job_id not in returned_ids, (
            "Unassigned job must be excluded from tech_id-filtered response"
        )

    def test_tech_id_with_no_assignments_returns_empty(
        self, client, db_session, test_tenant, test_user
    ):
        """?tech_id= with a UUID that has no assignments returns empty list."""
        random_user_id = str(uuid.uuid4())
        resp = client.get(f"{JOBS_BASE}/test?tech_id={random_user_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Random UUID has no assignments → inner join produces 0 rows
        assert len(data["items"]) == 0, (  # UI-FIX-1C: paginated response
            f"Expected empty list for unassigned user UUID, got {len(data['items'])} rows"
        )


# ---------------------------------------------------------------------------
# Tests: scheduled_date filter
# ---------------------------------------------------------------------------


class TestJobListScheduledDate:
    def test_scheduled_date_returns_only_matching_jobs(
        self, client, db_session, test_tenant, test_user
    ):
        """?scheduled_date= returns jobs with scheduled_start_at on that date."""
        cid, sid = _create_customer_and_site(client)

        target_date = (datetime.now(UTC) + timedelta(days=30)).date()
        target_dt = (datetime.now(UTC) + timedelta(days=30)).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        other_dt = (datetime.now(UTC) + timedelta(days=31)).replace(
            hour=8, minute=0, second=0, microsecond=0
        )

        # Use direct ORM insertion to control scheduled_start_at precisely
        target_job_id = _create_job_direct(
            db_session, cid, sid, _TEST_TENANT_ID, scheduled_start_at=target_dt
        )
        other_job_id = _create_job_direct(
            db_session, cid, sid, _TEST_TENANT_ID, scheduled_start_at=other_dt
        )

        resp = client.get(f"{JOBS_BASE}/test?scheduled_date={target_date}")
        assert resp.status_code == 200, resp.text
        data = resp.json()["items"]  # UI-FIX-1C: paginated response

        returned_ids = {j["id"] for j in data}
        assert target_job_id in returned_ids, (
            f"Job on target date {target_date} must be in response"
        )
        assert other_job_id not in returned_ids, (
            "Job on different date must be excluded from scheduled_date-filtered response"
        )

    def test_scheduled_date_excludes_null_start(
        self, client, db_session, test_tenant, test_user
    ):
        """?scheduled_date= excludes jobs with null scheduled_start_at."""
        cid, sid = _create_customer_and_site(client)

        # Job with no scheduled_start_at (inserted directly for consistency)
        null_date_job_id = _create_job_direct(
            db_session, cid, sid, _TEST_TENANT_ID, scheduled_start_at=None
        )

        # Query a far-future date that no seeded data will match
        target_date = (datetime.now(UTC) + timedelta(days=180)).date()
        resp = client.get(f"{JOBS_BASE}/test?scheduled_date={target_date}")
        assert resp.status_code == 200, resp.text
        data = resp.json()["items"]  # UI-FIX-1C: paginated response

        returned_ids = {j["id"] for j in data}
        assert null_date_job_id not in returned_ids, (
            "Job with null scheduled_start_at must be excluded from date-filtered response"
        )


# ---------------------------------------------------------------------------
# Tests: combined filters
# ---------------------------------------------------------------------------


class TestJobListCombinedFilters:
    def test_tech_id_and_scheduled_date_both_applied(
        self, client, db_session, test_tenant, test_user
    ):
        """Both ?tech_id= and ?scheduled_date= filters are applied together."""
        cid, sid = _create_customer_and_site(client)

        target_date = (datetime.now(UTC) + timedelta(days=45)).date()
        target_dt = (datetime.now(UTC) + timedelta(days=45)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        other_dt = (datetime.now(UTC) + timedelta(days=46)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

        # Job matching both filters (assigned + correct date)
        match_job_id = _create_job_direct(
            db_session, cid, sid, _TEST_TENANT_ID, scheduled_start_at=target_dt
        )
        _assign_tech(db_session, match_job_id, _TEST_USER_ID, _TEST_TENANT_ID)

        # Job assigned to tech but wrong date — must be excluded
        wrong_date_job_id = _create_job_direct(
            db_session, cid, sid, _TEST_TENANT_ID, scheduled_start_at=other_dt
        )
        _assign_tech(db_session, wrong_date_job_id, _TEST_USER_ID, _TEST_TENANT_ID)

        # Job on right date but not assigned — must be excluded
        unassigned_job_id = _create_job_direct(
            db_session, cid, sid, _TEST_TENANT_ID, scheduled_start_at=target_dt
        )

        resp = client.get(
            f"{JOBS_BASE}/test?tech_id={_TEST_USER_ID}&scheduled_date={target_date}"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["items"]  # UI-FIX-1C: paginated response

        returned_ids = {j["id"] for j in data}
        assert match_job_id in returned_ids, (
            "Job matching both tech_id and scheduled_date must appear"
        )
        assert wrong_date_job_id not in returned_ids, (
            "Job with wrong date must be excluded even if assigned to tech"
        )
        assert unassigned_job_id not in returned_ids, (
            "Job on correct date but unassigned must be excluded"
        )


# ---------------------------------------------------------------------------
# Tests: response shape (status_code, customer_name)
# ---------------------------------------------------------------------------


class TestJobListResponseFields:
    def test_status_code_present_in_response(self, client, test_tenant, test_user):
        """Response includes status_code string from job_status JOIN."""
        cid, sid = _create_customer_and_site(client)
        job_id = _create_job(client, cid, sid)

        resp = client.get(f"{JOBS_BASE}/test?limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()["items"]  # UI-FIX-1C: paginated response

        # Find our specific job by ID
        job_data = next((j for j in data if j["id"] == job_id), None)
        assert job_data is not None, "Created job must appear in list"
        assert "status_code" in job_data, "Response must include status_code field"
        # status_code should be a non-empty string (from seeded job statuses)
        assert job_data["status_code"] is not None, (
            "status_code must not be null for a seeded-status job"
        )
        assert isinstance(job_data["status_code"], str), "status_code must be a string"

    def test_customer_name_present_in_response(self, client, test_tenant, test_user):
        """Response includes customer_name from customer JOIN."""
        suffix = uuid.uuid4().hex[:6]
        display_name = f"MOB-B1 FieldCheck {suffix}"
        cust_resp = client.post(
            "/api/v1/customers/test",
            json={"display_name": display_name, "type": "person"},
        )
        assert cust_resp.status_code == 201, cust_resp.text
        customer_id = cust_resp.json()["id"]

        site_resp = client.post("/api/v1/sites/test", json={"customer_id": customer_id})
        assert site_resp.status_code == 201, site_resp.text
        site_id = site_resp.json()["id"]

        job_id = _create_job(client, customer_id, site_id)

        resp = client.get(f"{JOBS_BASE}/test?limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()["items"]  # UI-FIX-1C: paginated response

        job_data = next((j for j in data if j["id"] == job_id), None)
        assert job_data is not None, "Created job must appear in list"
        assert "customer_name" in job_data, "Response must include customer_name field"
        assert job_data["customer_name"] == display_name, (
            f"customer_name must match customer.display_name. "
            f"Expected '{display_name}', got '{job_data['customer_name']}'"
        )

    def test_response_shape_has_required_fields(self, client, test_tenant, test_user):
        """JobListItem response shape includes all expected fields."""
        cid, sid = _create_customer_and_site(client)
        job_id = _create_job(client, cid, sid)

        resp = client.get(f"{JOBS_BASE}/test?limit=200")
        assert resp.status_code == 200, resp.text
        data = resp.json()["items"]  # UI-FIX-1C: paginated response

        job_data = next((j for j in data if j["id"] == job_id), None)
        assert job_data is not None

        required_fields = {
            "id",
            "tenant_id",
            "customer_id",
            "site_id",
            "status_id",
            "status_code",
            "customer_name",
            "scheduled_start_at",
            "scheduled_end_at",
            "estimated_duration_minutes",
        }
        for field in required_fields:
            assert field in job_data, f"Response must include field: {field}"


# ---------------------------------------------------------------------------
# Tests: multi-tenancy (IDOR protection)
# ---------------------------------------------------------------------------


class TestJobListMultiTenancy:
    def test_all_returned_jobs_belong_to_test_tenant(
        self, client, test_tenant, test_user
    ):
        """
        Customer JOIN does not expose cross-tenant data.
        All returned jobs must have tenant_id matching the test tenant.
        The WHERE Customer.tenant_id = current_tenant_id clause is the guard.
        """
        cid, sid = _create_customer_and_site(client)
        _create_job(client, cid, sid)

        resp = client.get(f"{JOBS_BASE}/test")
        assert resp.status_code == 200, resp.text
        data = resp.json()["items"]  # UI-FIX-1C: paginated response

        # All jobs returned must have tenant_id matching the test tenant
        for job_item in data:
            assert job_item["tenant_id"] == _TEST_TENANT_ID, (
                f"All returned jobs must belong to test tenant. "
                f"Found tenant_id: {job_item['tenant_id']}"
            )


# ---------------------------------------------------------------------------
# Tests: pagination still works
# ---------------------------------------------------------------------------


class TestJobListPagination:
    def test_limit_is_respected(self, client, test_tenant, test_user):
        """limit query param still functions alongside new filters."""
        cid, sid = _create_customer_and_site(client)

        # Create 3 jobs
        for _ in range(3):
            _create_job(client, cid, sid)

        # With limit=1, we should get exactly 1 result
        resp = client.get(f"{JOBS_BASE}/test?limit=1")
        assert resp.status_code == 200, resp.text
        data = resp.json()["items"]  # UI-FIX-1C: paginated response
        assert len(data) == 1, f"limit=1 must return exactly 1 job, got {len(data)}"

    def test_no_params_returns_200(self, client, test_tenant, test_user):
        """Calling the endpoint with no params returns 200 and a list."""
        resp = client.get(f"{JOBS_BASE}/test")
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json()["items"], list)  # UI-FIX-1C: paginated response
