import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session, func, select

from api.schemas.quotes import (
    PaginatedQuoteListResponse,
    QuoteAcceptanceCreate,
    QuoteAcceptanceResponse,
    QuoteAnalyticsEvent,
    QuoteAnalyticsResponse,
    QuoteApplyDiscountRequest,
    QuoteApplyDiscountResponse,
    QuoteApprovalCommentResponse,
    QuoteApproveRequest,
    QuoteApproveResponse,
    QuoteConvertResponse,
    QuoteCreate,
    QuoteDetailResponse,
    QuoteKickbackRequest,
    QuoteKickbackResponse,
    QuoteLineCreate,
    QuoteLineResponse,
    QuoteListItem,
    QuotePendingEditCreate,
    QuotePendingEditResponse,
    QuotePendingEditUpdate,
    QuotePublicLinkCreate,
    QuotePublicLinkResponse,
    QuoteRejectRequest,
    QuoteRejectResponse,
    QuoteResponse,
    QuoteRevokeLinkResponse,
    QuoteSaveAsTemplateRequest,
    QuoteSaveAsTemplateResponse,
    QuoteSubmitForApprovalResponse,
    QuoteUpdate,
    QuoteVersionCreate,
    QuoteVersionResponse,
)
from app.models.catalog import PricingCache, SupplierItem
from app.models.crm import Contact, Customer
from app.models.fulfillment import Job, JobStatus
from app.models.quoting import (
    PricebookItemVersion,
    QcoLineType,
    QplContactActionType,
    Quote,
    QuoteAcceptance,
    QuoteApprovalComment,
    QuoteLine,
    QuoteLineTaxComponent,
    QuoteLinkStatus,
    QuotePendingEdit,
    QuotePublicLink,
    QuotePublicLinkContactAction,
    QuoteStatus,
    QuoteTemplate,
    QuoteTemplateLine,
    QuoteVersion,
)
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.tax_calculation import (
    calculate_combined_tax_rate,
    calculate_tax_components,
    get_jurisdiction_code_from_rates,
    get_tax_rates_for_quote_line,
)
from core.test_context import TestUserContext, get_test_context
from services.public_link_signer import (
    TokenExpiredError,
    TokenInvalidError,
    generate_signed_token,
    verify_signed_token,
)
from services.quote_service import (
    assert_quote_version_not_stale,
    get_quote_detail,
    get_quote_status_code,
    transition_quote_status,
)

router = APIRouter()


# ==================== SHARED BUSINESS LOGIC ====================


def _generate_quote_number(tenant_id: UUID, db: Session) -> str:
    """
    Generate a sequential quote number for the tenant: QUO-000001, QUO-000002, ...
    Uses MAX(numeric suffix) + 1 scoped to tenant_id.
    Retries up to 5 times on unique constraint violation (race condition guard).
    Format: QUO-000001 (sequential, tenant-scoped, zero-padded 6 digits)
    """
    from sqlalchemy import text as sa_text

    for _ in range(5):
        result = db.exec(
            sa_text(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(quote_number FROM 5) AS INTEGER)), 0) + 1 "
                "FROM quote WHERE tenant_id = :tid"
            ).bindparams(tid=str(tenant_id))
        ).first()
        next_num = result[0] if result else 1
        quote_number = f"QUO-{str(next_num).zfill(6)}"
        existing = db.exec(
            select(Quote).where(
                Quote.tenant_id == tenant_id,
                Quote.quote_number == quote_number,
            )
        ).first()
        if not existing:
            return quote_number
    raise ValueError("Unable to generate unique quote_number after 5 attempts")


def _create_quote_impl(
    quote_in: QuoteCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Quote:
    """
    Shared quote creation logic used by both authenticated and test endpoints.

    Args:
        quote_in: Quote data to create
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        Created Quote instance

    Raises:
        HTTPException: If no default quote status found

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    # Find default status
    statement = select(QuoteStatus).where(
        QuoteStatus.tenant_id == user_context.tenant_id, QuoteStatus.is_default == True
    )
    status_obj = db.exec(statement).first()

    if not status_obj:
        # Fallback to a system default if tenant specific doesn't exist
        statement = select(QuoteStatus).where(
            QuoteStatus.tenant_id == None, QuoteStatus.is_default == True
        )
        status_obj = db.exec(statement).first()

    if not status_obj:
        raise HTTPException(status_code=400, detail="No default quote status found")

    quote = Quote(
        tenant_id=user_context.tenant_id,
        customer_id=quote_in.customer_id,
        site_id=quote_in.site_id,
        status_id=status_obj.id,
        currency=quote_in.currency,
        idempotency_key=quote_in.idempotency_key,
        expires_at=quote_in.expires_at,  # FIND-096: Quote expiration timestamp
        quote_number=_generate_quote_number(user_context.tenant_id, db),
        title=quote_in.title if hasattr(quote_in, "title") else None,
        # B20: card-on-file override (None = inherit from customer.card_required)
        card_required=getattr(quote_in, "card_required", None),
    )
    db.add(quote)
    db.flush()  # quote.id available; lines query returns []
    _insert_quote_version(quote, db)  # v1, is_active=True, SAME transaction
    db.commit()
    db.refresh(quote)
    return quote


def _list_quotes_impl(
    skip: int,
    limit: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    status_filter: str | None = None,
    customer_search: str | None = None,
    title_search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    offset: int = 0,
    customer_id: "UUID | None" = None,
) -> PaginatedQuoteListResponse:
    """
    Shared quote listing logic used by both authenticated and test endpoints.

    UI-FIX-1C: Returns PaginatedQuoteListResponse with total count.
    BETA-B3 companion tasks:
    - BE-2: Optional ?status= filter param (case-insensitive match on QuoteStatus.code)
    - BE-3: status_code denormalized from QuoteStatus join
    - BE-4: customer_name denormalized from Customer join

    Args:
        skip: Deprecated — use offset instead (backward compat alias)
        limit: Maximum number of records to return
        db: Database session
        user_context: Either authenticated User or TestUserContext
        status_filter: Optional status code string to filter by (e.g. "draft", "sent")
        customer_search: Optional case-insensitive search on customer display_name
        title_search: Optional case-insensitive search on quote title
        date_from: Optional filter — quotes created on or after this datetime
        date_to: Optional filter — quotes created on or before this datetime
        offset: Canonical pagination offset (supersedes skip when > 0)

    Returns:
        PaginatedQuoteListResponse with items, total, limit, offset
    """
    effective_offset = offset if offset > 0 else skip

    statement = (
        select(Quote, QuoteStatus, Customer)
        .join(QuoteStatus, Quote.status_id == QuoteStatus.id)
        .join(Customer, Quote.customer_id == Customer.id)
        .where(Quote.tenant_id == user_context.tenant_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    )

    # BE-2: optional status filter
    if status_filter:
        statement = statement.where(
            func.lower(QuoteStatus.code) == status_filter.lower()
        )

    # UI-FIX-1C: customer name search
    if customer_search:
        statement = statement.where(Customer.display_name.ilike(f"%{customer_search}%"))

    # UI-FIX-2D: exact customer UUID filter
    if customer_id:
        statement = statement.where(Quote.customer_id == customer_id)

    # UI-FIX-1C: title search (nullable column — ilike handles NULL gracefully)
    if title_search:
        statement = statement.where(Quote.title.ilike(f"%{title_search}%"))

    # UI-FIX-1C: date range filters on created_at
    if date_from:
        statement = statement.where(Quote.created_at >= date_from)
    if date_to:
        statement = statement.where(Quote.created_at <= date_to)

    # Count query with same filters
    count_stmt = (
        select(func.count(Quote.id))
        .join(QuoteStatus, Quote.status_id == QuoteStatus.id)
        .join(Customer, Quote.customer_id == Customer.id)
        .where(Quote.tenant_id == user_context.tenant_id)
        .where(Customer.tenant_id == user_context.tenant_id)
    )
    if status_filter:
        count_stmt = count_stmt.where(
            func.lower(QuoteStatus.code) == status_filter.lower()
        )
    if customer_search:
        count_stmt = count_stmt.where(
            Customer.display_name.ilike(f"%{customer_search}%")
        )
    if customer_id:
        count_stmt = count_stmt.where(Quote.customer_id == customer_id)
    if title_search:
        count_stmt = count_stmt.where(Quote.title.ilike(f"%{title_search}%"))
    if date_from:
        count_stmt = count_stmt.where(Quote.created_at >= date_from)
    if date_to:
        count_stmt = count_stmt.where(Quote.created_at <= date_to)

    total = db.exec(count_stmt).one()

    statement = statement.offset(effective_offset).limit(limit)
    rows = db.exec(statement).all()

    items = []
    for quote, quote_status, customer in rows:
        items.append(
            QuoteListItem(
                id=quote.id,
                tenant_id=quote.tenant_id,
                customer_id=quote.customer_id,
                customer_name=customer.display_name,  # BE-4
                site_id=quote.site_id,
                status_id=quote.status_id,
                status_code=quote_status.code,  # BE-3
                subtotal_cents=quote.subtotal_cents,
                tax_cents=quote.tax_cents,
                total_cents=quote.total_cents,
                quote_number=quote.quote_number
                if hasattr(quote, "quote_number")
                else None,
                title=quote.title if hasattr(quote, "title") else None,
            )
        )

    return PaginatedQuoteListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=effective_offset,
    )


def _get_quote_impl(
    quote_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteResponse:
    """
    Shared quote retrieval logic used by both authenticated and test endpoints.

    Args:
        quote_id: ID of the quote to retrieve
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        QuoteResponse with status_code populated from quote_status JOIN

    Raises:
        HTTPException: If quote not found or doesn't belong to tenant

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    quote = db.get(Quote, quote_id)
    if not quote or quote.tenant_id != user_context.tenant_id:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Resolve status_code from quote_status table (required by QuoteStatusPill on the frontend)
    status_row = db.exec(
        select(QuoteStatus).where(QuoteStatus.id == quote.status_id)
    ).first()
    status_code = status_row.code if status_row else None

    response = QuoteResponse.model_validate(quote)
    response.status_code = status_code
    return response


def _update_quote_impl(
    quote_id: UUID,
    quote_update: QuoteUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> Quote:
    """
    Shared quote update logic used by both authenticated and test endpoints.

    Args:
        quote_id: ID of the quote to update
        quote_update: Fields to update
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        Updated Quote instance

    Raises:
        HTTPException: If quote not found or doesn't belong to tenant

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    quote = db.get(Quote, quote_id)
    if not quote or quote.tenant_id != user_context.tenant_id:
        raise HTTPException(status_code=404, detail="Quote not found")

    update_data = quote_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(quote, key, value)

    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


def _create_quote_line_impl(
    quote_id: UUID,
    line_in: QuoteLineCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteLine:
    """
    Shared quote line creation logic used by both authenticated and test endpoints.

    Args:
        quote_id: ID of the quote to add line to
        line_in: Line item data to create
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        Created QuoteLine instance

    Raises:
        HTTPException: If quote not found or doesn't belong to tenant

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    quote = db.get(Quote, quote_id)
    if not quote or quote.tenant_id != user_context.tenant_id:
        raise HTTPException(status_code=404, detail="Quote not found")

    # PLP-FIX-2: validate the line type BEFORE any insert — a bad UUID previously
    # surfaced as a raw 500 ForeignKeyViolation at db.flush() (Issue 5 from the author's test run on the pre-release AWS environment).
    # Platform rows (tenant_id IS NULL) are valid for every tenant.
    if line_in.qco_line_type_id is not None:
        line_type = db.exec(
            select(QcoLineType).where(
                QcoLineType.id == line_in.qco_line_type_id,
                (QcoLineType.tenant_id == user_context.tenant_id)
                | (QcoLineType.tenant_id == None),
                QcoLineType.is_active == True,
            )
        ).first()
        if not line_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://errors.pilotfortrades.com/not-found",
                    "title": "Line type not found",
                    "status": 404,
                    "detail": (
                        f"qco_line_type_id {line_in.qco_line_type_id} "
                        "does not exist or is not active."
                    ),
                },
            )

    unit_price_cents = line_in.unit_price_cents or 0

    if line_in.pricebook_item_id:
        # Fetch current price from PricebookItemVersion
        statement = (
            select(PricebookItemVersion)
            .where(
                PricebookItemVersion.tenant_id == user_context.tenant_id,
                PricebookItemVersion.pricebook_item_id == line_in.pricebook_item_id,
            )
            .order_by(PricebookItemVersion.id.desc())
        )
        pb_version = db.exec(statement).first()
        if pb_version:
            unit_price_cents = pb_version.default_unit_price_cents

    elif line_in.supplier_item_id:
        # SECURITY FIX (1-A-1): Scope SupplierItem lookup to current tenant.
        # Enforce `tenant_id IS NULL OR tenant_id = current_tenant.id` to prevent
        # cross-tenant IDOR — Tenant A cannot read Tenant B's private catalog prices.
        # Global/system-wide items (tenant_id IS NULL) are intentionally accessible
        # to all tenants as shared catalog entries.
        sup_item = db.exec(
            select(SupplierItem).where(
                SupplierItem.id == line_in.supplier_item_id,
                (SupplierItem.tenant_id == user_context.tenant_id)
                | (SupplierItem.tenant_id == None),
            )
        ).first()
        if sup_item:
            # SECURITY FIX (1-A-2): Scope PricingCache reads to the current tenant.
            # Prefer a tenant-specific negotiated price when one exists, then fall
            # back to the global (tenant_id IS NULL) shared price.
            # This prevents cross-tenant cache reads leaking material prices.
            cache_entry = db.exec(
                select(PricingCache)
                .where(
                    PricingCache.supplier_id == sup_item.supplier_id,
                    PricingCache.sku == sup_item.sku,
                    (PricingCache.tenant_id == user_context.tenant_id)
                    | (PricingCache.tenant_id == None),
                )
                # Prefer tenant-specific price over global price
                .order_by(PricingCache.tenant_id.nullslast())
            ).first()
            if cache_entry:
                unit_price_cents = cache_entry.price_cents

    subtotal_cents = int(line_in.quantity * unit_price_cents)

    # FIND-107: If customer has a taxability override, use it over line-level default
    _customer_taxability = None
    if quote.customer_id:
        from app.models.crm import Customer as _Customer

        _cust = db.exec(
            select(_Customer).where(
                _Customer.id == quote.customer_id,
                _Customer.tenant_id == user_context.tenant_id,
            )
        ).first()
        if _cust and _cust.taxability_code:
            _customer_taxability = _cust.taxability_code

    taxability_code = _customer_taxability or line_in.taxability_code or "taxable"
    as_of_timestamp = datetime.now(UTC)

    # Look up applicable tax rates
    tax_rates = get_tax_rates_for_quote_line(
        db=db,
        site_id=quote.site_id,
        taxability_code=taxability_code,
        as_of_timestamp=as_of_timestamp,
    )

    # Calculate tax components (round-up rounding)
    tax_amount_cents, tax_components = calculate_tax_components(
        subtotal_cents=subtotal_cents,
        tax_rates=tax_rates,
        quote_line_id=None,  # Will set after flush
        tenant_id=quote.tenant_id,
    )

    # Calculate totals
    total_cents = subtotal_cents + tax_amount_cents

    # Create quote line with tax information (Snapshot Principle)
    quote_line = QuoteLine(
        tenant_id=quote.tenant_id,
        quote_id=quote_id,
        position=line_in.position,
        qco_line_type_id=line_in.qco_line_type_id,
        pricebook_item_id=line_in.pricebook_item_id,
        supplier_id=line_in.supplier_id,
        supplier_item_id=line_in.supplier_item_id,
        taxability_code=taxability_code,
        description=line_in.description,
        quantity=line_in.quantity,
        unit=line_in.unit,
        unit_price_cents=unit_price_cents,
        subtotal_cents=subtotal_cents,
        tax_rate_pct=calculate_combined_tax_rate(tax_rates),
        tax_basis_cents=subtotal_cents,
        tax_amount_cents=tax_amount_cents,
        tax_jurisdiction_code=get_jurisdiction_code_from_rates(tax_rates),
        tax_as_of=as_of_timestamp,
        tax_source="internal_lookup",
        total_cents=total_cents,
    )

    # Save quote line first to get ID
    db.add(quote_line)
    db.flush()  # Get ID without committing transaction

    # Now save tax components with the quote_line_id
    for component in tax_components:
        component.quote_line_id = quote_line.id
        db.add(component)

    # Commit transaction (trigger will update quote header totals)
    db.commit()
    db.refresh(quote_line)
    return quote_line


def _insert_quote_version(
    quote: Quote,
    db: Session,
    presentation_style: str = "clean",
) -> QuoteVersion:
    """
    Insert the next QuoteVersion for an already tenant-verified Quote.

    Builds the snapshot from the (flushed) quote ORM object + its current
    quote_line rows (taxes nested per line), computes version_no = max+1,
    db.add() + db.flush() ONLY — never commits. Caller owns the transaction.
    """
    # Fetch lines
    statement = select(QuoteLine).where(QuoteLine.quote_id == quote.id)
    lines = db.exec(statement).all()

    # Build snapshot JSON
    snapshot = {
        "quote": quote.model_dump(mode="json"),
        "lines": [],
    }

    for line in lines:
        line_dict = line.model_dump(mode="json")
        # Fetch taxes for line
        tax_stmt = select(QuoteLineTaxComponent).where(
            QuoteLineTaxComponent.quote_line_id == line.id
        )
        taxes = db.exec(tax_stmt).all()
        line_dict["taxes"] = [t.model_dump(mode="json") for t in taxes]
        snapshot["lines"].append(line_dict)

    # Determine next version number
    version_stmt = (
        select(QuoteVersion.version_no)
        .where(QuoteVersion.quote_id == quote.id)
        .order_by(QuoteVersion.version_no.desc())
    )
    last_version = db.exec(version_stmt).first()
    next_version_no = (last_version or 0) + 1

    quote_version = QuoteVersion(
        tenant_id=quote.tenant_id,
        quote_id=quote.id,
        version_no=next_version_no,
        snapshot=snapshot,
        # FIND-095: persist caller-specified presentation style
        presentation_style=presentation_style,
    )
    db.add(quote_version)
    db.flush()
    return quote_version


def _create_quote_version_impl(
    quote_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    create_in: QuoteVersionCreate | None = None,
) -> QuoteVersion:
    """
    Shared quote version creation logic used by both authenticated and test endpoints.

    Args:
        quote_id: ID of the quote to create version for
        db: Database session
        user_context: Either authenticated User or TestUserContext
        create_in: Optional request body; defaults used if not provided

    Returns:
        Created QuoteVersion instance with snapshot

    Raises:
        HTTPException: If quote not found or doesn't belong to tenant

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    if create_in is None:
        create_in = QuoteVersionCreate()

    quote = db.get(Quote, quote_id)
    if not quote or quote.tenant_id != user_context.tenant_id:
        raise HTTPException(status_code=404, detail="Quote not found")

    version = _insert_quote_version(quote, db, create_in.presentation_style)
    db.commit()
    db.refresh(version)
    return version


def _create_public_link_impl(
    quote_id: UUID,
    version_id: UUID,
    link_in: QuotePublicLinkCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuotePublicLinkResponse:
    """
    Shared public link creation logic used by both authenticated and test endpoints.

    Args:
        quote_id: ID of the quote
        version_id: ID of the quote version
        link_in: Public link data to create
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        QuotePublicLinkResponse with generated URL and token

    Raises:
        HTTPException: If quote or version not found or doesn't belong to tenant

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    quote = db.get(Quote, quote_id)
    if not quote or quote.tenant_id != user_context.tenant_id:
        raise HTTPException(status_code=404, detail="Quote not found")

    version = db.exec(
        select(QuoteVersion).where(
            QuoteVersion.id == version_id,
            QuoteVersion.tenant_id == user_context.tenant_id,
        )
    ).first()
    if not version or version.quote_id != quote_id:
        raise HTTPException(status_code=404, detail="Quote version not found")

    # FIND-146: server resolves 'active' status — caller must not supply status_id
    active_status = db.exec(
        select(QuoteLinkStatus).where(
            QuoteLinkStatus.code == "active",
            QuoteLinkStatus.tenant_id.is_(None),
        )
    ).first()
    if not active_status:
        raise HTTPException(
            status_code=500,
            detail="quote_link_status 'active' seed row not found — run alembic upgrade head",
        )

    public_link = QuotePublicLink(
        tenant_id=quote.tenant_id,
        quote_id=quote_id,
        contact_id=link_in.contact_id,
        token_hash="placeholder",  # Legacy field — populated by default
        expires_at=link_in.expires_at,
        max_uses=link_in.max_uses,
        status_id=active_status.id,
    )

    db.add(public_link)
    db.commit()
    db.refresh(public_link)

    # FIND-097: Generate HMAC-signed token (matches invoice public link pattern from FIND-073)
    signed_token, expires_at = generate_signed_token(
        link_id=public_link.id,
        link_type="quote",
        customer_id=quote.customer_id,
        expires_in_days=90,
    )

    # Update the public link with the signed token
    public_link.signed_token = signed_token
    if link_in.expires_at is None:
        # Use the signed token's expiration if no custom expiration was provided
        public_link.expires_at = expires_at
    db.add(public_link)
    db.commit()
    db.refresh(public_link)

    # Format URL with signed token
    url = f"https://frontend-domain.com/quote/{signed_token}"

    return QuotePublicLinkResponse(
        url=url,
        id=public_link.id,
        quote_id=public_link.quote_id,
        contact_id=public_link.contact_id,
        expires_at=public_link.expires_at,
        signed_token=signed_token,
    )


def _list_quote_lines_impl(
    quote_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[QuoteLine]:
    """
    Shared quote lines listing logic used by both authenticated and test endpoints.

    Args:
        quote_id: UUID of quote to list lines for
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        List of QuoteLine instances

    Raises:
        HTTPException: If quote not found

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    # Verify quote belongs to tenant
    quote = db.exec(
        select(Quote)
        .where(Quote.id == quote_id)
        .where(Quote.tenant_id == user_context.tenant_id)
    ).first()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    # Get lines for quote
    lines = db.exec(select(QuoteLine).where(QuoteLine.quote_id == quote_id)).all()

    return lines


def _convert_quote_impl(
    quote_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteConvertResponse:
    """
    Shared Quote → Job auto-conversion logic.

    Business rules:
        1. Quote must be in `accepted` status — returns 422 otherwise.
        2. Creates a new Job stamped with the latest quote_version_id FK.
        3. Copies customer_id, site_id, quote_id, quote_version_id from the quote.
        4. Transitions quote status to `converted`.

    Args:
        quote_id: UUID of the quote to convert
        db: Database session
        user_context: Either AuthenticatedUser or TestUserContext

    Returns:
        QuoteConvertResponse with new job_id, quote_id, and updated status

    Raises:
        HTTPException 404: Quote not found or wrong tenant
        HTTPException 422: Quote not in `accepted` status
    """
    # 1. Fetch quote with tenant scope
    quote = db.exec(
        select(Quote)
        .where(Quote.id == quote_id)
        .where(Quote.tenant_id == user_context.tenant_id)
    ).first()

    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )

    # 2. Validate quote is in `accepted` status
    current_status = db.exec(
        select(QuoteStatus).where(QuoteStatus.id == quote.status_id)
    ).first()

    if not current_status or current_status.code != "accepted":
        raise HTTPException(
            status_code=422,
            detail={
                "type": "invalid_quote_status",
                "title": "Quote Cannot Be Converted",
                "detail": (
                    f"Only quotes in 'accepted' status can be converted to a job. "
                    f"Current status: {current_status.code if current_status else 'unknown'}"
                ),
                "current_status": current_status.code if current_status else None,
            },
        )

    # 3. Resolve the latest quote_version_id for the FK stamp on the job
    latest_version = db.exec(
        select(QuoteVersion)
        .where(QuoteVersion.quote_id == quote_id)
        .where(QuoteVersion.tenant_id == user_context.tenant_id)
        .order_by(QuoteVersion.version_no.desc())
    ).first()

    # 4. Resolve default job status
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
        job_status = db.exec(select(JobStatus)).first()
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No job statuses available in the system",
            )

    # 5. Create the Job record
    new_job = Job(
        tenant_id=user_context.tenant_id,
        customer_id=quote.customer_id,
        site_id=quote.site_id,
        quote_id=quote.id,
        quote_version_id=latest_version.id if latest_version else None,
        status_id=job_status.id,
    )
    db.add(new_job)
    db.flush()  # Get the job ID without committing yet

    # 6. Transition quote to `converted` status
    converted_status = db.exec(
        select(QuoteStatus).where(
            QuoteStatus.code == "converted",
            QuoteStatus.tenant_id == user_context.tenant_id,
        )
    ).first()

    if not converted_status:
        # Fall back to system-wide converted status
        converted_status = db.exec(
            select(QuoteStatus).where(
                QuoteStatus.code == "converted",
                QuoteStatus.tenant_id.is_(None),
            )
        ).first()

    if not converted_status:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System `converted` quote status is missing. Run the migration.",
        )

    quote.status_id = converted_status.id
    db.add(quote)

    # 7. Commit both changes atomically
    db.commit()
    db.refresh(new_job)
    db.refresh(quote)

    return QuoteConvertResponse(
        job_id=new_job.id,
        quote_id=quote.id,
        quote_status=converted_status.code,
        job_status_id=new_job.status_id,
        quote_version_id=new_job.quote_version_id,
    )


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================
# NOTE: Test endpoints MUST be registered BEFORE authenticated endpoints
# to avoid route matching conflicts with empty path "" catching "/test"


@router.post(
    "/test",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote_test(
    quote_in: QuoteCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new quote (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002

    Usage:
        curl -X POST http://localhost:8000/api/v1/quotes/test \\
          -H "Content-Type: application/json" \\
          -d '{"customer_id": "...", "site_id": "...", "currency": "USD"}'

    Returns:
        QuoteResponse with created quote data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_quote_impl(quote_in, db, test_context)


@router.get("/test", response_model=PaginatedQuoteListResponse)
def list_quotes_test(
    skip: int = 0,
    limit: int = 25,
    offset: int = 0,
    status: str | None = None,
    customer_search: str | None = None,
    title_search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    customer_id: UUID | None = Query(
        default=None, description="Filter quotes by exact customer UUID"
    ),
    db: Session = Depends(get_db),
):
    """
    List quotes (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns quotes from test tenant only: 00000000-0000-0000-0000-000000000001

    Params:
        status: Optional status code filter (e.g. "draft", "sent") — BETA-B3 BE-2

    Usage:
        curl http://localhost:8000/api/v1/quotes/test
        curl http://localhost:8000/api/v1/quotes/test?status=draft

    Returns:
        PaginatedQuoteListResponse from test tenant (UI-FIX-1C)
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _list_quotes_impl(
        skip,
        limit,
        db,
        test_context,
        status_filter=status,
        customer_search=customer_search,
        title_search=title_search,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        customer_id=customer_id,
    )


@router.get("/{quote_id}/test", response_model=QuoteResponse)
def get_quote_test(
    quote_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific quote (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses test tenant: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/quotes/{quote_id}/test

    Returns:
        QuoteResponse with quote data from test tenant
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _get_quote_impl(quote_id, db, test_context)


@router.patch("/{quote_id}/test", response_model=QuoteResponse)
def update_quote_test(
    quote_id: UUID,
    quote_update: QuoteUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a quote (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses test tenant: 00000000-0000-0000-0000-000000000001

    Usage:
        curl -X PATCH http://localhost:8000/api/v1/quotes/{quote_id}/test \\
          -H "Content-Type: application/json" \\
          -d '{"status_id": "..."}'

    Returns:
        QuoteResponse with updated quote data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _update_quote_impl(quote_id, quote_update, db, test_context)


@router.post(
    "/{quote_id}/convert/test",
    response_model=QuoteConvertResponse,
    status_code=status.HTTP_201_CREATED,
)
def convert_quote_test(
    quote_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Convert an accepted quote to a job (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses test tenant: 00000000-0000-0000-0000-000000000001

    Business Rules:
        - Quote must be in `accepted` status — returns 422 otherwise
        - Creates a new Job record linked to the quote and latest quote_version
        - Transitions quote status to `converted`

    Usage:
        curl -X POST http://localhost:8000/api/v1/quotes/{quote_id}/convert/test

    Returns:
        QuoteConvertResponse with new job_id, quote_id, and updated quote status
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _convert_quote_impl(quote_id, db, test_context)


@router.post(
    "/{quote_id}/lines/test",
    response_model=QuoteLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote_line_test(
    quote_id: UUID,
    line_in: QuoteLineCreate,
    db: Session = Depends(get_db),
):
    """
    Add a line item to a quote (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002

    Usage:
        curl -X POST http://localhost:8000/api/v1/quotes/{quote_id}/lines/test \\
          -H "Content-Type: application/json" \\
          -d '{"description": "Panel upgrade", "quantity": 1, "unit_price_cents": 50000, "position": 1}'

    Returns:
        QuoteLineResponse with created line item data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_quote_line_impl(quote_id, line_in, db, test_context)


@router.get("/{quote_id}/lines/test", response_model=list[QuoteLineResponse])
def list_quote_lines_test(
    quote_id: UUID,
    db: Session = Depends(get_db),
):
    """
    List line items for a quote (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns lines for quote in test tenant: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/quotes/{quote_id}/lines/test

    Returns:
        List of QuoteLineResponse objects from test tenant
    """
    test_context = get_test_context()
    return _list_quote_lines_impl(quote_id, db, test_context)


@router.post(
    "/{quote_id}/versions/test",
    response_model=QuoteVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote_version_test(
    quote_id: UUID,
    create_in: QuoteVersionCreate = QuoteVersionCreate(),
    db: Session = Depends(get_db),
):
    """
    Create a versioned snapshot of a quote (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002

    Usage:
        curl -X POST http://localhost:8000/api/v1/quotes/{quote_id}/versions/test

    Returns:
        QuoteVersionResponse with snapshot data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_quote_version_impl(quote_id, db, test_context, create_in)


@router.post(
    "/{quote_id}/versions/{version_id}/public-link/test",
    response_model=QuotePublicLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_public_link_test(
    quote_id: UUID,
    version_id: UUID,
    link_in: QuotePublicLinkCreate,
    db: Session = Depends(get_db),
):
    """
    Generate a public shareable link for a quote version (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002

    Usage:
        curl -X POST http://localhost:8000/api/v1/quotes/{quote_id}/versions/{version_id}/public-link/test \\
          -H "Content-Type: application/json" \\
          -d '{"expires_at": "2026-04-30T23:59:59Z"}'

    Returns:
        QuotePublicLinkResponse with shareable URL
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_public_link_impl(quote_id, version_id, link_in, db, test_context)


# ==================== QUOTE ACCEPTANCE HELPERS ====================


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For header."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can be a comma-separated list; take the first IP
        return forwarded.split(",")[0].strip()

    # Get host from request.client, fallback to localhost for tests
    if request.client and request.client.host:
        host = request.client.host
        # TestClient uses "testclient" which is not a valid IP for INET type
        if host == "testclient":
            return "127.0.0.1"
        return host
    return "127.0.0.1"


def _get_user_agent(request: Request) -> str:
    """Extract user agent from request headers."""
    return request.headers.get("User-Agent", "unknown")


async def _accept_quote_impl(
    quote_id: UUID,
    acceptance_data: QuoteAcceptanceCreate,
    request: Request,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    quote_public_link_id: UUID | None = None,
) -> QuoteAcceptanceResponse:
    """
    Shared implementation for quote acceptance.

    Args:
        quote_id: UUID of quote to accept
        acceptance_data: Acceptance request data
        request: FastAPI request object (for IP/user agent)
        db: Database session
        user_context: Authenticated user or test context
        quote_public_link_id: Optional link ID if accepted via public link

    Returns:
        QuoteAcceptanceResponse with acceptance details

    Raises:
        HTTPException: 404 if quote not found
        HTTPException: 403 if tenant mismatch
        HTTPException: 400 if quote status invalid
        HTTPException: 409 if quote already accepted
    """
    # 1. Fetch quote and verify tenant isolation
    quote = db.exec(
        select(Quote).where(
            Quote.id == quote_id, Quote.tenant_id == user_context.tenant_id
        )
    ).first()

    if not quote:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "quote_not_found",
                "title": "Quote Not Found",
                "detail": f"Quote {quote_id} not found or access denied",
            },
        )

    # 2. Get the latest quote version first (needed for duplicate check)
    latest_version = db.exec(
        select(QuoteVersion)
        .where(QuoteVersion.quote_id == quote_id)
        .order_by(QuoteVersion.version_no.desc())
    ).first()

    if not latest_version:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "no_quote_version",
                "title": "No Quote Version Found",
                "detail": f"Quote {quote_id} has no versions created",
            },
        )

    # 3. Check for existing acceptance BEFORE status validation (prevent duplicates)
    # This must come before status check because accepting changes status to "accepted"
    existing_acceptance = db.exec(
        select(QuoteAcceptance).where(
            QuoteAcceptance.quote_version_id == latest_version.id
        )
    ).first()

    if existing_acceptance:
        raise HTTPException(
            status_code=409,
            detail={
                "type": "quote_already_accepted",
                "title": "Quote Already Accepted",
                "detail": f"Quote was already accepted on {existing_acceptance.approved_at.isoformat()}",
                "accepted_at": existing_acceptance.approved_at.isoformat(),
            },
        )

    # 4. Validate quote status (must be in acceptable status)
    # Only checked if not already accepted
    status_obj = db.get(QuoteStatus, quote.status_id)
    if status_obj.code not in ["draft", "sent", "pending"]:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "invalid_quote_status",
                "title": "Invalid Quote Status",
                "detail": f"Quote must be in 'Draft', 'Sent', or 'Pending' status. Current status: {status_obj.name}",
                "current_status": status_obj.code,
            },
        )

    # 5. Capture IP and user agent (use provided or auto-capture)
    ip_address = acceptance_data.ip_address or _get_client_ip(request)
    user_agent = acceptance_data.user_agent or _get_user_agent(request)

    # 6. Determine contact_id and user_id
    contact_id = None  # For MVP, we don't require a pre-existing contact
    accepted_by_user_id = None
    if isinstance(user_context, AuthenticatedUser):
        accepted_by_user_id = user_context.id

    # 7. Create quote_acceptance record
    acceptance = QuoteAcceptance(
        tenant_id=quote.tenant_id,
        quote_version_id=latest_version.id,
        contact_id=contact_id,
        accepted_by_name=acceptance_data.accepted_by_name,
        accepted_by_email=acceptance_data.accepted_by_email,
        accepted_by_user_id=accepted_by_user_id,
        approved_at=datetime.now(UTC),
        approved_ip=ip_address,
        approved_user_agent=user_agent,
        signature_url=acceptance_data.signature_url,
        acceptance_notes=acceptance_data.acceptance_notes,
        quote_public_link_id=quote_public_link_id,
        terms_acknowledged=True,
    )
    db.add(acceptance)

    # 8. Update quote status to "Accepted"
    accepted_status = db.exec(
        select(QuoteStatus).where(
            QuoteStatus.code == "accepted",
            QuoteStatus.tenant_id == user_context.tenant_id,
        )
    ).first()

    if not accepted_status:
        # Fallback to system default
        accepted_status = db.exec(
            select(QuoteStatus).where(
                QuoteStatus.code == "accepted", QuoteStatus.tenant_id.is_(None)
            )
        ).first()

    if accepted_status:
        quote.status_id = accepted_status.id

    # 9. Commit transaction
    db.commit()
    db.refresh(acceptance)
    db.refresh(quote)

    # 10. Build response
    final_status = db.get(QuoteStatus, quote.status_id)
    return QuoteAcceptanceResponse(
        id=acceptance.id,
        quote_version_id=acceptance.quote_version_id,
        contact_id=acceptance.contact_id,
        accepted_by_name=acceptance.accepted_by_name,
        accepted_by_email=acceptance.accepted_by_email,
        accepted_by_user_id=acceptance.accepted_by_user_id,
        approved_at=acceptance.approved_at,
        approved_ip=acceptance.approved_ip,
        approved_user_agent=acceptance.approved_user_agent,
        signature_url=acceptance.signature_url,
        acceptance_notes=acceptance.acceptance_notes,
        quote_public_link_id=acceptance.quote_public_link_id,
        quote_status=final_status.name if final_status else "Unknown",
    )


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post(
    "",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote(
    quote_in: QuoteCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.create")),
):
    """
    Create a new quote (requires JWT authentication and quotes.create permission).

    Security:
        - Requires valid JWT token
        - Requires quotes.create permission
        - Quote created in authenticated user's tenant

    Note:
        Quotes are unlimited on every plan (PRD §3.11). No feature entitlement
        gate is enforced — only RBAC (``quotes.create``). PLP-FIX-1 removed the
        prior ``feature_code="quotes_per_month"`` wiring, which was a phantom
        gate (the feature was never seeded and contradicts the PRD pricing model).

    Returns:
        QuoteResponse with created quote data
    """
    return _create_quote_impl(quote_in, db, current_user)


@router.post(
    "/{quote_id}/convert",
    response_model=QuoteConvertResponse,
    status_code=status.HTTP_201_CREATED,
)
def convert_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.update")),
):
    """
    Convert an accepted quote to a job (requires JWT authentication and quotes.update permission).

    Business Rules:
        - Quote must be in `accepted` status — returns 422 Unprocessable Entity otherwise
        - Creates a new Job record stamped with quote_id and latest quote_version_id FK
        - Copies customer_id and site_id from the quote
        - Transitions quote status to `converted` (terminal)

    Security:
        - Requires valid JWT token
        - Requires quotes.update permission
        - Validates quote belongs to authenticated user's tenant

    Returns:
        QuoteConvertResponse with new job_id, quote_id, job_status_id, and updated quote status

    Raises:
        404: Quote not found or access denied
        422: Quote is not in `accepted` status
    """
    return _convert_quote_impl(quote_id, db, current_user)


@router.get("", response_model=PaginatedQuoteListResponse)
def list_quotes(
    skip: int = 0,
    limit: int = 25,
    offset: int = 0,
    status: str | None = None,
    customer_search: str | None = None,
    title_search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    customer_id: UUID | None = Query(
        default=None, description="Filter quotes by exact customer UUID"
    ),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
):
    """
    List quotes (requires JWT authentication and quotes.view permission).

    UI-FIX-1C: Returns PaginatedQuoteListResponse with total, limit, offset.
    BETA-B3 additions (BE-2, BE-3, BE-4):
    - ?status= filter: case-insensitive filter by status code (e.g. "draft", "sent")
    - Response includes status_code (denormalized from QuoteStatus) and
      customer_name (denormalized from Customer.display_name) for list display.

    Security:
        - Requires valid JWT token
        - Requires quotes.view permission
        - Returns only quotes in authenticated user's tenant

    Params:
        customer_search: Optional case-insensitive search on customer display_name
        title_search: Optional case-insensitive search on quote title
        date_from: Optional filter for quotes created on or after this datetime
        date_to: Optional filter for quotes created on or before this datetime
        customer_id: Optional exact UUID match on quote.customer_id (UI-FIX-2D)
        offset: Pagination offset (supersedes deprecated skip)

    Returns:
        PaginatedQuoteListResponse with total count
    """
    return _list_quotes_impl(
        skip,
        limit,
        db,
        current_user,
        status_filter=status,
        customer_search=customer_search,
        title_search=title_search,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        customer_id=customer_id,
    )


@router.get("/{quote_id}", response_model=QuoteResponse)
def get_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
):
    """
    Get a specific quote (requires JWT authentication and quotes.view permission).

    Security:
        - Requires valid JWT token
        - Requires quotes.view permission
        - Validates quote belongs to authenticated user's tenant

    Returns:
        QuoteResponse with quote data
    """
    return _get_quote_impl(quote_id, db, current_user)


@router.get(
    "/{quote_id}/detail/test",
    response_model=QuoteDetailResponse,
    include_in_schema=False,
    summary="Test-only: get aggregated quote detail without JWT (PRE-WS3-FIX-01)",
)
def get_quote_detail_test(
    quote_id: UUID,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    """
    Test-only endpoint — bypasses JWT auth. Uses canonical test tenant context.
    Required for the test suite to exercise the detail endpoint without mocking auth.
    PRE-WS3-FIX-01
    """
    return get_quote_detail(
        quote_id=quote_id,
        tenant_id=ctx.tenant_id,
        db=db,
    )


@router.get(
    "/{quote_id}/detail",
    response_model=QuoteDetailResponse,
    summary="Get aggregated quote detail for the approval/review surface (PRE-WS3-FIX-01)",
)
def get_quote_detail_endpoint(
    quote_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
):
    """
    Returns a fully aggregated QuoteDetailResponse for the QuoteDetailPage surface.

    Includes: status code, customer name, submitted-by user name, rejection timestamp
    (from approval comments), latest active version ID, pending edits flag, line items
    with resolved line types, margin percent, and require_approval setting.

    Security:
        - Requires valid JWT token
        - Requires quotes.view permission
        - Validates quote belongs to authenticated user's tenant

    See design doc: dev-docs/architecture-design/pre-wkstm-3-fix-designs/pre-wkstm-3-fix-01.md
    PRE-WS3-FIX-01
    """
    return get_quote_detail(
        quote_id=quote_id,
        tenant_id=current_user.tenant_id,
        db=db,
    )


@router.patch("/{quote_id}", response_model=QuoteResponse)
def update_quote(
    quote_id: UUID,
    quote_update: QuoteUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.update")),
):
    """
    Update a quote (requires JWT authentication and quotes.update permission).

    Security:
        - Requires valid JWT token
        - Requires quotes.update permission
        - Validates quote belongs to authenticated user's tenant

    Returns:
        QuoteResponse with updated quote data
    """
    return _update_quote_impl(quote_id, quote_update, db, current_user)


@router.post(
    "/{quote_id}/lines",
    response_model=QuoteLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote_line(
    quote_id: UUID,
    line_in: QuoteLineCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.update")),
):
    """
    Add a line item to a quote (requires JWT authentication and quotes.update permission).

    Security:
        - Requires valid JWT token
        - Requires quotes.update permission
        - Validates quote belongs to authenticated user's tenant
        - Auto-calculates pricing from pricebook or catalog

    Returns:
        QuoteLineResponse with created line item data
    """
    return _create_quote_line_impl(quote_id, line_in, db, current_user)


@router.get("/{quote_id}/lines", response_model=list[QuoteLineResponse])
def list_quote_lines(
    quote_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
):
    """
    List line items for a quote (requires JWT authentication and quotes.view permission).

    Security:
        - Requires valid JWT token
        - Requires quotes.view permission
        - Validates quote belongs to authenticated user's tenant

    Returns:
        List of QuoteLineResponse objects
    """
    return _list_quote_lines_impl(quote_id, db, current_user)


@router.post(
    "/{quote_id}/versions",
    response_model=QuoteVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote_version(
    quote_id: UUID,
    create_in: QuoteVersionCreate = QuoteVersionCreate(),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.create")),
):
    """
    Create a versioned snapshot of a quote (requires JWT authentication and quotes.create permission).

    Security:
        - Requires valid JWT token
        - Requires quotes.create permission
        - Validates quote belongs to authenticated user's tenant

    Returns:
        QuoteVersionResponse with snapshot data
    """
    return _create_quote_version_impl(quote_id, db, current_user, create_in)


@router.post(
    "/{quote_id}/versions/{version_id}/public-link",
    response_model=QuotePublicLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_public_link(
    quote_id: UUID,
    version_id: UUID,
    link_in: QuotePublicLinkCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.create")),
):
    """
    Generate a public shareable link for a quote version (requires JWT authentication and quotes.create permission).

    Security:
        - Requires valid JWT token
        - Requires quotes.create permission
        - Validates quote belongs to authenticated user's tenant
        - Generates secure token for public access

    Returns:
        QuotePublicLinkResponse with shareable URL
    """
    return _create_public_link_impl(quote_id, version_id, link_in, db, current_user)


@router.post("/quotes/{quote_id}/accept", response_model=QuoteAcceptanceResponse)
async def accept_quote(
    quote_id: UUID,
    acceptance_data: QuoteAcceptanceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.update")),
) -> QuoteAcceptanceResponse:
    """
    Accept a quote (authenticated endpoint).

    This endpoint is used by tenant users to accept quotes on behalf of customers.
    The acceptance is linked to the authenticated user for audit purposes.

    Security:
        - Requires valid JWT token
        - Requires quotes.update permission
        - Validates quote belongs to authenticated user's tenant
        - Captures IP address and user agent for audit trail
        - Prevents duplicate acceptances

    Args:
        quote_id: UUID of the quote to accept
        acceptance_data: Acceptance details (name, email, signature URL, notes)
        request: FastAPI request object (auto-injected)

    Returns:
        QuoteAcceptanceResponse with acceptance details and updated quote status

    Raises:
        404: Quote not found or access denied
        400: Invalid quote status (not in Draft/Sent/Pending)
        409: Quote already accepted
    """
    return await _accept_quote_impl(
        quote_id=quote_id,
        acceptance_data=acceptance_data,
        request=request,
        db=db,
        user_context=current_user,
    )


@router.post("/test/quotes/{quote_id}/accept", response_model=QuoteAcceptanceResponse)
async def accept_quote_test(
    quote_id: UUID,
    acceptance_data: QuoteAcceptanceCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> QuoteAcceptanceResponse:
    """
    Test endpoint for accepting quotes without authentication.

    Uses the test tenant context for development and testing.
    Blocked in production by TEST_ENDPOINT_ENABLED config flag.

    Args:
        quote_id: UUID of the quote to accept
        acceptance_data: Acceptance details
        request: FastAPI request object (auto-injected)

    Returns:
        QuoteAcceptanceResponse with acceptance details
    """
    test_context = get_test_context()
    return await _accept_quote_impl(
        quote_id=quote_id,
        acceptance_data=acceptance_data,
        request=request,
        db=db,
        user_context=test_context,
    )


def _resolve_quote_link_or_401(db: Session, token: str) -> tuple:
    """
    FIND-097: Resolve a signed quote public link token to (QuotePublicLink, payload).
    Raises 401 (invalid sig), 410 (expired or revoked).
    Supports both HMAC signed tokens and legacy token_hash for backward compatibility.
    """
    # Try HMAC verification first (new path)
    if "." in token:  # HMAC tokens contain a dot separator
        try:
            payload = verify_signed_token(token)
            link_id = payload.get("link_id")
            if not link_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )

            link = db.exec(
                select(QuotePublicLink).where(QuotePublicLink.id == UUID(link_id))
            ).first()

            if link is None:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="Link not found",
                )

            if link.revoked_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="Link has been revoked",
                )

            return link, payload
        except TokenExpiredError:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Link has expired",
            )
        except TokenInvalidError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid link token",
            )

    # Legacy path: fallback to token_hash lookup

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    link = db.exec(
        select(QuotePublicLink).where(QuotePublicLink.token_hash == token_hash)
    ).first()

    if not link:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "public_link_not_found",
                "title": "Public Link Not Found",
                "detail": "The provided quote link is invalid or has been revoked",
            },
        )

    return link, {}


@router.post("/public/{token}/accept", response_model=QuoteAcceptanceResponse)
async def accept_quote_via_public_link(
    token: str,
    acceptance_data: QuoteAcceptanceCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> QuoteAcceptanceResponse:
    """
    Accept a quote via public link (no authentication required).

    This endpoint allows customers to accept quotes using a public link token.
    The token is validated to ensure it's active and not expired.

    Security:
        - Token must be valid (HMAC signature or legacy hash lookup)
        - Link must be active (not revoked)
        - Link must not be expired
        - Usage count must be under max_uses limit

    Args:
        token: Public link token (from URL)
        acceptance_data: Acceptance details
        request: FastAPI request object (auto-injected)

    Returns:
        QuoteAcceptanceResponse with acceptance details

    Raises:
        404: Public link not found or quote not found
        403: Link inactive, expired, or usage limit exceeded
    """
    # 1. FIND-097: Resolve token (supports both HMAC and legacy token_hash)
    public_link, _ = _resolve_quote_link_or_401(db, token)

    # 3. Get the quote to determine tenant context
    quote = db.get(Quote, public_link.quote_id)
    if not quote:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "quote_not_found",
                "title": "Quote Not Found",
                "detail": "The quote associated with this link no longer exists",
            },
        )

    # 4. FIND-146: Enforce link status (replaces the "skip for MVP" placeholder)
    active_status = db.exec(
        select(QuoteLinkStatus).where(
            QuoteLinkStatus.code == "active",
            QuoteLinkStatus.tenant_id.is_(None),
        )
    ).first()

    # Inline expiry check and transition before status check
    if public_link.expires_at and public_link.expires_at < datetime.now(UTC):
        # Transition to 'expired' then reject
        expired_status = db.exec(
            select(QuoteLinkStatus).where(
                QuoteLinkStatus.code == "expired",
                QuoteLinkStatus.tenant_id.is_(None),
            )
        ).first()
        if expired_status:
            public_link.status_id = expired_status.id
            db.add(public_link)
            db.commit()
        raise HTTPException(
            status_code=403,
            detail={
                "type": "public_link_expired",
                "title": "Public Link Expired",
                "detail": f"This quote link expired on {public_link.expires_at.isoformat()}",
                "expired_at": public_link.expires_at.isoformat(),
            },
        )

    # Reject if not active (revoked or exhausted)
    if active_status and public_link.status_id != active_status.id:
        raise HTTPException(
            status_code=403,
            detail={
                "type": "public_link_inactive",
                "title": "Public Link No Longer Active",
                "detail": "This quote link is no longer active",
            },
        )

    # 5. Check expiration
    if public_link.expires_at and public_link.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=403,
            detail={
                "type": "public_link_expired",
                "title": "Public Link Expired",
                "detail": f"This quote link expired on {public_link.expires_at.isoformat()}",
                "expired_at": public_link.expires_at.isoformat(),
            },
        )

    # 6. Check usage limit
    if public_link.used_count >= public_link.max_uses:
        raise HTTPException(
            status_code=403,
            detail={
                "type": "public_link_max_uses_exceeded",
                "title": "Public Link Usage Limit Exceeded",
                "detail": f"This quote link has reached its maximum usage limit ({public_link.max_uses})",
            },
        )

    # 7. Create a pseudo user context with the quote's tenant
    # Use a special UUID for public link acceptances (no authenticated user)
    public_link_user_id = UUID("00000000-0000-0000-0000-000000000000")
    tenant_context = TestUserContext(
        tenant_id=quote.tenant_id,
        id=public_link_user_id,
    )

    # 8. Accept the quote
    result = await _accept_quote_impl(
        quote_id=public_link.quote_id,
        acceptance_data=acceptance_data,
        request=request,
        db=db,
        user_context=tenant_context,
        quote_public_link_id=public_link.id,
    )

    # 9. Increment usage count; transition to exhausted if max_uses reached (FIND-146)
    public_link.used_count += 1
    public_link.last_used_at = datetime.now(UTC)
    if public_link.max_uses > 0 and public_link.used_count >= public_link.max_uses:
        exhausted_status = db.exec(
            select(QuoteLinkStatus).where(
                QuoteLinkStatus.code == "exhausted",
                QuoteLinkStatus.tenant_id.is_(None),
            )
        ).first()
        if exhausted_status:
            public_link.status_id = exhausted_status.id
    db.commit()

    return result


# ==================== QUOTE VIEW ANALYTICS / READ RECEIPTS (Task 1-E-2) ====================


def _get_quote_analytics_impl(
    id: UUID,
    db: Session,
    user_context: "AuthenticatedUser | TestUserContext",
) -> QuoteAnalyticsResponse:
    """
    Build a sorted analytics timeline for a given quote.

    Performs a three-table JOIN:
      QuotePublicLinkContactAction → QplContactActionType (action name)
                                  → Contact (person who performed the action)

    IDOR Protection: filters by both quote_id AND tenant_id so a user from
    Tenant A can never read events recorded under Tenant B.

    Args:
        id:           The Quote UUID to retrieve analytics for.
        db:           Active SQLModel session.
        user_context: Authenticated user or TestUserContext (provides tenant_id).

    Returns:
        QuoteAnalyticsResponse with events sorted newest-first.
    """
    # Verify the quote exists AND belongs to this tenant (IDOR guard → 404, not 403)
    quote = db.exec(
        select(Quote).where(
            Quote.id == id,
            Quote.tenant_id == user_context.tenant_id,
        )
    ).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://pilotfortrades.com/errors/not-found",
                "title": "Quote Not Found",
                "status": 404,
                "detail": f"Quote {id} not found or does not belong to your tenant",
            },
        )

    # Three-table JOIN: action event + action type name + contact name
    rows = db.exec(
        select(
            QuotePublicLinkContactAction,
            QplContactActionType,
            Contact,
        )
        .join(
            QplContactActionType,
            QuotePublicLinkContactAction.qpl_contact_action_type_id
            == QplContactActionType.id,
        )
        .join(
            Contact,
            QuotePublicLinkContactAction.contact_id == Contact.id,
        )
        .where(
            QuotePublicLinkContactAction.quote_id == id,
            QuotePublicLinkContactAction.tenant_id == user_context.tenant_id,
        )
        .order_by(QuotePublicLinkContactAction.occurred_at.desc())
    ).all()

    events = []
    for action, action_type, contact in rows:
        # Build human-readable contact name
        parts = []
        if contact.first_name:
            parts.append(contact.first_name)
        if contact.last_name:
            parts.append(contact.last_name)
        contact_name = " ".join(parts) if parts else None

        events.append(
            QuoteAnalyticsEvent(
                action_name=action_type.name,
                contact_name=contact_name,
                occurred_at=action.occurred_at,
                ip_address=str(action.ip) if action.ip else None,
                user_agent=action.user_agent,
            )
        )

    return QuoteAnalyticsResponse(events=events)


# ── /test endpoint MUST be registered BEFORE the authenticated endpoint ──────


@router.get(
    "/{id}/analytics/test",
    response_model=QuoteAnalyticsResponse,
    summary="[TEST] Get quote view analytics timeline (no auth)",
    tags=["quotes"],
)
def get_quote_analytics_test(
    id: UUID,
    db: Session = Depends(get_db),
):
    """
    Test-only variant of GET /{id}/analytics.
    Requires TEST_ENDPOINT_ENABLED=true and ENVIRONMENT=dev|qa.
    """
    test_context = get_test_context()
    return _get_quote_analytics_impl(id, db, test_context)


@router.get(
    "/{id}/analytics",
    response_model=QuoteAnalyticsResponse,
    summary="Get quote view analytics timeline",
    tags=["quotes"],
)
def get_quote_analytics(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
):
    """
    Return a sorted timeline of all contact actions (views, acceptances, etc.)
    on a given quote's public links. Newest events appear first.

    IDOR-protected: a tenant can only see events for their own quotes.
    Returns 404 (not 403) for cross-tenant quote IDs.

    Requires the `quotes.view` permission.
    """
    return _get_quote_analytics_impl(id, db, current_user)


# ==================== SHARED _impl() FUNCTIONS (A2, A3, A27, A30, B15) ====================


def _submit_quote_for_approval_impl(
    id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteSubmitForApprovalResponse:
    """Shared logic for submitting a quote for approval."""
    quote = db.exec(
        select(Quote)
        .where(Quote.id == id)
        .where(Quote.tenant_id == user_context.tenant_id)
        .where(Quote.is_active == True)
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    current_status_code = get_quote_status_code(quote, db)
    if current_status_code != "draft":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/invalid-state",
                "title": "Invalid State Transition",
                "status": 422,
                "detail": f"Quote must be in 'draft' status to submit for approval. "
                f"Current status: '{current_status_code}'",
            },
        )

    now = datetime.now(UTC)
    quote.submitted_by_user_id = user_context.id
    quote.submitted_at = now
    db.add(quote)

    quote = transition_quote_status(
        quote, "pending_approval", db, user_context.tenant_id
    )

    return QuoteSubmitForApprovalResponse(
        quote_id=quote.id,
        status="pending_approval",
        submitted_at=quote.submitted_at,
        submitted_by_user_id=quote.submitted_by_user_id,
    )


def _approve_quote_impl(
    id: UUID,
    payload: QuoteApproveRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteApproveResponse:
    """Shared logic for approving a quote."""
    quote = db.exec(
        select(Quote)
        .where(Quote.id == id)
        .where(Quote.tenant_id == user_context.tenant_id)
        .where(Quote.is_active == True)
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    assert_quote_version_not_stale(
        payload.expected_quote_version_id, quote.id, db, user_context.tenant_id
    )

    current_status_code = get_quote_status_code(quote, db)
    if current_status_code != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/invalid-state",
                "title": "Invalid State Transition",
                "status": 422,
                "detail": f"Quote must be in 'pending_approval' status to approve. "
                f"Current status: '{current_status_code}'",
            },
        )

    now = datetime.now(UTC)
    quote.approved_by_user_id = user_context.id
    quote.approved_at = now
    db.add(quote)

    quote = transition_quote_status(quote, "approved", db, user_context.tenant_id)

    return QuoteApproveResponse(
        quote_id=quote.id,
        status="approved",
        approved_at=quote.approved_at,
        approved_by_user_id=quote.approved_by_user_id,
    )


def _reject_quote_impl(
    id: UUID,
    payload: QuoteRejectRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteRejectResponse:
    """Shared logic for rejecting a quote."""
    if not payload.overall_comment or not payload.overall_comment.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Validation Error",
                "status": 422,
                "detail": "overall_comment is required when rejecting a quote.",
            },
        )

    quote = db.exec(
        select(Quote)
        .where(Quote.id == id)
        .where(Quote.tenant_id == user_context.tenant_id)
        .where(Quote.is_active == True)
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    assert_quote_version_not_stale(
        payload.expected_quote_version_id, quote.id, db, user_context.tenant_id
    )

    current_status_code = get_quote_status_code(quote, db)
    if current_status_code != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/invalid-state",
                "title": "Invalid State Transition",
                "status": 422,
                "detail": f"Quote must be in 'pending_approval' status to reject. "
                f"Current status: '{current_status_code}'",
            },
        )

    quote = transition_quote_status(quote, "rejected", db, user_context.tenant_id)

    return QuoteRejectResponse(
        quote_id=quote.id,
        status="rejected",
    )


def _save_quote_as_template_impl(
    id: UUID,
    payload: QuoteSaveAsTemplateRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteSaveAsTemplateResponse:
    """Shared logic for saving a quote as a template."""
    quote = db.exec(
        select(Quote)
        .where(Quote.id == id)
        .where(Quote.tenant_id == user_context.tenant_id)
        .where(Quote.is_active == True)
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    existing = db.exec(
        select(QuoteTemplate).where(
            QuoteTemplate.tenant_id == user_context.tenant_id,
            QuoteTemplate.name == payload.name,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Duplicate Template Name",
                "status": 422,
                "detail": f"A template named '{payload.name}' already exists for this tenant.",
            },
        )

    style = payload.style or "component"
    valid_styles = {"component", "deliverable", "lump_sum"}
    if style not in valid_styles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Invalid Style",
                "status": 422,
                "detail": f"style must be one of: {', '.join(valid_styles)}",
            },
        )

    template = QuoteTemplate(
        tenant_id=user_context.tenant_id,
        name=payload.name,
        style=style,
        category=payload.category,
        is_system_template=False,
        is_active=True,
        current_version=1,
        created_by=user_context.id,
        updated_by=user_context.id,
    )
    db.add(template)
    db.flush()

    live_lines = db.exec(
        select(QuoteLine)
        .where(QuoteLine.quote_id == quote.id)
        .where(QuoteLine.is_active == True)
        .order_by(QuoteLine.position)
    ).all()

    for line in live_lines:
        tl = QuoteTemplateLine(
            tenant_id=user_context.tenant_id,
            quote_template_id=template.id,
            qco_line_type_id=line.qco_line_type_id,
            description=line.description,
            default_quantity=line.quantity,
            default_unit_price_cents=line.unit_price_cents,
            customer_visible=line.customer_visible,
            is_section_header=line.is_section_header,
            display_order=line.display_order,
            is_active=True,
            created_by=user_context.id,
            updated_by=user_context.id,
        )
        db.add(tl)

    db.commit()
    db.refresh(template)

    return QuoteSaveAsTemplateResponse(
        template_id=template.id,
        name=template.name,
        style=template.style,
        category=template.category,
        line_count=len(live_lines),
    )


def _apply_quote_discount_impl(
    id: UUID,
    payload: QuoteApplyDiscountRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteApplyDiscountResponse:
    """Shared logic for applying a discount to a quote."""
    quote = db.exec(
        select(Quote)
        .where(Quote.id == id)
        .where(Quote.tenant_id == user_context.tenant_id)
        .where(Quote.is_active == True)
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    assert_quote_version_not_stale(
        payload.expected_quote_version_id, quote.id, db, user_context.tenant_id
    )

    if quote.discount_pct is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Discount Already Applied",
                "status": 422,
                "detail": "This quote already has a discount applied. Remove the existing discount before applying a new one.",
            },
        )

    from services.setting_resolver import get_effective_setting

    max_pct_val, _ = get_effective_setting(
        db, user_context.tenant_id, "max_discount_pct_owner", fallback=15.0
    )
    max_pct = Decimal(str(max_pct_val))

    if payload.discount_pct > max_pct:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Discount Exceeds Cap",
                "status": 400,
                "detail": f"discount_pct {payload.discount_pct} exceeds max_discount_pct_owner {max_pct} for this tenant.",
            },
        )

    if payload.discount_pct < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://pilotfortrades.com/errors/validation",
                "title": "Invalid Discount",
                "status": 400,
                "detail": "discount_pct must be non-negative.",
            },
        )

    discount_amount_cents = int(
        quote.total_cents * payload.discount_pct / Decimal("100")
    )

    quote.discount_pct = payload.discount_pct
    quote.discount_amount_cents = discount_amount_cents
    quote.discount_expires_at = payload.discount_expires_at
    quote.discount_applied_by_user_id = user_context.id
    db.add(quote)
    db.flush()

    new_version = _create_quote_version_impl(quote.id, db, user_context)
    db.commit()
    db.refresh(new_version)

    return QuoteApplyDiscountResponse(
        quote_id=quote.id,
        discount_pct=quote.discount_pct,
        discount_amount_cents=quote.discount_amount_cents,
        discount_expires_at=quote.discount_expires_at,
        new_version_id=new_version.id,
    )


def _get_quote_comments_impl(
    id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[QuoteApprovalCommentResponse]:
    """Shared logic for listing quote approval comments."""
    quote = db.exec(
        select(Quote)
        .where(Quote.id == id)
        .where(Quote.tenant_id == user_context.tenant_id)
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    comments = db.exec(
        select(QuoteApprovalComment)
        .where(QuoteApprovalComment.quote_id == id)
        .where(QuoteApprovalComment.tenant_id == user_context.tenant_id)
        .order_by(QuoteApprovalComment.created_at.desc())
    ).all()
    return [QuoteApprovalCommentResponse.model_validate(c) for c in comments]


def _kickback_quote_impl(
    id: UUID,
    payload: QuoteKickbackRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteKickbackResponse:
    """Shared logic for kicking back a quote to draft."""
    if not payload.overall_comment and not payload.line_comments:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "detail": "At least one of overall_comment or line_comments is required."
            },
        )

    quote = db.exec(
        select(Quote)
        .where(Quote.id == id)
        .where(Quote.tenant_id == user_context.tenant_id)
        .where(Quote.is_active == True)
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    assert_quote_version_not_stale(
        payload.expected_quote_version_id, quote.id, db, user_context.tenant_id
    )

    current_status_code = get_quote_status_code(quote, db)
    if current_status_code != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "detail": f"Quote must be in 'pending_approval' status. Current: '{current_status_code}'"
            },
        )

    latest_version = db.exec(
        select(QuoteVersion)
        .where(QuoteVersion.quote_id == id)
        .where(QuoteVersion.tenant_id == user_context.tenant_id)
        .order_by(QuoteVersion.version_no.desc())
    ).first()

    comment_count = 0
    if latest_version:
        if payload.overall_comment:
            comment = QuoteApprovalComment(
                tenant_id=user_context.tenant_id,
                quote_id=id,
                quote_version_id=latest_version.id,
                author_user_id=user_context.id,
                comment_type="kickback",
                content=payload.overall_comment,
                created_by=user_context.id,
            )
            db.add(comment)
            comment_count += 1

        for line_comment in payload.line_comments or []:
            comment = QuoteApprovalComment(
                tenant_id=user_context.tenant_id,
                quote_id=id,
                quote_version_id=latest_version.id,
                target_line_id=line_comment.get("target_line_id"),
                author_user_id=user_context.id,
                comment_type="kickback",
                content=line_comment.get("content", ""),
                created_by=user_context.id,
            )
            db.add(comment)
            comment_count += 1

    db.flush()

    quote = transition_quote_status(quote, "draft", db, user_context.tenant_id)

    return QuoteKickbackResponse(
        quote_id=quote.id,
        status="draft",
        comment_count=comment_count,
    )


def _revoke_quote_public_link_impl(
    quote_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuoteRevokeLinkResponse:
    """Shared logic for revoking a quote public link."""
    from app.models.quoting import QuotePublicLink

    quote = db.exec(
        select(Quote)
        .where(Quote.id == quote_id)
        .where(Quote.tenant_id == user_context.tenant_id)
    ).first()
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found"
        )

    link = db.exec(
        select(QuotePublicLink)
        .where(QuotePublicLink.quote_id == quote_id)
        .where(QuotePublicLink.tenant_id == user_context.tenant_id)
        .where(QuotePublicLink.revoked_at == None)
    ).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active public link found for this quote",
        )

    revoked_status = db.exec(
        select(QuoteLinkStatus).where(
            QuoteLinkStatus.code == "revoked",
            QuoteLinkStatus.tenant_id.is_(None),
        )
    ).first()

    # Only set audit context for real authenticated users (not test context)
    if isinstance(user_context, AuthenticatedUser):
        set_audit_context_sync(db, user_context.id)

    now = datetime.now(UTC)
    link.revoked_at = now
    if revoked_status:
        link.status_id = revoked_status.id
    db.add(link)
    db.commit()

    return QuoteRevokeLinkResponse(id=link.id, revoked_at=now, status="revoked")


# ==================== TEST ENDPOINTS for A2, A3, A27, A30, B15 (register BEFORE authenticated) ====================


@router.post(
    "/{id}/submit-for-approval/test",
    response_model=QuoteSubmitForApprovalResponse,
    summary="Submit a quote for approval (TEST — no auth)",
    tags=["quotes"],
)
def submit_quote_for_approval_test(
    id: UUID,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required. Blocked in staging/production."""
    test_context = get_test_context()
    return _submit_quote_for_approval_impl(id, db, test_context)


@router.post(
    "/{id}/approve/test",
    response_model=QuoteApproveResponse,
    summary="Approve a pending quote (TEST — no auth)",
    tags=["quotes"],
)
def approve_quote_test(
    id: UUID,
    payload: QuoteApproveRequest,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _approve_quote_impl(id, payload, db, test_context)


@router.post(
    "/{id}/reject/test",
    response_model=QuoteRejectResponse,
    summary="Reject a pending quote (TEST — no auth)",
    tags=["quotes"],
)
def reject_quote_test(
    id: UUID,
    payload: QuoteRejectRequest,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _reject_quote_impl(id, payload, db, test_context)


@router.post(
    "/{id}/save-as-template/test",
    response_model=QuoteSaveAsTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a quote as a template (TEST — no auth)",
    tags=["quotes"],
)
def save_quote_as_template_test(
    id: UUID,
    payload: QuoteSaveAsTemplateRequest,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _save_quote_as_template_impl(id, payload, db, test_context)


@router.post(
    "/{id}/apply-discount/test",
    response_model=QuoteApplyDiscountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply a discount to a quote (TEST — no auth)",
    tags=["quotes"],
)
def apply_quote_discount_test(
    id: UUID,
    payload: QuoteApplyDiscountRequest,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _apply_quote_discount_impl(id, payload, db, test_context)


@router.get(
    "/{id}/comments/test",
    response_model=list[QuoteApprovalCommentResponse],
    summary="Get quote approval comments (TEST — no auth)",
    tags=["quotes"],
)
def get_quote_comments_test(
    id: UUID,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_quote_comments_impl(id, db, test_context)


@router.post(
    "/{id}/kickback/test",
    response_model=QuoteKickbackResponse,
    summary="Kick back a quote to draft (TEST — no auth)",
    tags=["quotes"],
)
def kickback_quote_test(
    id: UUID,
    payload: QuoteKickbackRequest,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _kickback_quote_impl(id, payload, db, test_context)


@router.post(
    "/{quote_id}/public-link/revoke/test",
    response_model=QuoteRevokeLinkResponse,
    summary="Revoke a quote public link (TEST — no auth)",
    tags=["quotes"],
)
def revoke_quote_public_link_test(
    quote_id: UUID,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _revoke_quote_public_link_impl(quote_id, db, test_context)


# ==================== A2: QUOTE APPROVAL WORKFLOW ====================


@router.post(
    "/{id}/submit-for-approval",
    response_model=QuoteSubmitForApprovalResponse,
    summary="Submit a quote for owner approval",
    tags=["quotes"],
)
def submit_quote_for_approval(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("quote.submit_for_approval")
    ),
):
    """
    A2: Submit a quote for owner/accountant approval.

    - Quote must be in 'draft' status.
    - When tenant.require_approval_for_tech_quotes = TRUE (default), transitions
      quote to 'pending_approval' and records submitter info.
    - Returns 422 if quote is not in 'draft' status.
    - Returns 404 if quote not found for tenant.
    """
    return _submit_quote_for_approval_impl(id, db, current_user)


@router.post(
    "/{id}/approve",
    response_model=QuoteApproveResponse,
    summary="Approve a pending quote",
    tags=["quotes"],
)
def approve_quote(
    id: UUID,
    payload: QuoteApproveRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quote.approve")),
):
    """
    A2: Approve a quote that is in 'pending_approval' status.

    - Owner/accountant permission required.
    - Staleness check via expected_quote_version_id (optional).
    - Transitions quote to 'approved' status.
    - Returns 409 if stale, 422 if not in pending_approval status.
    """
    return _approve_quote_impl(id, payload, db, current_user)


@router.post(
    "/{id}/reject",
    response_model=QuoteRejectResponse,
    summary="Reject a pending quote",
    tags=["quotes"],
)
def reject_quote(
    id: UUID,
    payload: QuoteRejectRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quote.approve")),
):
    """
    A2: Reject a quote that is in 'pending_approval' status.

    - Owner/accountant permission required.
    - overall_comment is required — rejection must have a reason.
    - Staleness check via expected_quote_version_id (optional).
    - Transitions quote to 'rejected' status (terminal state).
    - Returns 409 if stale, 422 if comment missing or not in pending_approval.
    """
    return _reject_quote_impl(id, payload, db, current_user)


# ==================== A27: SAVE QUOTE AS TEMPLATE ====================


@router.post(
    "/{id}/save-as-template",
    response_model=QuoteSaveAsTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a quote as a reusable template",
    tags=["quotes"],
)
def save_quote_as_template(
    id: UUID,
    payload: QuoteSaveAsTemplateRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("quote_template.create")
    ),
):
    """
    A27: Save the current live quote lines as a reusable quote template.

    - Operates on the live quote_line rows (is_active=True), not a historical snapshot.
    - Returns 404 if the quote is not found for this tenant.
    - Returns 422 if name already exists as a template for this tenant.
    RBAC: quote_template.create (owner, accountant only).
    """
    return _save_quote_as_template_impl(id, payload, db, current_user)


# ==================== A3: TIME-LIMITED DISCOUNTS ====================


@router.post(
    "/{id}/apply-discount",
    response_model=QuoteApplyDiscountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply a time-limited discount to a quote",
    tags=["quotes"],
)
def apply_quote_discount(
    id: UUID,
    payload: QuoteApplyDiscountRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("quote.apply_discount")
    ),
):
    """
    A3: Apply a percentage discount to a quote (any status).

    - Validates discount_pct does not exceed tenant max_discount_pct_owner.
    - Returns 400 if discount_pct exceeds the cap.
    - Returns 422 if discount already applied.
    - Returns 409 if stale version.
    RBAC: quote.apply_discount (owner, accountant only).
    """
    return _apply_quote_discount_impl(id, payload, db, current_user)


# ==================== A29: PENDING EDIT STORAGE — _impl() functions ====================


def _list_pending_edits_impl(
    id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[QuotePendingEditResponse]:
    """Shared logic for listing pending edits for the current user on a quote."""
    quote = db.exec(
        select(Quote)
        .where(Quote.id == id)
        .where(Quote.tenant_id == user_context.tenant_id)
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    edits = db.exec(
        select(QuotePendingEdit)
        .where(
            QuotePendingEdit.quote_id == id,
            QuotePendingEdit.editor_user_id == user_context.id,
        )
        .order_by(QuotePendingEdit.created_at)
    ).all()
    return [QuotePendingEditResponse.model_validate(e) for e in edits]


def _create_pending_edit_impl(
    id: UUID,
    payload: QuotePendingEditCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuotePendingEditResponse:
    """Shared logic for creating a pending edit on a quote."""
    quote = db.exec(
        select(Quote)
        .where(Quote.id == id)
        .where(Quote.tenant_id == user_context.tenant_id)
        .where(Quote.is_active == True)
    ).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    valid_types = {"modify_line", "add_line", "delete_line", "edit_notes"}
    if payload.edit_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "validation",
                "detail": f"edit_type must be one of {valid_types}",
            },
        )

    latest_version = db.exec(
        select(QuoteVersion)
        .where(QuoteVersion.quote_id == id)
        .where(QuoteVersion.tenant_id == user_context.tenant_id)
        .order_by(QuoteVersion.version_no.desc())
    ).first()
    if not latest_version:
        raise HTTPException(status_code=422, detail="Quote has no versions yet")

    edit = QuotePendingEdit(
        tenant_id=user_context.tenant_id,
        quote_id=id,
        quote_version_id=latest_version.id,
        editor_user_id=user_context.id,
        edit_type=payload.edit_type,
        target_line_id=payload.target_line_id,
        edit_payload=payload.edit_payload,
        annotation=payload.annotation,
        created_by=user_context.id,
        updated_by=user_context.id,
    )
    db.add(edit)
    db.commit()
    db.refresh(edit)
    return QuotePendingEditResponse.model_validate(edit)


def _update_pending_edit_impl(
    id: UUID,
    edit_id: UUID,
    payload: QuotePendingEditUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> QuotePendingEditResponse:
    """Shared logic for updating a pending edit."""
    edit = db.exec(
        select(QuotePendingEdit).where(
            QuotePendingEdit.id == edit_id,
            QuotePendingEdit.quote_id == id,
            QuotePendingEdit.editor_user_id == user_context.id,
        )
    ).first()
    if not edit:
        raise HTTPException(status_code=404, detail="Pending edit not found")

    if payload.edit_payload is not None:
        edit.edit_payload = payload.edit_payload
    if payload.annotation is not None:
        edit.annotation = payload.annotation
    edit.updated_by = user_context.id
    db.add(edit)
    db.commit()
    db.refresh(edit)
    return QuotePendingEditResponse.model_validate(edit)


def _delete_pending_edit_impl(
    id: UUID,
    edit_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """Shared logic for deleting a single pending edit."""
    edit = db.exec(
        select(QuotePendingEdit).where(
            QuotePendingEdit.id == edit_id,
            QuotePendingEdit.quote_id == id,
            QuotePendingEdit.editor_user_id == user_context.id,
        )
    ).first()
    if not edit:
        raise HTTPException(status_code=404, detail="Pending edit not found")

    db.delete(edit)
    db.commit()
    return {"deleted": True}


def _delete_all_pending_edits_impl(
    id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> dict:
    """Shared logic for deleting all pending edits for the current user on a quote."""
    edits = db.exec(
        select(QuotePendingEdit).where(
            QuotePendingEdit.quote_id == id,
            QuotePendingEdit.editor_user_id == user_context.id,
        )
    ).all()
    count = len(edits)
    for e in edits:
        db.delete(e)
    db.commit()
    return {"deleted_count": count}


# ==================== A29: PENDING EDIT STORAGE — TEST ENDPOINTS (register BEFORE authenticated) ====================
# ROUTE ORDERING NOTE: DELETE /test (delete-all) MUST be registered before DELETE /{edit_id}/test
# to prevent {edit_id} matching the literal string "test".


@router.get(
    "/{id}/pending-edits/test",
    response_model=list[QuotePendingEditResponse],
    summary="List pending edits for a quote (TEST — no auth)",
    tags=["quotes"],
)
def list_pending_edits_test(
    id: UUID,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _list_pending_edits_impl(id, db, test_context)


@router.post(
    "/{id}/pending-edits/test",
    response_model=QuotePendingEditResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pending edit (TEST — no auth)",
    tags=["quotes"],
)
def create_pending_edit_test(
    id: UUID,
    payload: QuotePendingEditCreate,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _create_pending_edit_impl(id, payload, db, test_context)


@router.patch(
    "/{id}/pending-edits/{edit_id}/test",
    response_model=QuotePendingEditResponse,
    summary="Update a pending edit (TEST — no auth)",
    tags=["quotes"],
)
def update_pending_edit_test(
    id: UUID,
    edit_id: UUID,
    payload: QuotePendingEditUpdate,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _update_pending_edit_impl(id, edit_id, payload, db, test_context)


# DELETE /test (delete-all) registered BEFORE DELETE /{edit_id}/test — critical ordering
@router.delete(
    "/{id}/pending-edits/test",
    summary="Delete all pending edits for current user on this quote (TEST — no auth)",
    tags=["quotes"],
)
def delete_all_pending_edits_test(
    id: UUID,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _delete_all_pending_edits_impl(id, db, test_context)


@router.delete(
    "/{id}/pending-edits/{edit_id}/test",
    summary="Delete a single pending edit (TEST — no auth)",
    tags=["quotes"],
)
def delete_pending_edit_test(
    id: UUID,
    edit_id: UUID,
    db: Session = Depends(get_db),
):
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _delete_pending_edit_impl(id, edit_id, db, test_context)


# ==================== A29: PENDING EDIT STORAGE — AUTHENTICATED ENDPOINTS ====================


@router.get(
    "/{id}/pending-edits",
    response_model=list[QuotePendingEditResponse],
    summary="List pending edits for a quote",
    tags=["quotes"],
)
def list_pending_edits(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quote.approve")),
):
    """A29: List all pending edits for the current user on this quote."""
    return _list_pending_edits_impl(id, db, current_user)


@router.post(
    "/{id}/pending-edits",
    response_model=QuotePendingEditResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pending edit",
    tags=["quotes"],
)
def create_pending_edit(
    id: UUID,
    payload: QuotePendingEditCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quote.approve")),
):
    """A29: Add a proposed edit while reviewing a pending_approval quote."""
    return _create_pending_edit_impl(id, payload, db, current_user)


@router.patch(
    "/{id}/pending-edits/{edit_id}",
    response_model=QuotePendingEditResponse,
    summary="Update a pending edit",
    tags=["quotes"],
)
def update_pending_edit(
    id: UUID,
    edit_id: UUID,
    payload: QuotePendingEditUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quote.approve")),
):
    """A29: Update an existing pending edit (only by the same editor)."""
    return _update_pending_edit_impl(id, edit_id, payload, db, current_user)


@router.delete(
    "/{id}/pending-edits/{edit_id}",
    summary="Delete a single pending edit",
    tags=["quotes"],
)
def delete_pending_edit(
    id: UUID,
    edit_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quote.approve")),
):
    """A29: Delete a single pending edit (only by the same editor)."""
    return _delete_pending_edit_impl(id, edit_id, db, current_user)


@router.delete(
    "/{id}/pending-edits",
    summary="Delete all pending edits for current user on this quote",
    tags=["quotes"],
)
def delete_all_pending_edits(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quote.approve")),
):
    """A29: Delete all pending edits the current user has on this quote."""
    return _delete_all_pending_edits_impl(id, db, current_user)


# ==================== A30: APPROVAL COMMENTS + KICKBACK ====================


@router.get(
    "/{id}/comments",
    response_model=list[QuoteApprovalCommentResponse],
    summary="Get all approval comments for a quote",
    tags=["quotes"],
)
def get_quote_comments(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
):
    """A30: Return all quote_approval_comment rows for this quote, ordered created_at DESC."""
    return _get_quote_comments_impl(id, db, current_user)


@router.post(
    "/{id}/kickback",
    response_model=QuoteKickbackResponse,
    summary="Kick back a pending_approval quote to draft",
    tags=["quotes"],
)
def kickback_quote(
    id: UUID,
    payload: QuoteKickbackRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quote.approve")),
):
    """
    A30: Kick back a pending_approval quote to draft status.

    - Requires at least one of overall_comment or line_comments.
    - Creates quote_approval_comment rows (type=kickback).
    - Transitions quote → draft.
    RBAC: quote.approve (owner, accountant).
    """
    return _kickback_quote_impl(id, payload, db, current_user)


# ─────────────────────────────────────────────────────────────────────────────
# B15/A80 — Revoke Quote Public Link
# POST /{quote_id}/public-link/revoke
# ─────────────────────────────────────────────────────────────────────────────


# FIND-162: Add response_model=QuoteRevokeLinkResponse + typed return
@router.post("/{quote_id}/public-link/revoke", response_model=QuoteRevokeLinkResponse)
def revoke_quote_public_link(
    quote_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.update")),
):
    """
    Revoke the active public link for a quote.
    Sets revoked_at timestamp on the QuotePublicLink row.
    RBAC: quotes.update (owner/accountant).
    Returns: {"revoked_at": "ISO-datetime-string"}
    """
    return _revoke_quote_public_link_impl(quote_id, db, current_user)
