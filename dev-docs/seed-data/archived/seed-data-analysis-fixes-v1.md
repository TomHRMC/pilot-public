> **📦 ARCHIVED 2026-08-20 — CLOSED-LOOP FINDINGS, ALL ACTIONED.** This 2026-06-08 analysis (seed findings + action items: empty `subscription_status`, `trial` tier plan mapping, conftest creating its own rows) was fully actioned in the Phase 0.8/0.9 work — `backend/README-seed-data.md` confirms "Phase 0.9 ✅ Complete" and is now the single seed-system authority. Archived to `dev-docs/seed-data/archived/` per Tom's decision. **Frozen reference — do not update.**

---

# Seed Data Analysis — Findings & Action Items v1.0

**Session date**: 2026-06-08  
**Analyst**: Pilot Architect  
**Source reference**: `seed-scripts-usage-reference-analysis.md`  
**Scripts reviewed**: `seed_core.py`, `seed_platform.py`, `seed_test_tenant.py`  
**Live DB verified**: All findings confirmed against local PostgreSQL via MCP query

---

## Table of Contents

- [Seed Data Analysis — Findings \& Action Items v1.0](#seed-data-analysis--findings--action-items-v10)
  - [Table of Contents](#table-of-contents)
  - [1. Finding 1 — `subscription_status` Is Empty in Dev DB (Critical)](#1-finding-1--subscription_status-is-empty-in-dev-db-critical)
    - [What Was Observed](#what-was-observed)
    - [Root Cause](#root-cause)
    - [Impact](#impact)
    - [Action Item 1a — Add `subscription_status` rows to `seed_platform.py`](#action-item-1a--add-subscription_status-rows-to-seed_platformpy)
  - [2. Finding 2 — `subscription_tier.trial` Has No `product_plan_code`](#2-finding-2--subscription_tiertrial-has-no-product_plan_code)
    - [What Was Observed](#what-was-observed-1)
    - [Root Cause](#root-cause-1)
    - [Impact](#impact-1)
    - [Action Item 2 — Add `trial` to `TIER_TO_PLAN_MAP` in `seed_platform.py`](#action-item-2--add-trial-to-tier_to_plan_map-in-seed_platformpy)
  - [3. Finding 3 — `conftest.py` Creates Its Own `subscription_status` Rows](#3-finding-3--conftestpy-creates-its-own-subscription_status-rows)
    - [What Was Observed](#what-was-observed-2)
    - [Impact](#impact-2)
    - [Action Item 3 — Update `conftest.py` to Query Existing Rows](#action-item-3--update-conftestpy-to-query-existing-rows)
  - [4. Finding 4 — No Alembic Migration Owns `subscription_status` Rows](#4-finding-4--no-alembic-migration-owns-subscription_status-rows)
    - [What Was Observed](#what-was-observed-3)
    - [Impact](#impact-3)
    - [Action Item 4 — Add Alembic Migration for `subscription_status` Rows](#action-item-4--add-alembic-migration-for-subscription_status-rows)
  - [5. Verified Correct — `notification_category` (8 rows)](#5-verified-correct--notification_category-8-rows)
  - [6. Verified Correct — `notification_default_policy` (24 rows)](#6-verified-correct--notification_default_policy-24-rows)
  - [7. Show/Inspect Mode Audit — All 5 Scripts](#7-showinspect-mode-audit--all-5-scripts)
    - [7.1 `seed_core.py` — `mode_show()`: `notification_channel` Missing Entirely](#71-seed_corepy--mode_show-notification_channel-missing-entirely)
    - [7.2 `seed_core.py` — `mode_inspect()`: `notification_category` Missing `description`](#72-seed_corepy--mode_inspect-notification_category-missing-description)
    - [7.3 `seed_platform.py` — `mode_show()` and `mode_inspect()`: Will Be Incomplete After Action Item 1a](#73-seed_platformpy--mode_show-and-mode_inspect-will-be-incomplete-after-action-item-1a)
    - [7.4 `seed_scenario_dispatch.py` — `mode_inspect()`: `scheduled_end_at` Not Shown for Jobs](#74-seed_scenario_dispatchpy--mode_inspect-scheduled_end_at-not-shown-for-jobs)
    - [7.5 `reset_dev_db.py` — `mode_inspect()`: `loto_confirmation` and `calendar_sync_conflict` Never Shown](#75-reset_dev_dbpy--mode_inspect-loto_confirmation-and-calendar_sync_conflict-never-shown)
    - [7.6 Verified Complete (No Gaps)](#76-verified-complete-no-gaps)
  - [8. Action Item Summary](#8-action-item-summary)
    - [Correct Implementation Order](#correct-implementation-order)

---

## 1. Finding 1 — `subscription_status` Is Empty in Dev DB (Critical)

### What Was Observed

Live DB query on `subscription_status` returns **0 rows**. The table exists with the correct schema:

| Column | Type | Nullable |
|---|---|:---:|
| `id` | `uuid` | NO |
| `tenant_id` | `uuid` | YES |
| `code` | `varchar` | NO |
| `name` | `varchar` | NO |
| `is_billing_active` | `boolean` | NO |

### Root Cause

A previous agent removed `subscription_status` from `seed_core.py` after discovering that `conftest.py` creates its own `active` row with a fresh UUID at test-time, and the Stripe webhook test found *two* `active` rows (seeded UUID + fixture UUID), causing an assertion failure on UUID mismatch.

**The removal was the wrong fix.** The correct fix is to ensure `conftest.py` queries the persistently-seeded row instead of inserting its own.

### Impact

`seed_test_tenant.py` (around line 506) looks up `subscription_status WHERE code = 'active'` before creating the `subscription` row. When it finds 0 rows, it prints a warning and **skips the subscription entirely**. This means:

- The test tenant has no `subscription` row after `seed_test_tenant.py` runs
- `entitlement_service.py` will fail at runtime for the test tenant
- `tier_limit_enforcer.py` will fail to resolve entitlements for the test tenant
- Any endpoint that calls `GET /settings/subscription` will return nothing

### Action Item 1a — Add `subscription_status` rows to `seed_platform.py`

`subscription_status` is logically platform-level configuration (same class as `product_plan`) — not tenant-scoped, not test-specific. It belongs in **Group B** (`seed_platform.py`), not Group A.

Add the following 6 rows to `seed_platform.py:mode_seed()`. These map 1:1 to Stripe's `subscription.status` field values received by `stripe_subscriptions.py`:

```python
SUBSCRIPTION_STATUS_ROWS = [
    {"code": "trialing",  "name": "Trialing",  "is_billing_active": True},
    {"code": "active",    "name": "Active",     "is_billing_active": True},
    {"code": "past_due",  "name": "Past Due",   "is_billing_active": True},
    {"code": "unpaid",    "name": "Unpaid",     "is_billing_active": False},
    {"code": "canceled",  "name": "Canceled",   "is_billing_active": False},
    {"code": "paused",    "name": "Paused",     "is_billing_active": False},
]
```

Insert logic (idempotent):

```python
for ss in SUBSCRIPTION_STATUS_ROWS:
    existing = db.execute(
        text("SELECT 1 FROM public.subscription_status WHERE code = :code AND tenant_id IS NULL"),
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
```

**Billing access logic:**
- `is_billing_active = true` → tenant retains full app access (trialing, active, past_due)
- `is_billing_active = false` → access revoked (unpaid, canceled, paused)

---

## 2. Finding 2 — `subscription_tier.trial` Has No `product_plan_code`

### What Was Observed

Live DB query on `subscription_tier`:

| `tier_name` | `is_trial` | `product_plan_code` |
|---|:---:|---|
| `trial` | `true` | **`null`** ← missing |
| `starter` | `false` | `starter_plan` |
| `professional` | `false` | `professional_plan` |
| `enterprise` | `false` | `enterprise_plan` |

### Root Cause

`seed_platform.py` `TIER_TO_PLAN_MAP` contains only 3 entries — `starter`, `professional`, `enterprise`. The `trial` tier is absent:

```python
# Current — missing trial
TIER_TO_PLAN_MAP = {
    "starter": "starter_plan",
    "professional": "professional_plan",
    "enterprise": "enterprise_plan",
}
```

### Impact

- `seed_test_tenant.py` (around line 270) queries `subscription_tier WHERE is_trial = true` to get the `tier_id` for the new tenant's `current_subscription_tier_id`. The row exists and the tier is found correctly.
- However, any entitlement resolution that traverses `tenant → subscription_tier → product_plan` will find `product_plan_code = null` for trial tenants and fail to resolve feature limits.

### Action Item 2 — Add `trial` to `TIER_TO_PLAN_MAP` in `seed_platform.py`

Trial tenants should get `starter_plan` entitlements (the baseline tier). Update `seed_platform.py`:

```python
TIER_TO_PLAN_MAP = {
    "trial":        "starter_plan",        # ← add this line
    "starter":      "starter_plan",
    "professional": "professional_plan",
    "enterprise":   "enterprise_plan",
}
```

The existing UPDATE logic in `seed_platform.py` (around line 205) will automatically handle the new entry — no structural changes needed beyond adding the mapping key.

---

## 3. Finding 3 — `conftest.py` Creates Its Own `subscription_status` Rows

### What Was Observed

The test suite's `conftest.py` inserts fresh `subscription_status` rows with generated UUIDs at test-time. When `seed_core.py` previously seeded `subscription_status` with hardcoded UUIDs, the Stripe lifecycle test found two `active` rows and failed on UUID assertion.

### Impact

This is the root cause that triggered the incorrect removal of `subscription_status` from all seed scripts. Until `conftest.py` is updated, re-adding persistent seed rows will break `test_stripe_subscription_lifecycle` again.

### Action Item 3 — Update `conftest.py` to Query Existing Rows

Instead of inserting its own `subscription_status` rows, `conftest.py` should use the persistently-seeded ones. Change the fixture from:

```python
# BEFORE (creates its own rows — causes UUID mismatch)
status = SubscriptionStatus(code="active", name="Active", is_billing_active=True)
db.add(status)
db.commit()
```

To:

```python
# AFTER (queries the seeded row — UUIDs match)
status = db.execute(
    text("SELECT id FROM public.subscription_status WHERE code = 'active' AND tenant_id IS NULL")
).first()
assert status is not None, "subscription_status 'active' must exist — run seed_platform.py first"
```

**Important**: This fix must be implemented **before** Action Item 1a (re-adding seed rows), or the test will fail again with duplicate `active` rows.

---

## 4. Finding 4 — No Alembic Migration Owns `subscription_status` Rows

### What Was Observed

`subscription_status` has 0 rows in the live DB. There is no Alembic migration `upgrade()` function that inserts these rows. This means a fresh production deploy via `alembic upgrade head` will have an empty `subscription_status` table.

### Impact

Production deployment gap: any Stripe webhook received after first deploy will fail to find a valid `subscription_status` row when the `stripe_subscriptions.py` service attempts a status lookup. This is a **silent billing failure** — no crash, but subscriptions won't be correctly linked to their status.

### Action Item 4 — Add Alembic Migration for `subscription_status` Rows

Create a new Alembic migration (e.g., `add_subscription_status_seed_rows`) with an `upgrade()` that inserts the 6 rows using `ON CONFLICT DO NOTHING`. This migration becomes the **authoritative** production source for these rows.

The migration should use the same 6 rows defined in Action Item 1a. The `seed_platform.py` version serves as the dev/restore fallback; the migration is the production source.

---

## 5. Verified Correct — `notification_category` (8 rows)

Live DB and `NOTIFICATION_CATEGORY_ROWS` are in sync. No action required.

| `display_order` | `code` | `display_label` |
|:---:|---|---|
| 1 | `quote_approvals` | Quote Approvals |
| 2 | `field_issues` | Field Issues |
| 3 | `sync_conflicts` | Sync Conflicts |
| 4 | `job_activity` | Job Activity |
| 5 | `customer_activity` | Customer Activity |
| 6 | `billing` | Billing |
| 7 | `background_sync_alerts` | Background Sync Alerts |
| 8 | `system_announcements` | System Announcements |

**Minor drift noted**: `sync_conflicts` description in the seed script omits the `"requiring attention"` suffix present in the live DB. This came from the migration, not the seed script — cosmetic only, no functional impact.

---

## 6. Verified Correct — `notification_default_policy` (24 rows)

Live DB matches `NOTIFICATION_DEFAULT_POLICY_ROWS` exactly. 8 categories × 3 channels (`email`, `in_app`, `push`) = 24 rows. `sms` channel is intentionally absent (opt-in only). No action required.

| Category | `email` | `in_app` | `push` |
|---|:---:|:---:|:---:|
| `quote_approvals` | ✅ | ✅ | ✅ |
| `field_issues` | ✅ | ✅ | ✅ |
| `sync_conflicts` | ✅ | ✅ | ❌ |
| `job_activity` | ❌ | ✅ | ✅ |
| `customer_activity` | ❌ | ✅ | ✅ |
| `billing` | ✅ | ✅ | ❌ |
| `background_sync_alerts` | ❌ | ✅ | ✅ |
| `system_announcements` | ✅ | ✅ | ❌ |

`in_app` is always ON. `email`/`push` are muted for high-volume/accountant-type events to prevent alert fatigue. Rows are `tenant_id IS NULL` (platform defaults); per-tenant overrides are merged at runtime by `notification_resolver.py`.

---

## 7. Show/Inspect Mode Audit — All 5 Scripts

Full audit of `--mode show` and `--mode inspect` across all seed scripts. Each gap is a table or field that exists in the seed data definition but is absent from the output modes.

---

### 7.1 `seed_core.py` — `mode_show()`: `notification_channel` Missing Entirely

**Gap**: `NOTIFICATION_CHANNEL_DEF` is a standalone module-level variable — it is NOT inside `SIMPLE_CODE_TABLES` or `TENANT_NULLABLE_CODE_TABLES`. `mode_show()` only iterates `{**SIMPLE_CODE_TABLES, **TENANT_NULLABLE_CODE_TABLES}`, then manually prints individual special tables (entity_type, platform_role, etc.). `notification_channel` is in neither path — it is completely absent from `--mode show` output.

**Impact**: A developer running `--mode show` to preview what will be seeded sees no mention of `notification_channel` (4 rows: `email`, `sms`, `push`, `in_app`). The rows DO get seeded by `mode_seed()` correctly — this is a documentation/visibility gap only.

**Fix**: Add to `mode_show()` after the `SIMPLE_CODE_TABLES` loop:
```python
print(f"  [notification_channel] — {len(NOTIFICATION_CHANNEL_DEF['rows'])} rows: "
      f"{', '.join(r['code'] for r in NOTIFICATION_CHANNEL_DEF['rows'])}")
```

---

### 7.2 `seed_core.py` — `mode_inspect()`: `notification_category` Missing `description`

**Gap**: The `mode_inspect()` query for `notification_category` selects only `code, display_label, display_order`. The `description` column (e.g., `"Notifications when quotes are submitted, approved, or rejected."`) is omitted from the output.

**Impact**: Minor cosmetic gap. Descriptions are the most human-readable field for this table and are useful for verifying the right rows were seeded. No functional impact.

**Fix**: Update the inspect query to include `description`:
```python
rows = db.execute(
    text("SELECT code, display_label, description, display_order FROM public.notification_category ORDER BY display_order")
).fetchall()
# and in the print loop:
print(f"    • [{r.display_order}] {r.code}  '{r.display_label}'  — {r.description[:60]}...")
```

---

### 7.3 `seed_platform.py` — `mode_show()` and `mode_inspect()`: Will Be Incomplete After Action Item 1a

**Gap**: Once Action Item 1a (adding 6 `subscription_status` rows to `seed_platform.py`) is implemented, both `mode_show()` and `mode_inspect()` will need corresponding updates — otherwise those 6 rows will be silently seeded but never surfaced in output modes.

**`mode_show()` fix** — add after notification templates block:
```python
print("\nSubscription Statuses (6):")
for ss in SUBSCRIPTION_STATUS_ROWS:
    billing = "billing_active" if ss["is_billing_active"] else "access_revoked"
    print(f"  {ss['code']}  '{ss['name']}'  [{billing}]")
```

**`mode_inspect()` fix** — add a new section after notification templates:
```python
statuses = db.execute(
    text("SELECT code, name, is_billing_active FROM public.subscription_status WHERE tenant_id IS NULL ORDER BY code")
).fetchall()
print(f"\n  [subscription_status]  {len(statuses)} row(s)")
for s in statuses:
    print(f"    • {s.code:<12}  '{s.name}'  billing_active={s.is_billing_active}")
```

---

### 7.4 `seed_scenario_dispatch.py` — `mode_inspect()`: `scheduled_end_at` Not Shown for Jobs

**Gap**: The `mode_inspect()` job query selects `j.id, js.code as status_code, j.scheduled_start_at` but omits `j.scheduled_end_at`. For dispatch board testing, both start and end times are needed to verify the job window is correct (e.g., "tomorrow 9am–1pm" vs "today 8am–5pm").

**Impact**: Developer can see when a job starts but not when it ends. Minor — doesn't block testing but reduces inspect utility.

**Fix**: Add `j.scheduled_end_at` to the SELECT and print loop:
```python
# query:
SELECT j.id, js.code as status_code, j.scheduled_start_at, j.scheduled_end_at
# print:
end = str(j.scheduled_end_at) if j.scheduled_end_at else "open"
print(f"    • {j.id}  status={j.status_code}  {sched} → {end}")
```

---

### 7.5 `reset_dev_db.py` — `mode_inspect()`: `loto_confirmation` and `calendar_sync_conflict` Never Shown

**Gap**: `GROUP_D_TABLES` includes `loto_confirmation` and `calendar_sync_conflict` — both are wiped by `--wipe-only`. However, `mode_inspect()` covers:
- Detailed output: `customer`, `site`, `job`, `job_tech_assignment`, `tech_availability`, `quote`, `quote_line`, `pricebook_item`
- Count-only output: `invoice`, `invoice_line`, `change_order`, `change_order_line`, `job_time_entry`, `job_expense`, `job_notes`, `job_attachment`, `quote_version`, `entity_address`, `entity_contact`, `contact`

Neither `loto_confirmation` nor `calendar_sync_conflict` appears in either list. A developer who runs `--mode inspect` after accidentally writing test data to these tables will not see it, but `--wipe-only` will delete it silently.

**Impact**: Data visibility gap. If a test or manual operation populates `loto_confirmation` (LOTO safety records) or `calendar_sync_conflict` rows, `--mode inspect` will show 0 rows for those tables, misleading the developer into thinking the DB is clean.

**Fix**: Add both tables to the count-only section:
```python
for table in [
    "loto_confirmation",
    "calendar_sync_conflict",
    "invoice",
    # ... rest of existing list
]:
```

---

### 7.6 Verified Complete (No Gaps)

| Script | `mode_show()` | `mode_inspect()` |
|---|:---:|:---:|
| `seed_core.py` | ⚠️ See 7.1 | ⚠️ See 7.2 |
| `seed_platform.py` | ⚠️ See 7.3 (future) | ⚠️ See 7.3 (future) |
| `seed_test_tenant.py` | ✅ Complete | ✅ Complete |
| `seed_scenario_quote_to_cash.py` | ✅ Complete | ✅ Complete |
| `seed_scenario_dispatch.py` | ✅ Complete | ⚠️ See 7.4 |
| `reset_dev_db.py` | N/A (interactive menu) | ⚠️ See 7.5 |

---

## 8. Action Item Summary

| # | Priority | File(s) | Change | Blocks |
|---|:---:|---|---|---|
| **1a** | 🔴 Critical | `seed_platform.py` | Add 6 `subscription_status` rows to `mode_seed()` | Test tenant subscription creation |
| **2** | 🔴 Critical | `seed_platform.py` | Add `"trial": "starter_plan"` to `TIER_TO_PLAN_MAP` | Trial tenant entitlement resolution |
| **3** | 🔴 Critical | `backend/tests/conftest.py` | Change `subscription_status` fixture to query seeded rows instead of inserting | Must precede Action Item 1a to avoid test failures |
| **4** | 🟡 Important | New Alembic migration | Insert 6 `subscription_status` rows with `ON CONFLICT DO NOTHING` | Production deploy correctness |
| **5** | 🟢 Polish | `seed_core.py` | Add `notification_channel` to `mode_show()` output | Dev visibility |
| **6** | 🟢 Polish | `seed_core.py` | Add `description` to `notification_category` inspect query | Dev visibility |
| **7** | 🟢 Polish | `seed_platform.py` | Add `subscription_status` to `mode_show()` + `mode_inspect()` after Action Item 1a | Dev visibility |
| **8** | 🟢 Polish | `seed_scenario_dispatch.py` | Add `scheduled_end_at` to job inspect output | Dev visibility |
| **9** | 🟡 Important | `reset_dev_db.py` | Add `loto_confirmation` + `calendar_sync_conflict` to inspect count-only loop | Prevents silent data presence after wipe |

### Correct Implementation Order

```
1. Action Item 3 first  →  update conftest.py to query seeded rows
2. Action Item 1a       →  add subscription_status to seed_platform.py
3. Action Item 2        →  add trial tier mapping to seed_platform.py
4. Action Items 5–9     →  show/inspect polish (can be done in any order)
5. Run: python migrations/scripts/seed_platform.py
6. Run: python migrations/scripts/seed_test_tenant.py
7. Run: pytest — verify zero new failures
8. Action Item 4        →  add Alembic migration (production hardening)
```
