# DISPATCH-B1.25 — Multi-Tech Commitment Visibility (Tech-Mode Views)

**Batch**: DISPATCH-B1.25
**Type**: Mixed (Backend + Frontend web) — **Python Engineer runs first**
**Owner(s)**: Pilot Python Engineer (Part A) → Pilot React Engineer (Part B)
**Plan**: `pilot-launch-plan.md §2.3`
**Prerequisite**: **DISPATCH-B1 complete** (this builds on B1's `DispatchBoardJobEntry` enrichment + `DispatchGridDayView`)
**Sequence**: Lands **after DISPATCH-B1, before DISPATCH-B1.5** — so the week-tech view (B1.5) consumes the commitments field natively with zero rework.
**Estimate**: Part A ~1.5–2h · Part B ~2–3h
**Status**: Design complete — awaiting implementation.

---

## Problem Statement

The dispatch board's **tech-mode** views (day-tech shipped in B1; week-tech coming in B1.5) are **availability views** — their purpose is to show a dispatcher every commitment each technician has, so they can schedule without double-booking. But `_dispatch_board_impl` groups each job **only under its primary tech** (the query filters `JobTechAssignment.role == "primary"`). A tech assigned as **helper/secondary** never sees that job as a commitment in their column.

This under-reports each tech's real workload and invites double-booking — a defect for an availability view, not a "new feature." Live data already has 2 active `helper` assignments (MCP-verified 2026-07-26), so the gap is real today.

**This is NOT a duplication bug.** The fix must be careful: the canonical `jobs[]` list is flattened by `useDispatchBoard` (`techs.flatMap(g => g.jobs)`) and consumed by **lane mode, week-lane, and month view**. Naively returning a job under both its primary and its helper would double-count it in all three of those surfaces. The design keeps `jobs[]` primary-only and adds a **separate, additive** commitments field consumed only by tech-mode views.

---

## A. Input Read Summary

| Input | Section(s) read | Why it mattered |
|---|---|---|
| `scheduling.py` | `_dispatch_board_impl` assignment query + grouping loop | The `role == "primary"` filter is the root cause; `_build_entry` (B1) is the injection point |
| `schemas.py` | `DispatchBoardJobEntry` (post-B1), `DispatchBoardTechGroup` | Where the additive field + role attribute go |
| `useDispatchBoard.ts` | `flatMap(g => g.jobs)` normalization | Proves why `jobs[]` MUST stay primary-only (lane/month/week-lane consume the flatten) |
| `dispatch-b1-ui-design-spec.md` §Surface 1 | day-tech row structure | Where commitment chips render in the tech row |
| Live DB (MCP) | `job_tech_assignment` role distribution | Confirmed roles in use: `primary` (11), `helper` (2), both `is_active=true` |

---

## B. Migration Plan

**No migration required.** All data exists: `job_tech_assignment` already carries `role`, `is_active`, `user_id`, `version`, `id`. This is a **query + Pydantic** change only.

**MCP verification (Python Engineer must re-run before coding)**:
```sql
-- 1. Confirm role/assignment columns used to build the commitments map
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='job_tech_assignment'
  AND column_name IN ('id','job_id','user_id','role','is_active','version') ORDER BY column_name;

-- 2. Confirm the set of role values in use (spec the badge labels from real data)
SELECT DISTINCT role FROM public.job_tech_assignment WHERE is_active = true ORDER BY role;
-- Known as of 2026-07-26: 'primary', 'helper'. Design must not hardcode a closed enum — render whatever role string comes back.
```

---

## C. Execution Order

| # | Step | Owner |
|---|---|---|
| 1 | MCP verify assignment columns + role values | Python |
| 2 | Add `assignment_role: str \| None` to `DispatchBoardJobEntry` | Python |
| 3 | Add `additional_job_commitments: list[DispatchBoardJobEntry]` to `DispatchBoardTechGroup` | Python |
| 4 | In `_dispatch_board_impl`: load ALL active assignments (drop the primary-only filter for the commitments map); keep primary-only for `jobs[]`; populate commitments per tech | Python |
| 5 | Ensure techs with ONLY commitments (no primary jobs) still appear as a tech group | Python |
| 6 | Backend tests (commitments populated; jobs[] not duplicated; commitment-only tech appears) | Python |
| 7 | `python export_openapi_json.py` → commit → handoff | Python |
| 8 | `pnpm sync-api-types` | React |
| 9 | Render read-only role-badged commitment chips in `DispatchGridDayView` (day-tech) | React |
| 10 | FE tests (commitment chip renders with role badge; not draggable; lane mode ignores field) | React |
| 11 | Two-phase verification | React |

---

## D. API Contract Changes (Part A)

### D.1 — `DispatchBoardJobEntry` (add one field)

```python
class DispatchBoardJobEntry(BaseModel):
    ...
    # ── DISPATCH-B1.25 addition ────────────────────────────────────────────
    assignment_role: str | None = None   # role of THIS placement's assignment
                                          # ('primary' in jobs[]; 'helper'/etc in commitments).
                                          # None for unassigned-bucket entries.
```

> The same `Job` can appear as a `DispatchBoardJobEntry` in a primary tech's `jobs[]` (`assignment_role='primary'`) AND in a helper tech's `additional_job_commitments[]` (`assignment_role='helper'`). The field tells the FE which badge to show and whether the placement is draggable.

### D.2 — `DispatchBoardTechGroup` (add one field)

```python
class DispatchBoardTechGroup(BaseModel):
    ...
    jobs: list[DispatchBoardJobEntry]                          # PRIMARY only — unchanged
    additional_job_commitments: list[DispatchBoardJobEntry] = []  # non-primary assignments for this tech
    eta_minutes_to_first_job: int | None = None
```

Additive + defaulted → backward compatible. `DispatchBoardResponse.unassigned[]` is **unchanged** (unassigned = no active primary; a job with only helper assignments and no primary still belongs in `unassigned` for `jobs[]` purposes, but also surfaces as a commitment under its helper — see D.3 edge case).

### D.3 — `_dispatch_board_impl` changes

Read the current implementation first (post-B1). Changes:

1. **Load ALL active assignments**, not just primary:
```python
all_assignments = db.exec(
    select(JobTechAssignment)
    .where(JobTechAssignment.tenant_id == user_context.tenant_id)
    .where(JobTechAssignment.job_id.in_(job_ids))
    .where(JobTechAssignment.is_active == True)
).all()
```
2. **Keep the primary map** (`job_to_assignment`, `job_to_tech`) derived by filtering `all_assignments` for `role == "primary"` — `jobs[]` grouping + `primary_assignment_id`/`assignment_version` stay exactly as B1 built them.
3. **Build a non-primary map**: `tech_id → list[(job, role, assignment_id, version)]` from `all_assignments` where `role != "primary"`.
4. **`_build_entry` gains a `role` param** so the same job can be emitted with the right `assignment_role` + assignment id/version in each context:
```python
def _build_entry(job, *, role, assignment_id=None, assignment_version=None):
    entry = DispatchBoardJobEntry.model_validate(job)   # version, job_number auto-map
    entry.assignment_role = role
    if role == "primary":
        entry.primary_assignment_id = assignment_id
        entry.assignment_version = assignment_version
    entry.customer_name = customer_name_by_id.get(job.customer_id)
    entry.site_address = site_address_by_id.get(job.site_id)
    return entry
```
5. **Populate `additional_job_commitments`** per tech group from the non-primary map. A tech that has non-primary commitments but **no** primary jobs must **still appear as a tech group** (with empty `jobs[]`) — otherwise their commitment is invisible. Union the primary-tech id set with the non-primary-tech id set when building `techs`.
6. **ETA note**: `eta_minutes_to_first_job` is computed from `jobs[]` (primary) only — leave as-is. A commitment-only tech has no primary first-job → ETA null. Acceptable for MVP.

> **Anti-N+1**: `all_assignments` is one query; customer/site enrichment maps from B1 are reused. Do not add per-job queries.

---

## E. Pattern Reuse Decisions

| Pattern | Applies | How |
|---|---|---|
| Additive-field, backward-compatible schema | ✅ | New fields default-valued; `jobs[]`/`unassigned[]` semantics unchanged |
| Single source of truth for `jobs[]` flatten | ✅ | Canonical `jobs[]` stays primary-only → lane/week-lane/month untouched |
| §16 optimistic move (409-and-refresh) | ✅ (unchanged) | Only primary placements are draggable → move pipeline unchanged; commitments are display-only |

**Move semantics (LOCKED)**: Only the **primary** job block is draggable. Rescheduling the primary moves the whole crew (the primary leads the job; all assigned techs inherit the new time). Commitment chips are **display-only** — no drag, no `/move`. Crew reassignment remains via the existing `TechAssignmentSection` in `JobPropertiesPanel` (UI-FIX-2B). Left-click on a commitment chip still opens `JobPropertiesPanel` (read/inspect); right-click still offers the context menu.

---

## F. Shared Module Interfaces (Part B)

```ts
// api-schema.d.ts (post sync) — DispatchBoardTechGroup gains:
additional_job_commitments: DispatchBoardJobEntry[];
// DispatchBoardJobEntry gains:
assignment_role: string | null;

// useDispatchBoard normalization (MODIFY):
// - Keep jobs[] built from techs.flatMap(g => g.jobs) as today (primary only).
// - Expose commitments per tech WITHOUT flattening them into jobs[].
//   Add to the normalized shape: techs[].commitments: DispatchBoardJob[]
//   (normalize each with assignment_role carried through).

// DispatchGridDayView (MODIFY):
// - For each tech row, render primary jobs (draggable, existing) AND
//   commitment chips (read-only, role-badged) at their scheduled positions.
```

---

## G. Open Questions Resolved

1. **Duplicate vs additive** → Additive `additional_job_commitments`; `jobs[]` stays primary-only (protects lane/week-lane/month flatten). Not a duplication.
2. **Draggability** → Only primary blocks draggable (moves whole crew). Commitment chips read-only.
3. **Role display** → Show the role as a badge ("Helper", etc.). Render whatever `assignment_role` string the API returns — do NOT hardcode a closed enum (roles beyond primary/helper may exist).
4. **Commitment-only techs** → Must appear as a tech group (empty `jobs[]`, populated commitments) so their commitment is visible.
5. **Sequencing** → Land before B1.5 so week-tech renders commitments natively.
6. **Reassignment** → Out of scope; use existing `TechAssignmentSection`. No new crew-management drag in this batch.

---

## H. Surface Mockup Reference (Frontend)

**Platform**: web only (`apps/web`). Tech-mode views only (day-tech now; week-tech inherits in B1.5).

Commitment chip visual (distinct from the tech's own primary job blocks):
- Same positioning math as a primary `JobBlock` (absolute `left`/`width` from scheduled times).
- Visually **secondary/muted**: dashed or lighter border, `cursor-default` (not `cursor-grab`), no drag listeners.
- A small **role badge** ("Helper") in the chip corner — `text-caption` pill, `bg-neutral-100 text-neutral-600`.
- Left-click → `JobPropertiesPanel`; right-click → `JobContextMenu` (same handlers as primary blocks, minus drag).

> UI Designer: a short spec addendum to `dispatch-b1-ui-design-spec.md` for the commitment-chip treatment (muted style + role badge) is recommended but not blocking — the React Engineer can derive it from the existing `JobBlock` with the muted/read-only variant described here.

---

## I. Component Manifest (Frontend)

| File | Action | Description |
|---|---|---|
| `useDispatchBoard.ts` | Modify | Carry `additional_job_commitments` per tech into the normalized shape (do NOT flatten into `jobs[]`); carry `assignment_role` on normalized jobs |
| `JobBlock.tsx` | Modify | Add a `readOnly`/`variant="commitment"` mode: muted style, no drag listeners, role badge slot |
| `DispatchGridDayView.tsx` | Modify | Render commitment chips (read-only) alongside primary blocks in each tech row |
| `types-stub.ts` / synced types | Modify | `assignment_role` + `additional_job_commitments` from synced schema |

> `DispatchBoardLanes` (lane mode) is **untouched** — it consumes `jobs[]` which stays primary-only. Month view untouched.

---

## Dependency Note for DISPATCH-B1.5

When B1.5 builds the week-tech view (transposed `DispatchWeekView`), it must render `additional_job_commitments` in each tech row/column using the same read-only `JobBlock` commitment variant from this batch. No backend work in B1.5 for this — the field already exists.

---

*Design authored by Pilot Architect, 2026-07-26. Builds on DISPATCH-B1. Part A (Python) runs first; hand off via `export_openapi_json.py` + `pnpm sync-api-types`.*
