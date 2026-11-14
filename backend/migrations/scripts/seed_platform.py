"""
seed_platform.py — Group B: Platform-level entitlement configuration.

Purpose: Seeds product_plan hierarchy and notification templates. Not required
for unit tests (entitlements are mocked), but required for UI testing where
the real entitlement system runs.

Schema verified against live DB 2026-06-01:
  product_plan: code (PK), name, description, is_active, created_at, updated_at
  product_plan_version: id (serial), product_plan_code, name, price_cents,
                         valid_period, recorded_at  (AppendOnly — no updated_at)
  product_plan_product_feature_version: id (serial), product_plan_code,
      product_feature_code, limit_quantity, included_quantity, overage_price_cents,
      valid_period, recorded_at, limit_enforcement  (AppendOnly — no updated_at)
  notification_template: id, tenant_id, notification_type_code, channel, locale,
                          subject, body, is_active, created_at, updated_at

SD-3 Changes (2026-07-14):
  - product_plan.code 'teams' → 'teams_plan' (Migration 1)
  - subscription_tier columns renamed: monthly_price_cents → annual_price_cents,
    stripe_price_id → stripe_price_id_monthly; new columns: monthly_price_cents,
    stripe_price_id_annual (Migration 2)
  - charter_plan product_plan_version.price_cents fixed: 4900 → 0 (Migration 2)
  - Added 18 notification_template rows for SD-2 notification types (6 types × 3 channels)

Modes:
  --mode seed     (default) Insert Group B rows; idempotent
  --mode inspect  Show current state of platform config
  --mode show     Print what would be seeded; no DB required
"""

import argparse
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text  # noqa: E402

from migrations.scripts._db_utils import get_db_session  # noqa: E402
from migrations.scripts._env_profiles import (  # noqa: E402
    EnvProfile,
    add_env_args,
    assert_group_allowed,
    assert_target_compatible,
    convergeable_tiers,
    print_seed_banner,
    resolve_profile_from_args,
)

# ── SEED DATA CONFIG ─────────────────────────────────────────────────────────

PRODUCT_PLANS = [
    {
        "code": "charter_plan",
        "name": "Charter",
        "description": "Charter program plan. 90 days free, then $49/mo locked at Starter limits for as long as subscribed.",
        "is_active": True,
    },
    {
        "code": "starter_plan",
        "name": "Starter Plan",
        "description": "For solo contractors starting out",
        "is_active": False,  # dormant until general release
    },
    {
        "code": "teams_plan",  # SD-3: renamed from 'teams'
        "name": "Teams Plan",
        "description": "For growing contractors and small teams",
        "is_active": False,  # dormant until general release
    },
    # enterprise_plan: removed — do not seed
]

# Map subscription_tier.tier_name → product_plan.code
# MKT-B11 / C-B1: Charter cohort period — only charter_plan is active
# SD-3: 'teams' value renamed to 'teams_plan'
TIER_TO_PLAN_MAP = {
    "charter": "charter_plan",
    "trial": "starter_plan",  # trial uses starter_plan entitlements
    "starter": "starter_plan",
    "teams": "teams_plan",  # SD-3: was "teams"
}

# Subscription status rows — map 1:1 to Stripe's subscription.status field
SUBSCRIPTION_STATUS_ROWS = [
    {"code": "trialing", "name": "Trialing", "is_billing_active": True},
    {"code": "active", "name": "Active", "is_billing_active": True},
    {"code": "past_due", "name": "Past Due", "is_billing_active": True},
    {"code": "unpaid", "name": "Unpaid", "is_billing_active": False},
    {"code": "canceled", "name": "Canceled", "is_billing_active": False},
    {"code": "paused", "name": "Paused", "is_billing_active": False},
]

# Product feature entitlements per plan
# MKT-B11: dispatch_slots → schedule_lanes; data_exports deleted (unlimited, untracked)
# enterprise_plan deleted; charter_plan added as only active plan during Charter cohort
# SD-3: 'teams' key renamed to 'teams_plan'
PLAN_FEATURE_LIMITS = {
    "charter_plan": {
        "schedule_lanes": {"limit": 5, "overage_cents": None, "enforcement": "block"},
        "voice_ai_minutes": {"limit": 90, "overage_cents": 5, "enforcement": "soft"},
        "outbound_sms_segments": {
            "limit": 100,
            "overage_cents": 5,
            "enforcement": "soft",
        },
    },
    "starter_plan": {
        "schedule_lanes": {"limit": 5, "overage_cents": None, "enforcement": "block"},
        "voice_ai_minutes": {"limit": 90, "overage_cents": 5, "enforcement": "soft"},
        "outbound_sms_segments": {
            "limit": 100,
            "overage_cents": 5,
            "enforcement": "soft",
        },
    },
    "teams_plan": {  # SD-3: renamed from 'teams'
        "schedule_lanes": {"limit": 20, "overage_cents": None, "enforcement": "block"},
        "voice_ai_minutes": {"limit": 300, "overage_cents": 5, "enforcement": "soft"},
        "outbound_sms_segments": {
            "limit": 500,
            "overage_cents": 5,
            "enforcement": "soft",
        },
    },
}

# SD-3: Per-plan list prices for product_plan_version rows
# charter_plan = $0 during cohort period (MKT-B11 set this incorrectly to 4900)
# The $49/mo billing at month 7 is a Stripe Subscription Schedule event (STRIPE-B1)
PRODUCT_PLAN_PRICES = {
    "charter_plan": 0,  # Free during cohort period (list price = $0)
    "starter_plan": 4900,  # $49/mo annual display price
    "teams_plan": 14900,  # $149/mo annual display price
}

# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(description="seed_platform.py — Group B seeder")
    parser.add_argument("--mode", choices=["seed", "inspect", "show"], default="seed")
    add_env_args(parser)
    return parser.parse_args()


def mode_seed(profile: EnvProfile):
    """Seed Group B: product_plan hierarchy + notification templates.

    DB-MGMT-1: Stripe price IDs are resolved from ``profile`` (env-aware).
    The converge-UPDATE path flips the 5 price-ID slots per the resolved
    ``--stripe-mode`` so re-running with a different mode converges cleanly
    (retires the one-off SQL in stripe-pricing-config.md §4). Charter is
    skipped until its price-ID mode is classified (design §G-7).
    """
    print("=== seed_platform: seed mode ===\n")

    with get_db_session() as db:
        # ── 1. Product Plans (StandardAuditMixin — needs created_at + updated_at) ──
        for plan in PRODUCT_PLANS:
            existing = db.execute(
                text("SELECT code FROM public.product_plan WHERE code = :code"),
                {"code": plan["code"]},
            ).first()
            if existing:
                print(f"  ℹ️  [product_plan] '{plan['code']}' already exists")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.product_plan
                        (code, name, description, is_active, created_at, updated_at)
                        VALUES (:code, :name, :description, :is_active, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    plan,
                )
                print(f"  ✅ [product_plan] Created '{plan['code']}'")

        # ── 2. Product Plan Versions (AppendOnly — no updated_at) ────────────
        # SD-3: Use PRODUCT_PLAN_PRICES for per-plan list price (charter_plan = $0)
        for plan in PRODUCT_PLANS:
            existing = db.execute(
                text(
                    "SELECT id FROM public.product_plan_version WHERE product_plan_code = :code"
                ),
                {"code": plan["code"]},
            ).first()
            if existing:
                print(
                    f"  ℹ️  [product_plan_version] '{plan['code']}' version already exists"
                )
            else:
                price_cents = PRODUCT_PLAN_PRICES.get(plan["code"], 0)
                db.execute(
                    text("""
                        INSERT INTO public.product_plan_version
                        (product_plan_code, name, price_cents, valid_period, recorded_at, created_at)
                        VALUES (:code, :name, :price_cents, tstzrange(now(), NULL), NOW(), NOW())
                    """),
                    {
                        "code": plan["code"],
                        "name": plan["name"],
                        "price_cents": price_cents,
                    },
                )
                print(
                    f"  ✅ [product_plan_version] Created version for '{plan['code']}' price_cents={price_cents}"
                )

        # ── 3. Product Feature Limits (AppendOnly — no updated_at) ──────────
        features = db.execute(
            text(
                "SELECT code FROM public.product_feature WHERE is_active = true ORDER BY code"
            )
        ).fetchall()
        feature_codes = {f.code for f in features}

        for plan_code, limits in PLAN_FEATURE_LIMITS.items():
            for feature_code, limit_cfg in limits.items():
                # MKT-B11: limit_cfg is now a dict with limit, overage_cents, enforcement keys
                limit_qty = limit_cfg["limit"]
                overage_cents = limit_cfg["overage_cents"]
                enforcement = limit_cfg["enforcement"]

                if feature_code not in feature_codes:
                    print(f"  ⚠️  Feature '{feature_code}' not in DB — skipping")
                    continue

                existing = db.execute(
                    text("""
                        SELECT id FROM public.product_plan_product_feature_version
                        WHERE product_plan_code = :plan_code AND product_feature_code = :feature_code
                    """),
                    {"plan_code": plan_code, "feature_code": feature_code},
                ).first()
                if existing:
                    print(
                        f"  ℹ️  [product_plan_product_feature_version] {plan_code}/{feature_code} already exists"
                    )
                else:
                    db.execute(
                        text("""
                            INSERT INTO public.product_plan_product_feature_version
                            (product_plan_code, product_feature_code, limit_quantity, included_quantity,
                             overage_price_cents, limit_enforcement, valid_period, recorded_at, created_at)
                            VALUES (:plan_code, :feature_code, :limit_qty, :limit_qty,
                                    :overage_cents, :enforcement, tstzrange(now(), NULL), NOW(), NOW())
                        """),
                        {
                            "plan_code": plan_code,
                            "feature_code": feature_code,
                            "limit_qty": limit_qty,
                            "overage_cents": overage_cents,
                            "enforcement": enforcement,
                        },
                    )
                    print(
                        f"  ✅ [product_plan_product_feature_version] {plan_code}/{feature_code} limit={limit_qty} enforcement={enforcement}"
                    )

        # ── 4. Ensure subscription_tier rows exist (MKT-B11: 4 tiers) ─────────
        # These rows are created by the MKT-B11 Alembic migration on the dev DB.
        # On a fresh E2E DB (schema-only restore), they must be seeded here.
        #
        # SD-3: Column renames:
        #   monthly_price_cents → annual_price_cents (holds annual-rate display price)
        #   stripe_price_id → stripe_price_id_monthly
        # SD-3: New columns:
        #   monthly_price_cents (month-to-month premium price)
        #   stripe_price_id_annual (NULL until Tom creates annual Stripe prices)
        #
        # DB-MGMT-1: stripe_price_id_monthly/annual resolved from the env profile
        # (design §F.1 / §B.3). The converge-UPDATE below flips them per
        # --stripe-mode. Charter is excluded from converge until its price-ID
        # mode is classified (design §G-7) — its INSERT uses the profile value
        # but the converge-UPDATE skips it.
        # C-B2: Added free_period_days, requires_payment_method, signup_cap, price_locked
        # C-B2: Charter pricing updated to $49/mo ($588 annual) — was $0 during cohort period
        _subscription_tier_rows = [
            {
                "tier_name": "charter",
                "display_label": "Charter",
                "annual_price_cents": 58800,  # C-B2: $588/yr (= $49/mo × 12, annual rate billed monthly)
                "monthly_price_cents": 4900,  # C-B2: $49/mo flat (annual rate billed monthly)
                "is_trial": False,
                "trial_duration_days": None,
                "is_active": True,
                "display_order": 0,
                "schedule_lanes": 5,
                "product_plan_code": "charter_plan",
                "stripe_price_id_monthly": profile.stripe_price_id(
                    "charter", "monthly"
                ),
                "stripe_price_id_annual": profile.stripe_price_id("charter", "annual"),
                # C-B2 fields:
                "free_period_days": 90,
                "requires_payment_method": False,
                "signup_cap": 12,
                "price_locked": True,
            },
            {
                "tier_name": "trial",
                "display_label": "Trial",
                "annual_price_cents": 0,
                "monthly_price_cents": 0,
                "is_trial": True,
                "trial_duration_days": 14,
                "is_active": False,
                "display_order": 1,
                "schedule_lanes": 5,
                "product_plan_code": "starter_plan",
                "stripe_price_id_monthly": None,
                "stripe_price_id_annual": None,
                # C-B2 fields:
                "free_period_days": 14,
                "requires_payment_method": False,
                "signup_cap": None,
                "price_locked": False,
            },
            {
                "tier_name": "starter",
                "display_label": "Starter",
                "annual_price_cents": 58800,  # $588/year (annual billing total — $49/mo × 12)
                "monthly_price_cents": 5900,  # $59/mo month-to-month premium (no annual commitment)
                "is_trial": False,
                "trial_duration_days": None,
                "is_active": False,
                "display_order": 2,
                "schedule_lanes": 5,
                "product_plan_code": "starter_plan",
                "stripe_price_id_monthly": profile.stripe_price_id(
                    "starter", "monthly"
                ),
                "stripe_price_id_annual": profile.stripe_price_id("starter", "annual"),
                # C-B2 fields:
                "free_period_days": None,
                "requires_payment_method": True,
                "signup_cap": None,
                "price_locked": False,
            },
            {
                "tier_name": "teams",
                "display_label": "Teams",
                "annual_price_cents": 178800,  # $1,788/year (annual billing total — $149/mo × 12)
                "monthly_price_cents": 17900,  # $179/mo month-to-month premium (no annual commitment)
                "is_trial": False,
                "trial_duration_days": None,
                "is_active": False,
                "display_order": 3,
                "schedule_lanes": 20,
                "product_plan_code": "teams_plan",  # SD-3: renamed from 'teams'
                "stripe_price_id_monthly": profile.stripe_price_id("teams", "monthly"),
                "stripe_price_id_annual": profile.stripe_price_id("teams", "annual"),
                # C-B2 fields:
                "free_period_days": None,
                "requires_payment_method": True,
                "signup_cap": None,
                "price_locked": False,
            },
        ]
        for tier in _subscription_tier_rows:
            existing_tier = db.execute(
                text(
                    "SELECT 1 FROM public.subscription_tier WHERE tier_name = :tier_name"
                ),
                {"tier_name": tier["tier_name"]},
            ).first()
            if existing_tier:
                print(f"  ℹ️  [subscription_tier] '{tier['tier_name']}' already exists")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.subscription_tier
                        (tier_id, tier_name, display_label, annual_price_cents, monthly_price_cents,
                         is_trial, trial_duration_days, is_active, display_order, schedule_lanes,
                         product_plan_code, stripe_price_id_monthly, stripe_price_id_annual,
                         free_period_days, requires_payment_method, signup_cap, price_locked,
                         created_at, updated_at)
                        VALUES
                        (gen_random_uuid(), :tier_name, :display_label, :annual_price_cents,
                         :monthly_price_cents, :is_trial, :trial_duration_days, :is_active,
                         :display_order, :schedule_lanes, :product_plan_code,
                         :stripe_price_id_monthly, :stripe_price_id_annual,
                         :free_period_days, :requires_payment_method, :signup_cap, :price_locked,
                         NOW(), NOW())
                    """),
                    tier,
                )
                print(f"  ✅ [subscription_tier] Inserted '{tier['tier_name']}'")

        # ── 4b. DB-MGMT-1: Env-aware idempotent stripe price ID converge ──────
        # Replaces the hardcoded test-mode price-ID patch with profile-driven
        # converge-UPDATE. Re-running with a different --stripe-mode flips the
        # 5 price-ID slots cleanly (retires the one-off SQL in
        # stripe-pricing-config.md §4). Charter is skipped until its price-ID
        # mode is classified (design §G-7). Converge touches ONLY the 5
        # price-ID columns — never pricing/lifecycle columns.
        for tier_name in convergeable_tiers():
            for interval, column in (
                ("monthly", "stripe_price_id_monthly"),
                ("annual", "stripe_price_id_annual"),
            ):
                price_id = profile.stripe_price_id(tier_name, interval)
                result = db.execute(
                    text(f"""
                        UPDATE public.subscription_tier
                        SET {column} = :price_id, updated_at = NOW()
                        WHERE tier_name = :tier_name
                        AND ({column} IS NULL OR {column} != :price_id)
                    """),
                    {"price_id": price_id, "tier_name": tier_name},
                )
                if result.rowcount > 0:
                    print(
                        f"  ✅ [subscription_tier] Converged {column} for "
                        f"tier '{tier_name}' → {price_id}"
                    )
                else:
                    print(
                        f"  ℹ️  [subscription_tier] {column} for '{tier_name}' "
                        f"already set to {price_id}"
                    )
        # Charter: converge only if its price ID is non-None in the profile.
        # Until Tom classifies the charter price-ID mode (design §G-7), the
        # charter row is left untouched by prod converge.
        charter_monthly = profile.stripe_price_id("charter", "monthly")
        if charter_monthly is not None:
            result = db.execute(
                text("""
                    UPDATE public.subscription_tier
                    SET stripe_price_id_monthly = :price_id, updated_at = NOW()
                    WHERE tier_name = 'charter'
                    AND (stripe_price_id_monthly IS NULL
                         OR stripe_price_id_monthly != :price_id)
                """),
                {"price_id": charter_monthly},
            )
            if result.rowcount > 0:
                print(
                    f"  ✅ [subscription_tier] Converged charter monthly → {charter_monthly}"
                )
            else:
                print(
                    f"  ℹ️  [subscription_tier] charter monthly already set to {charter_monthly}"
                )
        else:
            print(
                "  ⏭️  [subscription_tier] charter monthly skipped "
                "(profile has None — design §G-7: unclassified)"
            )

        # ── 4b2. Idempotent C-B2 field patch (pricing + lifecycle fields) ──────
        # Ensures existing dev/E2E DBs get correct Charter pricing + new lifecycle
        # fields on re-run. Matches the migration's Part 5 data UPDATEs.
        _c_b2_field_seed = {
            "charter": {
                "monthly_price_cents": 4900,
                "annual_price_cents": 58800,
                "free_period_days": 90,
                "requires_payment_method": False,
                "signup_cap": 12,
                "price_locked": True,
            },
            "trial": {
                "free_period_days": 14,
                "requires_payment_method": False,
                "signup_cap": None,
                "price_locked": False,
            },
            "starter": {
                "free_period_days": None,
                "requires_payment_method": True,
                "signup_cap": None,
                "price_locked": False,
            },
            "teams": {
                "free_period_days": None,
                "requires_payment_method": True,
                "signup_cap": None,
                "price_locked": False,
            },
        }
        for tier_name, fields in _c_b2_field_seed.items():
            set_clauses = ", ".join(f"{k} = :{k}" for k in fields)
            params = dict(fields, tier_name=tier_name)
            result = db.execute(
                text(
                    f"""
                    UPDATE public.subscription_tier
                    SET {set_clauses}, updated_at = NOW()
                    WHERE tier_name = :tier_name
                    """
                ),
                params,
            )
            if result.rowcount > 0:
                print(
                    f"  ✅ [subscription_tier] C-B2 fields set for tier '{tier_name}'"
                )
            else:
                print(
                    f"  ℹ️  [subscription_tier] C-B2 fields for '{tier_name}' already set"
                )

        # ── 4c. Link subscription_tier → product_plan_code ───────────────────
        for tier_name, plan_code in TIER_TO_PLAN_MAP.items():
            result = db.execute(
                text("""
                    UPDATE public.subscription_tier
                    SET product_plan_code = :plan_code, updated_at = NOW()
                    WHERE tier_name = :tier_name
                    AND (product_plan_code IS NULL OR product_plan_code != :plan_code)
                """),
                {"plan_code": plan_code, "tier_name": tier_name},
            )
            if result.rowcount > 0:
                print(
                    f"  ✅ [subscription_tier] Set product_plan_code='{plan_code}' for tier '{tier_name}'"
                )
            else:
                print(
                    f"  ℹ️  [subscription_tier] tier '{tier_name}' → '{plan_code}' already set"
                )

        # ── 4d. PLATFORM-SMS-B1: Pathway C notification_type rows ──────────────
        # 5 system notification_type rows for Pilot→owner platform SMS (campaign
        # CXXXXXX). These must exist before the notification_template loop below
        # can create their sms-channel template rows.
        _platform_sms_notification_types = [
            {
                "code": "platform_sms_double_optin",
                "name": "Platform SMS — Double Opt-In Request",
                "description": (
                    "Pathway C first message (§6 Sample 1 / §8). "
                    "Campaign-locked — do not edit without Telnyx resubmission."
                ),
            },
            {
                "code": "platform_sms_optin_reply",
                "name": "Platform SMS — Opt-In Reply (START/UNSTOP/YES)",
                "description": "§8 auto-reply. Campaign-locked.",
            },
            {
                "code": "platform_sms_optout_reply",
                "name": "Platform SMS — Opt-Out Reply (STOP)",
                "description": "§8 auto-reply. Campaign-locked. Carrier-mandatory.",
            },
            {
                "code": "platform_sms_help_reply",
                "name": "Platform SMS — Help Reply (HELP/INFO)",
                "description": "§8 auto-reply. Campaign-locked. Carrier-mandatory.",
            },
            {
                "code": "platform_payment_failed",
                "name": "Platform SMS — Subscription Payment Failed",
                "description": (
                    "§6 Sample 2 (Account Notifications). Campaign-locked. "
                    "Fires from invoice.payment_failed."
                ),
            },
            # PLATFORM-SMS-B2: Samples 3 & 4 (campaign CXXXXXX).
            {
                "code": "platform_security_new_device",
                "name": "Platform: New-Device Sign-In Alert",
                "description": (
                    "Pathway C security alert to tenant owners when a successful "
                    "sign-in occurs from a device Cognito has not remembered "
                    "(Post-Authentication trigger, newDeviceUsed). Campaign "
                    "CXXXXXX Sample 3."
                ),
            },
            {
                "code": "platform_maintenance_broadcast",
                "name": "Platform: Scheduled Maintenance Broadcast",
                "description": (
                    "Pathway C broadcast to all tenant owners announcing a "
                    "scheduled platform maintenance window (operator-run CLI). "
                    "Campaign CXXXXXX Sample 4."
                ),
            },
        ]
        for nt in _platform_sms_notification_types:
            existing = db.execute(
                text("SELECT code FROM public.notification_type WHERE code = :code"),
                {"code": nt["code"]},
            ).first()
            if existing:
                print(f"  ℹ️  [notification_type] '{nt['code']}' already exists")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.notification_type
                        (code, tenant_id, audience, name, description, is_active,
                         created_at, updated_at)
                        VALUES (:code, NULL, 'tenant', :name, :description, true,
                                NOW(), NOW())
                        ON CONFLICT (code) DO NOTHING
                    """),
                    nt,
                )
                print(f"  ✅ [notification_type] Created '{nt['code']}'")

        # ── 5. Notification Templates (StandardAuditMixin — needs created_at + updated_at) ──
        # SD-08: Use approved v1 copy for 9 known rows; fall back to placeholder for others.
        # SD-3: Added 18 new rows for 6 notification_type codes added by SD-2
        #        (job_assigned, schedule_changed, qb_sync_conflict, qb_conflict_pre_warning,
        #         gps_variance_alert, system_template_updated) × 3 channels
        notification_template_copy = {
            ("customer_communication_sent", "email"): {
                "subject": "[Customer Communication Sent] Notification",
                "body": "A customer communication was sent to {{customer_name}} via {{channel}}.",
            },
            ("customer_communication_sent", "in_app"): {
                "subject": "[Customer Communication Sent] Notification",
                "body": "Message sent to {{customer_name}}.",
            },
            ("customer_communication_sent", "push"): {
                "subject": "[Customer Communication Sent] Notification",
                "body": "Message sent to {{customer_name}}.",
            },
            ("dunning_reminder", "email"): {
                "subject": "[Dunning Reminder] Notification",
                "body": (
                    "Invoice {{invoice_number}} for {{customer_name}} is {{days_overdue}} days overdue. "
                    "Balance due: ${{amount_due}}. Review and follow up in Pilot."
                ),
            },
            ("dunning_reminder", "in_app"): {
                "subject": "[Dunning Reminder] Notification",
                "body": "Invoice {{invoice_number}} is {{days_overdue}} days overdue \u2014 ${{amount_due}} outstanding.",
            },
            ("dunning_reminder", "push"): {
                "subject": "[Dunning Reminder] Notification",
                "body": "Overdue invoice: {{invoice_number}} \u2014 ${{amount_due}} outstanding.",
            },
            ("quote_accepted", "email"): {
                "subject": "[Quote Accepted] Notification",
                "body": (
                    "{{customer_name}} accepted your quote. "
                    "Log in to Pilot to create a job and schedule the work."
                ),
            },
            ("quote_accepted", "in_app"): {
                "subject": "[Quote Accepted] Notification",
                "body": "{{customer_name}} accepted your quote.",
            },
            ("quote_accepted", "push"): {
                "subject": "[Quote Accepted] Notification",
                "body": "New quote acceptance from {{customer_name}}.",
            },
            # SD-3: Placeholder copy for 6 notification_type codes added by SD-2
            # Each type needs email, in_app, push templates (18 rows total)
            ("job_assigned", "email"): {
                "subject": "[Job Assigned] Notification",
                "body": "You have been assigned to job {{job_number}} — {{job_title}}. Scheduled: {{scheduled_date}}.",
            },
            ("job_assigned", "in_app"): {
                "subject": "[Job Assigned] Notification",
                "body": "New job assigned: {{job_number}} — {{job_title}}.",
            },
            ("job_assigned", "push"): {
                "subject": "[Job Assigned] Notification",
                "body": "New job: {{job_number}} — {{job_title}}.",
            },
            ("schedule_changed", "email"): {
                "subject": "[Schedule Changed] Notification",
                "body": "Your schedule has been updated. Job {{job_number}} is now scheduled for {{scheduled_date}}.",
            },
            ("schedule_changed", "in_app"): {
                "subject": "[Schedule Changed] Notification",
                "body": "Schedule updated for job {{job_number}}.",
            },
            ("schedule_changed", "push"): {
                "subject": "[Schedule Changed] Notification",
                "body": "Schedule change: {{job_number}} moved to {{scheduled_date}}.",
            },
            ("qb_sync_conflict", "email"): {
                "subject": "[QuickBooks Sync Conflict] Notification",
                "body": (
                    "A sync conflict was detected for {{entity_type}} {{entity_id}} in QuickBooks. "
                    "Log in to Pilot to review and resolve."
                ),
            },
            ("qb_sync_conflict", "in_app"): {
                "subject": "[QuickBooks Sync Conflict] Notification",
                "body": "QuickBooks sync conflict: {{entity_type}} {{entity_id}} requires your attention.",
            },
            ("qb_sync_conflict", "push"): {
                "subject": "[QuickBooks Sync Conflict] Notification",
                "body": "QB sync conflict detected — tap to resolve.",
            },
            ("qb_conflict_pre_warning", "email"): {
                "subject": "[QuickBooks Conflict Warning] Notification",
                "body": (
                    "A potential QuickBooks sync conflict has been detected for {{entity_type}} {{entity_id}}. "
                    "Review before it becomes a blocking conflict."
                ),
            },
            ("qb_conflict_pre_warning", "in_app"): {
                "subject": "[QuickBooks Conflict Warning] Notification",
                "body": "QB conflict warning: {{entity_type}} {{entity_id}} — review now.",
            },
            ("qb_conflict_pre_warning", "push"): {
                "subject": "[QuickBooks Conflict Warning] Notification",
                "body": "QB conflict warning — tap to review before it blocks.",
            },
            # QB-H1: connection-expiry notification (owner email/in_app/push)
            # Copy is byte-identical to the qb_h1_restore_app_service_registry migration.
            ("qb_connection_expired", "email"): {
                "subject": "[QuickBooks] Connection expired — reconnect to resume sync",
                "body": (
                    "Your QuickBooks Online connection for {{tenant_name}} has expired. "
                    "The refresh token was rejected by Intuit, so customer, invoice, and payment "
                    "sync is paused. No data was lost — queued changes will resume automatically "
                    "after you reconnect. Go to Settings → Integrations → QuickBooks → Reconnect."
                ),
            },
            ("qb_connection_expired", "in_app"): {
                "subject": "[QuickBooks] Connection expired — reconnect to resume sync",
                "body": (
                    "QuickBooks connection expired for {{tenant_name}}. "
                    "Sync is paused — reconnect in Settings → Integrations → QuickBooks."
                ),
            },
            ("qb_connection_expired", "push"): {
                "subject": "[QuickBooks] Connection expired — reconnect to resume sync",
                "body": "QuickBooks connection expired — tap to reconnect and resume sync.",
            },
            # STRIPE-CONNECT-1: Connect disconnect + dispute owner notifications
            # (byte-identical to migration d038d647ec41 — design §F.4)
            ("stripe_connect_disconnected", "email"): {
                "subject": "[Payments] Stripe account disconnected",
                "body": (
                    "Your Stripe Connect account for {{tenant_name}} has been disconnected. "
                    "Card payments on invoice links are paused, and customers now see "
                    "manual-payment instructions. Reconnect in Settings → Payment Method."
                ),
            },
            ("stripe_connect_disconnected", "in_app"): {
                "subject": "[Payments] Stripe account disconnected",
                "body": (
                    "Stripe account disconnected for {{tenant_name}}. "
                    "Card payments paused — reconnect in Settings → Payment Method."
                ),
            },
            ("stripe_connect_disconnected", "push"): {
                "subject": "[Payments] Stripe account disconnected",
                "body": "Stripe disconnected — card payments paused. Tap to reconnect.",
            },
            ("stripe_dispute_opened", "email"): {
                "subject": "[Payments] A customer disputed a payment",
                "body": (
                    "A customer has disputed a payment of {{amount}} on invoice "
                    "{{invoice_link}}. The dispute respond-by date is {{respond_by}}. "
                    "Respond in your Stripe dashboard — Pilot does not handle dispute "
                    "resolution in-app."
                ),
            },
            ("stripe_dispute_opened", "in_app"): {
                "subject": "[Payments] A customer disputed a payment",
                "body": (
                    "A customer disputed a payment of {{amount}} on invoice "
                    "{{invoice_link}}. Respond by {{respond_by}} in your Stripe dashboard."
                ),
            },
            ("stripe_dispute_opened", "push"): {
                "subject": "[Payments] A customer disputed a payment",
                "body": "Payment disputed ({{amount}}). Respond in your Stripe dashboard by {{respond_by}}.",
            },
            ("gps_variance_alert", "email"): {
                "subject": "[GPS Variance Alert] Notification",
                "body": (
                    "A GPS variance was detected for technician {{tech_name}} on job {{job_number}}. "
                    "Expected location: {{expected_location}}. Actual: {{actual_location}}."
                ),
            },
            ("gps_variance_alert", "in_app"): {
                "subject": "[GPS Variance Alert] Notification",
                "body": "GPS variance detected for {{tech_name}} on job {{job_number}}.",
            },
            ("gps_variance_alert", "push"): {
                "subject": "[GPS Variance Alert] Notification",
                "body": "GPS variance: {{tech_name}} is off-site on job {{job_number}}.",
            },
            ("system_template_updated", "email"): {
                "subject": "[System Template Updated] Notification",
                "body": (
                    "A system notification template has been updated. "
                    "Template: {{template_name}}. This may affect automated notifications sent to your customers."
                ),
            },
            ("system_template_updated", "in_app"): {
                "subject": "[System Template Updated] Notification",
                "body": "System template updated: {{template_name}}.",
            },
            ("system_template_updated", "push"): {
                "subject": "[System Template Updated] Notification",
                "body": "System update: {{template_name}} template changed.",
            },
            # C-B6: Charter free-period warning (3 channels)
            ("free_period_warning", "email"): {
                "subject": "Your Pilot free period ends soon",
                "body": (
                    "Your Pilot for Trades free period ends on {{expiry_date}}. "
                    "Add a payment method in Settings \u2192 Subscription & Billing "
                    "to keep your account running past that date."
                ),
            },
            ("free_period_warning", "in_app"): {
                "subject": "Your Pilot free period ends soon",
                "body": "Your free period ends on {{expiry_date}}. Add a payment method to keep your account running.",
            },
            ("free_period_warning", "push"): {
                "subject": "Your Pilot free period ends soon",
                "body": "Free period ends {{expiry_date}}. Add a payment method to avoid interruption.",
            },
            # PLATFORM-SMS-B1: Pathway C platform SMS templates (campaign CXXXXXX).
            # These bodies are campaign-locked verbatim strings — do NOT alter
            # punctuation, spacing, or wording. Editing requires a Telnyx portal
            # resubmission. See telnyx-10dlc-p4t-tenant-comms-campaign.md §6/§8.
            # subject=NULL for all sms rows (SMS has no subject line).
            ("platform_sms_double_optin", "sms"): {
                "subject": None,
                "body": (
                    "Pilot for Trades: Reply YES to get important account, billing & security "
                    "alerts by text. Msg freq varies. Msg & data rates may apply. "
                    "Reply HELP for help, STOP to cancel."
                ),
            },
            ("platform_sms_optin_reply", "sms"): {
                "subject": None,
                "body": (
                    "Pilot for Trades: You're opted in to account, billing & security alerts. "
                    "Msg freq varies. Msg & data rates may apply. "
                    "Reply HELP for help, STOP to cancel."
                ),
            },
            ("platform_sms_optout_reply", "sms"): {
                "subject": None,
                "body": (
                    "You have been unsubscribed from Pilot for Trades account alerts. "
                    "No further messages will be sent. Reply START to re-subscribe."
                ),
            },
            ("platform_sms_help_reply", "sms"): {
                "subject": None,
                "body": (
                    "Pilot for Trades account alerts. "
                    "For help, visit pilotfortrades.com or email info@pilotfortrades.com. "
                    "Msg & data rates may apply. Reply STOP to unsubscribe."
                ),
            },
            ("platform_payment_failed", "sms"): {
                "subject": None,
                "body": (
                    "Pilot for Trades: Your payment didn't go through. Please login to "
                    "app.pilotfortrades.com and update your credit card to keep your account "
                    "active. Reply STOP to opt out."
                ),
            },
            # PLATFORM-SMS-B2: Samples 3 & 4 (campaign CXXXXXX).
            # Sample 3 — stored fully static (verbatim from playbook §6).
            ("platform_security_new_device", "sms"): {
                "subject": None,
                "body": (
                    "Pilot for Trades: New sign-in to your account from a new device. "
                    "If this wasn't you, secure your account now. Reply STOP to opt out."
                ),
            },
            # Sample 4 — stored with {{ maint_date }} / {{ maint_window }} Jinja
            # placeholders; renders to the registered string. No en-dash in the
            # stored row (the en-dash is in the registered render values only).
            ("platform_maintenance_broadcast", "sms"): {
                "subject": None,
                "body": (
                    "Pilot for Trades: Scheduled maintenance {{ maint_date }} from "
                    "{{ maint_window }}. The app may be briefly unavailable. "
                    "Reply STOP to opt out."
                ),
            },
        }

        notification_types = db.execute(
            text(
                "SELECT code FROM public.notification_type WHERE is_active = true ORDER BY code"
            )
        ).fetchall()
        channels = ["email", "in_app", "push"]

        for nt in notification_types:
            for channel in channels:
                copy = notification_template_copy.get(
                    (nt.code, channel),
                    {
                        "subject": f"[{nt.code.replace('_', ' ').title()}] Notification",
                        "body": f"This is a placeholder {nt.code} notification via {channel}.",
                    },
                )
                existing = db.execute(
                    text("""
                        SELECT id FROM public.notification_template
                        WHERE notification_type_code = :type_code
                        AND channel = :channel AND tenant_id IS NULL
                    """),
                    {"type_code": nt.code, "channel": channel},
                ).first()
                if existing:
                    # SD-08: Update body with approved copy on subsequent seed runs
                    db.execute(
                        text("""
                            UPDATE public.notification_template
                            SET body = :body, subject = :subject, updated_at = NOW()
                            WHERE notification_type_code = :type_code
                            AND channel = :channel AND tenant_id IS NULL
                        """),
                        {
                            "type_code": nt.code,
                            "channel": channel,
                            "subject": copy["subject"],
                            "body": copy["body"],
                        },
                    )
                    print(f"  ℹ️  [notification_template] {nt.code}/{channel} updated")
                else:
                    try:
                        db.execute(
                            text("""
                                INSERT INTO public.notification_template
                                (id, tenant_id, notification_type_code, channel, locale,
                                 subject, body, is_active, created_at, updated_at)
                                VALUES (gen_random_uuid(), NULL, :type_code, :channel, 'en',
                                        :subject, :body, true, NOW(), NOW())
                                ON CONFLICT DO NOTHING
                            """),
                            {
                                "type_code": nt.code,
                                "channel": channel,
                                "subject": copy["subject"],
                                "body": copy["body"],
                            },
                        )
                        print(
                            f"  ✅ [notification_template] Created {nt.code}/{channel}"
                        )
                    except Exception as e:
                        # Quietly skip if check constraint rejects the channel value
                        db.rollback()
                        print(
                            f"  ⚠️  [notification_template] {nt.code}/{channel} skipped: {e}"
                        )

        # ── 5b. PLATFORM-SMS-B1: Pathway C sms-channel templates ─────────────
        # The loop above only handles email/in_app/push channels. The 5
        # campaign-locked sms templates need a separate insert (channel='sms',
        # subject=NULL). Idempotent: update-or-insert keyed on
        # (notification_type_code, channel='sms', tenant_id IS NULL).
        _platform_sms_type_codes = [
            "platform_sms_double_optin",
            "platform_sms_optin_reply",
            "platform_sms_optout_reply",
            "platform_sms_help_reply",
            "platform_payment_failed",
            # PLATFORM-SMS-B2: Samples 3 & 4.
            "platform_security_new_device",
            "platform_maintenance_broadcast",
        ]
        for sms_type_code in _platform_sms_type_codes:
            copy = notification_template_copy.get((sms_type_code, "sms"))
            if copy is None:
                continue
            existing = db.execute(
                text("""
                    SELECT id FROM public.notification_template
                    WHERE notification_type_code = :type_code
                    AND channel = 'sms' AND tenant_id IS NULL
                """),
                {"type_code": sms_type_code},
            ).first()
            if existing:
                db.execute(
                    text("""
                        UPDATE public.notification_template
                        SET body = :body, subject = NULL, updated_at = NOW()
                        WHERE notification_type_code = :type_code
                        AND channel = 'sms' AND tenant_id IS NULL
                    """),
                    {
                        "type_code": sms_type_code,
                        "body": copy["body"],
                    },
                )
                print(f"  ℹ️  [notification_template] {sms_type_code}/sms updated")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.notification_template
                        (id, tenant_id, notification_type_code, channel, locale,
                         subject, body, is_active, created_at, updated_at)
                        VALUES (gen_random_uuid(), NULL, :type_code, 'sms', 'en',
                                NULL, :body, true, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "type_code": sms_type_code,
                        "body": copy["body"],
                    },
                )
                print(f"  ✅ [notification_template] Created {sms_type_code}/sms")

        # ── subscription_status (6 rows — global platform config) ────────────────
        for ss in SUBSCRIPTION_STATUS_ROWS:
            existing = db.execute(
                text(
                    "SELECT 1 FROM public.subscription_status WHERE code = :code AND tenant_id IS NULL"
                ),
                {"code": ss["code"]},
            ).first()
            if existing:
                print(f"  ℹ️  [subscription_status] '{ss['code']}' already exists")
            else:
                db.execute(
                    text("""
                        INSERT INTO public.subscription_status
                        (id, tenant_id, code, name, is_billing_active, created_at, updated_at)
                        VALUES (gen_random_uuid(), NULL, :code, :name, :is_billing_active, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    ss,
                )
                print(f"  ✅ [subscription_status] Inserted '{ss['code']}'")

        # ── carrier_fee_schedule (C-B8/C-B9 10DLC carrier fee config) ─────────
        # Operator-maintained config table. Telnyx has no public pre-transaction
        # pricing API (Q#1), so fees are stored here and read at quote time.
        # C-B9: temporal lookup with millicents precision (1 millicent = $0.00001).
        # effective_to IS NULL means the row is current.
        carrier_fees = [
            # (fee_code, entity_type, amount_millicents, description)
            ("brand_registration", "standard", 400000, "Brand registration"),
            ("brand_registration", "sole_proprietor", 400000, "Brand registration"),
            (
                "campaign_registration_3mo",
                "standard",
                1500000,
                "Campaign registration (3 months prepaid)",
            ),
            (
                "campaign_registration_3mo",
                "sole_proprietor",
                1000000,
                "Campaign registration (3 months prepaid)",
            ),
            ("phone_number", "standard", 100000, "Phone number assignment"),
            (
                "phone_number",
                "sole_proprietor",
                100000,
                "Phone number assignment",
            ),
            ("campaign_quarterly", "standard", 1500000, "Campaign quarterly recurring"),
            (
                "campaign_quarterly",
                "sole_proprietor",
                1000000,
                "Campaign quarterly recurring",
            ),
            # C-B9: 12 new fee codes (surcharges + brand_vetting + tmobile + assignment)
            ("brand_vetting", "standard", 4000000, "External brand vetting (optional)"),
            (
                "brand_vetting",
                "sole_proprietor",
                4000000,
                "External brand vetting (optional)",
            ),
            (
                "campaign_registration_tmobile",
                "standard",
                5000000,
                "T-Mobile campaign registration (currently waived)",
            ),
            (
                "campaign_registration_tmobile",
                "sole_proprietor",
                5000000,
                "T-Mobile campaign registration (currently waived)",
            ),
            (
                "phone_number_assignment",
                "standard",
                30,
                "Phone number to campaign assignment",
            ),
            (
                "phone_number_assignment",
                "sole_proprietor",
                30,
                "Phone number to campaign assignment",
            ),
            ("surcharge_att", "standard", 300, "Per-segment surcharge (AT&T)"),
            ("surcharge_att", "sole_proprietor", 300, "Per-segment surcharge (AT&T)"),
            ("surcharge_tmobile", "standard", 300, "Per-segment surcharge (T-Mobile)"),
            (
                "surcharge_tmobile",
                "sole_proprietor",
                300,
                "Per-segment surcharge (T-Mobile)",
            ),
            ("surcharge_verizon", "standard", 310, "Per-segment surcharge (Verizon)"),
            (
                "surcharge_verizon",
                "sole_proprietor",
                310,
                "Per-segment surcharge (Verizon)",
            ),
        ]
        for fee_code, entity_type, amount_millicents, description in carrier_fees:
            existing = db.execute(
                text(
                    "SELECT 1 FROM public.carrier_fee_schedule "
                    "WHERE fee_code = :fee_code AND entity_type = :entity_type "
                    "AND effective_to IS NULL"
                ),
                {"fee_code": fee_code, "entity_type": entity_type},
            ).first()
            if existing:
                print(
                    f"  ℹ️  [carrier_fee_schedule] {fee_code}/{entity_type} already exists"
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO public.carrier_fee_schedule
                        (fee_code, entity_type, amount_millicents, description,
                         effective_from, effective_to, created_at, updated_at)
                        VALUES (:fee_code, :entity_type, :amount_millicents, :description,
                                NOW(), NULL, NOW(), NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "fee_code": fee_code,
                        "entity_type": entity_type,
                        "amount_millicents": amount_millicents,
                        "description": description,
                    },
                )
                print(
                    f"  ✅ [carrier_fee_schedule] Inserted {fee_code}/{entity_type} "
                    f"({amount_millicents} millicents)"
                )

        db.commit()

    print("\n🎉 seed_platform complete — Group B platform config present.")


def mode_inspect():
    """Show current state of Group B platform config."""
    print("=== seed_platform: inspect mode ===\n")

    with get_db_session() as db:
        plans = db.execute(
            text("SELECT code, name, is_active FROM public.product_plan ORDER BY code")
        ).fetchall()
        print(f"  [product_plan]  {len(plans)} row(s)")
        for p in plans:
            print(f"    • {p.code}  '{p.name}'  is_active={p.is_active}")
        print()

        versions = db.execute(
            text(
                "SELECT id, product_plan_code, name, price_cents FROM public.product_plan_version ORDER BY product_plan_code"
            )
        ).fetchall()
        print(f"  [product_plan_version]  {len(versions)} row(s)")
        for v in versions:
            print(
                f"    • id={v.id}  plan={v.product_plan_code}  '{v.name}'  price_cents={v.price_cents}"
            )
        print()

        feature_limits = db.execute(
            text("""
                SELECT product_plan_code, product_feature_code, limit_quantity, limit_enforcement
                FROM public.product_plan_product_feature_version
                ORDER BY product_plan_code, product_feature_code
            """)
        ).fetchall()
        print(f"  [product_plan_product_feature_version]  {len(feature_limits)} row(s)")
        for fl in feature_limits:
            print(
                f"    • {fl.product_plan_code}/{fl.product_feature_code}  limit={fl.limit_quantity}  enforcement={fl.limit_enforcement}"
            )
        print()

        # SD-3: Updated to reference renamed + new columns
        # C-B2: Added free_period_days, requires_payment_method, signup_cap, price_locked
        tiers = db.execute(
            text("""
                SELECT tier_name, product_plan_code, annual_price_cents, monthly_price_cents,
                       stripe_price_id_monthly, stripe_price_id_annual,
                       free_period_days, requires_payment_method, signup_cap, price_locked
                FROM public.subscription_tier
                ORDER BY display_order
            """)
        ).fetchall()
        print(f"  [subscription_tier → product_plan_code]  {len(tiers)} row(s)")
        for t in tiers:
            print(
                f"    • {t.tier_name}  → {t.product_plan_code or '(not linked)'}  "
                f"annual={t.annual_price_cents}¢  m2m={t.monthly_price_cents}¢  "
                f"stripe_monthly={t.stripe_price_id_monthly or 'NULL'}  "
                f"stripe_annual={t.stripe_price_id_annual or 'NULL'}"
            )
            print(
                f"      C-B2: free_days={t.free_period_days}  "
                f"card_req={t.requires_payment_method}  "
                f"cap={t.signup_cap}  locked={t.price_locked}"
            )
        print()

        templates = db.execute(
            text("""
                SELECT notification_type_code, channel, locale, is_active
                FROM public.notification_template
                WHERE tenant_id IS NULL
                ORDER BY notification_type_code, channel
            """)
        ).fetchall()
        print(f"  [notification_template]  {len(templates)} row(s)")
        for t in templates:
            print(
                f"    • {t.notification_type_code}/{t.channel}  locale={t.locale}  is_active={t.is_active}"
            )

        # subscription_status
        try:
            rows = db.execute(
                text(
                    "SELECT code, name, is_billing_active FROM public.subscription_status "
                    "WHERE tenant_id IS NULL ORDER BY code"
                )
            ).fetchall()
            print(f"\n  [subscription_status]  {len(rows)} row(s)")
            for r in rows:
                print(
                    f"    • {r.code:<12}  '{r.name}'  billing_active={r.is_billing_active}"
                )
        except Exception as e:
            print(f"  [subscription_status]  ERROR: {e}")


def mode_show(profile: EnvProfile):
    """Print what would be seeded without touching the DB.

    DB-MGMT-1: prints which Stripe price IDs *would* be written per tier
    for the resolved profile, without touching the DB.
    """
    print("=== seed_platform: show mode ===\n")
    print(
        f"Stripe price IDs (env={profile.env.value}, "
        f"stripe_mode={profile.stripe_mode.value if profile.stripe_mode else '(none)'}):"
    )
    for tier_name in ("charter", "trial", "starter", "teams"):
        monthly = profile.stripe_price_id(tier_name, "monthly")
        annual = profile.stripe_price_id(tier_name, "annual")
        converge_mark = " [converge]" if tier_name in convergeable_tiers() else ""
        print(
            f"  {tier_name:<10}  monthly={monthly or 'NULL':<32}  "
            f"annual={annual or 'NULL'}{converge_mark}"
        )
    print()
    print(f"Product Plans ({len(PRODUCT_PLANS)}):")
    for p in PRODUCT_PLANS:
        active_str = "ACTIVE" if p["is_active"] else "dormant"
        print(f"  {p['code']}  '{p['name']}'  [{active_str}]")
    print("\nProduct Plan Versions: 1 active version per plan (AppendOnly)")
    print("  Plan prices:")
    for code, price in PRODUCT_PLAN_PRICES.items():
        print(f"    {code}: {price}¢ (${price / 100:.2f}/mo)")
    print("\nProduct Feature Limits (MKT-B11 v3.0 / SD-3):")
    for plan_code, limits in PLAN_FEATURE_LIMITS.items():
        print(f"  [{plan_code}]")
        for feature, cfg in limits.items():
            overage = (
                f"overage={cfg['overage_cents']}¢"
                if cfg["overage_cents"]
                else "no_overage"
            )
            print(
                f"    {feature}: limit={cfg['limit']}  {overage}  enforcement={cfg['enforcement']}"
            )
    print("\nSubscription Tier → Plan Mappings:")
    for tier, plan in TIER_TO_PLAN_MAP.items():
        print(f"  {tier} → {plan}")
    print(
        "\nNotification Templates: approved v1 copy for 9 original types + SD-3 placeholder rows "
        "for 6 SD-2 types (27 total = 9 types × 3 channels)"
    )
    print(f"\nSubscription Statuses ({len(SUBSCRIPTION_STATUS_ROWS)}):")
    for ss in SUBSCRIPTION_STATUS_ROWS:
        billing = (
            "billing_active=true" if ss["is_billing_active"] else "billing_active=false"
        )
        print(f"  {ss['code']:<12}  '{ss['name']}'  [{billing}]")


if __name__ == "__main__":
    args = parse_args()
    profile = resolve_profile_from_args(args)
    assert_group_allowed(profile, "B", "seed_platform.py")
    db_url = os.environ.get("DATABASE_URL", "")
    if args.mode in ("seed", "inspect"):
        assert_target_compatible(profile, db_url)
    print_seed_banner(profile, db_url, "seed_platform.py")
    if args.mode == "seed":
        mode_seed(profile)
    elif args.mode == "inspect":
        mode_inspect()
    elif args.mode == "show":
        mode_show(profile)
