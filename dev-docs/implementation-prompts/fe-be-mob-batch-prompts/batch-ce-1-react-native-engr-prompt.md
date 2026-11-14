# Implementation Prompt: CE-1 (Part B) — Mobile Invoice Sign-Off Signature Capture (React Native)

**Mode**: Pilot React Engineer
**Batch**: CE-1 — Part B (Mobile)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 CE-1 (Beta Execution Order 1)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ce-1-design.md` — §D (endpoint contracts), §F.2 (hook interface), §G (resolved decisions), §I Part B (component manifest)
**UI design spec (Tom-approved)**: `dev-docs/architecture-design/batch-designs/batch-ce-1-mobile-ui-design-spec.md` — **the pixel/state authority for everything you build.** S1 = §3, S2 = §4, haptics = §5, accessibility = §6 (mandatory), implementation notes = §8
**Estimated session**: 2.5–3.5 hours
**Platform**: Mobile only (`apps/mobile/`)
**Backend companion**: **CE-1 Part A (Python) MUST be merged first** (`batch-ce-1-python-engr-prompt.md`). The endpoints you consume (`GET /api/v1/jobs/{job_id}/signoff-context`, `POST /api/v1/invoices/{invoice_id}/signoff`) do not exist until then. Your first Pre-Work step (`pnpm sync-api-types`) is the verification that Part A landed — if the endpoints are absent from `openapi_schema_map.md` → **STOP; Part A is not merged.**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`batch-ce-1-mobile-ui-design-spec.md`** — every section; you implement against its pixel specs, state tables, testIDs, and accessibility labels **verbatim**
- **`batch-ce-1-design.md`** — §D/§F/§G/§I

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If NOT there → **STOP and ask Tom** (Part A likely not merged).
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` / the generated types.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all payload types come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any shared component — this batch adds **zero** `packages/ui` components (design §I); `PendingBadge` is composed, not recreated.
- **Rule 8**: No new npm dependencies without checking `package.json` first — **single Tom-approved exception**: `react-native-signature-canvas` (Rule 9.8 approval recorded 2026-08-12; see Step 0).
- **Rule 10**: If ANY test fails during your work — even apparently pre-existing — fix it before declaring done. No "not my fault" exception. Root-cause unreachable → STOP and ask Tom.
- **Offline-first (non-negotiable product rule)**: Save MUST succeed with zero connectivity. The base64 PNG rides the WatermelonDB mutation queue inline (design §G-R5) — never a presigned-PUT-then-confirm flow.

**Invoice status "overdue" rule:** `invoice_status` has NO `overdue` code; signable statuses are exactly `issued`/`partial`, gated server-side. Never send status filters; consume the context response as-is.

---

## Design Decisions (Do Not Re-Litigate)

From design doc §G — final:

| Decision | Outcome | Rationale |
|---|---|---|
| Signature transport | **base64 PNG inline in the mutation payload** (~20–60KB) | Offline-first; presigned PUT requires connectivity at capture (R5) |
| Re-capture | **Supersede**, never 409-on-duplicate (idempotency key dedupes true replays) | Field reality: wrong name / customer re-signs (R4) |
| Capture permission | Rides `jobs.update`; context rides `jobs.view` | Techs are excluded from `invoices.*` (R3) |
| Tech sees invoice total | **Deliberate** — amount is inside the terms text being signed | Customer-present transaction (R3) |
| `react-native-signature-canvas` | **Tom-approved 2026-08-12** (Rule 9.8) | Mature, Expo-compatible, base64 PNG output (R7) |
| Public `/i/[token]` signature display | **Deferred** to CE-1-FU — do not touch the public page | Two-spec designer gate (R2) |
| Owner "invoice signed" notification | **Deferred** — do not add | Batch-size discipline (R8) |

Do NOT change these without asking Tom.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact count. Any pre-existing failure → fix or confirm with Tom before starting.

## Pre-Work: Sync API Types (the Part A handoff signal — Rule 9.3)

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Then confirm the generated types exist:

```bash
grep -n "SignoffContextResponse\|InvoiceSignoffCreateRequest\|InvoiceSignoffResponse" packages/shared-types/src/api-schema.d.ts
```

Missing → STOP (Part A not merged). Consume via `import type { components } from "@pilot/shared-types"; type SignoffContextResponse = components["schemas"]["SignoffContextResponse"];`

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "signoff-context" backend/openapi_schema_map.md
grep -A 5 "signoff" backend/openapi_schema_map.md | head -40
```

| Hook | Endpoint | Verified |
|---|---|---|
| `useSignoffContext` | `GET /api/v1/jobs/{job_id}/signoff-context` | ☐ confirm before coding |
| (sync-engine push) | `POST /api/v1/invoices/{invoice_id}/signoff` | ☐ confirm before coding |

## Pre-Work: Read These Source Files

```
dev-docs/architecture-design/batch-designs/batch-ce-1-mobile-ui-design-spec.md  ← build authority (pixels, states, testIDs, a11y)
frontend/apps/mobile/features/jobs/components/JobDetailScreen.tsx             ← mount point (spec §8.5: after PhotoSection ~line 306)
frontend/apps/mobile/features/jobs/components/detail/JobNotesSection.tsx      ← section container pattern you mirror
frontend/apps/mobile/features/jobs/components/detail/PhotoSection.tsx         ← sibling section; placement reference
frontend/apps/mobile/features/offline-sync/hooks/useCreateJobNote.ts          ← offline-mutation pattern (exact mirror for useCreateInvoiceSignoff)
frontend/apps/mobile/database/schema.ts                                       ← WatermelonDB schema — add invoice_signoffs table
frontend/apps/mobile/database/models/JobNote.ts                               ← model pattern reference (verify actual base class/decorators)
frontend/apps/mobile/database/sync/orchestrator.ts                            ← sync push registration (follow job_notes entry)
frontend/apps/mobile/app/(tabs)/_layout.tsx                                   ← tab suppression for the new capture route
frontend/apps/mobile/app/(tabs)/jobs/                                         ← route structure for [jobId]/invoice-signoff.tsx
frontend/apps/mobile/constants/style-constants.ts                             ← design tokens (never hardcode hex/px)
frontend/packages/ui/src/index.ts                                             ← confirm PendingBadge export name/variant props
frontend/apps/mobile/mocks/handlers/index.ts                                  ← MSW barrel — registration pattern
```

Also run: `find frontend/apps/mobile/mocks/handlers -name "*.ts" | head -20` and `grep -rn "PendingBadge" frontend/apps/mobile --include="*.tsx" -l | head -5` (existing mobile PendingBadge usage to mirror).

---

## Step 0 — Install the Tom-approved dependency (Rule 9.8 approval 2026-08-12)

```bash
cd <repo>/frontend
grep -n "react-native-webview\|react-native-signature-canvas" apps/mobile/package.json
pnpm --filter mobile add react-native-signature-canvas
```

`react-native-signature-canvas` is WebView-based: if `react-native-webview` is absent, add the Expo-SDK-54-compatible version (`pnpm --filter mobile add react-native-webview` — accept the version Expo pins). **Native dependency → the dev client must be rebuilt (EAS build / `npx expo prebuild`) before Tom can run this on a device.** Note this in your Completion Summary as an ops follow-up for Tom. Jest tests never load the real WebView — see Step 7 mock.

## Step 1 — WatermelonDB: `invoice_signoffs` local table + sync registration

Per spec §8.2 and the inclusions §8.2 mobile constraints:

- `database/models/InvoiceSignoff.ts` — mirror `JobNote.ts` exactly (same base class/decorators you find there). Fields per spec: `invoiceId`, `signedByName`, `termsAcknowledged`, `signaturePngBase64` (string), `capturedBy`, `localSyncStatus`, `idempotencyKey`, `clientCaptureAt`, `syncError`, `retryCount`.
- `database/schema.ts` — register the `invoice_signoffs` table (bump schema version per the file's existing convention).
- `database/sync/orchestrator.ts` — register the push mapping alongside `job_notes`: `invoice_signoffs` → `POST /api/v1/invoices/{invoice_id}/signoff` with `Idempotency-Key: record.idempotencyKey` header and body `{ signed_by_name, terms_acknowledged, signature_png_base64, client_capture_at }` (snake_case per the generated request type). On 200 → mark synced (store returned `signoff_id` if the orchestrator pattern keeps server IDs). On 409 → refetch context + mark resolved per the sync-engine's existing conflict path (spec §8.4 §16.4 note). Read the orchestrator's `job_notes` entry and copy its exact mechanics — do not invent a new registration style.

Intermediate: `pnpm --filter mobile build` (type check) must pass.

## Step 2 — `useSignoffContext` hook

`features/jobs/hooks/useSignoffContext.ts` (spec §8.1): TanStack Query v5 object-form; `queryKey: ["job-signoff-context", jobId]`; `queryFn` → `apiClient.get<SignoffContextResponse>(\`/api/v1/jobs/${jobId}/signoff-context\`)`; `retry: false`; `staleTime: 30_000`; type from `@pilot/shared-types`. Return `{ data, isPending, isError, refetch }`.

## Step 3 — `useCreateInvoiceSignoff` offline mutation hook

`features/offline-sync/hooks/useCreateInvoiceSignoff.ts` — **mirror `useCreateJobNote.ts` exactly**: `database.write(() => database.get<InvoiceSignoff>("invoice_signoffs").create(...))` setting `localSyncStatus: "pending"`, a generated `idempotencyKey` (copy the `generateIdempotencyKey()` helper — if two copies would exist after this batch, extract to a shared util per the file's existing conventions), `clientCaptureAt: new Date()`. Input interface per spec §8.1 (`CreateInvoiceSignoffInput`). Return `{ create, isPending, error }`.

## Step 4 — `InvoiceSignoffSection` (S1)

`features/jobs/components/detail/InvoiceSignoffSection.tsx` — implement spec §3 **verbatim**: container card tokens, "INVOICE SIGN-OFF" title, multi-invoice selector pills (default index 0), invoice number + amount row (**money-from-cents**: `total_cents / 100` via `Intl.NumberFormat("en-US", { style: "currency", currency: "USD" })` — never raw cents), status sub-line, "Capture Signature" CTA, signed summary + "Re-capture", `PendingBadge` composition (pending/syncing/failed variants), all eight states from the §3.3 table with the exact `testID`s. Props: `{ jobId: string; userId: string; testID?: string }` (adjust to what `JobDetailScreen` actually passes). Hidden state renders `null`.

## Step 5 — `InvoiceSignoffCaptureScreen` (S2) + route + tab suppression

- Route: `app/(tabs)/jobs/[jobId]/invoice-signoff.tsx` (verify the jobs route folder layout first; thin route file rendering the feature screen, params `jobId` + `invoiceId` via `useLocalSearchParams`).
- Screen component `features/jobs/components/detail/InvoiceSignoffCaptureScreen.tsx` — spec §4 verbatim: header bar, invoice context line, prominent bold total (display-size token), printed-name `TextInput` (maxLength 200), scrollable terms (`terms_text` from context), acknowledge checkbox (44×44 hit-slop wrapper), 220px white canvas wrapping `<SignatureCanvas>` (cache base64 from `onOK`; `onEmpty` → gate #3; `ref.clearSignature()` for Clear), Save gated on all three gates (spec §4.2), success overlay + haptics per spec §5 (`Vibration.vibrate(40)` success / `[0, 200, 100, 200]` failure; `AccessibilityInfo.announceForString` per §6.4), then `router.back()`.
- Save flow (spec §4.3): call `useCreateInvoiceSignoff.create({...})` — local write only; the sync engine pushes. Never await connectivity.
- Register the route's tab suppression in `app/(tabs)/_layout.tsx` per its existing pattern.

## Step 6 — Mount S1 in `JobDetailScreen.tsx`

Per spec §8.5: `<InvoiceSignoffSection jobId={userId…} />` after `<PhotoSection>` (~line 306), before the "Message Customer" row. Read the file first — adjust prop names to what the screen has in scope.

## Step 7 — MSW handlers + Tests

**MSW** (new domain handlers — registration in the barrel is mandatory):
`apps/mobile/mocks/handlers/invoiceSignoffHandlers.ts` — `http.get("/api/v1/jobs/:jobId/signoff-context", ...)` returning a fixture with: one `issued` invoice (no signoff), and cover variety per the seed-awareness note below; `http.post("/api/v1/invoices/:invoiceId/signoff", ...)` returning a 200 `InvoiceSignoffResponse`-shaped fixture. Register `...invoiceSignoffHandlers` in `mocks/handlers/index.ts`.

**Seed-data awareness (inclusions §18)**: Part A seeds a real signoff row + an overpaid payment. Your MSW fixtures must carry **varied** states — at minimum: (a) single invoice, `active_signoff: null`; (b) invoice with `active_signoff` populated; (c) multi-invoice context (2+ invoices) — so every S1 state is exercisable. Never assert by count.

**Canvas mock** (WebView can't load in Jest):
```typescript
jest.mock("react-native-signature-canvas", () => {
  const React = require("react");
  const { View } = require("react-native");
  return React.forwardRef((_props: any, ref: any) => {
    React.useImperativeHandle(ref, () => ({
      clearSignature: jest.fn(),
      getData: jest.fn(() => "iVBORw0KGgo="), // tiny valid base64 stub
    }));
    return <View testID="signoff-canvas" />;
  });
});
```
Drive gate behavior by invoking the `onOK`/`onEmpty` props your mock captures.

**Unit tests** (co-located `__tests__/`, Jest globals — NO vitest imports; `.toBeTruthy()` assertions; `fireEvent.press`; fresh `QueryClient` per test with `retry: false`; MSW `setupServer` + `server.resetHandlers()` in `afterEach`; mock `expo-router` AND the `database` module per the inclusions §8.2 patterns):
- `InvoiceSignoffSection.test.tsx` — hidden on empty invoices; ready state renders CTA; multi-invoice pills render + default selection; signed state shows summary + Re-capture; error state + retry calls `refetch`; loading state testID.
- `InvoiceSignoffCaptureScreen.test.tsx` — Save disabled until all three gates; name input enables gate 1; acknowledge toggles gate 2; canvas `onOK` enables gate 3; Save calls the create hook with the exact input shape; success path fires navigation back; Clear calls `clearSignature`.
- `useSignoffContext.test.tsx` + `useCreateInvoiceSignoff.test.tsx` — data shape, error state, query-key construction; local write sets `localSyncStatus "pending"` + `idempotencyKey` + `clientCaptureAt`.

**Integration tests** — `apps/mobile/__tests__/batch_ce_1/invoice_signoff.integration.test.tsx` (mobile integration tests live in batch folders, never co-located): job detail renders the section with MSW data (route does not 404); capture-screen route renders; full save flow enqueues the mutation (assert the sync-orchestrator push fires `POST` to the right URL with the `Idempotency-Key` header — MSW request assertion).

---

## Final Verification

> ❌ **BANNED**: `npx vitest run` in any form. Mobile tests run via `pnpm --filter mobile test` only.

### Phase 1 — Targeted (after each step)

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
pnpm --filter mobile test -- features/jobs/components/detail/__tests__/InvoiceSignoffSection.test.tsx 2>&1 | tail -10
```

### Phase 2 — Full canonical command (once, at the end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

Any failure in either phase → fix before done. (`pnpm --filter mobile build` IS the mobile type check — no `check-types` script exists.)

---

## Definition of Done — CE-1 Part B

- [ ] Regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run; `SignoffContextResponse` / `InvoiceSignoffCreateRequest` / `InvoiceSignoffResponse` confirmed in `api-schema.d.ts`
- [ ] Both endpoints verified in `openapi_schema_map.md` (Part A merged)
- [ ] Design doc + mobile UI spec fully read before coding; all mandatory source files read
- [ ] Step 0: dependency installed (Tom approval 2026-08-12 recorded); EAS dev-client rebuild flagged to Tom in Completion Summary
- [ ] Step 1: `InvoiceSignoff.ts` model + `schema.ts` row + orchestrator push registration (mirrors `job_notes` mechanics)
- [ ] Steps 2–3: hooks per spec §8.1 (TanStack Query v5 object-form, `retry: false`, colocated key; types from `@pilot/shared-types`)
- [ ] Step 4: S1 matches spec §3 — all 8 states, exact testIDs, token-only styling, PendingBadge composed
- [ ] Step 5: S2 matches spec §4 — 3-gate Save, canvas white/`neutral[50]`, haptics + a11y announcements per §5/§6; route + tab suppression registered
- [ ] Step 6: mounted after `PhotoSection` in `JobDetailScreen.tsx`
- [ ] Step 7: MSW handlers registered in `index.ts`; unit tests per component/hook; integration test in `__tests__/batch_ce_1/`; canvas + expo-router + WatermelonDB mocked; `retry: false`; no real DB writes
- [ ] Accessibility: all spec §6.1 labels/roles applied; target sizes ≥44pt; screen-reader announcements wired (rules §36 spirit — mobile)
- [ ] Zero new `packages/ui` components; zero hand-written payload interfaces; zero hardcoded hex/px
- [ ] **Phase 1** targeted tests pass; **Phase 2** full canonical command passes (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix C

---

## Completion Summary

Add to `dev-docs/analysis/pilot-launch-plan.md` **Appendix C**:

```markdown
### CE-1 (Part B) — Mobile Invoice Sign-Off Capture: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer (mobile)
**Baseline**: X passed (mobile)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished
- …

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|

#### Ops Follow-Up
- Native dependency added (react-native-signature-canvas — Tom-approved 2026-08-12): EAS dev-client rebuild required before on-device testing.
```

---

## After This Task — Next Step

This is **Part B of 3**. Remaining: Part C (web) — invoice detail sign-off card + overpayment review banner + partial-pay E2E verification — runs after the web-ui designer spec (H2+H3) is Tom-approved. Your Completion Summary is the signal that mobile is done; the Architect handles plan status updates.
