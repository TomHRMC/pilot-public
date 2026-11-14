"""
MKT-B9-A: Tests for state + notes fields on the waitlist signup endpoint.

Verifies that:
  - state and notes are accepted and persisted (both provided)
  - state and notes are optional (omitting both is valid)
  - state alone (without notes) is valid
  - 'Outside the US' is a valid state value
  - state/notes being optional doesn't relax required field validation

Domain: platform_infrastructure (unauthenticated marketing public form endpoints)

NOTE: Marked as integration (not unit) because these tests call the real waitlist
endpoint which triggers send_waitlist_confirmation.delay() via _dispatch(). When a
live Celery/Redis broker is running, the task executes and sends real emails to
sales@pilotfortrades.com. Marking as integration ensures these are excluded from
`-m unit` runs. If you need them in unit, add a mock for
`api.routes.marketing.send_waitlist_confirmation` per test_mkt_b1_waitlist_endpoint.py.
"""

import pytest

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.integration,
]


class TestMktB9WaitlistFields:
    def test_waitlist_signup_with_state_and_notes(self, client):
        """New state + notes fields are accepted and persisted."""
        res = client.post(
            "/api/v1/marketing/waitlist/test",
            json={
                "name": "Dave S.",
                "email": "owner@example.com",
                "trade": "electrical",
                "company_size": "2-5",
                "source": "test",
                "state": "PA",
                "notes": "I run a 3-person shop in Philly.",
                "cf_turnstile_response": "test-token",
            },
        )
        assert res.status_code in (200, 201)
        data = res.json()
        assert data["status"] == "success"

    def test_waitlist_signup_without_state_or_notes(self, client):
        """state and notes are optional — omitting both is valid."""
        res = client.post(
            "/api/v1/marketing/waitlist/test",
            json={
                "name": "Mike R.",
                "email": "owner@example.com",
                "trade": "electrical",
                "company_size": "solo",
                "source": "test",
                "cf_turnstile_response": "test-token",
            },
        )
        assert res.status_code in (200, 201)
        data = res.json()
        assert data["status"] == "success"

    def test_waitlist_signup_with_state_only(self, client):
        """state provided without notes is valid."""
        res = client.post(
            "/api/v1/marketing/waitlist/test",
            json={
                "name": "Chris W.",
                "email": "owner@example.com",
                "trade": "electrical",
                "company_size": "solo",
                "source": "test",
                "state": "DC",
                "cf_turnstile_response": "test-token",
            },
        )
        assert res.status_code in (200, 201)
        data = res.json()
        assert data["status"] == "success"

    def test_waitlist_signup_with_outside_us_state(self, client):
        """'Outside the US' is a valid state value."""
        res = client.post(
            "/api/v1/marketing/waitlist/test",
            json={
                "name": "Test User",
                "email": "owner@example.com",
                "trade": "electrical",
                "company_size": "solo",
                "source": "test",
                "state": "Outside the US",
                "cf_turnstile_response": "test-token",
            },
        )
        assert res.status_code in (200, 201)
        data = res.json()
        assert data["status"] == "success"

    def test_missing_required_trade_still_422(self, client):
        """state/notes being optional doesn't change required field behavior."""
        res = client.post(
            "/api/v1/marketing/waitlist/test",
            json={
                "name": "Test",
                "email": "test@testerror.com",
                "company_size": "solo",
                "source": "test",
                "state": "PA",
                "cf_turnstile_response": "test-token",
                # trade is intentionally omitted
            },
        )
        assert res.status_code == 422
