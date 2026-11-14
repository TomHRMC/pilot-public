# Implementation Prompt: PLP-FIX-11 Part B — Accountant Schedule-Read Mirrors + Technicians Header Gate (INV-BUG-18)

**Mode**: Pilot React Engineer
**Batch**: PLP-FIX-11 (Part B of 2 — runs after Part A closes; launch plan Ord 32, card §3.32)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.32
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-11-design.md` — read fully (A–I); §G decisions are binding
**Estimated session**: ~1.5 hours
**Platform**: Web (`apps/web`) + `packages/ui` static map only — mobile untouched (must stay 701/0)
**Backend companion**: PLP-FIX-11 Part A (Python) ✅ must be closed first — it carries the `seed_core.py` grant + grant tests. Part B mirrors the grant in FE fixtures/maps (fixtures lead the prod converge per FIX-7 §C.1) and uses **existing** endpoints only (zero OpenAPI delta), so `pnpm sync-api-types` is a formality — still the mandatory first pre-work step.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-plp-fix-11-design.md`** — every section (A–I)

Critical rules for this batch:

- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all backend payload types come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api` — `fetch()` is permanently banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — `RoleGate`, `useHasPermission` all exist (design §I: **zero new components** this batch).
- **Rule 8**: No new npm dependencies.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. Root cause unidentifiable → STOP and ask Tom.
- **Rule 12 (TanStack Query v5)**: object-form only; `isPending` not `isLoading`; invalidate (don't hand-patch) after mutations.
- **`useHasPermission` / `RoleGate permission=` accept any string** (FIX-10 widened the `RoleGate` prop to `string` — `schedule.view_all` compiles without touching the `PermissionKey` union; **do NOT touch `permissions.ts`'s union** — the only `permissions.ts` change is the static `ROLE_PERMISSION_MAP.accountant` array).

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Mechanism | Seed grant (Part A) — FE mirrors only | Tom's ruling; route re-gate would expose technician too (§G-Q1) |
| Accountant board | **Renders read-only** — Schedule nav item appears automatically (server-authoritative nav, FIX-7) | Accepted side effect (§G-Q2); write affordances stay `schedule.manage`-gated |
| Accountant Technicians box | **Renders read-only with real names** — assignments 200 via the new grant; users list 200 via `*.view`→`users.view` wildcard (suffix matcher, verified `roles.py`) | Picker/remove stay `schedule.manage`-gated; `*.view` does not match `.manage` |
| `schedule.manage` / `view_own` | NOT granted — no FE affordance changes for them | §G-Q3/Q6 |
| Header gate | Ship it — wrap `JobDetailPage`'s "Technicians" wrapper in `RoleGate permission="schedule.view_all"` | Structural fix — parent rendered outside the child's gate (§G-Q5) |
| FIX-10 test flips | Update, don't preserve — accountant-hidden assertions reverse under the ruling | Same class as the 1E invariant update in Part A (§G-Q4) |
| Designer gate | **Waived** (design §H) — zero new surfaces, locked idioms | Same basis as FIX-7/9/10 |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact counts. **Expected: ui `710 passed` · web `2302 passed` · mobile `701 passed`** (post-PLP-FIX-10 state; mobile untouched this batch). Any pre-existing failure → confirm with Tom or fix first.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Expected: no type changes (Part A had a timestamp-only OpenAPI diff). Anything beyond a timestamp → note it in your Completion Summary and proceed — no endpoint contracts changed.

---

## Pre-Work: Read These Source Files

1. `frontend/packages/ui/src/role-gate/permissions.ts` — the static `ROLE_PERMISSION_MAP.accountant` (lines ~232-246) you extend; **do not** touch the `PermissionKey` union or `hasPermission()`
2. `frontend/apps/web/src/mocks/handlers/userPermissionsHandlers.ts` — the MSW prod-mirror `accountant` array (lines ~67-78) you extend
3. `frontend/apps/web/src/features/jobs/components/JobDetailPage.tsx` — the "Technicians" `<h4>` + wrapper (lines ~147-152); `RoleGate` is **already imported** (line 23)
4. `frontend/apps/web/src/features/jobs/components/TechAssignmentSection.tsx` — post-FIX-10 state; note the **stale FIX-9 comment** (lines ~63-65) claiming accountant 403s on `useTenantUsers` — you correct it in STEP 4
5. `frontend/apps/web/src/__tests__/batch_plp_fix_10/board-gate.integration.test.tsx` — the accountant-hidden assertion you flip
6. `frontend/apps/web/src/__tests__/batch_plp_fix_10/tech-assignment-grace.integration.test.tsx` — the accountant section-null assertion you flip
7. `frontend/apps/web/src/mocks/handlers/index.ts` — the MSW barrel; confirm no new handlers are needed (all endpoints already mocked)

Also run these greps to find every other test encoding the old accountant-hidden truth:

```bash
grep -rln "accountant" apps/web/src/__tests__ packages/ui/src --include="*.tsx" --include="*.ts" | xargs grep -ln "schedule\|Schedule\|Technicians" 2>/dev/null
grep -rn "accountant" apps/web/src --include="*.tsx" -l | xargs grep -ln "nav\|Sidebar" 2>/dev/null
```

Any hit asserting accountant **lacks** schedule surfaces gets the same ruling-reversal update — list each in your Completion Summary.

---

## Context: What This Batch Does

Tom ruled 2026-09-06 (FIX-10 verification): **"the accountant should be able to view jobs including what techs have been assigned."** Part A shipped the `schedule.view_all` seed grant. Part B mirrors it into the FE test/mock layer and fixes the structural bare-header defect his run surfaced:

| STEP | Change | File |
|---|---|---|
| 1 | Static fallback map += grant | `packages/ui/src/role-gate/permissions.ts` |
| 2 | MSW prod-mirror fixture += grant | `mocks/handlers/userPermissionsHandlers.ts` |
| 3 | "Technicians" header gate | `JobDetailPage.tsx` |
| 4 | Stale-comment correction | `TechAssignmentSection.tsx` |
| 5 | Test true-up + new read-only coverage | `__tests__/batch_plp_fix_11/` + FIX-10 flips |

**Out of scope**: mobile; the `PermissionKey` union; any new component; any endpoint/hook work (zero new hooks this batch).

## STEP 1 — Static fallback map (design §F)

In `permissions.ts` `ROLE_PERMISSION_MAP.accountant`, add `"schedule.view_all"` with a one-line PLP-FIX-11 comment (INV-BUG-18, Tom-ruled 2026-09-06 — mock-mode fallback parity with the seed grant). `as never`-style casts are not needed — `schedule.view_all` is not in the `PermissionKey` union; follow exactly how the existing map entries handle this (they are all union members — so if the compiler rejects the non-union key, add it via a **local** `as PermissionKey` cast on that one element with the comment explaining why; do NOT add it to the union).

## STEP 2 — MSW prod mirror (design §F)

In `userPermissionsHandlers.ts` `ROLE_PERMISSIONS.accountant`, add `"schedule.view_all"` with the same PLP-FIX-11 comment (mirrors the Part A converge — fixtures lead the prod rollout per FIX-7 §C.1). No other role changes.

## STEP 3 — Header gate (design §G-Q5)

In `JobDetailPage.tsx` (~lines 147-152): wrap the **entire** "Technicians" wrapper `<div>` (the `<h4>` **and** `<TechAssignmentSection>` together) in `<RoleGate permission="schedule.view_all">`. `RoleGate` is already imported (line 23) — no new import. Nothing else changes on the page.

## STEP 4 — Stale-comment correction

In `TechAssignmentSection.tsx` (lines ~63-65): the FIX-9 comment says `useTenantUsers` "403s for accountant" — accountant's `*.view` wildcard actually covers `users.view` (suffix matcher; BE gate `roles.py`), so post-FIX-11 the users query 200s for accountant. Correct the comment to describe the `usersForbidden` defense accurately (it now guards any future role lacking `users.view`). **No logic change** — comment only.

## STEP 5 — Tests (`apps/web/src/__tests__/batch_plp_fix_11/` + FIX-10 flips)

Follow the FIX-10 `renderWithAuth` pattern (`batch_plp_fix_10/board-gate.integration.test.tsx`) — server-authoritative permission arrays, `retry: false` QueryClients, MSW at the HTTP level (never mock `apiClient`):

1. **FLIP — `batch_plp_fix_10/board-gate.integration.test.tsx`**: the accountant case currently asserts nothing renders. With STEP 2's fixture, accountant now holds the grant → update the assertion to **board content renders for accountant** (same lane/grid testids the office_staff case uses). Keep the office_staff + owner cases.
2. **FLIP — `batch_plp_fix_10/tech-assignment-grace.integration.test.tsx`**: the accountant case currently asserts section null. Update to: **accountant → the section renders the assignment rows read-only** (assignments + users MSW handlers return data) — `tech-row-*` testids present, **no** `add-tech-select`, **no** `remove-btn-*`. Keep the office_staff picker case, the 403-override → null case, and the 500-override → ErrorState case unchanged (they exercise office_staff — still valid).
3. **NEW — `batch_plp_fix_11/technicians-header-gate.integration.test.tsx`**: a role **without** `schedule.view_all` (use the technician fixture — holds `schedule.view_own` only) rendering `JobDetailPage` (or the narrowest mount that includes the wrapper — follow existing job-detail test infra if one exists) → `queryByText("Technicians")` is **null**; and an accountant render → the "Technicians" header **is** present (post-grant).
4. **NEW — `batch_plp_fix_11/accountant-schedule-readonly.integration.test.tsx`** (optional merge into 3 if cleaner): accountant on the dispatch board → board renders; write affordances absent (no drag-enabled affordance your existing board tests key on — reuse the board-gate test's assertions).

Grep-sweep hits from Pre-Work get the same treatment. If a nav test asserts accountant's nav set, it must now include Schedule.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. The ONLY correct runner is `pnpm --filter web test`.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/__tests__/batch_plp_fix_11/ apps/web/src/__tests__/batch_plp_fix_10/ 2>&1 | tail -10
pnpm --filter @pilot/ui test 2>&1 | tail -6
```

Fix any failure before moving to the next step — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without Tom's written confirmation. W1/W2 mobile warnings are verified benign (inclusions §10.2) — do not chase them. Mobile `--forceExit` lives in the test script (§10.1) — use the commands as written.

---

## Definition of Done — PLP-FIX-11 Part B

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (ui 710 / web 2302 / mobile 701 — zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — timestamp-only diff confirmed
- [ ] Design doc fully read before writing any code
- [ ] All mandatory source files read before modifying (including `mocks/handlers/index.ts`)
- [ ] **STEP 1**: `ROLE_PERMISSION_MAP.accountant` += `schedule.view_all` (union untouched; local cast only if the compiler requires it)
- [ ] **STEP 2**: MSW `ROLE_PERMISSIONS.accountant` += `schedule.view_all` with the PLP-FIX-11 comment
- [ ] **STEP 3**: "Technicians" wrapper (header + section) gated `permission="schedule.view_all"` in `JobDetailPage.tsx` — no new imports
- [ ] **STEP 4**: stale FIX-9 `useTenantUsers` comment corrected (comment-only)
- [ ] **STEP 5**: FIX-10 board-gate + tech-assignment-grace flips green; new `batch_plp_fix_11/` tests green (technician → no header; accountant → header + read-only rows); grep-sweep hits handled
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; components pure (rules §32)
- [ ] axe-core zero violations on changed surfaces (rules §36)
- [ ] Zero TypeScript errors (`check-types`); zero ESLint `no-hardcoded-design-values` warnings
- [ ] `PermissionKey` union untouched (only the static map array changed)
- [ ] Mobile suite untouched-green (701/0)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`) — exact command from the Final Verification section
- [ ] Final test count (before → after) documented in the Completion Summary appendix
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] Source spec task headers updated to ✅ Complete in any spec doc other than the launch plan — if applicable (N/A — no separate spec doc)

---

## Completion Summary

After all Definition of Done items are complete, fill in the appendix at the end of THIS prompt doc using the format below.

```markdown
### PLP-FIX-11 Part B — Accountant Schedule-Read Mirrors + Header Gate: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: ui X | web X | mobile X
**Final**: ui X | web X (+N) | mobile X

#### What Was Accomplished

- [grant mirrors + header gate + flips + stale comment]

#### Files Changed / Created

| File | Action |
|---|---|
| `packages/ui/src/role-gate/permissions.ts` | Updated — ... |
| ... | ... |

#### Tests Added / Updated

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/__tests__/batch_plp_fix_11/...` | Integration | N | ✅ |
```

---

## After This Task — Next Step

Commit + push and notify the batch is closed. Tom runs: **prod converge** (`seed_prod_db.py --mode seed --stripe-mode test`, typed `PILOT-PROD-SEED` — no API/worker/Lambda deploy) → **web image** → design §Verification 1-5: ① accountant sees the Technicians box **populated, read-only** (names/avatars; no picker/remove) on a job with an assignment · ② accountant Schedule nav appears, board read-only · ③ office1 picker regression · ④ converge SQL proof (`permissions ? 'schedule.view_all'` → `t`, `? 'schedule.manage'` → `f` on the accountant role) · ⑤ header-gate is code-covered (no prod-visible role triggers it). A green board closes INV-BUG-18.

---

## Appendix — Completion Summary

### PLP-FIX-11 Part B — Accountant Schedule-Read Mirrors + Header Gate: Completion Summary

**Completed**: 2026-09-06
**Mode**: Pilot React Engineer
**Baseline**: ui 710 | web 2302 | mobile 701
**Final**: ui 710 | web 2307 (+5) | mobile 701

#### What Was Accomplished

- Mirrored the Part A `schedule.view_all` seed grant into the FE static fallback map (`ROLE_PERMISSION_MAP.accountant`) and the MSW prod-mirror fixture (`ROLE_PERMISSIONS.accountant`), with PLP-FIX-11 comments referencing INV-BUG-18 and the Tom ruling.
- Added `schedule.view_all` to the `owner` and `office_staff` static map entries (they hold it in prod via `*` wildcard / explicit grant; the static map needed explicit keys for mock-mode fallback parity now that the AppSidebar nav gate uses `schedule.view_all`).
- Wrapped the entire "Technicians" wrapper (`<h4>` + `<TechAssignmentSection>`) in `<RoleGate permission="schedule.view_all">` in `JobDetailPage.tsx` — fixes the structural bare-header defect (parent rendered outside the child's gate).
- Changed the AppSidebar Schedule nav item gate from `schedule.manage` to `schedule.view_all` (Tom-approved) so accountant sees the Schedule nav item (read-only board). Write affordances inside the board stay `schedule.manage`-gated. Widened `NavItem.permission` type to `string` and `permissionGranted` map to `Record<string, boolean>` to accommodate the non-union key. Removed the now-unused `PermissionKey` type import.
- Corrected the stale FIX-9 `useTenantUsers` comment in `TechAssignmentSection.tsx` — accountant's `*.view` wildcard covers `users.view` (suffix matcher; BE gate `roles.py`), so the users query 200s post-grant. The `usersForbidden` defense now accurately described as guarding any future role lacking `users.view`.
- Flipped the FIX-10 board-gate accountant test from "board hidden" to "board renders (read-only)".
- Flipped the FIX-10 tech-assignment-grace accountant test from "section null" to "section renders read-only rows, no picker, no remove button".
- Created 2 new test files in `batch_plp_fix_11/`: technicians-header-gate (technician → no header; accountant → header present) and accountant-schedule-readonly (accountant → Schedule nav appears + board renders read-only; technician → Schedule nav absent).
- `PermissionKey` union untouched (only the static map arrays changed; local `as PermissionKey` casts on the non-union `schedule.view_all` entries).
- Zero new components, zero new hooks, zero new npm dependencies, zero endpoint changes.
- Mobile suite untouched-green (701/0).

#### Files Changed / Created

| File | Action |
|---|---|
| `packages/ui/src/role-gate/permissions.ts` | Updated — `ROLE_PERMISSION_MAP.accountant` += `schedule.view_all` (local `as PermissionKey` cast); `owner` and `office_staff` entries also += `schedule.view_all` for mock-mode nav-gate parity |
| `apps/web/src/mocks/handlers/userPermissionsHandlers.ts` | Updated — `ROLE_PERMISSIONS.accountant` += `schedule.view_all` with PLP-FIX-11 comment |
| `apps/web/src/features/jobs/components/JobDetailPage.tsx` | Updated — wrapped Technicians wrapper (header + section) in `<RoleGate permission="schedule.view_all">` |
| `apps/web/src/components/AppSidebar.tsx` | Updated — Schedule nav gate changed from `schedule.manage` to `schedule.view_all`; `NavItem.permission` widened to `string`; `permissionGranted` map widened to `Record<string, boolean>`; `canSchedule` uses `useHasPermission`; removed unused `PermissionKey` import |
| `apps/web/src/features/jobs/components/TechAssignmentSection.tsx` | Updated — stale FIX-9 `useTenantUsers` comment corrected (comment-only, no logic change) |
| `apps/web/src/__tests__/batch_plp_fix_10/board-gate.integration.test.tsx` | Updated — accountant case flipped from "board hidden" to "board renders (read-only)"; header comment + makeAuth comment updated |
| `apps/web/src/__tests__/batch_plp_fix_10/tech-assignment-grace.integration.test.tsx` | Updated — accountant case flipped from "section null" to "section renders read-only rows, no picker"; users MSW handler returns data; header comment updated |
| `apps/web/src/__tests__/batch_plp_fix_11/technicians-header-gate.integration.test.tsx` | Created — technician → no "Technicians" header; accountant → header present |
| `apps/web/src/__tests__/batch_plp_fix_11/accountant-schedule-readonly.integration.test.tsx` | Created — accountant → Schedule nav appears + board renders read-only; technician → Schedule nav absent |

#### Tests Added / Updated

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `batch_plp_fix_10/board-gate.integration.test.tsx` | Integration (flipped) | 3 | ✅ |
| `batch_plp_fix_10/tech-assignment-grace.integration.test.tsx` | Integration (flipped) | 4 | ✅ |
| `batch_plp_fix_11/technicians-header-gate.integration.test.tsx` | Integration (new) | 2 | ✅ |
| `batch_plp_fix_11/accountant-schedule-readonly.integration.test.tsx` | Integration (new) | 3 | ✅ |

#### Grep-Sweep Hits

- `sidebar-rbac.integration.test.tsx`: no accountant Schedule assertion existed — no change needed (technician "no Schedule" assertion still valid; owner/office_staff "sees Schedule" assertions still valid).
- `AppSidebar.test.tsx`: uses owner `["*"]` wildcard — `hasPermission(["*"], "schedule.view_all")` returns true; technician test uses `ROLE_PERMISSION_MAP.technician` (no `schedule.view_all`) — still correct. No changes needed.
- No other tests encoded the old accountant-lacks-schedule truth.

#### Deviation from Prompt

- **STEP 3b (AppSidebar)**: The prompt's 5 steps did not include touching AppSidebar. The design §G-Q2 states the Schedule nav appearing for accountant is an "accepted side effect" of the grant, but the AppSidebar gated the Schedule nav on `schedule.manage` (which accountant does NOT receive). Tom was asked and approved changing the gate to include `schedule.view_all` so the nav item appears for accountant. This required widening `NavItem.permission` to `string` and adding `schedule.view_all` to the `owner` and `office_staff` static map entries (for mock-mode fallback parity).
- All other steps executed exactly as specified in the prompt.
