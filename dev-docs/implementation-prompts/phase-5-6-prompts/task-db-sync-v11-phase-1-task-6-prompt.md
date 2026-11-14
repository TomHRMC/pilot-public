# Task 6: Tenant & User Management FK Constraints - Audit FK Constraints

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - Task 6
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **Audit FK Constraints Analysis** ⭐
- Current Live Database (Phase 6.0.1 Task 5 Post-State)
**Type:** Phase 6.0.1 - Foreign Key Constraints for Audit Columns
**Priority:** HIGH
**Change Type:** FOREIGN KEY CONSTRAINTS + MODEL UPDATES + TESTING

---

## Context

This is **Phase 6.0.1 Task 6 - DB Sync v#11**, part of the final audit integrity synchronization addressing **Foreign Key constraint enforcement** for all `created_by` and `updated_by` audit trail columns.

**Root Cause:** 
- The JSON master blueprint specifies that ALL `created_by` and `updated_by` tracking columns should have explicit Foreign Key constraints referencing `user.id`
- Currently, these columns exist physically and application code populates them correctly
- **But**: No database-level referential integrity enforcement exists

**Critical Impact:**
- **Data Integrity Vulnerability:** Invalid user IDs can be inserted into audit columns
- **Orphaned Audit Records:** If users are deleted, audit trail breaks
- **Broken Audit Trail:** Cannot reliably trace actions back to users
- **Compliance Violations:** SOC 2, GDPR audit requirements compromised

**Task 6 Scope:** **Tenant & User Management Domain** - **21 tables** requiring FK constraints:
- **16 tables**: Both `created_by` AND `updated_by` Foreign Keys (32 FKs)
- **5 tables**: Only `created_by` Foreign Key (5 FKs)
- **Total**: 37 Foreign Key constraints

**Key Principle:** Phase 6.0.1 uses **9 separate Alembic migrations** (one per functional domain) for surgical rollback capability, optimized task sizing (~15-21 tables per task), and keeping AI agent context usage at 50-60%.

---

## What Was Completed in Previous Phases

**Phase 6.0.1 Task 5 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 30 FK constraints added for Billing & Payments domain (12 tables × 2 + 6 tables × 1)
- ✅ 0 orphaned audit references found
- ✅ 794/794 unit tests, 821/821 total tests passing (100%)

**Current Baseline:** 794/794 unit tests, 821/821 total tests passing (100%)

**Previous Tasks:**
- **Task 1**: ✅ COMPLETE - Common & Reference Tables (20 tables, 39 FKs)
- **Task 2**: ✅ COMPLETE - Customer & Site Management (12 tables, 23 FKs)
- **Task 3**: ✅ COMPLETE - Job Management (12 tables, 23 FKs)
- **Task 4**: ✅ COMPLETE - Quoting System (12 tables, 19 FKs)
- **Task 5**: ✅ COMPLETE - Billing & Payments (18 tables, 30 FKs)

**See:**
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` for master plan
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` for comprehensive FK requirements

---

## Current Task: Tenant & User Management FK Constraints

**Effort:** 3-4 hours (estimated)
**Gap Reference:** Phase 6.0.1 Analysis - Audit Trail Foreign Key Constraints - Task 6
**Change Type:** MODEL VERIFICATION + MIGRATION + DATA VALIDATION + TESTING

This task adds Foreign Key constraints to all audit columns in the **Tenant & User Management** domain. These are critical tables that manage multi-tenancy, user memberships, and authentication - the foundation of the entire application's security and data isolation model.

**Special Considerations:**
- The `user` table itself has audit columns that reference `user.id` (self-referential FK)
- Tenant and user tables are high-traffic entities requiring careful migration testing
- User deletion prevention is especially critical in this domain

### What Needs to Be Fixed

**Task 6 Tables - Tenant & User Management Domain (21 tables, 37 FK constraints):**

#### Model Files to Update:

1. **`backend/app/models/core.py`** - Core tenant/user models
   - `tenant_settings` (Both FKs)
   - `user_preference` (Both FKs)
   - `user_endpoint` (Both FKs)

2. **`backend/app/models/auth.py`** - Authentication models
   - `tenant_domain` (Both FKs)
   - `tenant_user` (Both FKs)
   - `tenant_user_status` (Both FKs)
   - `tenant_user_role` (Both FKs)
   - `tenant_user_notification_pref` (Both FKs)
   - `user_sso_identity` (Both FKs)
   - `tenant_user_invite` (Created only - append-only)

3. **`backend/app/models/billing.py`** - Feature management
   - `tenant_product_feature_override` (Both FKs)

4. **`backend/app/models/system.py`** - Notification defaults
   - `tenant_notification_default` (Both FKs)

5. **`backend/app/models/catalog.py`** - Pricing versioning
   - `tenant_markup_version` (Created only - versioned)

**Tables with BOTH created_by AND updated_by (16 tables = 32 FKs):**
1. `tenant_settings` - Tenant configuration
2. `tenant_domain` - Custom domain mappings
3. `tenant_user` - User-tenant memberships
4. `tenant_user_status` - User status lookup
5. `tenant_user_role` - User role assignments
6. `tenant_user_notification_pref` - Notification preferences
7. `tenant_notification_default` - Default notification settings
8. `tenant_product_feature_override` - Feature flag overrides
9. `user_preference` - User preferences
10. `user_endpoint` - User communication endpoints
11. `user_sso_identity` - SSO identity mappings
12. `user` - **Core user table (self-referential FK)** ⚠️
13. `tenant` - **Core tenant table** ⚠️
14. `platform_role` - **Already completed in Task 1** ✅
15-16. **[To be identified from models]**

**Tables with ONLY created_by (5 tables = 5 FKs):**
1. `tenant_user_invite` - Append-only invite log
2. `tenant_markup_version` - Markup pricing version history
3-5. **[To be identified from models]**

**⚠️ CRITICAL NOTES:**
- `user` table has self-referential audit columns (created_by → user.id, updated_by → user.id)
- `tenant` table audit columns also reference user.id
- These require string-based FK references: `foreign_key="user.id"` not `foreign_key=User.id`

### Model Location Reference

For detailed model organization, see:
- `backend/db_models_map.md` - Complete map of all models by file
- `backend/app_model_imports.md` - Import patterns for all models

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

**Record the output of both results:** `794/794 & 821/821 tests passing` (Phase 6.0.1 Task 5 baseline)

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

**Example for Task 6 Tables:**
```sql
-- Check all Task 6 tables for orphaned created_by
SELECT 'tenant_settings' as table_name, created_by, COUNT(*) as count
FROM tenant_settings
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_settings.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_domain', created_by, COUNT(*)
FROM tenant_domain
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_domain.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_user', created_by, COUNT(*)
FROM tenant_user
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user.created_by)
GROUP BY created_by
UNION ALL
SELECT 'user', created_by, COUNT(*)
FROM "user"
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM u2 WHERE id = "user".created_by AND u2.id != "user".id)
GROUP BY created_by
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

**Task 6 Position in Overall Strategy:**
- This is migration **6 of 9**
- Covers Tenant & User Management domain
- 21 tables, 37 FK constraints
- HIGH priority due to core security/isolation impact

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

class TenantSettings(SQLModel, table=True):
    __tablename__ = "tenant_settings"
    
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
"""Phase 6.0.1 Task 6: FK constraints for Tenant & User Management tables

Revision ID: phase_6_0_1_task_6_fk_audit_tenant
Revises: phase_6_0_1_task_5_fk_audit_billing
Create Date: 2026-04-13
"""

def upgrade():
    # For tables with BOTH created_by and updated_by
    for table_name in [
        'tenant_settings', 'tenant_domain', 'tenant_user', 
        'tenant_user_status', 'tenant_user_role',
        'tenant_user_notification_pref', 'tenant_notification_default',
        'tenant_product_feature_override', 'user_preference',
        'user_endpoint', 'user_sso_identity', 'user', 'tenant'
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
    for table_name in ['tenant_user_invite', 'tenant_markup_version']:
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
    for table_name in ['tenant_user_invite', 'tenant_markup_version']:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'tenant_settings', 'tenant_domain', 'tenant_user',
        'tenant_user_status', 'tenant_user_role',
        'tenant_user_notification_pref', 'tenant_notification_default',
        'tenant_product_feature_override', 'user_preference',
        'user_endpoint', 'user_sso_identity', 'user', 'tenant'
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
    from app.models.core import TenantSettings
    
    # Attempt to create record with non-existent user ID
    invalid_user_id = uuid.uuid4()
    settings = TenantSettings(
        tenant_id=test_tenant.id,
        created_by=invalid_user_id  # Invalid user ID
    )
    db_session.add(settings)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_tenant_settings_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing User Deletion Prevention:**
```python
def test_user_deletion_prevented_by_audit_trail(db_session, test_user, test_tenant):
    """Test that user cannot be deleted if audit references exist"""
    from app.models.core import TenantSettings
    
    # Create record with user audit reference
    settings = TenantSettings(
        tenant_id=test_tenant.id,
        created_by=test_user.id
    )
    db_session.add(settings)
    db_session.commit()
    
    # Attempt to delete user (should fail due to RESTRICT)
    db_session.delete(test_user)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_tenant_settings_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing NULL Audit Columns (Backward Compatibility):**
```python
def test_null_audit_columns_allowed(db_session, test_tenant):
    """Test that NULL audit columns are allowed for backward compatibility"""
    from app.models.core import TenantSettings
    
    # Create record with NULL audit columns
    settings = TenantSettings(
        tenant_id=test_tenant.id,
        created_by=None,  # NULL allowed
        updated_by=None
    )
    db_session.add(settings)
    db_session.commit()  # Should succeed
    
    assert settings.created_by is None
    assert settings.updated_by is None
```

---

## Requirements

### Phase 6.0.1 Task 6 Breakdown

Phase 6.0.1 Task 6 focuses on **Tenant & User Management** domain tables.

#### Task 6: Tenant & User Management FK Constraints (Migration 6 of 9)

**Scope:**
- 21 tables total
- 16 tables with BOTH `created_by` AND `updated_by` FKs
- 5 tables with ONLY `created_by` FK (append-only/versioned)
- **Total**: 37 Foreign Key constraints

**Tables in This Task:**

**Tables with BOTH FKs (16 tables = 32 FKs):**
1. `tenant_settings` - Tenant configuration
2. `tenant_domain` - Custom domain mappings
3. `tenant_user` - User-tenant memberships
4. `tenant_user_status` - User status lookup
5. `tenant_user_role` - User role assignments
6. `tenant_user_notification_pref` - Notification preferences
7. `tenant_notification_default` - Default notification settings
8. `tenant_product_feature_override` - Feature flag overrides
9. `user_preference` - User preferences
10. `user_endpoint` - User communication endpoints
11. `user_sso_identity` - SSO identity mappings
12. `user` - Core user table ⚠️ (self-referential)
13. `tenant` - Core tenant table ⚠️
14-16. **[Verify from models if additional tables exist]**

**Tables with ONLY created_by (5 tables = 5 FKs):**
1. `tenant_user_invite` - Append-only invite log
2. `tenant_markup_version` - Markup pricing version history
3-5. **[Verify from models if additional tables exist]**

**Migration Pattern:**
```python
"""Phase 6.0.1 Task 6: FK constraints for Tenant & User Management audit columns

Revision ID: phase_6_0_1_task_6_fk_audit_tenant
Revises: phase_6_0_1_task_5_fk_audit_billing
Create Date: 2026-04-13
"""

def upgrade():
    # Add FK constraints for tables with both created_by and updated_by
    for table_name in [
        'tenant_settings', 'tenant_domain', 'tenant_user',
        'tenant_user_status', 'tenant_user_role',
        'tenant_user_notification_pref', 'tenant_notification_default',
        'tenant_product_feature_override', 'user_preference',
        'user_endpoint', 'user_sso_identity', 'user', 'tenant'
        # [ADD_REMAINING_TABLES_WITH_BOTH_FKS]
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
        'tenant_user_invite', 'tenant_markup_version'
        # [ADD_REMAINING_TABLES_WITH_CREATED_ONLY]
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
        'tenant_user_invite', 'tenant_markup_version'
        # [SAME_LIST_AS_UPGRADE]
    ]:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'tenant_settings', 'tenant_domain', 'tenant_user',
        'tenant_user_status', 'tenant_user_role',
        'tenant_user_notification_pref', 'tenant_notification_default',
        'tenant_product_feature_override', 'user_preference',
        'user_endpoint', 'user_sso_identity', 'user', 'tenant'
        # [SAME_LIST_AS_UPGRADE]
    ]:
        op.drop_constraint(f'fk_{table_name}_updated_by', table_name, type_='foreignkey')
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
```

---

### Task 1: SQLModel Schema Definitions Verification

**Effort:** 1-1.5 hours
**Scope:** Verify FK definitions across 21 tables in Task 6

#### What This Task Accomplishes

Confirm that all Phase 6.0.1 Task 6 changes are correctly defined in the Python SQLModel definitions. Update models with FK constraints on audit columns.

#### Tables to Check (Task 6 - Tenant & User Management)

**Model Files & Required Changes:**

1. **`backend/app/models/core.py`**
   - `Tenant`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `User`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` ⚠️ (self-referential)
   - `TenantSettings`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `UserPreference`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `UserEndpoint`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`

2. **`backend/app/models/auth.py`**
   - `TenantDomain`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `TenantUser`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `TenantUserStatus`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `TenantUserRole`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `TenantUserNotificationPref`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `UserSsoIdentity`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`
   - `TenantUserInvite`: Add `foreign_key="user.id"` to `created_by` only (append-only)

3. **`backend/app/models/billing.py`**
   - `TenantProductFeatureOverride`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`

4. **`backend/app/models/system.py`**
   - `TenantNotificationDefault`: Add `foreign_key="user.id"` to both `created_by` and `updated_by`

5. **`backend/app/models/catalog.py`**
   - `TenantMarkupVersion`: Add `foreign_key="user.id"` to `created_by` only (versioned)

**Verify remaining tables from model files to ensure all 21 tables are covered.**

#### SQLModel Syntax Examples

**Standard Table Pattern:**
```python
from typing import Optional
import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel

class TenantSettings(SQLModel, table=True):
    __tablename__ = "tenant_settings"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    
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

**Self-Referential Pattern (User table):**
```python
class User(SQLModel, table=True):
    __tablename__ = "user"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str
    
    # ✅ CORRECT - Self-referential audit columns
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",  # ← String reference for self-referential
        sa_column_kwargs={"ondelete": "RESTRICT"}
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",  # ← String reference for self-referential
        sa_column_kwargs={"ondelete": "RESTRICT"}
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Success Criteria for Task 1:**
- [ ] All 21 tables in Task 6 have FK definitions added
- [ ] All FKs use string reference `"user.id"` not class reference
- [ ] All FKs specify `sa_column_kwargs={"ondelete": "RESTRICT"}`
- [ ] All audit columns remain `Optional[uuid.UUID]` (NULL support)
- [ ] Self-referential FKs on `user` and `tenant` tables use string references
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models import *"`)

---

### Task 2: Pre-Migration Data Validation

**Effort:** 0.5-1 hour
**Dependencies:** None (can run independently)
**CRITICAL:** Validation MUST pass before generating migration

#### What This Task Accomplishes

Verify that the database is ready for Phase 6.0.1 Task 6 migration by checking for orphaned audit references that would prevent FK constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation: Orphaned Audit References (MANDATORY)**

```sql
-- Check for orphaned created_by references in Task 6 tables
SELECT 'tenant_settings' as table_name, created_by, COUNT(*) as count
FROM tenant_settings
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_settings.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_domain', created_by, COUNT(*)
FROM tenant_domain
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_domain.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_user', created_by, COUNT(*)
FROM tenant_user
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_user_status', created_by, COUNT(*)
FROM tenant_user_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_user_role', created_by, COUNT(*)
FROM tenant_user_role
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user_role.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_user_notification_pref', created_by, COUNT(*)
FROM tenant_user_notification_pref
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user_notification_pref.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_notification_default', created_by, COUNT(*)
FROM tenant_notification_default
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_notification_default.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_product_feature_override', created_by, COUNT(*)
FROM tenant_product_feature_override
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_product_feature_override.created_by)
GROUP BY created_by
UNION ALL
SELECT 'user_preference', created_by, COUNT(*)
FROM user_preference
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = user_preference.created_by)
GROUP BY created_by
UNION ALL
SELECT 'user_endpoint', created_by, COUNT(*)
FROM user_endpoint
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = user_endpoint.created_by)
GROUP BY created_by
UNION ALL
SELECT 'user_sso_identity', created_by, COUNT(*)
FROM user_sso_identity
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = user_sso_identity.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_user_invite', created_by, COUNT(*)
FROM tenant_user_invite
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user_invite.created_by)
GROUP BY created_by
UNION ALL
SELECT 'tenant_markup_version', created_by, COUNT(*)
FROM tenant_markup_version
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_markup_version.created_by)
GROUP BY created_by
UNION ALL
-- Self-referential check for user table
SELECT 'user', created_by, COUNT(*)
FROM "user" u1
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" u2 WHERE u2.id = u1.created_by)
GROUP BY created_by
UNION ALL
-- Check tenant table
SELECT 'tenant', created_by, COUNT(*)
FROM tenant
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant.created_by)
GROUP BY created_by
;
-- Expected: 0 rows (no orphaned references)

-- Check for orphaned updated_by references (only for tables with updated_by)
SELECT 'tenant_settings' as table_name, updated_by, COUNT(*) as count
FROM tenant_settings
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_settings.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'tenant_domain', updated_by, COUNT(*)
FROM tenant_domain
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_domain.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'tenant_user', updated_by, COUNT(*)
FROM tenant_user
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'tenant_user_status', updated_by, COUNT(*)
FROM tenant_user_status
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user_status.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'tenant_user_role', updated_by, COUNT(*)
FROM tenant_user_role
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user_role.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'tenant_user_notification_pref', updated_by, COUNT(*)
FROM tenant_user_notification_pref
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_user_notification_pref.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'tenant_notification_default', updated_by, COUNT(*)
FROM tenant_notification_default
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_notification_default.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'tenant_product_feature_override', updated_by, COUNT(*)
FROM tenant_product_feature_override
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant_product_feature_override.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'user_preference', updated_by, COUNT(*)
FROM user_preference
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = user_preference.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'user_endpoint', updated_by, COUNT(*)
FROM user_endpoint
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = user_endpoint.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'user_sso_identity', updated_by, COUNT(*)
FROM user_sso_identity
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = user_sso_identity.updated_by)
GROUP BY updated_by
UNION ALL
-- Self-referential check for user table
SELECT 'user', updated_by, COUNT(*)
FROM "user" u1
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" u2 WHERE u2.id = u1.updated_by)
GROUP BY updated_by
UNION ALL
-- Check tenant table
SELECT 'tenant', updated_by, COUNT(*)
FROM tenant
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = tenant.updated_by)
GROUP BY updated_by
;
-- Expected: 0 rows (no orphaned references)
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

**Effort:** 1-1.5 hours
**Dependencies:** Task 1 (models) and Task 2 (validation) must be complete
**Migration:** 6 of 9

#### What This Task Accomplishes

Generate and apply Alembic migration with FK constraints for all tables in Task 6.

#### Implementation Steps

**Step 1: Generate Migration Skeleton**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_1_task_6_fk_audit_tenant"
```

**Step 2: Manually Construct Complete Migration**

Use the migration pattern from Requirements section above. Ensure all 21 tables are included.

**Step 3: Apply Migration**
```bash
alembic upgrade head
```

**Step 4: Verify Database State**
```sql
-- Verify FK constraints exist for Task 6 tables
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
    'tenant_settings', 'tenant_domain', 'tenant_user',
    'tenant_user_status', 'tenant_user_role',
    'tenant_user_notification_pref', 'tenant_notification_default',
    'tenant_product_feature_override', 'user_preference',
    'user_endpoint', 'user_sso_identity', 'tenant_user_invite',
    'tenant_markup_version', 'user', 'tenant'
    -- [ADD_REMAINING_TABLES]
  )
  AND kcu.column_name IN ('created_by', 'updated_by')
  AND ccu.table_name = 'user'
ORDER BY tc.table_name, kcu.column_name;
-- Expected: 37 rows (16 tables × 2 FKs + 5 tables × 1 FK)
```

**Step 5: Test Migration Rollback**
```bash
alembic downgrade -1
# Verify FK constraints removed
alembic upgrade head
```

**Success Criteria for Task 3:**
- [ ] Migration created with all 37 FK constraints
- [ ] Migration applies successfully
- [ ] All verification queries pass
- [ ] Migration rolls back successfully
- [ ] Migration re-applies successfully

---

### Task 4: Comprehensive Testing

**Effort:** 1-1.5 hours
**Dependencies:** Task 3 must be complete

#### What This Task Accomplishes

Validate that all Phase 6.0.1 Task 6 FK constraints work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_1_task_6_audit_fk.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0.1 Task 6 - Tenant & User Management Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: phase-6.0-db-schema-sync-11-plan.md - Task 6
"""
import pytest
from sqlalchemy.exc import IntegrityError
import uuid


class TestAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""
    
    def test_tenant_settings_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        from app.models.core import TenantSettings
        
        invalid_user_id = uuid.uuid4()
        settings = TenantSettings(
            tenant_id=test_tenant.id,
            created_by=invalid_user_id
        )
        db_session.add(settings)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_tenant_settings_created_by" in str(exc_info.value)
        db_session.rollback()
    
    def test_tenant_user_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected for tenant_user"""
        from app.models.auth import TenantUser
        
        invalid_user_id = uuid.uuid4()
        tenant_user = TenantUser(
            tenant_id=test_tenant.id,
            user_id=uuid.uuid4(),  # Would also fail FK but created_by is first
            created_by=invalid_user_id
        )
        db_session.add(tenant_user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        # May fail on created_by or user_id FK, both acceptable
        assert "fk_tenant_user" in str(exc_info.value)
        db_session.rollback()
    
    # Add tests for other tables...


class TestAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""
    
    def test_tenant_settings_updated_by_fk_enforcement(self, db_session, test_tenant, test_user):
        """Test that invalid updated_by user ID is rejected"""
        from app.models.core import TenantSettings
        
        # Create valid record
        settings = TenantSettings(
            tenant_id=test_tenant.id,
            created_by=test_user.id
        )
        db_session.add(settings)
        db_session.commit()
        
        # Attempt to update with invalid user ID
        invalid_user_id = uuid.uuid4()
        settings.updated_by = invalid_user_id
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_tenant_settings_updated_by" in str(exc_info.value)
        db_session.rollback()
    
    # Add tests for other tables...


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""
    
    def test_user_deletion_blocked_by_tenant_settings_audit(self, db_session, test_tenant, test_user):
        """Test ON DELETE RESTRICT behavior"""
        from app.models.core import TenantSettings
        
        # Create record with user audit reference
        settings = TenantSettings(
            tenant_id=test_tenant.id,
            created_by=test_user.id
        )
        db_session.add(settings)
        db_session.commit()
        
        # Attempt to delete user (should fail due to RESTRICT)
        db_session.delete(test_user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_tenant_settings_created_by" in str(exc_info.value)
        db_session.rollback()
    
    # Add tests for other tables...


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""
    
    def test_tenant_settings_null_audit_columns(self, db_session, test_tenant):
        """Test that NULL created_by and updated_by are allowed"""
        from app.models.core import TenantSettings
        
        # Create record with NULL audit columns
        settings = TenantSettings(
            tenant_id=test_tenant.id,
            created_by=None,
            updated_by=None
        )
        db_session.add(settings)
        db_session.commit()  # Should succeed
        
        assert settings.created_by is None
        assert settings.updated_by is None
    
    # Add tests for other tables...


class TestSelfReferentialFK:
    """Test self-referential FK on user table"""
    
    def test_user_self_referential_created_by(self, db_session, test_tenant, test_user):
        """Test that user.created_by can reference another user"""
        from app.models.core import User
        
        # Create new user with test_user as creator
        new_user = User(
            email="newuser@example.com",
            tenant_id=test_tenant.id,
            created_by=test_user.id  # Valid reference to existing user
        )
        db_session.add(new_user)
        db_session.commit()  # Should succeed
        
        assert new_user.created_by == test_user.id
    
    def test_user_self_referential_invalid_created_by(self, db_session, test_tenant):
        """Test that user.created_by FK is enforced"""
        from app.models.core import User
        
        invalid_user_id = uuid.uuid4()
        new_user = User(
            email="newuser@example.com",
            tenant_id=test_tenant.id,
            created_by=invalid_user_id  # Invalid user reference
        )
        db_session.add(new_user)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "fk_user_created_by" in str(exc_info.value)
        db_session.rollback()
    
    # Add similar tests for tenant table...


class TestAppendOnlyTables:
    """Test append-only tables (created_by only)"""
    
    def test_tenant_user_invite_created_by_only(self, db_session, test_tenant, test_user):
        """Test that tenant_user_invite has created_by FK but no updated_by"""
        from app.models.auth import TenantUserInvite
        
        # Create invite with valid created_by
        invite = TenantUserInvite(
            tenant_id=test_tenant.id,
            email="invite@example.com",
            created_by=test_user.id
        )
        db_session.add(invite)
        db_session.commit()  # Should succeed
        
        assert invite.created_by == test_user.id
        # Verify no updated_by column (append-only)
        assert not hasattr(invite, 'updated_by') or invite.updated_by is None
    
    # Add tests for tenant_markup_version...
```

**Success Criteria for Task 4:**
- [ ] Test file created with all test categories
- [ ] FK enforcement tests prevent invalid user IDs
- [ ] User deletion prevention tests work correctly
- [ ] NULL audit column tests verify backward compatibility
- [ ] Self-referential FK tests validate user/tenant tables
- [ ] Append-only table tests confirm created_by-only constraints
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
# Expected: 794+ passed (794 baseline + new tests for Task 6)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 821+ passed (821 baseline + new tests for Task 6)
```

### Step 2: Verify Database State

Run all verification queries from Task 3 to confirm 37 FK constraints exist and match expectations.

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
### Phase 6.0.1 Task 6: Tenant & User Management FK Constraints - ✅ COMPLETE

**Status:** ✅ COMPLETE (2026-04-13)
**Effort:** [ACTUAL_HOURS] hours (actual vs 3-4 hours estimated)
**Priority:** HIGH

**Implementation Summary:**

- ✅ Model Updates: Updated 21 tables across 5 model files (core.py, auth.py, billing.py, system.py, catalog.py)
- ✅ Data Validation: Pre-migration orphan detection passed - 0 orphaned audit references found
- ✅ Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_1_task_6_fk_audit_tenant.py`]
- ✅ Test Suite: [`test_phase_6_0_1_task_6_audit_fk.py`] - [N] tests ✅
- ✅ Final Results: [NEW_UNIT]/[NEW_UNIT] unit tests (100%), [NEW_TOTAL]/[NEW_TOTAL] total tests (100%)

**Key Changes Completed:**
- ✅ 37 Foreign Key constraints added (16 tables × 2 + 5 tables × 1)
- ✅ All FKs use ON DELETE RESTRICT behavior
- ✅ Zero orphaned audit references found
- ✅ Self-referential FKs on user and tenant tables working correctly
- ✅ Migration rollback tested and validated
- ✅ User