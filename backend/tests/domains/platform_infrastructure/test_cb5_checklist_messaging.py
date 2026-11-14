"""
C-B5 — Onboarding checklist messaging_setup field.
Domain: platform_infrastructure (PRD §3.8)

Covers:
  - messaging_setup field present in checklist response
  - messaging_setup defaults to false on a fresh checklist
"""

import uuid

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.core import Tenant
from app.models.onboarding import TenantOnboardingChecklist
from app.models.subscription import SubscriptionTier

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]


class TestChecklistMessagingSetup:
    """messaging_setup field on the onboarding checklist response."""

    def test_messaging_setup_in_response(self, client, db_session, test_tenant):
        """GET checklist returns messaging_setup field."""
        # Delete any seeded checklist row for test_tenant so we get a fresh default
        db_session.execute(
            text(
                "DELETE FROM public.tenant_onboarding_checklist WHERE tenant_id = :tid"
            ),
            {"tid": str(test_tenant.id)},
        )
        db_session.commit()

        resp = client.get(f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/test")

        assert resp.status_code == 200
        data = resp.json()
        assert "messaging_setup" in data
        assert data["messaging_setup"] is False

    def test_messaging_setup_defaults_false_on_new_row(self, db_session):
        """A freshly created checklist row has messaging_setup=false."""
        # Use a fresh tenant (ORM model so audit defaults fire) to avoid seed conflicts
        trial_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "trial")
        ).first()

        fresh_tenant = Tenant(
            id=uuid.uuid4(),
            name="C-B5 Msg Default Test",
            is_active=True,
            current_subscription_tier_id=trial_tier.tier_id,
        )
        db_session.add(fresh_tenant)
        db_session.flush()

        checklist = TenantOnboardingChecklist(tenant_id=fresh_tenant.id)
        db_session.add(checklist)
        db_session.commit()
        db_session.refresh(checklist)

        assert checklist.messaging_setup is False
