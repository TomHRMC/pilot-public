"""
C-B5 — Step 5 confirmation: requires_payment_method conditional branching.
Domain: identity_access (PRD §3.5)

Covers:
  - Charter tier (requires_payment_method=false) skips activate_trial()
  - Non-Charter tier (requires_payment_method=true) still calls activate_trial()
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


def _make_tier(db_session, *, tier_name, requires_payment_method) -> SubscriptionTier:
    tier = SubscriptionTier(
        tier_id=uuid.uuid4(),
        tier_name=tier_name,
        display_label=f"C-B5 Step5 {tier_name} {uuid.uuid4().hex[:8]}",
        annual_price_cents=58800,
        monthly_price_cents=4900,
        is_trial=False,
        is_active=True,
        display_order=99,
        free_period_days=90 if not requires_payment_method else None,
        requires_payment_method=requires_payment_method,
        signup_cap=12 if not requires_payment_method else None,
        price_locked=not requires_payment_method,
    )
    db_session.add(tier)
    db_session.flush()
    return tier


def _make_tenant_and_signup(
    db_session, *, tier_id, state="step4_tier"
) -> tuple[Tenant, TenantSignup]:
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"C-B5 Step5 Test {uuid.uuid4().hex[:8]}",
        is_active=True,
        current_subscription_tier_id=tier_id,
    )
    db_session.add(tenant)
    db_session.flush()

    signup = TenantSignup(
        tenant_id=tenant.id,
        # ALPHA-FIX-1: set to step4_tier so destination is step5_confirm (which
        # processes confirm data). Under the old origin-keyed dispatch this set
        # step5_confirm and passed "step5_confirm" — which under the new contract
        # would dispatch to complete (wrong branch).
        signup_state=state,
        signup_started_at=datetime.now(UTC),
        business_name="Acme Electric",
        trade="electrical",
        business_size="1-5",
        zip="12345",
        time_zone="America/New_York",
        owner_email=f"step5-{uuid.uuid4()}@example.com",
        owner_first_name="Mike",
        owner_last_name="Johnson",
    )
    db_session.add(signup)
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(signup)
    return tenant, signup


class TestStep5Conditional:
    """Step 5 — requires_payment_method branching."""

    def test_charter_skips_activate_trial(self, db_session):
        """Charter tier (requires_payment_method=false) does NOT call activate_trial."""
        tier = _make_tier(
            db_session, tier_name="charter", requires_payment_method=False
        )
        tenant, _signup = _make_tenant_and_signup(db_session, tier_id=tier.tier_id)
        user_id = uuid.uuid4()

        with patch("services.trial_management.activate_trial") as mock_trial:
            result = advance_wizard_step(
                db_session,
                tenant.id,
                "step4_tier",
                {"confirmed": True, "user_id": str(user_id)},
            )

        assert result["signup_state"] == "complete"
        mock_trial.assert_not_called()

    def test_non_charter_calls_activate_trial(self, db_session):
        """Non-Charter tier (requires_payment_method=true) calls activate_trial."""
        tier = _make_tier(db_session, tier_name="starter", requires_payment_method=True)
        tenant, _signup = _make_tenant_and_signup(db_session, tier_id=tier.tier_id)
        user_id = uuid.uuid4()

        with patch("services.trial_management.activate_trial") as mock_trial:
            result = advance_wizard_step(
                db_session,
                tenant.id,
                "step4_tier",
                {"confirmed": True, "user_id": str(user_id)},
            )

        assert result["signup_state"] == "complete"
        mock_trial.assert_called_once()
        call_args = mock_trial.call_args
        assert call_args.args[1] == tenant.id  # tenant_id
        # user_id is passed as a string from step_data
        assert str(call_args.args[2]) == str(user_id)
