"""
B21: Tests for _generate_due_recurring_jobs_impl (Beat task logic).

Tests call the impl directly — no Celery needed.
Mocks enqueue_recurring_job_notification.delay to prevent actual task dispatch.

Covers:
- Due rule → job created, occurrences_created incremented, next_job_at advanced
- Inactive rule skipped
- Rule with ends_on in past → is_active set to false
- Rule with occurrences_created >= max_occurrences → is_active set to false
- Rule with next_job_at in future → skipped
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]

MOCK_NOTIFY = "tasks.recurring_jobs.enqueue_recurring_job_notification"


def _make_rule(db_session, tenant_id, customer_id, site_id, status_id, **kwargs):
    """Helper to insert a JobRecurrenceRule row directly into the test DB."""
    from app.models.fulfillment import JobRecurrenceRule

    defaults = dict(
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        pattern="weekly",
        interval_count=1,
        starts_on=date.today(),
        is_active=True,
        occurrences_created=0,
        next_job_at=datetime.now(UTC) - timedelta(minutes=1),  # due NOW
    )
    defaults.update(kwargs)
    rule = JobRecurrenceRule(**defaults)
    db_session.add(rule)
    db_session.flush()
    return rule


class TestBeatTask:
    def test_beat_creates_job_for_due_rule(
        self, client, db_session, test_tenant, test_user
    ):
        """Due rule → job created, occurrences_created incremented, next_job_at advanced."""
        from app.models.fulfillment import Job, JobStatus
        from tasks.recurring_jobs import _generate_due_recurring_jobs_impl

        # Create customer + site in test_tenant
        cust_resp = client.post(
            "/api/v1/customers/test",
            json={"display_name": "Beat Task Customer", "type": "person"},
        )
        assert cust_resp.status_code == 201
        cust = cust_resp.json()

        site_resp = client.post("/api/v1/sites/test", json={"customer_id": cust["id"]})
        assert site_resp.status_code == 201
        site = site_resp.json()

        # Get default status for tenant
        from sqlmodel import select

        job_status = db_session.exec(
            select(JobStatus).where(JobStatus.is_default == True).limit(1)
        ).first()
        assert job_status, "No default JobStatus found"

        rule = _make_rule(
            db_session,
            tenant_id=test_tenant.id,
            customer_id=uuid.UUID(cust["id"]),
            site_id=uuid.UUID(site["id"]),
            status_id=job_status.id,
        )
        db_session.commit()

        initial_occurrences = rule.occurrences_created

        with patch(MOCK_NOTIFY) as mock_notify:
            mock_notify.delay = MagicMock()
            result = _generate_due_recurring_jobs_impl(db_session)

        assert result["processed"] >= 1

        db_session.refresh(rule)
        assert rule.occurrences_created == initial_occurrences + 1

        # A job was created linked to this rule
        from sqlmodel import select

        job = db_session.exec(
            select(Job).where(Job.recurrence_rule_id == rule.id)
        ).first()
        assert job is not None

        # next_job_at was advanced (should be 1 week in the future)
        assert rule.next_job_at > datetime.now(UTC)

    def test_beat_skips_inactive_rule(self, client, db_session, test_tenant):
        """is_active=False rule is not processed."""
        from app.models.fulfillment import JobStatus
        from tasks.recurring_jobs import _generate_due_recurring_jobs_impl

        cust_resp = client.post(
            "/api/v1/customers/test",
            json={"display_name": "Inactive Rule Customer", "type": "person"},
        )
        assert cust_resp.status_code == 201
        cust = cust_resp.json()
        site_resp = client.post("/api/v1/sites/test", json={"customer_id": cust["id"]})
        assert site_resp.status_code == 201
        site = site_resp.json()

        from sqlmodel import select

        job_status = db_session.exec(
            select(JobStatus).where(JobStatus.is_default == True).limit(1)
        ).first()

        rule = _make_rule(
            db_session,
            tenant_id=test_tenant.id,
            customer_id=uuid.UUID(cust["id"]),
            site_id=uuid.UUID(site["id"]),
            status_id=job_status.id,
            is_active=False,  # INACTIVE — should be skipped
        )
        db_session.commit()

        initial_occurrences = rule.occurrences_created

        with patch(MOCK_NOTIFY) as mock_notify:
            mock_notify.delay = MagicMock()
            _generate_due_recurring_jobs_impl(db_session)

        db_session.refresh(rule)
        assert rule.occurrences_created == initial_occurrences  # unchanged

    def test_beat_deactivates_expired_rule(self, client, db_session, test_tenant):
        """Rule where ends_on < today → is_active set to False."""
        from app.models.fulfillment import JobStatus
        from tasks.recurring_jobs import _generate_due_recurring_jobs_impl

        cust_resp = client.post(
            "/api/v1/customers/test",
            json={"display_name": "Expired Rule Customer", "type": "person"},
        )
        assert cust_resp.status_code == 201
        cust = cust_resp.json()
        site_resp = client.post("/api/v1/sites/test", json={"customer_id": cust["id"]})
        assert site_resp.status_code == 201
        site = site_resp.json()

        from sqlmodel import select

        job_status = db_session.exec(
            select(JobStatus).where(JobStatus.is_default == True).limit(1)
        ).first()

        past_date = date.today() - timedelta(days=1)
        rule = _make_rule(
            db_session,
            tenant_id=test_tenant.id,
            customer_id=uuid.UUID(cust["id"]),
            site_id=uuid.UUID(site["id"]),
            status_id=job_status.id,
            ends_on=past_date,  # expired
        )
        db_session.commit()

        with patch(MOCK_NOTIFY) as mock_notify:
            mock_notify.delay = MagicMock()
            result = _generate_due_recurring_jobs_impl(db_session)

        assert result["deactivated"] >= 1
        db_session.refresh(rule)
        assert rule.is_active is False

    def test_beat_deactivates_maxed_rule(self, client, db_session, test_tenant):
        """Rule where occurrences_created >= max_occurrences → is_active set to False."""
        from app.models.fulfillment import JobStatus
        from tasks.recurring_jobs import _generate_due_recurring_jobs_impl

        cust_resp = client.post(
            "/api/v1/customers/test",
            json={"display_name": "Maxed Rule Customer", "type": "person"},
        )
        assert cust_resp.status_code == 201
        cust = cust_resp.json()
        site_resp = client.post("/api/v1/sites/test", json={"customer_id": cust["id"]})
        assert site_resp.status_code == 201
        site = site_resp.json()

        from sqlmodel import select

        job_status = db_session.exec(
            select(JobStatus).where(JobStatus.is_default == True).limit(1)
        ).first()

        rule = _make_rule(
            db_session,
            tenant_id=test_tenant.id,
            customer_id=uuid.UUID(cust["id"]),
            site_id=uuid.UUID(site["id"]),
            status_id=job_status.id,
            max_occurrences=3,
            occurrences_created=3,  # already at max
        )
        db_session.commit()

        with patch(MOCK_NOTIFY) as mock_notify:
            mock_notify.delay = MagicMock()
            result = _generate_due_recurring_jobs_impl(db_session)

        assert result["deactivated"] >= 1
        db_session.refresh(rule)
        assert rule.is_active is False

    def test_beat_skips_future_rule(self, client, db_session, test_tenant):
        """Rule with next_job_at in the future is not processed."""
        from app.models.fulfillment import JobStatus
        from tasks.recurring_jobs import _generate_due_recurring_jobs_impl

        cust_resp = client.post(
            "/api/v1/customers/test",
            json={"display_name": "Future Rule Customer", "type": "person"},
        )
        assert cust_resp.status_code == 201
        cust = cust_resp.json()
        site_resp = client.post("/api/v1/sites/test", json={"customer_id": cust["id"]})
        assert site_resp.status_code == 201
        site = site_resp.json()

        from sqlmodel import select

        job_status = db_session.exec(
            select(JobStatus).where(JobStatus.is_default == True).limit(1)
        ).first()

        future_time = datetime.now(UTC) + timedelta(days=7)
        rule = _make_rule(
            db_session,
            tenant_id=test_tenant.id,
            customer_id=uuid.UUID(cust["id"]),
            site_id=uuid.UUID(site["id"]),
            status_id=job_status.id,
            next_job_at=future_time,  # in the future — should be skipped
        )
        db_session.commit()

        initial_occurrences = rule.occurrences_created

        with patch(MOCK_NOTIFY) as mock_notify:
            mock_notify.delay = MagicMock()
            _generate_due_recurring_jobs_impl(db_session)

        db_session.refresh(rule)
        assert rule.occurrences_created == initial_occurrences  # unchanged
