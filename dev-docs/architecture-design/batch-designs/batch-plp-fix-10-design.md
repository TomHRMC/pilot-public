# PLP-FIX-10 Design — Dispatch-Board Gate + Technicians-Box 403 Grace + Checklist Unhide + Settings Tables Layout + Session-History Wiring

**Version**: 1.0
**Date**: 2026-09-06
**Author**: Pilot Architect
**Batch**: PLP-FIX-10 (launch plan Ord 31, card §3.31)
**Bugs closed**: INV-BUG-13, INV-BUG-10a, INV-BUG-14, INV-BUG-15, INV-BUG-16, INV-BUG-17 (+ INV-BUG-12 closure per INV-D-6 Option A)
**Rulings**: INV-D-6 = **Option A** (Tom 2026-09-06 — wildcards stay first-class grant options) · INV-BUG-15 table-layout direction (Tom 2026-09-06)
**Shape**: Mixed per architect-rules §1.3 — **Part A (Python, ~1.5 h, runs first)** → **Part B (React, ~2.5 h)**

---

## A. Input Read Summary

| Input | What it contributed |
|---|---|
| `tom-ui-issues-tracking.md` INV-BUG-13…17 + INV-D-6 | The six bug definitions + Tom's rulings |
| `plp-fix-9-prod-verification-plan.md` run records (09-06 ×2) | The prod evidence behind every bug (7/10 board + sub-check completion) |
| `pilot-launch-plan.md` §3.31 (v7.39) | Batch card scope |
| `batch-plp-fix-9-design.md` §G.6/G.7 | The two FIX-9 design assumptions this batch corrects (assignments gate; role-list sweep scope) |
| **MCP `postgres-local` (2026-09-06)** | Full `tenant_user_role` dump (accountant `*.view`; office_staff holds `schedule.view_all` + `schedule.manage` + `users.view`); `user_session_history` = **0 rows**; session-table inventory (`user_session_history`, `user_session_metadata`) |
| `DispatchBoardPage.tsx` (line 571) | `RoleGate role={["owner","accountant"]}` wraps the entire board — **INV-BUG-13 root** |
| `scheduling.py` | `GET /jobs/{job_id}/assignments` gated **`schedule.view_all`** (FIX-9 design assumed `jobs.view` — design miss) — **INV-BUG-10a root** |
| `TechAssignmentSection.tsx` (37-99) | `useJobAssignments` `isError` → `ErrorState "Failed to load technicians"`; the FIX-9 `usersForbidden` detector only covers `useTenantUsers` |
| `onboarding_checklist.py` | `PUT .../checklist/hidden` only calls `hide_checklist(db, …)` **when `payload.hidden` is true** — the `false` branch returns `{"checklist_hidden": false}` **without persisting anything** — **INV-BUG-14 root (backend, not FE)** |
| `OnboardingChecklistWidget.tsx` (60-80) + `useChecklistMutations.ts` | FE Show path is correct (`hideChecklist.mutate(false)`, optimistic) — "shows temporarily then re-collapses, survives logout/login" = the server flag is never cleared |
| `InvoiceDetailPage.tsx` (288-294) | "Generate & Copy Link" button carries **no gate** (FIX-9 swept Send/Record Payment only) — **INV-BUG-16 root**; it triggers the same `POST /{id}/send` public-link operation |
| `account_security.py` + grep `_upsert_session_history` | The A72 upsert has **zero production callers** (tests only) — **INV-BUG-17 root**; the endpoint 404s "No session history found" when no row exists |
| `session_revoke_service.py` + `models/security.py` + `models/auth.py` | A70 `user_session_metadata` rows link to `auth_refresh_token.session_id` — app refresh tokens are never issued in the Cognito-native web flow → A70 also unpopulated (§G.6 deferral) |
| `batch-plp-fix-8-python-engr-prompt.md` + `lambda/post_authentication/handler.py` | The Post-Auth Lambda resolves user + tenant(s) on every sign-in and enqueues per-tenant Celery tasks under a never-raise invariant — the **INV-BUG-17 wiring point** |
| `TeamSettingsPage.tsx` + `PendingInvitesSection.tsx` | Members table `w-full`; pending-invites table `table-fixed` — the **INV-BUG-15** redesign targets |
| `permissions.py` (BE) + `permissions.ts` (FE) | Both matchers expand `*.suffix` — accountant's `*.view` ⇒ `communications.view` (INV-D-6 context; ruled Option A) |
| `backend/python-engr-std-prompt-inclusions.md` + `frontend/react-engr-std-prompt-inclusions.md` | Prompt section requirements (Rules 1.1/1.2) |

---

## B. Migration Plan

**No Alembic migration. No seed changes.** INV-D-6 ruled Option A — grant arrays untouched. Part A is code-only: one route/service fix + one new Celery task + a Lambda enqueue.

**Runtime data note (not a seed change)**: `record_user_login` writes `user_session_history` rows at login time — production runtime data written by application code (the correct path per ADR-0016).

**Seed Data Rollout (Rule 11.5)**: **N/A** — zero changes to lookup/reference/scenario seed data. Recorded per the standing rule.

**Prod rollout (Tom, at deploy)** — order matters (the Lambda enqueues a task the worker must already know):

1. **API + worker images** (worker carries `record_user_login`; API carries the checklist-unhide fix).
2. **Post-Authentication Lambda redeploy** via `build-post-authentication-lambda.sh` + Terraform (carries the enqueue).
3. **Web image** (Part B).

Transition window: pre-redeploy Lambda events simply don't record logins — no errors, no backfill needed (history accrues from deploy forward; `first_login_at` starts at the first recorded login — accepted, §G.6).

---

## C. Execution Order

| # | Step | Owner | Depends on |
|---|---|---|---|
| 1 | Checklist unhide persistence: service-level set-hidden path + honor `hidden=false` in `PUT .../checklist/hidden` (+ `/test` twin parity) + regression test | Python | — |
| 2 | New `tasks/login_recording.py` — `record_user_login` Celery task calling `_upsert_session_history`; register in `tasks/__init__.py` (TEST-UPLIFT-1A registration guard) + task tests | Python | — |
| 3 | Lambda enqueue (additive, alongside `_enqueue_new_device_alerts`, per resolved tenant); extend `test_post_authentication_handler.py` | Python | 2 |
| 4 | Ruff (changed files) + unit suite + vendor-deselected full suite; OpenAPI timestamp-only check | Python | 1-3 |
| 5 | **Handoff** — no OpenAPI delta; notify Part B (`pnpm sync-api-types` still runs as the first Part B pre-work step per standing rule) | Python | 4 |
| 6 | INV-BUG-13: `DispatchBoardPage` role-list → `permission="schedule.view_all"` | React | 5 |
| 7 | INV-BUG-10a: Technicians section gate `schedule.view_all`; picker on `schedule.manage`; assignments-query 403 defense | React | 5 |
| 8 | INV-BUG-16: Generate-&-Copy-Link → `permission="invoices.update"` | React | 5 |
| 9 | INV-BUG-15: Team + Pending Invites tables — content-sized columns + horizontal-scroll wrapper | React | 5 |
| 10 | MSW fixture true-up + integration tests (`batch_plp_fix_10/`); full Phase 2 canonical gate | React | 6-9 |

---

## D. New API Endpoints

**None.** The `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden` route keeps its existing contract (`{hidden: bool}`) — it now honors `false`. No OpenAPI schema delta (timestamp-only diff expected).

---

## E. Pattern Reuse Decisions

| Pattern | Application |
|---|---|
| **Server-authoritative RBAC** (PLP-FIX-7; ADR-0010) | All FE gates consume `useHasPermission` against `GET /users/me/permissions`; `permission=` — never legacy `role={` lists |
| **403 ≠ 5xx** (PLP-FIX-9 §G.7) | Embedded panels degrade hidden/read-only on 403; `ErrorState` reserved for genuine 5xx |
| **Hide-not-disable** (§16 house idiom) | Board / Technicians section / Generate-link button are absent from the DOM, not disabled |
| **Never-raise Lambda invariant** (PLATFORM-SMS-B2 / FIX-8) | Login recording must never fail a sign-in; the enqueue rides the existing try/except posture |
| **Optimistic UI with an honest server roundtrip** (§16.8) | INV-BUG-14 is a *lying* mutation response (success returned, nothing persisted) — the fix restores contract honesty; the FE optimistic update stays as-is |
| **Celery registration guard** (TEST-UPLIFT-1A) | New task module explicitly registered in `tasks/__init__.py` |

---

## F. Shared Module Interfaces

```python
# backend/tasks/login_recording.py  (NEW)
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def record_user_login(self, tenant_id: str, user_id: str) -> None:
    """A72 wiring: upsert user_session_history (first_login_at / last_login_at /
    total_session_count) for the authenticated user. Enqueued by the
    Post-Authentication Lambda on every successful sign-in. Retry posture matches
    house defaults; gives up quietly — login telemetry must never page anyone,
    and the Lambda caller is never-raise."""

# backend/lambda/post_authentication/handler.py  (MODIFIED — additive)
# Per resolved tenant, alongside _enqueue_new_device_alerts:
#   record_user_login.apply_async(kwargs={"tenant_id": <tid>, "user_id": str(user.id)})
# inside the existing never-raise try/except posture. No new imports beyond the task.
```

Frontend: **no new shared modules** — edits only (§I).

---

## G. Open Questions Resolved

**G.1 — INV-BUG-13 gate key = `schedule.view_all`.** Matches the BE read gates on the board's data (`GET /scheduling/jobs/{job_id}/assignments` = `schedule.view_all`, verified at `scheduling.py`; the engineer greps the board-query endpoints to confirm the same vocabulary at impl). office_staff renders the board. **Accountant loses the board** — the role list had been papering over the grant truth (accountant holds no schedule grants); flagged for RBAC-CONFIG-1 (§2 row 2-18): if accountant should see the board, that's a grant ruling, not a gate exception. Technician unchanged (blocked from web entirely).

**G.2 — INV-BUG-10a fix shape.** `TechAssignmentSection`: gate the whole section on `useHasPermission("schedule.view_all")` — hidden for accountant (who cannot read assignments, period). Picker/manage affordances additionally gated `schedule.manage` (office_staff: full manage; any future view-only-schedule role gets read-only). Keep the FIX-9 `usersForbidden` read-only path **and** add the same `isAxiosError → 403` detector to the **assignments** query as defense-in-depth (403 → render null, never `ErrorState`); `ErrorState` only for non-403 failures.

**G.3 — INV-BUG-14 is a backend one-way write.** `onboarding_checklist.py`: the route calls `hide_checklist(db, tenant_id)` only when `payload.hidden` is true — the `false` branch returns `{"checklist_hidden": false}` **without persisting anything**. The FE is correct (optimistic expand → next refetch re-collapses; survives logout because the server flag never clears). Fix: add the unhide path in the checklist service (mirror `hide_checklist` → `set_checklist_hidden(db, tenant_id, hidden: bool)` or an `unhide_checklist` sibling) and call it in the else branch; `/hidden/test` twin gets parity. Regression test: PUT `false` after `true` → subsequent GET returns `checklist_hidden=false` — the exact prod repro.

**G.4 — INV-BUG-15 layout model (Tom-ruled 2026-09-06).** Both settings tables — Team members (`TeamSettingsPage.tsx`, `w-full`) and Pending Invites (`PendingInvitesSection.tsx`, `table-fixed`): drop `table-fixed`; wrap each table in an `overflow-x-auto` container; let columns size to content (`table-auto` + `whitespace-nowrap` on cells that must not wrap — email, name, actions); the email cell retains `truncate` + tooltip as the in-scroll-region fallback (a `max-w` applies only inside the scroll area). **Acceptance**: at desktop widths no truncation (full `tom@example-domain.org`-class values render); at narrow widths the table scrolls horizontally instead of crushing columns; Resend + Revoke fully visible at every width (closes the ④ tail).

**G.5 — INV-BUG-16 gate = `invoices.update`.** Generate-&-Copy-Link triggers the same operation as Send (`POST /{id}/send` generates the public link — FIX-9 §G.6 cites the BE gates at `invoices.py/1681`; the engineer grep-verifies the `/send` route's `require_permission` at impl). Wrap the button in `permission="invoices.update"` — hidden for accountant; **also hidden for office_staff** (holds `invoices.create` but not `invoices.update` — the same pre-flagged side effect as Send/Record Payment in FIX-9 §G.6).

**G.6 — INV-BUG-17 wiring = Post-Auth Lambda → Celery task; A70 deferred.** The Lambda already resolves `user.id` + tenant(s) per sign-in (the FIX-8 path). The new `record_user_login` task upserts A72 (`first_login_at` / `last_login_at` / `total_session_count`). History accrues from deploy forward — **no backfill** (reconstructing historical logins from Cognito is out of scope; `first_login_at` = first recorded login, accepted). **`user_session_metadata` (A70) is deliberately out of scope**: its rows link to `auth_refresh_token.session_id`, which the Cognito-native web flow never issues — proper population needs a device-identity design (Cognito device key ↔ app-session mapping), a discovery item of its own. Consequence: the Security page's *active-sessions* list stays empty after this batch; the A72 history block (first/last/total) works for every user. If Tom wants the device list next, that's its own small batch (noted in the launch-plan tail).

**G.7 — INV-D-6 = Option A (Tom, 2026-09-06).** No grant-array changes. Wildcards (`*.view`, `*.edit`, …) are first-class grant options and must be offered by the future RBAC config UI — with the recorded tradeoff that a wildcard can never carry exceptions and covers future matching surfaces (carried in RBAC-CONFIG-UI-1's notes, launch plan §6c). INV-BUG-12 closes: technician fixed by FIX-9; accountant's comms visibility is accepted behavior.

**G.8 — Designer gate: N/A.** Existing surfaces + locked idioms (`RoleGate` / `useHasPermission`, `<ErrorState>`, overflow-scroll tables); the table direction was ruled by Tom directly. Recorded per architect-rules §1.5.

---

## H. Surface Mockup Reference

**Designer spec: waived (G.8).** Every change is an existing surface consuming locked idioms:

| Surface | File | Change | Idiom consumed |
|---|---|---|---|
| `/schedule` (dispatch board) | `DispatchBoardPage.tsx` (571) | `role={["owner","accountant"]}` → `permission="schedule.view_all"` | server-authoritative RBAC |
| Job detail → Technicians box | `TechAssignmentSection.tsx` | section on `schedule.view_all`; picker on `schedule.manage`; assignments-403 → null | 403 ≠ 5xx; hide-not-disable |
| Dashboard checklist pill | *(FE correct — BE fix in Part A)* | unhide persists | honest optimistic roundtrip |
| Settings → Team (both tables) | `TeamSettingsPage.tsx`, `PendingInvitesSection.tsx` | content-sized columns + `overflow-x-auto`; truncate+tooltip as in-scroll fallback | Tom-ruled layout |
| Invoice detail | `InvoiceDetailPage.tsx` (288) | Generate-&-Copy-Link → `permission="invoices.update"` | hide-not-disable |
| Settings → Security | *(FE correct — Part A wiring)* | A72 history block populates | — |

Platform scope: **web only** (`apps/web`). Mobile untouched.

---

## I. Component Manifest

**Zero new components** (component-existence check against `packages/ui/src/index.ts`: `RoleGate`, `useHasPermission`, `ErrorState` all exist — every fix composes them).

| File | Action |
|---|---|
| `backend/services/` checklist service (mirror of `hide_checklist`) | Modified — set-hidden/unhide path |
| `backend/api/routes/onboarding_checklist.py` | Modified — honor `hidden=false` (+ `/test` twin parity) |
| `backend/tasks/login_recording.py` | **Created** — `record_user_login` Celery task |
| `backend/tasks/__init__.py` | Modified — register the new module (registration guard) |
| `backend/lambda/post_authentication/handler.py` | Modified — enqueue login recording per resolved tenant (never-raise) |
| `backend/tests/domains/onboarding/` | New regression test — PUT false after true → GET `checklist_hidden=false` |
| `backend/tests/domains/identity_access/test_post_authentication_handler.py` | Modified — extend enqueue assertions (login recording alongside device alerts) |
| `backend/tests/domains/` (new task test) | **Created** — task upsert called with resolved ids; retry posture |
| `DispatchBoardPage.tsx` | Modified — gate conversion |
| `TechAssignmentSection.tsx` | Modified — section gate + assignments-403 defense |
| `InvoiceDetailPage.tsx` | Modified — button gate |
| `TeamSettingsPage.tsx` + `PendingInvitesSection.tsx` | Modified — table layout |
| `apps/web/src/__tests__/batch_plp_fix_10/` | **Created** — integration tests: board gate (office_staff renders / accountant hidden), tech-section gate, Generate-link gate, table layout (min-widths + scroll + Revoke visible), checklist Show persists across refetch (MSW) |

No orphan components; no new top-level UX patterns.

---

## Verification (Tom, post-deploy)

1. **INV-BUG-13**: office1 → `/schedule` renders the full board (lanes + jobs). accountant → board hidden (grant truth).
2. **INV-BUG-10a**: accountant → job detail → no "Failed to load technicians" (section hidden); office1 → box renders with picker.
3. **INV-BUG-14**: hide the checklist → click Show → expands **and persists** across reload + logout/login.
4. **INV-BUG-15**: Team + Pending Invites tables show complete values at desktop width; narrow window → horizontal scroll; Revoke fully visible (④ final close).
5. **INV-BUG-16**: accountant invoice detail → no Generate-&-Copy-Link button.
6. **INV-BUG-17**: sign out/in twice as office1 (repeat as owner) → Settings → Security shows session history (first/last login + count ≥ 2).
