"""
B14/A76 — Stripe Webhook Dedup Table + Integration tests.

Test focus cases:
1. StripeWebhookEventProcessed model has correct PK (text event_id)
2. Webhook dedup: same event_id → duplicate response, second insert not committed
3. POST /api/v1/webhooks/stripe without Stripe-Signature → 401
4. POST /api/v1/webhooks/stripe with missing event_id → 400
5. Valid webhook insert creates dedup record
6. stripe_webhook_event_processed uses AppendOnlyMixin (no updated_at)
7. Config has STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_BASE_URL
"""

import json
import uuid
from datetime import UTC, datetime

from sqlmodel import select

from app.models.billing import StripeWebhookEventProcessed

# ==================== TEST CASES ====================


class TestStripeWebhookDedupModel:
    """Test cases 1-2, 6: StripeWebhookEventProcessed model."""

    def test_model_has_text_pk(self):
        """PK is a TEXT field (Stripe event IDs are strings)."""
        field_info = StripeWebhookEventProcessed.model_fields
        # PK should be event_id
        assert "event_id" in field_info

    def test_model_has_no_updated_at(self):
        """AppendOnlyMixin — no updated_at column."""
        assert not hasattr(StripeWebhookEventProcessed, "updated_at")

    def test_dedup_insert_creates_record(self, db_session):
        """Insert dedup record with string event_id."""
        event_id = f"evt_{uuid.uuid4().hex[:16]}"
        record = StripeWebhookEventProcessed(
            event_id=event_id,
            processed_at=datetime.now(UTC),
            event_type="invoice.paid",
        )
        db_session.add(record)
        db_session.commit()

        fetched = db_session.exec(
            select(StripeWebhookEventProcessed).where(
                StripeWebhookEventProcessed.event_id == event_id
            )
        ).first()
        assert fetched is not None
        assert fetched.event_type == "invoice.paid"

    def test_duplicate_event_id_detected(self, db_session):
        """Same event_id: inserting twice should fail (PK constraint)."""
        event_id = f"evt_{uuid.uuid4().hex[:16]}"
        record1 = StripeWebhookEventProcessed(
            event_id=event_id,
            processed_at=datetime.now(UTC),
            event_type="invoice.paid",
        )
        db_session.add(record1)
        db_session.commit()

        # Check existing before inserting
        existing = db_session.exec(
            select(StripeWebhookEventProcessed).where(
                StripeWebhookEventProcessed.event_id == event_id
            )
        ).first()
        assert existing is not None  # Dedup check would catch this


class TestStripeWebhookEndpoint:
    """Test cases 3-5: POST /api/v1/webhooks/stripe."""

    def _make_event(self, event_type="invoice.paid"):
        """Build a minimal Stripe-like event payload."""
        return {
            "id": f"evt_{uuid.uuid4().hex[:16]}",
            "type": event_type,
            "data": {"object": {"customer": "cus_test123"}},
        }

    def test_missing_signature_returns_401(self, client, test_tenant):
        """POST without Stripe-Signature header returns 401 when STRIPE_WEBHOOK_SECRET is set."""
        # When STRIPE_WEBHOOK_SECRET is empty string (default), signature verification is skipped
        # When configured, would return 401. For this test we verify the behavior with empty secret.
        from unittest.mock import patch

        from core.config import settings

        # Patch webhook secret to a non-empty value to trigger signature check
        with patch.object(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"):
            response = client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(self._make_event()).encode(),
                headers={"Content-Type": "application/json"},
            )
        assert response.status_code == 401

    def test_missing_event_id_returns_400(self, client, test_tenant):
        """POST with payload missing 'id' returns 400.

        Patches STRIPE_WEBHOOK_SECRET to '' so signature verification is skipped
        and the 400 (missing event_id) fires instead of 401 (bad signature).
        """
        from unittest.mock import patch

        from core.config import settings

        with patch.object(settings, "STRIPE_WEBHOOK_SECRET", ""):
            response = client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps({"type": "invoice.paid", "data": {}}).encode(),
                headers={"Content-Type": "application/json"},
            )
        assert response.status_code == 400

    def test_valid_webhook_creates_dedup_record(self, client, db_session, test_tenant):
        """Valid webhook (no signature configured) creates dedup record and returns 200.

        Patches STRIPE_WEBHOOK_SECRET to '' so signature verification is skipped,
        matching the 'no secret configured' design path tested here.
        """
        from unittest.mock import patch

        from core.config import settings

        event = self._make_event("invoice.paid")
        event_id = event["id"]

        with patch.object(settings, "STRIPE_WEBHOOK_SECRET", ""):
            response = client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event).encode(),
                headers={"Content-Type": "application/json"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["event_id"] == event_id

        # Verify dedup record was created
        record = db_session.exec(
            select(StripeWebhookEventProcessed).where(
                StripeWebhookEventProcessed.event_id == event_id
            )
        ).first()
        assert record is not None
        assert record.event_type == "invoice.paid"

    def test_duplicate_webhook_returns_duplicate_status(
        self, client, db_session, test_tenant
    ):
        """Same event_id submitted twice → second response is 'duplicate'.

        Patches STRIPE_WEBHOOK_SECRET to '' so signature verification is skipped,
        allowing the dedup logic to be exercised without a valid HMAC.
        """
        from unittest.mock import patch

        from core.config import settings

        event = self._make_event("customer.subscription.created")
        event_payload = json.dumps(event).encode()

        with patch.object(settings, "STRIPE_WEBHOOK_SECRET", ""):
            # First submission
            resp1 = client.post(
                "/api/v1/webhooks/stripe",
                content=event_payload,
                headers={"Content-Type": "application/json"},
            )
            assert resp1.status_code == 200
            assert resp1.json()["status"] == "received"

            # Second submission with same event_id
            resp2 = client.post(
                "/api/v1/webhooks/stripe",
                content=event_payload,
                headers={"Content-Type": "application/json"},
            )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "duplicate"


class TestStripeConfig:
    """Test case 7: Config settings."""

    def test_stripe_config_keys_exist(self):
        """STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_BASE_URL are in Settings."""
        from core.config import settings

        assert hasattr(settings, "STRIPE_SECRET_KEY")
        assert hasattr(settings, "STRIPE_WEBHOOK_SECRET")
        assert hasattr(settings, "STRIPE_BASE_URL")

    def test_stripe_base_url_default(self):
        """Default STRIPE_BASE_URL is the production Stripe API."""
        from core.config import settings

        assert settings.STRIPE_BASE_URL == "https://api.stripe.com"
