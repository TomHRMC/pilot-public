"""
End-to-End Notification Integration Tests

These tests verify the complete notification pipeline:
API → Database → Celery Worker → SendGrid → Database Update

Marked with @pytest.mark.e2e and @pytest.mark.requires_sendgrid
"""

import uuid

import pytest
from sqlmodel import Session, select

from app.models.core import EntityType
from app.models.system import (
    NotificationDeliveryAttempt,
    NotificationEvent,
    NotificationOutbox,
    NotificationType,
)
from core.config import settings
from tasks.notification_worker import _send_notification_impl

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.integration,
    pytest.mark.requires_sendgrid,
    pytest.mark.requires_db,
    pytest.mark.skipif(
        not settings.SENDGRID_API_KEY, reason="SENDGRID_API_KEY not configured"
    ),
]


@pytest.fixture
def test_recipient():
    """Default test recipient email address."""
    return "owner@example.com"


def test_e2e_email_notification_pipeline(
    db_session: Session, test_tenant, test_recipient
):
    """
    Test the complete notification flow from database record creation to email delivery.

    This verifies:
    1. NotificationEvent creation
    2. NotificationOutbox record creation
    3. Celery worker processing (synchronous execution)
    4. Template rendering
    5. Email sent via SendGrid
    6. NotificationDeliveryAttempt recorded
    7. Outbox status updated to 'sent'
    """
    # 1. Ensure test data exists
    entity_type = db_session.exec(
        select(EntityType).where(EntityType.code == "quote")
    ).first()
    if not entity_type:
        entity_type = EntityType(
            code="quote", name="Quote", description="Quote entity", is_active=True
        )
        db_session.add(entity_type)

    notif_type = db_session.exec(
        select(NotificationType).where(NotificationType.code == "quote_accepted")
    ).first()
    if not notif_type:
        notif_type = NotificationType(
            code="quote_accepted",
            audience="internal",
            name="Quote Accepted",
            is_active=True,
        )
        db_session.add(notif_type)

    db_session.commit()

    # 2. Create NotificationEvent
    event = NotificationEvent(
        tenant_id=test_tenant.id,
        notification_type_code="quote_accepted",
        entity_type_code="quote",
        entity_id=str(uuid.uuid4()),
        payload={
            "quote_id": "Q-12345",
            "customer_name": "Mike the Contractor",
            "amount": "$2,450.00",
        },
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.id is not None, "NotificationEvent should be created"

    # 3. Create NotificationOutbox record
    outbox = NotificationOutbox(
        tenant_id=test_tenant.id,
        notification_event_id=event.id,
        channel="email",
        to_address=test_recipient,
        subject="[E2E Test] Quote {{ quote_id }} Accepted",
        body="""Hello {{ customer_name }},

Your quote {{ quote_id }} for {{ amount }} has been accepted!

This is an end-to-end integration test of the Pilot for Trades notification system.

Best regards,
Pilot for Trades Team""",
        contextdata={
            "quote_id": "Q-12345",
            "customer_name": "Mike the Contractor",
            "amount": "$2,450.00",
        },
        status="pending",
        attempt_count=0,
        category_id="quote_approvals",
    )
    db_session.add(outbox)
    db_session.commit()
    db_session.refresh(outbox)

    assert outbox.id is not None, "NotificationOutbox should be created"
    assert outbox.status == "pending", "Initial status should be pending"

    # 4. Process notification (simulating Celery worker)
    result = _send_notification_impl(str(outbox.id), db_session)

    assert result["status"] == "sent", (
        f"Notification should be sent: {result.get('error')}"
    )
    assert result["attempt_count"] == 1, "Should have 1 delivery attempt"

    # 5. Verify database state after processing
    db_session.refresh(outbox)

    assert outbox.status == "sent", "Outbox status should be 'sent'"
    assert outbox.attempt_count == 1, "Attempt count should be 1"
    assert outbox.last_error is None, "Should have no errors"
    assert outbox.next_attempt_at is None, "Should not schedule retry"

    # 6. Verify delivery attempt was recorded
    attempt = db_session.exec(
        select(NotificationDeliveryAttempt).where(
            NotificationDeliveryAttempt.notification_outbox_id == outbox.id
        )
    ).first()

    assert attempt is not None, "NotificationDeliveryAttempt should be recorded"
    assert attempt.attempt_no == 1, "Should be attempt #1"
    assert attempt.status == "delivered", "Delivery attempt status should be 'sent'"
    assert attempt.provider == "sendgrid", "Provider should be SendGrid"
    assert attempt.http_status == 202, "SendGrid returns HTTP 202"
    assert attempt.error_message is None, "Should have no error message"

    # 7. Verify complete pipeline success
    assert outbox.status == "sent", "Final verification: outbox should be sent"
    assert attempt.status == "delivered", "Final verification: attempt should be sent"


def test_e2e_notification_with_template_error(
    db_session: Session, test_tenant, test_recipient
):
    """Test that template rendering errors are handled gracefully."""
    # Create event and outbox with invalid template
    event = NotificationEvent(
        tenant_id=test_tenant.id,
        notification_type_code="quote_accepted",
        entity_type_code="quote",
        entity_id=str(uuid.uuid4()),
        payload={},
    )
    db_session.add(event)
    db_session.commit()

    outbox = NotificationOutbox(
        tenant_id=test_tenant.id,
        notification_event_id=event.id,
        channel="email",
        to_address=test_recipient,
        subject="Test",
        body="Bad template {% if }",  # Invalid syntax
        status="pending",
        category_id="quote_approvals",
    )
    db_session.add(outbox)
    db_session.commit()
    db_session.refresh(outbox)

    # Process notification
    result = _send_notification_impl(str(outbox.id), db_session)

    # Verify failure handling
    assert result["status"] == "failed", "Should fail on template error"
    assert result["reason"] == "Template render error", "Should identify template error"

    # Verify database state
    db_session.refresh(outbox)
    assert outbox.status == "failed", "Outbox should be marked as error"
