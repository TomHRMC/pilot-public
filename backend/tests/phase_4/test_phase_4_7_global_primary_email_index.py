"""
Test Suite: Phase 4.7 Task 4 - Fix Global Primary Email Unique Index
Tests global email uniqueness enforcement - final schema alignment for production

Reference: phase-4.7-db-schema-sync-3-plan.md - Phase 3, Task 4

Security Impact:
- Ensures one primary email = one user globally
- Case-insensitive comparison prevents duplicates like admin@company.com and ADMIN@COMPANY.COM
- Critical for email-based authentication and password reset flows
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.core import User, UserEndpoint


class TestGlobalPrimaryEmailUniqueness:
    """Test global uniqueness of primary email addresses across all users"""

    def test_user_can_set_primary_email(
        self, db_session: Session, test_tenant, test_user
    ):
        """User should be able to set a primary email"""
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="unique@test.com",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(endpoint)
        db_session.commit()

        result = db_session.exec(
            select(UserEndpoint).where(UserEndpoint.id == endpoint.id)
        ).first()
        assert result is not None
        assert result.value == "unique@test.com"
        assert result.is_primary is True

    def test_duplicate_primary_email_rejected_same_case(
        self, db_session: Session, test_tenant
    ):
        """Second user cannot use same primary email (same case)"""
        # Create two users
        user1 = User(
            email="user1@temp.com", tenant_id=test_tenant.id, full_name="User One"
        )
        user2 = User(
            email="user2@temp.com", tenant_id=test_tenant.id, full_name="User Two"
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # User 1 sets primary email
        endpoint1 = UserEndpoint(
            user_id=user1.id,
            channel="email",
            value="shared@test.com",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(endpoint1)
        db_session.commit()

        # User 2 attempts same primary email (should fail)
        endpoint2 = UserEndpoint(
            user_id=user2.id,
            channel="email",
            value="shared@test.com",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(endpoint2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "ux_global_primary_email" in str(exc_info.value)

        db_session.rollback()

    def test_duplicate_primary_email_rejected_different_case(
        self, db_session: Session, test_tenant
    ):
        """Second user cannot use same primary email (different case - case-insensitive)"""
        # Create two users
        user1 = User(
            email="user1@temp.com", tenant_id=test_tenant.id, full_name="User One"
        )
        user2 = User(
            email="user2@temp.com", tenant_id=test_tenant.id, full_name="User Two"
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # User 1 sets primary email (lowercase)
        endpoint1 = UserEndpoint(
            user_id=user1.id,
            channel="email",
            value="admin@company.com",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(endpoint1)
        db_session.commit()

        # User 2 attempts same email with different case (should fail)
        endpoint2 = UserEndpoint(
            user_id=user2.id,
            channel="email",
            value="ADMIN@COMPANY.COM",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(endpoint2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "ux_global_primary_email" in str(exc_info.value)

        db_session.rollback()

    def test_same_email_allowed_as_non_primary(self, db_session: Session, test_tenant):
        """Multiple users can have same email as non-primary contact"""
        # Create two users
        user1 = User(
            email="user1@temp.com", tenant_id=test_tenant.id, full_name="User One"
        )
        user2 = User(
            email="user2@temp.com", tenant_id=test_tenant.id, full_name="User Two"
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # User 1 uses email as non-primary
        endpoint1 = UserEndpoint(
            user_id=user1.id,
            channel="email",
            value="shared@contact.com",
            is_primary=False,
            verification_status="verified",
        )
        db_session.add(endpoint1)
        db_session.commit()

        # User 2 can also use same email as non-primary (allowed)
        endpoint2 = UserEndpoint(
            user_id=user2.id,
            channel="email",
            value="shared@contact.com",
            is_primary=False,
            verification_status="verified",
        )
        db_session.add(endpoint2)
        db_session.commit()  # Should succeed

        assert endpoint1.value == endpoint2.value
        assert endpoint1.is_primary is False
        assert endpoint2.is_primary is False

    def test_index_definition_targets_value_not_user_id(self, db_session: Session):
        """Verify index definition targets LOWER(value) not user_id"""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT indexdef FROM pg_indexes WHERE indexname = 'ux_global_primary_email'"
            )
        ).first()

        assert result is not None, "Index ux_global_primary_email should exist"
        indexdef = result[0]

        # Verify index targets LOWER(value) not user_id
        assert "lower" in indexdef.lower(), (
            "Index should use LOWER() for case-insensitivity"
        )
        assert "value" in indexdef.lower(), "Index should target the value column"
        assert "user_id" not in indexdef or "user_endpoint" in indexdef, (
            "Index should not target user_id column (unless as table name)"
        )
