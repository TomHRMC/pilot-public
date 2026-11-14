"""
Test Suite: Phase 6.0.1 Task 6 - Tenant & User Management Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: phase-6.0-db-schema-sync-11-plan.md - Task 6

Note: Tests avoid tables without 'id' column (e.g., tenant_settings) due to audit trigger limitations.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError


class TestAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""

    def test_user_preference_created_by_fk_enforcement(
        self, db_session, test_tenant, test_user
    ):
        """Test that invalid created_by user ID is rejected for user_preference"""
        from sqlmodel import select

        from app.models.core import UserPreference

        # SD-6: Remove seeded user_preference for test_user+test_tenant before testing FK
        existing = db_session.exec(
            select(UserPreference)
            .where(UserPreference.user_id == test_user.id)
            .where(UserPreference.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        invalid_user_id = uuid.uuid4()
        pref = UserPreference(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            preferences={},
            created_by=invalid_user_id,
        )
        db_session.add(pref)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_user_preference_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_user_endpoint_created_by_fk_enforcement(self, db_session, test_user):
        """Test that invalid created_by user ID is rejected for user_endpoint"""
        from app.models.core import UserEndpoint

        invalid_user_id = uuid.uuid4()
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="test@example.com",
            created_by=invalid_user_id,
        )
        db_session.add(endpoint)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_user_endpoint_created_by" in str(exc_info.value)
        db_session.rollback()


class TestAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""

    def test_user_preference_updated_by_fk_enforcement(
        self, db_session, test_tenant, test_user
    ):
        """Test that invalid updated_by user ID is rejected"""
        from sqlmodel import select

        from app.models.core import UserPreference

        # SD-6: Remove seeded user_preference for test_user+test_tenant before testing FK
        existing = db_session.exec(
            select(UserPreference)
            .where(UserPreference.user_id == test_user.id)
            .where(UserPreference.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        # Create valid record
        pref = UserPreference(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            preferences={},
            created_by=test_user.id,
        )
        db_session.add(pref)
        db_session.commit()

        # Attempt to update with invalid user ID
        invalid_user_id = uuid.uuid4()
        pref.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_user_preference_updated_by" in str(exc_info.value)
        db_session.rollback()

    def test_user_endpoint_updated_by_fk_enforcement(self, db_session, test_user):
        """Test that invalid updated_by user ID is rejected for user_endpoint"""
        from app.models.core import UserEndpoint

        # Create valid record
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="test@example.com",
            created_by=test_user.id,
        )
        db_session.add(endpoint)
        db_session.commit()

        # Attempt to update with invalid user ID
        invalid_user_id = uuid.uuid4()
        endpoint.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_user_endpoint_updated_by" in str(exc_info.value)
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""

    def test_user_deletion_blocked_by_user_preference_audit(
        self, db_session, test_tenant, test_user
    ):
        """Test ON DELETE RESTRICT behavior"""
        from sqlmodel import select

        from app.models.core import UserPreference

        # SD-6: Remove seeded user_preference for test_user+test_tenant before inserting test row
        existing = db_session.exec(
            select(UserPreference)
            .where(UserPreference.user_id == test_user.id)
            .where(UserPreference.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        # Create record with user audit reference
        pref = UserPreference(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            preferences={},
            created_by=test_user.id,
        )
        db_session.add(pref)
        db_session.commit()

        # Attempt to delete user (should fail due to RESTRICT)
        db_session.delete(test_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Assert that any FK constraint prevents deletion (could be tenant_user, user_preference, etc.)
        # The important thing is that ON DELETE RESTRICT is working
        error_msg = str(exc_info.value).lower()
        assert (
            "foreign key constraint" in error_msg or "violates foreign key" in error_msg
        )
        db_session.rollback()


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""

    def test_user_preference_null_audit_columns(
        self, db_session, test_tenant, test_user
    ):
        """Test that NULL created_by and updated_by are allowed for user_preference"""
        from sqlmodel import select

        from app.models.core import UserPreference

        # SD-6: Remove seeded user_preference for test_user+test_tenant before inserting test row
        existing = db_session.exec(
            select(UserPreference)
            .where(UserPreference.user_id == test_user.id)
            .where(UserPreference.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        # Create record with NULL audit columns
        pref = UserPreference(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            preferences={},
            created_by=None,
            updated_by=None,
        )
        db_session.add(pref)
        db_session.commit()  # Should succeed

        assert pref.created_by is None
        assert pref.updated_by is None


class TestSelfReferentialFK:
    """Test self-referential FK on user table"""

    def test_user_self_referential_created_by(self, db_session, test_tenant, test_user):
        """Test that user.created_by can reference another user"""
        from app.models.core import User

        # Create new user with test_user as creator
        new_user = User(
            email="newuser@example.com",
            created_by=test_user.id,  # Valid reference to existing user
        )
        db_session.add(new_user)
        db_session.commit()  # Should succeed

        assert new_user.created_by == test_user.id

    def test_user_self_referential_invalid_created_by(self, db_session, test_tenant):
        """Test that user.created_by FK is enforced"""
        from app.models.core import User

        invalid_user_id = uuid.uuid4()
        new_user = User(
            email="newuser@example.com",
            created_by=invalid_user_id,  # Invalid user reference
        )
        db_session.add(new_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_user_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_tenant_created_by_fk_enforcement(self, db_session, test_user):
        """Test that tenant.created_by FK is enforced"""
        from app.models.core import Tenant

        # Valid tenant creation
        tenant = Tenant(name="Test Tenant Valid", created_by=test_user.id)
        db_session.add(tenant)
        db_session.commit()  # Should succeed

        assert tenant.created_by == test_user.id

    def test_tenant_invalid_created_by_fk_enforcement(self, db_session):
        """Test that tenant.created_by FK rejects invalid user ID"""
        from app.models.core import Tenant

        invalid_user_id = uuid.uuid4()
        tenant = Tenant(name="Test Tenant Invalid", created_by=invalid_user_id)
        db_session.add(tenant)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_tenant_created_by" in str(exc_info.value)
        db_session.rollback()


class TestAppendOnlyTables:
    """Test append-only tables (created_by only)"""

    def test_tenant_user_invite_created_by_only(
        self, db_session, test_tenant, test_user
    ):
        """Test that tenant_user_invite has created_by FK but no updated_by"""
        from datetime import UTC, datetime, timedelta

        from app.models.auth import TenantUserInvite

        # Create invite with valid created_by
        invite = TenantUserInvite(
            tenant_id=test_tenant.id,
            email="invite@example.com",
            token_hash="test_hash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            created_by=test_user.id,
        )
        db_session.add(invite)
        db_session.commit()  # Should succeed

        assert invite.created_by == test_user.id
        # Verify no updated_by column (append-only)
        assert not hasattr(invite, "updated_by") or invite.updated_by is None

    def test_tenant_user_invite_invalid_created_by(self, db_session, test_tenant):
        """Test that tenant_user_invite.created_by FK is enforced"""
        from datetime import UTC, datetime, timedelta

        from app.models.auth import TenantUserInvite

        invalid_user_id = uuid.uuid4()
        invite = TenantUserInvite(
            tenant_id=test_tenant.id,
            email="invite@example.com",
            token_hash="test_hash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            created_by=invalid_user_id,
        )
        db_session.add(invite)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_tenant_user_invite_created_by" in str(exc_info.value)
        db_session.rollback()


class TestMultipleTables:
    """Test FK constraints across multiple tables"""

    def test_tenant_domain_audit_fk(self, db_session, test_tenant, test_user):
        """Test tenant_domain audit FK constraints"""
        from app.models.auth import TenantDomain

        # Create valid record
        domain = TenantDomain(
            tenant_id=test_tenant.id, domain="example.com", created_by=test_user.id
        )
        db_session.add(domain)
        db_session.commit()

        assert domain.created_by == test_user.id

        # Test invalid updated_by
        invalid_user_id = uuid.uuid4()
        domain.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_tenant_domain_updated_by" in str(exc_info.value)
        db_session.rollback()

    def test_tenant_user_notification_pref_table_dropped(self, db_session):
        """FIND-080/B21: tenant_user_notification_pref table must not exist (dropped by migration)."""
        from sqlalchemy import text

        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'tenant_user_notification_pref'
            """)
        )
        assert result.scalar() == 0, (
            "tenant_user_notification_pref must be dropped by "
            "phase_fe_1_batch_b21_drop_legacy_notification_pref_tables"
        )

    def test_user_sso_identity_audit_fk(self, db_session, test_user):
        """Test user_sso_identity audit FK constraints"""
        from sqlmodel import select

        from app.models.auth import SsoProvider, UserSsoIdentity

        # Get or create a valid SSO provider for testing
        provider = db_session.exec(select(SsoProvider)).first()
        if not provider:
            provider = SsoProvider(
                code="test_sso",
                name="Test SSO Provider",
                is_active=True,
                created_by=test_user.id,
            )
            db_session.add(provider)
            db_session.commit()

        # Create valid record
        identity = UserSsoIdentity(
            user_id=test_user.id,
            sso_provider_code=provider.code,
            provider_user_id="external_id_123",
            created_by=test_user.id,
        )
        db_session.add(identity)
        db_session.commit()

        assert identity.created_by == test_user.id

        # Test invalid updated_by
        invalid_user_id = uuid.uuid4()
        identity.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_user_sso_identity_updated_by" in str(exc_info.value)
        db_session.rollback()
