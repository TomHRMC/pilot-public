# Task 9: Auth Security - Audit FK Constraints

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - Task 9
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

---

## What Was Completed in Previous Phases

**Phase 6.0 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 14 multi-tenant unique constraints + 5 business logic constraints
- ✅ 2 audit columns added (conversation_session: created_by, updated_by)
- ✅ 5 partial indexes + 1 GiST exclusion constraint
- ✅ 14 composite/sorting indexes + 1 redundant index removed
- ✅ All previous Task 1-8 FK migrations have been applied
- ✅ `subscription` and `usage_ledger` tables originally listed for Task 9 were completed early during Task 5.

**Current Baseline:** Use the testing instructions below to establish the baseline for this task.

**See:**
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` for Phase 6.0.1 history

---

## Current Task: Task 9 - Auth Security FK Constraints

**Effort:** 1.5 hours
**Gap Reference:** Phase 6.0.1 Analysis - Audit Trail Foreign Key Constraints
**Change Type:** MODEL VERIFICATION | MIGRATION + DATA VALIDATION | TESTING

This task completes Phase 6.0.1 by adding the final remaining audit FK constraints to the system's authentication and security tables. It focuses strictly on the append-only security logs and token tables to guarantee the integrity of security tracking data.

### What Needs to Be Fixed

**Scope:** 6 tables requiring FK constraints on audit columns
- All 6 tables: Only `created_by` FK (append-only security tables)

**Tables Included (all in `backend/app/models/auth.py`):**
1. `auth_api_token` - Created only
2. `auth_email_verification` - Created only
3. `auth_password_reset` - Created only
4. `auth_password_history` - Created only
5. `auth_mfa_otp` - Created only
6. `auth_jwk` - Created only

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

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 6.0.1 Specific Warnings

**BEFORE writing ANY code, review these Phase 6.0.1 critical issues:**

### 1. Orphaned Audit References - Pre-Migration Validation is MANDATORY

**CRITICAL:** Before creating FK constraints on `created_by` columns, you MUST verify no orphaned references exist.

**Validation Queries (MANDATORY for ALL 6 tables in your task):**

```sql
SELECT 'auth_api_token' as table_name, created_by, COUNT(*) as count
FROM auth_api_token
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = auth_api_token.created_by)
GROUP BY created_by
UNION ALL
SELECT 'auth_email_verification', created_by, COUNT(*)
FROM auth_email_verification
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = auth_email_verification.created_by)
GROUP BY created_by
UNION ALL
SELECT 'auth_password_reset', created_by, COUNT(*)
FROM auth_password_reset
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = auth_password_reset.created_by)
GROUP BY created_by
UNION ALL
SELECT 'auth_password_history', created_by, COUNT(*)
FROM auth_password_history
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = auth_password_history.created_by)
GROUP BY created_by
UNION ALL
SELECT 'auth_mfa_otp', created_by, COUNT(*)
FROM auth_mfa_otp
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = auth_mfa_otp.created_by)
GROUP BY created_by
UNION ALL
SELECT 'auth_jwk', created_by, COUNT(*)
FROM auth_jwk
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = auth_jwk.created_by)
GROUP BY created_by;
-- Expected: 0 rows total
```

### 2. Foreign Key Constraint Behavior: ON DELETE RESTRICT

**CRITICAL:** All FK constraints in Phase 6.0.1 use `ON DELETE RESTRICT` behavior.

```python
# CORRECT pattern for this phase
created_by: Optional[uuid.UUID] = Field(
    default=None,
    sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
)
```

### 3. Circular Dependency Handling for User Table

Always use string reference `"user.id"` not class reference `User.id`.

### 4. NULL Support for Backward Compatibility

All audit columns must remain `Optional[uuid.UUID]` with `default=None`.

### 5. Alembic Migration Pattern for FK Constraints

**Correct Migration Pattern:**
```python
"""Phase 6.0.1 Task 9: FK constraints for auth security tables

Revision ID: phase_6_0_1_task_9_fk_audit_auth
Revises: [PREVIOUS_REVISION]
Create Date: 2026-04-13
"""

def upgrade():
    # For append-only tables (created_by only)
    for table_name in [
        'auth_api_token', 'auth_email_verification', 'auth_password_reset',
        'auth_password_history', 'auth_mfa_otp', 'auth_jwk'
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
        'auth_jwk', 'auth_mfa_otp', 'auth_password_history',
        'auth_password_reset', 'auth_email_verification', 'auth_api_token'
    ]:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
```

---

## Requirements

### Task 1: SQLModel Schema Definitions Verification

**Scope:** Verify FK definitions across tables in `auth.py`

**Model Files & Required Changes:**
1. `backend/app/models/auth.py`
   - `AuthApiToken`: Override `created_by`
   - `AuthEmailVerification`: Override `created_by`
   - `AuthPasswordReset`: Override `created_by`
   - `AuthPasswordHistory`: Override `created_by`
   - `AuthMfaOtp`: Override `created_by`
   - `AuthJwk`: Override `created_by`

**Note:** Ensure you only add `created_by` overrides since these inherit from `AppendOnlyMixin` which only tracks `created_by`.

### Task 2: Pre-Migration Data Validation

Run the validation query from the Warnings section above using the `postgres-local` MCP server to ensure 0 orphaned records.

### Task 3: Migration Creation & Application

Generate and apply Alembic migration with FK constraints for all 6 tables in this task. Test downgrade and re-upgrade.

### Task 4: Comprehensive Testing

Create `backend/tests/test_phase_6_0_1_task_9_audit_fk.py` to validate:
- Valid `created_by` is accepted
- Invalid `created_by` is rejected
- User deletion is prevented (RESTRICT behavior)
- NULL values are accepted (backward compatibility)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
```

### Step 2: Final Validation

Ensure 100% test pass rate with NO REGRESSIONS from your baseline.

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md`

Add implementation status for Task 9.

---

## Key Files to Review

### Important Reference Docs for App Models ⭐
- `backend/db_models_map.md` - Details where models are located within `backend/app/models/`
- `backend/app_model_imports.md` - Details how to properly import models across the application

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - Master Plan
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - FK Requirements Analysis

### Backend Models (6 tables in this task)
- `backend/app/models/auth.py`

---

**Ready to Begin!** 🚀
