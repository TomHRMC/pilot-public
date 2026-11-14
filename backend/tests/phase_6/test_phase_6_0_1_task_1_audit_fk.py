"""
Test Suite: Phase 6.0.1 Task 1 - Common & Reference Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md - Task 1
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session


class TestCommonTablesCreatedByFK:
    """Test FK constraint enforcement on created_by column for common tables"""

    def test_address_type_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.crm import AddressType

        # Attempt to create record with non-existent user ID
        invalid_user_id = uuid.uuid4()
        address_type = AddressType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Address Type",
            created_by=invalid_user_id,
        )
        db_session.add(address_type)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_address_type_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_contact_type_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.crm import ContactType

        invalid_user_id = uuid.uuid4()
        contact_type = ContactType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Contact Type",
            created_by=invalid_user_id,
        )
        db_session.add(contact_type)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_contact_type_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_entity_type_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.core import EntityType

        invalid_user_id = uuid.uuid4()
        entity_type = EntityType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Entity Type",
            created_by=invalid_user_id,
        )
        db_session.add(entity_type)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_entity_type_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_currency_created_by_fk_enforcement(self, db_session: Session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        from app.models.billing import Currency

        invalid_user_id = uuid.uuid4()
        currency = Currency(
            tenant_id=test_tenant.id,
            code="TST",
            name="Test Currency",
            symbol="T",
            created_by=invalid_user_id,
        )
        db_session.add(currency)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_currency_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_taxability_code_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.quoting import TaxabilityCode

        invalid_user_id = uuid.uuid4()
        tax_code = TaxabilityCode(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Tax Code",
            created_by=invalid_user_id,
        )
        db_session.add(tax_code)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_taxability_code_created_by" in str(exc_info.value)
        db_session.rollback()


class TestCommonTablesValidCreatedBy:
    """Test that valid created_by user IDs are accepted"""

    def test_address_type_valid_created_by_accepted(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that valid created_by user ID is accepted"""
        from app.models.crm import AddressType

        address_type = AddressType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Address Type",
            created_by=test_user.id,
        )
        db_session.add(address_type)
        db_session.commit()

        assert address_type.created_by == test_user.id

    def test_contact_type_valid_created_by_accepted(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that valid created_by user ID is accepted"""
        from app.models.crm import ContactType

        contact_type = ContactType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Contact Type",
            created_by=test_user.id,
        )
        db_session.add(contact_type)
        db_session.commit()

        assert contact_type.created_by == test_user.id


class TestCommonTablesUpdatedByFK:
    """Test FK constraint enforcement on updated_by column"""

    def test_address_type_updated_by_fk_enforcement(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that invalid updated_by user ID is rejected"""
        from app.models.crm import AddressType

        # Create valid record
        address_type = AddressType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Address Type",
            created_by=test_user.id,
        )
        db_session.add(address_type)
        db_session.commit()

        # Attempt to update with invalid user ID
        invalid_user_id = uuid.uuid4()
        address_type.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_address_type_updated_by" in str(exc_info.value)
        db_session.rollback()

    def test_contact_type_updated_by_fk_enforcement(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that invalid updated_by user ID is rejected"""
        from app.models.crm import ContactType

        contact_type = ContactType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Contact Type",
            created_by=test_user.id,
        )
        db_session.add(contact_type)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        contact_type.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_contact_type_updated_by" in str(exc_info.value)
        db_session.rollback()


class TestNotificationTablesAuditFK:
    """Test FK constraint enforcement for notification tables"""

    def test_notification_channel_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import NotificationChannel

        invalid_user_id = uuid.uuid4()
        channel = NotificationChannel(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Channel",
            created_by=invalid_user_id,
        )
        db_session.add(channel)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_notification_channel_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_notification_type_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import NotificationType

        invalid_user_id = uuid.uuid4()
        notif_type = NotificationType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Type",
            audience="tenant",  # Required field
            created_by=invalid_user_id,
        )
        db_session.add(notif_type)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_notification_type_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_notification_template_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import NotificationTemplate, NotificationType

        # Create a notification type first
        notif_type = NotificationType(
            tenant_id=test_tenant.id,
            code="TEST_TYPE",
            name="Test Type",
            audience="tenant",
        )
        db_session.add(notif_type)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        template = NotificationTemplate(
            tenant_id=test_tenant.id,
            notification_type_code="TEST_TYPE",  # Required field
            channel="email",  # Required field
            locale="en_US",  # Required field
            subject="Test Subject",
            body="Test Body",
            created_by=invalid_user_id,
        )
        db_session.add(template)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_notification_template_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_notification_outbox_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import NotificationEvent, NotificationType

        # Create a notification type first
        notif_type = NotificationType(
            tenant_id=test_tenant.id,
            code="TEST_TYPE",
            name="Test Type",
            audience="tenant",
        )
        db_session.add(notif_type)
        db_session.commit()

        # Create a notification event (required for outbox)
        from app.models.core import EntityType

        entity_type = EntityType(
            tenant_id=test_tenant.id,
            code="TEST_ENTITY",
            name="Test Entity",
        )
        db_session.add(entity_type)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        notif_event = NotificationEvent(
            tenant_id=test_tenant.id,
            notification_type_code="TEST_TYPE",
            entity_type_code="TEST_ENTITY",
            entity_id=str(uuid.uuid4()),
            created_by=invalid_user_id,
        )
        db_session.add(notif_event)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_notification_event_created_by" in str(exc_info.value)
        db_session.rollback()


class TestAppendOnlyTablesCreatedByFK:
    """Test FK constraints on append-only tables (created_by only, no updated_by)"""

    def test_notification_event_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected for append-only table"""
        from app.models.core import EntityType
        from app.models.system import NotificationEvent, NotificationType

        # Create notification type first
        notif_type = NotificationType(
            tenant_id=test_tenant.id,
            code="TEST_TYPE",
            name="Test Type",
            audience="tenant",
        )
        db_session.add(notif_type)
        db_session.commit()

        # Create entity type
        entity_type = EntityType(
            tenant_id=test_tenant.id,
            code="TEST_ENTITY",
            name="Test Entity",
        )
        db_session.add(entity_type)
        db_session.commit()

        # Attempt to create event with non-existent user ID
        invalid_user_id = uuid.uuid4()
        event = NotificationEvent(
            tenant_id=test_tenant.id,
            notification_type_code="TEST_TYPE",
            entity_type_code="TEST_ENTITY",
            entity_id=str(uuid.uuid4()),
            created_by=invalid_user_id,
        )
        db_session.add(event)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_notification_event_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_notification_event_valid_created_by_accepted(
        self, db_session: Session, test_user, test_tenant
    ):
        """Test that valid created_by user ID is accepted for append-only table"""
        from app.models.core import EntityType
        from app.models.system import NotificationEvent, NotificationType

        # Create notification type first
        notif_type = NotificationType(
            tenant_id=test_tenant.id,
            code="TEST_TYPE",
            name="Test Type",
            audience="tenant",
            created_by=test_user.id,
        )
        db_session.add(notif_type)
        db_session.commit()

        # Create entity type
        entity_type = EntityType(
            tenant_id=test_tenant.id,
            code="TEST_ENTITY",
            name="Test Entity",
            created_by=test_user.id,
        )
        db_session.add(entity_type)
        db_session.commit()

        # Create event with valid user ID
        event = NotificationEvent(
            tenant_id=test_tenant.id,
            notification_type_code="TEST_TYPE",
            entity_type_code="TEST_ENTITY",
            entity_id=str(uuid.uuid4()),
            created_by=test_user.id,
        )
        db_session.add(event)
        db_session.commit()

        assert event.created_by == test_user.id
        # Verify no updated_by column exists
        assert not hasattr(event, "updated_by")

    def test_jwk_status_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected for append-only table"""
        from app.models.auth import JwkStatus

        invalid_user_id = uuid.uuid4()
        jwk_status = JwkStatus(
            tenant_id=test_tenant.id,
            code="ACTIVE",
            name="Active",
            created_by=invalid_user_id,
        )
        db_session.add(jwk_status)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_jwk_status_created_by" in str(exc_info.value)
        db_session.rollback()


class TestAuthTablesAuditFK:
    """Test FK constraint enforcement for auth tables"""

    def test_sso_provider_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.auth import SsoProvider

        invalid_user_id = uuid.uuid4()
        sso_provider = SsoProvider(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test SSO Provider",
            created_by=invalid_user_id,
        )
        db_session.add(sso_provider)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_sso_provider_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_password_policy_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.auth import PasswordPolicy

        invalid_user_id = uuid.uuid4()
        policy = PasswordPolicy(
            tenant_id=test_tenant.id,
            name="Test Policy",
            min_length=8,
            created_by=invalid_user_id,
        )
        db_session.add(policy)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_password_policy_created_by" in str(exc_info.value)
        db_session.rollback()


class TestCoreTablesAuditFK:
    """Test FK constraint enforcement for core tables"""

    def test_platform_role_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.core import PlatformRole

        invalid_user_id = uuid.uuid4()
        role = PlatformRole(code="TEST", name="Test Role", created_by=invalid_user_id)
        db_session.add(role)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_platform_role_created_by" in str(exc_info.value)
        db_session.rollback()


class TestSystemTablesAuditFK:
    """Test FK constraint enforcement for system tables"""

    def test_webhook_event_type_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import WebhookEventType

        invalid_user_id = uuid.uuid4()
        event_type = WebhookEventType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Event Type",
            created_by=invalid_user_id,
        )
        db_session.add(event_type)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_webhook_event_type_created_by" in str(exc_info.value)
        db_session.rollback()


class TestQuotingTablesAuditFK:
    """Test FK constraint enforcement for quoting tables"""

    def test_qco_line_type_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.quoting import QcoLineType

        invalid_user_id = uuid.uuid4()
        line_type = QcoLineType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Line Type",
            created_by=invalid_user_id,
        )
        db_session.add(line_type)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_qco_line_type_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_qpl_contact_action_type_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.quoting import QplContactActionType

        invalid_user_id = uuid.uuid4()
        action_type = QplContactActionType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Action Type",
            created_by=invalid_user_id,
        )
        db_session.add(action_type)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_qpl_contact_action_type_created_by" in str(exc_info.value)
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted (ON DELETE RESTRICT)"""

    def test_user_deletion_blocked_by_address_type_audit(
        self, db_session: Session, test_tenant
    ):
        """Test that user cannot be deleted if audit references exist"""
        from app.models.core import User
        from app.models.crm import AddressType

        # Create a user without tenant_user relationship to avoid that FK firing first
        user = User(
            email="test_delete@example.com",
            password_hash="dummy",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        # Create record with user audit reference
        address_type = AddressType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Address Type",
            created_by=user.id,
        )
        db_session.add(address_type)
        db_session.commit()

        # Attempt to delete user (should fail due to RESTRICT)
        db_session.delete(user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_address_type_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_user_deletion_blocked_by_notification_channel_audit(
        self, db_session: Session, test_tenant
    ):
        """Test that user cannot be deleted if audit references exist"""
        from app.models.core import User
        from app.models.system import NotificationChannel

        # Create a user without tenant_user relationship
        user = User(
            email="test_delete2@example.com",
            password_hash="dummy",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        channel = NotificationChannel(
            code="EMAIL",
            name="Email",
            created_by=user.id,
        )
        db_session.add(channel)
        db_session.commit()

        db_session.delete(user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_notification_channel_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_user_deletion_blocked_by_updated_by_reference(
        self, db_session: Session, test_tenant
    ):
        """Test that user cannot be deleted if updated_by references exist"""
        from app.models.core import User
        from app.models.crm import ContactType

        # Create a user without tenant_user relationship
        user = User(
            email="test_delete3@example.com",
            password_hash="dummy",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        contact_type = ContactType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Contact Type",
            created_by=user.id,
            updated_by=user.id,
        )
        db_session.add(contact_type)
        db_session.commit()

        db_session.delete(user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Should fail on either created_by or updated_by FK
        error_msg = str(exc_info.value)
        assert (
            "fk_contact_type_created_by" in error_msg
            or "fk_contact_type_updated_by" in error_msg
        )
        db_session.rollback()


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""

    def test_address_type_null_audit_columns(self, db_session: Session, test_tenant):
        """Test that NULL created_by and updated_by are allowed"""
        from app.models.crm import AddressType

        # Create record with NULL audit columns
        address_type = AddressType(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Address Type",
            created_by=None,
            updated_by=None,
        )
        db_session.add(address_type)
        db_session.commit()

        assert address_type.created_by is None
        assert address_type.updated_by is None

    def test_notification_channel_null_audit_columns(
        self, db_session: Session, test_tenant
    ):
        """Test that NULL audit columns are allowed"""
        from app.models.system import NotificationChannel

        channel = NotificationChannel(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Channel",
            created_by=None,
            updated_by=None,
        )
        db_session.add(channel)
        db_session.commit()

        assert channel.created_by is None
        assert channel.updated_by is None

    def test_notification_event_null_created_by(self, db_session: Session, test_tenant):
        """Test that NULL created_by is allowed for append-only table"""
        from app.models.core import EntityType
        from app.models.system import NotificationEvent, NotificationType

        # Create notification type
        notif_type = NotificationType(
            tenant_id=test_tenant.id,
            code="TEST_TYPE",
            name="Test Type",
            audience="tenant",
        )
        db_session.add(notif_type)
        db_session.commit()

        # Create entity type
        entity_type = EntityType(
            tenant_id=test_tenant.id,
            code="TEST_ENTITY",
            name="Test Entity",
        )
        db_session.add(entity_type)
        db_session.commit()

        # Create event with NULL created_by
        event = NotificationEvent(
            tenant_id=test_tenant.id,
            notification_type_code="TEST_TYPE",
            entity_type_code="TEST_ENTITY",
            entity_id=str(uuid.uuid4()),
            created_by=None,
        )
        db_session.add(event)
        db_session.commit()

        assert event.created_by is None


class TestServiceTablesAuditFK:
    """Test FK constraint enforcement for app_service* tables"""

    def test_app_service_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import AppService, AppServiceCategory, AppServiceProvider

        # Create required category and provider first
        category = AppServiceCategory(
            tenant_id=test_tenant.id,
            code="TEST_CAT",
            name="Test Category",
        )
        db_session.add(category)

        provider = AppServiceProvider(
            tenant_id=test_tenant.id,
            code="TEST_PROV",
            name="Test Provider",
        )
        db_session.add(provider)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        service = AppService(
            tenant_id=test_tenant.id,
            name="Test Service",
            category_code="TEST_CAT",
            provider_code="TEST_PROV",
            created_by=invalid_user_id,
        )
        db_session.add(service)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_app_service_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_app_service_category_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import AppServiceCategory

        invalid_user_id = uuid.uuid4()
        category = AppServiceCategory(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Category",
            created_by=invalid_user_id,
        )
        db_session.add(category)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_app_service_category_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_app_service_provider_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import AppServiceProvider

        invalid_user_id = uuid.uuid4()
        provider = AppServiceProvider(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test Provider",
            created_by=invalid_user_id,
        )
        db_session.add(provider)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_app_service_provider_created_by" in str(exc_info.value)
        db_session.rollback()


class TestValidAuditReferencesAccepted:
    """Test that valid audit references work correctly across all tables"""

    def test_all_task_1_tables_accept_valid_created_by(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that all Task 1 tables accept valid created_by user ID"""
        from app.models.auth import PasswordPolicy, SsoProvider
        from app.models.billing import Currency
        from app.models.core import EntityType, PlatformRole
        from app.models.crm import AddressType, ContactType
        from app.models.quoting import QcoLineType, QplContactActionType, TaxabilityCode
        from app.models.system import (
            NotificationChannel,
            NotificationType,
            WebhookEventType,
        )

        # Test a representative sample of tables
        records = [
            AddressType(
                tenant_id=test_tenant.id,
                code="T1",
                name="Test 1",
                created_by=test_user.id,
            ),
            ContactType(
                tenant_id=test_tenant.id,
                code="T2",
                name="Test 2",
                created_by=test_user.id,
            ),
            EntityType(
                tenant_id=test_tenant.id,
                code="T3",
                name="Test 3",
                created_by=test_user.id,
            ),
            Currency(
                tenant_id=test_tenant.id,
                code="TST",
                name="Test Currency",
                symbol="T",
                created_by=test_user.id,
            ),
            TaxabilityCode(
                tenant_id=test_tenant.id,
                code="T4",
                name="Test 4",
                created_by=test_user.id,
            ),
            NotificationChannel(
                tenant_id=test_tenant.id,
                code="T5",
                name="Test 5",
                created_by=test_user.id,
            ),
            NotificationType(
                tenant_id=test_tenant.id,
                code="T6",
                name="Test 6",
                audience="tenant",  # Required field
                created_by=test_user.id,
            ),
            SsoProvider(
                tenant_id=test_tenant.id,
                code="T7",
                name="Test 7",
                created_by=test_user.id,
            ),
            PasswordPolicy(
                tenant_id=test_tenant.id,
                name="Test 8",
                min_length=8,
                created_by=test_user.id,
            ),
            PlatformRole(code="T9", name="Test 9", created_by=test_user.id),
            WebhookEventType(
                tenant_id=test_tenant.id,
                code="T10",
                name="Test 10",
                created_by=test_user.id,
            ),
            QcoLineType(
                tenant_id=test_tenant.id,
                code="T11",
                name="Test 11",
                created_by=test_user.id,
            ),
            QplContactActionType(
                tenant_id=test_tenant.id,
                code="T12",
                name="Test 12",
                created_by=test_user.id,
            ),
        ]

        for record in records:
            db_session.add(record)

        db_session.commit()

        # Verify all records were created with correct created_by
        for record in records:
            assert record.created_by == test_user.id
