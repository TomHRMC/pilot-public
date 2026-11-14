"""C-B16 Part A — Tenant site authenticated routes.

GET    /api/v1/tenant-site                        — view config + defaults (settings.view)
PUT    /api/v1/tenant-site                        — upsert draft (settings.manage)
GET    /api/v1/tenant-site/slug-availability      — check slug (settings.view)
POST   /api/v1/tenant-site/publish                — publish site (settings.manage)
POST   /api/v1/tenant-site/unpublish              — unpublish site (settings.manage)

/test twins of PUT, publish, unpublish (unauthenticated, get_test_context).

Design: dev-docs/architecture-design/batch-designs/batch-c-b16-design.md §D
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from api.schemas.tenant_site import (
    PublishRequest,
    PublishResponse,
    SlugAvailabilityResponse,
    TenantSiteDefaults,
    TenantSiteGetResponse,
    TenantSiteResponse,
    TenantSiteUpsertRequest,
    UnpublishResponse,
)
from app.models.core import Tenant10DlcProfile
from app.models.tenant_site import TenantSite
from core.auth import AuthenticatedUser
from core.datetime_utils import safe_now_utc
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services import tenant_site_service as svc

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _rfc7807(err: svc.TenantSiteError) -> HTTPException:
    """Convert a TenantSiteError to an RFC 7807 HTTPException."""
    detail: dict = {
        "type": f"https://errors.pilotfortrades.com/{err.code}",
        "title": err.title,
        "status": err.http_status,
        "detail": err.detail,
    }
    if err.payload:
        detail.update(err.payload)
    return HTTPException(status_code=err.http_status, detail=detail)


def _to_response(
    db: Session, site: TenantSite | None, defaults: TenantSiteDefaults
) -> TenantSiteResponse:
    """Build a TenantSiteResponse from a site row + defaults."""
    requirements_emailed_at = svc.get_requirements_emailed_at(db, site.tenant_id)
    return TenantSiteResponse(
        id=site.id,
        tenant_id=site.tenant_id,
        slug=site.slug,
        site_kind=site.site_kind,
        status=site.status,
        display_name=site.display_name,
        tagline=site.tagline,
        public_email=site.public_email,
        public_phone=site.public_phone,
        public_city=site.public_city,
        public_state=site.public_state,
        public_address_line1=site.public_address_line1,
        public_postal_code=site.public_postal_code,
        show_full_address=site.show_full_address,
        template_version=site.template_version,
        published_at=site.published_at,
        unpublished_at=site.unpublished_at,
        kit_sent_at=site.kit_sent_at,
        website_auto_populated=site.website_auto_populated,
        idempotency_key=site.idempotency_key,
        site_url=svc.compute_site_url(site),
        requirements_emailed_at=requirements_emailed_at,
        defaults=defaults,
    )


def _to_publish_response(db: Session, result: svc.PublishResult) -> PublishResponse:
    """Build a PublishResponse from a PublishResult."""
    site = result.site
    requirements_emailed_at = svc.get_requirements_emailed_at(db, site.tenant_id)
    return PublishResponse(
        id=site.id,
        tenant_id=site.tenant_id,
        slug=site.slug,
        site_kind=site.site_kind,
        status=site.status,
        display_name=site.display_name,
        tagline=site.tagline,
        public_email=site.public_email,
        public_phone=site.public_phone,
        public_city=site.public_city,
        public_state=site.public_state,
        public_address_line1=site.public_address_line1,
        public_postal_code=site.public_postal_code,
        show_full_address=site.show_full_address,
        template_version=site.template_version,
        published_at=site.published_at,
        unpublished_at=site.unpublished_at,
        kit_sent_at=site.kit_sent_at,
        website_auto_populated=site.website_auto_populated,
        site_url=svc.compute_site_url(site),
        requirements_emailed_at=requirements_emailed_at,
        website_action=result.website_action,
        brand_status=result.brand_status,
        brand_guidance=result.brand_guidance,
    )


def _to_unpublish_response(
    db: Session, site: TenantSite, warning: str
) -> UnpublishResponse:
    """Build an UnpublishResponse from a site + warning."""
    requirements_emailed_at = svc.get_requirements_emailed_at(db, site.tenant_id)
    return UnpublishResponse(
        id=site.id,
        tenant_id=site.tenant_id,
        slug=site.slug,
        site_kind=site.site_kind,
        status=site.status,
        display_name=site.display_name,
        tagline=site.tagline,
        public_email=site.public_email,
        public_phone=site.public_phone,
        public_city=site.public_city,
        public_state=site.public_state,
        public_address_line1=site.public_address_line1,
        public_postal_code=site.public_postal_code,
        show_full_address=site.show_full_address,
        template_version=site.template_version,
        published_at=site.published_at,
        unpublished_at=site.unpublished_at,
        kit_sent_at=site.kit_sent_at,
        website_auto_populated=site.website_auto_populated,
        site_url=svc.compute_site_url(site),
        requirements_emailed_at=requirements_emailed_at,
        warning=warning,
    )


def _maybe_trigger_requirements_email(
    db: Session,
    tenant_id: uuid.UUID,
    site: TenantSite,
) -> None:
    """Option-1 email trigger (b) (§G-19).

    When the saved site_kind is 'compliance_kit', a tenant_10dlc_profile row
    exists, and requirements_emailed_at IS NULL → enqueue the requirements
    email and stamp requirements_emailed_at + kit_sent_at on success.
    """
    if site.site_kind != "compliance_kit":
        return

    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tenant_id)
    ).first()
    if not profile:
        return

    already_emailed = getattr(profile, "requirements_emailed_at", None)
    if already_emailed is not None:
        return

    # Enqueue the Celery task
    try:
        from tasks.tenant_site_emails import send_website_requirements_email

        send_website_requirements_email.delay(str(tenant_id))

        # Stamp on successful enqueue
        now = safe_now_utc()
        profile.requirements_emailed_at = now  # type: ignore[attr-defined]
        db.add(profile)
        site.kit_sent_at = now
        db.add(site)
        db.commit()
    except Exception:
        # Best-effort — don't block the PUT on email enqueue failure
        pass


# ─── Shared _impl functions ───────────────────────────────────────────────────


def _get_site_impl(db: Session, tenant_id: uuid.UUID) -> TenantSiteGetResponse:
    """GET logic — never 404 when no row (§D-1)."""
    defaults = svc.get_effective_defaults(db, tenant_id)
    site = svc.get_site(db, tenant_id)
    if not site:
        return TenantSiteGetResponse(configured=False, site=None, defaults=defaults)
    return TenantSiteGetResponse(
        configured=True,
        site=_to_response(db, site, defaults),
        defaults=defaults,
    )


def _upsert_site_impl(
    payload: TenantSiteUpsertRequest,
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_key: str | None = None,
) -> TenantSiteResponse:
    """PUT logic — upsert draft + Option-1 email trigger."""
    try:
        site = svc.upsert_draft(
            db, tenant_id, payload, idempotency_key=idempotency_key, user_id=user_id
        )
    except svc.TenantSiteError as exc:
        raise _rfc7807(exc) from exc

    # Option-1 email trigger (b)
    _maybe_trigger_requirements_email(db, tenant_id, site)

    defaults = svc.get_effective_defaults(db, tenant_id)
    return _to_response(db, site, defaults)


def _publish_site_impl(
    body: PublishRequest,
    db: Session,
    tenant_id: uuid.UUID,
) -> PublishResponse:
    """POST publish logic."""
    site = svc.get_site(db, tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://errors.pilotfortrades.com/no_draft",
                "title": "No draft to publish",
                "status": 409,
                "detail": "Create a draft site configuration before publishing.",
            },
        )
    try:
        result = svc.publish(
            db, site, confirm_website_overwrite=body.confirm_website_overwrite
        )
    except svc.TenantSiteError as exc:
        raise _rfc7807(exc) from exc

    # Invalidate public cache
    _invalidate_public_cache(site.slug)

    return _to_publish_response(db, result)


def _unpublish_site_impl(db: Session, tenant_id: uuid.UUID) -> UnpublishResponse:
    """POST unpublish logic."""
    site = svc.get_site(db, tenant_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://errors.pilotfortrades.com/not_published",
                "title": "Site is not published",
                "status": 409,
                "detail": "No published site to unpublish.",
            },
        )
    try:
        site = svc.unpublish(db, site)
    except svc.TenantSiteError as exc:
        raise _rfc7807(exc) from exc

    warning = svc.get_unpublish_warning(db, site)

    # Invalidate public cache
    _invalidate_public_cache(site.slug)

    return _to_unpublish_response(db, site, warning)


def _invalidate_public_cache(slug: str) -> None:
    """Best-effort cache invalidation on publish/unpublish."""
    try:
        from api.routes.public_tenant_sites import delete_public_cache

        delete_public_cache(slug)
    except Exception:
        pass  # Best-effort — don't block on cache errors


# ─── TEST ENDPOINTS (per §8.2 dual-endpoint pattern) ──────────────────────────


@router.put(
    "/test",
    response_model=TenantSiteResponse,
    summary="[TEST] Upsert tenant site draft — no auth",
    tags=["settings"],
)
def upsert_site_test(
    payload: TenantSiteUpsertRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _upsert_site_impl(payload, db, ctx.tenant_id, ctx.id, idempotency_key=None)


@router.post(
    "/publish/test",
    response_model=PublishResponse,
    summary="[TEST] Publish tenant site — no auth",
    tags=["settings"],
)
def publish_site_test(
    body: PublishRequest,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _publish_site_impl(body, db, ctx.tenant_id)


@router.post(
    "/unpublish/test",
    response_model=UnpublishResponse,
    summary="[TEST] Unpublish tenant site — no auth",
    tags=["settings"],
)
def unpublish_site_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    return _unpublish_site_impl(db, ctx.tenant_id)


# ─── AUTHENTICATED ENDPOINTS ──────────────────────────────────────────────────


@router.get(
    "",
    response_model=TenantSiteGetResponse,
    summary="Get tenant site configuration + defaults",
    tags=["settings"],
)
def get_site(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    return _get_site_impl(db, current_user.tenant_id)


@router.put(
    "",
    response_model=TenantSiteResponse,
    summary="Create or update tenant site draft",
    tags=["settings"],
)
def upsert_site(
    payload: TenantSiteUpsertRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
    idempotency_key: str | None = None,
):
    set_audit_context_sync(db, user_id=current_user.id)
    return _upsert_site_impl(
        payload, db, current_user.tenant_id, current_user.id, idempotency_key
    )


@router.get(
    "/slug-availability",
    response_model=SlugAvailabilityResponse,
    summary="Check slug availability",
    tags=["settings"],
)
def check_slug_availability(
    slug: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    if not slug or not slug.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://errors.pilotfortrades.com/missing_param",
                "title": "Missing required parameter",
                "status": 422,
                "detail": "The 'slug' query parameter is required.",
            },
        )
    result = svc.check_slug_availability(db, slug.strip())
    return SlugAvailabilityResponse(
        available=result.available,
        reason=result.reason,
        suggestion=result.suggestion,
    )


@router.post(
    "/publish",
    response_model=PublishResponse,
    summary="Publish tenant site",
    tags=["settings"],
)
def publish_site(
    body: PublishRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    set_audit_context_sync(db, user_id=current_user.id)
    return _publish_site_impl(body, db, current_user.tenant_id)


@router.post(
    "/unpublish",
    response_model=UnpublishResponse,
    summary="Unpublish tenant site",
    tags=["settings"],
)
def unpublish_site(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    set_audit_context_sync(db, user_id=current_user.id)
    return _unpublish_site_impl(db, current_user.tenant_id)
