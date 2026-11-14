#!/usr/bin/env python3
"""Stripe Bootstrap Script — creates/adopts Products, Prices, and Meters.

Batch C-B3. Manages all Stripe objects for the Pilot subscription billing model:
3 Products, 9 Prices, 2 Billing Meters. Idempotent — safe to re-run.

Usage:
    # AUDIT — read-only report of existing Stripe objects vs. what the script
    # would create. Classifies each as managed (has pilot_key) or orphaned.
    python scripts/stripe_bootstrap.py --mode test --audit

    # ADOPT-EXISTING — add metadata.pilot_key to existing manually-created
    # objects (Pilot Starter/Teams products + their prices). No new objects.
    python scripts/stripe_bootstrap.py --mode test --adopt-existing

    # CREATE (default) — create missing objects. Idempotent via pilot_key lookup.
    python scripts/stripe_bootstrap.py --mode test

    # UPDATE-DB — write generated price IDs to subscription_tier columns.
    python scripts/stripe_bootstrap.py --mode test --update-db

    # MIGRATE-PRICES — detect amount changes, create new prices, archive old.
    # Excludes price-locked tiers (Charter). Updates JSON file + DB.
    python scripts/stripe_bootstrap.py --mode test --migrate-prices

    # DRY-RUN — show what would happen without calling Stripe API.
    python scripts/stripe_bootstrap.py --mode test --dry-run

    # LIVE — requires explicit confirmation (creates in production account).
    python scripts/stripe_bootstrap.py --mode live --i-am-sure

References:
    - dev-docs/architecture-design/batch-designs/batch-c-b3-design.md
    - dev-docs/integrations/stripe/stripe-ops-runbook.md
    - dev-docs/integrations/stripe/stripe-pricing-config.md (superseded — historical reference)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import stripe

# Pin API version — legacy usage-records billing removed; metered prices
# must reference a Billing Meter.
stripe.api_version = "2025-03-31.basil"

# ---------------------------------------------------------------------------
# Object definitions — the source of truth for what should exist
# ---------------------------------------------------------------------------

PRODUCTS: dict[str, dict] = {
    "prod_starter": {
        "name": "Pilot for Trades — Starter",
        "description": (
            "Field management for solo contractors and small crews — Voice AI, "
            "job management, invoicing, QuickBooks sync. 5 schedule lanes, 90 "
            "Voice AI min/mo, 100 SMS segments/mo."
        ),
        "metadata": {
            "pilot_key": "prod_starter",
            "tier_name": "starter",
            "product_plan_code": "starter_plan",
        },
    },
    "prod_teams": {
        "name": "Pilot for Trades — Teams",
        "description": (
            "Full team operations for 6-20 employee shops - all Starter features "
            "plus 20 schedule lanes, 300 Voice AI min/mo, 500 SMS segments/mo, "
            "recurring jobs, and live dispatcher GPS."
        ),
        "metadata": {
            "pilot_key": "prod_teams",
            "tier_name": "teams",
            "product_plan_code": "teams_plan",
        },
    },
    "prod_passthrough": {
        "name": "Carrier fees (pass-through)",
        "description": (
            "Pass-through product for carrier fees (10DLC registration, SMS "
            "segment costs). Used for pass-through charges, not subscription tiers."
        ),
        "metadata": {
            "pilot_key": "prod_passthrough",
        },
    },
}

METERS: dict[str, dict] = {
    "meter_voice_minutes": {
        "display_name": "Voice AI minutes",
        "event_name": "voice_minutes",
        "default_aggregation": {"formula": "sum"},
        "customer_mapping": {
            "type": "by_id",
            "event_payload_key": "stripe_customer_id",
        },
        "value_settings": {"event_payload_key": "value"},
    },
    "meter_sms_segments": {
        "display_name": "SMS segments",
        "event_name": "sms_segments",
        "default_aggregation": {"formula": "sum"},
        "customer_mapping": {
            "type": "by_id",
            "event_payload_key": "stripe_customer_id",
        },
        "value_settings": {"event_payload_key": "value"},
    },
}

# Prices — keyed by pilot_key. Each references a product by pilot_key.
# Pricing decision 2026-08-04: whole-dollar amounts matching existing Stripe
# prices, so --migrate-prices is a no-op on first run (available for future use).
PRICES: dict[str, dict] = {
    "price_charter_monthly": {
        "product_key": "prod_starter",
        "currency": "usd",
        "unit_amount": 4900,  # $49.00/mo
        "recurring": {"interval": "month", "usage_type": "licensed"},
        "metadata": {
            "pilot_key": "price_charter_monthly",
            "tier_name": "charter",
            "price_locked": "true",
            "cohort": "charter_1",
        },
    },
    "price_starter_monthly": {
        "product_key": "prod_starter",
        "currency": "usd",
        "unit_amount": 5900,  # $59.00/mo
        "recurring": {"interval": "month", "usage_type": "licensed"},
        "metadata": {
            "pilot_key": "price_starter_monthly",
            "tier_name": "starter",
            "billing_interval": "monthly",
        },
    },
    "price_starter_annual": {
        "product_key": "prod_starter",
        "currency": "usd",
        "unit_amount": 58800,  # $588.00/yr
        "recurring": {"interval": "year", "usage_type": "licensed"},
        "metadata": {
            "pilot_key": "price_starter_annual",
            "tier_name": "starter",
            "billing_interval": "annual",
        },
    },
    "price_teams_monthly": {
        "product_key": "prod_teams",
        "currency": "usd",
        "unit_amount": 17900,  # $179.00/mo
        "recurring": {"interval": "month", "usage_type": "licensed"},
        "metadata": {
            "pilot_key": "price_teams_monthly",
            "tier_name": "teams",
            "billing_interval": "monthly",
        },
    },
    "price_teams_annual": {
        "product_key": "prod_teams",
        "currency": "usd",
        "unit_amount": 178800,  # $1,788.00/yr
        "recurring": {"interval": "year", "usage_type": "licensed"},
        "metadata": {
            "pilot_key": "price_teams_annual",
            "tier_name": "teams",
            "billing_interval": "annual",
        },
    },
    "price_voice_overage": {
        "product_key": "prod_starter",
        "currency": "usd",
        "unit_amount": 5,  # $0.05/min
        "recurring": {
            "interval": "month",
            "usage_type": "metered",
            "meter_key": "meter_voice_minutes",
        },
        "metadata": {
            "pilot_key": "price_voice_overage",
        },
    },
    "price_sms_overage": {
        "product_key": "prod_starter",
        "currency": "usd",
        "unit_amount": 5,  # $0.05/segment
        "recurring": {
            "interval": "month",
            "usage_type": "metered",
            "meter_key": "meter_sms_segments",
        },
        "metadata": {
            "pilot_key": "price_sms_overage",
        },
    },
    "price_lane_addon_1": {
        "product_key": "prod_starter",
        "currency": "usd",
        "unit_amount": 1000,  # $10.00/mo
        "recurring": {"interval": "month", "usage_type": "licensed"},
        "metadata": {
            "pilot_key": "price_lane_addon_1",
            "addon_type": "schedule_lane",
            "lane_count": "1",
        },
    },
    "price_lane_addon_5": {
        "product_key": "prod_starter",
        "currency": "usd",
        "unit_amount": 4000,  # $40.00/mo
        "recurring": {"interval": "month", "usage_type": "licensed"},
        "metadata": {
            "pilot_key": "price_lane_addon_5",
            "addon_type": "schedule_lane",
            "lane_count": "5",
        },
    },
}

# Existing objects to adopt (lookup_key → pilot_key).
# Products are looked up by name; prices by their existing lookup_key metadata.
ADOPTION_MAP: dict[str, dict] = {
    # Products: lookup by name
    "Pilot Starter": {"type": "product", "pilot_key": "prod_starter"},
    "Pilot Teams": {"type": "product", "pilot_key": "prod_teams"},
    # Prices: lookup by lookup_key metadata
    "pilot_starter_monthly": {
        "type": "price",
        "pilot_key": "price_starter_monthly",
    },
    "pilot_starter_annual": {
        "type": "price",
        "pilot_key": "price_starter_annual",
    },
    "pilot_teams_monthly": {
        "type": "price",
        "pilot_key": "price_teams_monthly",
    },
    "pilot_teams_annual": {
        "type": "price",
        "pilot_key": "price_teams_annual",
    },
}

# Tier → price key mapping for --update-db mode.
# Maps subscription_tier.tier_name to the price keys in PRICES.
TIER_PRICE_MAP: dict[str, dict[str, str | None]] = {
    "charter": {"monthly": "price_charter_monthly", "annual": None},
    "starter": {
        "monthly": "price_starter_monthly",
        "annual": "price_starter_annual",
    },
    "teams": {
        "monthly": "price_teams_monthly",
        "annual": "price_teams_annual",
    },
    # trial and founders have no Stripe prices (free tiers)
    "trial": {"monthly": None, "annual": None},
    "founders": {"monthly": None, "annual": None},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent


def _log(msg: str) -> None:
    """Print a timestamped log line to stderr."""
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr)


def _resolve_api_key(mode: str, i_am_sure: bool) -> str:
    """Resolve the Stripe API key for the given mode. Enforces live guard."""
    if mode == "test":
        key = os.environ.get("STRIPE_SECRET_KEY", "")
        if not key.startswith("sk_test_"):
            _log(
                "ERROR: STRIPE_SECRET_KEY env var must be a sk_test_... key "
                f"for test mode (got: {key[:12]!r}...)."
            )
            sys.exit(1)
        return key

    if mode == "live":
        if not i_am_sure:
            _log(
                "ERROR: Live mode requires --i-am-sure flag to prevent "
                "accidental production changes."
            )
            sys.exit(1)
        key = os.environ.get("STRIPE_LIVE_SECRET_KEY", "")
        if not key.startswith("sk_live_"):
            _log(
                "ERROR: STRIPE_LIVE_SECRET_KEY env var must be a sk_live_... "
                f"key for live mode (got: {key[:12]!r}...)."
            )
            sys.exit(1)
        return key

    _log(f"ERROR: Invalid mode {mode!r}. Use 'test' or 'live'.")
    sys.exit(1)


def _output_path(mode: str) -> Path:
    """Return the path to the stripe_ids.{mode}.json file."""
    return SCRIPTS_DIR / f"stripe_ids.{mode}.json"


def _load_existing_ids(mode: str) -> dict:
    """Load the existing stripe_ids.{mode}.json if present, else empty skeleton."""
    path = _output_path(mode)
    if path.exists():
        return json.loads(path.read_text())
    return {
        "mode": mode,
        "created_at": None,
        "api_version": stripe.api_version,
        "products": {},
        "meters": {},
        "prices": {},
    }


def _save_ids(mode: str, ids: dict) -> None:
    """Write the stripe_ids.{mode}.json file."""
    ids["mode"] = mode
    ids["api_version"] = stripe.api_version
    ids["created_at"] = datetime.now(UTC).isoformat()
    path = _output_path(mode)
    path.write_text(json.dumps(ids, indent=2, sort_keys=False) + "\n")
    _log(f"Wrote {path}")


# ---------------------------------------------------------------------------
# Stripe lookup helpers
# ---------------------------------------------------------------------------


def _list_all_products() -> list:
    """List all products in the Stripe account (auto-paginate)."""
    return list(stripe.Product.list(limit=100).auto_paging_iter())


def _meta(obj, key: str, default=None):
    """Safely read a metadata key from a StripeObject.

    StripeObject does not support dict-style .get(); metadata is a nested
    StripeObject. This helper normalizes access via .to_dict().
    """
    metadata = getattr(obj, "metadata", None)
    if metadata is None:
        return default
    if hasattr(metadata, "to_dict"):
        return metadata.to_dict().get(key, default)
    return default


def _metadata_to_dict(obj) -> dict:
    """Convert a StripeObject's metadata to a plain dict.

    dict(StripeObject) does not work as expected; use .to_dict() instead.
    """
    metadata = getattr(obj, "metadata", None)
    if metadata is None:
        return {}
    if hasattr(metadata, "to_dict"):
        return metadata.to_dict()
    return {}


def _list_all_prices() -> list:
    """List all prices in the Stripe account (auto-paginate)."""
    return list(stripe.Price.list(limit=100).auto_paging_iter())


def _list_all_meters() -> list:
    """List all billing meters in the Stripe account (auto-paginate)."""
    return list(stripe.billing.Meter.list(limit=100).auto_paging_iter())


def _find_product_by_pilot_key(pilot_key: str) -> str | None:
    """Find a product by metadata.pilot_key. Returns product ID or None."""
    for prod in _list_all_products():
        if _meta(prod, "pilot_key") == pilot_key:
            return prod.id
    return None


def _find_price_by_pilot_key(pilot_key: str) -> str | None:
    """Find a price by metadata.pilot_key. Returns price ID or None."""
    for price in _list_all_prices():
        if _meta(price, "pilot_key") == pilot_key:
            return price.id
    return None


def _find_meter_by_key(meter_key: str) -> str | None:
    """Find a billing meter by event_name (meters don't support metadata).

    Looks up the event_name from the METERS config and finds the matching meter.
    Only matches active meters — deactivated meters cannot be attached to prices.
    Returns meter ID or None.
    """
    event_name = METERS.get(meter_key, {}).get("event_name")
    if not event_name:
        return None
    for meter in _list_all_meters():
        if (
            getattr(meter, "event_name", None) == event_name
            and getattr(meter, "status", None) == "active"
        ):
            return meter.id
    return None


def _find_product_by_name(name: str) -> str | None:
    """Find a product by exact name. Returns product ID or None."""
    for prod in _list_all_products():
        if prod.name == name:
            return prod.id
    return None


def _find_price_by_lookup_key(lookup_key: str) -> str | None:
    """Find a price by its top-level lookup_key field. Returns price ID or None."""
    for price in _list_all_prices():
        if getattr(price, "lookup_key", None) == lookup_key:
            return price.id
    return None


# ---------------------------------------------------------------------------
# Mode: --audit
# ---------------------------------------------------------------------------


def mode_audit(mode: str, dry_run: bool) -> None:
    """Read-only report of existing Stripe objects vs. what the script manages."""
    _log(f"=== AUDIT MODE (mode={mode}, dry_run={dry_run}) ===")

    if dry_run:
        _log("[dry-run] Skipping Stripe API calls. Would list all objects.")
        _log("[dry-run] Expected managed objects: 3 products, 2 meters, 9 prices")
        return

    products = _list_all_products()
    prices = _list_all_prices()
    meters = _list_all_meters()

    _log(f"\n--- Products ({len(products)} total) ---")
    managed_pkeys = set(PRODUCTS.keys())
    for prod in products:
        pkey = _meta(prod, "pilot_key")
        status = "MANAGED" if pkey in managed_pkeys else "ORPHANED"
        _log(f"  [{status}] {prod.id}  name={prod.name!r}  pilot_key={pkey!r}")

    _log(f"\n--- Prices ({len(prices)} total) ---")
    managed_price_keys = set(PRICES.keys())
    for price in prices:
        pkey = _meta(price, "pilot_key")
        lkey = getattr(price, "lookup_key", None)
        status = "MANAGED" if pkey in managed_price_keys else "ORPHANED"
        amt = getattr(price, "unit_amount", None)
        recurring_obj = getattr(price, "recurring", None) or {}
        # D7: recurring_obj is a StripeObject when from a real Stripe Price;
        # StripeObject does not support .get(). getattr works for both
        # StripeObject (returns the attribute) and empty dict {} (returns
        # the default — dicts have no 'interval' attribute).
        interval = getattr(recurring_obj, "interval", "?")
        _log(
            f"  [{status}] {price.id}  amount={amt}  interval={interval}  "
            f"pilot_key={pkey!r}  lookup_key={lkey!r}"
        )

    _log(f"\n--- Billing Meters ({len(meters)} total) ---")
    for meter in meters:
        # Meters don't support metadata; classify by event_name match
        event_name = getattr(meter, "event_name", None)
        managed_events = {m["event_name"] for m in METERS.values()}
        status = "MANAGED" if event_name in managed_events else "ORPHANED"
        _log(
            f"  [{status}] {meter.id}  event={meter.event_name!r}  "
            f"display_name={meter.display_name!r}"
        )

    # Summary of what the script would create
    _log("\n--- What the script would create (if missing) ---")
    for pkey in PRODUCTS:
        existing = _find_product_by_pilot_key(pkey)
        action = "EXISTS" if existing else "CREATE"
        _log(f"  [{action}] product {pkey}")
    for mkey in METERS:
        existing = _find_meter_by_key(mkey)
        action = "EXISTS" if existing else "CREATE"
        _log(f"  [{action}] meter {mkey}")
    for price_key in PRICES:
        existing = _find_price_by_pilot_key(price_key)
        action = "EXISTS" if existing else "CREATE"
        _log(f"  [{action}] price {price_key}")

    _log("\n=== AUDIT COMPLETE (read-only, no changes made) ===")


# ---------------------------------------------------------------------------
# Mode: --adopt-existing
# ---------------------------------------------------------------------------


def mode_adopt_existing(mode: str, dry_run: bool) -> dict:
    """Add metadata.pilot_key to existing manually-created objects."""
    _log(f"=== ADOPT-EXISTING MODE (mode={mode}, dry_run={dry_run}) ===")

    ids = _load_existing_ids(mode)
    adopted = 0

    for lookup, mapping in ADOPTION_MAP.items():
        pilot_key = mapping["pilot_key"]
        obj_type = mapping["type"]

        if obj_type == "product":
            existing_id = _find_product_by_pilot_key(pilot_key)
            if existing_id:
                _log(
                    f"  SKIP product {pilot_key}: already has pilot_key ({existing_id})"
                )
                ids["products"][pilot_key] = existing_id
                continue

            target_id = _find_product_by_name(lookup)
            if not target_id:
                _log(f"  MISS product {pilot_key}: no product named {lookup!r} found")
                continue

            if dry_run:
                _log(
                    f"  [dry-run] Would adopt product {target_id} → pilot_key={pilot_key}"
                )
                ids["products"][pilot_key] = target_id
                adopted += 1
                continue

            # Merge pilot_key into existing metadata (preserve existing keys)
            prod = stripe.Product.retrieve(target_id)
            new_metadata = _metadata_to_dict(prod)
            new_metadata["pilot_key"] = pilot_key
            stripe.Product.modify(target_id, metadata=new_metadata)
            _log(f"  ADOPTED product {target_id} → pilot_key={pilot_key}")
            ids["products"][pilot_key] = target_id
            adopted += 1

        elif obj_type == "price":
            existing_id = _find_price_by_pilot_key(pilot_key)
            if existing_id:
                _log(f"  SKIP price {pilot_key}: already has pilot_key ({existing_id})")
                ids["prices"][pilot_key] = existing_id
                continue

            target_id = _find_price_by_lookup_key(lookup)
            if not target_id:
                _log(f"  MISS price {pilot_key}: no price with lookup_key={lookup!r}")
                continue

            if dry_run:
                _log(
                    f"  [dry-run] Would adopt price {target_id} → pilot_key={pilot_key}"
                )
                ids["prices"][pilot_key] = target_id
                adopted += 1
                continue

            price = stripe.Price.retrieve(target_id)
            new_metadata = _metadata_to_dict(price)
            new_metadata["pilot_key"] = pilot_key
            stripe.Price.modify(target_id, metadata=new_metadata)
            _log(f"  ADOPTED price {target_id} → pilot_key={pilot_key}")
            ids["prices"][pilot_key] = target_id
            adopted += 1

    _log(f"\nAdopted {adopted} object(s).")

    if not dry_run and adopted > 0:
        _save_ids(mode, ids)

    _log("=== ADOPT-EXISTING COMPLETE ===")
    return ids


# ---------------------------------------------------------------------------
# Mode: create (default)
# ---------------------------------------------------------------------------


def mode_create(mode: str, dry_run: bool, force: bool = False) -> dict:
    """Create missing objects. Order: Products → Meters → Prices.

    When ``force=True``, the JSON cache (``stripe_ids.{mode}.json``) is
    ignored for the existence check — the live Stripe lookup always runs.
    Use after purging the Stripe account so stale cached IDs don't mask
    missing objects. ``_save_ids`` still overwrites the cache at the end.
    """
    _log(f"=== CREATE MODE (mode={mode}, dry_run={dry_run}, force={force}) ===")

    if force:
        _log(
            f"FORCE: ignoring cached stripe_ids.{mode}.json — querying Stripe "
            "for all objects"
        )

    ids = _load_existing_ids(mode)
    created = 0

    # --- Products ---
    _log("\n--- Products ---")
    for pkey, pdef in PRODUCTS.items():
        existing = (
            None if force else ids["products"].get(pkey)
        ) or _find_product_by_pilot_key(pkey)
        if existing:
            _log(f"  EXISTS product {pkey} → {existing}")
            ids["products"][pkey] = existing
            continue

        if dry_run:
            _log(f"  [dry-run] Would create product {pkey}: {pdef['name']!r}")
            ids["products"][pkey] = f"[dry-run]prod_{pkey}"
            created += 1
            continue

        prod = stripe.Product.create(
            name=pdef["name"],
            description=pdef.get("description", ""),
            metadata=pdef["metadata"],
        )
        _log(f"  CREATED product {pkey} → {prod.id}")
        ids["products"][pkey] = prod.id
        created += 1

    # --- Meters (must be created BEFORE metered prices) ---
    _log("\n--- Billing Meters ---")
    for mkey, mdef in METERS.items():
        existing = (None if force else ids["meters"].get(mkey)) or _find_meter_by_key(
            mkey
        )
        if existing:
            _log(f"  EXISTS meter {mkey} → {existing}")
            ids["meters"][mkey] = existing
            continue

        if dry_run:
            _log(f"  [dry-run] Would create meter {mkey}: event={mdef['event_name']!r}")
            ids["meters"][mkey] = f"[dry-run]meter_{mkey}"
            created += 1
            continue

        # NOTE: Billing Meters do not support metadata. Idempotent lookup
        # is by event_name (see _find_meter_by_key).
        meter = stripe.billing.Meter.create(
            display_name=mdef["display_name"],
            event_name=mdef["event_name"],
            default_aggregation=mdef["default_aggregation"],
            customer_mapping=mdef["customer_mapping"],
            value_settings=mdef["value_settings"],
        )
        _log(f"  CREATED meter {mkey} → {meter.id}")
        ids["meters"][mkey] = meter.id
        created += 1

    # --- Prices ---
    _log("\n--- Prices ---")
    for price_key, pdef in PRICES.items():
        existing = (
            None if force else ids["prices"].get(price_key)
        ) or _find_price_by_pilot_key(price_key)
        if existing:
            _log(f"  EXISTS price {price_key} → {existing}")
            ids["prices"][price_key] = existing
            continue

        product_id = ids["products"].get(pdef["product_key"])
        if not product_id:
            _log(
                f"  ERROR price {price_key}: product {pdef['product_key']} not "
                "found in IDs map. Skipping."
            )
            continue

        if dry_run:
            _log(
                f"  [dry-run] Would create price {price_key}: "
                f"amount={pdef['unit_amount']} {pdef['currency']}"
            )
            ids["prices"][price_key] = f"[dry-run]price_{price_key}"
            created += 1
            continue

        recurring = dict(pdef["recurring"])
        usage_type = recurring.pop("usage_type", "licensed")
        meter_key = recurring.pop("meter_key", None)

        # For metered prices, reference the meter ID inside recurring
        if usage_type == "metered" and meter_key:
            meter_id = ids["meters"].get(meter_key)
            if not meter_id:
                _log(
                    f"  ERROR price {price_key}: meter {meter_key} not found. Skipping."
                )
                continue
            recurring["meter"] = meter_id

        create_params: dict = {
            "product": product_id,
            "currency": pdef["currency"],
            "unit_amount": pdef["unit_amount"],
            "recurring": recurring,
            "metadata": pdef["metadata"],
        }
        # usage_type is a top-level param, not inside recurring
        if usage_type == "metered":
            create_params["recurring"]["usage_type"] = "metered"
        else:
            create_params["recurring"]["usage_type"] = "licensed"

        price = stripe.Price.create(**create_params)
        _log(f"  CREATED price {price_key} → {price.id}")
        ids["prices"][price_key] = price.id
        created += 1

    _log(f"\nCreated {created} object(s).")

    if not dry_run:
        _save_ids(mode, ids)

    _log("=== CREATE COMPLETE ===")
    return ids


# ---------------------------------------------------------------------------
# Mode: --update-db
# ---------------------------------------------------------------------------


def mode_update_db(mode: str, dry_run: bool, ids: dict) -> None:
    """Write generated price IDs to subscription_tier columns via SQL UPDATE."""
    _log(f"=== UPDATE-DB MODE (mode={mode}, dry_run={dry_run}) ===")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        _log("ERROR: DATABASE_URL env var not set. Cannot update DB.")
        sys.exit(1)

    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)

    updates: list[tuple[str, str, str]] = []  # (tier_name, column, price_id)
    for tier_name, price_keys in TIER_PRICE_MAP.items():
        monthly_key = price_keys.get("monthly")
        annual_key = price_keys.get("annual")

        if monthly_key:
            monthly_id = ids["prices"].get(monthly_key)
            if monthly_id and not monthly_id.startswith("[dry-run]"):
                updates.append((tier_name, "stripe_price_id_monthly", monthly_id))
            elif monthly_id and monthly_id.startswith("[dry-run]"):
                updates.append((tier_name, "stripe_price_id_monthly", monthly_id))

        if annual_key:
            annual_id = ids["prices"].get(annual_key)
            if annual_id and not annual_id.startswith("[dry-run]"):
                updates.append((tier_name, "stripe_price_id_annual", annual_id))
            elif annual_id and annual_id.startswith("[dry-run]"):
                updates.append((tier_name, "stripe_price_id_annual", annual_id))

    _log(f"\nPlanned updates ({len(updates)}):")
    for tier_name, column, price_id in updates:
        _log(f"  {tier_name}.{column} = {price_id}")

    if dry_run:
        _log("\n[dry-run] Skipping DB writes.")
        _log("=== UPDATE-DB COMPLETE (dry-run, no changes) ===")
        return

    with engine.begin() as conn:
        for tier_name, column, price_id in updates:
            if price_id.startswith("[dry-run]"):
                _log(f"  SKIP {tier_name}.{column}: dry-run placeholder value")
                continue
            conn.execute(
                text(
                    f"UPDATE subscription_tier SET {column} = :pid "
                    "WHERE tier_name = :tn"
                ),
                {"pid": price_id, "tn": tier_name},
            )
            _log(f"  UPDATED {tier_name}.{column} = {price_id}")

    _log("=== UPDATE-DB COMPLETE ===")


# ---------------------------------------------------------------------------
# Mode: --migrate-prices
# ---------------------------------------------------------------------------


def mode_migrate_prices(mode: str, dry_run: bool, ids: dict) -> dict:
    """Detect amount changes, create new prices, archive old ones.

    Excludes price-locked tiers (Charter — filter on price_locked=true in
    price metadata). Updates JSON file + DB.
    """
    _log(f"=== MIGRATE-PRICES MODE (mode={mode}, dry_run={dry_run}) ===")

    migrated = 0

    for price_key, pdef in PRICES.items():
        # Skip price-locked tiers
        if pdef["metadata"].get("price_locked") == "true":
            _log(f"  SKIP {price_key}: price_locked=true (excluded from migration)")
            continue

        existing_id = ids["prices"].get(price_key)
        if not existing_id or existing_id.startswith("[dry-run]"):
            _log(f"  SKIP {price_key}: no existing price ID in map")
            continue

        # Retrieve the existing price to compare amounts
        existing_price = stripe.Price.retrieve(existing_id)
        existing_amount = existing_price.unit_amount
        config_amount = pdef["unit_amount"]

        if existing_amount == config_amount:
            _log(
                f"  OK {price_key}: amount matches ({config_amount}¢) — no migration needed"
            )
            continue

        _log(
            f"  MIGRATE {price_key}: existing={existing_amount}¢ → "
            f"config={config_amount}¢"
        )

        if dry_run:
            _log(
                f"    [dry-run] Would create new price at {config_amount}¢ and "
                f"archive {existing_id}"
            )
            migrated += 1
            continue

        # Create new price
        product_id = ids["products"].get(pdef["product_key"])
        if not product_id:
            _log(f"    ERROR: product {pdef['product_key']} not in IDs map. Skipping.")
            continue

        recurring = dict(pdef["recurring"])
        usage_type = recurring.pop("usage_type", "licensed")
        meter_key = recurring.pop("meter_key", None)
        if usage_type == "metered" and meter_key:
            meter_id = ids["meters"].get(meter_key)
            if meter_id:
                recurring["meter"] = meter_id
        recurring["usage_type"] = usage_type

        new_price = stripe.Price.create(
            product=product_id,
            currency=pdef["currency"],
            unit_amount=config_amount,
            recurring=recurring,
            metadata=pdef["metadata"],
        )
        _log(f"    CREATED new price {price_key} → {new_price.id}")

        # Archive old price
        stripe.Price.modify(existing_id, active=False)
        _log(f"    ARCHIVED old price {existing_id}")

        # Update IDs map
        ids["prices"][price_key] = new_price.id
        migrated += 1

    _log(f"\nMigrated {migrated} price(s).")

    if not dry_run and migrated > 0:
        _save_ids(mode, ids)
        # Also update DB with new price IDs
        _log("Running --update-db to sync new price IDs to subscription_tier...")
        mode_update_db(mode, dry_run=False, ids=ids)

    _log("=== MIGRATE-PRICES COMPLETE ===")
    return ids


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stripe Bootstrap Script — manage Products, Prices, and Meters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["test", "live"],
        default="test",
        help="Stripe account mode (default: test)",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Read-only report of existing Stripe objects",
    )
    parser.add_argument(
        "--adopt-existing",
        action="store_true",
        help="Add metadata.pilot_key to existing manually-created objects",
    )
    parser.add_argument(
        "--update-db",
        action="store_true",
        help="Write generated price IDs to subscription_tier columns",
    )
    parser.add_argument(
        "--migrate-prices",
        action="store_true",
        help="Detect amount changes, create new prices, archive old ones",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without calling Stripe API (limited — see notes)",
    )
    parser.add_argument(
        "--i-am-sure",
        action="store_true",
        help="Required for live mode to prevent accidental production changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore cached stripe_ids.{mode}.json and re-query Stripe for "
        "every object (use after purging the Stripe account).",
    )

    args = parser.parse_args()

    # Resolve API key (enforces live guard)
    api_key = _resolve_api_key(args.mode, args.i_am_sure)
    stripe.api_key = api_key

    # Determine which mode to run. Only one action mode at a time.
    # Priority: audit > adopt-existing > migrate-prices > update-db > create
    if args.audit:
        mode_audit(args.mode, args.dry_run)
        return

    if args.adopt_existing:
        ids = mode_adopt_existing(args.mode, args.dry_run)
        return

    if args.migrate_prices:
        # migrate-prices needs the current IDs map first
        ids = _load_existing_ids(args.mode)
        if not ids["prices"]:
            _log("No existing price IDs found. Run create mode first.")
            sys.exit(1)
        mode_migrate_prices(args.mode, args.dry_run, ids)
        return

    if args.update_db:
        ids = _load_existing_ids(args.mode)
        if not ids["prices"]:
            _log("No existing price IDs found. Run create mode first.")
            sys.exit(1)
        mode_update_db(args.mode, args.dry_run, ids)
        return

    # Default: create mode
    ids = mode_create(args.mode, args.dry_run, force=args.force)

    # Verify the final state
    _log("\n--- Final ID Map ---")
    _log(f"  Products ({len(ids['products'])}): {ids['products']}")
    _log(f"  Meters ({len(ids['meters'])}): {ids['meters']}")
    _log(f"  Prices ({len(ids['prices'])}): {ids['prices']}")

    total = len(ids["products"]) + len(ids["meters"]) + len(ids["prices"])
    _log(f"\nTotal objects: {total} (expected 14: 3 products + 2 meters + 9 prices)")


if __name__ == "__main__":
    main()
