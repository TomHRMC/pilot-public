"""
seed_second_tenant.py — Group C: Second dev/test tenant (SD-9).

Purpose: Creates a second tenant (Pilot Dev Tenant B, id …-0006) with two users
(owner …-0007, technician …-0008) so tenant isolation can be visually and
verifiably tested. Deliberately minimal — no subscription, labor rates, or Group D
business entities (design §G-3). Cognito pool users are out of scope (DB rows only).

NEVER run in production (Group C gating refuses prod).

Modes:
  --mode seed     (default) idempotent upsert of tenant-B + 2 users + tenant_user + email endpoints
  --mode inspect  show current state of tenant-B rows
  --mode show     print definitions, no DB
  --reset         FK-ordered wipe of tenant-B only (never touches tenant-1 data)

Injectable inner functions (_seed_tenant_b / _reset_tenant_b) accept an open
connection so tests can call them against the rollback-wrapped db_session fixture
without committing to the shared dev DB (design §F.6).
"""

import argparse
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
    assert_group_allowed,
    assert_target_compatible,
    print_seed_banner,
    resolve_profile_from_args,
)

# ── SEED DATA CONFIG ─────────────────────────────────────────────────────────

SECOND_TENANT_ID = UUID("00000000-0000-0000-0000-000000000006")
TENANT_B_OWNER_ID = UUID("00000000-0000-0000-0000-000000000007")
TENANT_B_TECH_ID = UUID("00000000-0000-0000-0000-000000000008")

TENANT_B_NAME = "Pilot Dev Tenant B"

OWNER_B_EMAIL = "devb@pilot.local"
OWNER_B_FIRST_NAME = "Dev"
OWNER_B_LAST_NAME = "Owner B"
OWNER_B_DISPLAY_COLOR = "#EF4444"  # red

TECH_B_EMAIL = "techb@pilot.local"
TECH_B_FIRST_NAME = "Dev"
TECH_B_LAST_NAME = "Technician B"
TECH_B_DISPLAY_COLOR = "#06B6D4"  # cyan


# ── INJECTABLE INNER FUNCTIONS (test-isolation seam, design §F.6) ────────────


def _seed_tenant_b(db) -> dict[str, int]:
    """All DB work for tenant-B upsert. Accepts an open connection/session.

    Returns a dict of per-table new-row counts (0 on idempotent re-run).
    Mirrors seed_test_tenant.py upsert pattern: charter tier + active status
    looked up by business key at runtime (never hardcoded UUIDs — DB-MGMT-1
    Task-4 precedent). CONFLICT path omits created_by (immutable trigger).
    """
    counts = {"tenant": 0, "user": 0, "tenant_user": 0, "user_endpoint": 0}
    tid = str(SECOND_TENANT_ID)
    owner_id = str(TENANT_B_OWNER_ID)
    tech_id = str(TENANT_B_TECH_ID)

    # ── 1. Runtime lookups (charter tier, active tenant_user_status) ──────────
    charter_tier = db.execute(
        text(
            "SELECT tier_id FROM public.subscription_tier "
            "WHERE tier_name = 'charter' LIMIT 1"
        )
    ).first()
    if not charter_tier:
        raise RuntimeError(
            "No 'charter' subscription_tier found — run seed_platform.py first."
        )
    tier_id = str(charter_tier.tier_id)

    active_status = db.execute(
        text(
            "SELECT id FROM public.tenant_user_status "
            "WHERE code = 'active' AND tenant_id IS NULL LIMIT 1"
        )
    ).first()
    if not active_status:
        raise RuntimeError(
            "No 'active' tenant_user_status (tenant_id IS NULL) — run seed_core.py first."
        )
    active_status_id = str(active_status.id)

    # ── 2. Users first (required so tenant.created_by FK is valid on INSERT) ──
    users = [
        {
            "id": owner_id,
            "email": OWNER_B_EMAIL,
            "first_name": OWNER_B_FIRST_NAME,
            "last_name": OWNER_B_LAST_NAME,
            "display_color": OWNER_B_DISPLAY_COLOR,
        },
        {
            "id": tech_id,
            "email": TECH_B_EMAIL,
            "first_name": TECH_B_FIRST_NAME,
            "last_name": TECH_B_LAST_NAME,
            "display_color": TECH_B_DISPLAY_COLOR,
        },
    ]
    for u in users:
        # Existence check to count new rows (upsert is idempotent but we want counts)
        existed = db.execute(
            text('SELECT 1 FROM public."user" WHERE id = :id'),
            {"id": u["id"]},
        ).first()
        db.execute(
            text("""
                INSERT INTO public."user"
                (id, email, first_name, last_name, is_active, display_color,
                 email_verified_at, created_at, updated_at)
                VALUES (:id, :email, :first_name, :last_name, true, :display_color,
                        NOW(), NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                    SET email = EXCLUDED.email,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        display_color = EXCLUDED.display_color,
                        updated_at = NOW()
            """),
            u,
        )
        if not existed:
            counts["user"] += 1
            print(f"  ✅ [user] Created {u['email']} ({u['id']})")
        else:
            print(f"  i️  [user] {u['email']} already exists (upserted)")

    # ── 3. Tenant (after users so FK created_by is valid on INSERT) ───────────
    # Upsert: INSERT on first run sets created_by=owner_id.
    # immutable trigger blocks UPDATE of created_by, so CONFLICT path omits it.
    existed_tenant = db.execute(
        text("SELECT 1 FROM public.tenant WHERE id = :id"),
        {"id": tid},
    ).first()
    db.execute(
        text("""
            INSERT INTO public.tenant
            (id, name, is_active, current_subscription_tier_id, created_by,
             stripe_customer_id, created_at, updated_at)
            VALUES (:id, :name, true, :tier_id, :created_by, NULL, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    current_subscription_tier_id = EXCLUDED.current_subscription_tier_id,
                    updated_at = NOW()
        """),
        {
            "id": tid,
            "name": TENANT_B_NAME,
            "tier_id": tier_id,
            "created_by": owner_id,
        },
    )
    if not existed_tenant:
        counts["tenant"] += 1
        print(f"  ✅ [tenant] Created '{TENANT_B_NAME}' ({SECOND_TENANT_ID})")
    else:
        print(f"  i️  [tenant] '{TENANT_B_NAME}' already exists (upserted)")

    # ── 4. UserEndpoint (email channel only per user) ─────────────────────────
    # Mirrors the tenant-1 email endpoint shape: is_primary=true, verified, opted_in.
    for u in users:
        existing_ep = db.execute(
            text(
                "SELECT id FROM public.user_endpoint "
                "WHERE user_id = :uid AND channel = 'email'"
            ),
            {"uid": u["id"]},
        ).first()
        if existing_ep:
            # UPDATE value in-place (safe — guard triggers only block is_primary demotion)
            db.execute(
                text("""
                    UPDATE public.user_endpoint
                    SET value = :email, updated_at = NOW()
                    WHERE user_id = :uid AND channel = 'email'
                """),
                {"uid": u["id"], "email": u["email"]},
            )
            print(f"  i️  [user_endpoint] Updated email → {u['email']}")
        else:
            db.execute(
                text("""
                    INSERT INTO public.user_endpoint
                    (id, user_id, channel, value, is_primary, verification_status,
                     consent_status, is_active, created_at, updated_at)
                    VALUES (gen_random_uuid(), :uid, 'email', :email, true, 'verified',
                            'opted_in', true, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {"uid": u["id"], "email": u["email"]},
            )
            counts["user_endpoint"] += 1
            print(f"  ✅ [user_endpoint] Created email endpoint for {u['email']}")

    # ── 5. TenantUser rows (owner=master/EMP-B01, tech=journeyman/EMP-B02) ────
    role_map = [
        (owner_id, "owner", "master", "EMP-B01"),
        (tech_id, "technician", "journeyman", "EMP-B02"),
    ]
    for uid, role, skill, emp_num in role_map:
        existing_tu = db.execute(
            text(
                "SELECT 1 FROM public.tenant_user "
                "WHERE tenant_id = :tid AND user_id = :uid"
            ),
            {"tid": tid, "uid": uid},
        ).first()
        if existing_tu:
            # Update skill/emp on existing row (idempotent correction)
            db.execute(
                text("""
                    UPDATE public.tenant_user
                    SET role_code = :role, status_id = :status_id,
                        skill_level_code = :skill, employee_number = :emp,
                        is_active = true, updated_at = NOW()
                    WHERE tenant_id = :tid AND user_id = :uid
                """),
                {
                    "tid": tid,
                    "uid": uid,
                    "role": role,
                    "status_id": active_status_id,
                    "skill": skill,
                    "emp": emp_num,
                },
            )
            print(f"  i️  [tenant_user] {uid} already linked (role={role}, updated)")
        else:
            db.execute(
                text("""
                    INSERT INTO public.tenant_user
                    (tenant_id, user_id, role_code, status_id, skill_level_code,
                     employee_number, is_active, joined_at, created_at, updated_at)
                    VALUES (:tid, :uid, :role, :status_id, :skill, :emp,
                            true, NOW(), NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tid": tid,
                    "uid": uid,
                    "role": role,
                    "status_id": active_status_id,
                    "skill": skill,
                    "emp": emp_num,
                },
            )
            counts["tenant_user"] += 1
            print(f"  ✅ [tenant_user] Linked {uid} as {role} ({skill}/{emp_num})")

    return counts


def _reset_tenant_b(db) -> dict[str, int]:
    """FK-ordered wipe of tenant-B only. Never touches tenant-1 data.

    Order: voice tables (all 5) → tenant_user → user_endpoint → tenant → user rows.
    The user rows …-0007/…-0008 are deleted last (their user_endpoint rows first).
    """
    counts: dict[str, int] = {}
    tid = str(SECOND_TENANT_ID)
    owner_id = str(TENANT_B_OWNER_ID)
    tech_id = str(TENANT_B_TECH_ID)

    # ── Voice tables (tenant-B voice rows, if any — wiped first, child-first) ──
    voice_tables = [
        "voice_feedback",
        "voice_command_entity_link",
        "voice_command_log",
        "conversation_message",
        "conversation_session",
    ]
    for table in voice_tables:
        result = db.execute(
            text(f"DELETE FROM public.{table} WHERE tenant_id = :tid"),
            {"tid": tid},
        )
        if result.rowcount:
            counts[table] = result.rowcount
            print(f"  🗑  [{table}] Deleted {result.rowcount} row(s)")

    # ── tenant_user (tenant-B links) ──────────────────────────────────────────
    result = db.execute(
        text("DELETE FROM public.tenant_user WHERE tenant_id = :tid"),
        {"tid": tid},
    )
    if result.rowcount:
        counts["tenant_user"] = result.rowcount
        print(f"  🗑  [tenant_user] Deleted {result.rowcount} row(s)")

    # ── user_endpoint (tenant-B users' endpoints) ─────────────────────────────
    for uid in (owner_id, tech_id):
        result = db.execute(
            text("DELETE FROM public.user_endpoint WHERE user_id = :uid"),
            {"uid": uid},
        )
        if result.rowcount:
            counts["user_endpoint"] = counts.get("user_endpoint", 0) + result.rowcount
            print(f"  🗑  [user_endpoint] Deleted {result.rowcount} row(s) for {uid}")

    # ── tenant (tenant-B row) ─────────────────────────────────────────────────
    result = db.execute(
        text("DELETE FROM public.tenant WHERE id = :tid"),
        {"tid": tid},
    )
    if result.rowcount:
        counts["tenant"] = result.rowcount
        print(f"  🗑  [tenant] Deleted '{TENANT_B_NAME}' ({tid})")

    # ── user rows (…-0007, …-0008 — deleted last after their endpoints) ──────
    for uid in (owner_id, tech_id):
        result = db.execute(
            text('DELETE FROM public."user" WHERE id = :uid'),
            {"uid": uid},
        )
        if result.rowcount:
            counts["user"] = counts.get("user", 0) + result.rowcount
            print(f"  🗑  [user] Deleted {uid}")

    return counts


# ── PUBLIC MODE WRAPPERS (open session, call inner fn, commit) ───────────────


def mode_seed(tenant_id: UUID = SECOND_TENANT_ID) -> None:
    """Idempotent upsert of tenant-B + 2 users + tenant_user + email endpoints."""
    print("=== seed_second_tenant: seed mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    with get_db_session() as db:
        counts = _seed_tenant_b(db)
        db.commit()

    total_new = sum(counts.values())
    print(f"\n🎉 seed_second_tenant complete — {total_new} new row(s) for {tenant_id}")


def mode_reset(tenant_id: UUID = SECOND_TENANT_ID) -> None:
    """FK-ordered wipe of tenant-B only."""
    print("=== seed_second_tenant: reset mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    with get_db_session() as db:
        counts = _reset_tenant_b(db)
        db.commit()

    total_del = sum(counts.values())
    print(f"\n✅ Tenant-B reset complete — {total_del} row(s) deleted.")


def mode_inspect() -> None:
    """Show current state of tenant-B rows."""
    print("=== seed_second_tenant: inspect mode ===\n")

    tid = str(SECOND_TENANT_ID)

    with get_db_session() as db:
        t = db.execute(
            text(
                "SELECT id, name, is_active, current_subscription_tier_id "
                "FROM public.tenant WHERE id = :tid"
            ),
            {"tid": tid},
        ).first()
        if t:
            print("  [tenant]  1 row(s)")
            print(f"    {t.id}  '{t.name}'  is_active={t.is_active}")
        else:
            print("  [tenant]  0 row(s)  ← NOT SEEDED")
        print()

        users = db.execute(
            text("""
                SELECT u.id, u.email, u.first_name, u.last_name, u.display_color,
                       tu.role_code, tu.skill_level_code, tu.employee_number
                FROM public."user" u
                JOIN public.tenant_user tu ON tu.user_id = u.id
                WHERE tu.tenant_id = :tid
                ORDER BY tu.role_code
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [user]  {len(users)} row(s)")
        for u in users:
            print(
                f"    {u.id}  {u.email}  role={u.role_code}  "
                f"skill={u.skill_level_code}  emp={u.employee_number}  "
                f"color={u.display_color}"
            )
        print()

        endpoints = db.execute(
            text("""
                SELECT ue.user_id, ue.channel, ue.value, ue.verification_status,
                       ue.consent_status, ue.is_primary
                FROM public.user_endpoint ue
                JOIN public.tenant_user tu ON tu.user_id = ue.user_id
                WHERE tu.tenant_id = :tid
                ORDER BY ue.user_id, ue.channel
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [user_endpoint]  {len(endpoints)} row(s)")
        for e in endpoints:
            print(
                f"    user={e.user_id}  channel={e.channel}  value={e.value}  "
                f"status={e.verification_status}  consent={e.consent_status}  "
                f"primary={e.is_primary}"
            )
        print()

        # Voice table counts (tenant-B side — seeded by seed_scenario_voice_ai.py)
        print("  [voice tables — tenant-B side]")
        for table in [
            "conversation_session",
            "conversation_message",
            "voice_command_log",
            "voice_command_entity_link",
            "voice_feedback",
        ]:
            count = db.execute(
                text(f"SELECT COUNT(*) FROM public.{table} WHERE tenant_id = :tid"),
                {"tid": tid},
            ).scalar()
            print(f"    {table:<35} {count} row(s)")


def mode_show() -> None:
    """Print what would be seeded without touching the DB."""
    print("=== seed_second_tenant: show mode ===\n")
    print(f"Tenant ID: {SECOND_TENANT_ID}")
    print(
        f"  [tenant]                  name='{TENANT_B_NAME}'  charter tier (runtime lookup)"
    )
    print(
        f"  [user] owner              {TENANT_B_OWNER_ID}  email={OWNER_B_EMAIL}  "
        f"color={OWNER_B_DISPLAY_COLOR}"
    )
    print(
        f"  [user] technician         {TENANT_B_TECH_ID}  email={TECH_B_EMAIL}  "
        f"color={TECH_B_DISPLAY_COLOR}"
    )
    print("  [user_endpoint]           2 rows (email channel only per user)")
    print(
        "  [tenant_user]             2 rows (owner=master/EMP-B01, "
        "technician=journeyman/EMP-B02)"
    )


# ── CLI ──────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="seed_second_tenant.py — Group C second-tenant seeder (SD-9)"
    )
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "C", "seed_second_tenant.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(
        args, "reset", False
    ):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_second_tenant.py")

    if args.reset:
        mode_reset()
    elif args.mode == "seed":
        mode_seed()
    elif args.mode == "inspect":
        mode_inspect()
    elif args.mode == "show":
        mode_show()
