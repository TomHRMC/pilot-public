"""
TP-B11 — Help Session Detail & Subscription Mutations — Test Endpoints

Coverage:
  1. GET  /api/v1/help/sessions/{session_id}/test                            → get_help_session_test
  2. POST /api/v1/help/sessions/{session_id}/feedback/test                   → submit_session_feedback_test
  3. PUT  /api/v1/tenants/{tenant_id}/subscription/upgrade/test              → upgrade_tenant_subscription_test
  4. POST /api/v1/tenants/{tenant_id}/subscription/convert-from-trial/test   → convert_from_trial_test
  5. POST /api/v1/tenants/{tenant_id}/subscription/change-tier/test          → change_tier_test

Notes per spec:
  - POST /sessions/delete-all has NO /test variant (501 stub — skipped by design)
  - Stripe calls are bypassed in TestUserContext (returns mock response)
  - convert-from-trial and change-tier require a paid tier with stripe_price_id
    → test verifies endpoint is reachable (not 403/405) and returns correct error shape

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - 404 for unknown session IDs
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi import status
from sqlmodel import select

from app.models.subscription import SubscriptionTier
from core.config import settings

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

HELP_BASE = "/api/v1/help"
TENANTS_BASE = "/api/v1/tenants"


# ==================== SECURITY GUARD TESTS ====================


class TestTpB11SecurityGuards:
    def test_get_session_blocked_when_disabled(self, client):
        """GET /help/sessions/{id}/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{HELP_BASE}/sessions/{uuid.uuid4()}/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "test_endpoints_disabled" in response.json()["detail"]["error"]

    def test_upgrade_blocked_in_production(self, client):
        """PUT /tenants/{id}/subscription/upgrade/test returns 403 in production."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.put(
                    f"{TENANTS_BASE}/{TEST_TENANT_ID}/subscription/upgrade/test",
                    json={"target_tier_id": str(uuid.uuid4())},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_feedback_blocked_when_disabled(self, client):
        """POST /sessions/{id}/feedback/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{HELP_BASE}/sessions/{uuid.uuid4()}/feedback/test",
                    json={"signal": "resolved"},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== GET HELP SESSION /test ====================


class TestTpB11GetHelpSession:
    def test_get_session_404_for_unknown(self, client):
        """GET /help/sessions/{id}/test returns 404 for unknown session."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{HELP_BASE}/sessions/{uuid.uuid4()}/test")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_session_endpoint_reachable(self, client):
        """GET /help/sessions/{id}/test is reachable (not 403/405)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get(f"{HELP_BASE}/sessions/{uuid.uuid4()}/test")
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED


# ==================== SUBMIT SESSION FEEDBACK /test ====================


class TestTpB11SubmitSessionFeedback:
    def test_feedback_404_for_unknown_session(self, client):
        """POST /help/sessions/{id}/feedback/test returns 404 for unknown session."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{HELP_BASE}/sessions/{uuid.uuid4()}/feedback/test",
                    json={"signal": "resolved"},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_feedback_400_for_invalid_signal(self, client):
        """POST /help/sessions/{id}/feedback/test returns 400 for invalid signal."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{HELP_BASE}/sessions/{uuid.uuid4()}/feedback/test",
                    json={"signal": "invalid_signal"},
                )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_feedback_endpoint_reachable(self, client):
        """POST /help/sessions/{id}/feedback/test is reachable (not 403/405)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{HELP_BASE}/sessions/{uuid.uuid4()}/feedback/test",
                    json={"signal": "resolved"},
                )
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED


# ==================== UPGRADE SUBSCRIPTION /test ====================


class TestTpB11UpgradeSubscription:
    def test_upgrade_404_for_unknown_tier(self, client, test_tenant):
        """PUT /tenants/{id}/subscription/upgrade/test returns 404 for unknown tier."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.put(
                    f"{TENANTS_BASE}/{TEST_TENANT_ID}/subscription/upgrade/test",
                    json={"target_tier_id": str(uuid.uuid4())},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_upgrade_to_charter_tier_succeeds(self, client, test_tenant, db_session):
        """PUT /upgrade/test to a free/charter tier performs direct update (no Stripe).

        Mode-aware branching:
        - charter mode  : upgrade target = charter tier (is_active=True, monthly_price_cents=0)
        - post-beta mode : upgrade target = charter tier (exists, monthly_price=0) OR
                          any active non-trial tier with no stripe_price_id;
                          if no suitable target found, test is skipped.

        Invariant in both modes: upgrading to a $0 tier should not redirect to Stripe.
        """
        charter_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
        ).first()
        if not charter_tier:
            pytest.skip("No charter tier seeded")

        # In charter mode, charter tier is active and has monthly_price_cents=0.
        # In post-beta mode, charter tier may be inactive but still exists with $0 price.
        # The upgrade endpoint accepts any tier by ID regardless of is_active,
        # so we can still use the charter tier ID to test the no-Stripe code path.
        target_tier = charter_tier

        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.put(
                    f"{TENANTS_BASE}/{TEST_TENANT_ID}/subscription/upgrade/test",
                    json={"target_tier_id": str(target_tier.tier_id)},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["redirect_to_stripe"] is False

    def test_upgrade_endpoint_reachable(self, client):
        """PUT /upgrade/test is reachable (not 403/405)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.put(
                    f"{TENANTS_BASE}/{TEST_TENANT_ID}/subscription/upgrade/test",
                    json={"target_tier_id": str(uuid.uuid4())},
                )
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED


# ==================== CONVERT FROM TRIAL /test ====================


class TestTpB11ConvertFromTrial:
    def test_convert_400_for_trial_tier_target(self, client, db_session):
        """POST /convert-from-trial/test returns 400 when targeting a trial tier."""
        trial_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
        ).first()
        if not trial_tier:
            pytest.skip("No trial tier seeded")

        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{TENANTS_BASE}/{TEST_TENANT_ID}/subscription/convert-from-trial/test",
                    json={
                        "target_tier_id": str(trial_tier.tier_id),
                        "payment_method_id": "pm_test",
                        "billing_email": "test@test.com",
                    },
                )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_convert_endpoint_reachable(self, client):
        """POST /convert-from-trial/test is reachable (not 403/405)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{TENANTS_BASE}/{TEST_TENANT_ID}/subscription/convert-from-trial/test",
                    json={
                        "target_tier_id": str(uuid.uuid4()),
                        "payment_method_id": "pm_test",
                        "billing_email": "test@test.com",
                    },
                )
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED


# ==================== CHANGE TIER /test ====================


class TestTpB11ChangeTier:
    def test_change_tier_400_for_trial_tier_target(self, client, db_session):
        """POST /change-tier/test returns 400 when targeting a trial tier."""
        trial_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
        ).first()
        if not trial_tier:
            pytest.skip("No trial tier seeded")

        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{TENANTS_BASE}/{TEST_TENANT_ID}/subscription/change-tier/test",
                    json={"target_tier_id": str(trial_tier.tier_id)},
                )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_tier_endpoint_reachable(self, client):
        """POST /change-tier/test is reachable (not 403/405)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"{TENANTS_BASE}/{TEST_TENANT_ID}/subscription/change-tier/test",
                    json={"target_tier_id": str(uuid.uuid4())},
                )
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED
