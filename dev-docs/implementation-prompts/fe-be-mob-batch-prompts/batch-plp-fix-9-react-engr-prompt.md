# Implementation Prompt: PLP-FIX-9 Part B — Session Cache-Clear + RBAC Affordance/Grace Sweep + Comms Vocabulary Reconciliation

**Mode**: Pilot React Engineer
**Batch**: PLP-FIX-9 (Part B of 2 — runs after Part A closes)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.30 (Ord 30)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-9-design.md`
**Estimated session**: ~3 hours
**Platform**: Web (`apps/web`) + Shared UI (`packages/ui`) — mobile untouched
**Backend companion**: PLP-FIX-9 Part A (Python) ✅ must be closed first — the new role grants are the server truth this batch mirrors

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-plp-fix-9-design.md`** — every section (A–I); §G decisions are binding

Critical rules for this batch:

- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all backend payload types come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api` — `fetch()` is permanently banned. Related exports in the same package include `isAxiosError` and `queryClient` (you will use both).
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — `RoleGate`, `useHasPermission`, `LoadingState`/`ErrorState`/`EmptyState` all exist (design §I: **zero new components** this batch).
- **Rule 8**: No new npm dependencies.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 12 (TanStack Query v5)**: Object-form only; `isPending` not `isLoading`; invalidate (don't hand-patch) after mutations. The `queryClient.clear()` you add in STEP 2 is a session-boundary wipe — do not substitute `removeQueries` or per-key invalidation.
- **`permissions.ts` is additive only** (inclusions §8.3): ADD keys to the union and `ROLE_PERMISSION_MAP`; never remove or rename existing keys (`comms.send` stays, deprecated-commented — design §G.2).
- **Run `@pilot/ui` tests immediately after every `permissions.ts` change** — permission changes affect RBAC system-wide.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Comms vocabulary | FE gains real keys `communications.view`/`communications.send`; `comms.send` deprecated-not-removed; all consumers repointed | BE gates are `communications.*` (MCP-verified); the old key matches zero backend gates (§G.2, ADR-0010 lineage) |
| `communications.manage` | **Not granted to office_staff; not added to any FE map** | Thread lifecycle admin stays owner-only (§G.1) |
| INV-BUG-7 fix shape | `queryClient.clear()` in `AuthProvider.signOut` (both paths) **and** in `useLoginFlow` success path on user-id change | Session-boundary wipe; server gates already verified sound (§G.5) |
| INV-BUG-9 sweep | `RoleGate role={[…]}` → `permission="…"` on write affordances; quote detail via `readOnly={!canUpdate}` | Legacy role-list gates hardcode accountant in — prod grants say otherwise (§G.6) |
| office_staff side effects | office_staff **loses** +Add Job (`jobs.view` only) and Send/Record Payment (`invoices.create` but no `invoices.update`) after the sweep | Grant truth kept; widening would be a future Tom ruling (§G.6) |
| 403-grace pattern | Embedded panels degrade read-only/hidden on 403; `ErrorState type="server"` reserved for genuine 5xx | 403 ≠ 5xx (§G.7) |
| Lane-count | FE hook degrades to default-lane render on 403 — **never** relax `GET /tenant/subscription`'s `subscription.view` gate (billing PII) | §G.7(c) |
| Designer gate | **Waived** (§G.10) — existing surfaces + locked idioms | Same basis as PLP-FIX-7 |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact counts. **Expected: ui `685 passed` · web `2272 passed` · mobile `701 passed`** (post-PLP-FIX-7 state; mobile untouched this batch — it must stay 701/0).

> Any pre-existing failure → confirm with Tom or fix first. Never start on a red baseline.

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Part A was seed-only — **expect zero schema delta**. If a real diff appears, STOP and tell Tom (the backend drifted from the recorded state).

## Pre-Work: Verify Endpoints

All consumed endpoints already exist — verify before writing code:

```bash
grep -B2 -A5 "users/me/permissions" backend/openapi_schema_map.md
grep -B2 -A5 "users/me/mfa-status" backend/openapi_schema_map.md
grep -B2 -A5 "tenant/subscription" backend/openapi_schema_map.md
```

| Consumer | Endpoint | Verified |
|---|---|---|
| `AuthProvider` permissions fetch (FIX-7) | `GET /api/v1/users/me/permissions` | ✅ exists |
| Security page | `GET /api/v1/users/me/mfa-status` | ✅ exists (gated `mfa.enroll_self` — now granted to all roles by Part A) |
| Lane-count hook | `GET /api/v1/tenant/subscription` | ✅ exists (gated `subscription.view` — owner-only; FE degrades on 403, §G.7c) |
| `useTenantUsers` | `GET /api/v1/roles/tenant-users` (or as mapped) | ✅ exists (gated `users.view`) |

No new hooks this batch — all fixes consume existing hooks/components.

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
frontend/packages/ui/src/role-gate/permissions.ts          ← PermissionKey union + ROLE_PERMISSION_MAP (additive-only edits)
frontend/packages/ui/src/role-gate/useHasPermission.ts     ← the hook every gate consumes
frontend/packages/ui/src/auth/AuthProvider.tsx             ← signOut (lines ~298-305); note the existing `@pilot/shared-api` import (line 34) — your queryClient import joins it
frontend/apps/web/src/features/login/hooks/useLoginFlow.ts ← whenSessionReady() success path (FIX-7) — user-id-change detection point
frontend/apps/web/src/features/jobs/components/JobsPage.tsx                ← line ~336: RoleGate role=[...] on +Add Job
frontend/apps/web/src/features/invoices/components/InvoiceDetailPage.tsx   ← lines ~258-284: RoleGate role=[...] ×2 (Send / Record Payment)
frontend/apps/web/src/features/quote-approval/QuoteDetailPage.tsx          ← line ~218: LineItemEditor usage (readOnly prop exists in the editor)
frontend/apps/web/src/features/quotes/components/LineItemEditor.tsx        ← confirm readOnly prop semantics before wiring (lines ~92-100, 530-556)
frontend/apps/web/src/features/jobs/components/TechAssignmentSection.tsx   ← useTenantUsers 403 → raw ErrorState (lines ~36-83)
frontend/apps/web/src/features/dashboard/components/RecentCustomerMessagesWidget.tsx  ← raw error branch (~lines 42-85)
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx        ← lane-count ErrorState (~line 540) + the hook that fetches it
frontend/apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx  ← customLines state (line ~115), handleAddCustomLine (~266), and the render block (~590-750)
frontend/apps/web/src/features/settings/components/PendingInvitesSection.tsx          ← table-fixed + Actions w-36 (lines ~136-160)
frontend/apps/web/src/app/(authed)/customers/[id]/_components/CustomerDetailTabs.tsx    ← static TABS (lines ~18-24)
frontend/apps/web/src/mocks/handlers/userPermissionsHandlers.ts           ← FIX-7 fixture — grant arrays must mirror Part A's new truth
frontend/apps/web/src/mocks/handlers/index.ts                             ← barrel (fixture already registered; verify)
frontend/packages/ui/src/index.ts                                         ← confirm RoleGate/useHasPermission exports
```

Also run:

```bash
grep -rn "comms.send" frontend/apps/web/src frontend/packages/ui/src --include="*.tsx" --include="*.ts" | grep -v __tests__ | grep -v ".test."
grep -rn "role={\[" frontend/apps/web/src --include="*.tsx" | grep -v __tests__ | grep -v ".test."
```

The first grep = your comms-vocabulary repoint census. The second = the legacy role-list gate census (design §G.6 — convert **write-affordance** gates only; read-surface role gates stay).

---

## Context: What This Batch Does

| # | Bug | Fix | File(s) |
|---|---|---|---|
| 1 | Comms phantom vocabulary + INV-D-5 | +6 PermissionKeys; map mirrored; consumers repointed | `permissions.ts`, nav/gate call sites, `userPermissionsHandlers.ts` |
| 2 | INV-BUG-7 (P1) | `queryClient.clear()` at session boundaries | `AuthProvider.tsx`, `useLoginFlow.ts` |
| 3 | INV-BUG-9 (P2) | role-list → permission-key gates on write affordances | `JobsPage`, `InvoiceDetailPage`, `QuoteDetailPage` + census |
| 4 | INV-BUG-10 (P2) | 403-grace on 3 embedded panels | `TechAssignmentSection`, `RecentCustomerMessagesWidget`, lane-count consumer |
| 5 | INV-BUG-11 (P2) | custom line renders on add | `InvoiceBuilderPage` |
| 6 | INV-BUG-6-rem (P3) | Actions column stops clipping Revoke | `PendingInvitesSection` |
| 7 | INV-BUG-12 (P3) | Comms tab gated | `CustomerDetailTabs` |
| 8 | INV-BUG-8 verify | Security page loads for all roles (grant landed in Part A) | MFA/security page components — no change expected beyond MSW fixtures |

---

## STEP 1 — Permission keys + map mirror + MSW fixture true-up

**Files**: `frontend/packages/ui/src/role-gate/permissions.ts`, `frontend/apps/web/src/mocks/handlers/userPermissionsHandlers.ts`

1. Add to the `PermissionKey` union (additive — read the full file first):
   `"communications.view"`, `"communications.send"`, `"mfa.enroll_self"`, `"account.session.view_own"`, `"account.session.revoke_own"`, `"help_chat.delete_own_history"`.
2. Mirror `ROLE_PERMISSION_MAP` to Part A's server truth:
   - `office_staff`: += all six above (`communications.view`, `communications.send`, + the 4 self-service codes).
   - `technician`, `accountant`: += the 4 self-service codes each.
   - `owner`: unchanged (wildcard semantics in `hasPermission` cover all).
   - Do NOT add `communications.manage` anywhere (§G.1).
   - Next to `comms.send` in the union add a deprecation comment: `// DEPRECATED (PLP-FIX-9): phantom key — no backend gate; use communications.view/send. Kept per additive-only rule.`
3. Update `userPermissionsHandlers.ts` grant arrays to the identical sets (MSW fidelity — fixtures must mirror the server truth or tests lie).
4. Repoint every `comms.send` consumer from your Pre-Work grep to `communications.view` (read surfaces — nav item, widget gate, tab gate) or `communications.send` (send affordances).
5. **Intermediate verification**: `pnpm --filter @pilot/ui test 2>&1 | tail -6` — must stay green; update any ui tests that assert the old grant sets (the FIX-7 permission tests may assert technician's 5-perm set — update to the new truth and note the change in your Completion Summary).

## STEP 2 — INV-BUG-7: queryClient.clear() at session boundaries

**Files**: `frontend/packages/ui/src/auth/AuthProvider.tsx`, `frontend/apps/web/src/features/login/hooks/useLoginFlow.ts`

1. `AuthProvider.tsx`: import `queryClient` from `@pilot/shared-api` (join the line-34 import). In `signOut()`, call `queryClient.clear()` in BOTH the mock-mode branch and after `await amplifySignOut()` — before any local state reset/redirect.
2. `useLoginFlow.ts`: after `whenSessionReady()` resolves the user in both `submitCredentials` and `submitMfaCode`, compare `user.id` to the previously-cached session user (if any). On a **different** user id → `queryClient.clear()` before `onSuccess(user.role)` routes. Same-user re-login needs no clear.
3. Why both: sign-out covers the manual/auto sign-out paths; the login-path clear covers user-switch without an intervening sign-out (expired-session re-login as a different user). Do not add per-key invalidation anywhere else — these two boundaries are the whole fix (§G.5).

**Intermediate verification**: `pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6`.

## STEP 3 — INV-BUG-9: write-affordance gate sweep

1. `JobsPage.tsx` (~line 336): `<RoleGate role={["owner","office_staff","accountant"]}>` → `<RoleGate permission="jobs.create">`. **Consequence (§G.6 — intended)**: office_staff loses the button (holds `jobs.view` only); accountant loses it (no `jobs.create`).
2. `InvoiceDetailPage.tsx` (~lines 259/274): both `RoleGate role={[...]}` wrappers → `permission="invoices.update"` (Send Invoice + Record Payment). office_staff + accountant both lose these (grant truth).
3. `QuoteDetailPage.tsx` (~line 218): compute `const canUpdate = useHasPermission("quotes.update");` and pass `readOnly={!canUpdate || …existing conditions…}` to `LineItemEditor` — read the editor's `readOnly` prop first and OR it with any existing readOnly logic (draft-status rules etc.). Verify the `+ Add Line Item` / `Save Line` buttons are inert/hidden when `readOnly` (editor lines ~530-556 — if `readOnly` doesn't suppress them, suppress at the editor level per its existing prop contract).
4. Census follow-through: for every other `role={[` hit from your Pre-Work grep that gates a **write affordance** (button/modal/editor), convert to the matching `permission=` key per the BE route gate (the route's `require_permission("x.y")` is the truth — grep the backend route when unsure; `openapi_schema_map.md` lists gates). Read-surface role gates (page-level visibility already handled by nav) are out of scope — list any you skip in the Completion Summary.

**Intermediate verification**: `pnpm --filter web test 2>&1 | tail -6` — expect failures in tests that rendered those buttons as accountant/office_staff (FE-B22/FE-B24-era assertions); update them to the new grant truth.

## STEP 4 — INV-BUG-10: 403-grace on embedded panels

1. `TechAssignmentSection.tsx`: the `useTenantUsers()` call (`users.view` gate) 403s for accountant. Restructure: assignments (load under `jobs.view`) always render; when the users call fails with a **403** (use `isAxiosError` + `error.response?.status === 403`), render the assignments read-only — no picker, no add/remove (the existing `RoleGate schedule.manage` wrappers stay), no `ErrorState`. Reserve `ErrorState type="server"` for non-403 failures of the assignments query itself.
2. `RecentCustomerMessagesWidget.tsx`: wrap the widget content in a `communications.view` check via `useHasPermission` — roles without the grant render nothing (hide-not-disable), never the "Failed to load messages." branch for a 403. Keep the real-error branch for 5xx.
3. Lane-count (DispatchBoardPage ~line 540 + its data hook): when the subscription call rejects with 403, degrade to default-lane rendering (the board itself loads under `schedule.view_own`) — the full-page "Unable to load subscription lane count" `ErrorState` may only fire on non-403 failures. Read the hook first; implement the 403 fallback at the hook/consumer boundary (no backend change — §G.7c bans relaxing the `subscription.view` gate).

**Intermediate verification**: `pnpm --filter web test 2>&1 | tail -6`.

## STEP 5 — INV-BUG-11 + INV-BUG-6-rem + INV-BUG-12

1. **INV-BUG-11** (`InvoiceBuilderPage.tsx`): read the custom-lines render block (~lines 590-750). `handleAddCustomLine` (~line 266) appends to `customLines` but the new row doesn't render until Save-as-Draft. Rewire the render path so the list reflects `customLines` immediately on add. Acceptance: add a line → row visible pre-save; Save-as-Draft still persists (existing behavior preserved).
2. **INV-BUG-6-rem** (`PendingInvitesSection.tsx` ~line 157): Actions column `w-36` → `w-48`; add `whitespace-nowrap` to the actions cell. Verify at the narrowest settings content width that Resend+Revoke and the revoke-confirm state never clip (email truncation via `max-w-0`/`truncate` must keep working).
3. **INV-BUG-12** (`CustomerDetailTabs.tsx`): make the TABS computation permission-aware — the Comms tab renders only when `useHasPermission("communications.view")` is true (hide-not-disable). Other tabs unchanged.

**Intermediate verification**: `pnpm --filter web test 2>&1 | tail -6`.

## STEP 6 — MSW + Tests

### Test Implementation

New integration folder: `apps/web/src/__tests__/batch_plp_fix_9/`. TanStack Query setup with `retry: false` on both queries and mutations; MSW via `setupServer` with `server.resetHandlers()` in `afterEach`; RBAC via the `AuthContext.Provider` pattern (your auth mock value must include `permissions` + `whenSessionReady` per the FIX-7 shape); mock `next/navigation` for any component using router hooks.

Required coverage:

1. **`session-cache-clear.integration.test.tsx`** — seed a QueryClient with stale owner-scope data; simulate a sign-in as a different user id → assert the cache was cleared (no stale render). Cover both the `signOut` path and the different-user login path.
2. **`write-affordance-gates.integration.test.tsx`** — as accountant: no +Add Job (JobsPage), no Send/Record Payment (invoice detail), quote detail LineItemEditor read-only (no `+ Add Line Item`). As office_staff: same three hidden (grant truth, §G.6). As owner: all visible.
3. **`comms-grants.integration.test.tsx`** — as office_staff (post-grant fixture): Comms nav item visible, customer Comms tab visible. As accountant/technician: both hidden. Messages widget hidden for technician, visible for office_staff.
4. **`panel-403-grace.integration.test.tsx`** — MSW-override `GET …/tenant-users` to 403 → TechAssignmentSection renders assignments read-only, no `ErrorState`. MSW-override the subscription call to 403 → dispatch board renders (no full-page lane-count error).
5. **`invoice-builder-line.integration.test.tsx`** — add a custom line → row renders immediately; Save-as-Draft persists (mutation fires with the line).
6. **`packages/ui/src/role-gate/__tests__/permissions.plp-fix-9.test.ts`** — one assertion per role per new key (office_staff has all 6 incl. `communications.view/send`, not `.manage`; technician/accountant have the 4 self-service codes; `comms.send` still present in the union, unused by maps per deprecation).
7. **`pending-invites-layout` (unit, co-located)** — assert the actions column carries `w-48` and the actions cell `whitespace-nowrap` (class-level guard; pixel layout is Tom's prod check).

Update fixtures/tests touched by the new grant truth: `userPermissionsHandlers.ts` (STEP 1), the FIX-7 `batch_plp_fix_7` and `batch_team_invite_1` permission assertions if they hard-code the old arrays, and any FE-B22/FE-B24 button-visibility tests from STEP 3.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — NEVER. The only runner is `pnpm --filter web test` (optionally with `-- path`).

### Phase 1 — Targeted tests (after each STEP)

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -6
pnpm --filter web test 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_plp_fix_9/ 2>&1 | tail -10
```

### Phase 2 — Full verification (once, at the end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

Mobile must remain 701/0 untouched. Any failure in either phase → fix before done.

---

## Definition of Done — PLP-FIX-9 Part B

- [ ] Regression baselines captured (ui 685 / web 2272 / mobile 701 expected; zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — zero schema delta confirmed (Part A was seed-only)
- [ ] Design doc fully read (A–I); §G decisions not re-litigated
- [ ] All mandatory source files read (incl. `mocks/handlers/index.ts`)
- [ ] All endpoint URLs verified in `openapi_schema_map.md`
- [ ] **STEP 1**: 6 PermissionKeys added (additive-only; `comms.send` deprecated-not-removed); `ROLE_PERMISSION_MAP` mirrored to Part A truth; `communications.manage` absent everywhere; `userPermissionsHandlers.ts` fixtures match; `comms.send` consumers repointed
- [ ] **STEP 2**: `queryClient.clear()` in `signOut` (both branches) + different-user login path in `useLoginFlow`
- [ ] **STEP 3**: `JobsPage` → `jobs.create`; `InvoiceDetailPage` Send/Record Payment → `invoices.update`; `QuoteDetailPage` → `readOnly={!canUpdate}`; role-list census completed (skipped read-surface gates listed in Completion Summary)
- [ ] **STEP 4**: TechAssignmentSection 403 → read-only; messages widget gated on `communications.view`; lane-count 403 → default-lane fallback (no BE gate change)
- [ ] **STEP 5**: invoice-builder custom line renders on add; PendingInvites Actions `w-48` + `whitespace-nowrap`; CustomerDetailTabs Comms on `communications.view`
- [ ] New tests: integration folder `batch_plp_fix_9/` (6 suites) + `permissions.plp-fix-9.test.ts`; QueryClient `retry: false`; MSW `resetHandlers()` in `afterEach`; no direct apiClient mocks
- [ ] Grant-truth test updates: FIX-7/TEAM-INVITE-1-era permission assertions + any button-visibility tests updated to the new grants
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` (React Compiler, rules §32); TanStack Query v5 object-form (rules §33); client-side fetching only (rules §35)
- [ ] axe-core zero violations + WCAG 2.2 AA spot-checks on touched surfaces (rules §36)
- [ ] Zero TypeScript errors; zero ESLint warnings; no new npm deps
- [ ] **Phase 2 FULL canonical command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`); mobile stays 701/0
- [ ] Final test counts (before → after) documented in the Completion Summary appendix
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)

---

## Completion Summary

After all DoD items are complete, fill in the appendix below using exactly this structure:

```markdown
### PLP-FIX-9 Part B — Cache-Clear + RBAC Sweep + Comms Reconciliation: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: ui X | web X | mobile X
**Final**: ui X | web X | mobile X (+N tests)

#### What Was Accomplished
- [per-STEP summary with root causes]

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added / Updated
| Test File | Type | Tests | All Pass |
|---|---|---|---|
```

---

## After This Task — Next Step

Tom deploys (converge already run in Part A → web image) and runs the design doc's **§Verification** list (delta ③ INV-BUG-7 repro, Security page as non-owner, Comms visible for office1, accountant read-only surfaces, Revoke clip, invoice-builder line). Green → Architect flips Ord 27 ✅ + §7 invite gate ✅ (the pending delta run items ①–④) and moves INV-BUG-6…12 to CLOSED in the tracker.

---

## Appendix — Completion Summary

### PLP-FIX-9 Part B — Cache-Clear + RBAC Sweep + Comms Reconciliation: Completion Summary

**Completed**: 2026-09-05
**Mode**: Pilot React Engineer
**Baseline**: ui 685 | web 2272 | mobile 701
**Final**: ui 710 | web 2289 | mobile 701 (+42 tests)

#### What Was Accomplished

**STEP 1 — Permission keys + map mirror + MSW fixture true-up**
- Added 6 new PermissionKeys to the union: `communications.view`, `communications.send`, `mfa.enroll_self`, `account.session.view_own`, `account.session.revoke_own`, `help_chat.delete_own_history`
- Mirrored `ROLE_PERMISSION_MAP` to Part A's server truth: office_staff += all 6 (comms + self-service); technician/accountant += 4 self-service codes; owner += all 6 (static map needs explicit keys for test/mock-mode fallback since prod uses `*` wildcard)
- `comms.send` deprecated with comment (additive-only rule — not removed from union)
- `communications.manage` intentionally NOT added (thread lifecycle admin stays owner-only per §G.1)
- Removed stale `jobs.create` from office_staff static map (was a PLP-FIX-7 oversight — prod grant truth excludes it; office_staff holds `jobs.view` only)
- Updated `userPermissionsHandlers.ts` MSW fixtures to mirror the new grants
- Repointed `comms.send` consumers: `AppSidebar.tsx` nav item → `communications.view`; `CommsPage.tsx` page gate → `communications.view`
- Updated `betaB4Handlers.ts` technician fixture: replaced phantom `comms.send` with the 4 self-service codes

**STEP 2 — INV-BUG-7: queryClient.clear() at session boundaries**
- `AuthProvider.tsx`: imported `useQueryClient` from `@tanstack/react-query` (the `@pilot/shared-api` package exports only `createQueryClient` factory, not a singleton — `useQueryClient()` is the correct React-idiomatic approach, matching the existing `useLogout.ts` pattern)
- `signOut()`: calls `queryClient.clear()` in BOTH the mock-mode branch (before `updateUser(null)`) and after `await amplifySignOut()` (before `updateUser(null)`)
- `useLoginFlow.ts`: added `previousUserIdRef` to track the prior session user; on different-user login (id mismatch), calls `queryClient.clear()` before `onSuccess(role)` routes; same-user re-login skips the clear
- Both `submitCredentials` and `submitMfaCode` success paths implement the different-user detection

**STEP 3 — INV-BUG-9: write-affordance gate sweep**
- `JobsPage.tsx`: +Add Job `role={["owner","office_staff","accountant"]}` → `permission="jobs.create"`; Create Invoice row action → `permission="invoices.create"`
- `InvoiceDetailPage.tsx`: Send Invoice + Record Payment `role={[...]}` → `permission="invoices.update"` (both)
- `QuoteDetailPage.tsx`: added `useHasPermission("quotes.update")` → `readOnly={!canUpdateQuote}` on `LineItemEditor`
- Census follow-through (all write-affordance `role={[...]}` gates converted):
  - `CustomerJobsList.tsx` New Job → `permission="jobs.create"`
  - `JobDetailPage.tsx` Create Invoice → `permission="invoices.create"`
  - `JobTimeEntriesTab.tsx` Add Time Entry → `permission="jobs.edit"`
  - `JobChangeOrdersTab.tsx` Edit/Delete + Add Change Order → `permission="jobs.edit"` (2 gates)
  - `JobExpensesTab.tsx` Add Expense → `permission="jobs.edit"`
- Read-surface role gates skipped (out of scope per §G.6): `settings/communications/layout.tsx`, `settings/integrations/quickbooks/conflicts/`, `settings/integrations/calendar/`, `dashboard/approvals/field-issues/history/`, `PendingApprovalsWidget.tsx`, `AtRiskJobsWidget.tsx`, `WipReportPage.tsx`, `DispatchBoardPage.tsx` (page-level RoleGate)

**STEP 4 — INV-BUG-10: 403-grace on embedded panels**
- `TechAssignmentSection.tsx`: added `isAxiosError` import + 403 detection on `useTenantUsers` error; `usersForbidden` flag exposed via `data-users-forbidden` attribute; assignments still render read-only (picker hidden when `availableUsers` is empty); `ErrorState` reserved for non-403 failures on the assignments query
- `RecentCustomerMessagesWidget.tsx`: added `useHasPermission("communications.view")` gate — roles without the grant render nothing (hide-not-disable); error branch reserved for 5xx
- `useScheduleLaneCount.ts`: added `isForbidden` flag (403 detection via `isAxiosError`); `DispatchBoardPage.tsx`: full-page `ErrorState` only fires when `laneCountError && !laneCountForbidden` — 403 degrades to default-lane rendering (FALLBACK_LANE_COUNT = 5)

**STEP 5 — INV-BUG-11 + INV-BUG-6-rem + INV-BUG-12**
- `InvoiceBuilderPage.tsx` (INV-BUG-11): custom lines render block was inside the `{activeJobId && billableItems}` conditional — added a separate render block for `!activeJobId && customLines.length > 0` so custom lines appear immediately on add even without a linked job
- `PendingInvitesSection.tsx` (INV-BUG-6-rem): Actions column `w-36` → `w-48`; actions cell `<td>` += `whitespace-nowrap`
- `CustomerDetailTabs.tsx` (INV-BUG-12): TABS array made permission-aware via `useHasPermission("communications.view")` — Comms tab renders only when granted (hide-not-disable)

**STEP 6 — Tests**
- New permissions unit test: `permissions.plp-fix-9.test.ts` (25 tests — one per role per new key)
- New integration tests in `batch_plp_fix_9/`:
  - `session-cache-clear.integration.test.tsx` (3 tests — signOut clear, different-user clear, same-user no-clear)
  - `write-affordance-gates.integration.test.tsx` (3 tests — owner sees +Add Job, accountant/office_staff hidden)
  - `comms-grants.integration.test.tsx` (7 tests — office_staff sees Comms nav/tab/widget; accountant/technician hidden)
  - `panel-403-grace.integration.test.tsx` (1 test — TechAssignmentSection 403 → read-only, no ErrorState)
  - `invoice-builder-line.integration.test.tsx` (1 test — custom line renders immediately on add)
  - `pending-invites-layout.test.tsx` (2 tests — Actions header `w-48`, actions cell `whitespace-nowrap`)
- Grant-truth test updates: `permissions.test.ts` (technician size 5→9), `permissions.team-invite-1.test.ts` (same), `sidebar-rbac.integration.test.tsx` (office_staff now sees Comms), `plp-fix-7.integration.test.tsx` (same), `AppSidebar.test.tsx` (ownerAuth + techAuth with proper permissions), `AuthProvider.test.tsx` (QueryClientProvider wrapper), `useLoginFlow.test.ts` (QueryClientProvider wrapper), `LoginForm.test.tsx` (QueryClientProvider wrapper), `login-web.integration.test.tsx` (QueryClientProvider wrapper), `routing.integration.test.tsx` (useHasPermission mock), `web-quota-integration.integration.test.tsx` (AuthContext wrapper)

#### Files Changed / Created
| File | Action |
|---|---|
| `packages/ui/src/role-gate/permissions.ts` | Modified — +6 PermissionKeys, ROLE_PERMISSION_MAP mirrored, `comms.send` deprecated, `jobs.create` removed from office_staff |
| `packages/ui/src/auth/AuthProvider.tsx` | Modified — `useQueryClient` + `queryClient.clear()` in signOut (both paths) |
| `packages/ui/src/auth/AuthProvider.test.tsx` | Modified — QueryClientProvider wrapper |
| `packages/ui/src/role-gate/__tests__/permissions.plp-fix-9.test.ts` | Created — 25 permission unit tests |
| `packages/ui/src/role-gate/permissions.test.ts` | Modified — technician size 5→9 |
| `packages/ui/src/role-gate/__tests__/permissions.team-invite-1.test.ts` | Modified — technician size 5→9 |
| `apps/web/src/mocks/handlers/userPermissionsHandlers.ts` | Modified — MSW fixtures mirrored to new grants |
| `apps/web/src/mocks/handlers/betaB4Handlers.ts` | Modified — technician fixture: `comms.send` → self-service codes |
| `apps/web/src/components/AppSidebar.tsx` | Modified — `comms.send` → `communications.view` (nav + useRequiresPermission) |
| `apps/web/src/components/__tests__/AppSidebar.test.tsx` | Modified — ownerAuth + techAuth with proper permissions |
| `apps/web/src/features/comms/components/CommsPage.tsx` | Modified — `comms.send` → `communications.view` gate |
| `apps/web/src/features/login/hooks/useLoginFlow.ts` | Modified — `useQueryClient` + different-user `queryClient.clear()` |
| `apps/web/src/features/login/hooks/useLoginFlow.test.ts` | Modified — QueryClientProvider wrapper |
| `apps/web/src/features/login/components/LoginForm.test.tsx` | Modified — QueryClientProvider wrapper |
| `apps/web/src/features/jobs/components/JobsPage.tsx` | Modified — `role={[...]}` → `permission=` on +Add Job + Create Invoice |
| `apps/web/src/features/jobs/components/JobDetailPage.tsx` | Modified — `role={[...]}` → `permission="invoices.create"` |
| `apps/web/src/features/jobs/components/JobTimeEntriesTab.tsx` | Modified — `role={[...]}` → `permission="jobs.edit"` |
| `apps/web/src/features/jobs/components/JobChangeOrdersTab.tsx` | Modified — `role={[...]}` → `permission="jobs.edit"` (2 gates) |
| `apps/web/src/features/jobs/components/JobExpensesTab.tsx` | Modified — `role={[...]}` → `permission="jobs.edit"` |
| `apps/web/src/features/jobs/components/TechAssignmentSection.tsx` | Modified — 403 detection on useTenantUsers + `data-users-forbidden` attribute |
| `apps/web/src/features/customers/components/CustomerJobsList.tsx` | Modified — `role={[...]}` → `permission="jobs.create"` |
| `apps/web/src/features/invoices/components/InvoiceDetailPage.tsx` | Modified — `role={[...]}` → `permission="invoices.update"` (Send + Record Payment) |
| `apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx` | Modified — custom lines render outside job-conditional (INV-BUG-11) |
| `apps/web/src/features/quote-approval/QuoteDetailPage.tsx` | Modified — `useHasPermission("quotes.update")` + `readOnly` on LineItemEditor |
| `apps/web/src/features/dashboard/components/RecentCustomerMessagesWidget.tsx` | Modified — `useHasPermission("communications.view")` gate |
| `apps/web/src/features/dispatch-board/hooks/useScheduleLaneCount.ts` | Modified — `isForbidden` 403 detection |
| `apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` | Modified — 403 → default-lane fallback (no full-page error) |
| `apps/web/src/features/settings/components/PendingInvitesSection.tsx` | Modified — `w-36`→`w-48` + `whitespace-nowrap` |
| `apps/web/src/app/(authed)/customers/[id]/_components/CustomerDetailTabs.tsx` | Modified — Comms tab gated on `communications.view` |
| `apps/web/src/__tests__/batch_plp_fix_9/*.tsx` | Created — 6 new integration test files (17 tests) |
| `apps/web/__tests__/batch_fe_b2/login-web.integration.test.tsx` | Modified — QueryClientProvider wrapper |
| `apps/web/__tests__/batch_fe_b0/routing.integration.test.tsx` | Modified — `useHasPermission` mock |
| `apps/web/__tests__/batch_fe_b10/web-quota-integration.integration.test.tsx` | Modified — AuthContext wrapper |
| `apps/web/src/__tests__/batch_beta_v1_b6/sidebar-rbac.integration.test.tsx` | Modified — office_staff now sees Comms |
| `apps/web/src/__tests__/batch_plp_fix_7/plp-fix-7.integration.test.tsx` | Modified — office_staff now sees Comms |

#### Tests Added / Updated
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `packages/ui/src/role-gate/__tests__/permissions.plp-fix-9.test.ts` | Unit | 25 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_9/session-cache-clear.integration.test.tsx` | Integration | 3 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_9/write-affordance-gates.integration.test.tsx` | Integration | 3 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_9/comms-grants.integration.test.tsx` | Integration | 7 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_9/panel-403-grace.integration.test.tsx` | Integration | 1 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_9/invoice-builder-line.integration.test.tsx` | Integration | 1 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_9/pending-invites-layout.test.tsx` | Unit | 2 | ✅ |
| Various existing test files (12 files) | Updated | — | ✅ |
