"""
C-B14-FIX: Post-C-B14 Stripe hardening follow-ups.

Covers:
    - Task 1: webhook metered-item provisioning on trial→active auto-conversion
      (Charter fallback branch + normal tier branch, out-of-order guard, failure swallow)
    - Task 3: stripe_bootstrap.py --force flag bypasses JSON cache
    - Task 4: mode_audit() meters-loop survives empty prices list

Domain: subscriptions_usage (PRD §3.11)
"""

import logging
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]

_FREE_PERIOD_END = datetime(2026, 11, 9, tzinfo=UTC)


def _unique_sub_id() -> str:
    return f"sub_test_cb14fix_{uuid.uuid4().hex[:16]}"


def _trialing_status_id(db):
    from app.models.billing import SubscriptionStatus

    status = db.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == "trialing")
    ).first()
    assert status is not None, "subscription_status 'trialing' must be seeded"
    return status.id


def _active_status_id(db):
    from app.models.billing import SubscriptionStatus

    status = db.exec(
        select(SubscriptionStatus)
        .where(SubscriptionStatus.code == "active")
        .where(SubscriptionStatus.is_billing_active == True)
    ).first()
    assert status is not None, "subscription_status 'active' must be seeded"
    return status.id


def _row_for_psp_sub_id(db, psp_subscription_id: str):
    from app.models.billing import Subscription

    return db.exec(
        select(Subscription).where(
            Subscription.psp_subscription_id == psp_subscription_id
        )
    ).first()


def _mock_stripe_ids():
    return {
        "prices": {
            "price_voice_overage": "price_voice_test_cb14fix",
            "price_sms_overage": "price_sms_test_cb14fix",
        }
    }


def _make_sub_with_items(price_ids: list[str], trial_settings=None):
    """Build a MagicMock subscription retrieve result with given item price IDs."""
    mock_sub = MagicMock()
    mock_sub.status = "active"
    items_data = []
    for pid in price_ids:
        item = MagicMock()
        item.__getitem__ = MagicMock(
            side_effect=lambda key, pid=pid: {"price": {"id": pid}}[key]
        )
        items_data.append(item)
    mock_sub.__getitem__ = MagicMock(
        side_effect=lambda key: {"items": {"data": items_data}}[key]
    )
    if trial_settings is not None:
        mock_sub.trial_settings = trial_settings
    else:
        mock_sub.trial_settings = None
    return mock_sub


# ─────────────────────────────────────────────────────────────────────────────
# Task 1 — Charter fallback branch
# ─────────────────────────────────────────────────────────────────────────────


class TestCharterAutoConversion:
    """Charter fallback branch: payload status='active' → status flip + metered items."""

    def test_charter_auto_conversion_flips_status_and_adds_metered(
        self, db_session, second_tenant
    ):
        """Payload status='active' → local row status_id resolves to 'active'
        AND _add_metered_overage_items invoked (Subscription.modify called
        with both overage price IDs)."""
        from services.stripe_subscriptions import handle_subscription_created

        second_tenant.stripe_customer_id = "cus_cb14fix_charter_active"
        second_tenant.free_period_ends_at = _FREE_PERIOD_END
        db_session.add(second_tenant)
        db_session.commit()

        sub_id = _unique_sub_id()
        event = {
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": "cus_cb14fix_charter_active",
                    "status": "active",
                    "metadata": {"tier_code": "charter"},
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": f"price_unknown_{uuid.uuid4().hex[:8]}",
                                    "recurring": {"interval": "month"},
                                }
                            }
                        ]
                    },
                }
            }
        }

        # Pre-write the trialing row (simulating create_charter_subscription
        # having already written it at signup time)
        from services.stripe_subscriptions import _write_local_charter_subscription_row

        _write_local_charter_subscription_row(
            db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id="cus_cb14fix_charter_active",
            stripe_subscription_id=sub_id,
            free_period_ends_at=_FREE_PERIOD_END,
        )

        # Mock: retrieve returns sub with NO metered items (both missing)
        mock_retrieved = _make_sub_with_items(
            [f"price_unknown_{uuid.uuid4().hex[:8]}"],
            trial_settings={"end_behavior": {"missing_payment_method": "pause"}},
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids") as mock_ids,
        ):
            mock_stripe = MagicMock()
            mock_stripe.Subscription.retrieve.return_value = mock_retrieved
            mock_client.return_value = mock_stripe
            mock_ids.return_value = _mock_stripe_ids()

            handle_subscription_created(db_session, event)

        # Verify local row status flipped to active
        row = _row_for_psp_sub_id(db_session, sub_id)
        assert row is not None
        assert row.status_id == _active_status_id(db_session)

        # Verify Subscription.modify called with both overage price IDs
        mock_stripe.Subscription.modify.assert_called_once()
        modify_kwargs = mock_stripe.Subscription.modify.call_args.kwargs
        modify_items = modify_kwargs["items"]
        added_prices = [item["price"] for item in modify_items]
        assert "price_voice_test_cb14fix" in added_prices
        assert "price_sms_test_cb14fix" in added_prices
        # trial_settings cleared to cancel
        assert modify_kwargs["trial_settings"] == {
            "end_behavior": {"missing_payment_method": "cancel"}
        }

    def test_charter_trialing_unchanged(self, db_session, second_tenant):
        """Payload status='trialing' → no Stripe client acquired, no modify;
        local status stays trialing."""
        from services.stripe_subscriptions import handle_subscription_created

        second_tenant.stripe_customer_id = "cus_cb14fix_charter_trialing"
        second_tenant.free_period_ends_at = _FREE_PERIOD_END
        db_session.add(second_tenant)
        db_session.commit()

        sub_id = _unique_sub_id()
        event = {
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": "cus_cb14fix_charter_trialing",
                    "status": "trialing",
                    "metadata": {"tier_code": "charter"},
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": f"price_unknown_{uuid.uuid4().hex[:8]}",
                                    "recurring": {"interval": "month"},
                                }
                            }
                        ]
                    },
                }
            }
        }

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids") as mock_ids,
        ):
            mock_stripe = MagicMock()
            mock_client.return_value = mock_stripe
            mock_ids.return_value = _mock_stripe_ids()

            handle_subscription_created(db_session, event)

        # No Stripe client acquired for trialing payload
        mock_stripe.Subscription.modify.assert_not_called()

        # Local row stays trialing
        row = _row_for_psp_sub_id(db_session, sub_id)
        assert row is not None
        assert row.status_id == _trialing_status_id(db_session)

    def test_out_of_order_guard_no_demotion(self, db_session, second_tenant):
        """D5: local row already 'active' + payload status='trialing' →
        no demotion (status remains active), info-logged."""
        from services.stripe_subscriptions import handle_subscription_created

        second_tenant.stripe_customer_id = "cus_cb14fix_ooo"
        second_tenant.free_period_ends_at = _FREE_PERIOD_END
        db_session.add(second_tenant)
        db_session.commit()

        sub_id = _unique_sub_id()

        # Pre-write the row as ACTIVE (simulating a prior auto-conversion)
        from app.models.billing import Subscription

        sub_row = Subscription(
            id=uuid.uuid4(),
            tenant_id=second_tenant.id,
            product_plan_code="charter_plan",
            status_id=_active_status_id(db_session),
            quantity_seats=1,
            psp_provider="stripe",
            psp_subscription_id=sub_id,
            psp_customer_id="cus_cb14fix_ooo",
            billing_interval="monthly",
            is_active=True,
            trial_ends_at=_FREE_PERIOD_END,
            renews_at=_FREE_PERIOD_END,
        )
        db_session.add(sub_row)
        db_session.commit()

        event = {
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": "cus_cb14fix_ooo",
                    "status": "trialing",
                    "metadata": {"tier_code": "charter"},
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": f"price_unknown_{uuid.uuid4().hex[:8]}",
                                    "recurring": {"interval": "month"},
                                }
                            }
                        ]
                    },
                }
            }
        }

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids") as mock_ids,
        ):
            mock_stripe = MagicMock()
            mock_client.return_value = mock_stripe
            mock_ids.return_value = _mock_stripe_ids()

            handle_subscription_created(db_session, event)

        # No modify called (stale event skipped)
        mock_stripe.Subscription.modify.assert_not_called()

        # Status remains active (no demotion)
        db_session.refresh(sub_row)
        assert sub_row.status_id == _active_status_id(db_session)


# ─────────────────────────────────────────────────────────────────────────────
# Task 1 — Normal tier branch
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalTierMeteredItems:
    """Normal tier branch: status='active' → metered items ensured."""

    def test_normal_path_idempotent_items_present(self, db_session, second_tenant):
        """Tier matched by price ID, status='active', retrieve shows both
        overage prices already present → no Subscription.modify call."""
        from app.models.subscription import SubscriptionTier
        from services.stripe_subscriptions import handle_subscription_created

        # Get the starter tier's monthly price ID
        starter_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter_tier and starter_tier.stripe_price_id_monthly

        price_id = starter_tier.stripe_price_id_monthly
        voice_price = "price_voice_test_cb14fix"
        sms_price = "price_sms_test_cb14fix"

        second_tenant.stripe_customer_id = "cus_cb14fix_normal_idem"
        db_session.add(second_tenant)
        db_session.commit()

        sub_id = _unique_sub_id()
        event = {
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": "cus_cb14fix_normal_idem",
                    "status": "active",
                    "billing_cycle_anchor": 1700000000,
                    "current_period_end": 1730000000,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": price_id,
                                    "recurring": {"interval": "month"},
                                }
                            }
                        ]
                    },
                }
            }
        }

        # Retrieve returns sub with all 3 items (starter + both overages)
        mock_retrieved = _make_sub_with_items(
            [price_id, voice_price, sms_price], trial_settings=None
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids") as mock_ids,
        ):
            mock_stripe = MagicMock()
            mock_stripe.Subscription.retrieve.return_value = mock_retrieved
            mock_client.return_value = mock_stripe
            mock_ids.return_value = _mock_stripe_ids()

            handle_subscription_created(db_session, event)

        # No modify called — items already present
        mock_stripe.Subscription.modify.assert_not_called()

    def test_normal_path_adds_missing_items(self, db_session, second_tenant):
        """Same but metered items absent → modify called once with both price IDs."""
        from app.models.subscription import SubscriptionTier
        from services.stripe_subscriptions import handle_subscription_created

        starter_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter_tier and starter_tier.stripe_price_id_monthly

        price_id = starter_tier.stripe_price_id_monthly

        second_tenant.stripe_customer_id = "cus_cb14fix_normal_add"
        db_session.add(second_tenant)
        db_session.commit()

        sub_id = _unique_sub_id()
        event = {
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": "cus_cb14fix_normal_add",
                    "status": "active",
                    "billing_cycle_anchor": 1700000000,
                    "current_period_end": 1730000000,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": price_id,
                                    "recurring": {"interval": "month"},
                                }
                            }
                        ]
                    },
                }
            }
        }

        # Retrieve returns sub with ONLY the starter price (overages missing)
        mock_retrieved = _make_sub_with_items([price_id], trial_settings=None)

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids") as mock_ids,
        ):
            mock_stripe = MagicMock()
            mock_stripe.Subscription.retrieve.return_value = mock_retrieved
            mock_client.return_value = mock_stripe
            mock_ids.return_value = _mock_stripe_ids()

            handle_subscription_created(db_session, event)

        # Modify called once with both overage price IDs
        mock_stripe.Subscription.modify.assert_called_once()
        modify_kwargs = mock_stripe.Subscription.modify.call_args.kwargs
        modify_items = modify_kwargs["items"]
        added_prices = [item["price"] for item in modify_items]
        assert "price_voice_test_cb14fix" in added_prices
        assert "price_sms_test_cb14fix" in added_prices

    def test_metered_failure_swallowed(self, db_session, second_tenant, caplog):
        """D6: force Subscription.modify to raise → handler completes without
        raising, local row still upserted, logger.error emitted."""
        from app.models.subscription import SubscriptionTier
        from services.stripe_subscriptions import handle_subscription_created

        starter_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter_tier and starter_tier.stripe_price_id_monthly

        price_id = starter_tier.stripe_price_id_monthly

        second_tenant.stripe_customer_id = "cus_cb14fix_normal_fail"
        db_session.add(second_tenant)
        db_session.commit()

        sub_id = _unique_sub_id()
        event = {
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": "cus_cb14fix_normal_fail",
                    "status": "active",
                    "billing_cycle_anchor": 1700000000,
                    "current_period_end": 1730000000,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": price_id,
                                    "recurring": {"interval": "month"},
                                }
                            }
                        ]
                    },
                }
            }
        }

        mock_retrieved = _make_sub_with_items([price_id], trial_settings=None)

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids") as mock_ids,
        ):
            mock_stripe = MagicMock()
            mock_stripe.Subscription.retrieve.return_value = mock_retrieved
            # modify raises!
            mock_stripe.Subscription.modify.side_effect = RuntimeError("stripe boom")
            mock_client.return_value = mock_stripe
            mock_ids.return_value = _mock_stripe_ids()

            with caplog.at_level(logging.ERROR, logger="services.stripe_subscriptions"):
                # Must NOT raise
                handle_subscription_created(db_session, event)

        # Local row was still upserted
        row = _row_for_psp_sub_id(db_session, sub_id)
        assert row is not None
        assert row.is_active is True

        # logger.error emitted
        assert any(
            "failed to add metered overage" in rec.message.lower()
            for rec in caplog.records
        )


# ─────────────────────────────────────────────────────────────────────────────
# Task 3 — --force flag bypasses JSON cache
# ─────────────────────────────────────────────────────────────────────────────


class TestForceFlagBypassesCache:
    """--force bypasses the JSON cache half; live Stripe lookup always runs."""

    def test_force_chooses_live_id_over_stale_cache(self):
        """With force=True, _load_existing_ids returns a stale product ID,
        _find_product_by_pilot_key returns the live ID → mode_create picks
        the live ID (cache bypassed)."""
        from scripts.stripe_bootstrap import mode_create

        stale_id = "prod_stale_cached"
        live_id = "prod_live_real"

        with (
            patch("scripts.stripe_bootstrap._load_existing_ids") as mock_load,
            patch(
                "scripts.stripe_bootstrap._find_product_by_pilot_key"
            ) as mock_find_prod,
            patch("scripts.stripe_bootstrap._find_meter_by_key") as mock_find_meter,
            patch(
                "scripts.stripe_bootstrap._find_price_by_pilot_key"
            ) as mock_find_price,
            patch("scripts.stripe_bootstrap._save_ids"),
        ):
            mock_load.return_value = {
                "mode": "test",
                "products": {"prod_starter": stale_id},
                "meters": {},
                "prices": {},
            }
            mock_find_prod.return_value = live_id
            mock_find_meter.return_value = "meter_live"
            mock_find_price.return_value = "price_live"

            ids = mode_create("test", dry_run=True, force=True)

        # With force=True, the stale cached ID is ignored; live ID wins
        assert ids["products"]["prod_starter"] == live_id

    def test_no_force_chooses_stale_cache(self):
        """With force=False (default), the stale cached ID wins over the
        live lookup (existing behavior preserved)."""
        from scripts.stripe_bootstrap import mode_create

        stale_id = "prod_stale_cached"
        live_id = "prod_live_real"

        with (
            patch("scripts.stripe_bootstrap._load_existing_ids") as mock_load,
            patch(
                "scripts.stripe_bootstrap._find_product_by_pilot_key"
            ) as mock_find_prod,
            patch("scripts.stripe_bootstrap._find_meter_by_key") as mock_find_meter,
            patch(
                "scripts.stripe_bootstrap._find_price_by_pilot_key"
            ) as mock_find_price,
            patch("scripts.stripe_bootstrap._save_ids"),
        ):
            mock_load.return_value = {
                "mode": "test",
                "products": {"prod_starter": stale_id},
                "meters": {},
                "prices": {},
            }
            mock_find_prod.return_value = live_id
            mock_find_meter.return_value = "meter_live"
            mock_find_price.return_value = "price_live"

            ids = mode_create("test", dry_run=True, force=False)

        # With force=False, stale cached ID wins
        assert ids["products"]["prod_starter"] == stale_id


# ─────────────────────────────────────────────────────────────────────────────
# Task 4 — mode_audit() meters-loop survives empty prices
# ─────────────────────────────────────────────────────────────────────────────


class TestAuditEmptyPrices:
    """mode_audit() must not crash with UnboundLocalError when the prices
    list is empty but meters exist."""

    def test_audit_survives_empty_prices(self, capsys):
        """Patch _list_all_products → [], _list_all_prices → [],
        _list_all_meters → one fake meter. mode_audit returns normally
        (today: UnboundLocalError) and logs the meter line."""
        from scripts.stripe_bootstrap import mode_audit

        fake_meter = MagicMock()
        fake_meter.id = "mtr_test_fake"
        fake_meter.event_name = "voice_minutes"
        fake_meter.display_name = "Voice AI minutes"
        fake_meter.status = "active"

        with (
            patch("scripts.stripe_bootstrap._list_all_products", return_value=[]),
            patch("scripts.stripe_bootstrap._list_all_prices", return_value=[]),
            patch(
                "scripts.stripe_bootstrap._list_all_meters", return_value=[fake_meter]
            ),
            patch(
                "scripts.stripe_bootstrap._find_product_by_pilot_key", return_value=None
            ),
            patch("scripts.stripe_bootstrap._find_meter_by_key", return_value=None),
            patch(
                "scripts.stripe_bootstrap._find_price_by_pilot_key", return_value=None
            ),
        ):
            # Must not raise UnboundLocalError
            mode_audit("test", dry_run=False)

        captured = capsys.readouterr()
        # Meter line logged without crashing
        assert "voice_minutes" in captured.err
