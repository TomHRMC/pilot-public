"""
C-B5 — get_signup_state() returns Charter lifecycle fields.
Domain: identity_access (PRD §3.5)

Covers:
  - free_period_ends_at returned in collected_data
  - requires_payment_method returned in collected_data
  - charter_member_number returned in collected_data
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.core import Tenant
from app.models.signup import TenantSignup
from app.models.subscription import SubscriptionTier
from services.tenant_signup import get_signup_state

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


def _make_tier(db_session, *, requires_payment_method) -> SubscriptionTier:
    tier = SubscriptionTier(
        tier_id=uuid.uuid4(),
        tier_name="charter" if not requires_payment_method else "starter",
        display_label=f"C-B5 State Test {uuid.uuid4().hex[:8]}",
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
    db_session, *, tier_id=None, free_period_ends_at=None, charter_member_number=None
) -> tuple[Tenant, TenantSignup]:
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"C-B5 State Fields {uuid.uuid4().hex[:8]}",
        is_active=True,
        current_subscription_tier_id=tier_id,
        free_period_ends_at=free_period_ends_at,
        charter_member_number=charter_member_number,
    )
    db_session.add(tenant)
    db_session.flush()

    signup = TenantSignup(
        tenant_id=tenant.id,
        signup_state="step5_confirm",
        signup_started_at=datetime.now(UTC),
        business_name="Acme Electric",
        trade="electrical",
        business_size="1-5",
        zip="12345",
        time_zone="America/New_York",
        owner_email=f"state-{uuid.uuid4()}@example.com",
        owner_first_name="Mike",
        owner_last_name="Johnson",
    )
    db_session.add(signup)
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(signup)
    return tenant, signup


class TestSignupStateFields:
    """get_signup_state() must surface C-B5 Charter lifecycle fields."""

    def test_charter_fields_returned(self, db_session):
        """Charter tenant with tier set returns all three new fields."""
        tier = _make_tier(db_session, requires_payment_method=False)
        fpe = datetime.now(UTC) + timedelta(days=90)
        tenant, _signup = _make_tenant_and_signup(
            db_session,
            tier_id=tier.tier_id,
            free_period_ends_at=fpe,
            charter_member_number=7,
        )

        result = get_signup_state(db_session, tenant.id)
        data = result["collected_data"]

        assert data["free_period_ends_at"] is not None
        assert data["free_period_ends_at"].startswith(fpe.strftime("%Y-%m-%d"))
        assert data["requires_payment_method"] is False
        assert data["charter_member_number"] == 7

    def test_non_charter_defaults(self, db_session):
        """Non-Charter tenant returns requires_payment_method=true, nulls for the rest."""
        tier = _make_tier(db_session, requires_payment_method=True)
        tenant, _signup = _make_tenant_and_signup(db_session, tier_id=tier.tier_id)

        result = get_signup_state(db_session, tenant.id)
        data = result["collected_data"]

        assert data["free_period_ends_at"] is None
        assert data["requires_payment_method"] is True
        assert data["charter_member_number"] is None
