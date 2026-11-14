# Batch SD-3 Design — Group B Platform Seed Audit & Billing Schema Expansion

**Version**: 1.0  
**Date**: 2026-07-14  
**Author**: Pilot Architect  
**Status**: READY FOR IMPLEMENTATION  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1  
**Companion batch**: STRIPE-B1 — Annual Billing Service + Founders Schedule (must immediately follow SD-3)

---

## Table of Contents

- [A. Input Read Summary](#a-input-read-summary)
- [B. Migration Plan](#b-migration-plan)
- [C. Execution Order](#c-execution-order)
- [D. Schema Changes](#d-schema-changes)
- [E. Seed Script Changes](#e-seed-script-changes--seed_platformpy)
- [F. Notification Template Gap](#f-notification-template-gap)
- [G. New Documentation Deliverables](#g-new-documentation-deliverables)
- [H. Open Questions Resolved](#h-open-questions-resolved)
- [I. What Is Deferred to STRIPE-B1](#i-what-is-deferred-to-stripe-b1)

---

## A. Input Read Summary

All inputs verified before this design was written:

| Input | Key Finding |
|---|---|
| `backend/migrations/scripts/seed_platform.py` | Live DB matches seed on product_plan (3 rows), ppfv (9 rows), subscription_tier (4 rows), subscription_status (6 rows) — no drift. seed has bug: `product_plan_version price_cents = 0` hardcoded; live DB has correct prices set by MKT-B11 migration. |
| `backend/README-seed-data.md` | Group B fully documented. SD-08 added approved notification template copy for 3 notification_types × 3 channels = 9 rows. SD-2 added 6 new notification_type rows — none have template rows yet (18 missing). |
| `dev-docs/analysis/pilot-launch-plan.md` | Annual billing and founders cohort auto-upgrade both listed as required before GA. STRIPE-B1 designed as companion batch for service-layer changes. |
| `dev-docs/integrations/stripe/stripe-pricing-config.md` | §7 documents annual billing as the default display price ($49/mo = $588/yr). Month-to-month is premium pricing ($59/mo). Only monthly prices exist in Stripe Dashboard today. |
| Live DB — `product_plan` | 3 rows: `founders_plan` (active), `starter_plan` (dormant), `teams` (dormant). `teams` naming is inconsistent with the `_plan` suffix convention — rename approved. |
| Live DB — `product_plan_version` | 3 rows. `founders_plan price_cents = 4900` is WRONG — founders plan list price is $0 (6-month free cohort; $49/mo billing activates in month 7 as a subscription-level event, not a plan-price change). |
| Live DB — `subscription_tier` | 4 rows. `monthly_price_cents` column currently stores the annual-rate-expressed-as-per-month ($49, $149). This is the display price, not the month-to-month Stripe charge. Month-to-month pricing ($59/$179) has no column. Annual Stripe price IDs have no column. |
| Live DB — `subscription_status` | 6 rows, all correct. No changes needed. |
| Live DB — `notification_template` | 9 rows (3 types × 3 channels with SD-08 approved copy). 6 notification_type rows added in SD-2 have zero template rows. |
| `backend/services/stripe_subscriptions.py` | Reads `tier.stripe_price_id` for Stripe subscription routing. Renaming this column in SD-3 requires updating the SQLModel field in `app/models/subscription.py`. Service routing logic update is STRIPE-B1 scope. |

---

## B. Migration Plan

### B.1 Pre-Migration DB State (MCP-verified 2026-07-14)

```sql
-- subscription_tier columns (relevant)
monthly_price_cents  INTEGER  NOT NULL  -- currently holds annual-rate display price (4900/14900)
stripe_price_id      TEXT     NULL      -- currently holds monthly Stripe test-mode price IDs

-- product_plan current codes
founders_plan, starter_plan, teams   -- 'teams' missing _plan suffix

-- product_plan_version
founders_plan  price_cents=4900  -- WRONG: founders plan list price should be 0
starter_plan   price_cents=4900  -- CORRECT
teams          price_cents=14900 -- CORRECT (but plan code will be renamed)
```

### B.2 Migration 1 — `teams` → `teams_plan` rename (FK cascade)

**Why**: Cosmetic consistency with `founders_plan` / `starter_plan` naming. All three plan codes should use the `_plan` suffix. No functional behavior changes.

**Tables with FK on `product_plan.code`:**
- `product_plan_version.product_plan_code`
- `product_plan_product_feature_version.product_plan_code`
- `subscription_tier.product_plan_code`
- `subscription.product_plan_code` (may have live rows for test tenant)

**Migration approach**: Disable FK triggers, UPDATE all affected columns, re-enable.

```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Step 1: Rename the plan code itself
    op.execute("""
        UPDATE public.product_plan
        SET code = 'teams_plan', updated_at = NOW()
        WHERE code = 'teams';
    """)

    # Step 2: Cascade to child tables
    op.execute("""
        UPDATE public.product_plan_version
        SET product_plan_code = 'teams_plan'
        WHERE product_plan_code = 'teams';
    """)
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET product_plan_code = 'teams_plan'
        WHERE product_plan_code = 'teams';
    """)
    op.execute("""
        UPDATE public.subscription_tier
        SET product_plan_code = 'teams_plan', updated_at = NOW()
        WHERE product_plan_code = 'teams';
    """)
    op.execute("""
        UPDATE public.subscription
        SET product_plan_code = 'teams_plan', updated_at = NOW()
        WHERE product_plan_code = 'teams';
    """)
```

```python
def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("UPDATE public.subscription SET product_plan_code = 'teams', updated_at = NOW() WHERE product_plan_code = 'teams_plan';")
    op.execute("UPDATE public.subscription_tier SET product_plan_code = 'teams', updated_at = NOW() WHERE product_plan_code = 'teams_plan';")
    op.execute("UPDATE public.product_plan_product_feature_version SET product_plan_code = 'teams' WHERE product_plan_code = 'teams_plan';")
    op.execute("UPDATE public.product_plan_version SET product_plan_code = 'teams' WHERE product_plan_code = 'teams_plan';")
    op.execute("UPDATE public.product_plan SET code = 'teams', updated_at = NOW() WHERE code = 'teams_plan';")
```

### B.3 Migration 2 — Annual billing schema + `founders_plan` price fix

**Why**: `subscription_tier` currently has one price column (`monthly_price_cents`) and one Stripe price ID column (`stripe_price_id`). Both are ambiguously named. The pricing model has two billing intervals (annual default; month-to-month premium). Each needs its own price and Stripe price ID. Additionally, `founders_plan` in `product_plan_version` has wrong `price_cents = 4900`.

**3-Part NOT NULL pattern** for new columns on existing table:

```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # ── Step 1: Rename existing columns to reflect their true meaning ────────
    # monthly_price_cents currently holds the annual-rate display price ($49/$149)
    # Rename to annual_price_cents to make its purpose explicit.
    op.alter_column('subscription_tier', 'monthly_price_cents',
                    new_column_name='annual_price_cents',
                    schema='public')

    # stripe_price_id currently holds the monthly billing Stripe price ID.
    # Rename to stripe_price_id_monthly — STRIPE-B1 will route correctly.
    op.alter_column('subscription_tier', 'stripe_price_id',
                    new_column_name='stripe_price_id_monthly',
                    schema='public')

    # ── Step 2a: Add monthly_price_cents (Part 1 — nullable first) ──────────
    op.add_column('subscription_tier',
                  sa.Column('monthly_price_cents', sa.Integer(), nullable=True),
                  schema='public')

    # ── Step 2b: Backfill monthly_price_cents (Part 2) ───────────────────────
    op.execute("""
        UPDATE public.subscription_tier
        SET monthly_price_cents = CASE
            WHEN tier_name = 'starter' THEN 5900
            WHEN tier_name = 'teams'   THEN 17900
            ELSE 0
        END;
    """)

    # ── Step 2c: Lock NOT NULL (Part 3) ──────────────────────────────────────
    op.alter_column('subscription_tier', 'monthly_price_cents',
                    nullable=False, server_default='0', schema='public')

    # ── Step 3: Add stripe_price_id_annual (nullable — Tom populates via Stripe) ──
    op.add_column('subscription_tier',
                  sa.Column('stripe_price_id_annual', sa.Text(), nullable=True),
                  schema='public')

    # ── Step 4: Fix founders_plan product_plan_version price_cents ───────────
    # MKT-B11 migration incorrectly set price_cents=4900 for founders_plan.
    # founders_plan list price is $0 (free cohort period). Billing activates
    # at month 7 as a Stripe subscription schedule event (STRIPE-B1 scope).
    op.execute("""
        UPDATE public.product_plan_version
        SET price_cents = 0
        WHERE product_plan_code = 'founders_plan'
          AND price_cents != 0;
    """)
    # Note: starter_plan (4900) and teams/teams_plan (14900) are already correct.
```

```python
def downgrade() -> None:
    # Remove the new columns
    op.drop_column('subscription_tier', 'stripe_price_id_annual', schema='public')
    op.drop_column('subscription_tier', 'monthly_price_cents', schema='public')

    # Rename columns back
    op.alter_column('subscription_tier', 'stripe_price_id_monthly',
                    new_column_name='stripe_price_id', schema='public')
    op.alter_column('subscription_tier', 'annual_price_cents',
                    new_column_name='monthly_price_cents', schema='public')

    # Restore founders_plan price_cents (downgrade restores to MKT-B11 value)
    op.execute("""
        UPDATE public.product_plan_version
        SET price_cents = 4900
        WHERE product_plan_code = 'founders_plan'
          AND price_cents = 0;
    """)
```

### B.4 MCP Pre-Work Verification Queries

The Python Engineer MUST run all of these before touching any file:

```sql
-- 1. Verify subscription_tier current columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;

-- 2. Verify product_plan current codes
SELECT code, name, is_active FROM public.product_plan ORDER BY code;

-- 3. Verify product_plan_version current price_cents
SELECT product_plan_code, price_cents FROM public.product_plan_version ORDER BY product_plan_code;

-- 4. Verify subscription rows referencing 'teams' plan code
SELECT COUNT(*) FROM public.subscription WHERE product_plan_code = 'teams';

-- 5. Verify ppfv rows referencing 'teams'
SELECT COUNT(*) FROM public.product_plan_product_feature_version WHERE product_plan_code = 'teams';

-- 6. Verify notification_template gap (should show only 9 rows — 3 types × 3 channels)
SELECT notification_type_code, COUNT(*) AS channel_count
FROM public.notification_template
WHERE tenant_id IS NULL
GROUP BY notification_type_code
ORDER BY notification_type_code;

-- 7. Verify all 9 notification_type codes currently active
SELECT code FROM public.notification_type WHERE is_active = true ORDER BY code;

-- 8. Verify alembic current head
SELECT version_num FROM public.alembic_version;
```

---

## C. Execution Order

| Step | Task | File(s) Touched |
|---|---|---|
| 1 | Run MCP pre-work verification queries — confirm all 8 results match expected | — |
| 2 | Write blank Alembic migration 1: `teams` → `teams_plan` FK cascade | `migrations/versions/YYYY_MM_DD_*_sd3_teams_plan_rename.py` |
| 3 | `alembic upgrade head` → verify rename applied | — |
| 4 | Write blank Alembic migration 2: annual billing schema + founders_plan price fix | `migrations/versions/YYYY_MM_DD_*_sd3_annual_billing_schema.py` |
| 5 | Update SQLModel: rename fields in `SubscriptionTier` model | `app/models/subscription.py` |
| 6 | `alembic upgrade head` → verify new columns exist | — |
| 7 | Run `python generate_db_model_map.py` → verify `SubscriptionTier` fields updated | `db_models_map.md` |
| 8 | Update `seed_platform.py` — 6 changes (see §E) | `migrations/scripts/seed_platform.py` |
| 9 | Add 18 placeholder notification_template rows to `seed_platform.py` (see §F) | `migrations/scripts/seed_platform.py` |
| 10 | Run `python migrations/scripts/seed_platform.py` → verify output | — |
| 11 | Write tests: 2 test files covering schema + seed correctness | `tests/domains/subscriptions_usage/test_sd3_billing_schema.py`, `tests/domains/notifications_comms/test_sd3_notification_templates.py` |
| 12 | Run `pytest -m unit --tb=short -q` → confirm clean pass | — |
| 13 | Run `pytest --tb=short -q` → confirm full suite passes | — |
| 14 | Run `python schema_manager.py --help` → use CRUD commands to update JSON schema for `subscription_tier` new/renamed columns | `dev-docs/db-design/pilot-db-schema-v2.6h.json` |
| 15 | Update `stripe-pricing-config.md` with annual billing price spec (Tom actions documented) | `dev-docs/integrations/stripe/stripe-pricing-config.md` |
| 16 | Write `pilot-docs-list.md` (root) | `/pilot-docs-list.md` |
| 17 | Write `dev-docs/pilot-operations.md` | `dev-docs/pilot-operations.md` |
| 18 | Update `README-seed-data.md` Group B table + §10 to reflect SD-3 | `backend/README-seed-data.md` |
| 19 | Update `pilot-launch-plan.md` — add SD-3 to Appendix A; update STRIPE-B1 as new P1 task | `dev-docs/analysis/pilot-launch-plan.md` |

---

## D. Schema Changes

### D.1 `subscription_tier` — Column Renames + Additions

| Column | Change | Old Type | New Type | Rationale |
|---|---|---|---|---|
| `monthly_price_cents` | RENAME → `annual_price_cents` | `INTEGER NOT NULL` | `INTEGER NOT NULL` | This column has always held the annual-rate display price per month ($49/$149). Renaming makes its purpose explicit. |
| `stripe_price_id` | RENAME → `stripe_price_id_monthly` | `TEXT NULL` | `TEXT NULL` | This column holds the Stripe monthly billing price ID. Renaming disambiguates from the new annual column. |
| `monthly_price_cents` *(new)* | ADD | — | `INTEGER NOT NULL DEFAULT 0` | Holds the month-to-month (premium) price: Starter=$59/mo (5900¢), Teams=$179/mo (17900¢), founders=0, trial=0. |
| `stripe_price_id_annual` *(new)* | ADD | — | `TEXT NULL` | Tom creates annual prices in Stripe Dashboard; engineer seeds NULL; populated via `seed_platform.py` patch block when IDs exist. |

**Seed values after migration:**

| tier_name | annual_price_cents | monthly_price_cents | stripe_price_id_monthly | stripe_price_id_annual |
|---|---|---|---|---|
| founders | 0 | 0 | NULL | NULL |
| trial | 0 | 0 | NULL | NULL |
| starter | 4900 | 5900 | `price_REDACTED...` (test) | NULL (Tom creates) |
| teams_plan | 14900 | 17900 | `price_REDACTED...` (test) | NULL (Tom creates) |

> **NOTE**: `stripe_price_id_monthly` will be updated by `seed_platform.py` idempotent patch block. The annual price IDs are NULL until Tom creates annual Stripe prices (documented in updated `stripe-pricing-config.md`).

### D.2 `product_plan` — Code Rename

| Old code | New code | Affected tables |
|---|---|---|
| `teams` | `teams_plan` | `product_plan`, `product_plan_version`, `product_plan_product_feature_version`, `subscription_tier`, `subscription` |

### D.3 `product_plan_version` — Data Fix

| plan_code | Old `price_cents` | New `price_cents` | Why |
|---|---|---|---|
| `founders_plan` | 4900 ❌ | 0 ✅ | Founders plan list price is $0. The $49/mo billing that activates at month 7 is a Stripe subscription schedule event, not a plan-price change. This is a historical ledger record of the plan's launch price. |
| `starter_plan` | 4900 ✅ | 4900 | No change |
| `teams` → `teams_plan` | 14900 ✅ | 14900 | No change (code cascaded by Migration 1) |

### D.4 SQLModel Changes Required in `app/models/subscription.py`

The Python Engineer must update the `SubscriptionTier` SQLModel class field names to match the renamed columns:

```python
# BEFORE
monthly_price_cents: int = Field(...)
stripe_price_id: str | None = Field(default=None)

# AFTER
annual_price_cents: int = Field(...)          # renamed
monthly_price_cents: int = Field(default=0)   # new column — month-to-month premium price
stripe_price_id_monthly: str | None = Field(default=None)   # renamed
stripe_price_id_annual: str | None = Field(default=None)    # new column
```

> **⚠️ Code impact**: `stripe_subscriptions.py` reads `tier.stripe_price_id` for Stripe routing. After SD-3, this becomes `tier.stripe_price_id_monthly`. The service still compiles because `stripe_price_id` no longer exists as a field — it will produce a `AttributeError` at runtime for any paid subscription creation attempt. This is acceptable pre-GA since no real paid subscriptions exist. STRIPE-B1 MUST fix this before any tenant can upgrade to a paid plan.

---

## E. Seed Script Changes — `seed_platform.py`

Six changes required in `seed_platform.py`:

### E.1 `PRODUCT_PLANS` — Update `teams` code

```python
# BEFORE
{"code": "teams", "name": "Teams Plan", ...}

# AFTER
{"code": "teams_plan", "name": "Teams Plan", ...}
```

### E.2 `TIER_TO_PLAN_MAP` — Update `teams` value

```python
# BEFORE
TIER_TO_PLAN_MAP = {
    "founders": "founders_plan",
    "trial": "starter_plan",
    "starter": "starter_plan",
    "teams": "teams",
}

# AFTER
TIER_TO_PLAN_MAP = {
    "founders": "founders_plan",
    "trial": "starter_plan",
    "starter": "starter_plan",
    "teams": "teams_plan",   # ← updated
}
```

### E.3 `PLAN_FEATURE_LIMITS` — Update `teams` key

```python
# BEFORE
PLAN_FEATURE_LIMITS = {
    "founders_plan": {...},
    "starter_plan": {...},
    "teams": {...},          # ← old key
}

# AFTER
PLAN_FEATURE_LIMITS = {
    "founders_plan": {...},
    "starter_plan": {...},
    "teams_plan": {...},     # ← renamed key
}
```

### E.4 `_SUBSCRIPTION_TIER_ROWS` — Update `teams` tier, add annual/monthly price columns

Update the `teams` tier row's `product_plan_code` value AND add the two new price fields to all 4 tier rows:

```python
_SUBSCRIPTION_TIER_ROWS = [
    {
        "tier_name": "founders",
        "display_label": "Founders",
        "annual_price_cents": 0,          # renamed field
        "monthly_price_cents": 0,         # new field (month-to-month = $0 during cohort)
        "is_trial": False,
        "trial_duration_days": None,
        "is_active": True,
        "display_order": 0,
        "schedule_lanes": 5,
        "product_plan_code": "founders_plan",
        "stripe_price_id_monthly": None,  # renamed field
        "stripe_price_id_annual": None,   # new field
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
    },
    {
        "tier_name": "starter",
        "display_label": "Starter",
        "annual_price_cents": 4900,        # $49/mo expressed as annual display rate
        "monthly_price_cents": 5900,       # $59/mo month-to-month premium
        "is_trial": False,
        "trial_duration_days": None,
        "is_active": False,
        "display_order": 2,
        "schedule_lanes": 5,
        "product_plan_code": "starter_plan",
        "stripe_price_id_monthly": "price_REDACTED03",  # test mode
        "stripe_price_id_annual": None,    # Tom creates; populated when available
    },
    {
        "tier_name": "teams",
        "display_label": "Teams",
        "annual_price_cents": 14900,       # $149/mo expressed as annual display rate
        "monthly_price_cents": 17900,      # $179/mo month-to-month premium
        "is_trial": False,
        "trial_duration_days": None,
        "is_active": False,
        "display_order": 3,
        "schedule_lanes": 20,
        "product_plan_code": "teams_plan", # ← renamed
        "stripe_price_id_monthly": "price_REDACTED04",  # test mode
        "stripe_price_id_annual": None,    # Tom creates; populated when available
    },
]
```

### E.5 Idempotent Stripe Price Patch Block — Update column names

```python
# Update _STRIPE_PRICE_SEED to use new column names
_STRIPE_PRICE_SEED = {
    "starter": {
        "stripe_price_id_monthly": "price_REDACTED03",
    },
    "teams": {
        "stripe_price_id_monthly": "price_REDACTED04",
    },
}
# Patch block UPDATE must reference stripe_price_id_monthly column (not stripe_price_id)
```

### E.6 `product_plan_version` Seed — Fix `price_cents` Values

The seed currently hardcodes `price_cents = 0` for ALL plans. Fix to reflect true list prices:

```python
PRODUCT_PLAN_VERSIONS = {
    "founders_plan": {"price_cents": 0},     # Free during cohort; billing activates month 7 via Stripe schedule
    "starter_plan":  {"price_cents": 4900},  # $49/mo annual display price
    "teams_plan":    {"price_cents": 14900}, # $149/mo annual display price
}
```

The `mode_seed()` product_plan_version INSERT block must use these values instead of hardcoded `0`.

---

## F. Notification Template Gap

### F.1 Current State

SD-08 added approved copy for 3 notification types × 3 channels = 9 rows. SD-2 added 6 new active notification_type codes. None of the 6 new types have template rows.

**Missing rows** (6 types × 3 channels = 18 rows):

| notification_type_code | Channels needed | Source |
|---|---|---|
| `job_assigned` | email, in_app, push | SD-2 |
| `schedule_changed` | email, in_app, push | SD-2 |
| `qb_sync_conflict` | email, in_app, push | SD-2 |
| `qb_conflict_pre_warning` | email, in_app, push | SD-2 |
| `gps_variance_alert` | email, in_app, push | SD-2 |
| `system_template_updated` | email, in_app, push | SD-2 |

### F.2 Placeholder Copy — SD-3 v1

These are v1 placeholder bodies. Tom may approve improved copy later (updating via seed re-run is idempotent via the UPDATE path in `mode_seed()`).

Add to `NOTIFICATION_TEMPLATE_COPY` dict in `seed_platform.py`:

```python
# job_assigned
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

# schedule_changed
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

# qb_sync_conflict
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

# qb_conflict_pre_warning
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

# gps_variance_alert
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

# system_template_updated
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
```

**Total notification_template rows after SD-3**: 9 (existing SD-08) + 18 (new SD-3) = **27 rows** (9 types × 3 channels).

---

## G. New Documentation Deliverables

### G.1 `pilot-docs-list.md` (root-level)

**Purpose**: Master registry of all active reference docs in the project. Helps Tom and agents quickly find the authoritative source for any topic.

**Format**: Markdown table per category with doc name, path, what it covers, and last updated date.

**Categories to cover**:
- Product & Strategy (PRD, roadmap, GTM, brand)
- Architecture & Design (mvp-arch, batch designs, architect methods)
- Implementation Tracking (launch plan, batch prompts, test lists)
- Database & Seed Data (db design, seed README, MCP guide)
- DevOps & Infrastructure (AWS docs, Terraform, Stripe config, runbooks)
- Testing & QA (scenario catalog, E2E guide, test README)
- Operations Reference (pilot-operations.md — new)

**When to update**: Whenever a new reference doc is created. The Python Engineer should update this doc as part of the SD-3 Completion Summary.

### G.2 `dev-docs/pilot-operations.md`

**Purpose**: Explains how the Pilot platform operates at runtime — how lookup tables, product plans, subscription tiers, and entitlements function as a connected system. Serves as onboarding reference for Tom, new engineers, and the AI agents.

**Sections to write**:

1. **Lookup Tables (Group A)** — How platform lookup tables work; why they use `(id, code, name)` triples; how application code references them by code string vs UUID FK; how `seed_core.py` is the recovery tool.

2. **Product Plan Hierarchy** — How `product_plan` → `product_plan_version` → `product_plan_product_feature_version` compose a versioned entitlement configuration. How `product_plan_version` is append-only (no updates, only new rows when price changes). How `product_plan_product_feature_version` defines per-plan feature limits with enforcement modes.

3. **Subscription Tier Model** — How `subscription_tier` is the customer-visible pricing layer (what the marketing site shows). How it maps to a `product_plan_code` that drives feature limits. How `annual_price_cents` vs `monthly_price_cents` work. How `stripe_price_id_monthly` and `stripe_price_id_annual` connect to Stripe.

4. **Tenant Subscription Lifecycle** — The full flow: Trial → Paywall → Plan Selection → Stripe Checkout → Webhook → `subscription` row created → tier updated. How `subscription.billing_interval` ('monthly' vs 'annual') is set. How `renews_at` is maintained. How `cancel_at_period_end` works.

5. **Founders Cohort Model** — How the founders tier works (is_active=true, $0 charge, same limits as Starter). How 6-month free period works (Stripe Subscription Schedule, STRIPE-B1). What happens at month 7.

6. **Entitlement Enforcement** — How the entitlement service reads the plan hierarchy at request time. How `tenant_product_feature_override` and `tenant_tier_override` tables let Tom give specific tenants custom deals. How `block` vs `soft` enforcement modes differ. How usage ledger tracks metered features.

7. **Notification Template System** — How `notification_type` → `notification_template` → `notification_outbox` flows. How platform-level templates (`tenant_id=NULL`) serve as defaults. How tenants can override (future).

8. **Subscription Status Machine** — How `subscription_status` rows map to Stripe's status enum. Which statuses enable app access (`is_billing_active=true`).

---

## H. Open Questions Resolved

| Question | Decision |
|---|---|
| Rename `teams` → `teams_plan`? | ✅ Yes — FK cascade migration in SD-3 |
| `product_plan_version.price_cents` for `founders_plan`? | ✅ Fix to 0. The $49/mo billing at month 7 is a Stripe subscription schedule event (STRIPE-B1), not a plan-price change. |
| `founders_plan.price_cents` for `starter_plan` and `teams`? | ✅ Leave at 4900/14900 — these are correct list prices. |
| Annual billing schema — Option A, B, or C? | ✅ Option A: rename `monthly_price_cents` → `annual_price_cents` + add NEW `monthly_price_cents` for month-to-month premium pricing. Rename `stripe_price_id` → `stripe_price_id_monthly` + add `stripe_price_id_annual`. |
| Annual billing pricing — how much? | ✅ Starter: annual $49/mo ($588/yr), month-to-month $59/mo. Teams: annual $149/mo ($1,788/yr), month-to-month $179/mo. |
| Founders 6-month auto-upgrade mechanism? | ✅ Stripe Subscription Schedule API (STRIPE-B1 scope). Manual activation acceptable for 3–5 beta founders. |
| Per-tenant feature/tier overrides? | ✅ `tenant_product_feature_override` and `tenant_tier_override` tables already exist (both empty). No seeding needed — these are operator-managed. Documented in `pilot-operations.md`. |
| Missing notification_template rows (18 rows for 6 SD-2 types)? | ✅ Add placeholder copy in SD-3 seed update. |
| Batch split SD-3 vs STRIPE-B1? | ✅ SD-3 = schema + seed only. STRIPE-B1 = service layer (routing, schedule API, webhook). SD-3 MUST deploy before STRIPE-B1. |
| New docs: `pilot-docs-list.md` + `pilot-operations.md`? | ✅ Both authored by Python Engineer as part of SD-3 deliverables. |

---

## I. What Is Deferred to STRIPE-B1

These items are explicitly OUT of SD-3 scope:

| Item | Why deferred |
|---|---|
| Annual billing routing in `stripe_subscriptions.py` — select `stripe_price_id_annual` vs `stripe_price_id_monthly` based on `billing_interval` | Requires service code change + thorough testing |
| Founders 6-month cohort Stripe Subscription Schedule API implementation | Separate service: `create_founders_subscription_schedule()` + `stripe_schedule_id` column on `subscription` + webhook handler for Phase 2 activation |
| `subscription_upgrade.py` route update — accept `billing_interval` in request body | API schema change + service routing |
| Tom creates annual Stripe prices in Dashboard | Tom action — cannot be scripted; price IDs documented in updated `stripe-pricing-config.md` |
| Marketing site billing toggle update (annual vs monthly toggle) | React Engineer scope |
| Update `stripe-pricing-config.md` with annual price spec sections | Partially done in SD-3 (document what to create); full IDs populated after Tom creates them in Stripe |

> **⚠️ STRIPE-B1 dependency**: After SD-3 deploys, any attempt to create a paid Stripe subscription will fail at runtime because `tier.stripe_price_id` no longer exists (renamed to `stripe_price_id_monthly`). This is acceptable pre-GA since no real tenants are on paid plans. STRIPE-B1 MUST be the next batch after SD-3 is verified.

---

## Reference: Live DB State at Design Time (2026-07-14)

| Table | Pre-SD3 State |
|---|---|
| `product_plan` | 3 rows: `founders_plan` (active), `starter_plan` (dormant), `teams` (dormant) |
| `product_plan_version` | 3 rows: `founders_plan price_cents=4900` ❌, `starter_plan price_cents=4900` ✅, `teams price_cents=14900` ✅ |
| `product_plan_product_feature_version` | 9 rows: 3 plans × 3 features — all correct values |
| `subscription_tier` | 4 rows: `monthly_price_cents` column holds annual display price; no `monthly_price_cents` for m2m; no annual Stripe price ID column |
| `subscription_status` | 6 rows — all correct, no changes needed |
| `notification_template` | 9 rows (3 types × 3 channels) — 18 rows missing for 6 SD-2 notification types |
