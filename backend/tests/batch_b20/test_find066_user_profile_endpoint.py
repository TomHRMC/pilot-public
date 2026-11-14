"""
FIND-066 — User Profile PATCH Endpoint + SMS MFA Invalidation Tests (B20, Task 11)

Test coverage:
  1. PATCH phone_number → user_endpoint updated + SMS MFA flagged pending_reverification
  2. PATCH phone_number with no SMS MFA enrolled → only user_endpoint updated
  3. PATCH time_zone → persisted and returned in response
  4. Profile photo S3 key → profile_photo_s3_key updated
  5. language_preference is always 'en' in MVP; PATCH attempts ignored
  6. GET /users/me/profile returns all profile columns
"""

from datetime import UTC, datetime

from fastapi import status
from sqlmodel import Session, select

from app.models.core import UserEndpoint
from app.models.security import UserMfaMethod


def test_patch_phone_number_updates_sms_endpoint_and_invalidates_mfa(
    client, test_tenant, test_user, db_session: Session
):
    """Phone number change → user_endpoint updated + SMS MFA marked pending_reverification"""
    # Setup: create SMS endpoint and SMS MFA on test_user
    sms_endpoint = UserEndpoint(
        user_id=test_user.id,
        channel="sms",
        value="+14155551234",
        is_primary=True,
        verification_status="verified",
    )
    db_session.add(sms_endpoint)
    db_session.flush()

    sms_mfa = UserMfaMethod(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        method_type="sms",
        verification_status="verified",
        enrolled_at=datetime.now(UTC),
        cognito_method_id="mock-cognito-sms-id",
    )
    db_session.add(sms_mfa)
    db_session.commit()

    # Action: PATCH phone_number
    response = client.patch(
        "/api/v1/users/me/profile/test",
        json={"phone_number": "+14155559999"},
    )

    # Assertions
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["phone_number"] == "+14155559999"

    # Verify SMS endpoint updated
    updated_endpoint = db_session.exec(
        select(UserEndpoint)
        .where(UserEndpoint.user_id == test_user.id)
        .where(UserEndpoint.channel == "sms")
        .where(UserEndpoint.is_primary == True)
    ).first()
    assert updated_endpoint is not None
    assert updated_endpoint.value == "+14155559999"

    # Verify SMS MFA marked pending_reverification
    updated_mfa = db_session.exec(
        select(UserMfaMethod)
        .where(UserMfaMethod.tenant_id == test_tenant.id)
        .where(UserMfaMethod.user_id == test_user.id)
        .where(UserMfaMethod.method_type == "sms")
    ).first()
    assert updated_mfa is not None
    assert updated_mfa.verification_status == "pending_reverification"


def test_patch_phone_number_without_sms_mfa_only_updates_endpoint(
    client, test_tenant, test_user, db_session: Session
):
    """Phone number change with NO SMS MFA → only endpoint updated"""
    sms_endpoint = UserEndpoint(
        user_id=test_user.id,
        channel="sms",
        value="+14155551111",
        is_primary=True,
        verification_status="verified",
    )
    db_session.add(sms_endpoint)
    db_session.commit()

    response = client.patch(
        "/api/v1/users/me/profile/test",
        json={"phone_number": "+14155552222"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["phone_number"] == "+14155552222"

    # Verify SMS endpoint updated
    updated_endpoint = db_session.exec(
        select(UserEndpoint)
        .where(UserEndpoint.user_id == test_user.id)
        .where(UserEndpoint.channel == "sms")
    ).first()
    assert updated_endpoint.value == "+14155552222"

    # Verify no SMS MFA exists
    mfa_count = len(
        db_session.exec(
            select(UserMfaMethod).where(UserMfaMethod.user_id == test_user.id)
        ).all()
    )
    assert mfa_count == 0


def test_patch_time_zone(client, test_tenant, test_user, db_session: Session):
    """PATCH time_zone → persisted and returned"""
    response = client.patch(
        "/api/v1/users/me/profile/test",
        json={"time_zone": "America/Los_Angeles"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["time_zone"] == "America/Los_Angeles"

    db_session.refresh(test_user)
    assert test_user.time_zone == "America/Los_Angeles"


def test_patch_profile_photo(client, test_tenant, test_user, db_session: Session):
    """PATCH profile_photo_s3_key → persisted"""
    s3_key = "profiles/user-123/photo.jpg"
    response = client.patch(
        "/api/v1/users/me/profile/test",
        json={"profile_photo_s3_key": s3_key},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["profile_photo_s3_key"] == s3_key

    db_session.refresh(test_user)
    assert test_user.profile_photo_s3_key == s3_key


def test_patch_multiple_fields(client, test_tenant, test_user, db_session: Session):
    """PATCH first_name + phone + time_zone in one request"""
    response = client.patch(
        "/api/v1/users/me/profile/test",
        json={
            "first_name": "Updated",
            "phone_number": "+14155556666",
            "time_zone": "America/Denver",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["phone_number"] == "+14155556666"
    assert data["time_zone"] == "America/Denver"

    db_session.refresh(test_user)
    assert test_user.first_name == "Updated"
    assert test_user.phone_number == "+14155556666"
    assert test_user.time_zone == "America/Denver"


def test_language_preference_always_en(
    client, test_tenant, test_user, db_session: Session
):
    """language_preference read-only in MVP; PATCH attempts ignored"""
    # Ensure language_preference starts as 'en'
    db_session.refresh(test_user)
    test_user.language_preference = "en"
    db_session.add(test_user)
    db_session.commit()

    # Try to PATCH language_preference to 'fr'
    response = client.patch(
        "/api/v1/users/me/profile/test",
        json={"language_preference": "fr"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["language_preference"] == "en"  # Still 'en'

    db_session.refresh(test_user)
    assert test_user.language_preference == "en"


def test_get_profile_returns_all_columns(
    client, test_tenant, test_user, db_session: Session
):
    """GET /users/me/profile returns all profile columns"""
    # Setup: set profile values on test_user
    test_user.phone_number = "+14155554444"
    test_user.time_zone = "America/Chicago"
    test_user.profile_photo_s3_key = "photos/user-123.jpg"
    test_user.language_preference = "en"
    db_session.add(test_user)
    db_session.commit()

    response = client.get(
        "/api/v1/users/me/profile/test",
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["first_name"] == test_user.first_name
    assert data["last_name"] == test_user.last_name
    assert data["email"] == test_user.email
    assert data["phone_number"] == "+14155554444"
    assert data["time_zone"] == "America/Chicago"
    assert data["profile_photo_s3_key"] == "photos/user-123.jpg"
    assert data["language_preference"] == "en"


def test_get_profile_with_null_fields(
    client, test_tenant, test_user, db_session: Session
):
    """GET /users/me/profile with NULL optional fields"""
    # Setup: clear optional fields on test_user
    test_user.phone_number = None
    test_user.time_zone = None
    test_user.profile_photo_s3_key = None
    db_session.add(test_user)
    db_session.commit()

    response = client.get(
        "/api/v1/users/me/profile/test",
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["phone_number"] is None
    assert data["time_zone"] is None
    assert data["profile_photo_s3_key"] is None
    assert data["language_preference"] == "en"
