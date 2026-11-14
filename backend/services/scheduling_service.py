"""
Scheduling Services — Tasks 1-B-4 & 1-C-2

Task 1-B-4 — Conflict Detection Service
  Validates a proposed job time slot against:
  1. The assigned tech's ``tech_availability`` records (PTO / unavailable blocks).
  2. The assigned tech's other active scheduled jobs (double-booking).

Task 1-C-2 — Sequence Feasibility Check
  Integrates ``map_service`` to flag insufficient drive time between consecutive
  jobs for a single technician.  The algorithm:

  1. Fetch all active primary assignments for the tech on the calendar window that
     brackets the proposed slot (same-day ± buffer to capture adjacent jobs on
     neighbouring days).
  2. Collect their ``scheduled_start_at`` / ``scheduled_end_at`` and resolve each job's
     primary site address via the polymorphic ``entity_address`` table.
  3. Insert the proposed slot (with its site's address) into that ordered list.
  4. For every pair of adjacent jobs (predecessor → proposed, proposed → successor),
     call ``map_service.get_drive_time_minutes()`` to obtain drive time.
  5. Flag any pair where ``gap_minutes < drive_time_minutes`` as a drive-time
     conflict.

Returns a ``SequenceFeasibilityResult`` dict that is merged into the overall
conflict check response by API callers.
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.models.crm import EntityAddress
from app.models.fulfillment import Job
from app.models.scheduling import JobTechAssignment, TechAvailability
from services.map_service import MapServiceError, get_drive_time_minutes

logger = logging.getLogger(__name__)


def check_slot_feasibility(
    db: Session,
    tenant_id: UUID,
    tech_user_id: UUID,
    proposed_start: datetime,
    proposed_end: datetime,
    exclude_job_id: UUID | None = None,
) -> dict:
    """Validate a proposed job slot for a technician.

    Checks two types of conflicts:

    1. **Availability block conflicts** — any active ``TechAvailability`` record
       of type ``'pto'`` or ``'unavailable'`` that overlaps the proposed window.
       Overlap condition: ``starts_at < proposed_end AND ends_at > proposed_start``.

    2. **Double-booking conflicts** — any other active scheduled job whose primary
       tech is ``tech_user_id`` and whose ``[scheduled_start_at, scheduled_end_at)`` range
       overlaps the proposed window.  The ``exclude_job_id`` parameter lets callers
       skip the job being edited (to avoid self-conflict on updates).

    Args:
        db:              Open SQLModel session.
        tenant_id:       Tenant scope — enforces IDOR isolation.
        tech_user_id:    UUID of the technician being evaluated.
        proposed_start:  Inclusive start of the proposed slot (timezone-aware).
        proposed_end:    Exclusive end of the proposed slot (timezone-aware).
        exclude_job_id:  Optional job to exclude from double-booking check (edit case).

    Returns:
        dict with keys:
            ``is_feasible`` (bool)
            ``conflicts``   (list of dicts with ``conflict_type``, ``description``,
                            and optional ``conflicting_entity_id``)
    """
    conflicts = []

    # ------------------------------------------------------------------
    # 1. Availability block conflicts (PTO / unavailable)
    # ------------------------------------------------------------------
    blocking_records = db.exec(
        select(TechAvailability)
        .where(TechAvailability.tenant_id == tenant_id)
        .where(TechAvailability.user_id == tech_user_id)
        .where(TechAvailability.is_active == True)
        .where(TechAvailability.availability_type.in_(["pto", "unavailable"]))
        # Overlap: block.starts_at < proposed_end AND block.ends_at > proposed_start
        .where(TechAvailability.starts_at < proposed_end)
        .where(TechAvailability.ends_at > proposed_start)
    ).all()

    for block in blocking_records:
        conflicts.append(
            {
                "conflict_type": "availability_block",
                "description": (
                    f"Tech has an active '{block.availability_type}' block "
                    f"from {block.starts_at.isoformat()} to {block.ends_at.isoformat()}"
                ),
                "conflicting_entity_id": str(block.id),
            }
        )

    # ------------------------------------------------------------------
    # 2. Double-booking conflicts
    # ------------------------------------------------------------------
    # Find other jobs where this tech is the active primary assignee
    # and the scheduled window overlaps the proposed slot.
    primary_assignments = db.exec(
        select(JobTechAssignment)
        .where(JobTechAssignment.tenant_id == tenant_id)
        .where(JobTechAssignment.user_id == tech_user_id)
        .where(JobTechAssignment.role == "primary")
        .where(JobTechAssignment.is_active == True)
    ).all()

    assigned_job_ids = [a.job_id for a in primary_assignments]

    if assigned_job_ids:
        # Fetch those jobs and filter for schedule overlap
        overlapping_jobs = db.exec(
            select(Job)
            .where(Job.tenant_id == tenant_id)
            .where(Job.id.in_(assigned_job_ids))
            .where(Job.is_active == True)
            .where(Job.scheduled_start_at != None)
            .where(Job.scheduled_end_at != None)
            # Overlap: job.scheduled_start_at < proposed_end AND job.scheduled_end_at > proposed_start
            .where(Job.scheduled_start_at < proposed_end)
            .where(Job.scheduled_end_at > proposed_start)
        ).all()

        for conflicting_job in overlapping_jobs:
            # Skip the job being edited (exclude_job_id)
            if exclude_job_id and str(conflicting_job.id) == str(exclude_job_id):
                continue
            conflicts.append(
                {
                    "conflict_type": "double_booking",
                    "description": (
                        f"Tech is already assigned to job {conflicting_job.id} "
                        f"scheduled from {conflicting_job.scheduled_start_at.isoformat()} "
                        f"to {conflicting_job.scheduled_end_at.isoformat()}"
                    ),
                    "conflicting_entity_id": str(conflicting_job.id),
                }
            )

    return {
        "is_feasible": len(conflicts) == 0,
        "tech_user_id": str(tech_user_id),
        "proposed_start": proposed_start.isoformat(),
        "proposed_end": proposed_end.isoformat(),
        "conflicts": conflicts,
    }


# ---------------------------------------------------------------------------
# Task 1-C-2: Sequence Feasibility Check
# ---------------------------------------------------------------------------

# How far around the proposed slot we look for adjacent jobs (in days).
# Covers overnight jobs that straddle midnight.
_SEQUENCE_WINDOW_DAYS = 2


def _get_primary_address_id_for_site(
    db: Session, tenant_id: UUID, site_id: UUID
) -> UUID | None:
    """Return the primary active address UUID for a site, or None.

    Uses the polymorphic ``entity_address`` table with ``entity_type_code='site'``.
    Returns the first ``is_primary=True, is_active=True`` address.  If no primary
    address exists, falls back to any active address linked to the site.
    """
    # Try primary address first
    row = db.exec(
        select(EntityAddress)
        .where(EntityAddress.tenant_id == tenant_id)
        .where(EntityAddress.entity_type_code == "site")
        .where(EntityAddress.entity_id == site_id)
        .where(EntityAddress.is_primary == True)
        .where(EntityAddress.is_active == True)
        .limit(1)
    ).first()

    if row:
        return row.address_id

    # Fallback: any active address
    row = db.exec(
        select(EntityAddress)
        .where(EntityAddress.tenant_id == tenant_id)
        .where(EntityAddress.entity_type_code == "site")
        .where(EntityAddress.entity_id == site_id)
        .where(EntityAddress.is_active == True)
        .limit(1)
    ).first()

    return row.address_id if row else None


def check_sequence_feasibility(
    db: Session,
    tenant_id: UUID,
    tech_user_id: UUID,
    proposed_start: datetime,
    proposed_end: datetime,
    proposed_site_id: UUID | None = None,
    exclude_job_id: UUID | None = None,
    map_provider: str | None = None,
) -> dict:
    """Validate that a technician has sufficient drive time between consecutive jobs.

    Algorithm
    ---------
    1. Fetch all active primary assignments for the tech within a ±``_SEQUENCE_WINDOW_DAYS``
       window around the proposed slot.
    2. Resolve each job's primary site address via ``entity_address``.
    3. Insert the proposed slot at its sorted position in the sequence.
    4. For every adjacent pair (predecessor → proposed, proposed → successor),
       call ``map_service.get_drive_time_minutes()``.
    5. Flag any pair where ``gap_minutes < drive_time_minutes``.

    Map errors (missing addresses, API failures) are treated as **soft warnings**
    (``warning`` conflict type) rather than hard failures so that scheduling is
    never blocked by missing address data.

    Args:
        db:                 Open SQLModel session.
        tenant_id:          Tenant scope for IDOR isolation.
        tech_user_id:       UUID of the technician being evaluated.
        proposed_start:     Inclusive start of the proposed slot (timezone-aware).
        proposed_end:       Exclusive end of the proposed slot (timezone-aware).
        proposed_site_id:   Optional site UUID for the proposed job.  When ``None``
                            the drive-time check from/to the proposed slot is skipped
                            (no address to resolve).
        exclude_job_id:     Optional job to exclude (edit-existing-job scenario).
        map_provider:       Override the map provider (``"google"`` or ``"mock"``).
                            Defaults to ``settings.MAP_PROVIDER``.

    Returns:
        dict with keys:
            ``is_feasible``  (bool)
            ``conflicts``    (list of dicts — conflict_type: ``"drive_time"`` or
                             ``"drive_time_warning"``, ``description``, optional
                             ``conflicting_entity_id`` (the predecessor/successor job id))
    """
    conflicts: list[dict] = []

    # --- 1. Fetch adjacent primary assignments in the window ------------------
    window_start = proposed_start - timedelta(days=_SEQUENCE_WINDOW_DAYS)
    window_end = proposed_end + timedelta(days=_SEQUENCE_WINDOW_DAYS)

    primary_assignments = db.exec(
        select(JobTechAssignment)
        .where(JobTechAssignment.tenant_id == tenant_id)
        .where(JobTechAssignment.user_id == tech_user_id)
        .where(JobTechAssignment.role == "primary")
        .where(JobTechAssignment.is_active == True)
    ).all()

    assigned_job_ids = [a.job_id for a in primary_assignments]

    if not assigned_job_ids:
        return {"is_feasible": True, "conflicts": []}

    # --- 2. Fetch scheduled jobs in the window --------------------------------
    scheduled_jobs = db.exec(
        select(Job)
        .where(Job.tenant_id == tenant_id)
        .where(Job.id.in_(assigned_job_ids))
        .where(Job.is_active == True)
        .where(Job.scheduled_start_at != None)
        .where(Job.scheduled_end_at != None)
        .where(Job.scheduled_start_at >= window_start)
        .where(Job.scheduled_start_at <= window_end)
    ).all()

    # Exclude the job being edited
    scheduled_jobs = [j for j in scheduled_jobs if j.id != exclude_job_id]

    if not scheduled_jobs and proposed_site_id is None:
        # No adjacent jobs and no site to check from/to → trivially feasible
        return {"is_feasible": True, "conflicts": []}

    # --- 3. Build sorted sequence with the proposed slot ---------------------
    # Each entry: (scheduled_start_at, scheduled_end_at, job_id_or_None, site_id_or_None)
    SlotTuple = tuple  # (start, end, job_id, site_id)

    sequence: list[SlotTuple] = []
    for job in scheduled_jobs:
        sequence.append(
            (job.scheduled_start_at, job.scheduled_end_at, job.id, job.site_id)
        )

    # Insert proposed slot (job_id=None marks it as the proposal)
    sequence.append((proposed_start, proposed_end, None, proposed_site_id))

    # Sort by start time
    sequence.sort(key=lambda t: t[0])

    # --- 4 & 5. Check drive time for each adjacent pair ----------------------
    proposed_index = next(i for i, s in enumerate(sequence) if s[2] is None)

    pairs_to_check: list[tuple[SlotTuple, SlotTuple]] = []
    if proposed_index > 0:
        pairs_to_check.append((sequence[proposed_index - 1], sequence[proposed_index]))
    if proposed_index < len(sequence) - 1:
        pairs_to_check.append((sequence[proposed_index], sequence[proposed_index + 1]))

    for predecessor, successor in pairs_to_check:
        pred_end: datetime = predecessor[1]
        succ_start: datetime = successor[0]
        gap_minutes = (succ_start - pred_end).total_seconds() / 60.0

        # Skip negative or zero gaps — those are already caught by double-booking
        if gap_minutes <= 0:
            continue

        pred_job_id = predecessor[2]
        pred_site_id = predecessor[3]
        succ_job_id = successor[2]
        succ_site_id = successor[3]

        # Resolve address IDs
        origin_address_id: UUID | None = None
        dest_address_id: UUID | None = None

        if pred_site_id is not None:
            origin_address_id = _get_primary_address_id_for_site(
                db, tenant_id, pred_site_id
            )
        if succ_site_id is not None:
            dest_address_id = _get_primary_address_id_for_site(
                db, tenant_id, succ_site_id
            )

        if origin_address_id is None or dest_address_id is None:
            # Soft warning: cannot check without addresses
            conflicts.append(
                {
                    "conflict_type": "drive_time_warning",
                    "description": (
                        "Drive time check skipped: one or both jobs lack a primary "
                        "site address.  Verify manually."
                    ),
                    "conflicting_entity_id": str(pred_job_id or succ_job_id),
                }
            )
            continue

        try:
            drive_minutes = get_drive_time_minutes(
                db,
                tenant_id,
                origin_address_id,
                dest_address_id,
                provider=map_provider,
            )
        except MapServiceError as exc:
            # Soft warning: map provider unavailable
            logger.warning(
                "scheduling_service.sequence: map_service error — %s "
                "(pred_job=%s, succ_job=%s)",
                exc,
                pred_job_id,
                succ_job_id,
            )
            conflicts.append(
                {
                    "conflict_type": "drive_time_warning",
                    "description": f"Drive time check failed: {exc}. Verify manually.",
                    "conflicting_entity_id": str(pred_job_id or succ_job_id),
                }
            )
            continue

        if gap_minutes < drive_minutes:
            # The job that is not the proposal is the conflicting entity
            conflicting_id = pred_job_id if succ_job_id is None else succ_job_id
            conflicts.append(
                {
                    "conflict_type": "drive_time",
                    "description": (
                        f"Insufficient drive time: gap is {gap_minutes:.0f} min "
                        f"but estimated drive is {drive_minutes} min."
                    ),
                    "conflicting_entity_id": str(conflicting_id),
                    "gap_minutes": round(gap_minutes),
                    "drive_time_minutes": drive_minutes,
                }
            )
        else:
            logger.debug(
                "scheduling_service.sequence: OK — gap %d min ≥ drive %d min "
                "(pred_job=%s, succ_job=%s)",
                gap_minutes,
                drive_minutes,
                pred_job_id,
                succ_job_id,
            )

    return {
        "is_feasible": all(c["conflict_type"] != "drive_time" for c in conflicts),
        "conflicts": conflicts,
    }
