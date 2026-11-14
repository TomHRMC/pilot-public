# SD-4 Decisions Tracker (Working Doc)

**Session**: 2026-07-14
**Purpose**: Track all Group C audit decisions before writing the batch-sd4-design.md

---

## Decisions Log

### D1 — README-seed-data.md: `quote_status` row count fix
- **Issue**: README §4 Group A lists only 9 `quote_status` codes by name — missing `accepted`. Live DB has 10 rows (confirmed). This is a documentation gap only, not a seed issue.
- **Action**: Update README §4 `quote_status` row to say 10 rows and list all 10 codes including `accepted`.
- **File**: `backend/README-seed-data.md`
- **Status**: 🔄 Pending

### D2 — `subscription_tier.stripe_price_id_annual`: populate from live Stripe prices
- **Issue**: All tiers have `stripe_price_id_annual = NULL` in the live DB. Tom has now created annual Stripe prices in both test and production environments.
- **Action**: Update `subscription_tier` rows for `starter` and `teams` in `seed_platform.py` to insert `stripe_price_id_annual`. `founders` and `trial` tiers stay NULL (no annual billing).
- **Stripe price IDs** (from `stripe-pricing-config.md` §4):

| tier_name | stripe_price_id_monthly (test) | stripe_price_id_annual (test) | stripe_price_id_monthly (live) | stripe_price_id_annual (live) |
|---|---|---|---|---|
| starter | `price_REDACTED03` | `price_REDACTED07` | `price_REDACTED01` | `price_REDACTED05` |
| teams | `price_REDACTED04` | `price_REDACTED08` | `price_REDACTED02` | `price_REDACTED06` |

- `seed_platform.py` must use the **test-mode** IDs (dev/QA DBs). Production DB gets live-mode IDs via the future prod seed script (env-flag design).
- **Status**: 🔄 Pending

### D3 — `user_endpoint`: add in_app + push endpoints for all 3 test users
- **Issue**: Only `email` endpoints exist for all 3 users. In-app and push notification UI won't have endpoints to configure/display.
- **SMS**: NOT adding yet — Telnyx 10DLC not yet authorized for outbound. Will be added when ready.
- **Action**: Add `in_app` and `push` endpoints for all 3 users (owner, tech, office_staff) in `seed_test_tenant.py`. Push endpoint = a fake but realistic Expo push token (format: `ExponentPushToken[xxx]`). In_app endpoint = user's email value (used as the in-app channel identifier).
- **Status**: 🔄 Pending

### D4 — `tenant.stripe_customer_id`: populate with a test-mode Stripe customer ID
- **Issue**: `stripe_customer_id` is NULL on the test tenant. For testing Stripe subscription flows (upgrade, founders schedule, webhook delivery), we need a real test-mode Stripe customer ID linked to the test tenant.
- **How production works**: On first paid plan upgrade, `POST /tenant/subscription/convert-from-trial` calls `create_stripe_customer()` in `stripe_subscriptions.py` which calls `stripe.Customer.create()` and immediately stores the returned `cus_xxx` on `tenant.stripe_customer_id`. The seed tenant skips the signup wizard, so the ID must be pre-set.
- **Test-mode Stripe customer**: Created 2026-07-14 in Stripe Dashboard (Test mode → Customers → + New → Name: "Pilot Dev Tenant", Email: `dev@pilot.local`)
- **Value**: `cus_REDACTEDX01`
- **Action**: Update `seed_test_tenant.py` to set `tenant.stripe_customer_id = 'cus_REDACTEDX01'` on the upsert.
- **Status**: ✅ Resolved — value provided by Tom 2026-07-14

### D5 — `user.display_color`: set for owner + office_staff users
- **Issue**: `display_color` is NULL for owner (`dev@pilot.local`) and office_staff (`office@pilot.local`). Dispatch board shows blank/grey for users without colors.
- **Action**: Update `seed_test_tenant.py` to set:
  - Owner (`...0002`): `#10B981` (green)
  - Office Staff (`...0004`): `#F59E0B` (amber)
  - Tech already has `#3B82F6` (blue) ✅
- **Status**: 🔄 Pending

### D6 — Add `accountant` role user (`accountant@pilot.local`)
- **Issue**: `tenant_user_role` has 4 roles: owner, technician, office_staff, `accountant`. No test user covers accountant role → QB sync screens and financial reports can't be RBAC-tested.
- **Action**: Add 4th test user to `seed_test_tenant.py`:
  - UUID: `00000000-0000-0000-0000-000000000005` (next in sequence — never reuse)
  - Email: `accountant@pilot.local`
  - First/Last: `Dev` / `Accountant`
  - Role: `accountant`
  - display_color: `#8B5CF6` (purple — distinct from existing 3)
  - `user_endpoint`: email (verified, opted_in), in_app, push (same as D3 above)
- **Status**: 🔄 Pending

### D7 — `password_policy`: fill lockout + history fields
- **Issue**: Only `min_length`, `min_uppercase`, `min_digits` are set. `lockout_threshold`, `lockout_window_minutes`, `lockout_duration_minutes`, `history_depth` are all NULL — Security settings UI shows blank for these fields.
- **Action**: Seed these values in `seed_test_tenant.py`:
  - `lockout_threshold = 5` (lock account after 5 failed attempts)
  - `lockout_window_minutes = 15` (within a 15-minute window)
  - `lockout_duration_minutes = 30` (lock for 30 minutes)
  - `history_depth = 5` (can't reuse last 5 passwords)
- **Status**: 🔄 Pending

### D8 — `tenant_email_branding`: add custom_footer; logo deferred to S3 upload
- **Issue**: `custom_footer=NULL`, `logo_s3_path=NULL` — email branding UI can't be tested for these fields.
- **How these get set**: Both can be updated via the Settings UI (PATCH `/tenant/email-branding`). The seed sets initial DB values. Logo specifically requires: UI file upload → `POST /tenant/email-branding/logo/upload-url` (signed S3 URL) → direct S3 upload → PATCH with S3 key. The seed cannot pre-populate a real S3 object.
- **Action**:
  - Seed `custom_footer = "© 2026 Pilot Dev Tenant. All rights reserved."` in `seed_test_tenant.py`
  - Logo (`logo_s3_path`) stays NULL in seed — Tom uploads test logo via the Settings UI after seeding (dev S3 bucket). Tom to upload a test image and note the S3 key for reference.
- **Status**: 🔄 Pending (footer); ⚠️ Tom action needed (logo — upload via UI)

### D9 — `tenant_onboarding_checklist`: keep test tenant as dismissed; second tenant for onboarding flow testing
- **Decision**: Test tenant (`...0001`) stays with all checklist steps `true` + `checklist_dismissed_permanently=true`. This suppresses onboarding banners so dashboard testing starts clean.
- **Onboarding flow testing**: Use a second tenant (new signup flow) — this tenant starts with all fields `false` (normal initial state). The second tenant is out of scope for SD-4 (separate "multi-tenant seed" task in launch plan).
- **No change to `tenant_onboarding_checklist` seed**. ✅

### D10 — `subscription`: update quantity_seats + add billing_anchor
- **Action**:
  - `quantity_seats = 4` (update from 1 to match 4 test users after D6)
  - `billing_anchor = '2026-07-01'` — gives the "next billing date" a visible value in the subscription settings UI. July 1 anchors the monthly cycle for the test tenant.
- **Status**: 🔄 Pending

### D11 — Founders Cohort → Starter transition (DEFERRED — design task, not SD-4)
- **Context**: `create_founders_subscription_schedule()` in `stripe_subscriptions.py` exists (STRIPE-B1) but isn't wired at signup because `stripe_customer_id` isn't available yet. Once D4 (Stripe customer ID) is resolved, the schedule needs to be created: Phase 1 = $0 for 6 months, Phase 2 = Starter monthly pricing at month 7.
- **This is a separate design task** — the subscription payment UI batch (which builds the Stripe.js card Elements form) is the correct place to wire `create_founders_subscription_schedule()`. Add to launch plan as a P1 design item.
- **No SD-4 seed change required.** Add as design task in `pilot-launch-plan.md`. ⚠️ Deferred.

### D12 — `labor_rate_version`: add non-zero burden_pct for testing burden calculations
- **Issue**: All 3 skill levels have `burden_pct=0.0`. The billing engine always applies burden via `hourly_rate_cents * (1 + burden_pct)` — it is **NOT opt-in**. With `burden_pct=0.0`, the burdened rate equals the base rate and the `burdened_rate_cents` field on the Labor Rates UI card always shows the same value as the base rate, which is misleading.
- **Confirmed**: `jobs.py` lines 307–309 and `voice_action_router.py` lines 1240–1242 both compute `int(rate_row.hourly_rate_cents * (1 + rate_row.burden_pct))`. The `burden_pct` is stored as a decimal fraction: `0.25` = 25% (NOT the integer `25`).
- **Action**: Update `seed_test_tenant.py` to seed non-zero `burden_pct` values:
  - `master`: `burden_pct = 0.25` → burdened rate = $120 * 1.25 = **$150.00/hr**
  - `journeyman`: `burden_pct = 0.20` → burdened rate = $85 * 1.20 = **$102.00/hr**
  - `apprentice`: `burden_pct = 0.15` → burdened rate = $55 * 1.15 = **$63.25/hr**
- **Note**: Since `labor_rate_version` rows already exist in DB with `burden_pct=0.0`, the Python Engineer must DELETE + re-INSERT (or UPDATE) these rows during SD-4. The GiST exclusion constraint means we cannot insert a new overlapping row — instead UPDATE the existing open-ended rows.
- **Status**: ✅ Resolved — non-zero values required, values confirmed above.

### D13 — `discount_version`: seed script exists but 0 rows in DB — must fix
- **Issue**: `discount_version` query returns 0 rows for test tenant. The seed script defines `SUMMER_PROMO` and `NEW_CUSTOMER` but they aren't in the DB (wiped and not re-seeded).
- **Action**: Ensure `seed_test_tenant.py` reliably seeds both rows on every run. The existing `INSERT` logic with `ON CONFLICT DO NOTHING` check (by `tenant_id + code`) is correct — the fix is simply ensuring the script is run. However, the `mode_inspect()` function doesn't currently show `discount_version` rows — add it so they're visible in inspect output.
- **Data**:
  - `SUMMER_PROMO`: `pct_off=10`, closed range `[2024-06-01, 2024-08-31)` — a past expired discount for historical testing
  - `NEW_CUSTOMER`: `amount_off_cents=2500` ($25 off), open-ended range `[2026-01-01, NULL)` — an active discount for quote testing
- **Status**: 🔄 Pending

---

## Tables Remaining to Audit (Group C)

- [x] `tenant` (D1–D4 decisions above)
- [x] `user` / `tenant_user` / `user_endpoint` (D3/D5/D6)
- [x] `password_policy` (D7)
- [x] `tenant_email_branding` (D8)
- [x] `tenant_onboarding_checklist` (D9 — no change)
- [x] `subscription` (D10)
- [x] `labor_rate_version` (D12)
- [x] `tenant_markup_version` — ✅ no issues, no change
- [x] `discount_version` (D13)

---

## Open Questions (Blockers for SD-4 Implementation)

1. **D4**: Tom needs to provide the test-mode Stripe customer ID (`cus_xxx`) for the test tenant. Create a Stripe test customer in the Stripe Dashboard (Customers → + New) and provide the ID. Python Engineer sets it in `seed_test_tenant.py` on the `tenant.stripe_customer_id` column.

2. **D8**: Logo — Tom uploads a test logo image via the Settings UI (Branding section) after SD-4 is seeded. No seed script action needed, but Tom should do this before the email branding UI smoke test.

3. **D11**: Founders schedule wiring — design task for subscription payment UI batch. Tom to approve adding to launch plan P1 queue.

4. **D12**: Python Engineer to verify `billing_rate_service.py` applies `burden_pct` in cost calculations before setting non-zero values. If burden is applied automatically, set non-zero values. If it's opt-in (0 = disabled), leave at 0 and note for documentation.

---

*This tracker will be superseded by `batch-sd4-design.md` at end of session.*
