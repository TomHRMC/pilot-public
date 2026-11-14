"""
C-B9: Tests for 10DLC provisioning state machine + checkout + carrier methods.
Domain: subscriptions_usage (PRD §3.11)

Tests (19 total per design doc §J.1):
  1.  test_initiate_provisioning_standard
  2.  test_initiate_provisioning_sole_proprietor
  3.  test_initiate_provisioning_idempotent
  4.  test_initiate_provisioning_conflict_active
  5.  test_create_checkout_session
  6.  test_checkout_session_completed_handler
  7.  test_submit_otp_success
  8.  test_submit_otp_wrong_state
  9.  test_otp_timeout_transition
  10. test_brand_rejected_refund
  11. test_campaign_rejected_partial_refund
  12. test_state_transition_invalid
  13. test_retry_from_payment_failed
  14. test_retry_wrong_state
  15. test_get_provisioning_status
  16. test_get_provisioning_status_not_found
  17. test_mock_carrier_create_brand
  18. test_mock_carrier_create_campaign
  19. test_campaign_payload_template
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


def _ensure_fee_rows(db_session, entity_type: str) -> None:
    """Ensure carrier_fee_schedule has current rows for the given entity_type."""
    from app.models.billing import CarrierFeeSchedule

    rows = [
        ("brand_registration", 400000, "Brand registration"),
        (
            "campaign_registration_3mo",
            1500000,
            "Campaign registration (3 months prepaid)",
        ),
        ("phone_number", 100000, "Phone number assignment"),
        ("campaign_quarterly", 1500000, "Campaign quarterly recurring"),
    ]

    for fee_code, amount_millicents, description in rows:
        existing = db_session.exec(
            select(CarrierFeeSchedule)
            .where(CarrierFeeSchedule.fee_code == fee_code)
            .where(CarrierFeeSchedule.entity_type == entity_type)
            .where(CarrierFeeSchedule.effective_to.is_(None))
        ).first()
        if not existing:
            fee = CarrierFeeSchedule(
                fee_code=fee_code,
                entity_type=entity_type,
                amount_millicents=amount_millicents,
                description=description,
            )
            db_session.add(fee)
    db_session.commit()


def _create_registration(
    db_session,
    tenant_id,
    entity_type="standard",
    status="quoting",
    user_id=None,
):
    """Create a TenantMessagingRegistration row for testing."""
    from app.models.sms import TenantMessagingRegistration

    reg = TenantMessagingRegistration(
        tenant_id=tenant_id,
        entity_type=entity_type,
        status=status,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(reg)
    db_session.commit()
    db_session.refresh(reg)
    return reg


def _create_profile(db_session, tenant_id, user_id=None):
    """Create a Tenant10DlcProfile row for testing."""
    from app.models.core import Tenant10DlcProfile

    now = datetime.now(UTC)
    profile = Tenant10DlcProfile(
        tenant_id=tenant_id,
        legal_business_name="Test Electric LLC",
        dba_name="Test Electric",
        ein="123456789",
        hq_address_line1="123 Main St",
        hq_city="Wilmington",
        hq_state="DE",
        hq_postal_code="19801",
        hq_country="US",
        support_email="owner@test.com",
        support_phone="+13025551234",
        website="https://test.com",
        vertical="ENERGY",
        created_at=now,
        updated_at=now,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


# ── Provisioning Tests ──────────────────────────────────────────────────────


class TestInitiateProvisioning:
    """Tests for initiate_provisioning()."""

    def test_initiate_provisioning_standard(self, db_session, second_tenant, test_user):
        """Creates registration + profile, fetches quote, status = quoting."""
        from services.messaging_provisioning import initiate_provisioning

        _ensure_fee_rows(db_session, "standard")

        profile_data = {
            "entity_type": "standard",
            "legal_business_name": "Acme Electric LLC",
            "dba_name": "Acme Electric",
            "ein": "123456789",
            "hq_address_line1": "123 Main St",
            "hq_city": "Wilmington",
            "hq_state": "DE",
            "hq_postal_code": "19801",
            "hq_country": "US",
            "support_email": "owner@acme.example.com",
            "support_phone": "+13025551234",
            "website": "https://acme.example.com",
            "vertical": "ENERGY",
        }

        registration, quote = initiate_provisioning(
            db=db_session,
            tenant_id=second_tenant.id,
            entity_type="standard",
            profile_data=profile_data,
            user_id=test_user.id,
        )

        assert registration.status == "quoting"
        assert registration.entity_type == "standard"
        assert registration.tenant_id == second_tenant.id
        assert quote["entity_type"] == "standard"
        assert quote["setup_total_millicents"] > 0

    def test_initiate_provisioning_sole_proprietor(
        self, db_session, second_tenant, test_user
    ):
        """Same but entity_type = sole_proprietor."""
        from services.messaging_provisioning import initiate_provisioning

        _ensure_fee_rows(db_session, "sole_proprietor")

        profile_data = {
            "entity_type": "sole_proprietor",
            "legal_business_name": "Joe Electric",
            "hq_address_line1": "456 Oak St",
            "hq_city": "Newark",
            "hq_state": "DE",
            "hq_postal_code": "19701",
            "support_phone": "+13025555678",
            "website": "https://joe.com",
            "vertical": "ENERGY",
        }

        registration, quote = initiate_provisioning(
            db=db_session,
            tenant_id=second_tenant.id,
            entity_type="sole_proprietor",
            profile_data=profile_data,
            user_id=test_user.id,
        )

        assert registration.status == "quoting"
        assert registration.entity_type == "sole_proprietor"
        assert quote["entity_type"] == "sole_proprietor"

    def test_initiate_provisioning_idempotent(
        self, db_session, second_tenant, test_user
    ):
        """Same tenant re-initiating from a retryable state returns same result."""
        from services.messaging_provisioning import initiate_provisioning

        _ensure_fee_rows(db_session, "standard")

        profile_data = {
            "entity_type": "standard",
            "legal_business_name": "Acme Electric LLC",
            "website": "https://acme.example.com",
            "vertical": "ENERGY",
        }

        # First call
        reg1, quote1 = initiate_provisioning(
            db=db_session,
            tenant_id=second_tenant.id,
            entity_type="standard",
            profile_data=profile_data,
            user_id=test_user.id,
        )

        # Second call (idempotent — re-initiates from quoting)
        reg2, quote2 = initiate_provisioning(
            db=db_session,
            tenant_id=second_tenant.id,
            entity_type="standard",
            profile_data=profile_data,
            user_id=test_user.id,
        )

        # Same registration row (not a duplicate)
        assert reg1.id == reg2.id
        assert reg2.status == "quoting"

    def test_initiate_provisioning_conflict_active(
        self, db_session, second_tenant, test_user
    ):
        """ValueError when status is already active."""
        from services.messaging_provisioning import initiate_provisioning

        _ensure_fee_rows(db_session, "standard")

        # Create a registration in 'active' state
        reg = _create_registration(
            db_session, second_tenant.id, "standard", "active", test_user.id
        )

        profile_data = {
            "entity_type": "standard",
            "legal_business_name": "Acme Electric LLC",
        }

        with pytest.raises(ValueError, match="non-retryable"):
            initiate_provisioning(
                db=db_session,
                tenant_id=second_tenant.id,
                entity_type="standard",
                profile_data=profile_data,
                user_id=test_user.id,
            )


# ── Checkout Tests ──────────────────────────────────────────────────────────


class TestCheckout:
    """Tests for checkout session creation + webhook handler."""

    def test_create_checkout_session(self, db_session, second_tenant, test_user):
        """Creates Stripe Checkout mock, status = awaiting_payment."""
        from services.messaging_provisioning import initiate_provisioning

        _ensure_fee_rows(db_session, "standard")

        profile_data = {
            "entity_type": "standard",
            "legal_business_name": "Acme Electric LLC",
            "website": "https://acme.example.com",
            "vertical": "ENERGY",
        }

        registration, _ = initiate_provisioning(
            db=db_session,
            tenant_id=second_tenant.id,
            entity_type="standard",
            profile_data=profile_data,
            user_id=test_user.id,
        )

        # Mock the Stripe client
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/c/cs_test_123"
        mock_session.payment_intent = "pi_test_123"

        # Set stripe_customer_id on tenant
        from app.models.core import Tenant

        tenant = db_session.get(Tenant, second_tenant.id)
        tenant.stripe_customer_id = "cus_test_123"
        db_session.add(tenant)
        db_session.commit()

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe:
            mock_stripe.return_value.checkout.Session.create.return_value = mock_session

            from services.messaging_checkout import create_10dlc_checkout_session

            checkout_url = create_10dlc_checkout_session(
                db=db_session,
                tenant_id=second_tenant.id,
                registration=registration,
            )

            assert checkout_url == "https://checkout.stripe.com/c/cs_test_123"
            assert registration.stripe_checkout_id == "cs_test_123"
            assert registration.status == "awaiting_payment"

    def test_checkout_session_completed_handler(
        self, db_session, second_tenant, test_user
    ):
        """Webhook handler: attaches PM, transitions to brand_submitted, enqueues task."""
        from services.stripe_subscriptions import handle_checkout_session_completed

        # Create a registration in awaiting_payment
        reg = _create_registration(
            db_session, second_tenant.id, "standard", "awaiting_payment", test_user.id
        )
        reg.quoted_setup_cents = 2000
        db_session.add(reg)
        db_session.commit()

        stripe_event = {
            "data": {
                "object": {
                    "id": "cs_test_456",
                    "metadata": {
                        "purpose": "a2p_10dlc_setup",
                        "registration_id": str(reg.id),
                        "tenant_id": str(second_tenant.id),
                    },
                    "customer": "cus_test_123",
                    "payment_intent": "pi_test_456",
                }
            }
        }

        # Mock Stripe client for PM attachment
        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe,
            patch("core.celery_app.celery_app.send_task") as mock_send_task,
        ):
            mock_pi = MagicMock()
            mock_pi.payment_method = "pm_test_123"
            mock_stripe.return_value.PaymentIntent.retrieve.return_value = mock_pi

            handle_checkout_session_completed(db_session, stripe_event)

            # Verify PM attachment was attempted
            mock_stripe.return_value.Customer.modify.assert_called_once()

            # Verify task was enqueued
            mock_send_task.assert_called_once_with(
                "provision_brand", args=[str(reg.id)]
            )

        # Verify registration transitioned to brand_submitted
        db_session.refresh(reg)
        assert reg.status == "brand_submitted"


# ── OTP Tests ───────────────────────────────────────────────────────────────


class TestOtp:
    """Tests for OTP submission."""

    def test_submit_otp_success(self, db_session, second_tenant, test_user):
        """OTP submitted, transitions to brand_verified."""
        from services.messaging_provisioning import submit_otp

        reg = _create_registration(
            db_session,
            second_tenant.id,
            "sole_proprietor",
            "awaiting_otp",
            test_user.id,
        )
        reg.otp_requested_at = datetime.now(UTC)
        db_session.add(reg)
        db_session.commit()

        new_status = submit_otp(db_session, second_tenant.id, "123456")

        assert new_status == "brand_verified"
        db_session.refresh(reg)
        assert reg.status == "brand_verified"
        assert reg.otp_verified_at is not None

    def test_submit_otp_wrong_state(self, db_session, second_tenant, test_user):
        """ValueError when status is not awaiting_otp."""
        from services.messaging_provisioning import submit_otp

        reg = _create_registration(
            db_session, second_tenant.id, "standard", "quoting", test_user.id
        )

        with pytest.raises(ValueError, match="not valid in status"):
            submit_otp(db_session, second_tenant.id, "123456")

    def test_otp_timeout_transition(self, db_session, second_tenant, test_user):
        """> 24h → transitions back to quoting."""
        from services.messaging_provisioning import check_otp_timeouts

        reg = _create_registration(
            db_session,
            second_tenant.id,
            "sole_proprietor",
            "awaiting_otp",
            test_user.id,
        )
        # Set otp_requested_at to 25 hours ago
        reg.otp_requested_at = datetime.now(UTC) - timedelta(hours=25)
        db_session.add(reg)
        db_session.commit()

        check_otp_timeouts(db_session)

        db_session.refresh(reg)
        assert reg.status == "quoting"
        assert reg.failure_reason is not None
        assert "timeout" in reg.failure_reason.lower()


# ── Rejection + Refund Tests ────────────────────────────────────────────────


class TestRejectionRefund:
    """Tests for brand/campaign rejection + refund."""

    def test_brand_rejected_refund(self, db_session, second_tenant, test_user):
        """Brand rejected → Stripe refund issued, terminal state."""
        from services.messaging_provisioning import poll_brand_status

        reg = _create_registration(
            db_session, second_tenant.id, "standard", "brand_submitted", test_user.id
        )
        reg.telnyx_brand_id = "brand_test_123"
        reg.stripe_payment_intent = "pi_test_789"
        reg.quoted_setup_cents = 2000
        db_session.add(reg)
        db_session.commit()

        # Mock carrier to return rejected, and mock the refund
        from services.sms_carrier import BrandResult

        with (
            patch("services.messaging_provisioning.get_sms_carrier") as mock_carrier,
            patch("services.messaging_provisioning._process_refund") as mock_refund,
        ):
            mock_carrier.return_value.get_brand.return_value = BrandResult(
                brand_id="brand_test_123",
                status="rejected",
                rejection_reason="Brand rejected by carrier",
            )

            poll_brand_status(db_session, reg.id)

            mock_refund.assert_called_once()
            call_kwargs = mock_refund.call_args
            assert call_kwargs.kwargs["full"] is True

        db_session.refresh(reg)
        assert reg.status == "brand_rejected"
        assert reg.failure_reason == "Brand rejected by carrier"

    def test_campaign_rejected_partial_refund(
        self, db_session, second_tenant, test_user
    ):
        """Campaign rejected → partial refund, terminal state."""
        from services.messaging_provisioning import poll_campaign_status

        reg = _create_registration(
            db_session, second_tenant.id, "standard", "campaign_submitted", test_user.id
        )
        reg.telnyx_campaign_id = "campaign_test_123"
        reg.stripe_payment_intent = "pi_test_789"
        reg.quoted_setup_cents = 2000
        db_session.add(reg)
        db_session.commit()

        # Mock carrier to return rejected, and mock the refund
        from services.sms_carrier import CampaignResult

        with (
            patch("services.messaging_provisioning.get_sms_carrier") as mock_carrier,
            patch("services.messaging_provisioning._process_refund") as mock_refund,
        ):
            mock_carrier.return_value.get_campaign.return_value = CampaignResult(
                campaign_id="campaign_test_123",
                status="rejected",
                rejection_reason="Campaign rejected by carrier",
            )

            poll_campaign_status(db_session, reg.id)

            mock_refund.assert_called_once()
            call_kwargs = mock_refund.call_args
            assert call_kwargs.kwargs["full"] is False

        db_session.refresh(reg)
        assert reg.status == "campaign_rejected"


# ── State Transition Tests ──────────────────────────────────────────────────


class TestStateTransition:
    """Tests for state machine validation."""

    def test_state_transition_invalid(self, db_session, second_tenant, test_user):
        """ValueError on invalid transition (e.g., not_started → active)."""
        from services.messaging_provisioning import transition_status

        reg = _create_registration(
            db_session, second_tenant.id, "standard", "not_started", test_user.id
        )

        with pytest.raises(ValueError, match="Invalid state transition"):
            transition_status(db_session, reg, "active")

    def test_retry_from_payment_failed(self, db_session, second_tenant, test_user):
        """payment_failed → quoting (re-fetch quote)."""
        from services.messaging_provisioning import transition_status

        _ensure_fee_rows(db_session, "standard")

        # Create a registration in payment_failed
        reg = _create_registration(
            db_session, second_tenant.id, "standard", "payment_failed", test_user.id
        )
        reg.quoted_setup_cents = 2000
        db_session.add(reg)
        db_session.commit()

        # Retry: transition back to quoting
        transition_status(db_session, reg, "quoting", user_id=test_user.id)

        db_session.refresh(reg)
        assert reg.status == "quoting"

    def test_retry_wrong_state(self, db_session, second_tenant, test_user):
        """409 when status is not payment_failed."""
        from api.routes.messaging_provisioning import _retry_impl

        reg = _create_registration(
            db_session, second_tenant.id, "standard", "quoting", test_user.id
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _retry_impl(db_session, second_tenant.id, test_user.id)

        assert exc_info.value.status_code == 409


# ── Status Tests ────────────────────────────────────────────────────────────


class TestProvisioningStatus:
    """Tests for get_provisioning_status()."""

    def test_get_provisioning_status(self, db_session, second_tenant, test_user):
        """Returns full status dict."""
        from services.messaging_provisioning import get_provisioning_status

        reg = _create_registration(
            db_session, second_tenant.id, "standard", "quoting", test_user.id
        )
        reg.quoted_setup_cents = 2000
        reg.quoted_monthly_cents = 500
        db_session.add(reg)
        db_session.commit()

        status = get_provisioning_status(db_session, second_tenant.id)

        assert status["registration_id"] == reg.id
        assert status["status"] == "quoting"
        assert status["entity_type"] == "standard"
        assert status["quoted_setup_cents"] == 2000
        assert status["quoted_monthly_cents"] == 500

    def test_get_provisioning_status_not_found(self, db_session, second_tenant):
        """ValueError when no registration exists."""
        from services.messaging_provisioning import get_provisioning_status

        with pytest.raises(ValueError, match="No messaging registration"):
            get_provisioning_status(db_session, second_tenant.id)


# ── Mock Carrier Tests ──────────────────────────────────────────────────────


class TestMockCarrier:
    """Tests for MockSmsCarrier 10DLC methods."""

    def test_mock_carrier_create_brand(self):
        """MockSmsCarrier.create_brand returns deterministic result."""
        from services.sms_carrier import MockSmsCarrier

        carrier = MockSmsCarrier()
        result = carrier.create_brand({"legal_business_name": "Test Co"})

        assert result.brand_id == "mock-brand-001"
        assert result.status == "pending"
        assert result.rejection_reason is None

    def test_mock_carrier_create_campaign(self):
        """MockSmsCarrier.create_campaign returns deterministic result."""
        from services.sms_carrier import MockSmsCarrier

        carrier = MockSmsCarrier()
        result = carrier.create_campaign(
            "mock-brand-001", {"campaign_name": "Test Campaign"}
        )

        assert result.campaign_id == "mock-campaign-001"
        assert result.status == "pending"
        assert result.rejection_reason is None

    def test_campaign_payload_template(self):
        """_build_campaign_payload produces correct fields."""
        from services.messaging_provisioning import _build_campaign_payload

        payload = _build_campaign_payload("Acme Electric", "standard")

        assert payload["campaign_name"] == "Acme Electric — Customer Messaging"
        assert payload["use_case"] == "MIXED"
        assert "Acme Electric" in payload["description"]
        assert "Acme Electric" in payload["sample_message_1"]
        assert payload["opt_in_keywords"] == ["START", "YES"]
        assert payload["opt_out_keywords"] == ["STOP", "CANCEL", "UNSUBSCRIBE"]
        assert payload["help_keywords"] == ["HELP"]
        assert payload["sub_use_cases"] is None

        # Sole proprietor uses SOLE_PROPRIETOR use case
        payload_sp = _build_campaign_payload("Joe Electric", "sole_proprietor")
        assert payload_sp["use_case"] == "SOLE_PROPRIETOR"


# ── Carrier Proxy Tests ─────────────────────────────────────────────────────


class TestCarrierProxy:
    """Tests for carrier proxy endpoints (verticals, numbers, assign)."""

    def test_get_verticals(self, db_session, second_tenant):
        """GET /messaging/verticals/test returns carrier verticals."""
        from api.routes.messaging_provisioning import _verticals_impl
        from services.sms_carrier import MockSmsCarrier

        with patch("api.routes.messaging_provisioning.get_sms_carrier") as mock:
            mock.return_value = MockSmsCarrier()
            result = _verticals_impl()

        assert len(result.verticals) > 0
        assert "ENERGY" in result.verticals

    def test_list_available_numbers(self, db_session, second_tenant):
        """GET /messaging/available-numbers/test returns carrier numbers."""
        from api.routes.messaging_provisioning import _available_numbers_impl
        from services.sms_carrier import MockSmsCarrier

        with patch("api.routes.messaging_provisioning.get_sms_carrier") as mock:
            mock.return_value = MockSmsCarrier()
            result = _available_numbers_impl("302", limit=5)

        assert len(result.numbers) > 0
        assert result.numbers[0].phone_number.startswith("+1302")
        assert result.numbers[0].monthly_cost_millicents > 0

    def test_assign_number(self, db_session, second_tenant, test_user):
        """POST /messaging/assign-number/test assigns number, transitions to active."""
        from services.messaging_provisioning import assign_phone_number
        from services.sms_carrier import MockSmsCarrier

        # Create a registration in awaiting_number_selection
        reg = _create_registration(
            db_session,
            second_tenant.id,
            "standard",
            "awaiting_number_selection",
            test_user.id,
        )
        reg.telnyx_campaign_id = "mock-campaign-001"
        db_session.add(reg)
        db_session.commit()

        with patch("services.messaging_provisioning.get_sms_carrier") as mock:
            mock.return_value = MockSmsCarrier()
            assigned = assign_phone_number(
                db_session, second_tenant.id, "+13025551234", test_user.id
            )

        assert assigned == "+13025551234"
        db_session.refresh(reg)
        assert reg.status == "active"
        assert reg.telnyx_phone_number == "+13025551234"
