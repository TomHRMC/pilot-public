"""
Test Suite: Phase 4.9 Task 3 - Normalize notification_outbox Status Spelling
Tests CHECK constraint value alignment with JSON schema (American spelling)

Reference: phase-4.9-db-schema-sync-5-plan.md - Task 3
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.system import NotificationOutbox


class TestNotificationOutboxStatusConstraint:
    """Test updated notification_outbox CHECK constraint"""

    def test_notification_outbox_valid_statuses(
        self, db_session: Session, test_tenant, test_notification_event
    ):
        """Verify all JSON-defined status values (American spelling) are accepted"""
        # Test all valid statuses
        for status in ["pending", "sent", "failed", "canceled"]:
            outbox = NotificationOutbox(
                tenant_id=test_tenant.id,
                notification_event_id=test_notification_event.id,
                channel="email",
                to_address="test@example.com",
                subject="Test",
                body="Test message",
                status=status,
                category_id="system_announcements",  # B10/A56: required NOT NULL
            )
            db_session.add(outbox)
            db_session.commit()

            # Verify it was saved with correct status
            assert outbox.status == status

            # Clean up
            db_session.delete(outbox)
            db_session.commit()

    def test_notification_outbox_rejects_british_spelling(
        self, db_session: Session, test_tenant, test_notification_event
    ):
        """Verify British spelling 'cancelled' is rejected"""
        # Test British spelling is rejected
        outbox = NotificationOutbox(
            tenant_id=test_tenant.id,
            notification_event_id=test_notification_event.id,
            channel="email",
            to_address="test@example.com",
            subject="Test",
            body="Test message",
            status="cancelled",  # type: ignore  # British spelling
            category_id="system_announcements",  # B10/A56: required NOT NULL
        )
        with pytest.raises(IntegrityError) as exc_info:
            db_session.add(outbox)
            db_session.commit()
        assert "notification_outbox_status_chk" in str(exc_info.value).lower()
        db_session.rollback()

    def test_notification_outbox_default_status(
        self, db_session: Session, test_tenant, test_notification_event
    ):
        """Verify default status is 'pending'"""
        outbox = NotificationOutbox(
            tenant_id=test_tenant.id,
            notification_event_id=test_notification_event.id,
            channel="email",
            to_address="test@example.com",
            subject="Test",
            body="Test message",
            # Don't set status - let default apply
            category_id="system_announcements",  # B10/A56: required NOT NULL
        )
        db_session.add(outbox)
        db_session.commit()

        assert outbox.status == "pending"

    def test_notification_outbox_american_spelling_consistency(
        self, db_session: Session
    ):
        """Verify American spelling is used consistently in code"""
        # Verify Literal type uses American spelling (Pydantic V2 API)
        status_field = NotificationOutbox.model_fields["status"]
        # Check the annotation directly
        assert "canceled" in str(status_field.annotation)
        assert "cancelled" not in str(status_field.annotation)
