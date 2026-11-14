"""
C-B4: Tests for core/stripe_config.py — singleton loader for stripe_ids.{mode}.json.
Domain: subscriptions_usage (PRD §3.11)
"""

import pytest

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestGetStripeIds:
    """Tests for get_stripe_ids() singleton loader."""

    def test_loads_test_json(self):
        """get_stripe_ids() loads stripe_ids.test.json and returns a dict with expected keys."""
        from core.stripe_config import get_stripe_ids, reset_stripe_ids_cache

        reset_stripe_ids_cache()
        ids = get_stripe_ids()

        assert isinstance(ids, dict)
        assert ids["mode"] == "test"
        assert "products" in ids
        assert "meters" in ids
        assert "prices" in ids
        # Charter monthly price must be present (C-B3 committed it)
        assert "price_charter_monthly" in ids["prices"]
        assert "price_voice_overage" in ids["prices"]
        assert "price_sms_overage" in ids["prices"]

    def test_singleton_cache_returns_same_dict(self):
        """Second call returns the same cached dict object (singleton)."""
        from core.stripe_config import get_stripe_ids, reset_stripe_ids_cache

        reset_stripe_ids_cache()
        first = get_stripe_ids()
        second = get_stripe_ids()

        assert first is second, "get_stripe_ids() should return the same cached object"
