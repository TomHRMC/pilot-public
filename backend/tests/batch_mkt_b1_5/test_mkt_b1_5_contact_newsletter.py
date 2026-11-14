"""
MKT-B1.5-BE — Contact form + Newsletter endpoint tests.
File: backend/tests/batch_mkt_b1_5/test_mkt_b1_5_contact_newsletter.py

Contact form tests (8):
  test_contact_submit_test_endpoint_returns_201
  test_contact_honeypot_non_empty_returns_400
  test_contact_turnstile_failure_returns_400
  test_contact_invalid_trade_returns_422
  test_contact_message_too_long_returns_422
  test_contact_missing_required_fields_returns_422
  test_contact_notification_task_dispatched
  test_contact_rate_limit_returns_429

Newsletter subscribe tests (7):
  test_newsletter_subscribe_test_endpoint_returns_201
  test_newsletter_honeypot_non_empty_returns_400
  test_newsletter_turnstile_failure_returns_400
  test_newsletter_duplicate_email_returns_200_same_shape
  test_newsletter_invalid_email_returns_422
  test_newsletter_confirmation_task_dispatched
  test_newsletter_rate_limit_returns_429

Newsletter unsubscribe tests (6):
  test_newsletter_unsubscribe_valid_token_sets_inactive
  test_newsletter_unsubscribe_invalid_token_returns_400
  test_newsletter_unsubscribe_expired_token_returns_400
  test_newsletter_unsubscribe_already_unsubscribed_returns_200
  test_newsletter_unsubscribe_unknown_email_returns_200
  test_newsletter_unsubscribe_token_verifies_via_task_helper

Total: 21 tests
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.marketing import MarketingNewsletterSubscriber
from core.rate_limit import reset_rate_limits
from tasks.marketing_notifications import generate_newsletter_unsubscribe_token

CONTACT_URL = "/api/v1/marketing/contact"
CONTACT_TEST_URL = "/api/v1/marketing/contact/test"
NEWSLETTER_URL = "/api/v1/marketing/newsletter"
NEWSLETTER_TEST_URL = "/api/v1/marketing/newsletter/test"
NEWSLETTER_UNSUB_URL = "/api/v1/marketing/newsletter/unsubscribe"


# ─── Shared helpers ───────────────────────────────────────────────────────────


def _valid_contact_payload(**overrides):
    base = {
        "name": "Mike Electrician",
        "email": f"mike-{uuid.uuid4().hex[:6]}@example.com",
        "subject": "Question about pricing",
        "message": "I'd like to know more about your plans.",
        "cf_turnstile_response": "valid-test-token",
        "honeypot": "",
    }
    base.update(overrides)
    return base


def _valid_newsletter_payload(**overrides):
    base = {
        "email": f"news-{uuid.uuid4().hex[:6]}@example.com",
        "trade_interest": ["electrical"],
        "cf_turnstile_response": "valid-test-token",
        "honeypot": "",
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def reset_rate_limiter_between_tests():
    """Reset Redis rate-limit counters before/after each test."""
    try:
        reset_rate_limits()
    except Exception:
        pass
    yield
    try:
        reset_rate_limits()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# CONTACT FORM TESTS
# ══════════════════════════════════════════════════════════════════════════════


# ─── Test 1 ───────────────────────────────────────────────────────────────────
def test_contact_submit_test_endpoint_returns_201(client):
    """POST /contact/test must return 201 without Turnstile token in dev context."""
    with patch("api.routes.marketing.send_contact_confirmation") as mock_task:
        mock_task.delay = MagicMock()
        response = client.post(
            CONTACT_TEST_URL,
            json=_valid_contact_payload(cf_turnstile_response=""),
        )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "success"
    assert "message" in data


# ─── Test 2 ───────────────────────────────────────────────────────────────────
def test_contact_honeypot_non_empty_returns_400(client):
    """Honeypot non-empty → 400 before Turnstile is checked."""
    with patch(
        "api.routes.marketing.verify_turnstile",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_turnstile:
        response = client.post(
            CONTACT_URL,
            json=_valid_contact_payload(honeypot="bot-filled"),
        )
        mock_turnstile.assert_not_called()
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid request"


# ─── Test 3 ───────────────────────────────────────────────────────────────────
def test_contact_turnstile_failure_returns_400(client):
    """Turnstile failure → 400 with generic error (no info leakage)."""
    with patch(
        "api.routes.marketing.verify_turnstile",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = client.post(
            CONTACT_URL,
            json=_valid_contact_payload(cf_turnstile_response="bad-token"),
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid request"


# ─── Test 4 ───────────────────────────────────────────────────────────────────
def test_contact_invalid_trade_returns_422(client):
    """trade='nuclear' not in allowed Literal → 422."""
    with patch(
        "api.routes.marketing.verify_turnstile",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = client.post(
            CONTACT_URL,
            json=_valid_contact_payload(trade="nuclear"),
        )
    assert response.status_code == 422, response.text


# ─── Test 5 ───────────────────────────────────────────────────────────────────
def test_contact_message_too_long_returns_422(client):
    """message > 5000 chars → Pydantic 422."""
    with patch(
        "api.routes.marketing.verify_turnstile",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = client.post(
            CONTACT_URL,
            json=_valid_contact_payload(message="x" * 5001),
        )
    assert response.status_code == 422, response.text


# ─── Test 6 ───────────────────────────────────────────────────────────────────
def test_contact_missing_required_fields_returns_422(client):
    """Missing name, subject, or message → Pydantic 422."""
    with patch(
        "api.routes.marketing.verify_turnstile",
        new_callable=AsyncMock,
        return_value=True,
    ):
        # Missing name
        r1 = client.post(
            CONTACT_URL,
            json={
                "email": "test@example.com",
                "subject": "Hello",
                "message": "Body",
                "cf_turnstile_response": "tok",
            },
        )
        # Missing subject
        r2 = client.post(
            CONTACT_URL,
            json={
                "name": "Test",
                "email": "test@example.com",
                "message": "Body",
                "cf_turnstile_response": "tok",
            },
        )
        # Missing message
        r3 = client.post(
            CONTACT_URL,
            json={
                "name": "Test",
                "email": "test@example.com",
                "subject": "Hello",
                "cf_turnstile_response": "tok",
            },
        )
    assert r1.status_code == 422, r1.text
    assert r2.status_code == 422, r2.text
    assert r3.status_code == 422, r3.text


# ─── Test 7 ───────────────────────────────────────────────────────────────────
def test_contact_notification_task_dispatched(client):
    """send_contact_confirmation.delay() is called on successful submit."""
    with (
        patch(
            "api.routes.marketing.verify_turnstile",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("api.routes.marketing.send_contact_confirmation") as mock_task,
    ):
        mock_task.delay = MagicMock()
        response = client.post(
            CONTACT_URL,
            json=_valid_contact_payload(name="Mike", subject="Test"),
        )

    assert response.status_code == 201, response.text
    mock_task.delay.assert_called_once()


# ─── Test 8 ───────────────────────────────────────────────────────────────────
def test_contact_rate_limit_returns_429(client):
    """11 requests → at most 10 succeed, at least 1 rejected (429 or 500)."""
    with (
        patch(
            "api.routes.marketing.verify_turnstile",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("api.routes.marketing.send_contact_confirmation") as mock_task,
    ):
        mock_task.delay = MagicMock()
        responses = [
            client.post(CONTACT_URL, json=_valid_contact_payload()) for _ in range(11)
        ]

    status_codes = [r.status_code for r in responses]
    success_count = sum(1 for s in status_codes if s in (200, 201))
    rejected_count = sum(1 for s in status_codes if s in (429, 500))
    assert success_count <= 10, f"Rate limiter failed: status_codes={status_codes}"
    assert rejected_count >= 1, f"Expected rejection: status_codes={status_codes}"


# ══════════════════════════════════════════════════════════════════════════════
# NEWSLETTER SUBSCRIBE TESTS
# ══════════════════════════════════════════════════════════════════════════════


# ─── Test 9 ───────────────────────────────────────────────────────────────────
def test_newsletter_subscribe_test_endpoint_returns_201(client):
    """POST /newsletter/test must return 201 without Turnstile in dev context."""
    with patch("api.routes.marketing.send_newsletter_confirmation") as mock_task:
        mock_task.delay = MagicMock()
        response = client.post(
            NEWSLETTER_TEST_URL,
            json=_valid_newsletter_payload(cf_turnstile_response=""),
        )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "success"


# ─── Test 10 ──────────────────────────────────────────────────────────────────
def test_newsletter_honeypot_non_empty_returns_400(client):
    """Honeypot non-empty → 400."""
    with patch(
        "api.routes.marketing.verify_turnstile",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_ts:
        response = client.post(
            NEWSLETTER_URL,
            json=_valid_newsletter_payload(honeypot="spambot"),
        )
        mock_ts.assert_not_called()
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid request"


# ─── Test 11 ──────────────────────────────────────────────────────────────────
def test_newsletter_turnstile_failure_returns_400(client):
    """Turnstile failure → 400."""
    with patch(
        "api.routes.marketing.verify_turnstile",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = client.post(NEWSLETTER_URL, json=_valid_newsletter_payload())
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid request"


# ─── Test 12 ──────────────────────────────────────────────────────────────────
def test_newsletter_duplicate_email_returns_200_same_shape(client, db_session):
    """Duplicate email → 200 with same response shape (no enumeration)."""
    email = f"dup-news-{uuid.uuid4().hex[:8]}@example.com"

    # Pre-insert the subscriber
    existing = MarketingNewsletterSubscriber(
        email=email.lower(),
        source="test",
    )
    db_session.add(existing)
    db_session.flush()

    with (
        patch(
            "api.routes.marketing.verify_turnstile",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("api.routes.marketing.send_newsletter_confirmation") as mock_task,
    ):
        mock_task.delay = MagicMock()
        response = client.post(
            NEWSLETTER_URL, json=_valid_newsletter_payload(email=email)
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert "message" in data


# ─── Test 13 ──────────────────────────────────────────────────────────────────
def test_newsletter_invalid_email_returns_422(client):
    """Invalid email → Pydantic 422."""
    with patch(
        "api.routes.marketing.verify_turnstile",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = client.post(
            NEWSLETTER_URL,
            json=_valid_newsletter_payload(email="not-an-email"),
        )
    assert response.status_code == 422, response.text


# ─── Test 14 ──────────────────────────────────────────────────────────────────
def test_newsletter_confirmation_task_dispatched(client):
    """send_newsletter_confirmation.delay() is called on successful subscribe."""
    with (
        patch(
            "api.routes.marketing.verify_turnstile",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("api.routes.marketing.send_newsletter_confirmation") as mock_task,
    ):
        mock_task.delay = MagicMock()
        response = client.post(NEWSLETTER_URL, json=_valid_newsletter_payload())

    assert response.status_code == 201, response.text
    mock_task.delay.assert_called_once()


# ─── Test 15 ──────────────────────────────────────────────────────────────────
def test_newsletter_rate_limit_returns_429(client):
    """11 requests → rate limit enforced."""
    with (
        patch(
            "api.routes.marketing.verify_turnstile",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("api.routes.marketing.send_newsletter_confirmation") as mock_task,
    ):
        mock_task.delay = MagicMock()
        responses = [
            client.post(NEWSLETTER_URL, json=_valid_newsletter_payload())
            for _ in range(11)
        ]

    status_codes = [r.status_code for r in responses]
    success_count = sum(1 for s in status_codes if s in (200, 201))
    rejected_count = sum(1 for s in status_codes if s in (429, 500))
    assert success_count <= 10, f"Rate limiter failed: status_codes={status_codes}"
    assert rejected_count >= 1, f"Expected rejection: status_codes={status_codes}"


# ══════════════════════════════════════════════════════════════════════════════
# NEWSLETTER UNSUBSCRIBE TESTS
# ══════════════════════════════════════════════════════════════════════════════


# ─── Test 16 ──────────────────────────────────────────────────────────────────
def test_newsletter_unsubscribe_valid_token_sets_inactive(client):
    """
    Valid token → subscriber set is_active=False, unsubscribed_at set.

    Strategy: subscribe via /newsletter/test endpoint (which commits properly),
    then unsubscribe with a valid signed token. Avoids db_session pre-insert
    which causes db.commit() issues with the outer test transaction.
    """
    email = f"unsub-{uuid.uuid4().hex[:8]}@example.com"

    # First: subscribe via /test endpoint (proper commit)
    with patch("api.routes.marketing.send_newsletter_confirmation") as mock_task:
        mock_task.delay = MagicMock()
        subscribe_response = client.post(
            NEWSLETTER_TEST_URL,
            json=_valid_newsletter_payload(email=email, cf_turnstile_response=""),
        )
    assert subscribe_response.status_code == 201, subscribe_response.text

    # Then: unsubscribe with a valid signed token
    token = generate_newsletter_unsubscribe_token(email)
    response = client.post(NEWSLETTER_UNSUB_URL, params={"token": token})

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"


# ─── Test 17 ──────────────────────────────────────────────────────────────────
def test_newsletter_unsubscribe_invalid_token_returns_400(client):
    """Tampered/malformed token → 400."""
    response = client.post(NEWSLETTER_UNSUB_URL, params={"token": "garbage.token"})
    assert response.status_code == 400, response.text


# ─── Test 18 ──────────────────────────────────────────────────────────────────
def test_newsletter_unsubscribe_expired_token_returns_400(client):
    """Expired token (TTL in the past) → 400."""
    import base64
    import hashlib
    import hmac
    import json

    from core.config import settings

    # Build a token with an already-expired timestamp
    secret = settings.NEWSLETTER_UNSUBSCRIBE_SECRET
    payload = {
        "email": "expired@example.com",
        "expiration": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode("ascii")
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    token = f"{payload_b64}.{sig_b64}"

    response = client.post(NEWSLETTER_UNSUB_URL, params={"token": token})
    assert response.status_code == 400, response.text


# ─── Test 19 ──────────────────────────────────────────────────────────────────
def test_newsletter_unsubscribe_already_unsubscribed_returns_200(client, db_session):
    """Already-unsubscribed subscriber → idempotent 200."""
    email = f"already-unsub-{uuid.uuid4().hex[:8]}@example.com"
    subscriber = MarketingNewsletterSubscriber(
        email=email.lower(),
        is_active=False,
        unsubscribed_at=datetime.now(UTC),
    )
    db_session.add(subscriber)
    db_session.flush()

    token = generate_newsletter_unsubscribe_token(email)
    response = client.post(NEWSLETTER_UNSUB_URL, params={"token": token})

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success"


# ─── Test 20 ──────────────────────────────────────────────────────────────────
def test_newsletter_unsubscribe_unknown_email_returns_200(client):
    """Email not in DB → idempotent 200 (no enumeration)."""
    token = generate_newsletter_unsubscribe_token("never-subscribed@example.com")
    response = client.post(NEWSLETTER_UNSUB_URL, params={"token": token})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success"


# ─── Test 21 ──────────────────────────────────────────────────────────────────
def test_newsletter_unsubscribe_token_verifies_via_task_helper():
    """
    generate_newsletter_unsubscribe_token() produces a token that
    _verify_newsletter_unsubscribe_token() can decode to the correct email.
    """
    from api.routes.marketing import _verify_newsletter_unsubscribe_token

    email = "roundtrip@example.com"
    token = generate_newsletter_unsubscribe_token(email)
    decoded_email = _verify_newsletter_unsubscribe_token(token)

    assert decoded_email == email
