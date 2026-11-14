"""C-B11 — Cohort dashboard Pydantic schemas (request/response models).

Separate from the SQLModel ORM classes in app/models/.  These schemas define
the API contract consumed by the React frontend (Part B).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CohortMemberResponse(BaseModel):
    """A single Charter member row in the cohort dashboard."""

    model_config = ConfigDict(from_attributes=True)
    tenant_id: UUID
    business_name: str
    charter_member_number: int | None
    free_period_ends_at: datetime | None
    days_remaining: int | None
    stripe_status: str
    has_payment_method: bool
    messaging_status: str
    customer_count: int
    invoice_count: int
    days_since_last_job: int | None
    last_contact: datetime | None
    alert_level: str  # "red" | "amber" | "none"


class CohortOverviewResponse(BaseModel):
    """Top-level cohort overview — tier metadata + member list."""

    model_config = ConfigDict(from_attributes=True)
    cohort_tier_name: str
    cohort_is_active: bool
    signup_cap: int
    members: list[CohortMemberResponse]


class ExtendFreePeriodRequest(BaseModel):
    """Request body for POST /operator/cohort/{tenant_id}/extend."""

    new_free_period_ends_at: datetime
    override_reason: str


class ExtendFreePeriodResponse(BaseModel):
    """Response for the silent free-period extension action."""

    model_config = ConfigDict(from_attributes=True)
    tenant_id: UUID
    previous_free_period_ends_at: datetime | None
    new_free_period_ends_at: datetime
    stripe_subscription_id: str
    stripe_trial_end_updated: bool


class CloseCohortResponse(BaseModel):
    """Response for the cohort close action."""

    model_config = ConfigDict(from_attributes=True)
    charter_price_archived: bool
    charter_tier_deactivated: bool
    activated_tiers: list[str]


class AuthMeResponse(BaseModel):
    """Response for GET /api/v1/auth/me — login routing discriminator.

    Returns user_type ("platform" | "tenant") and redirect_to so the frontend
    can route after Cognito authentication without a second API call.
    """

    model_config = ConfigDict(from_attributes=True)
    user_type: str  # "platform" | "tenant"
    user_id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    # Platform user fields (null for tenant users)
    platform_role_code: str | None = None
    # Tenant user fields (null for platform users)
    tenant_id: UUID | None = None
    role_code: str | None = None
    # Redirect target
    redirect_to: str
