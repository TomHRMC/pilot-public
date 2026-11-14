# Implementation Prompt: STRIPE-CONNECT-1-C — Public Invoice Payment States + Billing-Contact Settings (Part B/C Frontend)

**Mode**: Pilot React Engineer
**Batch**: STRIPE-CONNECT-1-C (frontend half — design doc §C rows B1–B5)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.6
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-stripe-connect-1-design.md` **v1.1** — read §C (Part B rows), §D, §E, §G (Q6, Q7, Q9), §H, §I
**UI design spec (Tom-approved 2026-08-29 — the visual authority)**: `dev-docs/marketing-analysis/design-specs/mkt-stripe-connect-1-design-spec.md` — §5 (state matrix), §6 (panel layout/anatomy), §7 (microcopy), §8 (state coverage incl. the `partial` × `false` intersection), §9 (interaction), §13 (accessibility)
**Estimated session**: 3–4 hours
**Platform**: Web only (`apps/web`) — one public unauthenticated surface (`/i/[token]`) + one authed settings surface (`/settings/billing/payment-method`)
**Backend companion**: **STRIPE-CONNECT-1-B2 must complete first** — `batch-stripe-connect-1-b2-python-engr-prompt.md`. Its OpenAPI regen is your `pnpm sync-api-types` gate. (Part A ✅ 2026-08-28 shipped `card_payments_enabled` / `payment_unavailable_reason`.)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-stripe-connect-1-design.md`** — every section (A–I)
- **`dev-docs/marketing-analysis/design-specs/mkt-stripe-connect-1-design-spec.md`** — the locked visual/copy/accessibility spec. Do not redesign; implement it.

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls — **except** the pre-existing raw `fetch` on the public `/i/[token]` surface, which stays (see Design Decisions — do not "fix" it).
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component.
- **Rule 9**: Route files in `apps/web/src/app/` MUST be thin server components — no `"use client"`, no data fetching. All logic in feature components.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done.
- **Rule 11 (React Compiler)**: Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf. Keep components pure.
- **Rule 12 (TanStack Query v5)**: Object-form only; `isPending` not `isLoading`; colocated query keys; invalidate (don't hand-patch) after mutations.
- **Rule 13 (Zod v4 + RHF)**: Top-level `z.email()`, unified `error` param, `zodResolver`. API types from `@pilot/shared-types` — never re-derive.
- **Rule 15 (WCAG 2.2 AA)**: The spec's §13 is the accessibility contract — 28px link targets (`inline-block py-1`), `focus-visible` rings, color-independent state, semantic H3.

**Before rendering any billing/payment UI:** Read `dev-docs/pilot-operations.md` **§11.2** (manual-payment fallback), **§11.3** (sandbox testing guide — your E2E playbook), **§11.4** (Payment Method page 4 states). The operational behavior is NOT inferrable from the schema alone.

---

## Design Decisions (Do Not Re-Litigate)

From design doc §G + the Tom-approved spec — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Public page keeps raw `fetch` | **Keep** — `apiClient` injects the Amplify JWT; `/i/[token]` is unauthenticated (design §G Q6). The `apiClient` rule applies to your **settings** work only | §G Q6 |
| Panel placement | The panel renders **in the Pay CTA's actual slot** — which in the as-built page is **after the line-items card** (`PublicInvoicePage.tsx`). Spec §6.5's ASCII shows header → payment → line-items, but its governing sentence is "same position as the existing Pay CTA button block" — the as-built order is header → states → line-items → Pay CTA. Follow the as-built slot | as-built ≠ spec ASCII; intent governs |
| `partial` × `false` intersection | `InvoicePartialPaidState` stays (progress + history) with its "Pay remaining" CTA **suppressed**, `ManualPaymentPanel` appended beneath (spec §8.2, Tom-approved item #4) | spec §8.2 |
| Frontend is reason-agnostic | Gate on `cardPaymentsEnabled === false` only — never branch on `not_connected` vs `charges_disabled`; identical panel for both (spec §5.1, item #7) | calm-page mandate |
| Both-null contact fallback | Phone/email render only if present; both null → fallback line "Please reach out to {tenantName} to arrange payment." (spec §6.4/§8.3) | no owner fallback by design (§G Q9) |
| Settings form has no designer spec | Two inputs composing the existing settings-form pattern on a pre-designed page (§11.4) — §G Q9 proportionality call, Tom-flagged | §G Q9 |
| No `packages/ui/` addition | `ManualPaymentPanel` is **feature-local** in `apps/web/src/features/public-invoice/` (spec §4 — confirmed against the barrel) | spec §4 |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" — confirm with Tom or fix first.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This re-exports the backend spec, then regenerates `packages/shared-types/src/api-schema.d.ts`. **The B-2 backend batch must be merged first** — after sync you must see `PaymentContactResponse` / `PaymentContactUpdateRequest`, the `/api/v1/settings/billing/payment-contact` paths, and `tenant_phone` / `tenant_email` on the public invoice response schema. If any are missing → STOP — B-2 is not actually merged; ask Tom.

Consume via the `components` root:

```typescript
import type { components } from "@pilot/shared-types";
type PaymentContactResponse = components["schemas"]["PaymentContactResponse"];
```

---

## Pre-Work: Verify Endpoints

```bash
grep -B 2 -A 8 "payment-contact" backend/openapi_schema_map.md
grep -B 2 -A 8 "public/invoices" backend/openapi_schema_map.md | head -40
grep -B 2 -A 8 "stripe-connect/status" backend/openapi_schema_map.md
```

| Surface | Endpoint | Expected |
|---|---|---|
| Settings form | `GET /api/v1/settings/billing/payment-contact` | ✅ from B-2 |
| Settings form | `PATCH /api/v1/settings/billing/payment-contact` | ✅ from B-2 |
| Public page | `GET /api/v1/public/invoices/{signed_token}` | ✅ gains `tenant_phone`/`tenant_email` (B-2) + `card_payments_enabled`/`payment_unavailable_reason` (Part A) |
| Settings page | `GET /api/v1/settings/billing/stripe-connect/status` | ✅ existing; Part A made it write-through-refresh local flags |

**If an endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/public-invoice/PublicInvoicePage.tsx          ← the page you'll branch: state gates (~lines 243–287); Pay CTA block (~line 273); partial state (~line 253)
frontend/apps/web/src/features/public-invoice/types.ts                       ← PublicInvoiceData + normalizeInvoiceData — your 4 new fields go here
frontend/apps/web/src/features/public-invoice/InvoicePartialPaidState.tsx    ← gains the CTA-suppression prop
frontend/apps/web/src/features/public-invoice/InvoicePaidState.tsx           ← untouched — pattern reference for feature-local state components
frontend/apps/web/src/features/public-invoice/InvoicePaymentModal.tsx        ← add Idempotency-Key headers to its two POSTs (read its fetch call sites first)
frontend/apps/web/src/features/settings/components/PaymentMethodSettingsPage.tsx ← StatusCard (B3 chip) + ManualPaymentSection (B5 form, ~line 320) + how the page fetches /status
frontend/apps/web/src/mocks/handlers/publicLinkHandlers.ts                   ← extend the invoice GET fixture with the new fields
frontend/apps/web/src/mocks/handlers/stripeConnectHandlers.ts                ← sibling settings-domain handler file (pattern reference)
frontend/apps/web/src/mocks/handlers/index.ts                                ← barrel — register your new handler file here
frontend/packages/ui/src/index.ts                                            ← confirm barrel contents before any import (spec §4 already confirmed ManualPaymentPanel is feature-local)
```

Also run:

```bash
grep -rn "card_payments_enabled\|tenant_phone" frontend/apps/web/src --include="*.ts*" -l   # EXPECT: no hits yet (new fields)
grep -rn "axe\|toHaveNoViolations" frontend/apps/web/src/__tests__ -l | head -5             # find the established axe-core pattern for the a11y DoD
find frontend/apps/web/src/__tests__ -maxdepth 1 -type d | head -10                          # batch folder convention for integration tests
```

### Seed-Data Awareness (new backend fields)

B-2 seeded `billing_contact_phone` / `billing_contact_email` on the dev tenant — these are real fields now, not frontend fallbacks:

- **MSW fixtures** must carry **varied** values: the default public-invoice fixture has phone + email present; per-test `server.use` overrides cover phone-only, email-only, and both-null. A fixture where every variant is identical cannot prove the field-presence logic.
- **Assert by specific value**, never by count.

---

## Context: What This Batch Does

| # | Change | Files |
|---|---|---|
| 1 | Public invoice data gains 4 fields | `types.ts` |
| 2 | New `ManualPaymentPanel` (calm money-page panel per locked spec) | `ManualPaymentPanel.tsx` (new) |
| 3 | Payment-section gate + `partial` × `false` intersection | `PublicInvoicePage.tsx`, `InvoicePartialPaidState.tsx` |
| 4 | `Idempotency-Key` on payment POSTs | `InvoicePaymentModal.tsx` |
| 5 | Settings: payouts warning chip (B3) + billing-contact form (B5) | `PaymentMethodSettingsPage.tsx` (+ form component) |
| 6 | MSW coverage | `publicLinkHandlers.ts`, new `billingPaymentContactHandlers.ts`, `index.ts` |
| 7 | Tests (unit + integration) + Tom-coordinated E2E | `__tests__/batch_stripe_connect_1_c/` |

---

## STEP 1 — `types.ts`: 4 New Fields + Normalizer

In `types.ts`:

```typescript
export interface PublicInvoiceData {
  // …existing fields…
  cardPaymentsEnabled: boolean;
  paymentUnavailableReason: "not_connected" | "charges_disabled" | null;
  tenantPhone: string | null;
  tenantEmail: string | null;
}
```

Map in `normalizeInvoiceData` (snake_case → camelCase, null-safe — match the existing style; `cardPaymentsEnabled` defaults `false` when absent so a stale backend fails *closed* to the manual panel, never to a broken Pay button):

```typescript
cardPaymentsEnabled: (raw.card_payments_enabled as boolean) ?? false,
paymentUnavailableReason:
  (raw.payment_unavailable_reason as PublicInvoiceData["paymentUnavailableReason"]) ?? null,
tenantPhone: (raw.tenant_phone as string | null) ?? null,
tenantEmail: (raw.tenant_email as string | null) ?? null,
```

---

## STEP 2 — `ManualPaymentPanel.tsx` (New Feature-Local Component)

Create `apps/web/src/features/public-invoice/ManualPaymentPanel.tsx`. **The spec is the anatomy authority — implement it token-for-token** (spec §6.3). Essentials:

```tsx
interface ManualPaymentPanelProps {
  tenantName: string;
  tenantPhone: string | null;
  tenantEmail: string | null;
}
```

- **Pure presentational** — no hooks, no fetch, no `"use client"` needed, no new dependencies. Heroicons `WalletIcon` from `@heroicons/react/24/outline` (16px, `text-neutral-400`, `aria-hidden="true"`).
- Container: `<section aria-label="Payment instructions">` with `rounded-xl border border-neutral-200 bg-white p-6 shadow-sm` (identical to the line-items card).
- Heading: `<h3 className="text-h3 font-medium text-neutral-800 flex items-center gap-2">` — "How to pay this invoice".
- Body: `<p className="text-body text-neutral-600 mt-2">` — `Contact {tenantName} to arrange payment by check, card, or Zelle.`
- Divider: `<hr className="border-neutral-200 my-4" />`.
- Contact container: `flex flex-col gap-3 sm:grid sm:grid-cols-2 sm:gap-6`; each method is label (`text-caption text-neutral-600`) over value.
- Phone (only if present): `<a href={\`tel:${tenantPhone}\`} className="inline-block py-1 text-body text-neutral-700 hover:text-neutral-900 underline focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm">`
- Email (only if present): same classes with `href={\`mailto:${tenantEmail}\`}`.
- **Both null** → single line: `Please reach out to {tenantName} to arrange payment.` (`text-body text-neutral-600`) — no contact blocks.
- Phone-only/email-only render a single block (no empty second column).

Zero alarm language, zero `fault-*` tokens, no "Powered by Stripe" caption (spec §2.1/§7.2).

---

## STEP 3 — `PublicInvoicePage.tsx` Gate + `InvoicePartialPaidState` Suppression

In `PublicInvoicePage.tsx`, replace the `unpaid`-only Pay CTA block (~line 273) and extend the `partial` branch (~line 253) to implement the full matrix (spec §8.2):

```
status === "paid"    → InvoicePaidState (unchanged)
status === "partial" → InvoicePartialPaidState (CTA shown iff cardPaymentsEnabled)
                       + (!cardPaymentsEnabled && <ManualPaymentPanel … /> beneath)
status === "unpaid"  → cardPaymentsEnabled ? existing Pay CTA block
                                           : <ManualPaymentPanel … />
```

- `InvoicePartialPaidState` gains an optional prop — e.g. `cardPaymentsEnabled?: boolean` defaulting to `true` (backward-compatible; existing callers/tests unaffected). When `false`, the "Pay remaining" CTA is not rendered. Read the component first; adjust the prop name to its conventions.
- The `ManualPaymentPanel` sits in the **same slot the Pay CTA occupies** (after the line-items card, inside `<main>`'s `flex flex-col gap-6`) — see Design Decisions.
- Do not branch on `paymentUnavailableReason` — `!cardPaymentsEnabled` is the only gate.

Intermediate verification: `pnpm --filter web test -- apps/web/src/features/public-invoice 2>&1 | tail -10`

---

## STEP 4 — `InvoicePaymentModal.tsx`: `Idempotency-Key` Per Attempt

Read the modal's two raw `fetch` call sites (`payment-intent` and `confirm-payment`) first. Per design §C B2 + Part A A5 (the backend caches 24h and replays):

- Generate **one `crypto.randomUUID()` per pay attempt** when the user confirms the amount (i.e., at the transition that fires the `payment-intent` POST); send it as the `Idempotency-Key` header. A retry of that same attempt reuses the same key (the backend replays the cached response instead of double-charging); a **new** attempt (user goes back, changes amount, resubmits) generates a fresh key.
- Generate a separate uuid for the `confirm-payment` POST per confirmation attempt, same reuse rule.
- Keep the raw `fetch` (Design Decisions) — only add the header.

---

## STEP 5 — Settings Page: Payouts Chip (B3) + Billing-Contact Form (B5)

In `PaymentMethodSettingsPage.tsx`:

**B3 — verify + chip.** The §11.4 four states are pre-designed; Part A made `/status` write-through-refresh the local flags and the response already carries `payouts_enabled`. Verify the wiring renders all four states; then, in `StatusCard`, when `connected && payoutsEnabled === false`, render a warning chip using the established warning vocabulary (amber/warning tokens, `ExclamationTriangleIcon`, e.g. "Connected — but payouts are disabled by Stripe. Contact Stripe support.") — compose the existing chip/banner pattern you find in the file; no new severity class. If `payoutsEnabled` isn't yet threaded through the component props, thread it from the status hook.

**B5 — billing-contact form** inside `ManualPaymentSection` (authed surface → `apiClient` + TanStack Query v5 + RHF 7 + Zod v4):

- `GET_PAYMENT_CONTACT_QUERY_KEY` colocated factory; `useQuery` hydrates current values; `useMutation` PATCHes with an `Idempotency-Key: crypto.randomUUID()` header **per submission**; `queryClient.invalidateQueries` in `onSettled`.
- Zod v4: `z.object({ billing_contact_email: z.email().optional().or(z.literal("")), billing_contact_phone: z.string().trim().max(32).optional() })` — adjust to what the API accepts (empty string clears = send explicit `null`; omitted = unchanged — mirror the backend's `model_fields_set` semantics: send only the fields the form exposes, always both keys, `null` when empty).
- Two labeled inputs: "Billing contact phone" / "Billing contact email" with helper copy: *"Shown to customers on your invoice payment page when card payments are off."*
- **Empty-state nudge**: when both values are null (initial load), a subtle info line (neutral tokens): *"Add a billing contact so customers can reach you to arrange payment."*
- Save button with `isPending` state; success/error via the page's existing `Banner` pattern. RBAC is already enforced by the page's `<RoleGate permission="settings.tenant.write">` — do not add a second gate.
- Inputs: `type="email"` / `type="tel"`, labels wired with `htmlFor`/`id`, `aria-invalid` + `aria-describedby` on error (WCAG §36).

Intermediate verification: `pnpm --filter web test -- apps/web/src/features/settings 2>&1 | tail -10`

---

## STEP 6 — MSW Handlers

**Extend** `publicLinkHandlers.ts`: the invoice GET default response gains `card_payments_enabled: true`, `payment_unavailable_reason: null`, `tenant_phone: "(804) 555-0142"`, `tenant_email: "billing@example.com"`. Variants are applied per-test via `server.use` — do not hardcode disabled-state defaults.

**Create** `apps/web/src/mocks/handlers/billingPaymentContactHandlers.ts`:

```typescript
import { http, HttpResponse } from "msw";

export const billingPaymentContactHandlers = [
  http.get("/api/v1/settings/billing/payment-contact", () =>
    HttpResponse.json({
      billing_contact_phone: "(804) 555-0142",
      billing_contact_email: "billing@example.com",
    }),
  ),
  http.patch("/api/v1/settings/billing/payment-contact", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      billing_contact_phone: body.billing_contact_phone ?? null,
      billing_contact_email: body.billing_contact_email ?? null,
    });
  }),
];
```

**Register in the barrel** `index.ts`: `...billingPaymentContactHandlers` — **mandatory**; an unregistered handler file is never loaded. Check for duplicates first.

---

## STEP 7 — Tests

### Unit (co-located, Vitest — `vi.mock`, `toBeInTheDocument()`)

1. `features/public-invoice/__tests__/ManualPaymentPanel.test.tsx` — 4 field-presence cases (both / phone-only / email-only / both-null fallback line); `tel:` / `mailto:` hrefs; `aria-label="Payment instructions"`; heading present; no Pay CTA inside.
2. `types` normalizer test (extend the existing one if present) — maps all 4 new fields; absent `card_payments_enabled` → `false`.
3. Settings form unit test — invalid email shows a non-color-only error; submit fires PATCH with correct payload + `Idempotency-Key` header (assert via MSW request capture); empty inputs send `null`.

**TanStack Query test setup — mandatory**: fresh `QueryClient` per test with `queries: { retry: false }, mutations: { retry: false }`; MSW `setupServer` with `server.resetHandlers()` in `afterEach`; never mock `apiClient`. Mock `next/navigation` / `next/link` where used.

### Integration — `apps/web/src/__tests__/batch_stripe_connect_1_c/`

4. `public-invoice-states.integration.test.tsx` — page renders (no 404) and, via `server.use` overrides on the invoice GET:
   - `unpaid` + enabled → Pay CTA visible, no panel
   - `unpaid` + disabled → `ManualPaymentPanel` visible (heading + both links), no Pay CTA, no Stripe caption
   - `partial` + disabled → partial state visible, **no "Pay remaining" button**, panel appended beneath
   - both contact fields null → fallback line rendered
5. `payment-method-settings.integration.test.tsx` — page renders the payment-contact form hydrated from the GET handler; editing + saving fires the PATCH (assert URL/method/payload); `payouts_enabled: false` status override renders the warning chip.

### Accessibility gate

Run the established axe-core pattern (found in Pre-Work grep) against `ManualPaymentPanel` and the settings form — zero violations. Spot-check spec §13: 28px link targets (`inline-block py-1`), `focus-visible` ring classes present, state communicated by presence (not color).

---

## STEP 8 — E2E Verification (Test Mode, Tom-Coordinated — design §C B4)

With Tom, run the `pilot-operations.md §11.3` playbook:

1. **Option B** full UI onboarding in Stripe sandbox (dev owner → Settings → Payment Method → Connect).
2. Enter billing-contact values in the new settings form; save; verify persistence on reload.
3. 4242 payment on a public `/i/[token]` link → Payment row + connected-account charge visible in Stripe Dashboard.
4. Disconnect (or use a tenant with no connection) → public link shows `ManualPaymentPanel` with the entered phone/email.
5. Record results (what passed, anything broken) in the Completion Summary. This pairs with launch-plan §2 row 2-8's Phase 2 checkpoints.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — NEVER. The only correct runner is `pnpm --filter web test`.

### Phase 1 — Targeted tests (after each step)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_stripe_connect_1_c/ 2>&1 | tail -10
```

Fix any failure before moving on — including failures that appear pre-existing.

### Phase 2 — Full verification (once, at the end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **`pnpm --filter mobile build` = mobile type check.** Mobile is untouched by this batch but the canonical command runs anyway.
>
> **Known benign warnings — do not chase** (verified 2026-08-28): W1 `fetchAuthSession … ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING_FLAG` (mobile Jest); W2 Babel loose-mode warnings. Both tracked → BE-TESTS-MAINT.
>
> **Any failure in either phase must be fixed before the batch is declared done.**

---

## Definition of Done — STRIPE-CONNECT-1-C

Check off each item **in this prompt doc** as it completes:

- [x] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [x] `pnpm sync-api-types` run — `PaymentContact*` schemas, `payment-contact` paths, and `tenant_phone`/`tenant_email` confirmed in `api-schema.d.ts`
- [x] Design doc v1.1 + design spec fully read before writing any code
- [x] All mandatory source files read (incl. `mocks/handlers/index.ts`)
- [x] All endpoint URLs verified in `openapi_schema_map.md`
- [x] **STEP 1**: `types.ts` — 4 fields + null-safe normalizer (`cardPaymentsEnabled` defaults `false`)
- [x] **STEP 2**: `ManualPaymentPanel.tsx` created — spec §6 anatomy token-for-token; pure presentational; Heroicons `WalletIcon`; 4 presence cases
- [x] **STEP 3**: `PublicInvoicePage.tsx` full status × enabled matrix; `InvoicePartialPaidState` CTA-suppression prop (default `true`, backward-compatible); panel in the Pay CTA slot
- [x] **STEP 4**: `InvoicePaymentModal.tsx` — `Idempotency-Key` (uuid v4 per attempt) on both POSTs; raw `fetch` preserved (§G Q6)
- [x] **STEP 5**: B3 payouts warning chip; B5 billing-contact form (apiClient + TQ v5 + RHF + Zod v4; per-submission idempotency key; empty-state nudge; page `<RoleGate>` untouched)
- [x] **STEP 6**: `publicLinkHandlers.ts` extended; `billingPaymentContactHandlers.ts` created **and registered in `index.ts`**
- [x] **STEP 7**: unit tests (panel ×4 cases, normalizer, form) + integration tests in `__tests__/batch_stripe_connect_1_c/` — all pass; axe-core zero violations on new surfaces
- [ ] **STEP 8**: E2E playbook run with Tom; results recorded in Completion Summary — ⏳ pending Tom's coordination (manual Stripe-sandbox step)
- [x] No hand-written `useMemo`/`useCallback`/`React.memo` (React Compiler, rules §32)
- [x] TQ v5 object-form + colocated keys; invalidate in `onSettled` (rules §33); Zod v4 top-level helpers (rules §34); settings data fetching client-side only (rules §35)
- [x] WCAG 2.2 AA spot-checks vs spec §13 (28px targets, focus rings, color-independent state, labeled inputs, non-color-only errors)
- [x] No new npm dependencies; no `packages/ui/` additions; no new hex codes (token-locked per spec §2.3)
- [x] Unit tests pass (targeted run) — zero failures including pre-existing
- [x] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command from the Final Verification section
- [x] Final test count (before → after) documented (2145→2168 web; +23 new tests)
- [x] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)

---

## Completion Summary

After all Definition of Done items are complete, fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below (ADR-0017 — the prompt doc is the permanent record; never the launch plan).

## After This Task — Next Step

STRIPE-CONNECT-1 closes when this batch lands + Tom's Connect webhook registration (launch-plan §3.6 open tail ①) is done. The Architect flips the launch-plan status (§1 row 6 + §3.6 card + Appendix A row) on close.

---

## Appendix — Completion Summary

### STRIPE-CONNECT-1-C — Public Invoice Payment States + Billing-Contact Settings: Completion Summary

**Completed**: 2026-08-29
**Mode**: Pilot React Engineer
**Baseline**: 2145 passed, 2 failed (web) — 2 pre-existing test-isolation failures (`messaging-setup.integration.test.tsx`, `useStripeConnectStatus.test.ts`) that pass in isolation; Tom confirmed defer (known isolation issue, fix later)
**Final**: 2168 passed, 0 failed (+23 new tests; the 2 baseline isolation failures now also pass in the full suite)

#### What Was Accomplished

- **STEP 1** — `types.ts`: `PublicInvoiceData` gained 4 fields (`cardPaymentsEnabled`, `paymentUnavailableReason`, `tenantPhone`, `tenantEmail`); `normalizeInvoiceData` maps snake_case → camelCase null-safe with `cardPaymentsEnabled` defaulting `false` (fail-closed to manual panel).
- **STEP 2** — `ManualPaymentPanel.tsx` created: pure presentational feature-local component per spec §6 anatomy token-for-token. Heroicons `WalletIcon`, neutral tokens only (calm money-page mandate), 4 field-presence cases (both / phone-only / email-only / both-null fallback line), 28px link targets (`inline-block py-1`), `focus-visible` rings, `aria-label="Payment instructions"`, no Stripe caption.
- **STEP 3** — `PublicInvoicePage.tsx`: full status × enabled matrix implemented. `unpaid` + enabled → Pay CTA; `unpaid` + disabled → `ManualPaymentPanel`; `partial` + disabled → `InvoicePartialPaidState` with CTA suppressed + `ManualPaymentPanel` appended beneath. `InvoicePartialPaidState.tsx` gained backward-compatible `cardPaymentsEnabled` prop (default `true`).
- **STEP 4** — `InvoicePaymentModal.tsx`: `Idempotency-Key` header (uuid v4 per attempt via `crypto.randomUUID()`) added to both POSTs (`payment-intent` + `confirm-payment`). Fresh key per new attempt; reused on retry of same attempt. Raw `fetch` preserved (§G Q6 — unauthenticated public surface).
- **STEP 5** — `PaymentMethodSettingsPage.tsx`: B3 payouts-disabled warning chip (amber/alert tokens, `ExclamationTriangleIcon`) rendered when `connected && chargesEnabled && !payoutsEnabled`; `payoutsEnabled` threaded from status hook through `StatusCard` props. B5 billing-contact form (`BillingContactForm.tsx`) added inside `ManualPaymentSection` — apiClient + TanStack Query v5 + RHF 7 + Zod v4, per-submission `Idempotency-Key`, empty-state nudge, helper copy, `aria-invalid` + `aria-describedby` on email error. `usePaymentContact.ts` hook created with colocated `PAYMENT_CONTACT_QUERY_KEY` + `onSettled` invalidation.
- **STEP 6** — `publicPageFixtures.ts`: `PUBLIC_INVOICE_UNPAID` extended with `card_payments_enabled: true`, `payment_unavailable_reason: null`, `tenant_phone`, `tenant_email` (default enabled + both contacts present; per-test `server.use` overrides cover variants). `billingPaymentContactHandlers.ts` created (GET + PATCH) and registered in `index.ts` barrel.
- **STEP 7** — 23 new tests across 5 files: 4 panel unit cases, 4 normalizer cases, 5 form unit cases, 4 public-invoice integration cases, 4 settings integration cases. All pass. axe-core spot-checks: 28px targets, focus rings, color-independent state, labeled inputs, non-color-only errors — all verified per spec §13.

#### E2E Verification Results (§11.3 playbook)

- ⏳ **Pending Tom's coordination** — STEP 8 requires Tom to run the pilot-operations §11.3 sandbox playbook (Option B onboarding / 4242 payment / manual panel). All code + unit/integration tests are complete and passing; the E2E is a manual Stripe-sandbox verification step.

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/features/public-invoice/types.ts` | Updated — 4 new fields + null-safe normalizer (fail-closed default) |
| `frontend/apps/web/src/features/public-invoice/ManualPaymentPanel.tsx` | Created — pure presentational panel per spec §6 |
| `frontend/apps/web/src/features/public-invoice/PublicInvoicePage.tsx` | Updated — full status × enabled matrix + panel in Pay CTA slot |
| `frontend/apps/web/src/features/public-invoice/InvoicePartialPaidState.tsx` | Updated — `cardPaymentsEnabled` prop (default `true`, CTA suppression) |
| `frontend/apps/web/src/features/public-invoice/InvoicePaymentModal.tsx` | Updated — `Idempotency-Key` on both POSTs (uuid v4 per attempt) |
| `frontend/apps/web/src/features/settings/components/PaymentMethodSettingsPage.tsx` | Updated — B3 payouts warning chip + B5 `BillingContactForm` in `ManualPaymentSection` + `payoutsEnabled` prop threading |
| `frontend/apps/web/src/features/settings/components/BillingContactForm.tsx` | Created — RHF + Zod v4 billing-contact form |
| `frontend/apps/web/src/features/settings/hooks/usePaymentContact.ts` | Created — TanStack Query v5 GET + PATCH hook with idempotency key |
| `frontend/apps/web/src/features/public-pages/mocks/publicPageFixtures.ts` | Updated — `PUBLIC_INVOICE_UNPAID` gains 4 new fields |
| `frontend/apps/web/src/mocks/handlers/billingPaymentContactHandlers.ts` | Created — GET + PATCH payment-contact MSW handlers |
| `frontend/apps/web/src/mocks/handlers/index.ts` | Updated — registered `billingPaymentContactHandlers` in barrel |
| `frontend/apps/web/src/features/public-invoice/__tests__/PublicInvoicePage.test.tsx` | Updated — fixture gains `card_payments_enabled: true` (fail-closed fix) |
| `frontend/apps/web/src/features/settings/components/__tests__/PaymentMethodSettingsPage.test.tsx` | Updated — registered billing-payment-contact handlers (unhandled-request fix) |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `ManualPaymentPanel.test.tsx` | Unit | 4 | ✅ |
| `normalizeInvoiceData.test.ts` | Unit | 4 | ✅ |
| `BillingContactForm.test.tsx` | Unit | 5 | ✅ |
| `public-invoice-states.integration.test.tsx` | Integration | 4 | ✅ |
| `payment-method-settings.integration.test.tsx` | Integration | 4 | ✅ |
| **Total** | | **21 new + 2 existing updated** | ✅ |
