"""
10DLC Business Profile Routes — DLC-1
======================================
GET  /api/v1/settings/10dlc-profile       — view profile (settings.view)
PUT  /api/v1/settings/10dlc-profile       — upsert profile (settings.manage)
GET  /api/v1/settings/10dlc-profile/test  — test endpoint (no auth)
PUT  /api/v1/settings/10dlc-profile/test  — test endpoint (no auth)

Single-row-per-tenant upsert pattern (same as TenantEmailBranding).
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.schemas.dlc import Tenant10DlcProfileRequest, Tenant10DlcProfileResponse
from app.models.core import Tenant10DlcProfile
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


def _mask_ein(ein: str | None) -> str | None:
    """Mask EIN to last 4 digits: **-***1234"""
    if not ein:
        return None
    clean = ein.replace("-", "").strip()
    if len(clean) < 4:
        return "**-***" + clean
    return "**-***" + clean[-4:]


def _to_response(profile: Tenant10DlcProfile) -> Tenant10DlcProfileResponse:
    return Tenant10DlcProfileResponse(
        tenant_id=profile.tenant_id,
        legal_business_name=profile.legal_business_name,
        dba_name=profile.dba_name,
        ein_masked=_mask_ein(profile.ein),
        hq_address_line1=profile.hq_address_line1,
        hq_address_line2=profile.hq_address_line2,
        hq_city=profile.hq_city,
        hq_state=profile.hq_state,
        hq_postal_code=profile.hq_postal_code,
        hq_country=profile.hq_country,
        support_email=profile.support_email,
        support_phone=profile.support_phone,
        website=profile.website,
        stock_symbol=profile.stock_symbol,
        vertical=profile.vertical,
        updated_at=profile.updated_at,
    )


def _upsert_10dlc_profile_impl(
    payload: Tenant10DlcProfileRequest,
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Tenant10DlcProfileResponse:
    """Shared upsert logic — called by both authenticated and test endpoints.

    C-B16 hooks (§G-18/19):
    - After a successful update where website changed, call
      ``on_profile_website_changed`` for reconciliation.
    - Email trigger (a): when the new website is non-empty, non-Pilot, and
      ``requirements_emailed_at IS NULL`` → enqueue the requirements email
      and stamp ``requirements_emailed_at`` on successful enqueue.
    """
    now = datetime.now(UTC)

    existing = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tenant_id)
    ).first()

    if existing:
        # Track website change for C-B16 hooks
        old_website = existing.website
        website_changed = old_website != payload.website

        existing.legal_business_name = payload.legal_business_name
        existing.dba_name = payload.dba_name
        if payload.ein is not None:
            existing.ein = payload.ein  # only overwrite if explicitly provided
        existing.hq_address_line1 = payload.hq_address_line1
        existing.hq_address_line2 = payload.hq_address_line2
        existing.hq_city = payload.hq_city
        existing.hq_state = payload.hq_state
        existing.hq_postal_code = payload.hq_postal_code
        existing.hq_country = payload.hq_country
        existing.support_email = payload.support_email
        existing.support_phone = payload.support_phone
        existing.website = payload.website
        existing.stock_symbol = payload.stock_symbol
        existing.vertical = payload.vertical
        existing.updated_by = user_id
        db.add(existing)
        db.commit()
        db.refresh(existing)

        # C-B16: Profile-edit reconciliation + email trigger (a)
        if website_changed:
            _handle_website_changed(db, tenant_id, payload.website)

        return _to_response(existing)
    else:
        # Build kwargs — exclude ein from model_dump if None to avoid overwriting
        dump_kwargs: dict = payload.model_dump()
        profile = Tenant10DlcProfile(
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
            created_by=user_id,
            updated_by=user_id,
            legal_business_name=dump_kwargs["legal_business_name"],
            dba_name=dump_kwargs.get("dba_name"),
            ein=dump_kwargs.get("ein"),
            hq_address_line1=dump_kwargs.get("hq_address_line1"),
            hq_address_line2=dump_kwargs.get("hq_address_line2"),
            hq_city=dump_kwargs.get("hq_city"),
            hq_state=dump_kwargs.get("hq_state"),
            hq_postal_code=dump_kwargs.get("hq_postal_code"),
            hq_country=dump_kwargs.get("hq_country", "US"),
            support_email=dump_kwargs.get("support_email"),
            support_phone=dump_kwargs.get("support_phone"),
            website=dump_kwargs.get("website"),
            stock_symbol=dump_kwargs.get("stock_symbol"),
            vertical=dump_kwargs.get("vertical"),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        # C-B16: Email trigger (a) — new profile with a self-managed website
        if payload.website:
            _handle_website_changed(db, tenant_id, payload.website)

        return _to_response(profile)


def _handle_website_changed(
    db: Session, tenant_id: uuid.UUID, new_website: str | None
) -> None:
    """C-B16 profile-PUT hook: reconciliation + one-time requirements email.

    1. Call ``on_profile_website_changed`` — flips ``website_auto_populated``
       FALSE when the new value is a non-Pilot URL (§G-18).
    2. Email trigger (a) (§G-19): when the new value is non-empty, non-Pilot,
       and ``requirements_emailed_at IS NULL`` → enqueue the requirements
       email and stamp ``requirements_emailed_at`` on successful enqueue.
    """
    from core.config import settings as _settings
    from core.datetime_utils import safe_now_utc
    from services import tenant_site_service as _svc

    if not new_website:
        return

    base_domain = _settings.TENANT_SITES_BASE_DOMAIN
    is_pilot_url = f".{base_domain}" in new_website

    # Reconciliation hook (§G-18)
    _svc.on_profile_website_changed(db, tenant_id, new_website)

    # Email trigger (a) — only for non-Pilot URLs
    if is_pilot_url:
        return

    # Check requirements_emailed_at guard
    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tenant_id)
    ).first()
    if not profile:
        return

    already_emailed = getattr(profile, "requirements_emailed_at", None)
    if already_emailed is not None:
        return

    try:
        from tasks.tenant_site_emails import send_website_requirements_email

        send_website_requirements_email.delay(str(tenant_id))
        # Stamp on successful enqueue
        profile.requirements_emailed_at = safe_now_utc()  # type: ignore[attr-defined]
        db.add(profile)
        db.commit()
    except Exception:
        pass  # Best-effort — don't block the profile PUT on email enqueue failure


# ── TEST ENDPOINTS FIRST (per §8.2 dual-endpoint pattern) ───────────────────


@router.get(
    "/10dlc-profile/test",
    response_model=Tenant10DlcProfileResponse,
    summary="[TEST] Get 10DLC profile — no auth",
    tags=["settings"],
)
def get_10dlc_profile_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == ctx.tenant_id)
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "10DLC profile not configured",
                "status": 404,
                "detail": "No 10DLC business profile has been saved for this tenant.",
            },
        )
    return _to_response(profile)


@router.put(
    "/10dlc-profile/test",
    response_model=Tenant10DlcProfileResponse,
    summary="[TEST] Upsert 10DLC profile — no auth",
    tags=["settings"],
)
def put_10dlc_profile_test(
    payload: Tenant10DlcProfileRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _upsert_10dlc_profile_impl(payload, db, ctx.tenant_id, ctx.id)


# ── AUTHENTICATED ENDPOINTS ──────────────────────────────────────────────────


@router.get(
    "/10dlc-profile",
    response_model=Tenant10DlcProfileResponse,
    summary="Get 10DLC business profile",
    tags=["settings"],
)
def get_10dlc_profile(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    profile = db.exec(
        select(Tenant10DlcProfile).where(
            Tenant10DlcProfile.tenant_id == current_user.tenant_id
        )
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "10DLC profile not configured",
                "status": 404,
                "detail": "No 10DLC business profile has been saved for this tenant yet.",
            },
        )
    return _to_response(profile)


@router.put(
    "/10dlc-profile",
    response_model=Tenant10DlcProfileResponse,
    summary="Create or update 10DLC business profile",
    tags=["settings"],
)
def put_10dlc_profile(
    payload: Tenant10DlcProfileRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    set_audit_context_sync(db, user_id=current_user.id)
    return _upsert_10dlc_profile_impl(
        payload, db, current_user.tenant_id, current_user.id
    )
