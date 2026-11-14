# backend/api/routes/communications.py
"""
Customer Communications API — B4 (A4, A8, A21, A23) + BETA-B1 (recent aggregate)

Endpoints:
  POST /api/v1/communications/send                          — A4/A21: send templated message
  POST /api/v1/communications/preview                       — A23: render only, no dispatch
  GET  /api/v1/customers/{customer_id}/communications       — A8: history (paginated)
  GET  /api/v1/customers/{customer_id}/threads              — customer SMS thread list
  GET  /api/v1/communications/recent                        — BETA-B1: cross-customer aggregate

Registered routers:
  router          → prefix=/api/v1/communications
  customers_router → prefix=/api/v1/customers  (for the history + threads endpoints)

Auth: JWT required. Permission: communications.send (send/preview), customers.view (history/threads),
      communications.view (recent aggregate).
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, func, select

from app.models.communications import CustomerCommTemplateType, CustomerCommunication
from app.models.core import User
from app.models.crm import Customer
from app.models.sms import CustomerCommunicationMessage, CustomerCommunicationThread
from app.models.system import NotificationEvent, NotificationOutbox, NotificationType
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.customer_comms_service import (
    render_communication_preview,
)

logger = logging.getLogger(__name__)
router = APIRouter()  # mounted at /api/v1/communications
customers_router = APIRouter()  # mounted at /api/v1/customers (for A8 history)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CommunicationSendRequest(BaseModel):
    customer_id: UUID
    template_code: str
    job_id: UUID | None = None
    variables: dict[str, Any] = {}
    channel_override: str | None = None  # A21: force channel, ignoring preference


class CommunicationSendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    communication_id: UUID
    template_code: str
    actual_channel: str
    channel_override_flag: bool
    status: str
    rendered_message: str
    rendered_subject: str | None
    recipient_address: str
    sent_at: Any | None


class EditableVariableResponse(BaseModel):
    name: str
    current_value: str | None
    description: str


class CommunicationPreviewResponse(BaseModel):
    rendered_subject: str | None
    rendered_body: str
    recipient_name: str
    recipient_address: str
    actual_channel: str
    editable_variables: list[EditableVariableResponse]


class CommunicationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    communication_id: UUID
    template_code: str
    actual_channel: str
    channel_override_flag: bool
    customer_preferred_channel: str | None
    rendered_message: str
    rendered_subject: str | None
    status: str
    sent_at: Any | None
    sender_user_id: UUID
    job_id: UUID | None


class CommunicationHistoryResponse(BaseModel):
    customer_id: UUID
    total: int
    page: int
    page_size: int
    items: list[CommunicationHistoryItem]


class CommunicationPreviewRequest(BaseModel):
    customer_id: UUID
    template_code: str
    variables: dict[str, Any] = {}
    channel_override: str | None = None


# ---------------------------------------------------------------------------
# Customer SMS Thread schemas (companion to frontend SmsThread type)
# ---------------------------------------------------------------------------


class SmsMessageResponse(BaseModel):
    """Single SMS message within a thread. Mirrors frontend SmsMessage interface."""

    model_config = ConfigDict(from_attributes=True)

    message_id: UUID
    thread_id: UUID
    direction: str
    channel: str
    body: str
    segment_count: int
    status: str
    carrier_message_id: str | None
    composition_method: str | None
    template_id: UUID | None
    voice_audio_id: int | None
    sent_at: Any | None
    delivered_at: Any | None
    received_at: Any | None
    audit_user_id: UUID
    created_at: Any


class SmsThreadResponse(BaseModel):
    """Single thread entry for GET /customers/{id}/threads. Mirrors frontend SmsThread interface."""

    model_config = ConfigDict(from_attributes=True)

    thread_id: UUID
    tenant_id: UUID
    customer_id: UUID
    customer_name: str
    customer_phone: str | None
    customer_sms_opted_out: bool
    customer_opted_out_at: Any | None
    tech_id: UUID
    tech_name: str
    tenant_phone_number_id: UUID
    status: str
    first_message_at: Any
    last_message_at: Any
    message_count: int
    unread_count: int
    originating_job_id: UUID | None
    originating_job_display: str | None
    created_at: Any
    updated_at: Any
    messages: list[SmsMessageResponse]


class CustomerSmsThreadsResponse(BaseModel):
    """Response for GET /api/v1/customers/{customer_id}/threads."""

    threads: list[SmsThreadResponse]
    total: int


# ---------------------------------------------------------------------------
# B20/A94 — Comm Template Type catalog schemas
# ---------------------------------------------------------------------------


class CommTemplateTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    slug: str
    name: str
    description: str | None
    category: str
    preferred_channel: str | None
    initiator: str
    requires_approval: bool
    send_mode: str
    trigger_event: str | None
    is_system: bool
    sort_order: int


class CommTemplateTypeListResponse(BaseModel):
    total: int
    items: list[CommTemplateTypeResponse]


# ---------------------------------------------------------------------------
# Shared business logic
# ---------------------------------------------------------------------------


def _send_communication_impl(
    data: CommunicationSendRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> CommunicationSendResponse:
    """
    Shared send logic — renders template, writes CustomerCommunication + NotificationOutbox.
    Accepts both AuthenticatedUser and TestUserContext.
    """
    tenant_id = user_context.tenant_id
    sender_user_id = user_context.id

    # 1. Validate channel_override value if provided
    if data.channel_override and data.channel_override not in ("sms", "email"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid channel_override '{data.channel_override}'. Must be 'sms' or 'email'.",
        )

    # 2. Render preview (pure, no writes)
    try:
        preview = render_communication_preview(
            db=db,
            tenant_id=tenant_id,
            customer_id=data.customer_id,
            template_code=data.template_code,
            variables=data.variables,
            channel_override=data.channel_override,
            sender_name=getattr(user_context, "display_name", None),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    # 2b. C-B7: Billing-active gate — block ALL services (including SMS) when
    #     the subscription is paused/unpaid/canceled. Tom override 2026-08-05:
    #     spec §9.3 SMS exception is overridden; when paused → everything blocked.
    if preview.actual_channel == "sms":
        from services.entitlement_service import is_subscription_billing_active

        if not is_subscription_billing_active(db, tenant_id):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "type": "https://errors.pilotfortrades.com/subscription-paused",
                    "title": "Subscription not billing-active",
                    "status": 402,
                    "detail": (
                        "SMS sending is blocked because the subscription is "
                        "paused, unpaid, or canceled. Resume the subscription "
                        "to re-enable SMS."
                    ),
                },
            )

    # 3. Write CustomerCommunication (status=pending)
    comm = CustomerCommunication(
        tenant_id=tenant_id,
        customer_id=data.customer_id,
        job_id=data.job_id,
        sender_user_id=sender_user_id,
        template_code=data.template_code,
        template_id=preview.template_id,
        rendered_subject=preview.rendered_subject,
        rendered_message=preview.rendered_body,
        channel=preview.actual_channel,
        customer_preferred_channel=preview.customer_preferred_channel,
        actual_channel=preview.actual_channel,
        channel_override_flag=preview.channel_override_flag,
        status="pending",
        variables_json=data.variables,
        created_by=sender_user_id,
        updated_by=sender_user_id,
    )
    db.add(comm)
    db.flush()  # get comm.id before creating outbox entry

    # 4. Create NotificationEvent
    notification_type = db.exec(
        select(NotificationType).where(
            NotificationType.code == "customer_communication_sent"
        )
    ).first()
    if not notification_type:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Notification type 'customer_communication_sent' not seeded. Run migrations.",
        )

    event = NotificationEvent(
        tenant_id=tenant_id,
        notification_type_code="customer_communication_sent",
        entity_type_code="customer_communication",
        entity_id=str(comm.id),
        created_by=sender_user_id,
    )
    db.add(event)
    db.flush()

    # 5. Create NotificationOutbox entry
    outbox = NotificationOutbox(
        tenant_id=tenant_id,
        notification_event_id=event.id,
        channel=preview.actual_channel,
        to_address=preview.recipient_address,
        body=preview.rendered_body,
        subject=preview.rendered_subject,
        idempotency_key=str(comm.id),
        created_by=sender_user_id,
        updated_by=sender_user_id,
        category_id="customer_activity",  # B10/A56
    )
    db.add(outbox)
    db.flush()

    # 6. Link outbox back to comm
    comm.notification_outbox_id = outbox.id
    db.add(comm)
    db.commit()
    db.refresh(comm)

    return CommunicationSendResponse(
        communication_id=comm.id,
        template_code=comm.template_code,
        actual_channel=comm.actual_channel,
        channel_override_flag=comm.channel_override_flag,
        status=comm.status,
        rendered_message=comm.rendered_message,
        rendered_subject=comm.rendered_subject,
        recipient_address=preview.recipient_address,
        sent_at=comm.sent_at,
    )


def _preview_communication_impl(
    data: CommunicationPreviewRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> CommunicationPreviewResponse:
    """
    Shared preview logic — render only. NEVER writes to customer_communication or notification_outbox.
    """
    tenant_id = user_context.tenant_id

    if data.channel_override and data.channel_override not in ("sms", "email"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid channel_override '{data.channel_override}'. Must be 'sms' or 'email'.",
        )

    try:
        preview = render_communication_preview(
            db=db,
            tenant_id=tenant_id,
            customer_id=data.customer_id,
            template_code=data.template_code,
            variables=data.variables,
            channel_override=data.channel_override,
            sender_name=getattr(user_context, "display_name", None),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    return CommunicationPreviewResponse(
        rendered_subject=preview.rendered_subject,
        rendered_body=preview.rendered_body,
        recipient_name=preview.recipient_name,
        recipient_address=preview.recipient_address,
        actual_channel=preview.actual_channel,
        editable_variables=[
            EditableVariableResponse(
                name=v.name,
                current_value=v.current_value,
                description=v.description,
            )
            for v in preview.editable_variables
        ],
    )


def _get_customer_communications_impl(
    customer_id: UUID,
    page: int,
    page_size: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> CommunicationHistoryResponse:
    """Shared history logic — paginated customer communication log."""
    tenant_id = user_context.tenant_id

    # Verify customer belongs to tenant
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == tenant_id)
    ).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Count total
    all_comms = db.exec(
        select(CustomerCommunication)
        .where(CustomerCommunication.customer_id == customer_id)
        .where(CustomerCommunication.tenant_id == tenant_id)
        .order_by(CustomerCommunication.sent_at.desc().nullslast())
    ).all()
    total = len(all_comms)

    # Paginate
    offset = (page - 1) * page_size
    items = all_comms[offset : offset + page_size]

    return CommunicationHistoryResponse(
        customer_id=customer_id,
        total=total,
        page=page,
        page_size=page_size,
        items=[
            CommunicationHistoryItem(
                communication_id=c.id,
                template_code=c.template_code,
                actual_channel=c.actual_channel,
                channel_override_flag=c.channel_override_flag,
                customer_preferred_channel=c.customer_preferred_channel,
                rendered_message=c.rendered_message,
                rendered_subject=c.rendered_subject,
                status=c.status,
                sent_at=c.sent_at,
                sender_user_id=c.sender_user_id,
                job_id=c.job_id,
            )
            for c in items
        ],
    )


# ---------------------------------------------------------------------------
# TEST ENDPOINTS (registered BEFORE authenticated endpoints)
# ---------------------------------------------------------------------------


@router.post(
    "/send/test",
    response_model=CommunicationSendResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_communication_test(
    data: CommunicationSendRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    set_audit_context_sync(db, test_context.id)
    return _send_communication_impl(data, db, test_context)


@router.post(
    "/preview/test",
    response_model=CommunicationPreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_communication_test(
    data: CommunicationPreviewRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _preview_communication_impl(data, db, test_context)


# ---------------------------------------------------------------------------
# AUTHENTICATED ENDPOINTS
# ---------------------------------------------------------------------------


@router.post(
    "/send",
    response_model=CommunicationSendResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_communication(
    data: CommunicationSendRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.send")
    ),
):
    """
    Send a templated customer communication (SMS or email).

    - Renders template via `render_communication_preview()` (same function as preview)
    - Writes `customer_communication` row (status=pending)
    - Creates `notification_event` + `notification_outbox` entry
    - Existing `poll_pending_notifications` Celery task dispatches the message
    """
    set_audit_context_sync(db, current_user.id)
    return _send_communication_impl(data, db, current_user)


@router.post(
    "/preview",
    response_model=CommunicationPreviewResponse,
    status_code=status.HTTP_200_OK,
)
def preview_communication(
    data: CommunicationPreviewRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.send")
    ),
):
    """
    Render a template without dispatching. Pure read operation.

    NEVER writes to customer_communication. NEVER creates a NotificationOutbox entry.
    Used by the frontend and voice path to show the user what will be sent before confirming.
    """
    return _preview_communication_impl(data, db, current_user)


# ---------------------------------------------------------------------------
# Customer SMS Threads — shared business logic
# GET /api/v1/customers/{customer_id}/threads
# ---------------------------------------------------------------------------


def _get_customer_sms_threads_impl(
    customer_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> CustomerSmsThreadsResponse:
    """
    Return all SMS threads for a customer, newest-last-message first.

    Join path:
      customer_communication_thread (tenant+customer filter)
        → customer (display_name, mobile_phone, sms_opted_out, sms_opt_out_at)
        → user (tech first_name + last_name for tech_name)
      customer_communication_message (per thread, all messages ordered by created_at)

    Tenant isolation enforced via customer_communication_thread.tenant_id.
    unread_count: returned as 0 for MVP (read-state tracking is phase 2).
    originating_job_id / originating_job_display: not stored on thread — returned as null.
    """
    tenant_id = user_context.tenant_id

    # Verify customer belongs to tenant (404 for cross-tenant, preventing enumeration)
    customer = db.exec(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == tenant_id)
    ).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Customer not found",
                "status": 404,
                "detail": f"Customer {customer_id} does not exist in this tenant.",
            },
        )

    # Fetch threads for this customer, newest last_message_at first
    threads = db.exec(
        select(CustomerCommunicationThread)
        .where(CustomerCommunicationThread.customer_id == customer_id)
        .where(CustomerCommunicationThread.tenant_id == tenant_id)
        .order_by(CustomerCommunicationThread.last_message_at.desc())
    ).all()

    thread_responses: list[SmsThreadResponse] = []
    for thread in threads:
        # Resolve tech display name from user table (first_name + last_name or email fallback)
        tech_user = db.exec(select(User).where(User.id == thread.tech_id)).first()
        if tech_user:
            tech_name = " ".join(
                filter(None, [tech_user.first_name, tech_user.last_name])
            ).strip() or str(tech_user.email)
        else:
            tech_name = str(thread.tech_id)

        # Load all messages for this thread ordered by created_at ASC
        messages = db.exec(
            select(CustomerCommunicationMessage)
            .where(CustomerCommunicationMessage.thread_id == thread.id)
            .order_by(CustomerCommunicationMessage.created_at.asc())
        ).all()

        message_responses = [
            SmsMessageResponse(
                message_id=msg.id,
                thread_id=msg.thread_id,
                direction=msg.direction,
                channel=msg.channel,
                body=msg.body,
                segment_count=msg.segment_count,
                status=msg.status,
                carrier_message_id=msg.carrier_message_id,
                composition_method=msg.composition_method,
                template_id=msg.template_id,
                voice_audio_id=msg.voice_audio_id,
                sent_at=msg.sent_at,
                delivered_at=msg.delivered_at,
                received_at=msg.received_at,
                audit_user_id=msg.audit_user_id,
                created_at=msg.created_at,
            )
            for msg in messages
        ]

        thread_responses.append(
            SmsThreadResponse(
                thread_id=thread.id,
                tenant_id=thread.tenant_id,
                customer_id=thread.customer_id,
                customer_name=customer.display_name,
                customer_phone=customer.mobile_phone,
                customer_sms_opted_out=customer.sms_opted_out,
                customer_opted_out_at=customer.sms_opt_out_at,
                tech_id=thread.tech_id,
                tech_name=tech_name,
                tenant_phone_number_id=thread.tenant_phone_number_id,
                status=thread.status,
                first_message_at=thread.first_message_at,
                last_message_at=thread.last_message_at,
                message_count=thread.message_count,
                unread_count=0,  # Phase 2: read-state tracking not yet computed
                originating_job_id=None,  # Not stored on thread — Phase 2
                originating_job_display=None,  # Not stored on thread — Phase 2
                created_at=thread.created_at,
                updated_at=thread.updated_at,
                messages=message_responses,
            )
        )

    return CustomerSmsThreadsResponse(
        threads=thread_responses, total=len(thread_responses)
    )


# ---------------------------------------------------------------------------
# A8 — Customer Communication History
# Mounted under customers_router (prefix=/api/v1/customers)
# ---------------------------------------------------------------------------


# NOTE: /test/{customer_id}/threads MUST be registered before /{customer_id}/threads
# to prevent the /{customer_id} wildcard from matching "test" as a customer_id.


@customers_router.get(
    "/test/{customer_id}/threads",
    response_model=CustomerSmsThreadsResponse,
    status_code=status.HTTP_200_OK,
    tags=["test-only"],
)
def get_customer_sms_threads_test(
    customer_id: UUID,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _get_customer_sms_threads_impl(customer_id, db, test_context)


@customers_router.get(
    "/{customer_id}/threads",
    response_model=CustomerSmsThreadsResponse,
    status_code=status.HTTP_200_OK,
)
def get_customer_sms_threads(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.view")),
):
    """
    Return all SMS threads for a customer, newest first.

    Surface SD-02 seeded data to the customer comms tab.
    Returns { threads: SmsThread[], total: number } matching the frontend SmsThread interface.
    Permission: customers.view
    """
    return _get_customer_sms_threads_impl(customer_id, db, current_user)


@customers_router.get(
    "/test/{customer_id}/communications",
    response_model=CommunicationHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def get_customer_communications_test(
    customer_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _get_customer_communications_impl(
        customer_id, page, page_size, db, test_context
    )


@customers_router.get(
    "/{customer_id}/communications",
    response_model=CommunicationHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def get_customer_communications(
    customer_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("customers.view")),
):
    """
    A8: Paginated communication history for a customer.
    Returns all messages sent to this customer, newest first.
    """
    return _get_customer_communications_impl(
        customer_id, page, page_size, db, current_user
    )


# ---------------------------------------------------------------------------
# B20/A94 — Comm Template Type catalog endpoint
# ---------------------------------------------------------------------------


def _list_comm_template_types_impl(
    db: Session,
    category: str | None = None,
    initiator: str | None = None,
) -> CommTemplateTypeListResponse:
    """
    Shared implementation — returns active comm template types from catalog.
    Always tenant-agnostic (system catalog). Filtered to is_active=true only.
    """
    query = select(CustomerCommTemplateType).where(
        CustomerCommTemplateType.is_active == True
    )
    if category is not None:
        query = query.where(CustomerCommTemplateType.category == category)
    if initiator is not None:
        query = query.where(CustomerCommTemplateType.initiator == initiator)
    query = query.order_by(CustomerCommTemplateType.sort_order)

    rows = db.exec(query).all()
    return CommTemplateTypeListResponse(
        total=len(rows),
        items=[CommTemplateTypeResponse.model_validate(r) for r in rows],
    )


@router.get(
    "/comm-template-types/test",
    response_model=CommTemplateTypeListResponse,
    status_code=status.HTTP_200_OK,
    tags=["test-only"],
)
def list_comm_template_types_test(
    category: str | None = Query(default=None),
    initiator: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Test-only variant — no auth required.
    Used by batch_b20 tests to verify catalog data without JWT.
    """
    test_context = get_test_context()
    if test_context is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Test endpoint not available"
        )
    return _list_comm_template_types_impl(db, category=category, initiator=initiator)


# ---------------------------------------------------------------------------
# BETA-B1: GET /api/v1/communications/recent — cross-customer aggregate
# ---------------------------------------------------------------------------


class CommunicationSummaryItem(BaseModel):
    """Single item in the recent-communications aggregate feed."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    customer_name: str
    channel: str  # "sms"
    direction: str  # "outbound" | "inbound"
    body: str
    created_at: datetime


class RecentCommunicationsResponse(BaseModel):
    """Paginated response for GET /api/v1/communications/recent (COMMS-UI-B1: canonical offset/limit)."""

    items: list[CommunicationSummaryItem]
    total: int
    limit: int
    offset: int


def _get_recent_communications_impl(
    db: Session,
    user_context,  # AuthenticatedUser | TestUserContext
    *,
    limit: int,
    offset: int,
    customer_search: str | None = None,
    channel: str | None = None,
    sent_from: datetime | None = None,
    sent_to: datetime | None = None,
) -> RecentCommunicationsResponse:
    """
    Aggregate the most recent cross-customer communications for the tenant.

    COMMS-UI-B1: canonical offset/limit pagination + search/filter support.

    Join path (MCP-verified column names):
      customer_communication_message.thread_id
        → customer_communication_thread.id (filter tenant_id)
        → customer.id (get display_name)

    Ordered by customer_communication_message.created_at DESC.
    Tenant isolation enforced via customer_communication_thread.tenant_id.

    Filters (all optional, applied to BOTH count and page query):
      - customer_search: case-insensitive ilike on customer.display_name
      - channel: exact match on customer_communication_message.channel (D-1: SMS-only today)
      - sent_from: inclusive lower bound on created_at
      - sent_to: inclusive upper bound on created_at
    """
    tenant_id = user_context.tenant_id

    # Build shared predicate list applied to BOTH count and page query
    # so `total` reflects the active filters (same pattern as customers.py).
    base_where = [CustomerCommunicationThread.tenant_id == tenant_id]

    if customer_search:
        base_where.append(Customer.display_name.ilike(f"%{customer_search}%"))
    if channel:
        base_where.append(CustomerCommunicationMessage.channel == channel)
    if sent_from:
        base_where.append(CustomerCommunicationMessage.created_at >= sent_from)
    if sent_to:
        base_where.append(CustomerCommunicationMessage.created_at <= sent_to)

    # Count total matching messages for this tenant (with filters applied)
    total = db.exec(
        select(func.count(CustomerCommunicationMessage.id))
        .join(
            CustomerCommunicationThread,
            CustomerCommunicationMessage.thread_id == CustomerCommunicationThread.id,
        )
        .join(
            Customer,
            CustomerCommunicationThread.customer_id == Customer.id,
        )
        .where(*base_where)
    ).one()

    # Fetch paginated messages with customer display_name
    rows = db.exec(
        select(
            CustomerCommunicationMessage.id,
            CustomerCommunicationThread.customer_id,
            Customer.display_name,
            CustomerCommunicationMessage.channel,
            CustomerCommunicationMessage.direction,
            CustomerCommunicationMessage.body,
            CustomerCommunicationMessage.created_at,
        )
        .join(
            CustomerCommunicationThread,
            CustomerCommunicationMessage.thread_id == CustomerCommunicationThread.id,
        )
        .join(
            Customer,
            CustomerCommunicationThread.customer_id == Customer.id,
        )
        .where(*base_where)
        # Secondary sort on id makes pagination deterministic when multiple
        # messages share the same created_at timestamp (seed data has ties).
        .order_by(
            CustomerCommunicationMessage.created_at.desc(),
            CustomerCommunicationMessage.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    items = [
        CommunicationSummaryItem(
            id=row[0],
            customer_id=row[1],
            customer_name=row[2],
            channel=row[3],
            direction=row[4],
            body=row[5],
            created_at=row[6],
        )
        for row in rows
    ]

    return RecentCommunicationsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/recent/test",
    response_model=RecentCommunicationsResponse,
    summary="[TEST] Cross-customer recent communications aggregate (no JWT)",
)
def get_recent_communications_test(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    customer_search: str | None = Query(default=None),
    channel: str | None = Query(
        default=None, description="sms | email (email has no data today)"
    ),
    sent_from: datetime | None = Query(default=None),
    sent_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RecentCommunicationsResponse:
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _get_recent_communications_impl(
        db,
        test_context,
        limit=limit,
        offset=offset,
        customer_search=customer_search,
        channel=channel,
        sent_from=sent_from,
        sent_to=sent_to,
    )


@router.get(
    "/recent",
    response_model=RecentCommunicationsResponse,
    summary="Cross-customer recent communications aggregate (COMMS-UI-B1)",
)
def get_recent_communications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    customer_search: str | None = Query(default=None),
    channel: str | None = Query(
        default=None, description="sms | email (email has no data today)"
    ),
    sent_from: datetime | None = Query(default=None),
    sent_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.view")
    ),
) -> RecentCommunicationsResponse:
    """
    COMMS-UI-B1: Aggregate the most recent communications across all customers for the tenant.

    Ordered by created_at DESC. Supports canonical offset/limit pagination plus
    optional filters: customer_search, channel, sent_from, sent_to.

    Used by the /comms page which calls GET /api/v1/communications/recent?limit=50&offset=0.
    Permission: communications.view
    """
    return _get_recent_communications_impl(
        db,
        current_user,
        limit=limit,
        offset=offset,
        customer_search=customer_search,
        channel=channel,
        sent_from=sent_from,
        sent_to=sent_to,
    )


@router.get(
    "/comm-template-types",
    response_model=CommTemplateTypeListResponse,
    status_code=status.HTTP_200_OK,
)
def list_comm_template_types(
    category: str | None = Query(
        default=None, description="Filter by lifecycle category"
    ),
    initiator: str | None = Query(
        default=None, description="Filter by initiator: tech, owner, system"
    ),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.send")
    ),
):
    """
    A94: Return active comm template types for the template picker UI.

    Returns only is_active=true rows ordered by sort_order ASC.
    Tenant-agnostic — system catalog applies to all tenants.
    Optional filters: category, initiator.
    """
    return _list_comm_template_types_impl(db, category=category, initiator=initiator)
