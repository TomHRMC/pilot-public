# Implementation Prompt: PLP-FIX-5 (Part B — Frontend Web) — Plan-Summary Card + Breadcrumbs (Issue 8) + JobFormModal Fields (Issue 12) + Invoice Job-Link (Issue 13b)

**Mode**: `pilot-react-engineer`
**Batch**: PLP-FIX-5 Part B (frontend half of a mixed batch)
**Launch plan**: `dev-docs/analysis/pilot-launch-plan.md` §1 / §3.26 (Ord 26)
**Design doc (read first)**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-5-design.md` — §G decisions + §H pattern spec + §I Component Manifest are binding
**Bug intake**: `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` (Issues 8, 12, 13b)
**Estimate**: ~2.5 h
**Platform**: Web (`apps/web`) — see Platform-Specific Rules below
**Backend companion**: Part A — `batch-plp-fix-5-python-engr-prompt.md` — **MUST be merged first.** Your first Pre-Work step is the `pnpm sync-api-types` it unblocks. If `packages/shared-types/src/api-schema.d.ts` does not contain `plan_summary` after syncing, STOP — Part A is not merged.
**Designer gate**: **WAIVED by Tom 2026-09-02** (design §G.8) — the plan-summary card composes the existing settings-card + badge patterns; §H of the design doc is the binding pattern spec. No designer spec exists; do not wait for one.

---

## ⚠️ MANDATORY STOP: Read These First

1. `.roo/rules-pilot-react-engineer/react-engineer-rules.md` — the authority (apiClient-only, TanStack object form, MSW rules, modern stack rules §32–§36)
2. The design doc — §G (10 settled decisions), §H (pattern spec), §I (Component Manifest — build exactly these, nothing more)
3. `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` — Issues 8/12/13b symptoms in Tom's words

---

## Batch-Specific Critical Rules

1. **BE contract is ready — trust it, don't re-derive it.** Part A added `plan_summary`, `charter_eligible`, `limits` to `GET /api/v1/tenants/{tenant_id}/subscription` and `annual_price_cents` to the tier object. Consume those fields; do not add client-side derivations of anything the payload now carries.
2. **Delete the `charterEligible` derivation + its TODO** (`useTenantSubscription.ts`) — the backend now exposes `charter_eligible` (design §G.10). This is a settled decision, not a suggestion.
3. **No new top-level UX patterns.** Status badge = the existing Trial-badge pill idiom; breadcrumb = a text link + separator; success feedback for job create = the existing `useNotificationQueue` pattern. (Design §H; Tom's waiver is contingent on pattern reuse.)
4. **Scope discipline on usage bars** (design §G.7): "Team members" becomes count-only (no users-limit feature exists — do NOT invent one); "SMS segments" wires `max` from `limits.outbound_sms_segments`. Do not add voice/lanes bars.
5. **`parseCentInput`/quantity/Unit Price inputs are untouched** — PLP-FIX-4 just shipped those; do not regress them while editing `InvoiceBuilderPage`.
6. **MSW fidelity**: the subscription fixture in `betaB4Handlers.ts` must be extended with the new sections so tests exercise the real payload shape — no hand-mocked `apiClient` (banned), no partial fixtures that omit the new keys.

---

## Pre-Work: Establish Regression Baseline

```bash
pnpm --filter web test | tail -5
```

Record the counts. (Reference point: PLP-FIX-4 closed at **web 2206 passed**.)

---

## Pre-Work: Sync API Types (FIRST — hard gate)

```bash
pnpm sync-api-types
```

Confirm `packages/shared-types/src/api-schema.d.ts` now includes `plan_summary`, `charter_eligible`, `limits`, `annual_price_cents` (subscription response) and `qco_line_type_id` (quote line detail). If absent → STOP; Part A is not merged.

---

## Pre-Work: Verify Endpoints

Against `backend/openapi.json` (regenerated in Part A):

- `GET /api/v1/tenants/{tenant_id}/subscription` → response includes `plan_summary{status_code,status_name,is_billing_active,billing_interval,renews_at,free_period_ends_at}`, `charter_eligible`, `limits{outbound_sms_segments,schedule_lanes,voice_ai_minutes}`; tier object includes `annual_price_cents`.
- `GET /api/v1/jobs/` → `customer_id` query param (existing — the JobCombobox data source).
- `GET /api/v1/job-types` → `JobTypeResponse[]` (existing).
- `POST /api/v1/jobs/` → body accepts `title`, `job_type_id` (existing — you are only widening the FE payload type).

---

## Pre-Work: Read These Source Files

1. `useTenantSubscription.ts` — full file (hand-written Raw/normalize layers you are trueing-up)
2. `BillingSettingsPage.tsx` — full file (Current Plan card 120–177, UsageBars 180–196, header 231–242)
3. `PaymentMethodSettingsPage.tsx` — header/breadcrumb insertion area (~448–560)
4. `JobFormModal.tsx` — full file
5. `useCreateJob.ts` — `JobCreatePayload`/`JobCreateResponse` (17–39)
6. `useJobTypes.ts`
7. `useJobs.ts` — `customer_id` option (73–104)
8. `SiteCombobox.tsx` — the pattern `JobCombobox` mirrors
9. `InvoiceBuilderPage.tsx` — Section 1 header panel (~342–370), job prefill effects (132–159), line-items empty state (444–449)
10. `betaB4Handlers.ts` — `SUBSCRIPTION_FIXTURE` + the GET handler (~150–160)
11. `mocks/handlers/index.ts` — barrel (register any new handler file here — one line, alphabetical per existing convention)
12. Existing tests: `BillingSettingsPage` tests (find via `grep -r "BillingSettingsPage" apps/web/src --include="*.test.*"`), `JobFormModal` tests, `InvoiceBuilderPage` tests

---

## Context: What This Batch Does

Three Tom-visible gaps from the 09-02 prod pass:

- **Issue 8**: the Billing page can't answer "what am I paying, when does it renew, monthly or annual" and neither billing page has a breadcrumb. Part A shipped the data; you render it.
- **Issue 12**: quick-add Job modal lacks Title + Job Type (both already accepted by `POST /jobs`) and says nothing about the assigned job number after create.
- **Issue 13b**: the standalone invoice builder says "Link a job above to pre-fill billable items" with no way to link one.

Issue 14 (quote Type "—") is **Part A only** — the editor already reads `qco_line_type_id`; no FE work. Do not touch `LineItemEditor`.

---

## Design Decisions (Do Not Re-Litigate)

From design §G — settled:

1. Job number: server-assigned; surfaced in the post-create **success notification** (`useNotificationQueue`) — no editable override, no new in-modal success state.
2. Job status: NOT selectable at creation (BE has no `status_id` on `JobCreate`); the success notification includes the assigned `status_code` (already on `JobResponse`). Deferred to backlog.
3. Job type: optional `<select>` via `useJobTypes`, default "No type" (`job_type_id` omitted when unset). No context inference.
4. Status badge labels/token pairs: per design §H.1 Row 2 — `trialing`→alert, `active`→success, `past_due`→alert, `paused`/`unpaid`/`canceled`→fault, none→neutral. Label always rendered (color-independent).
5. Price line: `annual_price_cents` is the **yearly total** → annual: `$588/yr ($49/mo)`; monthly: `$59/mo`; charter branch unchanged ("Your rate: $49/mo — locked"); no interval → tier monthly rate as list price.
6. Date line: charter tier → `free_period_ends_at` labeled "Free period ends …"; all others → `renews_at` labeled "Renews …". `toLocaleDateString` (existing idiom).
7. 13b placement: selector in Section 1 beside customer/site; visible when `customerId` set AND `activeJobId` null; linked state = chip summary + "Clear job"; `?job_id=` path untouched.

---

## STEP 1 — `useTenantSubscription` true-up (Issue 8 foundation)

**1a.** Extend the Raw interfaces to match the real (post-Part-A) payload:

```ts
interface PlanSummaryRaw {
  status_code: string | null;
  status_name: string | null;
  is_billing_active: boolean;
  billing_interval: "monthly" | "annual" | null;
  renews_at: string | null;
  free_period_ends_at: string | null;
}

interface PlanLimitsRaw {
  outbound_sms_segments: number | null;
  schedule_lanes: number | null;
  voice_ai_minutes: number | null;
}
```

Add `annual_price_cents: number` to `SubscriptionTierRaw`; add `plan_summary: PlanSummaryRaw`, `charter_eligible: boolean`, `limits: PlanLimitsRaw` to `SubscriptionRaw`. **Remove** `max_users` / `max_sms_segments_per_month` from `SubscriptionTierRaw` — the BE never sent them (design-time finding 8a).

**1b.** Mirror into the normalized `TenantSubscription`/`SubscriptionTier` exports (`planSummary`, `charterEligible` — now from the payload, `limits`, `annualPriceCents`). **Delete the derivation + TODO comment** (rule 2 above).

**1c.** The `usage` normalization stays as-is.

## STEP 2 — Plan-summary card + breadcrumbs (Issue 8)

**2a.** New `SettingsBreadcrumb` (`features/settings/components/SettingsBreadcrumb.tsx`) per design §F.2: `trail: { label: string; href?: string }[]`; non-last items render as `Link` (`text-brand-600 hover:underline`), separators ` / `, last item plain `text-neutral-500`; container `text-sm text-neutral-500 mb-2`.

**2b.** `BillingSettingsPage`: render `<SettingsBreadcrumb trail={[{ label: "Settings", href: "/settings" }, { label: "Billing & Subscription" }]} />` above the `h1`. Extend the Current Plan card per design §H.1:
- Status badge next to `displayLabel` (pill idiom copied from the existing Trial badge at line 140; token pairs per Design Decision 4).
- Price line branch on `planSummary.billing_interval` (Design Decision 5).
- Date line (Design Decision 6) — rendered only when the relevant date is non-null.
- Charter branch unchanged otherwise; upgrade CTAs unchanged.

**2c.** Usage bars (Design §G.7): "Team members" → drop the `max` prop (count-only; the bar segment disappears by the component's existing `max &&` guard); "SMS segments" → `max={limits.outboundSmsSegments}`. Do not touch `UsageBar` itself.

**2d.** `PaymentMethodSettingsPage`: same breadcrumb with trail `[{ label: "Settings", href: "/settings" }, { label: "Payment Method" }]` above its content header. Nothing else changes on this page.

## STEP 3 — JobFormModal fields (Issue 12)

**3a.** `useCreateJob.ts`: `JobCreatePayload` += `title?: string | null; job_type_id?: string | null;`. `JobCreateResponse` += `job_number?: string; status_code?: string | null;` (BE `JobResponse` already sends both — you're truing the interface, not the API).

**3b.** `JobFormModal.tsx`:
- **Title input** (optional) above the customer combobox — existing form-control idiom, placeholder "e.g. Panel upgrade".
- **Job Type `<select>`** below the site combobox — options from `useJobTypes()` (`{jt.id}` → `{jt.label}`), first option "No type" with empty value; omit `job_type_id` from the payload when empty.
- Pass both through in the `createJob(...)` call (and NOT to the recurrence-rule path — `createRule` payload shape is unchanged; when `isRecurring`, hide/ignore the two new fields per the existing conditional-render idiom).
- **Success notification**: in the `onSuccess` of `createJob`, fire `useNotificationQueue` with severity `success`, title including the assigned job number (e.g. `Job J-0007 created (Scheduled).`) — fall back to "Job created." when `job_number` is absent. Recurrence path notification unchanged.

## STEP 4 — Invoice job-link (Issue 13b)

**4a.** New `JobCombobox` (`apps/web/src/components/JobCombobox.tsx`) mirroring `SiteCombobox`'s structure/idioms (search-as-you-type, keyboard nav, loading/empty states), data via `useJobs({ customer_id: customerId })`; display `job_number` + (`title` ?? status); props per design §F.2.

**4b.** `InvoiceBuilderPage.tsx`:
- In Section 1 (below the Site combobox row), render the link UI **only when `customerId && !activeJobId`**: label "Link a job to pre-fill billable items (optional)" + `JobCombobox` (`onChange` → `setActiveJobId`).
- When `activeJobId` is set: replace the combobox with a chip summary — `J-0007 · {title ?? status_code}` + "Clear job" button (`setActiveJobId(null)`; customer/site stay as the prefill set them — do not reset them).
- Update the 444–449 empty-state copy to: "Link a job above to pre-fill billable items, or add custom line items manually." (unchanged text — it already says this; verify the combobox is visually "above" the copy).
- The `?job_id=` initial path and both prefill effects (132–159) are untouched.

## STEP 5 — MSW + tests

**5a.** `betaB4Handlers.ts`: extend `SUBSCRIPTION_FIXTURE` with `plan_summary` (an `active` monthly example), `charter_eligible: false`, `limits` (all three keys), and `annual_price_cents` on the tier object. If other subscription fixtures exist in the file (e.g. a charter variant), extend them too (charter: `billing_interval: "monthly"`, `free_period_ends_at` set, `charter_eligible: true`).

**5b.** Tests (TanStack `retry: false` setup per inclusions §9; MSW via the shared server — never `jest.mock`/`vi.mock` of `apiClient`):
- `BillingSettingsPage` — new/updated tests: badge renders the fixture's status label; annual fixture renders "$588/yr ($49/mo)"-style line; date line renders when `renews_at` set; SMS bar receives the real max (members row has no bar); breadcrumb renders with the Settings link.
- `PaymentMethodSettingsPage` — breadcrumb present.
- `JobFormModal` — title + job type submit through the payload (MSW capture); empty job type omits `job_type_id`; success notification contains the job number.
- `InvoiceBuilderPage` — combobox appears when customer set + no job; selecting a job sets the linked chip + triggers the prefill flow; Clear job returns to standalone.
- Integration tests live in `apps/web/src/__tests__/batch_plp_fix_5/` (new folder, mirrors `batch_plp_fix_4/` convention); unit tests co-located.

**5c.** Test resilience rule (inclusions §9): assert on user-visible text/roles, not class names; every new test must fail if its feature regresses (no tautological asserts).

---

## Final Verification

### Phase 1 — Targeted tests (run after each task group)

```bash
pnpm --filter web test -- --run src/features/settings src/features/jobs src/features/invoices src/components | tail -5
```

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
pnpm --filter web test | tail -5
```

Baseline → final counts in the Completion Summary (web baseline was recorded in Pre-Work).

---

## Definition of Done — PLP-FIX-5 Part B

- [ ] Pre-Work complete: baseline recorded; `sync-api-types` confirmed all five new fields; all 12 file reads done
- [ ] STEP 1: hook true-up — new sections normalized; `charterEligible` derivation + TODO deleted; phantom `max_users`/`max_sms_segments_per_month` removed from Raw
- [ ] STEP 2: badge + interval price + date line per §H.1; breadcrumb on both billing pages; usage bars per §G.7 (members count-only, SMS real max)
- [ ] STEP 3: Title + Job Type in the modal (non-recurrence path only); payload types extended; success notification shows job number
- [ ] STEP 4: `JobCombobox` + link/clear on the invoice builder; `?job_id=` path untouched
- [ ] STEP 5: fixtures extended; all new/updated tests green
- [ ] No `apiClient` mocks; no `fetch()`; TanStack object form; no hand-memoization (rules §32)
- [ ] WCAG 2.2 AA: badge labels are text (not color-only); combobox keyboard-navigable; focus rings preserved
- [ ] Phase 1 + Phase 2 run and recorded (final = baseline + new tests, zero regressions)
- [ ] Completion Summary filled in below

---

## Completion Summary

Append to `## Appendix — Completion Summary` at the bottom of this file using **exactly** this structure:

### PLP-FIX-5 Part B — Plan Summary + Job Modal Fields + Invoice Job-Link: Completion Summary

#### What Was Accomplished
(5–8 bullets mapped to Issues 8/12/13b + the hook true-up)

#### Files Changed / Created
(Table: file → created/modified → one-line purpose)

#### Tests Added / Updated
(Table: file → type → count → all-pass; baseline → final web counts)

#### Deploy Note for Tom
(Pure FE deploy after Part A is live; verification steps from the design doc's final section)

---

## Appendix — Completion Summary

### PLP-FIX-5 Part B — Plan Summary + Job Modal Fields + Invoice Job-Link: Completion Summary

#### What Was Accomplished

- **Issue 8 (hook true-up)**: Extended `useTenantSubscription.ts` Raw interfaces to match the post-Part-A payload (`plan_summary`, `charter_eligible`, `limits`, `annual_price_cents`); deleted the client-side `charterEligible` derivation + TODO; removed phantom `max_users`/`max_sms_segments_per_month` from `SubscriptionTierRaw`.
- **Issue 8 (plan-summary card)**: `BillingSettingsPage.tsx` now renders a status badge (color + text label per §H.1 Row 2), an interval-aware price line (annual `$588/yr ($49/mo)` / monthly `$59/mo` / charter locked), and a renews/free-period date line. Usage bars: "Team members" is count-only (no users-limit feature); "SMS segments" wires `max` from `limits.outboundSmsSegments`.
- **Issue 8 (breadcrumbs)**: New `SettingsBreadcrumb.tsx` component (feature-local; accepts explicit `trail` prop or auto-derives from pathname) rendered on both `/settings/billing` and `/settings/billing/payment-method`.
- **Issue 12 (JobFormModal fields)**: `JobFormModal.tsx` now has a Title input (optional) and Job Type `<select>` (optional, via `useJobTypes`), both on the non-recurrence path only. Success notification via `useNotificationQueue` includes the server-assigned `job_number` + `status_code`. `useCreateJob.ts` payload/response types extended.
- **Issue 13b (invoice job-link)**: New `JobCombobox.tsx` (mirrors `SiteCombobox` pattern; data via `useJobs({ customer_id })`). `InvoiceBuilderPage.tsx` renders the selector when `customerId && !activeJobId`; linked state shows a chip summary + "Clear job" button (no confirm dialog — replaces the old `window.confirm` dismiss flow).
- **Flaky test fix**: The 2 pre-existing flaky failures in `invoice_ui_b1` tests 4 & 5 (badge dismiss with `window.confirm`) are resolved — the confirm flow is replaced by the simpler "Clear job" button.

#### Files Changed / Created

| File | Created/Modified | Purpose |
|---|---|---|
| `useTenantSubscription.ts` | Modified | Raw interfaces true-up; `planSummary`/`charterEligible`/`limits`/`annualPriceCents` normalized; derivation deleted |
| `SettingsBreadcrumb.tsx` | Modified | Extended to accept `trail` prop; auto-derive fallback preserved for existing callers |
| `BillingSettingsPage.tsx` | Modified | Status badge, interval price, date line, breadcrumb, usage-bar max fix |
| `PaymentMethodSettingsPage.tsx` | Modified | Breadcrumb added above h1 |
| `useCreateJob.ts` | Modified | `JobCreatePayload` += `title?`, `job_type_id?`; `JobCreateResponse` += `job_number?`, `status_code?` |
| `JobFormModal.tsx` | Modified | Title input + Job Type select + success notification with job_number |
| `JobCombobox.tsx` | Created | Customer-scoped job typeahead combobox (mirrors SiteCombobox) |
| `InvoiceBuilderPage.tsx` | Modified | Job-link selector + chip/clear UI; `handleDismissJob` → `handleClearJob` (no confirm) |
| `betaB4Handlers.ts` | Modified | `SUBSCRIPTION_FIXTURE` extended with `plan_summary`, `charter_eligible`, `limits`, `annual_price_cents` |
| `dispatchBoardHandlers.ts` | Modified | `MOCK_CHARTER_TIER` += `annual_price_cents` |
| `quotes.ts` | Modified | 3 line items += `qco_line_type_id` (Part A OpenAPI regen type fix) |
| `billing_plan_summary.integration.test.tsx` | Created | 7 tests: badge, monthly/annual price, date line, breadcrumb, usage bars, charter |
| `job_form_modal_fields.integration.test.tsx` | Created | 6 tests: title input, job type select, payload capture, empty type, success notification, recurrence hide |
| `invoice_job_link.integration.test.tsx` | Created | 4 tests: selector appears, selecting job, clear job, no customer |
| `billing-upgrade.integration.test.tsx` | Modified | CHARTER/TEAMS fixtures updated with new payload sections |
| `invoice_ui_b1.integration.test.tsx` | Modified | Tests 2-5 updated for chip format + Clear job (no confirm) |
| `invoice_builder_job_prefill.integration.test.tsx` | Modified | Test 4 updated for Clear job (no confirm) |
| `PaymentMethodSettingsPage.test.tsx` | Modified | Breadcrumb test added; heading role fix |
| `billing.test.tsx` | Modified | Heading role fix (breadcrumb text collision) |
| `payment_method.integration.test.tsx` | Modified | Heading role fix (breadcrumb text collision) |
| `customer_jobs_new_job_modal.integration.test.tsx` | Modified | `NotificationQueueProvider` wrapper added (JobFormModal now uses `useNotificationQueue`) |

#### Tests Added / Updated

| File | Type | Count | All-pass |
|---|---|---|---|
| `billing_plan_summary.integration.test.tsx` | Integration (new) | 7 | ✅ |
| `job_form_modal_fields.integration.test.tsx` | Integration (new) | 6 | ✅ |
| `invoice_job_link.integration.test.tsx` | Integration (new) | 4 | ✅ |
| `PaymentMethodSettingsPage.test.tsx` | Unit (updated) | +1 | ✅ |
| `billing-upgrade.integration.test.tsx` | Integration (updated) | 8 (fixtures) | ✅ |
| `invoice_ui_b1.integration.test.tsx` | Integration (updated) | 6 | ✅ |
| `invoice_builder_job_prefill.integration.test.tsx` | Integration (updated) | 4 | ✅ |
| `billing.test.tsx` | Unit (updated) | 4 | ✅ |
| `payment_method.integration.test.tsx` | Integration (updated) | 6 | ✅ |
| `customer_jobs_new_job_modal.integration.test.tsx` | Integration (updated) | 4 | ✅ |

**Baseline → final web counts**: 2206 passed (2 flaky fails) → **2224 passed (0 fails)**. +18 new tests, 2 flaky failures fixed, zero regressions.

**Full canonical verification**: UI 660 ✅ · Web 2224 ✅ · Mobile 701 ✅ · Type checks ✅ · Lint ✅ · `=== MVP FINAL VERIFICATION COMPLETE ===`

#### Deploy Note for Tom

Pure FE deploy after Part A is live. Verification steps:
1. **Issue 8**: Settings → Billing & Subscription shows status badge ("Active"/"Trial"), interval-aware price ("$59/mo" or "$588/yr ($49/mo)"), and a renews/free-period date; breadcrumb appears on both billing pages; SMS usage bar shows a real limit.
2. **Issue 12**: Add Job modal offers Title + Job Type; on create, the success notification shows the assigned job number (e.g. "Job J-0007 created (scheduled).").
3. **Issue 13b**: New Invoice → pick customer → "Link a job" selector appears → selecting a job pre-fills customer/site + billable items; Clear job returns to standalone.
4. **Issue 14**: No FE deploy needed — the editor already reads `qco_line_type_id` (Part A only).
