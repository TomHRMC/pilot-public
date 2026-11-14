"""
Task 1-D-3: Public Invoice Payment Link API

Routes:
  POST /api/v1/invoices/{id}/send          → authenticated — generates public link
  POST /api/v1/invoices/{id}/send/test     → test version (no auth)

  Public GET/pay routes removed — see api/routes/public_invoices.py (canonical).

FIND-073: HMAC-SHA256 signed token integration for invoice public links.
- Replaces legacy token_hash (SHA-256) with HMAC-signed payload.
- Token payload includes: link_id, link_type='invoice', customer_id, expiration.
- Signature verification replaces DB hash lookup.
"""

import base64
import binascii
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlmodel import Session, func, select

from api.schemas.invoice_signoff import (
    InvoiceSignoffCreateRequest,
    InvoiceSignoffDetailResponse,
    InvoiceSignoffResponse,
)
from api.schemas.schemas import (
    InvoiceCreate,
    InvoiceLineItemCreate,
    InvoiceLineResponse,
    InvoiceListResponse,
    InvoicePublicLinkResponse,
    InvoiceResponse,
    InvoiceSendRequest,
    InvoiceSummary,
    PaymentRecordRequest,
    PaymentResponse,
    PaymentSummaryResponse,
    ResolveVarianceRequest,
)
from app.models.billing import (
    Invoice,
    InvoiceLine,
    InvoicePublicLink,
    InvoiceSignoff,
    InvoiceStatus,
    Payment,
)
from app.models.crm import Customer, Site
from app.models.fulfillment import Job, JobExpense, JobTimeEntry
from app.models.quoting import QcoLineType, Quote, QuoteLine
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.public_link_signer import (
    generate_signed_token,
)
from services.s3_service import (
    build_signature_object_key,
    generate_presigned_get_url,
    put_signature_object,
)

router = APIRouter()


# ==================== HELPERS ====================


def _generate_invoice_number(tenant_id: UUID, db: Session) -> str:
    """
    Generate a sequential invoice number for the tenant: INV-000001, INV-000002, ...
    Uses MAX(numeric suffix) + 1 scoped to tenant_id.
    Retries up to 5 times on unique constraint violation (race condition guard).
    Format: INV-000001 (sequential, tenant-scoped, zero-padded 6 digits)

    B19: Updated from random hex (INV-YYYYMMDD-XXXXXX) to sequential format.
    Existing records in old format are preserved — only new records use INV-000001.
    """
    from sqlalchemy import text as sa_text

    for _ in range(5):
        # SUBSTRING(invoice_number FROM 5) strips the 4-char 'INV-' prefix
        # CAST handles both old format (non-numeric) and new format — use NULLIF to skip old-format rows
        result = db.exec(
            sa_text(
                "SELECT COALESCE(MAX(CASE WHEN invoice_number ~ '^INV-[0-9]+$' "
                "THEN CAST(SUBSTRING(invoice_number FROM 5) AS INTEGER) ELSE 0 END), 0) + 1 "
                "FROM invoice WHERE tenant_id = :tid"
            ).bindparams(tid=str(tenant_id))
        ).first()
        next_num = result[0] if result else 1
        invoice_number = f"INV-{str(next_num).zfill(6)}"

        # Check uniqueness constraint (tenant_id, invoice_number)
        existing = db.exec(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id, Invoice.invoice_number == invoice_number
            )
        ).first()

        if not existing:
            return invoice_number

    # Fallback: use UUID suffix if all retries exhausted
    return f"INV-{str(tenant_id)[:8].upper()}"


# ==================== SHARED BUSINESS LOGIC ====================


def _send_invoice_impl(
    invoice_id: UUID,
    send_req: InvoiceSendRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> InvoicePublicLinkResponse:
    """
    Generate an InvoicePublicLink for the given invoice.
    FIND-073: Use HMAC-SHA256 signed token instead of legacy token_hash.
    """
    invoice = db.exec(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .where(Invoice.tenant_id == user_context.tenant_id)
    ).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Invoice not found",
                "status": 404,
                "detail": f"Invoice {invoice_id} does not exist in this tenant.",
            },
        )

    # Create InvoicePublicLink first so we have the link_id for token generation
    expires_at = None
    if send_req.expires_in_days is not None and send_req.expires_in_days > 0:
        expires_at = datetime.now(UTC) + timedelta(days=send_req.expires_in_days)

    import secrets

    link = InvoicePublicLink(
        tenant_id=user_context.tenant_id,
        invoice_id=invoice_id,
        contact_id=send_req.contact_id,
        token_hash=secrets.token_hex(
            32
        ),  # Unique random token (FIND-073 replaced by signed_token)
        expires_at=expires_at,
        max_uses=send_req.max_uses,
        used_count=0,
        status="active",
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    # FIND-073: Generate HMAC-signed token with payload: {link_id, link_type, customer_id, expiration}
    signed_token, _token_expiration = generate_signed_token(
        link_id=link.id,
        link_type="invoice",
        customer_id=invoice.customer_id,
        expires_in_days=send_req.expires_in_days or 90,
    )

    # Store the signed_token in the model
    link.signed_token = signed_token
    db.add(link)
    db.commit()
    db.refresh(link)

    # Build response — return the signed_token for URL construction
    response = InvoicePublicLinkResponse(
        id=link.id,
        tenant_id=link.tenant_id,
        invoice_id=link.invoice_id,
        contact_id=link.contact_id,
        signed_token=signed_token,  # HMAC-signed token for URL construction (FIND-073)
        expires_at=link.expires_at,
        max_uses=link.max_uses,
        used_count=link.used_count,
        status=link.status,
        last_used_at=link.last_used_at,
        created_at=link.created_at,
    )
    return response


# ==================== SHARED INVOICE CRUD LOGIC ====================


def _list_invoices_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    invoice_status: str | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    overdue: bool = False,
    limit: int = 50,
    offset: int = 0,
    customer_search: str | None = None,
    issued_from: datetime | None = None,
    issued_to: datetime | None = None,
    customer_id: "UUID | None" = None,
) -> InvoiceListResponse:
    """Shared list-invoices logic for both authenticated and test endpoints.

    UI-FIX-1C: Added customer_search, issued_from, issued_to filter params.
    UI-FIX-2D: Added customer_id exact UUID filter param.
    """
    now = datetime.now(UTC)

    query = (
        select(Invoice, InvoiceStatus, Customer)
        .join(InvoiceStatus, Invoice.status_id == InvoiceStatus.id)
        .join(Customer, Invoice.customer_id == Customer.id, isouter=True)
        .where(Invoice.tenant_id == user_context.tenant_id)
        .where(Customer.tenant_id == user_context.tenant_id)  # IDOR protection
    )

    if invoice_status:
        query = query.where(InvoiceStatus.code == invoice_status)
    if due_before:
        query = query.where(Invoice.due_at <= due_before)
    if due_after:
        query = query.where(Invoice.due_at >= due_after)

    # SD-06B: overdue=true — due_at < now AND status NOT IN ('paid', 'void', 'writeoff')
    if overdue:
        query = query.where(Invoice.due_at < now).where(
            InvoiceStatus.code.not_in(["paid", "void", "writeoff"])
        )

    # UI-FIX-1C: customer name search
    if customer_search:
        query = query.where(Customer.display_name.ilike(f"%{customer_search}%"))

    # UI-FIX-2D: exact customer UUID filter
    if customer_id:
        query = query.where(Invoice.customer_id == customer_id)

    # UI-FIX-1C: issued_at date range
    if issued_from:
        query = query.where(Invoice.issued_at >= issued_from)
    if issued_to:
        query = query.where(Invoice.issued_at <= issued_to)

    query = query.order_by(Invoice.created_at.desc())

    # Build count query with same filters
    count_query = (
        select(func.count(Invoice.id))
        .select_from(Invoice)
        .join(InvoiceStatus, Invoice.status_id == InvoiceStatus.id)
        .join(Customer, Invoice.customer_id == Customer.id, isouter=True)
        .where(Invoice.tenant_id == user_context.tenant_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    )
    if invoice_status:
        count_query = count_query.where(InvoiceStatus.code == invoice_status)
    if due_before:
        count_query = count_query.where(Invoice.due_at <= due_before)
    if due_after:
        count_query = count_query.where(Invoice.due_at >= due_after)
    if overdue:
        count_query = count_query.where(Invoice.due_at < now).where(
            InvoiceStatus.code.not_in(["paid", "void", "writeoff"])
        )
    if customer_search:
        count_query = count_query.where(
            Customer.display_name.ilike(f"%{customer_search}%")
        )
    if customer_id:
        count_query = count_query.where(Invoice.customer_id == customer_id)
    if issued_from:
        count_query = count_query.where(Invoice.issued_at >= issued_from)
    if issued_to:
        count_query = count_query.where(Invoice.issued_at <= issued_to)

    total = db.exec(count_query).one()
    rows = db.exec(query.offset(offset).limit(limit)).all()

    items = []
    for invoice, invoice_status_obj, customer in rows:
        summary = InvoiceSummary(
            **invoice.model_dump(),
            status_code=invoice_status_obj.code,
            customer_name=customer.display_name if customer else None,
        )
        items.append(summary)

    return InvoiceListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# B20: payment_terms → due_at day-offset mapping
# Matches chk_invoice_payment_terms and platform_setting_catalog allowed_values exactly
PAYMENT_TERMS_DAYS: dict[str, int] = {
    "due_on_receipt": 0,
    "net_15": 15,
    "net_30": 30,
}


def _compute_due_at_from_payment_terms(
    payment_terms: str | None,
    issued_at: "datetime | None",
    due_at_override: "datetime | None",
) -> "datetime | None":
    """
    B20 §G.1: Compute due_at from payment_terms + issued_at.
    - 'due_on_receipt' / 'net_15' / 'net_30': issued_at + N days
    - 'custom_date': caller must supply due_at_override (422 if absent)
    - None: return due_at_override unchanged (caller controls)
    """
    from fastapi import HTTPException
    from fastapi import status as http_status

    if payment_terms is None:
        return due_at_override
    if payment_terms in PAYMENT_TERMS_DAYS:
        if issued_at:
            from datetime import timedelta

            return issued_at + timedelta(days=PAYMENT_TERMS_DAYS[payment_terms])
        return due_at_override
    if payment_terms == "custom_date":
        if due_at_override is None:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "type": "https://errors.pilotfortrades.com/validation-error",
                    "title": "Missing due_at",
                    "status": 422,
                    "detail": "due_at is required when payment_terms is 'custom_date'.",
                },
            )
        return due_at_override
    return due_at_override


# ── PLP-FIX-1: custom invoice line helpers (sync def — rules §21) ────────────


def _resolve_qco_line_type_id(db: Session, code: str | None) -> uuid.UUID:
    """Resolve ``qco_line_type.code`` → id (default ``'misc'``).

    404 RFC 7807 if the code does not exist.
    """
    resolved = code or "misc"
    row = db.exec(select(QcoLineType).where(QcoLineType.code == resolved)).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Line type not found",
                "status": 404,
                "detail": f"qco_line_type code '{resolved}' does not exist.",
            },
        )
    return row.id


def _persist_custom_lines(
    line_items: list[InvoiceLineItemCreate],
    invoice_id: uuid.UUID,
    start_position: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> int:
    """Insert ad_hoc ``InvoiceLine`` rows; returns the added subtotal_cents.

    Each line: ``source_type='ad_hoc'``, ``source_id=None``, tax fields NULL,
    ``subtotal_cents = total_cents = round(quantity * unit_price_cents)``
    (computed with ``Decimal`` -- never float math on money).
    """
    added_subtotal = 0
    for i, item in enumerate(line_items):
        line_type_id = _resolve_qco_line_type_id(db, item.qco_line_type_code)
        # Decimal math on money (rules §22) -- quantity is Numeric(12,3)
        line_cents = round(item.quantity * Decimal(item.unit_price_cents))
        line = InvoiceLine(
            tenant_id=user_context.tenant_id,
            invoice_id=invoice_id,
            source_type="ad_hoc",
            source_id=None,
            position=start_position + i,
            qco_line_type_id=line_type_id,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            unit_price_cents=item.unit_price_cents,
            subtotal_cents=line_cents,
            total_cents=line_cents,
            is_active=True,
            created_by=user_context.id,
        )
        db.add(line)
        added_subtotal += line_cents
    return added_subtotal


def _create_invoice_impl(
    create_req: InvoiceCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> InvoiceResponse:
    """Shared create-invoice logic for both authenticated and test endpoints.

    PLP-FIX-1: three-mode resolution (quote / job / standalone) replaces the
    prior quote_id/job_id XOR. Custom ``line_items[]`` are appended after
    source-derived lines in all modes.
    """
    try:
        # ── Mode resolution (design §D.3) ────────────────────────────────────
        has_quote = bool(create_req.quote_id)
        has_job = bool(create_req.job_id)
        has_customer = bool(create_req.customer_id)
        has_site = bool(create_req.site_id)
        has_lines = bool(create_req.line_items)

        if has_quote and not has_job and not has_customer and not has_site:
            mode = "quote"
        elif has_job and not has_quote and not has_customer and not has_site:
            mode = "job"
        elif has_customer and has_site and not has_quote and not has_job and has_lines:
            mode = "standalone"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://errors.pilotfortrades.com/invalid-mode",
                    "title": "Invalid invoice source",
                    "status": 400,
                    "detail": (
                        "Provide exactly one invoice source: quote_id, job_id, "
                        "or customer_id+site_id with at least one line_items entry."
                    ),
                },
            )

        # Fetch draft status — prefer tenant-scoped, fall back to global (tenant_id IS NULL)
        draft_status = db.exec(
            select(InvoiceStatus)
            .where(
                InvoiceStatus.code == "draft",
                (InvoiceStatus.tenant_id == user_context.tenant_id)
                | (InvoiceStatus.tenant_id.is_(None)),
            )
            .order_by(InvoiceStatus.tenant_id.is_(None))  # tenant-specific first
        ).first()
        if not draft_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Draft status not found",
            )

        if mode == "quote":
            # ── Quote mode ────────────────────────────────────────────────────
            quote = db.exec(
                select(Quote).where(
                    Quote.id == create_req.quote_id,
                    Quote.tenant_id == user_context.tenant_id,
                )
            ).first()
            if not quote:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "type": "https://errors.pilotfortrades.com/not-found",
                        "title": "Quote not found",
                        "status": 404,
                        "detail": f"Quote {create_req.quote_id} does not exist in this tenant.",
                    },
                )

            # Fetch quote lines (excluding section headers)
            quote_lines = db.exec(
                select(QuoteLine)
                .where(
                    QuoteLine.quote_id == create_req.quote_id,
                    QuoteLine.tenant_id == user_context.tenant_id,
                    QuoteLine.is_active == True,
                    QuoteLine.is_section_header == False,
                )
                .order_by(QuoteLine.position)
            ).all()

            # Generate invoice number
            invoice_number = _generate_invoice_number(user_context.tenant_id, db)

            # B20: Compute due_at from payment_terms (design doc §G.1)
            resolved_issued_at = create_req.issued_at or datetime.now(UTC)
            resolved_due_at = _compute_due_at_from_payment_terms(
                create_req.payment_terms, resolved_issued_at, create_req.due_at
            )
            # Create invoice
            invoice = Invoice(
                tenant_id=user_context.tenant_id,
                invoice_number=invoice_number,
                quote_id=create_req.quote_id,
                customer_id=quote.customer_id,
                site_id=quote.site_id,
                status_id=draft_status.id,
                subtotal_cents=quote.subtotal_cents,
                tax_cents=quote.tax_cents,
                total_cents=quote.total_cents,
                balance_due_cents=quote.total_cents,
                currency=quote.currency,
                customer_notes=create_req.customer_notes,
                terms_and_conditions=create_req.terms_and_conditions,
                issued_at=resolved_issued_at,
                due_at=resolved_due_at,
                idempotency_key=create_req.idempotency_key,
                created_by=user_context.id,
                # B20: Invoice builder fields
                payment_terms=create_req.payment_terms,
                billing_mode=create_req.billing_mode,
                progress_pct=create_req.progress_pct,
                internal_memo=create_req.internal_memo,
            )
            db.add(invoice)
            db.flush()

            # Create invoice lines from quote lines
            for quote_line in quote_lines:
                line = InvoiceLine(
                    tenant_id=user_context.tenant_id,
                    invoice_id=invoice.id,
                    source_type="quote_line",
                    source_id=quote_line.id,
                    position=quote_line.position,
                    qco_line_type_id=quote_line.qco_line_type_id,
                    pricebook_item_id=quote_line.pricebook_item_id,
                    description=quote_line.description,
                    quantity=quote_line.quantity,
                    unit=quote_line.unit,
                    unit_price_cents=quote_line.unit_price_cents,
                    taxability_code=quote_line.taxability_code,
                    tax_rate_pct=quote_line.tax_rate_pct,
                    tax_basis_cents=quote_line.tax_basis_cents,
                    tax_amount_cents=quote_line.tax_amount_cents,
                    tax_jurisdiction_code=quote_line.tax_jurisdiction_code,
                    tax_as_of=quote_line.tax_as_of,
                    tax_source=quote_line.tax_source,
                    subtotal_cents=quote_line.subtotal_cents,
                    total_cents=quote_line.total_cents,
                    is_active=True,
                    created_by=user_context.id,
                )
                db.add(line)

            # PLP-FIX-1: append custom ad_hoc lines after quote lines
            next_position = max((ql.position for ql in quote_lines), default=-1) + 1
            custom_subtotal = _persist_custom_lines(
                create_req.line_items or [],
                invoice.id,
                next_position,
                db,
                user_context,
            )
            if custom_subtotal:
                invoice.subtotal_cents += custom_subtotal
                invoice.total_cents += custom_subtotal
                invoice.balance_due_cents += custom_subtotal

            db.commit()
            db.refresh(invoice)

        elif mode == "job":
            # ── Job mode ──────────────────────────────────────────────────────
            job = db.exec(
                select(Job).where(
                    Job.id == create_req.job_id,
                    Job.tenant_id == user_context.tenant_id,
                )
            ).first()
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "type": "https://errors.pilotfortrades.com/not-found",
                        "title": "Job not found",
                        "status": 404,
                        "detail": f"Job {create_req.job_id} does not exist in this tenant.",
                    },
                )

            # Fetch unbilled time entries (JobTimeEntry has no is_active column)
            time_entries = db.exec(
                select(JobTimeEntry).where(
                    JobTimeEntry.job_id == create_req.job_id,
                    JobTimeEntry.tenant_id == user_context.tenant_id,
                )
            ).all()

            # Fetch unbilled expenses
            expenses = db.exec(
                select(JobExpense).where(
                    JobExpense.job_id == create_req.job_id,
                    JobExpense.tenant_id == user_context.tenant_id,
                    JobExpense.is_billable == True,
                    JobExpense.invoice_line_id == None,
                    JobExpense.is_active == True,
                )
            ).all()

            # Compute totals
            subtotal_cents = sum(e.total_cost_cents for e in time_entries) + sum(
                e.billable_cents for e in expenses
            )

            # Generate invoice number
            invoice_number = _generate_invoice_number(user_context.tenant_id, db)

            # B20: Compute due_at from payment_terms (design doc §G.1)
            resolved_issued_at = create_req.issued_at or datetime.now(UTC)
            resolved_due_at = _compute_due_at_from_payment_terms(
                create_req.payment_terms, resolved_issued_at, create_req.due_at
            )
            # Create invoice
            invoice = Invoice(
                tenant_id=user_context.tenant_id,
                invoice_number=invoice_number,
                job_id=create_req.job_id,
                customer_id=job.customer_id,
                site_id=job.site_id,
                status_id=draft_status.id,
                subtotal_cents=subtotal_cents,
                tax_cents=0,
                total_cents=subtotal_cents,
                balance_due_cents=subtotal_cents,
                currency="USD",
                customer_notes=create_req.customer_notes,
                terms_and_conditions=create_req.terms_and_conditions,
                issued_at=resolved_issued_at,
                due_at=resolved_due_at,
                idempotency_key=create_req.idempotency_key,
                created_by=user_context.id,
                # B20: Invoice builder fields
                payment_terms=create_req.payment_terms,
                billing_mode=create_req.billing_mode,
                progress_pct=create_req.progress_pct,
                internal_memo=create_req.internal_memo,
            )
            db.add(invoice)
            db.flush()

            # PLP-FIX-1: resolve line-type ids once per request (DB NOT NULL fix)
            labor_type_id = _resolve_qco_line_type_id(db, "labor")
            material_type_id = _resolve_qco_line_type_id(db, "material")

            # Create invoice lines from time entries
            for i, entry in enumerate(time_entries):
                line = InvoiceLine(
                    tenant_id=user_context.tenant_id,
                    invoice_id=invoice.id,
                    source_type="ad_hoc",
                    position=i,
                    qco_line_type_id=labor_type_id,
                    description=f"Labor - {entry.hours}h @ ${entry.hourly_rate_cents / 100:.2f}/hr",
                    quantity=entry.hours,
                    unit="hr",
                    unit_price_cents=entry.hourly_rate_cents,
                    subtotal_cents=entry.total_cost_cents,
                    total_cents=entry.total_cost_cents,
                    is_active=True,
                    created_by=user_context.id,
                )
                db.add(line)

            # Create invoice lines from expenses
            for i, expense in enumerate(expenses):
                line = InvoiceLine(
                    tenant_id=user_context.tenant_id,
                    invoice_id=invoice.id,
                    source_type="ad_hoc",
                    source_id=expense.id,
                    position=len(time_entries) + i,
                    qco_line_type_id=material_type_id,
                    description=expense.description,
                    quantity=1,
                    unit_price_cents=expense.billable_cents,
                    subtotal_cents=expense.billable_cents,
                    total_cents=expense.billable_cents,
                    is_active=True,
                    created_by=user_context.id,
                )
                db.add(line)
                # Back-link expense
                expense.invoice_line_id = line.id

            # PLP-FIX-1: append custom ad_hoc lines after time+expense lines
            next_position = len(time_entries) + len(expenses)
            custom_subtotal = _persist_custom_lines(
                create_req.line_items or [],
                invoice.id,
                next_position,
                db,
                user_context,
            )
            if custom_subtotal:
                invoice.subtotal_cents += custom_subtotal
                invoice.total_cents += custom_subtotal
                invoice.balance_due_cents += custom_subtotal

            db.commit()
            db.refresh(invoice)

        else:
            # ── Standalone mode (PLP-FIX-1) ───────────────────────────────────
            # Validate customer (tenant-scoped — 404, never 403)
            customer = db.exec(
                select(Customer).where(
                    Customer.id == create_req.customer_id,
                    Customer.tenant_id == user_context.tenant_id,
                )
            ).first()
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "type": "https://errors.pilotfortrades.com/not-found",
                        "title": "Customer not found",
                        "status": 404,
                        "detail": f"Customer {create_req.customer_id} does not exist in this tenant.",
                    },
                )

            # Validate site (tenant-scoped — 404, never 403)
            site = db.exec(
                select(Site).where(
                    Site.id == create_req.site_id,
                    Site.tenant_id == user_context.tenant_id,
                )
            ).first()
            if not site:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "type": "https://errors.pilotfortrades.com/not-found",
                        "title": "Site not found",
                        "status": 404,
                        "detail": f"Site {create_req.site_id} does not exist in this tenant.",
                    },
                )

            # Site must belong to the customer (422)
            if site.customer_id != create_req.customer_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "type": "https://errors.pilotfortrades.com/validation-error",
                        "title": "Site does not belong to customer",
                        "status": 422,
                        "detail": (
                            f"Site {create_req.site_id} does not belong to "
                            f"customer {create_req.customer_id}."
                        ),
                    },
                )

            # Generate invoice number
            invoice_number = _generate_invoice_number(user_context.tenant_id, db)

            # B20: Compute due_at from payment_terms (design doc §G.1)
            resolved_issued_at = create_req.issued_at or datetime.now(UTC)
            resolved_due_at = _compute_due_at_from_payment_terms(
                create_req.payment_terms, resolved_issued_at, create_req.due_at
            )
            # Create invoice with zero base totals — custom lines set the totals
            invoice = Invoice(
                tenant_id=user_context.tenant_id,
                invoice_number=invoice_number,
                quote_id=None,
                job_id=None,
                customer_id=create_req.customer_id,
                site_id=create_req.site_id,
                status_id=draft_status.id,
                subtotal_cents=0,
                tax_cents=0,
                total_cents=0,
                balance_due_cents=0,
                currency="USD",
                customer_notes=create_req.customer_notes,
                terms_and_conditions=create_req.terms_and_conditions,
                issued_at=resolved_issued_at,
                due_at=resolved_due_at,
                idempotency_key=create_req.idempotency_key,
                created_by=user_context.id,
                # B20: Invoice builder fields
                payment_terms=create_req.payment_terms,
                billing_mode=create_req.billing_mode,
                progress_pct=create_req.progress_pct,
                internal_memo=create_req.internal_memo,
            )
            db.add(invoice)
            db.flush()

            # Persist custom lines (≥1 required — validated by mode resolution)
            custom_subtotal = _persist_custom_lines(
                create_req.line_items or [],
                invoice.id,
                0,
                db,
                user_context,
            )
            invoice.subtotal_cents = custom_subtotal
            invoice.total_cents = custom_subtotal
            invoice.balance_due_cents = custom_subtotal

            db.commit()
            db.refresh(invoice)

        # Fetch invoice with status for response
        invoice = db.exec(select(Invoice).where(Invoice.id == invoice.id)).first()
        status_obj = db.exec(
            select(InvoiceStatus).where(InvoiceStatus.id == invoice.status_id)
        ).first()
        lines = db.exec(
            select(InvoiceLine)
            .where(
                InvoiceLine.invoice_id == invoice.id,
                InvoiceLine.is_active == True,
            )
            .order_by(InvoiceLine.position)
        ).all()

        invoice_dict = invoice.model_dump()
        invoice_lines = [InvoiceLineResponse.model_validate(line) for line in lines]
        response = InvoiceResponse(
            **invoice_dict,
            status_code=status_obj.code,
            lines=invoice_lines,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating invoice: {e!s}")


def _get_invoice_impl(
    invoice_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> InvoiceResponse:
    """Shared get-invoice logic for both authenticated and test endpoints."""
    invoice = db.exec(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == user_context.tenant_id,
        )
    ).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Invoice not found",
                "status": 404,
                "detail": f"Invoice {invoice_id} does not exist in this tenant.",
            },
        )

    # Fetch status
    status_obj = db.exec(
        select(InvoiceStatus).where(InvoiceStatus.id == invoice.status_id)
    ).first()

    # Fetch lines
    lines = db.exec(
        select(InvoiceLine)
        .where(
            InvoiceLine.invoice_id == invoice_id,
            InvoiceLine.is_active == True,
        )
        .order_by(InvoiceLine.position)
    ).all()

    # FIX-013-BE: Fetch payments for this invoice (tenant-scoped)
    payments = db.exec(
        select(Payment)
        .where(Payment.invoice_id == invoice_id)
        .where(Payment.tenant_id == user_context.tenant_id)
        .where(Payment.is_active == True)
        .order_by(Payment.paid_at.desc().nulls_last())
    ).all()

    response = InvoiceResponse(
        **invoice.model_dump(),
        status_code=status_obj.code,
        lines=[InvoiceLineResponse.model_validate(line) for line in lines],
        payments=[PaymentSummaryResponse.model_validate(p) for p in payments],
    )
    return response


def _record_payment_impl(
    invoice_id: UUID,
    pay_req: PaymentRecordRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PaymentResponse:
    """Shared record-payment logic for both authenticated and test endpoints."""
    try:
        invoice = db.exec(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == user_context.tenant_id,
            )
        ).first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found",
            )

        if pay_req.amount_cents <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="amount_cents must be greater than zero",
            )

        # Require comment for partial payment
        if pay_req.amount_cents < invoice.balance_due_cents and not pay_req.comment:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Payment comment required for partial payment",
            )

        # Compute amount variance
        amount_variance_cents = pay_req.amount_cents - invoice.balance_due_cents

        # Create payment
        payment = Payment(
            tenant_id=user_context.tenant_id,
            invoice_id=invoice.id,
            amount_cents=pay_req.amount_cents,
            payment_method_id=pay_req.payment_method_id,
            status_id=pay_req.payment_status_id,
            paid_via=pay_req.paid_via,
            psp_payment_id=pay_req.reference,
            idempotency_key=pay_req.idempotency_key,
            customer_payment_comment=pay_req.comment,
            amount_variance_cents=amount_variance_cents
            if amount_variance_cents != 0
            else None,
            paid_at=pay_req.paid_at or datetime.now(UTC),
            created_by=user_context.id,
        )
        db.add(payment)

        # Update invoice balance
        invoice.balance_due_cents = max(
            0, invoice.balance_due_cents - pay_req.amount_cents
        )

        # Set status to paid if balance is zero
        if invoice.balance_due_cents == 0:
            paid_status = db.exec(
                select(InvoiceStatus).where(
                    InvoiceStatus.code == "paid",
                    InvoiceStatus.tenant_id == user_context.tenant_id,
                )
            ).first()
            if paid_status:
                invoice.status_id = paid_status.id

        db.add(invoice)
        db.commit()
        db.refresh(payment)

        return PaymentResponse(
            **payment.model_dump(),
            balance_due_cents=invoice.balance_due_cents,
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error recording payment: {e!s}")


# ==================== TEST ENDPOINTS (register FIRST) ====================


@router.post(
    "/{invoice_id}/send/test",
    response_model=InvoicePublicLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_invoice_test(
    invoice_id: UUID,
    send_req: InvoiceSendRequest,
    db: Session = Depends(get_db),
):
    """Generate an invoice public payment link (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _send_invoice_impl(invoice_id, send_req, db, test_context)


@router.get("/test", response_model=InvoiceListResponse)
def list_invoices_test(
    db: Session = Depends(get_db),
    status: str | None = Query(None),
    due_before: datetime | None = Query(None),
    due_after: datetime | None = Query(None),
    customer_search: str | None = Query(None),
    issued_from: datetime | None = Query(None),
    issued_to: datetime | None = Query(None),
    customer_id: UUID | None = Query(
        None, description="Filter invoices by exact customer UUID"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List invoices (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _list_invoices_impl(
        db,
        test_context,
        invoice_status=status,
        due_before=due_before,
        due_after=due_after,
        customer_search=customer_search,
        issued_from=issued_from,
        issued_to=issued_to,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/test", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED
)
def create_invoice_test(
    create_req: InvoiceCreate,
    db: Session = Depends(get_db),
):
    """Create a new invoice (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _create_invoice_impl(create_req, db, test_context)


@router.get("/{invoice_id}/test", response_model=InvoiceResponse)
def get_invoice_test(
    invoice_id: UUID,
    db: Session = Depends(get_db),
):
    """Get full invoice detail (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _get_invoice_impl(invoice_id, db, test_context)


@router.post(
    "/{invoice_id}/record-payment/test",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_payment_test(
    invoice_id: UUID,
    pay_req: PaymentRecordRequest,
    db: Session = Depends(get_db),
):
    """Record a manual payment against an invoice (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _record_payment_impl(invoice_id, pay_req, db, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post(
    "/{invoice_id}/send",
    response_model=InvoicePublicLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_invoice(
    invoice_id: UUID,
    send_req: InvoiceSendRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.update")),
):
    """Generate an invoice public payment link (requires invoices.update permission)."""
    return _send_invoice_impl(invoice_id, send_req, db, current_user)


# ==================== AUTHENTICATED INVOICE CRUD (FIND-076) ====================


@router.get(
    "/",
    response_model=InvoiceListResponse,
)
def list_invoices(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.view")),
    status: str | None = Query(None),
    due_before: datetime | None = Query(None),
    due_after: datetime | None = Query(None),
    overdue: bool = Query(
        default=False,
        description="SD-06B: Filter to only overdue invoices (due_at < now, status not in paid/void/writeoff)",
    ),
    customer_search: str | None = Query(None),
    issued_from: datetime | None = Query(None),
    issued_to: datetime | None = Query(None),
    customer_id: UUID | None = Query(
        None, description="Filter invoices by exact customer UUID"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Tenant-scoped invoice list with optional status, due_date, customer, and issued_date filters."""
    return _list_invoices_impl(
        db,
        current_user,
        invoice_status=status,
        due_before=due_before,
        due_after=due_after,
        overdue=overdue,
        customer_search=customer_search,
        issued_from=issued_from,
        issued_to=issued_to,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice(
    create_req: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.create")),
):
    """Create a new invoice from a quote or job."""
    return _create_invoice_impl(create_req, db, current_user)


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
)
def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.view")),
):
    """Get full invoice detail including line items."""
    return _get_invoice_impl(invoice_id, db, current_user)


@router.post(
    "/{invoice_id}/record-payment",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_payment(
    invoice_id: UUID,
    pay_req: PaymentRecordRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.create")),
):
    """Record a manual payment against an invoice."""
    return _record_payment_impl(invoice_id, pay_req, db, current_user)


# ==================== CE-1: INVOICE SIGN-OFF (D.2 + D.3) ====================

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_MAX_SIGNATURE_BYTES = 2 * 1024 * 1024  # 2 MB


def _create_signoff_impl(
    invoice_id: UUID,
    signoff_req: InvoiceSignoffCreateRequest,
    idempotency_key: str | None,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> InvoiceSignoffResponse:
    """CE-1 §D.2 — Capture a customer signature on an invoice.

    Single DB transaction; S3 put before commit. Replay-safe via
    uq_invoice_signoff_tenant_idempotency. Re-capture supersedes prior row.
    """
    # 1. Idempotency replay check (natural-key DB backstop)
    if idempotency_key:
        existing = db.exec(
            select(InvoiceSignoff)
            .where(InvoiceSignoff.tenant_id == user_context.tenant_id)
            .where(InvoiceSignoff.idempotency_key == idempotency_key)
        ).first()
        if existing:
            return InvoiceSignoffResponse(
                signoff_id=existing.id,
                invoice_id=existing.invoice_id,
                signed_by_name=existing.signed_by_name,
                signed_at=existing.signed_at,
                client_capture_at=existing.client_capture_at,
                captured_by_user_id=existing.captured_by_user_id,
                signature_url=generate_presigned_get_url(existing.signature_object_key),
            )

    # 2. Tenant-scoped invoice fetch → 404
    invoice = db.exec(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .where(Invoice.tenant_id == user_context.tenant_id)
    ).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Invoice not found",
                "status": 404,
                "detail": f"Invoice {invoice_id} does not exist in this tenant.",
            },
        )

    # 3. Status guard: must be issued/partial
    inv_status = db.exec(
        select(InvoiceStatus).where(InvoiceStatus.id == invoice.status_id)
    ).first()
    current_code = inv_status.code if inv_status else None
    if current_code not in ("issued", "partial"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/validation",
                "title": "Invoice not signable",
                "status": 422,
                "detail": (
                    f"Invoice status is '{current_code}'. "
                    "Only 'issued' or 'partial' invoices can be signed."
                ),
            },
        )

    # 4. Decode + validate PNG
    try:
        png_bytes = base64.b64decode(signoff_req.signature_png_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/validation",
                "title": "Invalid base64",
                "status": 422,
                "detail": f"signature_png_base64 is not valid base64: {exc}",
            },
        ) from exc

    if not png_bytes.startswith(_PNG_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/validation",
                "title": "Not a PNG",
                "status": 422,
                "detail": "Decoded bytes do not start with PNG magic bytes.",
            },
        )

    if len(png_bytes) > _MAX_SIGNATURE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/validation",
                "title": "Signature too large",
                "status": 422,
                "detail": (
                    f"Decoded signature is {len(png_bytes)} bytes; "
                    f"maximum is {_MAX_SIGNATURE_BYTES} bytes (2 MB)."
                ),
            },
        )

    # 5. Upload to S3 (before commit — on failure: 502, no row written)
    signoff_id = uuid.uuid4()
    object_key = build_signature_object_key(
        str(user_context.tenant_id), str(invoice_id), str(signoff_id)
    )
    try:
        put_signature_object(object_key, png_bytes)
    except ClientError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "type": "https://errors.pilotfortrades.com/storage-unavailable",
                "title": "Signature storage unavailable",
                "status": 502,
                "detail": "Unable to upload signature to S3. Please retry.",
            },
        ) from None

    # 6. Supersede prior active signoff
    db.exec(
        select(InvoiceSignoff)
        .where(InvoiceSignoff.invoice_id == invoice_id)
        .where(InvoiceSignoff.tenant_id == user_context.tenant_id)
        .where(InvoiceSignoff.superseded_at.is_(None))
    ).all()  # load for update pattern
    from sqlalchemy import text as sa_text

    db.execute(
        sa_text(
            "UPDATE invoice_signoff SET superseded_at = now() "
            "WHERE invoice_id = :iid AND tenant_id = :tid "
            "AND superseded_at IS NULL"
        ).bindparams(iid=str(invoice_id), tid=str(user_context.tenant_id))
    )

    # 7. Insert new signoff row
    signoff = InvoiceSignoff(
        id=signoff_id,
        tenant_id=user_context.tenant_id,
        invoice_id=invoice_id,
        signed_by_name=signoff_req.signed_by_name,
        signature_object_key=object_key,
        terms_acknowledged=True,
        signed_at=datetime.now(UTC),
        client_capture_at=signoff_req.client_capture_at,
        captured_by_user_id=user_context.id,
        idempotency_key=idempotency_key,
        created_by=user_context.id,
    )
    db.add(signoff)

    try:
        db.commit()
    except Exception:
        db.rollback()
        # Check if it's a unique-active race or idempotency conflict
        existing = (
            db.exec(
                select(InvoiceSignoff)
                .where(InvoiceSignoff.tenant_id == user_context.tenant_id)
                .where(InvoiceSignoff.idempotency_key == idempotency_key)
            ).first()
            if idempotency_key
            else None
        )
        if existing:
            return InvoiceSignoffResponse(
                signoff_id=existing.id,
                invoice_id=existing.invoice_id,
                signed_by_name=existing.signed_by_name,
                signed_at=existing.signed_at,
                client_capture_at=existing.client_capture_at,
                captured_by_user_id=existing.captured_by_user_id,
                signature_url=generate_presigned_get_url(existing.signature_object_key),
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://errors.pilotfortrades.com/conflict",
                "title": "Sign-off conflict",
                "status": 409,
                "detail": (
                    "Another sign-off was captured concurrently. "
                    "Please refresh the context and retry."
                ),
            },
        ) from None

    db.refresh(signoff)

    return InvoiceSignoffResponse(
        signoff_id=signoff.id,
        invoice_id=signoff.invoice_id,
        signed_by_name=signoff.signed_by_name,
        signed_at=signoff.signed_at,
        client_capture_at=signoff.client_capture_at,
        captured_by_user_id=signoff.captured_by_user_id,
        signature_url=generate_presigned_get_url(signoff.signature_object_key),
    )


def _get_signoff_impl(
    invoice_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> InvoiceSignoffDetailResponse:
    """CE-1 §D.3 — Get the latest active signoff for an invoice (web display)."""
    # Tenant-scoped invoice fetch → 404
    invoice = db.exec(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .where(Invoice.tenant_id == user_context.tenant_id)
    ).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Invoice not found",
                "status": 404,
                "detail": f"Invoice {invoice_id} does not exist in this tenant.",
            },
        )

    active = db.exec(
        select(InvoiceSignoff)
        .where(InvoiceSignoff.invoice_id == invoice_id)
        .where(InvoiceSignoff.tenant_id == user_context.tenant_id)
        .where(InvoiceSignoff.superseded_at.is_(None))
        .order_by(InvoiceSignoff.signed_at.desc())
    ).first()

    superseded_count = db.exec(
        select(func.count(InvoiceSignoff.id))
        .where(InvoiceSignoff.invoice_id == invoice_id)
        .where(InvoiceSignoff.tenant_id == user_context.tenant_id)
        .where(InvoiceSignoff.superseded_at.is_not(None))
    ).one()

    if not active:
        return InvoiceSignoffDetailResponse(
            signoff=None,
            superseded_count=superseded_count,
        )

    return InvoiceSignoffDetailResponse(
        signoff=InvoiceSignoffResponse(
            signoff_id=active.id,
            invoice_id=active.invoice_id,
            signed_by_name=active.signed_by_name,
            signed_at=active.signed_at,
            client_capture_at=active.client_capture_at,
            captured_by_user_id=active.captured_by_user_id,
            signature_url=generate_presigned_get_url(active.signature_object_key),
        ),
        superseded_count=superseded_count,
    )


# --- D.2/D.3 TEST endpoints (register BEFORE authenticated) ---


@router.post(
    "/{invoice_id}/signoff/test",
    response_model=InvoiceSignoffResponse,
)
def create_signoff_test(
    invoice_id: UUID,
    signoff_req: InvoiceSignoffCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """CE-1 §D.2 — Capture sign-off (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    set_audit_context_sync(db, user_id=test_context.id)
    return _create_signoff_impl(
        invoice_id, signoff_req, idempotency_key, db, test_context
    )


@router.get(
    "/{invoice_id}/signoff/test",
    response_model=InvoiceSignoffDetailResponse,
)
def get_signoff_test(
    invoice_id: UUID,
    db: Session = Depends(get_db),
):
    """CE-1 §D.3 — Get sign-off (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _get_signoff_impl(invoice_id, db, test_context)


# --- D.2/D.3 AUTHENTICATED endpoints ---


@router.post(
    "/{invoice_id}/signoff",
    response_model=InvoiceSignoffResponse,
)
def create_signoff(
    invoice_id: UUID,
    signoff_req: InvoiceSignoffCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.update")),
):
    """CE-1 §D.2 — Capture sign-off. RBAC: jobs.update (design §G-R3).

    Requires Idempotency-Key header (offline-queued by mobile app).
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/missing-header",
                "title": "Missing Idempotency-Key",
                "status": 400,
                "detail": "Idempotency-Key header is required for sign-off capture.",
            },
        )
    set_audit_context_sync(db, user_id=current_user.id)
    return _create_signoff_impl(
        invoice_id, signoff_req, idempotency_key, db, current_user
    )


@router.get(
    "/{invoice_id}/signoff",
    response_model=InvoiceSignoffDetailResponse,
)
def get_signoff(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.view")),
):
    """CE-1 §D.3 — Get sign-off. RBAC: invoices.view (web display)."""
    return _get_signoff_impl(invoice_id, db, current_user)


# ==================== CE-1: VARIANCE RESOLUTION (D.4) ====================


def _resolve_variance_impl(
    payment_id: UUID,
    resolve_req: ResolveVarianceRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PaymentResponse:
    """CE-1 §D.4 — Record overpayment variance resolution (record-keeping only).

    Never creates payment rows, calls Stripe, or enqueues QB work (§G-R6).
    """
    # Tenant-scoped payment fetch → 404
    payment = db.exec(
        select(Payment)
        .where(Payment.id == payment_id)
        .where(Payment.tenant_id == user_context.tenant_id)
    ).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Payment not found",
                "status": 404,
                "detail": f"Payment {payment_id} does not exist in this tenant.",
            },
        )

    # Guard 1: amount_cents > 0 (refund rows are negative per SD-2)
    if payment.amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/validation",
                "title": "Not an overpayment",
                "status": 422,
                "detail": "Refund (negative-amount) payments cannot have variance resolution.",
            },
        )

    # Guard 2: amount_variance_cents > 0
    if payment.amount_variance_cents is None or payment.amount_variance_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/validation",
                "title": "No overpayment to resolve",
                "status": 422,
                "detail": "This payment has no positive amount variance to resolve.",
            },
        )

    # Guard 3: not already resolved → 409
    if payment.variance_resolved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://errors.pilotfortrades.com/conflict",
                "title": "Variance already resolved",
                "status": 409,
                "detail": (
                    f"This payment variance was already resolved as "
                    f"'{payment.variance_resolution}'. "
                    "Refresh the invoice to see the current state."
                ),
            },
        )

    # Set resolution fields
    payment.variance_resolution = resolve_req.resolution
    payment.variance_resolution_note = resolve_req.note
    payment.variance_resolved_at = datetime.now(UTC)
    payment.variance_resolved_by_user_id = user_context.id
    payment.updated_by = user_context.id

    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Fetch invoice for balance_due_cents
    invoice = db.exec(
        select(Invoice)
        .where(Invoice.id == payment.invoice_id)
        .where(Invoice.tenant_id == user_context.tenant_id)
    ).first()

    return PaymentResponse(
        id=payment.id,
        invoice_id=payment.invoice_id,
        tenant_id=payment.tenant_id,
        amount_cents=payment.amount_cents,
        paid_via=payment.paid_via or "",
        balance_due_cents=invoice.balance_due_cents if invoice else 0,
        amount_variance_cents=payment.amount_variance_cents,
        status_id=payment.status_id,
        paid_at=payment.paid_at,
        idempotency_key=payment.idempotency_key,
        created_at=payment.created_at,
        variance_resolution=payment.variance_resolution,
        variance_resolution_note=payment.variance_resolution_note,
        variance_resolved_at=payment.variance_resolved_at,
        variance_resolved_by_user_id=payment.variance_resolved_by_user_id,
    )


# --- D.4 TEST endpoint ---


@router.post(
    "/{payment_id}/resolve-variance/test",
    response_model=PaymentResponse,
)
def resolve_variance_test(
    payment_id: UUID,
    resolve_req: ResolveVarianceRequest,
    db: Session = Depends(get_db),
):
    """CE-1 §D.4 — Resolve variance (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    set_audit_context_sync(db, user_id=test_context.id)
    return _resolve_variance_impl(payment_id, resolve_req, db, test_context)


# --- D.4 AUTHENTICATED endpoint ---


@router.post(
    "/{payment_id}/resolve-variance",
    response_model=PaymentResponse,
)
def resolve_variance(
    payment_id: UUID,
    resolve_req: ResolveVarianceRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("invoices.update")),
):
    """CE-1 §D.4 — Resolve overpayment variance. RBAC: invoices.update.

    Record-keeping only — no Stripe refund execution, no QB credit memo (§G-R6).
    """
    set_audit_context_sync(db, user_id=current_user.id)
    return _resolve_variance_impl(payment_id, resolve_req, db, current_user)
