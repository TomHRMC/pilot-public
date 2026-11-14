# Task [TASK_NUMBER]: [TASK_NAME] - Audit FK Constraints

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - Task [TASK_NUMBER]
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **Audit FK Constraints Analysis** ⭐
- Current Live Database (Phase 6.0 Post-State)
**Type:** Phase 6.0.1 - Foreign Key Constraints for Audit Columns
**Priority:** HIGH
**Change Type:** FOREIGN KEY CONSTRAINTS + MODEL UPDATES + TESTING

---

## Context

This is **Phase 6.0.1 - DB Sync v#11**, the final audit integrity synchronization addressing **Foreign Key constraint enforcement** for all `created_by` and `updated_by` audit trail columns.

**Root Cause:** 
- The JSON master blueprint specifies that ALL `created_by` and `updated_by` tracking columns should have explicit Foreign Key constraints referencing `user.id`
- Currently, these columns exist physically and application code populates them correctly
- **But**: No database-level referential integrity enforcement exists

**Critical Impact:**
- **Data Integrity Vulnerability:** Invalid user IDs can be inserted into audit columns
- **Orphaned Audit Records:** If users are deleted, audit trail breaks
- **Broken Audit Trail:** Cannot reliably trace actions back to users
- **Compliance Violations:** SOC 2, GDPR audit requirements compromised

**Scope:** **9 separate migrations** (Tasks 1-9) - **203 Foreign Key constraints** across **116 tables**:
- **87 tables**: Both `created_by` AND `updated_by` Foreign Keys (174 FKs)
- **29 tables**: Only `created_by` Foreign Key (29 FKs)

**Key Principle:** Phase 6.0.1 uses **9 separate Alembic migrations** (one per functional domain) for surgical rollback capability, optimized task sizing (~15-20 tables per task), and keeping AI agent context usage at 50-60%.

---

## What Was Completed in Previous Phases

**Phase 6.0 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 14 multi-tenant unique constraints + 5 business logic constraints
- ✅ 2 audit columns added (conversation_session: created_by, updated_by)
- ✅ 5 partial indexes + 1 GiST exclusion constraint
- ✅ 14 composite/sorting indexes + 1 redundant index removed
- ✅ 706/706 unit tests, 733/733 total tests passing (100%)

**Current Baseline:** 706/706 unit tests, 733/733 total tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement
- **Phase 5.1:** ✅ COMPLETE - Missing unique constraints & foreign keys
- **Phase 5.2:** ✅ COMPLETE - Exclusion constraints & critical indexes
- **Phase 5.3:** ✅ COMPLETE - Notification schema + idempotency + index standardization + triggers
- **Phase 6.0:** ✅ COMPLETE - Advanced constraints & performance indexes

**See:**
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` for Phase 6.0 history
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` for comprehensive FK requirements

---

## Current Task: [TASK_NAME]

**Effort:** [EFFORT_ESTIMATE]
**Gap Reference:** Phase 6.0.1 Analysis - Audit Trail Foreign Key Constraints
**Change Type:** [MODEL VERIFICATION | MIGRATION + DATA VALIDATION | TESTING]

[TASK_DESCRIPTION - 2-3 sentences explaining what this task accomplishes and WHY it matters]

### What Needs to Be Fixed

[TASK_SPECIFIC_TABLE - List tables, model files, and FK requirements for this specific task]

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

**Record the output of both results:** `706/706 & 733/733 tests passing` (Phase 6.0.1 baseline - starting from Phase 6.0 completion)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

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
-- Template for checking orphaned created_by references
SELECT '[TABLE_NAME]' as table_name, created_by, COUNT(*) as count
FROM [table_name]
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = [table_name].created_by)
GROUP BY created_by;
-- Expected: 0 rows (no orphaned references)

-- Template for checking orphaned updated_by references (ONLY for tables with updated_by)
SELECT '[TABLE_NAME]' as table_name, updated_by, COUNT(*) as count
FROM [table_name]
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = [table_name].updated_by)
GROUP BY updated_by;
-- Expected: 0 rows (no orphaned references)
```

**Example for Multiple Tables:**
```sql
-- Check all tables in Task 1 for orphaned created_by
SELECT 'address_type' as table_name, created_by, COUNT(*) as count
FROM address_type
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = address_type.created_by)
GROUP BY created_by
UNION ALL
SELECT 'contact_type', created_by, COUNT(*)
FROM contact_type
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = contact_type.created_by)
GROUP BY created_by
UNION ALL
-- ... (repeat for ALL tables in task)
;
-- Expected: 0 rows total
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

**Alternative Behaviors (NOT USED in Phase 6.0.1):**
- ❌ `SET NULL`: Would break audit trail (lose attribution of who created/updated)
- ❌ `CASCADE`: Would cascade delete audit records (massive data loss)
- ✅ `RESTRICT`: Prevents deletion (chosen approach)

**Impact on Application:**
- Users with audit trail references **CANNOT** be hard-deleted
- Requires soft-delete workflow: `user.deleted_at = now()`, `user.is_active = False`
- Document user deletion procedure in operational manual

---

### 3. Circular Dependency Handling for User Table

**CRITICAL:** The `user` table itself has `created_by` and `updated_by` columns that reference `user.id`.

**The Problem:**
```python
# ❌ WRONG - Creates circular dependency
class User(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True)
    created_by: Optional[uuid.UUID] = Field(foreign_key=User.id)  # Circular!
```

**The Solution:**
```python
# ✅ CORRECT - Use string reference
class User(SQLModel, table=True):
    id: uuid.UUID = Field(primary_key=True)
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",  # ← String reference, not User.id
        sa_column_kwargs={"ondelete": "RESTRICT"}
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",  # ← String reference
        sa_column_kwargs={"ondelete": "RESTRICT"}
    )
```

**Why This Works:**
- String-based FK references are resolved at metadata creation time
- Allows self-referential foreign keys
- Prevents Python import/initialization circular dependency errors

---

### 4. NULL Support for Backward Compatibility

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

**Incorrect Pattern:**
```python
# ❌ WRONG - Forces NOT NULL (breaks existing records)
created_by: uuid.UUID = Field(  # Not Optional
    foreign_key="user.id"
)
```

**Future Phase Consideration:**
- After backfilling NULL values with system user ID
- Consider adding `NOT NULL` constraints in future phase
- **NOT** in Phase 6.0.1 scope

---

### 5. Nine-Task Migration Strategy

**MANDATORY:** Phase 6.0.1 uses **9 separate Alembic migrations** for surgical rollback and context optimization:

**Task Sizing Rationale:**
- Each task limited to ~15-21 tables
- Keeps AI agent context usage at 50-60% (optimal)
- Functional domain grouping for logical organization
- Independent rollback capability per task

**Task Breakdown:**

| Task | Domain | Tables | Both FKs | Created Only | Total FKs |
|------|--------|--------|----------|--------------|-----------|
| **Task 1** | Common & Reference | 20 | 19 | 1 | 39 FKs |
| **Task 2** | Customer & Site | 15 | 14 | 1 | 29 FKs |
| **Task 3** | Job Management | 19 | 13 | 6 | 32 FKs |
| **Task 4** | Quoting System | 18 | 8 | 10 | 26 FKs |
| **Task 5** | Billing & Payments | 18 | 12 | 6 | 30 FKs |
| **Task 6** | Tenant & User | 21 | 16 | 5 | 37 FKs |
| **Task 7** | Integration & Sync | 10 | 7 | 3 | 17 FKs |
| **Task 8** | Supplier & Catalog | 19 | 11 | 8 | 30 FKs |
| **Task 9** | Auth & Subscription | 16 | 9 | 7 | 25 FKs |

**Why Separate Migrations:**
- Atomic rollback capability per domain
- Risk isolation (high-traffic tables separate from low-traffic)
- Easier troubleshooting if migration fails
- Clear task boundaries for AI agents
- Prevents context window overflow

---

### 6. SQLModel Foreign Key Syntax

**CRITICAL:** Use the correct SQLModel/SQLAlchemy pattern for foreign keys.

**Correct Syntax (SQLModel Field):**
```python
from typing import Optional
import uuid
from sqlmodel import Field, SQLModel

class AddressType(SQLModel, table=True):
    __tablename__ = "address_type"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    code: str
    name: str
    
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

**Incorrect Patterns:**
```python
# ❌ WRONG - Missing ondelete behavior
created_by: Optional[uuid.UUID] = Field(
    default=None,
    foreign_key="user.id"
    # Missing sa_column_kwargs!
)

# ❌ WRONG - Using class reference instead of string
from app.models.tenant import User
created_by: Optional[uuid.UUID] = Field(
    foreign_key=User.id  # Circular dependency if User has audit columns!
)

# ❌ WRONG - Not Optional (breaks NULL support)
created_by: uuid.UUID = Field(
    foreign_key="user.id"  # Should be Optional[uuid.UUID]
)
```

---

### 7. Alembic Migration Pattern for FK Constraints

**CRITICAL:** Use the correct Alembic operation for foreign key creation.

**Correct Migration Pattern:**
```python
"""Phase 6.0.1 Task X: FK constraints for [DOMAIN] tables

Revision ID: phase_6_0_1_task_X_fk_audit_[domain]
Revises: [PREVIOUS_REVISION]
Create Date: 2026-04-13
"""

def upgrade():
    # For tables with BOTH created_by and updated_by
    for table_name in [
        'address_type', 'contact_type', 'entity_type', 'currency'
        # ... (list all tables with both FKs)
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
    for table_name in ['notification_event', 'jwk_status']:
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
    for table_name in ['notification_event', 'jwk_status']:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'address_type', 'contact_type', 'entity_type', 'currency'
        # ... (same list as upgrade)
    ]:
        op.drop_constraint(f'fk_{table_name}_updated_by', table_name, type_='foreignkey')
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
```

**Key Points:**
- Use `op.create_foreign_key()` for creation
- Use `op.drop_constraint()` with `type_='foreignkey'` for rollback
- FK naming convention: `fk_{table_name}_{column_name}`
- **MUST** specify `ondelete='RESTRICT'`
- Downgrade must drop in reverse order

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

def test_created_by_fk_enforcement(db_session, test_tenant):
    """Test that invalid created_by user ID is rejected"""
    from app.models.common import AddressType
    
    # Attempt to create record with non-existent user ID
    invalid_user_id = uuid.uuid4()
    address_type = AddressType(
        tenant_id=test_tenant.id,
        code="TEST",
        name="Test",
        created_by=invalid_user_id  # Invalid user ID
    )
    db_session.add(address_type)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_address_type_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing User Deletion Prevention:**
```python
def test_user_deletion_prevented_by_audit_trail(db_session, test_user, test_tenant):
    """Test that user cannot be deleted if audit references exist"""
    from app.models.common import AddressType
    
    # Create record with user audit reference
    address_type = AddressType(
        tenant_id=test_tenant.id,
        code="TEST",
        name="Test",
        created_by=test_user.id
    )
    db_session.add(address_type)
    db_session.commit()
    
    # Attempt to delete user (should fail due to RESTRICT)
    db_session.delete(test_user)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_address_type_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing NULL Audit Columns (Backward Compatibility):**
```python
def test_null_audit_columns_allowed(db_session, test_tenant):
    """Test that NULL audit columns are allowed for backward compatibility"""
    from app.models.common import AddressType
    
    # Create record with NULL audit columns
    address_type = AddressType(
        tenant_id=test_tenant.id,
        code="TEST",
        name="Test",
        created_by=None,  # NULL allowed
        updated_by=None
    )
    db_session.add(address_type)
    db_session.commit()  # Should succeed
    
    assert address_type.created_by is None
    assert address_type.updated_by is None
```

---

## Requirements

### Phase 6.0.1 Task Breakdown

Phase 6.0.1 is divided into **9 separate Alembic migrations** for domain isolation and context optimization:

#### Task [X]: [DOMAIN_NAME] FK Constraints (Migration [X])

**Scope:**
- [Y] tables total
- [Z] tables with BOTH `created_by` AND `updated_by` FKs
- [W] tables with ONLY `created_by` FK (append-only)

**Tables in This Task:**
[LIST_SPECIFIC_TABLES - Customize per task]

**Migration Pattern:**
```python
"""Phase 6.0.1 Task [X]: FK constraints for [DOMAIN] audit columns

Revision ID: phase_6_0_1_task_[X]_fk_audit_[domain]
Revises: [PREVIOUS_REVISION]
Create Date: 2026-04-13
"""

def upgrade():
    # Add FK constraints for tables with both created_by and updated_by
    for table_name in [
        # [LIST_TABLES_WITH_BOTH_FKS]
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
    for table_name in [
        # [LIST_TABLES_WITH_CREATED_ONLY]
    ]:
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
    for table_name in [
        # [LIST_TABLES_WITH_CREATED_ONLY]
    ]:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        # [LIST_TABLES_WITH_BOTH_FKS]
    ]:
        op.drop_constraint(f'fk_{table_name}_updated_by', table_name, type_='foreignkey')
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
```

---

### Task 1: SQLModel Schema Definitions Verification

**Effort:** 0.5-1 day
**Scope:** Verify FK definitions across tables in this task

#### What This Task Accomplishes

Confirm that all Phase 6.0.1 Task [X] changes are correctly defined in the Python SQLModel definitions. Update models with FK constraints on audit columns.

#### Tables to Check (Task [X])

**Model Files & Required Changes:**

[CUSTOMIZE_PER_TASK - List model files and specific FK requirements]

Example:
1. `backend/app/models/common.py`
   - `AddressType`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `ContactType`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `EntityType`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`

#### SQLModel Syntax Examples

[See "SQLModel Foreign Key Syntax" section above for complete examples]

**Success Criteria for Task 1:**
- [ ] All tables in this task have FK definitions added
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

Verify that the database is ready for Phase 6.0.1 Task [X] migration by checking for orphaned audit references that would prevent FK constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation: Orphaned Audit References (MANDATORY)**

```sql
-- Check for orphaned created_by references in Task [X] tables
[CUSTOMIZE_PER_TASK - Create UNION ALL query for all tables]

Example:
SELECT 'address_type' as table_name, created_by, COUNT(*) as count
FROM address_type
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = address_type.created_by)
GROUP BY created_by
UNION ALL
SELECT 'contact_type', created_by, COUNT(*)
FROM contact_type
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = contact_type.created_by)
GROUP BY created_by
UNION ALL
-- ... (repeat for ALL tables in this task)
;
-- Expected: 0 rows (no orphaned references)

-- Check for orphaned updated_by references (only for tables with updated_by)
[Similar pattern for updated_by column]
```

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
**Migration:** [X] of 9

#### What This Task Accomplishes

Generate and apply Alembic migration with FK constraints for all tables in this task.

#### Implementation Steps

**Step 1: Generate Migration Skeleton**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_1_task_[X]_fk_audit_[domain]"
```

**Step 2: Manually Construct Complete Migration**

Use the migration pattern from Requirements section above.

**Step 3: Apply Migration**
```bash
alembic upgrade head
```

**Step 4: Verify Database State**
```sql
-- Verify FK constraints exist for this task
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
    -- [LIST_ALL_TABLES_IN_THIS_TASK]
  )
  AND kcu.column_name IN ('created_by', 'updated_by')
  AND ccu.table_name = 'user'
ORDER BY tc.table_name, kcu.column_name;
-- Expected: [EXPECTED_FK_COUNT] rows
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

Validate that all Phase 6.0.1 Task [X] FK constraints work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_1_task_[X]_audit_fk.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0.1 Task [X] - [DOMAIN] Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: phase-6.0-db-schema-sync-11-plan.md - Task [X]
"""
import pytest
from sqlalchemy.exc import IntegrityError
import uuid


class TestAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""
    
    def test_[table_name]_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        # [See example in Critical Warnings section above]
    
    def test_[table_name]_valid_created_by_accepted(self, db_session, test_tenant, test_user):
        """Test that valid created_by user ID is accepted"""
        # Create record with valid user ID
        # Verify successful commit


class TestAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""
    
    def test_[table_name]_updated_by_fk_enforcement(self, db_session, test_tenant, test_user):
        """Test that invalid updated_by user ID is rejected"""
        # Similar to created_by but for updated_by


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""
    
    def test_user_deletion_blocked_by_[table_name]_audit(self, db_session, test_tenant, test_user):
        """Test ON DELETE RESTRICT behavior"""
        # [See example in Critical Warnings section above]


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""
    
    def test_[table_name]_null_audit_columns(self, db_session, test_tenant):
        """Test that NULL created_by and updated_by are allowed"""
        # [See example in Critical Warnings section above]
```

**Success Criteria for Task 4:**
- [ ] Test file created with all test categories
- [ ] FK enforcement tests prevent invalid user IDs
- [ ] User deletion prevention tests work correctly
- [ ] NULL audit column tests verify backward compatibility
- [ ] Full test suite passes: [NEW_UNIT_COUNT]/[NEW_UNIT_COUNT] unit tests, [NEW_TOTAL_COUNT]/[NEW_TOTAL_COUNT] total (100%)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [NEW_COUNT]+ passed (706 baseline + new tests for this task)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [NEW_COUNT]+ passed (733 baseline + new tests for this task)
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
### Phase 6.0.1 Task [X]: [DOMAIN_NAME] FK Constraints - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_DAYS] days (actual)
**Priority:** HIGH

**Implementation Summary:**

- Model Verification: Updated [Y] tables in [Z] model files
- Data Validation: All pre-migration orphan detection queries passed (0 orphaned references)
- Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_1_task_[X]_fk_audit_[domain].py`]
- Test Suite: [`test_phase_6_0_1_task_[X]_audit_fk.py`] - [N] tests ✅
- Final Results: [NEW_UNIT]/[NEW_UNIT] unit tests (100%), [NEW_TOTAL]/[NEW_TOTAL] total tests (100%)

**Key Changes:**
- ✅ [FK_COUNT] Foreign Key constraints added ([BOTH_COUNT] tables × 2 + [CREATED_COUNT] tables × 1)
- ✅ All FKs use ON DELETE RESTRICT behavior
- ✅ Zero orphaned audit references found
- ✅ User deletion workflow validated
- ✅ Zero regressions in existing test suite

**Baseline:** [PREV_UNIT] unit tests, [PREV_TOTAL] total tests → **New:** [NEW_UNIT] unit tests (+[DIFF]), [NEW_TOTAL] total tests (+[DIFF])
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Phase 6.0.1 Task [X]:
- [ ] **Regression baseline captured** (706/706 unit, 733/733 total)
- [ ] **All orphaned audit reference queries returned 0 rows**
- [ ] **All [Y] tables verified in Python models**
- [ ] **All FKs use string reference `"user.id"`**
- [ ] **All FKs specify `ondelete='RESTRICT'`**
- [ ] **All audit columns remain `Optional[uuid.UUID]`**
- [ ] **Alembic migration created for this task**
- [ ] **Migration applied successfully**
- [ ] **All database verification queries passed**
- [ ] **Comprehensive tests written and passing**
- [ ] **ALL 706 existing unit tests still passing**
- [ ] **ALL 733 total tests still passing**
- [ ] **New total: [NEW_UNIT]+/[NEW_UNIT]+ unit, [NEW_TOTAL]+/[NEW_TOTAL]+ total (100%)**
- [ ] **Migration rollback tested**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **FK Requirements Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models ([Y] tables in this task)
[CUSTOMIZE_PER_TASK - List specific model files]

Example:
- `backend/app/models/common.py` - [N] tables
- `backend/app/models/notification.py` - [N] tables
- `backend/app/models/auth.py` - [N] tables

---

## Risk Assessment

**For Phase 6.0.1 Task [X]:**
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
- **Zero Regression:** All 706 unit + 733 total tests MUST pass

### Phase 6.0.1 Specific
- **203 FK Constraints:** 87 tables × 2 + 29 tables × 1
- **9 Migrations:** Domain-grouped for context optimization
- **User Deletion:** Requires soft-delete workflow (document in ops manual)
- **Audit Integrity:** Database-level enforcement prevents audit trail corruption
- **Compliance:** Supports SOC 2, GDPR audit trail requirements

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 6.0.1 plan for detailed specifications
- Verify all pre-migration orphan detection queries passed
- Check that correct task number migration is being created
- Verify FK definitions use string reference and `ondelete='RESTRICT'`
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Phase 6.0.1 Task [X] Checklist:
1. ✅ Capture baseline (706/706 unit, 733/733 total)
2. 🔍 **Verify all [Y] table FK definitions in Python models**
3. ✅ Verify Python syntax (`python -c "from app.models import *"`)
4. ⚠️ **CRITICAL: Run orphaned created_by queries (all tables in task)**
5. ⚠️ **CRITICAL: Run orphaned updated_by queries (tables with updated_by)**
6. ⚠️ **MANDATORY: Stop if ANY orphaned references found**
7. 🔧 **Create Migration: FK constraints for [DOMAIN] tables**
8. ✅ Apply Migration, verify FK constraints created
9. 🧪 **Create comprehensive test suite (FK enforcement + user deletion + NULL support)**
10. 🔄 Run regression tests ([NEW_COUNT]+/[NEW_COUNT]+ expected)
11. ↩️ Test migration rollback
12. 📚 Update project plan

Remember: Phase 6.0.1 brings database-level audit trail integrity, preventing orphaned references and ensuring compliance with SOC 2 and GDPR requirements. Validate thoroughly before migration, test extensively, and ensure zero regressions!
