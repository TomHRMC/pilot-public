# Implementation Prompt: DLC-2 — 10DLC MFA Screen Compliance (Web + Mobile)

**Mode**: Pilot React Engineer  
**Batch**: DLC-2  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P1 — 10DLC Compliance Engineering  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-dlc-2-design.md`  
**Estimated session**: 1–2 hours  
**Platform**: Both web (`apps/web`) + mobile (`apps/mobile`)  
**Pure frontend — no backend changes needed**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:

- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — shared components already exist.
- **Rule 8**: No new npm dependencies without first checking what is already installed in `package.json`.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**.

> **This batch is pure UI text/link changes only. There are NO new hooks, NO new API endpoints, NO new components.** The scope is surgical: two files are modified, test assertions are updated to match the new disclosure text.

---

## Context: Why This Batch Exists

The Pilot for Trades 10DLC SMS MFA campaign (Telnyx Campaign ID: `CYYYYYY`) failed MNO review with failure reason **806**:

> "Unable to verify, needs compliant and accurate CTA information. Update with specific path for mobile opt-in, HELP instructions, STOP instructions, message frequency disclosure, 'message and data rates may apply' disclosure and link to the message program privacy policy."

Telnyx support confirmed **two specific gaps** in the submitted screenshots:

1. **Web page** (`/settings/my-account/security/mfa`) — missing links to the privacy policy
2. **Mobile screen** (Settings → Security → Two-Factor Authentication → MFA screen) — missing HELP/STOP/frequency/privacy language

This batch fixes both. After the React Engineer completes this, Tom will take new screenshots and resubmit to Telnyx.

---

## Design Decisions (Do Not Re-Litigate)

| Decision | Outcome | Rationale |
|---|---|---|
| Web privacy policy link placement | Inline anchor tag in a new compliance footer `<p>` below the enrolled methods section, always visible | Must be visible at CTA level per Telnyx compliance requirement 806 |
| Mobile disclosure text replacement | Replace the entire `disclosureBox` `Text` content with the full compliant 4-line disclosure | Telnyx requires all four elements: STOP, HELP, freq, data rates, privacy policy — adding piecemeal creates maintenance risk |
| Privacy policy URL | `https://www.pilotfortrades.com/legal/privacy` | Canonical URL already submitted to Telnyx in campaign registration |
| Terms URL | `https://www.pilotfortrades.com/legal/terms` | Available if needed for future review; not required in this pass |
| Mobile privacy policy display | Plain text URL (not a `Linking.openURL` tappable link) | Sufficient for 10DLC compliance screenshot. A tappable link is a P3 enhancement. |
| Msg frequency disclosure wording | "Msg freq: 1 message per login or enrollment event." | Matches the campaign description submitted to Telnyx: "The system sends one SMS code per login or enrollment event." |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Web baseline:
pnpm --filter web test 2>&1 | tail -6

# Mobile baseline:
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom that it is a known accepted failure, or fix it before touching batch files.

---

## Pre-Work: Sync API Types

Not required — this batch touches no hooks.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx
  ← why: understand the full current JSX structure before adding the compliance footer

frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx
  ← why: understand the full current StyleSheet and disclosureBox structure before editing

frontend/apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx
  ← why: tests already assert on sms-disclosure testID and disclosure text content — must update assertions to match new text
```

---

## Context: What This Batch Does

| # | Platform | File | Change |
|---|---|---|---|
| 1 | Web | `apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` | Add a compliance footer paragraph with a clickable privacy policy link |
| 2 | Mobile | `apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` | Replace the `disclosureBox` text with the full 10DLC-compliant 4-element disclosure |
| 3 | Mobile tests | `apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx` | Update disclosure text assertions to match the new wording |

**No new files are created. No new components. No new hooks. No new endpoints.**

---

## STEP 1 — Web: Add Privacy Policy Link to MFA Page

**File**: `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx`

**Read the file first.** Adjust the placement to match what you actually find.

The web page is currently missing any link to the privacy policy. Telnyx requires it to be visible at the CTA level — meaning it must be present on the same page as the "Add this method" button.

Add a compliance footer paragraph **after** the enrolled methods summary box and **before** the "Add this method" button. It must always be visible (not conditional on `showEnrollWizard`).

### Exact text to render:

```
By adding an SMS method, you consent to receive one-time verification codes from Pilot for Trades. 
Msg freq: 1 message per login or enrollment event. Msg & data rates may apply. 
Reply STOP to opt out. Reply HELP for help. 
Privacy policy: [https://www.pilotfortrades.com/legal/privacy]
```

The privacy policy URL must be a proper `<a>` tag with `href` pointing to `https://www.pilotfortrades.com/legal/privacy`, `target="_blank"`, and `rel="noopener noreferrer"`.

### Approximate implementation pattern (read the file first — adjust to match):

```tsx
{/* ── 10DLC-COMPLIANT SMS DISCLOSURE — MANDATORY — DO NOT REMOVE OR EDIT ── */}
<p
  className="text-xs text-neutral-500 leading-relaxed"
  data-testid="sms-compliance-disclosure"
>
  By adding an SMS method, you consent to receive one-time verification codes
  from Pilot for Trades. Msg freq: 1 message per login or enrollment event.
  Msg &amp; data rates may apply. Reply STOP to opt out. Reply HELP for help.{" "}
  <a
    href="https://www.pilotfortrades.com/legal/privacy"
    target="_blank"
    rel="noopener noreferrer"
    className="underline hover:text-neutral-700"
  >
    Privacy policy
  </a>
  .
</p>
```

Place this paragraph **inside the outer `<div className="flex flex-col gap-6 max-w-2xl">`**, positioned after the enrolled methods summary `<div>` and before the "Add this method" `<button>`. It must be outside any conditional renders — always visible.

**Do NOT remove the existing page title or subtitle.** Insert only the new paragraph.

**After completing Step 1**, run:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```

Fix any failures before proceeding to Step 2.

---

## STEP 2 — Mobile: Replace SMS Disclosure Text

**File**: `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx`

**Read the file first.** The current `disclosureBox` content is:

> "📱 **SMS verification** uses your carrier's standard messaging network. Message and data rates may apply. By enrolling your phone number, you consent to receive one-time verification codes from Pilot for Trades. You can unenroll at any time by returning to this screen and removing the SMS method."

This text is missing: STOP instruction, HELP instruction, explicit message frequency, and privacy policy reference. Telnyx failure reason 806 requires all four.

### Replace the `disclosureBox` `<Text>` content with this exact text:

```
📱 SMS verification — By enrolling your phone number, you agree to receive 
one-time verification codes from Pilot for Trades. Msg freq: 1 message per 
login or enrollment event. Msg & data rates may apply. Reply STOP to opt out. 
Reply HELP for help. Privacy policy: pilotfortrades.com/legal/privacy
```

### Approximate implementation pattern (read the file first — adjust to match):

```tsx
{/* ── 10DLC-COMPLIANT SMS DISCLOSURE — MANDATORY — DO NOT REMOVE OR EDIT ── */}
<View style={styles.disclosureBox} testID="sms-disclosure">
  <Text style={styles.disclosureText}>
    {"📱 "}
    <Text style={styles.disclosureBold}>SMS verification</Text>
    {
      " — By enrolling your phone number, you agree to receive one-time verification codes from Pilot for Trades. Msg freq: 1 message per login or enrollment event. Msg & data rates may apply. Reply STOP to opt out. Reply HELP for help. Privacy policy: pilotfortrades.com/legal/privacy"
    }
  </Text>
</View>
```

**Keep the `testID="sms-disclosure"` on the `<View>` exactly as-is** — the existing integration tests assert on it.

**The `styles.disclosureBox`, `styles.disclosureText`, and `styles.disclosureBold` StyleSheet entries remain unchanged.** Only the text content inside `<Text>` changes.

---

## STEP 3 — Update Mobile Integration Tests

**File**: `frontend/apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx`

**Read the file first** before making changes. There are existing tests that assert on `sms-disclosure` content. These tests must be updated to match the new disclosure wording from Step 2.

Find the test(s) that:
1. Assert the `sms-disclosure` testID is visible
2. Assert on specific text strings within the disclosure (e.g., "Message and data rates may apply")

Update those text assertions to match the new wording. The new canonical text strings to assert on are:

| Test | New assertion string |
|---|---|
| "sms-disclosure testID is always visible" | No change — `testID="sms-disclosure"` is unchanged |
| "Message and data rates may apply text is visible" | Change expected text to `"Msg & data rates may apply"` (the abbreviated 10DLC standard form) |

If there are additional disclosure content assertions, update them to match the new text from Step 2.

**After completing Steps 2 and 3**, run:

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Fix any failures before proceeding.

---

## Test Requirements

### Web — New test for Step 1

The web `page.tsx` file currently has no test file covering the MFA methods page disclosure text. Create a minimal targeted test.

**Create**: `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/__tests__/MfaMethodsPage.disclosure.test.tsx`

Minimum coverage:
- The compliance disclosure renders (`data-testid="sms-compliance-disclosure"` is in the DOM)
- The disclosure contains the text "Privacy policy"
- The disclosure contains an `<a>` element linking to `https://www.pilotfortrades.com/legal/privacy`
- The disclosure contains "Msg & data rates may apply"
- The disclosure contains "Reply STOP to opt out"
- The disclosure contains "Reply HELP for help"

Use `vi.mock("next/navigation", ...)` for any navigation imports. The page uses `"use client"` and TanStack Query — wrap in `QueryClientProvider` with `retry: false`.

**TanStack Query setup (required)**:

```typescript
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";

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

Use MSW to mock the `/api/v1/users/me/mfa-status` response:

```typescript
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

const server = setupServer(
  http.get("/api/v1/users/me/mfa-status", () =>
    HttpResponse.json({
      enrolled_methods: [],
      tenant_policy_required: false,
      grace_period_active: false,
      grace_ends_at: null,
      enforcement_activated: false,
    }),
  ),
);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Mock `next/navigation`:
```typescript
vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/my-account/security/mfa",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
```

### Mobile — Update existing tests (Step 3 above)

No new test files for mobile. Update the text assertion in `batch_mob_b10/mfa.integration.test.tsx` as described in Step 3.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. The only correct commands are `pnpm --filter web test` and `pnpm --filter mobile test`.

### Phase 1 — Targeted (run after each step)

```bash
cd <repo>/frontend

# After Step 1 + web test creation:
pnpm --filter web test 2>&1 | tail -6

# After Steps 2 + 3 (mobile):
pnpm --filter mobile test 2>&1 | tail -8
```

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — DLC-2

- [ ] Pre-modification regression baseline captured (web + mobile counts recorded)
- [ ] All mandatory source files read before modifying
- [ ] **STEP 1**: `apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` — compliance footer added with `data-testid="sms-compliance-disclosure"`, privacy policy `<a>` link present
- [ ] **STEP 2**: `apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` — `disclosureBox` text replaced with full STOP/HELP/freq/privacy disclosure; `testID="sms-disclosure"` preserved
- [ ] **STEP 3**: `apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx` — disclosure text assertions updated to match new wording
- [ ] Web disclosure test created at `apps/web/src/app/(authed)/settings/my-account/security/mfa/__tests__/MfaMethodsPage.disclosure.test.tsx`
- [ ] Web disclosure test: asserts `sms-compliance-disclosure` testID visible
- [ ] Web disclosure test: asserts privacy policy link href = `https://www.pilotfortrades.com/legal/privacy`
- [ ] Web disclosure test: asserts "Reply STOP to opt out" visible
- [ ] Web disclosure test: asserts "Reply HELP for help" visible
- [ ] Web disclosure test: asserts "Msg & data rates may apply" visible
- [ ] Mobile: `testID="sms-disclosure"` assertion still passes
- [ ] Mobile: updated text assertion passes with new "Msg & data rates may apply" wording
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` and `pnpm --filter mobile build` pass)
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented in Completion Summary

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` §P1 using the format below.
2. Update `dev-docs/integrations/telnyx/telnyx-10dlc-mfa-campaign.md` — change **Screenshot Status** for both web and mobile from "❌ Non-compliant (needs update)" to "✅ Compliant — updated DLC-2" and add the completion date.

```markdown
### DLC-2 — 10DLC MFA Screen Compliance (Web + Mobile): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web) | X passed (mobile)
**Final**: X+N passed (web) | X+M passed (mobile)

#### What Was Accomplished

- Added 10DLC-compliant SMS disclosure footer to web MFA page with clickable privacy policy link
- Updated mobile MFA screen disclosure to include STOP/HELP/frequency/privacy language per Telnyx requirement 806
- Updated mobile integration test assertions to match new disclosure wording
- Created new web disclosure unit test verifying all 5 compliance elements

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` | Updated — added `sms-compliance-disclosure` paragraph with privacy policy link |
| `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` | Updated — replaced disclosureBox text with full STOP/HELP/freq/privacy disclosure |
| `frontend/apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx` | Updated — disclosure text assertions match new wording |
| `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/__tests__/MfaMethodsPage.disclosure.test.tsx` | Created — 5 disclosure compliance assertions |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/.../MfaMethodsPage.disclosure.test.tsx` | Unit | 5 | ✅ |
| `apps/mobile/__tests__/batch_mob_b10/mfa.integration.test.tsx` | Integration (updated) | — | ✅ |
```
