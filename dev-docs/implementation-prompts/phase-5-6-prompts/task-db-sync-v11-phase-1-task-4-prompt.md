# Task 4: Quoting System - Audit FK Constraints

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - Task 4
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **Audit FK Constraints Analysis** ⭐
- Current Live Database (Phase 6.0 Post-State)
**Model Reference Files:**
- `backend/db_models_map.md` - Model file location mapping ⭐
- `backend/app_model_imports.md` - Correct import patterns ⭐
**Type:** Phase 6.0.1 - Foreign Key Constraints for Audit Columns
**Priority:** HIGH
**Change Type:** FOREIGN KEY CONSTRAINTS + MODEL UPDATES + TESTING

---

## Context

This is **Phase 6.0.1 - DB Sync v#11, Task 4**, the fourth audit integrity synchronization task addressing **Foreign Key constraint enforcement** for all `created_by` and `updated_by` audit trail columns in the **Quoting System domain**.

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

**Phase 6.0.1 Task 1 Status:** ✅ COMPLETE (2026-04-13)
- ✅ 39 FK constraints added (20 tables: Common & Reference domain)
- ✅ Migration: `2026_04_13_1730-55be0a40204a_phase_6_0_1_task_1_fk_audit_common.py`
- ✅ Test Results: 738/738 tests passing (100%)

**Phase 6.0.1 Task 2 Status:** ✅ COMPLETE (2026-04-13)
- ✅ 23 FK constraints added (12 tables: Customer & Site domain)
- ✅ Migration: `2026_04_13_1822-a098b620e104_phase_6_0_1_task_2_fk_audit_customer.py`
- ✅ Test Results: 754/754 tests passing (100%)

**Phase 6.0.1 Task 3 Status:** ✅ COMPLETE (2026-04-13)
- ✅ 23 FK constraints added (12 tables: Job Management domain)
- ✅ Migration: `2026_04_13_1901-ec96305d27ec_phase_6_0_1_task_3_fk_audit_job.py`
- ✅ Test Results: 768/768 tests passing (100%)

**Current Baseline:** 768/768 tests passing (100%)

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

## Current Task: Quoting System FK Constraints

**Effort:** 3-4 hours (estimated)
**Gap Reference:** Phase 6.0.1 Analysis - Audit Trail Foreign Key Constraints (Quoting Domain)
**Change Type:** MODEL VERIFICATION + MIGRATION + DATA VALIDATION + TESTING

This task adds Foreign Key constraints to all quoting-related tables to enforce referential integrity on audit trail columns. The quoting system includes quote creation, versioning, public link sharing, and customer acceptance workflows - all requiring auditable user attribution.

### What Needs to Be Fixed

**Scope:** 18 tables in the Quoting System domain requiring FK constraints on audit columns
- **8 tables**: Both `created_by` AND `updated_by` FKs (16 constraints)
- **10 tables**: Only `created_by` FK (10 constraints) - append-only/versioned tables
- **Total**: 26 Foreign Key constraints

**Model File Updated:**
- `backend/app/models/quoting.py` - All quoting domain tables

**Tables Requiring Both FKs (8 tables - 16 constraints):**
1. **`quote`** - Core quote entity with full audit trail
2. **`quote_status`** - Quote status lookup table
3. **`quote_link_status`** - Quote link status lookup table
4. **`quote_message`** - Quote conversation/messaging (multi-tenant communication)
5. **`quote_public_link`** - Public quote link configuration
6. **`pricebook_item`** - Catalog pricing items (referenced by quotes)
7. **Additional tables** - Verify against `phase-6.0-db-schema-sync-11-analysis.md`

**Tables Requiring Created-Only FK (10 tables - 10 constraints - Append-Only/Versioned):**
1. **`quote_line`** - Quote line items (versioned, immutable after creation)
2. **`quote_version`** - Quote version history (append-only)
3. **`quote_acceptance`** - Quote acceptance log (append-only event)
4. **`quote_public_link_contact_action`** - Public link tracking (append-only analytics)
5. **`quote_line_tax_component`** - Tax breakdown (immutable calculation)
6. **`pricebook_item_version`** - Pricebook version history (append-only)
7. **Additional tables** - Verify against `phase-6.0-db-schema-sync-11-analysis.md`

**⚠️ IMPORTANT:** The plan document lists 18 tables but only explicitly details 10-12. You MUST:
1. Review `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` for the complete Task 4 table list
2. Cross-reference `backend/db_models_map.md` to identify all tables in `quoting.py`
3. Exclude tables already handled in Tasks 1-3 (e.g., `change_order*` tables are in Task 3)
4. Verify the final count matches: 8 tables with both FKs + 10 tables with created_by only = 18 total

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

**Record the output of both results:** `768/768 tests passing` (Phase 6.0.1 Task 3 baseline)

### Step 3: Document Your Baseline

**Write down this number before proceeding: 768/768 tests passing**

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

**Validation Queries (MANDATORY for ALL tables in Task 4):**

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

**Example for Task 4 Tables:**
```sql
-- Check all tables in Task 4 for orphaned created_by
SELECT 'quote' as table_name, created_by, COUNT(*) as count
FROM quote
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_status', created_by, COUNT(*)
FROM quote_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_link_status', created_by, COUNT(*)
FROM quote_link_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_link_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_message', created_by, COUNT(*)
FROM quote_message
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_message.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_public_link', created_by, COUNT(*)
FROM quote_public_link
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_public_link.created_by)
GROUP BY created_by
UNION ALL
-- Add ALL remaining Task 4 tables here
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
| **Task 1** | Common & Reference | 20 | 19 | 1 | 39 FKs ✅ |
| **Task 2** | Customer & Site | 12 | 11 | 1 | 23 FKs ✅ |
| **Task 3** | Job Management | 12 | 11 | 1 | 23 FKs ✅ |
| **Task 4** | Quoting System | 18 | 8 | 10 | 26 FKs ← YOU ARE HERE |
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

class Quote(SQLModel, table=True):
    __tablename__ = "quote"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    customer_id: uuid.UUID = Field(foreign_key="customer.id")
    
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
from app.models.core import User
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
"""Phase 6.0.1 Task 4: FK constraints for Quoting System tables

Revision ID: phase_6_0_1_task_4_fk_audit_quoting
Revises: phase_6_0_1_task_3_fk_audit_job
Create Date: 2026-04-13
"""

def upgrade():
    # For tables with BOTH created_by and updated_by
    for table_name in [
        'quote', 'quote_status', 'quote_link_status', 'quote_message',
        'quote_public_link', 'pricebook_item'
        # ... (list all tables with both FKs - verify count = 8)
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
    for table_name in [
        'quote_line', 'quote_version', 'quote_acceptance',
        'quote_public_link_contact_action', 'quote_line_tax_component',
        'pricebook_item_version'
        # ... (list all tables with created_by only - verify count = 10)
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
        'quote_line', 'quote_version', 'quote_acceptance',
        'quote_public_link_contact_action', 'quote_line_tax_component',
        'pricebook_item_version'
        # ... (same list as upgrade - created_by only)
    ]:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'quote', 'quote_status', 'quote_link_status', 'quote_message',
        'quote_public_link', 'pricebook_item'
        # ... (same list as upgrade - both FKs)
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
    from app.models.quoting import Quote
    
    # Attempt to create record with non-existent user ID
    invalid_user_id = uuid.uuid4()
    quote = Quote(
        tenant_id=test_tenant.id,
        customer_id=uuid.uuid4(),  # Assuming valid customer
        created_by=invalid_user_id  # Invalid user ID
    )
    db_session.add(quote)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_quote_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing User Deletion Prevention:**
```python
def test_user_deletion_prevented_by_audit_trail(db_session, test_user, test_tenant):
    """Test that user cannot be deleted if audit references exist"""
    from app.models.quoting import Quote
    
    # Create record with user audit reference
    quote = Quote(
        tenant_id=test_tenant.id,
        customer_id=uuid.uuid4(),
        created_by=test_user.id
    )
    db_session.add(quote)
    db_session.commit()
    
    # Attempt to delete user (should fail due to RESTRICT)
    db_session.delete(test_user)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_quote_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing NULL Audit Columns (Backward Compatibility):**
```python
def test_null_audit_columns_allowed(db_session, test_tenant):
    """Test that NULL audit columns are allowed for backward compatibility"""
    from app.models.quoting import Quote
    
    # Create record with NULL audit columns
    quote = Quote(
        tenant_id=test_tenant.id,
        customer_id=uuid.uuid4(),
        created_by=None,  # NULL allowed
        updated_by=None
    )
    db_session.add(quote)
    db_session.commit()  # Should succeed
    
    assert quote.created_by is None
    assert quote.updated_by is None
```

---

## Requirements

### Phase 6.0.1 Task 4 Breakdown

Phase 6.0.1 Task 4 addresses Foreign Key constraints for the **Quoting System** domain (Migration 4 of 9):

#### Task 4: Quoting System FK Constraints (Migration 4)

**Scope:**
- 18 tables total
- 8 tables with BOTH `created_by` AND `updated_by` FKs (16 constraints)
- 10 tables with ONLY `created_by` FK (10 constraints) - append-only/versioned
- **Total**: 26 Foreign Key constraints

**Tables in This Task:**

**Both FKs (8 tables - 16 constraints):**
1. `quote` - Core quote entity
2. `quote_status` - Quote status lookup
3. `quote_link_status` - Quote link status lookup
4. `quote_message` - Quote conversation messages
5. `quote_public_link` - Public quote links
6. `pricebook_item` - Catalog pricing items
7. **Additional 2 tables** - Verify in analysis document

**Created-Only FK (10 tables - 10 constraints):**
1. `quote_line` - Quote line items (versioned)
2. `quote_version` - Quote version history
3. `quote_acceptance` - Quote acceptance log
4. `quote_public_link_contact_action` - Public link tracking
5. `quote_line_tax_component` - Tax breakdown
6. `pricebook_item_version` - Pricebook version history
7. **Additional 4 tables** - Verify in analysis document

**Migration Pattern:**
```python
"""Phase 6.0.1 Task 4: FK constraints for Quoting System audit columns

Revision ID: phase_6_0_1_task_4_fk_audit_quoting
Revises: phase_6_0_1_task_3_fk_audit_job
Create Date: 2026-04-13
"""

def upgrade():
    # Add FK constraints for tables with both created_by and updated_by
    for table_name in [
        # [LIST_8_TABLES_WITH_BOTH_FKS]
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
        # [LIST_10_TABLES_WITH_CREATED_ONLY]
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
        # [LIST_10_TABLES_WITH_CREATED_ONLY]
    ]:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        # [LIST_8_TABLES_WITH_BOTH_FKS]
    ]:
        op.drop_constraint(f'fk_{table_name}_updated_by', table_name, type_='foreignkey')
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
```

---

### Sub-Task 1: SQLModel Schema Definitions Verification

**Effort:** 0.5-1 day
**Scope:** Verify FK definitions across all 18 tables in Task 4

#### What This Sub-Task Accomplishes

Confirm that all Phase 6.0.1 Task 4 changes are correctly defined in the Python SQLModel definitions. Update models with FK constraints on audit columns.

#### Tables to Check (Task 4)

**Model Files & Required Changes:**

1. `backend/app/models/quoting.py`
   - **Tables with Both FKs (8 tables):**
     - `Quote`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
     - `QuoteStatus`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
     - `QuoteLinkStatus`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
     - `QuoteMessage`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
     - `QuotePublicLink`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
     - `PricebookItem`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
     - **[Verify 2 additional tables in analysis document]**
   
   - **Tables with Created-Only FK (10 tables):**
     - `QuoteLine`: Add `foreign_key="user.id"` to `created_by` only
     - `QuoteVersion`: Add `foreign_key="user.id"` to `created_by` only
     - `QuoteAcceptance`: Add `foreign_key="user.id"` to `created_by` only
     - `QuotePublicLinkContactAction`: Add `foreign_key="user.id"` to `created_by` only
     - `QuoteLineTaxComponent`: Add `foreign_key="user.id"` to `created_by` only
     - `PricebookItemVersion`: Add `foreign_key="user.id"` to `created_by` only
     - **[Verify 4 additional tables in analysis document]**

#### SQLModel Syntax Examples

**For Tables with Both FKs:**
```python
from typing import Optional
import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel

class Quote(SQLModel, table=True):
    __tablename__ = "quote"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    customer_id: uuid.UUID = Field(foreign_key="customer.id")
    
    # Audit columns - ADD FOREIGN KEYS
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",  # ← ADD THIS
        sa_column_kwargs={"ondelete": "RESTRICT"}  # ← ADD THIS
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",  # ← ADD THIS
        sa_column_kwargs={"ondelete": "RESTRICT"}  # ← ADD THIS
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**For Append-Only Tables (Created-Only FK):**
```python
class QuoteLine(SQLModel, table=True):
    __tablename__ = "quote_line"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quote_id: uuid.UUID = Field(foreign_key="quote.id")
    
    # Audit columns - ADD FOREIGN KEY to created_by ONLY
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",  # ← ADD THIS
        sa_column_kwargs={"ondelete": "RESTRICT"}  # ← ADD THIS
    )
    # No updated_by column (append-only table)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Success Criteria for Sub-Task 1:**
- [ ] All 18 tables in Task 4 have FK definitions added
- [ ] All FKs use string reference `"user.id"` not class reference
- [ ] All FKs specify `sa_column_kwargs={"ondelete": "RESTRICT"}`
- [ ] All audit columns remain `Optional[uuid.UUID]` (NULL support)
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models.quoting import *"`)

---

### Sub-Task 2: Pre-Migration Data Validation

**Effort:** 0.5 day
**Dependencies:** None (can run independently)
**CRITICAL:** Validation MUST pass before generating migration

#### What This Sub-Task Accomplishes

Verify that the database is ready for Phase 6.0.1 Task 4 migration by checking for orphaned audit references that would prevent FK constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation: Orphaned Audit References (MANDATORY)**

```sql
-- Check for orphaned created_by references in ALL Task 4 tables (18 total)
SELECT 'quote' as table_name, created_by, COUNT(*) as count
FROM quote
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_status', created_by, COUNT(*)
FROM quote_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_link_status', created_by, COUNT(*)
FROM quote_link_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_link_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_message', created_by, COUNT(*)
FROM quote_message
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_message.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_public_link', created_by, COUNT(*)
FROM quote_public_link
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_public_link.created_by)
GROUP BY created_by
UNION ALL
SELECT 'pricebook_item', created_by, COUNT(*)
FROM pricebook_item
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = pricebook_item.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_line', created_by, COUNT(*)
FROM quote_line
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_line.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_version', created_by, COUNT(*)
FROM quote_version
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_version.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_acceptance', created_by, COUNT(*)
FROM quote_acceptance
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_acceptance.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_public_link_contact_action', created_by, COUNT(*)
FROM quote_public_link_contact_action
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_public_link_contact_action.created_by)
GROUP BY created_by
UNION ALL
SELECT 'quote_line_tax_component', created_by, COUNT(*)
FROM quote_line_tax_component
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_line_tax_component.created_by)
GROUP BY created_by
UNION ALL
SELECT 'pricebook_item_version', created_by, COUNT(*)
FROM pricebook_item_version
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = pricebook_item_version.created_by)
GROUP BY created_by
-- Add remaining Task 4 tables here (verify 18 total)
;
-- Expected: 0 rows (no orphaned references)
```

```sql
-- Check for orphaned updated_by references (only for 8 tables with both FKs)
SELECT 'quote' as table_name, updated_by, COUNT(*) as count
FROM quote
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'quote_status', updated_by, COUNT(*)
FROM quote_status
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_status.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'quote_link_status', updated_by, COUNT(*)
FROM quote_link_status
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_link_status.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'quote_message', updated_by, COUNT(*)
FROM quote_message
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_message.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'quote_public_link', updated_by, COUNT(*)
FROM quote_public_link
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = quote_public_link.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'pricebook_item', updated_by, COUNT(*)
FROM pricebook_item
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = pricebook_item.updated_by)
GROUP BY updated_by
-- Add remaining 2 tables with both FKs (verify 8 total)
;
-- Expected: 0 rows (no orphaned references)
```

**If ANY validation query fails:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results
- **Report** - Ask for guidance on data cleanup strategy
- **Clean** - Implement chosen remediation strategy
- **Re-validate** - Run all queries again

**Success Criteria for Sub-Task 2:**
- [ ] All created_by orphan queries return 0 rows (18 tables)
- [ ] All updated_by orphan queries return 0 rows (8 tables)
- [ ] Validation results documented
- [ ] Ready to proceed with migration

---

### Sub-Task 3: Migration Creation & Application

**Effort:** 1 day
**Dependencies:** Sub-Task 1 (models) and Sub-Task 2 (validation) must be complete
**Migration:** 4 of 9

#### What This Sub-Task Accomplishes

Generate and apply Alembic migration with FK constraints for all 18 tables in Task 4.

#### Implementation Steps

**Step 1: Generate Migration Skeleton**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_1_task_4_fk_audit_quoting"
```

**Step 2: Manually Construct Complete Migration**

Use the migration pattern from Requirements section above. Ensure:
- 8 tables in first loop (both created_by and updated_by FKs)
- 10 tables in second loop (created_by only FKs)
- Total: 26 FK constraints
- Proper downgrade() implementation

**Step 3: Apply Migration**
```bash
alembic upgrade head
```

**Step 4: Verify Database State**
```sql
-- Verify FK constraints exist for Task 4 tables
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
    'quote', 'quote_status', 'quote_link_status', 'quote_message',
    'quote_public_link', 'pricebook_item', 'quote_line', 'quote_version',
    'quote_acceptance', 'quote_public_link_contact_action',
    'quote_line_tax_component', 'pricebook_item_version'
    -- Add all 18 Task 4 tables here
  )
  AND kcu.column_name IN ('created_by', 'updated_by')
  AND ccu.table_name = 'user'
ORDER BY tc.table_name, kcu.column_name;
-- Expected: 26 rows (8 tables × 2 + 10 tables × 1)
```

**Step 5: Test Migration Rollback**
```bash
alembic downgrade -1
# Verify FK constraints removed
alembic upgrade head
```

**Success Criteria for Sub-Task 3:**
- [ ] Migration created with all 26 FK constraints
- [ ] Migration applies successfully
- [ ] All verification queries pass (26 FK constraints exist)
- [ ] Migration rolls back successfully
- [ ] Migration re-applies successfully

---

### Sub-Task 4: Comprehensive Testing

**Effort:** 1 day
**Dependencies:** Sub-Task 3 must be complete

#### What This Sub-Task Accomplishes

Validate that all Phase 6.0.1 Task 4 FK constraints work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_1_task_4_audit_fk.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0.1 Task 4 - Quoting System Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: phase-6.0-db-schema-sync-11-plan.md - Task 4
"""
import pytest
from sqlalchemy.exc import IntegrityError
import uuid
from decimal import Decimal


class TestQuotingAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""
    
    def test_quote_created_by_fk_enforcement(self, db_session, test_tenant, test_customer):
        """Test that invalid created_by user ID is rejected for Quote"""
        from app.models.quoting import Quote
        
        invalid_user_id = uuid.uuid4()
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            created_by=invalid_user_id
        )
        db_session.add(quote)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_quote_created_by" in str(exc_info.value)
        db_session.rollback()
    
    def test_quote_status_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected for QuoteStatus"""
        from app.models.quoting import QuoteStatus
        
        invalid_user_id = uuid.uuid4()
        status = QuoteStatus(
            tenant_id=test_tenant.id,
            code="TEST",
            name="Test",
            created_by=invalid_user_id
        )
        db_session.add(status)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_quote_status_created_by" in str(exc_info.value)
        db_session.rollback()
    
    # Add similar tests for all 18 tables


class TestQuotingAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""
    
    def test_quote_updated_by_fk_enforcement(self, db_session, test_tenant, test_customer, test_user):
        """Test that invalid updated_by user ID is rejected"""
        from app.models.quoting import Quote
        
        # Create valid quote
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            created_by=test_user.id
        )
        db_session.add(quote)
        db_session.commit()
        
        # Attempt update with invalid user ID
        invalid_user_id = uuid.uuid4()
        quote.updated_by = invalid_user_id
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_quote_updated_by" in str(exc_info.value)
        db_session.rollback()
    
    # Add similar tests for all 8 tables with updated_by


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""
    
    def test_user_deletion_blocked_by_quote_audit(self, db_session, test_tenant, test_customer, test_user):
        """Test ON DELETE RESTRICT behavior for Quote"""
        from app.models.quoting import Quote
        
        # Create quote with user audit reference
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            created_by=test_user.id
        )
        db_session.add(quote)
        db_session.commit()
        
        # Attempt to delete user
        db_session.delete(test_user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_quote_created_by" in str(exc_info.value)
        db_session.rollback()
    
    # Add similar tests for key tables


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""
    
    def test_quote_null_audit_columns(self, db_session, test_tenant, test_customer):
        """Test that NULL created_by and updated_by are allowed"""
        from app.models.quoting import Quote
        
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            created_by=None,
            updated_by=None
        )
        db_session.add(quote)
        db_session.commit()
        
        assert quote.created_by is None
        assert quote.updated_by is None
    
    # Add similar tests for all 18 tables


class TestAppendOnlyTables:
    """Test created_by-only FK enforcement for versioned tables"""
    
    def test_quote_line_created_by_only(self, db_session, test_tenant, test_user, test_quote):
        """Test that quote_line has created_by FK but no updated_by"""
        from app.models.quoting import QuoteLine
        
        # Valid creation with created_by
        line = QuoteLine(
            quote_id=test_quote.id,
            line_number=1,
            description="Test",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            created_by=test_user.id
        )
        db_session.add(line)
        db_session.commit()
        
        # Verify no updated_by column (append-only)
        assert hasattr(line, 'created_by')
        assert line.created_by == test_user.id
        # QuoteLine should not have updated_by
    
    # Add similar tests for all 10 append-only tables
```

**Success Criteria for Sub-Task 4:**
- [ ] Test file created with all test categories
- [ ] FK enforcement tests prevent invalid user IDs (18 tables)
- [ ] User deletion prevention tests work correctly
- [ ] NULL audit column tests verify backward compatibility
- [ ] Append-only table tests validate created_by-only FKs
- [ ] Full test suite passes: 780+/780+ unit tests, 795+/795+ total (100%)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 780+ passed (768 baseline + ~12 new tests for Task 4)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 795+ passed (768 baseline + ~12 new tests for Task 4 + integration tests)
```

### Step 2: Verify Database State

Run all verification queries from Sub-Task 3 to confirm all 26 FK constraints exist and match expectations.

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
### Phase 6.0.1 Task 4: Quoting System FK Constraints - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_HOURS] hours (actual vs 3-4 hours estimated)
**Priority:** HIGH

**Implementation Summary:**

- ✅ Model Updates: Updated 18 tables in `quoting.py`
- ✅ Data Validation: Pre-migration orphan detection passed - 0 orphaned audit references found
- ✅ Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_1_task_4_fk_audit_quoting.py`]
- ✅ Test Suite: [`test_phase_6_0_1_task_4_audit_fk.py`] - [N]/[N] tests ✅
- ✅ Final Results: [NEW_UNIT]/[NEW_UNIT] unit tests (100%), [NEW_TOTAL]/[NEW_TOTAL] total tests (100%)

**Key Changes Completed:**
- ✅ 26 Foreign Key constraints added (8 tables × 2 + 10 tables × 1)
- ✅ All FKs use ON DELETE RESTRICT behavior
- ✅ Zero orphaned audit references found
- ✅ All models import successfully
- ✅ Migration applied successfully
- ✅ Migration rollback tested and validated
- ✅ User deletion workflow validated

**Baseline:** 768 total tests → **New:** [NEW_COUNT] total tests (+[DIFF])
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Phase 6.0.1 Task 4:
- [ ] **Regression baseline captured** (768/768 tests passing)
- [ ] **Complete table list verified** (18 tables from analysis document)
- [ ] **All orphaned audit reference queries returned 0 rows**
- [ ] **All 18 tables verified in Python models**
- [ ] **All FKs use string reference `"user.id"`**
- [ ] **All FKs specify `ondelete='RESTRICT'`**
- [ ] **All audit columns remain `Optional[uuid.UUID]`**
- [ ] **