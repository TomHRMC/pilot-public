"""
seed_scenario_supplier_catalog.py — Group D: Supplier catalog scenario data.

Purpose: Seeds suppliers + supplier_items + supplier_item_prices + pricing_cache
for UI testing of the supplier catalog and pricebook features. Loads item
definitions from JSON data files in data/supplier_catalog/*.json (same pattern
as data/email_templates/).

SD-8 (2026-07-23): Refactored to JSON-driven loader; added description/taxability_code
fields; pricing_cache rows for Wesco items; updated reset/inspect/show modes.

Depends on seed_core.py (supplier_lifecycle_status, supplier_item_category,
supplier_item_uom rows) and seed_test_tenant.py having run first.

Schema verified against live DB 2026-07-23:
  supplier:           id, tenant_id, name, website, api_auth_type, api_base_url,
                      is_active, lifecycle_status_id
  supplier_item:      id, tenant_id, supplier_id, sku, name, description, uom_id,
                      category_id, taxability_code, is_active
  supplier_item_price: id, tenant_id, supplier_item_id, unit_price (NUMERIC), currency,
                       valid_period (tstzrange)
  pricing_cache:      id (bigint), tenant_id, supplier_id, sku, price_cents (int, NOT NULL),
                      currency (NOT NULL), expires_at (NOT NULL), created_at, created_by

Modes:
  --mode seed     (default) idempotent
  --mode inspect  show current state with values
  --mode show     print definitions from JSON, no DB
  --reset         wipe only this scenario's data, then exit

Usage:
  python migrations/scripts/seed_scenario_supplier_catalog.py
  python migrations/scripts/seed_scenario_supplier_catalog.py --mode inspect
  python migrations/scripts/seed_scenario_supplier_catalog.py --mode show
  python migrations/scripts/seed_scenario_supplier_catalog.py --reset
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from uuid import UUID

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text  # noqa: E402

from core.config import settings  # noqa: E402
from migrations.scripts._db_utils import get_db_session  # noqa: E402
from migrations.scripts._env_profiles import (  # noqa: E402
    add_env_args,
    assert_group_allowed,
    assert_target_compatible,
    print_seed_banner,
    resolve_profile_from_args,
)

# ── JSON DATA LOADING ─────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data" / "supplier_catalog"


def _load_supplier_definitions() -> list[dict]:
    """Load all supplier JSON files from data/supplier_catalog/, sorted by filename."""
    definitions = []
    for json_file in sorted(DATA_DIR.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            definitions.append(json.load(f))
    return definitions


SUPPLIER_DEFINITIONS = _load_supplier_definitions()

# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_scenario_supplier_catalog.py — Group D supplier catalog seeder"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


def _get_tenant_id(args=None) -> UUID:
    if args and args.tenant_id:
        return UUID(args.tenant_id)
    return UUID(settings.TEST_TENANT_ID)


def mode_show():
    """Print what would be seeded from JSON files; no DB required."""
    print("=== seed_scenario_supplier_catalog: show mode ===\n")
    print(
        f"  Loaded {len(SUPPLIER_DEFINITIONS)} supplier definition(s) from {DATA_DIR}\n"
    )
    total_items = 0
    for defn in SUPPLIER_DEFINITIONS:
        supplier_name = defn["supplier"]["name"]
        items = defn["items"]
        active_count = sum(1 for i in items if i.get("is_active", True))
        inactive_count = len(items) - active_count
        print(f"  Supplier: {supplier_name}")
        print(
            f"    Items: {len(items)} total ({active_count} active, {inactive_count} inactive)"
        )
        for item in items:
            active_str = "" if item.get("is_active", True) else " [INACTIVE]"
            print(
                f"    [{item['sku']}] '{item['name']}'  "
                f"category={item['category_code']}  uom={item['uom_code']}  "
                f"price=${item['current_price_dollars']:.2f}{active_str}"
            )
        print()
        total_items += len(items)
    print(f"  Total: {len(SUPPLIER_DEFINITIONS)} suppliers, {total_items} items")


def mode_reset(tenant_id: UUID):
    """Wipe this scenario's data from the test tenant.

    Delete order (FK safety): pricing_cache → supplier_item_price → supplier_item → supplier
    Each DELETE is scoped to tenant_id — never wipes rows from other tenants.
    """
    print("⚠️  WARNING: --reset will wipe supplier catalog Group D data.")
    print("    Press Ctrl+C to abort. Proceeding in 3 seconds...")
    time.sleep(3)

    tid = str(tenant_id)
    with get_db_session() as db:
        # 1. pricing_cache — FK: supplier_id references supplier
        deleted = db.execute(
            text("""
                DELETE FROM public.pricing_cache
                WHERE supplier_id IN (
                    SELECT id FROM public.supplier WHERE tenant_id = :tid
                )
            """),
            {"tid": tid},
        ).rowcount
        print(f"  🗑  [pricing_cache] Deleted {deleted} row(s)")

        # 2. supplier_item_price — FK: supplier_item_id references supplier_item
        deleted = db.execute(
            text("""
                DELETE FROM public.supplier_item_price
                WHERE supplier_item_id IN (
                    SELECT si.id FROM public.supplier_item si
                    JOIN public.supplier s ON s.id = si.supplier_id
                    WHERE s.tenant_id = :tid
                )
            """),
            {"tid": tid},
        ).rowcount
        print(f"  🗑  [supplier_item_price] Deleted {deleted} row(s)")

        # 3. supplier_item — FK: supplier_id references supplier
        deleted = db.execute(
            text("""
                DELETE FROM public.supplier_item
                WHERE supplier_id IN (
                    SELECT id FROM public.supplier WHERE tenant_id = :tid
                )
            """),
            {"tid": tid},
        ).rowcount
        print(f"  🗑  [supplier_item] Deleted {deleted} row(s)")

        # 4. supplier
        deleted = db.execute(
            text("DELETE FROM public.supplier WHERE tenant_id = :tid"),
            {"tid": tid},
        ).rowcount
        print(f"  🗑  [supplier] Deleted {deleted} row(s)")

        db.commit()
    print("  ✅ Supplier catalog data wiped.")


def mode_seed(tenant_id: UUID = None):
    """Seed the supplier catalog scenario data from JSON definition files."""
    if tenant_id is None:
        tenant_id = UUID(settings.TEST_TENANT_ID)

    print("=== seed_scenario_supplier_catalog: seed mode ===\n")
    tid = str(tenant_id)

    with get_db_session() as db:
        # --- Lookup supplier_lifecycle_status id for 'active' ---
        status_row = db.execute(
            text("""
                SELECT id FROM public.supplier_lifecycle_status
                WHERE code = 'active' AND (tenant_id IS NULL OR tenant_id = :tid)
                ORDER BY tenant_id NULLS LAST LIMIT 1
            """),
            {"tid": tid},
        ).first()
        if not status_row:
            print(
                "  ❌ supplier_lifecycle_status 'active' not found — run seed_core.py first"
            )
            return
        lifecycle_status_id = str(status_row.id)

        # --- Seed all suppliers from JSON definitions ---
        for defn in SUPPLIER_DEFINITIONS:
            supplier_info = defn["supplier"]
            current_supplier_name = supplier_info["name"]
            current_supplier_items = defn["items"]

            # Resolve or insert supplier
            supplier_row = db.execute(
                text("""
                    SELECT id FROM public.supplier
                    WHERE tenant_id = :tid AND name = :name
                """),
                {"tid": tid, "name": current_supplier_name},
            ).first()

            if supplier_row:
                supplier_id = str(supplier_row.id)
                print(
                    f"  ℹ️  [supplier] '{current_supplier_name}' already exists ({supplier_id})"
                )
                # Always update website/api fields (idempotent)
                db.execute(
                    text("""
                        UPDATE public.supplier
                        SET website = :website,
                            api_auth_type = :api_auth_type,
                            api_base_url = :api_base_url,
                            updated_at = NOW()
                        WHERE id = :sid AND tenant_id = :tid
                    """),
                    {
                        "website": supplier_info.get("website"),
                        "api_auth_type": supplier_info.get("api_auth_type"),
                        "api_base_url": supplier_info.get("api_base_url"),
                        "sid": supplier_id,
                        "tid": tid,
                    },
                )
                print(
                    f"  ✅ [supplier] '{current_supplier_name}' website/api fields updated"
                )
            else:
                result = db.execute(
                    text("""
                        INSERT INTO public.supplier
                        (id, tenant_id, name, website, api_auth_type, api_base_url,
                         is_active, lifecycle_status_id, created_at, updated_at)
                        VALUES (gen_random_uuid(), :tid, :name, :website, :api_auth_type,
                                :api_base_url, true, CAST(:status_id AS uuid), NOW(), NOW())
                        RETURNING id
                    """),
                    {
                        "tid": tid,
                        "name": current_supplier_name,
                        "website": supplier_info.get("website"),
                        "api_auth_type": supplier_info.get("api_auth_type"),
                        "api_base_url": supplier_info.get("api_base_url"),
                        "status_id": lifecycle_status_id,
                    },
                ).first()
                supplier_id = str(result.id)
                print(
                    f"  ✅ [supplier] Inserted '{current_supplier_name}' ({supplier_id})"
                )

            # --- Seed supplier_items + prices + pricing_cache ---
            for item in current_supplier_items:
                sku = item["sku"]
                uom_code = item["uom_code"]
                category_code = item["category_code"]
                item_is_active = item.get("is_active", True)
                price = item["current_price_dollars"]

                # Look up uom_id
                uom_row = db.execute(
                    text("""
                        SELECT id FROM public.supplier_item_uom
                        WHERE code = :code AND (tenant_id IS NULL OR tenant_id = :tid)
                        ORDER BY tenant_id NULLS LAST LIMIT 1
                    """),
                    {"code": uom_code, "tid": tid},
                ).first()
                if not uom_row:
                    print(
                        f"  ⚠️  [supplier_item] UOM '{uom_code}' not found — skipping {sku}"
                    )
                    continue
                uom_id = str(uom_row.id)

                # Look up category_id
                cat_row = db.execute(
                    text("""
                        SELECT id FROM public.supplier_item_category
                        WHERE code = :code AND (tenant_id IS NULL OR tenant_id = :tid)
                        ORDER BY tenant_id NULLS LAST LIMIT 1
                    """),
                    {"code": category_code, "tid": tid},
                ).first()
                category_id = str(cat_row.id) if cat_row else None

                # Check if item exists (keyed by supplier_id + sku)
                item_row = db.execute(
                    text("""
                        SELECT id FROM public.supplier_item
                        WHERE supplier_id = CAST(:supplier_id AS uuid) AND sku = :sku
                    """),
                    {"supplier_id": supplier_id, "sku": sku},
                ).first()

                if item_row:
                    item_id = str(item_row.id)
                    print(f"  ℹ️  [supplier_item] '{sku}' already exists")
                else:
                    result = db.execute(
                        text("""
                            INSERT INTO public.supplier_item
                            (id, tenant_id, supplier_id, sku, name, description, uom_id,
                             category_id, taxability_code, is_active, created_at, updated_at)
                            VALUES (gen_random_uuid(), :tid, CAST(:supplier_id AS uuid), :sku,
                                    :name, :description, CAST(:uom_id AS uuid),
                                    CAST(:category_id AS uuid), :taxability_code, :is_active,
                                    NOW(), NOW())
                            RETURNING id
                        """),
                        {
                            "tid": tid,
                            "supplier_id": supplier_id,
                            "sku": sku,
                            "name": item["name"],
                            "description": item.get("description"),
                            "uom_id": uom_id,
                            "category_id": category_id,
                            "taxability_code": item.get("taxability_code"),
                            "is_active": item_is_active,
                        },
                    ).first()
                    item_id = str(result.id)
                    active_str = "" if item_is_active else " [INACTIVE]"
                    print(f"  ✅ [supplier_item] '{sku}' — {item['name']}{active_str}")

                # Seed supplier_item_price (1 per item, open-ended valid_period)
                price_row = db.execute(
                    text("""
                        SELECT id FROM public.supplier_item_price
                        WHERE supplier_item_id = CAST(:item_id AS uuid) AND tenant_id = :tid
                    """),
                    {"item_id": item_id, "tid": tid},
                ).first()

                if price_row:
                    print(
                        f"  ℹ️  [supplier_item_price] Price for '{sku}' already exists"
                    )
                else:
                    db.execute(
                        text("""
                            INSERT INTO public.supplier_item_price
                            (tenant_id, supplier_item_id, unit_price, currency, valid_period,
                             created_at)
                            VALUES (:tid, CAST(:item_id AS uuid), :price, 'USD',
                                    tstzrange(NOW(), NULL), NOW())
                        """),
                        {"tid": tid, "item_id": item_id, "price": price},
                    )
                    print(f"  ✅ [supplier_item_price] ${price:.2f}/unit for '{sku}'")

                # Seed pricing_cache for Wesco items only
                if current_supplier_name == "Wesco Distribution":
                    price_cents = int(round(price * 100))
                    existing_cache = db.execute(
                        text("""
                            SELECT id FROM public.pricing_cache
                            WHERE tenant_id = :tid
                              AND supplier_id = CAST(:supplier_id AS uuid)
                              AND sku = :sku
                        """),
                        {"tid": tid, "supplier_id": supplier_id, "sku": sku},
                    ).first()
                    if not existing_cache:
                        db.execute(
                            text("""
                                INSERT INTO public.pricing_cache
                                (tenant_id, supplier_id, sku, price_cents, currency,
                                 expires_at, created_at)
                                VALUES (:tid, CAST(:supplier_id AS uuid), :sku, :price_cents,
                                        'USD', NOW() + INTERVAL '90 days', NOW())
                            """),
                            {
                                "tid": tid,
                                "supplier_id": supplier_id,
                                "sku": sku,
                                "price_cents": price_cents,
                            },
                        )
                        print(f"  ✅ [pricing_cache] {sku} → {price_cents}¢")
                    else:
                        print(f"  ℹ️  [pricing_cache] '{sku}' already exists")

        db.commit()

    total_items = sum(len(defn["items"]) for defn in SUPPLIER_DEFINITIONS)
    print(
        f"\n🎉 seed_scenario_supplier_catalog complete — "
        f"{len(SUPPLIER_DEFINITIONS)} suppliers, {total_items} items + prices seeded."
    )


def mode_inspect(tenant_id: UUID = None):
    """Show current state of supplier catalog data."""
    if tenant_id is None:
        tenant_id = UUID(settings.TEST_TENANT_ID)

    print("=== seed_scenario_supplier_catalog: inspect mode ===\n")
    tid = str(tenant_id)

    with get_db_session() as db:
        # Suppliers — show website/API fields
        rows = db.execute(
            text("""
                SELECT s.id, s.name, s.is_active, sls.code AS lifecycle,
                       s.website, s.api_auth_type, s.api_base_url
                FROM public.supplier s
                LEFT JOIN public.supplier_lifecycle_status sls ON sls.id = s.lifecycle_status_id
                WHERE s.tenant_id = :tid ORDER BY s.name
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [supplier]  {len(rows)} row(s)")
        for r in rows:
            website_str = f"  website={r.website}" if r.website else ""
            api_str = (
                f"  api_auth={r.api_auth_type}  api_base={r.api_base_url}"
                if r.api_auth_type
                else ""
            )
            print(
                f"    • '{r.name}'  lifecycle={r.lifecycle}  is_active={r.is_active}{website_str}{api_str}"
            )
        print()

        # Items — include description/taxability_code
        rows = db.execute(
            text("""
                SELECT si.id, si.sku, si.name, sic.code AS category, siu.code AS uom,
                       si.taxability_code, si.is_active, s.name AS supplier_name
                FROM public.supplier_item si
                LEFT JOIN public.supplier_item_category sic ON sic.id = si.category_id
                LEFT JOIN public.supplier_item_uom siu ON siu.id = si.uom_id
                JOIN public.supplier s ON s.id = si.supplier_id
                WHERE si.tenant_id = :tid ORDER BY s.name, si.sku
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [supplier_item]  {len(rows)} row(s)")
        for r in rows:
            active_str = "" if r.is_active else " [INACTIVE]"
            print(
                f"    • [{r.sku}] '{r.name}'  category={r.category}  uom={r.uom}"
                f"  taxability={r.taxability_code}{active_str}"
            )
        print()

        # Prices
        rows = db.execute(
            text("""
                SELECT sip.id, si.sku, sip.unit_price, sip.currency
                FROM public.supplier_item_price sip
                JOIN public.supplier_item si ON si.id = sip.supplier_item_id
                WHERE sip.tenant_id = :tid ORDER BY si.sku
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [supplier_item_price]  {len(rows)} row(s)")
        for r in rows:
            print(f"    • [{r.sku}]  unit_price={r.unit_price} {r.currency}")
        print()

        # pricing_cache rows
        rows = db.execute(
            text("""
                SELECT pc.id, pc.sku, pc.price_cents, pc.currency, pc.expires_at
                FROM public.pricing_cache pc
                JOIN public.supplier s ON s.id = pc.supplier_id
                WHERE pc.tenant_id = :tid ORDER BY pc.sku
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [pricing_cache]  {len(rows)} row(s)")
        for r in rows:
            print(
                f"    • [{r.sku}]  price_cents={r.price_cents} {r.currency}"
                f"  expires_at={r.expires_at}"
            )


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_supplier_catalog.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(args, "reset", False):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_supplier_catalog.py")
    tenant_id = _get_tenant_id(args)

    if args.reset:
        mode_reset(tenant_id)
    elif args.mode == "show":
        mode_show()
    elif args.mode == "inspect":
        mode_inspect(tenant_id)
    else:
        mode_seed(tenant_id)
