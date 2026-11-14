# Implementation Prompt: DISPATCH-B1 (Part A) — Dispatch Board Response Enrichment

**Mode**: Pilot Python Engineer
**Batch**: DISPATCH-B1 (Part A — Backend, runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 DISPATCH-B1
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-dispatch-b1-design.md` — **Part A**, §B, §C, §D.1
**Estimated session**: 2–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: DISPATCH-B1 (Part B — Pilot React Engineer). **This backend half MUST complete and hand off first.**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test structure, domain markers, fixture rules
- **`batch-dispatch-b1-design.md`** — Part A scope, §B (no migration), §D.1 (exact schema change)

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 3**: After any endpoint/response-model change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`). This is the **handoff signal** to the React Engineer.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never INSERT/UPDATE/DELETE through it.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. If you cannot identify the root cause → STOP and ask Tom.

> **No migration in this batch.** All fields you will surface already exist on the live schema (MCP-verified 2026-07-26). This is a **pure Pydantic response-schema + query-population change**. If you find yourself writing an Alembic migration, STOP — you have misread the scope.

---

## Background / Context

**What this batch does**: Enriches the dispatch-board response so the frontend can drive the **real** optimistic-locking `/scheduling/jobs/{id}/move` contract and render real job labels — retiring a fragile second-fetch hack the frontend currently uses.

**Why**: Contract verification (design doc §A) found that:
1. The frontend move/conflict hooks target non-existent `/schedule/...` endpoints; the real endpoints are `/scheduling/jobs/{id}/move` + `/check-conflicts` and require an **integer `expected_job_version`**.
2. `DispatchBoardJobEntry` omits `version`, `primary_assignment_id`, and `assignment_version` — so the frontend literally cannot construct a valid `/move` request. That's why the day board currently bypasses `/move` with a raw `PATCH /jobs/{id}` double-write.
3. The board entry omits `job_number`/`customer_name`/`site_address`, so the FE fakes labels via a second `GET /jobs/?scheduled_date=` call.

**Part A fixes the contract**; Part B (React) then rewrites the hooks and wires the pipeline.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: do NOT treat them as "pre-existing" and proceed. Either confirm with Tom it's a known accepted failure, or fix it before touching any batch files.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` MCP is **read-only verification only**. Never INSERT/UPDATE/DELETE. If a query fails or returns unexpected results → STOP and ask Tom.

> **Engineer safety net (MANDATORY)**: Before writing ANY SQLModel field reference or query in this batch, independently verify every column. The prompt's column names were derived from a prior MCP session — the live DB is the only authoritative source. If any name differs → use the MCP-returned name and note the discrepancy in your Completion Summary.

Run all of these via `postgres-local` MCP:

```sql
-- 1. Confirm job.version (optimistic lock) + job_number (label) exist; title absent until JOB-UI-B1
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
  AND column_name IN ('version', 'job_number', 'title', 'customer_id', 'site_id')
ORDER BY column_name;
-- EXPECT: version(integer,NO), job_number(character varying,NO), customer_id(uuid,NO), site_id(uuid,NO).
-- EXPECT: title returns ZERO rows (not yet added — JOB-UI-B1 adds it later).

-- 2. Confirm job_tech_assignment carries version + the columns used to find the active primary
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_tech_assignment'
  AND column_name IN ('id', 'version', 'role', 'is_active', 'user_id', 'job_id')
ORDER BY column_name;
-- EXPECT: id(uuid,NO), version(integer,NO), role(text,NO), is_active(boolean,NO), user_id(uuid,NO), job_id(uuid,NO).

-- 3. Confirm the customer display-name column (for customer_name enrichment)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer'
  AND column_name IN ('id', 'display_name')
ORDER BY column_name;

-- 4. Confirm the address/site columns used for site_address enrichment
--    (verify how site → address is modeled before assuming a column name)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name IN ('site', 'address')
ORDER BY table_name, ordinal_position;
```

> **On query 4**: The design doc references an `Address` import already used inside `_dispatch_board_impl` (for ETA GPS lookups). **Read that code** to see exactly how site → address is resolved before you decide which field(s) compose `site_address`. Do not assume a single `address` text column exists — it may be composed from line1/city/state.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/schemas/schemas.py                 ← lines ~787–856: DispatchBoardJobEntry / TechGroup / Response — the exact schema you extend
backend/api/routes/scheduling.py               ← _dispatch_board_impl (~line 955) + JobMoveRequest/Response (~1268) — how entries are built + what /move needs
backend/app/models/fulfillment.py              ← Job model: confirm version, job_number, customer_id, site_id field names
backend/app/models/scheduling.py               ← JobTechAssignment model: confirm id/version/role/is_active/user_id
backend/app/models/crm.py                       ← Customer + Address/Site models: confirm display_name + address composition
backend/tests/conftest.py                       ← available fixtures (test_tenant, test_job, test_customer, test_site, client)
backend/db_models_map.md                        ← confirm model→table names
```

Also run these greps to locate related code:

```bash
grep -rn "DispatchBoardJobEntry\|_dispatch_board_impl" backend/ --include="*.py" -l
grep -rn "model_validate(job)" backend/api/routes/scheduling.py
```

---

## Task 1 — Extend `DispatchBoardJobEntry` (Pydantic schema)

**File**: `backend/api/schemas/schemas.py`

Add the DISPATCH-B1 fields to `DispatchBoardJobEntry` per design doc §D.1. **Read the file first** and match the existing style (it uses `ConfigDict(from_attributes=True)`).

```python
class DispatchBoardJobEntry(BaseModel):
    """Minimal job summary included in the dispatch board payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    site_id: UUID
    status_id: UUID
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    estimated_duration_minutes: int | None
    external_calendar_event_id: str | None
    is_active: bool
    eta_minutes: int | None = None
    # ── DISPATCH-B1 additions ──────────────────────────────────────────────
    version: int                              # optimistic lock → FE sends as expected_job_version
    primary_assignment_id: UUID | None = None # active primary JobTechAssignment.id (null = unassigned)
    assignment_version: int | None = None     # → FE sends as expected_assignment_version
    job_number: str                           # label (until JOB-UI-B1 adds title)
    customer_name: str | None = None          # enrichment — retires FE second-fetch
    site_address: str | None = None           # enrichment
    title: str | None = None                  # FORWARD-COMPAT: null now; JOB-UI-B1 populates
```

> **Important — `from_attributes` will auto-map `version`, `job_number` from the `Job` ORM row** when you call `model_validate(job)`. But `primary_assignment_id`, `assignment_version`, `customer_name`, `site_address` are **NOT** on the `Job` row — they come from joined data you must inject explicitly in Task 2. Do not rely on `from_attributes` for those four.

Intermediate check:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Populate the new fields in `_dispatch_board_impl`

**File**: `backend/api/routes/scheduling.py`

Read the whole `_dispatch_board_impl` function first. It already:
- Loads all in-window `Job` rows (`jobs`).
- Loads all active primary `JobTechAssignment` rows (`assignments`) and builds `job_to_tech: dict[job_id → user_id]`.
- Calls `DispatchBoardJobEntry.model_validate(job)` per job (line ~1032).

Make these changes:

**2a — Extend the assignment map to carry assignment id + version.** Where `job_to_tech` is built (~line 1025), also build:
```python
# job_id → (user_id, assignment_id, assignment_version)
job_to_assignment: dict[UUID, tuple[UUID, UUID, int]] = {
    a.job_id: (a.user_id, a.id, a.version) for a in assignments
}
```

**2b — Batch-load customer names and site addresses (anti-N+1).** After the jobs are loaded, add exactly two batched queries keyed by the already-collected ids. Verify the exact column/relationship names against your MCP query 3 + 4 results and the model reads:
```python
# customer_name lookup — one query
customer_ids = {j.customer_id for j in jobs}
customers = db.exec(
    select(Customer).where(Customer.id.in_(customer_ids))
).all()
customer_name_by_id = {c.id: c.display_name for c in customers}

# site_address lookup — one query (compose from the real Address/Site model shape you confirmed)
site_ids = {j.site_id for j in jobs}
# ... load sites/addresses, build site_address_by_id: dict[site_id → str | None]
```

> Compose `site_address` from whatever the real model exposes (confirmed in your reads) — e.g. a single formatted string. If site→address requires a join, do it in one batched query, not per-job.

**2c — Inject the enrichment when building each entry.** Replace the bare `DispatchBoardJobEntry.model_validate(job)` with a helper that layers the joined fields on top:
```python
def _build_entry(job: Job) -> DispatchBoardJobEntry:
    entry = DispatchBoardJobEntry.model_validate(job)  # maps id, version, job_number, etc.
    assignment = job_to_assignment.get(job.id)
    if assignment:
        _user_id, assignment_id, assignment_version = assignment
        entry.primary_assignment_id = assignment_id
        entry.assignment_version = assignment_version
    entry.customer_name = customer_name_by_id.get(job.customer_id)
    entry.site_address = site_address_by_id.get(job.site_id)
    # entry.title stays None until JOB-UI-B1
    return entry
```

Use `_build_entry(job)` in **both** the assigned-tech grouping loop AND the unassigned bucket (unassigned entries must also carry `version`/`job_number`/`customer_name`/`site_address`; their `primary_assignment_id`/`assignment_version` stay `None`).

> **Confirm `version` + `job_number` populate via `from_attributes`.** If `model_validate(job)` raises because `version` is required but missing on the ORM instance, that means the field name differs from the live column — re-check MCP query 1 and use the exact name.

Intermediate check:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
python -m pytest tests/domains/scheduling_dispatch/ -q 2>&1 | tail -10
```

---

## Task 3 — Tests

Per `backend/tests/README-adding-tests.md`. Domain folder: **`scheduling_dispatch/`**.

Add tests (extend an existing dispatch-board test file if one exists in that folder; otherwise create `test_dispatch_b1_board_enrichment.py`):

```python
pytestmark = [
    pytest.mark.domain_scheduling_dispatch,
    pytest.mark.unit,
]
```

**Required coverage** (use the `client` fixture + `/dispatch-board/test` endpoint, and `test_tenant`/`test_job`/`test_customer`/`test_site` fixtures — never hardcoded UUIDs; scope assertions by inserted IDs, never total counts):

1. **Assigned job entry carries the new fields** — create a job with a scheduled time + a primary `JobTechAssignment`; call the board; find the entry by the inserted `job.id`; assert it has non-null `version` (int), `primary_assignment_id`, `assignment_version` (int), `job_number` (str), and `customer_name` matches the seeded customer's `display_name`.
2. **Unassigned entry carries labels but null assignment fields** — create a scheduled job with NO active primary assignment; assert the board's `unassigned[]` entry (by inserted id) has `version`, `job_number`, `customer_name` populated and `primary_assignment_id is None`, `assignment_version is None`.
3. **`title` is null (forward-compat)** — assert the entry's `title` is `None` (JOB-UI-B1 will populate later).
4. **`site_address` populated** — assert the entry's `site_address` reflects the seeded site's address (or is `None` if the seeded site has no address — assert the exact expected value for your fixture).

> Use the `/dispatch-board/test` unauthenticated endpoint (per the existing dispatch-board tests in the repo — read `backend/tests/batch_1e/test_task_1b3_dispatch_board.py` for the exact request pattern: `params={"start_date": ..., "end_date": ...}` with ISO datetimes).

Intermediate check:
```bash
python -m pytest tests/domains/scheduling_dispatch/ -v 2>&1 | tail -20
```

---

## Regenerate OpenAPI (handoff signal)

After all tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify the new fields appear in the machine spec (the React Engineer consumes this via `pnpm sync-api-types`):

```bash
python3 -c "
import json
spec = json.load(open('openapi.json'))
props = spec['components']['schemas']['DispatchBoardJobEntry']['properties']
for k in ['version','primary_assignment_id','assignment_version','job_number','customer_name','site_address','title']:
    print(k, '->', k in props)
"
grep -A 3 "DispatchBoardJobEntry" backend/openapi_schema_map.md | head -20
```

All seven keys must print `True`.

---

## Final Verification

### Phase 1 — Unit Tests Only (during development)
```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full Suite (once, at the end)
```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/scheduling_dispatch/ -v 2>&1 | tail -20
echo "=== DISPATCH-B1 PART A FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase — including apparently pre-existing — must be fixed before done. If you cannot find the root cause → STOP and ask Tom.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) via `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — `job.version`/`job_number` confirmed, `job.title` absent, `job_tech_assignment.version` confirmed, customer/site columns confirmed
- [ ] All mandatory source files read (including `api/schemas/schemas.py` + the two models)
- [ ] `DispatchBoardJobEntry` extended with `version`, `primary_assignment_id`, `assignment_version`, `job_number`, `customer_name`, `site_address`, `title` (forward-compat null)
- [ ] `_dispatch_board_impl` populates all new fields for BOTH assigned and unassigned entries
- [ ] Enrichment uses batched queries (no N+1) — customers + sites loaded once each
- [ ] New test file uses `pytestmark` with `domain_scheduling_dispatch` + `unit`; no module-level `TestClient`; `test_tenant`/`test_job` fixtures; ID-scoped assertions
- [ ] `python export_openapi_json.py` run — all 7 new keys present in `openapi.json` (verified via the python snippet) and `openapi_schema_map.md`
- [ ] **Phase 1**: All unit tests pass
- [ ] **Phase 2**: Full suite passes
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B
- [ ] **Handoff performed** (see below)

---

## Handoff to Part B (React Engineer)

After DoD is green, the React Engineer needs a clean handoff (Rule 9.3):

1. Confirm `python export_openapi_json.py` was run and committed.
2. In your Completion Summary, include this **Handoff Note**:
   > "Part A complete. `DispatchBoardJobEntry` now returns `version`, `primary_assignment_id`, `assignment_version`, `job_number`, `customer_name`, `site_address`, `title(null)`. React Engineer: run `pnpm sync-api-types` FIRST. The real move contract is `POST /api/v1/scheduling/jobs/{id}/move` with body `{tech_user_id, scheduled_start_at, scheduled_end_at, expected_job_version, expected_assignment_version?}`; conflict preview is `POST /api/v1/scheduling/jobs/{id}/check-conflicts` returning `{is_feasible, conflicts[], drive_time_*_minutes}`."

---

## Completion Summary

After all DoD items are complete, add a Completion Summary to `pilot-launch-plan.md` Appendix B using the standard template:

```markdown
### DISPATCH-B1 (Backend) — Dispatch Board Response Enrichment: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Source design doc**: `batch-dispatch-b1-design.md`
**Baseline**: X passed, Y skipped
**Final**: X+N passed, Y skipped (+N tests)

#### What Was Accomplished
- Extended `DispatchBoardJobEntry` with version/assignment/label fields (no migration — fields pre-existed)
- Populated new fields in `_dispatch_board_impl` for assigned + unassigned entries via batched queries
- Regenerated OpenAPI — enables Part B to drive the real /move contract

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/api/schemas/schemas.py` | Updated — DispatchBoardJobEntry fields |
| `backend/api/routes/scheduling.py` | Updated — _dispatch_board_impl enrichment |
| `backend/tests/domains/scheduling_dispatch/test_dispatch_b1_board_enrichment.py` | Created |
| `backend/openapi.json` / `openapi_schema_map.md` | Regenerated |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/scheduling_dispatch/test_dispatch_b1_board_enrichment.py` | `scheduling_dispatch` | N | ✅ |

#### Handoff Note
[the handoff note above]
```

---

## After This Task — Next Step

Hand off to the **Pilot React Engineer** with `batch-dispatch-b1-react-engr-prompt.md`. Do not start Part B yourself.
