"""Tenant site service — C-B16 Part A.

Implements the design §F interface: slug validation, draft upsert, snapshot
building, publish (three-way website rule + brand classification), unpublish,
and the profile-edit reconciliation hook.

All functions are sync ``def`` and take an injected ``Session`` (testable
without a request). Every query is tenant-scoped except ``get_published_snapshot``
and ``check_slug_availability``, which are keyed by the globally-unique ``slug``.

Design: dev-docs/architecture-design/batch-designs/batch-c-b16-design.md §F + §G
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session, select

from api.schemas.tenant_site import TenantSiteDefaults
from app.models.core import Tenant10DlcProfile
from app.models.sms import TenantMessagingRegistration
from app.models.tenant_site import TenantSite
from core.config import settings
from core.datetime_utils import safe_now_utc
from services.tenant_site_templates import render_page_paragraphs, render_template

# ─── Constants ────────────────────────────────────────────────────────────────

# Mirrors ck_tenant_site_slug_format: ^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$
SLUG_RE: re.Pattern = re.compile(r"^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$")

RESERVED_SLUGS: frozenset = frozenset(
    {
        "www",
        "api",
        "app",
        "mail",
        "smtp",
        "support",
        "help",
        "admin",
        "pilot",
        "p4t",
        "pilotfortrades",
        "staging",
        "dev",
        "qa",
        "test",
        "status",
        "billing",
        "login",
        "signup",
        "marketing",
        "cdn",
        "assets",
    }
)

# Brand status classification buckets (§G-17)
# Based on the C-B9 10DLC state machine (messaging_provisioning.py):
#   quoting, brand_submitted, brand_verified, awaiting_otp, brand_rejected,
#   campaign_submitted, awaiting_number_selection, number_assigned, active
_BRAND_DRAFT_STATUSES = frozenset({"quoting"})
_BRAND_IN_FLIGHT_STATUSES = frozenset(
    {
        "brand_submitted",
        "brand_verified",
        "awaiting_otp",
        "campaign_submitted",
        "awaiting_number_selection",
        "number_assigned",
    }
)
_BRAND_REJECTED_STATUSES = frozenset({"brand_rejected"})
_BRAND_LIVE_STATUSES = frozenset({"active"})


# ─── Data classes for service results ─────────────────────────────────────────


@dataclass
class SlugAvailability:
    available: bool
    reason: str | None = None  # 'taken' | 'invalid' | 'reserved'
    suggestion: str | None = None


@dataclass
class WebsiteAction:
    action: str  # 'set' | 'kept' | 'overwritten'
    brand_status: str  # raw registration status, or "none"
    brand_guidance: str  # 'none_or_draft' | 'in_flight' | 'brand_rejected' | 'live'
    current_url: str | None = None
    new_url: str | None = None


@dataclass
class PublishResult:
    site: TenantSite
    website_action: str  # 'set' | 'kept' | 'overwritten'
    brand_status: str
    brand_guidance: str


# ─── Exceptions ───────────────────────────────────────────────────────────────


class TenantSiteError(Exception):
    """Base exception for tenant-site service errors.

    Carries an RFC 7807-compatible error code in ``self.code`` and an
    optional ``payload`` dict for additional detail fields.
    """

    def __init__(
        self,
        code: str,
        title: str,
        status: int,
        detail: str,
        payload: dict | None = None,
    ):
        self.code = code
        self.title = title
        self.http_status = status
        self.detail = detail
        self.payload = payload
        super().__init__(detail)


# ─── Public service functions ─────────────────────────────────────────────────


def get_site(db: Session, tenant_id: uuid.UUID) -> TenantSite | None:
    """Fetch the tenant's site row (tenant-scoped)."""
    return db.exec(select(TenantSite).where(TenantSite.tenant_id == tenant_id)).first()


def get_effective_defaults(db: Session, tenant_id: uuid.UUID) -> TenantSiteDefaults:
    """Compute effective defaults from the tenant's 10DLC profile.

    display_name ← dba_name or legal_business_name
    public_email ← support_email
    public_phone ← support_phone
    public_city ← hq_city
    public_state ← hq_state
    Street address is NEVER defaulted (§G-10).
    """
    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tenant_id)
    ).first()

    if not profile:
        return TenantSiteDefaults()

    display_name = profile.dba_name or profile.legal_business_name
    display_name_source = "tenant_override" if profile.dba_name else "tenant_override"

    return TenantSiteDefaults(
        display_name=display_name,
        display_name_source=display_name_source,
        public_email=profile.support_email,
        public_email_source="tenant_override" if profile.support_email else None,
        public_phone=profile.support_phone,
        public_phone_source="tenant_override" if profile.support_phone else None,
        public_city=profile.hq_city,
        public_city_source="tenant_override" if profile.hq_city else None,
        public_state=profile.hq_state,
        public_state_source="tenant_override" if profile.hq_state else None,
    )


def check_slug_availability(db: Session, slug: str) -> SlugAvailability:
    """Check if a slug is available for use.

    Returns SlugAvailability with:
    - available=True if the slug is valid, not reserved, and not taken.
    - reason='invalid' if the slug fails format validation.
    - reason='reserved' if the slug is in the reserved list.
    - reason='taken' if another tenant already uses this slug (+suggestion).
    """
    slug_lower = slug.strip().lower()

    if not SLUG_RE.match(slug_lower):
        return SlugAvailability(available=False, reason="invalid")

    if slug_lower in RESERVED_SLUGS:
        return SlugAvailability(available=False, reason="reserved")

    existing = db.exec(select(TenantSite).where(TenantSite.slug == slug_lower)).first()

    if existing:
        suggestion = _derive_suggestion(db, slug_lower)
        return SlugAvailability(available=False, reason="taken", suggestion=suggestion)

    return SlugAvailability(available=True)


def upsert_draft(
    db: Session,
    tenant_id: uuid.UUID,
    payload,  # TenantSiteUpsertRequest
    idempotency_key: str | None = None,
    user_id: uuid.UUID | None = None,
) -> TenantSite:
    """Upsert a draft site configuration for the tenant.

    Slug rules:
    - Invalid format → 422 slug_invalid
    - Reserved → 422 slug_reserved
    - Taken by another tenant → 409 slug_taken
    - Slug change after first publish → 409 slug_immutable
    """
    slug = payload.slug.strip().lower()

    # Validate slug format
    if not SLUG_RE.match(slug):
        raise TenantSiteError(
            code="slug_invalid",
            title="Invalid slug format",
            status=422,
            detail=(
                "Slug must be 1-63 characters, lowercase alphanumeric and "
                "hyphens, starting and ending with a letter or number."
            ),
        )

    # Check reserved
    if slug in RESERVED_SLUGS:
        raise TenantSiteError(
            code="slug_reserved",
            title="Slug is reserved",
            status=422,
            detail=f"The slug '{slug}' is reserved and cannot be used.",
        )

    existing = get_site(db, tenant_id)

    if existing:
        # Slug immutability after first publish
        if existing.slug != slug and existing.status in ("published", "unpublished"):
            raise TenantSiteError(
                code="slug_immutable",
                title="Slug cannot be changed after publishing",
                status=409,
                detail=(
                    "The slug is immutable once the site has been published. "
                    "Contact support to change it."
                ),
            )

        # Check if slug is taken by another tenant
        if existing.slug != slug:
            other = db.exec(select(TenantSite).where(TenantSite.slug == slug)).first()
            if other:
                suggestion = _derive_suggestion(db, slug)
                raise TenantSiteError(
                    code="slug_taken",
                    title="Slug is already taken",
                    status=409,
                    detail=f"The slug '{slug}' is already in use by another tenant.",
                    payload={"suggestion": suggestion},
                )

        # Update existing draft
        existing.slug = slug
        existing.site_kind = payload.site_kind
        if payload.display_name is not None:
            existing.display_name = payload.display_name
        existing.tagline = payload.tagline
        existing.public_email = payload.public_email
        existing.public_phone = payload.public_phone
        existing.public_city = payload.public_city
        existing.public_state = payload.public_state
        existing.public_address_line1 = payload.public_address_line1
        existing.public_postal_code = payload.public_postal_code
        existing.show_full_address = payload.show_full_address
        if idempotency_key:
            existing.idempotency_key = idempotency_key
        if user_id:
            existing.updated_by = user_id
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Check slug availability for new row
        other = db.exec(select(TenantSite).where(TenantSite.slug == slug)).first()
        if other:
            suggestion = _derive_suggestion(db, slug)
            raise TenantSiteError(
                code="slug_taken",
                title="Slug is already taken",
                status=409,
                detail=f"The slug '{slug}' is already in use by another tenant.",
                payload={"suggestion": suggestion},
            )

        # Create new draft
        # display_name is required — use payload or fall back to slug
        display_name = payload.display_name or slug.replace("-", " ").title()
        site = TenantSite(
            tenant_id=tenant_id,
            slug=slug,
            site_kind=payload.site_kind,
            status="draft",
            display_name=display_name,
            tagline=payload.tagline,
            public_email=payload.public_email,
            public_phone=payload.public_phone,
            public_city=payload.public_city,
            public_state=payload.public_state,
            public_address_line1=payload.public_address_line1,
            public_postal_code=payload.public_postal_code,
            show_full_address=payload.show_full_address,
            idempotency_key=idempotency_key,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        return site


def build_snapshot(db: Session, site: TenantSite) -> dict:
    """Render the template_version set into a pages payload (§D).

    Returns a dict with 'pages' key containing landing/privacy/terms,
    plus the whitelisted public fields for the public response.
    """
    base_domain = settings.TENANT_SITES_BASE_DOMAIN
    site_url = f"https://{site.slug}.{base_domain}"

    # Build contact lines
    contact_lines: list[str] = []
    if site.public_phone:
        contact_lines.append(f"Phone: {site.public_phone}")
    if site.public_email:
        contact_lines.append(f"Email: {site.public_email}")
    contact_str = "\n".join(contact_lines) if contact_lines else ""

    # Common context for all pages
    ctx = {
        "display_name": site.display_name or "",
        "tagline": site.tagline or "",
        "public_email": site.public_email or "",
        "public_phone": site.public_phone or "",
        "public_city": site.public_city or "",
        "public_state": site.public_state or "",
        "contact_lines": contact_str,
        "site_url": site_url,
    }

    # Add address fields only when show_full_address
    if site.show_full_address:
        ctx["public_address_line1"] = site.public_address_line1 or ""
        ctx["public_postal_code"] = site.public_postal_code or ""
    else:
        ctx["public_address_line1"] = ""
        ctx["public_postal_code"] = ""

    version = site.template_version or "v1"

    # Render landing page
    landing_paragraphs = render_page_paragraphs("landing", version, ctx)
    # The first paragraph is the heading (display_name)
    landing_heading = landing_paragraphs[0] if landing_paragraphs else site.display_name
    landing_body = landing_paragraphs[1:] if len(landing_paragraphs) > 1 else []

    # Extract contact lines from the rendered landing (last section before links)
    # The template has "Contact" section — we pass contact_lines as a single block
    # For the public payload, we split the contact_lines into individual lines
    landing_contact_lines: list[str] = []
    for p in landing_body:
        if p.startswith("Phone:") or p.startswith("Email:"):
            landing_contact_lines.append(p)

    # Render privacy
    privacy_paragraphs = render_page_paragraphs("privacy", version, ctx)
    # First paragraph is "Privacy Policy" title
    privacy_title = privacy_paragraphs[0] if privacy_paragraphs else "Privacy Policy"
    privacy_body = privacy_paragraphs[1:] if len(privacy_paragraphs) > 1 else []

    # Render terms
    terms_paragraphs = render_page_paragraphs("terms", version, ctx)
    terms_title = terms_paragraphs[0] if terms_paragraphs else "Terms of Service"
    terms_body = terms_paragraphs[1:] if len(terms_paragraphs) > 1 else []

    snapshot: dict = {
        "slug": site.slug,
        "display_name": site.display_name,
        "tagline": site.tagline,
        "public_email": site.public_email,
        "public_phone": site.public_phone,
        "public_city": site.public_city,
        "public_state": site.public_state,
        "show_full_address": site.show_full_address,
        "template_version": version,
        "pages": {
            "landing": {
                "heading": landing_heading,
                "body_paragraphs": landing_body,
                "contact_lines": landing_contact_lines or None,
            },
            "privacy": {
                "title": privacy_title,
                "body_paragraphs": privacy_body,
            },
            "terms": {
                "title": terms_title,
                "body_paragraphs": terms_body,
            },
        },
    }

    # Include address fields only when show_full_address
    if site.show_full_address:
        snapshot["public_address_line1"] = site.public_address_line1
        snapshot["public_postal_code"] = site.public_postal_code

    return snapshot


def classify_website_action(db: Session, site: TenantSite) -> WebsiteAction:
    """Classify the website action and brand registration state.

    Reads the tenant's latest tenant_messaging_registration row (read-only).
    Buckets per §G-17:
    - no row / draft-family → none_or_draft
    - submitted/vetting/pending-family → in_flight
    - brand_rejected → brand_rejected
    - active/approved/campaign-live-family → live
    """
    registration = db.exec(
        select(TenantMessagingRegistration).where(
            TenantMessagingRegistration.tenant_id == site.tenant_id
        )
    ).first()

    if not registration:
        brand_status = "none"
        brand_guidance = "none_or_draft"
    elif registration.status in _BRAND_DRAFT_STATUSES:
        brand_status = registration.status
        brand_guidance = "none_or_draft"
    elif registration.status in _BRAND_IN_FLIGHT_STATUSES:
        brand_status = registration.status
        brand_guidance = "in_flight"
    elif registration.status in _BRAND_REJECTED_STATUSES:
        brand_status = registration.status
        brand_guidance = "brand_rejected"
    elif registration.status in _BRAND_LIVE_STATUSES:
        brand_status = registration.status
        brand_guidance = "live"
    else:
        # Unknown status — treat as draft (safe default)
        brand_status = registration.status
        brand_guidance = "none_or_draft"

    base_domain = settings.TENANT_SITES_BASE_DOMAIN
    new_url = f"https://{site.slug}.{base_domain}"

    # Read current profile website
    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == site.tenant_id)
    ).first()
    current_url = profile.website if profile else None

    # Determine action
    if not current_url:
        action = "set"
    elif _is_pilot_hosted_url(current_url, base_domain):
        action = "kept"
    else:
        action = "overwritten"  # requires confirmation at the route layer

    return WebsiteAction(
        action=action,
        brand_status=brand_status,
        brand_guidance=brand_guidance,
        current_url=current_url,
        new_url=new_url,
    )


def publish(
    db: Session,
    site: TenantSite,
    confirm_website_overwrite: bool = False,
) -> PublishResult:
    """Publish the site: build snapshot, set status, auto-populate website.

    Three-way website rule (§B.2/§G-16):
    1. profile website IS NULL → set to hosted URL, website_action='set'
    2. website_auto_populated=TRUE → silent refresh, website_action='kept'
    3. tenant-entered URL present:
       - confirm_website_overwrite=False → 409 website_overwrite_requires_confirmation
       - confirm_website_overwrite=True → overwrite, website_action='overwritten'

    Publish validation (§D-4):
    - Missing display_name, (public_phone OR public_email), public_city,
      public_state → 422 missing_required_fields
    """
    # Validate required fields
    missing: list[str] = []
    if not site.display_name:
        missing.append("display_name")
    if not site.public_phone and not site.public_email:
        missing.append("public_phone_or_email")
    if not site.public_city:
        missing.append("public_city")
    if not site.public_state:
        missing.append("public_state")

    if missing:
        raise TenantSiteError(
            code="missing_required_fields",
            title="Missing required fields for publishing",
            status=422,
            detail=(
                "The following fields are required to publish: " + ", ".join(missing)
            ),
            payload={"missing_fields": missing},
        )

    # Classify website action
    wa = classify_website_action(db, site)

    # Three-way website rule
    base_domain = settings.TENANT_SITES_BASE_DOMAIN
    hosted_url = f"https://{site.slug}.{base_domain}"

    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == site.tenant_id)
    ).first()

    website_action = "kept"  # default

    if profile and not profile.website:
        # Case 1: website IS NULL → set
        profile.website = hosted_url
        site.website_auto_populated = True
        website_action = "set"
        db.add(profile)
    elif site.website_auto_populated and profile and profile.website:
        # Case 2: we wrote it → silent refresh
        profile.website = hosted_url
        website_action = "kept"
        db.add(profile)
    elif (
        profile
        and profile.website
        and not _is_pilot_hosted_url(profile.website, base_domain)
    ):
        # Case 3: tenant-entered URL
        if not confirm_website_overwrite:
            raise TenantSiteError(
                code="website_overwrite_requires_confirmation",
                title="Website overwrite requires confirmation",
                status=409,
                detail=(
                    "Publishing will overwrite the tenant-entered website URL. "
                    "Call again with confirm_website_overwrite=true to proceed."
                ),
                payload={
                    "current_url": profile.website,
                    "new_url": hosted_url,
                    "brand_status": wa.brand_status,
                },
            )
        # Overwrite with confirmation
        profile.website = hosted_url
        site.website_auto_populated = True
        website_action = "overwritten"
        db.add(profile)

    # Build and store snapshot
    snapshot = build_snapshot(db, site)
    site.published_snapshot = snapshot
    site.status = "published"
    site.published_at = safe_now_utc()
    site.unpublished_at = None

    db.add(site)
    db.commit()
    db.refresh(site)

    return PublishResult(
        site=site,
        website_action=website_action,
        brand_status=wa.brand_status,
        brand_guidance=wa.brand_guidance,
    )


def on_profile_website_changed(
    db: Session, tenant_id: uuid.UUID, new_value: str | None
) -> None:
    """Reconciliation hook — called when the tenant edits website in the C-B9 profile.

    If the new value is non-empty and NOT a Pilot-hosted URL, flip
    website_auto_populated = FALSE on the tenant's site row if one exists (§G-18).
    """
    if not new_value:
        return

    base_domain = settings.TENANT_SITES_BASE_DOMAIN
    if _is_pilot_hosted_url(new_value, base_domain):
        return  # Still our URL — no reconciliation needed

    site = get_site(db, tenant_id)
    if site and site.website_auto_populated:
        site.website_auto_populated = False
        db.add(site)
        db.commit()


def unpublish(db: Session, site: TenantSite) -> TenantSite:
    """Unpublish the site. Does NOT clear website (§G-8).

    Returns the site with a warning string set (caller reads it).
    The warning escalates when the brand is live and points at our hosted URL.
    """
    if site.status != "published":
        raise TenantSiteError(
            code="not_published",
            title="Site is not published",
            status=409,
            detail="Cannot unpublish a site that is not currently published.",
        )

    site.status = "unpublished"
    site.unpublished_at = safe_now_utc()
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def get_unpublish_warning(db: Session, site: TenantSite) -> str:
    """Compute the warning string for an unpublish action (§G-8).

    Warning escalates when the brand is live and the current website
    points at our hosted URL.
    """
    wa = classify_website_action(db, site)
    base_domain = settings.TENANT_SITES_BASE_DOMAIN

    if (
        wa.brand_guidance == "live"
        and wa.current_url
        and _is_pilot_hosted_url(wa.current_url, base_domain)
    ):
        return (
            "Warning: Your 10DLC brand registration is currently live and "
            "references this hosted URL. Unpublishing may trigger carrier "
            "re-vetting. Your website URL will not be cleared."
        )
    return (
        "Your hosted compliance site has been unpublished. "
        "Your website URL has not been cleared to avoid disrupting "
        "any in-flight 10DLC registration."
    )


def get_published_snapshot(db: Session, slug: str) -> dict | None:
    """Public path — returns the published snapshot only when status='published'.

    Keyed by the globally-unique slug (not tenant-scoped).
    """
    site = db.exec(
        select(TenantSite)
        .where(TenantSite.slug == slug.strip().lower())
        .where(TenantSite.status == "published")
    ).first()

    if not site or not site.published_snapshot:
        return None

    return site.published_snapshot


def get_requirements_emailed_at(db: Session, tenant_id: uuid.UUID) -> datetime | None:
    """Read requirements_emailed_at from the tenant's 10DLC profile."""
    profile = db.exec(
        select(Tenant10DlcProfile).where(Tenant10DlcProfile.tenant_id == tenant_id)
    ).first()
    if not profile:
        return None
    return getattr(profile, "requirements_emailed_at", None)


def compute_site_url(site: TenantSite) -> str | None:
    """Compute the public site URL when published."""
    if site.status == "published":
        base_domain = settings.TENANT_SITES_BASE_DOMAIN
        return f"https://{site.slug}.{base_domain}"
    return None


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _is_pilot_hosted_url(url: str, base_domain: str) -> bool:
    """Check if a URL points at a Pilot-hosted tenant site."""
    if not url:
        return False
    return f".{base_domain}" in url


def _derive_suggestion(db: Session, base_slug: str) -> str:
    """Derive a suggested available slug from a taken base slug."""
    for i in range(2, 20):
        candidate = f"{base_slug}-{i}"
        # Check format
        if not SLUG_RE.match(candidate):
            continue
        if candidate in RESERVED_SLUGS:
            continue
        existing = db.exec(
            select(TenantSite).where(TenantSite.slug == candidate)
        ).first()
        if not existing:
            return candidate
    return f"{base_slug}-alt"


def render_kit_text(db: Session, tenant_id: uuid.UUID) -> str:
    """Render the Privacy/Terms kit text for the requirements email (§G-19).

    Uses the tenant's effective defaults to pre-merge the v1 templates.
    Single content path — same templates as the hosted site.
    """
    defaults = get_effective_defaults(db, tenant_id)
    contact_lines: list[str] = []
    if defaults.public_phone:
        contact_lines.append(f"Phone: {defaults.public_phone}")
    if defaults.public_email:
        contact_lines.append(f"Email: {defaults.public_email}")

    ctx = {
        "display_name": defaults.display_name or "Your Business",
        "tagline": "",
        "public_email": defaults.public_email or "",
        "public_phone": defaults.public_phone or "",
        "public_city": defaults.public_city or "",
        "public_state": defaults.public_state or "",
        "contact_lines": "\n".join(contact_lines),
        "site_url": "",
        "public_address_line1": "",
        "public_postal_code": "",
    }

    privacy_text = render_template("privacy", "v1", ctx)
    terms_text = render_template("terms", "v1", ctx)

    return f"{privacy_text}\n\n---\n\n{terms_text}"
