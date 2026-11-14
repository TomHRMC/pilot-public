"""
Test Suite: Phase 4.7 Task 2 - Convert user.preferred_mfa_channel ENUM to TEXT

Tests conversion of user.preferred_mfa_channel from native PostgreSQL ENUM
to TEXT with CHECK constraint validation - final ENUM standardization for
production deployment.

Reference: phase-4.7-db-schema-sync-3-plan.md - Phase 1, Task 2
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.core import User


class TestPreferredMfaChannelEnumToText:
    """Test user.preferred_mfa_channel ENUM → TEXT conversion"""

    def test_email_channel_valid(self, db_session: Session):
        """Test 'email' value accepted"""
        user = User(
            email="mfa-email@test.com",
            preferred_mfa_channel="email",
        )
        db_session.add(user)
        db_session.commit()

        # Verify stored correctly
        result = db_session.exec(select(User).where(User.id == user.id)).first()
        assert result is not None
        assert result.preferred_mfa_channel == "email"

    def test_sms_channel_valid(self, db_session: Session):
        """Test 'sms' value accepted"""
        user = User(
            email="mfa-sms@test.com",
            preferred_mfa_channel="sms",
        )
        db_session.add(user)
        db_session.commit()

        result = db_session.exec(select(User).where(User.id == user.id)).first()
        assert result is not None
        assert result.preferred_mfa_channel == "sms"

    def test_totp_channel_valid(self, db_session: Session):
        """Test 'totp' value accepted"""
        user = User(
            email="mfa-totp@test.com",
            preferred_mfa_channel="totp",
        )
        db_session.add(user)
        db_session.commit()

        result = db_session.exec(select(User).where(User.id == user.id)).first()
        assert result is not None
        assert result.preferred_mfa_channel == "totp"

    def test_null_channel_allowed(self, db_session: Session):
        """Test NULL value accepted (users can opt out of MFA)

        Note: As of Phase 5.0, the server default is 'email' per Golden Master,
        but explicit None assignment should still work since column is nullable.
        """
        user = User(
            email="mfa-none@test.com",
            preferred_mfa_channel="email",  # Start with default
        )
        db_session.add(user)
        db_session.commit()

        # Now update to None (opt out of MFA)
        user.preferred_mfa_channel = None
        db_session.commit()

        result = db_session.exec(select(User).where(User.id == user.id)).first()
        assert result is not None
        assert result.preferred_mfa_channel is None

    def test_invalid_channel_rejected(self, db_session: Session):
        """Test invalid value rejected (e.g., 'phone')"""
        user = User(
            email="mfa-invalid@test.com",
            preferred_mfa_channel="phone",  # Invalid value
        )
        db_session.add(user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "user_preferred_mfa_channel_chk" in str(exc_info.value)

        # Rollback to clean up failed transaction
        db_session.rollback()

    def test_column_type_is_text(self, db_session: Session):
        """Verify column is TEXT type in database"""
        result = db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'user'
                  AND column_name = 'preferred_mfa_channel'
            """)
        ).first()

        assert result is not None
        assert result[1] == "text"  # data_type
        assert result[2] == "YES"  # is_nullable

    def test_enum_type_dropped(self, db_session: Session):
        """Verify native ENUM type 'preferredmfachannel' no longer exists"""
        result = db_session.execute(
            text("""
                SELECT typname
                FROM pg_type
                WHERE typname = 'preferredmfachannel'
            """)
        ).first()

        # Should return None (0 rows) - ENUM type dropped
        assert result is None


class TestMfaWorkflowIntegration:
    """Test MFA workflow still functions correctly after migration"""

    def test_user_can_update_mfa_preference(self, db_session: Session):
        """Test user can change MFA channel preference"""
        # Create user with email MFA
        user = User(
            email="mfa-update@test.com",
            preferred_mfa_channel="email",
        )
        db_session.add(user)
        db_session.commit()

        # Update to SMS
        user.preferred_mfa_channel = "sms"
        db_session.commit()

        # Verify change persisted
        result = db_session.exec(select(User).where(User.id == user.id)).first()
        assert result is not None
        assert result.preferred_mfa_channel == "sms"

        # Update to TOTP
        user.preferred_mfa_channel = "totp"
        db_session.commit()

        result = db_session.exec(select(User).where(User.id == user.id)).first()
        assert result.preferred_mfa_channel == "totp"

        # Update to NULL (opt out)
        user.preferred_mfa_channel = None
        db_session.commit()

        result = db_session.exec(select(User).where(User.id == user.id)).first()
        assert result.preferred_mfa_channel is None

    def test_default_value_is_email(self, db_session: Session):
        """Test default value for new users is 'email' per Golden Master

        Note: As of Phase 5.0, server default changed from None to 'email'
        to align with Golden Master JSON specification (aevofab-db-schema-v2.6h.json).
        """
        user = User(email="mfa-default@test.com")
        db_session.add(user)
        db_session.commit()

        result = db_session.exec(select(User).where(User.id == user.id)).first()
        assert result is not None
        # Default should be 'email' per Golden Master specification
        assert result.preferred_mfa_channel == "email"
