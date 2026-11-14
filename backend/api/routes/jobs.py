import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Date as SADate
from sqlalchemy import cast, text
from sqlmodel import Session, select

from api.schemas.invoice_signoff import (
    DEFAULT_SIGNOFF_TERMS,
    InvoiceSignoffSummary,
    SignoffContextInvoice,
    SignoffContextResponse,
)
from api.schemas.schemas import (
    JOB_PRIORITY_VALUES,
    BillableExpense,
    BillableItemsResponse,
    BillableTimeEntry,
    ChangeOrderCreate,
    ChangeOrderLineCreate,
    ChangeOrderLineResponse,
    ChangeOrderLineUpdate,
    ChangeOrderResponse,
    ChangeOrderUpdate,
    JobCreate,
    JobExpenseCreate,
    JobExpenseResponse,
    JobListItem,
    JobNotesResponse,
    JobNotesUpdate,
    JobResponse,
    JobTimeEntryCreate,
    JobTimeEntryResponse,
    JobUpdate,
    LotoConfirmationCreate,
    LotoConfirmationRead,
    PaginatedJobListResponse,
)
from app.models.billing import Invoice, InvoiceSignoff, InvoiceStatus
from app.models.catalog import TenantMarkupVersion
from app.models.core import User
from app.models.crm import Customer, Site
from app.models.fulfillment import (
    Job,
    JobExpense,
    JobNotes,
    JobStatus,
    JobTimeEntry,
    JobType,
    LotoConfirmation,
)
from app.models.quoting import ChangeOrder, ChangeOrderLine, Quote
from app.models.scheduling import JobTechAssignment
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ==================== SHARED BUSINESS LOGIC ====================


def _generate_job_number(tenant_id: UUID, db: Session) -> str:
    """
    Generate a sequential job number for the tenant: JOB-000001, JOB-000002, ...
    Uses MAX(numeric suffix) + 1 scoped to tenant_id.
    Retries up to 5 times on unique constraint violation (race condition guard).
    Format: JOB-000001 (sequential, tenant-scoped, zero-padded 6 digits)
    """
    from sqlalchemy import text as sa_text

    for _ in range(5):
        result = db.exec(
            sa_text(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(job_number FROM 5) AS INTEGER)), 0) + 1 "
                "FROM job WHERE tenant_id = :tid"
            ).bindparams(tid=str(tenant_id))
        ).first()
        next_num = result[0] if result else 1
        job_number = f"JOB-{str(next_num).zfill(6)}"
        existing = db.exec(
            select(Job).where(
                Job.tenant_id == tenant_id,
                Job.job_number == job_number,
            )
        ).first()
        if not existing:
            return job_number
    raise ValueError("Unable to generate unique job_number after 5 attempts")


def _create_job_impl(
    job_in: JobCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Job:
    """
    Shared job creation logic used by both authenticated and test endpoints.

    Args:
        job_in: Job data to create
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        Created Job instance

    Raises:
        HTTPException: If customer, site not found or validation fails

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    # CLASS-B1: Validate priority if provided
    priority = job_in.priority if job_in.priority else "standard"
    if priority not in JOB_PRIORITY_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/invalid-priority",
                "title": "Invalid job priority",
                "status": 422,
                "detail": f"'{priority}' is not a valid priority. Must be one of: {sorted(JOB_PRIORITY_VALUES)}",
            },
        )

    # JOB-UI-B1: Resolve title — use provided, or default from quote.title if linked
    resolved_title = job_in.title
    if resolved_title is None and job_in.quote_id is not None:
        linked_quote = db.exec(
            select(Quote)
            .where(Quote.id == job_in.quote_id)
            .where(Quote.tenant_id == user_context.tenant_id)
        ).first()
        if linked_quote and linked_quote.title:
            resolved_title = linked_quote.title

    # Verify customer and site belong to tenant
    customer = db.exec(
        select(Customer)
        .where(Customer.id == job_in.customer_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    site = db.exec(
        select(Site)
        .where(Site.id == job_in.site_id)
        .where(Site.tenant_id == user_context.tenant_id)
    ).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if site.customer_id != customer.id:
        raise HTTPException(
            status_code=400, detail="Site does not belong to the selected customer"
        )

    # Find default job status
    job_status = db.exec(
        select(JobStatus)
        .where(
            (JobStatus.tenant_id == user_context.tenant_id)
            | (JobStatus.tenant_id == None)
        )
        .where(JobStatus.is_default == True)
        .order_by(JobStatus.tenant_id)  # Prefer tenant-specific over global
    ).first()

    if not job_status:
        # Fallback if no default exists
        job_status = db.exec(select(JobStatus)).first()
        if not job_status:
            raise HTTPException(
                status_code=500, detail="No job statuses available in the system"
            )

    job = Job(
        tenant_id=user_context.tenant_id,
        customer_id=job_in.customer_id,
        site_id=job_in.site_id,
        quote_id=job_in.quote_id,
        status_id=job_status.id,
        scheduled_start_at=job_in.scheduled_start_at,
        scheduled_end_at=job_in.scheduled_end_at,
        estimated_duration_minutes=job_in.estimated_duration_minutes,
        external_calendar_event_id=job_in.external_calendar_event_id,
        job_number=_generate_job_number(user_context.tenant_id, db),
        # CLASS-B1: Priority and job type classification
        priority=priority,
        job_type_id=job_in.job_type_id,
        # JOB-UI-B1: Human-readable title (may be defaulted from quote)
        title=resolved_title,
    )

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _list_jobs_impl(
    skip: int,
    limit: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    tech_id: str | None = None,
    scheduled_date: str | None = None,
    status: str | None = None,
    customer_search: str | None = None,
    scheduled_from: datetime | None = None,
    scheduled_to: datetime | None = None,
    offset: int = 0,
    customer_id: uuid.UUID | None = None,
) -> PaginatedJobListResponse:
    """
    Shared job listing logic used by both authenticated and test endpoints.

    UI-FIX-1C: Returns PaginatedJobListResponse with total count.
    MOB-B1-BE additions:
    - tech_id: Optional filter — returns only jobs where job_tech_assignment.user_id = tech_id
    - scheduled_date: Optional YYYY-MM-DD filter — filters on DATE(scheduled_start_at)
    - status_code: Denormalized from job_status JOIN
    - customer_name: Denormalized from customer JOIN (IDOR-protected by tenant_id filter)

    Args:
        skip: Deprecated — use offset instead (backward compat alias)
        limit: Maximum number of records to return
        db: Database session
        user_context: Either authenticated User or TestUserContext
        tech_id: Optional user UUID string — filter to jobs assigned to this tech
        scheduled_date: Optional YYYY-MM-DD string — filter to jobs scheduled on this date (dispatch board)
        status: Optional job status code filter (e.g. "draft", "scheduled")
        customer_search: Optional case-insensitive search on customer display_name
        scheduled_from: Optional filter for jobs starting on or after this datetime
        scheduled_to: Optional filter for jobs starting on or before this datetime
        offset: Canonical pagination offset (supersedes skip when > 0)

    Returns:
        PaginatedJobListResponse with items, total, limit, offset

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    from sqlalchemy import func as sqla_func

    effective_offset = offset if offset > 0 else skip

    statement = (
        select(Job, JobStatus, Customer)
        .join(JobStatus, Job.status_id == JobStatus.id, isouter=True)
        .join(Customer, Job.customer_id == Customer.id, isouter=True)
        .where(Job.tenant_id == user_context.tenant_id)
        .where(Customer.tenant_id == user_context.tenant_id)  # IDOR protection
    )

    if tech_id:
        statement = statement.join(
            JobTechAssignment,
            Job.id == JobTechAssignment.job_id,
        ).where(JobTechAssignment.user_id == tech_id)

    if scheduled_date:
        statement = statement.where(
            cast(Job.scheduled_start_at, SADate) == scheduled_date
        )

    # UI-FIX-1C: status code filter
    if status:
        statement = statement.where(sqla_func.lower(JobStatus.code) == status.lower())

    # UI-FIX-1C: customer name search
    if customer_search:
        statement = statement.where(Customer.display_name.ilike(f"%{customer_search}%"))

    # UI-FIX-2D: exact customer UUID filter
    if customer_id:
        statement = statement.where(Job.customer_id == customer_id)

    # UI-FIX-1C: scheduled date range
    if scheduled_from:
        statement = statement.where(Job.scheduled_start_at >= scheduled_from)
    if scheduled_to:
        statement = statement.where(Job.scheduled_start_at <= scheduled_to)

    # Count with same filters (re-build to avoid offset/limit in count)
    count_stmt = (
        select(sqla_func.count(Job.id))
        .join(JobStatus, Job.status_id == JobStatus.id, isouter=True)
        .join(Customer, Job.customer_id == Customer.id, isouter=True)
        .where(Job.tenant_id == user_context.tenant_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    )
    if tech_id:
        count_stmt = count_stmt.join(
            JobTechAssignment, Job.id == JobTechAssignment.job_id
        ).where(JobTechAssignment.user_id == tech_id)
    if scheduled_date:
        count_stmt = count_stmt.where(
            cast(Job.scheduled_start_at, SADate) == scheduled_date
        )
    if status:
        count_stmt = count_stmt.where(sqla_func.lower(JobStatus.code) == status.lower())
    if customer_search:
        count_stmt = count_stmt.where(
            Customer.display_name.ilike(f"%{customer_search}%")
        )
    if customer_id:
        count_stmt = count_stmt.where(Job.customer_id == customer_id)
    if scheduled_from:
        count_stmt = count_stmt.where(Job.scheduled_start_at >= scheduled_from)
    if scheduled_to:
        count_stmt = count_stmt.where(Job.scheduled_start_at <= scheduled_to)

    total = db.exec(count_stmt).one()

    statement = statement.offset(effective_offset).limit(limit)
    rows = db.exec(statement).all()

    # CLASS-B1: Batch-load job types for these jobs (one query, no N+1)
    job_type_ids = {job.job_type_id for job, _, _ in rows if job.job_type_id}
    job_type_by_id: dict = {}
    if job_type_ids:
        job_types = db.exec(select(JobType).where(JobType.id.in_(job_type_ids))).all()
        job_type_by_id = {jt.id: jt for jt in job_types}

    items = []
    for job, job_status, customer in rows:
        jt = job_type_by_id.get(job.job_type_id) if job.job_type_id else None
        items.append(
            JobListItem(
                id=job.id,
                tenant_id=job.tenant_id,
                customer_id=job.customer_id,
                site_id=job.site_id,
                status_id=job.status_id,
                status_code=job_status.code if job_status else None,
                customer_name=customer.display_name if customer else None,
                job_number=job.job_number if hasattr(job, "job_number") else None,
                scheduled_start_at=job.scheduled_start_at,
                scheduled_end_at=job.scheduled_end_at,
                estimated_duration_minutes=job.estimated_duration_minutes,
                # CLASS-B1: Priority and job type
                priority=job.priority,
                job_type_id=job.job_type_id,
                job_type_code=jt.code if jt else None,
                job_type_label=jt.label if jt else None,
                # JOB-UI-B1: Human-readable title
                title=job.title if hasattr(job, "title") else None,
            )
        )

    return PaginatedJobListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=effective_offset,
    )


def _create_job_time_entry_impl(
    job_id: UUID,
    entry_in: JobTimeEntryCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> JobTimeEntry:
    """
    Shared job time entry creation logic used by both authenticated and test endpoints.

    Args:
        job_id: ID of the job to add time entry to
        entry_in: Time entry data to create
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        Created JobTimeEntry instance

    Raises:
        HTTPException: If job not found

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id and user_id attributes (User model lacks tenant_id - Gap #40).
    """
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from sqlalchemy import func as sqlfunc

    from app.models.auth import TenantUser
    from app.models.catalog import LaborRateVersion
    from services.setting_resolver import get_effective_setting

    # B20/A91: Resolve burdened labor rate from LaborRateVersion catalog
    # Priority: voice-provided rate > catalog rate for skill level > platform default

    # Step 1: Check if voice handler pre-calculated a rate (B20/A90)
    if entry_in.hourly_rate_cents is not None:
        labor_rate_cents = entry_in.hourly_rate_cents
    else:
        # Step 2: Get skill_level_code from TenantUser
        tenant_user = db.exec(
            select(TenantUser)
            .where(TenantUser.tenant_id == user_context.tenant_id)
            .where(TenantUser.user_id == user_context.id)
        ).first()
        skill_code = tenant_user.skill_level_code if tenant_user else None

        # Step 3: Look up active catalog rate for this skill tier
        labor_rate_cents = None
        if skill_code:
            rate_row = db.exec(
                select(LaborRateVersion)
                .where(LaborRateVersion.tenant_id == user_context.tenant_id)
                .where(LaborRateVersion.skill_level_code == skill_code)
                .where(sqlfunc.now().op("<@")(LaborRateVersion.valid_period))
            ).first()
            if rate_row:
                labor_rate_cents = int(
                    rate_row.hourly_rate_cents * (1 + rate_row.burden_pct)
                )

        # Step 4: Fallback to platform default if no catalog row
        if labor_rate_cents is None:
            labor_rate_val, _ = get_effective_setting(
                db, user_context.tenant_id, "default_labor_rate_cents", fallback=8500
            )
            labor_rate_cents = int(labor_rate_val)

    hours = entry_in.hours
    if hours is None and entry_in.ended_at:
        delta = entry_in.ended_at - entry_in.started_at
        hours = delta.total_seconds() / 3600.0

    if hours is None:
        hours = 0.0

    total_cost_cents = int(hours * labor_rate_cents)

    # B3/A14: ETC validation — override note required when tech manually overrides ETC
    if entry_in.hours_remaining_was_overridden and not entry_in.override_note:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Override Note Required",
                "status": 422,
                "detail": "override_note is required when hours_remaining_was_overridden=true.",
            },
        )

    # FIND-050: Populate server_received_at when client submits with client_capture_at
    # (indicating this record was captured offline and is now being synced)
    server_received_at = None
    if getattr(entry_in, "client_capture_at", None) is not None:
        server_received_at = datetime.now(UTC)

    entry = JobTimeEntry(
        tenant_id=user_context.tenant_id,
        job_id=job.id,
        user_id=user_context.id,
        started_at=entry_in.started_at,
        ended_at=entry_in.ended_at,
        hours=hours,
        notes=entry_in.notes,
        hourly_rate_cents=labor_rate_cents,
        total_cost_cents=total_cost_cents,
        # B7a/A37 + FIND-050: offline capture timestamps
        client_capture_at=getattr(entry_in, "client_capture_at", None),
        server_received_at=server_received_at,
        # B3/A14: ETC fields
        hours_remaining_estimate=entry_in.hours_remaining_estimate,
        hours_remaining_was_overridden=entry_in.hours_remaining_was_overridden,
        override_note=entry_in.override_note,
        quote_line_id=entry_in.quote_line_id,
        etc_captured_at=entry_in.ended_at,  # F2: populated to ended_at at clock-out
    )

    # FIND-172: Check GPS variance and enqueue alert if needed (before commit)
    # Populate gps_variance_meters on the entry
    check_in_lat = getattr(entry_in, "check_in_lat", None)
    check_in_lng = getattr(entry_in, "check_in_lng", None)
    if check_in_lat is not None and check_in_lng is not None:
        from services.gps_variance_service import check_gps_variance_and_alert

        variance = check_gps_variance_and_alert(
            db, job_id, user_context.tenant_id, check_in_lat, check_in_lng
        )
        entry.check_in_lat = check_in_lat
        entry.check_in_lng = check_in_lng
        entry.gps_variance_meters = variance

    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Trigger profitability recalculation asynchronously
    from tasks.profitability_rollup import calculate_job_profitability

    calculate_job_profitability.delay(str(job.id))

    return entry


def _create_job_expense_impl(
    job_id: UUID,
    expense_in: JobExpenseCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> JobExpense:
    """
    Shared job expense creation logic used by both authenticated and test endpoints.

    Args:
        job_id: ID of the job to add expense to
        expense_in: Expense data to create
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        Created JobExpense instance

    Raises:
        HTTPException: If job not found

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Default logic if no markup version is found
    markup_pct = 0
    markup_amt_cents = None
    billable_cents = expense_in.cost_cents if expense_in.is_billable else 0

    if expense_in.is_billable:
        # Find applicable markup from TenantMarkupVersion using valid_period @> incurred_at
        # Use raw text for the valid_period containment check.
        markup_version = db.exec(
            select(TenantMarkupVersion)
            .where(TenantMarkupVersion.tenant_id == user_context.tenant_id)
            .where(
                TenantMarkupVersion.job_expense_category_code
                == expense_in.job_expense_category_code
            )
            .where(
                text("valid_period @> cast(:dt as timestamptz)").bindparams(
                    dt=expense_in.incurred_at
                )
            )
            .order_by(TenantMarkupVersion.recorded_at.desc())
        ).first()

        if markup_version:
            markup_pct = markup_version.markup_pct
            markup_amt_cents = markup_version.markup_amt_cents

            # Apply markup
            # If percentage is provided (e.g., 20.0 = 20%)
            # We assume markup_pct is a percentage like 20.0 (meaning 20%)
            if markup_pct is not None:
                billable_cents = int(
                    expense_in.cost_cents * (1 + (float(markup_pct) / 100.0))
                )
            elif markup_amt_cents is not None:
                billable_cents = expense_in.cost_cents + markup_amt_cents

    # FIND-050: Populate server_received_at when client submits with client_capture_at
    expense_server_received_at = None
    if getattr(expense_in, "client_capture_at", None) is not None:
        expense_server_received_at = datetime.now(UTC)

    expense = JobExpense(
        tenant_id=user_context.tenant_id,
        job_id=job.id,
        # FIND-121 (B18): user who incurred the expense (tech on-site, not necessarily the operator
        # entering the record). Both AuthenticatedUser and TestUserContext expose .id as the user UUID.
        user_id=user_context.id,
        job_expense_category_code=expense_in.job_expense_category_code,
        description=expense_in.description,
        vendor_name=expense_in.vendor_name,
        incurred_at=expense_in.incurred_at,
        cost_cents=expense_in.cost_cents,
        markup_pct=markup_pct,
        markup_amt_cents=markup_amt_cents,
        billable_cents=billable_cents,
        is_billable=expense_in.is_billable,
        client_capture_at=getattr(expense_in, "client_capture_at", None),
        server_received_at=expense_server_received_at,
    )

    db.add(expense)
    db.commit()
    db.refresh(expense)

    # Trigger profitability recalculation asynchronously
    from tasks.profitability_rollup import calculate_job_profitability

    calculate_job_profitability.delay(str(job.id))

    return expense


# JOB-UI-B1: Allowed status transitions (source_code → set of valid target_codes)
_JOB_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"scheduled", "cancelled"},
    "scheduled": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": {"cancelled"},
    "cancelled": set(),  # terminal — no forward transitions
}


def _update_job_impl(
    job_id: UUID,
    job_update: JobUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> "JobResponse":
    """
    Update mutable fields on a job (customer, site, schedule, title, status).

    Business logic:
    - Validates job belongs to tenant (IDOR protection)
    - If customer_id provided: validates customer belongs to tenant
    - If site_id provided: validates site belongs to tenant
    - If both customer_id and site_id provided: validates site belongs to customer
    - If only site_id provided: validates site belongs to existing job.customer_id
    - JOB-UI-B1: Accepts title (partial update) and status_code with transition validation.
      Illegal transitions return RFC 7807 422.
    - Applies only the fields that were sent (exclude_unset)
    """
    # 1. Tenant-scoped job fetch — db.get() BANNED per §7.1
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Job not found",
                "status": 404,
                "detail": f"Job {job_id} does not exist in this tenant.",
            },
        )

    update_data = job_update.model_dump(exclude_unset=True)

    # Determine effective customer_id for site validation
    effective_customer_id = update_data.get("customer_id", job.customer_id)

    # 2. If customer_id is being changed, validate it belongs to tenant
    if "customer_id" in update_data:
        customer = db.exec(
            select(Customer)
            .where(Customer.id == update_data["customer_id"])
            .where(Customer.tenant_id == user_context.tenant_id)
        ).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://errors.pilotfortrades.com/not-found",
                    "title": "Customer not found",
                    "status": 404,
                    "detail": f"Customer {update_data['customer_id']} does not exist in this tenant.",
                },
            )

    # 3. If site_id is being changed, validate it belongs to tenant + effective customer
    if "site_id" in update_data:
        site = db.exec(
            select(Site)
            .where(Site.id == update_data["site_id"])
            .where(Site.tenant_id == user_context.tenant_id)
        ).first()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://errors.pilotfortrades.com/not-found",
                    "title": "Site not found",
                    "status": 404,
                    "detail": f"Site {update_data['site_id']} does not exist in this tenant.",
                },
            )
        if site.customer_id != effective_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://errors.pilotfortrades.com/validation",
                    "title": "Site does not belong to customer",
                    "status": 400,
                    "detail": "The specified site does not belong to the specified (or existing) customer.",
                },
            )

    # 4a. CLASS-B1: Validate priority if being updated
    if "priority" in update_data:
        new_priority = update_data["priority"]
        if new_priority not in JOB_PRIORITY_VALUES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "type": "https://errors.pilotfortrades.com/invalid-priority",
                    "title": "Invalid job priority",
                    "status": 422,
                    "detail": f"'{new_priority}' is not a valid priority. Must be one of: {sorted(JOB_PRIORITY_VALUES)}",
                },
            )

    # 4b. JOB-UI-B1: Validate and apply status transition if requested
    if "status_code" in update_data:
        new_code = update_data.pop("status_code")  # remove — not a direct model column
        # Resolve current status code (tenant-scoped)
        current_status = db.exec(
            select(JobStatus).where(JobStatus.id == job.status_id)
        ).first()
        current_code = current_status.code if current_status else None

        allowed = _JOB_STATUS_TRANSITIONS.get(current_code, set())
        if new_code not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "type": "https://errors.pilotfortrades.com/invalid-status-transition",
                    "title": "Invalid status transition",
                    "status": 422,
                    "detail": (
                        f"Cannot transition job from '{current_code}' to '{new_code}'. "
                        f"Allowed targets: {sorted(allowed) if allowed else 'none (terminal status)'}."
                    ),
                },
            )
        # Resolve new status_id (platform-level: tenant_id IS NULL)
        new_status = db.exec(
            select(JobStatus)
            .where(JobStatus.code == new_code)
            .where(
                (JobStatus.tenant_id == user_context.tenant_id)
                | (JobStatus.tenant_id == None)
            )
            .order_by(JobStatus.tenant_id)  # prefer tenant row over platform row
        ).first()
        if not new_status:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "type": "https://errors.pilotfortrades.com/invalid-status-transition",
                    "title": "Invalid status code",
                    "status": 422,
                    "detail": f"Status code '{new_code}' does not exist in the system.",
                },
            )
        update_data["status_id"] = new_status.id

    # 4c. Apply updates (title is applied here as a direct column)
    for key, val in update_data.items():
        setattr(job, key, val)

    db.add(job)
    db.commit()
    db.refresh(job)
    # JOB-UI-B1: Return enriched JobResponse (includes status_code from JOIN)
    return _get_job_impl(job.id, db, user_context)


def _get_job_impl(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> JobResponse:
    """
    Shared job retrieval logic used by both authenticated and test endpoints.

    B19: Updated to JOIN job_status, site, customer to populate enriched fields:
    - status_code (from job_status.code)
    - site_name (from site.name)
    - customer_name (from customer.display_name)
    - job_number (from job.job_number)

    Args:
        job_id: UUID of job to retrieve
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        JobResponse with enriched detail fields

    Raises:
        HTTPException: If job not found

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    row = db.exec(
        select(Job, JobStatus, Site, Customer)
        .join(JobStatus, Job.status_id == JobStatus.id, isouter=True)
        .join(Site, Job.site_id == Site.id, isouter=True)
        .join(Customer, Job.customer_id == Customer.id, isouter=True)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Job not found",
                "status": 404,
                "detail": f"Job {job_id} does not exist in this tenant.",
            },
        )

    job, job_status, site, customer = row
    response = JobResponse.model_validate(job)
    response.status_code = job_status.code if job_status else None
    response.site_name = site.name if site else None
    response.customer_name = customer.display_name if customer else None
    # CLASS-B1: Enrich with job_type code/label (single lookup if job_type_id is set)
    if job.job_type_id:
        jt = db.exec(select(JobType).where(JobType.id == job.job_type_id)).first()
        response.job_type_code = jt.code if jt else None
        response.job_type_label = jt.label if jt else None
    # JOB-UI-B1: title and quote_version_id come through model_validate from Job model
    # (both are already present on the Job object — no extra JOIN needed)
    return response


def _list_job_time_entries_impl(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[JobTimeEntry]:
    """
    Shared job time entries listing logic used by both authenticated and test endpoints.

    Args:
        job_id: UUID of job to list time entries for
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        List of JobTimeEntry instances

    Raises:
        HTTPException: If job not found

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    # Verify job belongs to tenant
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

    # Get time entries for job - filter by tenant_id for IDOR protection
    time_entries = db.exec(
        select(JobTimeEntry)
        .where(JobTimeEntry.job_id == job_id)
        .where(JobTimeEntry.tenant_id == user_context.tenant_id)
    ).all()

    return time_entries


def _list_job_expenses_impl(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[JobExpense]:
    """
    Shared job expenses listing logic used by both authenticated and test endpoints.

    Args:
        job_id: UUID of job to list expenses for
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        List of JobExpense instances

    Raises:
        HTTPException: If job not found

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    # Verify job belongs to tenant
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

    # Get expenses for job
    expenses = db.exec(
        select(JobExpense)
        .where(JobExpense.job_id == job_id)
        .where(JobExpense.tenant_id == user_context.tenant_id)
    ).all()

    return expenses


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================
# NOTE: Test endpoints MUST be registered BEFORE authenticated endpoints
# to avoid route matching conflicts (/{id} would match /test)


@router.post("/test", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job_test(
    job_in: JobCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new job (TEST ENDPOINT - no authentication required).
    
    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled
        
    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002
        
    Usage:
        curl -X POST http://localhost:8000/api/v1/jobs/test \\
          -H "Content-Type: application/json" \\
          -d '{"customer_id": "...", "site_id": "...", "scheduled_start_at": "2026-04-01T09:00:00Z"}'
          
    Returns:
        JobResponse with created job data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_job_impl(job_in, db, test_context)


@router.get("/test", response_model=PaginatedJobListResponse)
def list_jobs_test(
    skip: int = 0,
    limit: int = 25,
    offset: int = 0,
    tech_id: str | None = Query(
        default=None, description="Filter by assigned tech user UUID"
    ),
    scheduled_date: str | None = Query(
        default=None, description="Filter by scheduled date (YYYY-MM-DD)"
    ),
    status: str | None = Query(
        default=None, description="Filter by job status code (e.g. draft, scheduled)"
    ),
    customer_search: str | None = Query(
        default=None, description="Case-insensitive search on customer name"
    ),
    scheduled_from: datetime | None = Query(
        default=None, description="Filter jobs starting on or after this datetime"
    ),
    scheduled_to: datetime | None = Query(
        default=None, description="Filter jobs starting on or before this datetime"
    ),
    customer_id: uuid.UUID | None = Query(
        default=None, description="Filter jobs by exact customer UUID"
    ),
    db: Session = Depends(get_db),
):
    """
    List jobs (TEST ENDPOINT - no authentication required).

    MOB-B1-BE: Added tech_id and scheduled_date filter params. Returns JobListItem
    (with status_code and customer_name denormalized) instead of JobResponse.

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns jobs from test tenant only: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/jobs/test
        curl http://localhost:8000/api/v1/jobs/test?tech_id=<uuid>
        curl http://localhost:8000/api/v1/jobs/test?scheduled_date=2026-06-05

    Returns:
        PaginatedJobListResponse from test tenant (UI-FIX-1C)
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _list_jobs_impl(
        skip,
        limit,
        db,
        test_context,
        tech_id=tech_id,
        scheduled_date=scheduled_date,
        status=status,
        customer_search=customer_search,
        scheduled_from=scheduled_from,
        scheduled_to=scheduled_to,
        offset=offset,
        customer_id=customer_id,
    )


@router.post(
    "/{job_id}/time-entries/test",
    response_model=JobTimeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job_time_entry_test(
    job_id: UUID,
    entry_in: JobTimeEntryCreate,
    db: Session = Depends(get_db),
):
    """
    Create a time entry for a job (TEST ENDPOINT - no authentication required).
    
    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled
        
    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002
        
    Usage:
        curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/time-entries/test \\
          -H "Content-Type: application/json" \\
          -d '{"started_at": "2026-04-01T09:00:00Z", "ended_at": "2026-04-01T17:00:00Z", "notes": "Panel upgrade"}'
          
    Returns:
        JobTimeEntryResponse with created time entry data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_job_time_entry_impl(job_id, entry_in, db, test_context)


@router.post(
    "/{job_id}/expenses/test",
    response_model=JobExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job_expense_test(
    job_id: UUID,
    expense_in: JobExpenseCreate,
    db: Session = Depends(get_db),
):
    """
    Create an expense for a job (TEST ENDPOINT - no authentication required).
    
    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled
        
    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002
        
    Usage:
        curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/expenses/test \\
          -H "Content-Type: application/json" \\
          -d '{"job_expense_category_code": "materials", "description": "Wire 12/2", "cost_cents": 5000, "incurred_at": "2026-04-01T10:00:00Z", "is_billable": true}'
          
    Returns:
        JobExpenseResponse with created expense data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_job_expense_impl(job_id, expense_in, db, test_context)


@router.get("/{job_id}/test", response_model=JobResponse)
def get_job_test(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific job (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns job from test tenant: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/jobs/{job_id}/test

    Returns:
        JobResponse with job data
    """
    test_context = get_test_context()
    return _get_job_impl(job_id, db, test_context)


@router.patch("/{job_id}/test", response_model=JobResponse)
def update_job_test(
    job_id: UUID,
    job_update: JobUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a job (TEST ENDPOINT — no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Blocked in staging/production
    """
    test_context = get_test_context()
    return _update_job_impl(job_id, job_update, db, test_context)


@router.get("/{job_id}/time-entries/test", response_model=list[JobTimeEntryResponse])
def list_job_time_entries_test(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """
    List time entries for a job (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns time entries for job in test tenant: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/jobs/{job_id}/time-entries/test

    Returns:
        List of JobTimeEntryResponse objects from test tenant
    """
    test_context = get_test_context()
    return _list_job_time_entries_impl(job_id, db, test_context)


@router.get("/{job_id}/expenses/test", response_model=list[JobExpenseResponse])
def list_job_expenses_test(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """
    List expenses for a job (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns expenses for job in test tenant: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/jobs/{job_id}/expenses/test

    Returns:
        List of JobExpenseResponse objects from test tenant
    """
    test_context = get_test_context()
    return _list_job_expenses_impl(job_id, db, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_in: JobCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.create")),
):
    """
    Create a new job (requires JWT authentication and jobs.create permission).

    Security:
        - Requires valid JWT token
        - Requires jobs.create permission
        - Job created in authenticated user's tenant
        - Validates customer and site belong to same tenant

    Returns:
        JobResponse with created job data
    """
    return _create_job_impl(job_in, db, current_user)


@router.get("/", response_model=PaginatedJobListResponse)
def list_jobs(
    skip: int = 0,
    limit: int = 25,
    offset: int = 0,
    tech_id: str | None = Query(
        default=None, description="Filter by assigned tech user UUID"
    ),
    scheduled_date: str | None = Query(
        default=None,
        description="Filter by scheduled date (YYYY-MM-DD) — dispatch board compat",
    ),
    status: str | None = Query(default=None, description="Filter by job status code"),
    customer_search: str | None = Query(
        default=None, description="Case-insensitive search on customer name"
    ),
    scheduled_from: datetime | None = Query(
        default=None, description="Filter jobs starting on or after this datetime"
    ),
    scheduled_to: datetime | None = Query(
        default=None, description="Filter jobs starting on or before this datetime"
    ),
    customer_id: uuid.UUID | None = Query(
        default=None, description="Filter jobs by exact customer UUID"
    ),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
):
    """
    List jobs (requires JWT authentication and jobs.view permission).

    UI-FIX-1C: Returns PaginatedJobListResponse with total, limit, offset.
    MOB-B1-BE: Added tech_id and scheduled_date filter params. Returns JobListItem
    (with status_code and customer_name denormalized) instead of JobResponse.

    Security:
        - Requires valid JWT token
        - Requires jobs.view permission
        - Returns only jobs in authenticated user's tenant

    Query params:
        - tech_id: Optional — filter to jobs assigned to the specified user UUID
        - scheduled_date: Optional YYYY-MM-DD — filter to jobs scheduled on that date (dispatch board)
        - status: Optional — filter by job status code
        - customer_search: Optional — case-insensitive search on customer name
        - scheduled_from/to: Optional datetime range filter on scheduled_start_at
        - customer_id: Optional — exact UUID match on job.customer_id (UI-FIX-2D)
        - offset: Pagination offset (supersedes deprecated skip)

    Returns:
        PaginatedJobListResponse with total count
    """
    return _list_jobs_impl(
        skip,
        limit,
        db,
        current_user,
        tech_id=tech_id,
        scheduled_date=scheduled_date,
        status=status,
        customer_search=customer_search,
        scheduled_from=scheduled_from,
        scheduled_to=scheduled_to,
        offset=offset,
        customer_id=customer_id,
    )


@router.post(
    "/{job_id}/time-entries",
    response_model=JobTimeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job_time_entry(
    job_id: UUID,
    entry_in: JobTimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("time_entries.create")
    ),
):
    """
    Create a time entry for a job (requires JWT authentication and time_entries.create permission).

    Security:
        - Requires valid JWT token
        - Requires time_entries.create permission
        - Validates job belongs to authenticated user's tenant
        - Uses tenant's default labor rate

    Returns:
        JobTimeEntryResponse with created time entry data
    """
    return _create_job_time_entry_impl(job_id, entry_in, db, current_user)


@router.post(
    "/{job_id}/expenses",
    response_model=JobExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job_expense(
    job_id: UUID,
    expense_in: JobExpenseCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("expenses.create")),
):
    """
    Create an expense for a job (requires JWT authentication and expenses.create permission).

    Security:
        - Requires valid JWT token
        - Requires expenses.create permission
        - Validates job belongs to authenticated user's tenant
        - Applies tenant-specific markup rates

    Returns:
        JobExpenseResponse with created expense data
    """
    return _create_job_expense_impl(job_id, expense_in, db, current_user)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
):
    """
    Get a specific job (requires JWT authentication and jobs.view permission).

    Security:
        - Requires valid JWT token
        - Requires jobs.view permission
        - Returns only job in authenticated user's tenant

    Returns:
        JobResponse with job data
    """
    return _get_job_impl(job_id, db, current_user)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: UUID,
    job_update: JobUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """
    Update a job's mutable fields (requires JWT and jobs.update permission).

    Updatable fields: customer_id, site_id, scheduled_start_at, scheduled_end_at,
    estimated_duration_minutes, title, status_code (with transition validation).
    All fields are optional — send only what changes.

    JOB-UI-B1: status_code is now editable with forward-transition validation.
    Valid transitions: draft→scheduled→in_progress→completed; any→cancelled.
    Illegal transitions return RFC 7807 422.

    Security:
        - Requires valid JWT token
        - Requires jobs.update permission
        - Job must belong to authenticated user's tenant
    """
    set_audit_context_sync(db, user_id=current_user.id)
    return _update_job_impl(job_id, job_update, db, current_user)


@router.get("/{job_id}/time-entries", response_model=list[JobTimeEntryResponse])
def list_job_time_entries(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("time_entries.view")),
):
    """
    List time entries for a job (requires JWT authentication and time_entries.view permission).

    Security:
        - Requires valid JWT token
        - Requires time_entries.view permission
        - Validates job belongs to authenticated user's tenant

    Returns:
        List of JobTimeEntryResponse objects
    """
    return _list_job_time_entries_impl(job_id, db, current_user)


@router.get("/{job_id}/expenses", response_model=list[JobExpenseResponse])
def list_job_expenses(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("expenses.view")),
):
    """
    List expenses for a job (requires JWT authentication and expenses.view permission).

    Security:
        - Requires valid JWT token
        - Requires expenses.view permission
        - Validates job belongs to authenticated user's tenant

    Returns:
        List of JobExpenseResponse objects
    """
    return _list_job_expenses_impl(job_id, db, current_user)


# ==================== JOB NOTES ENDPOINTS (FIND-064) — _impl() ====================


def _get_job_notes_impl(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> JobNotesResponse:
    """Shared logic for getting job notes (singleton resource)."""
    _verify_job_tenant(job_id, db, user_context)

    note = db.exec(
        select(JobNotes)
        .where(JobNotes.job_id == job_id)
        .where(JobNotes.tenant_id == user_context.tenant_id)
    ).first()

    if not note:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)

    return note


def _upsert_job_notes_impl(
    job_id: UUID,
    notes_in: JobNotesUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> JobNotesResponse:
    """Shared logic for creating or updating job notes (singleton upsert)."""
    _verify_job_tenant(job_id, db, user_context)

    note = db.exec(
        select(JobNotes)
        .where(JobNotes.job_id == job_id)
        .where(JobNotes.tenant_id == user_context.tenant_id)
    ).first()

    if note:
        note.notes = notes_in.notes
        note.updated_by = user_context.id
        db.add(note)
    else:
        note = JobNotes(
            id=uuid.uuid4(),
            tenant_id=user_context.tenant_id,
            job_id=job_id,
            notes=notes_in.notes,
            audio_object_key=None,
            customer_visible=False,
            created_by=user_context.id,
        )
        db.add(note)

    db.commit()
    db.refresh(note)
    return note


# TEST ENDPOINTS for job notes (register BEFORE authenticated)


@router.get("/{job_id}/notes/test", response_model=JobNotesResponse)
def get_job_notes_test(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """Get job notes (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _get_job_notes_impl(job_id, db, test_context)


@router.put(
    "/{job_id}/notes/test",
    response_model=JobNotesResponse,
    status_code=status.HTTP_200_OK,
)
def upsert_job_notes_test(
    job_id: UUID,
    notes_in: JobNotesUpdate,
    db: Session = Depends(get_db),
):
    """Create or update job notes (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _upsert_job_notes_impl(job_id, notes_in, db, test_context)


# AUTHENTICATED endpoints


@router.get("/{job_id}/notes", response_model=JobNotesResponse)
def get_job_notes(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
):
    """Get job notes. RBAC: jobs.view."""
    return _get_job_notes_impl(job_id, db, current_user)


@router.put(
    "/{job_id}/notes", response_model=JobNotesResponse, status_code=status.HTTP_200_OK
)
def upsert_job_notes(
    job_id: UUID,
    notes_in: JobNotesUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """Create or update job notes. RBAC: jobs.update."""
    return _upsert_job_notes_impl(job_id, notes_in, db, current_user)


# ==================== LOTO CONFIRMATION ENDPOINTS (B20/A89) ====================


def _create_loto_confirmation_impl(
    job_id: UUID,
    data: LotoConfirmationCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> tuple[LotoConfirmation, bool]:
    """
    Shared LOTO confirmation creation logic. Returns (record, created) where
    created=True means 201, False means 200 (idempotent replay).

    No db.get() — always tenant-scoped (§6.2 ban).
    """
    # 1. Tenant-scoped job fetch — db.get() BANNED per §7.1
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    # 2. Resolve server_received_at (offline pattern — matches job_time_entry)
    server_received_at = None
    if data.client_capture_at is not None:
        server_received_at = datetime.now(UTC)

    # 3. Idempotency check via natural key: (user_id, job_id, confirmed_at)
    user_id = user_context.id
    existing = db.exec(
        select(LotoConfirmation)
        .where(LotoConfirmation.user_id == user_id)
        .where(LotoConfirmation.job_id == job_id)
        .where(LotoConfirmation.confirmed_at == data.confirmed_at)
    ).first()
    if existing:
        return existing, False  # 200 idempotent replay

    # 4. INSERT
    record = LotoConfirmation(
        tenant_id=user_context.tenant_id,
        job_id=job_id,
        user_id=user_id,
        confirmed_at=data.confirmed_at,
        client_capture_at=data.client_capture_at,
        server_received_at=server_received_at,
        created_by=user_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record, True  # 201 created


def _list_loto_confirmations_impl(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list:
    """Shared logic for listing LOTO confirmations for a job."""
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    records = db.exec(
        select(LotoConfirmation)
        .where(LotoConfirmation.job_id == job_id)
        .where(LotoConfirmation.tenant_id == user_context.tenant_id)
        .order_by(LotoConfirmation.confirmed_at.desc())
    ).all()
    return records


# TEST ENDPOINTS for LOTO (register BEFORE authenticated)


@router.post(
    "/{job_id}/loto-confirmations/test",
    response_model=LotoConfirmationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_loto_confirmation_test(
    job_id: UUID,
    data: LotoConfirmationCreate,
    db: Session = Depends(get_db),
):
    """Record a LOTO confirmation (TEST ENDPOINT — no auth required)."""
    from fastapi.responses import JSONResponse

    test_context = get_test_context()
    record, created = _create_loto_confirmation_impl(job_id, data, db, test_context)
    response_data = LotoConfirmationRead.model_validate(record)
    if not created:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data.model_dump(mode="json"),
        )
    return record


@router.get(
    "/{job_id}/loto-confirmations/test",
    response_model=list[LotoConfirmationRead],
)
def list_loto_confirmations_test(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """List LOTO confirmations for a job (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _list_loto_confirmations_impl(job_id, db, test_context)


# AUTHENTICATED ENDPOINTS


@router.post(
    "/{job_id}/loto-confirmations",
    response_model=LotoConfirmationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_loto_confirmation(
    job_id: UUID,
    data: LotoConfirmationCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.loto_confirm")),
):
    """Record a LOTO confirmation. RBAC: jobs.loto_confirm."""
    from fastapi.responses import JSONResponse

    record, created = _create_loto_confirmation_impl(job_id, data, db, current_user)
    response_data = LotoConfirmationRead.model_validate(record)
    if not created:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data.model_dump(mode="json"),
        )
    return record


@router.get(
    "/{job_id}/loto-confirmations",
    response_model=list[LotoConfirmationRead],
)
def list_loto_confirmations(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
):
    """List LOTO confirmations for a job. RBAC: jobs.view."""
    return _list_loto_confirmations_impl(job_id, db, current_user)


# ==================== CHANGE ORDER SHARED BUSINESS LOGIC ====================


def _verify_job_tenant(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Job:
    """Verify the job exists and belongs to the user's tenant. Raises 404 otherwise."""
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return job


def _verify_change_order_tenant(
    job_id: UUID,
    co_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ChangeOrder:
    """Verify change order exists, belongs to the job, and belongs to the tenant."""
    co = db.exec(
        select(ChangeOrder)
        .where(ChangeOrder.id == co_id)
        .where(ChangeOrder.job_id == job_id)
        .where(ChangeOrder.tenant_id == user_context.tenant_id)
    ).first()
    if not co:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Change order not found"
        )
    return co


def _create_change_order_impl(
    job_id: UUID,
    co_in: ChangeOrderCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ChangeOrder:
    """Create a new change order for a job."""
    _verify_job_tenant(job_id, db, user_context)

    # FIND-050: Populate server_received_at when client submits with client_capture_at
    co_server_received_at = None
    if getattr(co_in, "client_capture_at", None) is not None:
        co_server_received_at = datetime.now(UTC)

    co = ChangeOrder(
        tenant_id=user_context.tenant_id,
        job_id=job_id,
        description=co_in.description,
        client_capture_at=getattr(co_in, "client_capture_at", None),
        server_received_at=co_server_received_at,
    )
    db.add(co)
    db.commit()
    db.refresh(co)
    return co


def _list_change_orders_impl(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[ChangeOrder]:
    """List all active change orders for a job."""
    _verify_job_tenant(job_id, db, user_context)

    return db.exec(
        select(ChangeOrder)
        .where(ChangeOrder.job_id == job_id)
        .where(ChangeOrder.tenant_id == user_context.tenant_id)
        .where(ChangeOrder.is_active == True)
    ).all()


def _get_change_order_impl(
    job_id: UUID,
    co_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ChangeOrder:
    """Get a single change order by ID."""
    return _verify_change_order_tenant(job_id, co_id, db, user_context)


def _update_change_order_impl(
    job_id: UUID,
    co_id: UUID,
    co_update: ChangeOrderUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ChangeOrder:
    """Update a change order's description or active state."""
    co = _verify_change_order_tenant(job_id, co_id, db, user_context)

    update_data = co_update.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(co, key, val)

    db.add(co)
    db.commit()
    db.refresh(co)
    return co


def _delete_change_order_impl(
    job_id: UUID,
    co_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """Soft-delete a change order."""
    co = _verify_change_order_tenant(job_id, co_id, db, user_context)
    co.is_active = False
    db.add(co)
    db.commit()
    return {"message": "Change order deactivated", "id": str(co_id)}


def _create_change_order_line_impl(
    job_id: UUID,
    co_id: UUID,
    line_in: ChangeOrderLineCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ChangeOrderLine:
    """Create a new line on a change order. DB trigger recalcs header totals."""
    _verify_change_order_tenant(job_id, co_id, db, user_context)

    subtotal = int(float(line_in.quantity) * line_in.unit_price_cents)

    # FIND-107: If customer has a taxability override, use it over line-level default
    _customer_taxability = None
    job = db.exec(
        select(Job).where(
            Job.id == job_id,
            Job.tenant_id == user_context.tenant_id,
        )
    ).first()

    if job and job.customer_id:
        from app.models.crm import Customer as _Customer

        _cust = db.exec(
            select(_Customer).where(
                _Customer.id == job.customer_id,
                _Customer.tenant_id == user_context.tenant_id,
            )
        ).first()
        if _cust and _cust.taxability_code:
            _customer_taxability = _cust.taxability_code

    taxability_code = _customer_taxability or line_in.taxability_code or "taxable"

    line = ChangeOrderLine(
        tenant_id=user_context.tenant_id,
        change_order_id=co_id,
        position=line_in.position,
        qco_line_type_id=line_in.qco_line_type_id,
        description=line_in.description,
        quantity=line_in.quantity,
        unit=line_in.unit,
        unit_price_cents=line_in.unit_price_cents,
        subtotal_cents=subtotal,
        total_cents=subtotal,
        pricebook_item_id=line_in.pricebook_item_id,
        supplier_id=line_in.supplier_id,
        supplier_item_id=line_in.supplier_item_id,
        taxability_code=taxability_code,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def _list_change_order_lines_impl(
    job_id: UUID,
    co_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[ChangeOrderLine]:
    """List all active lines for a change order."""
    _verify_change_order_tenant(job_id, co_id, db, user_context)

    return db.exec(
        select(ChangeOrderLine)
        .where(ChangeOrderLine.change_order_id == co_id)
        .where(ChangeOrderLine.tenant_id == user_context.tenant_id)
        .where(ChangeOrderLine.is_active == True)
        .order_by(ChangeOrderLine.position)
    ).all()


def _update_change_order_line_impl(
    job_id: UUID,
    co_id: UUID,
    line_id: UUID,
    line_update: ChangeOrderLineUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ChangeOrderLine:
    """Update a change order line. DB trigger recalcs header totals."""
    _verify_change_order_tenant(job_id, co_id, db, user_context)

    line = db.exec(
        select(ChangeOrderLine)
        .where(ChangeOrderLine.id == line_id)
        .where(ChangeOrderLine.change_order_id == co_id)
        .where(ChangeOrderLine.tenant_id == user_context.tenant_id)
    ).first()
    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Change order line not found"
        )

    update_data = line_update.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(line, key, val)

    # Recalc subtotal/total if quantity or unit_price changed
    if "quantity" in update_data or "unit_price_cents" in update_data:
        subtotal = int(float(line.quantity) * line.unit_price_cents)
        line.subtotal_cents = subtotal
        line.total_cents = subtotal

    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def _delete_change_order_line_impl(
    job_id: UUID,
    co_id: UUID,
    line_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """Soft-delete a change order line."""
    _verify_change_order_tenant(job_id, co_id, db, user_context)

    line = db.exec(
        select(ChangeOrderLine)
        .where(ChangeOrderLine.id == line_id)
        .where(ChangeOrderLine.change_order_id == co_id)
        .where(ChangeOrderLine.tenant_id == user_context.tenant_id)
    ).first()
    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Change order line not found"
        )

    line.is_active = False
    db.add(line)
    db.commit()
    return {"message": "Change order line deactivated", "id": str(line_id)}


# ==================== CHANGE ORDER TEST ENDPOINTS (register FIRST) ====================


@router.post(
    "/{job_id}/change-orders/test",
    response_model=ChangeOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_change_order_test(
    job_id: UUID,
    co_in: ChangeOrderCreate,
    db: Session = Depends(get_db),
):
    """Create a change order (TEST ENDPOINT - no auth required)."""
    test_context = get_test_context()
    return _create_change_order_impl(job_id, co_in, db, test_context)


@router.get("/{job_id}/change-orders/test", response_model=list[ChangeOrderResponse])
def list_change_orders_test(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """List change orders for a job (TEST ENDPOINT - no auth required)."""
    test_context = get_test_context()
    return _list_change_orders_impl(job_id, db, test_context)


@router.get("/{job_id}/change-orders/{co_id}/test", response_model=ChangeOrderResponse)
def get_change_order_test(
    job_id: UUID,
    co_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a change order (TEST ENDPOINT - no auth required)."""
    test_context = get_test_context()
    return _get_change_order_impl(job_id, co_id, db, test_context)


@router.patch(
    "/{job_id}/change-orders/{co_id}/test", response_model=ChangeOrderResponse
)
def update_change_order_test(
    job_id: UUID,
    co_id: UUID,
    co_update: ChangeOrderUpdate,
    db: Session = Depends(get_db),
):
    """Update a change order (TEST ENDPOINT - no auth required)."""
    test_context = get_test_context()
    return _update_change_order_impl(job_id, co_id, co_update, db, test_context)


@router.delete("/{job_id}/change-orders/{co_id}/test")
def delete_change_order_test(
    job_id: UUID,
    co_id: UUID,
    db: Session = Depends(get_db),
):
    """Soft-delete a change order (TEST ENDPOINT - no auth required)."""
    test_context = get_test_context()
    return _delete_change_order_impl(job_id, co_id, db, test_context)


@router.post(
    "/{job_id}/change-orders/{co_id}/lines/test",
    response_model=ChangeOrderLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_change_order_line_test(
    job_id: UUID,
    co_id: UUID,
    line_in: ChangeOrderLineCreate,
    db: Session = Depends(get_db),
):
    """Create a change order line (TEST ENDPOINT - no auth required)."""
    test_context = get_test_context()
    return _create_change_order_line_impl(job_id, co_id, line_in, db, test_context)


@router.get(
    "/{job_id}/change-orders/{co_id}/lines/test",
    response_model=list[ChangeOrderLineResponse],
)
def list_change_order_lines_test(
    job_id: UUID,
    co_id: UUID,
    db: Session = Depends(get_db),
):
    """List change order lines (TEST ENDPOINT - no auth required)."""
    test_context = get_test_context()
    return _list_change_order_lines_impl(job_id, co_id, db, test_context)


@router.patch(
    "/{job_id}/change-orders/{co_id}/lines/{line_id}/test",
    response_model=ChangeOrderLineResponse,
)
def update_change_order_line_test(
    job_id: UUID,
    co_id: UUID,
    line_id: UUID,
    line_update: ChangeOrderLineUpdate,
    db: Session = Depends(get_db),
):
    """Update a change order line (TEST ENDPOINT - no auth required)."""
    test_context = get_test_context()
    return _update_change_order_line_impl(
        job_id, co_id, line_id, line_update, db, test_context
    )


@router.delete("/{job_id}/change-orders/{co_id}/lines/{line_id}/test")
def delete_change_order_line_test(
    job_id: UUID,
    co_id: UUID,
    line_id: UUID,
    db: Session = Depends(get_db),
):
    """Soft-delete a change order line (TEST ENDPOINT - no auth required)."""
    test_context = get_test_context()
    return _delete_change_order_line_impl(job_id, co_id, line_id, db, test_context)


# ==================== CHANGE ORDER AUTHENTICATED ENDPOINTS ====================


@router.post(
    "/{job_id}/change-orders",
    response_model=ChangeOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_change_order(
    job_id: UUID,
    co_in: ChangeOrderCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """Create a change order for a job (requires jobs.update permission)."""
    return _create_change_order_impl(job_id, co_in, db, current_user)


@router.get("/{job_id}/change-orders", response_model=list[ChangeOrderResponse])
def list_change_orders(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
):
    """List change orders for a job (requires jobs.view permission)."""
    return _list_change_orders_impl(job_id, db, current_user)


@router.get("/{job_id}/change-orders/{co_id}", response_model=ChangeOrderResponse)
def get_change_order(
    job_id: UUID,
    co_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
):
    """Get a single change order (requires jobs.view permission)."""
    return _get_change_order_impl(job_id, co_id, db, current_user)


@router.patch("/{job_id}/change-orders/{co_id}", response_model=ChangeOrderResponse)
def update_change_order(
    job_id: UUID,
    co_id: UUID,
    co_update: ChangeOrderUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """Update a change order (requires jobs.update permission)."""
    return _update_change_order_impl(job_id, co_id, co_update, db, current_user)


@router.delete("/{job_id}/change-orders/{co_id}")
def delete_change_order(
    job_id: UUID,
    co_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """Soft-delete a change order (requires jobs.update permission)."""
    return _delete_change_order_impl(job_id, co_id, db, current_user)


@router.post(
    "/{job_id}/change-orders/{co_id}/lines",
    response_model=ChangeOrderLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_change_order_line(
    job_id: UUID,
    co_id: UUID,
    line_in: ChangeOrderLineCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """Create a change order line (requires jobs.update permission)."""
    return _create_change_order_line_impl(job_id, co_id, line_in, db, current_user)


@router.get(
    "/{job_id}/change-orders/{co_id}/lines",
    response_model=list[ChangeOrderLineResponse],
)
def list_change_order_lines(
    job_id: UUID,
    co_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
):
    """List change order lines (requires jobs.view permission)."""
    return _list_change_order_lines_impl(job_id, co_id, db, current_user)


@router.patch(
    "/{job_id}/change-orders/{co_id}/lines/{line_id}",
    response_model=ChangeOrderLineResponse,
)
def update_change_order_line(
    job_id: UUID,
    co_id: UUID,
    line_id: UUID,
    line_update: ChangeOrderLineUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """Update a change order line (requires jobs.update permission)."""
    return _update_change_order_line_impl(
        job_id, co_id, line_id, line_update, db, current_user
    )


@router.delete("/{job_id}/change-orders/{co_id}/lines/{line_id}")
def delete_change_order_line(
    job_id: UUID,
    co_id: UUID,
    line_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """Soft-delete a change order line (requires jobs.update permission)."""
    return _delete_change_order_line_impl(job_id, co_id, line_id, db, current_user)


# ===========================================================================
# B3/A14 — Projected Margin Endpoint
# ===========================================================================


def _projected_margin_impl(job_id: UUID, db: Session, user_context) -> dict:
    """Shared projected-margin logic — IDOR-safe, uses etc_service."""
    from services.etc_service import compute_projected_margin

    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
        .where(Job.is_active == True)
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    from sqlalchemy import func as sqlfunc

    from app.models.auth import TenantUser
    from app.models.catalog import LaborRateVersion
    from services.setting_resolver import get_effective_setting

    # B20/A91: Resolve burdened labor rate from LaborRateVersion catalog
    # Step 1: Get skill_level_code from TenantUser
    tenant_user = db.exec(
        select(TenantUser)
        .where(TenantUser.tenant_id == user_context.tenant_id)
        .where(TenantUser.user_id == user_context.id)
    ).first()
    skill_code = tenant_user.skill_level_code if tenant_user else None

    # Step 2: Look up active catalog rate for this skill tier
    labor_rate_cents = None
    if skill_code:
        rate_row = db.exec(
            select(LaborRateVersion)
            .where(LaborRateVersion.tenant_id == user_context.tenant_id)
            .where(LaborRateVersion.skill_level_code == skill_code)
            .where(sqlfunc.now().op("<@")(LaborRateVersion.valid_period))
        ).first()
        if rate_row:
            labor_rate_cents = int(
                rate_row.hourly_rate_cents * (1 + rate_row.burden_pct)
            )

    # Step 3: Fallback to platform default if no catalog row
    if labor_rate_cents is None:
        labor_rate_val2, _ = get_effective_setting(
            db, user_context.tenant_id, "default_labor_rate_cents", fallback=8500
        )
        labor_rate_cents = int(labor_rate_val2)
    margin_pct_val, _ = get_effective_setting(
        db, user_context.tenant_id, "margin_target_pct", fallback=20
    )
    margin_target_pct = int(margin_pct_val)

    # Quoted total from linked quote version (fallback to 0 if no quote)
    quoted_total_cents = 0
    if job.quote_version_id:
        from app.models.quoting import QuoteVersion

        qv = db.exec(
            select(QuoteVersion).where(QuoteVersion.id == job.quote_version_id)
        ).first()
        if qv:
            quoted_total_cents = getattr(qv, "total_price_cents", 0) or 0

    result = compute_projected_margin(
        db=db,
        tenant_id=user_context.tenant_id,
        job_id=job_id,
        hourly_rate_cents=labor_rate_cents,
        quoted_total_cents=quoted_total_cents,
        actual_labor_cost_cents=job.actual_labor_cost_cents,
        actual_material_cost_cents=job.actual_material_cost_cents,
        margin_target_pct=margin_target_pct,
    )

    return {
        "job_id": str(job.id),
        "quoted_total_cents": quoted_total_cents,
        "actual_labor_cost_cents": job.actual_labor_cost_cents,
        "actual_material_cost_cents": job.actual_material_cost_cents,
        **result,
        "projected_margin_pct": float(result["projected_margin_pct"]),
        "margin_target_pct": margin_target_pct,
    }


@router.get(
    "/{job_id}/projected-margin/test",
    status_code=200,
    summary="[TEST] Get projected margin — no auth required",
)
def projected_margin_test(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _projected_margin_impl(job_id, db, test_context)


@router.get(
    "/{job_id}/projected-margin",
    status_code=200,
    summary="Get projected margin with ETC",
)
def projected_margin(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
) -> dict:
    """Return projected margin for a job, incorporating latest ETC values."""
    return _projected_margin_impl(job_id, db, current_user)


# ==================== B20: BILLABLE ITEMS ====================


def _get_job_billable_items_impl(
    job_id: UUID,
    db: Session,
    user: AuthenticatedUser | TestUserContext,
) -> BillableItemsResponse:
    """
    Shared impl: return all time entries + expenses for a job.
    Used by the invoice builder (FE-B29) to pre-populate the line-item checklist.
    B20: is_already_invoiced is always False for time entries (MVP deferral — see design doc §D.1).
    Expenses: is_already_invoiced = (job_expense.invoice_line_id IS NOT NULL).
    """
    # IDOR-safe job lookup
    job = db.exec(
        select(Job)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user.tenant_id)
        .where(Job.is_active == True)
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Job not found",
                "status": 404,
                "detail": f"Job {job_id} does not exist in this tenant.",
            },
        )

    # Fetch customer name for the response header
    customer = db.exec(
        select(Customer)
        .where(Customer.id == job.customer_id)
        .where(Customer.tenant_id == user.tenant_id)
    ).first()

    # Fetch time entries with tech display_name JOIN
    time_entries_raw = db.exec(
        select(JobTimeEntry, User)
        .join(User, JobTimeEntry.user_id == User.id)
        .where(JobTimeEntry.job_id == job_id)
        .where(JobTimeEntry.tenant_id == user.tenant_id)
    ).all()

    time_entries = [
        BillableTimeEntry(
            id=te.id,
            user_id=te.user_id,
            tech_name=u.display_name,
            started_at=te.started_at,
            ended_at=te.ended_at,
            hours=te.hours,
            hourly_rate_cents=te.hourly_rate_cents,
            total_cost_cents=te.total_cost_cents,
            notes=te.notes,
            is_already_invoiced=False,  # MVP: always False for time entries
        )
        for te, u in time_entries_raw
    ]

    # Fetch ALL expenses (billable and non-billable) — FE shows non-billable greyed out
    expenses_raw = db.exec(
        select(JobExpense)
        .where(JobExpense.job_id == job_id)
        .where(JobExpense.tenant_id == user.tenant_id)
        .where(JobExpense.is_active == True)
    ).all()

    expenses = [
        BillableExpense(
            id=exp.id,
            description=exp.description,
            cost_cents=exp.cost_cents,
            billable_cents=exp.billable_cents,
            is_billable=exp.is_billable,
            is_already_invoiced=exp.invoice_line_id is not None,
            incurred_at=exp.incurred_at,
        )
        for exp in expenses_raw
    ]

    return BillableItemsResponse(
        job_id=job.id,
        job_number=job.job_number,
        customer_name=customer.display_name if customer else None,
        time_entries=time_entries,
        expenses=expenses,
    )


@router.get("/{job_id}/billable-items/test", response_model=BillableItemsResponse)
def get_job_billable_items_test(
    job_id: UUID,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> BillableItemsResponse:
    """Test-only — bypasses JWT auth. Uses canonical TestUserContext."""
    return _get_job_billable_items_impl(job_id=job_id, db=db, user=ctx)


@router.get("/{job_id}/billable-items", response_model=BillableItemsResponse)
def get_job_billable_items(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.create")),
) -> BillableItemsResponse:
    """
    Return all time entries + expenses for a job, used by the invoice builder
    to pre-populate the line-item checklist.
    B20: MVP — is_already_invoiced always False for time entries.
    """
    return _get_job_billable_items_impl(job_id=job_id, db=db, user=current_user)


# ==================== CE-1: INVOICE SIGN-OFF CONTEXT (D.1) ====================


def _get_signoff_context_impl(
    job_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> SignoffContextResponse:
    """CE-1 §D.1 — Return signable invoices for a job (mobile entry point).

    Signable = invoice.job_id == job_id, is_active=True, status code IN
    ('issued','partial'). Status resolved by code at runtime (never hardcoded
    UUIDs). Customer display_name mirrors the _get_job_impl expression.
    """
    # Tenant-scoped job fetch (404 on miss)
    row = db.exec(
        select(Job, Customer)
        .join(Customer, Job.customer_id == Customer.id, isouter=True)
        .where(Job.id == job_id)
        .where(Job.tenant_id == user_context.tenant_id)
    ).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Job not found",
                "status": 404,
                "detail": f"Job {job_id} does not exist in this tenant.",
            },
        )
    job, customer = row
    customer_display_name = customer.display_name if customer else ""

    # Resolve signable invoice status IDs by code (never hardcode UUIDs)
    signable_status_ids = db.exec(
        select(InvoiceStatus.id).where(
            InvoiceStatus.code.in_(["issued", "partial"]),
            (InvoiceStatus.tenant_id == user_context.tenant_id)
            | (InvoiceStatus.tenant_id.is_(None)),
        )
    ).all()

    if not signable_status_ids:
        return SignoffContextResponse(
            job_id=job.id,
            customer_display_name=customer_display_name,
            invoices=[],
        )

    # Fetch signable invoices for this job, newest first
    invoices = db.exec(
        select(Invoice)
        .where(Invoice.job_id == job_id)
        .where(Invoice.tenant_id == user_context.tenant_id)
        .where(Invoice.is_active.is_(True))
        .where(Invoice.status_id.in_(signable_status_ids))
        .order_by(Invoice.created_at.desc())
    ).all()

    # Batch-fetch active signoffs for all these invoices
    invoice_ids = [inv.id for inv in invoices]
    active_signoffs: dict = {}
    if invoice_ids:
        signoff_rows = db.exec(
            select(InvoiceSignoff)
            .where(InvoiceSignoff.invoice_id.in_(invoice_ids))
            .where(InvoiceSignoff.tenant_id == user_context.tenant_id)
            .where(InvoiceSignoff.superseded_at.is_(None))
        ).all()
        active_signoffs = {s.invoice_id: s for s in signoff_rows}

    context_invoices = []
    for inv in invoices:
        active = active_signoffs.get(inv.id)
        context_invoices.append(
            SignoffContextInvoice(
                invoice_id=inv.id,
                invoice_number=inv.invoice_number,
                status=db.exec(
                    select(InvoiceStatus.code).where(InvoiceStatus.id == inv.status_id)
                ).one(),
                total_cents=inv.total_cents,
                balance_due_cents=inv.balance_due_cents,
                currency=inv.currency,
                terms_text=inv.terms_and_conditions or DEFAULT_SIGNOFF_TERMS,
                active_signoff=(
                    InvoiceSignoffSummary(
                        signoff_id=active.id,
                        signed_by_name=active.signed_by_name,
                        signed_at=active.signed_at,
                    )
                    if active
                    else None
                ),
            )
        )

    return SignoffContextResponse(
        job_id=job.id,
        customer_display_name=customer_display_name,
        invoices=context_invoices,
    )


@router.get(
    "/{job_id}/signoff-context/test",
    response_model=SignoffContextResponse,
)
def get_signoff_context_test(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    """CE-1 §D.1 — Get signoff context for a job (TEST ENDPOINT — no auth)."""
    test_context = get_test_context()
    return _get_signoff_context_impl(job_id, db, test_context)


@router.get(
    "/{job_id}/signoff-context",
    response_model=SignoffContextResponse,
)
def get_signoff_context(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
):
    """CE-1 §D.1 — Get signoff context for a job. RBAC: jobs.view."""
    return _get_signoff_context_impl(job_id, db, current_user)
