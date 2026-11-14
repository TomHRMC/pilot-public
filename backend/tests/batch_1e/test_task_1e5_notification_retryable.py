"""
Task 1-E-5: notification_delivery_attempt.retryable Column — Test Suite

Verifies:
  A. Transient Error — Provider throws a 429 Rate Limit response.
     Worker sets attempt.retryable = True and attempt.next_attempt_after is
     in the future.
  B. Terminal Error — Provider throws a 400 Invalid Destination response.
     Worker sets attempt.retryable = False and attempt.next_attempt_after is
     None.

Implementation approach:
  - Directly call _send_notification_impl() with a real DB session so the
    NotificationDeliveryAttempt row is persisted inside the rollback transaction.
  - Mock _send_via_channel() to return a controlled provider result dict,
    simulating 429 (transient) and 400 (terminal) error payloads.
  - Assert against the persisted attempt row, not just the return value.

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-E-5
Batch: 1-E
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from sqlmodel import Session, select

from app.models.core import EntityType
from app.models.system import (
    NotificationDeliveryAttempt,
    NotificationEvent,
    NotificationOutbox,
    NotificationType,
)
from tasks.notification_worker import _send_notification_impl

# ============================================================
# Seed helpers
# ============================================================


def _ensure_entity_type(db_session: Session, code: str) -> None:
    """Idempotently ensure an EntityType row exists."""
    existing = db_session.exec(
        select(EntityType).where(EntityType.code == code)
    ).first()
    if not existing:
        db_session.add(
            EntityType(
                code=code, name=code.title(), description=code.title(), is_active=True
            )
        )
        db_session.flush()


def _ensure_notification_type(db_session: Session, code: str) -> None:
    """Idempotently ensure a NotificationType row exists."""
    existing = db_session.exec(
        select(NotificationType).where(NotificationType.code == code)
    ).first()
    if not existing:
        db_session.add(
            NotificationType(
                code=code,
                audience="tenant",
                name=code.replace("_", " ").title(),
                is_active=True,
            )
        )
        db_session.flush()


def _seed_pending_outbox(
    db_session: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    channel: str = "email",
    to_address: str = "test@example.com",
) -> NotificationOutbox:
    """
    Seed a NotificationEvent + NotificationOutbox in 'pending' status,
    ready for the notification worker to process.

    Note: notification_outbox_recipient_exclusive_chk requires exactly ONE of
    recipient_contact_id, recipient_user_id, or to_address to be set.
    For email/sms tests that exercise the to_address delivery path we set
    only to_address (no recipient_user_id) to satisfy the constraint.
    """
    _ensure_entity_type(db_session, "user")
    _ensure_notification_type(db_session, "test_retryable_notification")

    event = NotificationEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        notification_type_code="test_retryable_notification",
        entity_type_code="user",
        entity_id=str(user_id),
        occurred_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.flush()

    outbox = NotificationOutbox(
        id=uuid.uuid4(),
        notification_event_id=event.id,
        tenant_id=tenant_id,
        # recipient_user_id intentionally omitted — to_address satisfies the
        # exclusive recipient check for email/sms channel tests.
        channel=channel,
        to_address=to_address,
        subject="Retryable Test",
        body="Hello {{ name }}",
        status="pending",
        attempt_count=0,
        category_id="system_announcements",  # B10/A56: required NOT NULL
    )
    db_session.add(outbox)
    db_session.commit()
    db_session.refresh(outbox)
    return outbox


# ============================================================
# Test A — Transient Error (429 Rate Limit)
# ============================================================


class TestTransientError:
    """
    Mock the provider to return a 429 Rate Limit result.
    Worker must record attempt.retryable = True and populate
    attempt.next_attempt_after in the future.
    """

    def test_transient_429_sets_retryable_true_and_next_attempt_after(
        self, db_session: Session, test_tenant, test_user
    ):
        """
        Test A: On a 429 transient error, the persisted NotificationDeliveryAttempt
        must have retryable=True and next_attempt_after > now().
        """
        outbox = _seed_pending_outbox(
            db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            to_address="recipient@example.com",
        )

        # Simulate 429 Rate Limit response from the provider
        transient_result = {
            "status": "error",
            "details": {"error": "rate_limit_exceeded"},
            "error_message": "Too Many Requests: rate limit exceeded",
            "http_status": 429,
            "retryable": True,
        }

        with patch(
            "tasks.notification_worker._send_via_channel",
            return_value=transient_result,
        ):
            _send_notification_impl(str(outbox.id), db_session)

        # Reload the attempt from DB within this transaction
        attempt = db_session.exec(
            select(NotificationDeliveryAttempt).where(
                NotificationDeliveryAttempt.notification_outbox_id == outbox.id
            )
        ).first()

        assert attempt is not None, "NotificationDeliveryAttempt row must be created"

        # Core assertions for transient error
        assert attempt.retryable is True, (
            f"Expected retryable=True for 429, got {attempt.retryable}"
        )
        assert attempt.next_attempt_after is not None, (
            "next_attempt_after must be set for retryable errors"
        )
        assert attempt.next_attempt_after > datetime.now(UTC), (
            "next_attempt_after must be in the future"
        )

        # Supporting assertions
        assert attempt.http_status == 429
        assert attempt.error_message == "Too Many Requests: rate limit exceeded"
        assert attempt.status == "error"

        # The outbox record should stay 'pending' with a retry scheduled
        db_session.refresh(outbox)
        assert outbox.status == "pending", (
            f"Outbox should remain 'pending' for retryable error, got {outbox.status}"
        )
        assert outbox.next_attempt_at is not None, (
            "outbox.next_attempt_at must be set for transient errors"
        )


# ============================================================
# Test B — Terminal Error (400 Invalid Destination)
# ============================================================


class TestTerminalError:
    """
    Mock the provider to return a 400 Invalid Destination result.
    Worker must record attempt.retryable = False and next_attempt_after = None.
    """

    def test_terminal_400_sets_retryable_false_and_no_next_attempt(
        self, db_session: Session, test_tenant, test_user
    ):
        """
        Test B: On a 400 terminal error (invalid destination / hard bounce),
        the persisted NotificationDeliveryAttempt must have retryable=False
        and next_attempt_after=None.
        """
        outbox = _seed_pending_outbox(
            db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            to_address="invalid-bounce@example.com",
        )

        # Simulate 400 Bad Request / invalid destination from provider
        terminal_result = {
            "status": "error",
            "details": {"code": 21211, "details": "Invalid phone number"},
            "error_message": "400 Bad Request: The 'To' number is not a valid phone number",
            "http_status": 400,
            "retryable": False,
        }

        with patch(
            "tasks.notification_worker._send_via_channel",
            return_value=terminal_result,
        ):
            _send_notification_impl(str(outbox.id), db_session)

        # Reload the attempt from DB within this transaction
        attempt = db_session.exec(
            select(NotificationDeliveryAttempt).where(
                NotificationDeliveryAttempt.notification_outbox_id == outbox.id
            )
        ).first()

        assert attempt is not None, "NotificationDeliveryAttempt row must be created"

        # Core assertions for terminal error
        assert attempt.retryable is False, (
            f"Expected retryable=False for 400 terminal error, got {attempt.retryable}"
        )
        assert attempt.next_attempt_after is None, (
            f"next_attempt_after must be None for terminal errors, got {attempt.next_attempt_after}"
        )

        # Supporting assertions
        assert attempt.http_status == 400
        assert "400 Bad Request" in (attempt.error_message or "")
        assert attempt.status == "error"

        # The outbox record should be marked 'failed' — no further delivery attempts
        db_session.refresh(outbox)
        assert outbox.status == "failed", (
            f"Outbox should be 'failed' for terminal error, got {outbox.status}"
        )
        assert outbox.next_attempt_at is None, (
            "outbox.next_attempt_at must be None for terminal errors"
        )


# ============================================================
# Test C — Successful Delivery (sanity check)
# ============================================================


class TestSuccessfulDelivery:
    """
    Sanity check: successful delivery sets retryable=False and
    next_attempt_after=None on the attempt row.
    """

    def test_success_sets_retryable_false_and_no_next_attempt(
        self, db_session: Session, test_tenant, test_user
    ):
        """
        Test C: On a successful 'sent' response, the attempt row must have
        retryable=False and next_attempt_after=None (no retry needed).
        """
        outbox = _seed_pending_outbox(
            db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            to_address="success@example.com",
        )

        success_result = {
            "status": "sent",
            "details": {"message": "Delivered"},
            "error_message": None,
            "http_status": 202,
            "retryable": False,
        }

        with patch(
            "tasks.notification_worker._send_via_channel",
            return_value=success_result,
        ):
            result = _send_notification_impl(str(outbox.id), db_session)

        attempt = db_session.exec(
            select(NotificationDeliveryAttempt).where(
                NotificationDeliveryAttempt.notification_outbox_id == outbox.id
            )
        ).first()

        assert attempt is not None
        assert attempt.retryable is False
        assert attempt.next_attempt_after is None
        assert attempt.status == "delivered"
        assert attempt.http_status == 202

        db_session.refresh(outbox)
        assert outbox.status == "sent"
        assert result["status"] == "sent"
