"""
C-B5 — Step 4 tier selection: cohort cap + charter_member_number assignment.
Domain: identity_access (PRD §3.5)

Covers:
  - Charter tier selection assigns charter_member_number (1, 2, ...)
  - free_period_ends_at computed from tier.free_period_days
  - signup_cap flips tier.is_active to false when cap reached
  - Idempotent on re-submit (no duplicate number)

Stripe calls are mocked — no real Stripe API calls.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.models.core import Tenant
from app.models.signup import TenantSignup
from app.models.subscription import SubscriptionTier
from services.tenant_signup import advance_wizard_step

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


def _make_charter_tier(
    db_session, *, signup_cap=12, is_active=True
) -> SubscriptionTier:
    """Insert a fresh Charter-like tier row for this test (ID-scoped)."""
    tier = SubscriptionTier(
        tier_id=uuid.uuid4(),
        tier_name="charter",
        display_label=f"Charter Test {uuid.uuid4().hex[:8]}",
        annual_price_cents=58800,
        monthly_price_cents=4900,
        is_trial=False,
        is_active=is_active,
        display_order=99,
        free_period_days=90,
        requires_payment_method=False,
        signup_cap=signup_cap,
        price_locked=True,
    )
    db_session.add(tier)
    db_session.flush()
    return tier


def _make_tenant_and_signup(
    db_session, *, state="step3_phone"
) -> tuple[Tenant, TenantSignup]:
    """Insert a tenant + tenant_signup at step3_phone (ready for step4 advance).

    ALPHA-FIX-1: set to step3_phone so destination is step4_tier (which
    processes tier data). Under the old origin-keyed dispatch this set
    step4_tier and passed "step4_tier" — which under the new contract
    would dispatch to step5_confirm (wrong branch).
    """
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"C-B5 Cohort Test {uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(tenant)
    db_session.flush()

    signup = TenantSignup(
        tenant_id=tenant.id,
        signup_state=state,
        signup_started_at=datetime.now(UTC),
        business_name="Acme Electric",
        trade="electrical",
        business_size="1-5",
        zip="12345",
        time_zone="America/New_York",
        owner_email=f"cohort-{uuid.uuid4()}@example.com",
        owner_first_name="Mike",
        owner_last_name="Johnson",
    )
    db_session.add(signup)
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(signup)
    return tenant, signup


class TestStep4CohortCap:
    """Step 4 tier selection — charter_member_number + free_period_ends_at + cap."""

    def test_charter_selection_assigns_member_number_and_free_period(self, db_session):
        """Charter tier selection assigns charter_member_number and free_period_ends_at."""
        tier = _make_charter_tier(db_session)
        tenant, _signup = _make_tenant_and_signup(db_session)

        with (
            patch("services.stripe_subscriptions.create_stripe_customer") as mock_cust,
            patch(
                "services.stripe_subscriptions.create_charter_subscription"
            ) as mock_sub,
        ):
            mock_cust.return_value = "cus_test_123"
            mock_sub.return_value = "sub_test_456"

            result = advance_wizard_step(
                db_session,
                tenant.id,
                "step3_phone",
                {"selected_tier_id": str(tier.tier_id)},
            )

        assert result["signup_state"] == "step4_tier"

        db_session.refresh(tenant)
        assert tenant.charter_member_number is not None
        assert tenant.charter_member_number >= 1
        assert tenant.free_period_ends_at is not None
        assert tenant.current_subscription_tier_id == tier.tier_id

    def test_signup_cap_flips_is_active_false(self, db_session):
        """When charter_member_number >= signup_cap, tier.is_active flips to false."""
        # Use a cap of 1 so the very first assignment triggers the flip.
        tier = _make_charter_tier(db_session, signup_cap=1)
        tenant, _signup = _make_tenant_and_signup(db_session)

        with (
            patch("services.stripe_subscriptions.create_stripe_customer") as mock_cust,
            patch(
                "services.stripe_subscriptions.create_charter_subscription"
            ) as mock_sub,
        ):
            mock_cust.return_value = "cus_test_cap"
            mock_sub.return_value = "sub_test_cap"

            advance_wizard_step(
                db_session,
                tenant.id,
                "step3_phone",
                {"selected_tier_id": str(tier.tier_id)},
            )

        db_session.refresh(tier)
        assert tier.is_active is False

    def test_idempotent_no_duplicate_number_on_resubmit(self, db_session):
        """Re-submitting step 4 does not assign a second charter_member_number."""
        tier = _make_charter_tier(db_session)
        tenant, signup = _make_tenant_and_signup(db_session)

        with (
            patch("services.stripe_subscriptions.create_stripe_customer") as mock_cust,
            patch(
                "services.stripe_subscriptions.create_charter_subscription"
            ) as mock_sub,
        ):
            mock_cust.return_value = "cus_test_idem"
            mock_sub.return_value = "sub_test_idem"

            advance_wizard_step(
                db_session,
                tenant.id,
                "step3_phone",
                {"selected_tier_id": str(tier.tier_id)},
            )

        db_session.refresh(tenant)
        first_number = tenant.charter_member_number
        assert first_number is not None

        # Manually reset state back to step3_phone to simulate a re-submit
        # (the wizard staleness guard requires the DB state to match).
        signup.signup_state = "step3_phone"
        db_session.add(signup)
        db_session.commit()

        with (
            patch("services.stripe_subscriptions.create_stripe_customer") as mock_cust2,
            patch(
                "services.stripe_subscriptions.create_charter_subscription"
            ) as mock_sub2,
        ):
            mock_cust2.return_value = "cus_test_idem2"
            mock_sub2.return_value = "sub_test_idem2"

            advance_wizard_step(
                db_session,
                tenant.id,
                "step3_phone",
                {"selected_tier_id": str(tier.tier_id)},
            )

        db_session.refresh(tenant)
        # Number unchanged — idempotent
        assert tenant.charter_member_number == first_number

    def test_inactive_tier_returns_409_tier_closed(self, db_session):
        """Selecting a tier with is_active=false returns 409 tier-closed."""
        tier = _make_charter_tier(db_session, is_active=False)
        tenant, _signup = _make_tenant_and_signup(db_session)

        with pytest.raises(Exception) as exc_info:
            advance_wizard_step(
                db_session,
                tenant.id,
                "step3_phone",
                {"selected_tier_id": str(tier.tier_id)},
            )

        # FastAPI HTTPException wraps in Starlette HTTPException
        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert detail["type"] == "https://pilotfortrades.com/errors/tier-closed"
        assert detail["status"] == 409
