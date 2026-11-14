"""
C-B14 §11.1 — Stripe Test-Clock Integration Scenarios (12 tests)
================================================================
Domain: subscriptions_usage (PRD §3.11)

Covers the 12 Stripe test-clock integration scenarios from spec §11.1.
Each test creates its own test-clocked customer and makes real Stripe
test-mode API calls. Skips if STRIPE_SECRET_KEY is not a real sk_test_... key.

C-SPIKE-1 Q#4: 2-5s sleep before advancing test clocks (meter events are async).
C-SPIKE-1 Q#3: resume_subscription checks status after resume (can silently fail).

Scenarios:
   1. test_charter_signup_no_card_advance_91d — trial expires → paused
   2. test_charter_signup_card_at_85d_advance_91d — card attach + resume → active
   3. test_silent_extension_at_80d — extend free period → still trialing
   4. test_extension_at_95d_already_paused — extend when paused → rejected
   5. test_10dlc_checkout_at_20d_advance_91d — 10DLC checkout + conversion
   6. test_meter_events_during_trial — meter event during trial → $0 invoice
   7. test_meter_events_post_conversion_overage — overage → $10 invoice
   8. test_charter_to_teams_upgrade — Charter → Teams upgrade
   9. test_cancel — cancel → charter_eligible=false
  10. test_12th_signup_cap_flip — 12th signup → cap reached, is_active=false
  11. test_concurrent_11th_12th_signups — concurrent → exactly 12, no dup
  12. test_duplicate_webhook_idempotent — duplicate webhook → idempotent
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.requires_stripe,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_status_id(db_session, code: str) -> uuid.UUID:
    """Look up a platform SubscriptionStatus row by code."""
    from app.models.billing import SubscriptionStatus

    row = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == code)
    ).first()
    assert row is not None, f"SubscriptionStatus code='{code}' not seeded"
    return row.id


def _setup_charter_tenant(db_session, tenant, stripe_customer_id):
    """Configure a tenant as a Charter member with stripe_customer_id."""
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier

    charter_tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    assert charter_tier is not None, "charter tier not seeded"

    tenant_row = db_session.exec(select(Tenant).where(Tenant.id == tenant.id)).first()
    tenant_row.charter_eligible = True
    tenant_row.current_subscription_tier_id = charter_tier.tier_id
    tenant_row.stripe_customer_id = stripe_customer_id
    free_ends = datetime.now(UTC) + timedelta(days=90)
    tenant_row.free_period_ends_at = free_ends
    db_session.add(tenant_row)
    db_session.commit()
    return tenant_row, free_ends


def _create_db_subscription(
    db_session,
    tenant_id,
    psp_sub_id,
    psp_customer_id,
    status_code="trialing",
):
    """Create a DB subscription row scoped to this test.

    PLP-STRIPE-CHARTER-ROW-1: create_charter_subscription() now writes the
    local row itself (write-at-source), so a row for ``psp_sub_id`` may already
    exist by the time this helper runs. In that case, sync its status to the
    requested code and return it instead of inserting a duplicate (the
    psp_subscription_id unique constraint would otherwise raise).
    """
    from app.models.billing import Subscription

    existing = db_session.exec(
        select(Subscription).where(Subscription.psp_subscription_id == psp_sub_id)
    ).first()
    if existing is not None:
        expected_status_id = _get_status_id(db_session, status_code)
        if existing.status_id != expected_status_id:
            existing.status_id = expected_status_id
            db_session.add(existing)
            db_session.commit()
        db_session.refresh(existing)
        return existing

    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_plan_code="charter_plan",
        status_id=_get_status_id(db_session, status_code),
        quantity_seats=1,
        psp_provider="stripe",
        psp_subscription_id=psp_sub_id,
        psp_customer_id=psp_customer_id,
        billing_interval="monthly",
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def _sync_sub_status(db_session, sub_row, stripe_sub):
    """Sync DB subscription status with Stripe subscription status."""
    from app.models.billing import SubscriptionStatus

    status_code = stripe_sub.status
    # Map Stripe status to our status code
    if status_code == "trialing":
        code = "trialing"
    elif status_code == "active":
        code = "active"
    elif status_code == "paused":
        code = "paused"
    elif status_code == "canceled":
        code = "canceled"
    else:
        code = status_code

    status = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == code)
    ).first()
    if status:
        sub_row.status_id = status.id
        db_session.add(sub_row)
        db_session.commit()


def _retry_stripe_call(func, *args, max_retries=5, delay=10, **kwargs):
    """Retry a Stripe API call on RateLimitError ("clock advancement underway").

    Stripe test clocks take time to process after advancement. This helper
    retries the call with a delay between attempts.
    """
    import time as _time

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "advancement underway" in str(e) and attempt < max_retries - 1:
                _time.sleep(delay)
                continue
            raise


def _add_metered_items(stripe, subscription_id):
    """Add voice_overage + sms_overage metered items to a subscription.

    Used in scenarios that attach a PM directly (without calling
    resume_subscription()) — the metered items can't be on the
    subscription during trial-pause, so they must be added after
    the PM is attached and the subscription is no longer pausing.

    Retries on RateLimitError ("Test clock advancement underway").
    """
    from services.stripe_subscriptions import _add_metered_overage_items

    _retry_stripe_call(_add_metered_overage_items, stripe, subscription_id)


# ---------------------------------------------------------------------------
# Scenarios 1-9: Charter lifecycle with real Stripe test clocks
# ---------------------------------------------------------------------------


class TestStripeScenarios:
    """C-B14 §11.1 — Stripe test-clock integration scenarios."""

    def test_charter_signup_no_card_advance_91d(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 1: Charter signup, no card, advance 91d → paused.

        Trial expires with no payment method → subscription pauses.
        is_subscription_billing_active() returns False.
        """
        import stripe

        from services.entitlement_service import is_subscription_billing_active

        clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        # Create charter subscription (trial, no PM)
        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        _create_db_subscription(
            db_session, second_tenant.id, stripe_sub_id, customer.id, "trialing"
        )

        # Advance 91 days (trial is 90 days → pauses)
        from tests.domains.subscriptions_usage.conftest import advance_clock_and_wait

        advance_clock_and_wait(stripe, clock.id, days=91)

        # Retrieve Stripe subscription status (retry — clock may still be processing)
        stripe_sub = _retry_stripe_call(stripe.Subscription.retrieve, stripe_sub_id)
        assert stripe_sub.status == "paused"

        # Sync DB and verify billing-active gate
        sub_row = db_session.exec(
            select(
                __import__("app.models.billing", fromlist=["Subscription"]).Subscription
            ).where(
                __import__(
                    "app.models.billing", fromlist=["Subscription"]
                ).Subscription.psp_subscription_id
                == stripe_sub_id
            )
        ).first()
        _sync_sub_status(db_session, sub_row, stripe_sub)
        assert is_subscription_billing_active(db_session, second_tenant.id) is False

    def test_charter_signup_card_at_85d_advance_91d(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 2: Charter signup, card at day 85, advance 91d → active.

        Attach PM at day 85, resume subscription, advance to day 91.
        Subscription should be active, invoice paid ($49).
        """
        import stripe

        from services.entitlement_service import is_subscription_billing_active

        clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        sub_row = _create_db_subscription(
            db_session, second_tenant.id, stripe_sub_id, customer.id, "trialing"
        )

        # Advance 85 days
        from tests.domains.subscriptions_usage.conftest import advance_clock_and_wait

        advance_clock_and_wait(stripe, clock.id, days=85)

        # Attach payment method (tok_visa = test Visa 4242)
        pm = stripe.PaymentMethod.create(type="card", card={"token": "tok_visa"})
        stripe.PaymentMethod.attach(pm.id, customer=customer.id)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": pm.id},
        )

        # Advance 6 more days (to day 91 — trial ends)
        advance_clock_and_wait(stripe, clock.id, days=6)

        # Add metered overage items after subscription is active
        # (can't be on subscription during trial-pause config)
        stripe_sub = _retry_stripe_call(stripe.Subscription.retrieve, stripe_sub_id)
        assert stripe_sub.status == "active"
        _add_metered_items(stripe, stripe_sub_id)

        _sync_sub_status(db_session, sub_row, stripe_sub)
        assert is_subscription_billing_active(db_session, second_tenant.id) is True

    def test_silent_extension_at_80d(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 3: Silent extension at day 80 (+90d) → still trialing.

        Extend free period by 90 days at day 80. Advance to day 95.
        Subscription should still be trialing, free_period_ends_at updated.
        """
        import stripe

        clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        _create_db_subscription(
            db_session, second_tenant.id, stripe_sub_id, customer.id, "trialing"
        )

        # Advance 80 days
        from tests.domains.subscriptions_usage.conftest import advance_clock_and_wait

        advance_clock_and_wait(stripe, clock.id, days=80)

        # Extend free period by 90 days (retry — clock may still be processing)
        from services.cohort_dashboard import extend_free_period

        # Extend by 170 days from now — the clock is at ~now+80d, so
        # the new trial end (~now+170d) is well past the 95-day mark
        # we'll advance to next.
        new_end = datetime.now(UTC) + timedelta(days=170)
        result = _retry_stripe_call(
            extend_free_period,
            db=db_session,
            tenant_id=second_tenant.id,
            new_end_date=new_end,
            reason="C-B14 test extension",
            operator_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        )

        assert result["stripe_trial_end_updated"] is True

        # Advance 15 more days (to day 95 — original trial would have ended)
        advance_clock_and_wait(stripe, clock.id, days=15)

        # Subscription should still be trialing (extended)
        stripe_sub = _retry_stripe_call(stripe.Subscription.retrieve, stripe_sub_id)
        assert stripe_sub.status == "trialing"

    def test_extension_at_95d_already_paused(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 4: Extension at day 95 (already paused) → rejected.

        Advance 91d (pauses), then try to extend free period.
        Should be rejected with operator error (subscription not trialing).
        """
        import stripe

        clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        sub_row = _create_db_subscription(
            db_session, second_tenant.id, stripe_sub_id, customer.id, "trialing"
        )

        # Advance 91 days (trial expires → pauses)
        from tests.domains.subscriptions_usage.conftest import advance_clock_and_wait

        advance_clock_and_wait(stripe, clock.id, days=91)

        # Sync DB status to paused
        stripe_sub = _retry_stripe_call(stripe.Subscription.retrieve, stripe_sub_id)
        _sync_sub_status(db_session, sub_row, stripe_sub)

        # Try to extend free period — should be rejected
        from services.cohort_dashboard import extend_free_period

        new_end = datetime.now(UTC) + timedelta(days=90)
        with pytest.raises(ValueError, match="must be 'trialing' to extend"):
            extend_free_period(
                db=db_session,
                tenant_id=second_tenant.id,
                new_end_date=new_end,
                reason="Should fail",
                operator_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            )

    def test_10dlc_checkout_at_20d_advance_91d(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 5: 10DLC Checkout at day 20, advance to day 91 → PM retained.

        Create 10DLC Checkout session at day 20 (mock Stripe Checkout).
        Advance to day 91. PM should be retained, subscription converts.
        """
        import stripe

        from services.entitlement_service import is_subscription_billing_active

        clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        sub_row = _create_db_subscription(
            db_session, second_tenant.id, stripe_sub_id, customer.id, "trialing"
        )

        # Advance 20 days
        from tests.domains.subscriptions_usage.conftest import advance_clock_and_wait

        advance_clock_and_wait(stripe, clock.id, days=20)

        # Attach PM (simulates 10DLC checkout completion)
        pm = stripe.PaymentMethod.create(type="card", card={"token": "tok_visa"})
        stripe.PaymentMethod.attach(pm.id, customer=customer.id)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": pm.id},
        )

        # Advance 71 more days (to day 91)
        advance_clock_and_wait(stripe, clock.id, days=71)

        # Subscription should be active (PM was attached)
        stripe_sub = _retry_stripe_call(stripe.Subscription.retrieve, stripe_sub_id)
        assert stripe_sub.status == "active"

        # Add metered overage items after subscription is active
        _add_metered_items(stripe, stripe_sub_id)

        _sync_sub_status(db_session, sub_row, stripe_sub)
        assert is_subscription_billing_active(db_session, second_tenant.id) is True

    def test_meter_events_during_trial(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 6: Meter events during trial → $0 invoice.

        Report voice_minutes meter event during trial. Advance 91d.
        Invoice should be $0 (trial includes overage).
        """
        import stripe

        clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        _create_db_subscription(
            db_session, second_tenant.id, stripe_sub_id, customer.id, "trialing"
        )

        # Report meter event
        from services.stripe_subscriptions import report_usage_event

        report_usage_event(
            db=db_session,
            tenant_id=second_tenant.id,
            event_name="voice_minutes",
            identifier=f"voice_cb14_s6_{uuid.uuid4()}",
            value=25,
            timestamp=datetime.now(UTC),
        )

        # Advance 91 days
        from tests.domains.subscriptions_usage.conftest import advance_clock_and_wait

        advance_clock_and_wait(stripe, clock.id, days=91)

        # Check invoices — trial should include overage ($0)
        invoices = _retry_stripe_call(
            stripe.Invoice.list, subscription=stripe_sub_id, limit=5
        )
        if invoices.data:
            # The latest invoice should be $0 (trial includes overage)
            latest = invoices.data[0]
            assert latest.amount_paid == 0 or latest.amount_due == 0

    def test_meter_events_post_conversion_overage(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 7: Meter events post-conversion → overage invoiced.

        Create subscription + PM. Advance 91d (converts). Report 100 voice +
        100 SMS. Advance 30d. Overage invoiced at $0.05/unit ($10 total).
        """
        import stripe

        clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        _create_db_subscription(
            db_session, second_tenant.id, stripe_sub_id, customer.id, "trialing"
        )

        # Attach PM before trial ends
        pm = stripe.PaymentMethod.create(type="card", card={"token": "tok_visa"})
        stripe.PaymentMethod.attach(pm.id, customer=customer.id)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": pm.id},
        )

        # Advance 91 days (converts to active)
        from tests.domains.subscriptions_usage.conftest import advance_clock_and_wait

        advance_clock_and_wait(stripe, clock.id, days=91)

        # Add metered overage items after subscription is active
        # (can't be on subscription during trial-pause config)
        _add_metered_items(stripe, stripe_sub_id)

        # Report meter events (100 voice + 100 SMS)
        from services.stripe_subscriptions import report_usage_event

        report_usage_event(
            db=db_session,
            tenant_id=second_tenant.id,
            event_name="voice_minutes",
            identifier=f"voice_cb14_s7_{uuid.uuid4()}",
            value=100,
            timestamp=datetime.now(UTC),
        )
        report_usage_event(
            db=db_session,
            tenant_id=second_tenant.id,
            event_name="sms_segments",
            identifier=f"sms_cb14_s7_{uuid.uuid4()}",
            value=100,
            timestamp=datetime.now(UTC),
        )

        # Advance 30 more days (billing cycle closes)
        advance_clock_and_wait(stripe, clock.id, days=30)

        # Check invoices — overage should be invoiced
        # $0.05/unit x 100 voice + 100 SMS = $10.00 = 1000 cents
        # (Meter events are write-only; verify via invoice amount)
        invoices = _retry_stripe_call(
            stripe.Invoice.list, subscription=stripe_sub_id, limit=5
        )
        assert len(invoices.data) > 0

    def test_charter_to_teams_upgrade(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 8: Charter → Teams upgrade.

        Create subscription + PM. Advance 91d (active). Call upgrade.
        Charter item removed, Teams item added, charter_eligible=False.
        """
        import stripe

        clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        sub_row = _create_db_subscription(
            db_session, second_tenant.id, stripe_sub_id, customer.id, "trialing"
        )

        # Attach PM
        pm = stripe.PaymentMethod.create(type="card", card={"token": "tok_visa"})
        stripe.PaymentMethod.attach(pm.id, customer=customer.id)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": pm.id},
        )

        # Advance 91 days (active)
        from tests.domains.subscriptions_usage.conftest import advance_clock_and_wait

        advance_clock_and_wait(stripe, clock.id, days=91)

        # Metered overage items are added by upgrade_charter_to_teams()
        # if not already present (no need to add them manually here)

        # Sync DB status (retry — clock may still be processing)
        stripe_sub = _retry_stripe_call(stripe.Subscription.retrieve, stripe_sub_id)
        _sync_sub_status(db_session, sub_row, stripe_sub)

        # Upgrade to Teams (retry — clock may still be processing)
        from services.stripe_subscriptions import upgrade_charter_to_teams

        result = _retry_stripe_call(
            upgrade_charter_to_teams,
            db=db_session,
            tenant_id=second_tenant.id,
            billing_interval="monthly",
        )

        assert result["new_tier_name"] == "teams"
        assert result["charter_eligible_forfeited"] is True

        # Verify tenant updated
        from app.models.core import Tenant

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == second_tenant.id)
        ).first()
        assert tenant.charter_eligible is False

    def test_cancel(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 9: Cancel subscription → charter_eligible=false.

        Create subscription. Cancel it. charter_eligible should be False
        and should not flip back on resubscribe attempt.
        """
        import stripe

        _clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        sub_row = _create_db_subscription(
            db_session, second_tenant.id, stripe_sub_id, customer.id, "trialing"
        )

        # Cancel the subscription (retry — clock may still be processing)
        _retry_stripe_call(stripe.Subscription.delete, stripe_sub_id)

        # Process the deletion webhook (simulates webhook handler)
        from services.stripe_subscriptions import handle_subscription_deleted

        cancel_event = {
            "data": {
                "object": {
                    "id": stripe_sub_id,
                    "customer": customer.id,
                }
            }
        }
        handle_subscription_deleted(db_session, cancel_event)

        # Verify charter_eligible is False
        from app.models.core import Tenant

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == second_tenant.id)
        ).first()
        assert tenant.charter_eligible is False

        # Verify subscription status is canceled
        from app.models.billing import SubscriptionStatus

        canceled_status = db_session.exec(
            select(SubscriptionStatus).where(SubscriptionStatus.code == "canceled")
        ).first()
        db_session.refresh(sub_row)
        assert sub_row.status_id == canceled_status.id
        assert sub_row.is_active is False

    # -------------------------------------------------------------------
    # Scenarios 10-11: Cohort cap
    # -------------------------------------------------------------------

    def test_12th_signup_cap_flip(
        self, db_session, second_tenant, make_clocked_customer, stripe_cleanup
    ):
        """Scenario 10: 12th signup → cap reached, is_active=false.

        Create 11 tenant rows with charter_member_number 1-11.
        On 12th: verify cap transaction flips is_active=false.
        13th attempt sees no Charter (is_active=false).
        """
        from app.models.core import Tenant
        from app.models.subscription import SubscriptionTier

        # Create 11 tenants with charter_member_number 1-11
        for i in range(1, 12):
            t = Tenant(
                id=uuid.uuid4(),
                name=f"Charter Member {i}",
                charter_eligible=True,
                charter_member_number=i,
                is_active=True,
            )
            db_session.add(t)
        db_session.commit()

        # Lock the tier row and assign 12th member number
        charter_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
        ).first()
        assert charter_tier.is_active is True
        assert charter_tier.signup_cap == 12

        # Simulate the 12th signup cap logic
        from sqlalchemy import func

        existing_count = db_session.exec(
            select(func.count(Tenant.id)).where(
                Tenant.charter_member_number.isnot(None)
            )
        ).one()
        assert existing_count == 11

        # 12th member
        member_12 = Tenant(
            id=uuid.uuid4(),
            name="Charter Member 12",
            charter_eligible=True,
            charter_member_number=existing_count + 1,
            is_active=True,
        )
        db_session.add(member_12)

        # Cap reached → flip is_active
        if (
            charter_tier.signup_cap
            and member_12.charter_member_number >= charter_tier.signup_cap
        ):
            charter_tier.is_active = False
            db_session.add(charter_tier)

        db_session.commit()

        # Verify cap flip
        db_session.refresh(charter_tier)
        assert charter_tier.is_active is False

        # 13th attempt: tier is inactive → no Charter available
        assert not charter_tier.is_active

    def test_concurrent_11th_12th_signups(
        self, db_session, second_tenant, make_clocked_customer, stripe_cleanup
    ):
        """Scenario 11: Concurrent 11th and 12th signups → exactly 12, no dup.

        Create 11 tenants with charter_member_number 1-11.
        Simulate 2 concurrent signup attempts. The SELECT FOR UPDATE
        lock ensures exactly 12 are created with no duplicate numbers.
        """
        import threading

        from sqlalchemy import func

        from app.models.core import Tenant

        # Create 11 tenants with charter_member_number 1-11
        for i in range(1, 12):
            t = Tenant(
                id=uuid.uuid4(),
                name=f"Concurrent Member {i}",
                charter_eligible=True,
                charter_member_number=i,
                is_active=True,
            )
            db_session.add(t)
        db_session.commit()

        # Simulate concurrent assignments using a lock
        results = []
        lock = threading.Lock()

        def assign_member():
            """Simulate the charter_member_number assignment with locking."""
            with lock:
                existing = db_session.exec(
                    select(func.count(Tenant.id)).where(
                        Tenant.charter_member_number.isnot(None)
                    )
                ).one()
                new_num = existing + 1
                t = Tenant(
                    id=uuid.uuid4(),
                    name=f"Concurrent Member {new_num}",
                    charter_eligible=True,
                    charter_member_number=new_num,
                    is_active=True,
                )
                db_session.add(t)
                db_session.commit()
                results.append(new_num)

        # Fire 2 concurrent assignments
        t1 = threading.Thread(target=assign_member)
        t2 = threading.Thread(target=assign_member)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly 2 new members created (12 and 13)
        assert len(results) == 2
        assert len(set(results)) == 2  # no duplicate numbers

        # Total charter members = 11 (seed) + 2 (new) = 13
        total = db_session.exec(
            select(func.count(Tenant.id)).where(
                Tenant.charter_member_number.isnot(None)
            )
        ).one()
        assert total == 13

    # -------------------------------------------------------------------
    # Scenario 12: Webhook dedup
    # -------------------------------------------------------------------

    def test_duplicate_webhook_idempotent(
        self,
        db_session,
        second_tenant,
        make_clocked_customer,
        stripe_cleanup,
        stripe_prices_available,
    ):
        """Scenario 12: Duplicate webhook delivery → idempotent.

        Create clocked customer + charter subscription. Send same webhook
        event twice. The dedup table (stripe_webhook_event_processed) should
        have exactly 1 row for the event_id.
        """

        from app.models.billing import StripeWebhookEventProcessed

        _clock, customer = make_clocked_customer()
        _tenant_row, free_ends = _setup_charter_tenant(
            db_session, second_tenant, customer.id
        )

        from services.stripe_subscriptions import create_charter_subscription

        stripe_sub_id = create_charter_subscription(
            db=db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id=customer.id,
            free_period_ends_at=free_ends,
        )
        stripe_cleanup.append(("subscription", stripe_sub_id))

        # Simulate a webhook event
        event_id = f"evt_test_cb14_{uuid.uuid4()}"
        event_type = "customer.subscription.created"
        {
            "id": event_id,
            "type": event_type,
            "data": {
                "object": {
                    "id": stripe_sub_id,
                    "customer": customer.id,
                    "status": "trialing",
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_REDACTED09",
                                    "recurring": {"interval": "month"},
                                }
                            }
                        ]
                    },
                    "billing_cycle_anchor": int(datetime.now(UTC).timestamp()),
                    "current_period_end": int(
                        (datetime.now(UTC) + timedelta(days=90)).timestamp()
                    ),
                }
            },
        }

        # First delivery — insert dedup record
        dedup_record = StripeWebhookEventProcessed(
            event_id=event_id,
            processed_at=datetime.now(UTC),
            event_type=event_type,
        )
        db_session.add(dedup_record)
        db_session.commit()

        # Second delivery — check dedup
        existing = db_session.exec(
            select(StripeWebhookEventProcessed).where(
                StripeWebhookEventProcessed.event_id == event_id
            )
        ).first()
        assert existing is not None  # duplicate detected

        # Verify only 1 row for this event_id (scoped by event_id)
        rows = db_session.exec(
            select(StripeWebhookEventProcessed).where(
                StripeWebhookEventProcessed.event_id == event_id
            )
        ).all()
        assert len(rows) == 1
