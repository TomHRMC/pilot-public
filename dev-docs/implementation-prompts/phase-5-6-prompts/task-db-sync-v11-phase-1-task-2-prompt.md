# Task 2: Customer & Site Management - Audit FK Constraints

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - Task 2
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **Audit FK Constraints Analysis** ⭐
- Current Live Database (Phase 6.0.1 Post-State)
**Type:** Phase 6.0.1 - Foreign Key Constraints for Audit Columns
**Priority:** HIGH
**Change Type:** FOREIGN KEY CONSTRAINTS + MODEL UPDATES + TESTING

---

## Context

This is **Phase 6.0.1 - DB Sync v#11 Task 2**, continuing the audit integrity synchronization by addressing **Foreign Key constraint enforcement** for customer and site management related tables.

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

**Phase 6.0.1 Task 1 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 39 Foreign Key constraints added (19 tables × 2 FKs + 1 table × 1 FK)
- ✅ Common & Reference tables migration applied successfully
- ✅ Test suite: 738/738 tests passing (100%) - includes 32 new audit FK tests
- ✅ Zero orphaned audit references found
- ✅ All models import successfully

**Current Baseline:** 738/738 tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement
- **Phase 5.1:** ✅ COMPLETE - Missing unique constraints & foreign keys
- **Phase 5.2:** ✅ COMPLETE - Exclusion constraints & critical indexes
- **Phase 5.3:** ✅ COMPLETE - Notification schema + idempotency + index standardization + triggers
- **Phase 6.0:** ✅ COMPLETE - Advanced constraints & performance indexes
- **Phase 6.0.1 Task 1:** ✅ COMPLETE - Common & Reference tables FK constraints

**See:**
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` for Phase 6.0.1 master plan
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` for comprehensive FK requirements

---

## Current Task: Customer & Site Management FK Constraints

**Effort:** 2-3 hours (estimated)
**Gap Reference:** Phase 6.0.1 Analysis - Audit Trail Foreign Key Constraints - Task 2
**Change Type:** MODEL VERIFICATION + MIGRATION + DATA VALIDATION + TESTING

This task adds Foreign Key constraints to customer and site management tables, ensuring that all audit trail columns (`created_by`, `updated_by`) have database-level referential integrity enforcement. This covers core customer entities, site locations, addresses, contacts, and voice conversation sessions.

### What Needs to Be Fixed

**Scope:** 15 tables requiring FK constraints on audit columns
- **14 tables**: Both `created_by` AND `updated_by` FKs
- **1 table**: Only `created_by` FK (append-only)

**Tables in This Task:**

**Both FKs (14 tables)**:
1. `customer` - Core customer entity
2. `customer_lifecycle_status` - Customer status lookup
3. `site` - Customer site/location
4. `site_lifecycle_status` - Site status lookup
5. `address` - Physical addresses
6. `contact` - Contact information
7. `contact_endpoint` - Contact communication endpoints
8. `contact_notification_pref` - Contact notification preferences
9. `entity_address` - Polymorphic address links
10. `entity_contact` - Polymorphic contact links
11. `conversation_session` - Voice AI conversation sessions

**Created Only (1 table)**:
12. `contact_portal_invite` - Append-only invite log

**Note:** Task 2 scope shows 15 tables total (14 with both FKs + 1 with created_by only), but the detailed breakdown lists 12 specific tables. Verify the complete table list during implementation.

**Model Files to Update:**
- `backend/app/models/customer.py` - 5 tables
- `backend/app/models/common.py` - 6 tables
- `backend/app/models/voice.py` - 1 table

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

**Record the output of both results:** `738/738 tests passing` (Phase 6.0.1 Task 1 baseline)

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

**Example for Task 2 Tables:**
```sql
-- Check all Task 2 tables for orphaned created_by
SELECT 'customer' as table_name, created_by, COUNT(*) as count
FROM customer
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = customer.created_by)
GROUP BY created_by
UNION ALL
SELECT 'customer_lifecycle_status', created_by, COUNT(*)
FROM customer_lifecycle_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = customer_lifecycle_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'site', created_by, COUNT(*)
FROM site
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = site.created_by)
GROUP BY created_by
UNION ALL
SELECT 'site_lifecycle_status', created_by, COUNT(*)
FROM site_lifecycle_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = site_lifecycle_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'address', created_by, COUNT(*)
FROM address
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = address.created_by)
GROUP BY created_by
UNION ALL
SELECT 'contact', created_by, COUNT(*)
FROM contact
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = contact.created_by)
GROUP BY created_by
UNION ALL
SELECT 'contact_endpoint', created_by, COUNT(*)
FROM contact_endpoint
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = contact_endpoint.created_by)
GROUP BY created_by
UNION ALL
SELECT 'contact_notification_pref', created_by, COUNT(*)
FROM contact_notification_pref
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = contact_notification_pref.created_by)
GROUP BY created_by
UNION ALL
SELECT 'entity_address', created_by, COUNT(*)
FROM entity_address
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = entity_address.created_by)
GROUP BY created_by
UNION ALL
SELECT 'entity_contact', created_by, COUNT(*)
FROM entity_contact
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = entity_contact.created_by)
GROUP BY created_by
UNION ALL
SELECT 'conversation_session', created_by, COUNT(*)
FROM conversation_session
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = conversation_session.created_by)
GROUP BY created_by
UNION ALL
SELECT 'contact_portal_invite', created_by, COUNT(*)
FROM contact_portal_invite
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = contact_portal_invite.created_by)
GROUP BY created_by;
-- Expected: 0 rows total

-- Check tables with updated_by for orphaned updated_by references
SELECT 'customer' as table_name, updated_by, COUNT(*) as count
FROM customer
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = customer.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'customer_lifecycle_status', updated_by, COUNT(*)
FROM customer_lifecycle_status
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = customer_lifecycle_status.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'site', updated_by, COUNT(*)
FROM site
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = site.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'site_lifecycle_status', updated_by, COUNT(*)
FROM site_lifecycle_status
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = site_lifecycle_status.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'address', updated_by, COUNT(*)
FROM address
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = address.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'contact', updated_by, COUNT(*)
FROM contact
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = contact.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'contact_endpoint', updated_by, COUNT(*)
FROM contact_endpoint
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = contact_endpoint.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'contact_notification_pref', updated_by, COUNT(*)
FROM contact_notification_pref
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = contact_notification_pref.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'entity_address', updated_by, COUNT(*)
FROM entity_address
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = entity_address.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'entity_contact', updated_by, COUNT(*)
FROM entity_contact
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = entity_contact.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'conversation_session', updated_by, COUNT(*)
FROM conversation_session
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = conversation_session.updated_by)
GROUP BY updated_by;
-- Expected: 0 rows total (contact_portal_invite is append-only, no updated_by)
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

### 4. SQLModel Foreign Key Syntax

**CRITICAL:** Use the correct SQLModel/SQLAlchemy pattern for foreign keys.

**Correct Syntax (SQLModel Field):**
```python
from typing import Optional
import uuid
from sqlmodel import Field, SQLModel

class Customer(SQLModel, table=True):
    __tablename__ = "customer"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
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

### 5. Alembic Migration Pattern for FK Constraints

**CRITICAL:** Use the correct Alembic operation for foreign key creation.

**Correct Migration Pattern:**
```python
"""Phase 6.0.1 Task 2: FK constraints for customer & site tables

Revision ID: phase_6_0_1_task_2_fk_audit_customer
Revises: phase_6_0_1_task_1_fk_audit_common
Create Date: 2026-04-13
"""

def upgrade():
    # For tables with BOTH created_by and updated_by
    for table_name in [
        'customer', 'customer_lifecycle_status', 'site', 'site_lifecycle_status',
        'address', 'contact', 'contact_endpoint', 'contact_notification_pref',
        'entity_address', 'entity_contact', 'conversation_session'
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
    for table_name in ['contact_portal_invite']:
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
    for table_name in ['contact_portal_invite']:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'customer', 'customer_lifecycle_status', 'site', 'site_lifecycle_status',
        'address', 'contact', 'contact_endpoint', 'contact_notification_pref',
        'entity_address', 'entity_contact', 'conversation_session'
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
    from app.models.customer import Customer
    
    # Attempt to create record with non-existent user ID
    invalid_user_id = uuid.uuid4()
    customer = Customer(
        tenant_id=test_tenant.id,
        name="Test Customer",
        created_by=invalid_user_id  # Invalid user ID
    )
    db_session.add(customer)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_customer_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing User Deletion Prevention:**
```python
def test_user_deletion_prevented_by_audit_trail(db_session, test_user, test_tenant):
    """Test that user cannot be deleted if audit references exist"""
    from app.models.customer import Customer
    
    # Create record with user audit reference
    customer = Customer(
        tenant_id=test_tenant.id,
        name="Test Customer",
        created_by=test_user.id
    )
    db_session.add(customer)
    db_session.commit()
    
    # Attempt to delete user (should fail due to RESTRICT)
    db_session.delete(test_user)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_customer_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing NULL Audit Columns (Backward Compatibility):**
```python
def test_null_audit_columns_allowed(db_session, test_tenant):
    """Test that NULL audit columns are allowed for backward compatibility"""
    from app.models.customer import Customer
    
    # Create record with NULL audit columns
    customer = Customer(
        tenant_id=test_tenant.id,
        name="Test Customer",
        created_by=None,  # NULL allowed
        updated_by=None
    )
    db_session.add(customer)
    db_session.commit()  # Should succeed
    
    assert customer.created_by is None
    assert customer.updated_by is None
```

---

## Requirements

### Phase 6.0.1 Task 2 Breakdown

Phase 6.0.1 Task 2 focuses on customer and site management tables.

#### Task 2: Customer & Site Management FK Constraints (Migration 2)

**Scope:**
- 15 tables total
- 14 tables with BOTH `created_by` AND `updated_by` FKs
- 1 table with ONLY `created_by` FK (append-only)

**Tables in This Task:**
See "What Needs to Be Fixed" section above for complete table list.

**Migration Pattern:**
```python
"""Phase 6.0.1 Task 2: FK constraints for customer & site audit columns

Revision ID: phase_6_0_1_task_2_fk_audit_customer
Revises: phase_6_0_1_task_1_fk_audit_common
Create Date: 2026-04-13
"""

def upgrade():
    # Add FK constraints for tables with both created_by and updated_by
    for table_name in [
        'customer', 'customer_lifecycle_status', 'site', 'site_lifecycle_status',
        'address', 'contact', 'contact_endpoint', 'contact_notification_pref',
        'entity_address', 'entity_contact', 'conversation_session'
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
    for table_name in ['contact_portal_invite']:
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
    for table_name in ['contact_portal_invite']:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'customer', 'customer_lifecycle_status', 'site', 'site_lifecycle_status',
        'address', 'contact', 'contact_endpoint', 'contact_notification_pref',
        'entity_address', 'entity_contact', 'conversation_session'
    ]:
        op.drop_constraint(f'fk_{table_name}_updated_by', table_name, type_='foreignkey')
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
```

---

### Sub-Task 1: SQLModel Schema Definitions Verification

**Effort:** 0.5-1 day
**Scope:** Verify FK definitions across 15 tables in this task

#### What This Sub-Task Accomplishes

Confirm that all Phase 6.0.1 Task 2 changes are correctly defined in the Python SQLModel definitions. Update models with FK constraints on audit columns.

#### Tables to Check (Task 2)

**Model Files & Required Changes:**

1. `backend/app/models/customer.py`
   - `Customer`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`
   - `CustomerLifecycleStatus`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`
   - `Site`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`
   - `SiteLifecycleStatus`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`
   - `ContactPortalInvite`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to `created_by` ONLY (append-only table)

2. `backend/app/models/common.py`
   - `Address`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`
   - `Contact`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`
   - `ContactEndpoint`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`
   - `ContactNotificationPref`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`
   - `EntityAddress`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`
   - `EntityContact`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`

3. `backend/app/models/voice.py`
   - `ConversationSession`: Add `foreign_key="user.id"` + `sa_column_kwargs={"ondelete": "RESTRICT"}` to both `created_by` and `updated_by`

**Success Criteria for Sub-Task 1:**
- [ ] All 15 tables in this task have FK definitions added
- [ ] All FKs use string reference `"user.id"` not class reference
- [ ] All FKs specify `sa_column_kwargs={"ondelete": "RESTRICT"}`
- [ ] All audit columns remain `Optional[uuid.UUID]` (NULL support)
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models import *"`)

---

### Sub-Task 2: Pre-Migration Data Validation

**Effort:** 0.5 day
**Dependencies:** None (can run independently)
**CRITICAL:** Validation MUST pass before generating migration

#### What This Sub-Task Accomplishes

Verify that the database is ready for Phase 6.0.1 Task 2 migration by checking for orphaned audit references that would prevent FK constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation: Orphaned Audit References (MANDATORY)**

See the validation queries in the "Critical Warnings" section above for the complete SQL to check all Task 2 tables.

**If ANY validation query fails:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results
- **Report** - Ask for guidance on data cleanup strategy
- **Clean** - Implement chosen remediation strategy
- **Re-validate** - Run all queries again

**Success Criteria for Sub-Task 2:**
- [ ] All created_by orphan queries return 0 rows
- [ ] All updated_by orphan queries return 0 rows
- [ ] Validation results documented
- [ ] Ready to proceed with migration

---

### Sub-Task 3: Migration Creation & Application

**Effort:** 1 day
**Dependencies:** Sub-Task 1 (models) and Sub-Task 2 (validation) must be complete
**Migration:** 2 of 9

#### What This Sub-Task Accomplishes

Generate and apply Alembic migration with FK constraints for all 15 tables in this task.

#### Implementation Steps

**Step 1: Generate Migration Skeleton**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_1_task_2_fk_audit_customer"
```

**Step 2: Manually Construct Complete Migration**

Use the migration pattern from Requirements section above.

**Step 3: Apply Migration**
```bash
alembic upgrade head
```

**Step 4: Verify Database State**
```sql
-- Verify FK constraints exist for Task 2 tables
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
    'customer', 'customer_lifecycle_status', 'site', 'site_lifecycle_status',
    'address', 'contact', 'contact_endpoint', 'contact_notification_pref',
    'entity_address', 'entity_contact', 'conversation_session', 'contact_portal_invite'
  )
  AND kcu.column_name IN ('created_by', 'updated_by')
  AND ccu.table_name = 'user'
ORDER BY tc.table_name, kcu.column_name;
-- Expected: 29 rows (14 tables × 2 FKs + 1 table × 1 FK = 29 FKs)
```

**Step 5: Test Migration Rollback**
```bash
alembic downgrade -1
# Verify FK constraints removed
alembic upgrade head
```

**Success Criteria for Sub-Task 3:**
- [ ] Migration created with all FK constraints
- [ ] Migration applies successfully
- [ ] All verification queries pass
- [ ] Migration rolls back successfully
- [ ] Migration re-applies successfully

---

### Sub-Task 4: Comprehensive Testing

**Effort:** 1 day
**Dependencies:** Sub-Task 3 must be complete

#### What This Sub-Task Accomplishes

Validate that all Phase 6.0.1 Task 2 FK constraints work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_1_task_2_audit_fk.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0.1 Task 2 - Customer & Site Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: phase-6.0-db-schema-sync-11-plan.md - Task 2
"""
import pytest
from sqlalchemy.exc import IntegrityError
import uuid


class TestAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""
    
    def test_customer_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        # [See example in Critical Warnings section above]
    
    def test_customer_valid_created_by_accepted(self, db_session, test_tenant, test_user):
        """Test that valid created_by user ID is accepted"""
        # Create record with valid user ID
        # Verify successful commit


class TestAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""
    
    def test_customer_updated_by_fk_enforcement(self, db_session, test_tenant, test_user):
        """Test that invalid updated_by user ID is rejected"""
        # Similar to created_by but for updated_by


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""
    
    def test_user_deletion_blocked_by_customer_audit(self, db_session, test_tenant, test_user):
        """Test ON DELETE RESTRICT behavior"""
        # [See example in Critical Warnings section above]


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""
    
    def test_customer_null_audit_columns(self, db_session, test_tenant):
        """Test that NULL created_by and updated_by are allowed"""
        # [See example in Critical Warnings section above]
```

**Test Coverage Requirements:**
- Test FK enforcement for at least 3 representative tables from Task 2
- Test created_by FK constraint (invalid user ID rejected)
- Test updated_by FK constraint (invalid user ID rejected)
- Test valid user IDs accepted
- Test user deletion prevention (ON DELETE RESTRICT)
- Test NULL audit columns allowed (backward compatibility)
- Test append-only table behavior (contact_portal_invite)

**Success Criteria for Sub-Task 4:**
- [ ] Test file created with all test categories
- [ ] FK enforcement tests prevent invalid user IDs
- [ ] User deletion prevention tests work correctly
- [ ] NULL audit column tests verify backward compatibility
- [ ] Full test suite passes: [NEW_COUNT]/[NEW_COUNT] tests (100%)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 738+ passed (738 baseline + new tests for Task 2)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 738+ passed (738 baseline + new tests for Task 2)
```

### Step 2: Verify Database State

Run all verification queries from Sub-Task 3 to confirm FK constraints exist and match expectations.

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check migration was applied successfully
3. Verify FK constraint definitions in database
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md`

Add implementation status to the "Phase 6.0 Task 2" section:

```markdown
### Phase 6.0.1 Task 2: Customer & Site Management FK Constraints - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_HOURS] hours (actual)
**Priority:** HIGH

**Implementation Summary:**

- Model Verification: Updated 15 tables in 3 model files
- Data Validation: All pre-migration orphan detection queries passed (0 orphaned references)
- Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_1_task_2_fk_audit_customer.py`]
- Test Suite: [`test_phase_6_0_1_task_2_audit_fk.py`] - [N] tests ✅
- Final Results: [NEW_UNIT]/[NEW_UNIT] unit tests (100%), [NEW_TOTAL]/[NEW_TOTAL] total tests (100%)

**Key Changes:**
- ✅ 29 Foreign Key constraints added (14 tables × 2 + 1 table × 1)
- ✅ All FKs use ON DELETE RESTRICT behavior
- ✅ Zero orphaned audit references found
- ✅ User deletion workflow validated
- ✅ Zero regressions in existing test suite

**Baseline:** 738 total tests → **New:** [NEW_TOTAL] total tests (+[DIFF])
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Phase 6.0.1 Task 2:
- [ ] **Regression baseline captured** (738/738 tests)
- [ ] **All orphaned audit reference queries returned 0 rows**
- [ ] **All 15 tables verified in Python models**
- [ ] **All FKs use string reference `"user.id"`**
- [ ] **All FKs specify `ondelete='RESTRICT'`**
- [ ] **All audit columns remain `Optional[uuid.UUID]`**
- [ ] **Alembic migration created for this task**
- [ ] **Migration applied successfully**
- [ ] **All database verification queries passed**
- [ ] **Comprehensive tests written and passing**
- [ ] **ALL 738 existing tests still passing**
- [ ] **New total: [NEW_COUNT]+/[NEW_COUNT]+ tests (100%)**
- [ ] **Migration rollback tested**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **FK Requirements Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models (15 tables in this task)
- `backend/app/models/customer.py` - 5 tables
- `backend/app/models/common.py` - 6 tables (shared address/contact models)
- `backend/app/models/voice.py` - 1 table

---

## Risk Assessment

**For Phase 6.0.1 Task 2:**
- **Orphaned Reference Risk:** MEDIUM (orphaned audit references would prevent FK creation - validated before migration)
- **Customer Data Impact:** MEDIUM (core business entities - customer, site, address, contact)
- **User Deletion Impact:** MEDIUM (ON DELETE RESTRICT changes operational workflow)
- **Migration Complexity:** LOW (standard FK constraint operations)
- **Application Impact:** LOW (additive changes, improves data integrity without breaking changes)
- **Rollback Complexity:** LOW (single independent migration, surgical rollback)
- **Performance Impact:** MINIMAL (FK constraints add negligible overhead)
- **Mitigation:** Comprehensive pre-migration validation, extensive testing, documented user deletion workflow

---

## Notes

### Important Patterns to Follow
- **Separate Migration:** One migration for Task 2 customer & site tables
- **Zero Orphans:** Pre-migration validation MUST show 0 orphaned audit references
- **String References:** Always use `foreign_key="user.id"` not class reference
- **ON DELETE RESTRICT:** Mandatory for all audit FK constraints
- **NULL Support:** All audit columns must remain `Optional[uuid.UUID]`
- **Zero Regression:** All 738 tests MUST pass

### Phase 6.0.1 Task 2 Specific
- **29 FK Constraints:** 14 tables × 2 + 1 table × 1
- **Customer Focus:** Core customer and site management entities
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

### Phase 6.0.1 Task 2 Checklist:
1. ✅ Capture baseline (738/738 tests)
2. 🔍 **Verify all 15 table FK definitions in Python models**
3. ✅ Verify Python syntax (`python -c "from app.models import *"`)
4. ⚠️ **CRITICAL: Run orphaned created_by queries (all Task 2 tables)**
5. ⚠️ **CRITICAL: Run orphaned updated_by queries (14 tables with updated_by)**
6. ⚠️ **MANDATORY: Stop if ANY orphaned references found**
7. 🔧 **Create Migration: FK constraints for customer & site tables**
8. ✅ Apply Migration, verify FK constraints created
9. 🧪 **Create comprehensive test suite (FK enforcement + user deletion + NULL support)**
10. 🔄 Run regression tests (738+ expected)
11. ↩️ Test migration rollback
12. 📚 Update project plan

Remember: Phase 6.0.1 Task 2 focuses on customer and site management - the core business entities that drive revenue. Validate thoroughly before migration, test extensively, and ensure zero regressions!
