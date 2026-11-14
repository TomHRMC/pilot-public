# Batch Design: PLP-FIX-5 — Billing Plan Summary + Breadcrumbs (Issue 8) + JobFormModal Fields (Issue 12) + Invoice Job-Link (Issue 13b) + Quote-Line Type ID (Issue 14)

**Batch code**: PLP-FIX-5 (mixed — Part A Python runs first, Part B React gated on `pnpm sync-api-types`)
**Date**: 2026-09-02
**Author**: Pilot Architect
**Status**: Awaiting Tom approval → execute
**Bug intake doc**: `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` (Issues 8, 12, 13b, 14)
**Estimate**: Part A ~1.5 h · Part B ~2.5 h (total ~4 h; triage said 4–5 h)

---

## Scope Statement

Four Tom-reported gaps from the 09-02 prod testing pass, one batch:

1. **Issue 8 (P1)** — Settings → Billing & Subscription shows no plan status, no renewal/expiration date, no monthly-vs-annual indication; neither `/settings/billing` nor `/settings/billing/payment-method` has a breadcrumb back to Settings. Root cause split: the FE "Current Plan" card renders only `displayLabel` + `monthlyPriceCents` because the BE `TenantSubscriptionResponse` never exposes the `subscription` row (status, `billing_interval`, `renews_at`) — the data exists, the contract doesn't carry it.
2. **Issue 12 (P1)** — quick-add `JobFormModal` lacks title and job type (both already accepted by `JobCreate`), and gives no feedback about the server-assigned `job_number`/status after create.
3. **Issue 13b (P1)** — standalone `InvoiceBuilderPage` says "Link a job above to pre-fill billable items" but offers no way to link one; job prefill exists only via the `?job_id=` URL param.
4. **Issue 14 (P1)** — quote detail "Type" renders "—" on every persisted line: `QuoteLineDetailResponse` omits `qco_line_type_id`; the draft editor resolves persisted-row labels by id (`LineItemEditor.tsx`). The join at `quote_service.py` already fetches it — pure response-shape gap, BE-only additive fix, **zero FE code change** (the editor already declares the field optional).

**Design-time findings folded in**:
- **8a — usage bars silently degraded**: the FE hook's `SubscriptionTierRaw` declares `max_users` / `max_sms_segments_per_month` (`useTenantSubscription.ts`) that the BE `SubscriptionTierResponse` never sends → both `UsageBar`s render with `max=undefined` (no bar). MCP-verified only 3 `product_feature` codes exist (`outbound_sms_segments`, `schedule_lanes`, `voice_ai_minutes`) — there is **no users-limit feature** to source `maxUsers` from.
- **8b — `charterEligible` client derivation**: the hook derives it from `tierName` with an explicit TODO to delete when the BE exposes `charter_eligible` (`useTenantSubscription.ts`). The tenant column exists (MCP: boolean NOT NULL). Part A exposes it; Part B deletes the derivation.

**Explicitly out of scope**: selectable job status at creation (`JobCreate` has no `status_id`; route defaults — deferred), any new endpoint, generic tier picker (existing no-op button stays), mobile app changes.

---

## A. Input Read Summary

| Input | What was verified | Date |
|---|---|---|
| `PLP-testing-bugs-2026-09-02.md` | Issues 8/12/13b/14 sections incl. verified root causes | 2026-09-02 |
| `pilot-operations.md` §2–§6, §8 (rule §10.1 mandatory) | tier→plan→ppfv cascade; `billing_interval` semantics; `renews_at` from Stripe `current_period_end`; charter row written synchronously with `trial_ends_at=renews_at=free_period_ends_at`, `billing_interval='monthly'`, status `trialing`; 6 `subscription_status` codes + `is_billing_active` paywall semantics | 2026-09-02 |
| `stripe-pricing-config.md` §4 (rule §10.2) | all price IDs; `annual_price_cents` = **yearly total** ($588=58800¢), `monthly_price_cents` = month-to-month premium ($59=5900¢); charter = $49/mo price on the Starter product, annual charter = NULL | 2026-09-02 |
| `backend/services/quote_service.py` 300–386 | line-item assembly at 316–337: join selects `(QuoteLine, QcoLineType)`; constructor at 327–335 omits `qco_line_type_id` | 2026-09-02 |
| `backend/api/schemas/quotes.py` 107–122 | `QuoteLineDetailResponse` field list (no `qco_line_type_id`) | 2026-09-02 |
| `backend/api/routes/tenant_subscription.py` 1–222 | `TenantSubscriptionResponse` (50–55: tier, trial_ends_at, stripe_customer_id, usage, tier_override — **no subscription row**); `_get_tenant_subscription_impl` (114–186); tenant-isolation guard (218–221); `/test` twin exists (192–200) | 2026-09-02 |
| `backend/api/routes/subscription_tiers.py` 24–40 | `SubscriptionTierResponse` fields — has `monthly_price_cents`, **lacks `annual_price_cents`**, `charter_eligible` n/a (tenant column) | 2026-09-02 |
| `BillingSettingsPage.tsx` 1–243 | Current Plan card (120–177), trial banner (111–118), UsageBars (180–196) fed by `currentTier.maxUsers`/`maxSmsSegmentsPerMonth` (undefined today), no breadcrumb | 2026-09-02 |
| `useTenantSubscription.ts` 1–110 | hand-written Raw/normalize layers; `charterEligible` derivation + TODO; `SubscriptionTierRaw` declares fields BE never sends | 2026-09-02 |
| `JobFormModal.tsx` 1–120 | current field set: customer/site comboboxes, start/end, est. duration, recurrence; `useCreateJob` hook body type has no title/job_type | 2026-09-02 |
| `backend/api/schemas/schemas.py` 185–231 | `JobCreate` **already accepts** `title`, `job_type_id`, `priority`; `JobResponse` carries `job_number`, `status_code` — Issue 12 needs **no BE change** | 2026-09-02 |
| `backend/api/routes/job_types.py` 71–84 | `GET /api/v1/job-types` + `/test` exist | 2026-09-02 |
| `useJobTypes.ts` | hook exists (JOB-UI-B1) | 2026-09-02 |
| `InvoiceBuilderPage.tsx` 60–179 | `activeJobId` state drives prefill (`useJob` → customer/site at 143–148) + `useBillableItems`; no in-page job setter | 2026-09-02 |
| `useJobs.ts` 73–104 | `customer_id` filter param exists (UI-FIX-2D) → combobox data source ready | 2026-09-02 |
| `backend/services/entitlement_service.py` | `check_entitlement(tenant_id, ...)` resolver + `get_cached_entitlement` variant exist for the limits lookup | 2026-09-02 |
| **MCP `postgres-local`** (6 queries, results recorded in §B) | `subscription` columns; `tenant` trial/free-period columns; `subscription_status` 6 rows; `quote_line.qco_line_type_id` uuid NOT NULL; `subscription_tier` price columns int NOT NULL; `product_feature` = exactly 3 codes | 2026-09-02 |

---

## B. Migration Plan

**None.** Zero schema changes, zero data changes. Additive response fields only, sourced from existing columns/rows.

Seed Data Rollout (rule §11.5 consideration): **N/A** — no new lookup rows, no new seed values. `subscription_status` rows already seeded (6 codes MCP-verified); `product_feature` codes already seeded.

Prompt Pre-Work MCP queries (engineer re-runs; expected results recorded):

```sql
-- Q1 subscription write-source columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='subscription'
  AND column_name IN ('tenant_id','status_id','billing_interval','renews_at','trial_ends_at','is_active','product_plan_code')
ORDER BY ordinal_position;
-- Expected: tenant_id uuid NO · product_plan_code varchar NO · status_id uuid NO · billing_interval varchar NO · trial_ends_at timestamptz YES · renews_at timestamptz YES · is_active bool NO

-- Q2 status lookup rows
SELECT code, name, is_billing_active FROM public.subscription_status ORDER BY code;
-- Expected: active/t · canceled/f · past_due/t · paused/f · trialing/t · unpaid/f

-- Q3 tenant + tier columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='tenant'
  AND column_name IN ('trial_ends_at','free_period_ends_at','current_subscription_tier_id','charter_eligible');
-- Expected: 4 rows (trial_ends_at/free_period_ends_at nullable timestamptz; other two NOT NULL)

-- Q4 quote_line + tier price columns
SELECT table_name, column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND ((table_name='quote_line' AND column_name='qco_line_type_id')
  OR (table_name='subscription_tier' AND column_name IN ('annual_price_cents','monthly_price_cents')))
ORDER BY table_name, ordinal_position;
-- Expected: quote_line.qco_line_type_id uuid NO · subscription_tier.annual_price_cents int NO · monthly_price_cents int NO

-- Q5 feature codes for the limits object
SELECT code, name, is_active FROM public.product_feature ORDER BY code;
-- Expected: outbound_sms_segments · schedule_lanes · voice_ai_minutes (exactly 3 — no users-limit feature)
```

---

## C. Execution Order

### Part A — Backend (Python Engineer, runs first)

| # | Step | File(s) |
|---|---|---|
| 1 | Pre-Work: baseline, MCP Q1–Q5, mandatory reads | — |
| 2 | Issue 14: `QuoteLineDetailResponse` += `qco_line_type_id: UUID`; populate in the constructor | `api/schemas/quotes.py`, `services/quote_service.py` |
| 3 | Issue 8 BE: `PlanSummaryResponse` + `PlanLimitsResponse` schemas; extend `TenantSubscriptionResponse` (+`plan_summary`, +`charter_eligible`, +`limits`); extend `SubscriptionTierResponse` (+`annual_price_cents`); wire in `_get_tenant_subscription_impl` | `api/routes/tenant_subscription.py`, `api/routes/subscription_tiers.py` |
| 4 | Tests: Issue 14 round-trip via real `/detail` endpoint; plan-summary (subscription-row tenant, derived-trialing tenant, none-status tenant); limits resolved from ppfv; `annual_price_cents` present | `tests/domains/sales_quoting/…`, `tests/domains/subscriptions_usage/…` |
| 5 | OpenAPI regen (`export_openapi_json.py`) + commit → **handoff signal for Part B** | `backend/openapi.json` |

### Part B — Frontend (React Engineer, after Part A merges)

| # | Step | File(s) |
|---|---|---|
| 1 | `pnpm sync-api-types` (hard gate) | — |
| 2 | Issue 8 FE-a: hook normalization extended (`plan_summary`, `charter_eligible`, `limits`, `annual_price_cents`); delete `charterEligible` derivation + TODO | `useTenantSubscription.ts` |
| 3 | Issue 8 FE-b: plan-summary card extension (status badge, interval-aware price, renews/expires date) + `SettingsBreadcrumb` on billing + payment-method pages; usage bars: SMS real limit, members count-only | `BillingSettingsPage.tsx`, `PaymentMethodSettingsPage.tsx`, new `SettingsBreadcrumb.tsx` |
| 4 | Issue 12: `JobFormModal` + Title (optional) + Job Type (dropdown via `useJobTypes`); success shows `job_number` + status; `useCreateJob` body type extended | `JobFormModal.tsx`, `useCreateJob.ts` |
| 5 | Issue 13b: `JobCombobox` (mirrors `SiteCombobox` pattern) + link/clear affordance on `InvoiceBuilderPage` | new `JobCombobox.tsx`, `InvoiceBuilderPage.tsx` |
| 6 | Tests + two-phase verification | — |

---

## D. API Contract Changes (additive only — no new endpoints, no removals)

### D.1 — `GET /api/v1/quotes/{quote_id}/detail` (Issue 14)

`QuoteLineDetailResponse` gains:

```python
qco_line_type_id: UUID  # populated from QuoteLine.qco_line_type_id (join already fetches it)
```

### D.2 — `GET /api/v1/tenants/{tenant_id}/subscription` (Issue 8)

`SubscriptionTierResponse` gains `annual_price_cents: int` (MCP: NOT NULL).

`TenantSubscriptionResponse` gains:

```python
class PlanSummaryResponse(BaseModel):
    status_code: str | None        # subscription_status.code; derived "trialing" when no row + live trial
    status_name: str | None        # display label from the same row/derivation
    is_billing_active: bool        # row's flag; True for derived trialing
    billing_interval: str | None   # "monthly" | "annual" | None (no row)
    renews_at: str | None          # ISO; charter row: = free_period_ends_at
    free_period_ends_at: str | None  # tenant.free_period_ends_at (charter only)

class PlanLimitsResponse(BaseModel):
    outbound_sms_segments: int | None
    schedule_lanes: int | None
    voice_ai_minutes: int | None

class TenantSubscriptionResponse(BaseModel):
    current_tier: SubscriptionTierResponse
    trial_ends_at: str | None
    stripe_customer_id: str | None
    usage: UsageSummaryResponse | None
    tier_override: TierOverrideResponse | None
    plan_summary: PlanSummaryResponse   # NEW — always present; fields nullable inside
    charter_eligible: bool              # NEW — tenant.charter_eligible (retires FE derivation)
    limits: PlanLimitsResponse          # NEW — ppfv-resolved via check_entitlement
```

Derivation rule when no active `subscription` row exists (pre-conversion trial tenants): `status_code = "trialing"` + `is_billing_active = True` when `tenant.trial_ends_at > now()`; otherwise `status_code = None`, `is_billing_active = False`. (§G.4)

---

## E. Pattern Reuse Decisions

| Pattern | Applies? | How |
|---|---|---|
| §16 four-class severity / color-independent status | **Yes** | status badge = colored pill **plus** text label (existing Trial badge idiom at `BillingSettingsPage.tsx`); never color alone |
| §16 system-default/tenant-override | N/A | display-only surface |
| Tenant-scoped `select()` (no `db.get()`) | **Yes** | subscription-row lookup: `select(Subscription).where(Subscription.tenant_id == tenant_id, Subscription.is_active == True)` |
| `/test` endpoint twins | **Yes (existing)** | both touched endpoints already have `/test` twins delegating to the same `_impl` — they inherit the new fields; new tests prefer the twins |
| Limits resolution | **Yes (existing service)** | reuse `check_entitlement` (`entitlement_service.py`) per feature code — do NOT hand-write a ppfv query |
| Phantom-gate rule | **Yes (awareness)** | no `feature_code=` changes; the endpoint's `subscription.view` RBAC is unchanged |
| Designer gate (rule §1.5) | **WAIVED by Tom 2026-09-02** — recorded in §G.8 | plan-summary card composes the existing settings-card + badge patterns; no new top-level UX |
| apiClient + TanStack object form + MSW | **Yes** | all FE data paths; MSW handlers updated for the extended subscription payload |

---

## F. Shared Module Interfaces

### F.1 — Backend (Part A)

```python
# api/routes/tenant_subscription.py — inside _get_tenant_subscription_impl, after tier resolution:

# 1. Active subscription row (tenant-scoped)
sub_row = db.exec(
    select(Subscription)
    .where(Subscription.tenant_id == tenant_id)
    .where(Subscription.is_active == True)
).first()

sub_status = (
    db.exec(select(SubscriptionStatus).where(SubscriptionStatus.id == sub_row.status_id)).first()
    if sub_row else None
)

# 2. Derived status when no row (§G.4)
# 3. limits via check_entitlement(tenant_id, <feature_code>, db) per the 3 MCP-verified codes
#    (signature verified 2026-09-02: check_entitlement(tenant_id, feature_code, db) -> EntitlementResult;
#     EntitlementResult.limit is the PlanLimitsResponse value)
```

Model imports to add: `Subscription` + `SubscriptionStatus` — both live in `app/models/billing.py` (lines 541, 732), NOT `app.models.subscription` (that module holds `SubscriptionTier`/`TenantSubscriptionUsage`/`TenantTierOverride`, already imported at the top of the route file).

### F.2 — Frontend (Part B)

```ts
// features/settings/components/SettingsBreadcrumb.tsx (NEW — feature-local)
interface SettingsBreadcrumbProps {
  trail: { label: string; href?: string }[];  // last item = current page (no href)
}

// features/jobs/components/JobCombobox.tsx (NEW — mirrors components/SiteCombobox.tsx pattern)
interface JobComboboxProps {
  customerId: string;              // required — jobs are customer-scoped
  value: string | null;
  onChange: (jobId: string | null) => void;
  disabled?: boolean;
}
```

---

## G. Open Questions Resolved

1. **Job number (Issue 12)**: server-assigned (B19; `JobResponse.job_number`). No editable override — the modal's success state displays the assigned `job_number` + `status_code`. After-create feedback, not an input.
2. **Job status selectable at creation (Issue 12)**: **No** — `JobCreate` has no `status_id` and the route defaults it; adding status selection requires a BE contract + status-machine decision that is out of this batch's blast radius. Deferred to backlog (noted in launch-plan §8 candidate). The success state showing the assigned status satisfies the informational need.
3. **Job type defaulting (Issue 12)**: optional dropdown via existing `useJobTypes`; default = none (`job_type_id` nullable in `JobCreate`). No customer/site-context inference — that is a future heuristic, not a bug fix.
4. **Derived status with no subscription row (Issue 8)**: `trialing`/`True` when `tenant.trial_ends_at > now()` (pre-conversion trial tenants have no row — the trial banner path); else `status_code=None`, `is_billing_active=False`. Never fabricate a row lookup failure into "active".
5. **Charter display semantics (Issue 8)**: charter tier (`tier_name='charter'`) → the date line reads from `free_period_ends_at` labeled **"Free period ends …"**; price line keeps the existing "Your rate: $49/mo — locked" (already correct). For all other tiers: `renews_at` labeled **"Renews …"**; `trial_ends_at` keeps the existing trial banner.
6. **Price display (Issue 8)**: `annual_price_cents` is the **yearly total** (ops §3 / pricing-config §4) → annual renders "$588/yr ($49/mo)"; monthly renders "$59/mo"; `billing_interval` from `plan_summary` picks the branch; no interval (trial/no row) renders the tier's monthly rate as the list price.
7. **Usage bars (design-time finding 8a)**: only 3 `product_feature` codes exist (MCP) — there is no users-limit source. "Team members" row becomes **count-only** (drop the fabricated max, keep the count); "SMS segments" row wires `max` from `limits.outbound_sms_segments`. No new bars (voice/lanes limits are exposed in the payload for future use but not rendered — scope discipline).
8. **Designer gate**: **waived by Tom 2026-09-02** ("just reuse the settings-card and badge patterns"). §H below is the pattern spec the React Engineer builds against; no designer-mode spec is commissioned.
9. **13b selector placement**: rendered where the empty-state copy points ("Link a job above"), visible when `customerId` is set AND `activeJobId` is null; jobs filtered by `useJobs({ customer_id })`; selecting sets `activeJobId` (existing prefill + billable-items flow takes over unchanged); a "Clear job" affordance resets to the standalone path. The `?job_id=` param path is untouched.
10. **FE hook contract drift (8b)**: Part B deletes the `charterEligible` derivation + TODO and normalizes the three new payload sections; the hand-written `SubscriptionTierRaw`/`SubscriptionRaw` interfaces are corrected to match the true response (incl. removing reliance on the nonexistent `max_users`/`max_sms_segments_per_month`).

---

## H. Surface Mockup Reference (frontend half)

**Designer gate**: waived by Tom (§G.8) — this section is the binding pattern spec.

**H.1 — Plan-summary card** (extends the existing Current Plan card, `BillingSettingsPage.tsx`):
- **Row 1** (existing): "CURRENT PLAN" eyebrow + `displayLabel` + upgrade CTA right-aligned.
- **Row 2 — status badge**: pill idiom copied from the existing Trial badge (`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium`), token pairs by status: `trialing` → `bg-alert-100 text-alert-700` "Trial"; `active` → `bg-success-100 text-success-700` "Active"; `past_due` → `bg-alert-100 text-alert-700` "Past due"; `paused`/`unpaid`/`canceled` → `bg-fault-100 text-fault-700` + matching label; derived-none → `bg-neutral-100 text-neutral-600` "No active subscription". Label always present (color-independent, WCAG 2.2 AA).
- **Row 3 — price line**: per §G.6 interval branch (charter branch unchanged).
- **Row 4 — date line**: `text-sm text-neutral-500` — "Renews {date}" / "Free period ends {date}" (`toLocaleDateString`, existing idiom at line 114).
- **Breadcrumb**: above the `h1`, `text-sm text-neutral-500` — `Settings` (Link, `hover:underline`, `text-brand-600`) + ` / ` + current page label (plain text). Rendered on `/settings/billing` ("Billing & Subscription") and `/settings/billing/payment-method` ("Payment Method").

**H.2 — JobFormModal additions**: Title `text` input (optional, placeholder "e.g. Panel upgrade") above the customer combobox; Job Type `<select>` (optional, first option "No type") below Site; both existing form-control idioms from the modal. Success state: keep the current close-on-success for the simple path — display `job_number` + status via the existing success notification pattern (`useNotificationQueue`) instead of a new in-modal state (§16: no new UX pattern).

**H.3 — Invoice job-link**: `JobCombobox` + "Link a job to pre-fill billable items" label in the existing selector row; when a job is linked, a chip-style summary (job number + title, "Clear job" button) replaces the combobox; the 445-447 empty-state copy is updated to reference the selector.

**Platform scope**: web only (`apps/web`). §16 pattern consumption: optimistic UI not required (read surfaces); all async loads keep existing skeleton/error idioms.

---

## I. Component Manifest

| Component | Destination | New / Modified | Notes |
|---|---|---|---|
| `SettingsBreadcrumb` | `apps/web/src/features/settings/components/SettingsBreadcrumb.tsx` | **New** | feature-local; used by billing + payment-method pages |
| `BillingSettingsPage` | same | Modified | card extension (badge/price/date), breadcrumb, usage-bar max fix |
| `PaymentMethodSettingsPage` | same | Modified | breadcrumb only |
| `useTenantSubscription` | `features/settings/hooks/useTenantSubscription.ts` | Modified | normalize new sections; delete `charterEligible` derivation; true-up Raw interfaces |
| `JobFormModal` | `features/jobs/components/JobFormModal.tsx` | Modified | Title + Job Type fields; success notification with job_number/status |
| `useCreateJob` | `features/jobs/hooks/useCreateJob.ts` | Modified | request type += `title?`, `job_type_id?` (BE already accepts both) |
| `JobCombobox` | `apps/web/src/components/JobCombobox.tsx` | **New** | mirrors `SiteCombobox` pattern; data via `useJobs({ customer_id })` |
| `InvoiceBuilderPage` | same | Modified | link/clear job selector; empty-state copy update |

Component-existence check (rule §1.5.4): `packages/ui/src/index.ts` — no breadcrumb, no job combobox exists; `SettingsBreadcrumb` stays feature-local (settings-only), `JobCombobox` lives beside `CustomerCombobox`/`SiteCombobox` in `components/` (cross-feature reuse already established there). No orphan components; no `packages/ui` additions.

---

## Verification (post-implementation, Tom on prod)

1. **Issue 14**: open either previously-entered quote → every line shows its Type label (Labor/Material/etc.) — no FE deploy needed for this half (BE only).
2. **Issue 8**: Settings → Billing & Subscription shows status badge ("Trial"/"Active"), interval-aware price, and a renews/free-period date; breadcrumb appears on both billing pages; SMS usage bar shows a real limit.
3. **Issue 12**: Add Job modal offers Title + Job Type; on create, the success notification shows the assigned job number.
4. **Issue 13b**: New Invoice → pick customer → "Link a job" selector appears → selecting a job pre-fills customer/site + billable items; Clear job returns to standalone.
