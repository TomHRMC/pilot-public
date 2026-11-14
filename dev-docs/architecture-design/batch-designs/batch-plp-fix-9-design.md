# PLP-FIX-9 Design — Session Cache-Clear + Employee MFA + RBAC Affordance/Grace Sweep + office_staff Comms Grant

**Version**: 1.0
**Date**: 2026-09-05
**Author**: Pilot Architect
**Batch**: PLP-FIX-9 (launch plan Ord 30, card §3.30)
**Scope rulings**: Tom 2026-09-05 (INV-D-1…D-5 — see §G.1)
**Bugs closed**: INV-BUG-6-rem, INV-BUG-7, INV-BUG-8, INV-BUG-9, INV-BUG-10, INV-BUG-11, INV-BUG-12 + INV-D-5 grant (`tom-ui-issues-tracking.md`)
**Shape**: Mixed per architect-rules §1.3 — **Part A (Python, ~1 h, runs first)** → **Part B (React, ~3 h)**

---

## A. Input Read Summary

| Input | What it contributed |
|---|---|
| `tom-ui-issues-tracking.md` INV-BUG-6-rem…12 + INV-D-1…D-5 | The 7 bug definitions + Tom's 5 rulings (2026-09-05) |
| `pilot-launch-plan.md` §3.30 (v7.35) | Batch card scope + sequencing |
| `plp-fix-7-8-prod-verification-plan.md` run record | The 09-05 prod evidence behind every bug |
| `mvp-prd.md` §3.2 (lines 336/344/347/348/349) | Least-privilege role design; `require_permission()` on all routes; **"Self-service multi-method MFA enrollment is encouraged"** — the PRD basis for INV-BUG-8 |
| `mvp-arch.md` §16.8 + ADR-0010 (`pilot-adr-log.md`) | Locked patterns; FE uses **backend permission vocabulary** (drives §G.2 comms reconciliation) |
| **MCP `postgres-local` (2026-09-05)** | `tenant_user_role` columns (`code` natural PK — no surrogate id; `permissions` jsonb; StandardAuditMixin 4 cols); all 4 role rows dumped (office_staff already healed with `jobs.view` by the FIX-7 converge); no role holds any `communications.*`, `mfa.enroll_self`, `account.session.*`, or `help_chat.*` code |
| `backend/api/routes/account_security.py` (300-392 read) | `GET /me/mfa-status` gated `mfa.enroll_self`; session-history gated `account.session.view_own`; `revoke_own` ×3 — all self-scoped |
| `backend/api/routes/settings.py` (1296-1384 read) | `GET/PUT /tenant/mfa-required` gated `mfa.policy.edit` (owner via `*`) — **not** implicated in INV-BUG-8 |
| `backend/api/routes/communications.py` + `communications_threads.py` (grep) | BE vocabulary is **`communications.view` / `communications.send` / `communications.manage`** — the FE `comms.send` key is phantom (matches zero backend gates) |
| `backend/migrations/scripts/seed_core.py` (915-969 + 2562-2610 read) | `TENANT_USER_ROLE_ROWS` arrays; the FIX-7 converge UPDATE (permissions-only, value-scoped, idempotent) is **already in place** — this batch edits arrays only |
| `backend/core/permissions.py` (203-311 read) + `backend/core/auth.py` (152-218 read) | Server RBAC is per-request DB-grant-backed wildcard matching — confirmed the server side is sound (INV-BUG-7 is an FE session-state bug, not an API hole) |
| FE reads (2026-09-05): `AuthProvider.tsx` (signOut 298-304; imports `@pilot/shared-api`), `InvoiceDetailPage.tsx` (260/274 `RoleGate role=[…]`), `JobsPage.tsx` (336 same), `QuoteDetailPage.tsx` (219 LineItemEditor no readOnly gate), `TechAssignmentSection.tsx` (43 `useTenantUsers` → `users.view`; 76-83 raw ErrorState), `RecentCustomerMessagesWidget.tsx` (72-74 raw error), `DispatchBoardPage.tsx` (540 lane-count ErrorState), `PendingInvitesSection.tsx` (139-159 `table-fixed` + Actions `w-36`), `CustomerDetailTabs.tsx` (21-23 static TABS), `InvoiceBuilderPage.tsx` (115 `customLines`, 266 `handleAddCustomLine`) | Every Part B fix location + root cause code-verified |
| `backend/python-engr-std-prompt-inclusions.md` (full) + `frontend/react-engr-std-prompt-inclusions.md` (full) | Prompt section requirements (Rule 1.1/1.2 compliance) |

---

## B. Migration Plan

**No Alembic migration.** This batch changes **seed definitions only** (`tenant_user_role.permissions` arrays). Per ADR-0016, reference/lookup data changes ship via seed scripts + the established converge path, not migrations.

### B.1 Seed changes (Part A — the only DB-data changes)

`TENANT_USER_ROLE_ROWS` in `seed_core.py` — four arrays edited:

| Role | Add | Rationale |
|---|---|---|
| `office_staff` | `communications.view`, `communications.send` | INV-D-5 (Tom 2026-09-05) — office staff handle customer messaging; BE-verified vocabulary (§G.1/G.2) |
| `office_staff` | `mfa.enroll_self`, `account.session.view_own`, `account.session.revoke_own`, `help_chat.delete_own_history` | INV-BUG-8 — self-service Security page works for every role (PRD §3.2 line 349) |
| `technician` | same 4 self-service codes | same — techs self-serve MFA on mobile (MOB-B10 screens exist) |
| `accountant` | same 4 self-service codes | same |
| `owner` | *(no change)* | `*` wildcard already matches all |

**Converge mechanics — zero new code**: the `tenant_user_role` seed block (`seed_core.py`) already carries the FIX-7 converge UPDATE (`SET permissions … WHERE code=:code AND permissions <> CAST(:permissions AS jsonb)` — idempotent, touches only `permissions` + `updated_at`). Editing the arrays is sufficient; local + prod heal at the next converge run.

**MCP pre-change verification (2026-09-05, `postgres-local`)**:
- Columns: `created_at, updated_at, created_by, updated_by, code, name, description, permissions (jsonb), is_default, is_active` — PK is `code` (no surrogate id).
- office_staff row = seed array exactly (13 perms incl. `jobs.view`) — FIX-7 converge confirmed healed locally.
- No role holds `communications.*`, `mfa.enroll_self`, `account.session.*`, or `help_chat.*`.

**Prod rollout (Tom, at deploy)**: the standard prod converge — `seed_prod_db.py --mode seed --stripe-mode test` (typed `PILOT-PROD-SEED`), then verify via `postgres-prod` MCP: `SELECT permissions ? 'communications.send' FROM public.tenant_user_role WHERE code='office_staff';` → `t`; `SELECT permissions ? 'mfa.enroll_self' FROM public.tenant_user_role WHERE code='technician';` → `t`.

### B.2 Seed Data Rollout (Rule 11.5)

- **Layer 1 (core/platform)**: this batch IS a Layer-1 change — `TENANT_USER_ROLE_ROWS` edits in `seed_core.py` (Group A). The script's `seed`/`inspect` modes need no structural change (the block is data-driven from the arrays).
- **Layer 2 (scenario)**: N/A — no entity columns added; role grants are platform reference data, not scenario-seeded entities.
- **README**: `README-seed-data.md` §4 `tenant_user_role` rows updated (office_staff +2 comms codes; all three non-owner roles +4 self-service codes).
- **Verification**: `seed_core.py --mode inspect` + `pytest -m unit` after the change.

---

## C. Execution Order

| # | Step | Owner | Depends on |
|---|---|---|---|
| 1 | Edit the 4 `TENANT_USER_ROLE_ROWS` arrays (§B.1) | Python | — |
| 2 | New test file `test_tenant_user_role_grants.py` (grant matrix + converge idempotency — mirrors FIX-7's `TestOfficeStaffJobsViewSeed`) | Python | 1 |
| 3 | Run local converge (`seed_core.py --mode seed`) twice → first pass heals, second is no-op; MCP re-verify | Python | 1 |
| 4 | README-seed-data §4 update; `pytest -m unit` + full vendor-deselected suite | Python | 1-3 |
| 5 | **Handoff** — no OpenAPI delta (seed-only); notify Part B | Python | 4 |
| 6 | `permissions.ts`: add 6 PermissionKeys + mirror `ROLE_PERMISSION_MAP` to the new grants (additive-only; `comms.send` deprecated-not-removed) | React | 5 |
| 7 | `AuthProvider.signOut` + login success path: `queryClient.clear()` (INV-BUG-7) | React | 6 |
| 8 | Write-affordance sweep: `RoleGate role=[…]` → `permission=` (INV-BUG-9) + quote-detail `readOnly` | React | 6 |
| 9 | 403-grace panels: TechAssignmentSection, RecentCustomerMessagesWidget, lane-count fallback (INV-BUG-10) | React | 6 |
| 10 | Invoice-builder local-line render (INV-BUG-11) + PendingInvites Actions width (INV-BUG-6-rem) + CustomerDetailTabs Comms gate (INV-BUG-12) | React | 6 |
| 11 | MSW fixture true-up (`userPermissionsHandlers` grant arrays) + tests (integration + permissions unit) | React | 6-10 |
| 12 | Full Phase 2 canonical gate | React | 11 |

---

## D. New API Endpoints

**None.** Seed + FE-only batch. (Verified: no endpoint changes — `export_openapi_json.py` expected timestamp-only diff in Part A.)

---

## E. Pattern Reuse Decisions

| Pattern | Application |
|---|---|
| **Server-authoritative RBAC** (PLP-FIX-7; ADR-0010) | All FE gates consume `useHasPermission` against `GET /users/me/permissions`; the static `ROLE_PERMISSION_MAP` stays mock-fallback only and is re-mirrored to the new grants |
| **Hide-not-disable** (house RBAC idiom via `RoleGate`) | Write affordances hidden when the write permission is absent — never rendered-then-403 (INV-BUG-9); Comms tab hidden (INV-BUG-12); messages widget hidden (INV-BUG-10b) |
| **Graceful degradation** (`<EmptyState>`/read-only fallback from `packages/ui`) | Embedded panels degrade to read-only/hidden on 403 — never raw `<ErrorState type="server">` for an expected permission miss (INV-BUG-10) |
| **Optimistic UI with pending badges** (§16.8) | Already on PendingInvitesSection — preserved; only column widths change |
| **Value-scoped seed converge** (FIX-7 pattern; README-seed §7 DELETE safety) | Array edits only; the existing converge UPDATE heals rows; no DELETEs anywhere |

---

## F. Shared Module Interfaces

**No new backend functions.** FE additions (all in existing files — §I):

```typescript
// packages/ui/src/role-gate/permissions.ts — PermissionKey union += (additive only):
| "communications.view" | "communications.send"
| "mfa.enroll_self" | "account.session.view_own" | "account.session.revoke_own"
| "help_chat.delete_own_history"

// packages/ui/src/auth/AuthProvider.tsx
import { queryClient } from "@pilot/shared-api"; // precedent: getImpersonation import (line 34)
// signOut(): await amplifySignOut() → queryClient.clear()  (both mock + live paths)
// useLoginFlow success path (apps/web/src/features/login/hooks/useLoginFlow.ts):
//   after whenSessionReady() resolves a DIFFERENT user than the cached session → queryClient.clear()
```

---

## G. Open Questions Resolved

**G.1 — INV-D-5 exact grant set**: `communications.view` + `communications.send` for office_staff. `communications.manage` (thread lifecycle admin, 2 endpoints) **excluded** — conservative; owner keeps thread admin. Ruled by Tom 2026-09-05 ("yes, widen"); set chosen by Architect against the MCP-verified route gates.

**G.2 — The FE `comms.send` key is phantom vocabulary.** Zero backend routes check `comms.*`; the BE vocabulary is `communications.*` (grep-verified: `communications.send` ×4, `communications.view` ×3, `communications.manage` ×2). Granting office_staff `communications.*` without touching the FE would leave the nav hidden forever (the nav checks the phantom key, which `GET /users/me/permissions` will never contain). **Resolution**: add the real keys to `PermissionKey` + `ROLE_PERMISSION_MAP` (additive-only per react-engr inclusions §8.3 — `comms.send` stays in the union with a deprecation comment), and repoint every `comms.send` consumer (nav, any page gates) to `communications.view` (read surfaces) / `communications.send` (send affordances). ADR-0010 lineage: FE consumes backend vocabulary.

**G.3 — INV-BUG-8 root cause is grants, not endpoints.** `GET /me/mfa-status` + 4 sibling MFA endpoints are gated `mfa.enroll_self`; session endpoints `account.session.view_own`/`revoke_own`; help-history `help_chat.delete_own_history` — all self-scoped, and **no non-owner role holds any of them** (MCP-verified). Alternative considered and **rejected**: relaxing the gates to bare `get_current_user` — that would re-litigate MFA-WIRE-1's RBAC vocabulary design and remove the ability to ever restrict self-service per role. Granting the codes to all three non-owner roles preserves the vocabulary and matches PRD §3.2 ("self-service multi-method enrollment is encouraged"). `help_chat.delete_own_history` folded in — identical defect class (self-scoped gate, zero grants), same one-line array change. `mfa.policy.edit` stays owner-only (tenant policy — correct as-is; INV-D-2 UI is MFA-WIRE-2 scope).

**G.4 — Converge needs no new code.** The FIX-7 `tenant_user_role` converge UPDATE already heals `permissions` on existing rows (value-scoped, idempotent). This batch edits arrays only. Prod heals at Tom's next converge run. No migration (ADR-0016 seed-not-migration posture for reference data).

**G.5 — INV-BUG-7 fix shape.** `queryClient.clear()` (a) in `AuthProvider.signOut()` both mock + live paths, and (b) in `useLoginFlow`'s success path when `whenSessionReady()` resolves a **different user id** than the prior session (covers user-switch without an intervening sign-out). `queryClient` is already exported from `@pilot/shared-api` (react-engr Rule 2 cites it); `AuthProvider` already imports from that package (line 34). Server-side enforcement needs **zero** change — all customer/site/quote/invoice gates verified present (§A); this was never an API hole. Delta-run repro ③ stands as the prod proof.

**G.6 — INV-BUG-9 sweep = role-list → permission-key conversion.** The over-show is the **legacy `RoleGate role={[…]}` pattern** (pre-FIX-7), which hardcodes role names instead of consulting grants: `JobsPage` +Add Job and `InvoiceDetailPage` Send/Record Payment both carry `role={["owner","office_staff","accountant"]}` — accountant explicitly included, although prod accountant holds **no** `jobs.create`/`invoices.update` (`*.view` + `catalog.manage` only) and the APIs 403 on click. Conversions: +Add Job → `permission="jobs.create"` (BE gate `jobs.py`); Send/Record Payment → `permission="invoices.update"` (BE gates `invoices.py/1681`); quote-detail `LineItemEditor` → `readOnly={!canUpdate}` with `canUpdate = useHasPermission("quotes.update")` (the prop already exists; BE line-write gates `quotes.py+`). **Consequence flagged for Tom (grant truth kept)**: office_staff holds `invoices.create` but **not** `invoices.update`, so Send/Record Payment hides for office_staff too after the sweep — and office_staff loses +Add Job (holds `jobs.view` only). If Tom wants office staff sending invoices/creating jobs, that's a future grant ruling, not this batch. The engineer does a full `role={` census and converts any other **write-affordance** gates found (read-surface role gates are out of scope).

**G.7 — INV-BUG-10 grace taxonomy (403 ≠ 5xx).** (a) `TechAssignmentSection`: `useTenantUsers` (`roles.py` — `users.view`) 403s for accountant; assignments themselves load under `jobs.view`. Fix: render assignments read-only when the users call 403s; reserve `ErrorState type="server"` for genuine 5xx on the assignments call. (b) `RecentCustomerMessagesWidget`: wrap in a `communications.view` gate — hidden (not erroring) for roles without comms grants. (c) Dispatch lane-count: `GET /tenant/subscription` is `subscription.view` (owner-only by design — the payload carries billing PII; **BE gate relaxation rejected**). Fix in the hook/consumer: a 403 on the lane-count call degrades to default-lane rendering, never the full-page "Unable to load subscription lane count" error for `schedule.view_own` users.

**G.8 — INV-BUG-11 fix location.** `InvoiceBuilderPage.tsx`: `handleAddCustomLine` (line 266) appends to `customLines` state (line 115), but the added line doesn't render until Save-as-Draft. The engineer reads the custom-lines render block (~lines 590-750) and rewires it so the list reflects `customLines` immediately (local-state render sync). Acceptance: add a line → row visible before any save; Save-as-Draft still persists correctly (regression test covers both).

**G.9 — INV-BUG-6-rem fix shape.** Actions column `w-36` (144px) is narrower than the Resend+Revoke pair (~180px with padding) under `table-fixed`. Fix: Actions → `w-48` (192px) + actions cell `whitespace-nowrap`; verify the revoke-confirm inline state fits within 192px (it replaces the two buttons, so it fits). Email truncation (`max-w-0` + `truncate`) untouched — it works.

**G.10 — Designer gate**: N/A — existing surfaces + locked idioms (`RoleGate`, `<EmptyState>`, `<ErrorState>` from `packages/ui`); same waiver basis as PLP-FIX-7. Tom pre-approved the scope 2026-09-05 (INV-D rulings). Recorded per architect-rules §1.5.

**G.11 — INV-D-1 is parked, not built.** Employee SMS verify+opt-in path = future feature (Tom 2026-09-05). Nothing in this batch touches SMS consent or endpoints.

---

## H. Surface Mockup Reference

**Designer spec: waived (G.10).** Every change is an existing surface consuming locked idioms:

| Surface | File | Change | Idiom consumed |
|---|---|---|---|
| Settings → Team (pending invites) | `PendingInvitesSection.tsx` | Actions `w-36`→`w-48` + nowrap | table-fixed truncation (FIX-7) |
| Security (MFA/sessions) | `MfaSettingsPage` / `account_security` consumers | loads for all roles post-grant | server-authoritative perms |
| Jobs list | `JobsPage.tsx` | `role=[…]` → `permission="jobs.create"` | hide-not-disable |
| Invoice detail | `InvoiceDetailPage.tsx` | same → `permission="invoices.update"` | hide-not-disable |
| Quote detail | `quote-approval/QuoteDetailPage.tsx` | `readOnly={!canUpdate}` | server-authoritative perms |
| Job detail (Technicians box) | `TechAssignmentSection.tsx` | 403 → read-only assignments | graceful degradation |
| Dashboard | `RecentCustomerMessagesWidget.tsx` | gate on `communications.view` | hide-not-disable |
| Dispatch board | lane-count hook/consumer | 403 → default lanes | graceful degradation |
| Invoice builder | `InvoiceBuilderPage.tsx` | custom-line renders on add | local-state sync |
| Customer detail tab bar | `CustomerDetailTabs.tsx` | Comms tab on `communications.view` | hide-not-disable |
| Login/session | `AuthProvider.tsx`, `useLoginFlow.ts` | `queryClient.clear()` | session hygiene |

Platform scope: **web only** (`apps/web` + `packages/ui`). Mobile untouched (technician MFA self-service already exists there via MOB-B10 and benefits from the grant change automatically).

---

## I. Component Manifest

**Zero new components** (component-existence check against `packages/ui/src/index.ts`: `RoleGate`, `useHasPermission`, `LoadingState`/`ErrorState`/`EmptyState` all exist — every fix composes them). All work is edits to the existing files listed in §H plus:

| File | Action |
|---|---|
| `packages/ui/src/role-gate/permissions.ts` | +6 PermissionKeys; `ROLE_PERMISSION_MAP` mirrored (additive-only; `comms.send` deprecated comment) |
| `apps/web/src/mocks/handlers/userPermissionsHandlers.ts` | Fixture arrays updated to the new grants (MSW fidelity, FIX-7 rule) |
| `apps/web/src/__tests__/batch_plp_fix_9/` | New integration tests (cache-clear, affordance gates, comms gate, MFA loads) |
| `packages/ui/src/role-gate/__tests__/permissions.plp-fix-9.test.ts` | New permission unit tests (one per role per new key) |
| `backend/tests/domains/identity_access/test_tenant_user_role_grants.py` | New — grant matrix + converge idempotency |

No orphan components; no new top-level UX patterns.

---

## Verification (Tom, post-deploy)

1. **Delta ③ (INV-BUG-7)**: clean profile → tech1 login → Network tab — all customer/site/quote/invoice calls 403 with graceful states; no data renders. Then sign out → owner login → data renders (cache rebuilt clean).
2. **INV-BUG-8**: as accountant/office1 → Settings → My Account → Security — MFA methods load; session history loads; enrollment start works.
3. **INV-D-5**: after the prod converge — office1 sees the Comms nav item + customer Comms tab; send works.
4. **INV-BUG-9**: as accountant — no +Add Job, no Send/Record Payment, quote detail fully read-only.
5. **INV-BUG-6-rem**: long-email pending row — Revoke fully visible.
6. **INV-BUG-11**: owner invoice builder — added line renders immediately.
