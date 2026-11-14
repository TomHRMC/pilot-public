"""
Test Suite: Phase 6.0.1 Task 2 - Customer & Site Audit FK Constraints

Validates Foreign Key constraint enforcement on created_by and updated_by columns
for customer and site management tables.

Reference: dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md - Task 2
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.ai import ConversationSession
from app.models.auth import ContactPortalInvite
from app.models.core import Tenant, User
from app.models.crm import (
    Address,
    Contact,
    ContactEndpoint,
    Customer,
    CustomerLifecycleStatus,
    EntityAddress,
    EntityContact,
    Site,
    SiteLifecycleStatus,
)


class TestCustomerAuditFKConstraints:
    """Test FK constraint enforcement on customer table audit columns"""

    def test_customer_created_by_fk_enforcement(
        self, db_session: Session, test_tenant: Tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        invalid_user_id = uuid.uuid4()
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            created_by=invalid_user_id,
        )
        db_session.add(customer)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_customer_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_customer_updated_by_fk_enforcement(
        self, db_session: Session, test_tenant: Tenant, test_user: User
    ):
        """Test that invalid updated_by user ID is rejected"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            created_by=test_user.id,
        )
        db_session.add(customer)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        customer.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_customer_updated_by" in str(exc_info.value)
        db_session.rollback()

    def test_customer_valid_audit_columns(
        self, db_session: Session, test_tenant: Tenant, test_user: User
    ):
        """Test that valid created_by and updated_by user IDs are accepted"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(customer)
        db_session.commit()

        assert customer.created_by == test_user.id
        assert customer.updated_by == test_user.id

    def test_customer_null_audit_columns_allowed(
        self, db_session: Session, test_tenant: Tenant
    ):
        """Test that NULL created_by and updated_by are allowed for backward compatibility"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            created_by=None,
            updated_by=None,
        )
        db_session.add(customer)
        db_session.commit()

        assert customer.created_by is None
        assert customer.updated_by is None


class TestSiteAuditFKConstraints:
    """Test FK constraint enforcement on site table audit columns"""

    def test_site_created_by_fk_enforcement(
        self, db_session: Session, test_tenant: Tenant, test_user: User
    ):
        """Test that invalid created_by user ID is rejected"""
        # Create customer first
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            created_by=test_user.id,
        )
        db_session.add(customer)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        site = Site(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="Test Site",
            created_by=invalid_user_id,
        )
        db_session.add(site)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_site_created_by" in str(exc_info.value)
        db_session.rollback()


class TestContactAuditFKConstraints:
    """Test FK constraint enforcement on contact table audit columns"""

    def test_contact_created_by_fk_enforcement(
        self, db_session: Session, test_user: User, test_tenant: Tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        invalid_user_id = uuid.uuid4()
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="John",
            last_name="Doe",
            created_by=invalid_user_id,
        )
        db_session.add(contact)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_contact_created_by" in str(exc_info.value)
        db_session.rollback()


class TestAddressAuditFKConstraints:
    """Test FK constraint enforcement on address table audit columns"""

    def test_address_created_by_fk_enforcement(self, db_session: Session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        invalid_user_id = uuid.uuid4()
        address = Address(
            tenant_id=test_tenant.id,
            line1="123 Main St",
            city="Springfield",
            created_by=invalid_user_id,
        )
        db_session.add(address)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_address_created_by" in str(exc_info.value)
        db_session.rollback()


class TestConversationSessionAuditFKConstraints:
    """Test FK constraint enforcement on conversation_session table audit columns"""

    def test_conversation_session_created_by_fk_enforcement(
        self, db_session: Session, test_tenant: Tenant, test_user: User
    ):
        """Test that invalid created_by user ID is rejected"""
        invalid_user_id = uuid.uuid4()
        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            created_by=invalid_user_id,
        )
        db_session.add(session)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_conversation_session_created_by" in str(exc_info.value)
        db_session.rollback()


class TestContactPortalInviteAuditFKConstraints:
    """Test FK constraint enforcement on contact_portal_invite (append-only) table"""

    def test_contact_portal_invite_created_by_fk_enforcement(
        self, db_session: Session, test_user: User, test_tenant: Tenant
    ):
        """Test that invalid created_by user ID is rejected (append-only table)"""
        # Create contact first
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            created_by=test_user.id,
        )
        db_session.add(contact)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        from datetime import UTC, datetime, timedelta

        invite = ContactPortalInvite(
            tenant_id=test_tenant.id,
            contact_id=contact.id,
            email="jane@example.com",
            token_hash="test_hash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            created_by=invalid_user_id,
        )
        db_session.add(invite)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_contact_portal_invite_created_by" in str(exc_info.value)
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted (ON DELETE RESTRICT)"""

    def test_user_deletion_blocked_by_customer_audit(
        self, db_session: Session, test_tenant: Tenant, test_user: User
    ):
        """Test ON DELETE RESTRICT behavior for customer audit trail"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            created_by=test_user.id,
        )
        db_session.add(customer)
        db_session.commit()

        # Attempt to delete user (should fail due to RESTRICT)
        db_session.delete(test_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # User deletion is blocked by FK constraints (may be tenant_user or customer)
        assert "ForeignKeyViolation" in str(
            exc_info.value
        ) or "fk_customer_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_user_deletion_blocked_by_site_audit(
        self, db_session: Session, test_tenant: Tenant, test_user: User
    ):
        """Test ON DELETE RESTRICT behavior for site audit trail"""
        # Create customer
        customer = Customer(
            tenant_id=test_tenant.id, display_name=f"Test Customer {uuid.uuid4()}"
        )
        db_session.add(customer)
        db_session.commit()

        # Create site with audit reference
        site = Site(
            tenant_id=test_tenant.id,
            customer_id=customer.id,
            name="Test Site",
            created_by=test_user.id,
        )
        db_session.add(site)
        db_session.commit()

        # Attempt to delete user
        db_session.delete(test_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # User deletion is blocked by FK constraints (may be tenant_user or site)
        assert "ForeignKeyViolation" in str(
            exc_info.value
        ) or "fk_site_created_by" in str(exc_info.value)
        db_session.rollback()


class TestLifecycleStatusAuditFKConstraints:
    """Test FK constraint enforcement on lifecycle status tables"""

    def test_customer_lifecycle_status_created_by_fk_enforcement(
        self, db_session: Session, test_tenant: Tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        invalid_user_id = uuid.uuid4()
        status = CustomerLifecycleStatus(
            tenant_id=test_tenant.id,
            code="test",
            name="Test Status",
            created_by=invalid_user_id,
        )
        db_session.add(status)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_customer_lifecycle_status_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_site_lifecycle_status_created_by_fk_enforcement(
        self, db_session: Session, test_tenant: Tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        invalid_user_id = uuid.uuid4()
        status = SiteLifecycleStatus(
            tenant_id=test_tenant.id,
            code="test",
            name="Test Status",
            created_by=invalid_user_id,
        )
        db_session.add(status)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_site_lifecycle_status_created_by" in str(exc_info.value)
        db_session.rollback()


class TestPolymorphicAuditFKConstraints:
    """Test FK constraint enforcement on polymorphic mapping tables"""

    def test_entity_address_created_by_fk_enforcement(
        self, db_session: Session, test_user: User, test_tenant: Tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        # Create address first
        address = Address(
            tenant_id=test_tenant.id,
            line1="123 Main St",
            city="Springfield",
            created_by=test_user.id,
        )
        db_session.add(address)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        entity_address = EntityAddress(
            tenant_id=test_tenant.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            address_id=address.id,
            address_type_code="billing",
            created_by=invalid_user_id,
        )
        db_session.add(entity_address)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_entity_address_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_entity_contact_created_by_fk_enforcement(
        self, db_session: Session, test_user: User, test_tenant: Tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        # Create contact first
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="John",
            last_name="Doe",
            created_by=test_user.id,
        )
        db_session.add(contact)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        entity_contact = EntityContact(
            tenant_id=test_tenant.id,
            entity_type_code="customer",
            entity_id=uuid.uuid4(),
            contact_id=contact.id,
            contact_type_code="primary",
            created_by=invalid_user_id,
        )
        db_session.add(entity_contact)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_entity_contact_created_by" in str(exc_info.value)
        db_session.rollback()


class TestContactEndpointAuditFKConstraints:
    """Test FK constraint enforcement on contact_endpoint table"""

    def test_contact_endpoint_created_by_fk_enforcement(
        self, db_session: Session, test_user: User, test_tenant: Tenant
    ):
        """Test that invalid created_by user ID is rejected"""
        # Create contact first
        contact = Contact(
            tenant_id=test_tenant.id,
            first_name="John",
            last_name="Doe",
            created_by=test_user.id,
        )
        db_session.add(contact)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        endpoint = ContactEndpoint(
            tenant_id=test_tenant.id,
            contact_id=contact.id,
            channel="email",
            value="test@example.com",
            created_by=invalid_user_id,
        )
        db_session.add(endpoint)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_contact_endpoint_created_by" in str(exc_info.value)
        db_session.rollback()
