"""
reports.py — B5/A5

Six read-only GET endpoints for the Reports domain.
All endpoints require JWT + reports.view permission.
Tenant isolation is enforced automatically from current_user.tenant_id.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from api.schemas.reports import (
    ARAgingCustomerRow,
    ARAgingReportResponse,
    ARAgingSummary,
    ProfitabilityReportResponse,
    ProfitabilityRow,
    RevenueReportResponse,
    RevenueRow,
    TaxLiabilityReportResponse,
    TaxLiabilityRow,
    TechProductivityReportResponse,
    TechProductivityRow,
    VoiceAnalyticsReportResponse,
    VoiceAnalyticsRow,
    VoiceAnalyticsSummary,
    WipReportResponse,
    WipReportRow,
    WipSummary,
)
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.report_service import (
    compute_display_mode,
    get_ar_aging_report,
    get_profitability_report,
    get_report_chart_threshold,
    get_revenue_report,
    get_tax_liability_report,
    get_tech_productivity_report,
    get_voice_analytics_report,
)
from services.wip_service import (
    KNOWN_STATUS_CODES,
    VALID_ORDER,
    VALID_SORT,
    compute_wip_report,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _is_owner_or_manager(user: AuthenticatedUser | TestUserContext) -> bool:
    """Return True if user has cross-user visibility (owner/office_staff/accountant).
    TestUserContext is always treated as owner-level for report access."""
    if isinstance(user, TestUserContext):
        return True  # Test context has full access
    from core.permissions import has_permission

    return has_permission(user.permissions, "*") or has_permission(
        user.permissions, "reports.view_all"
    )


def _validate_date_range(date_from: date, date_to: date) -> None:
    """Raise 422 if date_from > date_to."""
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from must be <= date_to",
        )


# ---------------------------------------------------------------------------
# Shared _impl() Functions
# ---------------------------------------------------------------------------


def _get_profitability_impl(
    date_from: date,
    date_to: date,
    group_by: str,
    filter_status: str | None,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ProfitabilityReportResponse:
    """Shared logic for the profitability report."""
    _validate_date_range(date_from, date_to)
    status_codes = (
        [s.strip() for s in filter_status.split(",")] if filter_status else None
    )
    valid_group_by = {"job", "customer", "site"}
    if group_by not in valid_group_by:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"group_by must be one of: {', '.join(valid_group_by)}",
        )
    data = get_profitability_report(
        db=db,
        tenant_id=user_context.tenant_id,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
        filter_status=status_codes,
    )
    threshold = get_report_chart_threshold(db, user_context.tenant_id)
    row_count = len(data)
    return ProfitabilityReportResponse(
        report_type="profitability",
        date_from=date_from,
        date_to=date_to,
        display_mode=compute_display_mode(row_count, threshold),
        row_count=row_count,
        report_chart_threshold=threshold,
        data=[ProfitabilityRow(**r) for r in data],
    )


def _get_revenue_impl(
    date_from: date,
    date_to: date,
    group_by: str,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> RevenueReportResponse:
    """Shared logic for the revenue report."""
    _validate_date_range(date_from, date_to)
    valid_group_by = {"month", "week", "quarter"}
    if group_by not in valid_group_by:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"group_by must be one of: {', '.join(valid_group_by)}",
        )
    data = get_revenue_report(
        db=db,
        tenant_id=user_context.tenant_id,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
    )
    threshold = get_report_chart_threshold(db, user_context.tenant_id)
    row_count = len(data)
    return RevenueReportResponse(
        report_type="revenue",
        date_from=date_from,
        date_to=date_to,
        display_mode=compute_display_mode(row_count, threshold),
        row_count=row_count,
        report_chart_threshold=threshold,
        data=[RevenueRow(**r) for r in data],
    )


def _get_ar_aging_impl(
    date_from: date,
    date_to: date,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ARAgingReportResponse:
    """Shared logic for the AR aging report."""
    result = get_ar_aging_report(
        db=db,
        tenant_id=user_context.tenant_id,
        as_of_date=date_to,
    )
    threshold = get_report_chart_threshold(db, user_context.tenant_id)
    row_count = len(result["data"])
    return ARAgingReportResponse(
        report_type="ar_aging",
        as_of_date=date_to,
        display_mode=compute_display_mode(row_count, threshold),
        row_count=row_count,
        report_chart_threshold=threshold,
        summary=ARAgingSummary(**result["summary"]),
        data=[ARAgingCustomerRow(**r) for r in result["data"]],
    )


def _get_tech_productivity_impl(
    date_from: date,
    date_to: date,
    group_by: str,
    user_id: UUID | None,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TechProductivityReportResponse:
    """Shared logic for the tech productivity report."""
    _validate_date_range(date_from, date_to)
    effective_user_id = user_id
    if not _is_owner_or_manager(user_context):
        effective_user_id = user_context.id
    data = get_tech_productivity_report(
        db=db,
        tenant_id=user_context.tenant_id,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
        user_id=effective_user_id,
    )
    threshold = get_report_chart_threshold(db, user_context.tenant_id)
    row_count = len(data)
    return TechProductivityReportResponse(
        report_type="tech_productivity",
        date_from=date_from,
        date_to=date_to,
        display_mode=compute_display_mode(row_count, threshold),
        row_count=row_count,
        report_chart_threshold=threshold,
        data=[TechProductivityRow(**r) for r in data],
    )


def _get_tax_liability_impl(
    date_from: date,
    date_to: date,
    group_by: str,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> TaxLiabilityReportResponse:
    """Shared logic for the tax liability report."""
    _validate_date_range(date_from, date_to)
    valid_group_by = {"month", "quarter"}
    if group_by not in valid_group_by:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"group_by must be one of: {', '.join(valid_group_by)}",
        )
    data = get_tax_liability_report(
        db=db,
        tenant_id=user_context.tenant_id,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
    )
    threshold = get_report_chart_threshold(db, user_context.tenant_id)
    row_count = len(data)
    return TaxLiabilityReportResponse(
        report_type="tax_liability",
        date_from=date_from,
        date_to=date_to,
        display_mode=compute_display_mode(row_count, threshold),
        row_count=row_count,
        report_chart_threshold=threshold,
        data=[TaxLiabilityRow(**r) for r in data],
    )


def _get_voice_analytics_impl(
    date_from: date,
    date_to: date,
    group_by: str,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> VoiceAnalyticsReportResponse:
    """Shared logic for the voice analytics report."""
    _validate_date_range(date_from, date_to)
    valid_group_by = {"intent", "user", "day"}
    if group_by not in valid_group_by:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"group_by must be one of: {', '.join(valid_group_by)}",
        )
    result = get_voice_analytics_report(
        db=db,
        tenant_id=user_context.tenant_id,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
    )
    threshold = get_report_chart_threshold(db, user_context.tenant_id)
    row_count = len(result["data"])
    return VoiceAnalyticsReportResponse(
        report_type="voice_analytics",
        date_from=date_from,
        date_to=date_to,
        display_mode=compute_display_mode(row_count, threshold),
        row_count=row_count,
        report_chart_threshold=threshold,
        summary=VoiceAnalyticsSummary(**result["summary"]),
        data=[VoiceAnalyticsRow(**r) for r in result["data"]],
    )


def _get_wip_impl(
    status_filter: str | None,
    sort: str,
    order: str,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> WipReportResponse:
    """Shared logic for the WIP report (UP-1).

    Validates sort/order/status (RFC 7807 422 on invalid values), then delegates
    to ``wip_service.compute_wip_report()``.

    Note: ``status_filter`` (not ``status``) avoids shadowing the ``fastapi.status``
    module imported at the top of this file.
    """
    # --- Validate sort (RFC 7807 Problem Details — Rule 8) ---
    if sort not in VALID_SORT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/validation-error",
                "title": "Invalid sort parameter",
                "status": 422,
                "detail": f"sort must be one of: {', '.join(sorted(VALID_SORT))}",
            },
        )

    # --- Validate order ---
    if order not in VALID_ORDER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/validation-error",
                "title": "Invalid order parameter",
                "status": 422,
                "detail": f"order must be one of: {', '.join(sorted(VALID_ORDER))}",
            },
        )

    # --- Parse status CSV → list[str] (default active codes when None) ---
    if status_filter is None:
        status_codes: list[str] | None = None
    else:
        status_codes = [s.strip() for s in status_filter.split(",") if s.strip()]
        # Validate each code against known job_status codes
        invalid = [c for c in status_codes if c not in KNOWN_STATUS_CODES]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "type": "https://errors.pilotfortrades.com/validation-error",
                    "title": "Invalid status code",
                    "status": 422,
                    "detail": (
                        f"Unknown status code(s): {', '.join(invalid)}. "
                        f"Valid codes: {', '.join(sorted(KNOWN_STATUS_CODES))}"
                    ),
                },
            )

    data = compute_wip_report(
        db=db,
        tenant_id=user_context.tenant_id,
        status_codes=status_codes,
        sort=sort,
        order=order,
    )

    return WipReportResponse(
        report_type="wip",
        generated_at=datetime.now(UTC),
        margin_target_pct=float(data["margin_target_pct"]),
        row_count=len(data["rows"]),
        summary=WipSummary(**data["summary"]),
        rows=[WipReportRow(**r) for r in data["rows"]],
    )


# ---------------------------------------------------------------------------
# TEST ENDPOINTS (register BEFORE authenticated endpoints)
# ---------------------------------------------------------------------------


@router.get(
    "/profitability/test",
    response_model=ProfitabilityReportResponse,
    summary="Profitability Report (TEST — no auth)",
)
def get_profitability_test(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: str = Query(default="job"),
    filter_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ProfitabilityReportResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_profitability_impl(
        date_from, date_to, group_by, filter_status, db, test_context
    )


@router.get(
    "/revenue/test",
    response_model=RevenueReportResponse,
    summary="Revenue Report (TEST — no auth)",
)
def get_revenue_test(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: str = Query(default="month"),
    db: Session = Depends(get_db),
) -> RevenueReportResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_revenue_impl(date_from, date_to, group_by, db, test_context)


@router.get(
    "/ar-aging/test",
    response_model=ARAgingReportResponse,
    summary="AR Aging Report (TEST — no auth)",
)
def get_ar_aging_test(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
) -> ARAgingReportResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_ar_aging_impl(date_from, date_to, db, test_context)


@router.get(
    "/tech-productivity/test",
    response_model=TechProductivityReportResponse,
    summary="Tech Productivity Report (TEST — no auth)",
)
def get_tech_productivity_test(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: str = Query(default="user"),
    user_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> TechProductivityReportResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_tech_productivity_impl(
        date_from, date_to, group_by, user_id, db, test_context
    )


@router.get(
    "/tax-liability/test",
    response_model=TaxLiabilityReportResponse,
    summary="Tax Liability Report (TEST — no auth)",
)
def get_tax_liability_test(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: str = Query(default="month"),
    db: Session = Depends(get_db),
) -> TaxLiabilityReportResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_tax_liability_impl(date_from, date_to, group_by, db, test_context)


@router.get(
    "/voice-analytics/test",
    response_model=VoiceAnalyticsReportResponse,
    summary="Voice Analytics Report (TEST — no auth)",
)
def get_voice_analytics_test(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: str = Query(default="intent"),
    db: Session = Depends(get_db),
) -> VoiceAnalyticsReportResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_voice_analytics_impl(date_from, date_to, group_by, db, test_context)


@router.get(
    "/wip/test",
    response_model=WipReportResponse,
    summary="WIP Report (TEST — no auth)",
)
def get_wip_test(
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Comma-separated job_status.code values (default: scheduled,in_progress)",
    ),
    sort: str = Query(
        default="deviation_pct",
        description="Sort field: deviation_pct | projected_margin_pct | actual_cost_cents | scheduled_start_at",
    ),
    order: str = Query(default="desc", description="Sort order: asc | desc"),
    db: Session = Depends(get_db),
) -> WipReportResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_wip_impl(status_filter, sort, order, db, test_context)


# ---------------------------------------------------------------------------
# AUTHENTICATED ENDPOINTS
# ---------------------------------------------------------------------------


@router.get(
    "/profitability",
    response_model=ProfitabilityReportResponse,
    summary="Profitability Report",
    description="Aggregate job profitability by job, customer, or site within a date range.",
)
def get_profitability(
    date_from: date = Query(..., description="Report period start (inclusive)"),
    date_to: date = Query(..., description="Report period end (inclusive)"),
    group_by: str = Query(
        default="job", description="Grouping dimension: 'job' | 'customer' | 'site'"
    ),
    filter_status: str | None = Query(
        default=None, description="Comma-separated job_status.code values"
    ),
    current_user: AuthenticatedUser = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> ProfitabilityReportResponse:
    return _get_profitability_impl(
        date_from, date_to, group_by, filter_status, db, current_user
    )


@router.get(
    "/revenue",
    response_model=RevenueReportResponse,
    summary="Revenue Report",
    description="Aggregate invoiced vs collected revenue by month, week, or quarter.",
)
def get_revenue(
    date_from: date = Query(..., description="Report period start (inclusive)"),
    date_to: date = Query(..., description="Report period end (inclusive)"),
    group_by: str = Query(
        default="month", description="Grouping dimension: 'month' | 'week' | 'quarter'"
    ),
    current_user: AuthenticatedUser = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> RevenueReportResponse:
    return _get_revenue_impl(date_from, date_to, group_by, db, current_user)


@router.get(
    "/ar-aging",
    response_model=ARAgingReportResponse,
    summary="AR Aging Report",
    description="Accounts-receivable aging buckets (current, 31-60, 61-90, 91+) as of date_to.",
)
def get_ar_aging(
    date_from: date = Query(
        ...,
        description="Report period start (unused for aging; required for API consistency)",
    ),
    date_to: date = Query(..., description="Aging computed as of this date"),
    current_user: AuthenticatedUser = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> ARAgingReportResponse:
    return _get_ar_aging_impl(date_from, date_to, db, current_user)


@router.get(
    "/tech-productivity",
    response_model=TechProductivityReportResponse,
    summary="Tech Productivity Report",
    description="Technician productivity: jobs worked/completed, hours logged, labor cost.",
)
def get_tech_productivity(
    date_from: date = Query(..., description="Report period start (inclusive)"),
    date_to: date = Query(..., description="Report period end (inclusive)"),
    group_by: str = Query(
        default="user", description="Grouping dimension: 'user' | 'job_status'"
    ),
    user_id: UUID | None = Query(
        default=None,
        description="Optional UUID filter — restrict to a single technician",
    ),
    current_user: AuthenticatedUser = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> TechProductivityReportResponse:
    return _get_tech_productivity_impl(
        date_from, date_to, group_by, user_id, db, current_user
    )


@router.get(
    "/tax-liability",
    response_model=TaxLiabilityReportResponse,
    summary="Tax Liability Report",
    description="Tax collected per period (month or quarter) from invoice.tax_cents.",
)
def get_tax_liability(
    date_from: date = Query(..., description="Report period start (inclusive)"),
    date_to: date = Query(..., description="Report period end (inclusive)"),
    group_by: str = Query(
        default="month", description="Grouping dimension: 'month' | 'quarter'"
    ),
    current_user: AuthenticatedUser = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> TaxLiabilityReportResponse:
    return _get_tax_liability_impl(date_from, date_to, group_by, db, current_user)


@router.get(
    "/voice-analytics",
    response_model=VoiceAnalyticsReportResponse,
    summary="Voice Analytics Report",
    description="Voice command analytics: success rates, latency distribution, grouped by intent/user/day.",
)
def get_voice_analytics(
    date_from: date = Query(..., description="Report period start (inclusive)"),
    date_to: date = Query(..., description="Report period end (inclusive)"),
    group_by: str = Query(
        default="intent", description="Grouping dimension: 'intent' | 'user' | 'day'"
    ),
    current_user: AuthenticatedUser = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> VoiceAnalyticsReportResponse:
    return _get_voice_analytics_impl(date_from, date_to, group_by, db, current_user)


@router.get(
    "/wip",
    response_model=WipReportResponse,
    summary="WIP Report",
    description=(
        "Work-in-progress report: per-active-job actuals + ETC-projected cost vs "
        "quoted budget, with deviation % and projected margin %. 'Now' snapshot "
        "(no date range). Returns all active jobs sorted."
    ),
)
def get_wip(
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Comma-separated job_status.code values (default: scheduled,in_progress)",
    ),
    sort: str = Query(
        default="deviation_pct",
        description="Sort field: deviation_pct | projected_margin_pct | actual_cost_cents | scheduled_start_at",
    ),
    order: str = Query(default="desc", description="Sort order: asc | desc"),
    current_user: AuthenticatedUser = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> WipReportResponse:
    return _get_wip_impl(status_filter, sort, order, db, current_user)
