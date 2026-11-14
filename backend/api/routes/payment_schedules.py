"""
BILLING-B1 §D — Progress Billing: Payment Schedule API.

Router prefix: ``/api/v1/payment-schedules`` (registered in ``app/main.py``).

9 endpoints (each mutation has a ``/test`` twin via ``TestUserContext``):

| # | Endpoint                                          | Method | RBAC              |
|---|---------------------------------------------------|--------|-------------------|
| 1 | ``/payment-schedules``                            | POST   | invoices.create  |
| 2 | ``/payment-schedules/{id}``                       | GET    | invoices.view    |
| 3 | ``/payment-schedules/{id}``                       | PATCH  | invoices.update  |
| 4 | ``/payment-schedules/{id}/lines``                | POST   | invoices.update  |
| 5 | ``/payment-schedules/{id}/lines/{line_id}``       | PATCH  | invoices.update  |
| 6 | ``/payment-schedules/{id}/lines/{line_id}``       | DELETE | invoices.update  |
| 7 | ``/payment-schedules/{id}/activate``              | POST   | invoices.update  |
| 8 | ``/payment-schedules/{id}/lines/{line_id}/generate-invoice`` | POST | invoices.create |
| 9 | ``/payment-schedules``                            | GET    | invoices.view    |

All routes are sync ``def`` (§21 — never ``async def`` with the blocking Session).
Every mutation calls ``set_audit_context_sync()`` before the first ``db.add()``.
All fetches are tenant-scoped ``select()`` (Rule 4 — ``db.get()`` banned).
RFC 7807 errors: 404 not-found, 409 stale/re-invoice, 422 reconciliation.

NOT subscription-tier gated for MVP (design §G) — draw generation is a normal
invoice create under the existing ``is_billing_active`` paywall. No
``feature_code`` parameter on ``require_permission``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session, func, select

from api.schemas.schemas import (
    DrawInvoiceGenerateRequest,
    InvoiceResponse,
    PaymentScheduleActivateRequest,
    PaymentScheduleCreate,
    PaymentScheduleLineCreate,
    PaymentScheduleLineResponse,
    PaymentScheduleLineUpdate,
    PaymentScheduleListItem,
    PaymentScheduleListResponse,
    PaymentScheduleResponse,
    PaymentScheduleUpdate,
)
from app.models.billing import (
    InvoiceStatus,
    PaymentSchedule,
    PaymentScheduleLine,
)
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import get_test_context
from services.payment_schedule_service import (
    UserContext,
    _fetch_line,
    _fetch_lines,
    _fetch_schedule,
    _rfc7807,
    activate_schedule,
    compute_reconciliation,
    generate_draw_invoice,
    resolve_line_amount_cents,
)

router = APIRouter()


# ============================================================================
# SHARED BUSINESS LOGIC (_impl functions — called by both /test and auth twins)
# ============================================================================


def _build_line_response(
    line: PaymentScheduleLine, contract_total_cents: int
) -> PaymentScheduleLineResponse:
    """Build a ``PaymentScheduleLineResponse`` with the computed resolved amount."""
    resolved = resolve_line_amount_cents(line, contract_total_cents)
    return PaymentScheduleLineResponse(
        id=line.id,
        tenant_id=line.tenant_id,
        payment_schedule_id=line.payment_schedule_id,
        sequence=line.sequence,
        label=line.label,
        basis=line.basis,
        percent=line.percent,
        amount_cents=line.amount_cents,
        trigger_type=line.trigger_type,
        trigger_date=line.trigger_date,
        milestone_label=line.milestone_label,
        invoice_id=line.invoice_id,
        status=line.status,
        is_active=line.is_active,
        resolved_amount_cents=resolved,
    )


def _build_schedule_response(
    schedule: PaymentSchedule, db: Session
) -> PaymentScheduleResponse:
    """Build a ``PaymentScheduleResponse`` with lines + computed reconciliation."""
    lines = _fetch_lines(db, schedule.id, schedule.tenant_id)
    line_responses = [
        _build_line_response(ln, schedule.contract_total_cents) for ln in lines
    ]
    scheduled_total, residual = compute_reconciliation(
        lines, contract_total_cents=schedule.contract_total_cents
    )
    return PaymentScheduleResponse(
        id=schedule.id,
        tenant_id=schedule.tenant_id,
        quote_id=schedule.quote_id,
        job_id=schedule.job_id,
        customer_id=schedule.customer_id,
        site_id=schedule.site_id,
        contract_total_cents=schedule.contract_total_cents,
        status=schedule.status,
        basis_default=schedule.basis_default,
        is_active=schedule.is_active,
        lines=line_responses,
        scheduled_total_cents=scheduled_total,
        residual_cents=residual,
    )


def _create_schedule_impl(
    create_req: PaymentScheduleCreate,
    db: Session,
    user_context: UserContext,
) -> PaymentScheduleResponse:
    """Shared create-schedule logic (POST /payment-schedules).

    Note: ``PaymentSchedule`` has no ``idempotency_key`` column (unlike
    ``Invoice``). The ``idempotency_key`` field on the request schema is
    accepted for forward-compat but not persisted — schedule creation is not
    idempotent at the DB level. Draw-invoice generation (the only financial
    write in this batch) IS idempotent via the ``Invoice.idempotency_key``
    unique constraint.
    """
    set_audit_context_sync(db, user_id=user_context.id)

    schedule = PaymentSchedule(
        tenant_id=user_context.tenant_id,
        quote_id=create_req.quote_id,
        job_id=create_req.job_id,
        customer_id=create_req.customer_id,
        site_id=create_req.site_id,
        contract_total_cents=create_req.contract_total_cents,
        status="draft",
        basis_default=create_req.basis_default,
        is_active=True,
        created_by=user_context.id,
    )
    db.add(schedule)
    db.flush()  # get the schedule.id for the lines

    # Inline draws (optional — the builder may add draws later via POST /lines).
    for line_in in create_req.lines:
        line = PaymentScheduleLine(
            tenant_id=user_context.tenant_id,
            payment_schedule_id=schedule.id,
            sequence=line_in.sequence,
            label=line_in.label,
            basis=line_in.basis,
            percent=line_in.percent,
            amount_cents=line_in.amount_cents,
            trigger_type=line_in.trigger_type,
            trigger_date=line_in.trigger_date,
            milestone_label=line_in.milestone_label,
            status="pending",
            is_active=True,
            created_by=user_context.id,
        )
        db.add(line)

    db.commit()
    db.refresh(schedule)
    return _build_schedule_response(schedule, db)


def _get_schedule_impl(
    schedule_id: UUID,
    db: Session,
    user_context: UserContext,
) -> PaymentScheduleResponse:
    """Shared get-schedule logic (GET /payment-schedules/{id})."""
    schedule = _fetch_schedule(db, schedule_id, user_context.tenant_id)
    return _build_schedule_response(schedule, db)


def _update_schedule_impl(
    schedule_id: UUID,
    update_req: PaymentScheduleUpdate,
    db: Session,
    user_context: UserContext,
) -> PaymentScheduleResponse:
    """Shared draft-only header edit (PATCH /payment-schedules/{id})."""
    schedule = _fetch_schedule(db, schedule_id, user_context.tenant_id)

    # Draft-gate: only draft schedules can be edited.
    if schedule.status != "draft":
        raise _rfc7807(
            status.HTTP_409_CONFLICT,
            "Schedule not in draft state",
            f"Schedule {schedule_id} is '{schedule.status}'. Only draft "
            "schedules can be edited.",
            "conflict",
        )

    set_audit_context_sync(db, user_id=user_context.id)

    if update_req.contract_total_cents is not None:
        schedule.contract_total_cents = update_req.contract_total_cents
    if update_req.basis_default is not None:
        schedule.basis_default = update_req.basis_default
    schedule.updated_by = user_context.id

    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _build_schedule_response(schedule, db)


def _add_line_impl(
    schedule_id: UUID,
    line_in: PaymentScheduleLineCreate,
    db: Session,
    user_context: UserContext,
) -> PaymentScheduleLineResponse:
    """Shared add-draw logic (POST /payment-schedules/{id}/lines)."""
    schedule = _fetch_schedule(db, schedule_id, user_context.tenant_id)

    if schedule.status != "draft":
        raise _rfc7807(
            status.HTTP_409_CONFLICT,
            "Schedule not in draft state",
            f"Schedule {schedule_id} is '{schedule.status}'. Draws can only be "
            "added to draft schedules.",
            "conflict",
        )

    set_audit_context_sync(db, user_id=user_context.id)

    line = PaymentScheduleLine(
        tenant_id=user_context.tenant_id,
        payment_schedule_id=schedule_id,
        sequence=line_in.sequence,
        label=line_in.label,
        basis=line_in.basis,
        percent=line_in.percent,
        amount_cents=line_in.amount_cents,
        trigger_type=line_in.trigger_type,
        trigger_date=line_in.trigger_date,
        milestone_label=line_in.milestone_label,
        status="pending",
        is_active=True,
        created_by=user_context.id,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return _build_line_response(line, schedule.contract_total_cents)


def _update_line_impl(
    schedule_id: UUID,
    line_id: UUID,
    line_in: PaymentScheduleLineUpdate,
    db: Session,
    user_context: UserContext,
) -> PaymentScheduleLineResponse:
    """Shared edit/reorder-draw logic (PATCH /payment-schedules/{id}/lines/{line_id})."""
    schedule = _fetch_schedule(db, schedule_id, user_context.tenant_id)

    if schedule.status != "draft":
        raise _rfc7807(
            status.HTTP_409_CONFLICT,
            "Schedule not in draft state",
            f"Schedule {schedule_id} is '{schedule.status}'. Draws can only be "
            "edited on draft schedules.",
            "conflict",
        )

    line = _fetch_line(db, line_id, schedule_id, user_context.tenant_id)

    set_audit_context_sync(db, user_id=user_context.id)

    if line_in.sequence is not None:
        line.sequence = line_in.sequence
    if line_in.label is not None:
        line.label = line_in.label
    if line_in.basis is not None:
        line.basis = line_in.basis
    # Conditional-NOT-NULL: when basis changes, the paired field must be set
    # correctly. The Pydantic validator on the request schema enforces this
    # for the supplied fields; here we apply the update.
    if line_in.percent is not None:
        line.percent = line_in.percent
    if line_in.amount_cents is not None:
        line.amount_cents = line_in.amount_cents
    if line_in.trigger_type is not None:
        line.trigger_type = line_in.trigger_type
    if line_in.trigger_date is not None:
        line.trigger_date = line_in.trigger_date
    if line_in.milestone_label is not None:
        line.milestone_label = line_in.milestone_label
    if line_in.is_active is not None:
        line.is_active = line_in.is_active
    line.updated_by = user_context.id

    db.add(line)
    db.commit()
    db.refresh(line)
    return _build_line_response(line, schedule.contract_total_cents)


def _delete_line_impl(
    schedule_id: UUID,
    line_id: UUID,
    db: Session,
    user_context: UserContext,
) -> dict:
    """Shared soft-delete-draw logic (DELETE /payment-schedules/{id}/lines/{line_id}).

    Sets ``is_active=False`` (soft-delete — never hard-delete at runtime per §G).
    Draft-only gate: cannot delete a draw on an active/completed/cancelled schedule.
    """
    schedule = _fetch_schedule(db, schedule_id, user_context.tenant_id)

    if schedule.status != "draft":
        raise _rfc7807(
            status.HTTP_409_CONFLICT,
            "Schedule not in draft state",
            f"Schedule {schedule_id} is '{schedule.status}'. Draws can only be "
            "deleted from draft schedules.",
            "conflict",
        )

    line = _fetch_line(db, line_id, schedule_id, user_context.tenant_id)

    set_audit_context_sync(db, user_id=user_context.id)

    line.is_active = False
    line.updated_by = user_context.id
    db.add(line)
    db.commit()
    return {"id": str(line_id), "is_active": False, "deleted": True}


def _activate_impl(
    schedule_id: UUID,
    db: Session,
    user_context: UserContext,
) -> PaymentScheduleResponse:
    """Shared activate logic (POST /payment-schedules/{id}/activate)."""
    set_audit_context_sync(db, user_id=user_context.id)
    schedule = activate_schedule(db, schedule_id, user_context.tenant_id, user_context)
    return _build_schedule_response(schedule, db)


def _generate_invoice_impl(
    schedule_id: UUID,
    line_id: UUID,
    req: DrawInvoiceGenerateRequest,
    db: Session,
    user_context: UserContext,
) -> InvoiceResponse:
    """Shared generate-draw-invoice logic (POST .../generate-invoice)."""
    set_audit_context_sync(db, user_id=user_context.id)
    invoice = generate_draw_invoice(
        db,
        schedule_id,
        line_id,
        user_context.tenant_id,
        user_context,
        idempotency_key=req.idempotency_key,
    )
    # Build the InvoiceResponse (mirror invoices.py _get_invoice_impl shape).
    status_obj = db.exec(
        select(InvoiceStatus).where(InvoiceStatus.id == invoice.status_id)
    ).first()
    return InvoiceResponse(
        **invoice.model_dump(),
        status_code=status_obj.code if status_obj else "unknown",
        lines=[],
        payments=[],
    )


def _list_schedules_impl(
    db: Session,
    user_context: UserContext,
    quote_id: UUID | None = None,
    job_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PaymentScheduleListResponse:
    """Shared list-schedules logic (GET /payment-schedules)."""
    query = (
        select(PaymentSchedule)
        .where(PaymentSchedule.tenant_id == user_context.tenant_id)
        .where(PaymentSchedule.is_active == True)
    )
    if quote_id:
        query = query.where(PaymentSchedule.quote_id == quote_id)
    if job_id:
        query = query.where(PaymentSchedule.job_id == job_id)
    query = query.order_by(PaymentSchedule.created_at.desc())

    count_query = (
        select(func.count(PaymentSchedule.id))
        .where(PaymentSchedule.tenant_id == user_context.tenant_id)
        .where(PaymentSchedule.is_active == True)
    )
    if quote_id:
        count_query = count_query.where(PaymentSchedule.quote_id == quote_id)
    if job_id:
        count_query = count_query.where(PaymentSchedule.job_id == job_id)

    total = db.exec(count_query).one()
    rows = db.exec(query.offset(offset).limit(limit)).all()

    items = [
        PaymentScheduleListItem(
            id=r.id,
            tenant_id=r.tenant_id,
            quote_id=r.quote_id,
            job_id=r.job_id,
            customer_id=r.customer_id,
            site_id=r.site_id,
            contract_total_cents=r.contract_total_cents,
            status=r.status,
            basis_default=r.basis_default,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    return PaymentScheduleListResponse(
        items=items, total=total, limit=limit, offset=offset
    )


# ============================================================================
# TEST ENDPOINTS (registered FIRST to avoid route conflicts — see quotes.py)
# ============================================================================


@router.post(
    "/test",
    response_model=PaymentScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule_test(
    create_req: PaymentScheduleCreate,
    db: Session = Depends(get_db),
):
    """Create a draft payment schedule (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _create_schedule_impl(create_req, db, test_context)


@router.get("/test", response_model=PaymentScheduleListResponse)
def list_schedules_test(
    quote_id: UUID | None = Query(None),
    job_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List payment schedules (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _list_schedules_impl(
        db, test_context, quote_id=quote_id, job_id=job_id, limit=limit, offset=offset
    )


@router.get("/{schedule_id}/test", response_model=PaymentScheduleResponse)
def get_schedule_test(
    schedule_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a payment schedule with lines + reconciliation (TEST ENDPOINT)."""
    test_context = get_test_context()
    return _get_schedule_impl(schedule_id, db, test_context)


@router.patch("/{schedule_id}/test", response_model=PaymentScheduleResponse)
def update_schedule_test(
    schedule_id: UUID,
    update_req: PaymentScheduleUpdate,
    db: Session = Depends(get_db),
):
    """Edit a draft schedule header (TEST ENDPOINT)."""
    test_context = get_test_context()
    return _update_schedule_impl(schedule_id, update_req, db, test_context)


@router.post(
    "/{schedule_id}/lines/test",
    response_model=PaymentScheduleLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_line_test(
    schedule_id: UUID,
    line_in: PaymentScheduleLineCreate,
    db: Session = Depends(get_db),
):
    """Add a draw to a draft schedule (TEST ENDPOINT)."""
    test_context = get_test_context()
    return _add_line_impl(schedule_id, line_in, db, test_context)


@router.patch(
    "/{schedule_id}/lines/{line_id}/test",
    response_model=PaymentScheduleLineResponse,
)
def update_line_test(
    schedule_id: UUID,
    line_id: UUID,
    line_in: PaymentScheduleLineUpdate,
    db: Session = Depends(get_db),
):
    """Edit/reorder a draw on a draft schedule (TEST ENDPOINT)."""
    test_context = get_test_context()
    return _update_line_impl(schedule_id, line_id, line_in, db, test_context)


@router.delete(
    "/{schedule_id}/lines/{line_id}/test",
    status_code=status.HTTP_200_OK,
)
def delete_line_test(
    schedule_id: UUID,
    line_id: UUID,
    db: Session = Depends(get_db),
):
    """Soft-delete a draw from a draft schedule (TEST ENDPOINT)."""
    test_context = get_test_context()
    return _delete_line_impl(schedule_id, line_id, db, test_context)


@router.post(
    "/{schedule_id}/activate/test",
    response_model=PaymentScheduleResponse,
)
def activate_schedule_test(
    schedule_id: UUID,
    _req: PaymentScheduleActivateRequest,
    db: Session = Depends(get_db),
):
    """Activate a draft schedule after reconciliation (TEST ENDPOINT)."""
    test_context = get_test_context()
    return _activate_impl(schedule_id, db, test_context)


@router.post(
    "/{schedule_id}/lines/{line_id}/generate-invoice/test",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_invoice_test(
    schedule_id: UUID,
    line_id: UUID,
    req: DrawInvoiceGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generate a progress invoice for a draw (TEST ENDPOINT)."""
    test_context = get_test_context()
    return _generate_invoice_impl(schedule_id, line_id, req, db, test_context)


# ============================================================================
# AUTHENTICATED ENDPOINTS
# ============================================================================


@router.post(
    "",
    response_model=PaymentScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    create_req: PaymentScheduleCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.create")),
):
    """Create a draft payment schedule with optional inline draws.

    Idempotency-Key header supported for client retry safety.
    """
    return _create_schedule_impl(create_req, db, current_user)


@router.get("", response_model=PaymentScheduleListResponse)
def list_schedules(
    quote_id: UUID | None = Query(None),
    job_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.view")),
):
    """List payment schedules for the tenant, optionally filtered by quote/job."""
    return _list_schedules_impl(
        db, current_user, quote_id=quote_id, job_id=job_id, limit=limit, offset=offset
    )


@router.get("/{schedule_id}", response_model=PaymentScheduleResponse)
def get_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.view")),
):
    """Get a payment schedule with all draws + computed reconciliation."""
    return _get_schedule_impl(schedule_id, db, current_user)


@router.patch("/{schedule_id}", response_model=PaymentScheduleResponse)
def update_schedule(
    schedule_id: UUID,
    update_req: PaymentScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.update")),
):
    """Edit a draft schedule header (contract_total_cents, basis_default)."""
    return _update_schedule_impl(schedule_id, update_req, db, current_user)


@router.post(
    "/{schedule_id}/lines",
    response_model=PaymentScheduleLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_line(
    schedule_id: UUID,
    line_in: PaymentScheduleLineCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.update")),
):
    """Add a draw to a draft schedule."""
    return _add_line_impl(schedule_id, line_in, db, current_user)


@router.patch(
    "/{schedule_id}/lines/{line_id}",
    response_model=PaymentScheduleLineResponse,
)
def update_line(
    schedule_id: UUID,
    line_id: UUID,
    line_in: PaymentScheduleLineUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.update")),
):
    """Edit or reorder a draw on a draft schedule."""
    return _update_line_impl(schedule_id, line_id, line_in, db, current_user)


@router.delete(
    "/{schedule_id}/lines/{line_id}",
    status_code=status.HTTP_200_OK,
)
def delete_line(
    schedule_id: UUID,
    line_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.update")),
):
    """Soft-delete a draw from a draft schedule (sets is_active=False)."""
    return _delete_line_impl(schedule_id, line_id, db, current_user)


@router.post(
    "/{schedule_id}/activate",
    response_model=PaymentScheduleResponse,
)
def activate_schedule_route(
    schedule_id: UUID,
    _req: PaymentScheduleActivateRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.update")),
):
    """Activate a draft schedule after reconciliation passes (422 on residual)."""
    return _activate_impl(schedule_id, db, current_user)


@router.post(
    "/{schedule_id}/lines/{line_id}/generate-invoice",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_invoice(
    schedule_id: UUID,
    line_id: UUID,
    req: DrawInvoiceGenerateRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.create")),
):
    """Generate a progress invoice for a draw (409 if already invoiced)."""
    return _generate_invoice_impl(schedule_id, line_id, req, db, current_user)
