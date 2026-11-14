"""
Account Security API routes for Pilot for Trades — Batch B13.

Covers:
  A72 — GET /users/me/session-history
  A68 — GET /users/me/mfa-status
  A69 — MFA enrollment & recovery code endpoints
  A70 — GET/DELETE /users/me/sessions, POST /users/me/sessions/revoke-others
  A71 — POST/GET /users/me/data-exports

Route registration: /test endpoints BEFORE authenticated endpoints.
All routes are registered under prefix /api/v1/users in main.py.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.core import User
from app.models.security import (
    DataExportRequest,
    MfaGracePeriodTracking,
    UserMfaMethod,
    UserMfaRecoveryCode,
    UserSessionHistory,
    UserSessionMetadata,
)
from core.auth import (
    TEST_ACCESS_TOKEN_SENTINEL,
    AuthenticatedUser,
    get_cognito_access_token,
)
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.cognito_mfa_client import (
    CognitoMfaError,
    MfaAccessTokenInvalidError,
    MfaCodeExpiredError,
    MfaCodeMismatchError,
    MfaSmsRoleNotConfiguredError,
    get_cognito_mfa_client,
)
from services.session_revoke_service import revoke_others, revoke_session

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MFA-WIRE-1 helpers (design §F.3, §F.4)
# ---------------------------------------------------------------------------


def _mfa_error(
    http_status: int,
    code: str,
    title: str,
    detail: str,
) -> HTTPException:
    """Build an RFC 7807 Problem Details HTTPException for MFA errors."""
    return HTTPException(
        status_code=http_status,
        detail={
            "type": f"https://errors.pilotfortrades.com/{code}",
            "title": title,
            "status": http_status,
            "detail": detail,
            "code": code,
        },
    )


def _map_cognito_exception(e: Exception) -> HTTPException:
    """Map a CognitoMfaError subclass to the correct RFC 7807 HTTPException
    (design §F.3). Never includes the access token in the message."""
    if isinstance(e, MfaAccessTokenInvalidError):
        return _mfa_error(
            401,
            "mfa_access_token_invalid",
            "Cognito access token invalid",
            "The Cognito access token is invalid or expired.",
        )
    if isinstance(e, MfaCodeMismatchError):
        return _mfa_error(
            400,
            "mfa_code_invalid",
            "MFA code invalid",
            "The verification code does not match.",
        )
    if isinstance(e, MfaCodeExpiredError):
        return _mfa_error(
            400,
            "mfa_code_expired",
            "MFA code expired",
            "The verification code has expired.",
        )
    if isinstance(e, MfaSmsRoleNotConfiguredError):
        return _mfa_error(
            503,
            "sms_delivery_not_configured",
            "SMS delivery not configured",
            (
                "Cognito SMS delivery is not configured for this user pool. "
                "Contact your administrator."
            ),
        )
    # CognitoMfaError (base) — any other upstream failure
    return _mfa_error(
        502,
        "cognito_unavailable",
        "Cognito unavailable",
        "An upstream Cognito error occurred. Please try again.",
    )


def _normalize_phone_e164(raw: str) -> str:
    """Normalize a phone number to E.164 (design §F.4).

    - Strips formatting (spaces, dashes, parens, dots).
    - 10 digits → ``+1`` prefix (US default).
    - Already starts with ``+`` → passthrough (assumed valid E.164).
    - Anything else → raise ValueError (caller maps to 400 phone_number_invalid).
    """
    cleaned = "".join(c for c in raw if c.isdigit() or c == "+")
    if cleaned.startswith("+"):
        return cleaned
    if len(cleaned) == 10:
        return f"+1{cleaned}"
    raise ValueError(f"Unparseable phone number: {raw!r}")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SessionHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    first_login_at: datetime
    total_session_count: int
    last_login_at: datetime


class MfaMethodInfo(BaseModel):
    """One enrolled MFA method — drives the web method-card Remove UI (design §D.4)."""

    method_id: uuid.UUID
    method_type: str
    enrolled_at: datetime
    last_used_at: datetime | None = (
        None  # null this batch — Cognito owns challenge telemetry
    )
    destination_masked: str | None = None  # "***-***-1234" from metadata; null for totp


class MfaStatusResponse(BaseModel):
    enrolled_methods: list[str]  # KEPT (deprecated) — mobile useMfaStatus consumes it
    methods: list[MfaMethodInfo] = []  # NEW — additive (design §D.4)
    tenant_policy_required: bool
    grace_period_active: bool
    grace_ends_at: datetime | None
    enforcement_activated: bool


class MfaEnrollStartResponse(BaseModel):
    """TOTP: qr_code_uri + secret. SMS/Email: destination_masked."""

    method_type: str
    # TOTP fields
    qr_code_uri: str | None = None
    secret: str | None = None
    # SMS/Email fields
    destination_masked: str | None = None


class MfaEnrollConfirmRequest(BaseModel):
    code: str


class MfaEnrollConfirmResponse(BaseModel):
    method_id: uuid.UUID
    enrolled_at: datetime


class MfaRecoveryCodesGenerateResponse(BaseModel):
    codes: list[str]
    set_id: uuid.UUID


class MfaRecoveryCodesStatusResponse(BaseModel):
    unused_code_count: int
    last_generated_at: datetime | None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    session_id: uuid.UUID
    display_label: str
    ip_address: str
    geolocation: str | None
    created_at: datetime
    last_active_at: datetime
    is_current: bool
    revoked_at: datetime | None


class RevokeOthersResponse(BaseModel):
    revoked_count: int


class DataExportStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    export_id: uuid.UUID
    status: str
    requested_at: datetime
    expires_at: datetime | None
    signed_url: str | None
    data_scope: str
    failure_reason: str | None


class DataExportCreateResponse(BaseModel):
    export_id: uuid.UUID
    status: str
    requested_at: datetime


# ---------------------------------------------------------------------------
# A72 — Session History
# ---------------------------------------------------------------------------


def _upsert_session_history(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> UserSessionHistory:
    """Upsert the session history row on each successful login."""
    now = datetime.now(UTC)
    existing = db.exec(
        select(UserSessionHistory)
        .where(UserSessionHistory.tenant_id == tenant_id)
        .where(UserSessionHistory.user_id == user_id)
    ).first()

    if existing is None:
        row = UserSessionHistory(
            tenant_id=tenant_id,
            user_id=user_id,
            first_login_at=now,
            total_session_count=1,
            last_login_at=now,
        )
        db.add(row)
    else:
        existing.total_session_count += 1
        existing.last_login_at = now
        db.add(existing)

    db.commit()
    if existing is None:
        db.refresh(row)
        return row
    db.refresh(existing)
    return existing


def _get_session_history_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> SessionHistoryResponse:
    row = db.exec(
        select(UserSessionHistory)
        .where(UserSessionHistory.tenant_id == user_context.tenant_id)
        .where(UserSessionHistory.user_id == user_context.id)
    ).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No session history found for this user",
        )
    return SessionHistoryResponse.model_validate(row)


@router.get("/me/session-history/test", response_model=SessionHistoryResponse)
def get_session_history_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required."""
    ctx = get_test_context()
    return _get_session_history_impl(ctx, db)


@router.get("/me/session-history", response_model=SessionHistoryResponse)
def get_session_history(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("account.session.view_own")
    ),
):
    return _get_session_history_impl(current_user, db)


# ---------------------------------------------------------------------------
# A68 — MFA Status
# ---------------------------------------------------------------------------


def _get_mfa_status_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> MfaStatusResponse:
    # Load enrolled methods (tenant+user scoped)
    methods = db.exec(
        select(UserMfaMethod)
        .where(UserMfaMethod.tenant_id == user_context.tenant_id)
        .where(UserMfaMethod.user_id == user_context.id)
    ).all()
    enrolled_methods = [m.method_type for m in methods]

    # Build the additive methods[] array (design §D.4) — drives web Remove UI
    method_infos: list[MfaMethodInfo] = []
    for m in methods:
        destination_masked: str | None = None
        if m.method_metadata and "destination_last4" in m.method_metadata:
            destination_masked = f"***-***-{m.method_metadata['destination_last4']}"
        method_infos.append(
            MfaMethodInfo(
                method_id=m.mfa_method_id,
                method_type=m.method_type,
                enrolled_at=m.enrolled_at,
                last_used_at=m.last_used_at,
                destination_masked=destination_masked,
            )
        )

    # Load tenant MFA policy from platform_setting (post-FIND-086)
    from services.setting_resolver import get_effective_setting

    tenant_policy_required, _ = get_effective_setting(
        db, user_context.tenant_id, "tenant_mfa_required", fallback=False
    )
    grace_period_days_val, _ = get_effective_setting(
        db, user_context.tenant_id, "tenant_mfa_grace_period_days", fallback=7
    )
    grace_period_days = int(grace_period_days_val)

    # Load grace period tracking for this user
    grace_row = db.exec(
        select(MfaGracePeriodTracking)
        .where(MfaGracePeriodTracking.tenant_id == user_context.tenant_id)
        .where(MfaGracePeriodTracking.user_id == user_context.id)
    ).first()

    grace_period_active = False
    grace_ends_at = None
    enforcement_activated = False

    if grace_row:
        grace_ends_at = grace_row.grace_started_at + timedelta(days=grace_period_days)
        grace_period_active = (
            grace_row.enrolled_at is None and datetime.now(UTC) < grace_ends_at
        )
        enforcement_activated = grace_row.enforcement_activated_at is not None

    return MfaStatusResponse(
        enrolled_methods=enrolled_methods,
        methods=method_infos,
        tenant_policy_required=tenant_policy_required,
        grace_period_active=grace_period_active,
        grace_ends_at=grace_ends_at,
        enforcement_activated=enforcement_activated,
    )


@router.get("/me/mfa-status/test", response_model=MfaStatusResponse)
def get_mfa_status_test(db: Session = Depends(get_db)):
    ctx = get_test_context()
    return _get_mfa_status_impl(ctx, db)


@router.get("/me/mfa-status", response_model=MfaStatusResponse)
def get_mfa_status(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mfa.enroll_self")),
):
    return _get_mfa_status_impl(current_user, db)


# ---------------------------------------------------------------------------
# A69 — MFA Enrollment
# ---------------------------------------------------------------------------


def _enroll_start_impl(
    method_type: str,
    access_token: str,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> MfaEnrollStartResponse:
    """Start MFA enrollment via Cognito user-scoped APIs (design §D.1).

    - TOTP: ``AssociateSoftwareToken`` → real secret + otpauth URI.
    - SMS: normalize phone → ``SetUserAttributes`` → ``GetUserAttributeVerificationCode``
      → masked destination.
    - Email: 400 ``email_mfa_not_available`` (pool has no email factor — §G-Q2).

    Zero DB writes on any failure (fail-loud, never fake success).
    """
    valid_methods = {"totp", "sms"}
    if method_type not in valid_methods:
        if method_type == "email":
            raise _mfa_error(
                400,
                "email_mfa_not_available",
                "Email MFA not available",
                "Email MFA is not available for this user pool.",
            )
        raise _mfa_error(
            400,
            "invalid_method_type",
            "Invalid method type",
            f"Invalid method_type '{method_type}'. Valid: {sorted(valid_methods)}",
        )

    client = get_cognito_mfa_client()

    if method_type == "totp":
        try:
            secret = client.associate_software_token(access_token)
        except CognitoMfaError as e:
            raise _map_cognito_exception(e) from e
        # Look up the user's email for the otpauth label (User is not tenant-scoped)
        db_user = db.exec(select(User).where(User.id == user_context.id)).first()
        user_email = db_user.email if db_user else str(user_context.id)
        qr_uri = (
            f"otpauth://totp/PilotForTrades:{user_email}"
            f"?secret={secret}&issuer=PilotForTrades"
        )
        return MfaEnrollStartResponse(
            method_type="totp",
            qr_code_uri=qr_uri,
            secret=secret,
        )

    # method_type == "sms" — User is not tenant-scoped; query by id only
    db_user = db.exec(select(User).where(User.id == user_context.id)).first()
    phone = db_user.phone_number if db_user else None
    if not phone:
        raise _mfa_error(
            400,
            "phone_number_required",
            "Phone number required",
            "A phone number is required to enroll SMS MFA.",
        )
    try:
        e164 = _normalize_phone_e164(phone)
    except ValueError:
        raise _mfa_error(
            400,
            "phone_number_invalid",
            "Phone number invalid",
            "The phone number could not be parsed to E.164 format.",
        ) from None

    try:
        client.set_phone_number(access_token, e164)
        destination_masked = client.send_phone_verification_code(access_token)
    except CognitoMfaError as e:
        raise _map_cognito_exception(e) from e

    return MfaEnrollStartResponse(
        method_type="sms",
        destination_masked=destination_masked,
    )


def _enroll_confirm_impl(
    method_type: str,
    code: str,
    access_token: str,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> tuple[MfaEnrollConfirmResponse, int]:
    """Confirm MFA enrollment via Cognito, then write the DB row ONLY on success
    (design §D.2 — the anti-mock guarantee).

    Returns (response, status_code):
      - Existing row + Cognito factor already enabled → 200 (idempotent replay).
      - No row + verify success → 201 (new row written).
      - Any Cognito failure → mapped error, ZERO DB writes.
    """
    valid_methods = {"totp", "sms"}
    if method_type not in valid_methods:
        raise _mfa_error(
            400,
            "invalid_method_type",
            "Invalid method type",
            f"Invalid method_type '{method_type}'. Valid: {sorted(valid_methods)}",
        )

    now = datetime.now(UTC)
    client = get_cognito_mfa_client()

    # ── Replay short-circuit: existing row → idempotent 200 ─────────────────
    existing = db.exec(
        select(UserMfaMethod)
        .where(UserMfaMethod.tenant_id == user_context.tenant_id)
        .where(UserMfaMethod.user_id == user_context.id)
        .where(UserMfaMethod.method_type == method_type)
    ).first()

    if existing:
        # Idempotent replay — re-affirm the Cognito preference, return existing row
        prefer = method_type if _is_sole_method(db, user_context, method_type) else None
        try:
            if method_type == "totp":
                client.set_mfa_preference(
                    access_token, totp_enabled=True, prefer=prefer
                )
            else:
                client.set_mfa_preference(access_token, sms_enabled=True, prefer=prefer)
        except CognitoMfaError as e:
            raise _map_cognito_exception(e) from e
        return MfaEnrollConfirmResponse(
            method_id=existing.mfa_method_id, enrolled_at=existing.enrolled_at
        ), 200

    # ── New enrollment: verify with Cognito FIRST, then write DB ────────────
    try:
        if method_type == "totp":
            client.verify_software_token(access_token, code)
        else:
            client.verify_phone_number(access_token, code)
    except CognitoMfaError as e:
        raise _map_cognito_exception(e) from e

    # Cognito succeeded — now set the MFA preference
    prefer = method_type if _is_sole_method(db, user_context, method_type) else None
    try:
        if method_type == "totp":
            client.set_mfa_preference(access_token, totp_enabled=True, prefer=prefer)
        else:
            client.set_mfa_preference(access_token, sms_enabled=True, prefer=prefer)
    except CognitoMfaError as e:
        raise _map_cognito_exception(e) from e

    # ── DB writes ONLY after Cognito success (zero-DB-write invariant) ──────
    set_audit_context_sync(db, user_id=user_context.id)

    cognito_method_id = (
        "totp:software-token" if method_type == "totp" else "sms:phone_number"
    )
    method_metadata: dict | None = None
    if method_type == "sms":
        # Re-read the user row for the phone last-4 (User is not tenant-scoped)
        db_user = db.exec(select(User).where(User.id == user_context.id)).first()
        phone = db_user.phone_number if db_user else None
        if phone:
            method_metadata = {"destination_last4": phone[-4:]}

    new_method = UserMfaMethod(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        method_type=method_type,
        enrolled_at=now,
        cognito_method_id=cognito_method_id,
        verification_status="verified",
        method_metadata=method_metadata,
    )
    db.add(new_method)
    db.commit()
    db.refresh(new_method)
    method_id = new_method.mfa_method_id

    # Update grace period tracking if present (existing behavior preserved)
    grace_row = db.exec(
        select(MfaGracePeriodTracking)
        .where(MfaGracePeriodTracking.tenant_id == user_context.tenant_id)
        .where(MfaGracePeriodTracking.user_id == user_context.id)
    ).first()
    if grace_row and grace_row.enrolled_at is None:
        grace_row.enrolled_at = now
        db.add(grace_row)
        db.commit()

    return MfaEnrollConfirmResponse(method_id=method_id, enrolled_at=now), 201


def _is_sole_method(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    exclude_method_type: str,
) -> bool:
    """Return True if the user has zero other verified MFA methods (so the new
    enrollment should become the preferred factor)."""
    others = db.exec(
        select(UserMfaMethod)
        .where(UserMfaMethod.tenant_id == user_context.tenant_id)
        .where(UserMfaMethod.user_id == user_context.id)
        .where(UserMfaMethod.method_type != exclude_method_type)
        .where(UserMfaMethod.verification_status == "verified")
    ).all()
    return len(others) == 0


@router.post(
    "/me/mfa/methods/{method_type}/enroll-start/test",
    response_model=MfaEnrollStartResponse,
)
def enroll_start_test(method_type: str, db: Session = Depends(get_db)):
    ctx = get_test_context()
    return _enroll_start_impl(method_type, TEST_ACCESS_TOKEN_SENTINEL, ctx, db)


@router.post(
    "/me/mfa/methods/{method_type}/enroll-start", response_model=MfaEnrollStartResponse
)
def enroll_start(
    method_type: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mfa.enroll_self")),
):
    access_token = get_cognito_access_token(request)
    return _enroll_start_impl(method_type, access_token, current_user, db)


@router.post(
    "/me/mfa/methods/{method_type}/enroll-confirm/test",
    response_model=MfaEnrollConfirmResponse,
)
def enroll_confirm_test(
    method_type: str,
    body: MfaEnrollConfirmRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    ctx = get_test_context()
    result, code = _enroll_confirm_impl(
        method_type, body.code, TEST_ACCESS_TOKEN_SENTINEL, ctx, db
    )
    response.status_code = code
    return result


@router.post(
    "/me/mfa/methods/{method_type}/enroll-confirm",
    response_model=MfaEnrollConfirmResponse,
)
def enroll_confirm(
    method_type: str,
    body: MfaEnrollConfirmRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mfa.enroll_self")),
):
    access_token = get_cognito_access_token(request)
    result, code = _enroll_confirm_impl(
        method_type, body.code, access_token, current_user, db
    )
    response.status_code = code
    return result


def _delete_mfa_method_impl(
    method_id: uuid.UUID,
    access_token: str,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> None:
    method = db.exec(
        select(UserMfaMethod)
        .where(UserMfaMethod.mfa_method_id == method_id)
        .where(UserMfaMethod.tenant_id == user_context.tenant_id)
        .where(UserMfaMethod.user_id == user_context.id)
    ).first()
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MFA method not found"
        )

    # Cannot delete last method if tenant_mfa_required = true (post-FIND-086)
    from services.setting_resolver import get_effective_setting

    mfa_required_val, _ = get_effective_setting(
        db, user_context.tenant_id, "tenant_mfa_required", fallback=False
    )
    if mfa_required_val:
        count = db.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.tenant_id == user_context.tenant_id)
            .where(UserMfaMethod.user_id == user_context.id)
        ).all()
        if len(count) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "https://pilotfortrades.com/errors/last-method-required",
                    "title": "Last MFA Method",
                    "status": 409,
                    "detail": "Cannot delete the last MFA method when tenant MFA policy is required.",
                    "code": "last_method_required",
                },
            )

    # ── Cognito first, DB second (never strand a Cognito factor without a row) ─
    client = get_cognito_mfa_client()
    try:
        if method.method_type == "totp":
            client.set_mfa_preference(access_token, totp_enabled=False)
        else:
            client.set_mfa_preference(access_token, sms_enabled=False)
        # If another verified method remains, prefer it so Cognito always has one
        remaining = db.exec(
            select(UserMfaMethod)
            .where(UserMfaMethod.tenant_id == user_context.tenant_id)
            .where(UserMfaMethod.user_id == user_context.id)
            .where(UserMfaMethod.mfa_method_id != method_id)
            .where(UserMfaMethod.verification_status == "verified")
        ).all()
        if remaining:
            remaining_type = remaining[0].method_type
            if remaining_type == "totp":
                client.set_mfa_preference(
                    access_token, totp_enabled=True, prefer="totp"
                )
            else:
                client.set_mfa_preference(access_token, sms_enabled=True, prefer="sms")
    except CognitoMfaError as e:
        raise _map_cognito_exception(e) from e

    set_audit_context_sync(db, user_id=user_context.id)
    db.delete(method)
    db.commit()


@router.delete(
    "/me/mfa/methods/{method_id}/test", status_code=status.HTTP_204_NO_CONTENT
)
def delete_mfa_method_test(method_id: uuid.UUID, db: Session = Depends(get_db)):
    ctx = get_test_context()
    _delete_mfa_method_impl(method_id, TEST_ACCESS_TOKEN_SENTINEL, ctx, db)


@router.delete("/me/mfa/methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mfa_method(
    method_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mfa.reset_self")),
):
    access_token = get_cognito_access_token(request)
    _delete_mfa_method_impl(method_id, access_token, current_user, db)


def _hash_recovery_code(code: str) -> str:
    """Hash a recovery code using PBKDF2-SHA256 (stdlib — no bcrypt/passlib needed for MVP)."""
    import hashlib
    import os

    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", code.encode(), salt, 100_000)
    return salt.hex() + ":" + dk.hex()


def _generate_recovery_codes_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> MfaRecoveryCodesGenerateResponse:
    """Generate 10 PBKDF2-hashed recovery codes. Return plaintext only once."""
    now = datetime.now(UTC)
    new_set_id = uuid.uuid4()
    plaintext_codes = []

    for _ in range(10):
        code = uuid.uuid4().hex[:10].upper()
        plaintext_codes.append(code)
        code_hash = _hash_recovery_code(code)
        row = UserMfaRecoveryCode(
            tenant_id=user_context.tenant_id,
            user_id=user_context.id,
            code_hash=code_hash,
            generated_at=now,
            set_id=new_set_id,
        )
        db.add(row)

    db.commit()
    return MfaRecoveryCodesGenerateResponse(codes=plaintext_codes, set_id=new_set_id)


@router.post(
    "/me/mfa/recovery-codes/generate/test",
    response_model=MfaRecoveryCodesGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_recovery_codes_test(db: Session = Depends(get_db)):
    ctx = get_test_context()
    return _generate_recovery_codes_impl(ctx, db)


@router.post(
    "/me/mfa/recovery-codes/generate",
    response_model=MfaRecoveryCodesGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_recovery_codes(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mfa.enroll_self")),
):
    return _generate_recovery_codes_impl(current_user, db)


def _recovery_codes_status_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> MfaRecoveryCodesStatusResponse:
    codes = db.exec(
        select(UserMfaRecoveryCode)
        .where(UserMfaRecoveryCode.tenant_id == user_context.tenant_id)
        .where(UserMfaRecoveryCode.user_id == user_context.id)
    ).all()
    unused = [c for c in codes if c.used_at is None]
    last_generated = (
        max((c.generated_at for c in codes), default=None) if codes else None
    )
    return MfaRecoveryCodesStatusResponse(
        unused_code_count=len(unused),
        last_generated_at=last_generated,
    )


@router.get(
    "/me/mfa/recovery-codes/status/test", response_model=MfaRecoveryCodesStatusResponse
)
def recovery_codes_status_test(db: Session = Depends(get_db)):
    ctx = get_test_context()
    return _recovery_codes_status_impl(ctx, db)


@router.get(
    "/me/mfa/recovery-codes/status", response_model=MfaRecoveryCodesStatusResponse
)
def recovery_codes_status(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mfa.enroll_self")),
):
    return _recovery_codes_status_impl(current_user, db)


# ---------------------------------------------------------------------------
# A70 — Active Sessions
# ---------------------------------------------------------------------------


def _get_sessions_impl(
    request: Request | None,
    current_session_id: uuid.UUID | None,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> list[SessionResponse]:
    sessions = db.exec(
        select(UserSessionMetadata)
        .where(UserSessionMetadata.tenant_id == user_context.tenant_id)
        .where(UserSessionMetadata.user_id == user_context.id)
        .where(UserSessionMetadata.revoked_at == None)
    ).all()

    result = []
    for s in sessions:
        is_current = (
            current_session_id is not None and s.session_id == current_session_id
        )
        result.append(
            SessionResponse(
                session_id=s.session_id,
                display_label=s.display_label,
                ip_address=str(s.ip_address),
                geolocation=s.geolocation,
                created_at=s.created_at,
                last_active_at=s.last_active_at,
                is_current=is_current,
                revoked_at=s.revoked_at,
            )
        )
    return result


@router.get("/me/sessions/test", response_model=list[SessionResponse])
def get_sessions_test(db: Session = Depends(get_db)):
    ctx = get_test_context()
    return _get_sessions_impl(None, None, ctx, db)


@router.get("/me/sessions", response_model=list[SessionResponse])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("account.session.revoke_own")
    ),
):
    return _get_sessions_impl(None, None, current_user, db)


def _revoke_session_impl(
    session_id: uuid.UUID,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> None:
    found = revoke_session(
        db=db,
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        session_id=session_id,
        reason="user_revoked",
    )
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )


@router.delete("/me/sessions/{session_id}/test", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session_test(session_id: uuid.UUID, db: Session = Depends(get_db)):
    ctx = get_test_context()
    _revoke_session_impl(session_id, ctx, db)


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session_route(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("account.session.revoke_own")
    ),
):
    _revoke_session_impl(session_id, current_user, db)


def _revoke_others_impl(
    current_session_id: uuid.UUID | None,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> RevokeOthersResponse:
    if current_session_id is None:
        # No current session context in test mode — revoke all
        current_session_id = uuid.uuid4()
    count = revoke_others(
        db=db,
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        current_session_id=current_session_id,
        reason="revoke_others",
    )
    return RevokeOthersResponse(revoked_count=count)


@router.post("/me/sessions/revoke-others/test", response_model=RevokeOthersResponse)
def revoke_others_test(db: Session = Depends(get_db)):
    ctx = get_test_context()
    return _revoke_others_impl(None, ctx, db)


@router.post("/me/sessions/revoke-others", response_model=RevokeOthersResponse)
def revoke_others_route(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("account.session.revoke_own")
    ),
):
    # current_session_id would come from JWT claim in full implementation
    return _revoke_others_impl(None, current_user, db)


# ---------------------------------------------------------------------------
# A71 — Data Exports
# ---------------------------------------------------------------------------


def _create_data_export_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> DataExportCreateResponse:
    """
    Create a pending data export request, then enqueue the Celery task.
    Frequency limit: 429 if user has pending/processing export, or ready/failed within 24h.
    """
    now = datetime.now(UTC)
    cutoff_24h = now - timedelta(hours=24)

    # Check for blocking exports
    existing = db.exec(
        select(DataExportRequest)
        .where(DataExportRequest.tenant_id == user_context.tenant_id)
        .where(DataExportRequest.user_id == user_context.id)
    ).all()

    for ex in existing:
        if ex.status in ("pending", "processing"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="An export is already in progress. Please wait for it to complete.",
            )
        if ex.status in ("ready", "failed") and ex.requested_at >= cutoff_24h:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="A data export was already requested in the past 24 hours.",
            )

    # Determine data scope by role
    # Owners get full_tenant; technicians get user_specific
    role_code = getattr(user_context, "role_code", "technician")
    data_scope = "full_tenant" if role_code == "owner" else "user_specific"

    export = DataExportRequest(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        status="pending",
        data_scope=data_scope,
        requested_at=now,
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    # Enqueue Celery task
    try:
        from tasks.data_export_pipeline import process_data_export

        process_data_export.delay(str(export.export_id))
    except Exception as e:
        logger.warning(f"Failed to enqueue data export task: {e}")

    return DataExportCreateResponse(
        export_id=export.export_id,
        status=export.status,
        requested_at=export.requested_at,
    )


def _list_data_exports_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> list[DataExportStatusResponse]:
    exports = db.exec(
        select(DataExportRequest)
        .where(DataExportRequest.tenant_id == user_context.tenant_id)
        .where(DataExportRequest.user_id == user_context.id)
    ).all()
    return [DataExportStatusResponse.model_validate(e) for e in exports]


def _get_data_export_impl(
    export_id: uuid.UUID,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> DataExportStatusResponse:
    export = db.exec(
        select(DataExportRequest)
        .where(DataExportRequest.export_id == export_id)
        .where(DataExportRequest.tenant_id == user_context.tenant_id)
        .where(DataExportRequest.user_id == user_context.id)
    ).first()
    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        )
    return DataExportStatusResponse.model_validate(export)


@router.post(
    "/me/data-exports/test",
    response_model=DataExportCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_data_export_test(db: Session = Depends(get_db)):
    ctx = get_test_context()
    return _create_data_export_impl(ctx, db)


@router.post(
    "/me/data-exports",
    response_model=DataExportCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_data_export(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("account.data_export.request")
    ),
):
    return _create_data_export_impl(current_user, db)


@router.get("/me/data-exports/test", response_model=list[DataExportStatusResponse])
def list_data_exports_test(db: Session = Depends(get_db)):
    ctx = get_test_context()
    return _list_data_exports_impl(ctx, db)


@router.get("/me/data-exports", response_model=list[DataExportStatusResponse])
def list_data_exports(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("account.data_export.request")
    ),
):
    return _list_data_exports_impl(current_user, db)


@router.get(
    "/me/data-exports/{export_id}/test", response_model=DataExportStatusResponse
)
def get_data_export_test(export_id: uuid.UUID, db: Session = Depends(get_db)):
    ctx = get_test_context()
    return _get_data_export_impl(export_id, ctx, db)


@router.get("/me/data-exports/{export_id}", response_model=DataExportStatusResponse)
def get_data_export(
    export_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("account.data_export.request")
    ),
):
    return _get_data_export_impl(export_id, current_user, db)
