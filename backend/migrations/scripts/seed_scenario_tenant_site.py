"""
seed_scenario_tenant_site.py — Group D: C-B16 tenant site scenario data.

Purpose: Seeds one published hosted_compliance row for the primary demo tenant,
enabling local smoke-testing of the public pages at {slug}.localhost:3000.

The published_snapshot is built by calling build_snapshot() from the service,
so the snapshot shape can never drift from the renderer.

tenant_site has UNIQUE(tenant_id) → INSERT ... ON CONFLICT DO NOTHING is sufficient.
No DELETE needed (Rule 11.1 value-scoping not triggered).

Modes:
  --mode seed     (default) idempotent insert
  --mode inspect  show current state
"""

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text  # noqa: E402

from migrations.scripts._db_utils import get_db_session  # noqa: E402
from migrations.scripts._env_profiles import (  # noqa: E402
    add_env_args,
    assert_group_allowed,
    assert_target_compatible,
    print_seed_banner,
    resolve_profile_from_args,
)

# ── SEED DATA CONFIG ─────────────────────────────────────────────────────────

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
OWNER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")

# The slug for the primary demo tenant's hosted compliance site
SITE_SLUG = "pilot-dev-tenant"

# ── Seed function ────────────────────────────────────────────────────────────


def seed_tenant_site(db):
    """Seed the published hosted_compliance row for the primary demo tenant."""
    # Check if already exists
    existing = db.execute(
        text("SELECT id, status FROM public.tenant_site WHERE tenant_id = :tid"),
        {"tid": str(TENANT_ID)},
    ).first()

    if existing:
        print(f"  i️  [tenant_site] Already exists (status={existing.status})")
        return

    # Build the snapshot using the service renderer
    # We create a temporary in-memory site object, then call build_snapshot
    from app.models.tenant_site import TenantSite
    from services.tenant_site_service import build_snapshot

    # Fetch profile data for defaults
    profile = db.execute(
        text(
            "SELECT legal_business_name, dba_name, support_email, support_phone, "
            "hq_city, hq_state FROM public.tenant_10dlc_profile "
            "WHERE tenant_id = :tid"
        ),
        {"tid": str(TENANT_ID)},
    ).first()

    display_name = "Pilot Dev Tenant LLC"
    public_email = "support@pilotdevtenant.example.com"
    public_phone = "+15125551000"
    public_city = "Austin"
    public_state = "TX"

    if profile:
        display_name = profile.dba_name or profile.legal_business_name
        public_email = profile.support_email or public_email
        public_phone = profile.support_phone or public_phone
        public_city = profile.hq_city or public_city
        public_state = profile.hq_state or public_state

    # Create a temporary site object for snapshot building
    temp_site = TenantSite(
        tenant_id=TENANT_ID,
        slug=SITE_SLUG,
        site_kind="hosted_compliance",
        status="published",
        display_name=display_name,
        tagline="Residential & commercial electrical — Austin, TX",
        public_email=public_email,
        public_phone=public_phone,
        public_city=public_city,
        public_state=public_state,
        show_full_address=False,
        template_version="v1",
    )

    # Build the snapshot
    snapshot = build_snapshot(db, temp_site)

    import json

    now = datetime.now(UTC)

    # Insert the published site row
    db.execute(
        text(
            """
            INSERT INTO public.tenant_site
                (tenant_id, slug, site_kind, status, display_name, tagline,
                 public_email, public_phone, public_city, public_state,
                 show_full_address, template_version, published_snapshot,
                 published_at, website_auto_populated,
                 created_at, updated_at, created_by, updated_by)
            VALUES
                (:tenant_id, :slug, 'hosted_compliance', 'published',
                 :display_name, :tagline,
                 :public_email, :public_phone, :public_city, :public_state,
                 false, 'v1', :snapshot,
                 :now, true,
                 :now, :now, :owner_id, :owner_id)
            ON CONFLICT (tenant_id) DO NOTHING
            """
        ),
        {
            "tenant_id": str(TENANT_ID),
            "slug": SITE_SLUG,
            "display_name": display_name,
            "tagline": "Residential & commercial electrical — Austin, TX",
            "public_email": public_email,
            "public_phone": public_phone,
            "public_city": public_city,
            "public_state": public_state,
            "snapshot": json.dumps(snapshot),
            "now": now,
            "owner_id": str(OWNER_USER_ID),
        },
    )
    db.commit()
    print(
        f"  ✅ [tenant_site] Created published hosted_compliance site "
        f"(slug='{SITE_SLUG}', display_name='{display_name}')"
    )


def inspect_tenant_site(db):
    """Show current tenant_site state."""
    rows = db.execute(
        text(
            "SELECT slug, site_kind, status, display_name, published_at "
            "FROM public.tenant_site ORDER BY slug"
        )
    ).fetchall()

    if not rows:
        print("\n  [tenant_site]  0 row(s)  ← NOT SEEDED")
        return

    print(f"\n  [tenant_site]  {len(rows)} row(s)")
    for r in rows:
        print(
            f"    slug='{r.slug}'  kind={r.site_kind}  status={r.status}  "
            f"display_name='{r.display_name}'"
        )


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Seed C-B16 tenant_site scenario data")
    parser.add_argument(
        "--mode",
        choices=["seed", "inspect"],
        default="seed",
        help="seed (default) or inspect",
    )
    add_env_args(parser)
    args = parser.parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "D", "seed_scenario_tenant_site.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if args.mode in ("seed", "inspect"):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_scenario_tenant_site.py")

    with get_db_session() as db:
        if args.mode == "inspect":
            inspect_tenant_site(db)
        else:
            print("Seeding C-B16 tenant_site scenario data...")
            seed_tenant_site(db)
            inspect_tenant_site(db)
            print("\nDone.")


if __name__ == "__main__":
    main()
