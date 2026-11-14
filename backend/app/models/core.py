import uuid
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import StandardAuditMixin


# --- Models ---
class PlatformRole(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "platform_role"

    code: str = Field(primary_key=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    permissions: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class User(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_email"),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="user_email_format_chk",
        ),
        CheckConstraint(
            "platform_role_code IS NULL OR platform_role_code IN ('staff', 'superadmin')",
            name="user_platform_role_chk",
        ),
        CheckConstraint(
            "platform_role_code IS NULL OR "
            "(platform_role_code IN ('staff', 'superadmin') AND mfa_enforced = true)",
            name="user_platform_mfa_required_chk",
        ),
        CheckConstraint(
            "preferred_mfa_channel IS NULL OR preferred_mfa_channel IN ('email', 'sms', 'totp')",
            name="user_preferred_mfa_channel_chk",
        ),
        # FIND-066 (B18): MVP language lock — Phase 2 will expand ('fr', 'es')
        CheckConstraint(
            "language_preference IS NULL OR language_preference IN ('en')",
            name="user_language_preference_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Using CITEXT for case-insensitive email uniqueness and lookups
    email: str = Field(
        sa_column=Column(CITEXT, nullable=False, unique=True, index=True)
    )
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)

    is_platform_user: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    platform_role_code: str | None = Field(
        default=None, foreign_key="platform_role.code", index=True
    )

    password_hash: str | None = Field(default=None)
    email_verified_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    failed_login_count: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    locked_until: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    password_updated_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    require_password_reset: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    mfa_enforced: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    preferred_mfa_channel: str = Field(
        default="email",
        sa_column=Column(String, server_default=text("'email'"), nullable=False),
    )
    totp_secret: str | None = Field(default=None)

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    last_login_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # B3/A18: Dispatch board avatar color — hex string e.g. "#3B43D6". NULL until auto-assigned.
    display_color: str | None = Field(
        default=None,
        sa_column=Column(String(7), nullable=True),
    )

    # FIND-066 (B18): User profile columns — all nullable; code wiring in B20
    phone_number: str | None = Field(default=None)
    time_zone: str | None = Field(
        default=None,
        sa_column=Column(
            String, nullable=True, server_default=text("'America/New_York'")
        ),
    )
    profile_photo_s3_key: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    language_preference: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True, server_default=text("'en'")),
    )

    # Phase 6.0.1: Override audit fields with FK constraints (self-referential)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class UserPreference(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "user_preference"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_preference_user_tenant"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )

    preferences: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class Tenant(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "tenant"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, nullable=False)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # B14/A75: Subscription tier columns
    current_subscription_tier_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("subscription_tier.tier_id", ondelete="RESTRICT"),
            nullable=True,  # nullable in ORM; migration backfills and locks NOT NULL in DB
        ),
    )
    trial_started_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    trial_ends_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    trial_length_days_override: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    stripe_customer_id: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )

    # UI-FIX-2F: Stripe Connect account ID for invoice payment routing
    # NULL = not connected (manual payment fallback)
    # Set via POST /api/v1/settings/billing/stripe-connect/onboard
    stripe_connect_account_id: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    # STRIPE-CONNECT-1: Local capability persistence (write-through from
    # account.updated webhook + GET /status refresh). Lets the public invoice
    # hot path render card_payments_enabled / payment_unavailable_reason
    # without a live Stripe call. NULL = unknown (treat as not-connected).
    # The 402 guard on the payment POST remains the hard backstop.
    stripe_connect_charges_enabled: bool | None = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )
    stripe_connect_payouts_enabled: bool | None = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )

    # STRIPE-CONNECT-1-B2: Contractor-entered billing contact shown to customers
    # on the public invoice manual-payment panel (null = not entered — the
    # frontend renders a fallback line). No owner-user personal fallback (§G Q9).
    billing_contact_phone: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    billing_contact_email: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    # FIND-086: MFA grace period start timestamp (added by migration a7c3e5f91b02)
    mfa_grace_period_started_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # C-B2: Charter program lifecycle fields
    # Note: free_period_ends_at is distinct from trial_ends_at above.
    # trial_ends_at tracks the 14-day Trial tier period; free_period_ends_at
    # tracks the 90-day Charter free period. A tenant is on one or the other.
    free_period_ends_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )  # App source of truth for free period end. Stripe trial_end mirrors this.
    charter_member_number: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )  # 1..12, NULL for non-Charter tenants. Partial unique index in DB.
    charter_eligible: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )  # Flips false permanently on cancellation or Teams upgrade.

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# B14/A75: Auto-assign trial tier when creating a Tenant without current_subscription_tier_id.
# This ensures all tests that create bare Tenant() objects don't need to be individually updated.
@event.listens_for(Tenant, "before_insert")
def _assign_default_subscription_tier(mapper, connection, target):  # type: ignore[override]
    """
    If a Tenant is being inserted without current_subscription_tier_id,
    auto-query and assign the trial tier.
    """
    if target.current_subscription_tier_id is not None:
        return
    # Query the trial tier directly via the connection (not ORM session)
    result = connection.execute(
        __import__("sqlalchemy").text(
            "SELECT tier_id FROM subscription_tier WHERE is_trial = true LIMIT 1"
        )
    )
    row = result.fetchone()
    if row:
        target.current_subscription_tier_id = row[0]


class UserEndpoint(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "user_endpoint"
    __table_args__ = (
        CheckConstraint(
            "channel != 'email' OR value ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="user_endpoint_email_format_chk",
        ),
        CheckConstraint(
            "channel IN ('email', 'sms')",
            name="user_endpoint_channel_chk",
        ),
        CheckConstraint(
            "verification_status IN ('pending', 'verified', 'failed')",
            name="user_endpoint_verification_status_chk",
        ),
        CheckConstraint(
            "consent_status IN ('unknown', 'opted_in', 'opted_out')",
            name="user_endpoint_consent_status_chk",
        ),
        # FIND-067 (B18): idx_user_endpoint_primary_email and
        # idx_user_endpoint_email_value_lower were dropped — they are exact
        # duplicates of ux_user_email_primary and ux_global_primary_email
        # respectively. Canonical indexes retained; duplicates removed.
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    channel: str = Field(nullable=False)  # 'email' | 'sms'
    value: str = Field(nullable=False)

    is_primary: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    verification_status: str = Field(
        default="pending",
        sa_column=Column(String, server_default=text("'pending'"), nullable=False),
    )
    verified_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    consent_status: str = Field(
        default="unknown",
        sa_column=Column(String, server_default=text("'unknown'"), nullable=False),
    )
    consent_updated_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Safely renamed from metadata
    contextdata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# B15/A82 — Tenant Email Branding
# ─────────────────────────────────────────────────────────────────────────────


class TenantEmailBranding(StandardAuditMixin, SQLModel, table=True):
    """
    One mutable tenant configuration record per tenant for email branding.
    PK is tenant_id (one row per tenant, no UUID id column).

    Mixin: StandardAuditMixin — full audit trail needed to track who last updated branding.
    """

    __tablename__ = "tenant_email_branding"

    tenant_id: uuid.UUID = Field(
        primary_key=True,
        foreign_key="tenant.id",
    )

    logo_s3_path: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    brand_color_hex: str | None = Field(
        default=None,
        sa_column=Column(
            String(7), nullable=True
        ),  # e.g. "#5B3FF0"; null = Pilot brand-indigo
    )
    email_signature: str | None = Field(
        default=None,
        sa_column=Column(
            String, nullable=True
        ),  # 500 char max enforced application-side
    )
    custom_footer: str | None = Field(
        default=None,
        sa_column=Column(
            String, nullable=True
        ),  # 200 char max enforced application-side
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# DLC-1 — Tenant 10DLC Business Profile
# ─────────────────────────────────────────────────────────────────────────────


class Tenant10DlcProfile(StandardAuditMixin, SQLModel, table=True):
    """
    10DLC business registration data for a tenant.
    Required to provision Telnyx sub-brand per tenant for SMS campaign registration.
    Single row per tenant (PK = tenant_id). DLC-1.
    """

    __tablename__ = "tenant_10dlc_profile"

    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            primary_key=True,
            nullable=False,
        ),
    )
    legal_business_name: str = Field(sa_column=Column(Text, nullable=False))
    dba_name: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    ein: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hq_address_line1: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    hq_address_line2: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    hq_city: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hq_state: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    hq_postal_code: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    hq_country: str = Field(
        default="US",
        sa_column=Column(Text, server_default=text("'US'"), nullable=False),
    )
    support_email: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    support_phone: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    # C-B9: Brand registration fields needed for Telnyx API submission.
    # website is required at the app layer (not DB) — may be auto-populated
    # from C-SPIKE-2's compliance page in the future.
    website: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    stock_symbol: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    vertical: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # C-B16: One-time requirements email guard (§G-19). Nullable — NULL means
    # the email has not been sent yet. Stamped on successful enqueue.
    requirements_emailed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # StandardAuditMixin provides created_at, updated_at; override FK audit fields:
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class EntityType(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "entity_type"

    code: str = Field(primary_key=True)
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
