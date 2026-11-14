# Implementation Prompt: TEAM-INVITE-1 (Part B) — Invite Dialog + Pending Invites + `/invite/[token]` Landing + FE RBAC Reconciliation

**Mode**: Pilot React Engineer
**Batch**: TEAM-INVITE-1 — Part B (Frontend, runs **after Part A closes**)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.8 (card) + §7 founder-gate row
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-team-invite-1-design.md` — **read in full; §H/§I are the Tom-approved surface spec** (designer gate waived by Tom 2026-09-03, design §G.12)
**Estimated session**: 4–5 hours
**Platform**: Web (`apps/web`) + Shared UI (`packages/ui` — RBAC registry) · mobile untouched (type-check only — `PilotRole` is shared)
**Backend companion**: **TEAM-INVITE-1 Part A (Python) must close first** — its OpenAPI regen is your contract source. Your first Pre-Work step is `pnpm sync-api-types` against the regenerated spec. Do not start against an unmerged Part A.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-team-invite-1-design.md`** — every section (A–I); §H/§I are your surface spec, §D the API contract, §G the locked decisions

Critical rules for this batch:

- **Rule 1.1/1.2 (verify endpoints)**: The 5 Part A endpoints are new — grep them in `backend/openapi_schema_map.md` **after Part A merges** (table below). If missing → STOP and ask Tom. Do NOT invent URL shapes.
- **Rule 2 (`apiClient`)**: All **authenticated** `/api/v1/...` calls use `apiClient` from `@pilot/shared-api`. **Explicit exception — the public invite landing**: `GET /api/v1/invites/{token}` is an unauthenticated surface and uses bare `fetch()`, exactly like `PublicQuotePage.tsx` (documented house exception: "intentionally uses `fetch()` not `apiClient` — unauthenticated surface"). Do not "fix" that pattern, and do not extend it to any authenticated call.
- **Rule 7 (check the barrel)**: `packages/ui/src/index.ts` before creating anything — `RoleGate`, `useRequiresPermission`, `LoadingState`/`ErrorState`/`EmptyState`, `useOptimisticMutation`, `NotificationBanner` all exist. There is **no** shared generic Dialog — the existing `TeamSettingsPage` hand-rolls its modal; follow that local pattern (feature-local, `role="dialog"` + `aria-modal`).
- **Rule 10**: Any test failure during your work — even apparently pre-existing — gets fixed or Tom-confirmed before done.
- **Rule 11 (React Compiler)**: No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf. Components pure.
- **Rule 12 (TanStack Query v5)**: Object-form, colocated query keys, `isPending`, invalidate in `onSettled` (or the shared `useOptimisticMutation` pattern for the invite mutations).
- **Rule 13 (Zod v4 + RHF)**: `z.email()` top-level helper for the invite email field; unified `error` param; API types from `@pilot/shared-types` only.
- **Rule 14 (server vs client)**: Route files are thin server components. All data fetching in `"use client"` feature components.
- **Rule 15 (WCAG 2.2 AA)**: ≥24×24px targets (44×44 primary actions), visible `<label>` per field, `focus-visible` rings, modal focus-trap + return-focus, non-color-only status (chips carry text labels), reduced-motion fallbacks. axe-core zero violations on the new surfaces.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — final:

| Decision | Outcome | Rationale |
|---|---|---|
| Designer gate | **Waived by Tom** (§G.12) — §H/§I is the surface spec | Pattern reuse (settings dialog + badge/table; single-purpose public landing) |
| Invite roles | All 4 (owner, technician, office_staff, accountant) | Co-owner invites are real; triggers ADR-0010 reconciliation |
| FE role vocabulary | **Rename to BE vocabulary** (`tech`→`technician`, `operator`→`accountant`) with census-first gate | ADR-0010 invite-exposed subset; AuthProvider mapping becomes identity |
| `accountant` FE permission set | **Replaced** with the BE read-only set — NOT a string swap of the `operator` manager set | ADR-0010 consequence — the two sets are nearly opposite |
| Invite permission gating | New `users.manage` PermissionKey, **owner-only** (mirrors BE `require_permission("users.manage")`) | §G.10 — no new BE permission invented |
| Public landing fetch | Bare `fetch()` (public-quote precedent) | Unauthenticated surface — no Amplify session exists |
| Existing-user / duplicate invite | 409-driven UI states (`invite_user_exists`, `invite_pending_exists` → offer Resend) | §D1 contract |
| Public landing failure | ONE neutral "link no longer valid" state | §G.9 — backend uniform 404 is deliberate (no enumeration) |
| Mobile | Out of scope — `pnpm --filter mobile build` (type check) must simply stay green through the `PilotRole` rename | Card scope: web only |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
pnpm --filter mobile test 2>&1 | tail -8
```

Record exact counts (last known: **ui 660 / web 2224 / mobile 701**, all green at PLP-FIX-5 close). Fix or Tom-confirm any pre-existing failure before starting.

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This is the handoff signal from Part A (Rule 9.3). Confirms `TeamInviteCreateRequest`, `TeamInviteResponse`, `TeamInviteListItem`, `TeamInvitePublicResponse` (names per the Part A schemas — verify) are in `packages/shared-types/src/api-schema.d.ts`. Consume via `components["schemas"]["..."]` — never hand-written interfaces.

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "users/invites" backend/openapi_schema_map.md
grep -A 5 "invites/{token}" backend/openapi_schema_map.md
```

| Hook / call | Endpoint | Verified |
|---|---|---|
| `useTeamInvites` | `GET /api/v1/users/invites` | ☐ confirm post-Part A |
| `useCreateInvite` | `POST /api/v1/users/invites` | ☐ |
| `useResendInvite` | `POST /api/v1/users/invites/{id}/resend` | ☐ |
| `useRevokeInvite` | `POST /api/v1/users/invites/{id}/revoke` | ☐ |
| Landing fetch (bare `fetch`) | `GET /api/v1/invites/{token}` (public) | ☐ |
| (existing) members list | `GET /api/v1/users` | ✅ exists today |

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/settings/components/TeamSettingsPage.tsx   ← the page you extend; the P0 "coming soon" InviteDialog you replace (design §I.1); useRequiresPermission("settings.manage") call you re-gate
frontend/apps/web/src/features/settings/hooks/useTeamUsers.ts             ← hook pattern to mirror (apiClient, normalize*, colocated QUERY_KEY, invalidate onSuccess)
frontend/apps/web/src/app/(authed)/settings/team/page.tsx                 ← thin route (leave it thin)
frontend/packages/ui/src/auth/types.ts                                    ← PilotRole union (line ~17) — rename target
frontend/packages/ui/src/role-gate/permissions.ts                         ← PermissionKey union + ROLE_PERMISSION_MAP — add users.manage; replace accountant set
frontend/packages/ui/src/auth/AuthProvider.tsx                            ← role_code → PilotRole mapping (lines ~77, ~118) — becomes identity after rename
frontend/packages/ui/src/help-anchor/types.ts                             ← user_role union (line ~36) — rename target
frontend/packages/ui/src/role-gate/RoleGate.tsx + useRequiresPermission.ts ← how the map is consumed
frontend/packages/ui/src/hooks/useOptimisticMutation.ts                   ← §16.8 pattern for the invite mutations
frontend/apps/web/src/features/public-quote/PublicQuotePage.tsx           ← THE public-surface pattern (bare fetch + local state + invalid-link handling) for /invite/[token]
frontend/apps/web/src/mocks/handlers/index.ts                             ← MSW barrel — registration step is mandatory
frontend/apps/web/src/mocks/handlers/ (one domain file, e.g. settings or users) ← handler file conventions
frontend/apps/web/src/features/signup/                                    ← the SignUp flow the landing hands off to (check whether an email query-param prefill exists)
frontend/apps/web/src/__tests__/batch_ui_fix_2b/tech_assignment.integration.test.tsx ← integration-test conventions (batch folder, AuthContext.Provider)
```

Also run:

```bash
# STEP-1 census (see below) — capture BEFORE editing:
grep -rn '"tech"\|"operator"' frontend/packages/ui/src frontend/apps/web/src frontend/apps/mobile --include="*.ts" --include="*.tsx" -l
grep -rn "role=\"tech\"\|role=\"operator\"\|role={\[" frontend/apps/web/src frontend/packages/ui/src --include="*.tsx" -l
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
grep -n "Idempotency-Key" -r frontend/apps/web/src --include="*.tsx" --include="*.ts" | head -5   # confirm the header pattern (cf. ManualPaymentPanel)
```

---

## Context: What This Batch Does

| # | Change | Where |
|---|---|---|
| 1 | **FE RBAC reconciliation (ADR-0010 subset)**: `PilotRole` `"tech"`→`"technician"`, `"operator"`→`"accountant"`; accountant set **replaced** with BE read-only; new `users.manage` key (owner-only); AuthProvider mapping becomes identity; help-anchor union updated | `packages/ui` (+ call-site census) |
| 2 | **InviteMemberDialog** — replaces the P0 "coming soon" placeholder: email + role select (all 4 roles, plain-language descriptions), Zod `z.email()`, send via `POST /users/invites` with `Idempotency-Key`, 409 states | `/settings/team` |
| 3 | **PendingInvitesSection** — email / role badge / sent / expiry / status chip / Resend / Revoke (confirm), optimistic mutations | `/settings/team` below members |
| 4 | **`/invite/[token]` public landing** — valid state (tenant name, email, role, expiry + SignUp CTA) + one neutral invalid state | new public route |
| 5 | MSW handlers + tests (unit, integration, permissions) | mocks + `__tests__/batch_team_invite_1/` |

---

## STEP 1 — FE RBAC Reconciliation (`packages/ui`) — census first

**1a. Census gate (~30 min, report in your Completion Summary)**: run the census greps above. If the `"tech"`/`"operator"` literal blast radius across `apps/web` + `apps/mobile` + `packages/ui` exceeds what you can atomically fix in **~2 hours**, STOP the rename and fall back to **boundary-mapping** (keep the old union; map BE codes → FE codes inside `AuthProvider` where `role: data.role_code` is assigned) — record the call + the census counts in the Completion Summary. The full rename is the expected path (ADR-0010 direction).

**1b. The rename (expected path)**:
- `auth/types.ts`: `PilotRole = "owner" | "technician" | "office_staff" | "accountant"`.
- `help-anchor/types.ts`: same union update.
- `role-gate/permissions.ts`:
  - `ROLE_PERMISSION_MAP` keys renamed `tech`→`technician`, `operator`→`accountant`.
  - **`accountant` set REPLACED** with the BE read-only shape (design §I.5): view-only keys (`customers.view`, `quotes.view`, `invoices.view`, `jobs.view`, `reports.view`, `catalog.view`) — do NOT carry over the old `operator` manager keys. Cross-check the final set against the BE `tenant_user_role` accountant row (design §A table).
  - **Add `"users.manage"` to the `PermissionKey` union AND the `owner` set ONLY** (§8.3: additive for keys — never remove/rename existing permission keys; the ROLE rename is the ADR-0010-sanctioned exception).
  - `technician` keeps the old `tech` set verbatim.
- `AuthProvider.tsx`: after the rename, `role: data.role_code` is identity — delete any mapping shim you find; the type now matches the backend.
- **Call-site sweep**: every `role="tech"` / `role="operator"` / `wrapperFor("tech")` / `makeContext(...)` literal in app code and tests updated (RoleGate usages, `useRequiresPermission` tests, RoleGate tests — the census list is your checklist).
- `useRequiresPermission("settings.manage")` in `TeamSettingsPage` → **`"users.manage"`** (aligns with BE; do this in STEP 4 as part of the page edit).

**Intermediate verification (risky-step gate)**: `pnpm --filter @pilot/ui test 2>&1 | tail -6` — all green (update RoleGate/useRequiresPermission tests to the new literals), then `pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build` — zero type errors across all three before moving on.

## STEP 2 — MSW Handlers

Create `frontend/apps/web/src/mocks/handlers/teamInviteHandlers.ts`:

- `GET /api/v1/users/invites` → 200 with a **varied fixture** (≥4 rows): one `pending` technician (future expiry), one `pending` office_staff expiring soon, one `accepted` (accepted_at set), one `expired` (past expiry) — mirrors the dev seed's pending invite + gives the status-chip matrix data. Field names from `openapi.json` (`TeamInviteListItem`).
- `POST /api/v1/users/invites` → 201 echo with server `id`/`expires_at`/`created_at`; include a `server.use`-ready 409 helper shape for `invite_pending_exists` / `invite_user_exists` tests (RFC 7807 bodies).
- `POST /api/v1/users/invites/:inviteId/resend` → 200 with new `expires_at`.
- `POST /api/v1/users/invites/:inviteId/revoke` → 200 `{ id, is_active: false }`.
- `GET /api/v1/invites/:token` (public) → 200 `{ tenant_name: "Pilot Dev Tenant", email: "newguy@pilot.local", role_code: "technician", expires_at: <future> }` for a known token (e.g. `dev-invite-token-0001`); 404 RFC 7807 `invite_invalid` for anything else.

**Register in `mocks/handlers/index.ts`** (`...teamInviteHandlers` in the barrel array) — unregistered handlers never load. Check for path collisions first (none should exist).

## STEP 3 — Invite Hooks (`features/settings/hooks/`)

Mirror `useTeamUsers.ts` conventions (apiClient, colocated keys, normalize functions, invalidate in `onSettled`). Types from `@pilot/shared-types`.

- `useTeamInvites` — `TEAM_INVITES_QUERY_KEY = ["team-invites"]`; `GET /api/v1/users/invites`; staleTime 30s; returns items + the computed `status` field as delivered by the backend (do NOT recompute client-side).
- `useCreateInvite` — mutation POST; **`Idempotency-Key` header** (`crypto.randomUUID()` per attempt — verify the exact header-passing pattern against an existing caller, e.g. `ManualPaymentPanel`); surfaces the RFC 7807 409 bodies to the dialog (`getApiProblem` from `@pilot/shared-api` if available — verify export; else parse `error.response.data`).
- `useResendInvite` / `useRevokeInvite` — mutations with `Idempotency-Key`; on `onSettled` invalidate `TEAM_INVITES_QUERY_KEY` **and** `["team-users"]` (acceptance-side consistency). Use the shared `useOptimisticMutation` pattern for revoke/resend row states (§16.8 — `PendingBadge` on the row while in flight).

## STEP 4 — InviteMemberDialog + Team Page Wiring

Replace the placeholder `InviteDialog` in `TeamSettingsPage.tsx` (the literal "coming soon" — **its removal is a P0 acceptance criterion**):

- New feature component `InviteMemberDialog` (same folder; hand-rolled modal like the existing pattern, but production-grade a11y: `role="dialog"`, `aria-modal="true"`, labelled-by/described-by, focus-trap, return-focus to the "Invite team member" button on close, ESC + backdrop-close).
- Fields: **Email** (`z.email()` via RHF + `zodResolver`; visible `<label>`; `aria-invalid` + `aria-describedby` error wiring) + **Role** select — options from `ROLE_OPTIONS` (already BE vocabulary) each with a one-line plain-language description (Owner: full access incl. billing & team; Field Technician: jobs, time, expenses, voice; Office Staff: customers, quotes, scheduling; Accountant: read-only books & reports).
- States: idle → sending (button disabled + spinner, ≥44px target) → success (confirmation + dialog closes + pending list refetches) → **409 `invite_pending_exists`** (inline notice + primary action switches to "Resend invite" — fires `useResendInvite` against the id from the error detail) → **409 `invite_user_exists`** (inline explainer: this person already has a Pilot account — contact Pilot support for multi-business access).
- Page wiring: re-gate the page's manage affordances from `"settings.manage"` to **`"users.manage"`** (`useRequiresPermission`), keeping hide-not-disable `<RoleGate>` semantics; the "Invite team member" button opens the new dialog.

## STEP 5 — PendingInvitesSection

New `PendingInvitesSection` component rendered below the members table on `/settings/team`:

- Table rows: email, role badge (reuse the page's `RoleBadge` color map — extract it beside the dialog rather than duplicating), sent date, expiry (days-left, `text-alert-600` when <2d), status chip (`pending`/`expired`/`accepted`/`revoked` — **text-labeled chips, never color-only**), row actions **Resend** + **Revoke** (Revoke opens a small confirm step — destructive; Resend is one-click).
- Data states: skeleton rows while `isPending` (skeleton-over-spinner), `<ErrorState>` with retry on error, hidden entirely when the list is empty (no empty-table chrome), populated table otherwise. Accepted invites naturally age out of "pending" — the chip shows `accepted` (design: members list is the source for active users; invites list shows all statuses for audit).
- Mutations optimistic via `useOptimisticMutation` + `PendingBadge`; 409-and-refresh on stale state (e.g. resend an already-accepted invite → invalidate + neutral notice).

## STEP 6 — `/invite/[token]` Public Landing

New route `frontend/apps/web/src/app/invite/[token]/page.tsx` (thin server shell — static metadata only) + `"use client"` feature component `features/users/components/InviteLandingPage.tsx`:

- **Fetch pattern**: bare `fetch()` with local `useState`/`useEffect` state — mirror `PublicQuotePage.tsx` exactly (this is the sanctioned unauthenticated-surface exception; MSW intercepts it in tests the same way).
- **Valid state**: brand header (reuse the public-quote page's minimal brand treatment — check `TenantBrandedHeader`/`PoweredByPilotFooter` for what composes), "You've been invited to join **{tenant_name}**", invited email, role display name, expiry date, and a primary **Create your account** CTA (≥44px) linking into the signup flow — **verify** whether `features/signup` supports an email query-param prefill; if yes use `/signup?email={email}`, if not link `/signup` and display "sign up with **{email}**" prominently beside the CTA (Redundant Entry, WCAG 3.3.7).
- **Invalid state** (any 404 — expired/accepted/revoked/unknown are deliberately indistinguishable): one neutral panel — "This invite link is no longer valid." + "Ask the business owner to send you a fresh invite." No technical detail, no token echo.
- Loading skeleton while fetching; network-failure (non-404) retry state. No auth chrome, no app sidebar.

## STEP 7 — Tests

**Unit** (co-located `__tests__`):

- `useTeamInvites` / mutations — shape, error states, key construction, `Idempotency-Key` header presence (MSW request assertion), `retry: false` wrapper per inclusions §9.
- `InviteMemberDialog` — renders; email validation error (invalid format blocks submit); role select lists all 4 roles with descriptions; 409 pending → Resend switch fires resend for the detail id; 409 user-exists explainer; RBAC: non-owner never sees the invite button (use the `AuthContext.Provider` pattern with the **new** role literals).
- `PendingInvitesSection` — 4 data states; chip text labels present (not color-only); Revoke confirm flow; Resend mutation fires correct method/URL.
- `InviteLandingPage` — valid state renders tenant/email/role; 404 → neutral invalid state; non-404 → retry state. Mock `next/navigation` per inclusions.
- **Permissions** — `packages/ui/src/role-gate/__tests__/permissions.team-invite-1.test.ts`: `users.manage` in owner set; NOT in technician/office_staff/accountant sets; accountant set contains the read-only keys and NONE of the old operator manager keys; `ROLE_PERMISSION_MAP.technician` deep-equals the old tech set.

**Integration** (`apps/web/src/__tests__/batch_team_invite_1/`):

- `team-settings-invite.integration.test.tsx` — `/settings/team` renders (no 404); owner sees invite button + pending section with MSW fixture rows (assert by fixture email, never counts); full invite flow (open dialog → valid submit → POST fired with payload + Idempotency-Key → success → list invalidated); technician sees neither button nor section. **axe-core scan on the page** — zero violations (follow the existing axe pattern in the repo — grep for an existing usage first).
- `invite-landing.integration.test.tsx` — valid token renders the join panel + CTA href; unknown token renders the neutral state; axe scan zero violations.

---

## Final Verification

> ❌ **BANNED**: `npx vitest run` in any form. Only `pnpm --filter web test` / `pnpm --filter [pkg] test`.

### Phase 1 — Targeted (after each STEP)

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -6
pnpm --filter web test 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_team_invite_1/ 2>&1 | tail -10
```

### Phase 2 — Full (once, at the end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

Any failure in either phase is fixed (or Tom-confirmed) before done. The `PilotRole` rename touches shared code — **mobile type check (`mobile build`) and mobile tests must stay green** even though mobile is otherwise untouched.

---

## Definition of Done — TEAM-INVITE-1 Part B

- [ ] Pre-modification regression baselines captured (ui / web / mobile) — zero pre-existing failures or Tom-confirmed
- [ ] Part A merged confirmed; `pnpm sync-api-types` run — invite types present in `api-schema.d.ts`
- [ ] All 5 endpoints verified in `openapi_schema_map.md` (table above checked off)
- [ ] All mandatory source files read (incl. `mocks/handlers/index.ts`)
- [ ] **STEP 1**: census recorded (counts in Completion Summary); rename executed OR fallback boundary-mapping recorded with rationale; `permissions.ts` — `users.manage` added (owner-only), accountant set replaced read-only, technician set verbatim; `AuthProvider` identity mapping; help-anchor union updated; all call-site literals swept; intermediate ui/web/mobile type+test gate green
- [ ] **STEP 2**: `teamInviteHandlers.ts` created with varied fixture + registered in the barrel (no duplicate paths)
- [ ] **STEP 3**: 4 hooks live — TanStack v5 object-form, colocated keys, `Idempotency-Key` on mutations, invalidation covers both `team-invites` + `team-users`
- [ ] **STEP 4**: placeholder "coming soon" `InviteDialog` **deleted** (grep confirms zero "coming soon" in the file); `InviteMemberDialog` ships with all 5 states incl. both 409 paths; page re-gated to `users.manage`
- [ ] **STEP 5**: `PendingInvitesSection` — 4 data states, text-labeled chips, Resend/Revoke + confirm, optimistic + `PendingBadge`
- [ ] **STEP 6**: `/invite/[token]` thin route + `InviteLandingPage` — bare-fetch public pattern, valid + neutral-invalid + retry states, signup handoff verified
- [ ] **STEP 7**: unit + integration + permissions tests green; axe-core zero violations on both surfaces
- [ ] No hand-written memoization; components pure (React Compiler)
- [ ] Zod v4 (`z.email()`) + RHF; API types from `@pilot/shared-types` only
- [ ] Route files thin (no `"use client"` in `page.tsx`); authenticated fetching client-side only; public landing uses the documented bare-`fetch` exception and nothing else does
- [ ] WCAG 2.2 AA spot-checks: ≥24px targets, focus-visible rings, modal trap + return focus, visible labels, non-color-only status, reduced-motion fallbacks
- [ ] Zero TypeScript errors (ui + web check-types, mobile build); zero ESLint errors; zero `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===` — exact command above)
- [ ] Final test counts (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)

---

## Completion Summary

After all DoD items complete, fill in the appendix below (ADR-0017). No source-spec task headers close with this batch (the §7 gate row flips only after Tom's end-to-end smoke — noted in your handoff line).

## Handoff

- Batch deploys FE-only after Part A is live on prod (Part A deploys first per the launch-plan card).
- Tell Tom: the §7 gate row "TEAM-INVITE-1 closed — founders can invite up to ~5 employees" flips after his end-to-end smoke (owner invites a real email → invite email lands → SignUp → verify → attach → login with the invited role).

---

## Appendix — Completion Summary

### TEAM-INVITE-1 Part B — Invite UI + Landing + FE RBAC Reconciliation: Completion Summary

**Completed**: 2026-09-03
**Mode**: Pilot React Engineer
**Baseline**: ui 660 | web 2224 | mobile 701
**Final**: ui 685 (+25) | web 2236 (+12) | mobile 701 (+0)

#### What Was Accomplished

- **STEP 1 census**: 37 PilotRole literal occurrences found across `packages/ui`, `apps/web`, `apps/mobile` (excluding 4 false positives in `integration-conflict-resolver/chosenSide` and `communications/initiator` which are different concepts). Blast radius was well within the ~2h cap — **full rename executed** (no fallback to boundary-mapping).
- **Rename**: `PilotRole` `"tech"`→`"technician"`, `"operator"`→`"accountant"` in `auth/types.ts`, `help-anchor/types.ts`, and all call sites (RoleGate props, test wrappers, PILOT_ROLES arrays, LoginForm switch cases, usePostLoginRedirect, AppSidebar, mobile _layout.tsx, mobile LoginForm).
- **Accountant set REPLACED** with BE read-only shape: `customers.view`, `quotes.view`, `invoices.view`, `jobs.view`, `reports.view`, `catalog.view` — NOT a string swap of the old operator manager set.
- **`users.manage`** added to `PermissionKey` union and `owner` set ONLY.
- **AuthProvider** mapping was already identity (`role: data.role_code`) — no shim to delete.
- **5 tests updated** to reflect accountant read-only set (beta-b4, beta-b6, permissions-b3, permissions.test, SettingsIndexPage, payment_method, sidebar-rbac, comms_ui_b1).
- **Dispatch board `layoutMode`/`chipDisplayMode`** `"tech"` values correctly preserved (NOT PilotRole — display mode strings).
- **`coming soon` placeholder deleted** — grep confirms zero occurrences in TeamSettingsPage.tsx.
- **Page re-gated** from `"settings.manage"` to `"users.manage"`.

#### Files Changed / Created

| File | Action |
|---|---|
| `frontend/packages/ui/src/auth/types.ts` | Updated — PilotRole union renamed |
| `frontend/packages/ui/src/help-anchor/types.ts` | Updated — user_role union renamed |
| `frontend/packages/ui/src/role-gate/permissions.ts` | Updated — ROLE_PERMISSION_MAP keys renamed, accountant set replaced, users.manage added |
| `frontend/packages/ui/src/role-gate/__tests__/permissions.beta-b4.test.ts` | Updated — tech→technician, operator→accountant, accountant assertions flipped to read-only |
| `frontend/packages/ui/src/role-gate/__tests__/permissions.beta-b6.test.ts` | Updated — same rename + accountant assertions |
| `frontend/packages/ui/src/role-gate/__tests__/permissions-b3.test.ts` | Updated — same rename |
| `frontend/packages/ui/src/role-gate/__tests__/permissions.team-invite-1.test.ts` | Created — 23 tests for users.manage + accountant read-only + technician verbatim |
| `frontend/packages/ui/src/role-gate/permissions.test.ts` | Updated — tech→technician |
| `frontend/apps/web/src/mocks/handlers/teamInviteHandlers.ts` | Created — 5 MSW handlers with varied fixture (4 invite rows) |
| `frontend/apps/web/src/mocks/handlers/index.ts` | Updated — barrel registration |
| `frontend/apps/web/src/features/settings/hooks/useTeamInvites.ts` | Created — GET /users/invites, staleTime 30s |
| `frontend/apps/web/src/features/settings/hooks/useCreateInvite.ts` | Created — POST with Idempotency-Key, RFC 7807 409 parsing |
| `frontend/apps/web/src/features/settings/hooks/useResendInvite.ts` | Created — POST resend with Idempotency-Key |
| `frontend/apps/web/src/features/settings/hooks/useRevokeInvite.ts` | Created — POST revoke with Idempotency-Key |
| `frontend/apps/web/src/features/settings/components/InviteMemberDialog.tsx` | Created — Zod v4 + RHF, 5 states (idle/sending/success/409-pending/409-user-exists), a11y modal |
| `frontend/apps/web/src/features/settings/components/PendingInvitesSection.tsx` | Created — 4 data states, text-labeled chips, Resend/Revoke+confirm |
| `frontend/apps/web/src/features/settings/components/TeamSettingsPage.tsx` | Updated — deleted "coming soon", wired InviteMemberDialog + PendingInvitesSection, re-gated to users.manage |
| `frontend/apps/web/src/app/invite/[token]/page.tsx` | Created — thin server shell, static metadata |
| `frontend/apps/web/src/features/users/components/InviteLandingPage.tsx` | Created — bare fetch public landing, valid/invalid/retry states |
| `frontend/apps/web/src/__tests__/batch_team_invite_1/team-settings-invite.integration.test.tsx` | Created — 9 integration tests |
| `frontend/apps/web/src/__tests__/batch_team_invite_1/invite-landing.integration.test.tsx` | Created — 3 integration tests |
| `frontend/apps/web/src/__tests__/meta/error_surface_baseline.json` | Updated — pruned stale useTenantUsers.ts entry |
| ~30 call-site files across web+mobile | Updated — role literal sweep (sed) |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `packages/ui/src/role-gate/__tests__/permissions.team-invite-1.test.ts` | Unit | 23 | ✅ |
| `apps/web/src/__tests__/batch_team_invite_1/team-settings-invite.integration.test.tsx` | Integration | 9 | ✅ |
| `apps/web/src/__tests__/batch_team_invite_1/invite-landing.integration.test.tsx` | Integration | 3 | ✅ |
| `packages/ui/src/role-gate/__tests__/permissions.beta-b4.test.ts` | Unit (updated) | 12 | ✅ |
| `packages/ui/src/role-gate/__tests__/permissions.beta-b6.test.ts` | Unit (updated) | 8 | ✅ |
