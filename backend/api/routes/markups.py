"""
Category-Specific Markup Management Endpoints (A90 / FIND-055)

This module provides REST endpoints for managing tenant-specific markup rates per expense category.
Implements temporal versioning via the TenantMarkupVersion table using GIST exclusion constraints
to prevent overlapping validity periods.

Endpoints:
  - GET  /api/v1/settings/markups                           (list active markups)
  - POST /api/v1/settings/markups                           (temporal supersession)
  - GET  /api/v1/settings/markups/{category_code}/history   (audit trail)

Test endpoints (same signatures, no auth):
  - GET  /api/v1/settings/markups/test
  - POST /api/v1/settings/markups/test
  - GET  /api/v1/settings/markups/{category_code}/history/test

Pattern: Append-only with supersession via UPDATE + INSERT in one transaction.
GIST constraint enforces: exactly one active (valid_period @> now()) row per (tenant_id, category_code).
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, text

from api.schemas.schemas import (
    TenantMarkupVersionCreate,
    TenantMarkupVersionHistoryResponse,
    TenantMarkupVersionListResponse,
    TenantMarkupVersionResponse,
)
from app.models.catalog import TenantMarkupVersion
from app.models.fulfillment import JobExpenseCategory
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ==================== SHARED BUSINESS LOGIC ====================


def _parse_tstzrange(valid_period) -> tuple[datetime, datetime | None]:
    """
    Extract lower and upper bounds from a PostgreSQL tstzrange object.

    Args:
        valid_period: psycopg2.extras.DateTimeTZRange object from the ORM

    Returns:
        Tuple of (lower_bound: datetime, upper_bound: Optional[datetime])
        upper_bound is None if the range is open (infinite upper bound)
    """
    if valid_period is None:
        return None, None
    return valid_period.lower, valid_period.upper


def _get_active_markups_impl(
    tenant_id: UUID,
    db: Session,
) -> list[TenantMarkupVersion]:
    """
    Retrieve all active markup versions for the tenant (valid_period @> now()).

    Args:
        tenant_id: Tenant UUID
        db: Database session

    Returns:
        List of active TenantMarkupVersion rows for this tenant
    """
    now = datetime.now(UTC)
    rows = db.exec(
        select(TenantMarkupVersion)
        .where(TenantMarkupVersion.tenant_id == tenant_id)
        .where(text("valid_period @> cast(:now as timestamptz)").bindparams(now=now))
        .order_by(TenantMarkupVersion.job_expense_category_code)
    ).all()
    return rows


def _get_category_history_impl(
    category_code: str,
    tenant_id: UUID,
    db: Session,
) -> list[TenantMarkupVersion]:
    """
    Retrieve all historical versions of a markup for a category (audit trail).

    Args:
        category_code: Job expense category code
        tenant_id: Tenant UUID
        db: Database session

    Returns:
        List of all TenantMarkupVersion rows for this category, sorted by recorded_at DESC
    """
    rows = db.exec(
        select(TenantMarkupVersion)
        .where(TenantMarkupVersion.tenant_id == tenant_id)
        .where(TenantMarkupVersion.job_expense_category_code == category_code)
        .order_by(TenantMarkupVersion.recorded_at.desc())
    ).all()
    return rows


def _create_markup_supersession_impl(
    payload: TenantMarkupVersionCreate,
    tenant_id: UUID,
    user_id: UUID | None,
    db: Session,
) -> TenantMarkupVersion:
    """
    Temporal supersession: atomically close the current active markup row for a category
    and insert a new row in a single transaction.

    Implements the pattern:
    1. Find current active row (valid_period @> now())
    2. If exists: UPDATE its valid_period upper bound to effective_from to close it
    3. INSERT new row with valid_period = [effective_from, ∞)
    4. GIST exclusion constraint validates no overlap → IntegrityError on collision

    Args:
        payload: TenantMarkupVersionCreate with new markup data
        tenant_id: Tenant UUID
        user_id: User ID of the person making the change (created_by)
        db: Database session

    Returns:
        New TenantMarkupVersion row created by this supersession

    Raises:
        HTTPException 404: job_expense_category_code does not exist
        HTTPException 409: Overlap violation (GIST constraint) or effective_from == current lower bound
    """

    # Validate category exists
    category_exists = db.exec(
        select(JobExpenseCategory).where(
            JobExpenseCategory.code == payload.job_expense_category_code
        )
    ).first()

    if not category_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job expense category '{payload.job_expense_category_code}' not found",
        )

    # Find current active row for this (tenant_id, category_code)
    now = datetime.now(UTC)
    current = db.exec(
        select(TenantMarkupVersion)
        .where(TenantMarkupVersion.tenant_id == tenant_id)
        .where(
            TenantMarkupVersion.job_expense_category_code
            == payload.job_expense_category_code
        )
        .where(text("valid_period @> cast(:now as timestamptz)").bindparams(now=now))
    ).first()

    # Step 1: If current active row exists, check if effective_from equals its lower bound
    # (which would result in an empty range [lower, lower) and violate CHECK constraint)
    if current:
        current_lower = current.valid_period.lower
        if payload.effective_from == current_lower:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="effective_from cannot equal the current version's start date",
            )

        # Step 2: Close the current row by updating its upper bound
        db.execute(
            text(
                "UPDATE tenant_markup_version "
                "SET valid_period = tstzrange(lower(valid_period), :upper, '[)') "
                "WHERE id = :id"
            ).bindparams(upper=payload.effective_from, id=current.id)
        )

    # Step 3: Create new row with open upper bound [effective_from, ∞)
    new_row = TenantMarkupVersion(
        tenant_id=tenant_id,
        job_expense_category_code=payload.job_expense_category_code,
        markup_pct=payload.markup_pct,
        markup_amt_cents=payload.markup_amt_cents,
        valid_period=None,  # ORM will use server_default: tstzrange(now(), NULL, '[)')
        created_by=user_id,
    )

    # Manually set valid_period using raw SQL to control the exact range
    db.add(new_row)
    db.flush()  # Flush to get the ID, but don't commit yet

    # Now update the valid_period we just inserted to the correct effective_from
    db.execute(
        text(
            "UPDATE tenant_markup_version "
            "SET valid_period = tstzrange(:lower, null, '[)') "
            "WHERE id = :id"
        ).bindparams(lower=payload.effective_from, id=new_row.id)
    )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # Check if it's a GIST overlap violation
        if "tmv_no_overlap" in str(e) or "exclusion" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Markup period overlaps with existing row; temporal supersession not allowed",
            )
        raise

    db.refresh(new_row)
    return new_row


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.get(
    "/markups",
    response_model=TenantMarkupVersionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Active Category Markups",
    tags=["settings"],
)
def get_active_markups(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> TenantMarkupVersionListResponse:
    """
    List all currently active markup versions for the tenant's expense categories.

    Filters by `valid_period @> now()` — only rows where the current timestamp falls
    within the validity period are returned.

    **RBAC**: Requires `catalog.manage` permission (owner/accountant only).

    **Response**: List of active markups, one per category, with period bounds and rates.
    """
    rows = _get_active_markups_impl(current_user.tenant_id, db)
    items = [
        TenantMarkupVersionResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            job_expense_category_code=row.job_expense_category_code,
            markup_pct=float(row.markup_pct),
            markup_amt_cents=row.markup_amt_cents,
            valid_period_lower=row.valid_period.lower,
            valid_period_upper=row.valid_period.upper,
            recorded_at=row.recorded_at,
            created_by=row.created_by,
        )
        for row in rows
    ]
    return TenantMarkupVersionListResponse(items=items, total=len(items))


@router.post(
    "/markups",
    response_model=TenantMarkupVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create/Update Markup via Temporal Supersession",
    tags=["settings"],
)
def create_markup_supersession(
    payload: TenantMarkupVersionCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> TenantMarkupVersionResponse:
    """
    Temporal supersession: atomically close the current active markup for a category
    and create a new one effective at `effective_from`.

    **Supersession logic**:
    1. Find the current active row (valid_period @> now()) for this category
    2. If found: UPDATE its upper bound to `effective_from` to close it
    3. INSERT new row with valid_period = [effective_from, ∞)
    4. GIST exclusion constraint validates no overlap

    **RBAC**: Requires `catalog.manage` permission (owner/accountant only).

    **Validation**:
    - `markup_pct >= 0`
    - `effective_from` must be timezone-aware (UTC)
    - `effective_from` cannot be more than 90 days in the past (prevents accidental backdating)
    - `job_expense_category_code` must exist in job_expense_category table

    **Response**: HTTP 201 with the new TenantMarkupVersionResponse; HTTP 409 on overlap/collision.
    """
    new_row = _create_markup_supersession_impl(
        payload, current_user.tenant_id, current_user.id, db
    )
    return TenantMarkupVersionResponse(
        id=new_row.id,
        tenant_id=new_row.tenant_id,
        job_expense_category_code=new_row.job_expense_category_code,
        markup_pct=float(new_row.markup_pct),
        markup_amt_cents=new_row.markup_amt_cents,
        valid_period_lower=new_row.valid_period.lower,
        valid_period_upper=new_row.valid_period.upper,
        recorded_at=new_row.recorded_at,
        created_by=new_row.created_by,
    )


@router.get(
    "/markups/{category_code}/history",
    response_model=TenantMarkupVersionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Markup History for Category",
    tags=["settings"],
)
def get_markup_history(
    category_code: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("catalog.manage")),
) -> TenantMarkupVersionHistoryResponse:
    """
    Retrieve all historical markup versions for a given expense category (audit trail).

    Returns all rows for this category, sorted by `recorded_at` DESC (most recent first),
    providing a complete edit history of markup changes.

    **RBAC**: Requires `catalog.manage` permission (owner/accountant only).

    **Path Parameters**:
    - `category_code`: Job expense category code (e.g., 'labor', 'materials')

    **Response**: List of all TenantMarkupVersionResponse items for this category,
    sorted descending by recorded_at. Returns HTTP 200 with empty `items` list if no history.
    Returns HTTP 404 if category_code does not exist.
    """
    # Validate category exists
    category_exists = db.exec(
        select(JobExpenseCategory).where(JobExpenseCategory.code == category_code)
    ).first()

    if not category_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job expense category '{category_code}' not found",
        )

    rows = _get_category_history_impl(category_code, current_user.tenant_id, db)
    items = [
        TenantMarkupVersionResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            job_expense_category_code=row.job_expense_category_code,
            markup_pct=float(row.markup_pct),
            markup_amt_cents=row.markup_amt_cents,
            valid_period_lower=row.valid_period.lower,
            valid_period_upper=row.valid_period.upper,
            recorded_at=row.recorded_at,
            created_by=row.created_by,
        )
        for row in rows
    ]
    return TenantMarkupVersionHistoryResponse(
        category_code=category_code,
        items=items,
        total=len(items),
    )


# ==================== TEST ENDPOINTS (NO AUTH) ====================


@router.get(
    "/markups/test",
    response_model=TenantMarkupVersionListResponse,
    status_code=status.HTTP_200_OK,
    summary="[TEST] List Active Category Markups",
    tags=["settings"],
)
def get_active_markups_test(
    test_tenant_id: UUID | None = None,
    test_context: TestUserContext = Depends(get_test_context),
    db: Session = Depends(get_db),
) -> TenantMarkupVersionListResponse:
    """
    [TEST ENDPOINT — NO AUTH REQUIRED]
    Same as GET /api/v1/settings/markups but without RBAC check.

    Query parameter:
    - test_tenant_id (optional): Override tenant_id for multi-tenant testing
    """
    tenant_id = test_tenant_id if test_tenant_id is not None else test_context.tenant_id
    rows = _get_active_markups_impl(tenant_id, db)
    items = [
        TenantMarkupVersionResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            job_expense_category_code=row.job_expense_category_code,
            markup_pct=float(row.markup_pct),
            markup_amt_cents=row.markup_amt_cents,
            valid_period_lower=row.valid_period.lower,
            valid_period_upper=row.valid_period.upper,
            recorded_at=row.recorded_at,
            created_by=row.created_by,
        )
        for row in rows
    ]
    return TenantMarkupVersionListResponse(items=items, total=len(items))


@router.post(
    "/markups/test",
    response_model=TenantMarkupVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[TEST] Create/Update Markup via Temporal Supersession",
    tags=["settings"],
)
def create_markup_supersession_test(
    payload: TenantMarkupVersionCreate,
    test_tenant_id: UUID | None = None,
    test_context: TestUserContext = Depends(get_test_context),
    db: Session = Depends(get_db),
) -> TenantMarkupVersionResponse:
    """
    [TEST ENDPOINT — NO AUTH REQUIRED]
    Same as POST /api/v1/settings/markups but without RBAC check.

    Query parameter:
    - test_tenant_id (optional): Override tenant_id for multi-tenant testing
    """
    tenant_id = test_tenant_id if test_tenant_id is not None else test_context.tenant_id
    new_row = _create_markup_supersession_impl(payload, tenant_id, test_context.id, db)
    return TenantMarkupVersionResponse(
        id=new_row.id,
        tenant_id=new_row.tenant_id,
        job_expense_category_code=new_row.job_expense_category_code,
        markup_pct=float(new_row.markup_pct),
        markup_amt_cents=new_row.markup_amt_cents,
        valid_period_lower=new_row.valid_period.lower,
        valid_period_upper=new_row.valid_period.upper,
        recorded_at=new_row.recorded_at,
        created_by=new_row.created_by,
    )


@router.get(
    "/markups/{category_code}/history/test",
    response_model=TenantMarkupVersionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="[TEST] Get Markup History for Category",
    tags=["settings"],
)
def get_markup_history_test(
    category_code: str,
    test_tenant_id: UUID | None = None,
    test_context: TestUserContext = Depends(get_test_context),
    db: Session = Depends(get_db),
) -> TenantMarkupVersionHistoryResponse:
    """
    [TEST ENDPOINT — NO AUTH REQUIRED]
    Same as GET /api/v1/settings/markups/{category_code}/history but without RBAC check.

    Query parameter:
    - test_tenant_id (optional): Override tenant_id for multi-tenant testing
    """
    # Validate category exists
    category_exists = db.exec(
        select(JobExpenseCategory).where(JobExpenseCategory.code == category_code)
    ).first()

    if not category_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job expense category '{category_code}' not found",
        )

    tenant_id = test_tenant_id if test_tenant_id is not None else test_context.tenant_id
    rows = _get_category_history_impl(category_code, tenant_id, db)
    items = [
        TenantMarkupVersionResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            job_expense_category_code=row.job_expense_category_code,
            markup_pct=float(row.markup_pct),
            markup_amt_cents=row.markup_amt_cents,
            valid_period_lower=row.valid_period.lower,
            valid_period_upper=row.valid_period.upper,
            recorded_at=row.recorded_at,
            created_by=row.created_by,
        )
        for row in rows
    ]
    return TenantMarkupVersionHistoryResponse(
        category_code=category_code,
        items=items,
        total=len(items),
    )
