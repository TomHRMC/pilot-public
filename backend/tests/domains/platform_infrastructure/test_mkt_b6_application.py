"""
Tests for: MKT-B6 Job Application endpoint + Waitlist name field
Domain: platform_infrastructure (PRD §3.8)

Coverage:
    test_application_submit_success            — POST /application/test → 201, row in DB
    test_application_submit_honeypot_blocked   — POST /application with honeypot → 400
    test_application_submit_missing_required   — POST with missing required fields → 422
    test_waitlist_signup_with_name             — POST /waitlist/test with name → name stored
    test_waitlist_signup_without_name          — POST /waitlist/test without name → 201, nullable OK
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

from app.models.marketing import MarketingJobApplication, MarketingWaitlistSignup

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]

APPLICATION_TEST_URL = "/api/v1/marketing/application/test"
APPLICATION_URL = "/api/v1/marketing/application"
WAITLIST_TEST_URL = "/api/v1/marketing/waitlist/test"


def _valid_application_payload(**overrides):
    """Build a valid job application request payload."""
    base = {
        "name": "Jane Engineer",
        "email": f"applicant-{uuid.uuid4().hex[:8]}@example.com",
        "role": "AI / ML Engineer",
        "linkedin_url": "https://linkedin.com/in/jane-engineer",
        "portfolio_url": "https://github.com/jane-engineer",
        "why_interested": "I want to help solo contractors save time with AI.",
        "cf_turnstile_response": "valid-test-token",
        "honeypot": "",
    }
    base.update(overrides)
    return base


def _valid_waitlist_payload(**overrides):
    """Build a valid waitlist signup request payload."""
    base = {
        "email": f"waitlist-{uuid.uuid4().hex[:8]}@example.com",
        "trade": "electrical",
        "company_size": "solo",
        "source": "careers_page",
        "cf_turnstile_response": "valid-test-token",
        "honeypot": "",
    }
    base.update(overrides)
    return base


class TestApplicationSubmit:
    """Tests for POST /api/v1/marketing/application and /application/test"""

    def test_application_submit_success(self, client, db_session):
        """Happy path: POST to /test endpoint → 201, row stored in DB with correct fields."""
        with patch("api.routes.marketing.send_application_confirmation") as mock_task:
            mock_task.delay = MagicMock()

            payload = _valid_application_payload()
            response = client.post(APPLICATION_TEST_URL, json=payload)

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "success"
        assert (
            "application" in data["message"].lower()
            or "received" in data["message"].lower()
        )

        # Verify the row was persisted with correct data
        row = db_session.exec(
            select(MarketingJobApplication).where(
                MarketingJobApplication.email == payload["email"].lower()
            )
        ).first()
        assert row is not None, "Application row should be in DB"
        assert row.name == payload["name"]
        assert row.role == payload["role"]
        assert row.linkedin_url == payload["linkedin_url"]
        assert row.portfolio_url == payload["portfolio_url"]
        assert row.why_interested == payload["why_interested"]
        assert row.is_reviewed is False

    def test_application_submit_honeypot_blocked(self, client):
        """Honeypot field non-empty → reject with 400 (public endpoint)."""
        from unittest.mock import AsyncMock

        with patch(
            "api.routes.marketing.verify_turnstile",
            new_callable=AsyncMock,
            return_value=True,
        ):
            payload = _valid_application_payload(honeypot="bot-filled-this")
            response = client.post(APPLICATION_URL, json=payload)

        assert response.status_code == 400, response.text
        assert response.json()["detail"] == "Invalid request"

    def test_application_submit_missing_required_fields(self, client):
        """POST with missing required fields (name, role, why_interested) → 422."""
        # Missing `name`
        payload = _valid_application_payload()
        del payload["name"]
        response = client.post(APPLICATION_TEST_URL, json=payload)
        assert response.status_code == 422, response.text

    def test_application_submit_missing_role(self, client):
        """POST without role → 422."""
        payload = _valid_application_payload()
        del payload["role"]
        response = client.post(APPLICATION_TEST_URL, json=payload)
        assert response.status_code == 422, response.text


class TestWaitlistNameField:
    """Tests for name field addition to /waitlist/test endpoint."""

    def test_waitlist_signup_with_name(self, client, db_session):
        """POST /waitlist/test with name field → 201, name stored in DB."""
        with patch("api.routes.marketing.send_waitlist_confirmation") as mock_task:
            mock_task.delay = MagicMock()

            email = f"named-{uuid.uuid4().hex[:8]}@example.com"
            payload = _valid_waitlist_payload(email=email, name="Mike the Electrician")
            response = client.post(WAITLIST_TEST_URL, json=payload)

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "success"
        assert "position" in data

        # Verify name was stored in DB
        row = db_session.exec(
            select(MarketingWaitlistSignup).where(
                MarketingWaitlistSignup.email == email.lower()
            )
        ).first()
        assert row is not None, "Waitlist row should be in DB"
        assert row.name == "Mike the Electrician"

    def test_waitlist_signup_without_name(self, client, db_session):
        """POST /waitlist/test without name field → 201, name is NULL (backward compat)."""
        with patch("api.routes.marketing.send_waitlist_confirmation") as mock_task:
            mock_task.delay = MagicMock()

            email = f"noname-{uuid.uuid4().hex[:8]}@example.com"
            payload = _valid_waitlist_payload(email=email)
            # Do NOT include name field — backward compat
            response = client.post(WAITLIST_TEST_URL, json=payload)

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "success"

        # Verify row exists with name=None
        row = db_session.exec(
            select(MarketingWaitlistSignup).where(
                MarketingWaitlistSignup.email == email.lower()
            )
        ).first()
        assert row is not None, "Waitlist row should be in DB"
        assert row.name is None, "name should be NULL when not provided"


class TestEmailTLDValidation:
    """A-11: Email TLD guard — 1-char TLDs must be rejected by Pydantic validator."""

    def test_application_submit_invalid_email_tld(self, client):
        """me@me.t should be rejected — 1-char TLD fails our field_validator → 422."""
        resp = client.post(
            APPLICATION_TEST_URL,
            json={
                "name": "Test User",
                "email": "me@me.t",
                "role": "AI / ML Engineer",
                "linkedin_url": "https://linkedin.com/in/test",
                "why_interested": "I want to join the team.",
                "cf_turnstile_response": "test",
            },
        )
        assert resp.status_code == 422, resp.text

    def test_waitlist_submit_invalid_email_tld(self, client):
        """Waitlist: me@me.t → 422 via field_validator on WaitlistSignupRequest."""
        resp = client.post(
            WAITLIST_TEST_URL,
            json={
                "email": "me@me.t",
                "trade": "electrical",
                "company_size": "solo",
                "source": "test",
                "cf_turnstile_response": "test",
            },
        )
        assert resp.status_code == 422, resp.text

    def test_valid_two_char_tld_accepted(self, client, db_session):
        """2-char TLD like .io or .uk must pass validation."""
        with patch("api.routes.marketing.send_application_confirmation") as mock_task:
            mock_task.delay = MagicMock()
            resp = client.post(
                APPLICATION_TEST_URL,
                json={
                    "name": "Test User",
                    "email": f"test-{uuid.uuid4().hex[:6]}@example.io",
                    "role": "AI / ML Engineer",
                    "linkedin_url": "https://linkedin.com/in/test",
                    "why_interested": "I want to join the team.",
                    "cf_turnstile_response": "test",
                },
            )
        assert resp.status_code == 201, resp.text
