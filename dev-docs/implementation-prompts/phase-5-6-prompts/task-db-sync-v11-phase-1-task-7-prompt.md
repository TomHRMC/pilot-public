# Task 7: Integration & Sync FK Constraints - Audit FK Constraints

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - Task 7
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **Audit FK Constraints Analysis** ⭐
- Current Live Database (Phase 6.0.1 Task 6 Post-State)
**Type:** Phase 6.0.1 - Foreign Key Constraints for Audit Columns
**Priority:** MEDIUM
**Change Type:** FOREIGN KEY CONSTRAINTS + MODEL UPDATES + TESTING

---

## Context

This is **Phase 6.0.1 - DB Sync v#11 Task 7**, addressing **Foreign Key constraint enforcement** for `created_by` and `updated_by` audit trail columns in **Integration & Sync** tables.

**Root Cause:** 
- The JSON master blueprint specifies that ALL `created_by` and `updated_by` tracking columns should have explicit Foreign Key constraints referencing `user.id`
- Currently, these columns exist physically and application code populates them correctly
- **But**: No database-level referential integrity enforcement exists

**Critical Impact:**
- **Data Integrity Vulnerability:** Invalid user IDs can be inserted into audit columns
- **Orphaned Audit Records:** If users are deleted, audit trail breaks
- **Broken Audit Trail:** Cannot reliably trace actions back to users
- **Compliance Violations:** SOC 2, GDPR audit requirements compromised

**Scope:** Task 7 of 9 separate migrations - **8 Foreign Key constraints** across **4 tables**:
- **4 tables**: Both `created_by` AND `updated_by` Foreign Keys (8 FKs)
- **0 tables**: Only `created_by` FK (none - all integration tables with MachineLogMixin lack audit columns)

**Key Principle:** Phase 6.0.1 uses **9 separate Alembic migrations** (one per functional domain) for surgical rollback capability, optimized task sizing (~15-20 tables per task), and keeping AI agent context usage at 50-60%.

---

## What Was Completed in Previous Phases

**Phase 6.0.1 Task 6 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 28 Foreign Key constraints added (15 tables in Tenant & User domain)
- ✅ 809/809 unit tests, 836/836 total tests passing (100%)
- ✅ Migration rollback tested successfully

**Current Baseline:** 809/809 unit tests, 836/836 total tests passing (100%)

**Previous Tasks:**
- **Task 1**: ✅ COMPLETE - Common & Reference Tables (20 tables, 39 FKs)
- **Task 2**: ✅ COMPLETE - Customer & Site Management (12 tables, 23 FKs)
- **Task 3**: ✅ COMPLETE - Job Management (12 tables, 23 FKs)
- **Task 4**: ✅ COMPLETE - Quoting System (12 tables, 19 FKs)
- **Task 5**: ✅ COMPLETE - Billing & Payments (18 tables, 30 FKs)
- **Task 6**: ✅ COMPLETE - Tenant & User Management (15 tables, 28 FKs)

**See:**
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` for master plan
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` for comprehensive FK requirements

---

## Current Task: Integration & Sync FK Constraints

**Effort:** 2-3 hours (estimated)
**Gap Reference:** Phase 6.0.1 Analysis - Audit Trail Foreign Key Constraints
**Change Type:** MODEL VERIFICATION + MIGRATION + DATA VALIDATION + TESTING

This task adds Foreign Key constraints to integration and sync-related tables, ensuring that all audit trail columns properly reference valid users. These tables handle external system integrations (QuickBooks, etc.), OAuth credentials, entity mapping, and sync conflict resolution.

**Note:** Only tables using StandardAuditMixin are included. Tables using MachineLogMixin (connector_run_log, integration_sync_log, webhook_endpoint, webhook_event, webhook_delivery_attempt, idempotency_key) do NOT have `created_by`/`updated_by` columns and are excluded from this migration.

### What Needs to Be Fixed

**Model File:** `backend/app/models/system.py`

**Tables in This Task (4 total):**

**Both `created_by` AND `updated_by` FKs (4 tables - all use StandardAuditMixin):**
1. `connector_config` - Integration connector configurations
2. `integration_credential` - OAuth/API credentials
3. `integration_sync_mapping` - Entity mapping for sync
4. `integration_sync_conflict` - Sync conflict log

**Total:** 8 Foreign Key constraints (4 tables × 2)

**Excluded Tables (use MachineLogMixin - no audit columns):**
- `connector_run_log` - No created_by/updated_by columns
- `integration_sync_log` - No created_by/updated_by columns
- `webhook_endpoint` - No created_by/updated_by columns
- `webhook_event` - No created_by/updated_by columns
- `webhook_delivery_attempt` - No created_by/updated_by columns
- `idempotency_key` - No created_by/updated_by columns

### Tools Available

- You have access to the postgres-local MCP server to query the DB directly, in read-only mode.
- Remember that you do not need to insert any '\n' characters in the sql when creating it for the mcp server.

### Model Location Reference

**For locating models in the codebase:**
- Review `backend/db_models_map.md` - Shows which models are in which files
- Review `backend/app_model_imports.md` - Shows proper import patterns

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

**Record the output of both results:** `809/809 & 836/836 tests passing` (Phase 6.0.1 Task 6 baseline)

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

**Example for Task 7 Tables:**
```sql
-- Check all 4 tables in Task 7 for orphaned created_by
SELECT 'connector_config' as table_name, created_by, COUNT(*) as count
FROM connector_config
WHERE created_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = connector_config.created_by)
GROUP BY created_by
UNION ALL
SELECT 'integration_credential', created_by, COUNT(*)
FROM integration_credential
WHERE created_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = integration_credential.created_by)
GROUP BY created_by
UNION ALL
SELECT 'integration_sync_mapping', created_by, COUNT(*)
FROM integration_sync_mapping
WHERE created_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = integration_sync_mapping.created_by)
GROUP BY created_by
UNION ALL
SELECT 'integration_sync_conflict', created_by, COUNT(*)
FROM integration_sync_conflict
WHERE created_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = integration_sync_conflict.created_by)
GROUP BY created_by
;
-- Expected: 0 rows total

-- Check for orphaned updated_by references (all 4 tables have updated_by)
SELECT 'connector_config' as table_name, updated_by, COUNT(*) as count
FROM connector_config
WHERE updated_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = connector_config.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'integration_credential', updated_by, COUNT(*)
FROM integration_credential
WHERE updated_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = integration_credential.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'integration_sync_mapping', updated_by, COUNT(*)
FROM integration_sync_mapping
WHERE updated_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = integration_sync_mapping.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'integration_sync_conflict', updated_by, COUNT(*)
FROM integration_sync_conflict
WHERE updated_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = integration_sync_conflict.updated_by)
GROUP BY updated_by
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

### 4. Nine-Task Migration Strategy

**MANDATORY:** Phase 6.0.1 uses **9 separate Alembic migrations** for surgical rollback and context optimization:

**Task 7 Position:** 7th of 9 migrations
- **Completed**: Tasks 1-6 (162 FK constraints across 87 tables)
- **Current**: Task 7 (17 FK constraints across 10 tables)
- **Remaining**: Tasks 8-9 (24 FK constraints remaining)

**Why Separate Migrations:**
- Atomic rollback capability per domain
- Risk isolation (high-traffic tables separate from low-traffic)
- Easier troubleshooting if migration fails
- Clear task boundaries for AI agents
- Prevents context window overflow

---

### 5. SQLModel Foreign Key Syntax

**CRITICAL:** Use the correct SQLModel/SQLAlchemy pattern for foreign keys.

**Correct Syntax (SQLModel Field):**
```python
from typing import Optional
import uuid
from sqlmodel import Field, SQLModel

class ConnectorConfig(SQLModel, table=True):
    __tablename__ = "connector_config"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    connector_type: str
    
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
    foreign_key=User.id  # Circular dependency risk!
)

# ❌ WRONG - Not Optional (breaks NULL support)
created_by: uuid.UUID = Field(
    foreign_key="user.id"  # Should be Optional[uuid.UUID]
)
```

---

### 6. Alembic Migration Pattern for FK Constraints

**CRITICAL:** Use the correct Alembic operation for foreign key creation.

**Correct Migration Pattern:**
```python
"""Phase 6.0.1 Task 7: FK constraints for Integration & Sync tables

Revision ID: phase_6_0_1_task_7_fk_audit_integration
Revises: phase_6_0_1_task_6_fk_audit_tenant
Create Date: 2026-04-13
"""

def upgrade():
    # For tables with BOTH created_by and updated_by
    for table_name in [
        'connector_config',
        'integration_credential',
        'integration_sync_mapping',
        'integration_sync_conflict',
        'connector_run_log',
        'integration_sync_log',
        'webhook_endpoint'
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
        'webhook_event',
        'webhook_delivery_attempt',
        'idempotency_key'
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
        'webhook_event',
        'webhook_delivery_attempt',
        'idempotency_key'
    ]:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'connector_config',
        'integration_credential',
        'integration_sync_mapping',
        'integration_sync_conflict',
        'connector_run_log',
        'integration_sync_log',
        'webhook_endpoint'
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
    from app.models.system import ConnectorConfig
    
    # Attempt to create record with non-existent user ID
    invalid_user_id = uuid.uuid4()
    connector = ConnectorConfig(
        tenant_id=test_tenant.id,
        connector_type="quickbooks",
        created_by=invalid_user_id  # Invalid user ID
    )
    db_session.add(connector)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_connector_config_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing User Deletion Prevention:**
```python
def test_user_deletion_prevented_by_audit_trail(db_session, test_user, test_tenant):
    """Test that user cannot be deleted if audit references exist"""
    from app.models.system import ConnectorConfig
    
    # Create record with user audit reference
    connector = ConnectorConfig(
        tenant_id=test_tenant.id,
        connector_type="quickbooks",
        created_by=test_user.id
    )
    db_session.add(connector)
    db_session.commit()
    
    # Attempt to delete user (should fail due to RESTRICT)
    db_session.delete(test_user)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_connector_config_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing NULL Audit Columns (Backward Compatibility):**
```python
def test_null_audit_columns_allowed(db_session, test_tenant):
    """Test that NULL audit columns are allowed for backward compatibility"""
    from app.models.system import ConnectorConfig
    
    # Create record with NULL audit columns
    connector = ConnectorConfig(
        tenant_id=test_tenant.id,
        connector_type="quickbooks",
        created_by=None,  # NULL allowed
        updated_by=None
    )
    db_session.add(connector)
    db_session.commit()  # Should succeed
    
    assert connector.created_by is None
    assert connector.updated_by is None
```

---

## Requirements

### Phase 6.0.1 Task 7 Breakdown

#### Task 7: Integration & Sync FK Constraints (Migration 7 of 9)

**Scope:**
- 10 tables total
- 7 tables with BOTH `created_by` AND `updated_by` FKs (14 constraints)
- 3 tables with ONLY `created_by` FK (3 constraints)
- **Total**: 17 Foreign Key constraints

**Tables in This Task:**

**Both FKs (7 tables):**
1. `connector_config` - Integration connector configurations
2. `integration_credential` - OAuth/API credentials
3. `integration_sync_mapping` - Entity mapping for sync
4. `integration_sync_conflict` - Sync conflict log
5. `connector_run_log` - Connector execution log
6. `integration_sync_log` - Sync operation log
7. `webhook_endpoint` - Webhook endpoint configurations

**Created Only (3 tables - append-only):**
8. `webhook_event` - Append-only webhook event log
9. `webhook_delivery_attempt` - Append-only webhook delivery log
10. `idempotency_key` - Append-only idempotency tracking

---

### Task 1: SQLModel Schema Definitions Verification

**Effort:** 0.5-1 day
**Scope:** Verify FK definitions across 10 tables in this task

#### What This Task Accomplishes

Confirm that all Phase 6.0.1 Task 7 changes are correctly defined in the Python SQLModel definitions. Update models with FK constraints on audit columns.

#### Tables to Check (Task 7)

**Model Files & Required Changes:**

1. `backend/app/models/system.py`
   - `ConnectorConfig`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `IntegrationCredential`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `IntegrationSyncMapping`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `IntegrationSyncConflict`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `ConnectorRunLog`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `IntegrationSyncLog`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `WebhookEndpoint`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `WebhookEvent`: Add `foreign_key="user.id"` to `created_by` ONLY (append-only)
   - `WebhookDeliveryAttempt`: Add `foreign_key="user.id"` to `created_by` ONLY (append-only)
   - `IdempotencyKey`: Add `foreign_key="user.id"` to `created_by` ONLY (append-only)

#### SQLModel Syntax Examples

**For tables with both FKs:**
```python
from typing import Optional
import uuid
from sqlmodel import Field, SQLModel

class ConnectorConfig(SQLModel, table=True):
    __tablename__ = "connector_config"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    connector_type: str
    config_data: dict
    
    # ✅ CORRECT - Audit columns with FK constraints
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",
        sa_column_kwargs={"ondelete": "RESTRICT"}
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",
        sa_column_kwargs={"ondelete": "RESTRICT"}
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**For append-only tables (created_by only):**
```python
class WebhookEvent(SQLModel, table=True):
    __tablename__ = "webhook_event"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    event_type: str
    event_data: dict
    
    # ✅ CORRECT - Only created_by for append-only table
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",
        sa_column_kwargs={"ondelete": "RESTRICT"}
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # NO updated_by or updated_at for append-only tables
```

**Success Criteria for Task 1:**
- [ ] All 10 tables in this task have FK definitions added
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

Verify that the database is ready for Phase 6.0.1 Task 7 migration by checking for orphaned audit references that would prevent FK constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation: Orphaned Audit References (MANDATORY)**

See the comprehensive validation queries in the "Critical Warnings" section above. You MUST run:
1. Orphaned `created_by` check for ALL 10 tables
2. Orphaned `updated_by` check for 7 tables with both FKs

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
**Migration:** 7 of 9

#### What This Task Accomplishes

Generate and apply Alembic migration with FK constraints for all tables in this task.

#### Implementation Steps

**Step 1: Generate Migration Skeleton**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_1_task_7_fk_audit_integration"
```

**Step 2: Manually Construct Complete Migration**

Use the migration pattern from the "Critical Warnings" section above.

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
    'connector_config',
    'integration_credential',
    'integration_sync_mapping',
    'integration_sync_conflict',
    'connector_run_log',
    'integration_sync_log',
    'webhook_endpoint',
    'webhook_event',
    'webhook_delivery_attempt',
    'idempotency_key'
  )
  AND kcu.column_name IN ('created_by', 'updated_by')
  AND ccu.table_name = 'user'
ORDER BY tc.table_name, kcu.column_name;
-- Expected: 17 rows (7 tables × 2 + 3 tables × 1)
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

Validate that all Phase 6.0.1 Task 7 FK constraints work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_1_task_7_audit_fk.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0.1 Task 7 - Integration & Sync Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: phase-6.0-db-schema-sync-11-plan.md - Task 7
"""
import pytest
from sqlalchemy.exc import IntegrityError
import uuid


class TestAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""
    
    def test_connector_config_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import ConnectorConfig
        
        invalid_user_id = uuid.uuid4()
        connector = ConnectorConfig(
            tenant_id=test_tenant.id,
            connector_type="quickbooks",
            created_by=invalid_user_id
        )
        db_session.add(connector)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_connector_config_created_by" in str(exc_info.value)
        db_session.rollback()
    
    def test_webhook_event_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test append-only table FK enforcement"""
        from app.models.system import WebhookEvent
        
        invalid_user_id = uuid.uuid4()
        event = WebhookEvent(
            tenant_id=test_tenant.id,
            event_type="test.event",
            created_by=invalid_user_id
        )
        db_session.add(event)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_webhook_event_created_by" in str(exc_info.value)
        db_session.rollback()


class TestAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""
    
    def test_connector_config_updated_by_fk_enforcement(self, db_session, test_tenant, test_user):
        """Test that invalid updated_by user ID is rejected"""
        from app.models.system import ConnectorConfig
        
        # Create valid record
        connector = ConnectorConfig(
            tenant_id=test_tenant.id,
            connector_type="quickbooks",
            created_by=test_user.id
        )
        db_session.add(connector)
        db_session.commit()
        
        # Attempt to update with invalid user ID
        invalid_user_id = uuid.uuid4()
        connector.updated_by = invalid_user_id
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_connector_config_updated_by" in str(exc_info.value)
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""
    
    def test_user_deletion_blocked_by_connector_config_audit(self, db_session, test_tenant, test_user):
        """Test ON DELETE RESTRICT behavior"""
        from app.models.system import ConnectorConfig
        
        # Create record with user audit reference
        connector = ConnectorConfig(
            tenant_id=test_tenant.id,
            connector_type="quickbooks",
            created_by=test_user.id
        )
        db_session.add(connector)
        db_session.commit()
        
        # Attempt to delete user (should fail due to RESTRICT)
        db_session.delete(test_user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_connector_config_created_by" in str(exc_info.value)
        db_session.rollback()


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""
    
    def test_connector_config_null_audit_columns(self, db_session, test_tenant):
        """Test that NULL created_by and updated_by are allowed"""
        from app.models.system import ConnectorConfig
        
        # Create record with NULL audit columns
        connector = ConnectorConfig(
            tenant_id=test_tenant.id,
            connector_type="quickbooks",
            created_by=None,
            updated_by=None
        )
        db_session.add(connector)
        db_session.commit()  # Should succeed
        
        assert connector.created_by is None
        assert connector.updated_by is None
    
    def test_webhook_event_null_created_by_allowed(self, db_session, test_tenant):
        """Test that NULL created_by is allowed for append-only tables"""
        from app.models.system import WebhookEvent
        
        # Create record with NULL created_by
        event = WebhookEvent(
            tenant_id=test_tenant.id,
            event_type="test.event",
            created_by=None
        )
        db_session.add(event)
        db_session.commit()  # Should succeed
        
        assert event.created_by is None
```

**Test Coverage Requirements:**
- FK enforcement tests for at least 2-3 representative tables (both standard and append-only)
- Valid reference tests
- User deletion prevention tests
- NULL support tests for both table types

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
# Expected: 820+ passed (809 baseline + ~11 new tests for this task)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 847+ passed (836 baseline + ~11 new tests for this task)
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
### Phase 6.0.1 Task 7: Integration & Sync FK Constraints - ✅ COMPLETE

**Status:** ✅ COMPLETE (2026-04-13)
**Effort:** [ACTUAL_HOURS] hours (actual vs 2-3 hours estimated)
**Priority:** MEDIUM

**Implementation Summary:**

- ✅ Model Updates: Updated 10 tables in `system.py`
- ✅ Data Validation: Pre-migration orphan detection passed - 0 orphaned references found
- ✅ Migration: `YYYY_MM_DD_HHMM-[hash]_phase_6_0_1_task_7_fk_audit_integration.py`
- ✅ Test Suite: `test_phase_6_0_1_task_7_audit_fk.py` - [N]/[N] tests ✅
- ✅ Final Results: [NEW_UNIT]/[NEW_UNIT] unit tests (100%), [NEW_TOTAL]/[NEW_TOTAL] total tests (100%)

**Key Changes Completed:**
- ✅ 17 Foreign Key constraints added (7 tables × 2 + 3 tables × 1)
- ✅ All FKs use ON DELETE RESTRICT behavior
- ✅ Zero orphaned audit references found
- ✅ All models import successfully
- ✅ Migration applied successfully
- ✅ Migration rollback tested and validated
- ✅ User deletion workflow validated

**Scope:** 10 tables requiring FK constraints on audit columns
- 7 tables: Both `created_by` AND `updated_by` FKs (14 constraints)
- 3 tables: Only `created_by` FK (3 constraints) - append-only/event log tables

**Tables Included:**
- `connector_config` - Both
- `integration_credential` - Both
- `integration_sync_mapping` - Both
- `integration_sync_conflict` - Both
- `connector_run_log` - Both
- `integration_sync_log` - Both
- `webhook_endpoint` - Both
- `webhook_event` - Created only
- `webhook_delivery_attempt` - Created only
- `idempotency_key` - Created only

**Baseline:** 809 unit tests, 836 total tests → **New:** [NEW_UNIT] unit tests (+[DIFF]), [NEW_TOTAL] total tests (+[DIFF])
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Phase 6.0.1 Task 7:
- [ ] **Regression baseline captured** (809/809 unit, 836/836 total)
- [ ] **All orphaned audit reference queries returned 0 rows**
- [ ] **All 10 tables verified in Python models**
- [ ] **All FKs use string reference `"user.id"`**
- [ ] **All FKs specify `ondelete='RESTRICT'`**
- [ ] **All audit columns remain `Optional[uuid.UUID]`**
- [ ] **Alembic migration created for this task**
- [ ] **Migration applied successfully**
- [ ] **All database verification queries passed**
- [ ] **Comprehensive tests written and passing**
- [ ] **ALL 809 existing unit tests still passing**
- [ ] **ALL 836 total tests still passing**
- [ ] **New total: [NEW_UNIT]+/[NEW_UNIT]+ unit, [NEW_TOTAL]+/[NEW_TOTAL]+ total (100%)**
- [ ] **Migration rollback tested**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **FK Requirements Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models (10 tables in this task)
- `backend/app/models/system.py` - All 10 tables in this task

### Model Location References
- `backend/db_models_map.md` - Model-to-file mapping ⭐
- `backend/app_model_imports.md` - Proper import patterns ⭐

---

## Risk Assessment

**For Phase 6.0.1 Task 7:**
- **Orphaned Reference Risk:** LOW (integration tables typically have good audit data)
- **Circular Dependency Risk:** LOW (string-based FK references prevent Python circular imports)
- **User Deletion Impact:** LOW (integration configs rarely block user deletion)
- **Migration Complexity:** LOW (standard FK constraint operations)
- **Application Impact:** LOW (additive changes, improves data integrity without breaking changes)
- **Rollback Complexity:** LOW (single independent migration, surgical rollback)
- **Performance Impact:** MINIMAL (FK constraints add negligible overhead)
- **Mitigation:** Comprehensive pre-migration validation, extensive testing

---

## Notes

### Important Patterns to Follow
- **Nine Migrations:** One per functional domain (Tasks 1-9)
- **Zero Orphans:** Pre-migration validation MUST show 0 orphaned audit references
- **String References:** Always use `foreign_key="user.id"` not class reference
- **ON DELETE RESTRICT:** Mandatory for all audit FK constraints
- **NULL Support:** All audit columns must remain `Optional[uuid.UUID]`
- **Zero Regression:** All 809 unit + 836 total tests MUST pass

### Phase 6.0.1 Task 7 Specific
- **17 FK Constraints:** 7 tables × 2 + 3 tables × 1
- **Single Model File:** All tables in `system.py`
- **Append-Only Tables:** webhook_event, webhook_delivery_attempt, idempotency_key (created_by only)
- **Integration Focus:** Covers QuickBooks sync, webhook handling, idempotency tracking

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 6.0.1 plan for detailed specifications
- Verify all pre-migration orphan detection queries passed
- Check that correct task number migration is being created
- Verify FK definitions use string reference and `ondelete='RESTRICT'`
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Phase 6.0.1 Task 7 Checklist:
1. ✅ Capture baseline (809/809 unit, 836/836 total)
2. 🔍 **Verify all 10 table FK definitions in `system.py`**
3. ✅ Verify Python syntax (`python -c "from app.models import *"`)
4. ⚠️ **CRITICAL: Run orphaned created_by queries (all 10 tables)**
5. ⚠️ **CRITICAL: Run orphaned updated_by queries (7 tables with updated_by)**
6. ⚠️ **MANDATORY: Stop if ANY orphaned references found**
7. 🔧 **Create Migration: FK constraints for Integration & Sync tables**
8. ✅ Apply Migration, verify FK constraints created (17 FKs expected)
9. 🧪 **Create comprehensive test suite (FK enforcement + user deletion + NULL support)**
10. 🔄 Run regression tests ([NEW_COUNT]+/[NEW_COUNT]+ expected)
11. ↩️ Test migration rollback
12. 📚 Update project plan

Remember: Phase 6.0.1 brings database-level audit trail integrity, preventing orphaned references and ensuring compliance with SOC 2 and GDPR requirements. Validate thoroughly before migration, test extensively, and ensure zero regressions!
