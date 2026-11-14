# Batch SD-4 Design — Group C Test Tenant Seed Audit & Expansion

**Version**: 1.0  
**Date**: 2026-07-14  
**Author**: Pilot Architect  
**Status**: READY FOR IMPLEMENTATION  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1 — Full UI Seed Data Expansion  
**Decisions tracker**: `dev-docs/seed-data/sd4-decisions-tracker.md`

---

## Table of Contents

- [A. Input Read Summary](#a-input-read-summary)
- [B. Migration Plan](#b-migration-plan)
- [C. Execution Order](#c-execution-order)
- [D. seed\_platform.py Changes (Group B — D2)](#d-seed_platformpy-changes-group-b--d2)
- [E. seed\_test\_tenant.py Changes (Group C — D3–D13)](#e-seed_test_tenantpy-changes-group-c--d3d13)
- [F. Pattern Reuse Decisions](#f-pattern-reuse-decisions)
- [G. Open Questions Resolved](#g-open-questions-resolved)
- [H. Deferred Items](#h-deferred-items)

---

## A. Input Read Summary

All inputs read and verified via MCP before this design was written (2026-07-14):

| Input | Key Finding |
|---|---|
| `backend/migrations/scripts/seed_test_tenant.py` | Full source read. Confirmed all insert patterns, column names, and `mode_inspect()` coverage. `discount_version` inspect coverage missing. `password_policy` only sets 3 of 9 columns. `user_endpoint` email-only. `user.display_color` NULL for owner + office. |
| `backend/migrations/scripts/seed_platform.py` | Not read inline — SD-3 confirmed its structure. Change is narrowly scoped: add `stripe_price_id_annual` values to `subscription_tier` upsert block. |
| `backend/README-seed-data.md` | Group C §4 table reviewed. `quote_status` row listed only 9 of 10 codes — `accepted` was missing. **Fixed inline 2026-07-14.** |
| `dev-docs/integrations/stripe/stripe-pricing-config.md` | §4 contains all 8 confirmed Stripe price IDs (4 test-mode, 4 live). Annual price IDs created by Tom 2026-07-14. |
| Live DB — `subscription_tier` | `stripe_price_id_annual = NULL` on all tiers. Monthly IDs already set for starter/teams. `founders` and `trial` have no Stripe price at all (correct — free tier). |
| Live DB — `tenant` (`...0001`) | `stripe_customer_id = NULL`. Test-mode Stripe customer created 2026-07-14: `cus_REDACTEDX01`. |
| Live DB — `user` × 3 | owner/office_staff `display_color = NULL`. No `accountant` user exists. |
| Live DB — `user_endpoint` × 3 | Email only. No `in_app` or `push` endpoints exist for any user. |
| Live DB — `password_policy` | `min_length=8, min_uppercase=1, min_digits=1`. Lockout/history fields all NULL. |
| Live DB — `tenant_email_branding` | `custom_footer = NULL`. `logo_s3_path = NULL`. `brand_color_hex=#2563EB`. |
| Live DB — `subscription` | `quantity_seats=1`, `billing_anchor=NULL`. Correct plan/status. |
| Live DB — `labor_rate_version` | All 3 rates have `burden_pct=0.0`. Confirmed `burden_pct` is always applied via `hourly_rate_cents * (1 + burden_pct)` in `jobs.py` and `voice_action_router.py` — not opt-in. |
| Live DB — `discount_version` | **0 rows** for test tenant. Script defines the rows but they weren't re-seeded after a reset. |
| `services/voice_action_router.py` | Confirmed `burden_pct` is stored as a decimal fraction (`0.25` = 25%, NOT integer `25`). |

---

## B. Migration Plan

**No Alembic migrations required.** All changes are to Python seed scripts only:
- `backend/migrations/scripts/seed_platform.py` — add `stripe_price_id_annual` values to `subscription_tier` upsert
- `backend/migrations/scripts/seed_test_tenant.py` — 11 enhancements to Group C data

**No schema changes** — all columns being populated already exist in the live DB (verified via MCP).

### B.1 Pre-Implementation DB State (MCP-verified 2026-07-14)

```sql
-- subscription_tier annual price IDs (all NULL today)
SELECT tier_name, stripe_price_id_monthly, stripe_price_id_annual FROM subscription_tier ORDER BY display_order;
-- founders:  monthly=NULL        annual=NULL
-- trial:     monthly=NULL        annual=NULL
-- starter:   monthly=price_REDACTED...  annual=NULL   ← needs annual added
-- teams:     monthly=price_REDACTED...  annual=NULL   ← needs annual added

-- tenant stripe_customer_id
SELECT id, stripe_customer_id FROM tenant WHERE id = '00000000-0000-0000-0000-000000000001';
-- stripe_customer_id = NULL  ← needs cus_REDACTEDX01

-- user display_color
SELECT id, email, display_color FROM "user" WHERE id IN (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000004'
);
-- both NULL  ← needs #10B981 (owner) and #F59E0B (office_staff)

-- user_endpoint channels for test tenant users
SELECT user_id, channel FROM user_endpoint 
WHERE user_id IN ('00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000004');
-- only 'email' rows  ← needs in_app + push per user

-- discount_version
SELECT code, pct_off, amount_off_cents FROM discount_version 
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- 0 rows  ← must seed SUMMER_PROMO + NEW_CUSTOMER

-- labor_rate_version burden_pct
SELECT skill_level_code, hourly_rate_cents, burden_pct FROM labor_rate_version 
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- all burden_pct=0.0  ← UPDATE to 0.25/0.20/0.15

-- password_policy lockout fields
SELECT lockout_threshold, lockout_window_minutes, lockout_duration_minutes, history_depth 
FROM password_policy WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- all NULL  ← needs 5/15/30/5

-- subscription quantity_seats + billing_anchor
SELECT quantity_seats, billing_anchor FROM subscription 
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- quantity_seats=1, billing_anchor=NULL

-- tenant_email_branding
SELECT custom_footer FROM tenant_email_branding 
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
-- NULL
```

---

## C. Execution Order

No FK dependencies between these changes. All are safe to implement independently, but group them logically:

| Step | File | Change | Notes |
|---|---|---|---|
| 1 | `seed_platform.py` | Add `stripe_price_id_annual` to `subscription_tier` upsert | D2 — test-mode values only |
| 2 | `seed_test_tenant.py` | Add 4th user `accountant@pilot.local` (UUID `...0005`) | D6 — must come before `tenant_user`, `user_endpoint` changes |
| 3 | `seed_test_tenant.py` | Set `display_color` for owner + office_staff + accountant | D5 |
| 4 | `seed_test_tenant.py` | Set `tenant.stripe_customer_id = 'cus_REDACTEDX01'` | D4 |
| 5 | `seed_test_tenant.py` | Add `in_app` + `push` endpoints for all 4 users | D3 |
| 6 | `seed_test_tenant.py` | Fill `password_policy` lockout/history fields | D7 |
| 7 | `seed_test_tenant.py` | Set `tenant_email_branding.custom_footer` | D8 |
| 8 | `seed_test_tenant.py` | Update `subscription.quantity_seats=4`, `billing_anchor='2026-07-01'` | D10 |
| 9 | `seed_test_tenant.py` | UPDATE `labor_rate_version` burden_pct to 0.25/0.20/0.15 | D12 |
| 10 | `seed_test_tenant.py` | Add `discount_version` rows (SUMMER_PROMO + NEW_CUSTOMER) | D13 — fix missing rows |
| 11 | `seed_test_tenant.py` | Add `discount_version` rows to `mode_inspect()` output | D13 — inspect coverage |
| 12 | `backend/README-seed-data.md` | Update Group C §4 table to reflect all new rows | Documentation |

---

## D. seed_platform.py Changes (Group B — D2)

### D.1 subscription_tier — add stripe_price_id_annual

In the `subscription_tier` upsert block, add `stripe_price_id_annual` values for `starter` and `teams`. `founders` and `trial` stay NULL (free tiers, no annual Stripe price exists or is needed).

**Test-mode price IDs** (for dev + QA + e2e DBs):

| tier_name | stripe_price_id_annual (test) |
|---|---|
| `starter` | `price_REDACTED07` |
| `teams` | `price_REDACTED08` |

**Live-mode price IDs** (for production DB — not part of SD-4 seed scripts; handled in future prod seed script):

| tier_name | stripe_price_id_annual (live) |
|---|---|
| `starter` | `price_REDACTED05` |
| `teams` | `price_REDACTED06` |

**Implementation pattern** (constants at top of `seed_platform.py`):

```python
# ── Stripe annual price IDs ────────────────────────────────────────────────
# Test-mode (used by this script — targets dev/QA/e2e DBs):
STRIPE_PRICE_ID_ANNUAL_STARTER_TEST = "price_REDACTED07"  # $588/yr
STRIPE_PRICE_ID_ANNUAL_TEAMS_TEST   = "price_REDACTED08"  # $1,788/yr

# Live-mode (production DB — NOT used by this script today).
# When seed scripts are refactored to accept --env dev|production flags,
# pass these values when --env production is given:
# STRIPE_PRICE_ID_ANNUAL_STARTER_LIVE = "price_REDACTED05"  # $588/yr
# STRIPE_PRICE_ID_ANNUAL_TEAMS_LIVE   = "price_REDACTED06"  # $1,788/yr
```

In the `subscription_tier` upsert, use the test-mode constants and include `stripe_price_id_annual` in the `ON CONFLICT DO UPDATE` SET clause:

```sql
INSERT INTO public.subscription_tier
(..., stripe_price_id_annual, ...)
VALUES (..., :stripe_price_id_annual, ...)
ON CONFLICT (tier_name) DO UPDATE
    SET stripe_price_id_annual = EXCLUDED.stripe_price_id_annual,
        ...
```

> ⚠️ The `ON CONFLICT DO UPDATE` in the existing `subscription_tier` block must also be updated to include `stripe_price_id_annual = EXCLUDED.stripe_price_id_annual` so future re-runs don't silently skip the annual ID column.

> **Future env-flag design**: All seed scripts will eventually accept `--env dev|production` (or read `ENVIRONMENT`) and branch on env-specific data. This is mandatory before first production deployment — the production DB must receive live-mode Stripe price IDs. SD-4 seeds test-mode IDs only. Production values are co-located as comments in `seed_platform.py` so they're ready when the env-flag refactor runs (see launch plan §2 P1 — DB Management Strategy batch).

---

## E. seed_test_tenant.py Changes (Group C — D3–D13)

### E.1 Add `accountant@pilot.local` user (D6)

New 4th user — UUID `00000000-0000-0000-0000-000000000005` (next in the reserved sequence).

```python
ACCOUNTANT_USER_ID = UUID("00000000-0000-0000-0000-000000000005")
ACCOUNTANT_EMAIL = "accountant@pilot.local"
ACCOUNTANT_FIRST_NAME = "Dev"
ACCOUNTANT_LAST_NAME = "Accountant"
ACCOUNTANT_DISPLAY_COLOR = "#8B5CF6"  # purple
```

Add to the `users` list and the `role_map`:
```python
(str(ACCOUNTANT_USER_ID), "accountant")
```

Update `mode_show()` to mention the 4th user. Update `README-seed-data.md` to show 4 users.

**Reserved UUID registry update**: `00000000-0000-0000-0000-000000000005` is now occupied. Document in `README-seed-data.md` §5.

### E.2 Set display_color for owner + office_staff (D5)

Update the `users` list to include colors for all users:

```python
OWNER_DISPLAY_COLOR = "#10B981"   # green
OFFICE_DISPLAY_COLOR = "#F59E0B"  # amber
# TECH already: TECH_DISPLAY_COLOR = "#3B82F6"  (blue)
# ACCOUNTANT:   ACCOUNTANT_DISPLAY_COLOR = "#8B5CF6"  (purple)
```

The existing upsert `ON CONFLICT (id) DO UPDATE SET ... display_color = EXCLUDED.display_color` will handle this correctly for existing rows.

### E.3 Set tenant.stripe_customer_id (D4)

In the `tenant` upsert, add `stripe_customer_id` to the `ON CONFLICT DO UPDATE` block:

```python
STRIPE_CUSTOMER_ID_TEST = "cus_REDACTEDX01"  # Test-mode customer created 2026-07-14
```

In the INSERT/UPDATE:
```sql
INSERT INTO public.tenant
(id, name, is_active, current_subscription_tier_id, created_by, stripe_customer_id, created_at, updated_at)
VALUES (:id, :name, true, :tier_id, :created_by, :stripe_customer_id, NOW(), NOW())
ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name,
        stripe_customer_id = EXCLUDED.stripe_customer_id,
        updated_at = NOW()
```

### E.4 Add in_app + push user_endpoint rows (D3)

After the existing email endpoint upsert, add `in_app` and `push` channel endpoints for all users. SMS stays absent (Telnyx 10DLC not yet authorized).

**in_app endpoint**: Uses the user's email as the identifier (in-app channel identifier is the email address).  
**push endpoint**: Uses a deterministic fake Expo push token per user.

```python
# Deterministic fake Expo push tokens (test only — no real device)
PUSH_TOKENS = {
    str(owner_id):           "ExponentPushToken[test-owner-00000002]",
    str(TECH_USER_ID):       "ExponentPushToken[test-tech-00000003]",
    str(OFFICE_USER_ID):     "ExponentPushToken[test-office-00000004]",
    str(ACCOUNTANT_USER_ID): "ExponentPushToken[test-acct-00000005]",
}
```

Insert pattern for each user × each new channel (`in_app`, `push`):
```sql
INSERT INTO public.user_endpoint
(id, user_id, channel, value, is_primary, verification_status,
 consent_status, is_active, created_at, updated_at)
VALUES (gen_random_uuid(), :uid, :channel, :value, false, 'verified',
        'opted_in', true, NOW(), NOW())
ON CONFLICT DO NOTHING
```

> `is_primary = false` — email is the primary endpoint; in_app and push are secondary.

### E.5 Fill password_policy lockout/history fields (D7)

Update the existing `password_policy` INSERT to include all lockout + history fields:

```python
# Full password policy configuration
db.execute(text("""
    INSERT INTO public.password_policy
    (id, tenant_id, min_length, min_uppercase, min_digits,
     lockout_threshold, lockout_window_minutes, lockout_duration_minutes,
     history_depth, rotation_days, require_mfa, created_at, updated_at)
    VALUES (gen_random_uuid(), :tid, :min_length, :min_uppercase, :min_digits,
            5, 15, 30, 5, NULL, false, NOW(), NOW())
    ON CONFLICT DO NOTHING
"""), {...})
```

For existing rows (already inserted without lockout fields), add an UPDATE patch after the INSERT:
```sql
UPDATE public.password_policy
SET lockout_threshold = 5,
    lockout_window_minutes = 15,
    lockout_duration_minutes = 30,
    history_depth = 5,
    updated_at = NOW()
WHERE tenant_id = :tid
  AND lockout_threshold IS NULL
```

### E.6 Set tenant_email_branding.custom_footer (D8)

Update the `tenant_email_branding` INSERT to include `custom_footer`:

```python
CUSTOM_FOOTER = "© 2026 Pilot Dev Tenant. All rights reserved."
```

```sql
INSERT INTO public.tenant_email_branding
(tenant_id, brand_color_hex, email_signature, custom_footer, created_at)
VALUES (:tid, '#2563EB', 'Pilot Dev Tenant — dev only', :footer, NOW())
ON CONFLICT DO NOTHING
```

For existing rows, patch `custom_footer` if NULL:
```sql
UPDATE public.tenant_email_branding
SET custom_footer = :footer
WHERE tenant_id = :tid AND custom_footer IS NULL
```

**Note on logo**: `logo_s3_path` stays NULL in the seed. Tom uploads a test logo via the Settings UI (Branding section → Upload Logo) after seeding. The S3 key will be set automatically by the upload flow — no seed script action needed.

### E.7 Update subscription: quantity_seats + billing_anchor (D10)

The `subscription` INSERT uses `ON CONFLICT DO NOTHING` — an existing row will not be updated. The seed must also handle the UPDATE path for existing subscriptions:

```sql
-- Insert (first run):
INSERT INTO public.subscription
(id, tenant_id, product_plan_code, status_id, quantity_seats,
 billing_anchor, started_at, billing_interval, cancel_at_period_end, is_active,
 created_at, updated_at)
VALUES (gen_random_uuid(), :tid, :plan_code, :status_id, 4,
        '2026-07-01', NOW(), 'monthly', false, true,
        NOW(), NOW())
ON CONFLICT DO NOTHING

-- Patch existing rows:
UPDATE public.subscription
SET quantity_seats = 4,
    billing_anchor = '2026-07-01',
    updated_at = NOW()
WHERE tenant_id = :tid
  AND (quantity_seats <> 4 OR billing_anchor IS NULL)
```

### E.8 Update labor_rate_version burden_pct (D12)

`labor_rate_version` rows already exist with `burden_pct=0.0`. Cannot INSERT new open-ended overlapping rows (GiST exclusion constraint). Must UPDATE the existing rows:

```sql
UPDATE public.labor_rate_version
SET burden_pct = :new_pct
WHERE tenant_id = :tid AND skill_level_code = :code
```

**Values** (decimal fraction, not integer percentage):

| skill_level_code | burden_pct | burdened_rate |
|---|---|---|
| `master` | `0.25` | $120 × 1.25 = **$150.00/hr** |
| `journeyman` | `0.20` | $85 × 1.20 = **$102.00/hr** |
| `apprentice` | `0.15` | $55 × 1.15 = **$63.25/hr** |

> **Important**: Store as `0.25` (decimal fraction), NOT `25` (percentage). The formula is `hourly_rate_cents * (1 + burden_pct)` — using `25` would produce a 2600% burdened rate.

The seed must UPDATE (not INSERT) because:
1. A new row with the same `tenant_id + skill_level_code` and overlapping `valid_period` violates the GiST exclusion constraint.
2. `mode_seed()` should be idempotent — rerunning must not error.

Pattern:
```python
for lr in [("master", Decimal("0.25")), ("journeyman", Decimal("0.20")), ("apprentice", Decimal("0.15"))]:
    db.execute(text("""
        UPDATE public.labor_rate_version
        SET burden_pct = :pct
        WHERE tenant_id = :tid AND skill_level_code = :code
    """), {"tid": tid, "pct": lr[1], "code": lr[0]})
    print(f"  ✅ [labor_rate_version] Updated '{lr[0]}' burden_pct → {lr[1]}")
```

### E.9 Seed discount_version rows + add to mode_inspect() (D13)

The rows are already defined in `seed_test_tenant.py` but return 0 from the DB — they were wiped in a reset. The existing INSERT logic is correct; the rows just need to be present. No code change needed to the INSERT — just verify the script runs them.

However, `mode_inspect()` does **not** currently show `discount_version` rows. Add an inspect block:

```python
# Add to mode_inspect() after tenant_markup_version block:
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
        print(f"    '{d.code}'  {d.pct_off}% off  [{d.valid_from} → {d.valid_until}]")
    else:
        print(f"    '{d.code}'  ${d.amount_off_cents / 100:.2f} off  [{d.valid_from} → {d.valid_until}]")
```

---

## F. Pattern Reuse Decisions

| Pattern (from mvp-arch.md §16) | Applied |
|---|---|
| Idempotent `INSERT ... ON CONFLICT DO NOTHING` | All new endpoint inserts |
| UPDATE patch after INSERT for existing rows | `password_policy`, `tenant_email_branding`, `subscription`, `labor_rate_version` |
| Deterministic UUID constants for new user | `ACCOUNTANT_USER_ID = UUID("00000000-0000-0000-0000-000000000005")` |
| `mode_show()` / `mode_inspect()` parity | All new data visible in inspect output |
| GiST-safe: UPDATE not INSERT for temporal range tables | `labor_rate_version` burden_pct update |

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does `burden_pct=0` disable burden, or is it always applied? | Always applied: `int(rate_row.hourly_rate_cents * (1 + rate_row.burden_pct))`. `burden_pct=0.0` is a no-op, not a disable flag. Non-zero values required for meaningful UI display. |
| `stripe_price_id_annual` values — where to get them? | `stripe-pricing-config.md` §4. All 8 IDs confirmed by Tom 2026-07-14. Test-mode IDs used in seed scripts; live-mode IDs deferred to future prod seed script. |
| Test-mode Stripe customer ID for test tenant? | `cus_REDACTEDX01` — created by Tom 2026-07-14 in Stripe Dashboard (Test mode), Name: "Pilot Dev Tenant", Email: `dev@pilot.local`. |
| `user_endpoint.is_primary` for in_app/push? | `false` — email is the primary endpoint. Secondary channel endpoints do not need `is_primary=true`. |
| `in_app` endpoint value — what is the identifier? | User's email address (the in-app channel resolves delivery by email/user_id). |
| How does logo get set if not seeded? | Tom uploads via Settings → Branding → Upload Logo after seeding. The S3 key is stored automatically via the upload flow. No seed script action needed. |
| `discount_version` — INSERT or UPDATE needed? | The existing INSERT logic is correct; the table just needs to be re-run. The fix is ensuring `mode_inspect()` covers it so gaps are visible, and that the data is seeded on next run. |
| Founders cohort Stripe schedule wiring — included in SD-4? | No — deferred. The `create_founders_subscription_schedule()` function in `stripe_subscriptions.py` is already implemented (STRIPE-B1) but not called at signup. Wiring it is part of the subscription payment UI batch (requires `STRIPE_PUBLISHABLE_KEY` + card Elements form). |

---

## H. Deferred Items

| Item | Reason | Owner |
|---|---|---|
| `tenant.logo_s3_path` seed | Cannot seed without a real S3 object. Tom uploads test logo via Settings UI after seeding. | Tom |
| Production DB `stripe_price_id_annual` values | Live-mode price IDs must go through the future prod seed script with `--env production` flag (DB Management Strategy batch). | Future batch |
| SMS `user_endpoint` rows | Telnyx 10DLC not yet authorized for outbound SMS. Add after Campaign B is approved and numbers provisioned. | Post-10DLC |
| Founders schedule wiring (`create_founders_subscription_schedule()`) | Requires subscription payment UI batch (Stripe.js card Elements form + `STRIPE_PUBLISHABLE_KEY`). | Subscription payment UI batch |
| Second tenant (onboarding flow testing) | "Multi-tenant seed" task — separate design. The test tenant (`...0001`) stays dismissed; onboarding flow tested via a fresh signup. | Future SD batch |

---

## I. README-seed-data.md Updates Required

After SD-4 implementation, update `backend/README-seed-data.md`:

**§4 Group C table**:
- `user`: 4 rows (add accountant@pilot.local, UUID `...0005`)
- `user_endpoint`: 12 rows (4 users × 3 channels: email, in_app, push) — note SMS deferred
- `tenant_user`: 4 rows
- `password_policy`: add lockout/history field values
- `tenant_email_branding`: note custom_footer set
- `subscription`: `quantity_seats=4`, `billing_anchor=2026-07-01`
- `labor_rate_version`: note burden_pct values (master 0.25 / journeyman 0.20 / apprentice 0.15)
- `discount_version`: 2 rows (SUMMER_PROMO 10% + NEW_CUSTOMER $25 off)

**§5 Deterministic UUIDs**: Add accountant user `00000000-0000-0000-0000-000000000005`.

**§4 Group B** (seed_platform.py): Update `subscription_tier` row to note `stripe_price_id_annual` now set for starter + teams.
