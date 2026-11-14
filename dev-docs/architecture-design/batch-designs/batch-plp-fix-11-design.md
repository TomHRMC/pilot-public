# PLP-FIX-11 Design — Accountant Schedule-Read Grant + Technicians Header Gate (INV-BUG-18)

**Version**: 1.0 · **Date**: 2026-09-06 · **Author**: Pilot Architect
**Launch plan**: Ord 32, card §3.32 · **Tracker**: `tom-ui-issues-tracking.md` INV-BUG-18
**Batch shape**: Mixed (§1.3) — Part A Python (seed grant, ~1 h) → Part B React (~1.5 h)
**Tom ruling (2026-09-06, FIX-10 verification run)**: "the accountant should be able to view jobs including what techs have been assigned" — reverses the FIX-10 §G.1 grant-truth side effect.

---

## A. Input Read Summary

| Input | What it contributed |
|---|---|
| `tom-ui-issues-tracking.md` INV-BUG-18 | The ruling + observed behavior (bare "Technicians" header for accountant) |
| FIX-10 verification run record | Check 2 result + root cause (parent header outside the gated section) |
| **MCP `postgres-local`** — `tenant_user_role` row dump (2026-09-06) | accountant = `["audit.view","dashboard.manage","reports.view","*.view","catalog.manage","mfa.enroll_self","account.session.view_own","account.session.revoke_own","help_chat.delete_own_history"]` — **no `schedule.view_all`**; office_staff holds `schedule.view_all` + `schedule.manage` explicitly; technician holds `schedule.view_own` only |
| `scheduling.py` | `GET /scheduling/jobs/{id}/assignments` gated `require_permission("schedule.view_all")` — grant-only fix, **no route change** |
| `TechAssignmentSection.tsx` (post-FIX-10) | Section gate `useHasPermission("schedule.view_all")` (line 46→105); picker on `schedule.manage` (lines 181/198); assignments-403→null defense (line 111) — all correct; post-grant accountant renders read-only |
| `permissions.ts` `hasPermission()` (lines 35-52) | Suffix matcher: `*.view` → `key.endsWith(".view")` — does **not** match `schedule.view_all` (verified why the FIX-10 gates held for accountant) |
| `seed_core.py` `TENANT_USER_ROLE_ROWS` (913-1007) + converge (2579-2627) | Grant mechanism: array edit + converge-safe UPDATE (`SET permissions … WHERE code=:code AND permissions <> …` — permissions + updated_at only; PLP-FIX-7 §C.1 pattern, reused by FIX-9) |
| `test_task_1a4_scheduling_role_permissions.py` | **Collision**: `test_accountant_has_no_schedule_permissions` asserts zero `schedule.*` — must be updated to the new ruling |
| `test_tenant_user_role_grants.py` | FIX-9's grant-test home (INV-D-5 comms, INV-BUG-8 self-service) — Part A extends it |
| `userPermissionsHandlers.ts` (67-78) | MSW prod-mirror accountant array — gains the grant |
| `JobDetailPage.tsx` | The bare `<h4>Technicians</h4>` renders outside the gated section — the header-gate rider target |
| PRD §3.2/§3.5 (role definitions) | accountant = read-only books & reports; Tom's ruling extends read scope to schedule |
| `mvp-arch.md` §16 | Server-authoritative RBAC (post-FIX-7) — a grant change propagates to nav/pages at next login with zero FE gate wiring |
| FIX-7/FIX-9 Part A prompt appendices | Precedent for converge-safe grant rollouts + fixture-leads-prod ordering |

## B. Migration Plan

**No Alembic migration.** Grant change ships through the seed system only (FIX-7/FIX-9 mechanism):

1. **Edit**: `seed_core.py` `TENANT_USER_ROLE_ROWS["accountant"].permissions` += `"schedule.view_all"` (with `# PLP-FIX-11:` comment, INV-BUG-18 reference).
2. **Converge mechanism (already built, lines 2587-2607)**: on `--mode seed`, the existing UPDATE converges `permissions` to the seed definition only when different (`permissions <> CAST(:permissions AS jsonb)` — no-op when equal; touches nothing else on the row).
3. **Pre-migration state (MCP-verified 2026-09-06)**: local accountant array lacks `schedule.view_all` (dump in §A). Prod identical by construction (same seed lineage; FIX-9 converge applied there).
4. **MCP verification queries for the prompt**: (a) `tenant_user_role` column list; (b) current accountant `permissions` value pre-edit; (c) post-converge re-read expecting `schedule.view_all` present.
5. **3-part NOT NULL pattern**: N/A — no DDL.
6. **Seed Data Rollout (Rule 11.5)**: **Layer 1** — this change *is* the core seed edit (Group A `seed_core.py`; idempotent converge). **Layer 2** — N/A (no entity columns). **Verification** — `seed_core.py --mode inspect` prints the role rows; `pytest -m unit` after the edit (the 1E collision test is updated in-batch). **README** — `backend/README-seed-data.md` §4 updated (accountant row gains `schedule.view_all`).
7. **Prod rollout**: Tom runs the standard converge (`seed_prod_db.py --mode seed --stripe-mode test`, typed `PILOT-PROD-SEED`) — same gate as FIX-9 Phase 0.1. **No API/worker/Lambda deploy** (seed scripts run from the repo via the tunnel).

## C. Execution Order

| # | Step | Owner |
|---|---|---|
| 1 | Part A: baseline (expect **4848 passed, 1 skipped**) → MCP verifies → `seed_core.py` array edit → extend `test_tenant_user_role_grants.py` → update `test_task_1a4_scheduling_role_permissions.py` → grep sweep for other accountant-schedule assertions → seed inspect + unit + Phase 2 → OpenAPI export (timestamp-only expected) → completion summary | Python |
| 2 | Part B: `pnpm sync-api-types` (formality) → `permissions.ts` static map + `userPermissionsHandlers.ts` fixture += grant → `JobDetailPage` header gate → FIX-10 test true-up + new read-only coverage → Phase 2 → completion summary | React |
| 3 | Tom: prod converge (Part A) → web image (Part B) → design §Verification | Tom |

Handoff: Part A has **zero OpenAPI delta** (no endpoint changes) — Part B's `sync-api-types` stays mandatory-but-formality. No merge-order dependency between the parts; verification needs both.

## D. New API Endpoints

**None.** The fix is grant-only: the existing `schedule.view_all` gates (`scheduling.py` assignments read; dispatch-board read endpoints) begin passing for accountant after the converge.

## E. Pattern Reuse Decisions

- **§16 server-authoritative RBAC (FIX-7)**: grant edit propagates to nav + pages at next login — no FE wiring beyond the static-map/fixture mirrors. The Schedule nav item appears for accountant automatically (accepted consequence, §G-Q2).
- **§16 hide-not-disable**: unchanged — the Technicians picker stays hidden from accountant (`schedule.manage` not granted; `*.view` does not match it).
- **FIX-7 §C.1 converge pattern**: array edit + value-scoped UPDATE; fixtures lead the prod rollout (MSW/static map mirror the post-converge state before Tom converges).
- **FIX-9/FIX-10 403-grace taxonomy**: unchanged — post-grant the assignments query 200s for accountant; the 403→null defense remains for any future role lacking the grant.

## F. Shared Module Interfaces

No new functions, tasks, or schedules. Changes are data/array-level:

| Location | Change |
|---|---|
| `seed_core.py` `TENANT_USER_ROLE_ROWS["accountant"]` | += `"schedule.view_all"` |
| `permissions.ts` `ROLE_PERMISSION_MAP.accountant` | += `"schedule.view_all"` (mock-mode fallback parity) |
| `userPermissionsHandlers.ts` `ROLE_PERMISSIONS.accountant` | += `"schedule.view_all"` (MSW prod mirror) |
| `JobDetailPage.tsx` (~lines 147-152) | wrap the "Technicians" `<div>` (header + section) in the same `useHasPermission("schedule.view_all")` gate — hooks-order safe (the hook already runs inside the child; the parent gate uses its own call) |

## G. Open Questions Resolved

- **Q1 — Grant vs. re-gate the endpoint?** → **Grant** (Tom's ruling). Re-gating `scheduling.py` to `jobs.view` would also expose assignments to **technician** (`jobs.view` holder) on every surface — wider than the ruling and a BE-contract change. The seed grant is the FIX-7/FIX-9 house mechanism, converge-safe, reversible by one array edit.
- **Q2 — Side effect: accountant gains the Schedule nav item + read-only dispatch board?** → **Accepted** — it is the same `schedule.view_all` read key by design (Tom's ruling is about schedule read; the board's write affordances stay `schedule.manage`-gated post-FIX-10 STEP 1, and the lane-count 403-grace from FIX-9 covers the owner-only subscription read). To be re-confirmed in Tom's verification (§Verification 2).
- **Q3 — `schedule.manage` for accountant too?** → **No** (out of scope). The ruling is *view*; write stays owner/office_staff. A future widening is an RBAC-CONFIG-1 (§2 row 2-18) ruling.
- **Q4 — The 1E-era invariant test (`test_accountant_has_no_schedule_permissions`)?** → **Updated in-batch** to the new ruling: assert `schedule.view_all` present and `schedule.manage` / `schedule.view_own` absent. This is a ruling reversal, not a regression.
- **Q5 — Still ship the header gate if the grant makes it near-dead?** → **Yes** — post-grant only technician lacks `schedule.view_all` (and technician is web-blocked), but the bare-header defect is structural (parent renders outside the child's gate); any future role without the grant would reproduce it. Two-line correctness fix riding Part B.
- **Q6 — `schedule.view_own` for accountant?** → **No** — that key is technician-scoped (own-lane reads); the ruling needs the all-lanes read key only.

## H. Surface Mockup Reference

**Designer gate: waived** — zero new surfaces; existing pages + locked idioms (same basis as FIX-7/9/10). Behavior deltas: accountant sees the Schedule nav item, the read-only board, and the populated read-only Technicians box; no visual design changes.

## I. Component Manifest

**Zero new components.** Files touched: `permissions.ts`, `userPermissionsHandlers.ts`, `JobDetailPage.tsx`, plus test-file updates (`batch_plp_fix_10/board-gate`, `batch_plp_fix_10/tech-assignment-grace`, any nav-assertion tests found in the grep sweep).

---

## Verification (Tom, post-converge + web deploy)

1. **INV-BUG-18 core**: accountant → Jobs → open a job with an assigned tech → the **Technicians box renders the assignment(s)** (name/avatar/Lead badge); **no picker, no ✕ buttons** (read-only — `schedule.manage` withheld); no error.
2. **Side effect (accepted §G-Q2)**: accountant → **Schedule nav item appears** → the board renders read-only (lanes + jobs; no drag affordances).
3. **Regression**: office1 → Technicians box still renders **with** picker (add/remove works). Owner → unchanged.
4. **Header gate**: (code-level; no prod-visible role triggers it post-grant — technician is web-blocked) Part B test proves a role lacking `schedule.view_all` renders **no** "Technicians" header at all.
5. **Converge proof**: `PSQL "SELECT permissions ? 'schedule.view_all' AS has_view_all, permissions ? 'schedule.manage' AS has_manage FROM public.tenant_user_role WHERE code='accountant';"` → `t / f`.
