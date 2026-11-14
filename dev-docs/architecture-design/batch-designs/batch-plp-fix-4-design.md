# Batch Design: PLP-FIX-4 — Checklist Add-Customer Route + Email/Phone Validation + Unit-Price Input (Issues 7, 10, 11)

**Batch**: PLP-FIX-4 (frontend web + one non-blocking companion BE task)
**Version**: 1.0
**Date**: 2026-09-02
**Author**: Pilot Architect
**Status**: Approved for prompt authoring
**Bug report**: `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` — Issues 7, 10, 11 (7a root-caused at design time)
**Predecessor**: `batch-plp-fix-3-design.md` (closed ✅ 2026-09-02)
**Prompt**: `batch-plp-fix-4-react-engr-prompt.md`
**Platform**: Web only (`apps/web`) + shared `packages/ui` (one new component). No backend contract change; `pnpm sync-api-types` N/A (no new/modified hooks — see §G Q6).

---

## Scope Statement

Three founder-path form/navigation defects from Tom's 2026-09-02 prod testing:

1. **Issue 7** — The dashboard checklist's "Add customer →" anchor routes to `/customers/new`, which collides with the `/customers/[id]` dynamic segment (id `"new"`) and renders a customer-detail load instead of a create flow (same collision class as Issue 3's `/jobs/new`, fixed in PLP-FIX-2). **Design-time finding (7a)**: `mark_first_customer()` has **zero production callers** — the `first_customer_added` checklist flag never flips, so the widget would sit at "Add your first customer" forever even after customers exist. The flag wiring ships as a non-blocking companion BE task (§6-pattern).
2. **Issue 10** — `CustomerForm.tsx` accepts any string as email (`type="email"` with no explicit validation or inline error), and none of the **seven** web `type="tel"` fields format or normalize phone input. Fix: entry-time email validation (Zod v4 `z.email()`, inline non-color-only error, submit blocked when invalid) + one shared US phone input (digits-in, progressive `(XXX) XXX-XXXX` display, E.164 out) applied app-wide.
3. **Issue 11** — The Unit Price inputs in `LineItemEditor.tsx` (persisted-row + add-row) derive their `value` from cents with `.toFixed(2)` **on every render** while `onChange` re-parses via `parseCentInput` — each keystroke round-trips through reformatting, so decimals can't be entered and backspaced characters regenerate. Fix: raw-string state while editing + parse-and-format (`X.XX`) on blur, exactly Tom's requested behavior. Quantity already accepts decimals correctly — untouched.

**Explicitly out of scope**: RHF/Zod-resolver rewrite of `CustomerForm` (entry validation rides the existing `useState` pattern); the pre-existing `useMemo` at `CustomersPage.tsx` (React Compiler cleanup → BE-TESTS-MAINT); quantity input changes; mobile (`apps/mobile`) phone fields (no reported issue; the new util is web-first — mobile adoption is a later batch); `mark_catalog_setup` wiring is verified-but-not-guaranteed (companion BE task checks it — §G Q4); no new pages/modals; §1.5 designer gate N/A (§H).

---

## A. Input Read Summary

| Input | What it provided | Read |
|---|---|---|
| `PLP-testing-bugs-2026-09-02.md` Issues 7/10/11 | Symptoms + verified first-pass evidence | ✅ |
| `types.ts` (onboarding) | `firstCustomerAdded` item: `actionRoute: "/customers/new"` (line 138) — the collision | ✅ |
| `ChecklistItem.tsx` | Action renders as plain `<a href>` — config-only change, no component change | ✅ |
| `CustomersPage.tsx` | `showCreate` state + two `CreateCustomerModal` render sites (172, 275); no `useSearchParams` today | ✅ |
| `CreateCustomerModal.tsx` + `CustomerForm.tsx` | Existing modal+form reused for the fix; email `type="email"` no validation (195-203); mobile_phone `type="tel"` no mask (211-214); DLC-1 attestation gate present | ✅ |
| Phone inventory grep (`type="tel"` in `apps/web/src`) | **7 fields**: `app/signup/phone/page.tsx`, `components/settings/messaging/BrandRegistrationForm.tsx`, `features/settings/components/BillingContactForm.tsx`, `features/sms-compliance/components/TenantDlcProfileForm.tsx`, `features/tenant-site/components/TenantSiteSettingsForm.tsx`, `features/account-settings/components/ProfileSettingsForm.tsx`, `features/customers/components/CustomerForm.tsx` | ✅ |
| `packages/ui/src` grep (Phone/mask) | **No existing PhoneInput/mask component** — component-existence check passed (Rule 7); house convention for platform splits exists (`mfa-enrollment-wizard/web/`) | ✅ |
| `onboarding_service.py` + caller grep | `mark_first_customer` defined + idempotent; **callers = tests only** → 7a is real | ✅ |
| `LineItemEditor.tsx` | `parseCentInput` (68-70), updater (128-131), persisted-row input (312-321), add-row input (428-437) | ✅ |
| `frontend/react-engr-std-prompt-inclusions.md` | Full 1002-line read — Quick Reference §16 order, §6 companion-BE pattern, §9 tests, §10 gate | ✅ |
| `pilot-architect-methods.md` §3 | Design workflow (A–I) | ✅ |

---

## B. Migration Plan

**None** — zero DB/schema/seed changes. (The companion BE task FIX4-BE-01 is a code wiring change, no migration.)

---

## C. Execution Order

| # | Step | Why this order |
|---|---|---|
| 1 | Pre-work: baseline (`pnpm --filter web test` + `@pilot/ui test`), file reads, endpoint/param grep | Known-good counts first |
| 2 | STEP 1 — `formatUsPhone` util + `PhoneInput` (packages/ui) + barrel export + unit tests | Foundation component; everything else consumes it |
| 3 | STEP 2 — `CustomerForm`: email validation + `PhoneInput` for mobile_phone (preserves DLC-1 attestation gate) | Highest-traffic form; validates the component in its hardest consumer (create + inline-edit reuse) |
| 4 | STEP 3 — Roll `PhoneInput` into the other 6 tel fields (per-field E.164 expectation verified against each backend consumer) | Mechanical once STEP 2 proves the pattern |
| 5 | STEP 4 — Issue 11: Unit Price raw-string editing + format-on-blur (both inputs) | Independent; quote surface |
| 6 | STEP 5 — Issue 7b: `actionRoute` → `/customers?add=1`; CustomersPage opens modal on the param + clears it on close | Navigation fix last (smallest) |
| 7 | STEP 6 — Tests: new/updated unit tests + `__tests__/batch_plp_fix_4/` integration specs (3) | Lock-in |
| 8 | Companion BE task documented for Python handoff (FIX4-BE-01) + Phase 2 full canonical gate | Non-blocking by design |

---

## D. New API Endpoints

**None.** All work consumes existing endpoints (`GET /api/v1/onboarding/checklist`, `POST /api/v1/customers`, quote-line POSTs). No hook signature changes.

---

## E. Pattern Reuse Decisions

| Pattern | Source | Application |
|---|---|---|
| Modal-swap for dynamic-segment collisions | PLP-FIX-2 Issue 3 (`JobFormModal.prefilledCustomerId`) | Issue 7b mirrors it: never navigate to `/[entity]/new`; land on the list page + open the existing create modal (here via `?add=1` deep-link, since the dashboard is a different page) |
| `RoleGate` | `@pilot/ui/role-gate` | CustomersPage modal branches unchanged; PhoneInput carries no RBAC |
| Non-color-only form errors + `aria-invalid`/`aria-describedby` | WCAG 2.2 AA (rules §36) | Email + phone inline errors follow it; ≥24px targets preserved |
| Zod v4 top-level helpers (rules §34) | `z.email()` **without** a RHF rewrite — `z.email().safeParse(value)` at the field level, matching the form's existing `useState` pattern | CustomerForm email |
| Companion Backend Tasks (inclusions §6) | Non-blocking handoff | FIX4-BE-01 checklist-flag wiring — FE ships on existing GET + MSW |
| No hand-memoization (rules §32) | React Compiler | New code is plain; the pre-existing `useMemo` in CustomersPage stays untouched (routed to BE-TESTS-MAINT) |

---

## F. Shared Module Interfaces

### F.1 `packages/ui/src/phone-input/` (new — one component + one util, web-first)

```typescript
// formatUsPhone.ts — pure, platform-agnostic
/** Digits-in helpers: strip non-digits, drop a leading US "1" when 11 digits. */
export function normalizeUsPhoneDigits(raw: string): string;   // ≤10 digits
export function formatUsPhoneDisplay(digits: string): string;  // progressive "(XXX) XXX-XXXX"
export function usPhoneToE164(digits: string): string | null;  // "+1XXXXXXXXXX" | null when not 10 digits

// web/PhoneInput.tsx — DOM input wrapper
interface PhoneInputProps {
  id: string;
  value: string;                    // E.164 ("+1…"), 10 digits, or "" — all tolerated on mount
  onChange: (e164: string | null) => void;  // emits E.164 when 10 digits, null when cleared/partial
  onBlur?: () => void;
  disabled?: boolean;
  className?: string;               // caller passes the existing INPUT_CLASS — visual parity
  autoComplete?: string;            // default "tel-national"
  placeholder?: string;             // default "(555) 123-4567"
  ariaInvalid?: boolean;
  ariaDescribedby?: string;
}
```

Behavior: internal draft = digits only (max 10 after normalize); display = `formatUsPhoneDisplay` **progressively as you type** (paste-friendly — WCAG 2.5.3/paste allowed); backspace works naturally (re-formats from digits); on blur with 10 digits → display formatted + emit E.164; partial on blur → emit `null` (parent decides required-vs-optional; existing per-field semantics unchanged). Barrel export added to `packages/ui/src/index.ts` (engineer reads it first; follows existing export style).

### F.2 CustomerForm email validation (field-level, no RHF rewrite)

`const emailError = email.trim() && !z.email().safeParse(email.trim()).success ? "Enter a valid email address." : null` — inline `<p id="customer-email-error" class="text-fault-600 text-sm mt-1">` + `aria-invalid` + `aria-describedby`; submit disabled when `emailError` is set (OR-ed into the existing `isSubmitDisabled` logic — DLC-1 attestation gate preserved exactly).

### F.3 LineItemEditor Unit Price (both inputs)

Per-row editing state: `const [priceDraft, setPriceDraft] = useState<{ key: string; raw: string } | null>(null)`. `onFocus` → seed `raw` from the current cents (`(cents/100).toFixed(2)`); `onChange` → keep `raw` as typed (allow digits + at most one `.`); `onBlur` → `parseCentInput(raw)` → write cents to the line → clear the draft → display reverts to `(cents/100).toFixed(2)`. Value shown: `priceDraft?.key === rowKey ? priceDraft.raw : formatted`. Same pattern for the add-row (`addingLine`) with a single-row draft. Quantity input untouched.

### F.4 Companion Backend Task (Python handoff — non-blocking)

**FIX4-BE-01 — wire `mark_first_customer` (+ audit `mark_catalog_setup`)**: call `services.onboarding_service.mark_first_customer(db, tenant_id)` from the customer-create `_impl` (auth + `/test` paths both flow through it — verify), after successful commit; idempotent by design. Regression test: create customer via endpoint → `GET /onboarding/checklist` (or service read) shows `first_customer_added=True`. While there: grep `mark_catalog_setup` callers — if also test-only, wire it into the catalog/pricebook create path the same way (report either way in the BE completion summary). Handed to the Python Engineer after this batch (no FE dependency — the widget already reads the checklist endpoint; MSW covers dev).

---

## G. Open Questions Resolved

**Q1 — Why `?add=1` deep-link instead of hoisting `CreateCustomerModal` onto the dashboard?**
The checklist widget is on the dashboard; the modal + its mutation/query invalidation live in the customers feature. Hoisting would duplicate modal state and cache wiring on a second page for zero UX gain — the customer list is the correct destination after creation anyway (founder sees the new row land). `/customers?add=1` keeps one modal instance, mirrors the PLP-FIX-2 modal-swap precedent, and the anchor stays a plain href (SSR-friendly). On close, the param is cleared (`router.replace("/customers")`) so refresh doesn't re-pop the modal.

**Q2 — One shared `PhoneInput` vs. per-form local masks?**
Seven identical fields is the textbook shared-component case; per-form copies would drift. Placement `packages/ui/src/phone-input/` with a `web/` subfolder follows the `mfa-enrollment-wizard/web/` house split (RN variant can come later without a breaking move). Pure util (`formatUsPhone.ts`) is platform-agnostic and shared from day one.

**Q3 — E.164 storage vs. display masking — any data risk?**
None. All seven fields already expect/store E.164-ish strings (e.g. BrandRegistrationForm placeholder `+13025551234`; DLC support phone; Telnyx-facing paths). `PhoneInput` emits `+1XXXXXXXXXX` — identical shape to what those backends receive today. Each STEP 3 field's submit path is re-verified by the engineer (the two carrier forms BrandRegistrationForm + TenantDlcProfileForm get explicit attention — TCR verbatim formats). No DB migration, no backfill: existing stored values render fine on mount (E.164 in → digits → display).

**Q4 — Is `mark_catalog_setup` also unwired?**
Unknown at design time (grep confirmed only `mark_first_customer`). FIX4-BE-01 audits it — same service, same one-call fix if missing. Not FE-blocking either way.

**Q5 — `z.email()` without RHF — deviation from rules §34?**
No. §34 mandates Zod v4 idioms for form validation and bans v3 carryover; it does not mandate RHF adoption in a form that predates the convention. The calibrated fix uses `z.email().safeParse` at the field level (top-level v4 helper — compliant) and leaves the RHF rewrite for a future form-consolidation batch. Re-litigating this is out of scope.

**Q6 — `pnpm sync-api-types` required?**
N/A per inclusions §3 ("unless batch is purely UI with no new hooks"): no new/modified hooks, no contract change (the companion BE task adds no endpoint — it wires a service call). Engineer runs it anyway only if a type drift surfaces during the work, and says so in the Completion Summary.

**Q7 — `first_customer_added` display state vs. Tom's tenant?**
Tom's prod tenant has zero customers, so the widget correctly sits at "Add your first customer" today — the route fix (7b) is what he needs now; the flag wiring (7a) prevents the *next* trap (checklist never advancing). Both documented so he isn't surprised when the item persists until FIX4-BE-01 ships.

**Q8 — `CustomersPage` has two `CreateCustomerModal` instances (lines 172, 275)?**
Verified: two render branches (likely RoleGate/empty-state splits) sharing one `showCreate` state. The `?add=1` effect sets that single state — both branches benefit; no dedup refactor in scope.

---

## H. Surface Mockup Reference

**§1.5 designer gate: N/A** — identical justification to PLP-FIX-2: every change is behavior-level on **existing** surfaces (existing checklist anchor, existing modal, existing form inputs, existing editor table). No new surfaces, no new top-level UX patterns, no visual redesign; the phone mask + inline errors compose the locked WCAG/§36 conventions rather than inventing new ones. No mockups required.

Surfaces touched (all `apps/web` authenticated): Dashboard checklist widget · `/customers` list (+ `?add=1` modal open) · CreateCustomerModal/CustomerForm (create + inline-edit) · quote builder + quote-detail draft editor (Unit Price inputs) · 6 settings/signup phone fields.

## I. Component Manifest

| Component | Destination | Establishing batch | Notes |
|---|---|---|---|
| `formatUsPhone.ts` (util) | `packages/ui/src/phone-input/` | **PLP-FIX-4 (new)** | Pure; platform-agnostic |
| `PhoneInput.tsx` | `packages/ui/src/phone-input/web/` | **PLP-FIX-4 (new)** | Barrel export in `packages/ui/src/index.ts` (Rule 7/§8.3); RN variant deferred |
| `EmailFieldError` inline `<p>` | inside `CustomerForm.tsx` | PLP-FIX-4 (inline, not shared) | Follows existing form's error style (`text-fault-600`) — not a new component |
| No other new components | — | — | Everything else modifies existing files |

**Component-existence check**: `packages/ui/src` grep confirmed no existing phone/masked input (§A). No orphan components vs. designer manifests (N/A gate).
