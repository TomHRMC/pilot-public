# Batch CE-1 — Mobile UI Design Spec: Invoice Sign-Off Signature Capture

**Batch code**: CE-1 (launch plan §2.3, Beta Execution Order 1)
**Surface**: H1 — Mobile (React Native / Expo field app)
**Date**: 2026-08-12
**Author**: Pilot Voice UI Designer
**Status**: DRAFT — pending Tom approval
**Parent design**: `batch-ce-1-design.md` §H1 (row H1 only) + §I "Part B — Mobile" component manifest
**Scope**: S1 `InvoiceSignoffSection` (job-detail entry) + S2 `InvoiceSignoffCaptureScreen` (full-screen capture flow). Does **not** cover H2/H3/H4.

---

## 0. Open Gate — Expo Native Dependency (Rule 9.8)

> ⚠️ **`react-native-signature-canvas` is pending Tom's Rule 9.8 approval before install.**
> This spec designs against the library's documented API regardless of approval state. The RN engineer prompt (authored only after Tom approves this spec) restates the gate. No code ships until approval is recorded.

**Library API referenced** (v4.x, WebView-based):
- `<SignatureCanvas ref={…} onLoad={…} onOK={(base64) => …} onEmpty={…} … />`
- `ref.current.clearSignature()` — clears the canvas
- `ref.current.getData()` — returns base64 PNG data string
- `onOK` fires with `{ data: "<base64-png>" }` on a successful read
- `onClear` / `onEmpty` fire when the canvas is cleared or has no strokes

The canvas outputs **base64 PNG** (no raw stroke arrays). The Save flow reads base64 via `getData()` / `onOK` and passes it inline through the offline mutation (§E pattern, §G-R5).

---

## 1. Surface Overview

### S1 — `InvoiceSignoffSection` (job-detail entry point)

| Attribute | Value |
|---|---|
| Route / mount | Mounted inside `JobDetailScreen.tsx` `ScrollView`, as a new section sibling to `ClockInOutSection` / `PhotoSection` / `JobNotesSection`. Placed **after** `PhotoSection` (Section 7) and **before** the "Message Customer" link (Section 8). |
| Who sees it | Field technicians (role: `tech`). The section fetches `GET /api/v1/jobs/{job_id}/signoff-context` (D.1, auth `jobs.view`). |
| Visibility rule | Visible **only** when the context response returns ≥1 signable invoice (status `issued`/`partial`). Hidden/empty state renders nothing (no card, no spacer) when `invoices.length === 0`. |
| Data source | `useSignoffContext(jobId)` — TanStack Query wrapper on D.1 (`retry: false`, `staleTime: 30_000`). |
| Multiple invoices | If `invoices.length > 1`, a selection affordance (horizontal pill row) is shown; default selection = newest (index 0, server-ordered newest-first). |

### S2 — `InvoiceSignoffCaptureScreen` (full-screen capture flow)

| Attribute | Value |
|---|---|
| Route / entry | Pushed via `router.push("/(tabs)/jobs/{jobId}/invoice-signoff?invoiceId={invoiceId}")` from S1's CTA. Full-screen modal-style (own `SafeAreaView`, no job-detail scroll context). |
| Who sees it | Field technicians (role: `tech`). Capture rides `POST /api/v1/invoices/{invoice_id}/signoff` (D.2, auth `jobs.update`). |
| Offline-first | Save **always succeeds locally** and queues via `useCreateInvoiceSignoff` (WatermelonDB `invoice_signoffs` table → sync engine push). The user never needs connectivity at capture time. |
| Exit | Back/cancel returns to `JobDetailScreen`; S1 refetches context on focus. |

---

## 2. Design Token Reference (grounded in `tokens.ts`)

All specs reference tokens — **zero hardcoded hex** in implementation.

| Token | Value | Used for |
|---|---|---|
| `colors.neutral[900]` | `#1C1917` | Screen background (dark theme default for mobile) |
| `colors.neutral[800]` | `#292524` | Card / raised surface (section container) |
| `colors.neutral[600]` | `#57534E` | Borders (default) |
| `colors.neutral[400]` | `#A8A29E` | Secondary text, captions, placeholders |
| `colors.neutral[50]` | `#FAFAF9` | Primary text on dark surfaces |
| `colors.brand[400]` | `#6875F5` | Brand text/links on dark |
| `colors.brand[600]` | `#3B43D6` | Primary button fill (CTA) |
| `colors.margin[600]` | `#059669` | Success (signed confirmation, green check) |
| `colors.margin[400]` | `#34D399` | Success accent on dark |
| `colors.alert[400]` | `#F59E0B` | Pending-sync badge (amber) |
| `colors.fault[600]` | `#DC2626` | Error / sync-failed |
| `colors.fault[400]` | `#F87171` | Error accent on dark |
| `mobileFontSizes.caption` | 11 | Section titles, meta |
| `mobileFontSizes.body` | 13 | Default body, button text |
| `mobileFontSizes.bodyLg` | 15 | Invoice amount (prominent) |
| `mobileFontSizes.h3` | 17 | Screen title |
| `mobileFontSizes.h2` | 20 | Signer name summary |
| `mobileFontSizes.h1` | 22 | (reserved) |
| `mobileFontSizes.display` | 28 | Invoice total (bold, prominent line) |
| `fontWeights.medium` | 500 | Bold weights for amounts, button text, section titles |
| `fontWeights.regular` | 400 | Body copy |
| `spacing[3]` | 12 | Minimum inter-target separation (glove rule) |
| `spacing[4]` | 16 | Card padding, default gap |
| `radii.md` | 8 | Buttons, inputs, small cards |
| `radii.lg` | 12 | Section cards |
| `touchTargets.mobile.md` | 56 | Default mobile button height (glove-friendly) |
| `touchTargets.mobile.sm` | 44 | Minimum touch target (glove rule floor) |
| `motion.duration.voiceSuccess` | 800ms | Green-check confirmation persistence |
| `motion.duration.fast` | 150ms | Press-state transitions |

**Glove rule compliance**: every interactive target ≥ `touchTargets.mobile.sm` (44pt). Default buttons use `touchTargets.mobile.md` (56pt). Inter-target separation ≥ `spacing[3]` (12pt).

**Contrast**: dark theme is the mobile default (outdoor/sunlight-readable). All text/surface pairings meet WCAG AAA 7:1 (e.g. `neutral[50]` on `neutral[900]` ≈ 16:1; `neutral[50]` on `neutral[800]` ≈ 12:1).

---

## 3. S1 — `InvoiceSignoffSection` Spec

### 3.1 Layout & Pixel Specs

Container card — matches the existing section pattern in `JobNotesSection.tsx`:

| Element | Spec |
|---|---|
| Container | `backgroundColor: colors.neutral[800]`, `borderRadius: radii.lg` (12), `padding: spacing[4]` (16), `marginBottom: spacing[3]` (12), `gap: spacing[3]` (12) |
| Section title | "INVOICE SIGN-OFF", `fontSize: mobileFontSizes.caption` (11), `fontWeight: fontWeights.medium`, `color: colors.neutral[400]`, `textTransform: "uppercase"`, `letterSpacing: 0.5`, `lineHeight: 16` |
| Invoice selector pills (multi-invoice) | Horizontal `ScrollView` row, `gap: spacing[2]` (8), `marginBottom: spacing[1]`. Each pill: `minHeight: touchTargets.mobile.sm` (44), `paddingHorizontal: spacing[3]` (12), `borderRadius: radii.full`, `borderWidth: 1`. Selected pill: `backgroundColor: colors.brand[600]`, `borderColor: colors.brand[600]`, text `colors.neutral[50]`. Unselected: `backgroundColor: colors.neutral[900]`, `borderColor: colors.neutral[600]`, text `colors.neutral[400]`. Pill text: `fontSize: mobileFontSizes.body` (13), `fontWeight: fontWeights.medium`. |
| Invoice number + amount row | `flexDirection: "row"`, `justifyContent: "space-between"`, `alignItems: "center"`. Invoice number: `fontSize: mobileFontSizes.body` (13), `color: colors.neutral[50]`. Amount: `fontSize: mobileFontSizes.bodyLg` (15), `fontWeight: fontWeights.medium`, `color: colors.neutral[50]` (bold per glove rule §3). |
| Status sub-line | `fontSize: mobileFontSizes.caption` (11), `color: colors.neutral[400]`. Shows `status` + `balance_due` (e.g. "Issued · $1,250.00 due"). |
| CTA button ("Capture Signature") | `backgroundColor: colors.brand[600]`, `borderRadius: radii.md` (8), `minHeight: touchTargets.mobile.md` (56), `alignItems: "center"`, `justifyContent: "center"`. Text: "✍ Capture Signature", `fontSize: mobileFontSizes.body` (13), `fontWeight: fontWeights.medium`, `color: colors.neutral[50]`. |
| Signed summary block | `backgroundColor: colors.neutral[900]`, `borderRadius: radii.md`, `padding: spacing[3]` (12), `gap: spacing[1]`. Signer name: `fontSize: mobileFontSizes.h2` (20), `fontWeight: fontWeights.medium`, `color: colors.neutral[50]`. Signed-at: `fontSize: mobileFontSizes.caption`, `color: colors.neutral[400]`. |
| Re-capture affordance | Text button "Re-capture", `minHeight: touchTargets.mobile.sm` (44), `color: colors.brand[400]`, `fontSize: mobileFontSizes.body`, `fontWeight: fontWeights.medium`. |
| PendingBadge | Composed from `packages/ui` `PendingBadge` (`count`, `variant`). Placed inline-right of the signed summary header. `variant="pending"` (amber) while queued; `variant="syncing"` while in flight; `variant="failed"` on error. |

### 3.2 Money Formatting

All amounts use **money-from-cents**: `total_cents / 100`, formatted as USD (`Intl.NumberFormat("en-US", { style: "currency", currency: "USD" })`). Never display raw cents.

### 3.3 S1 State Coverage

| State | Trigger | Render |
|---|---|---|
| **loading** | `useSignoffContext` `isLoading === true` | Skeleton: section title + a `ActivityIndicator` (`colors.brand[400]`) centered in the card area. `testID="signoff-section-loading"`. |
| **hidden / empty** | Context resolved with `invoices.length === 0` | Render `null` (no card, no spacer). Section entirely absent from the scroll. |
| **error** | `useSignoffContext` `isError === true` (or 403/404) | Card with title + error text "Couldn't load invoice sign-off." + "Try again" button (`minHeight: 44`, `colors.brand[600]`). Button calls `refetch()`. `testID="signoff-section-error"`. |
| **ready-to-capture** (single invoice) | 1 invoice, `active_signoff === null` | Invoice number + amount row + status sub-line + "Capture Signature" CTA. `testID="signoff-section-ready"`. |
| **ready-to-capture** (multi-invoice) | >1 invoice, selected invoice `active_signoff === null` | Selector pills (default = index 0) + selected invoice's number/amount/status + CTA. `testID="signoff-section-multi"`. |
| **already-signed** | Selected invoice `active_signoff !== null` | Signed summary block (signer `signed_by_name` + `signed_at` formatted) + `PendingBadge` (if local row pending) + "Re-capture" text button. `testID="signoff-section-signed"`. |
| **pending-sync** | Local WatermelonDB row exists with `localSyncStatus === "pending"` for the selected invoice | Signed summary block + `PendingBadge` `variant="pending"` `count={1}`. CTA hidden (already captured). `testID="signoff-section-pending"`. |
| **sync-error / retry** | Local row `localSyncStatus === "failed"` | Signed summary block + `PendingBadge` `variant="failed"` + inline "Retry sync" text button (`minHeight: 44`, `colors.fault[400]`). Tapping retries the sync-engine push (not a re-capture). `testID="signoff-section-sync-error"`. |

### 3.4 S1 Interaction Spec

| Element | default | pressed | disabled | loading | error |
|---|---|---|---|---|---|
| Selector pill (unselected) | `neutral[900]` bg, `neutral[600]` border | `neutral[600]` border, `opacity: 0.8` | N/A | N/A | N/A |
| Selector pill (selected) | `brand[600]` bg, `neutral[50]` text | `brand[800]` bg | N/A | N/A | N/A |
| Capture CTA | `brand[600]` bg | `brand[800]` bg, `opacity: 0.9` | `opacity: 0.4` (when context loading) | `ActivityIndicator` replaces text | N/A |
| Re-capture text button | `brand[400]` text | `brand[200]` text | N/A | N/A | N/A |
| Retry-sync text button | `fault[400]` text | `fault[200]` text | `opacity: 0.4` (while retrying) | `ActivityIndicator` (small) | N/A |

Press transitions: `motion.duration.fast` (150ms), `motion.easing.standard`.

---

## 4. S2 — `InvoiceSignoffCaptureScreen` Spec

### 4.1 Screen Layout (top → bottom)

Full-screen `SafeAreaView`, `backgroundColor: colors.neutral[900]`. Content in a `ScrollView` (`keyboardShouldPersistTaps="handled"`) so the terms text can scroll independently of the screen scroll when the keyboard is open.

| # | Element | Spec |
|---|---|---|
| 1 | **Header bar** | `flexDirection: "row"`, `alignItems: "center"`, `padding: spacing[4]`, `borderBottomWidth: 1`, `borderBottomColor: colors.neutral[800]`. Back button "← Back" (`minHeight: 44`, `colors.brand[400]`). Title "Sign Invoice" `fontSize: mobileFontSizes.h3` (17), `fontWeight: fontWeights.medium`, `color: colors.neutral[50]`. |
| 2 | **Invoice context line** | `padding: spacing[4]`, `gap: spacing[1]`. Invoice number `fontSize: mobileFontSizes.body`, `color: colors.neutral[400]`. Customer name (`customer_display_name` from context) `fontSize: mobileFontSizes.body`, `color: colors.neutral[50]`. |
| 3 | **Invoice total — prominent bold line** | `paddingHorizontal: spacing[4]`, `paddingTop: spacing[2]`, `paddingBottom: spacing[3]`. Label "Total Due" `fontSize: mobileFontSizes.caption`, `color: colors.neutral[400]`, `textTransform: "uppercase"`. Value: `fontSize: mobileFontSizes.display` (28), `fontWeight: fontWeights.medium`, `color: colors.neutral[50]` — **bold, prominent, above the canvas** (per hard constraint). Money-from-cents on `total_cents`. |
| 4 | **Customer printed-name field** | `paddingHorizontal: spacing[4]`, `paddingBottom: spacing[3]`. Label "Customer Printed Name" `fontSize: mobileFontSizes.caption`, `color: colors.neutral[400]`. `TextInput`: `backgroundColor: colors.neutral[800]`, `borderRadius: radii.md`, `borderWidth: 1`, `borderColor: colors.neutral[600]`, `minHeight: touchTargets.mobile.md` (56), `paddingHorizontal: spacing[3]`, `fontSize: mobileFontSizes.bodyLg` (15), `color: colors.neutral[50]`, `placeholder: "Type the customer's full name"`, `placeholderTextColor: colors.neutral[400]`, `maxLength: 200`. `testID="signoff-name-input"`. |
| 5 | **Terms text (scrollable)** | `paddingHorizontal: spacing[4]`, `paddingBottom: spacing[2]`. Label "Terms & Conditions" `fontSize: mobileFontSizes.caption`, `color: colors.neutral[400]`, `textTransform: "uppercase"`. Scroll container: `maxHeight: 200`, `backgroundColor: colors.neutral[800]`, `borderRadius: radii.md`, `padding: spacing[3]`, `borderWidth: 1`, `borderColor: colors.neutral[600]`. Terms text from `terms_text` (context response): `fontSize: mobileFontSizes.body` (13), `lineHeight: 20`, `color: colors.neutral[200]`. `testID="signoff-terms-scroll"`. |
| 6 | **Acknowledge control** | `paddingHorizontal: spacing[4]`, `paddingVertical: spacing[2]`, `flexDirection: "row"`, `alignItems: "center"`, `gap: spacing[3]`. Checkbox `Pressable`: `width: 28`, `height: 28` (inside a `minHeight: 44` / `minWidth: 44` hit-slop wrapper), `borderWidth: 2`, `borderColor: colors.neutral[400]`, `borderRadius: radii.sm`. Checked: `backgroundColor: colors.margin[600]`, `borderColor: colors.margin[600]`, inner "✓" `color: colors.neutral[50]`. Label: "Customer agrees to the terms" `fontSize: mobileFontSizes.bodyLg` (15), `fontWeight: fontWeights.medium`, `color: colors.neutral[50]`, `flex: 1`. `testID="signoff-acknowledge"`. |
| 7 | **Signature canvas** | `paddingHorizontal: spacing[4]`, `paddingBottom: spacing[3]`. Label "Signature" `fontSize: mobileFontSizes.caption`, `color: colors.neutral[400]`, `textTransform: "uppercase"`. Canvas wrapper: `height: 220`, `backgroundColor: colors.neutral[50]` (white canvas for ink contrast), `borderRadius: radii.md`, `borderWidth: 2`, `borderColor: colors.neutral[600]`. `<SignatureCanvas>` fills the wrapper. `testID="signoff-canvas"`. |
| 8 | **Clear button** | `paddingHorizontal: spacing[4]`, `paddingBottom: spacing[2]`. Text button "Clear Signature", `minHeight: touchTargets.mobile.sm` (44), `alignSelf: "flex-start"`, `color: colors.neutral[400]`, `fontSize: mobileFontSizes.body`. Calls `ref.current.clearSignature()`. `testID="signoff-clear-button"`. |
| 9 | **Save button** | `paddingHorizontal: spacing[4]`, `paddingBottom: spacing[4]`. `backgroundColor: colors.brand[600]`, `borderRadius: radii.md`, `minHeight: touchTargets.mobile.md` (56), `alignItems: "center"`, `justifyContent: "center"`. Text "Save Signature", `fontSize: mobileFontSizes.body`, `fontWeight: fontWeights.medium`, `color: colors.neutral[50]`. `testID="signoff-save-button"`. |
| 10 | **Success overlay** (transient) | Absolute-fill overlay, `backgroundColor: colors.margin[600]` at `opacity: 0.95`, centered "✓" icon (100×100pt, `color: colors.neutral[50]`) + "Signature captured" text. Persists `motion.duration.voiceSuccess` (800ms) then dissolves. `testID="signoff-success-overlay"`. |

### 4.2 Save Gating

The Save button is **disabled** (visually + functionally) unless ALL three conditions hold:
1. Name field non-empty (trimmed length ≥ 1)
2. Acknowledge checkbox checked (`terms_acknowledged === true`)
3. Canvas non-empty (at least one stroke — tracked via `onOK`/`onEmpty` callbacks from `react-native-signature-canvas`)

| Save button state | Condition | Visual |
|---|---|---|
| disabled | Any gate unmet | `opacity: 0.4`, `onPress: undefined` |
| enabled | All gates met | `brand[600]` bg, full opacity |
| saving | Save in flight (local write) | `ActivityIndicator` (small, `colors.neutral[50]`) replaces text |
| error | Local write failed (rare — DB error) | Text "Save failed — try again", `colors.fault[400]` |

### 4.3 Save Flow (offline-first)

1. On Save press: read base64 PNG via `ref.current.getData()` (or use the cached value from the last `onOK` callback).
2. Call `useCreateInvoiceSignoff.create({ invoiceId, signedByName, termsAcknowledged: true, signaturePngBase64, capturedBy: userId })`.
3. The hook writes a WatermelonDB `invoice_signoffs` row (`localSyncStatus: "pending"`, `idempotencyKey`, `clientCaptureAt`) — mirrors `useCreateJobNote.ts`.
4. **Save always succeeds locally** — the user never waits on connectivity. The sync engine pushes `POST /api/v1/invoices/{invoice_id}/signoff` with `Idempotency-Key` + `client_capture_at` on reconnect (§E pattern, §G-R5).
5. On local-write success: fire **success haptic** (one short vibration — see §5) + show the green-check success overlay (800ms) + navigate back to `JobDetailScreen`.
6. S1 refetches context on focus → shows the signed summary with `PendingBadge`.

### 4.4 S2 State Coverage

| State | Trigger | Render |
|---|---|---|
| **default** | Screen mounted, gates unmet | All elements per §4.1; Save disabled. |
| **canvas-empty** | `onEmpty` fired (no strokes) | Save disabled; canvas border `colors.neutral[600]`. |
| **canvas-populated** | `onOK` fired (strokes present) | Save gate #3 met; canvas border unchanged. |
| **acknowledged** | Checkbox toggled on | Checkbox `margin[600]` fill + "✓"; gate #2 met. |
| **name-entered** | Name field trimmed length ≥ 1 | Gate #1 met. |
| **ready-to-save** | All 3 gates met | Save button enabled (`brand[600]`, full opacity). |
| **saving** | `useCreateInvoiceSignoff.isPending === true` | Save button shows `ActivityIndicator`; Clear disabled. |
| **success** | Local write resolved | Success overlay (800ms) + haptic + navigate back. |
| **save-error** | Local write rejected (DB error) | Save button text → "Save failed — try again" (`fault[400]`); user can retry. |
| **sync-pending** (post-save, on S1) | Handled by S1 pending-sync state | N/A on S2 (S2 navigates away on success). |

### 4.5 S2 Interaction Spec

| Element | default | pressed | disabled | loading | error |
|---|---|---|---|---|---|
| Back button | `brand[400]` text | `brand[200]` text | N/A | N/A | N/A |
| Name input | `neutral[800]` bg, `neutral[600]` border | `neutral[400]` border (focused) | N/A | N/A | `fault[400]` border (validation) |
| Acknowledge checkbox (unchecked) | `neutral[400]` border, transparent bg | `neutral[600]` border | N/A | N/A | N/A |
| Acknowledge checkbox (checked) | `margin[600]` bg + border, "✓" | `margin[800]` bg | N/A | N/A | N/A |
| Canvas | `neutral[50]` bg, `neutral[600]` border | N/A (drawing) | N/A | N/A | N/A |
| Clear button | `neutral[400]` text | `neutral[200]` text | `opacity: 0.4` (while saving) | N/A | N/A |
| Save button | `brand[600]` bg | `brand[800]` bg | `opacity: 0.4` (gates unmet) | `ActivityIndicator` | `fault[400]` text |

---

## 5. Animation & Haptic Spec

Per `voice-feedback-patterns.md` §3:

| Event | Visual | Haptic |
|---|---|---|
| Save success | Full-screen green-check overlay (100×100pt "✓", `colors.margin[600]` bg at 0.95 opacity), persists `motion.duration.voiceSuccess` (800ms), then dissolves. | **One short, crisp vibration** (`Vibration.vibrate(40)`). |
| Save failure | Save button text → "Save failed — try again" (`colors.fault[400]`); no overlay. | **Two long, heavy vibrations** (`Vibration.vibrate([0, 200, 100, 200])`). |
| Sync-error (S1) | `PendingBadge` `variant="failed"` (red). | None (passive — user taps Retry). |
| Press transitions | `opacity` / color shift, `motion.duration.fast` (150ms), `motion.easing.standard`. | None. |

The success overlay + haptic fire **on local-write success**, not on server sync confirmation — because the capture is offline-first and the user must receive immediate confirmation that their signature is saved (per voice-feedback "No-Guessing" mandate §1).

---

## 6. Accessibility Notes (mandatory)

### 6.1 Labels

| Element | `accessibilityLabel` | `accessibilityRole` |
|---|---|---|
| S1 section | "Invoice sign-off" | `header` (on title) |
| S1 Capture CTA | "Capture customer signature for invoice {invoice_number}" | `button` |
| S1 Re-capture | "Re-capture signature" | `button` |
| S1 Retry-sync | "Retry syncing signature" | `button` |
| S1 PendingBadge | "{count} signature pending sync" (default from `PendingBadge`) | N/A |
| S2 Back | "Go back to job detail" | `button` |
| S2 Name input | "Customer printed name" | `none` (TextInput) |
| S2 Terms scroll | "Terms and conditions" | `none` |
| S2 Acknowledge | "Customer agrees to the terms" | `checkbox` |
| S2 Canvas | "Signature pad — draw the customer's signature" | `none` |
| S2 Clear | "Clear signature" | `button` |
| S2 Save | "Save signature" (or "Save signature, disabled" when gated) | `button` |
| S2 Success overlay | "Signature captured successfully" | `alert` |

### 6.2 Focus Order (S2)

1. Back button
2. Name input (auto-focus on mount optional — prefer not, to avoid keyboard covering the canvas)
3. Terms scroll
4. Acknowledge checkbox
5. Canvas
6. Clear button
7. Save button

### 6.3 Target Sizes

All interactive elements ≥ `touchTargets.mobile.sm` (44×44pt). Default buttons ≥ `touchTargets.mobile.md` (56pt). The 28×28pt checkbox visual sits inside a 44×44pt hit-slop wrapper. Inter-target separation ≥ `spacing[3]` (12pt) throughout.

### 6.4 Screen-Reader Announcements

- On Save success: announce "Signature captured for {invoice_number}. It will sync when you're back online." (via `AccessibilityInfo.announceForString`).
- On Save failure: announce "Save failed. Please try again."
- On gate-blocked Save attempt (user taps disabled Save): announce which gate is unmet — "Enter the customer's name" / "Acknowledge the terms" / "Draw a signature".
- On sync-error (S1): the `PendingBadge` `accessibilityLabel` conveys state; the Retry button label is self-describing.

### 6.5 Contrast

Dark theme (mobile default) — all text/background pairings meet WCAG AAA 7:1. The white canvas (`neutral[50]`) with ink strokes provides maximum contrast for signature capture in direct sunlight.

---

## 7. Component Manifest (matches §I "Part B — Mobile" exactly)

| Component / file | Destination | Change |
|---|---|---|
| `InvoiceSignoffSection.tsx` | `features/jobs/components/detail/` | NEW — job-detail entry; fetches D.1; renders CTA or active-sign-off summary; hides on empty |
| `InvoiceSignoffCaptureScreen.tsx` | `features/jobs/components/detail/` (or `app/` route per mobile nav convention) | NEW — full-screen capture: name field, terms scroll + acknowledge, `react-native-signature-canvas` canvas, Clear/Save |
| `useSignoffContext.ts` | `features/jobs/hooks/` | NEW — TanStack Query wrapper on D.1 (`retry: false`) |
| `useCreateInvoiceSignoff.ts` | `features/offline-sync/hooks/` | NEW — §F.2 offline mutation |
| WatermelonDB model + schema row | `database/models/InvoiceSignoff.ts`, `database/schema.ts` | NEW — local table `invoice_signoffs` with `localSyncStatus`, `idempotencyKey`, `clientCaptureAt`, base64 field |
| Sync-engine push registration | sync engine module (follow `job_notes` registration) | MODIFY |
| `JobDetailScreen.tsx` | `features/jobs/components/` | MODIFY — mount `InvoiceSignoffSection` |

**Zero new `packages/ui` components** (per §I component-existence check). `PendingBadge` is composed from `packages/ui`; no signature/canvas shared component is proposed.

---

## 8. Implementation Notes for the RN Engineer

> These are pointers, not implementation code. The RN engineer prompt is authored only after Tom approves this spec.

### 8.1 Hooks

- **`useSignoffContext(jobId: string)`** — TanStack Query, `queryKey: ["job-signoff-context", jobId]`, `queryFn` calls `apiClient.get<SignoffContextResponse>("/api/v1/jobs/${jobId}/signoff-context")`, `retry: false`, `staleTime: 30_000`. Returns `{ data, isLoading, isError, refetch }`. Type `SignoffContextResponse` matches D.1 shape.
- **`useCreateInvoiceSignoff()`** — mirrors `useCreateJobNote.ts` exactly: `database.write(() => database.get<InvoiceSignoff>("invoice_signoffs").create((record) => { …; record.localSyncStatus = "pending"; record.idempotencyKey = generateIdempotencyKey(); record.clientCaptureAt = now; }))`. Input interface per §F.2 of the design doc:
  ```typescript
  export interface CreateInvoiceSignoffInput {
    invoiceId: string; signedByName: string; termsAcknowledged: true;
    signaturePngBase64: string; capturedBy: string;
  }
  ```

### 8.2 WatermelonDB Local Table

- New model `InvoiceSignoff` in `database/models/InvoiceSignoff.ts` extending `SyncableModel` (same base as `JobNote`). Fields: `invoiceId`, `signedByName`, `termsAcknowledged`, `signaturePngBase64`, `capturedBy`, `localSyncStatus`, `idempotencyKey`, `clientCaptureAt`, `syncError`, `retryCount`.
- Register the `invoice_signoffs` table in `database/schema.ts`.
- Register the sync-engine push mapping alongside `job_notes` (the sync engine module that handles `job_notes` push → follow the same registration path for `invoice_signoffs` → `POST /api/v1/invoices/{invoice_id}/signoff` with `Idempotency-Key` header + `client_capture_at` body field).

### 8.3 Canvas Integration (`react-native-signature-canvas`)

- Gate: **do not install until Tom's Rule 9.8 approval is recorded.**
- Use `<SignatureCanvas>` with `onOK` (cache base64 in state), `onEmpty` (set `canvasEmpty: true`), and a `ref` for `clearSignature()` / `getData()`.
- Canvas background must be `colors.neutral[50]` (white) for ink contrast; the wrapper provides the border.
- The base64 string travels **inline** in the mutation payload (§G-R5 — ~20–60KB at 220px height, no presigned-PUT round-trip).

### 8.4 Pattern Composition (§16 — no new top-level UX)

- **§16.8 Optimistic UI / `PendingBadge`**: the captured sign-off shows `PendingBadge` until sync confirms. Compose the existing `PendingBadge` — do not reinvent.
- **§16.4 409-and-Refresh**: if the sync engine receives a 409 (unique-active race loser on a deliberate re-capture), the sync engine refetches the signoff context and updates the local row. The UI surfaces this as the `sync-error` retry state on S1 (rare path).
- **§15 Offline Ops Contract**: the Save flow rides the WatermelonDB mutation queue exactly as `useCreateJobNote` does — local write first, sync-engine push on reconnect.

### 8.5 S1 Mount Point

In `JobDetailScreen.tsx`, mount `<InvoiceSignoffSection jobId={jobId} userId={userId} testID="section-invoice-signoff" />` after `<PhotoSection>` (line ~306) and before the "Message Customer" `Pressable` (line ~309).

---

## 9. Handoff Gate

**STOP. This spec is complete. No implementation code is authored by the designer.**

The spec now goes to **Tom for approval**. Per `batch-ce-1-design.md` §H handoff gate and Approval Gates §1–4:

1. Tom approves this mobile UI design spec.
2. Tom approves the `react-native-signature-canvas` native dependency (Rule 9.8) — **open gate, §0 above**.
3. Only then is the RN engineer prompt (`batch-ce-1-react-native-engr-prompt.md`) authored — and only after Part A (backend) merges + `pnpm sync-api-types` runs (§C step 9–10).

The RN engineer prompt is **not** authored by this designer. It is authored only after Tom approves this spec.
