"""
Test Suite: Phase 4 Task 12 - Partial Unique Indexes (Email Endpoint Logic)
Tests partial unique indexes on user_endpoint from Golden Master v2.6h
"""

from sqlalchemy import text
from sqlmodel import Session

from app.models.core import User, UserEndpoint


class TestUserEmailPrimaryIndex:
    """Test ux_user_email_primary: Only one primary email per user"""

    def test_multiple_non_primary_emails_allowed(self, db_session: Session):
        """User can have multiple non-primary emails"""
        # Create test user
        user = User(
            email="testuser@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create multiple non-primary emails
        email1 = UserEndpoint(
            user_id=user.id,
            channel="email",
            value="work@company.com",
            is_primary=False,
            verification_status="verified",
        )
        email2 = UserEndpoint(
            user_id=user.id,
            channel="email",
            value="personal@gmail.com",
            is_primary=False,
            verification_status="pending",
        )
        db_session.add(email1)
        db_session.add(email2)
        db_session.commit()

        # Should succeed - both are non-primary
        assert email1.id is not None
        assert email2.id is not None

    def test_one_primary_email_allowed(self, db_session: Session):
        """User can have one primary email"""
        # Create test user
        user = User(
            email="testuser2@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create one primary email
        email = UserEndpoint(
            user_id=user.id,
            channel="email",
            value="primary@company.com",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(email)
        db_session.commit()

        # Should succeed
        assert email.id is not None

    def test_two_primary_emails_auto_demoted(self, db_session: Session):
        """When setting a second email to primary, the first is auto-demoted by trigger"""
        # Create test user
        user = User(
            email="testuser3@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create first primary email
        email1 = UserEndpoint(
            user_id=user.id,
            channel="email",
            value="first@company.com",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(email1)
        db_session.commit()
        db_session.refresh(email1)

        # Create second primary email - trigger will auto-demote the first
        email2 = UserEndpoint(
            user_id=user.id,
            channel="email",
            value="second@company.com",
            is_primary=True,
            verification_status="pending",
        )
        db_session.add(email2)
        db_session.commit()

        # Refresh to see current state
        db_session.refresh(email1)
        db_session.refresh(email2)

        # Verify: email1 was auto-demoted, email2 is now primary
        assert email1.is_primary == False, "First email should be auto-demoted"
        assert email2.is_primary == True, "Second email should be primary"

        # Verify only one primary email exists in database
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM user_endpoint
                WHERE user_id = :user_id AND channel = 'email' AND is_primary = true
            """),
            {"user_id": str(user.id)},
        )
        count = result.scalar()
        assert count == 1, "Only one primary email should exist"


class TestGlobalPrimaryIndex:
    """Test ux_global_primary_email: Only one primary endpoint of ANY type per user"""

    def test_primary_email_and_non_primary_phone_allowed(self, db_session: Session):
        """User can have primary email and non-primary phone"""
        # Create test user
        user = User(
            email="testuser4@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create primary email
        email = UserEndpoint(
            user_id=user.id,
            channel="email",
            value="user@company.com",
            is_primary=True,
            verification_status="verified",
        )
        # Create non-primary phone
        phone = UserEndpoint(
            user_id=user.id,
            channel="sms",
            value="+15551234567",
            is_primary=False,
            verification_status="verified",
        )
        db_session.add(email)
        db_session.add(phone)
        db_session.commit()

        # Should succeed - only one primary
        assert email.id is not None
        assert phone.id is not None

    def test_primary_phone_and_non_primary_email_allowed(self, db_session: Session):
        """User can have primary phone and non-primary email"""
        # Create test user
        user = User(
            email="testuser5@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create primary phone
        phone = UserEndpoint(
            user_id=user.id,
            channel="sms",
            value="+15551234567",
            is_primary=True,
            verification_status="verified",
        )
        # Create non-primary email
        email = UserEndpoint(
            user_id=user.id,
            channel="email",
            value="user@company.com",
            is_primary=False,
            verification_status="verified",
        )
        db_session.add(phone)
        db_session.add(email)
        db_session.commit()

        # Should succeed - only one primary
        assert phone.id is not None
        assert email.id is not None

    def test_primary_email_and_primary_phone_allowed(self, db_session: Session):
        """User CAN have both a primary email and a primary phone (different channels).

        The ux_one_primary_per_user cross-channel index was dropped.  The DB now
        enforces per-channel uniqueness only:
          - idx_user_endpoint_primary_email  (one primary email per user)
        A separate primary SMS is therefore permitted.
        """
        user = User(
            email="testuser6@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create primary email
        email = UserEndpoint(
            user_id=user.id,
            channel="email",
            value="user@company.com",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(email)
        db_session.commit()

        # Create primary phone — must succeed (no cross-channel constraint)
        phone = UserEndpoint(
            user_id=user.id,
            channel="sms",
            value="+15551234567",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(phone)
        db_session.commit()

        assert email.id is not None
        assert phone.id is not None


class TestTenantIsolation:
    """Test that different users can have their own primary emails"""

    def test_different_users_can_have_primary_emails(self, db_session: Session):
        """Different users can each have their own primary email"""
        # Create two test users
        user1 = User(
            email="user1@example.com",
            first_name="User",
            last_name="One",
            is_active=True,
        )
        user2 = User(
            email="user2@example.com",
            first_name="User",
            last_name="Two",
            is_active=True,
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        db_session.refresh(user1)
        db_session.refresh(user2)

        # Create primary email for user1
        email1 = UserEndpoint(
            user_id=user1.id,
            channel="email",
            value="primary1@company.com",
            is_primary=True,
            verification_status="verified",
        )
        # Create primary email for user2
        email2 = UserEndpoint(
            user_id=user2.id,
            channel="email",
            value="primary2@company.com",
            is_primary=True,
            verification_status="verified",
        )
        db_session.add(email1)
        db_session.add(email2)
        db_session.commit()

        # Should succeed - different users, so no conflict
        assert email1.id is not None
        assert email2.id is not None


class TestIndexExistence:
    """Test that the partial unique indexes exist in the database"""

    def test_ux_user_email_primary_exists(self, db_session: Session):
        """Verify ux_user_email_primary index exists in database"""
        result = db_session.execute(
            text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE indexname = 'ux_user_email_primary'
        """)
        )
        index = result.fetchone()
        assert index is not None, "ux_user_email_primary index should exist"
        assert index[0] == "ux_user_email_primary"

    def test_ux_global_primary_email_exists(self, db_session: Session):
        """Verify ux_global_primary_email index exists in database"""
        result = db_session.execute(
            text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE indexname = 'ux_global_primary_email'
        """)
        )
        index = result.fetchone()
        assert index is not None, "ux_global_primary_email index should exist"
        assert index[0] == "ux_global_primary_email"

    def test_indexes_have_correct_definitions(self, db_session: Session):
        """Verify partial unique indexes have the correct WHERE clauses"""
        result = db_session.execute(
            text("""
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes
            WHERE indexname IN ('ux_user_email_primary', 'ux_global_primary_email')
            ORDER BY indexname
        """)
        )

        indexes = {row[0]: row[1] for row in result.fetchall()}

        # Verify ux_global_primary_email
        assert "ux_global_primary_email" in indexes
        assert "is_primary = true" in indexes["ux_global_primary_email"]
        assert "user_endpoint" in indexes["ux_global_primary_email"]

        # Verify ux_user_email_primary
        assert "ux_user_email_primary" in indexes
        assert "email" in indexes["ux_user_email_primary"]
        assert "is_primary = true" in indexes["ux_user_email_primary"]
        assert "user_endpoint" in indexes["ux_user_email_primary"]
