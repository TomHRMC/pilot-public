# Implementation Prompt: DISPATCH-B1.25 (Part A) — Multi-Tech Commitments in Dispatch Board Response

**Mode**: Pilot Python Engineer
**Batch**: DISPATCH-B1.25 (Part A — Backend, runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-dispatch-b1.25-design.md` — **Part A**, §B, §D
**Estimated session**: 1.5–2 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: DISPATCH-B1.25 (Part B — Pilot React Engineer). **This backend half MUST complete and hand off first.**
**Depends on**: DISPATCH-B1 (Part A) — the `DispatchBoardJobEntry` enrichment + `_build_entry` helper this batch extends must already be merged.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document
- **`batch-dispatch-b1.25-design.md`** — §B (no migration), §D (exact schema + query change), §Problem Statement (why jobs[] must stay primary-only)

Critical rules for this batch:

- **Rule 1**: Never guess column/table names. Use `postgres-local` MCP to verify before use. If MCP errors → STOP and ask Tom.
- **Rule 3**: After the response-model change → run `python export_openapi_json.py`. This is the handoff signal to the React Engineer.
- **Rule 5**: Never module-level `TestClient`. Use the `client` fixture.
- **Rule 6**: `db.get()` banned on tenant-scoped models — use tenant-scoped `select()` with `WHERE tenant_id`.
- **Rule 7**: `postgres-local` MCP is read-only verification. Never INSERT/UPDATE/DELETE.
- **Rule 11**: Any failing test — even apparently pre-existing — must be fixed before done. If root cause unclear → STOP and ask Tom.

> **No migration.** All data exists (`job_tech_assignment.role/is_active/user_id/version`). This is a **Pydantic + query** change. If you start writing an Alembic migration, STOP — you misread the scope.

> **CRITICAL — do NOT duplicate into `jobs[]`.** The canonical `jobs[]` list is flattened by the frontend (`techs.flatMap(g => g.jobs)`) and consumed by lane/week-lane/month views. It MUST stay **primary-only**. Non-primary assignments go into a NEW separate field `additional_job_commitments`. Duplicating a job into `jobs[]` would double-render it in three other surfaces.

---

## Background / Context

The dispatch board's tech-mode views are **availability views** — they must show every commitment a tech has. Today `_dispatch_board_impl` groups jobs only under the **primary** tech (`role == "primary"` filter), so a helper/secondary tech never sees the job in their column. Live data has active `helper` assignments today. This batch surfaces non-primary commitments via an **additive** field so every tech's real workload is visible — without breaking the primary-only `jobs[]` contract that other views depend on.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```
Record: **`X passed, Y failed`**. Fix any pre-existing failure (or confirm with Tom) before starting.

---

## Pre-Work: Run MCP Verification Queries

> **MCP is read-only.** If a query errors or surprises → STOP and ask Tom.
> **Safety net**: verify every column independently before referencing it — the live DB is authoritative.

```sql
-- 1. Confirm the assignment columns used to build the commitments map
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='job_tech_assignment'
  AND column_name IN ('id','job_id','user_id','role','is_active','version')
ORDER BY column_name;

-- 2. Confirm the role values actually in use (do NOT hardcode a closed enum in code)
SELECT DISTINCT role FROM public.job_tech_assignment WHERE is_active = true ORDER BY role;
-- Known 2026-07-26: 'primary', 'helper'. Treat role as an open string.

-- 3. Confirm DispatchBoardJobEntry already has the B1 fields (this batch depends on B1)
--    (verify via code read of api/schemas/schemas.py — version/job_number/customer_name present)
```

---

## Pre-Work: Read These Source Files

```
backend/api/schemas/schemas.py             ← DispatchBoardJobEntry (post-B1) + DispatchBoardTechGroup (~787–835)
backend/api/routes/scheduling.py           ← _dispatch_board_impl (~955–1150): assignment query, _build_entry, grouping loop, tech-group build
backend/app/models/scheduling.py           ← JobTechAssignment: confirm role/is_active/user_id/version/id
backend/tests/conftest.py                  ← fixtures (test_tenant, test_job, client) + how to create assignments
backend/tests/batch_1e/test_task_1b3_dispatch_board.py  ← the /dispatch-board/test request pattern
```

Grep:
```bash
grep -n "role == \"primary\"\|job_to_assignment\|job_to_tech\|_build_entry\|tech_to_jobs" backend/api/routes/scheduling.py
```

---

## Task 1 — Schema additions

**File**: `backend/api/schemas/schemas.py`

Add per design §D.1 / §D.2 (read the file; match style):
```python
# In DispatchBoardJobEntry (after the B1 additions):
assignment_role: str | None = None   # role of THIS placement ('primary' in jobs[]; 'helper'/etc in commitments; None if unassigned)

# In DispatchBoardTechGroup (after jobs):
additional_job_commitments: list[DispatchBoardJobEntry] = []  # non-primary assignments for this tech
```
Both additive + defaulted → backward compatible.

Intermediate:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — `_dispatch_board_impl` query + grouping

**File**: `backend/api/routes/scheduling.py`

Read the whole function first (post-B1). Make these changes per design §D.3:

**2a — Load ALL active assignments** (not just primary). Where the primary-only `assignments` query exists, either broaden it or add a parallel query:
```python
all_assignments = db.exec(
    select(JobTechAssignment)
    .where(JobTechAssignment.tenant_id == user_context.tenant_id)
    .where(JobTechAssignment.job_id.in_(job_ids))
    .where(JobTechAssignment.is_active == True)
).all()
```
Derive the **primary** map from `all_assignments` (filter `role == "primary"`) so `job_to_tech` / `job_to_assignment` (B1) are unchanged. Build a **non-primary** map:
```python
# tech_user_id -> list of (job_id, role, assignment_id, assignment_version)
from collections import defaultdict
non_primary_by_tech: dict[UUID, list[tuple[UUID, str, UUID, int]]] = defaultdict(list)
for a in all_assignments:
    if a.role != "primary":
        non_primary_by_tech[a.user_id].append((a.job_id, a.role, a.id, a.version))
```

**2b — Extend `_build_entry` with a `role` param** so the same job renders with the correct `assignment_role`:
```python
def _build_entry(job, *, role, assignment_id=None, assignment_version=None):
    entry = DispatchBoardJobEntry.model_validate(job)
    entry.assignment_role = role
    if role == "primary":
        entry.primary_assignment_id = assignment_id
        entry.assignment_version = assignment_version
    entry.customer_name = customer_name_by_id.get(job.customer_id)
    entry.site_address = site_address_by_id.get(job.site_id)
    return entry
```
Update the primary grouping loop + unassigned bucket to pass `role`:
- primary jobs → `_build_entry(job, role="primary", assignment_id=..., assignment_version=...)`
- unassigned bucket → `_build_entry(job, role=None)`

**2c — Populate `additional_job_commitments` per tech group.** Build a `job_by_id` lookup from the already-loaded `jobs`. When constructing each `DispatchBoardTechGroup`, add:
```python
commitments = [
    _build_entry(job_by_id[jid], role=role)   # non-primary: no primary_assignment_id
    for (jid, role, _aid, _ver) in non_primary_by_tech.get(tech_id, [])
    if jid in job_by_id
]
# ... DispatchBoardTechGroup(..., jobs=job_list, additional_job_commitments=commitments)
```

**2d — Commitment-only techs must appear.** The current `techs` loop iterates `tech_to_jobs` (primary only). A tech with ONLY non-primary commitments won't be in that dict → their commitment is invisible. Union the id sets:
```python
all_tech_ids = set(tech_to_jobs.keys()) | set(non_primary_by_tech.keys())
```
Iterate `all_tech_ids`; for a commitment-only tech, `jobs=[]`, `additional_job_commitments=[...]`, ETA `None`. Make sure the user-profile batch-fetch (`user_by_id`) loads all `all_tech_ids`, not just primary ones.

> **ETA**: keep computing from primary `jobs[]` only (design §D.3.6). Commitment-only techs get `eta_minutes_to_first_job = None` — acceptable.

Intermediate:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
python -m pytest tests/domains/scheduling_dispatch/ -q 2>&1 | tail -10
```

---

## Task 3 — Tests

Domain: **`scheduling_dispatch/`**. Extend the B1 dispatch-board test file or create `test_dispatch_b1_25_commitments.py`:
```python
pytestmark = [pytest.mark.domain_scheduling_dispatch, pytest.mark.unit]
```

Use the `/dispatch-board/test` endpoint + `test_tenant`/`test_job` fixtures; scope by inserted IDs. Create jobs + assignments via the assignment `/test` endpoint (see `test_task_1b3_dispatch_board.py` + `test_task_1b2_job_assignment_scheduling.py` for the assign pattern).

Required coverage:
1. **Helper commitment appears** — job with primary=Alice + helper=Bob. Board: the job is in Alice's `jobs[]` with `assignment_role="primary"`, AND in Bob's `additional_job_commitments[]` with `assignment_role="helper"`.
2. **No duplication in jobs[]** — that same job appears exactly ONCE across all `techs[].jobs` (Alice's), never in Bob's `jobs[]`. (Assert by counting occurrences of the inserted job id across flattened `jobs`.)
3. **Commitment-only tech appears** — a tech with only a helper assignment (no primary jobs) shows up as a tech group with empty `jobs[]` and a populated `additional_job_commitments[]`.
4. **Primary fields intact** — the primary entry still carries `primary_assignment_id` + `assignment_version`; the commitment entry has `assignment_role="helper"` and `primary_assignment_id is None`.

Intermediate:
```bash
python -m pytest tests/domains/scheduling_dispatch/ -v 2>&1 | tail -20
```

---

## Regenerate OpenAPI (handoff signal)

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
python3 -c "
import json
spec = json.load(open('openapi.json'))
job = spec['components']['schemas']['DispatchBoardJobEntry']['properties']
grp = spec['components']['schemas']['DispatchBoardTechGroup']['properties']
print('assignment_role in job entry ->', 'assignment_role' in job)
print('additional_job_commitments in tech group ->', 'additional_job_commitments' in grp)
"
```
Both must print `True`.

---

## Final Verification

### Phase 1 — Unit
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```
### Phase 2 — Full
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/scheduling_dispatch/ -v 2>&1 | tail -20
echo "=== DISPATCH-B1.25 PART A FINAL VERIFICATION COMPLETE ==="
```
Any failure in either phase must be fixed before done.

---

## Definition of Done

- [ ] Regression baseline captured; zero pre-existing failures (or confirmed with Tom)
- [ ] MCP queries run — assignment columns + role values confirmed
- [ ] Mandatory source files read
- [ ] `DispatchBoardJobEntry.assignment_role` added
- [ ] `DispatchBoardTechGroup.additional_job_commitments` added (defaulted)
- [ ] `_dispatch_board_impl`: all active assignments loaded; `jobs[]` stays primary-only; non-primary map built; `_build_entry` takes `role`
- [ ] Commitment-only techs appear as tech groups (union of id sets; user profiles fetched for all)
- [ ] No N+1 (single `all_assignments` query; reuse B1 enrichment maps)
- [ ] Tests: helper commitment appears; no duplication in jobs[]; commitment-only tech appears; primary fields intact
- [ ] `python export_openapi_json.py` run — both new keys present (verified via snippet)
- [ ] **Phase 1** unit pass · **Phase 2** full pass
- [ ] Final test count documented
- [ ] Completion Summary added to launch plan Appendix B
- [ ] Handoff note included (below)

---

## Handoff to Part B (React Engineer)

Include this in the Completion Summary:
> "Part A complete. `DispatchBoardTechGroup` now returns `additional_job_commitments: DispatchBoardJobEntry[]` (non-primary assignments per tech); each entry carries `assignment_role`. `jobs[]` remains primary-only — do NOT flatten commitments into the canonical jobs list. React Engineer: run `pnpm sync-api-types` first, then render read-only role-badged commitment chips in tech-mode views only (lane/month unchanged)."

---

## Completion Summary

Add to `pilot-launch-plan.md` Appendix B (Python template). Note that DISPATCH-B1.5 (week-tech) will consume `additional_job_commitments` natively with no further backend work.

---

## After This Task — Next Step

Hand off to the **Pilot React Engineer** with `batch-dispatch-b1.25-react-engr-prompt.md`.
