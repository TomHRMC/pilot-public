# SD-6 Decisions Tracker (Working Doc)

**Session**: 2026-07-15
**Purpose**: Track all post-SD-5 seed audit decisions and discuss relevance of remaining README sections before writing batch-sd6-design.md

---

## 0. Standing Design Decisions (Tom — 2026-07-15)

These apply to ALL future SD batches and supersede any conflicting prior decisions:

### DB Cleanup Philosophy
> The seed scripts must only manage data that they have inserted. They must NOT delete or modify data outside their own scope.

**Rule**: If the DB has spurious rows from prior testing (e.g., the 581 empty `tenant_phone_number` rows), **do not add cleanup logic to `reset_dev_db.py` or any seed script**. Instead, provide standalone SQL to run once manually. If a completely clean DB is needed, instantiate from the schema-only SQL file, then run seed scripts in order (A → B → C → D).

### DB Cleanup SQL — Run Once Manually

```sql
-- Remove 580 spurious tenant_phone_number rows with empty phone_number
-- These are from failed provisioning API calls in May 2026 testing
-- Preserves the seeded row: phone_number = '+15125559001'
-- Run against pilot_dev BEFORE running SD-6 seed scripts
DELETE FROM tenant_phone_number
WHERE phone_number = '';
```

> **Expected result**: `DELETE 580` — leaving exactly 1 row (`+15125559001`, status=provisioning_failed), which is the FK anchor for the customer_comms scenario.

### Scope Updates for SD-6

Tom confirmed (2026-07-15):
- **D7 is IN SD-6** — `user_preference` / `user_setting_override` must be tested; add to this batch (was previously P3 deferred)
- **D2 revised** — No `reset_dev_db.py` change; use the standalone SQL above instead
- **SD-5 close date**: 2026-07-15 ✅ (confirmed for README §10 entry)

---

## 1. Live DB State Verification (MCP-verified 2026-07-15)

All queries run against `pilot_dev` via `postgres-local` MCP.

### Group A — Lookup Tables ✅ All Confirmed

| Table | README Says | Live | Status |
|---|---|---|---|
| `address_type` | 4 | 4 | ✅ |
| `contact_type` | 4 | 4 | ✅ |
| `job_status` | 5 | 5 | ✅ |
| `quote_status` | 10 | 10 | ✅ |
| `invoice_status` | 6 | 6 | ✅ |
| `payment_status` | 5 | 5 | ✅ |
| `notification_template` | 27 | 27 | ✅ |
| `notification_type` | 9 | 9 | ✅ |
| `notification_category` | 8 | 8 | ✅ |
| `notification_default_policy` | 24 | 24 | ✅ |
| `email_template` | 16 | 16 | ✅ |
| `communication_template` | 15 | 17 | ⚠️ 2 extra rows — from migration additions, harmless |
| `platform_setting_catalog` | 42 | 48 | ⚠️ 6 extra catalog keys — added in later batches, not a gap |
| `platform_setting` | 42 | 49 | ⚠️ 7 extra default rows — matches catalog expansion, harmless |
| `sync_conflict_classification_matrix` | 17 | 17 | ✅ |
| `quote_template` | 3 | 3 | ✅ |

> **Verdict on Group A**: Fully populated. Minor count discrepancies on `communication_template` and `platform_setting_catalog` are from post-SD-01 batch migrations, not a seed gap. README row counts need to be updated to reflect the live totals.

---

### Group B — Platform Config ✅ All Confirmed

| Table | README Says | Live | Status |
|---|---|---|---|
| `product_plan` | 3 | 3 | ✅ |
| `product_plan_version` | 3 | 3 | ✅ |
| `product_plan_product_feature_version` | 9 | 9 | ✅ |
| `product_feature` | 3 | 3 | ✅ |
| `subscription_tier` | 4 | 4 | ✅ |
| `subscription_status` | 6 | 6 | ✅ |

**`subscription_tier` detail** (MCP-verified):

| tier_name | annual_price_cents | monthly_price_cents | is_active | stripe_price_id_monthly | stripe_price_id_annual |
|---|---|---|---|---|---|
| `trial` | 0 | 0 | false | null | null |
| `founders` | 0 | 0 | true | null | null |
| `starter` | 58,800 | 5,900 | false | `price_REDACTED03` | `price_REDACTED07` |
| `teams` | 178,800 | 17,900 | false | `price_REDACTED04` | `price_REDACTED08` |

> **Verdict on Group B**: Fully populated. Stripe price IDs confirmed in live DB (SD-4 patch applied). Founders tier correctly has `is_active=true` only.

---

### Group C — Test Tenant ✅ All Confirmed (SD-4 Fully Landed)

| Table | README Says | Live | Status |
|---|---|---|---|
| `tenant` | 1, stripe_customer_id set | 1, `cus_REDACTEDX01` | ✅ |
| `user` | 5 (4 tenant + sentinel) | 5 | ✅ |
| `tenant_user` | 4 | 4 | ✅ |
| `user_endpoint` | 12 (4×3 channels) | 12 | ✅ |
| `subscription` | qty_seats=4, billing_anchor=2026-07-01 | qty_seats=4, billing_anchor=2026-07-01, status=active, founders_plan | ✅ |
| `labor_rate_version` | 3, non-zero burden_pct | 3 (master=0.25, journeyman=0.20, apprentice=0.15) | ✅ |
| `discount_version` | 2 | 2 (SUMMER_PROMO + NEW_CUSTOMER) | ✅ |
| `password_policy` | lockout fields set | lockout_threshold=5, window=15, duration=30, history=5 | ✅ |
| `tenant_email_branding` | custom_footer set, logo deferred | custom_footer ✅, **logo_s3_path = "tenant-branding/.../logo.jpg"** | ✅ (Tom uploaded!) |

**User display colors** (MCP-verified):

| Email | UUID | Role | display_color |
|---|---|---|---|
| `dev@pilot.local` | `...0002` | owner | `#10B981` ✅ |
| `tech@pilot.local` | `...0003` | technician | `#3B82F6` ✅ |
| `office@pilot.local` | `...0004` | office_staff | `#F59E0B` ✅ |
| `accountant@pilot.local` | `...0005` | accountant | `#8B5CF6` ✅ |

**`user_endpoint` channels**: All 4 users have `email` (primary, verified, opted_in) + `in_app` + `push` — 12 total ✅

> **Verdict on Group C**: Fully seeded. SD-4 landed correctly. **Bonus discovery**: `tenant_email_branding.logo_s3_path` is already set to a real S3 key — Tom uploaded the logo, which closes the SD-4 D8 action item completely.

---

### Group D — Scenario Data ✅ SD-5 Fully Landed

| Table | SD-5 Target | Live | Status |
|---|---|---|---|
| `customer` | 8 qtc + 3 comms = 11+ | 12 | ✅ (1 extra from dispatch fallback — harmless) |
| `site` | 7 | 7 | ✅ |
| `quote` | 10 (all statuses) | 11 | ✅ (2 draft — one is QTC-001 draft enriched, one is old) |
| `quote_line` | 30+ | 30 | ✅ |
| `job` | 26 | 26 | ✅ (18 completed, 3 in_progress, 3 scheduled, 1 draft, 1 cancelled) |
| `job_tech_assignment` | 12+ | 22 | ✅ |
| `job_time_entry` | 11 → 18+ | 18 | ✅ |
| `job_expense` | 9 → 14+ | 14 | ✅ |
| `invoice` | 8 (all statuses) | 8 | ✅ |
| `payment` | 5 | 5 | ✅ |
| `pricebook_item` | 6 | 6 | ✅ |
| `supplier` | 3 | 3 | ✅ (Wesco, Graybar, Platt) |
| `supplier_item` | 14 | 14 | ✅ |
| `supplier_item_price` | 14 | 14 | ✅ |
| `tech_availability` | 2 → 3 | 3 | ✅ |
| `nec_calculation_log` | 3 | 3 | ✅ (voltage_drop ×2 + conduit_fill) |
| `mobile_sync_session` | 2 | 2 | ✅ |
| `mobile_sync_event` | 4 | 4 | ✅ |
| `customer_communication_thread` | 3 | 3 | ✅ |
| `customer_communication_message` | 9 | 9 | ✅ |

**Invoice status breakdown** (MCP-verified):

| invoice_number | status | total_cents | balance_due | job linked | quote linked | invoice_line count |
|---|---|---|---|---|---|---|
| `INV-900001` | paid | $1,026.00 | $0 | ✅ | ✅ | **0** ⚠️ |
| `INV-SEED-A` | paid | $1,325.16 | $0 | ✅ | null | **0** ⚠️ |
| `INV-SEED-B` | paid | $270.00 | $0 | ✅ | null | **0** ⚠️ |
| `INV-SEED-C` | issued | $883.63 | $883.63 | ✅ | null | **0** ⚠️ |
| `INV-SEED-D` | draft | $235.63 | $235.63 | ✅ | null | **0** ⚠️ |
| `INV-SEED-E` | partial | $450.36 | $250.36 | ✅ | null | **0** ⚠️ |
| `INV-SEED-F` | void | $738.72 | $738.72 | ✅ | null | **0** ⚠️ |
| `INV-SEED-G` | writeoff | $2,181.60 | $2,181.60 | ✅ | null | **0** ⚠️ |

> **CRITICAL GAP: `invoice_line` = 0 rows across ALL 8 invoices.** The Invoice Detail page will show a totals header but no line items — broken for UI testing.

> **Verdict on Group D**: SD-5 landed. All status code coverage targets met. One critical gap identified: `invoice_line` is completely empty.

---

## 2. Additional Notable DB Findings (Not in README)

### Finding F1 — `tenant_phone_number`: 581 Spurious Rows ⚠️
- **Live state**: 581 rows, all `status=provisioning_failed`, all `phone_number=''` (empty string), all created between 2026-05-02 and unknown date
- **Expected state**: 1 row: `+15125559001`, `status=provisioning_failed` (from `seed_scenario_customer_comms.py`)
- **Root cause**: Prior API testing in May 2026 hammered the `/tenant/phone-number/provision` endpoint, each failed attempt creating a DB row
- **Impact**: The Customer Comms scenario FK anchor row (the one with +15125559001) exists and is valid. The 580 extra empty rows are noise — harmless to the FK relationship but visually messy if inspected
- **Decision needed**: Should we add a cleanup step to `reset_dev_db.py` that deletes all `tenant_phone_number` rows where `phone_number = ''`?

### Finding F2 — `invoice_line`: 0 Rows (Critical UI Gap) 🔴
- **Live state**: 0 rows in `invoice_line`
- **Expected state**: Each invoice should have 2-5 line items reflecting the job's labor + materials + expenses
- **Root cause**: All 8 invoices were seeded with totals calculated manually (hardcoded `total_cents`) but `invoice_line` rows were never added to the seed scripts
- **Impact**: Invoice Detail UI shows totals but blank line item table — non-functional for UI smoke testing. This is the highest-priority gap remaining.
- **Complexity**: High — `invoice_line` rows require `unit_price_cents × quantity = extended_price_cents` and must sum to `subtotal_cents`. Tax component rows in `invoice_line_tax_component` are also needed for the tax row to render.
- **Decision needed**: Seed `invoice_line` + `invoice_line_tax_component` rows for all 8 invoices in SD-6.

### Finding F3 — `mobile_sync_owner_escalation`: 0 Rows
- **Live state**: 0 rows
- **Coverage catalog**: W-12 (Owner escalation created + resolved) has ☐ no coverage
- **Seedable**: Yes — no external API required
- **Tables involved**: `mobile_sync_owner_escalation` (linked to `mobile_sync_event`)
- **Decision needed**: Seed 1 open + 1 resolved owner escalation row for W-12 coverage.

### Finding F4 — `loto_confirmation`: 0 Rows
- **Live state**: 0 rows
- **Coverage catalog**: Not listed as a named workflow (embedded in job workflow)
- **Seedable**: Yes — linked to a `job` row
- **Decision needed**: Seed 1-2 LOTO confirmation rows (one confirmed, one pending) on a completed job.

### Finding F5 — `change_order` / `change_order_line`: 0 Rows
- **Live state**: 0 rows in both tables
- **Coverage catalog**: Not a named workflow but is part of the job detail surface
- **Seedable**: Yes — requires a job, customer, and line items
- **Decision needed**: Seed 1 change order with 2-3 lines on one of the completed jobs.

### Finding F6 — `in_app_notification`: 0 Rows
- **Live state**: 0 rows
- **Coverage catalog**: W-16 (Notification delivered across channels) has `cp7_notifications` for API-level testing but no seeded in-app notifications
- **Seedable**: Yes — can seed notification_event → notification_outbox → in_app_notification chain
- **Decision needed**: Seed a small set of in_app_notification rows for the notification center UI.

### Finding F7 — `user_preference` / `user_setting_override`: 0 Rows
- **Live state**: 0 rows in both
- **Impact**: User settings and preferences UI pages show all defaults — no user-customized state to test
- **Seedable**: Yes — simple key-value rows per user
- **Decision needed**: Seed 2-3 user_preference rows for the owner user (timezone, date_format, notifications).

### Finding F8 — `tenant_phone_number` Seed Script Row Present (Verified)
- Confirmed: The seed script's `+15125559001` row IS present in the 581 rows. The FK anchor for customer comms threads is valid.

### Finding F9 — `help_chat_session` / `help_chat_message`: Prior Testing Rows Present
- 1 help_chat_session + 2 help_chat_message rows from prior manual testing (not seeded)
- These are harmless — do not delete (could interfere with tests expecting empty state if we DELETE)

### Finding F10 — `integration_credential` / `integration_sync_mapping`: 9/1 Rows from Prior Testing
- These are from prior QB integration testing. Not seeded. Harmless.

### Finding F11 — `feedback_submission`: 1,813 Rows
- From prior testing/demo activity. Not a seed concern. Not seeded.

---

## 3. README Section Relevance Review (Post-Group D)

### §5 — Deterministic UUIDs (Permanent — Never Reuse)
- **Status**: ✅ Still fully relevant — unchanged reference
- **Action**: No changes needed. Current reserved range: `...0001` through `...0005` + `...0000` (sentinel). If we add a 5th tenant user in a future batch, `...0006` is the next available slot.

### §6 — Run Order & Quick Commands
- **Status**: ✅ Accurate
- **Minor update needed**: The "Expected after Step 5" note says `[customer] 5 row(s)` — live DB has 12. Should update the inspect output examples to match current seeded totals.
- **Action**: Update expected-output block in §6.

### §7 — Known Constraints & Gotchas
- **Status**: ✅ All still accurate
- **GiST constraint**: Still applies — labor_rate_version open-ended range `[2026-06-01,)` confirmed live
- **`user_endpoint` trigger guards**: Still applies — `trg_user_endpoint_guard_bd` / `trg_user_endpoint_guard_biu` confirmed live
- **"Empty tenant" tests**: Still applies — `test_tenant` now has more data than ever (22 jobs, 12 customers), so `second_tenant` fixture is mandatory for empty-state tests
- **Potential new gotcha to add**: `tenant_phone_number` noise — the 581 spurious empty-phone rows mean any test that does `COUNT(*)` on `tenant_phone_number` for the test tenant will get 581, not 1. Tests should query by `phone_number != ''` or use the specific ID.

### §8 — What Is NOT Seeded
- **`payment_method`**: Still deferred — requires real Stripe `psp_payment_method_id`. Still accurate.
- **`help_article` / `help_article_chunk`**: Still deferred — requires embedding pipeline. Still accurate.
- **`app_service` / `app_service_provider`**: Still not seeded — FK issue with `integration_sync_mapping` still applies. Still accurate.
- **New addition needed**: `psp_customer` / `psp_transaction_log` — cannot be seeded without real Stripe transaction IDs
- **New addition needed**: `voice_command_log` / `voice_command_entity_link` — requires live Voice AI session; blocked by Whisper/Ollama
- **New addition needed**: `integration_credential` / `integration_sync_log` — requires QB OAuth flow; blocked by external API

### §9 — Scenario Status Registry
- **Status**: ✅ All 7 scenarios show Complete
- **Action**: No changes — SD-5 didn't add new scenario scripts, it expanded existing ones

### §10 — Roadmap — Data Tasks
- **Status**: All prior tasks (SD-01 through SD-10, E2E-B1, SD-4) are marked ✅ Complete
- **Action**: Add SD-5 ✅ Complete entry (missing from README). Add SD-6 as the new active batch.

### §11 — Reference Documents
- **Status**: Mostly accurate
- **`seed-scripts-usage-reference-analysis.md`**: May be out of date (last updated before SD-4/5). Worth noting but not blocking.
- **`scenario-coverage-catalog.md`**: Updated through 2026-07-12. Needs update to reflect SD-5 changes and this session's W-12 discussion.
- **Action**: After SD-6 is implemented, update the scenario coverage catalog to close W-12 if owner escalation is seeded.

---

## 4. SD-6 Scope Decisions

### D1 — `invoice_line` + `invoice_line_tax_component`: Seed Real Line Items for All 8 Invoices (P0 — Critical)
- **Problem**: 0 `invoice_line` rows. Invoice Detail page shows blank line item table for all 8 invoices.
- **Tom confirmed (2026-07-15)**:
  - Must reference real `pricebook_item_version` FK records (not standalone text-only lines)
  - Line item math must be exact: `unit_price_cents × quantity` must sum to the invoice `subtotal_cents`
  - Both `invoice_line` and `invoice_line_tax_component` must be seeded with correct, balanced data
- **Decision**:
  - Seed `invoice_line` rows for all 8 invoices in `seed_scenario_quote_to_cash.py` (INV-900001) and `seed_scenario_reporting.py` (INV-SEED-A through G)
  - Each invoice gets 2-4 lines: labor lines reference the matching `pricebook_item_version` ID; material lines reference material pricebook items; misc items use the Permit Fee pricebook item
  - The Python Engineer must recalculate and SET `subtotal_cents`, `tax_cents`, `total_cents`, `balance_due_cents` FROM the line item data — existing hardcoded totals in the reporting script must be replaced with values derived from real line math
  - `invoice_line_tax_component`: 1 row per taxable line using `tax_rate_version` `code='US-DEFAULT'` (6%). Tax component amounts must sum to `invoice.tax_cents`.
- **MCP verification required before implementation**:
  - `invoice_line` full column schema
  - `invoice_line_tax_component` full column schema
  - Live `pricebook_item_version` IDs and `unit_price_cents` values (FK source for line items)
  - Live `tax_rate_version` ID for `US-DEFAULT`
  - Live `qco_line_type` IDs for labor/material/misc
- **Status**: 🔄 Pending (SD-6 must-have — highest priority task)

### D2 — `tenant_phone_number`: One-Time Cleanup SQL (P1 — Run Manually)
- **Problem**: 581 spurious `provisioning_failed` rows with `phone_number=''` from May 2026 API testing. Test hazard for any COUNT(*) on this table.
- **Tom confirmed (2026-07-15)**: Do NOT add cleanup to `reset_dev_db.py` or any seed script. Seed scripts only manage their own inserted data. Use the standalone SQL in §0 of this tracker to clean up manually before SD-6 seed run.
- **Decision**: The cleanup SQL is documented in §0 above. No code change to any seed script for this item.
- **Status**: ✅ Resolved — SQL provided in §0; Tom runs it once manually before SD-6 seed scripts

### D3 — `mobile_sync_owner_escalation`: Seed W-12 Coverage (P1)
- **Problem**: 0 rows. W-12 (Owner escalation created + resolved) has no seed coverage.
- **Decision**: Add 2 rows to `seed_scenario_mobile_sync.py`:
  - Row 1: **Open escalation** — linked to Session 2 / Event 3 (the conflict event). `resolved_at=NULL`, `resolution_action=NULL`. Represents an active owner escalation awaiting review.
  - Row 2: **Resolved escalation** — a past escalation from an older mobile event (fabricate the mobile_sync_event link with a past timestamp). `resolved_at = ANCHOR_DATE - 5 days`, `resolution_action='owner_accepted_device_change'`
- **Status**: 🔄 Pending (SD-6 must-have — closes W-12 gap)

### D4 — `loto_confirmation`: Seed Safety Workflow (P2)
- **Problem**: 0 rows. LOTO confirmation is an electrical safety workflow with its own UI surface. Not testable.
- **Decision**: Seed 2 LOTO confirmation rows in `seed_scenario_dispatch.py` (since LOTO confirmations are job-scoped):
  - Row 1: Status = `confirmed`, linked to a completed job — represents a field tech confirming lockout before work
  - Row 2: Status = `pending`, linked to an in-progress job — represents a lockout requirement that hasn't been confirmed yet
- **Needs**: Column schema verification via MCP before writing. `loto_confirmation` table schema unknown — must query `information_schema.columns` first.
- **Status**: 🔄 Pending (SD-6 should-have)

### D5 — `change_order` + `change_order_line`: Seed Change Order Workflow (P2)
- **Problem**: 0 rows. Change order UI surface can't be tested. Change orders are a first-class job feature.
- **Tom confirmed (2026-07-15)**: Seed at minimum one `pending` change order AND one `approved` change order (one of each status, minimum).
- **Decision**: Seed 2 change orders with lines in `seed_scenario_quote_to_cash.py`:
  - **CO-001**: Status = `pending`, attached to the Q-CONV-001 converted job — represents a CO submitted by tech and awaiting owner approval. Lines: 1 material addition ($450), 1 labor addition (2 hours @ master rate)
  - **CO-002**: Status = `approved`, attached to the same job — represents an already-approved CO. Lines: 1 note line + 1 material addition ($225)
- **Needs**: Column schema verification via MCP before writing. `change_order` and `change_order_line` schemas unknown — must query `information_schema.columns` first.
- **Status**: 🔄 Pending (SD-6 should-have)

### D6 — `seed_scenario_notifications.py`: New Script for Notification Center (P2)
- **Problem**: 0 rows in `in_app_notification`. Notification center UI shows blank.
- **Tom confirmed (2026-07-15)**: Create a new `seed_scenario_notifications.py` file — do not append to an existing script. This gives us a dedicated place to expand SMS notification testing when Telnyx 10DLC goes live.
- **Decision**:
  - New file: `migrations/scripts/seed_scenario_notifications.py`
  - Register as `"notifications"` in `reset_dev_db.py`
  - Seed 4-5 `in_app_notification` rows for the owner user covering different notification types:
    - 1 unread: `job_assigned` — "Tech assigned to Panel Upgrade job"
    - 1 unread: `qb_sync_conflict` — "QuickBooks sync conflict requires review"
    - 1 read: `dunning_reminder` — "Invoice INV-SEED-C is 14 days overdue"
    - 1 read: `customer_communication_sent` — "SMS sent to Carlos Rivera"
    - 1 read (older): `gps_variance_alert` — "GPS variance detected for tech on job"
  - Script must support standard `--mode seed|inspect|show --reset` pattern
- **Needs**: Column schema verification via MCP — `in_app_notification` schema unknown.
- **Status**: 🔄 Pending (SD-6 should-have)

### D7 — `user_preference` / `user_setting_override`: Seed User Settings (NOW IN SD-6)
- **Problem**: 0 rows in both. User settings pages show defaults only — no customized state to test UI override flows.
- **Tom confirmed (2026-07-15)**: Include in SD-6 — this needs to be testable. Promoted from P3 to P2.
- **Decision**:
  - Verify the exact schema of both `user_preference` and `user_setting_override` via MCP — they may serve different purposes (preference = user choices, override = per-user platform setting override)
  - Seed `user_setting_override` rows for the owner user using valid `platform_setting_catalog` keys:
    - A timezone or date format key (if available in catalog)
    - A notification-related key (e.g., digest interval or email frequency)
    - A display preference key (if available)
  - If `user_preference` is a separate free-form table, seed 1-2 rows there too
  - Add to `seed_test_tenant.py` (Group C) — these are user-level config, not ephemeral scenario data
- **Needs**: MCP column schema query for `user_preference`, `user_setting_override`, and a list of `user_setting_override`-eligible keys from `platform_setting_catalog` (`tenant_editable = true` and `value_type` = appropriate type)
- **Status**: 🔄 Pending (SD-6 should-have — promoted from P3)

### D8 — README §10 Roadmap: Add SD-5 ✅ Entry + SD-6 Active Entry
- **Problem**: SD-5 completed 2026-07-15 but not recorded in README §10 Roadmap.
- **Decision**: Add SD-5 completion entry matching the SD-4 format. Add SD-6 as the next active batch.
- **Status**: 🔄 Pending (documentation update — part of SD-6 batch)

### D9 — README §4 Group A Count Discrepancies: Minor Doc Update
- **Problem**: `communication_template` says 15 rows (live: 17), `platform_setting_catalog` says 42 (live: 48), `platform_setting` says 42 (live: 49)
- **Decision**: Update README §4 Group A table counts to match live DB. These are not seed errors — they're post-SD-01 migration additions that expanded the catalog.
- **Status**: 🔄 Pending (documentation update — part of SD-6 batch)

### D10 — README §8 "What Is NOT Seeded": Add 3 New Entries
- **Problem**: §8 is missing 3 tables that are clearly not seeded and warrant documentation.
- **Decision**: Add to §8:
  - `psp_customer` / `psp_transaction_log` — requires real Stripe transaction/customer IDs from live webhook events; cannot be fabricated
  - `voice_command_log` / `voice_command_entity_link` / `voice_feedback` — requires live Voice AI session (Whisper + Ollama); blocked by GPU dependency
  - `integration_credential` / `integration_sync_log` / `connector_run_log` — requires QB OAuth flow; blocked by external API
- **Status**: 🔄 Pending (documentation update — part of SD-6 batch)

---

## 5. What Does NOT Change in SD-6

| Item | Reason |
|---|---|
| All 7 Group D scenario scripts (core structure) | SD-5 delivered full status code coverage — no new status codes missing |
| Group A, B, C seed scripts | All confirmed correct per MCP audit |
| `payment_method` | Still deferred — real Stripe psp_payment_method_id required |
| `help_article` / `help_article_chunk` | Still deferred — embedding pipeline required |
| `app_service` / `app_service_provider` | Still deferred — FK teardown issue |
| Tier 2 Playwright tests | React Engineer work — out of scope for seed data batch |
| E2E harness (`tests/e2e/`) | No new E2E critical paths needed for SD-6 scope |
| `voice_command_log` / `conversation_session` | Blocked by Whisper/Ollama — not seedable |
| `integration_credential` / `integration_sync_mapping` | Blocked by QB OAuth — not seedable |

---

## 6. Scenario Coverage Catalog Updates Needed (Post-SD-6)

After SD-6 is implemented, update `dev-docs/testing-support/scenario-coverage-catalog.md`:

| Workflow | Current | Target After SD-6 |
|---|---|---|
| W-12 — Owner escalation created + resolved | ☐ No coverage | ✅ Seed data exists (D3) |
| W-16 — Notification delivered across channels | 🔄 Partial (cp7 only) | ✅ Seed data exists (D6 adds in_app rows) |

---

## 7. SD-6 Batch Classification — Final Scope (Tom Approved 2026-07-15)

**SD-6 Must-Have (P0/P1)**:
- D1: `invoice_line` + `invoice_line_tax_component` — real pricebook FKs, balanced math (highest priority)
- D2: `tenant_phone_number` cleanup — standalone SQL (§0), no code change
- D3: `mobile_sync_owner_escalation` — 1 open + 1 resolved (closes W-12 gap)
- D8: README §10 Roadmap — SD-5 ✅ entry (closed 2026-07-15) + SD-6 active
- D9: README §4 count corrections (communication_template: 17, platform_setting_catalog: 48, platform_setting: 49)
- D10: README §8 — add 3 new "not seeded" table groups

**SD-6 Should-Have (P2 — all IN scope)**:
- D4: `loto_confirmation` — 2 rows on dispatch jobs (pending + confirmed)
- D5: `change_order` + `change_order_line` — 2 change orders (pending + approved), minimum 3 lines each
- D6: `seed_scenario_notifications.py` — new script, 4-5 `in_app_notification` rows
- D7: `user_preference` / `user_setting_override` — in `seed_test_tenant.py` Group C (promoted from P3)

**Nothing deferred to SD-7 from this session.** All 10 decisions are in-scope for SD-6.

---

## 8. Pre-SD-6 MCP Queries Required

Before the Python Engineer writes any SD-6 code, the following column verifications are needed:

```sql
-- invoice_line schema
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice_line' ORDER BY ordinal_position;

-- invoice_line_tax_component schema
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice_line_tax_component' ORDER BY ordinal_position;

-- loto_confirmation schema
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'loto_confirmation' ORDER BY ordinal_position;

-- change_order schema
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'change_order' ORDER BY ordinal_position;

-- change_order_line schema
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'change_order_line' ORDER BY ordinal_position;

-- in_app_notification schema
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'in_app_notification' ORDER BY ordinal_position;

-- mobile_sync_owner_escalation schema
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'mobile_sync_owner_escalation' ORDER BY ordinal_position;

-- payment table (need to verify column name for payment type)
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment' ORDER BY ordinal_position;
```

---

## 9. Open Questions for Tom

| # | Question | Impact |
|---|---|---|
| Q1 | **invoice_line approach**: Should invoice lines be seeded with exact pricebook_item references (FK to `pricebook_item_version`), or as standalone descriptions (no FK — simpler)? | Affects SD-6 D1 FK design |
| Q2 | **change_order scope**: Should the change order be in `pending` (awaiting approval), `approved`, or show a status-progression (one of each)? | Affects SD-6 D5 decision |
| Q3 | **in_app_notification location**: New `seed_scenario_notifications.py` or appended to an existing script? Given 3-5 rows, appending to `seed_scenario_reporting.py` seems right — confirm? | Affects SD-6 D6 script structure |
| Q4 | **SD-5 official close date**: Was SD-5 completed 2026-07-15 (today)? Confirm for README §10 entry. | Affects D8 documentation |

---

*This tracker will be superseded by `batch-sd6-design.md` at end of session.*
