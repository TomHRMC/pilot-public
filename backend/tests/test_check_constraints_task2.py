"""
Test Suite: Phase 4.6 Task 2 - Missing Check Constraints
Tests platform MFA and email format validation constraints
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.auth import ContactPortalInvite, TenantUserInvite
from app.models.core import User
from app.models.crm import Contact, Customer


class TestPlatformMFAConstraint:
    """Test user_platform_mfa_required_chk constraint"""

    def test_staff_user_with_mfa_allowed(
        self, db_session: Session, test_tenant, test_platform_role_staff
    ):
        """Staff user with MFA enabled should be allowed"""
        user = User(
            email="staff@test.com",
            is_platform_user=True,
            platform_role_code="staff",
            mfa_enforced=True,
        )
        db_session.add(user)
        db_session.commit()

        # Verify the user was created
        result = db_session.exec(
            select(User).where(User.email == "staff@test.com")
        ).first()
        assert result is not None
        assert result.platform_role_code == "staff"
        assert result.mfa_enforced is True

    def test_staff_user_without_mfa_rejected(
        self, db_session: Session, test_tenant, test_platform_role_staff
    ):
        """Staff user without MFA should be rejected"""
        user = User(
            email="badstaff@test.com",
            is_platform_user=True,
            platform_role_code="staff",
            mfa_enforced=False,
        )
        db_session.add(user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "user_platform_mfa_required_chk" in str(exc_info.value)
        db_session.rollback()

    def test_superadmin_user_without_mfa_rejected(
        self, db_session: Session, test_tenant, test_platform_role_superadmin
    ):
        """Superadmin user without MFA should be rejected"""
        user = User(
            email="badsuperadmin@test.com",
            is_platform_user=True,
            platform_role_code="superadmin",
            mfa_enforced=False,
        )
        db_session.add(user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "user_platform_mfa_required_chk" in str(exc_info.value)
        db_session.rollback()

    def test_regular_user_without_mfa_allowed(self, db_session: Session, test_tenant):
        """Regular user (no platform role) without MFA should be allowed"""
        user = User(
            email="regular@test.com",
            is_platform_user=False,
            platform_role_code=None,
            mfa_enforced=False,
        )
        db_session.add(user)
        db_session.commit()

        # Verify the user was created
        result = db_session.exec(
            select(User).where(User.email == "regular@test.com")
        ).first()
        assert result is not None
        assert result.platform_role_code is None
        assert result.mfa_enforced is False


class TestContactPortalInviteEmailConstraint:
    """Test contact_portal_invite_email_chk constraint"""

    def test_valid_email_allowed(self, db_session: Session, test_tenant, test_contact):
        """Valid email format should be allowed"""
        invite = ContactPortalInvite(
            tenant_id=test_tenant.id,
            contact_id=test_contact.id,
            email="valid.email@example.com",
            token_hash="test_hash_" + str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(invite)
        db_session.commit()

        # Verify the invite was created
        result = db_session.exec(
            select(ContactPortalInvite).where(
                ContactPortalInvite.contact_id == test_contact.id
            )
        ).first()
        assert result is not None
        assert result.email == "valid.email@example.com"

    def test_invalid_email_rejected(
        self, db_session: Session, test_tenant, test_customer
    ):
        """Invalid email format should be rejected"""
        # Create a contact first
        contact = Contact(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            first_name="Test",
            last_name="Contact2",
            email="test2@example.com",
        )
        db_session.add(contact)
        db_session.commit()

        invite = ContactPortalInvite(
            tenant_id=test_tenant.id,
            contact_id=contact.id,
            email="not-an-email",
            token_hash="test_hash_" + str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(invite)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "contact_portal_invite_email_chk" in str(exc_info.value)
        db_session.rollback()

    def test_email_missing_domain_rejected(
        self, db_session: Session, test_tenant, test_customer
    ):
        """Email without proper domain should be rejected"""
        # Create a contact first
        contact = Contact(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            first_name="Test",
            last_name="Contact3",
            email="test3@example.com",
        )
        db_session.add(contact)
        db_session.commit()

        invite = ContactPortalInvite(
            tenant_id=test_tenant.id,
            contact_id=contact.id,
            email="email@",
            token_hash="test_hash_" + str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(invite)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "contact_portal_invite_email_chk" in str(exc_info.value)
        db_session.rollback()


class TestCustomerEmailConstraint:
    """Test customer_email_format_chk constraint"""

    def test_valid_email_allowed(self, db_session: Session, test_tenant):
        """Valid email format should be allowed"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Valid Email Customer",
            email="customer@example.com",
        )
        db_session.add(customer)
        db_session.commit()

        # Verify the customer was created
        result = db_session.exec(
            select(Customer).where(Customer.display_name == "Valid Email Customer")
        ).first()
        assert result is not None
        assert result.email == "customer@example.com"

    def test_null_email_allowed(self, db_session: Session, test_tenant):
        """NULL email should be allowed (nullable field)"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="No Email Customer",
            email=None,
        )
        db_session.add(customer)
        db_session.commit()

        # Verify the customer was created
        result = db_session.exec(
            select(Customer).where(Customer.display_name == "No Email Customer")
        ).first()
        assert result is not None
        assert result.email is None

    def test_invalid_email_rejected(self, db_session: Session, test_tenant):
        """Invalid email format should be rejected"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Invalid Email Customer",
            email="not.an.email",
        )
        db_session.add(customer)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "customer_email_format_chk" in str(exc_info.value)
        db_session.rollback()


class TestTenantUserInviteEmailConstraint:
    """Test tenant_user_invite_email_format_chk constraint"""

    def test_valid_email_allowed(self, db_session: Session, test_tenant, test_user):
        """Valid email format should be allowed"""
        invite = TenantUserInvite(
            tenant_id=test_tenant.id,
            email="invite@example.com",
            token_hash="test_hash_" + str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            invited_by=test_user.id,
        )
        db_session.add(invite)
        db_session.commit()

        # Verify the invite was created
        result = db_session.exec(
            select(TenantUserInvite).where(
                TenantUserInvite.email == "invite@example.com"
            )
        ).first()
        assert result is not None
        assert result.email == "invite@example.com"

    def test_invalid_email_rejected(self, db_session: Session, test_tenant, test_user):
        """Invalid email format should be rejected"""
        invite = TenantUserInvite(
            tenant_id=test_tenant.id,
            email="invalid-email",
            token_hash="test_hash_" + str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            invited_by=test_user.id,
        )
        db_session.add(invite)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "tenant_user_invite_email_format_chk" in str(exc_info.value)
        db_session.rollback()

    def test_complex_email_allowed(self, db_session: Session, test_tenant, test_user):
        """Complex but valid email should be allowed"""
        invite = TenantUserInvite(
            tenant_id=test_tenant.id,
            email="user.name+tag@sub.example.co.uk",
            token_hash="test_hash_" + str(uuid.uuid4()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            invited_by=test_user.id,
        )
        db_session.add(invite)
        db_session.commit()

        # Verify the invite was created
        result = db_session.exec(
            select(TenantUserInvite).where(
                TenantUserInvite.email == "user.name+tag@sub.example.co.uk"
            )
        ).first()
        assert result is not None
        assert result.email == "user.name+tag@sub.example.co.uk"


class TestCheckConstraintsExist:
    """Verify all 4 check constraints exist in database"""

    def test_all_constraints_exist(self, db_session: Session):
        """Verify all 4 constraints exist"""
        result = db_session.execute(
            text("""
                SELECT conname, conrelid::regclass
                FROM pg_constraint
                WHERE conname IN (
                    'user_platform_mfa_required_chk',
                    'contact_portal_invite_email_chk',
                    'customer_email_format_chk',
                    'tenant_user_invite_email_format_chk'
                )
                ORDER BY conname
            """)
        )
        constraints = result.fetchall()
        assert len(constraints) == 4

        constraint_names = [c[0] for c in constraints]
        assert "user_platform_mfa_required_chk" in constraint_names
        assert "contact_portal_invite_email_chk" in constraint_names
        assert "customer_email_format_chk" in constraint_names
        assert "tenant_user_invite_email_format_chk" in constraint_names
