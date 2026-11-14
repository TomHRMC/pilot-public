"""
Test case-insensitive email behavior with CITEXT column type.

This test module validates that User.email uses PostgreSQL's CITEXT type
to ensure case-insensitive uniqueness and lookups, as specified in the
Golden Master database design (aevofab-db-schema-v2.6h.json).
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.core import User


def test_case_insensitive_email_uniqueness(db_session: Session) -> None:
    """
    Test that case-insensitive duplicate emails are rejected by unique constraint.

    Validates: user@test.com and USER@test.com are treated as the same email.
    """
    # Create user with lowercase email
    user1 = User(
        email="user@test.com",
        first_name="Test",
        last_name="User",
        is_platform_user=False,
    )
    db_session.add(user1)
    db_session.commit()

    # Attempt to create another user with uppercase version of same email
    user2 = User(
        email="USER@test.com",
        first_name="Another",
        last_name="User",
        is_platform_user=False,
    )
    db_session.add(user2)

    # Should raise IntegrityError due to unique constraint violation
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    # Verify the error message mentions duplicate key or unique constraint
    assert (
        "duplicate" in str(exc_info.value).lower()
        or "unique" in str(exc_info.value).lower()
    )


def test_case_insensitive_email_lookup_lowercase_query(db_session: Session) -> None:
    """
    Test that email lookups are case-insensitive (lowercase query finds uppercase email).

    Validates: Querying for 'user@test.com' finds 'USER@TEST.COM'.
    """
    # Create user with uppercase email
    user = User(
        email="USER@TEST.COM",
        first_name="Test",
        last_name="User",
        is_platform_user=False,
    )
    db_session.add(user)
    db_session.commit()

    # Query with lowercase email
    statement = select(User).where(User.email == "user@test.com")
    result = db_session.exec(statement).first()

    # Should find the user despite case mismatch
    assert result is not None
    assert result.id == user.id
    assert result.email == "USER@TEST.COM"


def test_case_insensitive_email_lookup_uppercase_query(db_session: Session) -> None:
    """
    Test that email lookups are case-insensitive (uppercase query finds lowercase email).

    Validates: Querying for 'USER@TEST.COM' finds 'user@test.com'.
    """
    # Create user with lowercase email
    user = User(
        email="user@test.com",
        first_name="Test",
        last_name="User",
        is_platform_user=False,
    )
    db_session.add(user)
    db_session.commit()

    # Query with uppercase email
    statement = select(User).where(User.email == "USER@TEST.COM")
    result = db_session.exec(statement).first()

    # Should find the user despite case mismatch
    assert result is not None
    assert result.id == user.id
    assert result.email == "user@test.com"


def test_case_insensitive_email_mixed_case_query(db_session: Session) -> None:
    """
    Test that email lookups work with mixed case variations.

    Validates: 'UsEr@TeSt.CoM' finds 'user@test.com'.
    """
    # Create user with lowercase email
    user = User(
        email="user@test.com",
        first_name="Test",
        last_name="User",
        is_platform_user=False,
    )
    db_session.add(user)
    db_session.commit()

    # Query with mixed case email
    statement = select(User).where(User.email == "UsEr@TeSt.CoM")
    result = db_session.exec(statement).first()

    # Should find the user despite case mismatch
    assert result is not None
    assert result.id == user.id


def test_login_scenario_case_insensitive(db_session: Session) -> None:
    """
    Test realistic login scenario: User registers with lowercase, logs in with uppercase.

    This validates the core use case: preventing login failures due to case mismatch.
    """
    # User registers with lowercase email
    registration_email = "mike@contractor.example.com"
    user = User(
        email=registration_email,
        first_name="Mike",
        last_name="Contractor",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$...",  # Mock hash
        is_platform_user=False,
    )
    db_session.add(user)
    db_session.commit()
    user_id = user.id

    # User attempts to login with uppercase email (common user behavior)
    login_email = "MIKE@CONTRACTOR.EXAMPLE.COM"
    statement = select(User).where(User.email == login_email)
    result = db_session.exec(statement).first()

    # Login should succeed - user found despite case difference
    assert result is not None
    assert result.id == user_id
    assert result.first_name == "Mike"


def test_email_storage_preserves_case(db_session: Session) -> None:
    """
    Test that the database preserves the original case of the email when stored.

    CITEXT provides case-insensitive comparison but preserves the original value.
    """
    # Create user with mixed case email
    original_email = "MiXeD@CaSe.CoM"
    user = User(
        email=original_email,
        first_name="Test",
        last_name="User",
        is_platform_user=False,
    )
    db_session.add(user)
    db_session.commit()

    # Refresh from database
    db_session.refresh(user)

    # Email should be stored as entered (case preserved)
    assert user.email == original_email


def test_multiple_users_different_emails_case_insensitive(db_session: Session) -> None:
    """
    Test that multiple users with different emails can coexist (sanity check).

    Validates: alice@test.com and bob@test.com are distinct.
    """
    user1 = User(
        email="alice@test.com",
        first_name="Alice",
        last_name="Smith",
        is_platform_user=False,
    )
    user2 = User(
        email="bob@test.com",
        first_name="Bob",
        last_name="Jones",
        is_platform_user=False,
    )

    db_session.add(user1)
    db_session.add(user2)
    db_session.commit()

    # Both users should exist with distinct IDs
    assert user1.id != user2.id

    # Queries should find the correct users
    alice = db_session.exec(select(User).where(User.email == "alice@test.com")).first()
    bob = db_session.exec(select(User).where(User.email == "bob@test.com")).first()

    assert alice is not None
    assert bob is not None
    assert alice.id == user1.id
    assert bob.id == user2.id
