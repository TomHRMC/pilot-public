"""
Test Suite: Phase 3 Task 9 - Missing Check Constraints
Tests data validation constraints from Golden Master v2.6h
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.auth import AuthMfaOtp
from app.models.core import User, UserEndpoint
from app.models.crm import Customer
from app.models.system import (
    ConnectorRunLog,
    IntegrationSyncConflict,
    NotificationOutbox,
    WebhookDeliveryAttempt,
)


class TestEmailFormatConstraints:
    """Email format validation using regex CHECK constraints"""

    def test_user_email_valid_format(self, db_session: Session, test_tenant):
        """Valid email addresses should be accepted"""
        user = User(
            email="valid.user@example.com",
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        assert user.id is not None

    def test_user_email_invalid_format_no_at(self, db_session: Session, test_tenant):
        """Invalid email addresses (missing @) should be rejected"""
        user = User(
            email="invalid-email",  # Missing @domain
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(user)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "user_email_format_chk" in str(exc_info.value)
        db_session.rollback()

    def test_user_email_invalid_format_no_domain(
        self, db_session: Session, test_tenant
    ):
        """Invalid email addresses (missing domain) should be rejected"""
        user = User(
            email="test@",  # Missing domain
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(user)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "user_email_format_chk" in str(exc_info.value)
        db_session.rollback()

    def test_user_endpoint_email_valid(self, db_session: Session, test_user):
        """Valid email endpoints should be accepted"""
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="test@example.com",
            is_primary=True,
        )
        db_session.add(endpoint)
        db_session.commit()
        assert endpoint.id is not None

    def test_user_endpoint_email_invalid(self, db_session: Session, test_user):
        """Invalid email endpoints should be rejected"""
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="not-an-email",  # Invalid format
            is_primary=False,
        )
        db_session.add(endpoint)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "user_endpoint_email_format_chk" in str(exc_info.value)
        db_session.rollback()

    def test_user_endpoint_non_email_no_validation(
        self, db_session: Session, test_user
    ):
        """Non-email channels should not validate email format"""
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel="sms",
            value="+1234567890",  # Not an email, but that's OK for SMS
            is_primary=False,
        )
        db_session.add(endpoint)
        db_session.commit()
        assert endpoint.id is not None


class TestCustomerTypeConstraint:
    """Customer type must be 'person' or 'company'"""

    def test_customer_type_person_valid(self, db_session: Session, test_tenant):
        """Type 'person' should be accepted"""
        customer = Customer(
            tenant_id=test_tenant.id, display_name="John Doe", type="person"
        )
        db_session.add(customer)
        db_session.commit()
        assert customer.id is not None

    def test_customer_type_company_valid(self, db_session: Session, test_tenant):
        """Type 'company' should be accepted"""
        customer = Customer(
            tenant_id=test_tenant.id, display_name="ACME Corp", type="company"
        )
        db_session.add(customer)
        db_session.commit()
        assert customer.id is not None

    def test_customer_type_invalid(self, db_session: Session, test_tenant):
        """Invalid type should be rejected by CHECK constraint"""
        # Note: As of Phase 4.7, Customer.type uses TEXT + CHECK constraint
        # (converted from ENUM for better flexibility and SQLModel compatibility)
        from sqlalchemy.exc import IntegrityError

        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Invalid Type Customer",
            type="organization",  # Not in allowed list
        )
        db_session.add(customer)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "customer_type_chk" in str(exc_info.value)
        db_session.rollback()


class TestAuthMfaChannelConstraint:
    """MFA OTP channel must be 'email' or 'sms'"""

    def test_mfa_channel_email_valid(self, db_session: Session, test_user):
        """Channel 'email' should be accepted"""
        otp = AuthMfaOtp(
            user_id=test_user.id,
            channel="email",
            code_hash="hashed_code_123456",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        db_session.add(otp)
        db_session.commit()
        assert otp.id is not None

    def test_mfa_channel_sms_valid(self, db_session: Session, test_user):
        """Channel 'sms' should be accepted"""
        otp = AuthMfaOtp(
            user_id=test_user.id,
            channel="sms",
            code_hash="hashed_code_654321",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        db_session.add(otp)
        db_session.commit()
        assert otp.id is not None

    def test_mfa_channel_invalid(self, db_session: Session, test_user):
        """Invalid channel should be rejected"""
        otp = AuthMfaOtp(
            user_id=test_user.id,
            channel="push_notification",  # Not supported
            code_hash="hashed_code_999999",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        db_session.add(otp)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "auth_mfa_otp_channel_chk" in str(exc_info.value)
        db_session.rollback()


class TestPlatformRoleConstraint:
    """Platform role must be NULL, 'staff', or 'superadmin'"""

    def test_platform_role_null_valid(self, db_session: Session, test_tenant):
        """NULL platform role should be accepted (tenant user)"""
        user = User(
            email="tenant.user@example.com",
            tenant_id=test_tenant.id,
            platform_role_code=None,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        assert user.id is not None

    def test_platform_role_staff_valid(
        self, db_session: Session, test_platform_role_staff
    ):
        """Platform role 'staff' should be accepted"""
        user = User(
            email="staff@pilotfortrades.com",
            is_platform_user=True,  # Must set for platform users
            platform_role_code="staff",
            mfa_enforced=True,  # Platform users must have MFA
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        assert user.id is not None

    def test_platform_role_superadmin_valid(
        self, db_session: Session, test_platform_role_superadmin
    ):
        """Platform role 'superadmin' should be accepted"""
        user = User(
            email="admin@pilotfortrades.com",
            is_platform_user=True,  # Must set for platform users
            platform_role_code="superadmin",
            mfa_enforced=True,  # Platform users must have MFA
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        assert user.id is not None

    def test_platform_role_invalid(self, db_session: Session):
        """Invalid platform role should be rejected"""
        user = User(
            email="hacker@evil.com",
            platform_role_code="god_mode",  # Not allowed
            is_active=True,
        )
        db_session.add(user)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        # Either constraint can catch this - MFA constraint checks platform role validity too
        error_msg = str(exc_info.value)
        assert (
            "user_platform_role_chk" in error_msg
            or "user_platform_mfa_required_chk" in error_msg
        )
        db_session.rollback()


class TestNotificationOutboxStatusConstraint:
    """Notification outbox status must be valid enum value"""

    def test_notification_outbox_status_valid_all(
        self, db_session: Session, test_tenant, test_notification_event
    ):
        """Valid notification status values should be accepted"""
        for status in ["pending", "sent", "failed", "canceled"]:
            notification = NotificationOutbox(
                tenant_id=test_tenant.id,
                notification_event_id=test_notification_event.id,
                channel="email",
                body=f"Test body for {status}",
                to_address="test@example.com",
                status=status,
                category_id="system_announcements",  # B10/A56: required NOT NULL
            )
            db_session.add(notification)
            db_session.commit()
            assert notification.id is not None

    def test_notification_outbox_status_invalid(
        self, db_session: Session, test_tenant, test_notification_event
    ):
        """Invalid notification status should be rejected"""
        notification = NotificationOutbox(
            tenant_id=test_tenant.id,
            notification_event_id=test_notification_event.id,
            channel="email",
            body="Test body",
            to_address="test@example.com",
            status="delivered",  # Wrong enum value
            category_id="system_announcements",  # B10/A56: required NOT NULL
        )
        db_session.add(notification)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "notification_outbox_status_chk" in str(exc_info.value)
        db_session.rollback()


class TestWebhookDeliveryAttemptStatusConstraint:
    """Webhook delivery attempt status must be valid enum value"""

    def test_webhook_delivery_status_valid_all(
        self, db_session: Session, test_webhook_event, test_webhook_endpoint
    ):
        """Valid webhook delivery status values should be accepted"""
        for idx, status in enumerate(["pending", "success", "failed", "giving_up"]):
            attempt = WebhookDeliveryAttempt(
                webhook_event_id=test_webhook_event.id,
                webhook_endpoint_id=test_webhook_endpoint.id,
                tenant_id=test_webhook_endpoint.tenant_id,
                attempt_no=idx + 1,
                status=status,
            )
            db_session.add(attempt)
            db_session.commit()
            assert attempt.id is not None

    def test_webhook_delivery_status_invalid(
        self, db_session: Session, test_webhook_event, test_webhook_endpoint
    ):
        """Invalid webhook delivery status should be rejected"""
        attempt = WebhookDeliveryAttempt(
            webhook_event_id=test_webhook_event.id,
            webhook_endpoint_id=test_webhook_endpoint.id,
            tenant_id=test_webhook_endpoint.tenant_id,
            attempt_no=1,
            status="completed",  # Wrong enum value
        )
        db_session.add(attempt)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "webhook_delivery_attempt_status_chk" in str(exc_info.value)
        db_session.rollback()


class TestIntegrationSyncConflictStatusConstraint:
    """Integration sync conflict status must be valid enum value"""

    def test_integration_sync_conflict_status_valid_all(
        self, db_session: Session, test_tenant, test_app_service
    ):
        """Valid integration sync conflict status values should be accepted"""
        for idx, status in enumerate(
            ["pending", "resolved_keep_internal", "resolved_keep_external"]
        ):
            conflict = IntegrationSyncConflict(
                tenant_id=test_tenant.id,
                app_service_id=test_app_service.id,
                entity_type_code="customer",
                entity_id="12345678-1234-1234-1234-123456789012",
                external_id=f"EXT{idx}",
                status=status,
                internal_payload={"data": "internal"},
                external_payload={"data": "external"},
            )
            db_session.add(conflict)
            db_session.commit()
            assert conflict.id is not None

    def test_integration_sync_conflict_status_invalid(
        self, db_session: Session, test_tenant, test_app_service
    ):
        """Invalid integration sync conflict status should be rejected"""
        conflict = IntegrationSyncConflict(
            tenant_id=test_tenant.id,
            app_service_id=test_app_service.id,
            entity_type_code="customer",
            entity_id="12345678-1234-1234-1234-123456789012",
            external_id="EXT_INVALID",
            status="resolved",  # Wrong enum value
            internal_payload={"data": "internal"},
            external_payload={"data": "external"},
        )
        db_session.add(conflict)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "integration_sync_conflict_status_chk" in str(exc_info.value)
        db_session.rollback()


class TestConnectorRunLogStatusConstraint:
    """Connector run log status must be valid enum value"""

    def test_connector_run_log_status_valid_all(
        self, db_session: Session, test_supplier
    ):
        """Valid connector run log status values should be accepted"""
        for status in ["running", "success", "failed"]:
            log = ConnectorRunLog(
                supplier_id=test_supplier.id,
                status=status,
            )
            db_session.add(log)
            db_session.commit()
            assert log.id is not None

    def test_connector_run_log_status_invalid(self, db_session: Session, test_supplier):
        """Invalid connector run log status should be rejected"""
        log = ConnectorRunLog(
            supplier_id=test_supplier.id,
            status="pending",  # Wrong enum value
        )
        db_session.add(log)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "connector_run_log_status_chk" in str(exc_info.value)
        db_session.rollback()
