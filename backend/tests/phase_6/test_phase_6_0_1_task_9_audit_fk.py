import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.auth import (
    AuthApiToken,
    AuthEmailVerification,
    AuthJwk,
    AuthMfaOtp,
    AuthPasswordHistory,
    AuthPasswordReset,
    JwkStatus,
)
from app.models.core import User


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(
        email=f"test_audit_user_{uuid.uuid4()}@example.com",
        password_hash="fake_hash",
        first_name="Test",
        last_name="User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_jwk_status(db_session: Session) -> JwkStatus:
    status = JwkStatus(
        code=f"TEST_{uuid.uuid4().hex[:8]}",
        name="Test Status",
    )
    db_session.add(status)
    db_session.commit()
    db_session.refresh(status)
    return status


def test_auth_api_token_audit_fk(db_session: Session, test_user: User):
    # 1. Null values accepted
    token_null = AuthApiToken(name="test_token", token_hash="hash1")
    db_session.add(token_null)
    db_session.commit()

    # 2. Invalid created_by rejected
    try:
        with db_session.begin_nested():
            token_invalid = AuthApiToken(
                name="test_token_3", token_hash="hash3", created_by=uuid.uuid4()
            )
            db_session.add(token_invalid)
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass

    # 3. Valid created_by accepted
    token_valid = AuthApiToken(
        name="test_token_2", token_hash="hash2", created_by=test_user.id
    )
    db_session.add(token_valid)
    db_session.commit()

    # 4. User deletion prevented (RESTRICT)
    try:
        with db_session.begin_nested():
            db_session.execute(
                text('DELETE FROM "user" WHERE id = :id'), {"id": test_user.id}
            )
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass


def test_auth_email_verification_audit_fk(db_session: Session, test_user: User):
    now = datetime.now(UTC)

    # 1. Null values accepted
    verify_null = AuthEmailVerification(
        token_hash="hash1", expires_at=now + timedelta(days=1)
    )
    db_session.add(verify_null)
    db_session.commit()

    # 2. Invalid created_by rejected
    try:
        with db_session.begin_nested():
            verify_invalid = AuthEmailVerification(
                token_hash="hash3",
                expires_at=now + timedelta(days=1),
                created_by=uuid.uuid4(),
            )
            db_session.add(verify_invalid)
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass

    # 3. Valid created_by accepted
    verify_valid = AuthEmailVerification(
        token_hash="hash2", expires_at=now + timedelta(days=1), created_by=test_user.id
    )
    db_session.add(verify_valid)
    db_session.commit()

    # 4. User deletion prevented (RESTRICT)
    try:
        with db_session.begin_nested():
            db_session.execute(
                text('DELETE FROM "user" WHERE id = :id'), {"id": test_user.id}
            )
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass


def test_auth_password_reset_audit_fk(db_session: Session, test_user: User):
    now = datetime.now(UTC)

    # 1. Null values accepted
    reset_null = AuthPasswordReset(
        token_hash="hash1", expires_at=now + timedelta(days=1)
    )
    db_session.add(reset_null)
    db_session.commit()

    # 2. Invalid created_by rejected
    try:
        with db_session.begin_nested():
            reset_invalid = AuthPasswordReset(
                token_hash="hash3",
                expires_at=now + timedelta(days=1),
                created_by=uuid.uuid4(),
            )
            db_session.add(reset_invalid)
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass

    # 3. Valid created_by accepted
    reset_valid = AuthPasswordReset(
        token_hash="hash2", expires_at=now + timedelta(days=1), created_by=test_user.id
    )
    db_session.add(reset_valid)
    db_session.commit()

    # 4. User deletion prevented (RESTRICT)
    try:
        with db_session.begin_nested():
            db_session.execute(
                text('DELETE FROM "user" WHERE id = :id'), {"id": test_user.id}
            )
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass


def test_auth_password_history_audit_fk(db_session: Session, test_user: User):
    # 1. Null values accepted
    history_null = AuthPasswordHistory(password_hash="hash1")
    db_session.add(history_null)
    db_session.commit()

    # 2. Invalid created_by rejected
    try:
        with db_session.begin_nested():
            history_invalid = AuthPasswordHistory(
                password_hash="hash3", created_by=uuid.uuid4()
            )
            db_session.add(history_invalid)
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass

    # 3. Valid created_by accepted
    history_valid = AuthPasswordHistory(password_hash="hash2", created_by=test_user.id)
    db_session.add(history_valid)
    db_session.commit()

    # 4. User deletion prevented (RESTRICT)
    try:
        with db_session.begin_nested():
            db_session.execute(
                text('DELETE FROM "user" WHERE id = :id'), {"id": test_user.id}
            )
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass


def test_auth_mfa_otp_audit_fk(db_session: Session, test_user: User):
    now = datetime.now(UTC)

    # 1. Null values accepted
    otp_null = AuthMfaOtp(
        channel="email", code_hash="hash1", expires_at=now + timedelta(minutes=5)
    )
    db_session.add(otp_null)
    db_session.commit()

    # 2. Invalid created_by rejected
    try:
        with db_session.begin_nested():
            otp_invalid = AuthMfaOtp(
                channel="email",
                code_hash="hash3",
                expires_at=now + timedelta(minutes=5),
                created_by=uuid.uuid4(),
            )
            db_session.add(otp_invalid)
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass

    # 3. Valid created_by accepted
    otp_valid = AuthMfaOtp(
        channel="email",
        code_hash="hash2",
        expires_at=now + timedelta(minutes=5),
        created_by=test_user.id,
    )
    db_session.add(otp_valid)
    db_session.commit()

    # 4. User deletion prevented (RESTRICT)
    try:
        with db_session.begin_nested():
            db_session.execute(
                text('DELETE FROM "user" WHERE id = :id'), {"id": test_user.id}
            )
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass


def test_auth_jwk_audit_fk(
    db_session: Session, test_user: User, test_jwk_status: JwkStatus
):
    # 1. Null values accepted
    jwk_null = AuthJwk(
        kid=f"kid_{uuid.uuid4()}",
        alg="RS256",
        public_jwk={"kty": "RSA"},
        jwk_status_id=test_jwk_status.id,
    )
    db_session.add(jwk_null)
    db_session.commit()

    # 2. Invalid created_by rejected
    try:
        with db_session.begin_nested():
            jwk_invalid = AuthJwk(
                kid=f"kid_{uuid.uuid4()}",
                alg="RS256",
                public_jwk={"kty": "RSA"},
                jwk_status_id=test_jwk_status.id,
                created_by=uuid.uuid4(),
            )
            db_session.add(jwk_invalid)
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass

    # 3. Valid created_by accepted
    jwk_valid = AuthJwk(
        kid=f"kid_{uuid.uuid4()}",
        alg="RS256",
        public_jwk={"kty": "RSA"},
        jwk_status_id=test_jwk_status.id,
        created_by=test_user.id,
    )
    db_session.add(jwk_valid)
    db_session.commit()

    # 4. User deletion prevented (RESTRICT)
    try:
        with db_session.begin_nested():
            db_session.execute(
                text('DELETE FROM "user" WHERE id = :id'), {"id": test_user.id}
            )
            db_session.commit()
        pytest.fail("IntegrityError not raised")
    except IntegrityError:
        pass
