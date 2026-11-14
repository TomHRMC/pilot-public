# Batch UI-FIX-2A Design — Legacy `job_assignment` Table Removal + Seed Re-Target

**Batch**: UI-FIX-2A  
**Fix**: FIX-016  
**Engineer**: Python Engineer  
**Type**: Backend-only  
**Estimated effort**: ~2–3h  
**Dependencies**: None — can run immediately  
**Source decisions**: `ui-fix-2-decisions.md § FIX-016`

---

## A. Input Read Summary

| Input | Key Finding |
|---|---|
| `ui-fix-2-decisions.md` FIX-016 | Two separate tables: `job_assignment` (legacy, 0 rows, `fulfillment.py`) vs `job_tech_assignment` (active, scheduling API). FIX-005B seed wrote to wrong table. |
| MCP `job_assignment` columns | `id, tenant_id, job_id, user_id, is_lead, is_active` — **0 rows in live DB** |
| MCP `job_tech_assignment` columns | `id, tenant_id, job_id, user_id, assigned_by_user_id, role, ordinal, assigned_at, is_active, version` — **active, has rows** |
| `backend/app/models/fulfillment.py` | `JobAssignment` class at line ~392, `__tablename__ = "job_assignment"` |
| `backend/app/models/__init__.py` | `JobAssignment` exported at line ~84 |
| `backend/services/data_export_compiler.py` | Imports and queries `JobAssignment` at line ~179 — returns empty results silently |
| `backend/migrations/scripts/seed_scenario_dispatch.py` | FIX-005B block at line ~511 writes to `public.job_assignment` — wrong table |
| `backend/check_columns_exist.py` | Lines 104–105 reference `("job_assignment", "is_lead")` and `("job_assignment", "is_active")` |
| Test files audited | 4 test methods verify constraints/indexes on the dropped table |

---

## B. Migration Plan

### Migration: Drop `job_assignment` Table

**Pre-migration state** (verified via MCP):
- `job_assignment` has 0 rows — safe to drop with no data loss
- All prior Alembic migrations for this table (FK hardening, composite indexes, datetime awareness, audit triggers) are in `versions/` and must NOT be modified (historical record for `alembic downgrade` chain)
- The audit trigger `audit_job_assignment_changes` fires on every INSERT/UPDATE/DELETE — must be dropped first

**MCP verification queries before migration**:
```sql
-- 1. Confirm 0 rows in job_assignment
SELECT COUNT(*) FROM public.job_assignment;

-- 2. Confirm all columns on job_assignment before drop
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_assignment'
ORDER BY ordinal_position;

-- 3. Confirm job_tech_assignment is intact and has active rows
SELECT COUNT(*) FROM public.job_tech_assignment WHERE is_active = true;

-- 4. Confirm audit trigger exists
SELECT trigger_name FROM information_schema.triggers
WHERE event_object_table = 'job_assignment';

-- 5. Confirm all constraints on job_assignment
SELECT conname, contype FROM pg_constraint
WHERE conrelid = 'public.job_assignment'::regclass;

-- 6. Confirm all indexes on job_assignment
SELECT indexname FROM pg_indexes
WHERE tablename = 'job_assignment';

-- 7. Current alembic head
SELECT version_num FROM public.alembic_version;
```

**New migration file**: `YYYY_MM_DD_HHMM-<hash>_remove_legacy_job_assignment_table.py`

**upgrade() sequence** (order matters — drop dependent objects before table):
1. Drop audit trigger: `DROP TRIGGER IF EXISTS audit_job_assignment_changes ON job_assignment`
2. Drop indexes: `idx_job_assignment_user_active`, `ix_job_assignment_tenant_id`
3. Drop unique constraint: `uq_job_assignment_job_user`
4. Drop FK constraints: `job_assignment_tenant_id_fkey`, `job_assignment_job_id_fkey`
5. Drop table: `job_assignment`

**downgrade()** (minimal — for rollback safety only): recreates table with original schema (no data recovery needed since table was empty).

**3-part NOT NULL pattern**: Not applicable — this is a DROP, not an ADD NOT NULL.

---

## C. Execution Order

| # | Task | File(s) | Type |
|---|---|---|---|
| 1 | Run MCP pre-work queries (verify 0 rows, table structure) | — | Verification |
| 2 | Write and run Alembic migration to drop `job_assignment` table | New migration file | Migration |
| 3 | Remove `JobAssignment` class from `fulfillment.py` | `backend/app/models/fulfillment.py` | Model |
| 4 | Remove `JobAssignment` from `__init__.py` | `backend/app/models/__init__.py` | Model |
| 5 | Replace `JobAssignment` query in `data_export_compiler.py` with `JobTechAssignment` | `backend/services/data_export_compiler.py` | Service |
| 6 | Remove `("job_assignment", ...)` entries from `check_columns_exist.py` | `backend/check_columns_exist.py` | Script |
| 7 | Re-target FIX-005B seed block to `job_tech_assignment` in `seed_scenario_dispatch.py` | `backend/migrations/scripts/seed_scenario_dispatch.py` | Seed |
| 8 | Delete test methods that verify dropped table constraints/indexes | 4 test files | Tests |
| 9 | Run unit tests; confirm no new failures | — | Verification |
| 10 | Run full test suite | — | Verification |

---

## D. New API Endpoints

None — this batch has no new or modified API endpoints.

---

## E. Pattern Reuse Decisions

- **No `set_audit_context_sync` required** — no mutation endpoints in this batch
- **No RFC 7807 required** — no endpoints added
- **Alembic blank migration pattern** — `alembic revision -m "remove_legacy_job_assignment_table"` (never `--autogenerate`)
- **`data_export_compiler.py` fix** — replace `JobAssignment` import with `JobTechAssignment` from `app.models.scheduling`. The query filters on `user_id` — same field exists on both tables.

---

## F. Shared Module Interfaces

### `data_export_compiler.py` fix (line ~179)

**Before** (broken — queries empty legacy table):
```python
from app.models.fulfillment import JobAssignment

for a in db.exec(
    select(JobAssignment).where(JobAssignment.user_id == user_id)
).all()
```

**After** (correct — queries active table):
```python
from app.models.scheduling import JobTechAssignment

for a in db.exec(
    select(JobTechAssignment)
    .where(JobTechAssignment.user_id == user_id)
    .where(JobTechAssignment.tenant_id == tenant_id)  # must add tenant scope
    .where(JobTechAssignment.is_active == True)
).all()
```

**Note**: The calling context must provide `tenant_id`. Confirm what variables are available at line ~179 before writing the fix — read the full function.

### `seed_scenario_dispatch.py` FIX-005B re-target

**Before** (wrong table):
```sql
SELECT id FROM public.job_assignment
WHERE tenant_id = :tid AND job_id = :jid AND user_id = :uid

INSERT INTO public.job_assignment
(id, tenant_id, job_id, user_id, is_lead, is_active, created_at, updated_at)
VALUES (:id, :tid, :jid, :uid, true, true, NOW(), NOW())
```

**After** (correct table + required columns):
```sql
SELECT id FROM public.job_tech_assignment
WHERE tenant_id = :tid AND job_id = :jid AND user_id = :uid

INSERT INTO public.job_tech_assignment
  (id, tenant_id, job_id, user_id, assigned_by_user_id,
   role, ordinal, assigned_at, is_active, version,
   created_at, updated_at)
VALUES
  (:id, :tid, :jid, :uid, :uid,
   'primary', 1, NOW(), true, 1,
   NOW(), NOW())
```

The log messages (`ℹ️` and `✅`) and the loop structure remain the same — only the SQL table name, column list, and values change.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Is `job_assignment` safe to drop? | ✅ Yes — 0 rows confirmed via MCP. |
| What about existing Alembic migrations that reference `job_assignment`? | ✅ Do NOT modify them — they are the historical record for `alembic downgrade` chain integrity. The new DROP migration is the final word. |
| Does `data_export_compiler.py` need `tenant_id` added to the `JobTechAssignment` query? | ✅ Yes — `JobTechAssignment` is tenant-scoped. The replacement query MUST filter by `tenant_id`. Read the full function to find where `tenant_id` is available in scope. |
| What about `test_find141_customer_response_sms_fields.py` which has `category_id="job_assignment"`? | ✅ No change needed — that string is a notification category identifier, not a table name. |
| What about the FIX-005B seed data that was already inserted into `job_assignment`? | ✅ The migration drops the table entirely, so old seed data is gone. The corrected seed will INSERT fresh rows into `job_tech_assignment` when `seed_scenario_dispatch.py` is run after the migration. |
