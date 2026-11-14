"""
Tests for: GET /api/v1/communications/recent — COMMS-UI-B1 filter + pagination coverage
Domain: notifications_comms (PRD §3.7)

Covers the 6 required scenarios from the COMMS-UI-B1 batch prompt:
  1. No filters → canonical response shape (items, total, limit, offset)
  2. offset/limit paginate — page 2 differs from page 1; total identical
  3. customer_search = substring of a known seeded customer's display_name
  4. channel=sms → all sms; channel=email → 0 rows (documents D-1)
  5. sent_from / sent_to date-range bounds
  6. Tenant isolation: second_tenant does not see test_tenant's messages

Uses the /recent/test no-JWT endpoint + the test_tenant seeded comms scenario data.
Assertions are ID-scoped / subset-relationship-scoped — never total-count asserts
against the shared seeded tenant (per Test Resilience Rule).
"""

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


class TestCommsUiB1RecentFilters:
    """COMMS-UI-B1: filter + canonical pagination coverage for /recent."""

    # ------------------------------------------------------------------
    # Scenario 1 — No filters → canonical response shape
    # ------------------------------------------------------------------
    def test_no_filters_returns_canonical_shape(self, client, test_tenant):
        """No filters → returns items, total, limit, offset keys; defaults 50/0."""
        response = client.get("/api/v1/communications/recent/test")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) >= {"items", "total", "limit", "offset"}
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert data["limit"] == 50
        assert data["offset"] == 0

    # ------------------------------------------------------------------
    # Scenario 2 — offset/limit paginate
    # ------------------------------------------------------------------
    def test_pagination_page2_differs_from_page1_same_total(self, client, test_tenant):
        """offset=1,limit=1 returns a different first item than offset=0,limit=1;
        total is identical across both pages."""
        page1 = client.get(
            "/api/v1/communications/recent/test",
            params={"limit": 1, "offset": 0},
        )
        page2 = client.get(
            "/api/v1/communications/recent/test",
            params={"limit": 1, "offset": 1},
        )
        assert page1.status_code == 200
        assert page2.status_code == 200
        d1, d2 = page1.json(), page2.json()
        # total must be identical regardless of page
        assert d1["total"] == d2["total"]
        # If there are at least 2 messages, page 2's first item differs from page 1's
        if d1["total"] >= 2:
            assert len(d1["items"]) == 1
            assert len(d2["items"]) == 1
            assert d1["items"][0]["id"] != d2["items"][0]["id"]

    # ------------------------------------------------------------------
    # Scenario 3 — customer_search
    # ------------------------------------------------------------------
    def test_customer_search_filters_by_display_name(self, client, test_tenant):
        """customer_search = substring of a known seeded customer's display_name
        → every returned item's customer_name matches (case-insensitive);
        total ≤ unfiltered total."""
        # First get the unfiltered total
        unfiltered = client.get("/api/v1/communications/recent/test")
        assert unfiltered.status_code == 200
        unfiltered_total = unfiltered.json()["total"]

        # If there is seed data, pick a known customer name substring
        if unfiltered_total == 0:
            pytest.skip("No seeded comms data to test customer_search against")

        # Use a substring of the first item's customer_name
        first_name = unfiltered.json()["items"][0]["customer_name"]
        # Take a distinctive substring (first 3 chars, lowercased for case-insensitive check)
        search_term = first_name[:3]

        response = client.get(
            "/api/v1/communications/recent/test",
            params={"customer_search": search_term},
        )
        assert response.status_code == 200
        data = response.json()
        # Every returned item's customer_name must contain the search term (case-insensitive)
        for item in data["items"]:
            assert search_term.lower() in item["customer_name"].lower()
        # Filtered total ≤ unfiltered total
        assert data["total"] <= unfiltered_total

    # ------------------------------------------------------------------
    # Scenario 4 — channel filter (D-1: SMS-only today)
    # ------------------------------------------------------------------
    def test_channel_sms_returns_all_sms(self, client, test_tenant):
        """channel=sms → all returned items have channel == 'sms'."""
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"channel": "sms"},
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["channel"] == "sms"

    def test_channel_email_returns_zero_rows(self, client, test_tenant):
        """channel=email → items == [] and total == 0 (documents D-1: no email data today)."""
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"channel": "email"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    # ------------------------------------------------------------------
    # Scenario 5 — sent_from / sent_to date-range bounds
    # ------------------------------------------------------------------
    def test_sent_from_future_returns_empty(self, client, test_tenant):
        """sent_from set to 'now + 1 day' → items == [] (nothing in the future)."""
        future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"sent_from": future},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_sent_to_past_returns_empty(self, client, test_tenant):
        """sent_to set to 'now - 10 years' → items == []."""
        past = (datetime.now(UTC) - timedelta(days=365 * 10)).isoformat()
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"sent_to": past},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_sent_window_spanning_seed_data_returns_nonempty(self, client, test_tenant):
        """A date window that spans the seed data → non-empty (if seed data exists)."""
        # Wide window: 10 years ago to 1 day in the future
        start = (datetime.now(UTC) - timedelta(days=365 * 10)).isoformat()
        end = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        response = client.get(
            "/api/v1/communications/recent/test",
            params={"sent_from": start, "sent_to": end},
        )
        assert response.status_code == 200
        data = response.json()
        # If seed data exists, this wide window should return it
        if data["total"] > 0:
            assert len(data["items"]) > 0

    # ------------------------------------------------------------------
    # Scenario 6 — Tenant isolation
    # ------------------------------------------------------------------
    def test_tenant_isolation_second_tenant_sees_no_test_data(
        self, client, db_session, second_tenant
    ):
        """second_tenant context → does not see test_tenant's messages.

        Uses the impl directly with a second_tenant-scoped context to verify
        the tenant_id join isolates data correctly.
        """
        from api.routes.communications import _get_recent_communications_impl
        from core.test_context import TestUserContext

        # Build a TestUserContext scoped to second_tenant
        second_ctx = TestUserContext(
            id=second_tenant.id,  # arbitrary non-reserved UUID
            tenant_id=second_tenant.id,
        )

        result = _get_recent_communications_impl(
            db_session,
            second_ctx,
            limit=50,
            offset=0,
        )
        # second_tenant has no seeded comms data — must see zero rows
        assert result.total == 0
        assert result.items == []
