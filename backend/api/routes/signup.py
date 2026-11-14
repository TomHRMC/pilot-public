"""
B14/A73 + A74 — Tenant Signup Wizard + Legal Acceptance routes.
POST /api/v1/signup          — initiate wizard (step 1, public)
PUT  /api/v1/signup/{id}/step{N} — advance wizard (steps 2-5, JWT required)
GET  /api/v1/signup/{id}/state   — resumability endpoint
POST /api/v1/signup/{id}/legal/accept  — record legal acceptance (A74)
GET  /api/v1/signup/{id}/legal/required — list required docs + acceptance status (A74)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from api.schemas.signup import (
    PhoneConsentRequest,
    PhoneConsentResponse,
    SendOptinRequest,
    SendOptinResponse,
)
from app.models.legal_acceptance import TenantLegalAcceptance
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.tenant_signup import (
    advance_wizard_step,
    get_signup_state,
    initiate_signup,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== SCHEMAS ====================


class SignupInitiateRequest(BaseModel):
    business_name: str
    trade: str
    business_size: str
    zip: str
    time_zone: str
    owner_email: str
    owner_first_name: str
    owner_last_name: str


class SignupInitiateResponse(BaseModel):
    tenant_id: UUID
    signup_state: str
    owner_email: str
    credential_pending: bool = False


class SignupStepRequest(BaseModel):
    # Step 2: legal docs accepted
    documents_accepted: list[str] | None = None
    # Step 3: "Stay Informed" (SIGNUP-C) — phone is REQUIRED, phone_skipped removed.
    phone_number: str | None = None
    sms_consent: bool | None = None
    disclosure_hash: str | None = None
    # Step 4: tier
    selected_tier_id: UUID | None = None
    # Step 5: confirm
    confirmed: bool | None = None
    stripe_payment_method_id: str | None = None


class SignupStepResponse(BaseModel):
    tenant_id: UUID
    signup_state: str
    next_step: str | None


class SignupStateResponse(BaseModel):
    tenant_id: UUID
    signup_state: str
    collected_data: dict


# ==================== TEST ENDPOINTS (register FIRST) ====================


@router.post(
    "/test",
    response_model=SignupInitiateResponse,
    status_code=status.HTTP_201_CREATED,
)
def initiate_signup_test(data: SignupInitiateRequest, db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Blocked in staging/production."""
    get_test_context()
    result = initiate_signup(
        db=db,
        business_name=data.business_name,
        trade=data.trade,
        business_size=data.business_size,
        zip_code=data.zip,
        time_zone=data.time_zone,
        owner_email=data.owner_email,
        owner_first_name=data.owner_first_name,
        owner_last_name=data.owner_last_name,
    )
    return SignupInitiateResponse(
        tenant_id=UUID(result["tenant_id"]),
        signup_state=result["signup_state"],
        owner_email=result["owner_email"],
        credential_pending=result.get("credential_pending", False),
    )


@router.put(
    "/{tenant_id}/step2/test",
    response_model=SignupStepResponse,
    status_code=status.HTTP_200_OK,
)
def advance_step2_test(
    tenant_id: UUID, data: SignupStepRequest, db: Session = Depends(get_db)
):
    """Test endpoint for step 2."""
    get_test_context()
    result = advance_wizard_step(
        db, tenant_id, "step1_account", data.model_dump(exclude_none=True)
    )
    return SignupStepResponse(**result)


@router.put(
    "/{tenant_id}/step3/test",
    response_model=SignupStepResponse,
    status_code=status.HTTP_200_OK,
)
def advance_step3_test(
    tenant_id: UUID, data: SignupStepRequest, db: Session = Depends(get_db)
):
    get_test_context()
    result = advance_wizard_step(
        db, tenant_id, "step2_legal", data.model_dump(exclude_none=True)
    )
    return SignupStepResponse(**result)


@router.put(
    "/{tenant_id}/step4/test",
    response_model=SignupStepResponse,
    status_code=status.HTTP_200_OK,
)
def advance_step4_test(
    tenant_id: UUID, data: SignupStepRequest, db: Session = Depends(get_db)
):
    get_test_context()
    result = advance_wizard_step(
        db, tenant_id, "step3_phone", data.model_dump(exclude_none=True)
    )
    return SignupStepResponse(**result)


@router.put(
    "/{tenant_id}/step5/test",
    response_model=SignupStepResponse,
    status_code=status.HTTP_200_OK,
)
def advance_step5_test(
    tenant_id: UUID, data: SignupStepRequest, db: Session = Depends(get_db)
):
    get_test_context()
    result = advance_wizard_step(
        db, tenant_id, "step4_tier", data.model_dump(exclude_none=True)
    )
    return SignupStepResponse(**result)


@router.get(
    "/{tenant_id}/state/test",
    response_model=SignupStateResponse,
    status_code=status.HTTP_200_OK,
)
def get_signup_state_test(tenant_id: UUID, db: Session = Depends(get_db)):
    get_test_context()
    result = get_signup_state(db, tenant_id)
    return SignupStateResponse(**result)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.post(
    "/",
    response_model=SignupInitiateResponse,
    status_code=status.HTTP_201_CREATED,
)
def initiate_signup_route(
    data: SignupInitiateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Step 1: Initiate tenant signup. Public — no JWT required.
    Creates tenant + tenant_signup record.
    """
    result = initiate_signup(
        db=db,
        business_name=data.business_name,
        trade=data.trade,
        business_size=data.business_size,
        zip_code=data.zip,
        time_zone=data.time_zone,
        owner_email=data.owner_email,
        owner_first_name=data.owner_first_name,
        owner_last_name=data.owner_last_name,
        request=request,
    )
    return SignupInitiateResponse(
        tenant_id=UUID(result["tenant_id"]),
        signup_state=result["signup_state"],
        owner_email=result["owner_email"],
        credential_pending=result.get("credential_pending", False),
    )


@router.put(
    "/{tenant_id}/step2",
    response_model=SignupStepResponse,
    status_code=status.HTTP_200_OK,
)
def advance_signup_step2(
    tenant_id: UUID,
    data: SignupStepRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("tenant.signup.complete")
    ),
):
    set_audit_context_sync(db, current_user.id)
    result = advance_wizard_step(
        db, tenant_id, "step1_account", data.model_dump(exclude_none=True), request
    )
    return SignupStepResponse(**result)


@router.put(
    "/{tenant_id}/step3",
    response_model=SignupStepResponse,
    status_code=status.HTTP_200_OK,
)
def advance_signup_step3(
    tenant_id: UUID,
    data: SignupStepRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("tenant.signup.complete")
    ),
):
    set_audit_context_sync(db, current_user.id)
    step_data = data.model_dump(exclude_none=True)
    step_data["user_id"] = current_user.id
    result = advance_wizard_step(db, tenant_id, "step2_legal", step_data, request)
    return SignupStepResponse(**result)


@router.put(
    "/{tenant_id}/step4",
    response_model=SignupStepResponse,
    status_code=status.HTTP_200_OK,
)
def advance_signup_step4(
    tenant_id: UUID,
    data: SignupStepRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("tenant.signup.complete")
    ),
):
    set_audit_context_sync(db, current_user.id)
    result = advance_wizard_step(
        db, tenant_id, "step3_phone", data.model_dump(exclude_none=True), request
    )
    return SignupStepResponse(**result)


@router.put(
    "/{tenant_id}/step5",
    response_model=SignupStepResponse,
    status_code=status.HTTP_200_OK,
)
def advance_signup_step5(
    tenant_id: UUID,
    data: SignupStepRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("tenant.signup.complete")
    ),
):
    set_audit_context_sync(db, current_user.id)
    step_data = data.model_dump(exclude_none=True)
    step_data["user_id"] = current_user.id
    result = advance_wizard_step(db, tenant_id, "step4_tier", step_data, request)
    return SignupStepResponse(**result)


@router.get(
    "/{tenant_id}/state",
    response_model=SignupStateResponse,
    status_code=status.HTTP_200_OK,
)
def get_signup_state_route(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("tenant.signup.complete")
    ),
):
    result = get_signup_state(db, tenant_id)
    return SignupStateResponse(**result)


# ==================== SIGNUP-C: PHONE CONSENT + DOUBLE OPT-IN ENDPOINTS ====================


def _phone_consent_impl(
    tenant_id: UUID,
    data: PhoneConsentRequest,
    db: Session,
    user_id: UUID,
    client_ip: str | None,
) -> PhoneConsentResponse:
    """Shared logic for recording the owner's phone + SMS consent (SIGNUP-C)."""
    from services.notification_endpoints import upsert_owner_sms_endpoint

    endpoint = upsert_owner_sms_endpoint(
        db,
        user_id=user_id,
        tenant_id=tenant_id,
        phone=data.phone_number,
        consent=data.sms_consent,
        ip=client_ip,
        disclosure_hash=data.disclosure_hash,
    )
    return PhoneConsentResponse(
        user_endpoint_id=endpoint.id,
        verification_status=endpoint.verification_status,
    )


def _send_optin_impl(
    tenant_id: UUID,
    data: SendOptinRequest,
    db: Session,
    user_id: UUID,
) -> SendOptinResponse:
    """Shared logic for enqueuing the platform double-opt-in SMS (SIGNUP-C)."""
    from datetime import UTC, datetime, timedelta

    from app.models.core import UserEndpoint

    endpoint = db.exec(
        select(UserEndpoint).where(
            UserEndpoint.id == data.user_endpoint_id,
            UserEndpoint.user_id == user_id,
        )
    ).first()

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Endpoint not found",
                "status": 404,
                "detail": "SMS endpoint not found for this user.",
            },
        )

    if not endpoint.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/validation-error",
                "title": "Validation Error",
                "status": 422,
                "detail": "Endpoint has no phone number.",
            },
        )

    # Resend cooldown — prevent spamming. Only blocks if a double-opt-in SMS
    # was already sent within the last 60s (checked via the audit trail, not
    # consent_updated_at, so the first send right after attestation is allowed).
    from app.models.communications import UserSmsConsentAudit

    last_sent = db.exec(
        select(UserSmsConsentAudit)
        .where(
            UserSmsConsentAudit.user_endpoint_id == endpoint.id,
            UserSmsConsentAudit.action == "double_opt_in_sent",
        )
        .order_by(UserSmsConsentAudit.created_at.desc())
    ).first()
    if last_sent is not None:
        elapsed = datetime.now(UTC) - last_sent.created_at
        if elapsed < timedelta(seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "type": "https://errors.pilotfortrades.com/rate-limited",
                    "title": "Resend cooldown",
                    "status": 429,
                    "detail": "Please wait before requesting another opt-in text.",
                },
            )

    from tasks.sms_compliance_platform import send_platform_double_optin_sms

    send_platform_double_optin_sms.delay(str(user_id), str(tenant_id))
    return SendOptinResponse(status="sent")


# ---- TEST ENDPOINTS ----


@router.post(
    "/{tenant_id}/phone/consent/test",
    response_model=PhoneConsentResponse,
    status_code=status.HTTP_201_CREATED,
)
def phone_consent_test(
    tenant_id: UUID,
    data: PhoneConsentRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    """Test endpoint — bypasses JWT, uses canonical test tenant."""
    return _phone_consent_impl(
        tenant_id=tenant_id,
        data=data,
        db=db,
        user_id=ctx.id,
        client_ip="127.0.0.1",
    )


@router.post(
    "/{tenant_id}/phone/send-optin/test",
    response_model=SendOptinResponse,
    status_code=status.HTTP_200_OK,
)
def send_optin_test(
    tenant_id: UUID,
    data: SendOptinRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    """Test endpoint — bypasses JWT, uses canonical test tenant."""
    return _send_optin_impl(tenant_id=tenant_id, data=data, db=db, user_id=ctx.id)


# ---- AUTHENTICATED ENDPOINTS ----


@router.post(
    "/{tenant_id}/phone/consent",
    response_model=PhoneConsentResponse,
    status_code=status.HTTP_201_CREATED,
)
def phone_consent(
    tenant_id: UUID,
    data: PhoneConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("tenant.signup.complete")
    ),
):
    """Record the owner's mobile + SMS consent (SIGNUP-C "Stay Informed")."""
    set_audit_context_sync(db, current_user.id)
    client_ip = request.client.host if request.client else None
    return _phone_consent_impl(
        tenant_id=tenant_id,
        data=data,
        db=db,
        user_id=current_user.id,
        client_ip=client_ip,
    )


@router.post(
    "/{tenant_id}/phone/send-optin",
    response_model=SendOptinResponse,
    status_code=status.HTTP_200_OK,
)
def send_optin(
    tenant_id: UUID,
    data: SendOptinRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("tenant.signup.complete")
    ),
):
    """Enqueue the platform double-opt-in SMS to the owner (SIGNUP-C)."""
    set_audit_context_sync(db, current_user.id)
    return _send_optin_impl(
        tenant_id=tenant_id, data=data, db=db, user_id=current_user.id
    )


# ==================== A74: LEGAL ACCEPTANCE ENDPOINTS ====================

# Document version hashes — placeholder SHA-256 values for dev/test
# In production: compute from actual published document content
DOCUMENT_HASHES = {
    "tos": "a" * 64,
    "privacy": "b" * 64,
    "eula": "c" * 64,
    "marketing_email_optin": "d" * 64,
}
REQUIRED_DOCUMENTS = ["tos", "privacy", "eula"]


class LegalAcceptRequest(BaseModel):
    document_type: str
    document_version_hash: str
    accepted_at: str  # ISO timestamp from client


class LegalAcceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    acceptance_id: UUID
    document_type: str
    accepted_at: str


class RequiredDocumentStatus(BaseModel):
    document_type: str
    current_version_hash: str
    already_accepted: bool


class LegalRequiredResponse(BaseModel):
    required_documents: list[RequiredDocumentStatus]


def _record_legal_acceptance_impl(
    tenant_id: UUID,
    user_id: UUID,
    data: LegalAcceptRequest,
    db: Session,
    client_ip: str,
    user_agent: str,
) -> LegalAcceptResponse:
    """Shared logic for recording legal acceptance."""
    from datetime import datetime

    valid_types = list(DOCUMENT_HASHES.keys())
    if data.document_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid document_type. Must be one of: {valid_types}",
        )

    try:
        accepted_at = datetime.fromisoformat(data.accepted_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid accepted_at format. Use ISO 8601.",
        )

    acceptance = TenantLegalAcceptance(
        tenant_id=tenant_id,
        user_id=user_id,
        document_type=data.document_type,
        document_version_hash=data.document_version_hash,
        accepted_at=accepted_at,
        ip_address=client_ip,
        user_agent=user_agent,
        created_by=user_id,
    )
    db.add(acceptance)
    db.commit()
    db.refresh(acceptance)

    return LegalAcceptResponse(
        acceptance_id=acceptance.acceptance_id,
        document_type=acceptance.document_type,
        accepted_at=acceptance.accepted_at.isoformat(),
    )


def _get_legal_required_impl(
    tenant_id: UUID,
    user_id: UUID,
    db: Session,
) -> LegalRequiredResponse:
    """Return required docs with acceptance status for this user."""
    from app.models.legal_acceptance import TenantLegalAcceptance as LegalAcceptance

    accepted = db.exec(
        select(LegalAcceptance)
        .where(LegalAcceptance.tenant_id == tenant_id)
        .where(LegalAcceptance.user_id == user_id)
        .where(LegalAcceptance.document_type.in_(REQUIRED_DOCUMENTS))
    ).all()
    accepted_types = {a.document_type for a in accepted}

    required = [
        RequiredDocumentStatus(
            document_type=doc_type,
            current_version_hash=DOCUMENT_HASHES[doc_type],
            already_accepted=doc_type in accepted_types,
        )
        for doc_type in REQUIRED_DOCUMENTS
    ]

    return LegalRequiredResponse(required_documents=required)


# ---- TEST ENDPOINTS ----


@router.post(
    "/{tenant_id}/legal/accept/test",
    response_model=LegalAcceptResponse,
    status_code=status.HTTP_201_CREATED,
)
def accept_legal_document_test(
    tenant_id: UUID,
    data: LegalAcceptRequest,
    db: Session = Depends(get_db),
):
    test_ctx = get_test_context()
    return _record_legal_acceptance_impl(
        tenant_id=tenant_id,
        user_id=test_ctx.id,
        data=data,
        db=db,
        client_ip="127.0.0.1",
        user_agent="test",
    )


@router.get(
    "/{tenant_id}/legal/required/test",
    response_model=LegalRequiredResponse,
    status_code=status.HTTP_200_OK,
)
def get_legal_required_test(
    tenant_id: UUID,
    db: Session = Depends(get_db),
):
    test_ctx = get_test_context()
    return _get_legal_required_impl(tenant_id=tenant_id, user_id=test_ctx.id, db=db)


# ---- AUTHENTICATED ENDPOINTS ----


@router.post(
    "/{tenant_id}/legal/accept",
    response_model=LegalAcceptResponse,
    status_code=status.HTTP_201_CREATED,
)
def accept_legal_document(
    tenant_id: UUID,
    data: LegalAcceptRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("legal_acceptance.accept")
    ),
):
    """Record legal document acceptance. Immutable — cannot be modified after recording."""
    set_audit_context_sync(db, current_user.id)
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return _record_legal_acceptance_impl(
        tenant_id=tenant_id,
        user_id=current_user.id,
        data=data,
        db=db,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.get(
    "/{tenant_id}/legal/required",
    response_model=LegalRequiredResponse,
    status_code=status.HTTP_200_OK,
)
def get_legal_required(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("tenant.signup.complete")
    ),
):
    """Return list of required legal documents and current acceptance status."""
    return _get_legal_required_impl(tenant_id=tenant_id, user_id=current_user.id, db=db)
