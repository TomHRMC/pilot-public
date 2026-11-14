# Implementation Prompt: PLP-FIX-10 Part B — Dispatch-Board Gate + Technicians-Box 403 Grace + Generate-Link Gate + Settings Tables Layout (INV-BUG-13, 10a, 15, 16)

**Mode**: Pilot React Engineer
**Batch**: PLP-FIX-10 (Part B of 2 — runs after Part A closes; launch plan Ord 31, card §3.31)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.31
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-10-design.md` — read fully (A–I); §G decisions are binding
**Estimated session**: ~2.5 hours
**Platform**: Web (`apps/web`) only — mobile untouched (must stay 701/0)
**Backend companion**: PLP-FIX-10 Part A (Python) ✅ must be closed first — it carries the checklist-unhide BE fix + session-history wiring. Part B's surfaces use **existing** endpoints only (zero OpenAPI delta), so `pnpm sync-api-types` is a formality — still the mandatory first pre-work step.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-plp-fix-10-design.md`** — every section (A–I)

Critical rules for this batch:

- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all backend payload types come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api` — `fetch()` is permanently banned. Related exports in the same package: `isAxiosError`, `queryClient`.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — `RoleGate`, `useHasPermission`, `LoadingState`/`ErrorState`/`EmptyState` all exist (design §I: **zero new components** this batch).
- **Rule 8**: No new npm dependencies.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. Root cause unidentifiable → STOP and ask Tom.
- **Rule 12 (TanStack Query v5)**: object-form only; `isPending` not `isLoading`; invalidate (don't hand-patch) after mutations.
- **`useHasPermission` accepts any string** (verified: `useHasPermission.ts` — `key: string`). `"schedule.view_all"` works **without** adding it to the `PermissionKey` union — do NOT touch `permissions.ts` this batch (additive-only rule is irrelevant here; zero permission changes).

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Board gate key | `permission="schedule.view_all"` (replaces `role={["owner","accountant"]}`) | Matches the BE read gates (`scheduling.py`); role lists are the legacy defect class (§G.1) |
| Accountant loses the board | **Accepted** — grant truth (accountant holds no schedule grants) | The role list was papering over it; widening is an RBAC-CONFIG-1 ruling, not a gate exception (§G.1) |
| Technicians box | Section hidden unless `schedule.view_all`; picker on `schedule.manage`; assignments-query 403 → render null, never `ErrorState` | 403 ≠ 5xx; the FIX-9 fix guarded the wrong query (§G.2) |
| Generate-&-Copy-Link gate | `permission="invoices.update"` — hidden for accountant **and office_staff** | Same operation as `POST /{id}/send`; office_staff side effect pre-flagged (§G.5, FIX-9 §G.6 lineage) |
| Table layout (Tom-ruled) | Drop `table-fixed`; content-sized columns; `overflow-x-auto` wrapper; `truncate`+tooltip only inside the scroll region | Full values at desktop width; horizontal scroll on overflow; Resend/Revoke always fully visible (§G.4) |
| Checklist Show | **No FE change** — Part A fixed the BE one-way write; Part B only adds the contract-locking test | FE was correct; the BE returned success without persisting (§G.3) |
| Designer gate | **Waived** (§G.8) — existing surfaces + locked idioms | Same basis as PLP-FIX-7/9 |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact counts. **Expected: ui `710 passed` · web `2289 passed` · mobile `701 passed`** (post-PLP-FIX-9 state; mobile untouched this batch). Any pre-existing failure → confirm with Tom or fix first.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Expected: no type changes (Part A had a timestamp-only OpenAPI diff). If the diff shows anything beyond a timestamp → note it in your Completion Summary and proceed — no endpoint contracts changed.

---

## Pre-Work: Verify Endpoints

No new hooks this batch. The checklist contract test uses the existing endpoint — verify it exists:

```bash
grep -n "onboarding/checklist/hidden" backend/openapi_schema_map.md
grep -n "session-history" backend/openapi_schema_map.md
```

Expected: `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden` and `GET /api/v1/users/me/session-history` both present. If either is missing → **STOP and ask Tom**.

---

## Pre-Work: Read These Source Files

1. `frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` — the `RoleGate role={["owner","accountant"]}` wrapper (line ~571) you convert
2. `frontend/apps/web/src/features/jobs/components/TechAssignmentSection.tsx` — full component (the FIX-9 `usersForbidden` pattern you extend to the assignments query)
3. `frontend/apps/web/src/features/invoices/components/InvoiceDetailPage.tsx` — the ungated "Generate & Copy Link" button (lines ~288-294) + how FIX-9 gated Send/Record in the same file (mirror that mechanism exactly)
4. `frontend/apps/web/src/features/settings/components/TeamSettingsPage.tsx` — the members `<table>` (line ~99)
5. `frontend/apps/web/src/features/settings/components/PendingInvitesSection.tsx` — the `table-fixed` pending-invites table + the FIX-9 `w-48` Actions column
6. `frontend/apps/web/src/features/onboarding/components/OnboardingChecklistWidget.tsx` + `frontend/apps/web/src/features/onboarding/hooks/useChecklistMutations.ts` — the Show path you contract-test (no changes)
7. `frontend/packages/ui/src/role-gate/useHasPermission.ts` — confirm the `key: string` signature before using `"schedule.view_all"`
8. `frontend/apps/web/src/__tests__/batch_plp_fix_9/panel-403-grace.integration.test.tsx` — the `renderWithAuth` pattern your tests follow
9. `frontend/apps/web/src/__tests__/batch_plp_fix_9/comms-grants.integration.test.tsx` — the permission-aware AuthContext test pattern
10. `frontend/apps/web/src/mocks/handlers/index.ts` — the MSW barrel; confirm no new handlers are needed (all endpoints already mocked)

---

## Context: What This Batch Does

Four surface fixes from the 09-06 prod verification run — all roots code-verified at design time, all existing surfaces, zero new components:

| STEP | Bug | File | Fix |
|---|---|---|---|
| 1 | INV-BUG-13 — `/schedule` blank for office_staff | `DispatchBoardPage.tsx` | `role={["owner","accountant"]}` → `permission="schedule.view_all"` |
| 2 | INV-BUG-10a — "Failed to load technicians" for accountant | `TechAssignmentSection.tsx` | section on `schedule.view_all`; picker on `schedule.manage`; assignments-403 → null |
| 3 | INV-BUG-16 — Generate-&-Copy-Link visible to view-only roles | `InvoiceDetailPage.tsx` | gate on `invoices.update` |
| 4 | INV-BUG-15 — settings tables truncate real data (Tom-ruled) | `TeamSettingsPage.tsx`, `PendingInvitesSection.tsx` | content-sized columns + horizontal scroll |
| 5 | Tests | `__tests__/batch_plp_fix_10/` | integration coverage for all four + the checklist Show contract |

**Out of scope**: mobile; `permissions.ts` (zero changes); the checklist FE (Part A fixed the BE; you only contract-test it); session history UI (Part A wires the data; the existing Security page renders it).

---

## STEP 1 — INV-BUG-13: dispatch board gate (design §G.1)

- In `DispatchBoardPage.tsx` (~line 571): replace `<RoleGate role={["owner", "accountant"]}>` with `<RoleGate permission="schedule.view_all">`. Nothing else changes — the `DndContext` tree, lane logic, and the FIX-9 lane-count 403 fallback all stay.
- Read the file first. If any sibling role-list gates exist inside the board tree (drag affordances, job panel), convert **write** affordances to their write permission (`schedule.manage`) per the FIX-9 sweep rule; read-surface gates follow the section gate.
- Update the stale docstring (line ~131: "Protected by RoleGate (schedule.manage permission)") to name the actual gate.
- Intermediate verification: `pnpm --filter web test -- apps/web/src/__tests__/batch_dispatch_b3/ 2>&1 | tail -6`

## STEP 2 — INV-BUG-10a: Technicians box 403 grace (design §G.2)

In `TechAssignmentSection.tsx`:

- Gate the whole section: `const canViewSchedule = useHasPermission("schedule.view_all");` → `if (!canViewSchedule) return null;` (place after the hooks — every hook still runs unconditionally; the early return precedes the JSX).
- Picker/manage affordances: `const canManageSchedule = useHasPermission("schedule.manage");` — the add-picker and remove buttons render only when true (a view-only-schedule role sees assignments read-only).
- Defense-in-depth on the **assignments** query (the actual 403 source on prod — `GET /jobs/{id}/assignments` is `schedule.view_all`-gated): mirror the FIX-9 `usersForbidden` detector — `const assignmentsForbidden = isError && isAxiosError(error) && error.response?.status === 403;` → render null when true. `ErrorState` only fires for non-403 failures. (You need the query's `error` object — extend the existing `useJobAssignments` destructure.)
- Keep the FIX-9 `usersForbidden` read-only path intact.

## STEP 3 — INV-BUG-16: Generate-&-Copy-Link gate (design §G.5)

- In `InvoiceDetailPage.tsx` (~lines 288-294): wrap the "Generate & Copy Link" / "Copy Public Link" button in the **same gating mechanism FIX-9 used for Send/Record Payment in this file** (`<RoleGate permission="invoices.update">` — mirror, don't reinvent). Hidden for accountant and office_staff.
- First grep the `/send` route's BE gate to confirm the key: `grep -n "require_permission" backend/api/routes/invoices.py | grep -i send` — expect `invoices.update`. If it differs → use the BE gate's key and note it in the Completion Summary.

## STEP 4 — INV-BUG-15: settings tables layout (design §G.4, Tom-ruled)

In `TeamSettingsPage.tsx` and `PendingInvitesSection.tsx`:

- Drop `table-fixed`; the table uses natural content sizing (`w-full` stays).
- Wrap the table in a horizontal-scroll container: `<div className="overflow-x-auto" tabIndex={0} role="region" aria-label="…table, scrollable">` (WCAG 2.2 AA — keyboard users must be able to scroll the region; the existing outer `overflow-hidden` border wrapper moves **outside** the scroll container or merges — keep the rounded border intact).
- Cells that must not wrap (email, name, actions): `whitespace-nowrap`.
- The email cell keeps its `truncate` + tooltip — but the `max-w` now applies only as the in-scroll-region fallback (an extreme value truncates within the scroll area instead of crushing other columns).
- **Acceptance (design §G.4)**: desktop width → full email values render (no ellipsis on `tom@example-domain.org`-class values); narrow window → horizontal scroll instead of crushed columns; Resend + Revoke fully visible at every width (the FIX-9 `w-48` + nowrap on Actions stays).
- Intermediate verification: `pnpm --filter web test -- apps/web/src/__tests__/batch_plp_fix_9/pending-invites-layout.test.tsx 2>&1 | tail -6` (the FIX-9 layout tests must still pass — update them if the structure changed, keeping their intent)

## STEP 5 — Tests (`apps/web/src/__tests__/batch_plp_fix_10/`)

Follow the FIX-9 `renderWithAuth` pattern (`panel-403-grace.integration.test.tsx`, `comms-grants.integration.test.tsx`) — server-authoritative permission arrays on the AuthContext, `retry: false` QueryClients, MSW at the HTTP level (never mock `apiClient`), `vi.mock("next/navigation", ...)` where needed:

1. **`board-gate.integration.test.tsx`** — office_staff → board content renders (lane/grid testids); accountant → nothing renders (grant-truth side effect, §G.1); owner → renders.
2. **`tech-assignment-grace.integration.test.tsx`** — accountant → section null, no "Failed to load technicians"; office_staff → assignments + picker render; per-test MSW override forcing the assignments GET → 403 → section renders null, **no** `ErrorState`; override → 500 → `ErrorState` renders.
3. **`generate-link-gate.integration.test.tsx`** — accountant → no Generate-&-Copy-Link button; owner → button present.
4. **`settings-tables-layout.integration.test.tsx`** — both tables: `table-fixed` absent; `overflow-x-auto` wrapper present with `tabIndex={0}` + `role="region"`; actions cell `whitespace-nowrap`; long-email fixture row → Revoke button rendered and visible.
5. **`checklist-show-contract.integration.test.tsx`** — MSW: hidden pill → click Show → PUT fires with `{"hidden": false}` → on refetch returning `checklist_hidden: false` the widget **stays expanded** (locks the Part A contract — the FE was already correct).

Also update any pre-existing tests that render these components with stale assumptions (grep for `DispatchBoardPage`, `TechAssignmentSection` in test files — e.g. `batch_dispatch_b3`, `panel-403-grace`): align their auth fixtures to the new gates (office_staff fixtures need `schedule.view_all`/`schedule.manage` — already mirrored in the FIX-9 MSW permission fixtures; verify with `grep -n "schedule" apps/web/src/mocks/handlers/userPermissionsHandlers.ts`).

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. The ONLY correct runner is `pnpm --filter web test`.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/__tests__/batch_plp_fix_10/ 2>&1 | tail -10
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to the next step — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without Tom's written confirmation. W1/W2 mobile warnings are verified benign (inclusions §10.2) — do not chase them. Mobile `--forceExit` lives in the test script (§10.1) — use the commands as written.

---

## Definition of Done — PLP-FIX-10 Part B

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (ui 710 / web 2289 / mobile 701 — zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — timestamp-only diff confirmed
- [ ] Design doc fully read before writing any code
- [ ] All mandatory source files read before modifying (including `mocks/handlers/index.ts`)
- [ ] Both endpoints verified in `openapi_schema_map.md` (`checklist/hidden`, `session-history`)
- [ ] **STEP 1**: `DispatchBoardPage` gate → `permission="schedule.view_all"`; docstring corrected; sibling write gates on `schedule.manage`
- [ ] **STEP 2**: `TechAssignmentSection` — section gate + `schedule.manage` picker gate + assignments-query 403→null defense; `ErrorState` only for non-403
- [ ] **STEP 3**: Generate-&-Copy-Link gated `invoices.update` (BE gate grep-verified)
- [ ] **STEP 4**: both settings tables — `table-fixed` dropped, `overflow-x-auto` region with `tabIndex={0}` + `role="region"` + `aria-label`, nowrap cells, truncate+tooltip as in-scroll fallback; FIX-9 layout tests updated/intact
- [ ] **STEP 5**: all five `batch_plp_fix_10/` integration test files green
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; components pure (rules §32)
- [ ] axe-core zero violations + WCAG 2.2 AA spot-checks on changed surfaces (scroll-region keyboard access, target sizes, focus not obscured) (rules §36)
- [ ] Zero TypeScript errors (`check-types`); zero ESLint `no-hardcoded-design-values` warnings
- [ ] `permissions.ts` untouched (zero permission changes this batch)
- [ ] Mobile suite untouched-green (701/0)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command from the Final Verification section
- [ ] Final test count (before → after) documented in the Completion Summary appendix
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] Source spec task headers updated to ✅ Complete in any spec doc other than the launch plan — if applicable (N/A — no separate spec doc)

---

## Completion Summary

After all Definition of Done items are complete, fill in the appendix at the end of THIS prompt doc using the format below.

```markdown
### PLP-FIX-10 Part B — Board/Tech-Section/Link Gates + Tables Layout: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: ui X | web X | mobile X
**Final**: ui X | web X | mobile X (+N tests)

#### What Was Accomplished

- [four surface fixes + root causes]

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` | Updated — ... |
| ... | ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/__tests__/batch_plp_fix_10/...` | Integration | N | ✅ |
```

---

## After This Task — Next Step

Commit + push and notify the batch is closed. Tom deploys the **web image** (Part A already deployed API + worker + Lambda), then runs the full design §Verification board: ① office1 `/schedule` renders / accountant hidden · ② accountant job detail — no Technicians error; office1 picker works · ③ checklist Show persists (Part A) · ④ tables show full values + h-scroll + Revoke visible · ⑤ accountant — no Generate-&-Copy-Link · ⑥ Security page session history (Part A). A green board closes the verification-plan tail and flips **Ord 27 (TEAM-INVITE-2) ✅ + the §7 invite gate ✅** (Architect action).

---

## Appendix — Completion Summary

### PLP-FIX-10 Part B — Board/Tech-Section/Link Gates + Tables Layout: Completion Summary

**Completed**: 2026-09-06
**Mode**: Pilot React Engineer
**Baseline**: ui 710 | web 2289 | mobile 701
**Final**: ui 710 | web 2302 (+13) | mobile 701

#### What Was Accomplished

- **INV-BUG-13**: Converted `DispatchBoardPage.tsx` gate from `role={["owner","accountant"]}` to `permission="schedule.view_all"` — office_staff now sees the board; accountant loses it (grant truth). Docstring corrected.
- **INV-BUG-10a**: `TechAssignmentSection.tsx` — section gated on `schedule.view_all` (hidden for accountant); picker/manage affordances already gated on `schedule.manage` via `RoleGate`; assignments-query 403 → render null (defense-in-depth); `ErrorState` only for non-403 failures.
- **INV-BUG-16**: `InvoiceDetailPage.tsx` — "Generate & Copy Link" button wrapped in `<RoleGate permission="invoices.update">` (BE gate grep-verified at `invoices.py`). Hidden for accountant + office_staff.
- **INV-BUG-15**: `TeamSettingsPage.tsx` + `PendingInvitesSection.tsx` — dropped `table-fixed`; wrapped tables in `overflow-x-auto` containers with `tabIndex={0}` + `role="region"` + `aria-label`; `whitespace-nowrap` on cells; truncate+tooltip as in-scroll fallback on email cell.
- **RoleGate prop widening**: `RoleGate.tsx` `permission` prop widened from `PermissionKey` to `string` to match `useHasPermission`'s `key: string` signature — `schedule.view_all` (not in the `PermissionKey` union) now compiles. `permissions.ts` untouched (zero permission changes).
- **Stale test fixtures updated**: 6 pre-existing test files updated to include `schedule.view_all` in auth fixtures (mirroring prod grant truth from `userPermissionsHandlers.ts` MSW fixture): `panel-403-grace.integration.test.tsx`, `tech_assignment.integration.test.tsx`, `dispatch_b2.integration.test.tsx`, `dispatch_b1_5.integration.test.tsx`, `dispatch_board_lanes.integration.test.tsx`, `invoice_ui_b1.integration.test.tsx`, `TechAssignmentSection.test.tsx`.

#### Files Changed / Created

| File | Action |
|---|---|
| `packages/ui/src/role-gate/RoleGate.tsx` | Updated — `permission` prop widened from `PermissionKey` to `string` |
| `apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` | Updated — gate → `permission="schedule.view_all"`; docstring corrected |
| `apps/web/src/features/jobs/components/TechAssignmentSection.tsx` | Updated — section gate + assignments-403 defense + docstring |
| `apps/web/src/features/invoices/components/InvoiceDetailPage.tsx` | Updated — Generate-&-Copy-Link gated `invoices.update` |
| `apps/web/src/features/settings/components/TeamSettingsPage.tsx` | Updated — table layout (overflow-x-auto, nowrap, no table-fixed) |
| `apps/web/src/features/settings/components/PendingInvitesSection.tsx` | Updated — table layout (overflow-x-auto, nowrap, no table-fixed) |
| `apps/web/src/__tests__/batch_plp_fix_10/board-gate.integration.test.tsx` | Created — 3 tests |
| `apps/web/src/__tests__/batch_plp_fix_10/tech-assignment-grace.integration.test.tsx` | Created — 4 tests |
| `apps/web/src/__tests__/batch_plp_fix_10/generate-link-gate.integration.test.tsx` | Created — 3 tests |
| `apps/web/src/__tests__/batch_plp_fix_10/settings-tables-layout.integration.test.tsx` | Created — 2 tests |
| `apps/web/src/__tests__/batch_plp_fix_10/checklist-show-contract.integration.test.tsx` | Created — 1 test |
| `apps/web/src/__tests__/batch_plp_fix_9/panel-403-grace.integration.test.tsx` | Updated — office_staff fixture (was accountant; accountant now lacks schedule.view_all) |
| `apps/web/src/__tests__/batch_ui_fix_2b/tech_assignment.integration.test.tsx` | Updated — owner auth fixture includes schedule.view_all + schedule.manage |
| `apps/web/src/__tests__/batch_dispatch_b2/dispatch_b2.integration.test.tsx` | Updated — owner auth fixture includes schedule.view_all |
| `apps/web/src/__tests__/batch_dispatch_b1_5/dispatch_b1_5.integration.test.tsx` | Updated — JobPropertiesPanel render wrapped with AuthContext |
| `apps/web/src/__tests__/batch_mkt_b11_dispatch/dispatch_board_lanes.integration.test.tsx` | Updated — JobPropertiesPanel renders wrapped with AuthContext |
| `apps/web/src/__tests__/batch_invoice_ui_b1/invoice_ui_b1.integration.test.tsx` | Updated — makeAuthValue role-aware with permissions; JobPropertiesPanel render wrapped with AuthContext |
| `apps/web/src/features/jobs/components/__tests__/TechAssignmentSection.test.tsx` | Updated — makeAuthContext includes permissions with schedule.view_all + schedule.manage |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/__tests__/batch_plp_fix_10/board-gate.integration.test.tsx` | Integration | 3 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_10/tech-assignment-grace.integration.test.tsx` | Integration | 4 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_10/generate-link-gate.integration.test.tsx` | Integration | 3 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_10/settings-tables-layout.integration.test.tsx` | Integration | 2 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_10/checklist-show-contract.integration.test.tsx` | Integration | 1 | ✅ |
| **Total** | | **13** | ✅ |

#### Notes

- `pnpm sync-api-types` ran — timestamp-only diff (key reordering, net -8 lines, no contract change).
- BE gate grep-verified: `send_invoice` at `invoices.py` uses `require_permission("invoices.update")`.
- `permissions.ts` untouched (zero permission changes — the `RoleGate` prop widening was the correct fix, not adding `schedule.view_all` to the `PermissionKey` union).
- Mobile suite untouched-green (701/0).
- No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf (React 19 compiler handles memoization).
- WCAG 2.2 AA: scroll regions have `tabIndex={0}` + `role="region"` + `aria-label` for keyboard access; target sizes preserved; focus not obscured.
