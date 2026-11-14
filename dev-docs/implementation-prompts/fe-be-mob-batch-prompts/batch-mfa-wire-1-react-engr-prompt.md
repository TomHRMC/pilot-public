# Implementation Prompt: MFA-WIRE-1 (Part B) — Web MFA Method Cards + Remove Flow + Wizard Access-Token Header

**Mode**: Pilot React Engineer
**Batch**: MFA-WIRE-1 (Part B of 3 — web; Part A backend ✅ COMPLETE 2026-08-16; Part C mobile is a separate prompt)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 6 + §2.3 MFA-WIRE-1 card
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-design.md` v1.2 ✅ APPROVED 2026-08-16 — §D (endpoint contracts), §E (pattern reuse), §F.3 (error map), §G (open questions), §H (surfaces), §I (component manifest), DoD
**UI design spec (binding)**: `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-web-ui-design-spec.md` ✅ Tom-approved — pixel specs, copy tables, state coverage, component manifest. **Implement the spec exactly.**
**Estimated session**: 2–3 hours
**Platform**: Web (`apps/web`) + one minimal modification in `packages/ui` (web wizard header helper)
**Backend companion**: MFA-WIRE-1 Part A (Python) — ✅ **COMPLETE 2026-08-16** (4594 passed / +52 tests; OpenAPI regenerated with `MfaStatusResponse.methods[]`)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-design.md`** — every section (A–I)
- **`dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-web-ui-design-spec.md`** — every section; this is the binding pixel/copy spec

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design doc.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces. Part A regenerated the OpenAPI spec on 2026-08-16; the generated `MfaStatusResponse` now includes `methods[]`.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. **One documented exception**: the web wizard's internal `fetch` helper is pre-existing FE-B12 code whose `apiClient` migration is deferred to PLAT-DEBT (design §G-Q7 — Tom-approved). Part B only *extends* that helper with the `X-Cognito-Access-Token` header. Do NOT migrate the wizard to `apiClient` in this batch. **All NEW code you write (the `useRemoveMfaMethod` hook) MUST use `apiClient`.**
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<PendingBadge>`, `<NotificationBanner>`, `<ErrorState>`, `<EmptyState>`, and `useOptimisticMutation` all exist and are exported (verified by the Architect 2026-08-17). The method-card components are **surface-scoped** in `apps/web/src/features/account-settings/` — do NOT add them to `packages/ui` (design §I, spec §8).
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` stay thin. The existing `mfa/page.tsx` already has `"use client"` + logic inline (FE-B12 legacy); this batch refactors it per spec §8 — the page keeps rendering but the card list logic moves to `features/account-settings/components/`.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. There is no "not my fault" exception. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 12 (TanStack Query v5)**: Object-form only (`useQuery({ queryKey, queryFn })`); `isPending` not `isLoading`; invalidate (don't hand-patch) after mutations except inside the shared `useOptimisticMutation` pattern.
- **Rule 15 (WCAG 2.2 AA)**: modal focus trap + focus return, ≥24×24px targets (44px where spec'd), paste allowed on the OTP input, `focus-visible` rings, `motion-reduce` fallbacks, non-color-only status. The spec's §10 accessibility notes are requirements, not suggestions.

---

## Design Decisions (Do Not Re-Litigate)

From the design doc §G and the web spec — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Access token transport | New `X-Cognito-Access-Token` header on the three MFA mutation calls (design §G-Q1) | Cognito user-scoped MFA APIs require the **access token**; the wizard historically sent only the ID token. Header value = `fetchAuthSession().tokens?.accessToken`. In-memory only — never logged, never persisted. |
| Email MFA | **Not available** — `allowedPaths={["totp","sms"]}` on both MFA pages; `ALL_MFA_METHODS` drops `"email"`; email enroll-start returns 400 `email_mfa_not_available` from the backend (design §G-Q2) | Prod pool has TOTP+SMS factors only. **No "coming soon" strings, no disabled email card (Rule 9.4).** |
| Wizard `fetch` → `apiClient` | **Deferred to PLAT-DEBT** (design §G-Q7) | Pre-existing FE-B12 pattern; migration needs custom-header support. This batch only extends the helper. |
| Optimistic Remove UX | **Dim + `<PendingBadge>`**, not disappearance (spec §2.4) | Stable row, unambiguous rollback; the locked §16.8 optimistic-UI pattern composed with `<PendingBadge>`. |
| `last_used_at` | **In the type, never rendered** (spec §2.3) | Always `null` this batch (Cognito owns challenge telemetry). No "Never used" noise on cards. |
| Last-method guard | **Server-side 409 only** — Remove is always enabled on a card (spec §6.1) | The card cannot reliably know tenant policy + other-methods state; 409-and-refresh handles it. |
| Method cards placement | **Surface-scoped** `apps/web/src/features/account-settings/components/` — NOT `packages/ui` (design §I, spec §8) | Component-existence check passed; no new shared exports. |
| Mobile Remove | **Not in this batch** — web only (DoD 4) | Mobile keeps `enrolled_methods` read-only summary (Part C scope). |

These were resolved in the design doc + approved spec. Do NOT change them without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# This batch touches apps/web AND packages/ui (web wizard file):
pnpm --filter web test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either (a) confirm with Tom that this is a known, accepted failure with a documented reason, or (b) fix the failure before touching any batch files. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Part A regenerated `openapi.json` on 2026-08-16 with the additive `MfaStatusResponse.methods[]` array. After sync, consume the generated type via:

```typescript
import type { components } from "@pilot/shared-types";
type MfaStatusResponse = components["schemas"]["MfaStatusResponse"];
type MfaMethodInfo = components["schemas"]["MfaMethodInfo"];
```

> Verify the generated schema actually contains `methods` on `MfaStatusResponse` after sync. If it does NOT → STOP and ask Tom (the Part A handoff signal is broken). If the generated name differs from `MfaMethodInfo`, use the generated name.

---

## Pre-Work: Verify Endpoints

For each API call in this batch, verify the endpoint exists before writing any code:

```bash
grep -B 2 -A 8 "mfa-status" backend/openapi_schema_map.md
grep -B 2 -A 8 "mfa/methods" backend/openapi_schema_map.md
```

Verified endpoints for this batch (Architect-confirmed against regenerated `openapi.json` 2026-08-17):

| Consumer | Endpoint | Verified |
|---|---|---|
| page status query (existing) | `GET /api/v1/users/me/mfa-status` — response now includes `methods[]` | ✅ Confirmed |
| `useRemoveMfaMethod` (new) | `DELETE /api/v1/users/me/mfa/methods/{method_id}` | ✅ Confirmed |
| wizard enroll (existing helper) | `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start` | ✅ Confirmed |
| wizard confirm (existing helper) | `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm` | ✅ Confirmed |

**If an endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

- `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` ← the page being refactored (current raw "Enrolled: …" block at lines 76–84; `ALL_MFA_METHODS` at line 28; wizard embed at lines 110–126)
- `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/enroll/page.tsx` ← force-flow page (adds `allowedPaths` + context banner)
- `frontend/packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx` ← full file; the `getAuthHeaders()` helper (~line 39) gains the access-token header; error slots at ~851–859 (top-of-wizard) and the `VerifyStep` (~379) inline error
- `frontend/packages/ui/src/mfa-enrollment-wizard/types.ts` ← **LOCKED interface — do not modify**; confirm `allowedPaths` prop exists (~line 66)
- `frontend/apps/web/src/mocks/handlers/accountSecurityHandlers.ts` ← extend the mfa-status + DELETE handlers (spec §8 row 8)
- `frontend/apps/web/src/mocks/handlers/index.ts` ← confirm handler registration pattern (no new file — extend the existing one)
- `frontend/apps/web/src/features/account-settings/hooks/useMfaStatus.ts` ← the OLDER hook shape (`method_count`/`totp_enabled`) used by `SecurityIndexPage` — do NOT break it; both consume the same endpoint (spec §8 "Not modified" note)
- `frontend/apps/web/src/features/account-settings/components/SecurityIndexPage.tsx` ← upstream nav card; unchanged, but read to understand the dual-type situation
- `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/__tests__/MfaMethodsPage.disclosure.test.tsx` ← the disclosure test you must update (assertion at ~line 138)
- `frontend/packages/ui/src/hooks/useOptimisticMutation.ts` ← the shared optimistic-mutation hook's exact signature before using it
- `frontend/apps/web/src/features/account-settings/mocks/accountFixtures.ts` ← `MFA_STATUS_NONE` fixture gains the `methods: []` field

Also run these to confirm exports before importing:

```bash
grep -n "PendingBadge\|useOptimisticMutation\|NotificationBanner" frontend/packages/ui/src/index.ts
grep -n "ErrorState\|EmptyState" frontend/packages/ui/src/index.ts
```

---

## Context: What This Batch Does

Part A rewired the backend MFA enrollment to real Cognito. The web UI now needs to: (1) send the Cognito **access token** on the three mutation calls (the backend requires `X-Cognito-Access-Token`); (2) replace the raw "Enrolled: totp, sms" text block with **method cards** consuming the new `methods[]` array, with an optimistic **Remove** flow; (3) constrain both MFA pages to `["totp","sms"]` (email is not a pool factor); (4) render the tenant-policy/grace banner; (5) map the §F.3 RFC 7807 error codes to the wizard's two error slots with the spec's exact copy.

| # | Change | File(s) | Spec reference |
|---|---|---|---|
| 1 | `MfaStatusResponse` type extension (`methods[]` + policy/grace fields) | `mfa/page.tsx` (or generated type) | spec §11.3 |
| 2 | Shared `getCognitoAccessToken()` helper | `apps/web/src/lib/cognito-token.ts` (NEW) | spec §11.4 |
| 3 | Wizard `getAuthHeaders()` adds `X-Cognito-Access-Token` | `packages/ui/.../web/MFAEnrollmentWizard.tsx` | spec §8 row 7 |
| 4 | Method-card list + card + confirm modal + Remove hook | `features/account-settings/` (4 NEW files) | spec §2.3–2.5, §8 rows 3–6 |
| 5 | Page refactor: cards, tenant-policy banner, skeleton, empty state, Add-hide | `mfa/page.tsx` | spec §2.1–2.9 |
| 6 | Force-flow page: `allowedPaths` + context banner | `mfa/enroll/page.tsx` | spec §2.10 |
| 7 | Wizard error-code → copy/placement table | `packages/ui/.../web/MFAEnrollmentWizard.tsx` | spec §9 |
| 8 | MSW handlers: `methods[]` shape + `cognito-fail` sentinel | `mocks/handlers/accountSecurityHandlers.ts` + fixtures | spec §8 row 8 |
| 9 | Disclosure test update | `__tests__/MfaMethodsPage.disclosure.test.tsx` | spec §8 row 9, §11.10 |

---

## STEP 1 — Shared access-token helper (`apps/web/src/lib/cognito-token.ts`, NEW)

Create a tiny web-app-specific helper that both the wizard header helper and the new Remove hook use (spec §11.4 — avoids duplicating the Amplify import):

```typescript
// apps/web/src/lib/cognito-token.ts
// MFA-WIRE-1 (design §G-Q1): Cognito user-scoped MFA APIs require the ACCESS token.
// In-memory only — NEVER log, persist, or return this value (design §E security pattern).
import { fetchAuthSession } from "aws-amplify/auth";

export async function getCognitoAccessToken(): Promise<string | null> {
  const session = await fetchAuthSession();
  return session.tokens?.accessToken?.toString() ?? null;
}
```

_Read the wizard file first. Adjust the Amplify import to match what the wizard already uses (`MFAEnrollmentWizard.tsx` uses `fetchAuthSession` from `aws-amplify/auth`)._

> **Note**: `apps/web/src/lib/` currently contains only `amplify-config.ts` (rules §2) — this is the second file. It is NOT an API client; all `/api/v1/...` calls still go through `apiClient` (new code) or the wizard's documented PLAT-DEBT `fetch` helper.

---

## STEP 2 — Wizard `getAuthHeaders()` gains the access-token header (`packages/ui`, MINIMAL)

In `frontend/packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx` (~line 39), extend the existing `getAuthHeaders()` helper so every wizard API call sends BOTH tokens:

- `Authorization: Bearer {idToken}` — unchanged (existing behavior)
- `X-Cognito-Access-Token: {accessToken}` — NEW, from `session.tokens?.accessToken`

**Constraints (spec §8 row 7):** No prop changes. No visual changes. No `fetch`→`apiClient` migration (PLAT-DEBT, §G-Q7). If the header value is missing (session expired), still send the request — the backend's 400 `mfa_access_token_required` / 401 `mfa_access_token_invalid` mapping (STEP 7) presents the correct copy.

**Intermediate verification**:

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui test 2>&1 | tail -6
```

The existing wizard tests must still pass — you are adding a header, not changing behavior.

---

## STEP 3 — `useRemoveMfaMethod` hook (`features/account-settings/hooks/useRemoveMfaMethod.ts`, NEW)

TanStack Query v5 `useMutation` wrapping `DELETE /api/v1/users/me/mfa/methods/{method_id}` via **`apiClient`** (new code — Rule 2 applies):

- Sends `X-Cognito-Access-Token` header (from the STEP 1 helper) as an axios per-request `headers` option.
- On 204 → `queryClient.invalidateQueries({ queryKey: ["users", "me", "mfa-status"] })`.
- Exposes the RFC 7807 `code` from the error response body for the banner-routing logic (spec §5.2). Use `isAxiosError` from `@pilot/shared-api` to safely read `error.response?.data?.code`.
- The token is in-memory only — never log it.

```typescript
// Approximate shape — adjust to the actual apiClient/isAxiosError signatures you find:
const mutation = useMutation({
  mutationFn: async (methodId: string) => {
    const accessToken = await getCognitoAccessToken();
    await apiClient.delete(`/api/v1/users/me/mfa/methods/${methodId}`, {
      headers: { "X-Cognito-Access-Token": accessToken ?? "" },
    });
  },
  onSuccess: () =>
    queryClient.invalidateQueries({ queryKey: ["users", "me", "mfa-status"] }),
});
```

---

## STEP 4 — Method-card components (`features/account-settings/components/`, 3 NEW files)

Implement **exactly** per spec §2.3 (card), §2.4 (optimistic pending — dim + `<PendingBadge>`), §2.5 (confirm modal with focus trap + focus return), §6 (interaction states), §7 (animations + reduced-motion), §10 (accessibility). Zero hex codes — `pilotPreset` tokens only (spec §3).

1. **`MfaMethodCard.tsx`** — icon (`ShieldCheckIcon` TOTP / `DevicePhoneMobileIcon` SMS, Heroicons outline), label ("Authenticator app" / "Text message"), secondary line (`{destination_masked} · Enrolled {date}` for SMS; `Enrolled {date}` for TOTP — `Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })`, spec §11.8), Remove text-button (`data-testid="mfa-method-remove-{method_type}"`, `aria-label="Remove {method label} method"`). Pending state: `opacity-60 pointer-events-none` + `<PendingBadge>` from `@pilot/ui`, `aria-busy="true"`. **`last_used_at` is never rendered** (spec §2.3).
2. **`RemoveMethodConfirmModal.tsx`** — destructive confirm per spec §2.5: overlay `mfa-remove-modal-overlay`, panel `mfa-remove-modal`, focus moves to "Keep method" (safe default) on open, Tab/Shift+Tab cycle within the modal, Escape = cancel, focus returns to the Remove button that opened it (`mfa-method-remove-{method_type}`) on close, `aria-modal="true"` + `aria-labelledby`. The engineer owns the focus-trap implementation (spec §10.4 — `react-focus-lock` if already a dependency, else a lightweight `useEffect` Tab handler — check `package.json` first, Rule 8).
3. **`MfaMethodCardList.tsx`** — maps `methods[]` → `<MfaMethodCard>`; renders the tenant-policy banner (spec §2.2, `role="alert"`, `data-testid="mfa-tenant-policy-banner"`, copy varies by `grace_period_active` / days remaining per §2.2 + §5.3); manages modal open state; drives the Remove mutation through `useOptimisticMutation` from `@pilot/ui` (spec §11.5: `onMutate` snapshot + mark pending, `onError` rollback + RFC 7807 `code` → `<NotificationBanner>` severity/copy per §5.2, `onSuccess` invalidate); renders `<NotificationBanner>` for 409 `last_method_required` (warning + invalidate — 409-and-refresh), 502 `cognito_unavailable` (error, card stays), 401 `mfa_access_token_invalid` (error, no forced redirect).

**Do NOT export these from `packages/ui`** — surface-scoped by design (§I).

---

## STEP 5 — Page refactor (`mfa/page.tsx`)

Per spec §2.1–§2.9 and §8 row 1:

- Extend the local `MfaStatusResponse` interface with `methods: MfaMethod[]` — **prefer the generated type from `@pilot/shared-types`** after `pnpm sync-api-types` (spec §11.3); the local interface is only a fallback.
- Replace the raw "Enrolled: …" text block (current lines 76–84) with `<MfaMethodCardList>`.
- `ALL_MFA_METHODS` → `["totp", "sms"]` (line 28).
- Add button: **hidden, not disabled**, when both methods enrolled (spec §2.6 — remove the `disabled` + `title` tooltip); correct `hover:bg-brand-800` → `hover:bg-brand-700` on the buttons you touch (spec §11.11).
- Pass `allowedPaths={["totp","sms"]}` to the wizard (the prop already exists on the locked interface — one-line add).
- Loading state: replace the bare spinner (lines 56–62) with the 2-card skeleton (spec §2.8, `data-testid="mfa-method-card-skeleton"`, `motion-reduce:animate-none`).
- Error state: `<ErrorState>` from `@pilot/ui/states` with retry → `refetch()` (spec §2.9, `data-testid="mfa-status-error"`).
- Empty state: spec §2.7 (`data-testid="mfa-empty-state"`). The SMS disclosure stays **inside the wizard's `SmsSetupStep`** — do not duplicate it on the page (the existing disclosure test must keep passing with the updates in STEP 8).

**Intermediate verification**:

```bash
cd <repo>/frontend && pnpm --filter web test -- apps/web/src/app/\(authed\)/settings/my-account/security/mfa 2>&1 | tail -10
```

---

## STEP 6 — Force-flow page (`mfa/enroll/page.tsx`)

Per spec §2.10:

- Add `allowedPaths={["totp","sms"]}` to the embedded `<MFAEnrollmentWizard>` (one line).
- Add the force-flow context banner above the wizard: `data-testid="mfa-force-flow-context-banner"`, `role="alert"`, `bg-alert-50 border-alert-200`, `ShieldExclamationIcon`, copy: "Your organization requires multi-factor authentication. Enrollment is not optional — set up a method to continue."
- `forceFlow={true}` already hides Cancel — unchanged.

---

## STEP 7 — Wizard error-code mapping (spec §9 — the copy/placement table is binding)

Wire the backend's RFC 7807 `code` field (returned by Part A's `_map_cognito_exception()`) to the wizard's two existing error slots — top-of-wizard (`data-testid="wizard-error"`) and inline verify (`id="verify-error"`). Implement the **exact copy** from spec §9:

| HTTP | `code` | Slot | Copy (verbatim from spec §9) |
|---|---|---|---|
| 400 | `mfa_access_token_required` | top | "Your session needs a fresh authentication token. Please sign out and sign back in, then try again." |
| 401 | `mfa_access_token_invalid` | top | "Your session has expired. Please sign in again to manage your MFA methods." |
| 400 | `mfa_code_invalid` | inline verify | "That code doesn't match. Check your {authenticator app / phone} and try again." |
| 400 | `mfa_code_expired` | inline verify | SMS: "That code has expired. Tap 'Resend code' and try again." / TOTP: "That code has expired. Restart authenticator setup." (+ "Restart setup" affordance → `handleStartEnrollment(selectedPath)`) |
| 400 | `email_mfa_not_available` | — | **No copy** — email is unreachable via `allowedPaths`; backend guard only |
| 400 | `phone_number_required` | top (SMS setup) | "We need a phone number on your profile to send text-message codes. Add one at **Account → Profile**, then come back." (with `<Link>` to `/settings/my-account/profile`) |
| 400 | `phone_number_invalid` | top (SMS setup) | "That phone number doesn't look right. Update it at **Account → Profile** using the format +1 (555) 555-1234, then try again." (same `<Link>`) |
| 503 | `sms_delivery_not_configured` | top (SMS setup) | "Text-message setup is temporarily unavailable — use an authenticator app instead." — render with **warning** tokens (`bg-alert-50 border-alert-200 text-alert-700` + `ShieldExclamationIcon`) + a "Set up authenticator app" button that calls `handleSelectPath("totp")` |
| 502 | `cognito_unavailable` | top | "We couldn't reach the authentication service. Your {enrollment / change} was not completed. Please try again in a moment." (+ "Try again" re-invokes the last action) |

Also (spec §9 WCAG 2.2 SC 3.3.8 — additive, not visual):

- Add `autoComplete="one-time-code"` to the wizard's verify input (~line 418).
- **Paste must stay allowed** — do not add any `onPaste` blocker.

_Read the wizard's current error-handling code first. The wizard currently reads `error` strings from failed fetches — you are switching the mapping to the structured RFC 7807 `code` field (`error.response.data.code` shape; Part A returns RFC 7807 Problem Details). Keep the existing string fallback for network-level failures (no response body)._

---

## STEP 8 — MSW handlers + fixtures (spec §8 row 8)

Extend `accountSecurityHandlers.ts` (do NOT create a new handler file — it is already registered in `mocks/handlers/index.ts`):

1. `GET /me/mfa-status` — the response gains the `methods[]` array alongside `enrolled_methods`. Keep the two in sync from the same module-level `enrolledMethods` state (e.g. derive `methods` entries with stable mock `method_id`s like `"mfa-method-totp"` / `"mfa-method-sms"`, `enrolled_at` ISO strings, `last_used_at: null`, `destination_masked: "•••0001"` for SMS / `null` for TOTP).
2. `DELETE /me/mfa/methods/:methodId` — add the **`cognito-fail` sentinel**: when `params.methodId === "cognito-fail"`, return 502 with `{ code: "cognito_unavailable", detail: "..." }` so the rollback + banner path is testable. Preserve the existing 409 `last_method_required` path.
3. The `MFA_STATUS_NONE` fixture (`accountFixtures.ts`) gains `methods: []`.

Also confirm the enroll-confirm MSW simulations still align with Part A's mock-client code matrix: backend mock uses `000000` = mismatch / `999999` = expired. The MSW handler currently uses `000000` / `111111` — **update `111111` → `999999`** for the expired path so frontend mocks match the backend mock semantics (Part A completion summary).

---

## STEP 9 — Disclosure test update (spec §8 row 9)

`MfaMethodsPage.disclosure.test.tsx`: the assertion at ~line 138 (`screen.getByText("Enrolled: totp")`) breaks when cards replace the raw text block. Update to assert `screen.getByText("Authenticator app")` + `screen.getByTestId("mfa-method-card-totp")`, and update the test's MSW fixture/override to return the new `methods[]` shape. The DLC-2 SMS disclosure assertions (`sms-consent-disclosure`) are **preserved** — the disclosure still lives inside the wizard's `SmsSetupStep`.

---

## Test Requirements

### TanStack Query — Required Setup for All Tests

**Always use `retry: false`** on the QueryClient in tests — default retry=3 causes test timeouts. **Never share a QueryClient across tests** — fresh instance per test via a `createWrapper()`.

```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

### MSW in Tests

`setupServer` from `msw/node`; `server.listen({ onUnhandledRequest: "warn" })`; `server.resetHandlers()` in `afterEach` (mandatory); `server.close()` in `afterAll`. Per-test state overrides via `server.use(...)`. **Never mock `apiClient` directly.**

For the wizard header tests, mock the Amplify session so `fetchAuthSession()` resolves tokens:

```typescript
vi.mock("aws-amplify/auth", () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: { accessToken: { toString: () => "mock-access-token" }, idToken: { toString: () => "mock-id-token" } },
  }),
}));
```

The web app uses **Vitest + `@testing-library/react`**: `vi.mock()`, `toBeInTheDocument()`, `import { describe, it, expect, vi } from "vitest"`. Mock `next/navigation` / `next/link` where the component imports them.

### Unit Tests (co-located `__tests__/`)

- **`MfaMethodCard.test.tsx`** — renders TOTP + SMS variants (label, secondary line, `destination_masked` only for SMS); Remove button `aria-label`; pending state (`opacity-60`, `<PendingBadge>`, `aria-busy`); `last_used_at` NOT rendered even when provided.
- **`RemoveMethodConfirmModal.test.tsx`** — opens with focus on "Keep method"; Escape cancels; confirm fires `onConfirm`; focus returns to the Remove button on close (assert `document.activeElement`).
- **`useRemoveMfaMethod.test.ts`** — 204 invalidates `["users","me","mfa-status"]`; request carries the `X-Cognito-Access-Token` header (assert via an MSW request handler capturing `request.headers.get("x-cognito-access-token")`); error path exposes the RFC 7807 `code`.
- **Wizard header test** (extend the existing wizard test file if one exists — find it with `find frontend/packages/ui/src/mfa-enrollment-wizard -name "*.test.*"`) — `getAuthHeaders()` output includes both `Authorization` and `X-Cognito-Access-Token`.

### Integration Tests (batch-scoped folder)

Create `apps/web/src/__tests__/batch_mfa_wire_1/mfa-methods.integration.test.tsx`:

1. Page renders method cards from `methods[]` (not the raw "Enrolled:" text) — `mfa-method-card-totp` present.
2. Remove flow happy path: click Remove → modal → confirm → card enters pending → 204 → card gone after invalidate.
3. Rollback path: `cognito-fail` sentinel → 502 → card returns to default + error banner copy "We couldn't reach the authentication service — your method was NOT removed. Try again."
4. 409 path: last-method → warning banner "Your organization requires MFA. Add another method before removing this one." + status query re-invalidated.
5. Add button hidden when both `totp` and `sms` are enrolled; visible otherwise.
6. `allowedPaths` constraint: wizard method-select shows exactly "Authenticator app" + "Text message (SMS)" — **no email option, no "coming soon" string anywhere** (Rule 9.4 — assert `queryByText(/email/i)` is null inside the chooser and `queryByText(/coming soon/i)` is null page-wide).
7. Tenant-policy banner renders with grace copy when `tenant_policy_required && grace_period_active` (`mfa-tenant-policy-banner`).
8. Force-flow page renders `mfa-force-flow-context-banner` and passes the `allowedPaths` constraint.

### Test Resilience Rule (MANDATORY)

Never rely on module-level mock data shared across tests without `server.resetHandlers()` in `afterEach`. Never assert on total counts — assert by `data-testid` / specific content. Never mutate shared fixtures — copy them. Note the account-security handlers use **module-level mutable state** (`enrolledMethods`) — your integration tests must reset it between tests (re-init via a fixture reset or a `beforeEach` that re-enrolls the needed state through the handlers; read the existing disclosure test for the established reset idiom).

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. It bypasses the monorepo workspace setup and causes resolution failures. The ONLY correct test runner for `apps/web` is `pnpm --filter web test`.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend

pnpm --filter @pilot/ui test 2>&1 | tail -6       # wizard header + error mapping
pnpm --filter web test 2>&1 | tail -6             # page, components, hooks

# Single batch folder:
pnpm --filter web test -- apps/web/src/__tests__/batch_mfa_wire_1/ 2>&1 | tail -10
```

Fix any failure before moving to the next task — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify the root cause → STOP and ask Tom.

---

## Definition of Done — MFA-WIRE-1 Part B

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — generated `MfaStatusResponse` confirmed to include `methods[]`
- [ ] Design doc + web UI design spec fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] All endpoint URLs verified in `openapi_schema_map.md`
- [ ] **STEP 1**: `apps/web/src/lib/cognito-token.ts` created — `getCognitoAccessToken()` (in-memory only)
- [ ] **STEP 2**: Web wizard `getAuthHeaders()` sends `X-Cognito-Access-Token` alongside `Authorization`; zero prop/visual changes; `packages/ui` tests still green
- [ ] **STEP 3**: `useRemoveMfaMethod.ts` created — `apiClient`, access-token header, 204 invalidation, RFC 7807 `code` exposure
- [ ] **STEP 4**: `MfaMethodCardList.tsx` + `MfaMethodCard.tsx` + `RemoveMethodConfirmModal.tsx` created per spec §2.3–2.5 (token-only, `data-testid`s, focus trap + return, dim+badge pending, `last_used_at` never rendered)
- [ ] **STEP 5**: `mfa/page.tsx` refactored — cards replace raw text, `ALL_MFA_METHODS=["totp","sms"]`, Add hidden when both enrolled, `allowedPaths` passed, skeleton + `<ErrorState>` + empty state
- [ ] **STEP 6**: `enroll/page.tsx` — `allowedPaths` + `mfa-force-flow-context-banner`
- [ ] **STEP 7**: Wizard error-code mapping implements the spec §9 table verbatim (incl. 503 warning-style + TOTP nudge, profile `<Link>`s, TOTP "Restart setup" affordance); `autoComplete="one-time-code"` added; paste untouched
- [ ] **STEP 8**: MSW handlers extended — `methods[]` in sync with `enrolled_methods`, `cognito-fail` sentinel 502, expired-code sentinel aligned to `999999`; no new handler file (existing one extended; barrel unchanged)
- [ ] **STEP 9**: Disclosure test updated (card label + testids; `sms-consent-disclosure` assertions preserved)
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; components pure (React Compiler, rules §32)
- [ ] All new hooks use TanStack Query v5 object-form + colocated query keys; invalidation (not hand-patching) after mutations outside the `useOptimisticMutation` pattern (rules §33)
- [ ] No tenant-data fetching in Server Components (rules §35)
- [ ] WCAG 2.2 AA spot-checks pass: modal focus trap + return, ≥24×24px targets (44px where spec'd), paste allowed + `autoComplete="one-time-code"` on the OTP input, `focus-visible` rings, `motion-reduce` fallbacks, non-color-only status (rules §36)
- [ ] No new shared exports added to `packages/ui/src/index.ts` (method cards are surface-scoped)
- [ ] No new npm dependencies without checking `package.json` first (Rule 8 — `react-focus-lock` only if already present)
- [ ] No "coming soon" strings; no email option rendered anywhere (Rule 9.4)
- [ ] New code (`useRemoveMfaMethod`) uses `apiClient`; only the pre-existing wizard helper keeps `fetch` (PLAT-DEBT exception)
- [ ] Unit tests pass (targeted run)
- [ ] Integration tests pass in `apps/web/src/__tests__/batch_mfa_wire_1/`
- [ ] Zero TypeScript errors (`check-types` passes for `@pilot/ui` + `web`)
- [ ] No regressions in pre-existing test suites (web + `@pilot/ui`)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command in the Final Verification section above
- [ ] Final test count (before → after) documented in the Completion Summary
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix C (format below)

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` **Appendix C** titled `### MFA-WIRE-1 (Part B) — Web MFA Method Cards + Remove Flow: Completion Summary` using the format below.
2. Update the launch plan §2.3 MFA-WIRE-1 card **Status** line: flip "Parts B/C next" note — Part B ✅ with date; Part C still pending.
3. Do NOT update `pilot-operations.md` — Part A already made the §13 doc corrections; Part B has no ops-doc surface. (The Architect verifies the overall §13.13 status refresh at batch close.)
4. If any endpoint, type name, or fixture detail differed from this prompt, list the discrepancy in the summary.

```markdown
### MFA-WIRE-1 (Part B) — Web MFA Method Cards + Remove Flow: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web) | X passed (@pilot/ui)
**Final**: X+N passed (web), X+M passed (@pilot/ui) (+N/+M new tests)

#### What Was Accomplished

- [Wizard access-token header]
- [Method cards + optimistic Remove + confirm modal]
- [allowedPaths constraint + policy/grace banner + skeleton/empty/error states]
- [Wizard RFC 7807 error-code copy mapping incl. 503 sms_delivery_not_configured]
- [MSW methods[] + cognito-fail sentinel; disclosure test updated]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/lib/cognito-token.ts` | Created — … |
| `frontend/packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx` | Updated — … |
| `frontend/apps/web/src/features/account-settings/hooks/useRemoveMfaMethod.ts` | Created — … |
| `frontend/apps/web/src/features/account-settings/components/MfaMethodCard*.tsx`, `RemoveMethodConfirmModal.tsx` | Created — … |
| `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` | Updated — … |
| `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/enroll/page.tsx` | Updated — … |
| `frontend/apps/web/src/mocks/handlers/accountSecurityHandlers.ts` (+ fixtures) | Updated — … |
| `.../__tests__/MfaMethodsPage.disclosure.test.tsx` | Updated — … |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/__tests__/batch_mfa_wire_1/mfa-methods.integration.test.tsx` | Integration | N | ✅ |
| ... | Unit | N | ✅ |

#### Verification

- Phase 1 targeted: …
- Phase 2 full canonical command: `=== MVP FINAL VERIFICATION COMPLETE ===` …
- Deviations from prompt: none / [list]
```
