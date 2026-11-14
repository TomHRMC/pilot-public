"""
seed_pricebook_starter.py — Per-tenant starter pricebook (DB-MGMT-1, design §F.5).

Seeds a starter electrical pricebook for a specific tenant. Run at concierge
provisioning time (Beta) to give each founder tenant a real, editable starter
pricebook. GA self-serve signup integration is a future batch.

``pricebook_item.tenant_id`` is NOT NULL (MCP-verified) — platform-owned rows
are schema-impossible, so this script is per-tenant by design (§G-5).

Idempotency: ``INSERT ... ON CONFLICT (tenant_id, sku) DO NOTHING`` — the
``uq_pricebook_item_tenant_sku`` unique constraint is MCP-verified to exist.
No DELETE path is needed.

For each item, also inserts one current ``pricebook_item_version`` row with:
  - ``default_unit_price_cents`` (int NOT NULL)
  - ``valid_period`` (tstzrange NOT NULL) — single open-ended range per item
    starting at a past date (per README §7 GiST caveat; the ``piv_no_overlap``
    exclusion constraint prevents overlapping ranges for the same
    tenant_id + pricebook_item_id).

CLI:
  python migrations/scripts/seed_pricebook_starter.py --env dev --tenant-id <uuid>
  python migrations/scripts/seed_pricebook_starter.py --env prod --tenant-id <uuid> [--mode seed|show|inspect]

**Content sign-off gate**: Tom must approve the catalog before first prod use.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text  # noqa: E402

from migrations.scripts._db_utils import get_db_session  # noqa: E402
from migrations.scripts._env_profiles import (  # noqa: E402
    add_env_args,
    assert_target_compatible,
    print_seed_banner,
    resolve_profile_from_args,
)

# Path to the JSON catalog
CATALOG_PATH = (
    Path(__file__).parent / "data" / "pricebook_starter" / "default_catalog.json"
)

# Start date for valid_period (past date to avoid GiST conflicts with future ranges)
VALID_PERIOD_START = "2026-01-01T00:00:00+00:00"


def _load_catalog() -> list[dict]:
    """Load the starter catalog from the JSON file."""
    with open(CATALOG_PATH) as f:
        data = json.load(f)
    return data["items"]


def _resolve_uom_ids(db) -> dict[str, str]:
    """Map uom_code → supplier_item_uom.id from the live DB."""
    rows = db.execute(text("SELECT id, code FROM public.supplier_item_uom")).fetchall()
    return {row.code: str(row.id) for row in rows}


def mode_seed(tenant_id: UUID) -> None:
    """Seed the starter pricebook for the given tenant."""
    print(f"=== seed_pricebook_starter: seed mode (tenant={tenant_id}) ===\n")
    items = _load_catalog()

    with get_db_session() as db:
        uom_map = _resolve_uom_ids(db)
        inserted = 0
        skipped = 0

        for item in items:
            uom_id = uom_map.get(item["uom_code"])
            if not uom_id:
                print(
                    f"  ⚠️  [{item['sku']}] UOM '{item['uom_code']}' not found — skipping"
                )
                continue

            # Insert pricebook_item (ON CONFLICT DO NOTHING)
            result = db.execute(
                text("""
                    INSERT INTO public.pricebook_item
                    (id, tenant_id, sku, name, description, uom_id, taxability_code,
                     is_active, created_at, updated_at)
                    VALUES
                    (gen_random_uuid(), :tenant_id, :sku, :name, :description, :uom_id,
                     :taxability_code, true, NOW(), NOW())
                    ON CONFLICT (tenant_id, sku) DO NOTHING
                    RETURNING id
                """),
                {
                    "tenant_id": str(tenant_id),
                    "sku": item["sku"],
                    "name": item["name"],
                    "description": item.get("description"),
                    "uom_id": uom_id,
                    "taxability_code": item.get("taxability_code"),
                },
            )
            row = result.first()

            if row:
                pricebook_item_id = str(row.id)
                # Insert pricebook_item_version (open-ended valid_period)
                db.execute(
                    text("""
                        INSERT INTO public.pricebook_item_version
                        (tenant_id, pricebook_item_id, default_unit_price_cents,
                         valid_period, recorded_at, created_at)
                        VALUES
                        (:tenant_id, :pricebook_item_id, :default_unit_price_cents,
                         tstzrange(:start, NULL), NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "tenant_id": str(tenant_id),
                        "pricebook_item_id": pricebook_item_id,
                        "default_unit_price_cents": item["default_unit_price_cents"],
                        "start": VALID_PERIOD_START,
                    },
                )
                print(
                    f"  ✅ [{item['sku']}] {item['name']} — "
                    f"${item['default_unit_price_cents'] / 100:.2f}/{item['uom_code']}"
                )
                inserted += 1
            else:
                print(
                    f"  ℹ️  [{item['sku']}] already exists for this tenant — skipped"  # noqa: RUF001
                )
                skipped += 1

        db.commit()
        print(f"\n  Done: {inserted} inserted, {skipped} already existed.")


def mode_inspect(tenant_id: UUID) -> None:
    """Show current pricebook items for the given tenant."""
    print(f"=== seed_pricebook_starter: inspect mode (tenant={tenant_id}) ===\n")
    with get_db_session() as db:
        rows = db.execute(
            text("""
                SELECT pi.sku, pi.name, pi.description, pi.is_active,
                       pi.taxability_code, u.code AS uom_code,
                       piv.default_unit_price_cents
                FROM public.pricebook_item pi
                LEFT JOIN public.supplier_item_uom u ON pi.uom_id = u.id
                LEFT JOIN public.pricebook_item_version piv
                  ON piv.pricebook_item_id = pi.id
                  AND piv.valid_period @> NOW()
                WHERE pi.tenant_id = :tenant_id
                ORDER BY pi.sku
            """),
            {"tenant_id": str(tenant_id)},
        ).fetchall()
        print(f"  [pricebook_item]  {len(rows)} row(s) for tenant {tenant_id}")
        for r in rows:
            price = (
                f"${r.default_unit_price_cents / 100:.2f}"
                if r.default_unit_price_cents
                else "NULL"
            )
            print(
                f"    • {r.sku:<28}  {r.name:<35}  "
                f"uom={r.uom_code or 'NULL':<12}  "
                f"tax={r.taxability_code or 'NULL':<10}  "
                f"price={price}  active={r.is_active}"
            )


def mode_show() -> None:
    """Print what would be seeded without touching the DB."""
    print("=== seed_pricebook_starter: show mode ===\n")
    items = _load_catalog()
    print(f"Starter catalog: {len(items)} items from {CATALOG_PATH.name}")
    print(f"valid_period start: {VALID_PERIOD_START}\n")
    for item in items:
        price = item["default_unit_price_cents"] / 100
        print(
            f"  • {item['sku']:<28}  {item['name']:<35}  "
            f"uom={item['uom_code']:<12}  "
            f"tax={item.get('taxability_code', 'NULL'):<10}  "
            f"price=${price:.2f}"
        )
    print(f"\n  Total: {len(items)} items")
    print("  ⚠️  Content sign-off gate: Tom must approve before first prod use.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="seed_pricebook_starter.py — per-tenant starter pricebook (DB-MGMT-1)"
    )
    parser.add_argument(
        "--mode",
        choices=["seed", "inspect", "show"],
        default="seed",
        help="seed: insert items | inspect: show current state | show: print catalog",
    )
    parser.add_argument(
        "--tenant-id",
        required=False,
        default=None,
        help="Tenant UUID (required for seed and inspect modes)",
    )
    add_env_args(parser)
    args = parser.parse_args()

    profile = resolve_profile_from_args(args)
    db_url = os.environ.get("DATABASE_URL", "")
    if args.mode in ("seed", "inspect"):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_pricebook_starter.py")

    if args.mode == "show":
        mode_show()
        return

    if not args.tenant_id:
        print(
            "ERROR: --tenant-id is required for seed and inspect modes.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        tenant_id = UUID(args.tenant_id)
    except ValueError:
        print(f"ERROR: Invalid UUID: {args.tenant_id}", file=sys.stderr)
        sys.exit(1)

    if args.mode == "seed":
        mode_seed(tenant_id)
    elif args.mode == "inspect":
        mode_inspect(tenant_id)


if __name__ == "__main__":
    main()
