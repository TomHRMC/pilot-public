"""C-B16 Pydantic schemas for tenant-site endpoints.

Request/response shapes — separate from the SQLModel ORM layer (app/models/tenant_site.py).
All v2 idioms: ConfigDict, field_validator, model_dump.
"""

import uuid

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator

# ─── Request schemas ──────────────────────────────────────────────────────────


class TenantSiteUpsertRequest(BaseModel):
    """PUT /api/v1/tenant-site — upsert draft configuration."""

    site_kind: str
    slug: str
    display_name: str | None = None
    tagline: str | None = None
    public_email: str | None = None
    public_phone: str | None = None
    public_city: str | None = None
    public_state: str | None = None
    public_address_line1: str | None = None
    public_postal_code: str | None = None
    show_full_address: bool = False

    @field_validator("site_kind")
    @classmethod
    def site_kind_valid(cls, v: str) -> str:
        if v not in ("compliance_kit", "hosted_compliance"):
            raise ValueError(
                "site_kind must be 'compliance_kit' or 'hosted_compliance'"
            )
        return v

    @field_validator("slug")
    @classmethod
    def slug_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("slug cannot be blank")
        return v.strip().lower()


class PublishRequest(BaseModel):
    """POST /api/v1/tenant-site/publish — publish the current draft."""

    confirm_website_overwrite: bool = False


# ─── Defaults schema (§16.5 effective defaults from profile) ──────────────────


class TenantSiteDefaults(BaseModel):
    """Effective defaults merged from tenant_10dlc_profile for form pre-fill.

    Each field carries a ``source`` indicator: 'tenant_override' when the
    tenant has entered a value in their profile, 'system_default' when falling
    back to a platform default, or None when no value is available.
    """

    display_name: str | None = None
    display_name_source: str | None = None
    public_email: str | None = None
    public_email_source: str | None = None
    public_phone: str | None = None
    public_phone_source: str | None = None
    public_city: str | None = None
    public_city_source: str | None = None
    public_state: str | None = None
    public_state_source: str | None = None


# ─── Response schemas ─────────────────────────────────────────────────────────


class TenantSiteResponse(BaseModel):
    """Full site configuration + computed fields."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    slug: str
    site_kind: str
    status: str
    display_name: str
    tagline: str | None = None
    public_email: str | None = None
    public_phone: str | None = None
    public_city: str | None = None
    public_state: str | None = None
    public_address_line1: str | None = None
    public_postal_code: str | None = None
    show_full_address: bool = False
    template_version: str = "v1"
    published_at: AwareDatetime | None = None
    unpublished_at: AwareDatetime | None = None
    kit_sent_at: AwareDatetime | None = None
    website_auto_populated: bool = False
    idempotency_key: str | None = None
    # Computed: https://{slug}.{TENANT_SITES_BASE_DOMAIN} when published
    site_url: str | None = None
    # Read from the profile row (nullable — UI renders "Guide emailed on {date}")
    requirements_emailed_at: AwareDatetime | None = None
    # Effective defaults for form pre-fill
    defaults: TenantSiteDefaults | None = None


class TenantSiteGetResponse(BaseModel):
    """GET /api/v1/tenant-site — never 404 when no row (§D-1)."""

    configured: bool
    site: TenantSiteResponse | None = None
    defaults: TenantSiteDefaults


class SlugAvailabilityResponse(BaseModel):
    """GET /api/v1/tenant-site/slug-availability?slug=…"""

    available: bool
    reason: str | None = None  # 'taken' | 'invalid' | 'reserved'
    suggestion: str | None = None


class PublishResponse(BaseModel):
    """POST /api/v1/tenant-site/publish — site payload + website/brand context."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    slug: str
    site_kind: str
    status: str
    display_name: str
    tagline: str | None = None
    public_email: str | None = None
    public_phone: str | None = None
    public_city: str | None = None
    public_state: str | None = None
    public_address_line1: str | None = None
    public_postal_code: str | None = None
    show_full_address: bool = False
    template_version: str = "v1"
    published_at: AwareDatetime | None = None
    unpublished_at: AwareDatetime | None = None
    kit_sent_at: AwareDatetime | None = None
    website_auto_populated: bool = False
    site_url: str | None = None
    requirements_emailed_at: AwareDatetime | None = None
    # Three-way website action result
    website_action: str  # 'set' | 'kept' | 'overwritten'
    # Brand registration state for UI sequencing (§G-17)
    brand_status: str  # raw tenant_messaging_registration.status, or "none"
    brand_guidance: str  # 'none_or_draft' | 'in_flight' | 'brand_rejected' | 'live'


class UnpublishResponse(BaseModel):
    """POST /api/v1/tenant-site/unpublish — site payload + warning (§G-8)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    slug: str
    site_kind: str
    status: str
    display_name: str
    tagline: str | None = None
    public_email: str | None = None
    public_phone: str | None = None
    public_city: str | None = None
    public_state: str | None = None
    public_address_line1: str | None = None
    public_postal_code: str | None = None
    show_full_address: bool = False
    template_version: str = "v1"
    published_at: AwareDatetime | None = None
    unpublished_at: AwareDatetime | None = None
    kit_sent_at: AwareDatetime | None = None
    website_auto_populated: bool = False
    site_url: str | None = None
    requirements_emailed_at: AwareDatetime | None = None
    warning: str


# ─── Public response (whitelisted only — §D-7) ────────────────────────────────


class PublicTenantSitePage(BaseModel):
    """A single rendered page in the published snapshot."""

    heading: str | None = None  # landing only
    title: str | None = None  # privacy/terms
    body_paragraphs: list[str] = []
    contact_lines: list[str] | None = None  # landing only


class PublicTenantSiteResponse(BaseModel):
    """GET /api/v1/public/tenant-sites/{slug} — whitelisted published snapshot.

    This response_model IS the public payload whitelist — the route never
    returns the ORM row. Address fields present only when show_full_address=TRUE.
    """

    slug: str
    display_name: str
    tagline: str | None = None
    public_email: str | None = None
    public_phone: str | None = None
    public_city: str | None = None
    public_state: str | None = None
    public_address_line1: str | None = None
    public_postal_code: str | None = None
    template_version: str = "v1"
    published_at: AwareDatetime | None = None
    pages: dict[str, PublicTenantSitePage] = {}
