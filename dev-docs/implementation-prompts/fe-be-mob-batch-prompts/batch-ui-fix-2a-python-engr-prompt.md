# Implementation Prompt: UI-FIX-2A — Legacy `job_assignment` Table Removal + Seed Re-Target

**Mode**: Pilot Python Engineer  
**Batch**: UI-FIX-2A  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-016`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2a-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: None — this batch is a prerequisite for UI-FIX-2B (tech assignment)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Use `alembic revision -m "descriptive_name"`.
- **Rule 1**: Never guess column names. Use `postgres-local` MCP to verify before writing any SQL. If MCP returns an error → **STOP and ask Tom**.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.
- **Rule 3 (Migration)**: Always implement a complete `downgrade()` — never leave it empty.
- **Rule 11**: If ANY test fails — even one that appears pre-existing — **fix it before declaring done**. No exceptions without explicit confirmation from Tom.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: Do NOT proceed. Either (a) confirm with Tom that this is a known, accepted failure, OR (b) fix the failure first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. CRITICAL: Confirm 0 rows in job_assignment (safe to drop)
SELECT COUNT(*) AS row_count FROM public.job_assignment;

-- 2. Confirm job_assignment columns before drop
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_assignment'
ORDER BY ordinal_position;

-- 3. Confirm job_tech_assignment is intact and has rows
SELECT COUNT(*) AS active_rows FROM public.job_tech_assignment WHERE is_active = true;

-- 4. Confirm audit trigger exists on job_assignment
SELECT trigger_name FROM information_schema.triggers
WHERE event_object_table = 'job_assignment';

-- 5. Confirm all constraints on job_assignment (must drop before table)
SELECT conname, contype FROM pg_constraint
WHERE conrelid = 'public.job_assignment'::regclass;

-- 6. Confirm all indexes on job_assignment (must drop before table)
SELECT indexname FROM pg_indexes WHERE tablename = 'job_assignment';

-- 7. Verify current alembic head
SELECT version_num FROM public.alembic_version;
```

**Expected results**:
- Query 1: `row_count = 0` — if non-zero → **STOP and ask Tom before proceeding**
- Query 3: at least some active rows in `job_tech_assignment`
- Query 7: your current head revision

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/fulfillment.py          ← Find JobAssignment class (~line 392), understand fields
backend/app/models/__init__.py             ← Find JobAssignment export (~line 84)
backend/services/data_export_compiler.py  ← Find JobAssignment import/query (~line 179), understand the full function context before replacing
backend/check_columns_exist.py            ← Find the two job_assignment entries (~lines 104-105)
backend/migrations/scripts/seed_scenario_dispatch.py  ← Find FIX-005B block (~line 511), understand the full loop before editing
backend/app/models/scheduling.py          ← Read JobTechAssignment model — understand all fields before writing replacement query
```

Also run these to find test files referencing job_assignment:

```bash
grep -rn "job_assignment\|JobAssignment" backend/tests/ --include="*.py" -l
```

---

## Background

The legacy `job_assignment` table in `app/models/fulfillment.py` was superseded by `job_tech_assignment` in `app/models/scheduling.py`. The scheduling API exclusively uses `job_tech_assignment`. The legacy table has **0 rows** in the live DB and is not referenced by any active API endpoint — but it causes maintenance confusion, audit trigger noise, and most critically: the FIX-005B seed data from UI-FIX-1A (dispatch board seed) wrote assignments to the wrong table, which means the dispatch board still shows all DISP jobs as unassigned.

This batch: (1) drops the legacy table via Alembic migration, (2) removes the dead model and references, and (3) re-targets the seed script to write to the correct `job_tech_assignment` table.

---

## Task 1 — Alembic Migration: Drop `job_assignment` Table

**File**: New migration via `alembic revision -m "remove_legacy_job_assignment_table"`

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "remove_legacy_job_assignment_table"
```

Write the migration content. **Order matters** — drop dependent objects before the table itself:

```python
"""remove_legacy_job_assignment_table

Revision ID: <generated>
Revises: <current_head>
Create Date: <generated>
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    # 1. Drop audit trigger first
    op.execute("DROP TRIGGER IF EXISTS audit_job_assignment_changes ON job_assignment;")

    # 2. Drop indexes
    op.drop_index("idx_job_assignment_user_active", table_name="job_assignment")
    op.drop_index("ix_job_assignment_tenant_id", table_name="job_assignment")

    # 3. Drop unique constraint
    op.drop_constraint("uq_job_assignment_job_user", "job_assignment", type_="unique")

    # 4. Drop FK constraints
    op.drop_constraint(
        "job_assignment_tenant_id_fkey", "job_assignment", type_="foreignkey"
    )
    op.drop_constraint(
        "job_assignment_job_id_fkey", "job_assignment", type_="foreignkey"
    )

    # 5. Drop table
    op.drop_table("job_assignment")


def downgrade() -> None:
    # Recreate table (minimal — for rollback safety; 0 rows were present before upgrade)
    op.create_table(
        "job_assignment",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(), nullable=True),
        sa.Column("updated_by", postgresql.UUID(), nullable=True),
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("job_id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column(
            "is_lead", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.PrimaryKeyConstraint("id"),
    )
```

> **Verify constraint/index names match exactly** against what MCP returned in Pre-Work queries 5 and 6. If names differ → use the MCP-returned names, not the names in this prompt.

Run and verify:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current   # must show the new revision as head
```

**Intermediate unit test check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Remove `JobAssignment` Model + Exports

### 2.1 — `backend/app/models/fulfillment.py`

Read the file first. Locate the `JobAssignment` class (around line 392) and delete it entirely — the class definition plus any blank lines immediately before it that separate it from the preceding class.

**Do NOT** delete any other class. Only the `JobAssignment` class with `__tablename__ = "job_assignment"`.

### 2.2 — `backend/app/models/__init__.py`

Read the file first. Remove:
- The import of `JobAssignment` from `app.models.fulfillment`
- The `JobAssignment` entry from `__all__` (if present)

**Do NOT** remove any other imports. Only the `JobAssignment` import.

**Intermediate unit test check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 3 — Fix `data_export_compiler.py`

Read `backend/services/data_export_compiler.py` in full before editing. Find the function that imports `JobAssignment` (around line 179) and understand:
- What variables are in scope (especially whether `tenant_id` is available)
- What the query result is used for

Replace the `JobAssignment` import and query with `JobTechAssignment`:

```python
# BEFORE (broken — queries empty legacy table):
from app.models.fulfillment import JobAssignment

for a in db.exec(
    select(JobAssignment).where(JobAssignment.user_id == user_id)
).all()

# AFTER (correct — queries active table, must include tenant scope):
from app.models.scheduling import JobTechAssignment

for a in db.exec(
    select(JobTechAssignment)
    .where(JobTechAssignment.user_id == user_id)
    .where(JobTechAssignment.tenant_id == tenant_id)   # add tenant_id from context
    .where(JobTechAssignment.is_active == True)
).all()
```

> **If `tenant_id` is not in scope at that location**: Find where it comes from in the calling context and pass it through. Do NOT skip the `tenant_id` filter — `JobTechAssignment` is a tenant-scoped table and must always be filtered by tenant.

**Intermediate unit test check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 4 — Remove Dead Entries from `check_columns_exist.py`

Read `backend/check_columns_exist.py`. Find and remove these two tuples (around lines 104–105):

```python
("job_assignment", "is_lead"),
("job_assignment", "is_active"),
```

Do NOT remove any other tuples. The file is a list of `(table, column)` pairs used to verify column existence — the `job_assignment` table no longer exists.

---

## Task 5 — Re-Target FIX-005B Seed to `job_tech_assignment`

Read `backend/migrations/scripts/seed_scenario_dispatch.py` in full. Find the FIX-005B block (around line 511) that:
1. Does a SELECT to check if an assignment already exists for the DISP job
2. Does an INSERT if the assignment doesn't exist

**Change both SQL statements** to target `public.job_tech_assignment` instead of `public.job_assignment`.

The SELECT check (change table name only):
```sql
-- BEFORE:
SELECT id FROM public.job_assignment
WHERE tenant_id = :tid AND job_id = :jid AND user_id = :uid

-- AFTER:
SELECT id FROM public.job_tech_assignment
WHERE tenant_id = :tid AND job_id = :jid AND user_id = :uid
```

The INSERT (change table name AND column list):
```sql
-- BEFORE:
INSERT INTO public.job_assignment
(id, tenant_id, job_id, user_id, is_lead, is_active, created_at, updated_at)
VALUES (:id, :tid, :jid, :uid, true, true, NOW(), NOW())

-- AFTER:
INSERT INTO public.job_tech_assignment
  (id, tenant_id, job_id, user_id, assigned_by_user_id,
   role, ordinal, assigned_at, is_active, version,
   created_at, updated_at)
VALUES
  (:id, :tid, :jid, :uid, :uid,
   'primary', 1, NOW(), true, 1,
   NOW(), NOW())
```

Keep all other Python code (loop structure, print messages, error handling) unchanged. Only the SQL strings change.

> **Note**: `assigned_by_user_id` defaults to the same user being assigned (`:uid`) since seed data doesn't track a separate assigner.

---

## Task 6 — Delete Dead Test Methods

Find these test methods (use the grep output from Pre-Work) and delete them:

| File | Method to delete |
|---|---|
| `backend/tests/phase_6/test_phase_6_0_task_1_constraints_audit.py` | `test_job_assignment_duplicate_prevention` — verifies `uq_job_assignment_job_user` constraint on the dropped table |
| `backend/tests/phase_6/test_phase_6_0_task_3_composite_indexes.py` | `test_job_assignment_user_active_index_exists` — verifies `idx_job_assignment_user_active` on dropped table; ALSO remove `'idx_job_assignment_user_active'` from any bulk index list in that same file |
| `backend/tests/batch_1b/test_task_1b1_financial_fk_hard_delete_lockdown.py` | `test_job_assignment_tenant_id` AND `test_job_assignment_job_id` — both verify FK constraints on the dropped table |
| `backend/tests/batch_1e/test_task_1b4_conflict_detection.py` | Remove `("job_assignment", "job_id")` from whatever list/tuple it appears in — the table is gone |

**Read each file before editing.** Delete only the listed method(s) and the `("job_assignment", ...)` list entry. Do NOT delete other test methods in those files.

> **`test_find141_customer_response_sms_fields.py`** has `category_id="job_assignment"` — this is a notification category string, NOT a table name. Do NOT touch it.

**Intermediate unit test check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Test Requirements

No new tests are added in this batch — this is a deletion/cleanup batch. All four deleted test methods verified constraints and indexes on the now-dropped table.

**After Task 6**: Verify the deleted test file passes (i.e., the remaining tests in those files still pass):

```bash
python -m pytest backend/tests/phase_6/test_phase_6_0_task_1_constraints_audit.py --tb=short -q
python -m pytest backend/tests/phase_6/test_phase_6_0_task_3_composite_indexes.py --tb=short -q
python -m pytest backend/tests/batch_1b/test_task_1b1_financial_fk_hard_delete_lockdown.py --tb=short -q
python -m pytest backend/tests/batch_1e/test_task_1b4_conflict_detection.py --tb=short -q
```

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass. Fix any failure before proceeding to Phase 2.

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10

echo "=== UI-FIX-2A FINAL VERIFICATION COMPLETE ==="
```

> **Any failure must be fixed before declaring the batch done.** No "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] MCP query 1 confirmed: `job_assignment` has 0 rows
- [ ] MCP query 3 confirmed: `job_tech_assignment` has active rows
- [ ] All 7 MCP pre-work queries run — results match expected values
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: Alembic migration written and run — `alembic current` shows new head; downgrade/upgrade cycle verified
- [ ] **Task 2**: `JobAssignment` class deleted from `fulfillment.py`; import removed from `__init__.py`
- [ ] **Task 3**: `data_export_compiler.py` updated to use `JobTechAssignment` with `tenant_id` scope
- [ ] **Task 4**: Two `job_assignment` entries removed from `check_columns_exist.py`
- [ ] **Task 5**: `seed_scenario_dispatch.py` FIX-005B block re-targeted to `job_tech_assignment` with correct column list
- [ ] **Task 6**: 4 dead test methods deleted; remaining tests in those files still pass
- [ ] No module-level `TestClient` in any modified test file
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `ui-fix-2-decisions.md` batch overview section

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** subsection to `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` under the Implementation Batches section for **UI-FIX-2A**:

```markdown
### UI-FIX-2A — Legacy `job_assignment` Removal + Seed Re-Target: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests / -M deleted tests)

#### What Was Accomplished

- Dropped `job_assignment` table via Alembic migration (0 rows, safe drop)
- Removed `JobAssignment` ORM model from `fulfillment.py` and `__init__.py`
- Fixed `data_export_compiler.py` — now queries `JobTechAssignment` with proper tenant scope
- Removed dead `check_columns_exist.py` entries
- Re-targeted FIX-005B seed block to `job_tech_assignment` with required columns
- Deleted 4 test methods that verified constraints on the dropped table

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/<hash>_remove_legacy_job_assignment_table.py` | Created — drops job_assignment table, indexes, constraints, audit trigger |
| `backend/app/models/fulfillment.py` | Updated — removed JobAssignment class |
| `backend/app/models/__init__.py` | Updated — removed JobAssignment import |
| `backend/services/data_export_compiler.py` | Updated — replaced JobAssignment query with JobTechAssignment |
| `backend/check_columns_exist.py` | Updated — removed job_assignment column entries |
| `backend/migrations/scripts/seed_scenario_dispatch.py` | Updated — FIX-005B re-targeted to job_tech_assignment |
| `backend/tests/phase_6/test_phase_6_0_task_1_constraints_audit.py` | Updated — deleted test_job_assignment_duplicate_prevention |
| `backend/tests/phase_6/test_phase_6_0_task_3_composite_indexes.py` | Updated — deleted test_job_assignment_user_active_index_exists |
| `backend/tests/batch_1b/test_task_1b1_financial_fk_hard_delete_lockdown.py` | Updated — deleted 2 FK lockdown test methods |
| `backend/tests/batch_1e/test_task_1b4_conflict_detection.py` | Updated — removed job_assignment from FK check list |
```

---

## After This Batch — Next Step

Once UI-FIX-2A is complete and all tests pass:
- **UI-FIX-2B** (tech assignment multi-surface) can start — it requires the seed data to correctly target `job_tech_assignment` so the dispatch board shows populated assignments
- **UI-FIX-2C** (Notifications consolidation) and **UI-FIX-2D** (Customer detail tabs) can run in parallel immediately — they have no dependency on this batch
