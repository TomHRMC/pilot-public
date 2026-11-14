"""
Tests for FIND-110: reschedule_job and check_next_job voice handlers.

FIND-110 adds two new voice intent handlers:
1. `reschedule_job_via_voice`: Moves an already-scheduled job to a new time
   - Includes conflict detection with multi-turn confirmation if conflict exists
   - Emits schedule_changed notification to assigned tech
   - Creates VoiceCommandEntityLink row with action='rescheduled'

2. `check_next_job_via_voice`: Read-only query of next upcoming job for tech
   - Returns job details (customer name, address, time, description)
   - No DB writes, no VoiceCommandEntityLink row
   - Returns "no upcoming jobs" message if no assignments
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.models.ai import ConversationSession
from app.models.fulfillment import Job, JobStatus
from app.models.scheduling import JobTechAssignment
from core.test_context import TestUserContext
from services.voice_action_router import (
    check_next_job_via_voice,
    reschedule_job_via_voice,
)


def _get_or_create_job_status(db_session: Session, code: str = "scheduled"):
    """Get or create a job status for testing."""
    status = db_session.exec(select(JobStatus).where(JobStatus.code == code)).first()
    if not status:
        status = JobStatus(
            id=uuid.uuid4(),
            code=code,
            name=code.title(),
            description=f"Job is {code}",
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()
    return status


def _create_test_job(
    db_session: Session,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    site_id: uuid.UUID,
    user_id: uuid.UUID,
    scheduled_start_at: datetime = None,
    scheduled_end_at: datetime = None,
) -> Job:
    """Create a minimal test job with status_id."""
    status = _get_or_create_job_status(db_session)

    if scheduled_start_at is None:
        scheduled_start_at = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)
    if scheduled_end_at is None:
        scheduled_end_at = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)

    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=status.id,
        scheduled_start_at=scheduled_start_at,
        scheduled_end_at=scheduled_end_at,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


class TestRescheduleJobNoConflict:
    """Reschedule with no scheduling conflict — immediate success."""

    @pytest.mark.asyncio
    async def test_reschedule_job_no_conflict_updates_job(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """reschedule_job with no conflict updates job scheduled times."""
        # Create job with initial schedule
        job = _create_test_job(
            db_session,
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            user_id=test_user.id,
        )

        # Create conversation session
        session = ConversationSession(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            context_window_json={},
            created_by=test_user.id,
        )
        db_session.add(session)
        db_session.commit()

        # Create mock current_user
        current_user = TestUserContext(
            id=test_user.id,
            tenant_id=test_tenant.id,
            email=test_user.email,
        )

        # Call handler
        new_start = datetime(2026, 5, 16, 9, 0, tzinfo=UTC)
        new_end = datetime(2026, 5, 16, 11, 0, tzinfo=UTC)

        result = await reschedule_job_via_voice(
            entities={
                "job_id": str(job.id),
                "scheduled_start_at": new_start.isoformat(),
                "scheduled_end_at": new_end.isoformat(),
            },
            current_user=current_user,
            db=db_session,
            session=session,
        )

        # Verify success response
        assert result["action"] == "reschedule_job"
        assert result["success"] is True

        # Verify job updated
        refreshed_job = db_session.exec(select(Job).where(Job.id == job.id)).first()
        assert refreshed_job.scheduled_start_at == new_start
        assert refreshed_job.scheduled_end_at == new_end


class TestCheckNextJob:
    """check_next_job read-only queries."""

    @pytest.mark.asyncio
    async def test_check_next_job_returns_upcoming_job(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """check_next_job returns next upcoming job for tech."""
        # Create upcoming job
        next_time = datetime.now(UTC) + timedelta(hours=2)
        job = _create_test_job(
            db_session,
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            user_id=test_user.id,
            scheduled_start_at=next_time,
            scheduled_end_at=next_time + timedelta(hours=2),
        )

        # Create assignment to test user
        assignment = JobTechAssignment(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            job_id=job.id,
            user_id=test_user.id,
            role="primary",
            ordinal=1,
            assigned_by_user_id=test_user.id,
            is_active=True,
            created_by=test_user.id,
        )
        db_session.add(assignment)
        db_session.commit()

        # Create session
        session = ConversationSession(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            context_window_json={},
            created_by=test_user.id,
        )
        db_session.add(session)
        db_session.commit()

        # Create mock current_user
        current_user = TestUserContext(
            id=test_user.id,
            tenant_id=test_tenant.id,
            email=test_user.email,
        )

        # Call handler
        result = await check_next_job_via_voice(
            entities={},
            current_user=current_user,
            db=db_session,
            session=session,
        )

        assert result["success"] is True
        assert result["action"] == "check_next_job"
        assert result["data"]["next_job"] is not None
        assert result["data"]["next_job"]["job_id"] == str(job.id)
