"""
User Profile API — FIND-066 User Profile Columns & MFA Invalidation (B20, Task 11).
BE-UI-NAV-S1: Avatar presigned upload URL, avatar delete, profile_photo_url in response.

Endpoints:
  GET    /api/v1/users/me/profile                    — get user profile
  PATCH  /api/v1/users/me/profile                    — update user profile (name, phone, timezone, photo)
  POST   /api/v1/users/me/avatar/presigned-url       — generate S3 presigned PUT URL for avatar upload
  DELETE /api/v1/users/me/avatar                     — remove profile photo (clears key + best-effort S3 delete)

Updates to user.profile_photo_s3_key and phone_number; SMS MFA invalidation on phone change.
Follows dual-endpoint architecture (§8.2): authenticated + test variants.
"""

import logging

import boto3
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.core import User, UserEndpoint
from app.models.security import UserMfaMethod
from core.auth import AuthenticatedUser, get_current_user
from core.config import settings as app_settings
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== REQUEST / RESPONSE SCHEMAS ====================


class UserProfilePatchRequest(BaseModel):
    """Request body for PATCH /api/v1/users/me/profile"""

    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    time_zone: str | None = None
    profile_photo_s3_key: str | None = None
    # language_preference is read-only in MVP (always 'en'); PATCH attempts are ignored


class UserProfileResponse(BaseModel):
    """Response for PATCH /api/v1/users/me/profile and GET /api/v1/users/me/profile"""

    id: str
    first_name: str | None
    last_name: str | None
    email: str
    phone_number: str | None
    time_zone: str | None
    profile_photo_s3_key: str | None
    profile_photo_url: str | None  # BE-UI-NAV-S1: signed S3 GET URL (1-hour TTL)
    language_preference: str  # Always 'en' in MVP


class AvatarPresignedUrlResponse(BaseModel):
    """Response for POST /api/v1/users/me/avatar/presigned-url"""

    upload_url: str  # S3 presigned PUT URL (15-min TTL)
    s3_key: str  # key to pass back in PATCH /api/v1/users/me/profile


class AvatarDeleteResponse(BaseModel):
    """Response for DELETE /api/v1/users/me/avatar"""

    success: bool = True


# ==================== S3 HELPERS ====================


def _generate_avatar_url(s3_key: str | None) -> str | None:
    """
    Generate a 1-hour presigned GET URL for the profile photo.
    Gracefully returns None on error (no URL, no crash).
    """
    if not s3_key:
        return None
    try:
        s3 = boto3.client("s3", region_name=app_settings.AWS_S3_REGION)
        return s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": app_settings.AWS_S3_PHOTOS_BUCKET_NAME,
                "Key": s3_key,
            },
            ExpiresIn=3600,
        )
    except Exception:
        return None  # Graceful degradation


# ==================== SHARED BUSINESS LOGIC ====================


def _update_profile_impl(
    patch: UserProfilePatchRequest,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> UserProfileResponse:
    """
    Shared logic for PATCH /users/me/profile.

    When phone_number changes:
      1. Update user_endpoint WHERE channel='sms' AND is_primary=true
      2. If user_mfa_method WHERE method_type='sms' exists, mark as verification_status='pending_reverification'

    Args:
        patch: Profile patch request
        user_context: Authenticated user context
        db: Database session

    Returns:
        UserProfileResponse with updated profile

    Raises:
        HTTPException: If user not found (should not happen with auth context)
    """
    # Load user
    user = db.exec(select(User).where(User.id == user_context.id)).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Track if phone_number changed for MFA invalidation
    phone_changed = (
        patch.phone_number is not None and patch.phone_number != user.phone_number
    )

    # Update simple fields
    if patch.first_name is not None:
        user.first_name = patch.first_name
    if patch.last_name is not None:
        user.last_name = patch.last_name
    if patch.time_zone is not None:
        user.time_zone = patch.time_zone
    if patch.profile_photo_s3_key is not None:
        user.profile_photo_s3_key = patch.profile_photo_s3_key

    # Handle phone_number change
    if phone_changed:
        user.phone_number = patch.phone_number

        # Update user_endpoint WHERE channel='sms' AND is_primary=true
        sms_endpoint = db.exec(
            select(UserEndpoint)
            .where(UserEndpoint.user_id == user_context.id)
            .where(UserEndpoint.channel == "sms")
            .where(UserEndpoint.is_primary == True)
        ).first()

        if sms_endpoint:
            sms_endpoint.value = patch.phone_number
            db.add(sms_endpoint)

        # Invalidate SMS MFA method if enrolled
        sms_mfa = db.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.tenant_id == user_context.tenant_id)
            .where(UserMfaMethod.user_id == user_context.id)
            .where(UserMfaMethod.method_type == "sms")
        ).first()

        if sms_mfa:
            sms_mfa.verification_status = "pending_reverification"
            db.add(sms_mfa)

    # language_preference is read-only in MVP; silently ignore PATCH attempts
    # (Phase 2 will expand to support 'fr', 'es')

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserProfileResponse(
        id=str(user.id),
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone_number=user.phone_number,
        time_zone=user.time_zone,
        profile_photo_s3_key=user.profile_photo_s3_key,
        profile_photo_url=_generate_avatar_url(user.profile_photo_s3_key),
        language_preference=user.language_preference or "en",
    )


def _get_profile_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> UserProfileResponse:
    """
    Shared logic for GET /users/me/profile.

    Args:
        user_context: Authenticated user context
        db: Database session

    Returns:
        UserProfileResponse with current profile

    Raises:
        HTTPException: If user not found (should not happen with auth context)
    """
    user = db.exec(select(User).where(User.id == user_context.id)).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(
        id=str(user.id),
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone_number=user.phone_number,
        time_zone=user.time_zone,
        profile_photo_s3_key=user.profile_photo_s3_key,
        profile_photo_url=_generate_avatar_url(user.profile_photo_s3_key),
        language_preference=user.language_preference or "en",
    )


def _generate_avatar_presigned_url_impl(
    user_context: AuthenticatedUser | TestUserContext,
) -> AvatarPresignedUrlResponse:
    """
    Generate a presigned PUT URL for avatar upload.
    No DB write here — key stored via PATCH /me/profile.

    Client flow:
      1. Call this endpoint → receive upload_url + s3_key
      2. PUT cropped JPEG blob to upload_url directly (S3, not through API)
      3. Call PATCH /api/v1/users/me/profile with { profile_photo_s3_key: s3_key }
    """
    s3_key = f"avatars/{user_context.tenant_id}/{user_context.id}/avatar.jpg"
    try:
        s3 = boto3.client("s3", region_name=app_settings.AWS_S3_REGION)
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": app_settings.AWS_S3_PHOTOS_BUCKET_NAME,
                "Key": s3_key,
                "ContentType": "image/jpeg",
            },
            ExpiresIn=900,  # 15 minutes
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "https://errors.pilotfortrades.com/s3-error",
                "title": "S3 presigned URL generation failed",
                "status": 500,
                "detail": f"Could not generate upload URL: {exc}",
            },
        )
    return AvatarPresignedUrlResponse(upload_url=upload_url, s3_key=s3_key)


def _delete_avatar_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> AvatarDeleteResponse:
    """
    Clear profile_photo_s3_key from the user record.
    Best-effort S3 delete — never fails the endpoint on S3 error.
    """
    user = db.exec(select(User).where(User.id == user_context.id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "User not found",
                "status": 404,
                "detail": "User record not found.",
            },
        )

    old_key = user.profile_photo_s3_key
    user.profile_photo_s3_key = None
    db.add(user)
    db.commit()

    # Best-effort S3 delete — never fail the endpoint if S3 delete errors
    if old_key:
        try:
            s3 = boto3.client("s3", region_name=app_settings.AWS_S3_REGION)
            s3.delete_object(Bucket=app_settings.AWS_S3_PHOTOS_BUCKET_NAME, Key=old_key)
        except Exception as exc:
            logger.warning("Failed to delete avatar from S3 (key=%s): %s", old_key, exc)

    return AvatarDeleteResponse(success=True)


# ==================== TEST ENDPOINTS ====================


@router.get("/me/profile/test", response_model=UserProfileResponse)
def get_profile_test(db: Session = Depends(get_db)):
    """GET /api/v1/users/me/profile (test variant)"""
    test_context = get_test_context()
    return _get_profile_impl(test_context, db)


@router.patch("/me/profile/test", response_model=UserProfileResponse)
def update_profile_test(
    patch: UserProfilePatchRequest,
    db: Session = Depends(get_db),
):
    """PATCH /api/v1/users/me/profile (test variant)"""
    test_context = get_test_context()
    return _update_profile_impl(patch, test_context, db)


@router.post(
    "/me/avatar/presigned-url/test",
    response_model=AvatarPresignedUrlResponse,
    status_code=201,
)
def get_avatar_presigned_url_test(
    db: Session = Depends(get_db),
):
    """[TEST] Generate avatar presigned upload URL — no auth."""
    test_context = get_test_context()
    return _generate_avatar_presigned_url_impl(test_context)


@router.delete("/me/avatar/test", response_model=AvatarDeleteResponse)
def delete_avatar_test(
    db: Session = Depends(get_db),
):
    """[TEST] Delete avatar — no auth."""
    test_context = get_test_context()
    return _delete_avatar_impl(test_context, db)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.get("/me/profile", response_model=UserProfileResponse)
def get_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/users/me/profile

    Retrieve current user's profile information (read-only endpoint).
    No permission check required — users can always read their own profile.

    Returns:
        UserProfileResponse with current profile
    """
    return _get_profile_impl(user, db)


@router.patch(
    "/me/profile",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
)
def update_profile(
    patch: UserProfilePatchRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    PATCH /api/v1/users/me/profile

    Update current user's profile.

    RBAC: mfa.enroll_self (own profile only — no elevated permission needed)

    When phone_number changes:
      - Updates user_endpoint WHERE channel='sms' AND is_primary=true
      - Marks user_mfa_method WHERE method_type='sms' as verification_status='pending_reverification'

    Language preference is read-only in MVP (always 'en'); PATCH attempts are silently ignored.

    Args:
        patch: Profile patch request (all fields optional)
        user: Authenticated user
        db: Database session

    Returns:
        UserProfileResponse with updated profile
    """
    require_permission(user.permissions, "mfa.enroll_self")
    return _update_profile_impl(patch, user, db)


@router.post(
    "/me/avatar/presigned-url",
    response_model=AvatarPresignedUrlResponse,
    status_code=201,
)
def get_avatar_presigned_url(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    POST /api/v1/users/me/avatar/presigned-url

    Generate a presigned S3 PUT URL for uploading a profile photo.
    Client flow:
      1. Call this endpoint → receive upload_url + s3_key
      2. PUT cropped JPEG blob to upload_url directly (S3, not through API)
      3. Call PATCH /api/v1/users/me/profile with { profile_photo_s3_key: s3_key }

    RBAC: mfa.enroll_self (own profile only)
    """
    require_permission(user.permissions, "mfa.enroll_self")
    return _generate_avatar_presigned_url_impl(user)


@router.delete("/me/avatar", response_model=AvatarDeleteResponse)
def delete_avatar(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    DELETE /api/v1/users/me/avatar

    Remove profile photo. Clears profile_photo_s3_key on user record.
    Best-effort S3 object deletion (logged on failure, endpoint always succeeds).

    RBAC: mfa.enroll_self (own profile only)
    """
    require_permission(user.permissions, "mfa.enroll_self")
    set_audit_context_sync(db, user_id=user.id)
    return _delete_avatar_impl(user, db)
