"""
Test Suite: Phase 4.9 Task 2 - Normalize webhook_delivery_attempt Status Values
Tests CHECK constraint value alignment with JSON schema

Reference: phase-4.9-db-schema-sync-5-plan.md - Task 2
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.system import WebhookDeliveryAttempt, WebhookEndpoint, WebhookEvent


class TestWebhookDeliveryAttemptStatusConstraint:
    """Test updated webhook_delivery_attempt CHECK constraint"""

    def test_webhook_delivery_valid_statuses(self, db_session: Session, test_tenant):
        """Verify all JSON-defined status values are accepted"""
        # Create necessary parent objects
        endpoint = WebhookEndpoint(
            tenant_id=test_tenant.id,
            url="https://example.com/webhook",
            events=["test.event"],
        )
        db_session.add(endpoint)
        db_session.commit()

        event = WebhookEvent(
            tenant_id=test_tenant.id,
            event_type="test.event",
            payload={"test": "data"},
        )
        db_session.add(event)
        db_session.commit()

        # Test all valid statuses from JSON schema
        for status in ["pending", "success", "failed", "giving_up"]:
            attempt = WebhookDeliveryAttempt(
                webhook_event_id=event.id,
                webhook_endpoint_id=endpoint.id,
                tenant_id=test_tenant.id,
                status=status,
                attempt_no=1,
            )
            db_session.add(attempt)
            db_session.commit()

            # Verify it was saved with correct status
            assert attempt.status == status

            # Clean up
            db_session.delete(attempt)
            db_session.commit()

    def test_webhook_delivery_rejects_legacy_statuses(
        self, db_session: Session, test_tenant
    ):
        """Verify legacy status values are rejected"""
        # Test legacy statuses are rejected
        for legacy_status in ["delivered", "retrying"]:
            # Create fresh parent objects for each test iteration
            endpoint = WebhookEndpoint(
                tenant_id=test_tenant.id,
                url="https://example.com/webhook",
                events=["test.event"],
            )
            db_session.add(endpoint)
            db_session.commit()

            event = WebhookEvent(
                tenant_id=test_tenant.id,
                event_type="test.event",
                payload={"test": "data"},
            )
            db_session.add(event)
            db_session.commit()

            attempt = WebhookDeliveryAttempt(
                webhook_event_id=event.id,
                webhook_endpoint_id=endpoint.id,
                tenant_id=test_tenant.id,
                status=legacy_status,
                attempt_no=1,
            )
            with pytest.raises(IntegrityError) as exc_info:
                db_session.add(attempt)
                db_session.commit()
            assert "webhook_delivery_attempt_status_chk" in str(exc_info.value).lower()
            db_session.rollback()

    def test_webhook_delivery_default_status(self, db_session: Session, test_tenant):
        """Verify default status value"""
        # Create necessary parent objects
        endpoint = WebhookEndpoint(
            tenant_id=test_tenant.id,
            url="https://example.com/webhook",
            events=["test.event"],
        )
        db_session.add(endpoint)
        db_session.commit()

        event = WebhookEvent(
            tenant_id=test_tenant.id,
            event_type="test.event",
            payload={"test": "data"},
        )
        db_session.add(event)
        db_session.commit()

        attempt = WebhookDeliveryAttempt(
            webhook_event_id=event.id,
            webhook_endpoint_id=endpoint.id,
            tenant_id=test_tenant.id,
            attempt_no=1,
            # Don't set status - let default apply
        )
        db_session.add(attempt)
        db_session.commit()

        assert attempt.status == "pending"
