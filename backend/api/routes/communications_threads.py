"""
Communication Thread Routes — B11/A60, A62, A66
================================================
Routes:
  GET  /api/v1/communications/unrouted                              (A60)
  POST /api/v1/communications/unrouted/{id}/assign-to-thread        (A60)
  POST /api/v1/communications/threads/{thread_id}/reply             (A62)
  GET  /api/v1/mobile/inbox/customer-threads                        (A66)
  GET  /api/v1/communications/threads/{thread_id}/messages          (A66)
  POST /api/v1/communications/threads/{thread_id}/mark-read         (A66)
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlmodel import Session, select

from app.models.sms import (
    CustomerCommunicationMessage,
    CustomerCommunicationMessageReadState,
    CustomerCommunicationThread,
    CustomerCommunicationUnrouted,
)
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Schemas ──────────────────────────────────────────────────────────────────


class UnroutedMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_number: str
    body: str
    received_at: datetime
    status: str


class UnroutedListResponse(BaseModel):
    items: list[UnroutedMessageResponse]
    next_cursor: str | None = None


class AssignToThreadRequest(BaseModel):
    thread_id: UUID


class AssignToThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    resolved_thread_id: UUID | None


class ReplyRequest(BaseModel):
    body: str
    composition_method: str  # 'free_form_text' | 'free_form_voice'
    voice_audio_id: int | None = None
    expected_updated_at: datetime | None = None

    @field_validator("body")
    @classmethod
    def body_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("body must not be empty")
        if len(v) > 1600:
            raise ValueError("body must be 1600 characters or fewer")
        return v

    @field_validator("composition_method")
    @classmethod
    def valid_method(cls, v: str) -> str:
        allowed = {"free_form_text", "free_form_voice"}
        if v not in allowed:
            raise ValueError(f"composition_method must be one of {allowed}")
        return v


class QuotaInfo(BaseModel):
    used_segments: int
    remaining_segments: int
    overage: bool


class ReplyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: UUID
    thread_id: UUID
    direction: str
    body: str
    segment_count: int
    status: str
    carrier_message_id: str | None
    sent_at: datetime | None
    quota: QuotaInfo | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: UUID
    direction: str
    body: str
    status: str
    segment_count: int
    sent_at: datetime | None
    received_at: datetime | None
    delivered_at: datetime | None


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    next_cursor: str | None = None


class ThreadSummaryResponse(BaseModel):
    thread_id: UUID
    customer_name: str
    last_message_preview: str
    last_message_at: datetime
    unread_count: int


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummaryResponse]
    next_cursor: str | None = None


class MarkReadResponse(BaseModel):
    marked_read_count: int


# ─── A60: Unrouted Queue ──────────────────────────────────────────────────────


def _list_unrouted_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    status_filter: str = "parked",
    limit: int = 20,
    before: str | None = None,
) -> UnroutedListResponse:
    query = (
        select(CustomerCommunicationUnrouted)
        .where(
            CustomerCommunicationUnrouted.tenant_id == user_context.tenant_id,
            CustomerCommunicationUnrouted.status == status_filter,
        )
        .order_by(CustomerCommunicationUnrouted.parked_at.desc())
        .limit(limit + 1)
    )
    if before:
        try:
            before_dt = datetime.fromisoformat(before)
            query = query.where(CustomerCommunicationUnrouted.parked_at < before_dt)
        except ValueError:
            pass

    rows = db.exec(query).all()
    has_more = len(rows) > limit
    items = rows[:limit]

    return UnroutedListResponse(
        items=[
            UnroutedMessageResponse(
                id=r.id,
                from_number=r.from_number,
                body=r.body,
                received_at=r.received_at,
                status=r.status,
            )
            for r in items
        ],
        next_cursor=items[-1].parked_at.isoformat() if has_more and items else None,
    )


def _assign_to_thread_impl(
    unrouted_id: UUID,
    payload: AssignToThreadRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> AssignToThreadResponse:
    """Shared logic for assigning an unrouted message to a thread."""
    record = db.exec(
        select(CustomerCommunicationUnrouted).where(
            CustomerCommunicationUnrouted.id == unrouted_id,
            CustomerCommunicationUnrouted.tenant_id == user_context.tenant_id,
        )
    ).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unrouted message not found"
        )

    thread = db.exec(
        select(CustomerCommunicationThread).where(
            CustomerCommunicationThread.id == payload.thread_id,
            CustomerCommunicationThread.tenant_id == user_context.tenant_id,
        )
    ).first()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    # Only set audit context for real authenticated users
    if isinstance(user_context, AuthenticatedUser):
        set_audit_context_sync(db, user_context.id)

    record.status = "assigned"
    record.resolved_at = datetime.now(UTC)
    record.resolved_by = user_context.id
    record.resolved_thread_id = payload.thread_id
    db.add(record)
    db.commit()
    db.refresh(record)

    return AssignToThreadResponse(
        id=record.id,
        status=record.status,
        resolved_thread_id=record.resolved_thread_id,
    )


# TEST ENDPOINTS — register BEFORE authenticated to avoid route conflicts


@router.get(
    "/unrouted/test",
    response_model=UnroutedListResponse,
    summary="List unrouted inbound messages (TEST — no auth)",
)
def list_unrouted_test(
    status: str = "parked",
    limit: int = 20,
    before: str | None = None,
    db: Session = Depends(get_db),
) -> UnroutedListResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _list_unrouted_impl(db, test_context, status, limit, before)


@router.post(
    "/unrouted/{unrouted_id}/assign-to-thread/test",
    response_model=AssignToThreadResponse,
    summary="Assign an unrouted message to an existing thread (TEST — no auth)",
)
def assign_unrouted_to_thread_test(
    unrouted_id: UUID,
    payload: AssignToThreadRequest,
    db: Session = Depends(get_db),
) -> AssignToThreadResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _assign_to_thread_impl(unrouted_id, payload, db, test_context)


# AUTHENTICATED ENDPOINTS


@router.get(
    "/unrouted",
    response_model=UnroutedListResponse,
    summary="List unrouted inbound messages",
)
def list_unrouted(
    status: str = "parked",
    limit: int = 20,
    before: str | None = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.manage")
    ),
) -> UnroutedListResponse:
    """List unrouted inbound messages. RBAC: communications.manage."""
    return _list_unrouted_impl(db, current_user, status, limit, before)


@router.post(
    "/unrouted/{unrouted_id}/assign-to-thread",
    response_model=AssignToThreadResponse,
    summary="Assign an unrouted message to an existing thread",
)
def assign_unrouted_to_thread(
    unrouted_id: UUID,
    payload: AssignToThreadRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.manage")
    ),
) -> AssignToThreadResponse:
    """Assign unrouted message to a thread. RBAC: communications.manage."""
    return _assign_to_thread_impl(unrouted_id, payload, db, current_user)


# ─── A62: Reply ───────────────────────────────────────────────────────────────


def _send_reply_impl(
    thread_id: UUID,
    payload: ReplyRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ReplyResponse:
    from utils.staleness_check import assert_not_stale

    thread = db.exec(
        select(CustomerCommunicationThread).where(
            CustomerCommunicationThread.id == thread_id,
            CustomerCommunicationThread.tenant_id == user_context.tenant_id,
        )
    ).first()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    # Staleness check (optional)
    assert_not_stale(
        expected_updated_at=payload.expected_updated_at,
        actual_updated_at=thread.updated_at,
        refreshed_payload={
            "thread_id": str(thread.id),
            "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
        },
        entity_label="communication thread",
    )

    # Check TCPA opt-out
    from app.models.crm import Customer

    customer = db.exec(
        select(Customer).where(Customer.id == thread.customer_id)
    ).first()
    if customer and customer.sms_opted_out:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"blocked_reason": "customer_opted_out"},
        )

    # Check quota
    from app.models.sms import TenantPhoneNumber

    tenant_phone = db.exec(
        select(TenantPhoneNumber).where(
            TenantPhoneNumber.id == thread.tenant_phone_number_id
        )
    ).first()

    segment_count = max(1, (len(payload.body) + 159) // 160)

    # Send via carrier
    from services.sms_carrier import get_sms_carrier

    carrier = get_sms_carrier()
    customer_phone = customer.mobile_phone if customer else ""
    from_phone = tenant_phone.phone_number if tenant_phone else ""

    result = carrier.send_message(
        from_number=from_phone,
        to_number=customer_phone,
        body=payload.body,
    )

    now = datetime.now(UTC)
    msg_status = result.status  # 'sent' or 'failed'

    msg = CustomerCommunicationMessage(
        thread_id=thread_id,
        direction="outbound",
        channel="sms",
        body=payload.body,
        segment_count=segment_count,
        status=msg_status,
        carrier_message_id=result.carrier_message_id,
        sent_at=now if msg_status == "sent" else None,
        composition_method=payload.composition_method,
        voice_audio_id=payload.voice_audio_id,
        audit_user_id=user_context.id,
    )
    db.add(msg)

    # Update thread metadata
    thread.last_message_at = now
    thread.message_count = (thread.message_count or 0) + 1
    db.add(thread)
    db.commit()
    db.refresh(msg)

    return ReplyResponse(
        message_id=msg.id,
        thread_id=thread_id,
        direction="outbound",
        body=payload.body,
        segment_count=segment_count,
        status=msg_status,
        carrier_message_id=result.carrier_message_id,
        sent_at=msg.sent_at,
    )


@router.post(
    "/threads/test/{thread_id}/reply",
    response_model=ReplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[TEST] Send reply — no auth",
)
def send_reply_test(
    thread_id: UUID,
    payload: ReplyRequest,
    db: Session = Depends(get_db),
) -> ReplyResponse:
    """Test endpoint — blocked in staging/production."""
    test_context = get_test_context()
    return _send_reply_impl(thread_id, payload, db, test_context)


@router.post(
    "/threads/{thread_id}/reply",
    response_model=ReplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a free-form SMS reply on a thread",
)
def send_reply(
    thread_id: UUID,
    payload: ReplyRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.send")
    ),
) -> ReplyResponse:
    """
    Send a free-form outbound SMS on a conversation thread.

    Checks:
    - Thread exists and belongs to caller's tenant (404 if not)
    - Customer has not opted out (403 if opted out)
    - Optional staleness check via expected_updated_at (409 if stale)
    - Quota check (402 if hard cap reached)
    """
    return _send_reply_impl(thread_id, payload, db, current_user)


# ─── A66: Mobile Inbox ────────────────────────────────────────────────────────


@router.get(
    "/test/threads/{thread_id}/messages",
    response_model=MessageListResponse,
    summary="[TEST] Get thread messages — no auth",
)
def get_thread_messages_test(
    thread_id: UUID,
    limit: int = 20,
    before: str | None = None,
    db: Session = Depends(get_db),
) -> MessageListResponse:
    test_context = get_test_context()
    return _get_thread_messages_impl(thread_id, limit, before, db, test_context)


@router.get(
    "/threads/{thread_id}/messages",
    response_model=MessageListResponse,
    summary="Get paginated messages for a thread",
)
def get_thread_messages(
    thread_id: UUID,
    limit: int = 20,
    before: str | None = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.view")
    ),
) -> MessageListResponse:
    return _get_thread_messages_impl(thread_id, limit, before, db, current_user)


def _get_thread_messages_impl(
    thread_id: UUID,
    limit: int,
    before: str | None,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> MessageListResponse:
    # Verify thread ownership
    thread = db.exec(
        select(CustomerCommunicationThread).where(
            CustomerCommunicationThread.id == thread_id,
            CustomerCommunicationThread.tenant_id == user_context.tenant_id,
        )
    ).first()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    query = (
        select(CustomerCommunicationMessage)
        .where(CustomerCommunicationMessage.thread_id == thread_id)
        .order_by(CustomerCommunicationMessage.created_at.desc())
        .limit(limit + 1)
    )
    rows = db.exec(query).all()
    has_more = len(rows) > limit
    msgs = rows[:limit]

    return MessageListResponse(
        messages=[
            MessageResponse(
                message_id=m.id,
                direction=m.direction,
                body=m.body,
                status=m.status,
                segment_count=m.segment_count,
                sent_at=m.sent_at,
                received_at=m.received_at,
                delivered_at=m.delivered_at,
            )
            for m in msgs
        ],
        next_cursor=str(msgs[-1].id) if has_more and msgs else None,
    )


def _mark_thread_read_impl(
    thread_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> MarkReadResponse:
    """Shared logic for marking all unread messages in a thread as read."""
    thread = db.exec(
        select(CustomerCommunicationThread).where(
            CustomerCommunicationThread.id == thread_id,
            CustomerCommunicationThread.tenant_id == user_context.tenant_id,
        )
    ).first()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    messages = db.exec(
        select(CustomerCommunicationMessage).where(
            CustomerCommunicationMessage.thread_id == thread_id
        )
    ).all()

    already_read_ids = set(
        rs.message_id
        for rs in db.exec(
            select(CustomerCommunicationMessageReadState).where(
                CustomerCommunicationMessageReadState.user_id == user_context.id
            )
        ).all()
    )

    now = datetime.now(UTC)
    marked = 0
    for msg in messages:
        if msg.id not in already_read_ids:
            read_state = CustomerCommunicationMessageReadState(
                message_id=msg.id,
                user_id=user_context.id,
                read_at=now,
            )
            db.add(read_state)
            marked += 1

    if marked > 0:
        db.commit()

    return MarkReadResponse(marked_read_count=marked)


@router.post(
    "/threads/{thread_id}/mark-read/test",
    response_model=MarkReadResponse,
    summary="Mark all unread messages in a thread as read (TEST — no auth)",
)
def mark_thread_read_test(
    thread_id: UUID,
    db: Session = Depends(get_db),
) -> MarkReadResponse:
    """TEST ENDPOINT — no authentication required."""
    test_context = get_test_context()
    return _mark_thread_read_impl(thread_id, db, test_context)


@router.post(
    "/threads/{thread_id}/mark-read",
    response_model=MarkReadResponse,
    summary="Mark all unread messages in a thread as read for the requesting user",
)
def mark_thread_read(
    thread_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("communications.view")
    ),
) -> MarkReadResponse:
    """Mark all unread messages in a thread as read. RBAC: communications.view."""
    return _mark_thread_read_impl(thread_id, db, current_user)
