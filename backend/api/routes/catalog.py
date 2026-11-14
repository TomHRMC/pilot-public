import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, func, or_, select, text

from api.schemas.schemas import (
    PaginatedCatalogResponse,
    PricebookItemCreate,
    PricebookItemCurrentPriceResponse,
    PricebookItemPatch,
    PricebookItemPriceCreate,
    PricebookItemResponse,
    PricingCacheResponse,
    SupplierItemCreate,
    SupplierItemResponse,
)
from app.models.catalog import PricingCache, SupplierItem
from app.models.quoting import PricebookItem, PricebookItemVersion
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.onboarding_service import mark_catalog_setup

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== SHARED BUSINESS LOGIC ====================


def _create_supplier_item_impl(
    item_in: SupplierItemCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> SupplierItem:
    """
    Shared supplier item creation logic used by both authenticated and test endpoints.

    Args:
        item_in: Supplier item data to create
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        Created SupplierItem instance

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    item = SupplierItem(
        tenant_id=user_context.tenant_id,
        supplier_id=item_in.supplier_id,
        sku=item_in.sku,
        name=item_in.name,
        description=item_in.description,
        uom_id=item_in.uom_id,
        category_id=item_in.category_id,
        taxability_code=item_in.taxability_code,
    )

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _list_supplier_items_impl(
    skip: int,
    limit: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[SupplierItem]:
    """
    Shared supplier item listing logic used by both authenticated and test endpoints.

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session
        user_context: Either authenticated User or TestUserContext

    Returns:
        List of SupplierItem instances for the tenant

    Note:
        This function works for both authenticated and test endpoints because
        TestUserContext provides tenant_id attribute (User model lacks this - Gap #40).
    """
    statement = (
        select(SupplierItem)
        .where(SupplierItem.tenant_id == user_context.tenant_id)
        .offset(skip)
        .limit(limit)
    )
    items = db.exec(statement).all()
    return items


def _get_pricing_cache_impl(
    sku: str | None,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[PricingCache]:
    """
    Shared pricing cache retrieval logic used by both authenticated and test endpoints.

    Args:
        sku: Optional SKU filter
        db: Database session
        user_context: Either authenticated User or TestUserContext (unused but kept for consistency)

    Returns:
        List of PricingCache instances

    Note:
        PricingCache rows with tenant_id IS NULL are global/shared prices accessible to
        all tenants (distributor list price). Rows with tenant_id = UUID are private
        negotiated prices for that tenant only. Both are returned for the requesting
        tenant, ordered with tenant-specific prices first (NULLS LAST) so the frontend
        can use the first match per SKU as the "best price".

        FIND-054 (S1 IDOR fix): filter must always be applied — returning all tenants'
        private prices was an IDOR vulnerability.
    """
    statement = (
        select(PricingCache)
        .where(
            or_(
                PricingCache.tenant_id.is_(None),  # type: ignore[union-attr]
                PricingCache.tenant_id == user_context.tenant_id,
            )
        )
        .order_by(PricingCache.tenant_id.nulls_last())
    )  # type: ignore[union-attr]
    if sku:
        statement = statement.where(PricingCache.sku == sku)

    items = db.exec(statement).all()
    return items


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post(
    "/supplier-items",
    response_model=SupplierItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_supplier_item(
    item_in: SupplierItemCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.create")),
):
    """
    Create a new supplier catalog item (requires JWT authentication and catalog.create permission).

    Security:
        - Requires valid JWT token
        - Requires catalog.create permission (owner / office_staff)
        - Item created in authenticated user's tenant

    Returns:
        SupplierItemResponse with created item data
    """
    return _create_supplier_item_impl(item_in, db, current_user)


@router.get("/supplier-items", response_model=list[SupplierItemResponse])
def list_supplier_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.view")),
):
    """
    List supplier catalog items (requires JWT authentication and catalog.view permission).

    Security:
        - Requires valid JWT token
        - Requires catalog.view permission
        - Returns only items in authenticated user's tenant

    Returns:
        List of SupplierItemResponse objects
    """
    return _list_supplier_items_impl(skip, limit, db, current_user)


@router.get("/pricing-cache", response_model=list[PricingCacheResponse])
def get_pricing_cache(
    sku: str | None = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.view")),
):
    """
    Get pricing cache data (requires JWT authentication and catalog.view permission).

    Security:
        - Requires valid JWT token
        - Requires catalog.view permission
        - Pricing cache is tenant-scoped (tenant_id IS NULL OR tenant_id = current tenant)

    Returns:
        List of PricingCacheResponse objects
    """
    return _get_pricing_cache_impl(sku, db, current_user)


# ==================== TEST ENDPOINTS (UNAUTHENTICATED) ====================


@router.post(
    "/supplier-items/test",
    response_model=SupplierItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_supplier_item_test(
    item_in: SupplierItemCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new supplier catalog item (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses hardcoded test tenant: 00000000-0000-0000-0000-000000000001
        - Uses hardcoded test user: 00000000-0000-0000-0000-000000000002

    Usage:
        curl -X POST http://localhost:8000/api/v1/catalog/supplier-items/test \\
          -H "Content-Type: application/json" \\
          -d '{"supplier_id": "...", "sku": "ABC123", "name": "Wire 12/2", ...}'

    Returns:
        SupplierItemResponse with created item data
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _create_supplier_item_impl(item_in, db, test_context)


@router.get("/supplier-items/test", response_model=list[SupplierItemResponse])
def list_supplier_items_test(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List supplier catalog items (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Returns items from test tenant only: 00000000-0000-0000-0000-000000000001

    Usage:
        curl http://localhost:8000/api/v1/catalog/supplier-items/test

    Returns:
        List of SupplierItemResponse objects from test tenant
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _list_supplier_items_impl(skip, limit, db, test_context)


@router.get("/pricing-cache/test", response_model=list[PricingCacheResponse])
def get_pricing_cache_test(
    sku: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Get pricing cache data (TEST ENDPOINT - no authentication required).

    Security:
        - Only available when TEST_ENDPOINT_ENABLED=true
        - Only available in DEV/QA environments (blocked in staging/production)
        - Returns HTTP 403 if disabled

    Test Context:
        - Uses test tenant: 00000000-0000-0000-0000-000000000001

    Note:
        Returns global rows plus this tenant's rows only

    Usage:
        curl http://localhost:8000/api/v1/catalog/pricing-cache/test

    Returns:
        List of PricingCacheResponse objects
    """
    test_context = get_test_context()  # Raises 403 if disabled
    return _get_pricing_cache_impl(sku, db, test_context)


# ============================================================================
# FIND-171: Pricebook Item CRUD + Temporal Price Management
# ============================================================================


def _parse_tstzrange_bounds(valid_period) -> tuple:
    """Extract lower and upper datetime bounds from a psycopg2 DateTimeTZRange object."""
    if valid_period is None:
        return None, None
    return valid_period.lower, valid_period.upper


def _build_current_price_response(
    version: PricebookItemVersion,
) -> PricebookItemCurrentPriceResponse:
    """Convert a PricebookItemVersion row to PricebookItemCurrentPriceResponse."""
    lower, upper = _parse_tstzrange_bounds(version.valid_period)
    return PricebookItemCurrentPriceResponse(
        id=version.id,
        default_unit_price_cents=version.default_unit_price_cents,
        valid_period_lower=lower,
        valid_period_upper=upper,
        recorded_at=version.recorded_at,
    )


def _get_current_price(
    db: Session, tenant_id: UUID, item_id: UUID
) -> PricebookItemCurrentPriceResponse | None:
    """
    Fetch the current active price version for a pricebook item.

    Uses func.now().op("<@") temporal containment operator to find the version
    whose valid_period contains the current moment (same pattern as labor_rates.py).
    Returns None if no current version exists.
    """
    row = db.exec(
        select(PricebookItemVersion)
        .where(PricebookItemVersion.tenant_id == tenant_id)
        .where(PricebookItemVersion.pricebook_item_id == item_id)
        .where(func.now().op("<@")(PricebookItemVersion.valid_period))
        .order_by(PricebookItemVersion.id.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    return _build_current_price_response(row)


def _build_pricebook_item_response(
    item: PricebookItem, db: Session
) -> PricebookItemResponse:
    """Build PricebookItemResponse with current_price populated."""
    current_price = _get_current_price(db, item.tenant_id, item.id)
    return PricebookItemResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        sku=item.sku,
        name=item.name,
        description=item.description,
        uom_id=item.uom_id,
        taxability_code=item.taxability_code,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
        created_by=item.created_by,
        updated_by=item.updated_by,
        current_price=current_price,
    )


# ==================== PRICEBOOK SHARED _impl() FUNCTIONS ====================


def _list_pricebook_items_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    skip: int = 0,
    limit: int = 25,
    is_active: bool = True,
    search: str | None = None,
    offset: int = 0,
) -> PaginatedCatalogResponse:
    """Shared logic for listing pricebook items.

    UI-FIX-1C: Returns PaginatedCatalogResponse with total count.
    Adds optional search param across name, description, sku.
    """
    from sqlalchemy import func as sqla_func

    effective_offset = offset if offset > 0 else skip

    base_stmt = (
        select(PricebookItem)
        .where(PricebookItem.tenant_id == user_context.tenant_id)
        .where(PricebookItem.is_active == is_active)
    )

    if search:
        q = f"%{search}%"
        base_stmt = base_stmt.where(
            or_(
                PricebookItem.name.ilike(q),
                PricebookItem.description.ilike(q),
                PricebookItem.sku.ilike(q),
            )
        )

    count_stmt = (
        select(sqla_func.count(PricebookItem.id))
        .where(PricebookItem.tenant_id == user_context.tenant_id)
        .where(PricebookItem.is_active == is_active)
    )
    if search:
        q = f"%{search}%"
        count_stmt = count_stmt.where(
            or_(
                PricebookItem.name.ilike(q),
                PricebookItem.description.ilike(q),
                PricebookItem.sku.ilike(q),
            )
        )

    total = db.exec(count_stmt).one()
    items = db.exec(base_stmt.offset(effective_offset).limit(limit)).all()
    item_responses = [_build_pricebook_item_response(item, db) for item in items]

    return PaginatedCatalogResponse(
        items=item_responses,
        total=total,
        limit=limit,
        offset=effective_offset,
    )


def _create_pricebook_item_impl(
    item_in: PricebookItemCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PricebookItemResponse:
    """Shared logic for creating a pricebook item with initial price."""
    effective_from = item_in.effective_from or datetime.now(UTC)

    try:
        item = PricebookItem(
            tenant_id=user_context.tenant_id,
            sku=item_in.sku,
            name=item_in.name,
            description=item_in.description,
            uom_id=item_in.uom_id,
            taxability_code=item_in.taxability_code,
            is_active=True,
            created_by=user_context.id,
            updated_by=user_context.id,
        )
        db.add(item)
        db.flush()

        db.execute(
            text(
                "INSERT INTO pricebook_item_version "
                "(tenant_id, pricebook_item_id, default_unit_price_cents, valid_period, created_by, created_at) "
                "VALUES (:tenant_id, :item_id, :price_cents, tstzrange(:lower, null, '[)'), :created_by, :created_at)"
            ).bindparams(
                tenant_id=user_context.tenant_id,
                item_id=item.id,
                price_cents=item_in.initial_price_cents,
                lower=effective_from,
                created_by=user_context.id,
                created_at=datetime.now(UTC),
            )
        )
        db.commit()
        db.refresh(item)

        # FIX4-BE-01 (PLP-FIX-6): advance onboarding checklist — never fail the create
        try:
            mark_catalog_setup(db, user_context.tenant_id)
        except Exception:
            logger.warning(
                "mark_catalog_setup failed for tenant %s",
                user_context.tenant_id,
                exc_info=True,
            )

        return _build_pricebook_item_response(item, db)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        error_str = str(e)
        if "uq_pricebook_item_tenant_sku" in error_str or "23505" in error_str:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "https://pilotfortrades.com/errors/conflict",
                    "title": "Duplicate SKU",
                    "status": 409,
                    "detail": f"A pricebook item with SKU '{item_in.sku}' already exists for this tenant.",
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


def _get_pricebook_item_impl(
    item_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PricebookItemResponse:
    """Shared logic for getting a single pricebook item."""
    item = db.exec(
        select(PricebookItem)
        .where(PricebookItem.id == item_id)
        .where(PricebookItem.tenant_id == user_context.tenant_id)
    ).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://pilotfortrades.com/errors/not-found",
                "title": "Pricebook Item Not Found",
                "status": 404,
                "detail": f"Pricebook item {item_id} not found.",
            },
        )
    return _build_pricebook_item_response(item, db)


def _patch_pricebook_item_impl(
    item_id: UUID,
    patch_in: PricebookItemPatch,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PricebookItemResponse:
    """Shared logic for patching pricebook item metadata."""
    item = db.exec(
        select(PricebookItem)
        .where(PricebookItem.id == item_id)
        .where(PricebookItem.tenant_id == user_context.tenant_id)
    ).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://pilotfortrades.com/errors/not-found",
                "title": "Pricebook Item Not Found",
                "status": 404,
                "detail": f"Pricebook item {item_id} not found.",
            },
        )

    patch_data = patch_in.model_dump(exclude_unset=True)
    for field, value in patch_data.items():
        setattr(item, field, value)
    item.updated_by = user_context.id

    db.add(item)
    db.commit()
    db.refresh(item)
    return _build_pricebook_item_response(item, db)


def _create_pricebook_item_price_impl(
    item_id: UUID,
    price_in: PricebookItemPriceCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PricebookItemCurrentPriceResponse:
    """Shared logic for setting a new price via temporal supersession."""
    item = db.exec(
        select(PricebookItem)
        .where(PricebookItem.id == item_id)
        .where(PricebookItem.tenant_id == user_context.tenant_id)
    ).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://pilotfortrades.com/errors/not-found",
                "title": "Pricebook Item Not Found",
                "status": 404,
                "detail": f"Pricebook item {item_id} not found.",
            },
        )

    effective_from = price_in.effective_from

    try:
        current_version = db.exec(
            select(PricebookItemVersion)
            .where(PricebookItemVersion.pricebook_item_id == item_id)
            .where(PricebookItemVersion.tenant_id == user_context.tenant_id)
            .order_by(PricebookItemVersion.id.desc())
        ).first()

        if current_version is not None:
            db.execute(
                text(
                    "UPDATE pricebook_item_version "
                    "SET valid_period = tstzrange(lower(valid_period), :effective_from, '[)') "
                    "WHERE id = :version_id "
                    "AND tenant_id = :tenant_id"
                ).bindparams(
                    effective_from=effective_from,
                    version_id=current_version.id,
                    tenant_id=user_context.tenant_id,
                )
            )

        db.execute(
            text(
                "INSERT INTO pricebook_item_version "
                "(tenant_id, pricebook_item_id, default_unit_price_cents, valid_period, created_by, created_at) "
                "VALUES (:tenant_id, :item_id, :price_cents, tstzrange(:lower, null, '[)'), :created_by, :created_at)"
            ).bindparams(
                tenant_id=user_context.tenant_id,
                item_id=item_id,
                price_cents=price_in.unit_price_cents,
                lower=effective_from,
                created_by=user_context.id,
                created_at=datetime.now(UTC),
            )
        )
        db.commit()

        new_version = db.exec(
            select(PricebookItemVersion)
            .where(PricebookItemVersion.pricebook_item_id == item_id)
            .where(PricebookItemVersion.tenant_id == user_context.tenant_id)
            .order_by(PricebookItemVersion.id.desc())
        ).first()

        return _build_current_price_response(new_version)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        error_str = str(e)
        if (
            "piv_no_overlap" in error_str
            or "23P01" in error_str
            or "exclusion" in error_str.lower()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "https://pilotfortrades.com/errors/conflict",
                    "title": "Overlapping Price Period",
                    "status": 409,
                    "detail": "The effective_from date overlaps with an existing price version. "
                    "Cannot create overlapping temporal price periods.",
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


def _get_pricebook_item_price_history_impl(
    item_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[PricebookItemCurrentPriceResponse]:
    """Shared logic for getting price history of a pricebook item."""
    item = db.exec(
        select(PricebookItem)
        .where(PricebookItem.id == item_id)
        .where(PricebookItem.tenant_id == user_context.tenant_id)
    ).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://pilotfortrades.com/errors/not-found",
                "title": "Pricebook Item Not Found",
                "status": 404,
                "detail": f"Pricebook item {item_id} not found.",
            },
        )

    versions = db.exec(
        select(PricebookItemVersion)
        .where(PricebookItemVersion.pricebook_item_id == item_id)
        .where(PricebookItemVersion.tenant_id == user_context.tenant_id)
        .order_by(PricebookItemVersion.id.desc())
    ).all()

    return [_build_current_price_response(v) for v in versions]


# ==================== PRICEBOOK TEST ENDPOINTS (register BEFORE authenticated) ====================
# Route ordering: /pricebook/test and /pricebook/{item_id}/price-history/test
# and /pricebook/{item_id}/price/test must come before /pricebook/{item_id}


@router.get(
    "/pricebook/test",
    response_model=PaginatedCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="List pricebook items (TEST — no auth)",
    tags=["Pricebook"],
)
def list_pricebook_items_test(
    skip: int = 0,
    limit: int = 25,
    offset: int = 0,
    is_active: bool = True,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> PaginatedCatalogResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _list_pricebook_items_impl(
        db,
        test_context,
        skip=skip,
        limit=limit,
        is_active=is_active,
        search=search,
        offset=offset,
    )


@router.post(
    "/pricebook/test",
    response_model=PricebookItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pricebook item (TEST — no auth)",
    tags=["Pricebook"],
)
def create_pricebook_item_test(
    item_in: PricebookItemCreate,
    db: Session = Depends(get_db),
) -> PricebookItemResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _create_pricebook_item_impl(item_in, db, test_context)


@router.get(
    "/pricebook/{item_id}/test",
    response_model=PricebookItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single pricebook item (TEST — no auth)",
    tags=["Pricebook"],
)
def get_pricebook_item_test(
    item_id: UUID,
    db: Session = Depends(get_db),
) -> PricebookItemResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_pricebook_item_impl(item_id, db, test_context)


@router.patch(
    "/pricebook/{item_id}/test",
    response_model=PricebookItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Update pricebook item metadata (TEST — no auth)",
    tags=["Pricebook"],
)
def patch_pricebook_item_test(
    item_id: UUID,
    patch_in: PricebookItemPatch,
    db: Session = Depends(get_db),
) -> PricebookItemResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _patch_pricebook_item_impl(item_id, patch_in, db, test_context)


@router.post(
    "/pricebook/{item_id}/price/test",
    response_model=PricebookItemCurrentPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set a new price via temporal supersession (TEST — no auth)",
    tags=["Pricebook"],
)
def create_pricebook_item_price_test(
    item_id: UUID,
    price_in: PricebookItemPriceCreate,
    db: Session = Depends(get_db),
) -> PricebookItemCurrentPriceResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _create_pricebook_item_price_impl(item_id, price_in, db, test_context)


@router.get(
    "/pricebook/{item_id}/price-history/test",
    response_model=list[PricebookItemCurrentPriceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get price history for a pricebook item (TEST — no auth)",
    tags=["Pricebook"],
)
def get_pricebook_item_price_history_test(
    item_id: UUID,
    db: Session = Depends(get_db),
) -> list[PricebookItemCurrentPriceResponse]:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_pricebook_item_price_history_impl(item_id, db, test_context)


# ==================== PRICEBOOK AUTHENTICATED ENDPOINTS ====================


@router.get(
    "/pricebook",
    response_model=PaginatedCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="List pricebook items",
    tags=["Pricebook"],
)
def list_pricebook_items(
    skip: int = 0,
    limit: int = 25,
    offset: int = 0,
    is_active: bool = True,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> PaginatedCatalogResponse:
    """List pricebook items. RBAC: catalog.manage. UI-FIX-1C: returns PaginatedCatalogResponse."""
    return _list_pricebook_items_impl(
        db,
        current_user,
        skip=skip,
        limit=limit,
        is_active=is_active,
        search=search,
        offset=offset,
    )


@router.post(
    "/pricebook",
    response_model=PricebookItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pricebook item with initial price",
    tags=["Pricebook"],
)
def create_pricebook_item(
    item_in: PricebookItemCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> PricebookItemResponse:
    """Create a new pricebook item. RBAC: catalog.manage."""
    return _create_pricebook_item_impl(item_in, db, current_user)


@router.get(
    "/pricebook/{item_id}",
    response_model=PricebookItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single pricebook item",
    tags=["Pricebook"],
)
def get_pricebook_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> PricebookItemResponse:
    """Get a single pricebook item. RBAC: catalog.manage."""
    return _get_pricebook_item_impl(item_id, db, current_user)


@router.patch(
    "/pricebook/{item_id}",
    response_model=PricebookItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Update pricebook item metadata",
    tags=["Pricebook"],
)
def patch_pricebook_item(
    item_id: UUID,
    patch_in: PricebookItemPatch,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> PricebookItemResponse:
    """Update pricebook item metadata. RBAC: catalog.manage."""
    return _patch_pricebook_item_impl(item_id, patch_in, db, current_user)


@router.post(
    "/pricebook/{item_id}/price",
    response_model=PricebookItemCurrentPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set a new price via temporal supersession",
    tags=["Pricebook"],
)
def create_pricebook_item_price(
    item_id: UUID,
    price_in: PricebookItemPriceCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> PricebookItemCurrentPriceResponse:
    """Set a new price via temporal supersession. RBAC: catalog.manage."""
    return _create_pricebook_item_price_impl(item_id, price_in, db, current_user)


@router.get(
    "/pricebook/{item_id}/price-history",
    response_model=list[PricebookItemCurrentPriceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get price history for a pricebook item",
    tags=["Pricebook"],
)
def get_pricebook_item_price_history(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> list[PricebookItemCurrentPriceResponse]:
    """Get price history for a pricebook item. RBAC: catalog.manage."""
    return _get_pricebook_item_price_history_impl(item_id, db, current_user)
