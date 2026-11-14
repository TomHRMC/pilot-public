"""
dashboard.py — B5/A5

Widget CRUD endpoints for the user Dashboard.
All endpoints require JWT + dashboard.manage permission.
Users can only manage their own widgets — tenant isolation is enforced,
and ownership is enforced at the row level (user_id = current_user.id).
Returns 404 (not 403) for unowned widgets to prevent user enumeration.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, select

from api.schemas.reports import (
    UserDashboardWidgetCreate,
    UserDashboardWidgetResponse,
    UserDashboardWidgetUpdate,
)
from app.models.reports import UserDashboardWidget
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_owned_widget_or_404(
    db: Session, widget_id: UUID, user_context: AuthenticatedUser | TestUserContext
) -> UserDashboardWidget:
    """Fetch widget by ID, enforcing both tenant and user ownership.

    Returns 404 (not 403) when widget is not found or belongs to a different user.
    This prevents user enumeration — the caller cannot distinguish between
    'widget does not exist' and 'widget belongs to someone else'.
    """
    widget = db.exec(
        select(UserDashboardWidget)
        .where(UserDashboardWidget.id == widget_id)
        .where(UserDashboardWidget.tenant_id == user_context.tenant_id)
        .where(UserDashboardWidget.user_id == user_context.id)
    ).first()

    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://pilotfortrades.com/errors/not-found",
                "title": "Widget Not Found",
                "status": 404,
                "detail": f"Dashboard widget {widget_id} not found",
            },
        )
    return widget


# ---------------------------------------------------------------------------
# B11/A64: Recent Customer Messages Widget — schema
# ---------------------------------------------------------------------------


class RecentMessageItem(BaseModel):
    thread_id: UUID
    customer_id: UUID
    customer_name: str
    tech_id: UUID
    tech_name: str
    direction: str
    body_preview: str
    last_message_at: datetime
    unread_count: int


class RecentCustomerMessagesResponse(BaseModel):
    messages: list[RecentMessageItem]


# ---------------------------------------------------------------------------
# Shared _impl() Functions
# ---------------------------------------------------------------------------


def _list_widgets_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> list[UserDashboardWidgetResponse]:
    """Shared logic for listing current user's dashboard widgets."""
    widgets = db.exec(
        select(UserDashboardWidget)
        .where(UserDashboardWidget.user_id == user_context.id)
        .where(UserDashboardWidget.tenant_id == user_context.tenant_id)
        .order_by(UserDashboardWidget.position_y, UserDashboardWidget.position_x)
    ).all()
    return [UserDashboardWidgetResponse.model_validate(w) for w in widgets]


def _create_widget_impl(
    widget_in: UserDashboardWidgetCreate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> UserDashboardWidgetResponse:
    """Shared logic for creating a new dashboard widget."""
    now = datetime.now(UTC)
    widget = UserDashboardWidget(
        user_id=user_context.id,
        tenant_id=user_context.tenant_id,
        widget_type=widget_in.widget_type.value,
        widget_config_json=widget_in.widget_config_json,
        position_x=widget_in.position_x,
        position_y=widget_in.position_y,
        width=widget_in.width,
        height=widget_in.height,
        created_by=user_context.id,
        updated_by=user_context.id,
        created_at=now,
        updated_at=now,
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return UserDashboardWidgetResponse.model_validate(widget)


def _update_widget_impl(
    widget_id: UUID,
    widget_in: UserDashboardWidgetUpdate,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> UserDashboardWidgetResponse:
    """Shared logic for updating a dashboard widget."""
    widget = _get_owned_widget_or_404(db, widget_id, user_context)

    if widget_in.widget_config_json is not None:
        widget.widget_config_json = widget_in.widget_config_json
    if widget_in.position_x is not None:
        widget.position_x = widget_in.position_x
    if widget_in.position_y is not None:
        widget.position_y = widget_in.position_y
    if widget_in.width is not None:
        widget.width = widget_in.width
    if widget_in.height is not None:
        widget.height = widget_in.height

    widget.updated_at = datetime.now(UTC)
    widget.updated_by = user_context.id

    db.add(widget)
    db.commit()
    db.refresh(widget)
    return UserDashboardWidgetResponse.model_validate(widget)


def _delete_widget_impl(
    widget_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> None:
    """Shared logic for hard-deleting a dashboard widget."""
    widget = _get_owned_widget_or_404(db, widget_id, user_context)
    db.delete(widget)
    db.commit()


def _get_recent_customer_messages_impl(
    limit: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> RecentCustomerMessagesResponse:
    """Shared logic for the recent customer messages widget."""
    from app.models.core import User
    from app.models.crm import Customer
    from app.models.sms import (
        CustomerCommunicationMessage,
        CustomerCommunicationMessageReadState,
        CustomerCommunicationThread,
    )

    limit = min(limit, 50)

    threads = db.exec(
        select(CustomerCommunicationThread)
        .where(
            CustomerCommunicationThread.tenant_id == user_context.tenant_id,
            CustomerCommunicationThread.status == "active",
        )
        .order_by(CustomerCommunicationThread.last_message_at.desc())
        .limit(limit)
    ).all()

    items = []
    for thread in threads:
        customer = db.exec(
            select(Customer).where(Customer.id == thread.customer_id)
        ).first()
        tech = db.exec(select(User).where(User.id == thread.tech_id)).first()

        last_msg = db.exec(
            select(CustomerCommunicationMessage)
            .where(CustomerCommunicationMessage.thread_id == thread.id)
            .order_by(CustomerCommunicationMessage.created_at.desc())
        ).first()

        all_inbound = db.exec(
            select(CustomerCommunicationMessage).where(
                CustomerCommunicationMessage.thread_id == thread.id,
                CustomerCommunicationMessage.direction == "inbound",
            )
        ).all()

        read_ids = set(
            rs.message_id
            for rs in db.exec(
                select(CustomerCommunicationMessageReadState).where(
                    CustomerCommunicationMessageReadState.user_id == user_context.id
                )
            ).all()
        )
        unread_count = sum(1 for m in all_inbound if m.id not in read_ids)

        customer_name = customer.display_name if customer else "Unknown"
        tech_first = getattr(tech, "first_name", "") or ""
        tech_last = getattr(tech, "last_name", "") or ""
        tech_name = f"{tech_first} {tech_last}".strip() or "Unknown"

        body = last_msg.body[:80] if last_msg else ""
        direction = last_msg.direction if last_msg else "inbound"

        items.append(
            RecentMessageItem(
                thread_id=thread.id,
                customer_id=thread.customer_id,
                customer_name=customer_name,
                tech_id=thread.tech_id,
                tech_name=tech_name,
                direction=direction,
                body_preview=body,
                last_message_at=thread.last_message_at,
                unread_count=unread_count,
            )
        )

    return RecentCustomerMessagesResponse(messages=items)


# ---------------------------------------------------------------------------
# TEST ENDPOINTS — register BEFORE authenticated to avoid route conflicts
# Route ordering critical:
#   GET  /widgets/test                           (list)
#   POST /widgets/test                           (create)
#   GET  /widgets/recent-customer-messages/test  (widget)
# All must come BEFORE PATCH/DELETE /widgets/{widget_id} and authenticated variants
# ---------------------------------------------------------------------------


@router.get(
    "/widgets/test",
    response_model=list[UserDashboardWidgetResponse],
    summary="List Dashboard Widgets (TEST — no auth)",
)
def list_widgets_test(
    db: Session = Depends(get_db),
) -> list[UserDashboardWidgetResponse]:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _list_widgets_impl(db, test_context)


@router.post(
    "/widgets/test",
    response_model=UserDashboardWidgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Dashboard Widget (TEST — no auth)",
)
def create_widget_test(
    widget_in: UserDashboardWidgetCreate,
    db: Session = Depends(get_db),
) -> UserDashboardWidgetResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _create_widget_impl(widget_in, db, test_context)


@router.get(
    "/widgets/recent-customer-messages/test",
    response_model=RecentCustomerMessagesResponse,
    summary="Recent inbound customer messages widget (TEST — no auth)",
)
def get_recent_customer_messages_test(
    limit: int = 10,
    db: Session = Depends(get_db),
) -> RecentCustomerMessagesResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _get_recent_customer_messages_impl(limit, db, test_context)


@router.patch(
    "/widgets/{widget_id}/test",
    response_model=UserDashboardWidgetResponse,
    summary="Update Dashboard Widget (TEST — no auth)",
)
def update_widget_test(
    widget_id: UUID,
    widget_in: UserDashboardWidgetUpdate,
    db: Session = Depends(get_db),
) -> UserDashboardWidgetResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _update_widget_impl(widget_id, widget_in, db, test_context)


@router.delete(
    "/widgets/{widget_id}/test",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Dashboard Widget (TEST — no auth)",
)
def delete_widget_test(
    widget_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _delete_widget_impl(widget_id, db, test_context)


# ---------------------------------------------------------------------------
# AUTHENTICATED ENDPOINTS
# ---------------------------------------------------------------------------


@router.get(
    "/widgets",
    response_model=list[UserDashboardWidgetResponse],
    summary="List Dashboard Widgets",
    description="List the authenticated user's pinned dashboard widgets.",
)
def list_widgets(
    current_user: AuthenticatedUser = Depends(require_permission("dashboard.manage")),
    db: Session = Depends(get_db),
) -> list[UserDashboardWidgetResponse]:
    return _list_widgets_impl(db, current_user)


@router.post(
    "/widgets",
    response_model=UserDashboardWidgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Dashboard Widget",
    description="Pin a new widget to the authenticated user's dashboard.",
)
def create_widget(
    widget_in: UserDashboardWidgetCreate,
    current_user: AuthenticatedUser = Depends(require_permission("dashboard.manage")),
    db: Session = Depends(get_db),
) -> UserDashboardWidgetResponse:
    return _create_widget_impl(widget_in, db, current_user)


@router.patch(
    "/widgets/{widget_id}",
    response_model=UserDashboardWidgetResponse,
    summary="Update Dashboard Widget",
    description="Update widget config, position, or size. Returns 404 if widget not found or not owned by caller.",
)
def update_widget(
    widget_id: UUID,
    widget_in: UserDashboardWidgetUpdate,
    current_user: AuthenticatedUser = Depends(require_permission("dashboard.manage")),
    db: Session = Depends(get_db),
) -> UserDashboardWidgetResponse:
    return _update_widget_impl(widget_id, widget_in, db, current_user)


@router.delete(
    "/widgets/{widget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Dashboard Widget",
    description="Hard-delete a widget. Returns 404 if widget not found or not owned by caller.",
)
def delete_widget(
    widget_id: UUID,
    current_user: AuthenticatedUser = Depends(require_permission("dashboard.manage")),
    db: Session = Depends(get_db),
) -> None:
    return _delete_widget_impl(widget_id, db, current_user)


@router.get(
    "/widgets/recent-customer-messages",
    response_model=RecentCustomerMessagesResponse,
    summary="Recent inbound customer messages widget — B11/A64",
)
def get_recent_customer_messages(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.view")
    ),
) -> RecentCustomerMessagesResponse:
    """Return the most recent inbound customer SMS messages for the owner dashboard."""
    return _get_recent_customer_messages_impl(limit, db, current_user)


# ---------------------------------------------------------------------------
# FE-B23/A1: At-Risk Jobs Widget — schema + impl
# ---------------------------------------------------------------------------


class AtRiskJobItem(BaseModel):
    job_id: UUID
    customer_name: str
    site_name: str | None = None
    status_code: str | None = None
    scheduled_start_at: datetime | None = None
    actual_cost_cents: int
    quoted_budget_cents: int | None = None
    projected_margin_pct: float | None = None


class AtRiskJobsResponse(BaseModel):
    jobs: list[AtRiskJobItem]
    total: int


def _get_at_risk_jobs_impl(
    limit: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> AtRiskJobsResponse:
    """Return jobs below the tenant's margin target, worst margin first."""
    from app.models.crm import Customer, Site
    from app.models.fulfillment import Job, JobStatus
    from app.models.quoting import Quote
    from services.setting_resolver import get_effective_setting

    # Resolve margin target (default 20%)
    margin_val, _ = get_effective_setting(
        db, user_context.tenant_id, "margin_target_pct", fallback=20
    )
    try:
        margin_target = float(margin_val)
    except (TypeError, ValueError):
        margin_target = 20.0

    # Active in-flight job status codes
    ACTIVE_STATUS_CODES = ("in_progress", "scheduled")

    jobs = db.exec(
        select(Job, JobStatus, Customer, Site, Quote)
        .join(JobStatus, Job.status_id == JobStatus.id)
        .join(Customer, Job.customer_id == Customer.id)
        .join(Site, Job.site_id == Site.id, isouter=True)
        .join(Quote, Job.quote_id == Quote.id, isouter=True)
        .where(Job.tenant_id == user_context.tenant_id)
        .where(Job.is_active == True)
        .where(JobStatus.code.in_(ACTIVE_STATUS_CODES))
    ).all()

    items: list[AtRiskJobItem] = []
    for job, job_status, customer, site, quote in jobs:
        actual_cost_cents = job.actual_labor_cost_cents + job.actual_material_cost_cents

        projected_margin_pct: float | None = None
        quoted_budget_cents: int | None = None

        if quote is not None and quote.total_cents and quote.total_cents > 0:
            quoted_budget_cents = quote.total_cents
            projected_margin_pct = (
                (quote.total_cents - actual_cost_cents) / quote.total_cents * 100
            )
            # Only include if below margin target
            if projected_margin_pct >= margin_target:
                continue
        else:
            # No linked quote — include only if costs have been recorded
            if actual_cost_cents <= 0:
                continue
            projected_margin_pct = None

        items.append(
            AtRiskJobItem(
                job_id=job.id,
                customer_name=customer.display_name,
                site_name=site.name if site else None,
                status_code=job_status.code,
                scheduled_start_at=job.scheduled_start_at,
                actual_cost_cents=actual_cost_cents,
                quoted_budget_cents=quoted_budget_cents,
                projected_margin_pct=projected_margin_pct,
            )
        )

    # Sort: worst margin first (None values last), then by actual cost descending
    def sort_key(item: AtRiskJobItem):
        margin = item.projected_margin_pct
        if margin is None:
            return (1, -item.actual_cost_cents)
        return (0, margin)

    items.sort(key=sort_key)
    items = items[:limit]

    return AtRiskJobsResponse(jobs=items, total=len(items))


# ---------------------------------------------------------------------------
# FE-B23/A2: Pending Approvals Summary — schema + impl
# ---------------------------------------------------------------------------


class PendingApprovalsSummaryResponse(BaseModel):
    pending_quotes: int
    pending_field_issues: int


def _get_pending_approvals_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PendingApprovalsSummaryResponse:
    """Count pending-approval quotes and pending owner escalations for this tenant."""
    from app.models.quoting import Quote, QuoteStatus
    from app.models.system import MobileSyncOwnerEscalation

    # Count quotes in pending_approval status
    pending_status = db.exec(
        select(QuoteStatus).where(QuoteStatus.code == "pending_approval")
    ).first()

    pending_quotes = 0
    if pending_status is not None:
        all_pending = db.exec(
            select(Quote)
            .where(Quote.tenant_id == user_context.tenant_id)
            .where(Quote.status_id == pending_status.id)
            .where(Quote.is_active == True)
        ).all()
        pending_quotes = len(all_pending)

    # Count pending owner escalations
    escalations = db.exec(
        select(MobileSyncOwnerEscalation)
        .where(MobileSyncOwnerEscalation.tenant_id == user_context.tenant_id)
        .where(MobileSyncOwnerEscalation.status == "pending")
    ).all()
    pending_field_issues = len(escalations)

    return PendingApprovalsSummaryResponse(
        pending_quotes=pending_quotes,
        pending_field_issues=pending_field_issues,
    )


# ---------------------------------------------------------------------------
# FE-B23 TEST ENDPOINTS — register before authenticated
# ---------------------------------------------------------------------------


@router.get(
    "/at-risk-jobs/test",
    response_model=AtRiskJobsResponse,
    summary="At-Risk Jobs widget (TEST — no auth)",
)
def get_at_risk_jobs_test(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> AtRiskJobsResponse:
    """TEST ENDPOINT — no authentication required."""
    ctx = get_test_context()
    return _get_at_risk_jobs_impl(limit, db, ctx)


@router.get(
    "/pending-approvals-summary/test",
    response_model=PendingApprovalsSummaryResponse,
    summary="Pending Approvals Summary (TEST — no auth)",
)
def get_pending_approvals_summary_test(
    db: Session = Depends(get_db),
) -> PendingApprovalsSummaryResponse:
    """TEST ENDPOINT — no authentication required."""
    ctx = get_test_context()
    return _get_pending_approvals_impl(db, ctx)


# ---------------------------------------------------------------------------
# FE-B23 AUTHENTICATED ENDPOINTS
# ---------------------------------------------------------------------------


@router.get(
    "/at-risk-jobs",
    response_model=AtRiskJobsResponse,
    summary="At-Risk Jobs widget — FE-B23/A1",
    description=(
        "Returns active jobs below the tenant's margin target, worst margin first. "
        "Jobs without a linked quote are included if actual costs > 0."
    ),
)
def get_at_risk_jobs(
    limit: int = Query(10, ge=1, le=50),
    current_user: AuthenticatedUser = Depends(require_permission("reports.view")),
    db: Session = Depends(get_db),
) -> AtRiskJobsResponse:
    return _get_at_risk_jobs_impl(limit, db, current_user)


@router.get(
    "/pending-approvals-summary",
    response_model=PendingApprovalsSummaryResponse,
    summary="Pending Approvals Summary — FE-B23/A2",
    description=(
        "Returns count of quotes awaiting approval and pending owner escalations."
    ),
)
def get_pending_approvals_summary(
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
    db: Session = Depends(get_db),
) -> PendingApprovalsSummaryResponse:
    return _get_pending_approvals_impl(db, current_user)
