# Implementation Prompt: PLP-FIX-4 — Checklist Add-Customer Route + Email/Phone Validation + Unit-Price Input (Issues 7, 10, 11)

**Mode**: Pilot React Engineer
**Batch**: PLP-FIX-4
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.24
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-4-design.md` — read sections A–I in full
**Bug report**: `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` — Issues 7, 10, 11
**Estimated session**: 3–4 hours
**Platform**: Web (`apps/web`) + shared UI (`packages/ui` — one new component)
**Backend companion**: None blocking — FIX4-BE-01 (checklist-flag wiring) is a documented Python handoff (§Companion Backend Tasks); do NOT wait for it
**Branch**: `feature/plp-founder-mvp-batches`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-plp-fix-4-design.md`** — every section (A–I)

Critical rules for this batch:

- **Rule 1.1/1.2**: Verify every endpoint you call exists in `backend/openapi_schema_map.md`. Do NOT invent URL patterns or parameter names.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — the design already did (no PhoneInput exists), but you re-verify before placing new exports.
- **Rule 8**: No new npm dependencies — the phone mask is hand-rolled string formatting (design §F.1). `grep` the relevant `package.json` before assuming any helper lib.
- **Rule 9**: Route files stay thin server components — `?add=1` is read inside the **feature component** (`CustomersPage.tsx` is already `"use client"`), never in `page.tsx`.
- **Rule 10**: Any test failure — fix it before done, no "pre-existing" exception without Tom's written confirmation.
- **Rule 11 (React Compiler, §32)**: No hand-written `useMemo`/`useCallback`/`React.memo` in NEW code. (The pre-existing `useMemo` in `CustomersPage.tsx` is explicitly OUT OF SCOPE — routed to BE-TESTS-MAINT; do not touch it.)
- **Rule 12 (TanStack Query v5, §33)**: Object-form only; invalidate (don't hand-patch) after mutations.
- **Rule 13 (Zod v4, §34)**: `z.email()` top-level helper — never `z.string().email()`. This batch uses field-level `safeParse` (no RHF rewrite — design §G Q5, final).
- **Rule 15 (WCAG 2.2 AA, §36)**: inline errors are non-color-only with `aria-invalid` + `aria-describedby`; paste must work on the phone input; modal focus behavior unchanged.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Issue 7b mechanism | `/customers?add=1` deep-link → existing `CreateCustomerModal` opens; param cleared on close | One modal instance, correct post-create destination; mirrors PLP-FIX-2's modal-swap (§G Q1) |
| Phone masking | ONE shared `PhoneInput` + `formatUsPhone` util in `packages/ui/src/phone-input/` (web/ split), applied to all 7 tel fields | 7 identical fields = shared component; house web/ convention (§G Q2) |
| Phone data format | Display `(XXX) XXX-XXXX`; emit E.164 `+1XXXXXXXXXX` / `null` | Matches what all 7 backends already receive — zero data migration (§G Q3) |
| Email validation | `z.email().safeParse` field-level on the existing `useState` form | RHF rewrite explicitly out of scope (§G Q5) |
| `sync-api-types` | N/A — purely UI, no new/modified hooks, no contract change (§G Q6) | Run only if type drift surfaces; say so in the summary |
| Issue 7a (flag never flips) | Companion BE task FIX4-BE-01 — **not your work** | `mark_first_customer` has zero production callers; FE ships on the existing checklist GET + MSW (§G Q7) |
| Quantity input | Untouched — decimals already work | Tom-confirmed correct for measured materials |

---

## Companion Backend Tasks (Python Engineer — Do Not Block React Work)

| # | Task ID | What's Needed | Endpoint |
|---|---|---|---|
| FIX4-BE-01 | Wire `mark_first_customer` (+ audit `mark_catalog_setup`) | Call `services.onboarding_service.mark_first_customer(db, tenant_id)` from the customer-create `_impl` (auth + `/test` both flow through it) after commit; regression test (create → checklist flag true); grep `mark_catalog_setup` callers and wire similarly if test-only | existing `POST /api/v1/customers` |

> **Handed off after this batch completes.** The checklist widget already reads `GET /api/v1/onboarding/checklist` — your work does not depend on the flag flipping. Note it in your Completion Summary as handed off.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
```

Record exact counts (expect ~ui 644, web 2188 passed — PLP-FIX-2 Part B final). Fix or Tom-confirm any failure BEFORE batch work.

## Pre-Work: Sync API Types

**N/A this batch** (design §G Q6 — purely UI, no hook/contract changes). If a type error surfaces during work, run `pnpm sync-api-types` and record it in the Completion Summary.

## Pre-Work: Verify Endpoints

```bash
grep -n "onboarding/checklist" backend/openapi_schema_map.md | head -5
grep -n "customers" backend/openapi_schema_map.md | head -10
```

| Consumer | Endpoint | Verified |
|---|---|---|
| Checklist widget (existing) | `GET /api/v1/onboarding/checklist` | ☐ confirm |
| `useCreateCustomer` (existing) | `POST /api/v1/customers` | ☐ confirm |

No new endpoints are consumed in this batch. If either grep comes back empty → STOP and ask Tom.

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/onboarding/types.ts                     ← CHECKLIST_ITEMS config (actionRoute at line 138)
frontend/apps/web/src/features/onboarding/components/ChecklistItem.tsx ← how the action anchor renders (127–135)
frontend/apps/web/src/features/customers/components/CustomersPage.tsx  ← showCreate + both CreateCustomerModal sites (91, 172, 275)
frontend/apps/web/src/features/customers/components/CreateCustomerModal.tsx
frontend/apps/web/src/features/customers/components/CustomerForm.tsx   ← email (191–203), phone (207–220), DLC-1 gate (71–88, 222–248)
frontend/apps/web/src/features/quotes/components/LineItemEditor.tsx    ← parseCentInput (67–70), updater (120–135), persisted-row price input (300–325), add-row price input (420–440)
frontend/packages/ui/src/index.ts                                      ← barrel export conventions before adding PhoneInput
frontend/packages/ui/src/mfa-enrollment-wizard/web/                    ← house web/ subfolder convention (structure reference)
frontend/apps/web/src/mocks/handlers/index.ts                          ← confirm onboarding + customers handlers already registered
```

Also locate the 6 remaining tel fields (paths in design §A — verify line numbers yourself before editing): `app/signup/phone/page.tsx`, `components/settings/messaging/BrandRegistrationForm.tsx`, `features/settings/components/BillingContactForm.tsx`, `features/sms-compliance/components/TenantDlcProfileForm.tsx`, `features/tenant-site/components/TenantSiteSettingsForm.tsx`, `features/account-settings/components/ProfileSettingsForm.tsx`.

---

## Context: What This Batch Does

| # | Change | Files |
|---|---|---|
| 1 | Shared US phone input (digits-in, progressive `(XXX) XXX-XXXX`, E.164 out) | `packages/ui/src/phone-input/` (new) + `index.ts` export |
| 2 | CustomerForm: email entry validation + mobile_phone via PhoneInput (DLC-1 gate preserved) | `CustomerForm.tsx` |
| 3 | PhoneInput rolled into the other 6 tel fields | 6 files listed above |
| 4 | Unit Price: raw-string editing + format-on-blur (both inputs) | `LineItemEditor.tsx` |
| 5 | Checklist "Add customer" → `/customers?add=1` → modal opens | `types.ts`, `CustomersPage.tsx` |

---

## STEP 1 — `formatUsPhone` util + `PhoneInput` (packages/ui)

Create `packages/ui/src/phone-input/formatUsPhone.ts` and `packages/ui/src/phone-input/web/PhoneInput.tsx` per design §F.1 (signatures are specified there — follow them; read both house patterns first). Requirements:

- `normalizeUsPhoneDigits`: strip non-digits; drop leading `1` when 11 digits; cap at 10.
- `formatUsPhoneDisplay`: progressive — `""` → `""`; `"5"` → `"5"`; `"55"` → `"55"`; `"555"` → `"(555)"`-style ramp… implement the standard ramp: 0–3 digits plain, 4–6 as `(XXX) YYY`, 7–10 as `(XXX) YYY-ZZZZ`.
- `usPhoneToE164`: 10 digits → `"+1" + digits`; otherwise `null`.
- `PhoneInput` (DOM): internal digit draft; display formatted on every render from the draft; **paste works**; backspace natural; on blur → 10 digits → emit E.164, else emit `null`; mounts tolerantly from E.164/digits/""; caller supplies `className` (existing `INPUT_CLASS` — visual parity, no new styling); `aria-invalid`/`aria-describedby` passthrough.
- Add the barrel export to `packages/ui/src/index.ts` (read it first; match existing style).
- **No new npm deps** — hand-rolled formatting.

Intermediate: `pnpm --filter @pilot/ui test 2>&1 | tail -5` after the component's unit test (STEP 6) exists — but create code first, test in STEP 6.

## STEP 2 — CustomerForm: email validation + PhoneInput

- Email: `emailError` per design §F.2 (`z.email().safeParse` on trimmed non-empty value); inline `<p id="customer-email-error" className="text-fault-600 text-sm mt-1">`; `aria-invalid={!!emailError}` + `aria-describedby`; OR `!!emailError` into the existing `isSubmitDisabled` (preserve the DLC-1 attestation gate exactly).
- Mobile phone: replace the raw `<input type="tel">` with `PhoneInput`; `onChange` receives E.164/`null` — store in the existing `mobilePhone` state (adjust state type to `string | null` as needed); submit keeps `mobile_phone: mobilePhone || null` semantics; the DLC-1 attestation block keys off non-empty phone — keep it working with the new value shape.

Intermediate: `pnpm --filter web test -- apps/web/src/features/customers 2>&1 | tail -8`.

## STEP 3 — PhoneInput rollout (6 fields)

Apply `PhoneInput` to the 6 remaining fields (paths above). **Per-field**: read the surrounding submit code first and confirm the value shape that backend expects (all are E.164 today — design §G Q3); keep each field's existing id/label/disabled/class semantics. Pay special attention to the two carrier forms (`BrandRegistrationForm`, `TenantDlcProfileForm`) — TCR-facing values must stay E.164. The signup phone page (`app/signup/phone/page.tsx`) — verify how it stores/transmits the number (Cognito attribute?) before swapping.

Intermediate: `pnpm --filter web test 2>&1 | tail -6`.

## STEP 4 — Unit Price raw-string editing (LineItemEditor)

Implement design §F.3 for BOTH inputs (persisted-row ~line 312; add-row ~line 428): focused-row draft state (`{ key, raw } | null`); `onFocus` seeds raw from cents; `onChange` keeps raw as typed (digits + max one `.`); `onBlur` → `parseCentInput(raw)` → write cents → clear draft → display reverts to `(cents/100).toFixed(2)`. Do not change `parseCentInput` itself or the quantity input.

Intermediate: `pnpm --filter web test -- apps/web/src/features/quotes 2>&1 | tail -8`.

## STEP 5 — Issue 7b: `?add=1` checklist deep-link

- `features/onboarding/types.ts`: `firstCustomerAdded.actionRoute` → `"/customers?add=1"` (nothing else changes — `ChecklistItem` renders the same anchor).
- `CustomersPage.tsx`: `useSearchParams()` (from `next/navigation` — the component is already client); effect: when `searchParams.get("add") === "1"` → `setShowCreate(true)`. On modal close (`onClose`) → clear the param via `router.replace("/customers")` so refresh/back doesn't re-pop. Guard so the effect runs once per param presence (not in a loop).

Intermediate: `pnpm --filter web test -- apps/web/src/features/customers 2>&1 | tail -8`.

## STEP 6 — Tests

**MSW**: no new handlers — confirm the existing onboarding-checklist + customers handlers are registered in `mocks/handlers/index.ts` (read it; if the checklist handler is missing, add it to the existing onboarding handler file and register — barrel step mandatory).

**Unit — new**: `packages/ui/src/phone-input/web/__tests__/PhoneInput.test.tsx` — progressive format as you type; strips letters; 11-digit leading-1 normalize; backspace re-formats; blur with 10 digits emits `+1XXXXXXXXXX`; blur partial emits `null`; mounts from E.164; paste of `(555) 123-4567` works.

**Unit — updated**: `CustomerForm`/`CreateCustomerModal` tests (invalid email → inline error + submit disabled; valid email passes; phone entry shows mask + submits E.164; DLC-1 gate still blocks when phone present + unchecked); `LineItemEditor` tests (type `5.50` into Unit Price; backspace deletes; blur displays `5.50`; add-row same).

**Integration — new folder `apps/web/src/__tests__/batch_plp_fix_4/`** (3 specs):
1. `checklist_add_customer_deep_link.integration.test.tsx` — render `CustomersPage` with `useSearchParams` mocked to `?add=1` → create modal opens; close → `router.replace("/customers")` called. Also: `types.ts` config has no `/customers/new` route remaining (grep-guard as a test or assertion on `CHECKLIST_ITEMS`).
2. `customer_form_validation_phone.integration.test.tsx` — full create flow: invalid email blocks submit + shows error; phone typed as `5551234567` displays `(555) 123-4567` and the POST payload carries E.164; attestation gate intact.
3. `quote_unit_price_entry.integration.test.tsx` — add-line flow: `5.50` entry persists as 550 cents; editing a persisted row's price allows backspace + decimal; blur formats 2dp.

All tests: `retry: false` QueryClient (inclusions §9), MSW `setupServer` (never mock `apiClient`), `vi.mock("next/navigation")` where navigation hooks are used, fresh QueryClient per test, assert by specific content/IDs (never counts), web assertions `toBeInTheDocument()`.

---

## Final Verification

### Phase 1 — Targeted (during development)

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -6
pnpm --filter web test 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_plp_fix_4/ 2>&1 | tail -10
```

> ❌ `npx vitest run` is PERMANENTLY BANNED — only `pnpm --filter …`.

### Phase 2 — Full canonical gate (once, at the end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> `pnpm --filter mobile build` IS the mobile type check. Any failure in either phase → fix before done, or STOP and ask Tom. Mobile is untouched by this batch but the canonical gate runs repo-wide — mobile stays green from baseline.

---

## Definition of Done — PLP-FIX-4

- [ ] Regression baseline captured for `@pilot/ui` + `web` (zero pre-existing failures, or Tom-confirmed)
- [ ] `sync-api-types` disposition recorded (N/A per design §G Q6 — or run + noted)
- [ ] Both endpoint greps confirmed in `openapi_schema_map.md`
- [ ] All mandatory source files read before modifying (incl. `packages/ui/src/index.ts` + `mocks/handlers/index.ts`)
- [ ] **STEP 1**: `formatUsPhone.ts` + `PhoneInput.tsx` created per design §F.1; barrel export added; zero new npm deps
- [ ] **STEP 2**: CustomerForm email validation (inline, `aria-invalid`/`aria-describedby`, submit blocked) + mobile_phone on PhoneInput; DLC-1 attestation gate behavior unchanged
- [ ] **STEP 3**: all 6 remaining tel fields on PhoneInput; each submit path's E.164 expectation verified (carrier forms explicit)
- [ ] **STEP 4**: both Unit Price inputs raw-string editing + blur format; `parseCentInput` and quantity untouched; zero remaining `.toFixed(2)`-in-value on those inputs
- [ ] **STEP 5**: `actionRoute: "/customers?add=1"`; param opens modal once; close clears param via `router.replace`
- [ ] **STEP 6**: PhoneInput unit test (new), CustomerForm + LineItemEditor tests updated, 3 integration specs in `__tests__/batch_plp_fix_4/` — all pass targeted
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` in NEW code (rules §32); components pure
- [ ] Zod v4 top-level `z.email()` used (rules §34); no `z.string().email()`
- [ ] WCAG 2.2 AA spot-checks: inline errors non-color-only + aria wiring; paste works on PhoneInput; ≥24px targets; modal focus unchanged (rules §36)
- [ ] MSW: no duplicate handlers; any added handler registered in `index.ts` barrel
- [ ] FIX4-BE-01 documented as handed off in the Completion Summary
- [ ] **Phase 1**: targeted tests pass — zero failures
- [ ] **Phase 2 FULL canonical gate passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command from the Final Verification section
- [ ] Final test counts (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)

---

## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix below using the exact format.
2. This batch closes no task tracked in another source spec — no external spec headers to flip.
3. State the FIX4-BE-01 handoff explicitly (it's queued for the next Python batch).

```markdown
### PLP-FIX-4 — Checklist Route + Email/Phone Validation + Unit-Price Input: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: ui X passed | web X passed
**Final**: ui X+N passed | web X+N passed (+N new tests)

#### What Was Accomplished
- …

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added / Updated
| Test File | Type | Tests | All Pass |
|---|---|---|---|
```

---

## After This Task — Next Step

Notify Tom: FIX4-BE-01 (checklist-flag wiring) is ready for the next Python batch; Issue 9 debug inputs are with Tom; PLP-FIX-5 (mixed: Issues 8+12+13b+14) authors next per the triage. Deploy note: pure FE deploy — no backend dependency, no migration, no deploy-order constraint.

---

## Appendix — Completion Summary

### PLP-FIX-4 — Checklist Route + Email/Phone Validation + Unit-Price Input: Completion Summary

**Completed**: 2026-09-02
**Mode**: Pilot React Engineer
**Baseline**: ui 644 passed | web 2188 passed
**Final**: ui 660 passed | web 2206 passed (+16 ui, +18 web = +34 new tests)

#### What Was Accomplished
- **Issue 7b (checklist route collision)**: Changed `firstCustomerAdded.actionRoute` from `/customers/new` → `/customers?add=1` in `types.ts`. `CustomersPage.tsx` now reads `useSearchParams()` and opens the existing `CreateCustomerModal` when `?add=1` is present; `handleCloseCreate` clears the param via `router.replace("/customers")` so refresh/back doesn't re-pop. Mirrors the PLP-FIX-2 modal-swap precedent.
- **Issue 10 (email + phone validation)**: Created a shared `PhoneInput` component + `formatUsPhone` pure util in `packages/ui/src/phone-input/` (web-first, platform-agnostic util). Progressive `(XXX) XXX-XXXX` display as you type; emits E.164 `+1XXXXXXXXXX` on blur/commit, `null` for partial/empty. Zero new npm deps — hand-rolled formatting. Rolled into all 7 web `type="tel"` fields (CustomerForm, signup phone page, BrandRegistrationForm, BillingContactForm, TenantDlcProfileForm, TenantSiteSettingsForm, ProfileSettingsForm). RHF forms use `Controller`; useState forms use direct `onChange`/`onBlur`. Email validation added to CustomerForm via Zod v4 `z.email().safeParse` at the field level (no RHF rewrite) with inline non-color-only error + `aria-invalid`/`aria-describedby`.
- **Issue 11 (Unit Price input)**: Both Unit Price inputs in `LineItemEditor.tsx` (create-mode row + edit-mode add-row) now use raw-string draft state while focused (`onFocus` seeds from cents, `onChange` preserves typed digits + max one `.`, `onBlur` parses via existing `parseCentInput` → writes cents → clears draft → display reverts to 2dp). Decimals and backspace now work naturally. `parseCentInput` and quantity input untouched.
- **FIX4-BE-01 (companion backend task)**: Handed off — `mark_first_customer` has zero production callers; the checklist flag never flips. FE ships on the existing `GET /api/v1/onboarding/checklist` + MSW. The Python Engineer should wire `services.onboarding_service.mark_first_customer(db, tenant_id)` into the customer-create `_impl` after commit, and audit `mark_catalog_setup` similarly.

#### Files Changed / Created
| File | Action |
|---|---|
| `packages/ui/src/phone-input/formatUsPhone.ts` | Created — pure util (normalize, format, E.164) |
| `packages/ui/src/phone-input/web/PhoneInput.tsx` | Created — web component |
| `packages/ui/src/phone-input/index.ts` | Created — barrel |
| `packages/ui/src/phone-input/web/__tests__/PhoneInput.test.tsx` | Created — 16 unit tests |
| `packages/ui/src/index.ts` | Modified — barrel export added |
| `packages/ui/package.json` | Modified — subpath exports added |
| `apps/web/src/features/onboarding/types.ts` | Modified — actionRoute → `/customers?add=1` |
| `apps/web/src/features/customers/components/CustomersPage.tsx` | Modified — useSearchParams + useRouter + handleCloseCreate |
| `apps/web/src/features/customers/components/CustomerForm.tsx` | Modified — email validation + PhoneInput + DLC-1 gate |
| `apps/web/src/features/quotes/components/LineItemEditor.tsx` | Modified — Unit Price raw-string draft (both inputs) |
| `apps/web/src/app/signup/phone/page.tsx` | Modified — PhoneInput + showPhoneError logic |
| `apps/web/src/components/settings/messaging/BrandRegistrationForm.tsx` | Modified — PhoneInput via RHF Controller |
| `apps/web/src/features/settings/components/BillingContactForm.tsx` | Modified — PhoneInput via RHF Controller |
| `apps/web/src/features/sms-compliance/components/TenantDlcProfileForm.tsx` | Modified — PhoneInput |
| `apps/web/src/features/tenant-site/components/TenantSiteSettingsForm.tsx` | Modified — PhoneInput |
| `apps/web/src/features/account-settings/components/ProfileSettingsForm.tsx` | Modified — PhoneInput |
| `apps/web/src/features/customers/components/__tests__/CustomerForm.test.tsx` | Modified — +5 email/phone tests |
| `apps/web/src/features/quotes/components/__tests__/LineItemEditor.test.tsx` | Modified — +3 unit price tests |
| `apps/web/src/features/customers/components/__tests__/CustomersPage.test.tsx` | Modified — next/navigation mock |
| `apps/web/src/__tests__/batch_plp_fix_4/checklist_add_customer_deep_link.integration.test.tsx` | Created — 3 tests |
| `apps/web/src/__tests__/batch_plp_fix_4/customer_form_validation_phone.integration.test.tsx` | Created — 4 tests |
| `apps/web/src/__tests__/batch_plp_fix_4/quote_unit_price_entry.integration.test.tsx` | Created — 3 tests |
| `apps/web/src/__tests__/batch_fe_b18/customerList.integration.test.tsx` | Modified — next/navigation mock |
| `apps/web/__tests__/batch_beta_v1_b3/customers.test.tsx` | Modified — next/navigation mock |
| `apps/web/src/features/settings/components/__tests__/BillingContactForm.test.tsx` | Modified — E.164 payload assertion |
| `apps/web/src/__tests__/batch_stripe_connect_1_c/payment-method-settings.integration.test.tsx` | Modified — E.164 payload assertion |
| `apps/web/src/__tests__/batch_c_b16/settings-website.integration.test.tsx` | Modified — formatted display assertion |

#### Tests Added / Updated
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `packages/ui/src/phone-input/web/__tests__/PhoneInput.test.tsx` | Unit (new) | 16 | ✅ |
| `apps/web/src/features/customers/components/__tests__/CustomerForm.test.tsx` | Unit (updated) | 25 (was 20, +5) | ✅ |
| `apps/web/src/features/quotes/components/__tests__/LineItemEditor.test.tsx` | Unit (updated) | 9 (was 6, +3) | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_4/checklist_add_customer_deep_link.integration.test.tsx` | Integration (new) | 3 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_4/customer_form_validation_phone.integration.test.tsx` | Integration (new) | 4 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_4/quote_unit_price_entry.integration.test.tsx` | Integration (new) | 3 | ✅ |

#### Notes
- `pnpm sync-api-types`: N/A per design §G Q6 — purely UI, no new/modified hooks, no contract change. Not run.
- No hand-written `useMemo`/`useCallback`/`React.memo` in new code (rules §32). The pre-existing `useMemo` in `CustomersPage.tsx` was left untouched (routed to BE-TESTS-MAINT per design).
- Zod v4 top-level `z.email()` used (rules §34); no `z.string().email()`.
- WCAG 2.2 AA: inline email error is non-color-only (text + `aria-invalid` + `aria-describedby`); paste works on PhoneInput; ≥24px targets preserved; modal focus behavior unchanged.
- FIX4-BE-01 handed off to the next Python batch — `mark_first_customer` wiring + `mark_catalog_setup` audit.
- Deploy note: pure FE deploy — no backend dependency, no migration, no deploy-order constraint.
