# Implementation Prompt: SIGNUP-C — Signup Step 3 "Stay Informed" Screen (Web Frontend)

**Mode**: Pilot React Engineer
**Batch**: SIGNUP-C (Frontend half — runs AFTER the Python half)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md`
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-signup-c-design.md` — read every section (A–I)
**UI design spec**: `dev-docs/architecture-design/batch-designs/batch-signup-c-ui-design-spec.md` — **Tom-approved before you start** (authored by `pilot-web-ui-designer`)
**Estimated session**: 3–4 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: **SIGNUP-C Python half must be COMPLETE and deployed first** — `batch-signup-c-python-engr-prompt.md`. Your first Pre-Work step is `pnpm sync-api-types`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-signup-c-design.md`** — every section (A–I); esp. §D (endpoints), §H (surface), §I (component manifest)
- **`dev-docs/architecture-design/batch-designs/batch-signup-c-ui-design-spec.md`** — the pixel/token/WCAG spec you build to; **do not start if this is not Tom-approved**

Critical rules for this batch:

- **Rule 1.1**: Every endpoint must exist in `backend/openapi_schema_map.md` before you call it. If missing → STOP and ask Tom (means the Python half didn't ship).
- **Rule 1.3**: Run `pnpm sync-api-types` FIRST — all backend payload types come from `@pilot/shared-types`, never hand-written.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is banned for `/api/v1/...`. (Note: this signup flow is public/JWT-mixed — the existing pages already use `apiClient`; follow their pattern.)
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — `<LoadingState>`, `<ErrorState>` etc. already exist. The consent disclosure may reuse the existing customer-consent pattern.
- **Rule 9**: Route files (`app/signup/phone/page.tsx`) stay thin — logic lives in `features/signup/`.
- **Rule 11 (React Compiler §32)**: no hand-written `useMemo`/`useCallback`/`React.memo` for perf.
- **Rule 12 (TanStack Query v5 §33)**: object-form; `isPending` not `isLoading`.
- **Rule 13 (Zod v4 + RHF §34)**: `z.string().min(1)` for phone; top-level `z.email()`/`z.uuid()` where relevant; unified `error` param. Infer API payloads from `@pilot/shared-types`.
- **Rule 15 (WCAG 2.2 AA §36)**: ≥24×24px targets, allow paste, `focus-visible` rings, non-color-only errors, `prefers-reduced-motion` — the spec bakes these; the axe-core gate enforces them.

---

## Design Decisions (Do Not Re-Litigate — from design §G + ADR-0013)

| Decision | Outcome |
|---|---|
| Screen purpose | Reframe `/signup/phone` from "Verify phone" → **"Stay Informed"** (Pilot→owner account alerts). NOT tenant→customer SMS. |
| Phone field | **Required** (E.164-validated). No skip button. |
| Consent checkbox | **UNCHECKED by default**, toggleable, benefit-forward label (spec §). |
| After submit | Real **"reply YES" double-opt-in** confirmation sub-state — **replaces the fake 6-digit OTP grid** in `PhoneOtpSubscreen`. |
| Disclosure block | Full 10DLC CTA language (program name, message types, "Msg freq varies", "Msg & data rates may apply", STOP/HELP, Privacy Policy link) — this is the TCR consent screenshot. |
| Consent authority | The reply-YES seals consent server-side (webhook). The screen shows optimistic "Text sent — reply YES" then reflects verified via `/state` polling. |

---

## Pre-Work: Establish Regression Baseline
```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```
Record the count. Fix any pre-existing failure or confirm with Tom before starting.

## Pre-Work: Sync API Types
```bash
cd <repo>/frontend
pnpm sync-api-types
```
Consume types via the `components` root:
```typescript
import type { components } from "@pilot/shared-types";
```
> If this fails because an endpoint is missing → the Python half is not deployed. STOP and confirm with Tom. Do NOT build against MSW stubs for a batch whose backend is supposed to be live.

## Pre-Work: Verify Endpoints
```bash
grep -A 5 "phone/consent\|phone/send-optin\|/step3" backend/openapi_schema_map.md
```
| Hook / call | Endpoint | Verified |
|---|---|---|
| consent submit | `POST /api/v1/signup/{tenant_id}/phone/consent` | ☐ confirm |
| send opt-in text | `POST /api/v1/signup/{tenant_id}/phone/send-optin` | ☐ confirm |
| advance step | `PUT /api/v1/signup/{tenant_id}/step3` (phone required) | ☐ confirm |
| poll state | `GET /api/v1/signup/{tenant_id}/state` | ☐ confirm (existing) |

If any is missing → STOP and ask Tom.

## Pre-Work: Read These Source Files
```
frontend/apps/web/src/app/signup/phone/page.tsx                       ← the page you rewrite (currently fake OTP flow)
frontend/apps/web/src/features/signup/components/PhoneOtpSubscreen.tsx ← replace fake OTP with reply-YES confirm sub-state
frontend/apps/web/src/features/signup/types.ts                        ← WizardSignupState, stepToUrl, WIZARD_TENANT_ID_KEY
frontend/apps/web/src/app/signup/legal/page.tsx                       ← the prior step — pattern for state-guard + advance
frontend/apps/web/src/features/signup/components/WizardProgressBar.tsx ← reuse
frontend/apps/web/src/features/signup/components/LegalCheckboxGroup.tsx ← consent-checkbox pattern to mirror
frontend/packages/ui/src/index.ts                                     ← confirm existing components before creating SmsConsentDisclosure
frontend/apps/web/src/mocks/handlers/signupHandlers.ts                ← extend for the new endpoints (tests)
frontend/apps/web/src/mocks/handlers/index.ts                         ← register any new handler
```
```bash
grep -n "SmsConsentDisclosure\|ConsentDisclosure" frontend/packages/ui/src/index.ts frontend/apps/web/src -r
find frontend/apps/web/src/features/signup -name "*.tsx"
```

---

## Context: What This Batch Does

| Change | File |
|---|---|
| Rewrite step-3 page body → "Stay Informed" (required phone + unchecked consent + disclosure) | `app/signup/phone/page.tsx` (thin) → `features/signup/` component |
| New `SmsConsentDisclosure` (full 10DLC language, reuses existing disclosure pattern if present) | `features/signup/components/SmsConsentDisclosure.tsx` |
| Replace fake OTP grid with reply-YES confirmation sub-state | `features/signup/components/` (rename/replace `PhoneOtpSubscreen`) |
| Wire consent submit → `phone/consent` → (if consent) `phone/send-optin` → `PUT /step3` | feature component |
| Optimistic "Text sent — reply YES"; reflect verified via `/state` poll | feature component |

---

## STEP 1 — `SmsConsentDisclosure` component
Read `packages/ui/src/index.ts` first — if a customer-SMS disclosure already exists, reuse/adapt rather than duplicate (Rule 7). Build to the design spec: program name "Pilot for Trades", message types "account, billing & security alerts", "Message frequency varies", "Msg & data rates may apply", "Reply STOP to opt out", "HELP for help", clickable Privacy Policy → `https://www.pilotfortrades.com/legal/privacy`. Token-only, WCAG 2.2 AA per spec. Add `data-testid="signup-sms-consent-disclosure"` (this element is the TCR screenshot target).

Intermediate: `pnpm --filter web test 2>&1 | tail -6`

## STEP 2 — Rewrite the "Stay Informed" step
In `features/signup/`, build the step body (page.tsx stays thin):
- Required phone input (Zod `z.string().min(1)` + E.164 normalization; allow paste per WCAG).
- **Unchecked-by-default** consent checkbox with the spec's benefit-forward label + the `SmsConsentDisclosure` beneath it.
- Continue calls, in order (all `apiClient`, types from `@pilot/shared-types`):
  1. `POST /{tenantId}/phone/consent` `{ phone_number, sms_consent, disclosure_hash }`.
  2. If `sms_consent` true → `POST /{tenantId}/phone/send-optin` `{ user_endpoint_id }` → enter the reply-YES confirm sub-state.
  3. `PUT /{tenantId}/step3` `{ phone_number, sms_consent }` → advance to `/signup/plan` (mirror the legal→phone guard/advance pattern).
- `disclosure_hash`: hash the exact disclosure text shown (spec defines the canonical string; SHA-256 hex). If the spec centralizes this, import it — do not invent a second copy.
- Keep the existing wizard state-guard (redirect if `signup_state` doesn't belong on this page).

Preserve `Idempotency-Key` behavior if the existing signup calls set it (check `apiClient` usage in sibling steps).

## STEP 3 — Reply-YES confirmation sub-state (replace fake OTP)
Replace the 6-digit OTP grid in `PhoneOtpSubscreen` with a confirmation panel: "We texted {masked phone}. Reply **YES** to confirm." Optimistically show "sent"; poll `GET /{tenantId}/state` (TanStack Query, object-form) to reflect verified status if it flips during the session. Provide "Use a different number" (re-opens the form) and a "Skip for now → continue" that advances via `PUT /step3` with `sms_consent:false` (phone still saved). No fake attempt-counter/lockout logic — the real consent is the inbound YES.

Intermediate: `pnpm --filter web test 2>&1 | tail -6`

---

## Test Requirements

Per the inclusions file. Web = Vitest + `@testing-library/react`, `vi.mock()`, `toBeInTheDocument()`. Mock `next/navigation`. Use MSW (`setupServer`) — never mock `apiClient`. `QueryClient` with `retry:false`.

**MSW**: extend `mocks/handlers/signupHandlers.ts` for `phone/consent` + `phone/send-optin`; register in `index.ts` barrel.

**Unit** (`features/signup/components/__tests__/`):
- `SmsConsentDisclosure` renders all required 10DLC strings + Privacy Policy link.
- Step body: consent box is **unchecked on mount**; phone required (empty → validation error, no API call).

**Integration** (`apps/web/src/__tests__/batch_signup_c/stay_informed.integration.test.tsx`):
- Page renders (not 404); progress bar present.
- Phone + consent checked → Continue fires `POST /phone/consent`, then `POST /phone/send-optin`, then `PUT /step3` (assert method+URL+body order); routes to `/signup/plan`.
- Consent left unchecked → Continue fires `POST /phone/consent` (sms_consent:false) → **no** `send-optin` → `PUT /step3` → `/signup/plan`.
- Reply-YES sub-state renders after send-optin; "Use a different number" returns to the form.
- Assert by specific content/IDs from MSW fixtures — never total counts.

---

## Final Verification

> ❌ **BANNED**: `npx vitest run`. Only `pnpm --filter web test`.

### Phase 1 — targeted
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/__tests__/batch_signup_c/ 2>&1 | tail -10
```

### Phase 2 — full (once, at end)
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

Any failure in either phase must be fixed before done.

---

## Definition of Done — SIGNUP-C (Frontend)

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — new endpoints present, no type errors
- [ ] Design doc + Tom-approved UI design spec read before coding
- [ ] All endpoint URLs verified in `openapi_schema_map.md`
- [ ] **STEP 1**: `SmsConsentDisclosure` — full 10DLC language, Privacy link, `data-testid`, token-only, WCAG
- [ ] **STEP 2**: "Stay Informed" step — required phone, **unchecked-by-default** consent, ordered consent→send-optin→step3 calls, advances to `/signup/plan`
- [ ] **STEP 3**: reply-YES confirm sub-state replaces fake OTP grid; `/state` poll; skip path saves phone with `sms_consent:false`
- [ ] Route file `app/signup/phone/page.tsx` stays thin (no `"use client"`, no fetch)
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo`; components pure (§32)
- [ ] TanStack Query v5 object-form + colocated keys (§33); Zod v4 + `zodResolver`, API types from `@pilot/shared-types` (§34)
- [ ] axe-core zero violations + WCAG 2.2 AA spot-checks (target size, paste allowed, focus-visible, non-color-only errors) (§36)
- [ ] New MSW handlers registered in `mocks/handlers/index.ts`
- [ ] Unit + integration tests pass in `__tests__/batch_signup_c/`
- [ ] Zero TS errors (`check-types`); zero `no-hardcoded-design-values` lint warnings
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to the launch plan
- [ ] **Post-deploy handoff to Tom**: the "Stay Informed" screen is live → Tom captures `signup-stayinformed-checked.png` + `-unchecked.png` for the Telnyx `CXXXXXX` resubmission (see `telnyx-10dlc-p4t-tenant-comms-campaign.md` §5)

## Completion Summary

Add a **Completion Summary** to `pilot-launch-plan.md` (Completed date, Mode, Baseline→Final counts, What Was Accomplished, Files Changed, Tests Added). Update design doc `batch-signup-c-design.md` §C frontend rows + §H/§I to ✅. Note in the summary that the screen is ready for the Telnyx consent-screenshot capture (unblocks campaign submission).
