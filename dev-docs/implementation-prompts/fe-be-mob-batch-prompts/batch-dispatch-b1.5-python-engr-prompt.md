# Implementation Prompt: DISPATCH-B1.5 (Part A) — Add `site_name` to Dispatch Board Response

**Mode**: Pilot Python Engineer
**Batch**: DISPATCH-B1.5 (Part A — Backend, runs FIRST)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 DISPATCH-B1.5
**Design doc**: `batch-dispatch-b1-design.md` (Part A pattern this mirrors) · `dispatch-b1.5-ui-design-spec.md`
**Estimated session**: 30–45 minutes
**Platform**: Backend only (`backend/`)
**Frontend companion**: DISPATCH-B1.5 (Part B — Pilot React Engineer). This backend half runs first + hands off.
**Depends on**: DISPATCH-B1 (Part A) — the `DispatchBoardJobEntry` enrichment + site batch-load this extends must already be merged.

---

## ⚠️ MANDATORY STOP: Read These First

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design)
- **`backend/tests/README-adding-tests.md`** — full document

Critical rules for this batch:

- **Rule 1**: Never guess column names. Use `postgres-local` MCP to verify. If MCP errors → STOP and ask Tom.
- **Rule 3**: After the response-model change → run `python export_openapi_json.py`. Handoff signal to the React Engineer.
- **Rule 5**: Never module-level `TestClient`. Use the `client` fixture.
- **Rule 6**: `db.get()` banned on tenant-scoped models — tenant-scoped `select()` with `WHERE tenant_id`.
- **Rule 7**: `postgres-local` MCP is read-only. Never INSERT/UPDATE/DELETE.
- **Rule 11**: Any failing test — even apparently pre-existing — must be fixed before done.

> **No migration.** `site.name` already exists (MCP-verified 2026-07-26: `character varying`, nullable). Pure Pydantic + one-line enrichment change. If you start an Alembic migration, STOP — you misread the scope.

---

## Background / Context

The `JobPropertiesPanel` should show **customer + site name + address** so the dispatcher sees whatever's meaningful (a commercial account's site name like "North Warehouse" is often more useful than a raw address). DISPATCH-B1 added `customer_name` + `site_address` to `DispatchBoardJobEntry` but **not** the site's name — so the React Engineer was blocked from rendering it. This batch adds the one missing field, populated from the same site batch-load B1 already runs.

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

> **MCP is read-only.** If a query errors → STOP and ask Tom.

```sql
-- 1. Confirm site.name exists (the field this batch surfaces)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'site'
  AND column_name IN ('id', 'name')
ORDER BY column_name;
-- EXPECT: id(uuid,NO), name(character varying,YES)

-- 2. Confirm DispatchBoardJobEntry already carries B1's site_address (this batch depends on B1)
--    Verify via code read of api/schemas/schemas.py — site_address present.
```

---

## Pre-Work: Read These Source Files

```
backend/api/schemas/schemas.py       ← DispatchBoardJobEntry (~788) — add site_name next to site_address
backend/api/routes/scheduling.py     ← _dispatch_board_impl (~955–1065): the site batch-load + _build_entry helper B1 added for site_address
backend/app/models/crm.py            ← Site model: confirm `name` field
backend/tests/batch_1e/test_task_1b3_dispatch_board.py  ← /dispatch-board/test request pattern
```

Grep the existing site enrichment to find exactly where to extend it:
```bash
grep -n "site_address\|site_address_by_id\|Site\b\|_build_entry" backend/api/routes/scheduling.py
```

---

## Task 1 — Add `site_name` to the schema

**File**: `backend/api/schemas/schemas.py`

Add next to `site_address` (read the file; match the B1 comment style):
```python
    site_name: str | None = None   # site.name — dispatcher-facing label (e.g. "North Warehouse")
```

---

## Task 2 — Populate it in `_dispatch_board_impl`

**File**: `backend/api/routes/scheduling.py`

B1 already batch-loads sites to build `site_address_by_id`. Extend that **same** load to also capture the name — do NOT add a second query:
```python
# Where B1 builds site_address_by_id from the batched Site load, also build:
site_name_by_id = {s.id: s.name for s in sites}   # reuse the SAME `sites` result set
```
Then in the `_build_entry` helper (B1), set:
```python
    entry.site_name = site_name_by_id.get(job.site_id)
```
Applies to both assigned and unassigned entries (same as `site_address`).

> If B1 loaded only specific columns of `Site` rather than full rows, confirm `name` is included; adjust the select to include `Site.name`. Verify against your file read — do not assume.

Intermediate:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
python -m pytest tests/domains/scheduling_dispatch/ -q 2>&1 | tail -10
```

---

## Task 3 — Test

Domain **`scheduling_dispatch/`**. Extend the existing B1/B1.25 dispatch-board test file (or add `test_dispatch_b1_5_site_name.py`):
```python
pytestmark = [pytest.mark.domain_scheduling_dispatch, pytest.mark.unit]
```
Coverage (use `/dispatch-board/test`, `test_tenant`/`test_job`/`test_site` fixtures, ID-scoped assertions):
1. **`site_name` populated** — create a job on a site with a known `name`; the board entry (found by inserted job id) has `site_name` equal to that site's name.
2. **Null-safe** — a site with `name = None` yields `site_name is None` (no error).

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
p = json.load(open('openapi.json'))['components']['schemas']['DispatchBoardJobEntry']['properties']
print('site_name present ->', 'site_name' in p)
"
```
Must print `True`.

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
echo "=== DISPATCH-B1.5 PART A FINAL VERIFICATION COMPLETE ==="
```
Any failure in either phase fixed before done.

---

## Definition of Done

- [ ] Regression baseline captured; zero pre-existing failures (or confirmed with Tom)
- [ ] MCP query 1 run — `site.name` confirmed
- [ ] Source files read (including `scheduling.py` site batch-load)
- [ ] `DispatchBoardJobEntry.site_name` added
- [ ] `_dispatch_board_impl` populates `site_name` from the EXISTING site batch-load (no new query); applied to assigned + unassigned entries
- [ ] Tests: `site_name` populated + null-safe
- [ ] `python export_openapi_json.py` run — `site_name` present (verified via snippet)
- [ ] Phase 1 unit pass · Phase 2 full pass
- [ ] Final test count documented
- [ ] Completion Summary added to launch plan Appendix B
- [ ] Handoff note included

---

## Handoff to Part B

Include in the Completion Summary:
> "Part A complete. `DispatchBoardJobEntry` now returns `site_name` (from `site.name`). React Engineer: run `pnpm sync-api-types` first; the JobPropertiesPanel can now render customer + site name + address."

---

## Completion Summary

Add to `pilot-launch-plan.md` Appendix B (Python template).

---

## After This Task — Next Step

Hand off to the **Pilot React Engineer** with `batch-dispatch-b1.5-react-engr-prompt.md`.
