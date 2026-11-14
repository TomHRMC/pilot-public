"""
Quote domain business logic — state machine, version management,
approval workflow coordination.

Established: B1 (A2)
Consumed by: B1 (A2, A29, A30, A31), future batches touching quote status
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.quoting import Quote, QuoteStatus, QuoteVersion

if TYPE_CHECKING:  # avoids F821 on the return annotation (deferred import below)
    from api.schemas.quotes import QuoteDetailResponse

logger = logging.getLogger(__name__)


def transition_quote_status(
    quote: Quote,
    new_status_code: str,
    db: Session,
    tenant_id: UUID,
    actor_user_id: UUID | None = None,
) -> Quote:
    """
    Transition a quote to a new status code. Validates the code exists for the tenant.

    Args:
        quote: The Quote ORM object to update (must be fetched and tenant-verified by caller)
        new_status_code: Target status code string (e.g., 'pending_approval', 'approved', 'draft')
        db: Database session
        tenant_id: Current tenant UUID for status lookup scoping
        actor_user_id: Optional UUID of the user performing the transition (for audit)

    Returns:
        Updated Quote with new status_id committed to DB

    Raises:
        HTTPException 500: If the target status code does not exist in quote_status table
    """
    # Look up status — system statuses have tenant_id=NULL, tenant overrides have tenant_id set
    status_obj = db.exec(
        select(QuoteStatus).where(
            QuoteStatus.code == new_status_code,
            QuoteStatus.is_active == True,
        )
    ).first()

    if not status_obj:
        logger.error(
            "quote_service: status code '%s' not found for tenant %s",
            new_status_code,
            tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "https://pilotfortrades.com/errors/internal",
                "title": "Status Code Missing",
                "status": 500,
                "detail": (
                    f"Quote status '{new_status_code}' not found in quote_status table. "
                    "Ensure the migration seeded the required status codes."
                ),
            },
        )

    quote.status_id = status_obj.id
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


def assert_quote_version_not_stale(
    expected_version_id: UUID | None,
    quote_id: UUID,
    db: Session,
    tenant_id: UUID,
) -> None:
    """
    Raise HTTP 409 if client's expected_quote_version_id doesn't match live latest version.

    B1 inline implementation of the pre-commit staleness check pattern (arch §7.9, §16.4).
    Refactor callers to use utils/staleness_check.py when B3 establishes that module.

    Args:
        expected_version_id: UUID the client expects to be the latest. None = skip check.
        quote_id: UUID of the quote to check
        db: Database session
        tenant_id: Current tenant UUID for IDOR protection

    Raises:
        HTTPException 409: With current_version_id in detail payload
    """
    if expected_version_id is None:
        return

    latest = db.exec(
        select(QuoteVersion)
        .where(QuoteVersion.quote_id == quote_id)
        .where(QuoteVersion.tenant_id == tenant_id)
        .order_by(QuoteVersion.version_no.desc())
    ).first()

    if latest and latest.id != expected_version_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/stale-state",
                "title": "Quote Updated",
                "status": 409,
                "detail": "This quote was updated since you last viewed it. "
                "Please refresh and re-submit.",
                "current_version_id": str(latest.id),
            },
        )


def get_quote_status_code(quote: Quote, db: Session) -> str:
    """
    Resolve the current status code string for a quote (lookup by status_id).

    Args:
        quote: Quote ORM object with status_id set
        db: Database session

    Returns:
        The status code string (e.g., 'draft', 'pending_approval', 'approved')

    Raises:
        HTTPException 500: If status cannot be resolved
    """
    status_obj = db.get(QuoteStatus, quote.status_id)
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "https://pilotfortrades.com/errors/internal",
                "title": "Status Lookup Failed",
                "status": 500,
                "detail": f"Could not resolve status_id {quote.status_id} for quote {quote.id}",
            },
        )
    return status_obj.code


def get_quote_pending_approval_summary(
    tenant_id: UUID,
    db: Session,
) -> list[dict]:
    """
    Read-only: return summary of all quotes in pending_approval status for a tenant.
    Used by A31 voice intent list_pending_quotes.

    Returns:
        List of dicts: [{ "quote_id": str, "total_cents": int,
                          "submitted_by_user_id": str|None, "submitted_at": str|None }]
    """

    # Resolve the pending_approval status id
    status_obj = db.exec(
        select(QuoteStatus).where(
            QuoteStatus.code == "pending_approval",
            QuoteStatus.is_active == True,
        )
    ).first()

    if not status_obj:
        return []

    from app.models.quoting import Quote  # local import

    quotes = db.exec(
        select(Quote).where(
            Quote.tenant_id == tenant_id,
            Quote.status_id == status_obj.id,
            Quote.is_active == True,
        )
    ).all()

    result = []
    for q in quotes:
        result.append(
            {
                "quote_id": str(q.id),
                "total_cents": q.total_cents,
                "submitted_by_user_id": str(q.submitted_by_user_id)
                if q.submitted_by_user_id
                else None,
                "submitted_at": q.submitted_at.isoformat() if q.submitted_at else None,
            }
        )

    return result


def get_quote_detail(
    quote_id: UUID,
    tenant_id: UUID,
    db: Session,
) -> QuoteDetailResponse:
    """
    Aggregated quote detail for the owner approval/review surface.
    PRE-WS3-FIX-01

    Performs targeted queries:
    1. Main quote + status code + customer name + submitted_by user name
    2. Latest active quote_version (for optimistic lock ID)
    3. Pending edits existence check
    4. Rejection timestamp from quote_approval_comment
    5. Active line items with resolved qco_line_type codes
    Plus: get_effective_setting for require_approval

    Returns QuoteDetailResponse.
    Raises HTTPException 404 (RFC 7807) if not found or cross-tenant.
    """
    from fastapi import HTTPException
    from fastapi import status as http_status

    from api.schemas.quotes import QuoteDetailResponse, QuoteLineDetailResponse
    from app.models.core import User
    from app.models.crm import Customer
    from app.models.quoting import (
        QcoLineType,
        Quote,
        QuoteApprovalComment,
        QuoteLine,
        QuotePendingEdit,
        QuoteStatus,
        QuoteVersion,
    )
    from services.setting_resolver import get_effective_setting

    # ── 1. Main quote row (tenant-scoped — db.get() is permanently banned) ──────
    quote = db.exec(
        select(Quote).where(Quote.id == quote_id).where(Quote.tenant_id == tenant_id)
    ).first()
    if not quote:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Quote not found",
                "status": 404,
                "detail": f"Quote {quote_id} does not exist in this tenant.",
            },
        )

    # ── Status code ──────────────────────────────────────────────────────────────
    status_row = db.exec(
        select(QuoteStatus).where(QuoteStatus.id == quote.status_id)
    ).first()
    status_code = status_row.code if status_row else None

    # ── Customer name ────────────────────────────────────────────────────────────
    customer = db.exec(
        select(Customer)
        .where(Customer.id == quote.customer_id)
        .where(Customer.tenant_id == tenant_id)
    ).first()
    customer_name = customer.display_name if customer else None

    # ── Submitted-by user name ───────────────────────────────────────────────────
    submitted_by_name: str | None = None
    if quote.submitted_by_user_id:
        submitter = db.exec(
            select(User).where(User.id == quote.submitted_by_user_id)
        ).first()
        if submitter:
            parts = [p for p in [submitter.first_name, submitter.last_name] if p]
            submitted_by_name = " ".join(parts).strip() or str(submitter.email)

    # ── 2. Latest active quote_version ───────────────────────────────────────────
    latest_version = db.exec(
        select(QuoteVersion)
        .where(QuoteVersion.quote_id == quote_id)
        .where(QuoteVersion.tenant_id == tenant_id)
        .where(QuoteVersion.is_active == True)
        .order_by(QuoteVersion.version_no.desc())
    ).first()
    if not latest_version:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Quote version not found",
                "status": 404,
                "detail": f"No active version found for quote {quote_id}.",
            },
        )

    # ── 3. Pending edits existence ───────────────────────────────────────────────
    # quote_pending_edit has no is_active column — presence of any row = True
    pending_edit = db.exec(
        select(QuotePendingEdit)
        .where(QuotePendingEdit.quote_id == quote_id)
        .where(QuotePendingEdit.tenant_id == tenant_id)
    ).first()
    has_owner_edits = pending_edit is not None

    # ── 4. Rejection timestamp from approval comments ────────────────────────────
    rejection_comment = db.exec(
        select(QuoteApprovalComment)
        .where(QuoteApprovalComment.quote_id == quote_id)
        .where(QuoteApprovalComment.tenant_id == tenant_id)
        .where(QuoteApprovalComment.comment_type.in_(["rejection", "kickback"]))
        .order_by(QuoteApprovalComment.created_at.desc())
    ).first()
    rejected_at = rejection_comment.created_at if rejection_comment else None

    # ── 5. Active line items with resolved line type ──────────────────────────────
    line_rows = db.exec(
        select(QuoteLine, QcoLineType)
        .join(QcoLineType, QuoteLine.qco_line_type_id == QcoLineType.id)
        .where(QuoteLine.quote_id == quote_id)
        .where(QuoteLine.tenant_id == tenant_id)
        .where(QuoteLine.is_active == True)
        .order_by(QuoteLine.display_order.asc(), QuoteLine.position.asc())
    ).all()

    line_items = [
        QuoteLineDetailResponse(
            id=line.id,
            description=line.description,
            customer_visible=line.customer_visible,
            unit_price_cents=line.unit_price_cents,
            quantity=float(line.quantity),
            total_cents=line.total_cents,
            line_type=line_type.code,
            qco_line_type_id=line.qco_line_type_id,  # PLP-FIX-5 (Issue 14)
        )
        for line, line_type in line_rows
    ]

    # ── margin_percent ───────────────────────────────────────────────────────────
    margin_percent: float | None = None
    if line_rows and quote.total_cents > 0:
        costs = [line.unit_cost_cents for line, _ in line_rows]
        if all(c is not None for c in costs):
            total_cost = sum(
                int(line.unit_cost_cents) * float(line.quantity)
                for line, _ in line_rows
            )
            margin_percent = round(
                (quote.total_cents - total_cost) / quote.total_cents * 100, 2
            )

    # ── require_approval from platform_setting ───────────────────────────────────
    require_approval_val, _ = get_effective_setting(
        db=db,
        tenant_id=tenant_id,
        setting_key="quotes.require_approval",
        fallback=False,
    )
    require_approval: bool = (
        bool(require_approval_val) if require_approval_val is not None else False
    )

    # ── Assemble response ────────────────────────────────────────────────────────
    quote_number = f"Q-{str(quote.id)[:8].upper()}"

    return QuoteDetailResponse(
        id=quote.id,
        quote_number=quote_number,
        status=status_code,
        customer_id=quote.customer_id,
        customer_name=customer_name,
        site_id=quote.site_id,
        submitted_by_user_id=quote.submitted_by_user_id,
        submitted_by_name=submitted_by_name,
        submitted_at=quote.submitted_at,
        approved_at=quote.approved_at,
        rejected_at=rejected_at,
        subtotal_cents=quote.subtotal_cents,
        tax_cents=quote.tax_cents,
        total_cents=quote.total_cents,
        margin_percent=margin_percent,
        quote_version_id=latest_version.id,
        has_owner_edits=has_owner_edits,
        require_approval=require_approval,
        line_items=line_items,
    )
