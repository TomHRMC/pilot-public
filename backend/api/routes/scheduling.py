"""
Scheduling & Dispatch API — Tasks 1-B-1, 1-B-2, 1-B-3, and 1-B-4

1-B-1: TechAvailability CRUD
1-B-2: Job Assignment & Scheduling
  - PATCH /api/v1/scheduling/jobs/{job_id}/schedule — update scheduled times
  - POST  /api/v1/scheduling/jobs/{job_id}/assignments — assign a tech (upsert primary)
  - GET   /api/v1/scheduling/jobs/{job_id}/assignments — list active assignments
  - DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{assignment_id} — soft-delete
1-B-3: Dispatch Board Query
  - GET  /api/v1/scheduling/dispatch-board — grouped board payload
1-B-4: Conflict Detection Service
  - POST /api/v1/scheduling/conflict-check — validate a proposed job slot

Dual-endpoint architecture:
  /test   endpoints — no JWT, DEV/QA only
  /       endpoints — require JWT + schedule.* permission

Permissions used:
  schedule.manage  — create / update / delete
  schedule.view_all — list all techs' availability / assignments
  schedule.view_own — list own availability only
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models.fulfillment import Job
from app.models.scheduling import JobTechAssignment, TechAvailability
from app.models.system import (
    AuditEvent,
    NotificationEvent,
    NotificationOutbox,
    NotificationType,
)
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API Schemas (FIND-117: Job Schedule History)
# ---------------------------------------------------------------------------


class ScheduleHistoryEntry(BaseModel):
    """Single scheduling change entry for a job."""

    model_config = {"from_attributes": True}

    changed_at: datetime = Field(description="When the change occurred")
    changed_by_user_id: UUID | None = Field(
        description="User who made the change (NULL for system changes)"
    )
    field_name: str = Field(
        description="Field that changed (scheduled_start, assigned_tech_id, status)"
    )
    old_value: Any | None = Field(
        description="Previous value (NULL for INSERT or initial value)"
    )
    new_value: Any | None = Field(description="New value (NULL for DELETE operations)")


class ScheduleHistoryResponse(BaseModel):
    """Paginated list of schedule history entries for a job."""

    job_id: UUID
    entries: list[ScheduleHistoryEntry]
    total: int = Field(description="Total count of history entries")
    limit: int = Field(description="Page size used")
    offset: int = Field(description="Starting offset used")


# ---------------------------------------------------------------------------
# Notification helper (Task 1-C-3)
# ---------------------------------------------------------------------------

_JOB_ASSIGNED_TYPE_CODE = "job_assigned"
_JOB_ENTITY_TYPE_CODE = "job"


def _emit_job_assigned_notification(
    db: Session,
    tenant_id: UUID,
    job_id: UUID,
    tech_user_id: UUID,
    assigner_user_id: UUID,
) -> None:
    """Insert a ``notification_outbox`` record alerting a tech of a new assignment.

    Silently no-ops when the assigner is the tech themselves (self-assignment).

    Args:
        db:               Open SQLModel session (caller owns the transaction).
        tenant_id:        Tenant scope for IDOR isolation.
        job_id:           UUID of the job being assigned.
        tech_user_id:     UUID of the technician who was assigned.
        assigner_user_id: UUID of the user performing the assignment.
    """
    # PRD constraint: only notify if the assigner ≠ the tech
    if tech_user_id == assigner_user_id:
        return

    # 1. Upsert NotificationType 'job_assigned' (idempotent)
    notif_type = db.exec(
        select(NotificationType).where(NotificationType.code == _JOB_ASSIGNED_TYPE_CODE)
    ).first()
    if not notif_type:
        notif_type = NotificationType(
            code=_JOB_ASSIGNED_TYPE_CODE,
            name="Job Assigned",
            audience="tenant",
            description="Notifies a technician when they are assigned to a job.",
            is_active=True,
        )
        db.add(notif_type)
        db.flush()

    # 2. Create NotificationEvent
    event = NotificationEvent(
        tenant_id=tenant_id,
        notification_type_code=_JOB_ASSIGNED_TYPE_CODE,
        entity_type_code=_JOB_ENTITY_TYPE_CODE,
        entity_id=str(job_id),
        occurred_at=datetime.now(UTC),
        payload={
            "job_id": str(job_id),
            "tech_user_id": str(tech_user_id),
            "assigned_by_user_id": str(assigner_user_id),
        },
        created_by=assigner_user_id,
    )
    db.add(event)
    db.flush()

    # 3. Create NotificationOutbox (in_app channel requires recipient_user_id)
    outbox = NotificationOutbox(
        tenant_id=tenant_id,
        notification_event_id=event.id,
        recipient_user_id=tech_user_id,
        channel="in_app",
        body=f"You have been assigned to job {job_id}.",
        status="pending",
        priority=5,
        created_by=assigner_user_id,
        category_id="job_activity",  # B10/A56
        sub_trigger_id="job_activity.assignment",  # B10/A56
        recipient_user_id_originating=tech_user_id,  # B10/A56 forced-minimum support
    )
    db.add(outbox)
    db.flush()
    logger.debug(
        "scheduling.notification: job_assigned outbox created "
        "(job=%s, tech=%s, assigner=%s)",
        job_id,
        tech_user_id,
        assigner_user_id,
    )


def _emit_schedule_changed_notification(
    db: Session,
    tenant_id: UUID,
    job_id: UUID,
    tech_user_id: UUID,
    assigner_user_id: UUID,
) -> None:
    """Insert a ``notification_outbox`` record alerting a tech of a schedule change.

    Always fires for schedule changes (no self-suppression like assignment).
    The owner may re-enter a tech's schedule on their behalf.

    Args:
        db:               Open SQLModel session (caller owns the transaction).
        tenant_id:        Tenant scope for IDOR isolation.
        job_id:           UUID of the job whose schedule changed.
        tech_user_id:     UUID of the technician assigned to the job.
        assigner_user_id: UUID of the user who changed the schedule.
    """
    # 1. Create NotificationEvent
    event = NotificationEvent(
        tenant_id=tenant_id,
        notification_type_code="schedule_changed",
        entity_type_code=_JOB_ENTITY_TYPE_CODE,
        entity_id=str(job_id),
        occurred_at=datetime.now(UTC),
        payload={
            "job_id": str(job_id),
            "tech_user_id": str(tech_user_id),
            "changed_by_user_id": str(assigner_user_id),
        },
        created_by=assigner_user_id,
    )
    db.add(event)
    db.flush()

    # 2. Create NotificationOutbox (in_app channel requires recipient_user_id)
    # FIND-082: Added schedule_changed notification
    outbox = NotificationOutbox(
        tenant_id=tenant_id,
        notification_event_id=event.id,
        recipient_user_id=tech_user_id,
        channel="in_app",
        body=f"Your schedule for job {job_id} has been updated.",
        status="pending",
        priority=5,
        created_by=assigner_user_id,
        category_id="scheduling",  # FIND-082: added
        sub_trigger_id="schedule_changed",  # FIND-082: added
        recipient_user_id_originating=None,  # schedule changes don't suppress for self
    )
    db.add(outbox)
    db.flush()
    logger.debug(
        "scheduling.notification: schedule_changed outbox created "
        "(job=%s, tech=%s, changed_by=%s)",
        job_id,
        tech_user_id,
        assigner_user_id,
    )


from api.schemas.schemas import (
    ConflictCheckRequest,
    ConflictCheckResponse,
    DispatchBoardJobEntry,
    DispatchBoardResponse,
    DispatchBoardTechGroup,
    JobResponse,
    JobScheduleUpdate,
    JobTechAssignmentCreate,
    JobTechAssignmentResponse,
    SoftDeleteResponse,
    TechAvailabilityCreate,
    TechAvailabilityResponse,
    TechAvailabilityUpdate,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

_VALID_TYPES = {"working_hours", "pto", "unavailable"}


def _validate_availability(
    data: TechAvailabilityCreate | TechAvailabilityUpdate,
) -> None:
    """Enforce the DB check constraint logic at the application layer for cleaner 400s."""
    atype = getattr(data, "availability_type", None)
    if atype is None:
        return  # partial update — nothing to validate

    if atype not in _VALID_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid availability_type '{atype}'. "
            f"Valid values: {sorted(_VALID_TYPES)}",
        )

    starts_at = getattr(data, "starts_at", None)
    ends_at = getattr(data, "ends_at", None)
    rrule = getattr(data, "recurrence_rrule", None)

    if atype == "working_hours":
        if not rrule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recurrence_rrule is required for availability_type='working_hours'",
            )
    else:
        # pto / unavailable
        if starts_at is None or ends_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="starts_at and ends_at are required for pto/unavailable availability records",
            )
        if ends_at <= starts_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ends_at must be after starts_at",
            )


# ---------------------------------------------------------------------------
# Shared business logic
# ---------------------------------------------------------------------------


def _create_tech_availability_impl(
    data: TechAvailabilityCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TechAvailability:
    """Shared creation logic — used by both test and authenticated endpoints."""
    _validate_availability(data)

    set_audit_context_sync(db, user_context.id)

    record = TechAvailability(
        tenant_id=user_context.tenant_id,
        user_id=data.user_id,
        availability_type=data.availability_type,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        recurrence_rrule=data.recurrence_rrule,
        notes=data.notes,
        created_by=user_context.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _list_tech_availability_impl(
    skip: int,
    limit: int,
    user_id: UUID | None,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[TechAvailability]:
    """List availability records for the tenant, optionally filtered by user_id."""
    query = (
        select(TechAvailability)
        .where(TechAvailability.tenant_id == user_context.tenant_id)
        .where(TechAvailability.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    if user_id is not None:
        query = query.where(TechAvailability.user_id == user_id)
    return db.exec(query).all()


def _get_tech_availability_impl(
    record_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TechAvailability:
    """Retrieve a single active availability record scoped to the tenant."""
    record = db.exec(
        select(TechAvailability)
        .where(TechAvailability.id == record_id)
        .where(TechAvailability.tenant_id == user_context.tenant_id)
    ).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tech availability record not found",
        )
    return record


def _update_tech_availability_impl(
    record_id: UUID,
    data: TechAvailabilityUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TechAvailability:
    """Partial update — mutate only supplied fields."""
    record = _get_tech_availability_impl(record_id, db, user_context)

    # Run validation against the merged state (existing values + patch values)
    merged_type = data.availability_type or record.availability_type
    merged_starts = data.starts_at if data.starts_at is not None else record.starts_at
    merged_ends = data.ends_at if data.ends_at is not None else record.ends_at
    merged_rrule = (
        data.recurrence_rrule
        if data.recurrence_rrule is not None
        else record.recurrence_rrule
    )

    # Build a lightweight object for the validator
    class _Merged:
        availability_type = merged_type
        starts_at = merged_starts
        ends_at = merged_ends
        recurrence_rrule = merged_rrule

    _validate_availability(_Merged())  # type: ignore[arg-type]

    set_audit_context_sync(db, user_context.id)

    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(record, key, val)
    record.updated_by = user_context.id

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _delete_tech_availability_impl(
    record_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """Soft-delete a tech availability record."""
    record = _get_tech_availability_impl(record_id, db, user_context)

    set_audit_context_sync(db, user_context.id)

    record.is_active = False
    record.updated_by = user_context.id
    db.add(record)
    db.commit()
    return {"message": "Tech availability record deactivated", "id": str(record_id)}


# ---------------------------------------------------------------------------
# TEST ENDPOINTS — register BEFORE authenticated endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/tech-availability/test",
    response_model=TechAvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tech availability (test — no auth)",
)
def create_tech_availability_test(
    data: TechAvailabilityCreate,
    db: Session = Depends(get_db),
):
    """Create a tech availability record — TEST ENDPOINT, no authentication required.

    Blocked in staging/production. Returns HTTP 403 if ``TEST_ENDPOINT_ENABLED`` is false.
    """
    test_context = get_test_context()
    return _create_tech_availability_impl(data, db, test_context)


@router.get(
    "/tech-availability/test",
    response_model=list[TechAvailabilityResponse],
    summary="List tech availability (test — no auth)",
)
def list_tech_availability_test(
    skip: int = 0,
    limit: int = 100,
    user_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    """List tech availability records — TEST ENDPOINT, no authentication required."""
    test_context = get_test_context()
    return _list_tech_availability_impl(skip, limit, user_id, db, test_context)


@router.get(
    "/tech-availability/{record_id}/test",
    response_model=TechAvailabilityResponse,
    summary="Get tech availability (test — no auth)",
)
def get_tech_availability_test(
    record_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a single tech availability record — TEST ENDPOINT."""
    test_context = get_test_context()
    return _get_tech_availability_impl(record_id, db, test_context)


@router.patch(
    "/tech-availability/{record_id}/test",
    response_model=TechAvailabilityResponse,
    summary="Update tech availability (test — no auth)",
)
def update_tech_availability_test(
    record_id: UUID,
    data: TechAvailabilityUpdate,
    db: Session = Depends(get_db),
):
    """Partial update of a tech availability record — TEST ENDPOINT."""
    test_context = get_test_context()
    return _update_tech_availability_impl(record_id, data, db, test_context)


# FIND-154: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete(
    "/tech-availability/{record_id}/test",
    response_model=SoftDeleteResponse,
    summary="Soft-delete tech availability (test — no auth)",
)
def delete_tech_availability_test(
    record_id: UUID,
    db: Session = Depends(get_db),
):
    """Soft-delete a tech availability record — TEST ENDPOINT."""
    test_context = get_test_context()
    return _delete_tech_availability_impl(record_id, db, test_context)


# ---------------------------------------------------------------------------
# AUTHENTICATED ENDPOINTS
# ---------------------------------------------------------------------------


@router.post(
    "/tech-availability/",
    response_model=TechAvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tech availability",
)
def create_tech_availability(
    data: TechAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
):
    """Create a tech availability record (requires ``schedule.manage`` permission)."""
    return _create_tech_availability_impl(data, db, current_user)


@router.get(
    "/tech-availability/",
    response_model=list[TechAvailabilityResponse],
    summary="List tech availability",
)
def list_tech_availability(
    skip: int = 0,
    limit: int = 100,
    user_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.view_all")),
):
    """List all tech availability records for the tenant (requires ``schedule.view_all``)."""
    return _list_tech_availability_impl(skip, limit, user_id, db, current_user)


@router.get(
    "/tech-availability/{record_id}",
    response_model=TechAvailabilityResponse,
    summary="Get tech availability record",
)
def get_tech_availability(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.view_all")),
):
    """Get a single tech availability record (requires ``schedule.view_all``)."""
    return _get_tech_availability_impl(record_id, db, current_user)


@router.patch(
    "/tech-availability/{record_id}",
    response_model=TechAvailabilityResponse,
    summary="Update tech availability record",
)
def update_tech_availability(
    record_id: UUID,
    data: TechAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
):
    """Partial update of a tech availability record (requires ``schedule.manage``)."""
    return _update_tech_availability_impl(record_id, data, db, current_user)


# FIND-154: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete(
    "/tech-availability/{record_id}",
    response_model=SoftDeleteResponse,
    summary="Soft-delete tech availability record",
)
def delete_tech_availability(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
):
    """Soft-delete a tech availability record (requires ``schedule.manage``)."""
    return _delete_tech_availability_impl(record_id, db, current_user)


# ===========================================================================
# Task 1-B-2: Job Schedule Update + JobTechAssignment CRUD
# ===========================================================================

# ---------------------------------------------------------------------------
# Helper: verify job belongs to tenant
# ---------------------------------------------------------------------------


def _get_job_or_404(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Job:
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job


# ---------------------------------------------------------------------------
# Shared logic: job schedule update
# ---------------------------------------------------------------------------


def _update_job_schedule_impl(
    job_id: UUID,
    data: JobScheduleUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Job:
    """Patch scheduled_start_at, scheduled_end_at, estimated_duration_minutes,
    and/or external_calendar_event_id on a job.

    Enforces: if either start or end is supplied, both must be supplied
    and end must be after start.
    """
    job = _get_job_or_404(job_id, db, user_context)

    # Validate that start/end are always supplied together and ordered correctly
    new_start = (
        data.scheduled_start_at
        if data.scheduled_start_at is not None
        else job.scheduled_start_at
    )
    new_end = (
        data.scheduled_end_at
        if data.scheduled_end_at is not None
        else job.scheduled_end_at
    )

    if (new_start is None) != (new_end is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scheduled_start_at and scheduled_end_at must both be provided or both be null",
        )
    if new_start is not None and new_end is not None and new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scheduled_end_at must be after scheduled_start_at",
        )
    if (
        data.estimated_duration_minutes is not None
        and data.estimated_duration_minutes <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="estimated_duration_minutes must be a positive integer",
        )

    set_audit_context_sync(db, user_context.id)

    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(job, key, val)
    job.updated_by = user_context.id

    db.add(job)
    db.commit()
    db.refresh(job)

    # FIND-082: Emit schedule_changed notification to all assigned techs
    assigned_techs = db.exec(
        select(JobTechAssignment)
        .where(JobTechAssignment.tenant_id == user_context.tenant_id)
        .where(JobTechAssignment.job_id == job_id)
        .where(JobTechAssignment.is_active == True)
    ).all()
    for assignment in assigned_techs:
        _emit_schedule_changed_notification(
            db=db,
            tenant_id=user_context.tenant_id,
            job_id=job_id,
            tech_user_id=assignment.user_id,
            assigner_user_id=user_context.id,
        )
    db.commit()

    return job


# ---------------------------------------------------------------------------
# Shared logic: assign tech (upsert primary)
# ---------------------------------------------------------------------------


def _assign_tech_impl(
    job_id: UUID,
    data: JobTechAssignmentCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> JobTechAssignment:
    """Assign a technician to a job.

    Upsert semantics for role='primary':
      - If there is already an active primary assignment for this job+tenant,
        soft-delete it before creating the new one.
    For role='helper':
      - Simply create a new record (no uniqueness constraint to enforce here).
    """
    _get_job_or_404(job_id, db, user_context)

    if data.role not in ("primary", "helper"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{data.role}'. Valid values: ['primary', 'helper']",
        )
    if data.ordinal < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ordinal must be >= 1",
        )

    set_audit_context_sync(db, user_context.id)

    # Upsert: soft-delete existing active primary assignment (if assigning primary)
    if data.role == "primary":
        existing_primary = db.exec(
            select(JobTechAssignment)
            .where(JobTechAssignment.tenant_id == user_context.tenant_id)
            .where(JobTechAssignment.job_id == job_id)
            .where(JobTechAssignment.role == "primary")
            .where(JobTechAssignment.is_active == True)
        ).first()
        if existing_primary:
            existing_primary.is_active = False
            existing_primary.updated_by = user_context.id
            db.add(existing_primary)

    assigned_by = (
        data.assigned_by_user_id if data.assigned_by_user_id else user_context.id
    )

    assignment = JobTechAssignment(
        tenant_id=user_context.tenant_id,
        job_id=job_id,
        user_id=data.user_id,
        role=data.role,
        ordinal=data.ordinal,
        assigned_by_user_id=assigned_by,
        assigned_at=datetime.now(UTC),
        is_active=True,
        created_by=user_context.id,
    )
    db.add(assignment)

    # Task 1-C-3: Emit in-app notification if assigner ≠ tech
    _emit_job_assigned_notification(
        db=db,
        tenant_id=user_context.tenant_id,
        job_id=job_id,
        tech_user_id=data.user_id,
        assigner_user_id=assigned_by,
    )

    db.commit()
    db.refresh(assignment)
    return assignment


def _list_assignments_impl(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[JobTechAssignment]:
    """List all active assignments for a job."""
    _get_job_or_404(job_id, db, user_context)
    return db.exec(
        select(JobTechAssignment)
        .where(JobTechAssignment.tenant_id == user_context.tenant_id)
        .where(JobTechAssignment.job_id == job_id)
        .where(JobTechAssignment.is_active == True)
    ).all()


def _delete_assignment_impl(
    job_id: UUID,
    assignment_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """Soft-delete a specific job tech assignment."""
    _get_job_or_404(job_id, db, user_context)

    assignment = db.exec(
        select(JobTechAssignment)
        .where(JobTechAssignment.id == assignment_id)
        .where(JobTechAssignment.job_id == job_id)
        .where(JobTechAssignment.tenant_id == user_context.tenant_id)
    ).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    set_audit_context_sync(db, user_context.id)

    assignment.is_active = False
    assignment.updated_by = user_context.id
    db.add(assignment)
    db.commit()
    return {"message": "Assignment deactivated", "id": str(assignment_id)}


# ---------------------------------------------------------------------------
# TEST ENDPOINTS — Job Schedule & Assignments (register BEFORE authenticated)
# ---------------------------------------------------------------------------


@router.patch(
    "/jobs/{job_id}/schedule/test",
    response_model=JobResponse,
    summary="Update job schedule (test — no auth)",
)
def update_job_schedule_test(
    job_id: UUID,
    data: JobScheduleUpdate,
    db: Session = Depends(get_db),
):
    """Update a job's scheduled times — TEST ENDPOINT."""
    test_context = get_test_context()
    return _update_job_schedule_impl(job_id, data, db, test_context)


@router.post(
    "/jobs/{job_id}/assignments/test",
    response_model=JobTechAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign tech to job (test — no auth)",
)
def assign_tech_test(
    job_id: UUID,
    data: JobTechAssignmentCreate,
    db: Session = Depends(get_db),
):
    """Assign a technician to a job — TEST ENDPOINT."""
    test_context = get_test_context()
    return _assign_tech_impl(job_id, data, db, test_context)


@router.get(
    "/jobs/{job_id}/assignments/test",
    response_model=list[JobTechAssignmentResponse],
    summary="List job assignments (test — no auth)",
)
def list_assignments_test(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """List active assignments for a job — TEST ENDPOINT."""
    test_context = get_test_context()
    return _list_assignments_impl(job_id, db, test_context)


# FIND-155: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete(
    "/jobs/{job_id}/assignments/{assignment_id}/test",
    response_model=SoftDeleteResponse,
    summary="Soft-delete job assignment (test — no auth)",
)
def delete_assignment_test(
    job_id: UUID,
    assignment_id: UUID,
    db: Session = Depends(get_db),
):
    """Soft-delete a job assignment — TEST ENDPOINT."""
    test_context = get_test_context()
    return _delete_assignment_impl(job_id, assignment_id, db, test_context)


# ---------------------------------------------------------------------------
# AUTHENTICATED ENDPOINTS — Job Schedule & Assignments
# ---------------------------------------------------------------------------


@router.patch(
    "/jobs/{job_id}/schedule",
    response_model=JobResponse,
    summary="Update job schedule",
)
def update_job_schedule(
    job_id: UUID,
    data: JobScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
):
    """Update a job's scheduled times (requires ``schedule.manage``)."""
    return _update_job_schedule_impl(job_id, data, db, current_user)


@router.post(
    "/jobs/{job_id}/assignments",
    response_model=JobTechAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign tech to job",
)
def assign_tech(
    job_id: UUID,
    data: JobTechAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
):
    """Assign a technician to a job. Upserts primary role (requires ``schedule.manage``)."""
    return _assign_tech_impl(job_id, data, db, current_user)


@router.get(
    "/jobs/{job_id}/assignments",
    response_model=list[JobTechAssignmentResponse],
    summary="List job assignments",
)
def list_assignments(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.view_all")),
):
    """List active assignments for a job (requires ``schedule.view_all``)."""
    return _list_assignments_impl(job_id, db, current_user)


# FIND-155: Add response_model=SoftDeleteResponse to DELETE decorators
@router.delete(
    "/jobs/{job_id}/assignments/{assignment_id}",
    response_model=SoftDeleteResponse,
    summary="Soft-delete job assignment",
)
def delete_assignment(
    job_id: UUID,
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
):
    """Soft-delete a job assignment (requires ``schedule.manage``)."""
    return _delete_assignment_impl(job_id, assignment_id, db, current_user)


# ===========================================================================
# Task 1-B-3: Dispatch Board Query
# ===========================================================================


def _dispatch_board_impl(
    start_date: datetime,
    end_date: datetime,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> DispatchBoardResponse:
    """Build the dispatch board payload for the given date window.

    Algorithm:
    1. Fetch all active jobs whose ``scheduled_start_at`` falls within [start_date, end_date].
    2. For each job, look up its active primary ``JobTechAssignment``.
    3. Group jobs by their primary tech's ``user_id``.
    4. Jobs with no active primary assignment go into the ``unassigned`` bucket.
    5. For each tech: compute ETA to their first scheduled job (if they have GPS coords).

    FIND-115 (ETA at request time + Redis cache):
    - Fetches tech's latest stored GPS coordinates from DB.
    - Calls map_service.get_drive_time_minutes() with cached results (15-min TTL, Redis DB 0).
    - Returns eta_minutes_to_first_job (nullable if no GPS on file).

    Args:
        start_date: Inclusive start of the query window (must be timezone-aware).
        end_date:   Exclusive end of the query window (must be timezone-aware).
        db:         Database session.
        user_context: Authenticated user or test context — tenant scope enforced.

    Returns:
        ``DispatchBoardResponse`` with ``techs`` (ETA computed) and ``unassigned`` arrays.

    Raises:
        HTTPException 400: If ``end_date`` is not after ``start_date``.
    """
    from app.models.crm import Address, Customer, EntityAddress, Site
    from services.map_service import MapServiceError, get_drive_time_minutes

    if end_date <= start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be after start_date",
        )

    # Fetch jobs scheduled in the window (scheduled_start_at in [start_date, end_date])
    jobs = db.exec(
        select(Job)
        .where(Job.tenant_id == user_context.tenant_id)
        .where(Job.is_active == True)
        .where(Job.scheduled_start_at >= start_date)
        .where(Job.scheduled_start_at < end_date)
    ).all()

    if not jobs:
        return DispatchBoardResponse(
            start_date=start_date,
            end_date=end_date,
            techs=[],
            unassigned=[],
        )

    job_ids = [j.id for j in jobs]

    # DISPATCH-B1.25: Load ALL active assignments (primary + non-primary) in one query
    all_assignments = db.exec(
        select(JobTechAssignment)
        .where(JobTechAssignment.tenant_id == user_context.tenant_id)
        .where(JobTechAssignment.job_id.in_(job_ids))
        .where(JobTechAssignment.is_active == True)
    ).all()

    # DISPATCH-B1: Build a lookup: job_id → (user_id, assignment_id, assignment_version)
    # Derived from all_assignments filtered to primary role — jobs[] stays primary-only
    job_to_assignment: dict[UUID, tuple[UUID, UUID, int]] = {
        a.job_id: (a.user_id, a.id, a.version)
        for a in all_assignments
        if a.role == "primary"
    }
    # Backward-compat: job_id → tech_id (still used in tech group building below)
    job_to_tech: dict[UUID, UUID] = {
        a.job_id: a.user_id for a in all_assignments if a.role == "primary"
    }

    # DISPATCH-B1.25: Build non-primary map: tech_user_id → list[(job_id, role, assignment_id, version)]
    from collections import defaultdict

    non_primary_by_tech: dict[UUID, list[tuple[UUID, str, UUID, int]]] = defaultdict(
        list
    )
    for a in all_assignments:
        if a.role != "primary":
            non_primary_by_tech[a.user_id].append((a.job_id, a.role, a.id, a.version))

    # DISPATCH-B1: Batch-load customer names (one query, no N+1)
    customer_ids = {j.customer_id for j in jobs}
    customers = db.exec(select(Customer).where(Customer.id.in_(customer_ids))).all()
    customer_name_by_id: dict[UUID, str] = {c.id: c.display_name for c in customers}
    # CLASS-B1: customer.type for dispatch board enrichment
    customer_type_by_id: dict[UUID, str | None] = {c.id: c.type for c in customers}

    # DISPATCH-B1: Batch-load site addresses via polymorphic entity_address join (one query)
    site_ids = {j.site_id for j in jobs}
    site_address_rows = db.exec(
        select(EntityAddress, Address)
        .join(Address, Address.id == EntityAddress.address_id)
        .where(EntityAddress.entity_type_code == "site")
        .where(EntityAddress.entity_id.in_(site_ids))
        .where(EntityAddress.is_primary == True)
        .where(EntityAddress.is_active == True)
        .where(Address.is_active == True)
    ).all()
    # Compose a human-readable address string from line1/city/state
    site_address_by_id: dict[UUID, str | None] = {}
    for ea, addr in site_address_rows:
        parts = [p for p in [addr.line1, addr.city, addr.state] if p]
        site_address_by_id[ea.entity_id] = ", ".join(parts) if parts else None

    # DISPATCH-B1.5: Batch-load site names (one query, no N+1) — reuses site_ids from above
    sites = db.exec(select(Site).where(Site.id.in_(site_ids))).all()
    site_name_by_id: dict[UUID, str | None] = {s.id: s.name for s in sites}
    # CLASS-B1: site_type for dispatch board enrichment
    site_type_by_id: dict[UUID, str | None] = {s.id: s.site_type for s in sites}

    # CLASS-B1: Batch-load job_type code+label (one query, no N+1)
    from app.models.fulfillment import JobType

    job_type_ids = {j.job_type_id for j in jobs if j.job_type_id}
    job_type_code_by_id: dict[UUID, str] = {}
    job_type_label_by_id: dict[UUID, str] = {}
    if job_type_ids:
        job_types_for_board = db.exec(
            select(JobType).where(JobType.id.in_(job_type_ids))
        ).all()
        for jt in job_types_for_board:
            job_type_code_by_id[jt.id] = jt.code
            job_type_label_by_id[jt.id] = jt.label

    # DISPATCH-B1: Helper to build an enriched entry for a single job
    # DISPATCH-B1.25: Extended with role param so the same job renders with correct assignment_role
    def _build_entry(
        job: Job,
        *,
        role: str | None,
        assignment_id: UUID | None = None,
        assignment_version: int | None = None,
    ) -> DispatchBoardJobEntry:
        entry = DispatchBoardJobEntry.model_validate(job)
        entry.assignment_role = role
        if role == "primary":
            assignment = job_to_assignment.get(job.id)
            if assignment:
                _user_id, _aid, _aver = assignment
                entry.primary_assignment_id = _aid
                entry.assignment_version = _aver
        entry.customer_name = customer_name_by_id.get(job.customer_id)
        entry.site_name = site_name_by_id.get(job.site_id)
        entry.site_address = site_address_by_id.get(job.site_id)
        # entry.title stays None until JOB-UI-B1
        # CLASS-B1: Enrichment fields (priority already on the job row)
        entry.customer_type = customer_type_by_id.get(job.customer_id)
        entry.site_type = site_type_by_id.get(job.site_id)
        entry.job_type_code = (
            job_type_code_by_id.get(job.job_type_id) if job.job_type_id else None
        )
        entry.job_type_label = (
            job_type_label_by_id.get(job.job_type_id) if job.job_type_id else None
        )
        return entry

    # DISPATCH-B1.25: Build a job_by_id lookup for commitment entry construction
    job_by_id: dict[UUID, Job] = {j.id: j for j in jobs}

    # Group jobs by tech_id using enriched entries (primary only → jobs[] stays primary-only)
    tech_to_jobs: dict[UUID, list[DispatchBoardJobEntry]] = {}
    unassigned: list[DispatchBoardJobEntry] = []

    for job in jobs:
        entry = _build_entry(job, role="primary")
        tech_id = job_to_tech.get(job.id)
        if tech_id:
            tech_to_jobs.setdefault(tech_id, []).append(entry)
        else:
            # Unassigned: no primary tech — role=None
            entry.assignment_role = None
            unassigned.append(entry)

    # DISPATCH-B1.25: Union primary tech IDs with non-primary tech IDs so commitment-only
    # techs appear as a tech group (empty jobs[], populated additional_job_commitments).
    all_tech_ids: set[UUID] = set(tech_to_jobs.keys()) | set(non_primary_by_tech.keys())

    # Batch-fetch user profiles for ALL techs (primary + commitment-only)
    from app.models.core import User

    users = db.exec(select(User).where(User.id.in_(list(all_tech_ids)))).all()
    user_by_id: dict[UUID, User] = {u.id: u for u in users}

    # Build tech groups with ETA computation
    techs = []
    for tech_id in all_tech_ids:
        job_list = tech_to_jobs.get(tech_id, [])
        # FIND-115: Compute ETA to first job (sorted by scheduled_start_at)
        eta_minutes = None
        if job_list:
            first_job = min(
                job_list, key=lambda j: j.scheduled_start_at or datetime.max
            )
            try:
                # Fetch tech's current location (for MVP: using a hardcoded address lookup)
                # In production, this would fetch tech's latest mobile GPS coordinates
                tech_current_address = db.exec(
                    select(Address)
                    .where(Address.tenant_id == user_context.tenant_id)
                    .where(
                        Address.id == first_job.site_id
                    )  # Simplified: use site as origin
                    .where(Address.is_active == True)
                ).first()

                job_site_address = db.exec(
                    select(Address)
                    .where(Address.tenant_id == user_context.tenant_id)
                    .where(Address.id == first_job.site_id)
                    .where(Address.is_active == True)
                ).first()

                # Only compute ETA if both addresses are found and have GPS coordinates
                if tech_current_address and job_site_address:
                    if (
                        tech_current_address.latitude is not None
                        and tech_current_address.longitude is not None
                        and job_site_address.latitude is not None
                        and job_site_address.longitude is not None
                    ):
                        eta_minutes = get_drive_time_minutes(
                            db=db,
                            tenant_id=user_context.tenant_id,
                            origin_address_id=tech_current_address.id,
                            destination_address_id=job_site_address.id,
                        )
            except MapServiceError:
                # Gracefully handle ETA computation failures
                logger.warning(
                    f"ETA computation failed for tech {tech_id}, first_job {first_job.id}",
                    exc_info=True,
                )
                eta_minutes = None

        user = user_by_id.get(tech_id)
        tech_name = (
            f"{user.first_name or ''} {user.last_name or ''}".strip()
            if user
            else str(tech_id)
        )
        # DISPATCH-B1.25: Build additional_job_commitments for non-primary assignments
        commitments = [
            _build_entry(job_by_id[jid], role=role)
            for (jid, role, _aid, _ver) in non_primary_by_tech.get(tech_id, [])
            if jid in job_by_id
        ]
        techs.append(
            DispatchBoardTechGroup(
                tech_id=tech_id,
                id=tech_id,
                name=tech_name,
                display_color=user.display_color if user else None,
                avatar_url=None,  # profile_photo_s3_key requires S3 signing — deferred to Phase 2
                jobs=job_list,
                additional_job_commitments=commitments,
                eta_minutes_to_first_job=eta_minutes,
            )
        )

    return DispatchBoardResponse(
        start_date=start_date,
        end_date=end_date,
        techs=techs,
        unassigned=unassigned,
    )


# ---------------------------------------------------------------------------
# TEST ENDPOINT — Dispatch Board (register BEFORE authenticated)
# ---------------------------------------------------------------------------


@router.get(
    "/dispatch-board/test",
    response_model=DispatchBoardResponse,
    summary="Dispatch board query (test — no auth)",
)
def dispatch_board_test(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
):
    """Return the dispatch board grouped payload — TEST ENDPOINT.

    Blocked in staging/production. Returns HTTP 403 if ``TEST_ENDPOINT_ENABLED`` is false.

    Query params:
        start_date: ISO-8601 datetime (inclusive)
        end_date:   ISO-8601 datetime (exclusive)
    """
    test_context = get_test_context()
    return _dispatch_board_impl(start_date, end_date, db, test_context)


# ---------------------------------------------------------------------------
# AUTHENTICATED ENDPOINT — Dispatch Board
# ---------------------------------------------------------------------------


@router.get(
    "/dispatch-board",
    response_model=DispatchBoardResponse,
    summary="Dispatch board query",
)
def dispatch_board(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.view_all")),
):
    """Return the dispatch board grouped payload (requires ``schedule.view_all``).

    Query params:
        start_date: ISO-8601 datetime (inclusive)
        end_date:   ISO-8601 datetime (exclusive)
    """
    return _dispatch_board_impl(start_date, end_date, db, current_user)


# ===========================================================================
# Task 1-B-4: Conflict Detection
# ===========================================================================


def _conflict_check_impl(
    data: ConflictCheckRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ConflictCheckResponse:
    """Shared conflict detection logic.

    Delegates to ``scheduling_service.check_slot_feasibility`` and adapts the
    result dict back to the Pydantic response schema.
    """
    from services.scheduling_service import check_slot_feasibility

    if data.proposed_end <= data.proposed_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="proposed_end must be after proposed_start",
        )

    result = check_slot_feasibility(
        db=db,
        tenant_id=user_context.tenant_id,
        tech_user_id=data.tech_user_id,
        proposed_start=data.proposed_start,
        proposed_end=data.proposed_end,
        exclude_job_id=data.exclude_job_id,
    )

    return ConflictCheckResponse(**result)


# ---------------------------------------------------------------------------
# TEST ENDPOINT — Conflict Check (register BEFORE authenticated)
# ---------------------------------------------------------------------------


@router.post(
    "/conflict-check/test",
    response_model=ConflictCheckResponse,
    summary="Check slot feasibility (test — no auth)",
)
def conflict_check_test(
    data: ConflictCheckRequest,
    db: Session = Depends(get_db),
):
    """Validate a proposed job slot for a technician — TEST ENDPOINT.

    Blocked in staging/production. Returns HTTP 403 if ``TEST_ENDPOINT_ENABLED`` is false.
    """
    test_context = get_test_context()
    return _conflict_check_impl(data, db, test_context)


# ---------------------------------------------------------------------------
# AUTHENTICATED ENDPOINT — Conflict Check
# ---------------------------------------------------------------------------


@router.post(
    "/conflict-check",
    response_model=ConflictCheckResponse,
    summary="Check slot feasibility",
)
def conflict_check(
    data: ConflictCheckRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
):
    """Validate a proposed job slot for a technician (requires ``schedule.manage``)."""
    return _conflict_check_impl(data, db, current_user)


# ===========================================================================
# B3/A19 — Job Move (Optimistic Locking) + Check-Conflicts + SSE Stream
# ===========================================================================

from datetime import datetime
from uuid import UUID

from fastapi import Query
from fastapi.responses import StreamingResponse

from app.models.scheduling import JobTechAssignment
from services.scheduling_service import check_slot_feasibility

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class JobMoveRequest(BaseModel):
    tech_user_id: UUID
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    expected_job_version: int
    expected_assignment_version: int | None = None


class JobMoveResponse(BaseModel):
    job_id: str
    job_version: int
    assignment_id: str | None
    assignment_version: int | None
    tech_user_id: str
    scheduled_start_at: str
    scheduled_end_at: str
    conflicts: list[dict]


class JobCheckConflictRequest(BaseModel):
    tech_user_id: UUID
    scheduled_start_at: datetime
    scheduled_end_at: datetime


class JobCheckConflictResponse(BaseModel):
    is_feasible: bool
    conflicts: list[dict]
    drive_time_to_next_minutes: int | None = None
    drive_time_from_prev_minutes: int | None = None


# ---------------------------------------------------------------------------
# Shared implementation: job move
# ---------------------------------------------------------------------------


def _job_move_impl(
    job_id: UUID,
    body: JobMoveRequest,
    db: Session,
    user_context,
) -> JobMoveResponse:
    """Atomic job reassign + reschedule with optimistic locking (§16.4 pattern)."""
    from app.models.fulfillment import Job

    # Tenant-scoped load — IDOR-safe (§16.3)
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
        .where(Job.is_active == True)
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Optimistic lock check on job
    if job.version != body.expected_job_version:
        raise HTTPException(
            status_code=409,
            detail={
                "type": "https://pilotfortrades.com/errors/conflict",
                "title": "Concurrent Modification",
                "status": 409,
                "detail": "Job was modified by another user. Review the refreshed state.",
                "current_job_version": job.version,
                "current_state": {
                    "scheduled_start_at": job.scheduled_start_at.isoformat()
                    if job.scheduled_start_at
                    else None,
                    "scheduled_end_at": job.scheduled_end_at.isoformat()
                    if job.scheduled_end_at
                    else None,
                },
            },
        )

    # Fetch the active primary assignment for this job (if any)
    assignment = db.exec(
        select(JobTechAssignment)
        .where(JobTechAssignment.job_id == job_id)
        .where(JobTechAssignment.tenant_id == user_context.tenant_id)
        .where(JobTechAssignment.role == "primary")
        .where(JobTechAssignment.is_active == True)
    ).first()

    # Optimistic lock check on assignment (if client sent expected version)
    if assignment and body.expected_assignment_version is not None:
        if assignment.version != body.expected_assignment_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "https://pilotfortrades.com/errors/conflict",
                    "title": "Concurrent Modification",
                    "status": 409,
                    "detail": "Assignment was modified by another user.",
                    "current_assignment_version": assignment.version,
                },
            )

    # Conflict check before committing
    conflict_result = check_slot_feasibility(
        db=db,
        tenant_id=user_context.tenant_id,
        tech_user_id=body.tech_user_id,
        proposed_start=body.scheduled_start_at,
        proposed_end=body.scheduled_end_at,
        exclude_job_id=job_id,
    )

    set_audit_context_sync(db, user_context.id)

    # Update job times + bump version
    job.scheduled_start_at = body.scheduled_start_at
    job.scheduled_end_at = body.scheduled_end_at
    job.version += 1
    db.add(job)

    # Soft-delete old assignment + create new one for new tech
    new_assignment_id = None
    new_assignment_version = None

    if assignment:
        if str(assignment.user_id) != str(body.tech_user_id):
            # Tech changed — soft-delete old, create new
            assignment.is_active = False
            assignment.version += 1
            db.add(assignment)
            new_assignment = JobTechAssignment(
                tenant_id=user_context.tenant_id,
                job_id=job_id,
                user_id=body.tech_user_id,
                assigned_by_user_id=user_context.id,
                role="primary",
                ordinal=1,
                assigned_at=datetime.now(UTC),
                is_active=True,
                version=1,
            )
            db.add(new_assignment)
            db.flush()
            db.refresh(new_assignment)
            new_assignment_id = str(new_assignment.id)
            new_assignment_version = new_assignment.version
        else:
            # Same tech — just bump version
            assignment.version += 1
            db.add(assignment)
            new_assignment_id = str(assignment.id)
            new_assignment_version = assignment.version
    else:
        # No existing assignment — create one
        new_assignment = JobTechAssignment(
            tenant_id=user_context.tenant_id,
            job_id=job_id,
            user_id=body.tech_user_id,
            assigned_by_user_id=user_context.id,
            role="primary",
            ordinal=1,
            assigned_at=datetime.now(UTC),
            is_active=True,
            version=1,
        )
        db.add(new_assignment)
        db.flush()
        db.refresh(new_assignment)
        new_assignment_id = str(new_assignment.id)
        new_assignment_version = new_assignment.version

    db.commit()
    db.refresh(job)

    return JobMoveResponse(
        job_id=str(job.id),
        job_version=job.version,
        assignment_id=new_assignment_id,
        assignment_version=new_assignment_version,
        tech_user_id=str(body.tech_user_id),
        scheduled_start_at=job.scheduled_start_at.isoformat(),
        scheduled_end_at=job.scheduled_end_at.isoformat(),
        conflicts=conflict_result.get("conflicts", []),
    )


# ---------------------------------------------------------------------------
# Shared implementation: check-conflicts (preview-only)
# ---------------------------------------------------------------------------


def _check_conflicts_impl(
    job_id: UUID,
    body: JobCheckConflictRequest,
    db: Session,
    user_context,
) -> JobCheckConflictResponse:
    """Preview-only conflict check. No commit, no version bump, no SSE event."""
    result = check_slot_feasibility(
        db=db,
        tenant_id=user_context.tenant_id,
        tech_user_id=body.tech_user_id,
        proposed_start=body.scheduled_start_at,
        proposed_end=body.scheduled_end_at,
        exclude_job_id=job_id,
    )
    return JobCheckConflictResponse(**result)


# ---------------------------------------------------------------------------
# TEST endpoints (register BEFORE authenticated)
# ---------------------------------------------------------------------------


@router.post(
    "/jobs/{job_id}/move/test",
    response_model=JobMoveResponse,
    status_code=200,
    summary="[TEST] Move/reassign a job — no auth required",
)
def job_move_test(
    job_id: UUID,
    body: JobMoveRequest,
    db: Session = Depends(get_db),
) -> JobMoveResponse:
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _job_move_impl(job_id, body, db, test_context)


@router.post(
    "/jobs/{job_id}/check-conflicts/test",
    response_model=JobCheckConflictResponse,
    status_code=200,
    summary="[TEST] Preview conflict check — no auth required",
)
def check_conflicts_test(
    job_id: UUID,
    body: JobCheckConflictRequest,
    db: Session = Depends(get_db),
) -> JobCheckConflictResponse:
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _check_conflicts_impl(job_id, body, db, test_context)


# ---------------------------------------------------------------------------
# AUTHENTICATED endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/jobs/{job_id}/move",
    response_model=JobMoveResponse,
    status_code=200,
    summary="Move/reassign a job (optimistic locking)",
)
def job_move(
    job_id: UUID,
    body: JobMoveRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
) -> JobMoveResponse:
    """Atomic job reassign + reschedule with optimistic concurrency (§7.9)."""
    return _job_move_impl(job_id, body, db, current_user)


@router.post(
    "/jobs/{job_id}/check-conflicts",
    response_model=JobCheckConflictResponse,
    status_code=200,
    summary="Preview conflict check for a proposed job slot",
)
def check_conflicts(
    job_id: UUID,
    body: JobCheckConflictRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.manage")),
) -> JobCheckConflictResponse:
    """Preview-only conflict check. No state change, no SSE event."""
    return _check_conflicts_impl(job_id, body, db, current_user)


# ---------------------------------------------------------------------------
# FIND-117: Job Schedule History Endpoint
# ---------------------------------------------------------------------------


def _get_job_schedule_history_impl(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    limit: int = 50,
    offset: int = 0,
) -> ScheduleHistoryResponse:
    """Shared logic for retrieving the schedule change history for a specific job."""
    job = db.exec(
        select(Job).where(Job.id == job_id, Job.tenant_id == user_context.tenant_id)
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found in tenant {user_context.tenant_id}",
        )

    scheduling_fields = {"scheduled_start", "assigned_tech_id", "status"}

    base_query = (
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == user_context.tenant_id,
            AuditEvent.entity_name == "job",
            AuditEvent.entity_id == str(job_id),
        )
        .order_by(AuditEvent.occurred_at.asc())
    )

    total_count = db.exec(
        select(AuditEvent).where(
            AuditEvent.tenant_id == user_context.tenant_id,
            AuditEvent.entity_name == "job",
            AuditEvent.entity_id == str(job_id),
        )
    ).all()

    events = db.exec(base_query.offset(offset).limit(limit)).all()

    entries: list[ScheduleHistoryEntry] = []
    for event in events:
        if event.action in ("UPDATE", "DELETE"):
            if event.old_values and event.new_values:
                for field_name in scheduling_fields:
                    old_val = event.old_values.get(field_name)
                    new_val = event.new_values.get(field_name)
                    if old_val != new_val:
                        entries.append(
                            ScheduleHistoryEntry(
                                changed_at=event.occurred_at,
                                changed_by_user_id=event.user_id,
                                field_name=field_name,
                                old_value=old_val,
                                new_value=new_val,
                            )
                        )

    return ScheduleHistoryResponse(
        job_id=job_id,
        entries=entries,
        total=len(total_count),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/jobs/{job_id}/history/test",
    response_model=ScheduleHistoryResponse,
    status_code=200,
    summary="Get scheduling history for a job (TEST — no auth)",
)
def get_job_schedule_history_test(
    job_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> ScheduleHistoryResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_job_schedule_history_impl(
        job_id, db, test_context, limit=limit, offset=offset
    )


@router.get(
    "/jobs/{job_id}/history",
    response_model=ScheduleHistoryResponse,
    status_code=200,
    summary="Get scheduling history for a job",
)
def get_job_schedule_history(
    job_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("schedule.view_all")),
) -> ScheduleHistoryResponse:
    """Get job schedule change history. RBAC: schedule.view_all."""
    return _get_job_schedule_history_impl(
        job_id, db, current_user, limit=limit, offset=offset
    )


# ---------------------------------------------------------------------------
# SSE endpoint — GET /board/stream
# ---------------------------------------------------------------------------


@router.get(
    "/board/stream",
    summary="Dispatch board SSE stream (JWT via ?token= query param)",
    response_class=StreamingResponse,
)
async def board_stream(
    token: str = Query(
        ..., description="JWT for SSE auth (cannot use headers with EventSource)"
    ),
    last_event_id: str | None = Query(None, alias="lastEventId"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Open a Server-Sent Events stream for the dispatch board.

    JWT passed as ?token= because browser EventSource cannot set Authorization headers.
    Permission required: schedule.manage or schedule.view_all.
    """
    from core.sse_middleware import validate_sse_token
    from services.dispatch_board_stream import sse_event_generator

    user = validate_sse_token(token, db)

    # Permission check
    if not user.has_permission("schedule.manage") and not user.has_permission(
        "schedule.view_all"
    ):
        raise HTTPException(
            status_code=403,
            detail="Requires schedule.manage or schedule.view_all permission.",
        )

    try:
        import redis.asyncio as aioredis

        from core.config import settings

        redis_client = aioredis.from_url(settings.REDIS_URL)
    except Exception:
        redis_client = None

    if redis_client is None:
        raise HTTPException(
            status_code=503,
            detail="SSE stream unavailable: Redis not configured.",
        )

    async def event_stream():
        try:
            async for chunk in sse_event_generator(
                redis_client=redis_client,
                tenant_id=str(user.tenant_id),
                user_id=str(user.id),
                last_event_id=last_event_id,
            ):
                yield chunk
        finally:
            await redis_client.aclose()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
