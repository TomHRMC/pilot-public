# Task 5: Billing & Payments FK Constraints - Audit FK Constraints

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - Task 5
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **Audit FK Constraints Analysis** ⭐
- Current Live Database (Phase 6.0.1 Post-Task 4 State)
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

**Phase 6.0.1 Task 4 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 19 Foreign Key constraints added (7 tables × 2 + 5 tables × 1)
- ✅ All quoting system tables (quote, quote_status, quote_line, etc.)
- ✅ All FKs use ON DELETE RESTRICT behavior
- ✅ Zero orphaned audit references found
- ✅ 781/781 unit tests, 808/808 total tests passing (100%)

**Current Baseline:** 781/781 unit tests, 808/808 total tests passing (100%)

**Previous Tasks:**
- **Phase 6.0.1 Task 1:** ✅ COMPLETE - Common & Reference Tables (39 FKs, 20 tables)
- **Phase 6.0.1 Task 2:** ✅ COMPLETE - Customer & Site Management (23 FKs, 12 tables)
- **Phase 6.0.1 Task 3:** ✅ COMPLETE - Job Management (23 FKs, 12 tables)
- **Phase 6.0.1 Task 4:** ✅ COMPLETE - Quoting System (19 FKs, 12 tables)

**See:**
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` for Phase 6.0.1 history
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` for comprehensive FK requirements

---

## Current Task: Billing & Payments FK Constraints

**Effort:** 3-4 hours
**Gap Reference:** Phase 6.0.1 Analysis - Audit Trail Foreign Key Constraints
**Change Type:** MODEL VERIFICATION + MIGRATION + DATA VALIDATION + TESTING

This task adds Foreign Key constraints to **18 billing and payment-related tables**, ensuring all financial transactions have complete audit trail integrity with database-level referential enforcement. This is critical for financial compliance (SOC 2, GDPR) and preventing orphaned audit records in the payment processing pipeline.

### What Needs to Be Fixed

**Model Files & Required Changes:**

**File:** `backend/app/models/billing.py`

**Tables with BOTH created_by AND updated_by FKs (12 tables):**

1. **`invoice`** - Core invoice entity
   - Add `foreign_key="user.id"` to `created_by`
   - Add `foreign_key="user.id"` to `updated_by`
   - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

2. **`invoice_status`** - Invoice status lookup
   - Add `foreign_key="user.id"` to `created_by`
   - Add `foreign_key="user.id"` to `updated_by`
   - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

3. **`payment`** - Payment records
   - Add `foreign_key="user.id"` to `created_by`
   - Add `foreign_key="user.id"` to `updated_by`
   - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

4. **`payment_status`** - Payment status lookup
   - Add `foreign_key="user.id"` to `created_by`
   - Add `foreign_key="user.id"` to `updated_by`
   - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

5. **`payment_type`** - Payment type lookup
   - Add `foreign_key="user.id"` to `created_by`
   - Add `foreign_key="user.id"` to `updated_by`
   - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

6. **`payment_method`** - Stored payment methods
   - Add `foreign_key="user.id"` to `created_by`
   - Add `foreign_key="user.id"` to `updated_by`
   - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

7. **`psp_customer`** - Payment provider customer mapping
   - Add `foreign_key="user.id"` to `created_by`
   - Add `foreign_key="user.id"` to `updated_by`
   - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

8. **`subscription`** - Tenant subscriptions
   - Add `foreign_key="user.id"` to `created_by`
   - Add `foreign_key="user.id"` to `updated_by`
   - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

9. **`subscription_status`** - Subscription status lookup
   - Add `foreign_key="user.id"` to `created_by`
   - Add `foreign_key="user.id"` to `updated_by`
   - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

10. **`subscription_usage`** - Usage tracking
    - Add `foreign_key="user.id"` to `created_by`
    - Add `foreign_key="user.id"` to `updated_by`
    - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

11. **`product_plan`** - Subscription plans
    - Add `foreign_key="user.id"` to `created_by`
    - Add `foreign_key="user.id"` to `updated_by`
    - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

12. **`product_feature`** - Feature registry
    - Add `foreign_key="user.id"` to `created_by`
    - Add `foreign_key="user.id"` to `updated_by`
    - Both with `sa_column_kwargs={"ondelete": "RESTRICT"}`

**Tables with ONLY created_by FK (6 tables - append-only/transactional):**

13. **`invoice_line`** - Invoice line items (append-only)
    - Add `foreign_key="user.id"` to `created_by`
    - With `sa_column_kwargs={"ondelete": "RESTRICT"}`

14. **`invoice_line_tax_component`** - Tax breakdown (append-only)
    - Add `foreign_key="user.id"` to `created_by`
    - With `sa_column_kwargs={"ondelete": "RESTRICT"}`

15. **`psp_transaction_log`** - Payment transaction log (append-only)
    - Add `foreign_key="user.id"` to `created_by`
    - With `sa_column_kwargs={"ondelete": "RESTRICT"}`

16. **`usage_ledger`** - Usage tracking ledger (append-only)
    - Add `foreign_key="user.id"` to `created_by`
    - With `sa_column_kwargs={"ondelete": "RESTRICT"}`

17. **`product_plan_version`** - Plan version history (append-only)
    - Add `foreign_key="user.id"` to `created_by`
    - With `sa_column_kwargs={"ondelete": "RESTRICT"}`

18. **`product_plan_product_feature_version`** - Feature version history (append-only)
    - Add `foreign_key="user.id"` to `created_by`
    - With `sa_column_kwargs={"ondelete": "RESTRICT"}`

**Model Location References:**
- See `backend/db_models_map.md` for model file locations
- See `backend/app_model_imports.md` for proper import syntax

**Total FK Constraints for Task 5:** 30 Foreign Keys (12 tables × 2 + 6 tables × 1)

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

**Record the output of both results:** `781/781 & 808/808 tests passing` (Phase 6.0.1 Task 4 baseline)

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

**Example for Task 5 Tables:**
```sql
-- Check all tables in Task 5 for orphaned created_by
SELECT 'invoice' as table_name, created_by, COUNT(*) as count
FROM invoice
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = invoice.created_by)
GROUP BY created_by
UNION ALL
SELECT 'invoice_status', created_by, COUNT(*)
FROM invoice_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = invoice_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'payment', created_by, COUNT(*)
FROM payment
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = payment.created_by)
GROUP BY created_by
UNION ALL
SELECT 'payment_status', created_by, COUNT(*)
FROM payment_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = payment_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'payment_type', created_by, COUNT(*)
FROM payment_type
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = payment_type.created_by)
GROUP BY created_by
UNION ALL
SELECT 'payment_method', created_by, COUNT(*)
FROM payment_method
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = payment_method.created_by)
GROUP BY created_by
UNION ALL
SELECT 'psp_customer', created_by, COUNT(*)
FROM psp_customer
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = psp_customer.created_by)
GROUP BY created_by
UNION ALL
SELECT 'subscription', created_by, COUNT(*)
FROM subscription
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = subscription.created_by)
GROUP BY created_by
UNION ALL
SELECT 'subscription_status', created_by, COUNT(*)
FROM subscription_status
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = subscription_status.created_by)
GROUP BY created_by
UNION ALL
SELECT 'subscription_usage', created_by, COUNT(*)
FROM subscription_usage
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = subscription_usage.created_by)
GROUP BY created_by
UNION ALL
SELECT 'product_plan', created_by, COUNT(*)
FROM product_plan
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = product_plan.created_by)
GROUP BY created_by
UNION ALL
SELECT 'product_feature', created_by, COUNT(*)
FROM product_feature
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = product_feature.created_by)
GROUP BY created_by
UNION ALL
SELECT 'invoice_line', created_by, COUNT(*)
FROM invoice_line
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = invoice_line.created_by)
GROUP BY created_by
UNION ALL
SELECT 'invoice_line_tax_component', created_by, COUNT(*)
FROM invoice_line_tax_component
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = invoice_line_tax_component.created_by)
GROUP BY created_by
UNION ALL
SELECT 'psp_transaction_log', created_by, COUNT(*)
FROM psp_transaction_log
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = psp_transaction_log.created_by)
GROUP BY created_by
UNION ALL
SELECT 'usage_ledger', created_by, COUNT(*)
FROM usage_ledger
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = usage_ledger.created_by)
GROUP BY created_by
UNION ALL
SELECT 'product_plan_version', created_by, COUNT(*)
FROM product_plan_version
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = product_plan_version.created_by)
GROUP BY created_by
UNION ALL
SELECT 'product_plan_product_feature_version', created_by, COUNT(*)
FROM product_plan_product_feature_version
WHERE created_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = product_plan_product_feature_version.created_by)
GROUP BY created_by;
-- Expected: 0 rows total

-- Check for orphaned updated_by references (only for tables with updated_by)
SELECT 'invoice' as table_name, updated_by, COUNT(*) as count
FROM invoice
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = invoice.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'invoice_status', updated_by, COUNT(*)
FROM invoice_status
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = invoice_status.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'payment', updated_by, COUNT(*)
FROM payment
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = payment.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'payment_status', updated_by, COUNT(*)
FROM payment_status
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = payment_status.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'payment_type', updated_by, COUNT(*)
FROM payment_type
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = payment_type.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'payment_method', updated_by, COUNT(*)
FROM payment_method
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = payment_method.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'psp_customer', updated_by, COUNT(*)
FROM psp_customer
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = psp_customer.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'subscription', updated_by, COUNT(*)
FROM subscription
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = subscription.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'subscription_status', updated_by, COUNT(*)
FROM subscription_status
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = subscription_status.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'subscription_usage', updated_by, COUNT(*)
FROM subscription_usage
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = subscription_usage.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'product_plan', updated_by, COUNT(*)
FROM product_plan
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = product_plan.updated_by)
GROUP BY updated_by
UNION ALL
SELECT 'product_feature', updated_by, COUNT(*)
FROM product_feature
WHERE updated_by IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM "user" WHERE id = product_feature.updated_by)
GROUP BY updated_by;
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

class Invoice(SQLModel, table=True):
    __tablename__ = "invoice"
    
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
"""Phase 6.0.1 Task 5: FK constraints for Billing & Payments tables

Revision ID: phase_6_0_1_task_5_fk_audit_billing
Revises: phase_6_0_1_task_4_fk_audit_quoting
Create Date: 2026-04-13
"""

def upgrade():
    # For tables with BOTH created_by and updated_by
    for table_name in [
        'invoice', 'invoice_status', 'payment', 'payment_status',
        'payment_type', 'payment_method', 'psp_customer', 'subscription',
        'subscription_status', 'subscription_usage', 'product_plan', 'product_feature'
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
        'invoice_line', 'invoice_line_tax_component', 'psp_transaction_log',
        'usage_ledger', 'product_plan_version', 'product_plan_product_feature_version'
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
        'invoice_line', 'invoice_line_tax_component', 'psp_transaction_log',
        'usage_ledger', 'product_plan_version', 'product_plan_product_feature_version'
    ]:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'invoice', 'invoice_status', 'payment', 'payment_status',
        'payment_type', 'payment_method', 'psp_customer', 'subscription',
        'subscription_status', 'subscription_usage', 'product_plan', 'product_feature'
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
    from app.models.billing import Invoice
    
    # Attempt to create record with non-existent user ID
    invalid_user_id = uuid.uuid4()
    invoice = Invoice(
        tenant_id=test_tenant.id,
        customer_id=uuid.uuid4(),
        created_by=invalid_user_id  # Invalid user ID
    )
    db_session.add(invoice)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_invoice_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing User Deletion Prevention:**
```python
def test_user_deletion_prevented_by_audit_trail(db_session, test_user, test_tenant):
    """Test that user cannot be deleted if audit references exist"""
    from app.models.billing import Invoice
    
    # Create record with user audit reference
    invoice = Invoice(
        tenant_id=test_tenant.id,
        customer_id=uuid.uuid4(),
        created_by=test_user.id
    )
    db_session.add(invoice)
    db_session.commit()
    
    # Attempt to delete user (should fail due to RESTRICT)
    db_session.delete(test_user)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_invoice_created_by" in str(exc_info.value)
    db_session.rollback()
```

**Pattern for Testing NULL Audit Columns (Backward Compatibility):**
```python
def test_null_audit_columns_allowed(db_session, test_tenant):
    """Test that NULL audit columns are allowed for backward compatibility"""
    from app.models.billing import Invoice
    
    # Create record with NULL audit columns
    invoice = Invoice(
        tenant_id=test_tenant.id,
        customer_id=uuid.uuid4(),
        created_by=None,  # NULL allowed
        updated_by=None
    )
    db_session.add(invoice)
    db_session.commit()  # Should succeed
    
    assert invoice.created_by is None
    assert invoice.updated_by is None
```

---

## Requirements

### Phase 6.0.1 Task 5 Breakdown

Phase 6.0.1 Task 5 is the **5th of 9 separate Alembic migrations** for domain isolation and context optimization:

#### Task 5: Billing & Payments FK Constraints (Migration 5)

**Scope:**
- 18 tables total
- 12 tables with BOTH `created_by` AND `updated_by` FKs
- 6 tables with ONLY `created_by` FK (append-only)

**Tables in This Task:**

**Both created_by AND updated_by (12 tables):**
1. `invoice`
2. `invoice_status`
3. `payment`
4. `payment_status`
5. `payment_type`
6. `payment_method`
7. `psp_customer`
8. `subscription`
9. `subscription_status`
10. `subscription_usage`
11. `product_plan`
12. `product_feature`

**Created only (6 tables):**
13. `invoice_line`
14. `invoice_line_tax_component`
15. `psp_transaction_log`
16. `usage_ledger`
17. `product_plan_version`
18. `product_plan_product_feature_version`

**Migration Pattern:**
```python
"""Phase 6.0.1 Task 5: FK constraints for Billing & Payments audit columns

Revision ID: phase_6_0_1_task_5_fk_audit_billing
Revises: phase_6_0_1_task_4_fk_audit_quoting
Create Date: 2026-04-13
"""

def upgrade():
    # Add FK constraints for tables with both created_by and updated_by
    for table_name in [
        'invoice', 'invoice_status', 'payment', 'payment_status',
        'payment_type', 'payment_method', 'psp_customer', 'subscription',
        'subscription_status', 'subscription_usage', 'product_plan', 'product_feature'
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
        'invoice_line', 'invoice_line_tax_component', 'psp_transaction_log',
        'usage_ledger', 'product_plan_version', 'product_plan_product_feature_version'
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
        'invoice_line', 'invoice_line_tax_component', 'psp_transaction_log',
        'usage_ledger', 'product_plan_version', 'product_plan_product_feature_version'
    ]:
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
    
    for table_name in [
        'invoice', 'invoice_status', 'payment', 'payment_status',
        'payment_type', 'payment_method', 'psp_customer', 'subscription',
        'subscription_status', 'subscription_usage', 'product_plan', 'product_feature'
    ]:
        op.drop_constraint(f'fk_{table_name}_updated_by', table_name, type_='foreignkey')
        op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
```

---

### Task 1: SQLModel Schema Definitions Verification

**Effort:** 0.5-1 day
**Scope:** Verify FK definitions across 18 billing & payment tables

#### What This Task Accomplishes

Confirm that all Phase 6.0.1 Task 5 changes are correctly defined in the Python SQLModel definitions. Update models with FK constraints on audit columns.

#### Tables to Check (Task 5)

**Model Files & Required Changes:**

1. `backend/app/models/billing.py`
   - `Invoice`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `InvoiceStatus`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `Payment`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `PaymentStatus`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `PaymentType`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `PaymentMethod`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `PspCustomer`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `Subscription`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `SubscriptionStatus`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `SubscriptionUsage`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `ProductPlan`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `ProductFeature`: Add `foreign_key="user.id"` to both `created_by` and `updated_by` with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `InvoiceLine`: Add `foreign_key="user.id"` to `created_by` (only) with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `InvoiceLineTaxComponent`: Add `foreign_key="user.id"` to `created_by` (only) with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `PspTransactionLog`: Add `foreign_key="user.id"` to `created_by` (only) with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `UsageLedger`: Add `foreign_key="user.id"` to `created_by` (only) with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `ProductPlanVersion`: Add `foreign_key="user.id"` to `created_by` (only) with `sa_column_kwargs={"ondelete": "RESTRICT"}`
   - `ProductPlanProductFeatureVersion`: Add `foreign_key="user.id"` to `created_by` (only) with `sa_column_kwargs={"ondelete": "RESTRICT"}`

#### SQLModel Syntax Examples

**See "SQLModel Foreign Key Syntax" section above for complete examples**

**Success Criteria for Task 1:**
- [ ] All 18 tables in this task have FK definitions added
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

Verify that the database is ready for Phase 6.0.1 Task 5 migration by checking for orphaned audit references that would prevent FK constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation: Orphaned Audit References (MANDATORY)**

Use the queries provided in the "Critical Warnings" section above for all 18 tables.

**If ANY validation query fails:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results
- **Report** - Ask for guidance on data cleanup strategy
- **Clean** - Implement chosen remediation strategy
- **Re-validate** - Run all queries again

**Success Criteria for Task 2:**
- [ ] All created_by orphan queries return 0 rows
- [ ] All updated_by orphan queries return 0 rows (for 12 tables with updated_by)
- [ ] Validation results documented
- [ ] Ready to proceed with migration

---

### Task 3: Migration Creation & Application

**Effort:** 1 day
**Dependencies:** Task 1 (models) and Task 2 (validation) must be complete
**Migration:** 5 of 9

#### What This Task Accomplishes

Generate and apply Alembic migration with FK constraints for all 18 billing & payment tables in this task.

#### Implementation Steps

**Step 1: Generate Migration Skeleton**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_1_task_5_fk_audit_billing"
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
    'invoice', 'invoice_status', 'payment', 'payment_status',
    'payment_type', 'payment_method', 'psp_customer', 'subscription',
    'subscription_status', 'subscription_usage', 'product_plan', 'product_feature',
    'invoice_line', 'invoice_line_tax_component', 'psp_transaction_log',
    'usage_ledger', 'product_plan_version', 'product_plan_product_feature_version'
  )
  AND kcu.column_name IN ('created_by', 'updated_by')
  AND ccu.table_name = 'user'
ORDER BY tc.table_name, kcu.column_name;
-- Expected: 30 rows (12 tables × 2 FKs + 6 tables × 1 FK)
```

**Step 5: Test Migration Rollback**
```bash
alembic downgrade -1
# Verify FK constraints removed
alembic upgrade head
```

**Success Criteria for Task 3:**
- [ ] Migration created with all 30 FK constraints
- [ ] Migration applies successfully
- [ ] All verification queries pass
- [ ] Migration rolls back successfully
- [ ] Migration re-applies successfully

---

### Task 4: Comprehensive Testing

**Effort:** 1 day
**Dependencies:** Task 3 must be complete

#### What This Task Accomplishes

Validate that all Phase 6.0.1 Task 5 FK constraints work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_1_task_5_audit_fk.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0.1 Task 5 - Billing & Payments Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: phase-6.0-db-schema-sync-11-plan.md - Task 5
"""
import pytest
from sqlalchemy.exc import IntegrityError
import uuid


class TestAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""
    
    def test_invoice_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        # [See example in Critical Warnings section above]
    
    def test_payment_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        # Similar pattern for payment table
    
    # ... (repeat for all 18 tables)


class TestAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""
    
    def test_invoice_updated_by_fk_enforcement(self, db_session, test_tenant, test_user):
        """Test that invalid updated_by user ID is rejected"""
        # Similar to created_by but for updated_by (12 tables only)


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""
    
    def test_user_deletion_blocked_by_invoice_audit(self, db_session, test_tenant, test_user):
        """Test ON DELETE RESTRICT behavior"""
        # [See example in Critical Warnings section above]


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""
    
    def test_invoice_null_audit_columns(self, db_session, test_tenant):
        """Test that NULL created_by and updated_by are allowed"""
        # [See example in Critical Warnings section above]
```

**Success Criteria for Task 4:**
- [ ] Test file created with all test categories
- [ ] FK enforcement tests prevent invalid user IDs (18 tables)
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
# Expected: [NEW_COUNT]+ passed (781 baseline + new tests for this task)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [NEW_COUNT]+ passed (808 baseline + new tests for this task)
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
### Phase 6.0.1 Task 5: Billing & Payments FK Constraints - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_DAYS] days (actual)
**Priority:** HIGH

**Implementation Summary:**

- Model Verification: Updated 18 tables in `billing.py`
- Data Validation: All pre-migration orphan detection queries passed (0 orphaned references)
- Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_1_task_5_fk_audit_billing.py`]
- Test Suite: [`test_phase_6_0_1_task_5_audit_fk.py`] - [N] tests ✅
- Final Results: [NEW_UNIT]/[NEW_UNIT] unit tests (100%), [NEW_TOTAL]/[NEW_TOTAL] total tests (100%)

**Key Changes:**
- ✅ 30 Foreign Key constraints added (12 tables × 2 + 6 tables × 1)
- ✅ All FKs use ON DELETE RESTRICT behavior
- ✅ Zero orphaned audit references found
- ✅ User deletion workflow validated
- ✅ Zero regressions in existing test suite

**Baseline:** 781 unit tests, 808 total tests → **New:** [NEW_UNIT] unit tests (+[DIFF]), [NEW_TOTAL] total tests (+[DIFF])
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Phase 6.0.1 Task 5:
- [ ] **Regression baseline captured** (781/781 unit, 808/808 total)
- [ ] **All orphaned audit reference queries returned 0 rows**
- [ ] **All 18 tables verified in Python models**
- [ ] **All FKs use string reference `"user.id"`**
- [ ] **All FKs specify `ondelete='RESTRICT'`**
- [ ] **All audit columns remain `Optional[uuid.UUID]`**
- [ ] **Alembic migration created for this task**
- [ ] **Migration applied successfully**
- [ ] **All database verification queries passed (30 FK constraints)**
- [ ] **Comprehensive tests written and passing**
- [ ] **ALL 781 existing unit tests still passing**
- [ ] **ALL 808 total tests still passing**
- [ ] **New total: [NEW_UNIT]+/[NEW_UNIT]+ unit, [NEW_TOTAL]+/[NEW_TOTAL]+ total (100%)**
- [ ] **Migration rollback tested**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-6.0-db-schema-sync-11-analysis.md` - **FK Requirements Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models (Task 5)
- `backend/app/models/billing.py` - 18 tables
- `backend/db_models_map.md` - Model file locations
- `backend/app_model_imports.md` - Import syntax reference

---

## Risk Assessment

**For Phase 6.0.1 Task 5:**
- **Orphaned Reference Risk:** MEDIUM (orphaned audit references would prevent FK creation - validated before migration)
- **Circular Dependency Risk:** LOW (string-based FK references prevent Python circular imports)
- **User Deletion Impact:** MEDIUM (ON DELETE RESTRICT changes operational workflow)
- **Migration Complexity:** LOW (standard FK constraint operations)
- **Application Impact:** LOW (additive changes, improves data integrity without breaking changes)
- **Rollback Complexity:** LOW (single independent migration, surgical rollback)
- **Performance Impact:** MINIMAL (FK constraints add negligible overhead)
- **Financial Data Integrity:** HIGH (critical for billing/payment audit compliance)
- **Mitigation:** Comprehensive pre-migration validation, extensive testing, documented user deletion workflow

---

## Notes

### Important Patterns to Follow
- **Nine Migrations:** One per functional domain (Tasks 1-9)
- **Zero Orphans:** Pre-migration validation MUST show 0 orphaned audit references
- **String References:** Always use `foreign_key="user.id"` not class reference
- **ON DELETE RESTRICT:** Mandatory for all audit FK constraints
- **NULL Support:** All audit columns must remain `Optional[uuid.UUID]`
- **Zero Regression:** All 781 unit + 808 total tests MUST pass

### Phase 6.0.1 Specific
- **203 FK Constraints:** 87 tables × 2 + 29 tables × 1
- **9 Migrations:** Domain-grouped for context optimization
- **User Deletion:** Requires soft-delete workflow (document in ops manual)
- **Audit Integrity:** Database-level enforcement prevents audit trail corruption
- **Compliance:** Supports SOC 2, GDPR audit trail requirements
- **Financial Compliance:** Task 5 focuses on billing/payment audit integrity

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 6.0.1 plan for detailed specifications
- Verify all pre-migration orphan detection queries passed
- Check that correct task number migration is being created
- Verify FK definitions use string reference and `ondelete='RESTRICT'`
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Phase 6.0.1 Task 5 Checklist:
1. ✅ Capture baseline (781/781 unit, 808/808 total)
2. 🔍 **Verify all 18 table FK definitions in Python models**
3. ✅ Verify Python syntax (`python -c "from app.models import *"`)
4. ⚠️ **CRITICAL: Run orphaned created_by queries (all 18 tables)**
5. ⚠️ **CRITICAL: Run orphaned updated_by queries (12 tables with updated_by)**
6. ⚠️ **MANDATORY: Stop if ANY orphaned references found**
7. 🔧 **Create Migration: FK constraints for Billing & Payments tables**
8. ✅ Apply Migration, verify 30 FK constraints created
9. 🧪 **Create comprehensive test suite (FK enforcement + user deletion + NULL support)**
10. 🔄 Run regression tests ([NEW_COUNT]+/[NEW_COUNT]+ expected)
11. ↩️ Test migration rollback
12. 📚 Update project plan

Remember: Phase 6.0.1 brings database-level audit trail integrity to critical billing and payment tables, preventing orphaned references and ensuring compliance with SOC 2 and GDPR requirements. Validate thoroughly before migration, test extensively, and ensure zero regressions!
