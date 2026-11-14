"""
B14/A75 — Tenant subscription routes.
GET  /api/v1/tenants/{tenant_id}/subscription
PUT  /api/v1/tenants/{tenant_id}/subscription/upgrade
(A76 extends this file with convert-from-trial and change-tier endpoints)
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from api.routes.subscription_tiers import SubscriptionTierResponse
from app.models.billing import Subscription, SubscriptionStatus
from app.models.core import Tenant
from app.models.subscription import (
    SubscriptionTier,
    TenantSubscriptionUsage,
    TenantTierOverride,
)
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ==================== SCHEMAS ====================


class UsageSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period_start: str | None
    period_end: str | None
    current_user_count: int
    current_sms_segment_count: int


class TierOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    override_tier_id: UUID | None
    override_trial_length_days: int | None
    override_reason: str | None


class PlanSummaryResponse(BaseModel):
    """PLP-FIX-5 (Issue 8): plan status surfaced from the subscription row.

    When no active subscription row exists (pre-conversion trial tenants),
    status_code/is_billing_active are derived from tenant.trial_ends_at
    (design §G.4): "trialing"/True when the trial is live, else None/False.
    """

    model_config = ConfigDict(from_attributes=True)

    status_code: str | None
    status_name: str | None
    is_billing_active: bool
    billing_interval: str | None
    renews_at: str | None
    free_period_ends_at: str | None


class PlanLimitsResponse(BaseModel):
    """PLP-FIX-5 (Issue 8): ppfv-resolved limits for the 3 metered features.

    Values come from check_entitlement per the MCP-verified product_feature
    codes (no users-limit feature exists). ``None`` = no quantity cap.
    """

    model_config = ConfigDict(from_attributes=True)

    outbound_sms_segments: int | None
    schedule_lanes: int | None
    voice_ai_minutes: int | None


class TenantSubscriptionResponse(BaseModel):
    current_tier: SubscriptionTierResponse
    trial_ends_at: str | None
    stripe_customer_id: str | None
    usage: UsageSummaryResponse | None
    tier_override: TierOverrideResponse | None
    plan_summary: PlanSummaryResponse
    charter_eligible: bool
    limits: PlanLimitsResponse


class SubscriptionUpgradeRequest(BaseModel):
    target_tier_id: UUID


class SubscriptionUpgradeResponse(BaseModel):
    redirect_to_stripe: bool
    message: str


class ConvertFromTrialRequest(BaseModel):
    target_tier_id: UUID
    payment_method_id: str
    billing_email: str
    billing_interval: Literal["monthly", "annual"] = "monthly"


class ConvertFromTrialResponse(BaseModel):
    psp_subscription_id: str
    status: str


class ChangeTierRequest(BaseModel):
    target_tier_id: UUID
    billing_interval: Literal["monthly", "annual"] = "monthly"


class ChangeTierResponse(BaseModel):
    status: str


class ResumeSubscriptionRequest(BaseModel):
    stripe_payment_method_id: str


class ResumeSubscriptionResponse(BaseModel):
    psp_subscription_id: str
    status: str
    billing_cycle_anchor: int | None = None


class UpgradeFromCharterRequest(BaseModel):
    billing_interval: Literal["monthly", "annual"]


class UpgradeFromCharterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    psp_subscription_id: str
    new_tier_name: str
    billing_interval: str
    charter_eligible_forfeited: bool


# ==================== SHARED LOGIC ====================


def _get_tenant_subscription_impl(
    tenant_id: UUID,
    db: Session,
) -> TenantSubscriptionResponse:
    """Return subscription state for a tenant."""
    from datetime import UTC, datetime

    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    # Resolve effective tier (operator override → tenant tier)
    override = db.exec(
        select(TenantTierOverride).where(TenantTierOverride.tenant_id == tenant_id)
    ).first()

    tier_id = (
        override.override_tier_id
        if (override and override.override_tier_id)
        else tenant.current_subscription_tier_id
    )
    tier = db.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_id == tier_id)
    ).first()

    if not tier:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription tier not found — data integrity error",
        )

    # Current period usage
    now = datetime.now(UTC)
    usage_row = db.exec(
        select(TenantSubscriptionUsage)
        .where(TenantSubscriptionUsage.tenant_id == tenant_id)
        .where(TenantSubscriptionUsage.period_end >= now)
        .order_by(TenantSubscriptionUsage.period_end)
        .limit(1)
    ).first()

    usage = None
    if usage_row:
        usage = UsageSummaryResponse(
            period_start=usage_row.period_start.isoformat()
            if usage_row.period_start
            else None,
            period_end=usage_row.period_end.isoformat()
            if usage_row.period_end
            else None,
            current_user_count=usage_row.current_user_count,
            current_sms_segment_count=usage_row.current_sms_segment_count,
        )

    tier_override = None
    if override:
        tier_override = TierOverrideResponse(
            override_tier_id=override.override_tier_id,
            override_trial_length_days=override.override_trial_length_days,
            override_reason=override.override_reason,
        )

    # PLP-FIX-5 (Issue 8): plan summary from the active subscription row
    sub_row = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)
    ).first()

    sub_status = (
        db.exec(
            select(SubscriptionStatus).where(SubscriptionStatus.id == sub_row.status_id)
        ).first()
        if sub_row
        else None
    )

    if sub_status is not None:
        status_code: str | None = sub_status.code
        status_name: str | None = sub_status.name
        is_billing_active = bool(sub_status.is_billing_active)
        billing_interval: str | None = sub_row.billing_interval if sub_row else None
        renews_at = (
            sub_row.renews_at.isoformat() if sub_row and sub_row.renews_at else None
        )
    elif tenant.trial_ends_at and tenant.trial_ends_at > now:
        # Design §G.4: pre-conversion trial tenants have no subscription row
        status_code, status_name, is_billing_active = "trialing", "Trialing", True
        billing_interval, renews_at = None, None
    else:
        status_code, status_name, is_billing_active = None, None, False
        billing_interval, renews_at = None, None

    plan_summary = PlanSummaryResponse(
        status_code=status_code,
        status_name=status_name,
        is_billing_active=is_billing_active,
        billing_interval=billing_interval,
        renews_at=renews_at,
        free_period_ends_at=tenant.free_period_ends_at.isoformat()
        if tenant.free_period_ends_at
        else None,
    )

    # Limits via the entitlement service (never a hand-written ppfv query)
    from services.entitlement_service import check_entitlement

    limits = PlanLimitsResponse(
        outbound_sms_segments=check_entitlement(
            tenant_id, "outbound_sms_segments", db
        ).limit,
        schedule_lanes=check_entitlement(tenant_id, "schedule_lanes", db).limit,
        voice_ai_minutes=check_entitlement(tenant_id, "voice_ai_minutes", db).limit,
    )

    return TenantSubscriptionResponse(
        current_tier=SubscriptionTierResponse.model_validate(tier),
        trial_ends_at=tenant.trial_ends_at.isoformat()
        if tenant.trial_ends_at
        else None,
        stripe_customer_id=tenant.stripe_customer_id,
        usage=usage,
        tier_override=tier_override,
        plan_summary=plan_summary,
        charter_eligible=tenant.charter_eligible,
        limits=limits,
    )


# ==================== TEST ENDPOINTS ====================


@router.get(
    "/{tenant_id}/subscription/test",
    response_model=TenantSubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
def get_tenant_subscription_test(tenant_id: UUID, db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Blocked in staging/production."""
    get_test_context()
    return _get_tenant_subscription_impl(tenant_id, db)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.get(
    "/{tenant_id}/subscription",
    response_model=TenantSubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
def get_tenant_subscription(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("subscription.view")),
):
    """Return tenant subscription state including tier, usage, and any operator override."""
    # Enforce tenant isolation
    if tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    return _get_tenant_subscription_impl(tenant_id, db)


def _select_stripe_price_id(
    tier: SubscriptionTier,
    billing_interval: str,
) -> str | None:
    """
    Select the correct Stripe price ID based on billing interval.
    Returns None if the required price ID is not yet configured (annual prices pending Tom).
    billing_interval must be 'monthly' or 'annual'.
    """
    if billing_interval == "annual":
        return (
            tier.stripe_price_id_annual
        )  # None until Tom creates annual prices in Stripe
    return tier.stripe_price_id_monthly


def _upgrade_tenant_subscription_impl(
    tenant_id: UUID,
    payload: SubscriptionUpgradeRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> SubscriptionUpgradeResponse:
    """Shared logic for upgrading tenant subscription tier."""
    if tenant_id != user_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    target_tier = db.exec(
        select(SubscriptionTier)
        .where(SubscriptionTier.tier_id == payload.target_tier_id)
        .where(SubscriptionTier.is_active == True)
    ).first()

    if not target_tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target subscription tier not found or inactive",
        )

    # Paid tier requires Stripe payment flow (A76 handles actual Stripe integration)
    # For TestUserContext: skip Stripe redirect — treat as direct update (trial/free tier assumed)
    if (
        not isinstance(user_context, TestUserContext)
        and not target_tier.is_trial
        and target_tier.stripe_price_id_monthly
    ):
        return SubscriptionUpgradeResponse(
            redirect_to_stripe=True,
            message="Payment required — complete via Stripe",
        )

    # Direct update (trial tier or operator-initiated no-charge upgrade)
    if isinstance(user_context, AuthenticatedUser):
        set_audit_context_sync(db, user_context.id)
    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    tenant.current_subscription_tier_id = target_tier.tier_id
    db.add(tenant)
    db.commit()

    return SubscriptionUpgradeResponse(
        redirect_to_stripe=False,
        message=f"Tier updated to {target_tier.display_label}",
    )


def _convert_from_trial_impl(
    tenant_id: UUID,
    payload: ConvertFromTrialRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ConvertFromTrialResponse:
    """Shared logic for converting a trial tenant to a paid subscription.
    For TestUserContext: bypasses Stripe API calls and returns mock response."""
    if tenant_id != user_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    target_tier = db.exec(
        select(SubscriptionTier)
        .where(SubscriptionTier.tier_id == payload.target_tier_id)
        .where(SubscriptionTier.is_active == True)
    ).first()

    if not target_tier or target_tier.is_trial:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target tier must be a paid tier",
        )

    selected_price_id = _select_stripe_price_id(target_tier, payload.billing_interval)
    if not selected_price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/billing-not-configured",
                "title": "Billing not configured",
                "status": 400,
                "detail": (
                    f"Tier '{target_tier.tier_name}' does not have a Stripe price configured "
                    f"for '{payload.billing_interval}' billing. "
                    "Use 'monthly' billing or contact support."
                ),
            },
        )

    # For TestUserContext: skip Stripe API calls entirely
    if isinstance(user_context, TestUserContext):
        return ConvertFromTrialResponse(
            psp_subscription_id="test_sub_mock_id",
            status="pending_webhook_confirmation",
        )

    from services.stripe_subscriptions import (
        create_stripe_customer,
        create_stripe_subscription,
    )

    stripe_customer_id = tenant.stripe_customer_id
    if not stripe_customer_id:
        stripe_customer_id = create_stripe_customer(
            db, tenant_id, payload.billing_email
        )

    stripe_subscription_id = create_stripe_subscription(
        db,
        tenant_id,
        stripe_customer_id,
        selected_price_id,
        payload.payment_method_id,
    )

    return ConvertFromTrialResponse(
        psp_subscription_id=stripe_subscription_id,
        status="pending_webhook_confirmation",
    )


def _change_tier_impl(
    tenant_id: UUID,
    payload: ChangeTierRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ChangeTierResponse:
    """Shared logic for changing an existing paid subscription tier.
    For TestUserContext: bypasses Stripe API calls and returns mock response."""
    if tenant_id != user_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    if not tenant.stripe_customer_id and not isinstance(user_context, TestUserContext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant does not have an active Stripe subscription",
        )

    current_subscription = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)
    ).first()

    if not current_subscription or not current_subscription.psp_subscription_id:
        if not isinstance(user_context, TestUserContext):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active subscription found",
            )

    target_tier = db.exec(
        select(SubscriptionTier)
        .where(SubscriptionTier.tier_id == payload.target_tier_id)
        .where(SubscriptionTier.is_active == True)
    ).first()

    if not target_tier or target_tier.is_trial:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target tier must be a paid tier",
        )

    selected_price_id = _select_stripe_price_id(target_tier, payload.billing_interval)
    if not selected_price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/billing-not-configured",
                "title": "Billing not configured",
                "status": 400,
                "detail": (
                    f"Tier '{target_tier.tier_name}' does not have a Stripe price configured "
                    f"for '{payload.billing_interval}' billing. "
                    "Use 'monthly' billing or contact support."
                ),
            },
        )

    # For TestUserContext: skip Stripe API calls entirely
    if isinstance(user_context, TestUserContext):
        return ChangeTierResponse(status="pending_webhook_confirmation")

    import stripe

    from core.config import settings

    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.Subscription.modify(
        current_subscription.psp_subscription_id,
        items=[{"price": selected_price_id}],
    )

    return ChangeTierResponse(status="pending_webhook_confirmation")


def _resume_subscription_impl(
    tenant_id: UUID,
    payload: ResumeSubscriptionRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ResumeSubscriptionResponse:
    """Shared logic for resuming a paused subscription.

    For TestUserContext: bypasses Stripe API calls and returns mock response.
    """
    if tenant_id != user_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Tenant not found",
                "status": 404,
                "detail": "Cannot resume subscription for another tenant.",
            },
        )

    if isinstance(user_context, TestUserContext):
        # Test mode — bypass Stripe
        return ResumeSubscriptionResponse(
            psp_subscription_id="test_sub_mock_id",
            status="active",
            billing_cycle_anchor=None,
        )

    if isinstance(user_context, AuthenticatedUser):
        set_audit_context_sync(db, user_id=user_context.id)

    from services.stripe_subscriptions import ResumeFailedError, resume_subscription

    try:
        result = resume_subscription(
            db=db,
            tenant_id=tenant_id,
            stripe_payment_method_id=payload.stripe_payment_method_id,
        )
    except ResumeFailedError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "type": "https://errors.pilotfortrades.com/stripe-resume-failed",
                "title": "Subscription resume failed",
                "status": 502,
                "detail": "Subscription remains paused after resume — "
                "payment method may have failed",
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://errors.pilotfortrades.com/invalid-request",
                "title": "Invalid request",
                "status": 400,
                "detail": str(e),
            },
        )

    return ResumeSubscriptionResponse(
        psp_subscription_id=result["psp_subscription_id"],
        status=result["status"],
        billing_cycle_anchor=result["billing_cycle_anchor"],
    )


def _upgrade_from_charter_impl(
    tenant_id: UUID,
    payload: UpgradeFromCharterRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> UpgradeFromCharterResponse:
    """Shared logic for upgrading a Charter member to Teams.

    For TestUserContext: bypasses Stripe API calls and returns mock response.
    """
    if tenant_id != user_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Tenant not found",
                "status": 404,
                "detail": "Cannot upgrade subscription for another tenant.",
            },
        )

    # For TestUserContext: skip Stripe API calls entirely
    if isinstance(user_context, TestUserContext):
        return UpgradeFromCharterResponse(
            psp_subscription_id="test_sub_mock_id",
            new_tier_name="teams",
            billing_interval=payload.billing_interval,
            charter_eligible_forfeited=True,
        )

    if isinstance(user_context, AuthenticatedUser):
        set_audit_context_sync(db, user_id=user_context.id)

    from services.stripe_subscriptions import upgrade_charter_to_teams

    try:
        result = upgrade_charter_to_teams(
            db=db,
            tenant_id=tenant_id,
            billing_interval=payload.billing_interval,
        )
    except ValueError as exc:
        msg = str(exc)
        # Determine status code from error message
        if "not a charter" in msg.lower() or "not on the charter tier" in msg.lower():
            code = status.HTTP_400_BAD_REQUEST
        elif "no active subscription" in msg.lower():
            code = status.HTTP_400_BAD_REQUEST
        elif "no payment method" in msg.lower():
            code = status.HTTP_400_BAD_REQUEST
        elif "not found" in msg.lower():
            code = status.HTTP_404_NOT_FOUND
        else:
            code = status.HTTP_502_BAD_GATEWAY

        raise HTTPException(
            status_code=code,
            detail={
                "type": "https://errors.pilotfortrades.com/charter-upgrade-error",
                "title": "Charter upgrade failed",
                "status": code,
                "detail": msg,
            },
        )

    return UpgradeFromCharterResponse(**result)


# ==================== TEST ENDPOINTS (register BEFORE authenticated) ====================


@router.put(
    "/{tenant_id}/subscription/upgrade/test",
    response_model=SubscriptionUpgradeResponse,
    status_code=status.HTTP_200_OK,
)
def upgrade_tenant_subscription_test(
    tenant_id: UUID,
    payload: SubscriptionUpgradeRequest,
    db: Session = Depends(get_db),
):
    """Upgrade tenant subscription tier (TEST ENDPOINT — no auth required)."""
    test_context = get_test_context()
    return _upgrade_tenant_subscription_impl(tenant_id, payload, db, test_context)


@router.post(
    "/{tenant_id}/subscription/convert-from-trial/test",
    response_model=ConvertFromTrialResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def convert_from_trial_test(
    tenant_id: UUID,
    payload: ConvertFromTrialRequest,
    db: Session = Depends(get_db),
):
    """Convert trial to paid subscription (TEST ENDPOINT — no auth; Stripe bypassed)."""
    test_context = get_test_context()
    return _convert_from_trial_impl(tenant_id, payload, db, test_context)


@router.post(
    "/{tenant_id}/subscription/change-tier/test",
    response_model=ChangeTierResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def change_tier_test(
    tenant_id: UUID,
    payload: ChangeTierRequest,
    db: Session = Depends(get_db),
):
    """Change subscription tier (TEST ENDPOINT — no auth; Stripe bypassed)."""
    test_context = get_test_context()
    return _change_tier_impl(tenant_id, payload, db, test_context)


@router.post(
    "/{tenant_id}/subscription/resume/test",
    response_model=ResumeSubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
def resume_subscription_test(
    tenant_id: UUID,
    payload: ResumeSubscriptionRequest,
    db: Session = Depends(get_db),
):
    """Resume paused subscription (TEST ENDPOINT — no auth; Stripe bypassed)."""
    test_context = get_test_context()
    return _resume_subscription_impl(tenant_id, payload, db, test_context)


@router.post(
    "/{tenant_id}/subscription/upgrade-from-charter/test",
    response_model=UpgradeFromCharterResponse,
    status_code=status.HTTP_200_OK,
)
def upgrade_from_charter_test(
    tenant_id: UUID,
    payload: UpgradeFromCharterRequest,
    db: Session = Depends(get_db),
):
    """Upgrade Charter to Teams (TEST ENDPOINT — no auth; Stripe bypassed)."""
    test_context = get_test_context()
    return _upgrade_from_charter_impl(tenant_id, payload, db, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.put(
    "/{tenant_id}/subscription/upgrade",
    response_model=SubscriptionUpgradeResponse,
    status_code=status.HTTP_200_OK,
)
def upgrade_tenant_subscription(
    tenant_id: UUID,
    payload: SubscriptionUpgradeRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("subscription.tier.change")
    ),
):
    """Upgrade tenant subscription tier. RBAC: subscription.tier.change."""
    return _upgrade_tenant_subscription_impl(tenant_id, payload, db, current_user)


@router.post(
    "/{tenant_id}/subscription/convert-from-trial",
    response_model=ConvertFromTrialResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def convert_from_trial(
    tenant_id: UUID,
    payload: ConvertFromTrialRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("subscription.tier.change")
    ),
):
    """Convert trial to paid subscription. Initiates Stripe subscription creation. RBAC: subscription.tier.change."""
    return _convert_from_trial_impl(tenant_id, payload, db, current_user)


@router.post(
    "/{tenant_id}/subscription/change-tier",
    response_model=ChangeTierResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def change_tier(
    tenant_id: UUID,
    payload: ChangeTierRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("subscription.tier.change")
    ),
):
    """Change existing paid subscription tier. Modifies Stripe subscription. RBAC: subscription.tier.change."""
    return _change_tier_impl(tenant_id, payload, db, current_user)


@router.post(
    "/{tenant_id}/subscription/resume",
    response_model=ResumeSubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
def resume_subscription(
    tenant_id: UUID,
    payload: ResumeSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("subscription.tier.change")
    ),
):
    """Resume a paused subscription after payment method addition.

    RBAC: subscription.tier.change.
    """
    return _resume_subscription_impl(tenant_id, payload, db, current_user)


@router.post(
    "/{tenant_id}/subscription/upgrade-from-charter",
    response_model=UpgradeFromCharterResponse,
    status_code=status.HTTP_200_OK,
)
def upgrade_from_charter(
    tenant_id: UUID,
    payload: UpgradeFromCharterRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("subscription.tier.change")
    ),
):
    """Upgrade a Charter member to the Teams plan. PERMANENT — forfeits the Charter rate.

    Deletes the Charter monthly item, adds the Teams item (monthly or annual),
    ends the trial if active, and permanently sets charter_eligible=false.

    RBAC: subscription.tier.change.
    """
    return _upgrade_from_charter_impl(tenant_id, payload, db, current_user)
