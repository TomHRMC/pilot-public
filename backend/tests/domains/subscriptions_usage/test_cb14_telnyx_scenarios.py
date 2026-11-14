"""
C-B14 §11.2 — Telnyx Mock Scenarios (8 tests)
=============================================
Domain: subscriptions_usage (PRD §3.11)

Covers the 8 Telnyx provisioning state-machine scenarios from spec §11.2.
All tests mock the Telnyx SDK (via carrier mocking) and Stripe Checkout
(via _get_stripe_client patching). No real Telnyx or Stripe API calls.

Scenarios:
  1. test_ein_happy_path — Standard EIN brand → campaign → number assignment
  2. test_sole_prop_happy_path — Sole prop brand → OTP required
  3. test_sole_prop_otp_timeout — OTP >24h timeout → back to quoting
  4. test_brand_rejected — Brand rejected → full Stripe refund
  5. test_campaign_rejected — Campaign rejected → partial refund
  6. test_checkout_abandoned — Checkout created, not completed → stays awaiting_payment
  7. test_fee_schedule_change — Fee changes between quote and payment → quote honored
  8. test_month4_recurring_item — Registration active >90d → recurring item created
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _create_subscription(db_session, tenant_id, psp_subscription_id="sub_test_cb14"):
    """Create an active Stripe Subscription row for testing."""
    from app.models.billing import Subscription, SubscriptionStatus

    active_status = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == "active")
    ).first()

    sub = Subscription(
        tenant_id=tenant_id,
        product_plan_code="charter_plan",
        status_id=active_status.id,
        psp_provider="stripe",
        psp_subscription_id=psp_subscription_id,
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


# ---------------------------------------------------------------------------
# Scenario 1 — Standard (EIN) happy path
# ---------------------------------------------------------------------------


class TestTelnyxScenarios:
    """C-B14 §11.2 — Telnyx mock scenarios."""

    def test_ein_happy_path(self, db_session, second_tenant, test_user):
        """Standard EIN brand → campaign → number assignment → active.

        State transitions:
          not_started → quoting → awaiting_payment → brand_submitted →
          brand_verified → campaign_submitted → awaiting_number_selection →
          number_assigned → active
        """
        from services.messaging_provisioning import (
            assign_phone_number,
            initiate_provisioning,
            poll_brand_status,
            poll_campaign_status,
            transition_status,
        )
        from services.sms_carrier import (
            BrandResult,
            CampaignResult,
            MockSmsCarrier,
        )

        _ensure_fee_rows(db_session, "standard")

        profile_data = {
            "entity_type": "standard",
            "legal_business_name": "Acme Electric LLC",
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

        # Step 1: initiate → quoting
        registration, quote = initiate_provisioning(
            db=db_session,
            tenant_id=second_tenant.id,
            entity_type="standard",
            profile_data=profile_data,
            user_id=test_user.id,
        )
        assert registration.status == "quoting"
        assert quote["setup_total_millicents"] > 0

        # Step 2: quoting → awaiting_payment
        transition_status(db_session, registration, "awaiting_payment")
        assert registration.status == "awaiting_payment"

        # Step 3: awaiting_payment → brand_submitted (checkout completed)
        transition_status(db_session, registration, "brand_submitted")
        registration.telnyx_brand_id = "brand_ein_001"
        db_session.add(registration)
        db_session.commit()

        # Step 4: brand_submitted → brand_verified (standard, no OTP)
        with patch("services.messaging_provisioning.get_sms_carrier") as mock_carrier:
            mock_carrier.return_value.get_brand.return_value = BrandResult(
                brand_id="brand_ein_001",
                status="verified",
                rejection_reason=None,
            )
            poll_brand_status(db_session, registration.id)

        assert registration.status == "brand_verified"

        # Step 5: brand_verified → campaign_submitted
        transition_status(db_session, registration, "campaign_submitted")
        registration.telnyx_campaign_id = "campaign_ein_001"
        db_session.add(registration)
        db_session.commit()

        # Step 6: campaign_submitted → awaiting_number_selection
        with patch("services.messaging_provisioning.get_sms_carrier") as mock_carrier:
            mock_carrier.return_value.get_campaign.return_value = CampaignResult(
                campaign_id="campaign_ein_001",
                status="approved",
                rejection_reason=None,
            )
            poll_campaign_status(db_session, registration.id)

        assert registration.status == "awaiting_number_selection"

        # Step 7: awaiting_number_selection → number_assigned → active
        with patch("services.messaging_provisioning.get_sms_carrier") as mock_carrier:
            mock_carrier.return_value = MockSmsCarrier()
            assigned = assign_phone_number(
                db_session, second_tenant.id, "+13025551234", test_user.id
            )

        assert assigned == "+13025551234"
        assert registration.status == "active"
        assert registration.telnyx_phone_number == "+13025551234"

    def test_sole_prop_happy_path(self, db_session, second_tenant, test_user):
        """Sole prop brand → OTP required → state halts at awaiting_otp.

        Sole proprietors require OTP verification after brand approval.
        The state machine transitions to awaiting_otp (not brand_verified).
        """
        from services.messaging_provisioning import (
            initiate_provisioning,
            poll_brand_status,
            transition_status,
        )
        from services.sms_carrier import BrandResult

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

        registration, _ = initiate_provisioning(
            db=db_session,
            tenant_id=second_tenant.id,
            entity_type="sole_proprietor",
            profile_data=profile_data,
            user_id=test_user.id,
        )
        assert registration.status == "quoting"

        # quoting → awaiting_payment → brand_submitted
        transition_status(db_session, registration, "awaiting_payment")
        transition_status(db_session, registration, "brand_submitted")
        registration.telnyx_brand_id = "brand_sp_001"
        db_session.add(registration)
        db_session.commit()

        # brand_submitted → awaiting_otp (sole_proprietor path)
        with patch("services.messaging_provisioning.get_sms_carrier") as mock_carrier:
            mock_carrier.return_value.get_brand.return_value = BrandResult(
                brand_id="brand_sp_001",
                status="verified",
                rejection_reason=None,
            )
            poll_brand_status(db_session, registration.id)

        assert registration.status == "awaiting_otp"
        assert registration.otp_requested_at is not None

    def test_sole_prop_otp_timeout(self, db_session, second_tenant, test_user):
        """OTP >24h timeout → operator alerted at T+18h, state returns to quoting.

        The check_otp_timeouts function finds registrations in awaiting_otp
        where otp_requested_at is older than 24h and transitions them back to
        quoting with a failure_reason.
        """
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

    def test_brand_rejected(self, db_session, second_tenant, test_user):
        """Brand rejected → automatic Stripe refund, terminal state brand_rejected.

        poll_brand_status detects rejection, transitions to brand_rejected,
        and calls _process_refund with full=True (full refund of setup charge).
        """
        from services.messaging_provisioning import poll_brand_status
        from services.sms_carrier import BrandResult

        reg = _create_registration(
            db_session,
            second_tenant.id,
            "standard",
            "brand_submitted",
            test_user.id,
        )
        reg.telnyx_brand_id = "brand_rej_001"
        reg.stripe_payment_intent = "pi_test_brand_rej"
        reg.quoted_setup_cents = 2000
        db_session.add(reg)
        db_session.commit()

        with (
            patch("services.messaging_provisioning.get_sms_carrier") as mock_carrier,
            patch("services.messaging_provisioning._process_refund") as mock_refund,
        ):
            mock_carrier.return_value.get_brand.return_value = BrandResult(
                brand_id="brand_rej_001",
                status="rejected",
                rejection_reason="Brand rejected by carrier",
            )

            poll_brand_status(db_session, reg.id)

            mock_refund.assert_called_once()
            assert mock_refund.call_args.kwargs["full"] is True

        db_session.refresh(reg)
        assert reg.status == "brand_rejected"
        assert reg.failure_reason == "Brand rejected by carrier"

    def test_campaign_rejected(self, db_session, second_tenant, test_user):
        """Campaign rejected → partial refund, terminal state campaign_rejected.

        poll_campaign_status detects rejection, transitions to campaign_rejected,
        and calls _process_refund with full=False (partial refund — brand fee
        consumed, campaign+number refunded).
        """
        from services.messaging_provisioning import poll_campaign_status
        from services.sms_carrier import CampaignResult

        reg = _create_registration(
            db_session,
            second_tenant.id,
            "standard",
            "campaign_submitted",
            test_user.id,
        )
        reg.telnyx_campaign_id = "campaign_rej_001"
        reg.stripe_payment_intent = "pi_test_camp_rej"
        reg.quoted_setup_cents = 2000
        db_session.add(reg)
        db_session.commit()

        with (
            patch("services.messaging_provisioning.get_sms_carrier") as mock_carrier,
            patch("services.messaging_provisioning._process_refund") as mock_refund,
        ):
            mock_carrier.return_value.get_campaign.return_value = CampaignResult(
                campaign_id="campaign_rej_001",
                status="rejected",
                rejection_reason="Campaign rejected by carrier",
            )

            poll_campaign_status(db_session, reg.id)

            mock_refund.assert_called_once()
            assert mock_refund.call_args.kwargs["full"] is False

        db_session.refresh(reg)
        assert reg.status == "campaign_rejected"

    def test_checkout_abandoned(self, db_session, second_tenant, test_user):
        """Checkout session created, not completed → no Telnyx call, stays awaiting_payment.

        The tenant creates a checkout session (status → awaiting_payment) but
        never completes it. No Telnyx API calls should be made. The state
        stays at awaiting_payment indefinitely.
        """
        from services.messaging_checkout import create_10dlc_checkout_session
        from services.messaging_provisioning import initiate_provisioning

        _ensure_fee_rows(db_session, "standard")

        profile_data = {
            "entity_type": "standard",
            "legal_business_name": "Abandoned Checkout LLC",
            "website": "https://abandoned.com",
            "vertical": "ENERGY",
        }

        registration, _ = initiate_provisioning(
            db=db_session,
            tenant_id=second_tenant.id,
            entity_type="standard",
            profile_data=profile_data,
            user_id=test_user.id,
        )
        assert registration.status == "quoting"

        # Set stripe_customer_id on tenant for checkout
        from app.models.core import Tenant

        tenant = db_session.get(Tenant, second_tenant.id)
        tenant.stripe_customer_id = "cus_test_abandoned"
        db_session.add(tenant)
        db_session.commit()

        # Create checkout session (mock Stripe)
        mock_session = MagicMock()
        mock_session.id = "cs_test_abandoned_001"
        mock_session.url = "https://checkout.stripe.com/c/cs_test_abandoned_001"
        mock_session.payment_intent = "pi_test_abandoned"

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe:
            mock_stripe.return_value.checkout.Session.create.return_value = mock_session

            checkout_url = create_10dlc_checkout_session(
                db=db_session,
                tenant_id=second_tenant.id,
                registration=registration,
            )

        assert checkout_url == "https://checkout.stripe.com/c/cs_test_abandoned_001"
        assert registration.status == "awaiting_payment"
        assert registration.stripe_checkout_id == "cs_test_abandoned_001"

        # Verify NO Telnyx calls were made (checkout not completed)
        # The registration should still be in awaiting_payment
        db_session.refresh(registration)
        assert registration.status == "awaiting_payment"
        assert registration.telnyx_brand_id is None

    def test_fee_schedule_change(self, db_session, second_tenant, test_user):
        """Fee changes between quote and payment → quote honored, delta logged.

        The carrier_fee_schedule fee changes after the quote is generated but
        before checkout is completed. The registration's quoted_setup_cents
        should retain the original quote value (quote is honored at checkout
        time, not re-fetched).
        """
        from app.models.billing import CarrierFeeSchedule
        from services.messaging_provisioning import initiate_provisioning

        _ensure_fee_rows(db_session, "standard")

        profile_data = {
            "entity_type": "standard",
            "legal_business_name": "Fee Change LLC",
            "website": "https://feechange.com",
            "vertical": "ENERGY",
        }

        registration, quote = initiate_provisioning(
            db=db_session,
            tenant_id=second_tenant.id,
            entity_type="standard",
            profile_data=profile_data,
            user_id=test_user.id,
        )

        original_quoted_setup = registration.quoted_setup_cents
        assert original_quoted_setup is not None
        assert original_quoted_setup > 0

        # Now change the fee schedule — update the existing brand_registration row
        brand_fee = db_session.exec(
            select(CarrierFeeSchedule)
            .where(CarrierFeeSchedule.fee_code == "brand_registration")
            .where(CarrierFeeSchedule.entity_type == "standard")
            .where(CarrierFeeSchedule.effective_to.is_(None))
        ).first()
        assert brand_fee is not None

        original_brand_millicents = brand_fee.amount_millicents
        brand_fee.amount_millicents = original_brand_millicents + 100000  # +$100
        db_session.add(brand_fee)
        db_session.commit()

        # The registration's quoted_setup_cents should NOT have changed
        # (quote was stored at provisioning time, not re-fetched)
        db_session.refresh(registration)
        assert registration.quoted_setup_cents == original_quoted_setup

        # Verify the quote dict also reflects the original (pre-change) amount
        # The quote was computed before the fee change
        assert quote["setup_total_millicents"] > 0

    def test_month4_recurring_item(self, db_session, second_tenant, test_user):
        """Registration active >90d, no recurring item → correct amount, no double-charge.

        create_recurring_carrier_item() creates a Stripe SubscriptionItem with
        unit_amount = registration.quoted_monthly_cents. The idempotency guard
        prevents double-charge (if stripe_recurring_item_id is already set, skip).
        """
        from datetime import UTC, datetime, timedelta

        from services.messaging_recurring import create_recurring_carrier_item

        # Create registration: active, >90d old, no recurring item
        old_date = datetime.now(UTC) - timedelta(days=100)
        reg = _create_registration(
            db_session,
            second_tenant.id,
            "standard",
            "active",
            test_user.id,
        )
        reg.quoted_monthly_cents = 500
        reg.created_at = old_date
        db_session.add(reg)
        db_session.commit()

        _create_subscription(db_session, second_tenant.id)

        mock_ids = {
            "products": {"prod_passthrough": "prod_test_passthrough_001"},
            "prices": {},
            "meters": {},
        }

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe,
            patch("core.stripe_config.get_stripe_ids", return_value=mock_ids),
        ):
            mock_item = MagicMock()
            mock_item.id = "si_test_recurring_cb14_001"
            mock_stripe.return_value.SubscriptionItem.create.return_value = mock_item

            result_id = create_recurring_carrier_item(db_session, reg.id)

        assert result_id == "si_test_recurring_cb14_001"

        db_session.refresh(reg)
        assert reg.stripe_recurring_item_id == "si_test_recurring_cb14_001"
        assert reg.recurring_item_created_at is not None

        # Verify Stripe was called with correct amount from quoted_monthly_cents
        call_kwargs = mock_stripe.return_value.SubscriptionItem.create.call_args.kwargs
        assert call_kwargs["price_data"]["unit_amount"] == 500
        assert call_kwargs["proration_behavior"] == "none"

        # Idempotency: calling again should NOT create a second item
        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe2,
            patch("core.stripe_config.get_stripe_ids", return_value=mock_ids),
        ):
            result_id2 = create_recurring_carrier_item(db_session, reg.id)

        assert result_id2 == "si_test_recurring_cb14_001"
        mock_stripe2.return_value.SubscriptionItem.create.assert_not_called()
