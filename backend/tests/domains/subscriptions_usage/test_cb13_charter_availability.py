"""C-B13: Tests for the public Charter availability endpoint.

GET /api/v1/public/charter-availability → {open: bool, remaining: int}
Domain: subscriptions_usage

This endpoint is public (no auth). Tests use the ``client`` fixture which
overrides the DB session with the transaction-rollback ``db_session`` fixture.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import func
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


# ==================== HELPERS ====================


def _get_charter_tier(db_session):
    """Fetch the seeded Charter tier (read-only)."""
    from app.models.subscription import SubscriptionTier

    return db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()


def _count_charter_tenants(db_session):
    """Count charter-eligible tenants (read-only, mirrors endpoint logic)."""
    from app.models.core import Tenant

    return db_session.exec(
        select(func.count(Tenant.id)).where(Tenant.charter_eligible == True)
    ).one()


# ==================== ENDPOINT TESTS (via client fixture) ====================


class TestCharterAvailabilityEndpoint:
    """Tests hitting GET /api/v1/public/charter-availability via TestClient."""

    def test_charter_availability_no_auth_required(self, client):
        """Endpoint returns 200 without any auth headers."""
        resp = client.get("/api/v1/public/charter-availability")
        assert resp.status_code == 200

    def test_charter_availability_response_shape(self, client):
        """Response has ``open`` (bool) and ``remaining`` (int) fields."""
        resp = client.get("/api/v1/public/charter-availability")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"open", "remaining"}
        assert isinstance(body["open"], bool)
        assert isinstance(body["remaining"], int)

    def test_charter_availability_open(self, client, db_session):
        """Charter tier active + Charter tenants exist → open=True, remaining>0.

        Seed data: Charter tier signup_cap=12, at least 1 charter-eligible tenant.
        We assert the endpoint reflects the live DB state.
        """
        charter_tier = _get_charter_tier(db_session)
        assert charter_tier is not None, "Charter tier not seeded"
        assert charter_tier.is_active, "Charter tier should be active in seed data"

        charter_count = _count_charter_tenants(db_session)
        expected_remaining = charter_tier.signup_cap - charter_count

        resp = client.get("/api/v1/public/charter-availability")
        assert resp.status_code == 200
        body = resp.json()

        if expected_remaining > 0:
            assert body["open"] is True
            assert body["remaining"] == expected_remaining
            assert body["remaining"] > 0
        else:
            # Cap reached — cohort closed
            assert body["open"] is False
            assert body["remaining"] == 0

    def test_charter_availability_remaining_calculation(self, client, db_session):
        """``remaining == signup_cap - charter_count`` against live DB state."""
        charter_tier = _get_charter_tier(db_session)
        assert charter_tier is not None

        charter_count = _count_charter_tenants(db_session)
        expected_remaining = max(charter_tier.signup_cap - charter_count, 0)

        resp = client.get("/api/v1/public/charter-availability")
        assert resp.status_code == 200
        body = resp.json()
        assert body["remaining"] == expected_remaining


# ==================== SERVICE LOGIC TESTS (direct function call) ====================


class TestCharterAvailabilityLogic:
    """Test the endpoint function directly with a mock session.

    This lets us exercise the closed-tier and tier-not-found branches
    without mutating shared seed data.
    """

    def test_closed_tier_returns_closed(self):
        """When Charter tier is_active=False → {open: False, remaining: 0}."""
        from api.routes.public_charter import get_charter_availability

        mock_tier = MagicMock()
        mock_tier.is_active = False
        mock_tier.signup_cap = 12

        mock_db = MagicMock()
        mock_db.exec.return_value.first.return_value = mock_tier

        result = get_charter_availability(db=mock_db)
        assert result.open is False
        assert result.remaining == 0

    def test_tier_not_found_returns_closed(self):
        """When Charter tier does not exist → {open: False, remaining: 0}."""
        from api.routes.public_charter import get_charter_availability

        mock_db = MagicMock()
        mock_db.exec.return_value.first.return_value = None

        result = get_charter_availability(db=mock_db)
        assert result.open is False
        assert result.remaining == 0

    def test_cap_reached_returns_closed(self):
        """When charter_count >= signup_cap → {open: False, remaining: 0}."""
        from api.routes.public_charter import get_charter_availability

        mock_tier = MagicMock()
        mock_tier.is_active = True
        mock_tier.signup_cap = 12

        mock_db = MagicMock()
        # First .exec() call → tier lookup; second → count query
        tier_result = MagicMock()
        tier_result.first.return_value = mock_tier
        count_result = MagicMock()
        count_result.one.return_value = 12  # cap reached

        mock_db.exec.side_effect = [tier_result, count_result]

        result = get_charter_availability(db=mock_db)
        assert result.open is False
        assert result.remaining == 0

    def test_open_with_remaining(self):
        """When tier active and count < cap → {open: True, remaining: N}."""
        from api.routes.public_charter import get_charter_availability

        mock_tier = MagicMock()
        mock_tier.is_active = True
        mock_tier.signup_cap = 12

        mock_db = MagicMock()
        tier_result = MagicMock()
        tier_result.first.return_value = mock_tier
        count_result = MagicMock()
        count_result.one.return_value = 1  # 1 charter tenant

        mock_db.exec.side_effect = [tier_result, count_result]

        result = get_charter_availability(db=mock_db)
        assert result.open is True
        assert result.remaining == 11
