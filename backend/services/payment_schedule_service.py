"""
BILLING-B1 §F — Progress Billing: Payment Schedule Orchestration service.

Pure-Python helpers + DB-touching orchestration for payment schedules and their
draws. No Celery — draw generation is synchronous and user-triggered.

Integrity rules (design §F, analysis §5.3.3), enforced at app layer + backstopped
by DB CHECKs / unique indexes:

1. Sum reconciliation — ``activate_schedule`` raises 422 if ``residual_cents != 0``.
2. Mixed basis — fixed_amount lines resolved first, percent lines distributed
   across the remainder (``contract_total - sum(fixed)``).
3. Deposit convention — ``sequence=1`` is the deposit in UI/PDF (no special column).
4. One invoice per draw — ``uq_psl_invoice_id`` partial unique + app-layer 409
   on re-invoice (void the prior invoice first).
5. Conditional NOT NULL — ``percent``/``amount_cents`` + ``trigger_date``/
   ``milestone_label`` via table CHECKs + Pydantic ``@model_validator``.

All DB-touching functions are plain ``def`` (sync Session — §21). Money is
integer cents; ``percent`` is ``Decimal`` (never float arithmetic on money).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.billing import (
    Invoice,
    InvoiceStatus,
    PaymentSchedule,
    PaymentScheduleLine,
)
from core.auth import AuthenticatedUser
from core.test_context import TestUserContext

# Re-export the user-context union type for route signatures.
UserContext = AuthenticatedUser | TestUserContext

# Decimal constants — never use float for money.
_HUNDRED = Decimal("100")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_QUANTIZE_CENTS = Decimal("1")  # round to whole cents


# ============================================================================
# Pure helpers (no DB) — unit-testable in isolation
# ============================================================================


def resolve_line_amount_cents(
    line: PaymentScheduleLine, contract_total_cents: int
) -> int:
    """Resolve a single draw's amount in integer cents.

    - ``basis='percent'``      → ``round(contract_total_cents * percent / 100)``
      using ``Decimal`` + ``ROUND_HALF_UP`` (banker's rounding is NOT used —
      matches typical billing expectations).
    - ``basis='fixed_amount'`` → ``line.amount_cents`` (already integer cents).

    The DB CHECK ``psl_basis_amount_chk`` guarantees exactly one of
    ``percent``/``amount_cents`` is set per the ``basis``, so no defensive
    branching on "both None" is needed here — the row cannot exist.
    """
    if line.basis == "fixed_amount":
        # CHECK guarantees amount_cents IS NOT NULL here.
        return int(line.amount_cents)  # type: ignore[arg-type]

    # percent path — Decimal arithmetic, never float.
    # CHECK guarantees percent IS NOT NULL here.
    pct = Decimal(line.percent)  # type: ignore[arg-type]
    total = Decimal(contract_total_cents)
    amount = (total * pct / _HUNDRED).quantize(_QUANTIZE_CENTS, rounding=ROUND_HALF_UP)
    return int(amount)


def compute_reconciliation(
    lines: list[PaymentScheduleLine],
    *,
    contract_total_cents: int,
) -> tuple[int, int]:
    """Compute ``(scheduled_total_cents, residual_cents)`` for a set of draws.

    Mixed-basis rule (§F rule 2): resolve ``fixed_amount`` lines first, then
    distribute ``percent`` lines across the **remainder**
    (``contract_total - sum(fixed)``). This means a 50% draw on a $10,000
    contract with a $2,000 fixed deposit resolves to 50% of $8,000 = $4,000,
    not 50% of $10,000.

    Only **active** lines (``is_active=True``) count toward the reconciliation.
    Inactive (soft-deleted) draws are excluded.

    Returns:
        ``(scheduled_total_cents, residual_cents)`` where
        ``residual = contract_total_cents - scheduled_total_cents``.
        A schedule can be activated only when ``residual_cents == 0``.
    """
    active_lines = [ln for ln in lines if ln.is_active]

    # Phase 1 — fixed amounts (sum directly).
    fixed_total = sum(
        int(ln.amount_cents)  # type: ignore[arg-type]
        for ln in active_lines
        if ln.basis == "fixed_amount"
    )

    # Phase 2 — percent lines distributed across the remainder.
    remainder = Decimal(contract_total_cents) - Decimal(fixed_total)
    percent_total = 0
    for ln in active_lines:
        if ln.basis != "percent":
            continue
        pct = Decimal(ln.percent)  # type: ignore[arg-type]
        amount = (remainder * pct / _HUNDRED).quantize(
            _QUANTIZE_CENTS, rounding=ROUND_HALF_UP
        )
        percent_total += int(amount)

    scheduled_total = fixed_total + percent_total
    residual = contract_total_cents - scheduled_total
    return scheduled_total, residual


# ============================================================================
# DB-touching orchestration (sync Session — §21)
# ============================================================================


def _rfc7807(status_code: int, title: str, detail: str, err_type: str) -> HTTPException:
    """Build an RFC 7807 Problem Details ``HTTPException``."""
    return HTTPException(
        status_code=status_code,
        detail={
            "type": f"https://errors.pilotfortrades.com/{err_type}",
            "title": title,
            "status": status_code,
            "detail": detail,
        },
    )


def _fetch_schedule(db: Session, schedule_id: UUID, tenant_id: UUID) -> PaymentSchedule:
    """Tenant-scoped schedule fetch (never ``db.get`` — Rule 4).

    Raises 404 (not 403) on cross-tenant access to prevent UUID enumeration.
    """
    schedule = db.exec(
        select(PaymentSchedule)
        .where(PaymentSchedule.id == schedule_id)
        .where(PaymentSchedule.tenant_id == tenant_id)
    ).first()
    if not schedule:
        raise _rfc7807(
            status.HTTP_404_NOT_FOUND,
            "Payment schedule not found",
            f"Schedule {schedule_id} does not exist in this tenant.",
            "not-found",
        )
    return schedule


def _fetch_line(
    db: Session, line_id: UUID, schedule_id: UUID, tenant_id: UUID
) -> PaymentScheduleLine:
    """Tenant-scoped draw fetch (never ``db.get`` — Rule 4)."""
    line = db.exec(
        select(PaymentScheduleLine)
        .where(PaymentScheduleLine.id == line_id)
        .where(PaymentScheduleLine.payment_schedule_id == schedule_id)
        .where(PaymentScheduleLine.tenant_id == tenant_id)
    ).first()
    if not line:
        raise _rfc7807(
            status.HTTP_404_NOT_FOUND,
            "Payment schedule line not found",
            f"Draw {line_id} does not exist on schedule {schedule_id} in this tenant.",
            "not-found",
        )
    return line


def _fetch_lines(
    db: Session, schedule_id: UUID, tenant_id: UUID
) -> list[PaymentScheduleLine]:
    """Fetch all draws for a schedule, ordered by sequence (tenant-scoped)."""
    return list(
        db.exec(
            select(PaymentScheduleLine)
            .where(PaymentScheduleLine.payment_schedule_id == schedule_id)
            .where(PaymentScheduleLine.tenant_id == tenant_id)
            .order_by(PaymentScheduleLine.sequence)
        ).all()
    )


def _resolve_draft_status(db: Session, tenant_id: UUID) -> InvoiceStatus:
    """Look up the ``draft`` invoice status row (tenant-scoped, fallback global).

    Mirrors ``_create_invoice_impl`` in ``api/routes/invoices.py`` — never
    hardcode a status UUID. Prefers a tenant-specific row, falls back to the
    platform default (``tenant_id IS NULL``).
    """
    draft = db.exec(
        select(InvoiceStatus)
        .where(InvoiceStatus.code == "draft")
        .where(
            (InvoiceStatus.tenant_id == tenant_id) | (InvoiceStatus.tenant_id.is_(None))
        )
        .order_by(InvoiceStatus.tenant_id.is_(None))  # tenant-specific first
    ).first()
    if not draft:
        raise _rfc7807(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Invoice draft status missing",
            "The 'draft' invoice_status row could not be resolved for this tenant.",
            "server-error",
        )
    return draft


def activate_schedule(
    db: Session,
    schedule_id: UUID,
    tenant_id: UUID,
    user_context: UserContext,
) -> PaymentSchedule:
    """Activate a draft payment schedule after reconciliation passes.

    §F rule 1: recompute reconciliation; if ``residual_cents != 0`` → 422
    (over/under-billing guard).

    Idempotent: re-activating an already-active schedule is a no-op 200.
    A ``cancelled`` or ``completed`` schedule cannot be re-activated (409).

    Args:
        db: Sync SQLAlchemy ``Session``.
        schedule_id: Schedule to activate.
        tenant_id: Caller's tenant (tenant-scoped fetch — Rule 4).
        user_context: Authenticated user or test context (for audit attribution).

    Returns:
        The activated ``PaymentSchedule`` (``status='active'``).
    """
    schedule = _fetch_schedule(db, schedule_id, tenant_id)

    # Idempotent no-op: already active.
    if schedule.status == "active":
        return schedule

    # Terminal/non-draft states cannot be activated.
    if schedule.status in ("cancelled", "completed"):
        raise _rfc7807(
            status.HTTP_409_CONFLICT,
            "Schedule not in draft state",
            f"Schedule {schedule_id} is '{schedule.status}' and cannot be activated.",
            "conflict",
        )

    # Reconciliation guard (rule 1).
    lines = _fetch_lines(db, schedule_id, tenant_id)
    _scheduled, residual = compute_reconciliation(
        lines, contract_total_cents=schedule.contract_total_cents
    )
    if residual != 0:
        sign = "over" if residual < 0 else "under"
        raise _rfc7807(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Schedule does not reconcile",
            (
                f"Draws {sign}-bill the contract total by {abs(residual)} cents. "
                "Adjust the draws so they sum exactly to contract_total_cents."
            ),
            "validation-error",
        )

    schedule.status = "active"
    schedule.updated_by = user_context.id
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def generate_draw_invoice(
    db: Session,
    schedule_id: UUID,
    line_id: UUID,
    tenant_id: UUID,
    user_context: UserContext,
    idempotency_key: str | None = None,
) -> Invoice:
    """Generate a ``progress`` invoice for a single draw.

    Preconditions (tenant-scoped, §F):
        - ``schedule.status == 'active'`` (else 409 — schedule not active).
        - ``line.status == 'pending'`` (else 409 — line already invoiced/void).
        - ``line.invoice_id IS NULL`` (rule 4 — one invoice per draw; else 409).

    Two-step write resolves the circular FK (``invoice ↔ payment_schedule_line``):
        1. Create ``Invoice(billing_mode='progress',
           payment_schedule_line_id=line.id, total_cents=resolved_amount,
           customer_id/site_id/job_id from schedule, status=draft,
           progress_pct=cumulative % billed to date)`` → commit.
        2. Back-fill ``line.invoice_id`` + ``line.status='invoiced'`` → commit.

    Idempotency-Key (24h TTL): a retried generation with the same key returns
    the SAME invoice (reuses the existing ``invoice.idempotency_key`` unique
    constraint — see ``uq_invoice_tenant_idempotency``).

    Args:
        db: Sync SQLAlchemy ``Session``.
        schedule_id: Parent schedule (must be active).
        line_id: Draw to invoice (must be pending, invoice_id NULL).
        tenant_id: Caller's tenant (tenant-scoped fetch — Rule 4).
        user_context: Authenticated user or test context (audit attribution).
        idempotency_key: Optional client-supplied idempotency key (24h TTL).

    Returns:
        The generated ``Invoice`` (``billing_mode='progress'``,
        ``payment_schedule_line_id`` set).
    """
    schedule = _fetch_schedule(db, schedule_id, tenant_id)
    line = _fetch_line(db, line_id, schedule_id, tenant_id)

    # Precondition: schedule must be active.
    if schedule.status != "active":
        raise _rfc7807(
            status.HTTP_409_CONFLICT,
            "Schedule not active",
            f"Schedule {schedule_id} is '{schedule.status}'. Activate it before "
            "generating draw invoices.",
            "conflict",
        )

    # Idempotency-Key reuse: if a key is supplied, check for an existing invoice
    # with that key in this tenant. If found, return it (retried request).
    # This check runs BEFORE the line-status precondition so a retried request
    # (where the line is already invoiced) returns the original invoice, not 409.
    if idempotency_key:
        existing = db.exec(
            select(Invoice)
            .where(Invoice.tenant_id == tenant_id)
            .where(Invoice.idempotency_key == idempotency_key)
        ).first()
        if existing:
            return existing

    # Precondition: line must be pending and uninvoiced (rule 4).
    if line.status != "pending" or line.invoice_id is not None:
        raise _rfc7807(
            status.HTTP_409_CONFLICT,
            "Draw already invoiced",
            f"Draw {line_id} has status='{line.status}' and invoice_id="
            f"{line.invoice_id}. Void the existing invoice first to re-invoice.",
            "conflict",
        )

    # Resolve the draw amount (Decimal, never float).
    draw_amount_cents = resolve_line_amount_cents(line, schedule.contract_total_cents)

    # Compute cumulative progress_pct across the schedule (invoiced + this draw).
    lines = _fetch_lines(db, schedule_id, tenant_id)
    cumulative_billed = 0
    for ln in lines:
        if not ln.is_active:
            continue
        # Count this draw's amount if it's already invoiced OR it's the current
        # draw being invoiced now.
        if ln.invoice_id is not None or ln.id == line.id:
            cumulative_billed += resolve_line_amount_cents(
                ln, schedule.contract_total_cents
            )
    if schedule.contract_total_cents > 0:
        progress_pct = (
            Decimal(cumulative_billed)
            / Decimal(schedule.contract_total_cents)
            * _HUNDRED
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        progress_pct = _ZERO

    # Resolve the draft invoice status (never hardcode a UUID).
    draft_status = _resolve_draft_status(db, tenant_id)

    # Generate an invoice number (reuse the invoices.py helper).
    # Imported lazily to avoid a circular import at module load.
    from api.routes.invoices import _generate_invoice_number

    invoice_number = _generate_invoice_number(tenant_id, db)

    # Step 1 — create the progress invoice with the line FK set.
    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=invoice_number,
        quote_id=schedule.quote_id,
        job_id=schedule.job_id,
        customer_id=schedule.customer_id,
        site_id=schedule.site_id,
        status_id=draft_status.id,
        subtotal_cents=draw_amount_cents,
        tax_cents=0,
        total_cents=draw_amount_cents,
        balance_due_cents=draw_amount_cents,
        currency="USD",
        issued_at=datetime.now(UTC),
        idempotency_key=idempotency_key,
        created_by=user_context.id,
        # B20 / BILLING-B1 fields:
        billing_mode="progress",
        progress_pct=progress_pct,
        payment_schedule_line_id=line.id,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Step 2 — back-fill the line's invoice_id + status (circular FK resolved).
    line.invoice_id = invoice.id
    line.status = "invoiced"
    line.updated_by = user_context.id
    db.add(line)
    db.commit()
    db.refresh(line)

    return invoice
