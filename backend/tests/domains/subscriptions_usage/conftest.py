"""
C-B14 — Stripe test-clock conftest fixtures for the subscriptions_usage domain.

Provides fixtures for Stripe test-mode integration tests:
  - stripe_test_key: Returns sk_test_... or skips if not configured
  - stripe_cleanup: Tracks and cleans up Stripe test objects after each test
  - make_clocked_customer: Creates a Stripe TestClock + Customer

These fixtures are only used by tests marked @pytest.mark.requires_stripe.
"""

import time
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture(scope="session")
def stripe_test_key():
    """Return sk_test_... key or skip if not available.

    Same pattern as test_invoice_stripe.py:_get_stripe_key().
    """
    from core.config import settings

    key = getattr(settings, "STRIPE_SECRET_KEY", None)
    if not key or not key.startswith("sk_test_"):
        pytest.skip(
            "Real Stripe test-mode key not configured — "
            "set STRIPE_SECRET_KEY to a real sk_test_... key to run Stripe scenarios"
        )
    return key


@pytest.fixture
def stripe_cleanup():
    """Track and clean up Stripe test objects after each test.

    Usage:
        def test_something(self, stripe_cleanup):
            stripe_cleanup.append(('customer', 'cus_...'))
            ...

    After the test yields, all registered objects are deleted best-effort.
    Order: subscriptions first, then customers, then clocks.
    """
    registry: list[tuple[str, str]] = []
    yield registry

    import stripe

    # Sort so subscriptions are deleted before customers, clocks last
    priority = {"subscription": 0, "customer": 1, "clock": 2}
    sorted_registry = sorted(registry, key=lambda x: priority.get(x[0], 99))

    for obj_type, obj_id in reversed(sorted_registry):
        try:
            if obj_type == "clock":
                stripe.test_helpers.TestClock.delete(obj_id)
            elif obj_type == "subscription":
                try:
                    stripe.Subscription.delete(obj_id, cancel_at_period_end=False)
                except Exception:
                    # Already canceled or deleted
                    pass
            elif obj_type == "customer":
                stripe.Customer.delete(obj_id)
        except Exception:
            pass  # best-effort

    # Wait for Stripe to finish processing deletions before the next test
    # starts — concurrent clock operations cause RateLimitError.
    time.sleep(5)


@pytest.fixture
def make_clocked_customer(stripe_test_key, stripe_cleanup):
    """Create a Stripe TestClock + Customer. Returns (clock, customer).

    The clock is frozen at the current time. The customer is created on that
    clock. Both are registered for cleanup.
    """
    import stripe

    stripe.api_key = stripe_test_key

    def _create(email_suffix: str | None = None):
        now = int(datetime.now(UTC).timestamp())
        clock = stripe.test_helpers.TestClock.create(frozen_time=now)
        suffix = email_suffix or clock.id[:8]
        customer = stripe.Customer.create(
            email=f"cb14-test-{suffix}@pilot.local",
            test_clock=clock.id,
        )
        stripe_cleanup.append(("clock", clock.id))
        stripe_cleanup.append(("customer", customer.id))
        return clock, customer

    return _create


@pytest.fixture
def stripe_prices_available(stripe_test_key):
    """Verify that the Charter price exists in the Stripe test account.

    Skips the test if the price is not found (e.g., test data was purged
    or bootstrap script has not been run). This prevents false failures
    when the Stripe test account is not fully set up.
    """
    import stripe

    stripe.api_key = stripe_test_key
    from core.stripe_config import get_stripe_ids

    ids = get_stripe_ids()
    charter_price_id = ids["prices"]["price_charter_monthly"]

    try:
        price = stripe.Price.retrieve(charter_price_id)
        if not price or not price.active:
            pytest.skip(
                f"Charter price {charter_price_id} is not active in the Stripe "
                f"test account — run: python scripts/stripe_bootstrap.py --mode test"
            )
    except Exception:
        pytest.skip(
            f"Charter price {charter_price_id} not found in the Stripe test "
            f"account — run: python scripts/stripe_bootstrap.py --mode test"
        )

    return ids


def advance_clock_and_wait(stripe, clock_id: str, days: int, sleep_seconds: int = 5):
    """Advance a test clock by N days. Sleeps first for async meter processing.

    C-SPIKE-1 Q#4 resolution: meter events are processed asynchronously.
    The sleep allows pending meter events to be processed before the clock
    advances, ensuring invoice amounts are correct.

    Stripe limits test clock advancement to 2 intervals at a time (60 days
    for a monthly subscription). This function automatically advances in
    increments of ≤59 days to stay within the limit.
    """
    time.sleep(sleep_seconds)

    # Stripe limits advancement to 2 intervals (60 days for monthly).
    # Advance in increments of 59 days to stay safely within the limit.
    # Retrieve the clock's current frozen time and advance from there
    # (not from datetime.now — the clock may have been advanced by a
    # previous call in the same test).
    max_increment = 59
    clock = stripe.test_helpers.TestClock.retrieve(clock_id)
    current_frozen = datetime.fromtimestamp(clock.frozen_time, tz=UTC)
    target_time = current_frozen + timedelta(days=days)
    total_delta = target_time - current_frozen
    total_days = total_delta.days

    advanced = 0
    while advanced < total_days:
        step = min(total_days - advanced, max_increment)
        advanced += step
        new_time = int((current_frozen + timedelta(days=advanced)).timestamp())
        # Retry the advance call — Stripe may still be processing a
        # previous advancement ("Test clock advancement underway").
        # Up to 8 retries with 15s delay = 2 min max wait.
        for attempt in range(8):
            try:
                stripe.test_helpers.TestClock.advance(clock_id, frozen_time=new_time)
                break
            except Exception as e:
                if "advancement underway" in str(e) and attempt < 7:
                    time.sleep(15)
                    continue
                raise
        # Wait for the clock advancement to complete before next step
        # or before returning (Stripe needs time to process webhooks/status).
        time.sleep(10)
