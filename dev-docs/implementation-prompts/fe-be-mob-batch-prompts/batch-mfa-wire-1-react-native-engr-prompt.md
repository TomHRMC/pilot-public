# Implementation Prompt: MFA-WIRE-1 (Part C) — Mobile MFA Wizard Flesh-Out (Real API Wiring + Step Content)

**Mode**: Pilot React Engineer (React Native / `apps/mobile` focus)
**Batch**: MFA-WIRE-1 (Part C of 3 — mobile; Part A backend ✅ COMPLETE 2026-08-16; Part B web is a separate prompt)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 6 + §2.3 MFA-WIRE-1 card
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-design.md` v1.2 ✅ APPROVED 2026-08-16 — §D (endpoint contracts), §F.3 (error map), §G-Q1/Q4/Q6, §H (surfaces), §I (component manifest), DoD 6–7
**UI design spec (binding)**: `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-mobile-ui-design-spec.md` ✅ Tom-approved — per-step content/layout specs, token tables, error + haptic table, accessibility notes. **Implement the spec exactly.**
**Estimated session**: 3–4 hours
**Platform**: Mobile (`apps/mobile` — Expo SDK 54 / React Native) + the shared mobile wizard file in `packages/ui/src/mfa-enrollment-wizard/mobile/`
**Backend companion**: MFA-WIRE-1 Part A (Python) — ✅ **COMPLETE 2026-08-16** (OpenAPI regenerated; enroll-start/confirm/delete now call real Cognito behind the mock seam)

---

## ⚠️ RULE 9.8 DEPENDENCY GATE — `expo-clipboard` (READ FIRST)

The approved mobile spec's copy affordances ("Copy key", "Copy setup link instead", "Copy all codes") use `Clipboard` from **`expo-clipboard`**. Architect verification on 2026-08-17: **`expo-clipboard` is NOT currently a dependency anywhere in the frontend workspace** (grep of all `package.json` files — zero hits). It is a **new native Expo dependency** and therefore requires **Tom's explicit approval under Rule 9.8 before you install it** (same class as CE-1's `react-native-signature-canvas`, approved 2026-08-12; and MOB-B11's pending `react-native-qrcode-svg`).

- **If Tom has approved `expo-clipboard`** (check the launch-plan §2.3 MFA-WIRE-1 card status line / ask before starting): `pnpm --filter mobile add expo-clipboard`, then proceed with the spec's copy buttons as written. Note the approval date in your Completion Summary. Like CE-1, this native dep requires an **EAS dev-client rebuild** for on-device testing — record that as a Tom follow-up in the summary (do NOT run `eas build` yourself).
- **If approval has NOT been given**: do NOT install anything. Implement the fallback: make the secret / otpauth URI / recovery codes `Text` components **`selectable={true}`** (React Native core — zero deps) and replace the copy buttons with a "Press and hold to select and copy" caption (`tokens.mobileFontSizes.caption`, `tokens.colors.neutral[600]`). All other spec content is unchanged. Record "clipboard fallback shipped (Rule 9.8 pending)" in the summary.

Confirmed already-available deps you WILL use (verified 2026-08-17): `expo-haptics` (~15.0.8) and `react-native-svg` (jest mock exists at `apps/mobile/__mocks__/react-native-svg.js`). Do not add any other dependency.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-design.md`** — every section (A–I)
- **`dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-mobile-ui-design-spec.md`** — every section; this is the binding spec

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design doc.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — Part A regenerated the OpenAPI spec 2026-08-16. Backend payload types come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2 (mobile-scoped exception)**: All NEW `/api/v1/...` calls normally use `apiClient` from `@pilot/shared-api`. **Documented exception (design §G-Q7, Tom-approved)**: the mobile wizard's API helper uses `fetch` directly — same pattern as the web wizard — because it needs the custom `X-Cognito-Access-Token` header; `apiClient` migration is PLAT-DEBT, not this batch. This exception applies ONLY to the mobile wizard file. The host screen keeps using its existing `useMfaStatus` hook.
- **Rule 8**: No new npm dependencies without checking `package.json` first — and `expo-clipboard` is gated by Rule 9.8 (see the gate section above).
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. There is no "not my fault" exception. If you cannot identify the root cause → STOP and ask Tom.
- **WCAG / glove-friendly (spec §6)**: all targets ≥44×44pt (`tokens.touchTargets.mobile.sm/md`), `accessibilityLabel` on every `Pressable`, `textContentType="oneTimeCode"` on the verify input, no paste-blocking, `allowFontScaling={true}` on all `Text`, color is never the only status signal. The spec's §6 notes are requirements, not suggestions.

---

## Design Decisions (Do Not Re-Litigate)

From the design doc §G and the mobile spec — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Access token transport | `X-Cognito-Access-Token` header on enroll-start / enroll-confirm (design §G-Q1) | Cognito user-scoped MFA APIs require the **access token**; value = `fetchAuthSession().tokens?.accessToken.toString()`. In-memory only — never logged, never persisted. |
| TOTP setup on mobile | **Manual secret entry** — copyable grouped secret + "Copy setup link" (`otpauth://` URI). **NO QR image** (design §G-Q4) | QR rendering is MOB-B11 (P2 polish, gated on Rule 9.8 approval for `react-native-qrcode-svg`). Do NOT add any QR dependency. |
| Email MFA | **Never renders** — `MOBILE_ALLOWED_PATHS = ["totp","sms"]` is already correct in the skeleton (spec §1.2). **Do not "fix" it.** No "coming soon" strings (Rule 9.4). | Pool has TOTP+SMS only; email enroll-start returns 400 `email_mfa_not_available`. |
| Method Remove on mobile | **Not in this batch** — web-only (DoD 4; spec §1.3) | Host screen keeps the read-only `enrolled_methods` bullet list. Do NOT spec or build a Remove affordance. |
| Mobile data source | Host screen keeps consuming **`enrolled_methods: string[]`** (design §D.4 backward compat) — do NOT switch to `methods[]` | The new `methods[]` array is web's contract this batch; mobile adoption is a future batch. |
| Wizard file | **Flesh in place** — `packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx`; locked props; no new components; no new `packages/ui` exports (design §I, spec §7) | One-file batch for the wizard + light host-screen touch. |
| Idempotency-Key header | **Not required** (design §E) | MFA enrollment is online-only; replay safety is the backend's §D.2 replay matrix + UNIQUE natural key. |
| `expo-clipboard` | **Rule 9.8 gate** — see the gate section above | New native dep; Tom approval required before install; `selectable` Text fallback otherwise. |

These were resolved in the design doc + approved spec. Do NOT change them without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

pnpm --filter mobile test 2>&1 | tail -8
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either (a) confirm with Tom that this is a known, accepted failure with a documented reason, or (b) fix the failure before touching any batch files.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Part A regenerated `openapi.json` on 2026-08-16. The enroll-start/confirm response types (`qr_code_uri`/`secret`/`destination_masked`, `method_id`/`enrolled_at`) come from `@pilot/shared-types` via `components["schemas"][...]` — never hand-written.

---

## Pre-Work: Verify Endpoints

```bash
grep -B 2 -A 8 "mfa/methods" backend/openapi_schema_map.md
grep -B 2 -A 8 "mfa-status" backend/openapi_schema_map.md
```

Verified endpoints for this batch (Architect-confirmed against regenerated `openapi.json` 2026-08-17):

| Consumer | Endpoint | Verified |
|---|---|---|
| wizard enroll-start | `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start` | ✅ |
| wizard enroll-confirm | `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm` | ✅ |
| host screen status (existing hook) | `GET /api/v1/users/me/mfa-status` | ✅ |

**If an endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

- `frontend/packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` ← **the file you flesh in place** (309-line skeleton: `MOBILE_ALLOWED_PATHS` line 19, step order, `handleNext()` at ~64 advancing with zero API calls, step indicator + grace banner preserved)
- `frontend/packages/ui/src/mfa-enrollment-wizard/types.ts` ← **LOCKED — do not modify**; confirm `MFAEnrollmentWizardProps` base + `MFAEnrollmentWizardPropsExtended` (the FE-B12 additive props `forceFlow`, `showRecoveryCodes`, `onRecoveryCodesAcknowledged`, `enrolledMethods`)
- `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` ← host screen (light touch: four-state refinement + token migration; SMS disclosure at ~116–136 is **preserved unchanged**)
- `frontend/apps/mobile/features/login/components/MfaChallengeStep.tsx` ← the verify-input idiom you mirror (`number-pad`, `textContentType="oneTimeCode"`, mono font, haptics usage)
- `frontend/apps/mobile/features/login/components/MfaEnrollmentRequiredGate.tsx` ← `forceFlow` warning-banner token reference (~159–166)
- `frontend/apps/mobile/mocks/handlers/accountSettingsHandlers.ts` ← extend with enroll-start/enroll-confirm (registered barrel already exists at `mocks/handlers/index.ts`)
- `frontend/apps/mobile/constants/style-constants.ts` ← the `tokens` / `fontWeights` re-export surface you must use (zero hex codes)
- `frontend/packages/ui/src/tokens/` (skim `mobileFontSizes`, `touchTargets.mobile`, `radii`, `colors`) ← token names used throughout the spec
- `frontend/apps/mobile/package.json` ← confirm `expo-haptics`, `react-native-svg`; confirm `expo-clipboard` gate status

Also run:

```bash
# Confirm the mobile jest mock for react-native-svg exists (you'll import Svg icons):
ls frontend/apps/mobile/__mocks__/react-native-svg.js

# Find the existing mobile MFA/wizard tests (if any) to extend:
find frontend/apps/mobile -name "*.test.tsx" -path "*mfa*" -o -name "*.test.tsx" -path "*MFAEnrollment*" | head -10
find frontend/packages/ui/src/mfa-enrollment-wizard -name "*.test.*" | head -10
```

---

## Context: What This Batch Does

Part A rewired the backend to real Cognito. The mobile wizard skeleton currently advances steps with **zero API calls**. Part C fleshes it in place: real enroll-start/enroll-confirm calls with the access-token header, manual-secret TOTP setup, SMS masked-destination + resend, 6-digit verify, recovery-codes complete step, the §F.3 error table with haptics, and a light four-state + token-migration touch on the host screen. After this batch, a field tech can enroll TOTP or SMS MFA entirely on mobile against real Cognito (prod smoke per design §C step 7).

| # | Change | File(s) | Spec reference |
|---|---|---|---|
| 1 | Wizard step content — chooser, setup-totp, setup-sms, verify, complete (+recovery codes) | `packages/ui/.../mobile/MFAEnrollmentWizard.tsx` | spec §2.1–2.5 |
| 2 | Real API wiring (`enroll-start`, `enroll-confirm`) + `X-Cognito-Access-Token` | same (local helper) | spec §8.1 |
| 3 | Error + haptic table (§F.3 codes → inline/blocking + haptic pattern) | same | spec §4 |
| 4 | Prop annotation widened to `MFAEnrollmentWizardPropsExtended`; `forceFlow` hides Cancel + warning banner | same | spec §1.2, §8.7 |
| 5 | Host screen: four data states + token migration; pass `allowedPaths` explicitly | `apps/mobile/.../security/mfa.tsx` | spec §5, §8.13 |
| 6 | MSW: enroll-start/enroll-confirm handlers | `apps/mobile/mocks/handlers/accountSettingsHandlers.ts` | this prompt §STEP 6 |

---

## STEP 1 — Local API helper inside the mobile wizard file

Add a small helper **inside the wizard file** (not a new shared module — spec §8.1):

```typescript
// Approximate — adjust to the Amplify import style used elsewhere in apps/mobile:
import { fetchAuthSession } from "aws-amplify/auth";

async function getMfaAuthHeaders(): Promise<Record<string, string>> {
  const session = await fetchAuthSession();
  return {
    Authorization: `Bearer ${session.tokens?.idToken?.toString() ?? ""}`,
    "X-Cognito-Access-Token": session.tokens?.accessToken?.toString() ?? "",
    "Content-Type": "application/json",
  };
}
```

- Base URL: use the same API base URL resolution the mobile app already uses for `fetch` (read how `apps/mobile` configures its API base — check `constants/` or the existing auth/API utilities; do not invent a new env var).
- Parse error responses as RFC 7807 (`body.code`) — STEP 4 maps codes to copy. Keep a string fallback for network-level failures.
- The access token is **in-memory only** — never logged, never persisted (design §E).

---

## STEP 2 — Wizard step content (spec §2.1–2.5 — binding)

Replace the placeholder step bodies (skeleton lines ~137–258) with the spec'd content. All dimensions in pt; all colors via `tokens.colors.*` / `lightTheme.*`; **zero hex codes** (do not copy the legacy hexes from `mfa.tsx` styles); all `Text` gets `allowFontScaling={true}` (spec §6.7).

1. **Chooser (`method-select`)** — spec §2.1: two option rows (56pt min height, 12pt gap, radio role + `checked` state), leading icon circles with **inline SVGs** (`shield-check`, `device-phone-mobile` via `react-native-svg` — already a dep; ~5 lines of Heroicons outline path data each; spec §8.10), labels + descriptions, "Recommended" badge on TOTP (text + green badge — never color alone). Selection auto-advances via `handleSelectPath` (preserved). Footer: Cancel only.
2. **Setup TOTP** — spec §2.2: 3-step instructions; secret panel (`testID="totp-secret"`, mono, 4-char grouping via `secret.match(/.{1,4}/g).join(" ")`, VoiceOver label joins groups with commas — spec §8.3); "Copy key" primary button + "Copy setup link instead" secondary (**subject to the Rule 9.8 gate** — clipboard or `selectable` fallback); Continue disabled until `enrollStartPayload` loaded.
3. **Setup SMS** — spec §2.3: masked-destination readout (`testID="sms-destination"`, mono); "Resend code" with **30s cooldown** (`setInterval` in a ref, cleared on unmount — spec §8.4); the host screen's SMS disclosure is NOT duplicated. Re-calling enroll-start resends the code (design §D.1 re-enrollment row).
4. **Verify** — spec §2.4: 6-digit `TextInput` mirroring `MfaChallengeStep` (`number-pad`, `textContentType="oneTimeCode"`, mono, center, `letterSpacing: 4`, 56pt min height, auto-focus, digits-only filter, paste allowed); inline error (`testID="mfa-code-error"`, `accessibilityRole="alert"`); SMS resend below the error; TOTP "Restart authenticator setup" link (`testID="totp-restart-setup"` → `handleStartEnrollment("totp")`); Verify disabled until 6 digits.
5. **Complete (+ recovery codes)** — spec §2.5: success icon (48pt margin-token circle + check SVG), "MFA enabled", body copy; recovery-codes block only when `showRecoveryCodes` (grid of mono codes, "Copy all codes" per the Rule 9.8 gate, acknowledgment checkbox `testID="recovery-codes-ack"`, Finish `testID="mfa-wizard-finish"` **disabled until acknowledged** → `onComplete(selectedPath)`). When `showRecoveryCodes` is false, fire `onComplete` without the gate (spec §8.5).

Preserve: step indicator dots (with `accessibilityLabel` per step), grace-period banner, `MOBILE_ALLOWED_PATHS` filter, `testID` names already in the skeleton.

---

## STEP 3 — Real API wiring

- `handleSelectPath(path)` → advance to `setup` AND call `enroll-start` (store the response as `enrollStartPayload`: TOTP → `{ secret, qr_code_uri }`; SMS → `{ destination_masked }`).
- `handleNext()` from `verify` → call `enroll-confirm` with the 6-digit code → on 201/200 (200 = idempotent replay, design §D.2) advance to `complete`; on error, map per STEP 4 and stay on `verify`.
- Re-enrollment (resend / restart) re-calls `enroll-start` — the backend supersedes/resends (design §D.1).
- When `showRecoveryCodes` is true, fetch the recovery codes for the complete step via the existing recovery-codes endpoints already in the backend contract (check `openapi_schema_map.md` for `recovery-codes` — read the host screen / web wizard for the established call pattern; if the FE-B12 skeleton already has a recovery-codes fetch path, reuse it).

**Intermediate verification**:

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui test 2>&1 | tail -6
```

---

## STEP 4 — Error + haptic table (spec §4 — binding)

Every §F.3 RFC 7807 code → presentation + exact copy + haptic. Blocking notices use the spec §4 style (fault tokens for errors, alert tokens for the 503 warning, `testID="wizard-error"`, `accessibilityRole="alert"`):

| HTTP | `code` | Presentation | Copy (verbatim from spec §4) | Haptic |
|---|---|---|---|---|
| 400 | `mfa_access_token_required` | blocking (top) | "Your session needs a fresh sign-in. Please sign out and back in, then try again." | Error (two long) |
| 401 | `mfa_access_token_invalid` | blocking (top) | "Your session has expired. Sign in again to manage your MFA." | Error |
| 400 | `mfa_code_invalid` | inline verify | "That code didn't match — try again." | Error |
| 400 | `mfa_code_expired` | inline verify + resend/restart | SMS: "That code expired — resend a new one." / TOTP: "That code expired — restart authenticator setup." | Error |
| 400 | `email_mfa_not_available` | — | **No copy** — unreachable (allowedPaths) | — |
| 400 | `phone_number_required` | blocking (setup-sms) | "We need a phone number on your profile to send text codes. Add one in Account → Profile, then come back." | Error |
| 400 | `phone_number_invalid` | blocking (setup-sms) | "That phone number doesn't look right. Update it in Account → Profile, then try again." | Error |
| 503 | `sms_delivery_not_configured` | blocking (setup-sms) + TOTP nudge button (`testID="sms-unavailable-totp-nudge"` → `handleSelectPath("totp")`) | "Text-message setup is temporarily unavailable — use an authenticator app instead." | **None** (warning = visual-only) |
| 502 | `cognito_unavailable` | blocking (top) + "Try again" re-invokes last action | "We couldn't reach the authentication service. Nothing was saved — try again." | Error |

Haptics via `expo-haptics` (confirmed dep): success = `Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success)` on copy actions, verify success, finish; failure = `...NotificationFeedbackType.Error` (spec §8.8).

---

## STEP 5 — Props widening + `forceFlow` + host screen

1. **Widen the wizard's prop type annotation** from `MFAEnrollmentWizardProps` to `MFAEnrollmentWizardPropsExtended` (additive — accepts `forceFlow`, `showRecoveryCodes`, `enrolledMethods` from the host screen; spec §1.2). `types.ts` itself is LOCKED.
2. **`forceFlow` variant** (spec §8.7): hide the footer Cancel when `forceFlow === true` (the skeleton renders Cancel unconditionally — add the check); render the force-flow warning banner at the top of the wizard using `lightTheme.warning` tokens (mirror `MfaEnrollmentRequiredGate`).
3. **Host screen `mfa.tsx`** (light touch — spec §5, §8.13): loading → 2 skeleton rows (`testID="mfa-status-skeleton"`); error → fault-colored text + "Try again" `Pressable` (`testID="mfa-status-retry"` → `refetch()`); empty/populated branches preserved; SMS disclosure block **untouched**; migrate the `styles` object's hardcoded hexes to `tokens` references (in-scope cleanup since you're editing the state branches); pass `allowedPaths={["totp","sms"]}` explicitly to the wizard (defensive — the skeleton already filters).
4. **No Remove affordance on mobile** (spec §1.3). The escalation note ("Manage on web dashboard") is **not specced as a component** — do not add one.

---

## STEP 6 — MSW handlers (mobile)

Extend `frontend/apps/mobile/mocks/handlers/accountSettingsHandlers.ts` (already registered in the barrel — do NOT create a new file):

- `POST */api/v1/users/me/mfa/methods/:methodType/enroll-start` → TOTP: `{ method_type: "totp", qr_code_uri: "otpauth://totp/PilotForTrades:...", secret: "JBSWY3DPEHPK3PXP" }`; SMS: `{ method_type: "sms", destination_masked: "•••0001" }`.
- `POST */api/v1/users/me/mfa/methods/:methodType/enroll-confirm` → success 201 `{ method_id, enrolled_at }`; **`000000` → 400 `{ code: "mfa_code_invalid" }`; `999999` → 400 `{ code: "mfa_code_expired" }`** — matching Part A's `MockCognitoMfaClient` code matrix exactly.
- Keep the existing `GET mfa-status` handler shape (`enrolled_methods: string[]`) — mobile does not consume `methods[]`.

---

## Test Requirements

### Framework (mobile)

Jest (jest-expo preset) + `@testing-library/react-native` — `jest.mock()`, `.toBeTruthy()` / `.not.toBeNull()` (NOT `toBeInTheDocument()` — that is web-only), `fireEvent.press()`. Mock `expo-router` in any screen test. Mock `react-native-svg` via the existing `__mocks__/react-native-svg.js` (automatic via moduleNameMapper). Mock Amplify:

```typescript
jest.mock("aws-amplify/auth", () => ({
  fetchAuthSession: jest.fn().mockResolvedValue({
    tokens: {
      accessToken: { toString: () => "mock-access-token" },
      idToken: { toString: () => "mock-id-token" },
    },
  }),
}));
```

Mock `expo-haptics` and `expo-clipboard` (if approved) with `jest.mock()` so tests assert the calls without native modules. MSW `setupServer` from `msw/node` with `server.resetHandlers()` in `afterEach` — never mock the API layer directly.

### Unit Tests (co-located `__tests__/` next to the wizard)

`packages/ui/src/mfa-enrollment-wizard/mobile/__tests__/MFAEnrollmentWizard.test.tsx` (extend if it already exists — find it first):

1. Chooser renders exactly two options (`mfa-path-totp`, `mfa-path-sms`) — **no email** (Rule 9.4: `queryByText(/email/i)` is null; no "coming soon").
2. Selecting TOTP fires enroll-start (assert via MSW request capture) with both `Authorization` and `x-cognito-access-token` headers.
3. TOTP setup renders the grouped secret (`totp-secret`) — e.g. `JBSW Y3DP EHPK 3PXP`.
4. Verify: 6-digit entry enables Verify; `000000` → inline `mfa-code-error` "That code didn't match — try again." + error haptic fired; valid code → advance to complete.
5. SMS setup: `sms-destination` shows the masked destination; resend enters 30s cooldown (fake timers).
6. 503 path: enroll-start SMS → 503 `sms_delivery_not_configured` → warning notice + `sms-unavailable-totp-nudge` button switches to TOTP; **no haptic** on the warning.
7. Recovery codes: `showRecoveryCodes` → Finish disabled until `recovery-codes-ack` checked; `showRecoveryCodes=false` → no gate.
8. `forceFlow` hides Cancel and renders the warning banner.

### Host-screen test

Extend the existing `mfa.tsx` test (find it — `find frontend/apps/mobile -name "*.test.tsx" -path "*security*"`): skeleton on loading, retry on error, disclosure preserved, wizard receives `allowedPaths`.

### Integration Tests (batch folder — never co-located)

Create `apps/mobile/__tests__/batch_mfa_wire_1/mfa-enrollment.integration.test.tsx`: full TOTP enrollment walk through the host screen (chooser → setup → verify → complete) against MSW; assert the enroll-confirm request body contains the 6-digit code; assert `onComplete` behavior via the host screen's refetch. Follow the established mobile integration-test patterns in `apps/mobile/__tests__/` (read one existing batch folder first, e.g. the CE-1 Part B tests).

### Test Resilience Rule (MANDATORY)

Fresh MSW state per test via `server.resetHandlers()`; never share mutable mock state; assert by `testID` / specific content, never counts; never mutate shared fixtures.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. The ONLY correct runners are `pnpm --filter mobile test` and `pnpm --filter @pilot/ui test`.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend

pnpm --filter @pilot/ui test 2>&1 | tail -6       # wizard package
pnpm --filter mobile test 2>&1 | tail -8          # host screen + integration

# Single files:
pnpm --filter @pilot/ui test -- src/mfa-enrollment-wizard/mobile 2>&1 | tail -10
pnpm --filter mobile test -- __tests__/batch_mfa_wire_1/ 2>&1 | tail -10
```

Fix any failure before moving to the next task — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **`pnpm --filter mobile build` = mobile type check** (`tsc --noEmit`) — there is no `check-types` script for mobile.
>
> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify the root cause → STOP and ask Tom.

---

## Definition of Done — MFA-WIRE-1 Part C

- [ ] Rule 9.8 gate resolved BEFORE any install: `expo-clipboard` approved by Tom (date recorded) OR the `selectable` Text fallback shipped — never an unapproved install
- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design doc + mobile UI design spec fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] All endpoint URLs verified in `openapi_schema_map.md`
- [ ] **STEP 1**: local API helper sends `Authorization` (ID token) + `X-Cognito-Access-Token`; token in-memory only
- [ ] **STEP 2**: all five step bodies implemented per spec §2.1–2.5 (tokens only, zero hex, `allowFontScaling`, 44/56pt targets, testIDs per spec)
- [ ] **STEP 3**: enroll-start on path select; enroll-confirm on verify; 200 replay treated as success; resend/restart re-call enroll-start
- [ ] **STEP 4**: full §4 error table implemented verbatim (inline vs blocking, TOTP nudge on 503, haptic patterns — success short / failure two-long / warning none)
- [ ] **STEP 5**: prop annotation widened to extended props; `forceFlow` hides Cancel + warning banner; host screen four-state refinement + token migration; SMS disclosure untouched; `allowedPaths` passed explicitly; NO Remove affordance; NO QR dependency
- [ ] **STEP 6**: mobile MSW enroll handlers added to `accountSettingsHandlers.ts` (barrel unchanged — file already registered); code matrix `000000`/`999999` matches Part A mock
- [ ] No new shared exports in `packages/ui/src/index.ts`; `types.ts` untouched (LOCKED)
- [ ] No new npm dependencies beyond a Tom-approved `expo-clipboard`
- [ ] Mobile escalation / §16 patterns respected — no new top-level UX pattern introduced
- [ ] WCAG mobile spot-checks: `textContentType="oneTimeCode"`, paste allowed, VoiceOver labels per spec §6.1 (incl. comma-grouped secret), checkbox/radio roles + states, Dynamic Type
- [ ] Unit tests pass (targeted run)
- [ ] Integration tests pass in `apps/mobile/__tests__/batch_mfa_wire_1/`
- [ ] Zero TypeScript errors (`@pilot/ui check-types` + `mobile build` pass)
- [ ] No regressions in pre-existing suites (`mobile` + `@pilot/ui`)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command in the Final Verification section above
- [ ] Final test count (before → after) documented in the Completion Summary
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix C (format below)

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` **Appendix C** titled `### MFA-WIRE-1 (Part C) — Mobile MFA Wizard Flesh-Out: Completion Summary` using the format below.
2. Update the launch plan §2.3 MFA-WIRE-1 card **Status** line — Part C ✅ with date; note the `expo-clipboard` approval/fallback outcome.
3. If `expo-clipboard` was approved and installed, record the **EAS dev-client rebuild** as a Tom follow-up (native module — Expo Go cannot load it; same precedent as CE-1 Part B).
4. If any endpoint, type name, token name, or fixture detail differed from this prompt, list the discrepancy in the summary.

```markdown
### MFA-WIRE-1 (Part C) — Mobile MFA Wizard Flesh-Out: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer (React Native)
**Baseline**: X passed (mobile) | X passed (@pilot/ui)
**Final**: X+N passed (mobile), X+M passed (@pilot/ui) (+N/+M new tests)
**expo-clipboard**: approved by Tom YYYY-MM-DD / fallback shipped (selectable Text)

#### What Was Accomplished

- [Wizard fleshed in place: real enroll-start/confirm with access-token header]
- [Step content per spec: chooser / manual-secret TOTP / SMS masked-dest + 30s resend / 6-digit verify / recovery-codes complete]
- [§F.3 error + haptic table incl. 503 sms_delivery_not_configured TOTP nudge]
- [forceFlow variant; host screen four-state + token migration; MSW enroll handlers]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` | Updated — fleshed in place |
| `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` | Updated — four states + tokens |
| `frontend/apps/mobile/mocks/handlers/accountSettingsHandlers.ts` | Updated — enroll handlers |
| ...tests... | Created/Updated |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/mobile/__tests__/batch_mfa_wire_1/mfa-enrollment.integration.test.tsx` | Integration | N | ✅ |
| ... | Unit | N | ✅ |

#### Verification

- Phase 1 targeted: …
- Phase 2 full canonical command: `=== MVP FINAL VERIFICATION COMPLETE ===` …
- Deviations from prompt: none / [list]
```
