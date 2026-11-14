# Implementation Prompt: SIGNUP-UI-FIX-2 — Signup Wizard Polish Bundle

**Mode**: Pilot React Engineer
**Batch**: SIGNUP-UI-FIX-2 (master table row 10a)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` — §2.0 row 10a + §2.3 E2E-REMAIN follow-ups (SIGNUP-C-FU, SIGNUP-C-FU2, SIGNUP-UI-FIX-2 items)
**Design doc**: None — 4 items are fully spec'd in the launch plan; this prompt is the authoritative task list
**Estimated session**: 3–4 hours
**Platform**: Web only (`apps/web`) — Next.js App Router signup wizard
**Backend companion**: PLATFORM-SMS-B1 ✅ (closed 2026-08-10 — `sms_consent_status` now live in `/state` `collected_data`). All endpoints this batch calls already exist in `openapi.json`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`pilot-launch-plan.md`** — the SIGNUP-C-FU, SIGNUP-C-FU2, and SIGNUP-UI-FIX-2 rows in the §2.3 E2E-REMAIN follow-ups table (the canonical item specs)

Critical rules for this batch:

- **Rule 1.1/1.2**: Verify every endpoint in `backend/openapi_schema_map.md` / `openapi.json` before calling it. If not there → STOP and ask Tom. (All endpoints below are pre-verified by the Architect — see Pre-Work table.)
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — PLATFORM-SMS-B1 regenerated `openapi.json` on 2026-08-10; types must come from `@pilot/shared-types`, never hand-written.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...`.
- **Rule 8**: No new npm dependencies. Everything needed (Heroicons, existing signup components) is installed.
- **Rule 10**: If ANY test fails during your work — even apparently pre-existing — fix it or get explicit written confirmation from Tom before proceeding.
- **Rule 11 (React Compiler)**: No hand-written `useMemo`/`useCallback`/`React.memo`. Keep components pure.
- **Rule 15 (WCAG 2.2 AA)**: New button/link targets ≥24×24px, `focus-visible` rings, non-color-only state, `role="alert"` on errors, `aria-live` on the resend countdown/success feedback.

## Design Decisions (Do Not Re-Litigate)

| Decision | Outcome | Rationale |
|---|---|---|
| Item (a) Charter blocker is **investigate-first** | Diagnose before editing; the visible symptom ("Loading payment form…" stuck, Continue never enables) may be env-config, not code | Found 2026-08-10 during Charter E2E; must not blindly patch render logic |
| `sms_consent_status` stays an untyped key in `collected_data` | FE reads `collected_data.sms_consent_status` as a runtime field (Architect decision 2026-08-10 in `batch-platform-sms-b1-design.md` header) | `collected_data` is an intentionally extensible wizard-data bag; no typed model retrofit |
| Resend cooldown is 60s, client-mirrored | Backend already enforces 429 + "Please wait before requesting another opt-in text." (`signup.py`) | Client countdown matches the server cooldown; never bypass the 429 |
| SIGNUP-C-FU disclosure copy may already be shipped | Task is **verify-and-close**, not blindly re-edit | `SMS_CONSENT_DISCLOSURE_TEXT` already contains "support" as of this authoring — confirm + close with evidence |
| No new top-level UX pattern | Compose existing signup components + tokens (token-only, zero hex, `pilotPreset`) | §16 pattern lock; designer rules for web surfaces |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch. If any tests fail before you start → do NOT proceed; confirm with Tom or fix first.

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

PLATFORM-SMS-B1 closed 2026-08-10 and regenerated `openapi.json` — this sync regenerates `packages/shared-types/src/api-schema.d.ts` to match.

## Pre-Work: Verify Endpoints

Verified by the Architect against `backend/openapi.json` (2026-08-10) — confirm before coding:

| Hook / call | Endpoint | Verified |
|---|---|---|
| Resend opt-in text | `POST /api/v1/signup/{tenant_id}/phone/send-optin` | ✅ `openapi.json` (~L29640); request `SendOptinRequest`, response `SendOptinResponse` |
| Consent (returns `user_endpoint_id`) | `POST /api/v1/signup/{tenant_id}/phone/consent` | ✅ `openapi.json` (~L29581); response `PhoneConsentResponse` |
| Wizard state polling | `GET /api/v1/signup/{tenant_id}/state` | ✅ already consumed by `signup/phone/page.tsx` (`collected_data.sms_consent_status`) |

```bash
grep -n "send-optin" backend/openapi_schema_map.md
```

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

- `frontend/apps/web/src/app/signup/plan/page.tsx` — Charter blocker lives here (see Task 1 hypothesis map)
- `frontend/apps/web/src/app/signup/phone/page.tsx` — full file: consent submit flow (`handleSubmit` ~L151), polling effect (~L121), subscreen wiring (~L368)
- `frontend/apps/web/src/features/signup/components/DoubleOptinConfirmSubscreen.tsx` — the confirm subscreen receiving the new Resend link
- `frontend/apps/web/src/features/signup/components/VerifyEmailStep.tsx` — verify-page button state (~L289–305) + post-verify flow
- `frontend/apps/web/src/features/signup/components/SmsConsentDisclosure.tsx` — `SMS_CONSENT_DISCLOSURE_TEXT` (~L48) + hash contract (any text change changes the SHA-256 sent to `/phone/consent`)
- `frontend/apps/web/src/features/signup/components/__tests__/SmsConsentDisclosure.test.tsx` — message-types assertion (~L31)
- `frontend/apps/web/src/mocks/handlers/signupHandlers.ts` + `frontend/apps/web/src/mocks/handlers/index.ts` — existing signup MSW handlers; check whether `send-optin` already has a handler before adding one

Also run:

```bash
find frontend/apps/web/src/features/signup -name "*.tsx" | head -30
grep -rn "user_endpoint_id" frontend/apps/web/src/app/signup/phone/page.tsx
```

---

## Task 1 — Charter plan page blocker (HIGHEST PRIORITY — blocks all Charter signup E2E)

**Symptom (2026-08-10)**: select Charter on `/signup/plan` → "Loading payment form…" persists and Continue never enables.

**Investigate first — hypothesis map** (from reading `plan/page.tsx`):

1. The loading placeholder renders only when `!selectedTierIsTrial && !selectedTierIsCharter && !clientSecret && selectedTier` (~L315–323). For a correctly-detected Charter selection this block should **not** render at all → the bug is upstream: **Charter is not being detected as Charter**.
2. Detection is `selectedTierIsCharter = selectedTier?.requires_payment_method === false` (~L221). Check whether the tiers payload actually carries `requires_payment_method: false` for the Charter tier (network tab / MSW fixture / the tiers endpoint response shape after `pnpm sync-api-types`). If the field is absent/`undefined`, Charter falls into the paid path → waits forever for a `clientSecret` that never resolves.
3. Check `effectiveSelectedTierId` / `handleSelectTier` wiring (~L167) — `CharterTierCard` calls `onSelect={() => handleSelectTier(tier.tier_name)}` while `TierPickerCard` uses a different signature (~L276 vs L283); confirm `selectedTier` resolves after clicking the Charter card.
4. **Env check (eliminate before code edits)**: if the root cause turns out to be Stripe-related instead, verify `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` is set on the `pilot-web` ECS task definition (local `pk_test_placeholder` fallback at ~L36 masks misconfiguration). If it's an env gap, document it and hand to Tom/DevOps — do not code around it.

**Fix**: minimal change addressing the confirmed root cause. Likely candidates: fall back to `tier_name === "charter"` when `requires_payment_method` is absent, or fix the selection-state resolution. Keep the existing `canContinue` semantics (`Join Charter →` requires only selection, no payment method).

**Test**: unit test covering "select Charter → no payment-form placeholder, Continue enabled with `Join Charter →` label". Place in the existing signup test area; add an MSW fixture variant if the tiers payload shape is implicated.

## Task 2 — Verify-page transition copy ("Setting up your account…")

**Symptom**: after email-code verify succeeds, the button sits on "Verifying…" through tenant/user provisioning (Post-Confirmation Lambda) until `/state` advances to `step2_legal`.

**Fix** in `VerifyEmailStep.tsx`: introduce a post-verify provisioning phase (e.g., a `phase: "verifying" | "provisioning"` state set when confirm succeeds, cleared when the wizard advances). Button copy: `"Verifying…"` while the confirm request is in flight → `"Setting up your account…"` during provisioning. Keep the button disabled in both phases; add `aria-live="polite"` (or extend the existing pattern) so the copy change is announced. Follow the existing polling/advance mechanism in the component — do not invent a new one.

**Test**: unit test asserting copy transitions `Verify & continue →` → `Verifying…` → `Setting up your account…` across the mocked confirm + advance sequence.

## Task 3 — SIGNUP-C-FU disclosure copy: VERIFY-AND-CLOSE

The campaign-compliance item asked to add "support" to the disclosure so message types match the **Mixed** `CXXXXXX` campaign. **As of 2026-08-10 the copy already includes support**: `SmsConsentDisclosure.tsx` reads "…account, billing, security, and support messages — including replies to support requests you submit to us…" and the checkbox label in `phone/page.tsx` includes "support".

**Do**:
1. Confirm the rendered disclosure + checkbox label both disclose support (run the existing `SmsConsentDisclosure.test.tsx`; update its message-types assertion at ~L31 if it doesn't assert "support").
2. If anything is still missing, make the copy edit — **remember the hash contract**: `SMS_CONSENT_DISCLOSURE_TEXT` is SHA-256 hashed into `POST /phone/consent`; rendered text and constant must never diverge (component splits on `"See our Privacy Policy."`).
3. Close the item with evidence (test output + the two file refs) in your Completion Summary.

## Task 4 — SIGNUP-C-FU2 "Resend text" link on the double-opt-in confirm screen

**Spec** (from launch plan): the confirm subscreen offers only "Use a different number" / "Skip for now" — a user whose opt-in SMS never arrived has no self-serve retry.

**Implementation**:
- Add a secondary text button **"Resend text"** to `DoubleOptinConfirmSubscreen.tsx`, under the confirm copy.
- Wire it through `phone/page.tsx`: the parent must retain `userEndpointId` from the consent response (`consentRes.data.user_endpoint_id`, ~L174 — currently local to `handleSubmit`; lift to state) and pass an `onResend` handler into the subscreen.
- `onResend` calls `apiClient.post(`/api/v1/signup/${tenantId}/phone/send-optin`, { user_endpoint_id: userEndpointId })`.
- After each send, disable the button with countdown copy for **60s** (match the backend cooldown), e.g. `"Resend text (available in 42s)"`; re-enable at 0.
- Success: toast or inline `role="status"` confirmation on `{"status":"sent"}` — check `SendOptinResponse` in `@pilot/shared-types` for the exact shape.
- Errors: surface RFC 7807 detail — 429 → "We just sent a text. Wait a moment before trying again."; 422 → the validation message. Reuse the existing error styling from the page (`text-fault-600`, `role="alert"`).
- Token-only styling, ≥24×24px target, `focus-visible` ring — mirror the existing "Use a different number" secondary-button classes in the subscreen.
- Hidden/disabled once `confirmed` is true.

**MSW**: check `signupHandlers.ts` for an existing `send-optin` handler; if absent, add one (200 `{"status":"sent"}` + a 429 path usable by tests) and confirm it's exported via the existing `signupHandlers` barrel entry in `mocks/handlers/index.ts` (already registered — do not duplicate the path).

**Test**: unit tests on the subscreen/page — resend fires with correct body; button disabled with countdown after send; 429 surfaces the cooldown copy; success shows confirmation; hidden after `confirmed`.

---

## Test Implementation

- Framework: **Vitest + Testing Library** (web). One test file per touched component, colocated in `__tests__/` next to the component; signup-flow integration coverage in `apps/web/src/__tests__/` if an existing signup integration file exists (check first — extend, don't duplicate).
- TanStack Query is **not** required for these fixes (the pages use direct `apiClient` calls) — if you introduce any hook, use object-form `useMutation`/`useQuery` with `retry: false` in test setup and colocated keys (rules §33).
- MSW: reuse/extend `signupHandlers.ts`; verify registration in `mocks/handlers/index.ts`.
- Every error state must be asserted via `role="alert"` / accessible name — not color or class names.

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — NEVER use it. The only correct runner for `apps/web` is `pnpm --filter web test`.

### Phase 1 — Targeted (after each task)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/signup 2>&1 | tail -10
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving on — including apparently pre-existing ones.

### Phase 2 — Full verification (once, at the very end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> `pnpm --filter mobile build` IS the mobile type check. Any failure in either phase must be fixed before declaring done — no "pre-existing" exception without written confirmation from Tom.

## Definition of Done — SIGNUP-UI-FIX-2

- [ ] Pre-modification regression baseline captured (zero unexplained failures)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] All mandatory source files read before modifying
- [ ] All endpoint URLs confirmed in `openapi_schema_map.md` / `openapi.json`
- [ ] **Task 1**: Charter selection no longer shows the payment-form placeholder; Continue enables with `Join Charter →`; root cause documented in the Completion Summary (incl. env-vs-code determination)
- [ ] **Task 2**: Verify button transitions to "Setting up your account…" during provisioning; `aria-live` announcement verified
- [ ] **Task 3**: SIGNUP-C-FU verified closed (disclosure + label disclose "support"; test assertion updated if needed) — or copy corrected with hash contract intact
- [ ] **Task 4**: Resend link live with 60s countdown, 429/422 error surfacing, hidden after confirm
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo`; components pure (rules §32)
- [ ] axe-core zero violations + WCAG 2.2 AA spot-checks on touched surfaces (rules §36)
- [ ] MSW `send-optin` handler present + registered (no duplicate paths)
- [ ] Unit tests pass (targeted run)
- [ ] Zero TypeScript errors; zero `no-hardcoded-design-values` ESLint warnings
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — command above
- [ ] Launch plan updates: row 10a → ✅; SIGNUP-C-FU / SIGNUP-C-FU2 / SIGNUP-UI-FIX-2 rows in the §2.3 follow-ups table → ✅ with one-line evidence

## Completion Summary

After all DoD items complete, append to `pilot-launch-plan.md` **Appendix C** using this format, and add the one-row Appendix A entry:

### SIGNUP-UI-FIX-2 — Signup Wizard Polish Bundle: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- [Task 1 root cause + fix — one line]
- [Task 2 / 3 / 4 outcomes — one line each]

#### Files Changed / Created
| File | Action |
|---|---|
| … | … |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| … | … | … | ✅ |
