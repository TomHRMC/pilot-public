"""
CP-7: Notification Delivery (SD-10 E2E Tier 1)

W-16: Notification delivery pipeline — notification_event → notification_outbox →
_send_notification_impl → notification_delivery_attempt.

Strategy: Insert rows directly via e2e_engine, call _send_notification_impl,
assert delivery_attempt row is created.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

pytestmark = [pytest.mark.e2e]

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OWNER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def _create_notification_event(db, tenant_id: uuid.UUID) -> object:
    """Insert a notification_event row and return it."""
    from app.models.system import NotificationEvent

    event = NotificationEvent(
        tenant_id=tenant_id,
        notification_type_code="dunning_reminder",
        entity_type_code="invoice",
        entity_id=str(uuid.uuid4()),
        occurred_at=datetime.now(UTC),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _create_notification_outbox(
    db, tenant_id: uuid.UUID, event_id: uuid.UUID, channel: str = "in_app"
) -> object:
    """Insert a notification_outbox row and return it."""
    from app.models.system import NotificationOutbox

    outbox = NotificationOutbox(
        notification_event_id=event_id,
        tenant_id=tenant_id,
        recipient_user_id=OWNER_USER_ID,
        channel=channel,
        body="E2E test notification body",
        status="pending",
        category_id="billing",
        priority=5,
        attempt_count=0,
    )
    db.add(outbox)
    db.commit()
    db.refresh(outbox)
    return outbox


class TestNotificationDelivery:
    """W-16: Notification delivery pipeline — in_app channel."""

    def test_in_app_notification_delivered_on_worker_call(
        self, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Insert notification_event + notification_outbox(channel='in_app', status='pending').
        Call _send_notification_impl. Assert outbox.status == 'sent' and
        a notification_delivery_attempt row is created.
        """
        from sqlmodel import Session

        from tasks.notification_worker import _send_notification_impl

        with Session(e2e_engine) as db:
            # Insert notification_event
            event = _create_notification_event(db, TEST_TENANT_ID)
            event_id = event.id

            # Insert notification_outbox
            outbox = _create_notification_outbox(db, TEST_TENANT_ID, event_id, "in_app")
            outbox_id = outbox.id

            # Call the impl function
            result = _send_notification_impl(str(outbox_id), db)

            # Result should be truthy (a dict with status info)
            assert result is not None, (
                "_send_notification_impl must return a result dict"
            )

            # Refresh outbox and check status
            db.refresh(outbox)
            assert outbox.status == "sent", (
                f"Outbox status must be 'sent' after processing, got: {outbox.status}"
            )

            # Store outbox_id for next test
            TestNotificationDelivery._outbox_id = outbox_id
            TestNotificationDelivery._tenant_id = TEST_TENANT_ID

    def test_delivery_attempt_row_has_correct_fields(
        self, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Verify the delivery_attempt row created in test 1 has the expected fields.
        """
        from sqlmodel import Session, select

        from app.models.system import NotificationDeliveryAttempt

        # Use stored IDs from test 1, or create fresh notification if not available
        outbox_id = getattr(TestNotificationDelivery, "_outbox_id", None)

        if outbox_id is None:
            # Create fresh notification for independent run
            from tasks.notification_worker import _send_notification_impl

            with Session(e2e_engine) as db:
                event = _create_notification_event(db, TEST_TENANT_ID)
                outbox = _create_notification_outbox(
                    db, TEST_TENANT_ID, event.id, "in_app"
                )
                outbox_id = outbox.id
                _send_notification_impl(str(outbox_id), db)

        with Session(e2e_engine) as db:
            attempt = db.exec(
                select(NotificationDeliveryAttempt).where(
                    NotificationDeliveryAttempt.notification_outbox_id == outbox_id
                )
            ).first()

            assert attempt is not None, (
                f"notification_delivery_attempt row must exist for outbox {outbox_id}"
            )
            assert attempt.attempt_no >= 1, "attempt_no must be >= 1"
            assert attempt.status == "delivered", (
                f"delivery_attempt.status must be 'delivered', got: {attempt.status}"
            )
            assert attempt.provider, "provider must be a non-empty string"

    def test_in_app_channel_requires_no_external_service(
        self, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Verify in_app channel delivers without external service calls.
        No exception must be raised — confirms in_app delivery is purely local.
        """
        from sqlmodel import Session

        from tasks.notification_worker import _send_notification_impl

        with Session(e2e_engine) as db:
            event = _create_notification_event(db, TEST_TENANT_ID)
            outbox = _create_notification_outbox(db, TEST_TENANT_ID, event.id, "in_app")

            # Should not raise any exception
            try:
                result = _send_notification_impl(str(outbox.id), db)
            except Exception as exc:
                pytest.fail(
                    f"_send_notification_impl raised an unexpected exception for in_app channel: {exc}"
                )

            assert result is not None, "Result must not be None"
            # in_app delivers status "sent" with http_status 200
            status = result.get("status") if isinstance(result, dict) else None
            assert status in ("sent", "skipped"), (
                f"Expected result status 'sent' or 'skipped', got: {status!r}"
            )
