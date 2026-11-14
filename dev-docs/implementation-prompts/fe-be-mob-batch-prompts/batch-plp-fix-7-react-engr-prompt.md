# Implementation Prompt: PLP-FIX-7 Part B — Invite 409 FE Fix + Login Role-Race + Server-Authoritative RBAC + Pending-List Filter

**Mode**: Pilot React Engineer
**Batch**: PLP-FIX-7 (launch plan Ord 28, card §3.28) — **Part B (runs SECOND)**
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.28
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-7-design.md` — read **every section (A–I)** before coding
**Estimated session**: ~3 hours
**Platform**: Web only (`apps/web`) + shared auth/gating in `packages/ui`
**Backend companion**: **PLP-FIX-7 Part A (Python) MUST be complete first** — its 409 type-URI fix + office_staff `jobs.view` seed grant are contract inputs. Your first pre-work step is `pnpm sync-api-types`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-plp-fix-7-design.md`** — every section (A–I)

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls. (Pre-existing sanctioned exception: `AuthProvider.tsx`'s permissions fetch — leave its `fetch` as-is; do not copy that pattern anywhere else.)
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` all exist. This batch creates **zero** new visual components.
- **Rule 10**: If ANY test fails during your work — even one that appears pre-existing — **you must fix it before declaring the batch done**. No "not my fault" exception.
- **Rule 12 (TanStack Query v5)**: Object-form only; `isPending` not `isLoading`; colocated query keys; invalidate after mutations.
- **Rule 15 (WCAG 2.2 AA)**: the invite dialog + error states you touch must keep their existing AA properties (focus trap, non-color-only errors, ≥24px targets).

---

## Design Decisions / Context

Tom's TEAM-INVITE-1 prod run found five FE-side defects (design §B, all code-verified). You are fixing them as one batch because four share a single root theme: **the FE must consume server-authoritative RBAC, not a hand-maintained mirror**.

1. **INV-BUG-1 (409 crash)**: `useCreateInvite` parses the wrong envelope level. The house convention is FastAPI's nested form — body = `{"detail": {type, title, status, detail, invite_id?}}` — and `getApiProblem` (TEST-UPLIFT-1B) already unwraps it. The hook read top-level `data.type` (undefined) and passed the nested `data.detail` **object** through as a string; the dialog's generic branch rendered the object → React threw → route error boundary (Tom's black screen). Part A fixed the BE type URIs (`.../invite_pending_exists` / `.../invite_user_exists`); you fix the FE parse + harden the render.
2. **INV-BUG-2 (tech block no-op)**: `useLoginFlow` calls `onSuccess(role ?? "owner")` while the auth-context role is still resolving (async `/users/me/permissions` fetch after Cognito DONE) → technicians route as owner and the `role === "technician"` block in `usePostLoginRedirect` never fires. You make the login flow **await** the resolved user and delete the `?? "owner"` default.
3. **INV-BUG-3 (RBAC drift)**: `ROLE_PERMISSION_MAP` (packages/ui) drifted from the prod `tenant_user_role` grants in both directions (design §B.3 matrix). `AuthProvider` already fetches `GET /api/v1/users/me/permissions` — and **discards `permissions[]`**. You carry it on `PilotUser`, add a wildcard matcher, re-point `useRequiresPermission`/`RoleGate` at the server set, and gate both navs.
4. **INV-BUG-5**: `PendingInvitesSection` renders all invite states — filter out `status === "accepted"` (FE-only; the hook intentionally lists all states).
5. **INV-BUG-6**: long emails overflow the pending row — truncate with tooltip.

**Prod-verified `tenant_user_role` grants (design §A — your MSW fixtures MUST mirror these exactly, fixture-blindness is the bug class that shipped two of these defects):**

- `owner`: `*`, `users.manage`, `users.view`, `integrations.manage`, `jobs.loto_confirm`
- `office_staff`: `addresses.*`, `contacts.*`, `customers.*`, `invoices.create`, `invoices.view`, `quotes.*`, `reports.view`, `sites.*`, `users.view`, `schedule.manage`, `schedule.view_all`, `dashboard.manage` (+ **`jobs.view`** once Part A's converge lands — include it in fixtures)
- `technician`: `dashboard.manage`, `expenses.*`, `jobs.update`, `jobs.view`, `mobile_sync.*`, `nec.calculate`, `schedule.view_own`, `time_entries.*`, `voice.*`, `jobs.loto_confirm`
- `accountant`: `audit.view`, `dashboard.manage`, `reports.view`, `*.view`, `catalog.manage`

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch. If anything is already failing: confirm with Tom or fix first — never proceed on assumption.

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Part A expects an **empty** OpenAPI diff — if `sync-api-types` produces type changes, note them in your Completion Summary (someone else's spec drift, not yours). Consume types via `import type { components } from "@pilot/shared-types"`.

## Pre-Work: Endpoint Verification

Verify these exist in `backend/openapi_schema_map.md` before touching any hook:

- `POST /api/v1/users/invites` (create — 409 bodies now carry the specific type URIs after Part A)
- `GET /api/v1/users/invites` (list — `TeamInviteListItem.status` is BE-computed; do not recompute client-side)
- `POST /api/v1/users/invites/{invite_id}/resend` and the revoke endpoint (already consumed by `useResendInvite`/`useRevokeInvite`)
- `GET /api/v1/users/me/permissions` (returns `{user_id, tenant_id, role_code, role_name, permissions: string[]}` — confirm the response model name for the shared-types import)

## Pre-Work: Mandatory File Reads

1. `frontend/packages/ui/src/auth/AuthProvider.tsx` + `frontend/packages/ui/src/auth/types.ts`
2. `frontend/packages/ui/src/role-gate/permissions.ts` + `useRequiresPermission.ts` + `RoleGate.tsx`
3. `frontend/apps/web/src/components/AppSidebar.tsx`
4. `frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx` + `SettingsIndexPage.tsx` + `TeamSettingsPage.tsx`
5. `frontend/apps/web/src/features/login/hooks/useLoginFlow.ts` + `frontend/apps/web/src/hooks/usePostLoginRedirect.ts` + `frontend/apps/web/src/app/login/page.tsx`
6. `frontend/apps/web/src/features/settings/hooks/useCreateInvite.ts` + `components/InviteMemberDialog.tsx` + `components/PendingInvitesSection.tsx` + `hooks/useTeamInvites.ts`
7. The `getApiProblem` helper (TEST-UPLIFT-1B — locate via `grep -r "getApiProblem" apps/web/src packages/shared-api/src | head -5`)
8. `frontend/apps/web/src/mocks/handlers/index.ts` + the invite/permissions handler files it registers (you will update fixtures)

---

## Tasks

### Task 1 — Server permissions on the auth context (design §F.1)

- `types.ts`: `PilotUser` gains `permissions: string[]`; `AuthContextValue` gains `permissions: readonly string[]` (`[]` unauthenticated).
- `AuthProvider.fetchUserFromBackend`: map `permissions: data.permissions ?? []` onto the built `PilotUser`; expose from context. Mock mode (`buildMockUser`): derive permissions from `ROLE_PERMISSION_MAP[role]` so existing tests keep working.

### Task 2 — Wildcard matcher + gating re-point (design §F.2)

- `packages/ui/src/role-gate/permissions.ts`: add `hasPermission(perms: readonly string[], key: string): boolean` per the design's exact contract (`*` match-all, exact match, `resource.*` prefix expansion).
- New `packages/ui/src/role-gate/useHasPermission.ts`: `useHasPermission(key: string): boolean` — reads context permissions, delegates to `hasPermission`; when `user != null && permissions.length === 0` fall back to the static map path and `console.warn` once (defensive; should not occur outside mock mode).
- Re-point `useRequiresPermission` + `RoleGate` to the same server-set path (keep the `PermissionKey` union for call-site documentation; the matcher boundary accepts `string`).
- Export `hasPermission` + `useHasPermission` from `packages/ui/src/index.ts`.

### Task 3 — Nav gating (design §F.3 matrix)

- `AppSidebar.tsx`: items gain `permission?: string`; filter via `useHasPermission`. Apply the design §F.3 matrix exactly (Schedule→`schedule.manage`, Customers→`customers.view`, Quotes→`quotes.view`, Jobs→`jobs.view`, Invoices→`invoices.view`, Comms→`comms.send`, Catalog→`catalog.view`, Reports→`reports.view`, Dashboard→`dashboard.manage`).
- `SettingsSidebar.tsx`: **evaluate** `roleRequired` (currently dead config) via the same hook; Team item gains `roleRequired: "users.view"`.
- `SettingsIndexPage.tsx`: gate the Team card on `users.view`; audit the other cards' gates against the prod grant table (Operations/Integrations/Website stay hidden for office_staff — that matches prod; do not widen anything).
- `TeamSettingsPage.tsx`: confirm its `canManage` check flows through the re-pointed server-set path (`users.manage` — owner-only per prod).

### Task 4 — Login role-race fix (design §F.4)

- `AuthProvider`: expose a session-ready signal the login flow can await (simplest form consistent with the provider — e.g. `whenSessionReady(): Promise<PilotUser | null>` sharing the same in-flight load promise, or an `isSessionReady` flag the flow awaits with a short poll bound ~5 s). Do not change the provider's public shape beyond this addition.
- `useLoginFlow.submitCredentials` + `submitMfaCode`: on `signInStep === "DONE"`, **await** the resolved user and call `onSuccess(user.role)`. **Delete `?? "owner"`** in both places. If the user fails to resolve within the bound → set the existing error state ("Sign-in failed. Please try again.") and stay on `/login` — never default-route.
- `usePostLoginRedirect.ts`: `ROLE_ROUTE_MAP.accountant` → `/dashboard` (rename artifact — was `/operator/cohort`); unknown-role fallback `?? "/dashboard"` → sign-out + error notification + `/login`; fix the stale `tech` vocabulary in the docblock.

### Task 5 — Invite 409 FE fix (design §F.5)

- `useCreateInvite.ts`: replace the hand-rolled parse with `getApiProblem` (the house helper — it unwraps the nested envelope); read `type/title/detail/invite_id` from the unwrapped payload; keep the no-response network branch. Preserve the `CreateInviteError` shape the dialog consumes.
- `InviteMemberDialog.tsx`: generic-error branch renders `typeof errorState.detail === "string" ? errorState.detail : "Something went wrong. Please try again."`.
- Result contract (test plan Tests 5/6): duplicate pending → amber explainer + working **Resend invite** action; existing member → neutral "already has a Pilot account" explainer. **No error boundary on any 409.**

### Task 6 — Pending list filter + truncation (design §F.6)

- `PendingInvitesSection.tsx`: `visible = invites?.filter((i) => i.status !== "accepted")`; return `null` when empty (revoked rows keep rendering with their chip; accepted rows disappear).
- Email cell: `table-fixed` on the table + `max-w-0` cell + inner `<span className="block truncate" title={invite.email}>`; give the other columns explicit `w-*` header widths so proportions hold.

### Task 7 — MSW fixture fidelity (anti-fixture-blindness)

- Update the invite MSW handlers: 409 responses use the **nested envelope** with the Part-A type URIs (`invite_pending_exists` + `invite_id`, `invite_user_exists`) — mirrors the real FastAPI shape.
- Update the `users/me/permissions` handler: each role fixture carries the **prod-verified grant arrays** from Design Decisions §2 (office_staff includes `jobs.view` — Part A's converge is the prod rollout, fixtures lead it).
- Register any new handler files in `apps/web/src/mocks/handlers/index.ts`.

### Task 8 — Reports-blank investigation (design §G.4, bounded)

Repro locally as the seeded office_staff user on `/reports`. Fix to render the reports surface (or the designed empty state if the tenant simply has no report data). Suspects: a sub-resource call 403ing on a non-`reports.view` permission, or an unguarded empty-data render. **Do not widen office_staff's grants** and do not build reports features — the bound is working-or-empty-state.

### Task 9 — Tests

- Unit (Vitest): `hasPermission` (wildcard matrix incl. `*`, `resource.*`, exact, miss); `useHasPermission` (server set vs fallback); updated `useCreateInvite` (nested-envelope 409s → typed errors; network branch); `PendingInvitesSection` (accepted filtered; long-email truncation renders `title`); `useLoginFlow` (role awaited — technician resolves to `onSuccess("technician")`; unresolvable → error state, never owner).
- Integration: `apps/web/src/__tests__/batch_plp_fix_7/` — invite dialog 409 state machine (both branches render inline, Resend fires); office_staff nav matrix (Jobs visible, Comms/Catalog hidden, Settings→Team visible read-only); technician login block (banner + sign-out called); `AppSidebar` gating per role fixtures.
- TanStack Query v5 `retry: false` in test setup; MSW for all network; follow the existing `__tests__/batch_*` conventions.

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. The ONLY correct runner is `pnpm --filter web test` / `pnpm --filter @pilot/ui test`.

### Phase 1 — Targeted tests (run after each task group during development)

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -6
pnpm --filter web test 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_plp_fix_7/ 2>&1 | tail -10
```

Fix any failure before moving to the next task — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **`pnpm --filter mobile build` = mobile type check.** Any failure in either phase must be fixed before the batch is declared done — no "pre-existing failure" exception without Tom's written confirmation.

---

## Definition of Done — PLP-FIX-7 Part B

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors (or drift noted)
- [ ] Design doc fully read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] All endpoint URLs verified in `openapi_schema_map.md`
- [ ] Task 1: `PilotUser.permissions` + context exposure; mock mode derives from the static map
- [ ] Task 2: `hasPermission` + `useHasPermission`; `useRequiresPermission`/`RoleGate` on server set; exports added to `packages/ui/src/index.ts`
- [ ] Task 3: `AppSidebar` permission-keyed; `SettingsSidebar` `roleRequired` evaluated + Team `users.view`; `SettingsIndexPage` Team card gated; `TeamSettingsPage` manage check on server set
- [ ] Task 4: login flow awaits resolved role — `?? "owner"` deleted in BOTH submit paths; unknown-role → error + stay on `/login`; `usePostLoginRedirect` accountant `/dashboard` + unknown-role sign-out
- [ ] Task 5: `useCreateInvite` uses `getApiProblem`; dialog generic branch string-guarded; both 409 states render inline (no error boundary)
- [ ] Task 6: accepted invites filtered (section hides when empty); email truncation + tooltip
- [ ] Task 7: MSW invite 409s nested-envelope with Part-A URIs; permissions fixtures mirror the prod grant arrays; `index.ts` registrations
- [ ] Task 8: `/reports` renders for office_staff (or designed empty state) — root cause noted in the Completion Summary
- [ ] Task 9: unit + `batch_plp_fix_7` integration tests green; TQ v5 `retry: false`; MSW throughout
- [ ] axe-core zero violations on touched surfaces + WCAG spot-checks (dialog focus trap intact, non-color-only errors, ≥24px targets)
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; components pure (React Compiler, rules §32)
- [ ] No tenant-data fetching in Server Components (rules §35)
- [ ] Zero TypeScript errors (`check-types` passes)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite (targeted run confirms)
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===` — the exact command above)
- [ ] Final test count (before → after) documented in the Completion Summary appendix
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] Source spec task headers updated to ✅ Complete in any spec doc other than the launch plan — if applicable

---

## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below.
2. Note for Tom: the deploy order is **Part A backend first, then this frontend** (the 409 inline states expect the specific type URIs live), plus the prod seed converge from Part A (office_staff `jobs.view`).

```markdown
### PLP-FIX-7 Part B — 409 FE fix + login race + server RBAC: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (ui) | X passed (web)
**Final**: X+N passed (ui) | X+M passed (web)

#### What Was Accomplished

- [Server-authoritative permissions end-to-end (context → matcher → gates)]
- [Login role-race fix — technician block engages]
- [409 inline states + pending filter + truncation + reports-blank root cause]

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/packages/ui/src/...` | Created / Updated — ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/__tests__/batch_plp_fix_7/...` | Integration | N | ✅ |
```

---

## After This Task — Next Step

Tom re-runs Tests 5, 6, 10 of `team-invite-1-prod-test-plan.md` on prod after the Part A → Part B deploy — a green board flips the §7 invite gate (Architect action). PLP-FIX-8 (SMS recipient resolution, Ord 29) executes after that deploy per Tom's sequencing.

---

## Appendix — Completion Summary

### PLP-FIX-7 Part B — 409 FE fix + login race + server RBAC: Completion Summary

**Completed**: 2026-09-04
**Mode**: Pilot React Engineer
**Baseline**: 685 passed (ui) | 2256 passed (web)
**Final**: 685 passed (ui) | 2272 passed (web) — +16 web tests (14 new + 2 updated assertions)

#### What Was Accomplished

- **Server-authoritative permissions end-to-end** (context → matcher → gates): `PilotUser.permissions` carried from `GET /users/me/permissions` through `AuthProvider` → `AuthContextValue.permissions` → `useHasPermission` → `useRequiresPermission`/`RoleGate` → `AppSidebar`/`SettingsSidebar`/`SettingsIndexPage`/`TeamSettingsPage`. The static `ROLE_PERMISSION_MAP` is now the mock-mode fallback only, mirrored to prod grants (office_staff gains `dashboard.manage`+`users.view`+`jobs.view`, loses `comms.send`; technician loses `comms.send`, gains `dashboard.manage`+`jobs.view`; accountant gains `dashboard.manage`).
- **Login role-race fix** (INV-BUG-2): `useLoginFlow` now awaits `whenSessionReady()` to get the resolved user before calling `onSuccess(user.role)`. Deleted `?? "owner"` in both `submitCredentials` and `submitMfaCode`. Unknown-role fallback in `usePostLoginRedirect` now signs out + error notification + `/login` (never default-routes to a privileged landing). Accountant route corrected from `/operator/cohort` to `/dashboard` (ADR-0010 rename artifact).
- **409 inline states** (INV-BUG-1): `useCreateInvite` now uses `getApiProblem` (the house RFC 7807 normalizer) to unwrap the nested FastAPI envelope. `invite_id` passthrough extracted from the nested detail dict. Dialog generic-error branch string-guards the render (`typeof errorState.detail === "string"`). Both 409 branches render inline — no error boundary.
- **Pending list filter + truncation** (INV-BUG-5/6): `PendingInvitesSection` filters `status !== "accepted"` (section hides when empty). Email cell uses `table-fixed` + `max-w-0` + inner `<span className="block truncate" title={email}>` for ellipsis + tooltip.
- **Reports-blank root cause** (Task 8): `ProfitabilityPage` gated on `role={["owner", "accountant"]}` — office_staff excluded despite holding `reports.view`. Fixed to `permission="reports.view"` (server-authoritative gate). No grant widening.
- **MSW fixture fidelity**: Invite 409 handlers now use the nested envelope `{"detail": {type, title, status, detail, invite_id?}}` mirroring real FastAPI shape. New `userPermissionsHandlers.ts` serves `GET /users/me/permissions` with prod-verified grant arrays (office_staff includes `jobs.view` — Part A converge).

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/packages/ui/src/auth/types.ts` | Updated — `PilotUser.permissions` + `AuthContextValue.permissions` + `whenSessionReady` (all optional for test compat) |
| `frontend/packages/ui/src/auth/AuthProvider.tsx` | Updated — `userRef` + `updateUser` + `whenSessionReady` + `permissions` in context value + mock-mode derives from `ROLE_PERMISSION_MAP` |
| `frontend/packages/ui/src/role-gate/permissions.ts` | Updated — `hasPermission()` wildcard matcher (`*`, `resource.*`, `*.suffix`, exact); `ROLE_PERMISSION_MAP` mirrored to prod grants; `dashboard.manage`+`users.view` added to `PermissionKey` union |
| `frontend/packages/ui/src/role-gate/useHasPermission.ts` | Created — server-authoritative permission hook with static-map fallback |
| `frontend/packages/ui/src/role-gate/useRequiresPermission.ts` | Updated — delegates to `useHasPermission` |
| `frontend/packages/ui/src/role-gate/RoleGate.tsx` | Updated — permission check via `useHasPermission` (Rules-of-Hooks-safe) |
| `frontend/packages/ui/src/role-gate/index.ts` | Updated — exports `hasPermission` + `useHasPermission` |
| `frontend/packages/ui/src/index.ts` | Updated — exports `hasPermission` + `useHasPermission` |
| `frontend/apps/web/src/components/AppSidebar.tsx` | Updated — all 9 nav items permission-keyed per design §F.3 matrix |
| `frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx` | Updated — `roleRequired` evaluated via `useHasPermission`; Team item gains `users.view` |
| `frontend/apps/web/src/features/settings/components/SettingsIndexPage.tsx` | Updated — section-level gate removed; each card individually gated; Team card on `users.view` |
| `frontend/apps/web/src/features/settings/components/TeamSettingsPage.tsx` | Updated — outer gate `users.view` (office_staff sees read-only); inner `canManage` on `users.manage` |
| `frontend/apps/web/src/features/login/hooks/useLoginFlow.ts` | Updated — awaits `whenSessionReady()`; deleted `?? "owner"` in both submit paths |
| `frontend/apps/web/src/hooks/usePostLoginRedirect.ts` | Updated — accountant `/dashboard`; unknown-role sign-out + error; docblock fixed |
| `frontend/apps/web/src/features/settings/hooks/useCreateInvite.ts` | Updated — `getApiProblem` + `invite_id` passthrough from nested detail |
| `frontend/apps/web/src/features/settings/components/InviteMemberDialog.tsx` | Updated — generic-error branch string-guarded |
| `frontend/apps/web/src/features/settings/components/PendingInvitesSection.tsx` | Updated — accepted filter + `table-fixed` + email truncation + tooltip |
| `frontend/apps/web/src/features/profitability/components/ProfitabilityPage.tsx` | Updated — gate `permission="reports.view"` (was `role={["owner","accountant"]}`) |
| `frontend/apps/web/src/mocks/handlers/teamInviteHandlers.ts` | Updated — 409 responses use nested envelope |
| `frontend/apps/web/src/mocks/handlers/userPermissionsHandlers.ts` | Created — `GET /users/me/permissions` with prod-verified grant arrays |
| `frontend/apps/web/src/mocks/handlers/index.ts` | Updated — registers `userPermissionsHandlers` |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/__tests__/batch_plp_fix_7/hasPermission.test.ts` | Unit | 7 | ✅ |
| `apps/web/src/__tests__/batch_plp_fix_7/plp-fix-7.integration.test.tsx` | Integration | 7 | ✅ |

#### Tests Updated (existing — assertions changed to reflect new server-authoritative gating)

| Test File | Changes |
|---|---|
| `packages/ui/src/auth/useAuth.test.ts` | Added `permissions` + `whenSessionReady` to mock context |
| `packages/ui/src/role-gate/RoleGate.test.tsx` | Added `permissions` + `whenSessionReady` to mock context |
| `packages/ui/src/role-gate/useRequiresPermission.test.ts` | Added `permissions` + `whenSessionReady`; technician `comms.send` → `false` |
| `packages/ui/src/role-gate/permissions.test.ts` | Technician set updated (5 perms, no `comms.send`) |
| `packages/ui/src/role-gate/__tests__/permissions.team-invite-1.test.ts` | Technician `comms.send` → `false`; count → 5 |
| `apps/web/src/__tests__/batch_beta_v1_b6/sidebar-rbac.integration.test.tsx` | Nav matrix per role (office_staff no Comms; technician limited) |
| `apps/web/src/__tests__/batch_team_invite_1/team-settings-invite.integration.test.tsx` | 409 overrides use nested envelope; auth mock has `permissions` |
| `apps/web/src/features/settings/components/__tests__/SettingsSidebar.test.tsx` | AuthContext wrapper added |
| `apps/web/src/features/settings/components/__tests__/SettingsIndexPage.test.tsx` | office_staff sees Team card |
| `apps/web/src/__tests__/batch_fe_ui_nav_s1/settings_index.integration.test.tsx` | office_staff sees Team card |
| `apps/web/src/features/login/hooks/useLoginFlow.test.ts` | Mock `whenSessionReady` added |
| `apps/web/__tests__/batch_fe_b2/login-web.integration.test.tsx` | Mock `whenSessionReady` added |
| `apps/web/__tests__/batch_beta_b7/settings-sidebar.integration.test.tsx` | AuthContext wrapper added |

#### Notes for Tom

1. **Deploy order**: Part A backend first (409 type URIs + office_staff `jobs.view` seed), then this frontend.
2. **Comms for office_staff**: Prod grant set has no `comms.send` for office_staff — nav hides it. Whether office staff *should* get comms is a separate product/seed decision for Tom.
3. **Two test folders**: `apps/web/__tests__/` (older batches) and `apps/web/src/__tests__/` (newer batches) — historical artifact. Consolidating is recommended but out of scope for this batch (would touch ~100+ test files and import paths).
4. **`permissions` and `whenSessionReady` are optional** in `AuthContextValue`/`PilotUser` types to avoid breaking ~100 existing test mocks. The provider always sets them in production; `useHasPermission` falls back to the static map when undefined.
