"""
seed_test_tenant.py — Group C: Dev/test tenant infrastructure.

Purpose: Creates the canonical dev/test tenant, 3 users (owner/tech/office),
tenant configuration, and pricing engine rows. NEVER run in production.

⚠️  Subscription row requires product_plan rows from seed_platform.py.
    Run seed_platform.py first, then run this script, or run this script
    twice (2nd run creates subscription after plans exist).

Modes:
  --mode seed     (default) Insert all Group C rows; idempotent
  --mode inspect  Show current state of all Group C tables
  --mode show     Print what would be seeded; no DB required
  --reset         Wipe Group C data (+ cascades to Group D) then exit
  --tenant-id     Override tenant UUID (default: settings.TEST_TENANT_ID)

Usage:
  python migrations/scripts/seed_test_tenant.py
  python migrations/scripts/seed_test_tenant.py --mode inspect
  python migrations/scripts/seed_test_tenant.py --mode show
  python migrations/scripts/seed_test_tenant.py --reset
"""

import argparse
import hashlib
import json
import os
import sys
import time
from decimal import Decimal
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

# ── SEED DATA CONFIG ─────────────────────────────────────────────────────────

TENANT_NAME = "Pilot Dev Tenant"

# Deterministic UUIDs — never use uuid4() so re-runs are idempotent.
TECH_USER_ID = UUID("00000000-0000-0000-0000-000000000003")
OFFICE_USER_ID = UUID("00000000-0000-0000-0000-000000000004")
ACCOUNTANT_USER_ID = UUID("00000000-0000-0000-0000-000000000005")  # SD-4

OWNER_EMAIL = "dev@pilot.local"
OWNER_FIRST_NAME = "Dev"
OWNER_LAST_NAME = "Owner"
OWNER_DISPLAY_COLOR = "#10B981"  # green — SD-4

TECH_EMAIL = "tech@pilot.local"
TECH_FIRST_NAME = "Dev"
TECH_LAST_NAME = "Technician"
TECH_DISPLAY_COLOR = "#3B82F6"  # blue — dispatch board calendar

OFFICE_EMAIL = "office@pilot.local"
OFFICE_FIRST_NAME = "Dev"
OFFICE_LAST_NAME = "Office"
OFFICE_DISPLAY_COLOR = "#F59E0B"  # amber — SD-4

ACCOUNTANT_EMAIL = "accountant@pilot.local"  # SD-4
ACCOUNTANT_FIRST_NAME = "Dev"
ACCOUNTANT_LAST_NAME = "Accountant"
ACCOUNTANT_DISPLAY_COLOR = "#8B5CF6"  # purple — SD-4

# SD-4: Test-mode Stripe customer ID (created 2026-07-14)
STRIPE_CUSTOMER_ID_TEST = "cus_REDACTEDX01"

# SD-4: Custom footer for tenant_email_branding
CUSTOM_FOOTER = "© 2026 Pilot Dev Tenant. All rights reserved."

# STRIPE-CONNECT-1-B2: Billing contact shown on the public invoice manual-payment panel
BILLING_CONTACT_PHONE = "(804) 555-0142"
BILLING_CONTACT_EMAIL = "billing@pilotdevtenant.example.com"

# SD-4: Deterministic fake Expo push tokens (test-only — no real device registration)
PUSH_TOKENS = {
    "00000000-0000-0000-0000-000000000002": "ExponentPushToken[test-owner-00000002]",
    "00000000-0000-0000-0000-000000000003": "ExponentPushToken[test-tech-00000003]",
    "00000000-0000-0000-0000-000000000004": "ExponentPushToken[test-office-00000004]",
    "00000000-0000-0000-0000-000000000005": "ExponentPushToken[test-acct-00000005]",
}

LABOR_RATE_MASTER = 12000  # cents/hr = $120.00
LABOR_RATE_JOURNEYMAN = 8500  # cents/hr = $85.00
LABOR_RATE_APPRENTICE = 5500  # cents/hr = $55.00
MARKUP_PCT = 20.0

PASSWORD_MIN_LENGTH = 8
PASSWORD_MIN_UPPERCASE = 1
PASSWORD_MIN_DIGITS = 1

# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(description="seed_test_tenant.py — Group C seeder")
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--reset", action="store_true")
    add_env_args(parser)
    return parser.parse_args()


def _get_tenant_id(args=None) -> UUID:
    if args and args.tenant_id:
        return UUID(args.tenant_id)
    return UUID(settings.TEST_TENANT_ID)


def _get_owner_id() -> UUID:
    return UUID(settings.TEST_USER_ID)


def mode_reset(tenant_id: UUID):
    """Reset Group C config data. Wipes Group D and clears tenant config rows.

    IMPORTANT: user, user_endpoint, and tenant rows are UPDATED in-place, not deleted.
    These rows have 150+ FK children across the schema — deleting them cascades
    unpredictably and breaks test fixtures. The deterministic UUIDs are permanent;
    only stale name/email values are corrected.
    """
    print("⚠️  WARNING: --reset will wipe Group D data and clear Group C config rows.")
    print(
        "    tenant, user, and user_endpoint rows are UPDATED in-place (not deleted)."
    )
    print("    Group A (lookup tables) and Group B (platform config) are NOT affected.")
    print("    Press Ctrl+C to abort. Proceeding in 3 seconds...")
    time.sleep(3)

    tid = str(tenant_id)
    owner_id = str(_get_owner_id())

    with get_db_session() as db:
        # ── Delete Group D (all tenant-scoped scenario data) ─────────────────
        # IMPORTANT: strict child-first FK order derived from pg_constraint audit.
        # Uses SAVEPOINT per table so a missing table or constraint violation does
        # not poison the whole transaction.
        # Each entry is either a table name string (DELETE WHERE tenant_id = :tid)
        # or a (table_name, custom_sql) tuple for tables without tenant_id.
        # IMPORTANT: strict child-first FK order derived from pg_constraint audit.
        group_d_deletes = [
            # ── Deepest children first ────────────────────────────────────────
            "loto_confirmation",
            "calendar_sync_conflict",
            "job_tech_assignment",
            "job_time_entry",
            "job_expense",
            "job_notes",
            "job_attachment",
            "change_order_line_tax_component",  # ← SD-7 B1: child of change_order_line
            "change_order_line",
            "change_order",
            "tech_availability",
            # ── Quote children (must all precede quote) ───────────────────────
            "quote_acceptance",  # ← SD-7 B1: child of quote_version
            "quote_line_tax_component",  # ← SD-7 B1: child of quote_line
            "quote_line",
            "quote_version",
            "quote_public_link_contact_action",  # ← child of quote_public_link
            "quote_public_link",  # ← child of quote
            "quote_message",  # ← child of quote
            "quote_pending_edit",  # ← child of quote
            "quote_approval_comment",  # ← child of quote
            # ── Invoice children (must all precede invoice) ───────────────────
            "invoice_line_tax_component",  # ← child of invoice_line
            "invoice_line",  # ← child of invoice
            "invoice_public_link",  # ← child of invoice
            "payment",  # ← child of invoice
            # ── Other children ────────────────────────────────────────────────
            "mobile_sync_owner_escalation",  # ← SD-6 / W-12 escalations
            "in_app_notification",  # ← SD-6 notifications
            # ── invoice + job + quote (after all their children) ─────────────
            "invoice",
            "customer_communication",  # ← child of job + customer (before both)
            "job_recurrence_rule",  # ← child of site + customer
            "job",
            "quote",  # ← must precede site (site_id FK)
            "pricebook_item_version",
            "pricebook_item",
            "entity_address",
            "entity_contact",
            # contact_endpoint: not seeded — channel chk allows only email|sms; sms is on hold
            "contact",
            "address",  # ← after entity_address
            "site",
            # ── Customer children (before customer) ──────────────────────────
            "customer_sms_consent_audit",  # ← child of customer
            "psp_customer",  # ← child of customer
            "payment_method",  # ← child of customer
            # customer_communication_message_read_state — delete via subquery (no tenant_id)
            (
                "customer_communication_message_read_state",
                "DELETE FROM public.customer_communication_message_read_state "
                "WHERE message_id IN ("
                "  SELECT m.id FROM public.customer_communication_message m "
                "  JOIN public.customer_communication_thread t ON t.id = m.thread_id "
                "  WHERE t.tenant_id = :tid"
                ")",
            ),
            # customer_communication_message has no tenant_id — delete via thread_id subquery
            (
                "customer_communication_message",
                "DELETE FROM public.customer_communication_message WHERE thread_id IN "
                "(SELECT id FROM public.customer_communication_thread WHERE tenant_id = :tid)",
            ),
            "customer_communication_unrouted",  # ← SD-7 B3: parked inbound SMS
            "customer_communication_thread",  # ← child of customer + tenant_phone_number
            "customer",
            "tenant_phone_number",  # ← SD-02 customer_comms
            # ── Supplier catalog ─────────────────────────────────────────────
            "supplier_item_price",  # ← SD-09 (price → item → supplier)
            "supplier_item",
            "supplier",
            # ── Mobile sync + NEC ─────────────────────────────────────────────
            "mobile_sync_event",  # ← E2E-B1 (event → session)
            "mobile_sync_session",
            "nec_calculation_log",  # ← E2E-B1
        ]
        for entry in group_d_deletes:
            if isinstance(entry, tuple):
                table, sql = entry
            else:
                table = entry
                sql = f"DELETE FROM public.{table} WHERE tenant_id = :tid"
            sp = f"sp_reset_{table}"
            try:
                db.execute(text(f"SAVEPOINT {sp}"))
                result = db.execute(text(sql), {"tid": tid})
                db.execute(text(f"RELEASE SAVEPOINT {sp}"))
                if result.rowcount:
                    print(f"  🗑  [{table:<35}] Deleted {result.rowcount} row(s)")
            except Exception as exc:
                db.execute(text(f"ROLLBACK TO SAVEPOINT {sp}"))
                print(f"  ⚠️  [{table:<35}] Skipped ({type(exc).__name__})")

        # ── Delete Group C config rows (safe — these are direct tenant children) ──
        group_c_config_tables = [
            "notification_delivery_attempt",  # ← SD-7 B2: child of notification_outbox (via outbox's tenant_id)
            "notification_outbox",  # ← SD-7 B2: child of notification_event
            "notification_event",  # ← SD-7 B2
            "notification_preference",  # ← SD-7 B2
            "mobile_device_push_token",  # ← SD-7 B2
            "subscription_usage",  # ← SD-7 B2
            "tenant_subscription_usage",  # ← SD-7 B2
            "user_dashboard_widget",  # ← SD-7 B2
            "tenant_10dlc_profile",  # ← SD-7 B2
            "discount_version",  # ← SD-4 (must precede subscription)
            "labor_rate_version",
            "tenant_markup_version",
            "subscription",
            "password_policy",
            "tenant_email_branding",
            "tenant_onboarding_checklist",
            "user_preference",  # ← SD-6
            "user_setting_override",  # ← SD-6
        ]
        # SD-7 B1: auth_jwk has tenant_id IS NULL — delete by kid, not by tenant_id
        sp = "sp_reset_auth_jwk"
        try:
            db.execute(text(f"SAVEPOINT {sp}"))
            result = db.execute(
                text("DELETE FROM public.auth_jwk WHERE kid = :kid"),
                {"kid": "pilot-dev-signing-key-v1"},
            )
            db.execute(text(f"RELEASE SAVEPOINT {sp}"))
            if result.rowcount:
                print(f"  🗑  [auth_jwk{'':<31}] Deleted {result.rowcount} row(s)")
        except Exception as exc:
            db.execute(text(f"ROLLBACK TO SAVEPOINT {sp}"))
            print(f"  ⚠️  [auth_jwk{'':<31}] Skipped ({type(exc).__name__})")
        for table in group_c_config_tables:
            sp = f"sp_reset_{table}"
            try:
                db.execute(text(f"SAVEPOINT {sp}"))
                result = db.execute(
                    text(f"DELETE FROM public.{table} WHERE tenant_id = :tid"),
                    {"tid": tid},
                )
                db.execute(text(f"RELEASE SAVEPOINT {sp}"))
                if result.rowcount:
                    print(f"  🗑  [{table:<35}] Deleted {result.rowcount} row(s)")
            except Exception as exc:
                db.execute(text(f"ROLLBACK TO SAVEPOINT {sp}"))
                print(f"  ⚠️  [{table:<35}] Skipped ({type(exc).__name__})")

        # ── Delete tenant_user links (safe — only links tenant↔user, no further deps) ──
        sp = "sp_reset_tenant_user"
        db.execute(text(f"SAVEPOINT {sp}"))
        result = db.execute(
            text("DELETE FROM public.tenant_user WHERE tenant_id = :tid"), {"tid": tid}
        )
        db.execute(text(f"RELEASE SAVEPOINT {sp}"))
        if result.rowcount:
            print(f"  🗑  [tenant_user{'':<26}] Deleted {result.rowcount} row(s)")

        # ── UPDATE tenant in-place (never delete — has FK children) ──────────
        db.execute(
            text("""
                UPDATE public.tenant
                SET name = :name, updated_at = NOW()
                WHERE id = :tid
            """),
            {"tid": tid, "name": TENANT_NAME},
        )
        print(f"  ✅ [tenant] Updated name → '{TENANT_NAME}'")

        # ── STRIPE-CONNECT-1-B2: billing contact for the manual-payment panel ──
        db.execute(
            text("""
                UPDATE public.tenant
                SET billing_contact_phone = :phone,
                    billing_contact_email = :email,
                    updated_at = NOW()
                WHERE id = :tid
            """),
            {
                "tid": tid,
                "phone": BILLING_CONTACT_PHONE,
                "email": BILLING_CONTACT_EMAIL,
            },
        )
        print(
            f"  ✅ [tenant] Updated billing_contact → phone='{BILLING_CONTACT_PHONE}'  email='{BILLING_CONTACT_EMAIL}'"
        )

        # ── UPDATE users in-place (never delete — 150+ FK children) ─────────
        users = [
            {
                "id": owner_id,
                "email": OWNER_EMAIL,
                "first_name": OWNER_FIRST_NAME,
                "last_name": OWNER_LAST_NAME,
                "display_color": OWNER_DISPLAY_COLOR,
            },
            {
                "id": str(TECH_USER_ID),
                "email": TECH_EMAIL,
                "first_name": TECH_FIRST_NAME,
                "last_name": TECH_LAST_NAME,
                "display_color": TECH_DISPLAY_COLOR,
            },
            {
                "id": str(OFFICE_USER_ID),
                "email": OFFICE_EMAIL,
                "first_name": OFFICE_FIRST_NAME,
                "last_name": OFFICE_LAST_NAME,
                "display_color": OFFICE_DISPLAY_COLOR,
            },
            {
                "id": str(ACCOUNTANT_USER_ID),
                "email": ACCOUNTANT_EMAIL,
                "first_name": ACCOUNTANT_FIRST_NAME,
                "last_name": ACCOUNTANT_LAST_NAME,
                "display_color": ACCOUNTANT_DISPLAY_COLOR,
            },
        ]
        for u in users:
            exists = db.execute(
                text('SELECT 1 FROM public."user" WHERE id = :id'), {"id": u["id"]}
            ).first()
            if exists:
                db.execute(
                    text("""
                        UPDATE public."user"
                        SET email = :email, first_name = :first_name,
                            last_name = :last_name, display_color = :display_color,
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    u,
                )
                print(f"  ✅ [user] Updated {u['email']} ({u['id']})")
            else:
                print(
                    f"  i️  [user] {u['id']} not present — will be created by mode_seed"
                )

        # ── UPDATE user_endpoint value in-place ───────────────────────────────
        # Updating value (email address) is safe — the guard trigger only blocks
        # demotion of is_primary, not value changes.
        for u in users:
            ep_exists = db.execute(
                text(
                    "SELECT 1 FROM public.user_endpoint WHERE user_id = :uid AND channel = 'email'"
                ),
                {"uid": u["id"]},
            ).first()
            if ep_exists:
                db.execute(
                    text("""
                        UPDATE public.user_endpoint
                        SET value = :email, updated_at = NOW()
                        WHERE user_id = :uid AND channel = 'email'
                    """),
                    {"uid": u["id"], "email": u["email"]},
                )
                print(f"  ✅ [user_endpoint] Updated email → {u['email']}")

        db.commit()

    print("\n✅ Group C reset complete — config wiped, users/tenant updated in-place.")
    print("   Run: python migrations/scripts/seed_test_tenant.py")
    print("   to re-seed Group C config rows.")


def mode_seed(tenant_id: UUID):
    """Seed Group C: tenant, users, config, pricing engine."""
    print("=== seed_test_tenant: seed mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    owner_id = _get_owner_id()
    tid = str(tenant_id)

    with get_db_session() as db:
        # ── 1. Tenant lookup: charter tier ─────────────────────────────────
        # MKT-B11 / C-B1: Use charter tier explicitly (not is_trial=true; charter is is_trial=false)
        charter_tier = db.execute(
            text(
                "SELECT tier_id FROM public.subscription_tier WHERE tier_name = 'charter' LIMIT 1"
            )
        ).first()
        if not charter_tier:
            print(
                "  ❌ [tenant] No 'charter' subscription_tier found — cannot create tenant."
            )
            print("      Run the MKT-B11 Alembic migration first.")
            return

        # ── 2. Users first (required so tenant.created_by FK is valid) ──────
        users = [
            {
                "id": str(owner_id),
                "email": OWNER_EMAIL,
                "first_name": OWNER_FIRST_NAME,
                "last_name": OWNER_LAST_NAME,
                "display_color": OWNER_DISPLAY_COLOR,
            },
            {
                "id": str(TECH_USER_ID),
                "email": TECH_EMAIL,
                "first_name": TECH_FIRST_NAME,
                "last_name": TECH_LAST_NAME,
                "display_color": TECH_DISPLAY_COLOR,
            },
            {
                "id": str(OFFICE_USER_ID),
                "email": OFFICE_EMAIL,
                "first_name": OFFICE_FIRST_NAME,
                "last_name": OFFICE_LAST_NAME,
                "display_color": OFFICE_DISPLAY_COLOR,
            },
            {
                "id": str(ACCOUNTANT_USER_ID),
                "email": ACCOUNTANT_EMAIL,
                "first_name": ACCOUNTANT_FIRST_NAME,
                "last_name": ACCOUNTANT_LAST_NAME,
                "display_color": ACCOUNTANT_DISPLAY_COLOR,
            },
        ]

        for u in users:
            # Upsert: INSERT or UPDATE in-place — never skip stale values.
            # user rows have 150+ FK children; we UPDATE rather than delete+insert.
            db.execute(
                text("""
                    INSERT INTO public."user"
                    (id, email, first_name, last_name, is_active, display_color,
                     created_at, updated_at)
                    VALUES (:id, :email, :first_name, :last_name, true, :display_color,
                            NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE
                        SET email = EXCLUDED.email,
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            display_color = EXCLUDED.display_color,
                            updated_at = NOW()
                """),
                u,
            )
            print(f"  ✅ [user] Upserted {u['email']} ({u['id']})")

        # ── 1. Tenant (after users so FK created_by is valid on INSERT) ─────
        # Upsert: INSERT on first run sets created_by=owner_id.
        # immutable trigger blocks UPDATE of created_by, so CONFLICT path omits it.
        # SD-4: added stripe_customer_id
        db.execute(
            text("""
                INSERT INTO public.tenant
                (id, name, is_active, current_subscription_tier_id, created_by,
                 stripe_customer_id, billing_contact_phone, billing_contact_email,
                 created_at, updated_at)
                VALUES (:id, :name, true, :tier_id, :created_by, :stripe_customer_id,
                        :billing_phone, :billing_email, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        stripe_customer_id = EXCLUDED.stripe_customer_id,
                        billing_contact_phone = EXCLUDED.billing_contact_phone,
                        billing_contact_email = EXCLUDED.billing_contact_email,
                        updated_at = NOW()
            """),
            {
                "id": tid,
                "name": TENANT_NAME,
                "tier_id": str(charter_tier.tier_id),
                "created_by": str(owner_id),
                "stripe_customer_id": STRIPE_CUSTOMER_ID_TEST,
                "billing_phone": BILLING_CONTACT_PHONE,
                "billing_email": BILLING_CONTACT_EMAIL,
            },
        )
        print(f"  ✅ [tenant] Upserted '{TENANT_NAME}' ({tenant_id})")
        print(
            f"  ✅ [tenant] billing_contact → phone='{BILLING_CONTACT_PHONE}'  email='{BILLING_CONTACT_EMAIL}'"
        )

        # ── 3. UserEndpoint (email, in_app, push — 3 channels per user) ─────
        # SD-4: added in_app + push; email remains primary (is_primary=true),
        #        in_app + push are secondary (is_primary=false).
        for u in users:
            existing = db.execute(
                text(
                    "SELECT id FROM public.user_endpoint WHERE user_id = :uid AND channel = 'email'"
                ),
                {"uid": u["id"]},
            ).first()
            if existing:
                # UPDATE value in-place — safe, guard triggers only block is_primary demotion
                db.execute(
                    text("""
                        UPDATE public.user_endpoint
                        SET value = :email, updated_at = NOW()
                        WHERE user_id = :uid AND channel = 'email'
                    """),
                    {"uid": u["id"], "email": u["email"]},
                )
                print(f"  ✅ [user_endpoint] Updated email → {u['email']}")
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
                print(f"  ✅ [user_endpoint] Created email endpoint for {u['email']}")

        # SD-4: in_app + push endpoints for all users.
        # user_endpoint has no unique constraint on (user_id, channel) — PK is UUID id.
        # ON CONFLICT DO NOTHING is a no-op here. Use targeted DELETE + INSERT instead.
        #
        # IMPORTANT: DELETE is scoped to (user_id, channel, value) — the exact rows
        # we're about to insert. This preserves any other in_app/push endpoints the
        # user may have (e.g. real device tokens added via the app).
        #
        # SD-7 B3 fix: wrap DELETE in SAVEPOINT — notification_outbox FK references
        # user_endpoint rows and blocks bare DELETE. If delete fails, skip re-insert
        # (row already exists with correct values).
        for u in users:
            # in_app endpoint
            _sp = f"sp_ue_inapp_{u['id'][:8]}"
            db.execute(text(f"SAVEPOINT {_sp}"))
            try:
                db.execute(
                    text(
                        "DELETE FROM public.user_endpoint "
                        "WHERE user_id = :uid AND channel = 'in_app' AND value = :value"
                    ),
                    {"uid": u["id"], "value": u["email"]},
                )
                db.execute(text(f"RELEASE SAVEPOINT {_sp}"))
                # Only INSERT if delete succeeded (row was replaced)
                db.execute(
                    text("""
                        INSERT INTO public.user_endpoint
                        (id, user_id, channel, value, is_primary, verification_status,
                         consent_status, is_active, created_at, updated_at)
                        VALUES (gen_random_uuid(), :uid, 'in_app', :value, false, 'verified',
                                'opted_in', true, NOW(), NOW())
                    """),
                    {"uid": u["id"], "value": u["email"]},
                )
            except Exception:
                db.execute(text(f"ROLLBACK TO SAVEPOINT {_sp}"))
                # Row exists and is FK-referenced — skip re-insert (already correct)
                pass

            # push endpoint
            push_token = PUSH_TOKENS.get(u["id"])
            if push_token:
                _sp2 = f"sp_ue_push_{u['id'][:8]}"
                db.execute(text(f"SAVEPOINT {_sp2}"))
                try:
                    db.execute(
                        text(
                            "DELETE FROM public.user_endpoint "
                            "WHERE user_id = :uid AND channel = 'push' AND value = :value"
                        ),
                        {"uid": u["id"], "value": push_token},
                    )
                    db.execute(text(f"RELEASE SAVEPOINT {_sp2}"))
                    db.execute(
                        text("""
                            INSERT INTO public.user_endpoint
                            (id, user_id, channel, value, is_primary, verification_status,
                             consent_status, is_active, created_at, updated_at)
                            VALUES (gen_random_uuid(), :uid, 'push', :value, false, 'verified',
                                    'opted_in', true, NOW(), NOW())
                        """),
                        {"uid": u["id"], "value": push_token},
                    )
                except Exception:
                    db.execute(text(f"ROLLBACK TO SAVEPOINT {_sp2}"))
                    pass

        print(
            f"  ✅ [user_endpoint] in_app + push endpoints set for {len(users)} users "
            f"(SAVEPOINT-guarded DELETE+INSERT — skips FK-referenced rows)"
        )

        # ── 4. TenantUser rows ──────────────────────────────────────────────
        active_status = db.execute(
            text(
                "SELECT id FROM public.tenant_user_status WHERE code = 'active' AND tenant_id IS NULL LIMIT 1"
            )
        ).first()
        active_status_id = str(active_status.id) if active_status else None

        role_map = [
            (str(owner_id), "owner"),
            (str(TECH_USER_ID), "technician"),
            (str(OFFICE_USER_ID), "office_staff"),
            (str(ACCOUNTANT_USER_ID), "accountant"),  # SD-4
        ]
        for uid, role in role_map:
            existing = db.execute(
                text(
                    "SELECT 1 FROM public.tenant_user WHERE tenant_id = :tid AND user_id = :uid"
                ),
                {"tid": tid, "uid": uid},
            ).first()
            if existing:
                print(f"  i️  [tenant_user] {uid} already linked (role={role})")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.tenant_user
                        (tenant_id, user_id, role_code, status_id, is_active, created_at, updated_at)
                        VALUES (:tid, :uid, :role, :status_id, true, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "tid": tid,
                        "uid": uid,
                        "role": role,
                        "status_id": active_status_id,
                    },
                )
                print(f"  ✅ [tenant_user] Linked {uid} as {role}")

        # ── 5. Password Policy ───────────────────────────────────────────────
        # SD-4: added lockout/history fields to INSERT + UPDATE patch for existing rows
        existing = db.execute(
            text("SELECT id FROM public.password_policy WHERE tenant_id = :tid"),
            {"tid": tid},
        ).first()
        if existing:
            print("  i️  [password_policy] Already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.password_policy
                    (id, tenant_id, min_length, min_uppercase, min_digits,
                     lockout_threshold, lockout_window_minutes, lockout_duration_minutes,
                     history_depth, rotation_days, require_mfa, created_at, updated_at)
                    VALUES (gen_random_uuid(), :tid, :min_length, :min_uppercase, :min_digits,
                            5, 15, 30, 5, NULL, false, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tid": tid,
                    "min_length": PASSWORD_MIN_LENGTH,
                    "min_uppercase": PASSWORD_MIN_UPPERCASE,
                    "min_digits": PASSWORD_MIN_DIGITS,
                },
            )
            print("  ✅ [password_policy] Created")

        # SD-4: patch existing rows that are missing lockout fields
        db.execute(
            text("""
                UPDATE public.password_policy
                SET lockout_threshold = 5,
                    lockout_window_minutes = 15,
                    lockout_duration_minutes = 30,
                    history_depth = 5,
                    updated_at = NOW()
                WHERE tenant_id = :tid
                  AND lockout_threshold IS NULL
            """),
            {"tid": tid},
        )
        print("  ✅ [password_policy] Lockout/history fields ensured")

        # ── 6. Tenant Email Branding ─────────────────────────────────────────
        # SD-4: added custom_footer to INSERT + UPDATE patch for existing rows
        existing = db.execute(
            text(
                "SELECT tenant_id FROM public.tenant_email_branding WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).first()
        if existing:
            print("  i️  [tenant_email_branding] Already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.tenant_email_branding
                    (tenant_id, brand_color_hex, email_signature, custom_footer, created_at, updated_at)
                    VALUES (:tid, '#2563EB', 'Pilot Dev Tenant — dev only', :footer, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {"tid": tid, "footer": CUSTOM_FOOTER},
            )
            print("  ✅ [tenant_email_branding] Created")

        # SD-4: patch existing rows that have no custom_footer
        db.execute(
            text("""
                UPDATE public.tenant_email_branding
                SET custom_footer = :footer
                WHERE tenant_id = :tid AND custom_footer IS NULL
            """),
            {"tid": tid, "footer": CUSTOM_FOOTER},
        )
        print("  ✅ [tenant_email_branding] custom_footer ensured")

        # ── 7. Tenant Onboarding Checklist (completed state) ────────────────
        # tenant_onboarding_checklist has server defaults of now() for timestamps
        existing = db.execute(
            text(
                "SELECT tenant_id FROM public.tenant_onboarding_checklist WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).first()
        if existing:
            print("  i️  [tenant_onboarding_checklist] Already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.tenant_onboarding_checklist
                    (tenant_id, account_created, legal_accepted, tier_selected,
                     first_customer_added, catalog_setup, quickbooks_connected, quickbooks_skipped,
                     calendar_connected, calendar_skipped, team_invited, team_skipped,
                     checklist_hidden, checklist_dismissed_permanently)
                    VALUES
                    (:tid, true, true, true, true, true, false, true, false, true, false, true, true, true)
                    ON CONFLICT DO NOTHING
                """),
                {"tid": tid},
            )
            print("  ✅ [tenant_onboarding_checklist] Created (completed state)")

        # ── 8. Subscription (requires product_plan from seed_platform.py) ───
        existing = db.execute(
            text("SELECT id FROM public.subscription WHERE tenant_id = :tid"),
            {"tid": tid},
        ).first()
        if existing:
            print("  i️  [subscription] Already exists")
        else:
            # MKT-B11 / C-B1: Use charter_plan explicitly (not "first active alphabetically")
            plan_row = db.execute(
                text(
                    "SELECT code FROM public.product_plan WHERE code = 'charter_plan' LIMIT 1"
                )
            ).first()

            if not plan_row:
                print(
                    "  ⚠️  [subscription] 'charter_plan' not found — run seed_platform.py first,"
                )
                print("      then re-run this script to create the subscription.")
            else:
                sub_status = db.execute(
                    text(
                        "SELECT id FROM public.subscription_status WHERE code = 'active' LIMIT 1"
                    )
                ).first()
                if not sub_status:
                    print(
                        "  ⚠️  [subscription] No subscription_status 'active' found — skipping"
                    )
                else:
                    db.execute(
                        text("""
                            INSERT INTO public.subscription
                            (id, tenant_id, product_plan_code, status_id, quantity_seats,
                             billing_anchor, started_at, billing_interval,
                             cancel_at_period_end, is_active, created_at, updated_at)
                            VALUES
                            (gen_random_uuid(), :tid, :plan_code, :status_id, 4,
                             '2026-07-01', NOW(), 'monthly', false, true, NOW(), NOW())
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "tid": tid,
                            "plan_code": plan_row.code,
                            "status_id": str(sub_status.id),
                        },
                    )
                    print(
                        f"  ✅ [subscription] Created charter subscription (plan={plan_row.code})"
                    )

        # SD-4: patch existing subscription rows missing quantity_seats=4 or billing_anchor
        db.execute(
            text("""
                UPDATE public.subscription
                SET quantity_seats = 4,
                    billing_anchor = '2026-07-01',
                    updated_at = NOW()
                WHERE tenant_id = :tid
                  AND (quantity_seats <> 4 OR billing_anchor IS NULL)
            """),
            {"tid": tid},
        )
        print("  ✅ [subscription] quantity_seats=4, billing_anchor=2026-07-01 ensured")

        # ── 9. Labor Rate Versions (3 skill levels) ──────────────────────────
        labor_rates = [
            {"skill_level_code": "master", "hourly_rate_cents": LABOR_RATE_MASTER},
            {
                "skill_level_code": "journeyman",
                "hourly_rate_cents": LABOR_RATE_JOURNEYMAN,
            },
            {
                "skill_level_code": "apprentice",
                "hourly_rate_cents": LABOR_RATE_APPRENTICE,
            },
        ]
        for lr in labor_rates:
            existing = db.execute(
                text("""
                    SELECT id FROM public.labor_rate_version
                    WHERE tenant_id = :tid AND skill_level_code = :code
                """),
                {"tid": tid, "code": lr["skill_level_code"]},
            ).first()
            if existing:
                print(
                    f"  i️  [labor_rate_version] '{lr['skill_level_code']}' already exists"
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.labor_rate_version
                        (tenant_id, skill_level_code, hourly_rate_cents, burden_pct, valid_period, recorded_at)
                        VALUES (:tid, :code, :rate, 0.0, tstzrange(now(), NULL), NOW())
                    """),
                    {
                        "tid": tid,
                        "code": lr["skill_level_code"],
                        "rate": lr["hourly_rate_cents"],
                    },
                )
                print(
                    f"  ✅ [labor_rate_version] '{lr['skill_level_code']}' @ {lr['hourly_rate_cents']}¢/hr"
                )

        # SD-4: UPDATE burden_pct on existing rows — DO NOT INSERT new rows
        # ⚠️ GiST exclusion constraint on (tenant_id, skill_level_code) with overlapping
        #    valid_period prohibits inserting duplicate open-ended rows.
        burden_updates = [
            ("master", Decimal("0.25")),  # $120 x 1.25 = $150.00/hr burdened
            ("journeyman", Decimal("0.20")),  # $85  x 1.20 = $102.00/hr burdened
            ("apprentice", Decimal("0.15")),  # $55  x 1.15 = $63.25/hr burdened
        ]
        for skill_level, burden in burden_updates:
            db.execute(
                text("""
                    UPDATE public.labor_rate_version
                    SET burden_pct = :pct
                    WHERE tenant_id = :tid AND skill_level_code = :code
                """),
                {"tid": tid, "pct": burden, "code": skill_level},
            )
            print(
                f"  ✅ [labor_rate_version] Updated '{skill_level}' burden_pct → {burden}"
            )

        # ── 10. Tenant Markup Version ────────────────────────────────────────
        existing = db.execute(
            text("SELECT id FROM public.tenant_markup_version WHERE tenant_id = :tid"),
            {"tid": tid},
        ).first()
        if existing:
            print("  i️  [tenant_markup_version] Already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.tenant_markup_version
                    (tenant_id, job_expense_category_code, markup_pct, valid_period, recorded_at, created_at)
                    VALUES (:tid, 'materials', :pct, tstzrange(now(), NULL), NOW(), NOW())
                """),
                {"tid": tid, "pct": MARKUP_PCT},
            )
            print(f"  ✅ [tenant_markup_version] {MARKUP_PCT}% markup")

        # ── 11. Discount Versions (SD-09) ────────────────────────────────────
        # discount_version: AppendOnly — id BIGINT serial, no updated_at
        # CHECK: exactly one of pct_off or amount_off_cents must be non-null
        discount_rows = [
            {
                "code": "SUMMER_PROMO",
                "pct_off": "10",
                "amount_off_cents": None,
                "valid_period": "tstzrange('2024-06-01', '2024-08-31')",
                "note": "10% off — closed past range",
            },
            {
                "code": "NEW_CUSTOMER",
                "pct_off": None,
                "amount_off_cents": 2500,
                "valid_period": "tstzrange('2026-01-01', NULL)",
                "note": "$25 off — open-ended",
            },
        ]
        for dr in discount_rows:
            existing = db.execute(
                text("""
                    SELECT id FROM public.discount_version
                    WHERE tenant_id = :tid AND code = :code
                """),
                {"tid": tid, "code": dr["code"]},
            ).first()
            if existing:
                print(f"  i️  [discount_version] '{dr['code']}' already exists")
            else:
                if dr["pct_off"] is not None:
                    db.execute(
                        text(f"""
                            INSERT INTO public.discount_version
                            (tenant_id, code, pct_off, amount_off_cents, valid_period, recorded_at, created_at)
                            VALUES (:tid, :code, :pct_off, NULL, {dr["valid_period"]}, NOW(), NOW())
                        """),
                        {"tid": tid, "code": dr["code"], "pct_off": dr["pct_off"]},
                    )
                else:
                    db.execute(
                        text(f"""
                            INSERT INTO public.discount_version
                            (tenant_id, code, pct_off, amount_off_cents, valid_period, recorded_at, created_at)
                            VALUES (:tid, :code, NULL, :amount_off_cents, {dr["valid_period"]}, NOW(), NOW())
                        """),
                        {
                            "tid": tid,
                            "code": dr["code"],
                            "amount_off_cents": dr["amount_off_cents"],
                        },
                    )
                print(f"  ✅ [discount_version] '{dr['code']}' — {dr['note']}")

        # ── SD-6: user_preference for owner user ─────────────────────────────
        owner_id_str = str(owner_id)
        existing_pref = db.execute(
            text("SELECT id FROM public.user_preference WHERE user_id = :uid"),
            {"uid": owner_id_str},
        ).first()
        if existing_pref:
            print("  i️  [user_preference] Owner user preference already exists")
        else:
            prefs = json.dumps(
                {
                    "theme": "light",
                    "sidebar_collapsed": False,
                    "notification_sounds": True,
                    "default_invoice_terms": "net_30",
                    "dashboard_layout": "default",
                }
            )
            db.execute(
                text("""
                    INSERT INTO public.user_preference
                    (id, user_id, tenant_id, preferences, created_at, updated_at,
                     created_by, updated_by)
                    VALUES (gen_random_uuid(), :uid, :tid, CAST(:prefs AS jsonb),
                            NOW(), NOW(), NULL, NULL)
                    ON CONFLICT (user_id, tenant_id) DO NOTHING
                """),
                {"uid": owner_id_str, "tid": tid, "prefs": prefs},
            )
            print("  ✅ [user_preference] Created for dev@pilot.local (5 keys)")

        # ── SD-6: user_setting_override for owner user (2 rows) ──────────────
        setting_overrides = [
            ("background_sync_enabled", json.dumps(True)),
            ("voice_persona_tone", json.dumps("professional")),
        ]
        for setting_key, value_json in setting_overrides:
            db.execute(
                text("""
                    INSERT INTO public.user_setting_override
                    (tenant_id, user_id, setting_key, value, created_at, updated_at,
                     created_by, updated_by)
                    VALUES (:tid, :uid, :key, CAST(:val AS jsonb), NOW(), NOW(), NULL, NULL)
                    ON CONFLICT (tenant_id, user_id, setting_key) DO NOTHING
                """),
                {
                    "tid": tid,
                    "uid": owner_id_str,
                    "key": setting_key,
                    "val": value_json,
                },
            )
        print(
            "  ✅ [user_setting_override] 2 rows created for dev@pilot.local (background_sync_enabled, voice_persona_tone)"
        )

        # ── SD-7 Batch 1: user.email_verified_at + last_login_at ────────────────
        # Set on all 4 test users. email_verified_at = created_at (pre-verified).
        # last_login_at = realistic past timestamps per user role.
        from datetime import UTC, datetime, timedelta

        now_utc = datetime.now(UTC)
        user_login_offsets = {
            str(owner_id): timedelta(hours=2),  # owner: 2 hours ago
            str(TECH_USER_ID): timedelta(days=1),  # tech: 1 day ago
            str(OFFICE_USER_ID): timedelta(days=3),  # office: 3 days ago
            str(ACCOUNTANT_USER_ID): timedelta(days=7),  # accountant: 1 week ago
        }
        for uid_str, offset in user_login_offsets.items():
            db.execute(
                text("""
                    UPDATE public."user"
                    SET email_verified_at = COALESCE(email_verified_at, created_at),
                        last_login_at = :last_login_at,
                        updated_at = NOW()
                    WHERE id = :uid
                """),
                {"uid": uid_str, "last_login_at": now_utc - offset},
            )
        print("  ✅ [user] email_verified_at + last_login_at set for all 4 test users")

        # ── SD-7 Batch 1: tenant_user.skill_level_code + employee_number ────────
        # master=owner, journeyman=tech, apprentice=office; accountant→NULL (admin role)
        skill_updates = [
            (str(owner_id), "master", "EMP-001"),
            (str(TECH_USER_ID), "journeyman", "EMP-002"),
            (str(OFFICE_USER_ID), "apprentice", "EMP-003"),
            (str(ACCOUNTANT_USER_ID), None, None),  # admin, not field-based
        ]
        for uid_str, skill_code, emp_num in skill_updates:
            db.execute(
                text("""
                    UPDATE public.tenant_user
                    SET skill_level_code = :skill,
                        employee_number = :emp,
                        updated_at = NOW()
                    WHERE tenant_id = :tid AND user_id = :uid
                """),
                {"tid": tid, "uid": uid_str, "skill": skill_code, "emp": emp_num},
            )
        print("  ✅ [tenant_user] skill_level_code + employee_number set for 4 users")

        # ── SD-7 Batch 1: auth_jwk — 1 active signing key ───────────────────────
        # The `auth_jwk` table requires: kid, alg, public_jwk (jsonb), jwk_status_id.
        # We seed a synthetic RSA-256 test key — NOT a real private key, public only.
        # Look up jwk_status 'active' by code — seed_core.py uses gen_random_uuid()
        # for the PK, so the UUID differs per DB. Hardcoding the dev UUID breaks on
        # any freshly-provisioned env (QA, e2e, prod). DB-MGMT-1 Task 4 fix.
        jwk_status_row = db.execute(
            text("SELECT id FROM public.jwk_status WHERE code = 'active' LIMIT 1")
        ).first()
        if not jwk_status_row:
            print(
                "  ❌ [auth_jwk] No 'active' jwk_status found — run seed_core.py first."
            )
            return
        jwk_status_active_id = str(jwk_status_row[0])
        jwk_kid = "pilot-dev-signing-key-v1"
        existing_jwk = db.execute(
            text("SELECT id FROM public.auth_jwk WHERE kid = :kid"),
            {"kid": jwk_kid},
        ).first()
        if existing_jwk:
            print(f"  i️  [auth_jwk] '{jwk_kid}' already exists")
        else:
            # Synthetic RSA public JWK (no private key — test-only placeholder)
            public_jwk = {
                "kty": "RSA",
                "use": "sig",
                "kid": jwk_kid,
                "alg": "RS256",
                "n": "sBbhDr9ZV5_placeholder_test_public_key_modulus_pilot_dev_001",
                "e": "AQAB",
            }
            db.execute(
                text("""
                    INSERT INTO public.auth_jwk
                    (id, kid, alg, public_jwk, jwk_status_id, tenant_id,
                     not_before, not_after, created_at, created_by)
                    VALUES (
                        gen_random_uuid(),
                        :kid,
                        'RS256',
                        CAST(:public_jwk AS jsonb),
                        CAST(:status_id AS uuid),
                        NULL,
                        NOW(),
                        NULL,
                        NOW(),
                        NULL
                    )
                    ON CONFLICT DO NOTHING
                """),
                {
                    "kid": jwk_kid,
                    "public_jwk": json.dumps(public_jwk),
                    "status_id": jwk_status_active_id,
                },
            )
            print(
                f"  ✅ [auth_jwk] Created active signing key '{jwk_kid}' (RS256, no expiry)"
            )

        # ── SD-7 Batch 2: notification_preference for owner user ────────────────
        # Schema: id (uuid), tenant_id, user_id (nullable), category_id (text), channel (text),
        #         enabled (bool), created_at, updated_at, created_by, updated_by
        # Seed email/in_app/push overrides for 4 notification categories (no SMS).
        notif_prefs = [
            ("billing", "email", True),
            ("billing", "in_app", True),
            ("billing", "push", True),
            ("job_activity", "email", True),
            ("job_activity", "in_app", True),
            ("job_activity", "push", True),
            ("quote_approvals", "email", True),
            ("quote_approvals", "in_app", True),
            ("quote_approvals", "push", False),  # push disabled for quote_approvals
            ("sync_conflicts", "email", True),
            ("sync_conflicts", "in_app", True),
            ("sync_conflicts", "push", True),
        ]
        for category_id, channel, enabled in notif_prefs:
            existing_pref = db.execute(
                text("""
                    SELECT id FROM public.notification_preference
                    WHERE tenant_id = :tid AND user_id = :uid
                      AND category_id = :cat AND channel = :ch
                    LIMIT 1
                """),
                {"tid": tid, "uid": owner_id_str, "cat": category_id, "ch": channel},
            ).first()
            if not existing_pref:
                db.execute(
                    text("""
                        INSERT INTO public.notification_preference
                        (id, tenant_id, user_id, category_id, channel, enabled,
                         created_at, updated_at, created_by, updated_by)
                        VALUES (gen_random_uuid(), :tid, :uid, :cat, :ch, :enabled,
                                NOW(), NOW(), NULL, NULL)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "tid": tid,
                        "uid": owner_id_str,
                        "cat": category_id,
                        "ch": channel,
                        "enabled": enabled,
                    },
                )
        print(
            f"  ✅ [notification_preference] {len(notif_prefs)} channel overrides ensured for dev@pilot.local"
        )

        # ── SD-7 Batch 2: mobile_device_push_token for tech user ────────────────
        # Schema: id (uuid), tenant_id, user_id, device_id, platform, push_token,
        #         app_version, os_version, registered_at, last_seen_at,
        #         notification_permission_granted, revoked_at, created_at, updated_at
        tech_device_id = UUID("00000000-0000-0000-0001-000000000001")
        tech_push_token = "ExponentPushToken[test-tech-00000003]"
        existing_token = db.execute(
            text("""
                SELECT id FROM public.mobile_device_push_token
                WHERE tenant_id = :tid AND user_id = :uid AND device_id = :device_id
                LIMIT 1
            """),
            {"tid": tid, "uid": str(TECH_USER_ID), "device_id": str(tech_device_id)},
        ).first()
        if existing_token:
            print("  i️  [mobile_device_push_token] Tech user token already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.mobile_device_push_token
                    (id, tenant_id, user_id, device_id, platform, push_token,
                     app_version, os_version, registered_at, last_seen_at,
                     notification_permission_granted, created_at, updated_at,
                     created_by, updated_by)
                    VALUES (
                        gen_random_uuid(), :tid, :uid, :device_id, 'ios', :push_token,
                        '1.2.0', '17.4.1', NOW() - INTERVAL '7 days', NOW() - INTERVAL '1 day',
                        true, NOW(), NOW(), NULL, NULL
                    )
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tid": tid,
                    "uid": str(TECH_USER_ID),
                    "device_id": str(tech_device_id),
                    "push_token": tech_push_token,
                },
            )
            print(
                f"  ✅ [mobile_device_push_token] Created for tech@pilot.local (device={tech_device_id})"
            )

        # ── SD-7 Batch 2: subscription_usage (current-period rows) ───────────────
        # Schema: id (bigint serial), subscription_id, product_feature_code,
        #         period_start (date), period_end (date), used_quantity (int),
        #         tenant_id, created_at, updated_at, created_by, updated_by
        sub_row = db.execute(
            text("SELECT id FROM public.subscription WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tid},
        ).first()
        if sub_row:
            sub_id = str(sub_row.id)
            # Current billing period: 2026-07-01 → 2026-07-31 (charter monthly)
            period_start = "2026-07-01"
            period_end = "2026-07-31"
            usage_rows = [
                ("schedule_lanes", 3),  # 3 active lanes in use
                ("voice_ai_minutes", 42),  # 42 AI minutes consumed this month
                ("outbound_sms_segments", 18),  # 18 SMS segments sent this month
            ]
            for feature_code, used_qty in usage_rows:
                existing_usage = db.execute(
                    text("""
                        SELECT id FROM public.subscription_usage
                        WHERE tenant_id = :tid AND subscription_id = :sub_id
                          AND product_feature_code = :feat AND period_start = :ps
                        LIMIT 1
                    """),
                    {
                        "tid": tid,
                        "sub_id": sub_id,
                        "feat": feature_code,
                        "ps": period_start,
                    },
                ).first()
                if existing_usage:
                    print(f"  i️  [subscription_usage] '{feature_code}' already exists")
                else:
                    db.execute(
                        text("""
                            INSERT INTO public.subscription_usage
                            (subscription_id, product_feature_code, period_start, period_end,
                             used_quantity, tenant_id, created_at, updated_at, created_by, updated_by)
                            VALUES (:sub_id, :feat, :ps, :pe, :qty, :tid,
                                    NOW(), NOW(), NULL, NULL)
                        """),
                        {
                            "sub_id": sub_id,
                            "feat": feature_code,
                            "ps": period_start,
                            "pe": period_end,
                            "qty": used_qty,
                            "tid": tid,
                        },
                    )
                    print(
                        f"  ✅ [subscription_usage] '{feature_code}'  used={used_qty}  period={period_start}→{period_end}"
                    )
        else:
            print(
                "  ⚠️  [subscription_usage] No subscription found — run seed_platform.py first"
            )

        # ── SD-7 Batch 2: tenant_subscription_usage (current-period summary) ─────
        # Schema: tenant_id (PK), period_start (timestamptz), period_end (timestamptz),
        #         current_user_count (int), current_sms_segment_count (int),
        #         created_at, updated_at, created_by, updated_by
        existing_tsu = db.execute(
            text("""
                SELECT tenant_id FROM public.tenant_subscription_usage
                WHERE tenant_id = :tid
                LIMIT 1
            """),
            {"tid": tid},
        ).first()
        if existing_tsu:
            print("  i️  [tenant_subscription_usage] Already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.tenant_subscription_usage
                    (tenant_id, period_start, period_end,
                     current_user_count, current_sms_segment_count,
                     created_at, updated_at, created_by, updated_by)
                    VALUES (:tid, '2026-07-01 00:00:00+00', '2026-07-31 23:59:59+00',
                            4, 18, NOW(), NOW(), NULL, NULL)
                    ON CONFLICT DO NOTHING
                """),
                {"tid": tid},
            )
            print(
                "  ✅ [tenant_subscription_usage] Created current-period summary (users=4, sms_segments=18)"
            )

        # ── SD-7 Batch 2: user_dashboard_widget (3 widgets for owner user) ────────
        # Schema: id (uuid), user_id, tenant_id, widget_type, widget_config_json (jsonb),
        #         position_x, position_y, width, height,
        #         created_at, updated_at, created_by, updated_by
        dashboard_widgets = [
            {
                "widget_type": "revenue_summary",
                "config": {"period": "month", "show_target": True},
                "position_x": 0,
                "position_y": 0,
                "width": 4,
                "height": 2,
            },
            {
                "widget_type": "job_pipeline",
                "config": {
                    "statuses": ["scheduled", "in_progress"],
                    "tech_filter": None,
                },
                "position_x": 4,
                "position_y": 0,
                "width": 4,
                "height": 2,
            },
            {
                "widget_type": "outstanding_invoices",
                "config": {"overdue_only": False, "limit": 5},
                "position_x": 0,
                "position_y": 2,
                "width": 8,
                "height": 2,
            },
        ]
        existing_widgets = db.execute(
            text("""
                SELECT COUNT(*) FROM public.user_dashboard_widget
                WHERE tenant_id = :tid AND user_id = :uid
            """),
            {"tid": tid, "uid": owner_id_str},
        ).scalar()
        if existing_widgets >= len(dashboard_widgets):
            print(
                f"  i️  [user_dashboard_widget] {existing_widgets} widget(s) already exist for owner user"
            )
        else:
            for widget in dashboard_widgets:
                # Check by widget_type (idempotent)
                existing_widget = db.execute(
                    text("""
                        SELECT id FROM public.user_dashboard_widget
                        WHERE tenant_id = :tid AND user_id = :uid AND widget_type = :wtype
                        LIMIT 1
                    """),
                    {"tid": tid, "uid": owner_id_str, "wtype": widget["widget_type"]},
                ).first()
                if not existing_widget:
                    db.execute(
                        text("""
                            INSERT INTO public.user_dashboard_widget
                            (id, user_id, tenant_id, widget_type, widget_config_json,
                             position_x, position_y, width, height,
                             created_at, updated_at, created_by, updated_by)
                            VALUES (
                                gen_random_uuid(), :uid, :tid, :wtype, CAST(:config AS jsonb),
                                :px, :py, :w, :h,
                                NOW(), NOW(), NULL, NULL
                            )
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "tid": tid,
                            "uid": owner_id_str,
                            "wtype": widget["widget_type"],
                            "config": json.dumps(widget["config"]),
                            "px": widget["position_x"],
                            "py": widget["position_y"],
                            "w": widget["width"],
                            "h": widget["height"],
                        },
                    )
                    print(
                        f"  ✅ [user_dashboard_widget] '{widget['widget_type']}' at ({widget['position_x']},{widget['position_y']})"
                    )
            print(
                f"  ✅ [user_dashboard_widget] {len(dashboard_widgets)} widgets seeded for dev@pilot.local"
            )

        # ── SD-7 Batch 2: tenant_10dlc_profile ────────────────────────────────────
        # Schema: tenant_id (PK), legal_business_name (text, NOT NULL), dba_name, ein,
        #         hq_address_line1..hq_postal_code, hq_country (default 'US'),
        #         support_email, support_phone, created_at, updated_at, created_by, updated_by
        existing_10dlc = db.execute(
            text(
                "SELECT tenant_id FROM public.tenant_10dlc_profile WHERE tenant_id = :tid LIMIT 1"
            ),
            {"tid": tid},
        ).first()
        if existing_10dlc:
            print("  i️  [tenant_10dlc_profile] Already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.tenant_10dlc_profile
                    (tenant_id, legal_business_name, dba_name, ein,
                     hq_address_line1, hq_address_line2, hq_city, hq_state,
                     hq_postal_code, hq_country, support_email, support_phone,
                     created_at, updated_at, created_by, updated_by)
                    VALUES (
                        :tid,
                        'Pilot Dev Tenant LLC',
                        'Pilot Dev Electrical',
                        NULL,
                        '123 Main St',
                        NULL,
                        'Austin',
                        'TX',
                        '78701',
                        'US',
                        'dev@pilot.local',
                        '+15125550001',
                        NOW(), NOW(), NULL, NULL
                    )
                    ON CONFLICT DO NOTHING
                """),
                {"tid": tid},
            )
            print(
                "  ✅ [tenant_10dlc_profile] Created (legal_name='Pilot Dev Tenant LLC', TX HQ)"
            )

        # ── SD-7 Batch 3: tenant_user skill_level_code / employee_number corrections ─
        # Per Batch 3 spec: owner=master, tech=journeyman, office_staff=NULL, accountant=NULL.
        # employee_number: EMP-001 through EMP-004 on all 4 users.
        print("\n  -- SD-7 Batch 3: tenant_user field corrections --")
        batch3_skill_updates = [
            (str(owner_id), "master", "EMP-001"),
            (str(TECH_USER_ID), "journeyman", "EMP-002"),
            (str(OFFICE_USER_ID), None, "EMP-003"),  # skill=NULL per B3 spec
            (str(ACCOUNTANT_USER_ID), None, "EMP-004"),  # admin role + employee_number
        ]
        for uid_str, skill_code, emp_num in batch3_skill_updates:
            db.execute(
                text("""
                    UPDATE public.tenant_user
                    SET skill_level_code = :skill,
                        employee_number = :emp,
                        updated_at = NOW()
                    WHERE tenant_id = :tid AND user_id = :uid
                """),
                {"tid": tid, "uid": uid_str, "skill": skill_code, "emp": emp_num},
            )
        print(
            "  ✅ [tenant_user] skill_level_code + employee_number corrected (B3): "
            "owner=master/EMP-001, tech=journeyman/EMP-002, office=NULL/EMP-003, acct=NULL/EMP-004"
        )

        # ── SD-7 Batch 3: tenant_signup ──────────────────────────────────────────
        # Schema: tenant_id (PK), signup_state, signup_started_at, signup_completed_at,
        #         business_name, trade, business_size, zip, time_zone,
        #         created_at, updated_at, created_by, updated_by
        existing_signup = db.execute(
            text("SELECT tenant_id FROM public.tenant_signup WHERE tenant_id = :tid"),
            {"tid": tid},
        ).first()
        if existing_signup:
            print("  i️  [tenant_signup] Already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.tenant_signup
                    (tenant_id, signup_state, signup_started_at, signup_completed_at,
                     business_name, trade, business_size, zip, time_zone,
                     owner_email, owner_first_name, owner_last_name,
                     created_at, updated_at, created_by, updated_by)
                    VALUES (:tid, 'complete', '2026-06-01 10:00:00+00', '2026-06-01 10:15:00+00',
                            'Pilot Dev Electrical', 'electrical', 'solo', '78701', 'America/Chicago',
                            'dev@pilot.local', 'Dev', 'Owner',
                            NOW(), NOW(), NULL, NULL)
                    ON CONFLICT DO NOTHING
                """),
                {"tid": tid},
            )
            print(
                "  ✅ [tenant_signup] Created (state=complete, trade=electrical, solo)"
            )

        # ── SD-7 Batch 3: tenant_legal_acceptance ────────────────────────────────
        # Schema: acceptance_id (uuid PK), tenant_id, user_id, document_type (text),
        #         document_version_hash (text), accepted_at, ip_address (inet, NOT NULL),
        #         user_agent (text, NOT NULL), created_at, created_by
        existing_tos = db.execute(
            text("""
                SELECT acceptance_id FROM public.tenant_legal_acceptance
                WHERE tenant_id = :tid AND document_type = 'tos'
                LIMIT 1
            """),
            {"tid": tid},
        ).first()
        if existing_tos:
            print("  i️  [tenant_legal_acceptance] ToS acceptance already exists")
        else:
            db.execute(
                text("""
                    INSERT INTO public.tenant_legal_acceptance
                    (acceptance_id, tenant_id, user_id, document_type,
                     document_version_hash, accepted_at,
                     ip_address, user_agent, created_at, created_by)
                    VALUES (gen_random_uuid(), :tid, :uid, 'tos',
                            'sha256-placeholder-tos-v1-2026-06-01',
                            '2026-06-01 10:14:00+00',
                            '127.0.0.1'::inet,
                            'Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 Pilot-Seed/1.0',
                            NOW(), NULL)
                    ON CONFLICT DO NOTHING
                """),
                {"tid": tid, "uid": str(owner_id)},
            )
            print(
                "  ✅ [tenant_legal_acceptance] ToS accepted by owner (document_type=tos, hash=sha256-placeholder-tos-v1-2026-06-01)"
            )

        # ── TEAM-INVITE-1: pending dev invite for FE pending-list dev ──────────
        # Raw token: dev-invite-token-0001 (documented for FE landing-page dev;
        # never stored in the DB — only the SHA-256 hash is stored).
        # Idempotent: ON CONFLICT DO NOTHING on uq_tenant_user_invite_tenant_id_email.
        # Value-scoped per README §7 — the natural key (tenant_id, email) is the
        # exact row being re-inserted.
        dev_invite_token_hash = hashlib.sha256(b"dev-invite-token-0001").hexdigest()
        db.execute(
            text("""
                INSERT INTO public.tenant_user_invite
                (id, tenant_id, email, token_hash, role_code, expires_at,
                 invited_by, is_active, created_at, updated_at)
                VALUES (
                    gen_random_uuid(), :tid, 'newguy@pilot.local', :token_hash,
                    'technician', NOW() + INTERVAL '7 days',
                    :owner_id, true, NOW(), NOW()
                )
                ON CONFLICT (tenant_id, email) DO NOTHING
            """),
            {
                "tid": tid,
                "token_hash": dev_invite_token_hash,
                "owner_id": str(owner_id),
            },
        )
        print(
            "  ✅ [tenant_user_invite] Pending dev invite for newguy@pilot.local "
            "(raw token: dev-invite-token-0001)"
        )

        db.commit()

    print(f"\n🎉 seed_test_tenant complete — Group C data present for {tenant_id}")


def mode_inspect(tenant_id: UUID):
    """Show current state of all Group C data."""
    print("=== seed_test_tenant: inspect mode ===")
    print(f"    Tenant ID: {tenant_id}\n")

    tid = str(tenant_id)

    with get_db_session() as db:
        t = db.execute(
            text(
                "SELECT id, name, is_active, billing_contact_phone, billing_contact_email "
                "FROM public.tenant WHERE id = :tid"
            ),
            {"tid": tid},
        ).first()
        if t:
            print("  [tenant]  1 row(s)")
            print(f'    {t.id}  "{t.name}"  is_active={t.is_active}')
            print(
                f"    billing_contact_phone={t.billing_contact_phone}  "
                f"billing_contact_email={t.billing_contact_email}"
            )
        else:
            print("  [tenant]  0 row(s)  ← NOT SEEDED")
        print()

        users = db.execute(
            text("""
                SELECT u.id, u.email, tu.role_code
                FROM public."user" u
                JOIN public.tenant_user tu ON tu.user_id = u.id
                WHERE tu.tenant_id = :tid ORDER BY tu.role_code
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [user]  {len(users)} row(s)")
        for u in users:
            print(f"    {u.id}  {u.email}  role={u.role_code}")
        print()

        endpoints = db.execute(
            text("""
                SELECT ue.user_id, ue.channel, ue.value, ue.verification_status, ue.consent_status
                FROM public.user_endpoint ue
                JOIN public.tenant_user tu ON tu.user_id = ue.user_id
                WHERE tu.tenant_id = :tid
            """),
            {"tid": tid},
        ).fetchall()
        print(f"  [user_endpoint]  {len(endpoints)} row(s)")
        for e in endpoints:
            print(
                f"    {e.user_id}  channel={e.channel}  value={e.value}  status={e.verification_status}  consent={e.consent_status}"
            )
        print()

        pp = db.execute(
            text(
                "SELECT id, min_length, min_uppercase, min_digits, lockout_threshold FROM public.password_policy WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).first()
        print(
            f"  [password_policy]  {'1 row(s)  min_length=' + str(pp.min_length) + '  (lockout_threshold=' + str(pp.lockout_threshold) + ')' if pp else '0 row(s)  ← NOT SEEDED'}"
        )

        eb = db.execute(
            text(
                "SELECT brand_color_hex, custom_footer FROM public.tenant_email_branding WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).first()
        print(
            f"  [tenant_email_branding]  {'1 row(s)  brand_color=' + str(eb.brand_color_hex) if eb else '0 row(s)  ← NOT SEEDED'}"
        )

        oc = db.execute(
            text(
                "SELECT checklist_dismissed_permanently FROM public.tenant_onboarding_checklist WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).first()
        print(
            f"  [tenant_onboarding_checklist]  {'1 row(s)  dismissed=' + str(oc.checklist_dismissed_permanently) if oc else '0 row(s)  ← NOT SEEDED'}"
        )

        sub = db.execute(
            text(
                "SELECT id, product_plan_code, is_active, quantity_seats, billing_anchor FROM public.subscription WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).first()
        if sub:
            print(
                f"\n  [subscription]  1 row(s)  plan={sub.product_plan_code}  is_active={sub.is_active}"
            )
            print(
                f"    (quantity_seats={sub.quantity_seats}, billing_anchor={sub.billing_anchor})"
            )
        else:
            print(
                "\n  [subscription]  0 row(s)  ← NOT SEEDED (run seed_platform.py first)"
            )

        lrv = db.execute(
            text(
                "SELECT skill_level_code, hourly_rate_cents, burden_pct FROM public.labor_rate_version WHERE tenant_id = :tid ORDER BY skill_level_code"
            ),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [labor_rate_version]  {len(lrv)} row(s)")
        for lr in lrv:
            burdened = float(lr.hourly_rate_cents) * (1 + float(lr.burden_pct)) / 100
            print(
                f"    {lr.skill_level_code}  @ {lr.hourly_rate_cents}¢/hr  (${lr.hourly_rate_cents / 100:.2f}/hr)  burden={lr.burden_pct}  → burdened=${burdened:.2f}/hr"
            )

        mv = db.execute(
            text(
                "SELECT markup_pct FROM public.tenant_markup_version WHERE tenant_id = :tid"
            ),
            {"tid": tid},
        ).first()
        print(
            f"\n  [tenant_markup_version]  {'1 row(s)  pct=' + str(mv.markup_pct) if mv else '0 row(s)  ← NOT SEEDED'}"
        )

        # SD-6: user_preference
        pref_rows = db.execute(
            text("SELECT id FROM public.user_preference WHERE user_id = :uid"),
            {"uid": str(_get_owner_id())},
        ).fetchall()
        print(f"\n  [user_preference]  {len(pref_rows)} row(s)  user=dev@pilot.local")

        # SD-6: user_setting_override
        override_rows = db.execute(
            text("""
                SELECT setting_key FROM public.user_setting_override
                WHERE tenant_id = :tid AND user_id = :uid
                ORDER BY setting_key
            """),
            {"tid": tid, "uid": str(_get_owner_id())},
        ).fetchall()
        keys = [r[0] for r in override_rows]
        print(
            f"  [user_setting_override]  {len(override_rows)} row(s)  user=dev@pilot.local  keys={','.join(keys)}"
        )

        # SD-4: discount_version inspect block
        discounts = db.execute(
            text("""
                SELECT code, pct_off, amount_off_cents,
                       lower(valid_period) AS valid_from,
                       upper(valid_period) AS valid_until
                FROM public.discount_version
                WHERE tenant_id = :tid
                ORDER BY code
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [discount_version]  {len(discounts)} row(s)")
        for d in discounts:
            if d.pct_off is not None:
                print(
                    f"    '{d.code}'  {d.pct_off}% off  valid: [{d.valid_from} → {d.valid_until or 'open'}]"
                )
            else:
                print(
                    f"    '{d.code}'  ${d.amount_off_cents / 100:.2f} off  valid: [{d.valid_from} → {d.valid_until or 'open'}]"
                )

        # SD-7 Batch 2: notification_preference
        np_rows = db.execute(
            text("""
                SELECT category_id, channel, enabled
                FROM public.notification_preference
                WHERE tenant_id = :tid AND user_id = :uid
                ORDER BY category_id, channel
            """),
            {"tid": tid, "uid": str(_get_owner_id())},
        ).fetchall()
        print(
            f"\n  [notification_preference]  {len(np_rows)} row(s)  user=dev@pilot.local"
        )
        for r in np_rows:
            print(
                f"    category={r.category_id}  channel={r.channel}  enabled={r.enabled}"
            )

        # SD-7 Batch 2: mobile_device_push_token
        push_tokens = db.execute(
            text("""
                SELECT id, user_id, device_id, platform, push_token,
                       notification_permission_granted, last_seen_at
                FROM public.mobile_device_push_token
                WHERE tenant_id = :tid
                ORDER BY registered_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [mobile_device_push_token]  {len(push_tokens)} row(s)")
        for t in push_tokens:
            print(
                f"    • {t.id}  user={t.user_id}  platform={t.platform}  "
                f"permission_granted={t.notification_permission_granted}  last_seen={t.last_seen_at}"
            )

        # SD-7 Batch 2: subscription_usage
        su_rows = db.execute(
            text("""
                SELECT product_feature_code, used_quantity, period_start, period_end
                FROM public.subscription_usage
                WHERE tenant_id = :tid
                ORDER BY product_feature_code
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [subscription_usage]  {len(su_rows)} row(s)")
        for r in su_rows:
            print(
                f"    feature={r.product_feature_code}  used={r.used_quantity}  "
                f"period={r.period_start}→{r.period_end}"
            )

        # SD-7 Batch 2: tenant_subscription_usage
        tsu = db.execute(
            text("""
                SELECT period_start, period_end, current_user_count, current_sms_segment_count
                FROM public.tenant_subscription_usage
                WHERE tenant_id = :tid
                LIMIT 1
            """),
            {"tid": tid},
        ).first()
        if tsu:
            print(
                f"\n  [tenant_subscription_usage]  1 row(s)  "
                f"users={tsu.current_user_count}  sms_segments={tsu.current_sms_segment_count}  "
                f"period={tsu.period_start}→{tsu.period_end}"
            )
        else:
            print("\n  [tenant_subscription_usage]  0 row(s)  ← NOT SEEDED")

        # SD-7 Batch 2: user_dashboard_widget
        widgets = db.execute(
            text("""
                SELECT id, widget_type, position_x, position_y, width, height
                FROM public.user_dashboard_widget
                WHERE tenant_id = :tid AND user_id = :uid
                ORDER BY position_y, position_x
            """),
            {"tid": tid, "uid": str(_get_owner_id())},
        ).fetchall()
        print(
            f"\n  [user_dashboard_widget]  {len(widgets)} row(s)  user=dev@pilot.local"
        )
        for w in widgets:
            print(
                f"    • {w.id}  type={w.widget_type}  "
                f"pos=({w.position_x},{w.position_y})  size={w.width}x{w.height}"
            )

        # SD-7 Batch 2: tenant_10dlc_profile
        dlc = db.execute(
            text("""
                SELECT legal_business_name, dba_name, ein, hq_city, hq_state,
                       support_email, support_phone
                FROM public.tenant_10dlc_profile
                WHERE tenant_id = :tid
                LIMIT 1
            """),
            {"tid": tid},
        ).first()
        if dlc:
            print(
                f"\n  [tenant_10dlc_profile]  1 row(s)  "
                f"legal='{dlc.legal_business_name}'  dba='{dlc.dba_name}'  "
                f"hq={dlc.hq_city},{dlc.hq_state}  support={dlc.support_email}"
            )
        else:
            print("\n  [tenant_10dlc_profile]  0 row(s)  ← NOT SEEDED")

        # SD-7 Batch 3: tenant_user skill_level_code / employee_number
        tu_rows = db.execute(
            text("""
                SELECT tu.user_id, u.email, tu.role_code, tu.skill_level_code, tu.employee_number
                FROM public.tenant_user tu
                JOIN public."user" u ON u.id = tu.user_id
                WHERE tu.tenant_id = :tid
                ORDER BY tu.role_code
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [tenant_user (skill/employee)]  {len(tu_rows)} row(s)")
        for tu in tu_rows:
            skill_str = (
                f"  skill={tu.skill_level_code}"
                if tu.skill_level_code
                else "  skill=NULL"
            )
            emp_str = (
                f"  emp={tu.employee_number}" if tu.employee_number else "  emp=NULL"
            )
            print(f"    {tu.email}  role={tu.role_code}{skill_str}{emp_str}")

        # SD-7 Batch 3: tenant_signup
        signup = db.execute(
            text("""
                SELECT signup_state, signup_started_at, signup_completed_at,
                       business_name, trade, business_size
                FROM public.tenant_signup
                WHERE tenant_id = :tid
                LIMIT 1
            """),
            {"tid": tid},
        ).first()
        if signup:
            print(
                f"\n  [tenant_signup]  1 row(s)  state={signup.signup_state}"
                f"  business='{signup.business_name}'  trade={signup.trade}"
                f"  size={signup.business_size}  completed={signup.signup_completed_at}"
            )
        else:
            print("\n  [tenant_signup]  0 row(s)  ← NOT SEEDED")

        # SD-7 Batch 3: tenant_legal_acceptance
        tos_rows = db.execute(
            text("""
                SELECT acceptance_id, user_id, document_type, document_version_hash, accepted_at
                FROM public.tenant_legal_acceptance
                WHERE tenant_id = :tid
                ORDER BY accepted_at
            """),
            {"tid": tid},
        ).fetchall()
        print(f"\n  [tenant_legal_acceptance]  {len(tos_rows)} row(s)")
        for tos in tos_rows:
            print(
                f"    • acceptance_id={tos.acceptance_id}"
                f"  doc_type={tos.document_type}"
                f"  accepted_at={tos.accepted_at}"
                f"  hash={tos.document_version_hash[:20]}..."
            )


def mode_show(tenant_id: UUID):
    """Print what would be seeded without touching the DB."""
    print("=== seed_test_tenant: show mode ===\n")
    print(f"Tenant ID (target): {tenant_id}")
    print(
        f"  [tenant]                  name='{TENANT_NAME}'  stripe_customer_id={STRIPE_CUSTOMER_ID_TEST}"
    )
    print(
        f"  [tenant]                  billing_contact_phone='{BILLING_CONTACT_PHONE}'  billing_contact_email='{BILLING_CONTACT_EMAIL}'"
    )
    print(
        f"  [user] owner              {settings.TEST_USER_ID}  email={OWNER_EMAIL}  color={OWNER_DISPLAY_COLOR}"
    )
    print(
        f"  [user] technician         {TECH_USER_ID}  email={TECH_EMAIL}  color={TECH_DISPLAY_COLOR}"
    )
    print(
        f"  [user] office_staff       {OFFICE_USER_ID}  email={OFFICE_EMAIL}  color={OFFICE_DISPLAY_COLOR}"
    )
    print(
        f"  [user] accountant         {ACCOUNTANT_USER_ID}  email={ACCOUNTANT_EMAIL}  color={ACCOUNTANT_DISPLAY_COLOR}"
    )
    print(
        "  [user_endpoint]           12 rows (email/in_app/push, one per user x 3 channels)"
    )
    print(
        "  [tenant_user]             4 rows (owner / technician / office_staff / accountant)"
    )
    print(
        f"  [password_policy]         min_length={PASSWORD_MIN_LENGTH}  min_uppercase={PASSWORD_MIN_UPPERCASE}  min_digits={PASSWORD_MIN_DIGITS}"
        "  lockout_threshold=5  lockout_window=15m  lockout_duration=30m  history_depth=5"
    )
    print("  [tenant_email_branding]   brand_color=#2563EB  custom_footer set")
    print("  [tenant_onboarding_checklist] completed/dismissed state")
    print(
        "  [subscription]            charter_plan  quantity_seats=4  billing_anchor=2026-07-01"
        "  (requires seed_platform.py to run first)"
    )
    print(
        f"  [labor_rate_version]      master={LABOR_RATE_MASTER}¢ burden=0.25  journeyman={LABOR_RATE_JOURNEYMAN}¢ burden=0.20  apprentice={LABOR_RATE_APPRENTICE}¢ burden=0.15"
    )
    print(f"  [tenant_markup_version]   markup={MARKUP_PCT}%  category=material")
    print(
        "  [discount_version]        2 rows (SUMMER_PROMO 10% + NEW_CUSTOMER $25 off)"
    )
    # SD-7 Batch 2
    print(
        "  [notification_preference] 12 rows (4 categories x 3 channels, email/in_app/push — no SMS)"
    )
    print(
        "  [mobile_device_push_token] 1 row for tech@pilot.local (iOS, device=00000000-0000-0000-0001-000000000001)"
    )
    print(
        "  [subscription_usage]      3 rows (schedule_lanes=3, voice_ai_minutes=42, outbound_sms_segments=18)"
    )
    print(
        "  [tenant_subscription_usage] 1 current-period row (users=4, sms_segments=18)"
    )
    print(
        "  [user_dashboard_widget]   3 rows for owner (revenue_summary, job_pipeline, outstanding_invoices)"
    )
    print("  [tenant_10dlc_profile]    1 row (Pilot Dev Tenant LLC, Austin TX)")


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "C", "seed_test_tenant.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if getattr(args, "mode", "seed") in ("seed", "inspect") or getattr(
        args, "reset", False
    ):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_test_tenant.py")
    tenant_id = _get_tenant_id(args)

    if args.reset:
        mode_reset(tenant_id)
    elif args.mode == "seed":
        mode_seed(tenant_id)
    elif args.mode == "inspect":
        mode_inspect(tenant_id)
    elif args.mode == "show":
        mode_show(tenant_id)
