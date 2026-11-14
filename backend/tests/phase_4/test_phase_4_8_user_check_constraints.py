"""
Test Suite: Phase 4.8 Task 1 - Replace Legacy User Check Constraints

Tests modern platform role assignment - final constraint logic alignment.

This test suite verifies that:
1. Platform users MUST have a platform_role_code (boolean logic, not hardcoded roles)
2. Platform users can be assigned ANY valid role code (constraint doesn't hardcode specific values)
3. Regular users MUST NOT have a platform_role_code
4. All platform users MUST have MFA enforced

Reference: dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md - Phase 1, Task 1
Authority: dev-docs/db-design/aevofab-db-schema-v2.6h.json

Migration: 2026_04_08_1313-3ca8bf106191_phase_4_8_replace_user_check_.py
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.core import PlatformRole, User


class TestUserPlatformRoleConstraints:
    """Test updated user table CHECK constraints - Phase 4.8 Task 1"""

    def test_platform_user_requires_role(self, db_session: Session):
        """Platform users MUST have a platform_role_code (user_platform_role_chk)"""
        user = User(
            email="platform@pilotfortrades.com",
            is_platform_user=True,
            platform_role_code=None,  # Invalid! Platform user needs a role
            mfa_enforced=True,
        )
        db_session.add(user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "user_platform_role_chk" in str(exc_info.value)
        db_session.rollback()

    def test_platform_user_can_use_any_role_code(self, db_session: Session):
        """
        Platform users can be assigned ANY valid role code (constraint uses boolean logic).

        The old constraint hardcoded 'staff' and 'superadmin' as the only allowed values.
        The new constraint uses is_platform_user flag instead, so it doesn't restrict
        which specific role codes can be used - it only requires that platform users
        HAVE a role code (not NULL).

        This test verifies the constraint accepts any non-NULL string value for
        platform_role_code when is_platform_user=True, proving it doesn't hardcode
        specific role values.
        """
        # Create a test platform role to satisfy the foreign key constraint
        test_role = PlatformRole(
            code="test_role",
            name="Test Role",
            description="Test role for constraint validation",
        )
        db_session.add(test_role)
        db_session.commit()

        # Now create a platform user with this role
        user = User(
            email="test_platform@pilotfortrades.com",
            is_platform_user=True,
            platform_role_code="test_role",  # Uses test role, not hardcoded 'staff'/'superadmin'
            mfa_enforced=True,
        )
        db_session.add(user)
        db_session.commit()

        # Verify created successfully
        result = db_session.exec(
            select(User).where(User.email == "test_platform@pilotfortrades.com")
        ).first()
        assert result is not None
        assert result.platform_role_code == "test_role"
        assert result.is_platform_user is True
        assert result.mfa_enforced is True

        # Clean up (delete user first, then role due to FK constraint)
        db_session.delete(result)
        db_session.commit()
        db_session.delete(test_role)
        db_session.commit()

    def test_tenant_user_cannot_have_platform_role(self, db_session: Session):
        """Regular users MUST NOT have platform_role_code (user_platform_role_chk)"""
        user = User(
            email="regular@tenant.com",
            is_platform_user=False,
            platform_role_code="owner",  # Invalid! Regular user cannot have platform role
            mfa_enforced=False,
        )
        db_session.add(user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "user_platform_role_chk" in str(exc_info.value)
        db_session.rollback()

    def test_platform_user_must_have_mfa(self, db_session: Session):
        """All platform users MUST have MFA enforced (user_platform_mfa_required_chk)"""
        user = User(
            email="platform@pilotfortrades.com",
            is_platform_user=True,
            platform_role_code="owner",
            mfa_enforced=False,  # Invalid! Platform user requires MFA
        )
        db_session.add(user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "user_platform_mfa_required_chk" in str(exc_info.value)
        db_session.rollback()
