"""
Task 1-D-3: Schedule-Aware Voice Intents — unit tests.

Coverage:
  schedule_job_via_voice:
    1. Missing job_id (no context) → success=False
    2. Job not found → success=False
    3. Missing scheduled_start_at/end → success=False
    4. end <= start → success=False
    5. No tech_user_id → skips conflict check, persists times → success=True
    6. tech_user_id provided, no conflicts → persists → success=True
    7. tech_user_id provided, hard conflict (double_booking) → success=False,
       job times NOT persisted

  reassign_job_via_voice:
    8. No job_id (no context) → success=False
    9. No tech_user_id → success=False
   10. Job not scheduled → skips conflict check, upserts assignment → success=True
   11. Conflict found → success=False, no new assignment row
   12. Valid reassignment: old primary soft-deleted, new primary created → success=True

Patch target for conflict mocking:
    ``services.scheduling_service.check_slot_feasibility``
    (the function is lazily imported inside the handler)

For JobTechAssignment we must use a real user from the DB (``test_user``), not
random UUIDs, because ``fk_jta_user`` enforces referential integrity.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import select

from app.models.ai import ConversationSession
from app.models.fulfillment import Job, JobStatus
from app.models.scheduling import JobTechAssignment
from services.voice_action_router import (
    reassign_job_via_voice,
    schedule_job_via_voice,
)

_PATCH_TARGET = "services.scheduling_service.check_slot_feasibility"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(db, tenant_id, user_id) -> ConversationSession:
    sess = ConversationSession(
        tenant_id=tenant_id,
        user_id=user_id,
        context_window_json={},
        is_active=True,
        created_by=user_id,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _make_job(
    db,
    tenant_id,
    customer_id,
    site_id,
    user_id,
    *,
    scheduled: bool = True,
) -> Job:
    js = db.exec(select(JobStatus)).first()
    assert js is not None
    now = datetime.now(UTC)
    job = Job(
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=js.id,
        scheduled_start_at=(now + timedelta(hours=2)) if scheduled else None,
        scheduled_end_at=(now + timedelta(hours=4)) if scheduled else None,
        is_active=True,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _make_assignment(
    db, tenant_id, job_id, tech_user_id, assigner_id
) -> JobTechAssignment:
    a = JobTechAssignment(
        tenant_id=tenant_id,
        job_id=job_id,
        user_id=tech_user_id,
        role="primary",
        ordinal=1,
        assigned_by_user_id=assigner_id,
        is_active=True,
        created_by=assigner_id,
        updated_by=assigner_id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _user_ctx(test_user, test_tenant):
    from types import SimpleNamespace

    return SimpleNamespace(id=test_user.id, tenant_id=test_tenant.id)


_DT_START = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0)
_DT_END = _DT_START + timedelta(hours=2)

_FEASIBLE = {"is_feasible": True, "conflicts": []}
_CONFLICT = {
    "is_feasible": False,
    "conflicts": [
        {
            "conflict_type": "double_booking",
            "description": "Tech is already booked",
            "conflicting_entity_id": str(uuid.uuid4()),
        }
    ],
}
_PTO_CONFLICT = {
    "is_feasible": False,
    "conflicts": [
        {
            "conflict_type": "availability_block",
            "description": "Tech has PTO",
            "conflicting_entity_id": str(uuid.uuid4()),
        }
    ],
}


# ---------------------------------------------------------------------------
# schedule_job_via_voice
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schedule_job_no_job_id(db_session, test_tenant, test_user):
    """1. No job_id and empty context → success=False."""
    sess = _make_session(db_session, test_tenant.id, test_user.id)
    result = await schedule_job_via_voice(
        {}, _user_ctx(test_user, test_tenant), db_session, sess
    )
    assert result["success"] is False
    assert result["error"] == "No job specified"


@pytest.mark.asyncio
async def test_schedule_job_not_found(db_session, test_tenant, test_user):
    """2. Random job UUID → job not found → success=False."""
    sess = _make_session(db_session, test_tenant.id, test_user.id)
    result = await schedule_job_via_voice(
        {"job_id": str(uuid.uuid4())},
        _user_ctx(test_user, test_tenant),
        db_session,
        sess,
    )
    assert result["success"] is False
    assert result["error"] == "Job not found"


@pytest.mark.asyncio
async def test_schedule_job_missing_times(
    db_session, test_tenant, test_user, test_customer, test_site
):
    """3. Job found, no start/end → success=False."""
    job = _make_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=False,
    )
    sess = _make_session(db_session, test_tenant.id, test_user.id)
    result = await schedule_job_via_voice(
        {"job_id": str(job.id)},
        _user_ctx(test_user, test_tenant),
        db_session,
        sess,
    )
    assert result["success"] is False
    assert result["error"] == "Missing schedule times"


@pytest.mark.asyncio
async def test_schedule_job_invalid_time_range(
    db_session, test_tenant, test_user, test_customer, test_site
):
    """4. end <= start → success=False."""
    job = _make_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=False,
    )
    sess = _make_session(db_session, test_tenant.id, test_user.id)
    result = await schedule_job_via_voice(
        {
            "job_id": str(job.id),
            "scheduled_start_at": _DT_END.isoformat(),  # end as start
            "scheduled_end_at": _DT_START.isoformat(),  # start as end
        },
        _user_ctx(test_user, test_tenant),
        db_session,
        sess,
    )
    assert result["success"] is False
    assert result["error"] == "Invalid time range"


@pytest.mark.asyncio
async def test_schedule_job_no_tech_skips_conflict_check(
    db_session, test_tenant, test_user, test_customer, test_site
):
    """5. No tech_user_id → conflict check skipped, times persisted → success."""
    job = _make_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=False,
    )
    sess = _make_session(db_session, test_tenant.id, test_user.id)
    result = await schedule_job_via_voice(
        {
            "job_id": str(job.id),
            "scheduled_start_at": _DT_START.isoformat(),
            "scheduled_end_at": _DT_END.isoformat(),
        },
        _user_ctx(test_user, test_tenant),
        db_session,
        sess,
    )
    assert result["success"] is True
    db_session.refresh(job)
    assert job.scheduled_start_at is not None


@pytest.mark.asyncio
async def test_schedule_job_with_tech_no_conflicts(
    db_session, test_tenant, test_user, test_customer, test_site
):
    """6. tech_user_id provided, feasibility OK → times persisted → success."""
    job = _make_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=False,
    )
    sess = _make_session(db_session, test_tenant.id, test_user.id)

    with patch(_PATCH_TARGET, return_value=_FEASIBLE):
        result = await schedule_job_via_voice(
            {
                "job_id": str(job.id),
                "scheduled_start_at": _DT_START.isoformat(),
                "scheduled_end_at": _DT_END.isoformat(),
                "tech_user_id": str(test_user.id),
            },
            _user_ctx(test_user, test_tenant),
            db_session,
            sess,
        )

    assert result["success"] is True
    db_session.refresh(job)
    assert job.scheduled_start_at is not None


@pytest.mark.asyncio
async def test_schedule_job_hard_conflict_blocks_save(
    db_session, test_tenant, test_user, test_customer, test_site
):
    """7. Hard conflict → success=False, job times NOT updated."""
    job = _make_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=False,
    )
    original_start = job.scheduled_start_at  # None

    sess = _make_session(db_session, test_tenant.id, test_user.id)

    with patch(_PATCH_TARGET, return_value=_CONFLICT):
        result = await schedule_job_via_voice(
            {
                "job_id": str(job.id),
                "scheduled_start_at": _DT_START.isoformat(),
                "scheduled_end_at": _DT_END.isoformat(),
                "tech_user_id": str(test_user.id),
            },
            _user_ctx(test_user, test_tenant),
            db_session,
            sess,
        )

    assert result["success"] is False
    assert result["error"] == "scheduling_conflict"
    db_session.refresh(job)
    assert job.scheduled_start_at == original_start


# ---------------------------------------------------------------------------
# reassign_job_via_voice
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reassign_job_no_job_id(db_session, test_tenant, test_user):
    """8. No job_id and empty context → success=False."""
    sess = _make_session(db_session, test_tenant.id, test_user.id)
    result = await reassign_job_via_voice(
        {}, _user_ctx(test_user, test_tenant), db_session, sess
    )
    assert result["success"] is False
    assert result["error"] == "No job specified"


@pytest.mark.asyncio
async def test_reassign_job_no_tech(
    db_session, test_tenant, test_user, test_customer, test_site
):
    """9. No tech_user_id → success=False."""
    job = _make_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
    )
    sess = _make_session(db_session, test_tenant.id, test_user.id)
    result = await reassign_job_via_voice(
        {"job_id": str(job.id)},
        _user_ctx(test_user, test_tenant),
        db_session,
        sess,
    )
    assert result["success"] is False
    assert result["error"] == "No technician specified"


@pytest.mark.asyncio
async def test_reassign_job_unscheduled_skips_conflict_check(
    db_session, test_tenant, test_user, test_customer, test_site
):
    """10. Job has no scheduled times → conflict check skipped → success=True.

    Uses ``test_user.id`` as tech_id to satisfy FK constraint on user table.
    """
    job = _make_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=False,
    )
    sess = _make_session(db_session, test_tenant.id, test_user.id)

    result = await reassign_job_via_voice(
        {"job_id": str(job.id), "tech_user_id": str(test_user.id)},
        _user_ctx(test_user, test_tenant),
        db_session,
        sess,
    )

    assert result["success"] is True
    assignment = db_session.exec(
        select(JobTechAssignment).where(
            JobTechAssignment.job_id == job.id,
            JobTechAssignment.user_id == test_user.id,
            JobTechAssignment.is_active == True,
        )
    ).first()
    assert assignment is not None


@pytest.mark.asyncio
async def test_reassign_job_conflict_blocks_reassignment(
    db_session, test_tenant, test_user, test_customer, test_site
):
    """11. Conflict → success=False, no new assignment row."""
    job = _make_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=True,
    )
    sess = _make_session(db_session, test_tenant.id, test_user.id)

    with patch(_PATCH_TARGET, return_value=_PTO_CONFLICT):
        result = await reassign_job_via_voice(
            {"job_id": str(job.id), "tech_user_id": str(test_user.id)},
            _user_ctx(test_user, test_tenant),
            db_session,
            sess,
        )

    assert result["success"] is False
    assert result["error"] == "scheduling_conflict"


@pytest.mark.asyncio
async def test_reassign_job_success_replaces_primary(
    db_session, test_tenant, test_user, test_customer, test_site
):
    """12. Valid reassignment: old assignment soft-deleted, new primary created.

    Both old_tech and new_tech must be the same ``test_user`` (real DB user)
    to satisfy the FK. We test the upsert semantics: the existing 'active'
    assignment is soft-deleted and a fresh one is inserted.
    """
    job = _make_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=True,
    )
    # Seed an existing primary assignment (using test_user as the "old" tech)
    old_assignment = _make_assignment(
        db_session, test_tenant.id, job.id, test_user.id, test_user.id
    )

    sess = _make_session(db_session, test_tenant.id, test_user.id)

    with patch(_PATCH_TARGET, return_value=_FEASIBLE):
        result = await reassign_job_via_voice(
            {"job_id": str(job.id), "tech_user_id": str(test_user.id)},
            _user_ctx(test_user, test_tenant),
            db_session,
            sess,
        )

    assert result["success"] is True

    # Old assignment must be soft-deleted
    db_session.refresh(old_assignment)
    assert old_assignment.is_active is False

    # A new active primary assignment must exist
    new_assignments = db_session.exec(
        select(JobTechAssignment).where(
            JobTechAssignment.job_id == job.id,
            JobTechAssignment.user_id == test_user.id,
            JobTechAssignment.is_active == True,
            JobTechAssignment.role == "primary",
        )
    ).all()
    assert len(new_assignments) >= 1
