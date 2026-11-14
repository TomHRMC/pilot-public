# Implementation Prompt: DLC-B2 (Frontend) — Customer SMS Consent Disclosure

**Mode**: Pilot React Engineer
**Batch**: DLC-B2 (React half — runs AFTER the Python half)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 (DLC-B2 card, §2.0 row #9)
**Design doc**: None — single-surface disclosure addition; exact copy specified inline.
**Submission playbook**: `dev-docs/integrations/telnyx/telnyx-10dlc-customer-comms-campaign.md` §11 — the required visible elements for the compliance screenshot.
**Estimated session**: 1–1.5 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: `batch-dlc-b2-python-engr-prompt.md` — **must be complete first** (it is; this batch has no shared endpoints, but the campaign submission depends on both halves being deployed together).
**Pure frontend — no backend changes needed** (no new hooks, no new endpoints).

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full.
- **`dev-docs/integrations/telnyx/telnyx-10dlc-customer-comms-campaign.md`** — §4 (opt-in narrative), §11 (required screenshot elements). Your disclosure paragraph is the "consumer consent CTA" that MNO reviewers evaluate.

**Critical rules for this batch:**

- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component. You almost certainly do NOT need a new component — this is a copy addition inside an existing form.
- **Rule 8**: No new npm dependencies.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` stay thin — all changes are in the feature component.
- **Rule 10**: If ANY test fails during your work — even one that looks pre-existing — fix it before declaring done. If you cannot find the root cause → STOP and ask Tom.

- **⚠️ Compliance-copy rule (batch-specific)**: The disclosure paragraph text must contain ALL required elements from playbook §11. A missing element (e.g., no privacy-policy link, or no "Msg & data rates may apply") is the exact failure that got the first campaign rejected (806). Use the copy in STEP 1 verbatim.

---

## Design Decisions (Do Not Re-Litigate)

| Decision | Outcome | Rationale |
|---|---|---|
| Where does the disclosure go? | Inside the existing DLC-1 consent block in `CustomerForm.tsx`, directly below the attestation checkbox, rendered whenever the phone field has a value | It must be co-located with the phone/consent CTA so the compliance screenshot captures both in one frame |
| New component or inline? | **Inline** in `CustomerForm.tsx` | Single-use compliance copy; no reuse case. Do not create a `packages/ui` component. |
| Does the checkbox behavior change? | **No** — the attestation checkbox, `sms_attestation_checked` submit gating, and warning text are unchanged | This batch is additive: it only adds the consumer-facing disclosure paragraph |
| New backend field or hook? | **No** | Consent state already flows via `sms_attestation_checked` (DLC-1). Nothing to add. |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the count. It must still pass at the end.

> If any test is already failing: confirm with Tom it's a known accepted failure, OR fix it before touching batch files. Do not start on an unexplained red suite.

> **`pnpm sync-api-types` is NOT required** — this batch adds no hooks and touches no backend payloads. Skip it.

---

## Pre-Work: Read These Source Files

Read each with `read_file` before modifying:

```
frontend/apps/web/src/features/customers/components/CustomerForm.tsx                      ← the file you edit; the DLC-1 consent block is ~lines 222–251
frontend/apps/web/src/features/customers/components/__tests__/CustomerForm.test.tsx        ← existing tests; extend, don't break
frontend/packages/ui/src/index.ts                                                          ← confirm no existing disclosure component to reuse (there isn't; confirm)
```

Confirm the current consent block structure (checkbox + warning) before adding the disclosure — do not disturb the existing `data-testid="sms-attestation-checkbox"` or `data-testid="sms-attestation-warning"` logic.

---

## Context: What This Batch Does

The customer create/edit form already has a contractor **attestation checkbox** (DLC-1). But it has **no consumer-facing disclosure** — the program name, message types, frequency, rates, STOP/HELP instructions, and privacy-policy link that MNO reviewers require to see at the SMS opt-in CTA. Without it, the customer-consent screenshot fails 10DLC review (the same 806 failure the MFA campaign hit).

This batch adds one disclosure paragraph (`data-testid="customer-sms-consent-disclosure"`) inside the existing consent block. That's it.

---

## STEP 1 — Add the consumer disclosure paragraph to `CustomerForm.tsx`

**File**: `frontend/apps/web/src/features/customers/components/CustomerForm.tsx`

Read the file first. The DLC-1 consent block renders when `mobilePhone.trim()` is truthy (~line 223). Add the disclosure paragraph **inside** that block, directly **below** the `<label>`/checkbox and above (or below) the warning `<p>`. It must render whenever the consent block renders (i.e., whenever a phone number is present) so it is always in the compliance screenshot.

**Exact copy to render** (adjust the JSX wrapper to match the file's existing styling conventions — use the same neutral text classes as the surrounding block; do NOT hardcode hex colors):

```tsx
<p
  className="mt-3 text-xs text-neutral-600 leading-relaxed"
  data-testid="customer-sms-consent-disclosure"
>
  By saving a mobile number, this customer will receive service SMS from
  Pilot for Trades on behalf of your business — appointment reminders,
  job updates, and invoice links. Message frequency varies. Msg &amp; data
  rates may apply. Reply STOP to opt out, HELP for help. See our{" "}
  <a
    href="https://www.pilotfortrades.com/legal/privacy"
    target="_blank"
    rel="noopener noreferrer"
    className="text-brand-600 underline hover:text-brand-700"
  >
    Privacy Policy
  </a>
  .
</p>
```

> **Required elements checklist** (all must be present in the rendered text — playbook §11):
> - Program name: "Pilot for Trades" ✅
> - Message types: "appointment reminders, job updates, and invoice links" ✅
> - Frequency: "Message frequency varies" ✅
> - Rates: "Msg & data rates may apply" ✅
> - Opt-out: "Reply STOP to opt out" ✅
> - Help: "HELP for help" ✅
> - Clickable privacy-policy link → `https://www.pilotfortrades.com/legal/privacy` ✅

> **Styling note**: Read the existing consent block (`border border-neutral-200 rounded-md bg-neutral-50`) and match its typography. Use design tokens / existing utility classes only — the ESLint `no-hardcoded-design-values` rule will flag raw hex or px. If `text-brand-600` is not the correct link token in this codebase, grep for how other links are styled (`grep -rn "underline" frontend/apps/web/src/features` ) and match.

Intermediate check after the edit:
```bash
pnpm --filter web test -- apps/web/src/features/customers/components/__tests__/CustomerForm.test.tsx 2>&1 | tail -10
```

---

## Test Requirements

Extend `CustomerForm.test.tsx` (do not create a new file). Use Vitest + `@testing-library/react` (web patterns: `toBeInTheDocument()`, `vi.mock()`).

Add these tests:

1. **`disclosure renders when a phone number is entered`** — render the form, set the mobile phone field to a value, assert `screen.getByTestId("customer-sms-consent-disclosure")` is in the document and its text contains `"Msg & data rates may apply"` and `"Reply STOP"`.
2. **`disclosure is hidden when no phone number`** — with an empty phone field, assert `screen.queryByTestId("customer-sms-consent-disclosure")` is `null` (mirrors the existing checkbox conditional).
3. **`privacy policy link points to the correct URL`** — assert the link within the disclosure has `href="https://www.pilotfortrades.com/legal/privacy"`.

> **Test resilience**: follow the existing test file's setup (it already renders `CustomerForm` and toggles the checkbox — reuse its render helper and the phone-input query approach). Do not assert on total element counts. If the existing tests mock `next/navigation`, keep that mock. Create a fresh `QueryClient` with `retry: false` per test only if the form requires a provider (check the existing tests — mirror exactly what they do).

---

## Final Verification

> ❌ **BANNED**: `npx vitest run` — never use it. The only correct runner is `pnpm --filter web test`.

### Phase 1 — Targeted (during development)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/customers/components/__tests__/CustomerForm.test.tsx 2>&1 | tail -10
```

### Phase 2 — Full verification (once, at the end)

```bash
cd <repo>/frontend && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== DLC-B2 FE FINAL VERIFICATION COMPLETE ==="
```

> This batch touches only `apps/web` — the UI and mobile packages are unaffected, so the web-only Phase 2 above is sufficient. Any failure must be fixed before done.

---

## Definition of Done — DLC-B2 (Frontend)

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `CustomerForm.tsx` read in full before editing
- [ ] **STEP 1**: disclosure paragraph added inside the consent block with `data-testid="customer-sms-consent-disclosure"`, all 7 required elements present, privacy-policy link functional
- [ ] Attestation checkbox behavior unchanged (submit gating + warning still work)
- [ ] No new component created in `packages/ui`; no new npm dependency; no new hook
- [ ] 3 tests added to `CustomerForm.test.tsx` (renders-with-phone, hidden-without-phone, privacy-link-href)
- [ ] Zero TypeScript errors (`pnpm --filter web check-types`)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 web verification passes** (`=== DLC-B2 FE FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B
- [ ] Notify Tom that the disclosure is deployed so he can take the customer-consent compliance screenshot (playbook §11)

---

## Completion Summary

After all DoD items are complete, add a Completion Summary to `pilot-launch-plan.md` Appendix B:

```markdown
### DLC-B2 (Frontend) — Customer SMS Consent Disclosure: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+3 passed (+3 new tests)

#### What Was Accomplished
- Added consumer-facing 10DLC disclosure paragraph to the customer create/edit consent block
- `data-testid="customer-sms-consent-disclosure"` with program name, message types, frequency, rates, STOP/HELP, privacy-policy link

#### Files Changed / Created
| File | Action |
|---|---|
| `frontend/apps/web/src/features/customers/components/CustomerForm.tsx` | Updated — added disclosure paragraph |
| `frontend/apps/web/src/features/customers/components/__tests__/CustomerForm.test.tsx` | Updated — +3 tests |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/customers/components/__tests__/CustomerForm.test.tsx` | Unit | 3 | ✅ |
```

---

## After This Task — Next Step

Once both DLC-B2 halves (backend + this) are merged and deployed to production, Tom:
1. Takes the customer-consent compliance screenshot (`/customers/new` with a phone entered) → uploads to `pilotfortrades.com/compliance/customer-sms-consent.png`.
2. Submits the Mixed campaign per `telnyx-10dlc-customer-comms-campaign.md`.
3. After approval, buys 1 Telnyx number and runs the end-to-end test (playbook §13) — closing **10DLC Steps 2 & 3** in the launch plan.
