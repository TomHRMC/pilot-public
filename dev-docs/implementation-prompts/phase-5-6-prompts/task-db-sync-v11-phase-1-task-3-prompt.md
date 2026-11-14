# Task 3: Job Management Tables - Audit FK Constraints

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - Task 3
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **Audit FK Constraints Analysis** ⭐
- Current Live Database (Phase 6.0.1 Task 2 Post-State)
**Type:** Phase 6.0.1 - Foreign Key Constraints for Audit Columns
**Priority:** HIGH
**Change Type:** FOREIGN KEY CONSTRAINTS + MODEL UPDATES + TESTING

---

## Context

This is **Phase 6.0.1 Task 3 - DB Sync v#11**, implementing **Foreign Key constraint enforcement** for Job Management audit trail columns.

**Root Cause:** 
- The JSON master blueprint specifies that ALL `created_by` and `updated_by` tracking columns should have explicit Foreign Key constraints referencing `user.id`
- Currently, these columns exist physically and application code populates them correctly
- **But**: No database-level referential integrity enforcement exists

**Critical Impact:**
- **Data Integrity Vulnerability:** Invalid user IDs can be inserted into audit columns
- **Orphaned Audit Records:** If users are deleted, audit trail breaks
- **Broken Audit Trail:** Cannot reliably trace actions back to users
- **Compliance Violations:** SOC 2, GDPR audit requirements compromised

**Scope:** **Task 3 of 9** - **32 Foreign Key constraints** across **19 tables**:
- **13 tables**: Both `created_by` AND `updated_by` Foreign Keys (26 FKs)
- **6 tables**: Only `created_by` Foreign Key (6 FKs)

**Key Principle:** Phase 6.0.1 uses **9 separate Alembic migrations** (one per functional domain) for surgical rollback capability, optimized task sizing (~15-20 tables per task), and keeping AI agent context usage at 50-60%.

---

## What Was Completed in Previous Tasks

**Phase 6.0.1 Task 1 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 39 Foreign Key constraints (19 tables × 2 FKs + 1 table × 1 FK)
- ✅ Common & Reference tables (20 tables)
- ✅ 32 new tests passing
- ✅ 738/738 total tests passing (100%)

**Phase 6.0.1 Task 2 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 23 Foreign Key constraints (11 tables × 2 FKs + 1 table × 1 FK)
- ✅ Customer & Site Management tables (12 tables)
- ✅ 16 new tests passing
- ✅ 754/754 total tests passing (100%)

**Current Baseline:** 754/754 total tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement
- **Phase 5.1:** ✅ COMPLETE - Missing unique constraints & foreign keys
- **Phase 5.2:** ✅ COMPLETE - Exclusion constraints & critical indexes
- **Phase 5.3:** ✅ COMPLETE - Notification schema + idempotency + index standardization + triggers
- **Phase 6.0:** ✅ COMPLETE - Advanced constraints & performance indexes

**See:**
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` for Phase 6.0.1 complete plan
- `dev-docs/implementation-prompts/task-db-sync-v11-phase-1-task-1-prompt.md` for Task 1 details
- `dev-docs/implementation-prompts/task-db-sync-v11-phase-1-task-2-prompt.md` for Task 2 details

---

## Current Task: Job Management Tables - Audit FK Constraints

**Effort:** 3-4 hours (estimated)
**Gap Reference:** Phase 6.0.1 Analysis - Audit Trail Foreign Key Constraints
**Change Type:** MODEL VERIFICATION + MIGRATION + DATA VALIDATION + TESTING

This task implements Foreign Key constraints on audit columns for all Job Management tables, ensuring database-level referential integrity for job-related audit trails.

### What Needs to Be Fixed

**Job Management Tables (19 total):**

**Tables with BOTH created_by AND updated_by FKs (13 tables):**

| Table | Model File | Description |
|-------|-----------|-------------|
| `job` | `backend/app/models/fulfillment.py` | Core job entity |
| `job_status` | `backend/app/models/fulfillment.py` | Job status lookup |
| `job_assignment` | `backend/app/models/fulfillment.py` | User-to-job assignments |
| `job_notes` | `backend/app/models/fulfillment.py` | Job notes/comments |
| `job_attachment` | `backend/app/models/fulfillment.py` | Job file attachments |
| `job_expense` | `backend/app/models/fulfillment.py` | Job expenses |
| `job_expense_category` | `backend/app/models/fulfillment.py` | Expense categorization |
| `job_time_entry` | `backend/app/models/fulfillment.py` | Time tracking |
| `change_order` | `backend/app/models/quoting.py` | Change orders |
| `change_order_line` | `backend/app/models/quoting.py` | Change order line items |
| `change_order_attachment` | `backend/app/models/quoting.py` | Change order attachments |
| `job_labor_entry` | `backend/app/models/fulfillment.py` | Labor time tracking |
| `job_material_usage` | `backend/app/models/fulfillment.py` | Material consumption tracking |

**Tables with ONLY created_by FK (6 tables - append-only/transactional):**

| Table | Model File | Description |
|-------|-----------|-------------|
| `change_order_line_tax_component` | `backend/app/models/quoting.py` | Tax breakdown (append-only) |
| `job_status_history` | `backend/app/models/fulfillment.py` | Job status transitions (append-only) |
| `job_workflow_log` | `backend/app/models/fulfillment.py` | Workflow audit log (append-only) |
| `job_inspection` | `backend/app/models/fulfillment.py` | Inspection records (append-only) |
| `job_completion_checklist` | `backend/app/models/fulfillment.py` | Completion verification (append-only) |
| `job_photo` | `backend/app/models/fulfillment.py` | Job photos/documentation (append-only) |

### Model Location References

**IMPORTANT:** Use these reference files to understand model locations and import patterns:

- `backend/db_models_map.md` - Complete map of all models and their source files
- `backend/app_model_imports.md` - How to import models correctly in tests

**Example lookups:**
```markdown
# From db_models_map.md:
### `fulfillment.py`
- JobStatus
- Job
- JobNotes
- JobAttachment
- JobAssignment
- JobTimeEntry
- JobExpenseCategory
- JobExpense

### `quoting.py`
- ChangeOrder
- ChangeOrderLine
- ChangeOrderLineTaxComponent
- ChangeOrderAttachment
```

### Tools Available

- You have access to the postgres-local MCP server to query the DB directly, in read-only mode.
- Remember that you do not need to insert any '\n' characters in the sql when creating it for the mcp server.

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** Capture the current test baseline BEFORE making ANY changes.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run ALL Tests (Current Baseline)

```bash
# Run full test suite but without the integration tests FIRST

# Concise output to capture baseline count (this is preferred option to minimize tokens)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Full output to capture errors and warnings, or modify the concise output version as well
pytest --ignore=tests/integration/ tests/ -v

# Run all tests SECOND

# Concise output to capture baseline count (this is preferred option to minimize tokens)
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Full output to capture errors and warnings, or modify the concise output version as well
pytest tests/ -v
```

**Record the output:** `754/754 tests passing` (Phase 6.0.1 Task 2 completion baseline)

### Step 3: Document Your Baseline

**Write down this number before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 6.0.1 Specific Warnings

**BEFORE writing ANY code, review these Phase 6.0.1 critical issues:**

### 1. Orphaned Audit References - Pre-Migration Validation is MANDATORY

**CRITICAL:** Before creating FK constraints on `created_by` and `updated_by` columns, you MUST verify no orphaned references exist (audit columns referencing non-existent users).

**Why This Matters:**
- If `created_by = '12345678-...'` but that user ID doesn't exist in the user table, FK constraint creation will **FAIL**
- Migration would crash mid-execution
- Requires manual data cleanup before proceeding

**Validation Queries (MANDATORY for ALL tables in your task):**

```sql
-- Check orphaned created_by references for ALL Task 3 tables
SELECT 'job' as table_name, created_by, COUNT(*) as count
FROM job
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job.created_by)
GROUP BY created_by
UNION ALL
SELECT 'job_status', created_by, COUNT(*)
FROM job_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'job_assignment', created_by, COUNT(*)
FROM job_assignment
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_assignment.created_by)
GROUP BY created_by
UNION ALL
SELECT 'job_notes', created_by, COUNT(*)
FROM job_notes
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_notes.created_by)
GROUP BY created_by
UNION ALL
SELECT 'job_attachment', created_by, COUNT(*)
FROM job_attachment
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_attachment.created_by)
GROUP BY created_by
UNION ALL
SELECT 'job_expense', created_by, COUNT(*)
FROM job_expense
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_expense.created_by)
GROUP BY created_by
UNION ALL
SELECT 'job_expense_category', created_by, COUNT(*)
FROM job_expense_category
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_expense_category.created_by)
GROUP BY created_by
UNION ALL
SELECT 'job_time_entry', created_by, COUNT(*)
FROM job_time_entry
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_time_entry.created_by)
GROUP BY created_by
UNION ALL
SELECT 'change_order', created_by, COUNT(*)
FROM change_order
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = change_order.created_by)
GROUP BY created_by
UNION ALL
SELECT 'change_order_line', created_by, COUNT(*)
FROM change_order_line
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = change_order_line.created_by)
GROUP BY created_by
UNION ALL
SELECT 'change_order_attachment', created_by, COUNT(*)
FROM change_order_attachment
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = change_order_attachment.created_by)
GROUP BY created_by
UNION ALL
SELECT 'change_order_line_tax_component', created_by, COUNT(*)
FROM change_order_line_tax_component
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = change_order_line_tax_component.created_by)
GROUP BY created_by;
-- Expected: 0 rows (no orphaned references)

-- Check orphaned updated_by references (only for tables with updated_by - first 11 tables)
SELECT 'job' as table_name, updated_by, COUNT(*) as count
FROM job
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'job_status', updated_by, COUNT(*)
FROM job_status
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_status.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'job_assignment', updated_by, COUNT(*)
FROM job_assignment
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_assignment.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'job_notes', updated_by, COUNT(*)
FROM job_notes
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_notes.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'job_attachment', updated_by, COUNT(*)
FROM job_attachment
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_attachment.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'job_expense', updated_by, COUNT(*)
FROM job_expense
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_expense.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'job_expense_category', updated_by, COUNT(*)
FROM job_expense_category
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_expense_category.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'job_time_entry', updated_by, COUNT(*)
FROM job_time_entry
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = job_time_entry.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'change_order', updated_by, COUNT(*)
FROM change_order
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = change_order.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'change_order_line', updated_by, COUNT(*)
FROM change_order_line
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = change_order_line.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'change_order_attachment', updated_by, COUNT(*)
FROM change_order_attachment
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = change_order_attachment.updated_by)
GROUP BY updated_by;
-- Expected: 0 rows (no orphaned references)
```

**If ANY query returns rows > 0:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results showing orphaned user IDs
- **Report** - Ask for guidance on data cleanup strategy
- **Options:**
  - **Option A**: Set orphaned references to NULL (loses attribution but allows migration)
  - **Option B**: Create system user and map orphaned references to it (preserves "system created" attribution)
  - **Option C**: Delete records with orphaned references (data loss - use cautiously)
- **Re-validate** - Run all queries again to confirm 0 violations

---

### 2. Foreign Key Constraint Behavior: ON DELETE RESTRICT

**CRITICAL:** All FK constraints in Phase 6.0.1 use `ON DELETE RESTRICT` behavior.

**What This Means:**
```python
# CORRECT pattern for this phase
created_by: Optional[uuid.UUID] = Field(
    default=None,
    foreign_key="user.id",
    sa_column_kwargs={"ondelete": "RESTRICT"}  # ← MANDATORY
)
```

**Why RESTRICT:**
- **Preserves Audit Integrity**: Cannot delete a user if any audit trail references exist
- **Prevents Data Loss**: Ensures audit trail is never corrupted
- **Compliance**: Required for SOC 2, GDPR audit requirements

**Impact on Application:**
- Users with audit trail references **CANNOT** be hard-deleted
- Requires soft-delete workflow: `user.deleted_at = now()`, `user.is_active = False`

---

### 3. NULL Support for Backward Compatibility

**CRITICAL:** All audit column FK constraints MUST support NULL values.

**Current Schema:**
- Audit columns are defined as `nullable=True` in all models
- Existing records may have NULL audit fields (created before audit tracking)
- Future records should be non-NULL (application enforces), but DB allows NULL

**Correct Pattern:**
```python
# ✅ CORRECT - Allows NULL for backward compatibility
created_by: Optional[uuid.UUID] = Field(
    default=None,  # ← NULL is allowed
    foreign_key="user.id",
    sa_column_kwargs={"ondelete": "RESTRICT"}
)
```

---

### 4. SQLModel Foreign Key Syntax

**CRITICAL:** Use the correct SQLModel/SQLAlchemy pattern for foreign keys.

**Correct Syntax (SQLModel Field):**
```python
from typing import Optional
import uuid
from sqlmodel import Field, SQLModel

class Job(SQLModel, table=True):
    __tablename__ = "job"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    
    # ✅ CORRECT - Audit columns with FK constraints
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",  # ← String reference
        sa_column_kwargs={"ondelete": "RESTRICT"}
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",  # ← String reference
        sa_column_kwargs={"ondelete": "RESTRICT"}
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### 5. Alembic Migration Pattern for FK Constraints

**CRITICAL:** Use the correct Alembic operation for foreign key creation.

**Correct Migration Pattern:**
```python
"""Phase 6.0.1 Task 3: FK constraints for job management tables

Revision ID: phase_6_0_1_task_3_fk_audit_job
Revises: [PREVIOUS_REVISION_FROM_TASK_2]
Create Date: 2026-04-13
"""

def upgrade():
    # For tables with BOTH created_by and updated_by
    for table_name in [
        'job', 'job_status', 'job_assignment', 'job_notes', 'job_attachment',
        'job_expense', 'job_expense_category', 'job_time_entry',
        'change_order', 'change_order_line', 'change_order_attachment'
    ]:
        op.create_foreign_key(
            f'fk_{table_name}_created_by',
            table_name,
            'user',
            ['created_by'],
            ['id'],
            ondelete='RESTRICT'
        )
        op.create_foreign_key(
            f'fk_{table_name}_updated_by',
            table_name,
            'user',
            ['updated_by'],
            ['id'],
            ondelete='RESTRICT'
        )
    
    # For append-only tables (created_by only)
    for table_name in ['change_order_line_tax_component']:
        op.create_foreign_key(
            f'fk_{table_name}_created_by',
            table_name,
            'user',
            ['created_by'],
            ['id'],
            ondelete='RESTRICT'
        )

def downgrade():
    # Drop FK constraints in reverse order
    for table_name in ['change_order_line_tax_component']:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'job', 'job_status', 'job_assignment', 'job_notes', 'job_attachment',
        'job_expense', 'job_expense_category', 'job_time_entry',
        'change_order', 'change_order_line', 'change_order_attachment'
    ]:
        op.drop_constraint(f'fk_{table_name}_updated_by', table_name, type_='foreignkey')
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
```

---

## ⚠️ CRITICAL: Coding Agent Best Practices (From Previous Phases)

### 1. Use `db_session` NOT `session` in Tests
❌ **WRONG:**
```python
def test_example(session: Session, test_tenant):  # Wrong parameter name
    user = User(email="test@example.com")
    session.add(user)
```

✅ **CORRECT:**
```python
def test_example(db_session: Session, test_tenant):  # Correct parameter name
    user = User(email="test@example.com")
    db_session.add(user)
```

**Why:** The pytest fixture is named `db_session` in `backend/tests/conftest.py`.

---

### 2. Use SQLModel `select()` with `exec()` NOT `query()`

❌ **WRONG (Creates Deprecation Warnings):**
```python
user = db_session.query(User).filter(User.email == "test@example.com").first()
```

✅ **CORRECT (SQLModel Pattern):**
```python
from sqlmodel import select

user = db_session.exec(
    select(User).where(User.email == "test@example.com")
).first()
```

---

### 3. Test Foreign Key Constraints with pytest.raises(IntegrityError)

**Pattern for Testing FK Enforcement:**
```python
import pytest
from sqlalchemy.exc import IntegrityError
import uuid

def test_job_created_by_fk_enforcement(db_session, test_tenant):
    """Test that invalid created_by user ID is rejected"""
    from app.models.fulfillment import Job
    
    # Attempt to create record with non-existent user ID
    invalid_user_id = uuid.uuid4()
    job = Job(
        tenant_id=test_tenant.id,
        job_number="TEST-001",
        created_by=invalid_user_id  # Invalid user ID
    )
    db_session.add(job)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_job_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing User Deletion Prevention:**
```python
def test_user_deletion_prevented_by_job_audit_trail(db_session, test_user, test_tenant):
    """Test that user cannot be deleted if job audit references exist"""
    from app.models.fulfillment import Job
    
    # Create job with user audit reference
    job = Job(
        tenant_id=test_tenant.id,
        job_number="TEST-001",
        created_by=test_user.id
    )
    db_session.add(job)
    db_session.commit()
    
    # Attempt to delete user (should fail due to RESTRICT)
    db_session.delete(test_user)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_job_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing NULL Audit Columns (Backward Compatibility):**
```python
def test_job_null_audit_columns_allowed(db_session, test_tenant):
    """Test that NULL audit columns are allowed for backward compatibility"""
    from app.models.fulfillment import Job
    
    # Create record with NULL audit columns
    job = Job(
        tenant_id=test_tenant.id,
        job_number="TEST-001",
        created_by=None,  # NULL allowed
        updated_by=None
    )
    db_session.add(job)
    db_session.commit()  # Should succeed
    
    assert job.created_by is None
    assert job.updated_by is None
```

---

## Requirements

### Phase 6.0.1 Task 3 Breakdown

#### Task 3: Job Management FK Constraints (Migration 3 of 9)

**Scope:**
- 19 tables total
- 13 tables with BOTH `created_by` AND `updated_by` FKs (26 FKs)
- 6 tables with ONLY `created_by` FK (6 FKs)

**Migration Pattern:**
```python
"""Phase 6.0.1 Task 3: FK constraints for job management audit columns

Revision ID: phase_6_0_1_task_3_fk_audit_job
Revises: [PREVIOUS_REVISION_FROM_TASK_2]
Create Date: 2026-04-13
"""

def upgrade():
    # Add FK constraints for tables with both created_by and updated_by
    for table_name in [
        'job', 'job_status', 'job_assignment', 'job_notes', 'job_attachment',
        'job_expense', 'job_expense_category', 'job_time_entry',
        'change_order', 'change_order_line', 'change_order_attachment'
    ]:
        op.create_foreign_key(
            f'fk_{table_name}_created_by',
            table_name,
            'user',
            ['created_by'],
            ['id'],
            ondelete='RESTRICT'
        )
        op.create_foreign_key(
            f'fk_{table_name}_updated_by',
            table_name,
            'user',
            ['updated_by'],
            ['id'],
            ondelete='RESTRICT'
        )
    
    # Add FK constraints for append-only tables (created_by only)
    for table_name in ['change_order_line_tax_component']:
        op.create_foreign_key(
            f'fk_{table_name}_created_by',
            table_name,
            'user',
            ['created_by'],
            ['id'],
            ondelete='RESTRICT'
        )

def downgrade():
    # Drop FK constraints in reverse order
    for table_name in ['change_order_line_tax_component']:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'job', 'job_status', 'job_assignment', 'job_notes', 'job_attachment',
        'job_expense', 'job_expense_category', 'job_time_entry',
        'change_order', 'change_order_line', 'change_order_attachment'
    ]:
        op.drop_constraint(f'fk_{table_name}_updated_by', table_name, type_='foreignkey')
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
```

---

### Task 1: SQLModel Schema Definitions Verification

**Effort:** 0.5-1 day
**Scope:** Verify FK definitions across 19 tables in Task 3

#### What This Task Accomplishes

Confirm that all Phase 6.0.1 Task 3 changes are correctly defined in the Python SQLModel definitions. Update models with FK constraints on audit columns.

#### Tables to Check (Task 3)

**Model Files & Required Changes:**

1. `backend/app/models/fulfillment.py`
   - `Job`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `JobStatus`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `JobAssignment`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `JobNotes`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `JobAttachment`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `JobExpense`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `JobExpenseCategory`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `JobTimeEntry`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`

2. `backend/app/models/quoting.py`
   - `ChangeOrder`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `ChangeOrderLine`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `ChangeOrderAttachment`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `ChangeOrderLineTaxComponent`: Add `foreign_key="user.id"` to `created_by` ONLY (append-only)

**Success Criteria for Task 1:**
- [ ] All 19 tables in Task 3 have FK definitions added
- [ ] All FKs use string reference `"user.id"` not class reference
- [ ] All FKs specify `sa_column_kwargs={"ondelete": "RESTRICT"}`
- [ ] All audit columns remain `Optional[uuid.UUID]` (NULL support)
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models import *"`)

---

### Task 2: Pre-Migration Data Validation

**Effort:** 0.5 day
**Dependencies:** None (can run independently)
**CRITICAL:** Validation MUST pass before generating migration

#### What This Task Accomplishes

Verify that the database is ready for Phase 6.0.1 Task 3 migration by checking for orphaned audit references that would prevent FK constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Use the validation queries from the Critical Warnings section above.**

**If ANY validation query fails:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results
- **Report** - Ask for guidance on data cleanup strategy
- **Clean** - Implement chosen remediation strategy
- **Re-validate** - Run all queries again

**Success Criteria for Task 2:**
- [ ] All created_by orphan queries return 0 rows
- [ ] All updated_by orphan queries return 0 rows
- [ ] Validation results documented
- [ ] Ready to proceed with migration

---

### Task 3: Migration Creation & Application

**Effort:** 1 day
**Dependencies:** Task 1 (models) and Task 2 (validation) must be complete
**Migration:** 3 of 9

#### What This Task Accomplishes

Generate and apply Alembic migration with FK constraints for all tables in Task 3.

#### Implementation Steps

**Step 1: Generate Migration Skeleton**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_1_task_3_fk_audit_job"
```

**Step 2: Manually Construct Complete Migration**

Use the migration pattern from Requirements section above.

**Step 3: Apply Migration**
```bash
alembic upgrade head
```

**Step 4: Verify Database State**
```sql
-- Verify FK constraints exist for Task 3 tables
SELECT 
    tc.table_name,
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
  AND tc.table_name IN (
    'job', 'job_status', 'job_assignment', 'job_notes', 'job_attachment',
    'job_expense', 'job_expense_category', 'job_time_entry',
    'change_order', 'change_order_line', 'change_order_attachment',
    'change_order_line_tax_component'
  )
  AND kcu.column_name IN ('created_by', 'updated_by')
  AND ccu.table_name = 'user'
ORDER BY tc.table_name, kcu.column_name;
-- Expected: 32 rows (11 tables × 2 FKs + 1 table × 1 FK = 23 FKs)
```

**Step 5: Test Migration Rollback**
```bash
alembic downgrade -1
# Verify FK constraints removed
alembic upgrade head
```

**Success Criteria for Task 3:**
- [ ] Migration created with all FK constraints
- [ ] Migration applies successfully
- [ ] All verification queries pass
- [ ] Migration rolls back successfully
- [ ] Migration re-applies successfully

---

### Task 4: Comprehensive Testing

**Effort:** 1 day
**Dependencies:** Task 3 must be complete

#### What This Task Accomplishes

Validate that all Phase 6.0.1 Task 3 FK constraints work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_1_task_3_audit_fk.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0.1 Task 3 - Job Management Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: phase-6.0-db-schema-sync-11-plan.md - Task 3
"""
import pytest
from sqlalchemy.exc import IntegrityError
import uuid


class TestAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""
    
    def test_job_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        from app.models.fulfillment import Job
        
        invalid_user_id = uuid.uuid4()
        job = Job(
            tenant_id=test_tenant.id,
            job_number="TEST-001",
            created_by=invalid_user_id
        )
        db_session.add(job)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_job_created_by" in str(exc_info.value)
        db_session.rollback()
    
    def test_job_valid_created_by_accepted(self, db_session, test_tenant, test_user):
        """Test that valid created_by user ID is accepted"""
        from app.models.fulfillment import Job
        
        job = Job(
            tenant_id=test_tenant.id,
            job_number="TEST-001",
            created_by=test_user.id
        )
        db_session.add(job)
        db_session.commit()
        
        assert job.created_by == test_user.id


class TestAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""
    
    def test_job_updated_by_fk_enforcement(self, db_session, test_tenant, test_user):
        """Test that invalid updated_by user ID is rejected"""
        from app.models.fulfillment import Job
        
        job = Job(
            tenant_id=test_tenant.id,
            job_number="TEST-001",
            created_by=test_user.id
        )
        db_session.add(job)
        db_session.commit()
        
        invalid_user_id = uuid.uuid4()
        job.updated_by = invalid_user_id
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_job_updated_by" in str(exc_info.value)
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""
    
    def test_user_deletion_blocked_by_job_audit(self, db_session, test_tenant, test_user):
        """Test ON DELETE RESTRICT behavior"""
        from app.models.fulfillment import Job
        
        job = Job(
            tenant_id=test_tenant.id,
            job_number="TEST-001",
            created_by=test_user.id
        )
        db_session.add(job)
        db_session.commit()
        
        db_session.delete(test_user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_job_created_by" in str(exc_info.value)
        db_session.rollback()


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""
    
    def test_job_null_audit_columns(self, db_session, test_tenant):
        """Test that NULL created_by and updated_by are allowed"""
        from app.models.fulfillment import Job
        
        job = Job(
            tenant_id=test_tenant.id,
            job_number="TEST-001",
            created_by=None,
            updated_by=None
        )
        db_session.add(job)
        db_session.commit()
        
        assert job.created_by is None
        assert job.updated_by is None


class TestAppendOnlyTables:
    """Test append-only tables (created_by only)"""
    
    def test_change_order_line_tax_component_created_by_only(self, db_session, test_tenant, test_user):
        """Test that append-only table only has created_by FK"""
        from app.models.quoting import ChangeOrderLineTaxComponent
        
        # This test verifies the FK exists and works
        # Note: Actual test would need proper setup of parent change_order_line
        pass
```

**Success Criteria for Task 4:**
- [ ] Test file created with all test categories
- [ ] FK enforcement tests prevent invalid user IDs
- [ ] User deletion prevention tests work correctly
- [ ] NULL audit column tests verify backward compatibility
- [ ] Full test suite passes: 770+/770+ total tests (100%)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 754+ passed (754 baseline + new tests for Task 3)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 770+ passed (754 baseline + ~16 new tests for Task 3)
```

### Step 2: Verify Database State

Run all verification queries from Task 3 to confirm FK constraints exist and match expectations.

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check migration was applied successfully
3. Verify FK constraint definitions in database
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md`

Add implementation status:

```markdown
### Phase 6.0.1 Task 3: Job Management FK Constraints - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_HOURS] hours (actual)
**Priority:** HIGH

**Implementation Summary:**

- Model Verification: Updated 19 tables in 2 model files (fulfillment.py, quoting.py)
- Data Validation: All pre-migration orphan detection queries passed (0 orphaned references)
- Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_1_task_3_fk_audit_job.py`]
- Test Suite: [`test_phase_6_0_1_task_3_audit_fk.py`] - [N] tests ✅
- Final Results: [NEW_TOTAL]/[NEW_TOTAL] total tests (100%)

**Key Changes:**
- ✅ 32 Foreign Key constraints added (13 tables × 2 + 6 tables × 1)
- ✅ All FKs use ON DELETE RESTRICT behavior
- ✅ Zero orphaned audit references found
- ✅ User deletion workflow validated
- ✅ Zero regressions in existing test suite

**Baseline:** 754 total tests → **New:** [NEW_TOTAL] total tests (+[DIFF])
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Phase 6.0.1 Task 3:
- [ ] **Regression baseline captured** (754/754 total)
- [ ] **All orphaned audit reference queries returned 0 rows**
- [ ] **All 19 tables verified in Python models**
- [ ] **All FKs use string reference `"user.id"`**
- [ ] **All FKs specify `ondelete='RESTRICT'`**
- [ ] **All audit columns remain `Optional[uuid.UUID]`**
- [ ] **Alembic migration created for Task 3**
- [ ] **Migration applied successfully**
- [ ] **All database verification queries passed**
- [ ] **Comprehensive tests written and passing**
- [ ] **ALL 754 existing tests still passing**
- [ ] **New total: 770+/770+ tests (100%)**
- [ ] **Migration rollback tested**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **FK Requirements Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models (2 files affected in Task 3)
- `backend/app/models/fulfillment.py` - 8 tables
- `backend/app/models/quoting.py` - 4 tables

### Model Location References
- `backend/db_models_map.md` - Model to file mapping
- `backend/app_model_imports.md` - Import patterns

---

## Risk Assessment

**For Phase 6.0.1 Task 3:**
- **Orphaned Reference Risk:** MEDIUM (orphaned audit references would prevent FK creation - validated before migration)
- **Circular Dependency Risk:** LOW (string-based FK references prevent Python circular imports)
- **User Deletion Impact:** MEDIUM (ON DELETE RESTRICT changes operational workflow)
- **Migration Complexity:** LOW (standard FK constraint operations)
- **Application Impact:** LOW (additive changes, improves data integrity without breaking changes)
- **Rollback Complexity:** LOW (single independent migration, surgical rollback)
- **Performance Impact:** MINIMAL (FK constraints add negligible overhead)
- **Mitigation:** Comprehensive pre-migration validation, extensive testing, documented user deletion workflow

---

## Notes

### Important Patterns to Follow
- **Nine Migrations:** One per functional domain (Tasks 1-9)
- **Zero Orphans:** Pre-migration validation MUST show 0 orphaned audit references
- **String References:** Always use `foreign_key="user.id"` not class reference
- **ON DELETE RESTRICT:** Mandatory for all audit FK constraints
- **NULL Support:** All audit columns must remain `Optional[uuid.UUID]`
- **Zero Regression:** All 754 tests MUST pass

### Phase 6.0.1 Specific
- **203 FK Constraints Total:** 87 tables × 2 + 29 tables × 1 across all 9 tasks
- **Task 3 Scope:** 32 FK constraints across 19 Job Management tables
- **User Deletion:** Requires soft-delete workflow (document in ops manual)
- **Audit Integrity:** Database-level enforcement prevents audit trail corruption
- **Compliance:** Supports SOC 2, GDPR audit trail requirements

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 6.0.1 plan for detailed specifications
- Verify all pre-migration orphan detection queries passed
- Check that correct task number migration is being created
- Verify FK definitions use string reference and `ondelete='RESTRICT'`
- Use model mapping files to find correct import paths
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Phase 6.0.1 Task 3 Checklist:
1. ✅ Capture baseline (754/754 total)
2. 🔍 **Verify all 19 table FK definitions in Python models**
3. 📚 **Reference db_models_map.md and app_model_imports.md for model locations**
4. ✅ Verify Python syntax (`python -c "from app.models import *"`)
5. ⚠️ **CRITICAL: Run orphaned created_by queries (all 19 tables)**
6. ⚠️ **CRITICAL: Run orphaned updated_by queries (13 tables with updated_by)**
7. ⚠️ **MANDATORY: Stop if ANY orphaned references found**
8. 🔧 **Create Migration: FK constraints for job management tables**
9. ✅ Apply Migration, verify FK constraints created (32 expected)
10. 🧪 **Create comprehensive test suite (FK enforcement + user deletion + NULL support)**
11. 🔄 Run regression tests (770+/770+ expected)
12. ↩️ Test migration rollback
13. 📚 Update project plan

Remember: Phase 6.0.1 brings database-level audit trail integrity, preventing orphaned references and ensuring compliance with SOC 2 and GDPR requirements. Validate thoroughly before migration, test extensively, and ensure zero regressions!
