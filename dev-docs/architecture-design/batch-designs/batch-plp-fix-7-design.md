# PLP-FIX-7 — Design: Invite 409 Crash + Technician Web-Block + office_staff RBAC Reconciliation + Pending-List Filter + Row Overflow

**Batch**: PLP-FIX-7 (launch plan Ord 28, card §3.28) · **Type**: Mixed (§1.3) — **Part A (Python, small, runs first)** + **Part B (React, primary)**
**Date**: 2026-09-04 · **Author**: Pilot Architect · **Status**: v1.0 — for Tom approval
**Findings source**: `team-invite-1-prod-test-plan.md` Result lines (Tests 5, 6, 10 ❌) + `tom-ui-issues-tracking.md` INV-BUG-1…6 · **Estimate**: A ~1 h · B ~3 h
**Designer gate**: N/A (existing surfaces, defect fixes + locked §16 patterns — same waiver posture as PLP-FIX-4/5, recorded §H)

---

## A. Input Read Summary

| Input | What it contributed | Read |
|---|---|---|
| `team-invite-1-prod-test-plan.md` | Test 5/6/10 contracts (409 explainers, tech block, office RBAC expectations); failure-signature table | ✅ 2026-09-04 |
| `tom-ui-issues-tracking.md` INV-BUG-1…6 | The six logged defects with severities | ✅ 2026-09-04 |
| PROD `tenant_user_role` grants (postgres-prod MCP) | Server-authoritative permission sets per role — the RBAC truth | ✅ 2026-09-04 (prod ≡ local) |
| `InviteMemberDialog.tsx` | 409 state machine (safe as written) | ✅ |
| `useCreateInvite.ts` | The envelope-misparsing hook (INV-BUG-1 FE half) | ✅ |
| `team_invites.py` (`_to_http_exception`) | The 409 body construction (INV-BUG-1 BE half) | ✅ |
| `usePostLoginRedirect.ts` + `useLoginFlow.ts` | Tech-block logic (intact) + the role race (INV-BUG-2 root) | ✅ |
| `AuthProvider.tsx` | `GET /users/me/permissions` already fetched, `permissions[]` **discarded** | ✅ |
| `permissions.ts` + `useRequiresPermission.ts` | The drifted FE-hardcoded `ROLE_PERMISSION_MAP` | ✅ |
| `AppSidebar.tsx` + `SettingsSidebar.tsx` | Main nav (no gating) + settings sidebar (`roleRequired` declared, never evaluated) | ✅ |
| `PendingInvitesSection.tsx` + `useTeamInvites.ts` | All-states list (no accepted filter) + unbounded email cell | ✅ |

---

## B. Root-Cause Findings (all code-verified 2026-09-04)

### B.1 — INV-BUG-1 (409 crash): triple contract defect

1. **BE type URIs are generic** — `team_invites.py` maps both `invite_user_exists` and `invite_pending_exists` to `https://errors.pilotfortrades.com/conflict`. The FE dialog's state machine matches the **specific** URIs (`.../invite_pending_exists`, `.../invite_user_exists`) → both branches never fire.
2. **FE parses the wrong envelope level** — the house convention (used by `getApiProblem`, TEST-UPLIFT-1B) is FastAPI's nested form: body = `{"detail": {type, title, status, detail, invite_id?}}`. `useCreateInvite.ts` reads `data.type` (undefined at top level) and passes `data.detail` — **the nested object** — through as a `string`.
3. **Generic branch renders a non-string** → React throws *"Objects are not valid as a React child"* → route error boundary → the black full-page error Tom saw on every 409.

Fix = BE emits the two specific type URIs (contract alignment; other codes keep `/conflict`) **and** FE unwraps via the house helper + string-hardens the render. Defense in depth — either alone prevents the crash; both fixes ship because the URI specificity is also the state-machine contract.

### B.2 — INV-BUG-2 (tech block no-op): role race + unsafe default

`useLoginFlow.ts`: on `signInStep === "DONE"` it calls `onSuccess(role ?? "owner")`, where `role` comes from the auth context — which AuthProvider populates **asynchronously** (Cognito session → `GET /api/v1/users/me/permissions`). At the DONE moment the context role is commonly still `null` → **`?? "owner"` routes everyone as owner** → `redirectForRole("owner")` → auth/me → `/dashboard`. The exact-match `role === "technician"` block never engages. Invisible for owners (same destination); fatal for the technician block.

Latent secondary: `ROLE_ROUTE_MAP` maps `accountant → /operator/cohort` (an ADR-0010 rename artifact — the old `operator` key). The server `redirect_to` currently wins so it's masked; the rename left a wrong fallback. And `ROLE_ROUTE_MAP[role] ?? "/dashboard"` is a privileged-default for unknown roles.

### B.3 — INV-BUG-3 (RBAC): FE mirror map drifted from server grants

The FE gates nav/pages on a **hand-maintained** `ROLE_PERMISSION_MAP` while the BE enforces `tenant_user_role.permissions` (jsonb). Drift (FE map vs **prod-verified** grants):

| Surface | FE map (office_staff) | PROD grant | Observed |
|---|---|---|---|
| Settings → Team | no `users.view` key exists at all | `users.view` ✅ | **over-hide** — Team absent |
| Jobs | `jobs.view` ✅ | none | **under-hide** — nav shows, API 403s |
| Comms | `comms.send` ✅ | none | **under-hide** — nav shows, API 403s |
| Catalog | `catalog.view` ✅ | none | **under-hide** — nav shows, API 403s |
| Schedule | `schedule.manage` ✅ | `schedule.manage` + `schedule.view_all` ✅ | nav OK, but the board loads jobs → `jobs.view` missing → page error |
| Reports | `reports.view` ✅ | `reports.view` ✅ | page renders but is blank (see §H.4) |

Compounding: AuthProvider **already fetches** the server set (`AuthProvider.tsx` → `{user_id, tenant_id, role_code, role_name, permissions: string[]}`) and **discards it** — `PilotUser` keeps only role/tenantId. Main nav (`AppSidebar.tsx`) has no gating at all; settings sidebar declares `roleRequired` but never evaluates it (`SettingsSidebar.tsx`).

Fix = **server-authoritative permissions in the FE** (ADR-0010 direction): carry `permissions[]` on `PilotUser`, check them (with wildcard expansion) in `useRequiresPermission`/`RoleGate`, gate both navs, fix the Team surface to `users.view`-visibility. The static map stays only as a mock-mode/test fallback. The mirror-drift class dies with this batch.

### B.4 — INV-BUG-5 (pending list): no accepted-row filter

`useTeamInvites` lists "all states" by design (revoked chips show); `PendingInvitesSection` maps **every** row — accepted invites never leave the list. Fix = FE-side filter on the BE-computed `status` (`!== "accepted"`); section hides when the filtered list is empty. **No BE change** (decision §H.2).

### B.5 — INV-BUG-6 (row overflow): unbounded email cell

`PendingInvitesSection.tsx` renders `{invite.email}` in a plain `<td>` — long addresses stretch the table (container is `overflow-hidden`, no scroll). Fix = truncate with ellipsis + `title` attr (`max-w-0 truncate` idiom on the cell, inner span `title={invite.email}`).

---

## Part A — Backend (Python Engineer)

### C. Migration & Seed Plan

**No migration DDL.** Two data changes, both via the established seed paths:

**C.1 — `office_staff` gains `jobs.view`** (Group A seed; resolves the Schedule-page 403 — §H.1 Tom decision, recommend YES):

- Locate the `tenant_user_role` seed owner (expected `migrations/scripts/seed_core.py` or `seed_platform.py` — **engineer verifies the owning script at pre-work via grep for `schedule.view_all`**) and add `"jobs.view"` to the office_staff `permissions` jsonb array (idempotent pattern already in the script — `ON CONFLICT`/value-scoped per seed rules §11).
- **Prod rollout** (Tom, post-deploy): `seed_prod_db.py --mode seed --stripe-mode test` converge (typed `PILOT-PROD-SEED`) — the established prod path; then verify via `postgres-prod` MCP that office_staff `permissions` contains `jobs.view`.
- **README update** (Rule 11.5): `backend/README-seed-data.md` §4 — office_staff grant list gains `jobs.view` (+ note: Schedule board requires it).
- **Verification**: `seed_core.py --mode inspect` + `pytest -m unit`.

**C.2 — 409 type-URI contract fix** (`team_invites.py` `_to_http_exception`):

```python
error_type_map = {
    "invalid_role": "https://errors.pilotfortrades.com/invalid-role",
    "invite_user_exists": "https://errors.pilotfortrades.com/invite_user_exists",      # was /conflict
    "invite_pending_exists": "https://errors.pilotfortrades.com/invite_pending_exists", # was /conflict
    "invite_not_found": "https://errors.pilotfortrades.com/not-found",
    "invite_already_accepted": "https://errors.pilotfortrades.com/conflict",
    "invite_revoked": "https://errors.pilotfortrades.com/conflict",
}
```

The envelope stays the house-standard nested `HTTPException(detail={...})` form (FE Part B parses it via `getApiProblem`; other consumers already do). `invite_id` passthrough for `InvitePendingExistsError` unchanged.

**C.3 — MCP verification queries (pre-work)**:

```sql
-- 1. Current office_staff grants (expect: no jobs.view pre-change)
SELECT code, permissions FROM public.tenant_user_role WHERE code = 'office_staff';
-- 2. Seed-owner grep target confirmation (engineer runs grep, not SQL)
-- 3. Post-seed verification (local): permissions contains 'jobs.view'
SELECT permissions ? 'jobs.view' AS has_jobs_view FROM public.tenant_user_role WHERE code = 'office_staff';
```

### D. New/Changed API Endpoints

None new. Changed: `POST /api/v1/users/invites` (+ `/test` twin) 409 error bodies for the two conflict codes — `type` field value changes only (`/conflict` → the specific URI); no schema-model change, **no OpenAPI regen required** (error bodies aren't response models — engineer confirms `openapi.json` diff is empty and still runs `export_openapi_json.py` as the handoff signal per §1.3).

### E. Execution Order (Part A)

1. Pre-work: baseline (`pytest -m unit --tb=no -q | tail -5`), MCP C.3 queries, grep the seed owner of `tenant_user_role` rows.
2. Seed change (C.1) + seed README §4 update.
3. `_to_http_exception` URI map (C.2).
4. Tests: update/extend `test_team_invites.py` — assert the two 409 bodies carry the specific type URIs (+ `invite_id` on pending_exists); assert office_staff seed set contains `jobs.view` (seed-level test or inspect assertion, per the script's existing test posture).
5. Two-phase gate: Phase 1 unit-only; Phase 2 full vendor-deselected suite.

---

## Part B — Frontend (React Engineer)

### F. Shared Module Interfaces

**F.1 — Server permissions on the auth context** (`packages/ui/src/auth`):

```ts
// types.ts — PilotUser gains:
export interface PilotUser {
  // …existing fields…
  permissions: string[];   // server-authoritative set from GET /users/me/permissions
}
// AuthContextValue gains:
permissions: readonly string[];   // [] when unauthenticated
```

`AuthProvider.tsx` `fetchUserFromBackend` maps `permissions: data.permissions ?? []`; mock-mode `buildMockUser` keeps producing permissions from the static map (test compatibility).

**F.2 — Wildcard permission matcher** (`packages/ui/src/role-gate/permissions.ts`):

```ts
export function hasPermission(perms: readonly string[], key: string): boolean {
  if (perms.includes("*")) return true;
  if (perms.includes(key)) return true;
  const prefix = key.split(".")[0] + ".";
  return perms.some((p) => p.endsWith(".*") && key.startsWith(p.slice(0, -1)));
}
```

Covers server wildcards (`customers.*` → `customers.view/create/edit/…`; `*` → owner). `useRequiresPermission` + `RoleGate` switch from `ROLE_PERMISSION_MAP[role].has(key)` to `hasPermission(userPermissions, key)`; the static map is retained **only** as the mock-mode source + documented fallback when `user != null && permissions.length === 0` (defensive — should not occur; log a console warning once). `PermissionKey` union relaxed to `string` at the matcher boundary (server emits keys the FE union doesn't declare, e.g. `schedule.view_all`) — the union stays for compile-time call-site documentation.

**F.3 — Nav gating** (server keys; prod-verified matrix):

| Nav item | Gate key | office_staff (prod) | Result after fix |
|---|---|---|---|
| Dashboard | `dashboard.manage` | ✅ | visible |
| Schedule | `schedule.manage` | ✅ | visible (+ works once A-C.1 lands) |
| Customers | `customers.view` | ✅ (`customers.*`) | visible |
| Quotes | `quotes.view` | ✅ (`quotes.*`) | visible |
| Jobs | `jobs.view` | ✅ after A-C.1 | visible |
| Invoices | `invoices.view` | ✅ | visible |
| Comms | `comms.send` | ❌ | **hidden** (§H.3) |
| Catalog | `catalog.view` | ❌ | **hidden** |
| Reports | `reports.view` | ✅ | visible (blank-page fix §G.4) |

- `AppSidebar.tsx`: items gain a `permission?: string` field; render filters via `useRequiresPermission`-family check against the **server set** (new lightweight `useHasPermission(key)` hook in packages/ui consuming F.2).
- `SettingsSidebar.tsx`: `roleRequired` becomes **evaluated** (same hook); Team item gains `roleRequired: "users.view"` → office_staff sees Team (read-only affordances already gated `users.manage` in `TeamSettingsPage.tsx` — verify that check also consumes the server set after F.2).
- Settings index page (`SettingsIndexPage.tsx`): Team card gated on `users.view` (audit the other cards' gates against prod grants while touching — Operations/Integrations/Website stay hidden for office_staff, matching prod).

**F.4 — Login role-race fix** (INV-BUG-2):

- `AuthProvider` exposes a session-ready signal the login flow can await (engineer's choice of the simplest form that fits the provider — e.g. a `whenSessionReady(): Promise<PilotUser | null>` resolving with the loaded user, or an `isSessionReady` flag polled with a short bound). Contract: `useLoginFlow.submitCredentials` on `signInStep === "DONE"` **awaits the resolved user** and calls `onSuccess(user.role)` — **`?? "owner"` is deleted**. If the user fails to resolve within a bounded wait (~5 s), show the existing error state ("Sign-in failed. Please try again.") and stay on `/login` — never default-route to a privileged landing. Same fix in `submitMfaCode`.
- `usePostLoginRedirect.ts`: `ROLE_ROUTE_MAP` `accountant` entry corrected `/operator/cohort` → `/dashboard` (rename artifact); unknown-role fallback `?? "/dashboard"` → sign-out + `/login` with an error notification (unknown role must never land in the app). Stale `tech` vocabulary in the file docblock corrected.

**F.5 — Invite 409 FE fix** (INV-BUG-1):

- `useCreateInvite.ts`: parse via the house helper (`getApiProblem` from TEST-UPLIFT-1B — it unwraps the nested `detail` envelope), preserving the `invite_id` passthrough read from the unwrapped payload; keep the no-response network branch.
- `InviteMemberDialog.tsx`: generic-error branch renders `typeof errorState.detail === "string" ? errorState.detail : "Something went wrong. Please try again."` (belt-and-braces against any future non-string detail).
- The two 409 branches then engage per the designed state machine: `invite_pending_exists` → explainer + **Resend invite** action; `invite_user_exists` → "already has a Pilot account" explainer (test plan Tests 5/6 contract).

**F.6 — Pending list filter + row overflow** (INV-BUG-5/6):

- `PendingInvitesSection.tsx`: `const visible = invites?.filter((i) => i.status !== "accepted")` — section returns `null` when `visible` is empty (revoked rows keep rendering with their chip; accepted rows disappear — test plan Test 3 contract "accepted invite leaves pending").
- Email cell: truncate + tooltip (`<td className="px-4 py-3 text-neutral-900 max-w-0"><span className="block truncate" title={invite.email}>{invite.email}</span></td>`; table gets `table-fixed` so `max-w-0` takes effect; role/sent/expires/status/actions columns keep current proportions via `w-*` on headers).

### G. Pattern Reuse Decisions (§16 + house)

1. **Hide-not-disable** — nav gating composes the existing `RoleGate`/`useRequiresPermission` pattern, re-pointed to server truth; no new UX pattern introduced.
2. **House error helper** — `getApiProblem` (TEST-UPLIFT-1B) is the only RFC 7807 parser; one-off parsing in `useCreateInvite` is deleted (its own comment admits it reimplemented the helper badly).
3. **Graceful 403 state** — pages that can still 403 (e.g., a deep-link to a hidden surface) render the shared `<ErrorState>`/`type="server"` pattern rather than crashing; the nav fix makes the common path unreachable, the page guard is defense in depth. Applied to the five surfaces Tom hit only — no broad page sweep (scope discipline).
4. **409-and-refresh** — the Resend-offer path already invalidates `team-invites`; unchanged.
5. **G.4 (Reports blank)** — `reports.view` is held, so the blank Reports page is a page/API defect, not gating: engineer repros locally as a seeded office_staff user and fixes to render the reports surface (or the designed empty state if the tenant simply has no report data yet). Suspects: a sub-resource call 403ing on a non-`reports.view` permission, or an unguarded empty-data render. Fix must not widen office_staff's grants.

### H. Open Questions Resolved

1. **Grant office_staff `jobs.view`?** → **YES (recommended, needs Tom's confirm at approval)** — office staff schedule jobs; they must see them. Technicians already hold it. Implemented via seed (C.1) + prod converge. If Tom declines, fallback = Schedule page degrades to a permission notice for office_staff (inferior — office can't do its core job).
2. **INV-BUG-5 filter location** → **FE-only**. The hook intentionally lists all states (revoked chips are a designed affordance); the BE list endpoint contract is unchanged.
3. **Comms for office_staff** → **follow prod truth: hidden**. The prod grant set has no comms permission for office_staff; whether office staff *should* get comms is a separate product/seed decision for Tom, not this batch. Flagged in the Completion Summary for Tom's awareness.
4. **Reports blank root** → treated as a defect to diagnose and fix in-batch (G.4), not assumed to be gating; bounded to a working-or-empty-state outcome (no reports feature work).
5. **Accountant fallback route** → `/dashboard` (F.4); `operator` vocabulary is gone (ADR-0010).
6. **Unknown-role posture at login** → never default to a privileged route (F.4): bounded wait → error + stay on `/login`.
7. **Designer gate** → N/A (existing surfaces, defect fixes, locked §16 patterns; same posture Tom waived for PLP-FIX-4/5).

### I. Component Manifest (Part B)

| Component / module | Destination | Change |
|---|---|---|
| `hasPermission()` + `useHasPermission()` | `packages/ui/src/role-gate/permissions.ts` (util) + new `useHasPermission.ts` | new — server-set matcher + hook |
| `PilotUser.permissions` / context exposure | `packages/ui/src/auth/types.ts`, `AuthProvider.tsx` | extend |
| `useRequiresPermission` / `RoleGate` | `packages/ui/src/role-gate/` | re-point to server set (map = mock fallback) |
| `AppSidebar` nav gating | `apps/web/src/components/AppSidebar.tsx` | permission-keyed items |
| `SettingsSidebar` `roleRequired` evaluation + Team `users.view` | `apps/web/src/features/settings/components/SettingsSidebar.tsx` | fix |
| `SettingsIndexPage` card gates audit + Team `users.view` | `apps/web/src/features/settings/components/SettingsIndexPage.tsx` | fix |
| `useLoginFlow` role-await | `apps/web/src/features/login/hooks/useLoginFlow.ts` | fix (delete `?? "owner"`) |
| `usePostLoginRedirect` accountant fallback + unknown-role posture | `apps/web/src/hooks/usePostLoginRedirect.ts` | fix |
| `useCreateInvite` envelope parsing | `apps/web/src/features/settings/hooks/useCreateInvite.ts` | `getApiProblem` + `invite_id` passthrough |
| `InviteMemberDialog` generic-branch string guard | `apps/web/src/features/settings/components/InviteMemberDialog.tsx` | harden |
| `PendingInvitesSection` accepted filter + email truncation | `apps/web/src/features/settings/components/PendingInvitesSection.tsx` | fix |

No new top-level components; zero orphan components (§1.5.4 reconciliation — all edits compose existing `packages/ui` primitives).

---

## Verification (Tom, post-deploy)

1. Test plan re-run: **Tests 5, 6, 10** green (409 explainers inline, tech banner + 5 s sign-out, office nav correct incl. Team read-only + Schedule/Jobs working, Reports renders).
2. office1 login: Jobs/Comms/Catalog absent; Schedule loads; Reports renders; Settings → Team read-only (no Invite button).
3. tech1 login: info banner → auto sign-out.
4. Invite dup/existing-user: inline explainers, no error boundary; Resend offer works end-to-end.
5. Accepted invite leaves Pending Invites; long email truncates with tooltip.
6. Prod converge run (C.1) + `postgres-prod` verify office_staff `permissions ? 'jobs.view'`.
