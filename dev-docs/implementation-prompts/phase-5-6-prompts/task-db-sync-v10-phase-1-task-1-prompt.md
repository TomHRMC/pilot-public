# Task 1: Constraints & Audit Columns

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` - Task 1
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` - **Advanced Constraints & Performance Indexes Analysis** ⭐
- Current Live Database (Phase 5.3 Post-State)
**Type:** Phase 6.0 - Multi-Tenant Constraints + Business Logic Constraints + Audit Columns
**Priority:** HIGH
**Change Type:** UNIQUE CONSTRAINTS + AUDIT COLUMNS

---

## Context

This is **Phase 6.0 Task 1 - DB Sync v#10**, the first of three tasks implementing comprehensive database constraints and performance optimizations.

**Root Cause:** 
- Multi-tenant lookup tables missing `(tenant_id, code)` unique constraints
- Business logic unique constraints not enforced at database level
- Incomplete audit columns on conversation_session

**Critical Impact:**
- **Multi-Tenant Isolation Risk:** Duplicate codes within same tenant possible (violates data integrity)
- **Business Logic Gap:** Duplicate job assignments, payment methods, user preferences allowed
- **Audit Trail Gap:** conversation_session missing created_by/updated_by columns

**Scope:** **1 migration** - 19 unique constraints + 2 audit columns across 20+ tables.

**Key Principle:** Phase 6.0 uses **3 separate Alembic migrations** (one per task) for surgical rollback capability and risk isolation.

---

## What Was Completed in Previous Phases

**Phase 5.3 Status:** ✅ COMPLETE (April 11, 2026)
- ✅ notification_delivery_attempt schema synchronized (column rename + 3 new columns)
- ✅ 4 idempotency unique constraints added (invoice, quote, payment)
- ✅ 7 indexes renamed/standardized (conversation_session, job_time_entry, voice_command_log)
- ✅ 2 triggers attached to discount_version (audit + immutability)
- ✅ 661/661 unit tests, 688/688 total tests passing (100%)

**Current Baseline:** 661/661 unit tests, 688/688 total tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement
- **Phase 5.1:** ✅ COMPLETE - Missing unique constraints & foreign keys
- **Phase 5.2:** ✅ COMPLETE - Exclusion constraints & critical indexes
- **Phase 5.3:** ✅ COMPLETE - Notification schema + idempotency + index standardization + triggers

**See:**
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md` for Phase 5.3 history
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` for comprehensive gap details

---

## Current Task: Constraints & Audit Columns

**Effort:** 2-3 hours
**Gap Reference:** Phase 6.0 Analysis - Multi-Tenant/Business Logic Gaps
**Change Type:** MODEL VERIFICATION + MIGRATION + DATA VALIDATION

This task implements database-level enforcement of multi-tenant isolation and critical business rules through unique constraints, while adding audit trail columns to conversation_session for compliance.

### What Needs to Be Fixed

**Multi-Tenant Unique Constraints (14 tables):**

| Table | Constraint | Columns | Impact |
|-------|-----------|---------|--------|
| `customer_lifecycle_status` | `uq_customer_lifecycle_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |
| `invoice_status` | `uq_invoice_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |
| `job_status` | `uq_job_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |
| `payment_status` | `uq_payment_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |
| `payment_type` | `uq_payment_type_tenant_code` | `(tenant_id, code)` | Prevent duplicate payment types per tenant |
| `qpl_contact_action_type` | `uq_qpl_contact_action_type_tenant_code` | `(tenant_id, code)` | Prevent duplicate action types per tenant |
| `quote_link_status` | `uq_quote_link_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |
| `quote_status` | `uq_quote_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |
| `site_lifecycle_status` | `uq_site_lifecycle_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |
| `subscription_status` | `uq_subscription_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |
| `supplier_item_category` | `uq_supplier_item_category_tenant_code` | `(tenant_id, code)` | Prevent duplicate category codes per tenant |
| `supplier_item_uom` | `uq_supplier_item_uom_tenant_code` | `(tenant_id, code)` | Prevent duplicate UOM codes per tenant |
| `supplier_lifecycle_status` | `uq_supplier_lifecycle_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |
| `tenant_user_status` | `uq_tenant_user_status_tenant_code` | `(tenant_id, code)` | Prevent duplicate status codes per tenant |

**Business Logic Unique Constraints (5 tables):**

| Table | Constraint | Columns | Impact |
|-------|-----------|---------|--------|
| `job_assignment` | `uq_job_assignment_job_user` | `(job_id, user_id)` | Prevent duplicate user assignments to same job |
| `payment_method` | `uq_payment_method_tenant_psp` | `(tenant_id, psp_provider, psp_payment_method_id)` | Prevent duplicate PSP payment methods |
| `psp_customer` | `uq_psp_customer_provider_id` | `(psp_provider, psp_customer_id)` | Prevent duplicate PSP customer IDs |
| `user_preference` | `uq_user_preference_user_tenant` | `(user_id, tenant_id)` | Prevent duplicate preferences per user-tenant |
| `user` | `uq_user_email` | `(email)` | Formalize email uniqueness constraint |

**Audit Columns (1 table):**

| Table | New Columns | Type | Impact |
|-------|-------------|------|--------|
| `conversation_session` | `created_by`, `updated_by` | `UUID` (nullable) | Add audit trail for conversation sessions |

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

**Record the output of both results:** `661/661 & 688/688 tests passing` (Phase 6.0 baseline - starting from Phase 5.3 completion)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 6.0 Task 1 Specific Warnings

**BEFORE writing ANY code, review these critical Task 1 issues:**

### 1. Multi-Tenant Unique Constraints - Pre-Migration Validation is MANDATORY

**CRITICAL:** Before creating `UniqueConstraint('tenant_id', 'code')` on 14 lookup tables, you MUST verify no duplicate codes exist within the same tenant.

**Validation Queries (MANDATORY):**
```sql
-- Check for duplicate codes in multi-tenant tables
SELECT 'customer_lifecycle_status' as table_name, tenant_id, code, COUNT(*) as count
FROM customer_lifecycle_status GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'invoice_status', tenant_id, code, COUNT(*)
FROM invoice_status GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'job_status', tenant_id, code, COUNT(*)
FROM job_status GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'payment_status', tenant_id, code, COUNT(*)
FROM payment_status GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'payment_type', tenant_id, code, COUNT(*)
FROM payment_type GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'qpl_contact_action_type', tenant_id, code, COUNT(*)
FROM qpl_contact_action_type GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'quote_link_status', tenant_id, code, COUNT(*)
FROM quote_link_status GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'quote_status', tenant_id, code, COUNT(*)
FROM quote_status GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'site_lifecycle_status', tenant_id, code, COUNT(*)
FROM site_lifecycle_status GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'subscription_status', tenant_id, code, COUNT(*)
FROM subscription_status GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'supplier_item_category', tenant_id, code, COUNT(*)
FROM supplier_item_category GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'supplier_item_uom', tenant_id, code, COUNT(*)
FROM supplier_item_uom GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'supplier_lifecycle_status', tenant_id, code, COUNT(*)
FROM supplier_lifecycle_status GROUP BY tenant_id, code HAVING COUNT(*) > 1
UNION ALL
SELECT 'tenant_user_status', tenant_id, code, COUNT(*)
FROM tenant_user_status GROUP BY tenant_id, code HAVING COUNT(*) > 1;
-- Expected: 0 rows (no duplicates)
```

**If ANY query returns rows > 0:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results showing duplicate codes
- **Report** - Ask for guidance on data cleanup strategy
- **Options:** Delete duplicates, keep oldest record, or reassign foreign key references
- **Re-validate** - Run all queries again to confirm 0 violations

---

### 2. Business Logic Unique Constraints Validation

**CRITICAL:** Before creating business logic unique constraints, verify no duplicates exist.

**Validation Queries:**
```sql
-- Check for duplicate job assignments
SELECT job_id, user_id, COUNT(*) as count
FROM job_assignment 
GROUP BY job_id, user_id 
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Check for duplicate payment methods
SELECT tenant_id, psp_provider, psp_payment_method_id, COUNT(*) as count
FROM payment_method 
WHERE psp_payment_method_id IS NOT NULL
GROUP BY tenant_id, psp_provider, psp_payment_method_id 
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Check for duplicate psp customers
SELECT psp_provider, psp_customer_id, COUNT(*) as count
FROM psp_customer 
GROUP BY psp_provider, psp_customer_id 
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Check for duplicate user preferences
SELECT user_id, tenant_id, COUNT(*) as count
FROM user_preference 
GROUP BY user_id, tenant_id 
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Check for duplicate emails
SELECT email, COUNT(*) as count
FROM "user" 
GROUP BY email 
HAVING COUNT(*) > 1;
-- Expected: 0 rows
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

### 3. Test Unique Constraints with pytest.raises(IntegrityError)

**Pattern for Testing Multi-Tenant Code Uniqueness:**
```python
import pytest
from sqlalchemy.exc import IntegrityError

def test_job_status_tenant_code_prevents_duplicates(db_session, test_tenant):
    # Insert first status
    status1 = JobStatus(
        tenant_id=test_tenant.id,
        code="PENDING",
        name="Pending Review"
    )
    db_session.add(status1)
    db_session.commit()
    
    # Attempt duplicate code within same tenant (should fail)
    status2 = JobStatus(
        tenant_id=test_tenant.id,
        code="PENDING",  # DUPLICATE
        name="Pending Approval"
    )
    db_session.add(status2)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "uq_job_status_tenant_code" in str(exc_info.value)
    db_session.rollback()
```

---

## Requirements

### Task 1: SQLModel Schema Definitions Verification

**Effort:** 0.5-1 day
**Scope:** Verify schema changes across 20+ tables in Python models

#### What This Task Accomplishes

Confirm that all Phase 6.0 Task 1 changes are correctly defined in the Python SQLModel definitions. Update models with unique constraints and audit columns.

#### Tables to Check (Task 1)

**Model Files & Required Changes:**

**Multi-Tenant Unique Constraints (14 tables):**
1. `backend/app/models/customer.py`
   - `CustomerLifecycleStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_customer_lifecycle_status_tenant_code')`
   - `SiteLifecycleStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_site_lifecycle_status_tenant_code')`

2. `backend/app/models/billing.py`
   - `InvoiceStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_invoice_status_tenant_code')`
   - `PaymentStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_payment_status_tenant_code')`
   - `PaymentType`: Add `UniqueConstraint('tenant_id', 'code', name='uq_payment_type_tenant_code')`

3. `backend/app/models/job.py`
   - `JobStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_job_status_tenant_code')`

4. `backend/app/models/quoting.py`
   - `QplContactActionType`: Add `UniqueConstraint('tenant_id', 'code', name='uq_qpl_contact_action_type_tenant_code')`
   - `QuoteLinkStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_quote_link_status_tenant_code')`
   - `QuoteStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_quote_status_tenant_code')`

5. `backend/app/models/subscription.py`
   - `SubscriptionStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_subscription_status_tenant_code')`

6. `backend/app/models/supplier.py`
   - `SupplierItemCategory`: Add `UniqueConstraint('tenant_id', 'code', name='uq_supplier_item_category_tenant_code')`
   - `SupplierItemUom`: Add `UniqueConstraint('tenant_id', 'code', name='uq_supplier_item_uom_tenant_code')`
   - `SupplierLifecycleStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_supplier_lifecycle_status_tenant_code')`

7. `backend/app/models/tenant.py`
   - `TenantUserStatus`: Add `UniqueConstraint('tenant_id', 'code', name='uq_tenant_user_status_tenant_code')`

**Business Logic Unique Constraints (5 tables):**
1. `backend/app/models/job.py`
   - `JobAssignment`: Add `UniqueConstraint('job_id', 'user_id', name='uq_job_assignment_job_user')`

2. `backend/app/models/billing.py`
   - `PaymentMethod`: Add `UniqueConstraint('tenant_id', 'psp_provider', 'psp_payment_method_id', name='uq_payment_method_tenant_psp')`
   - `PspCustomer`: Add `UniqueConstraint('psp_provider', 'psp_customer_id', name='uq_psp_customer_provider_id')`

3. `backend/app/models/tenant.py`
   - `UserPreference`: Add `UniqueConstraint('user_id', 'tenant_id', name='uq_user_preference_user_tenant')`
   - `User`: Add `UniqueConstraint('email', name='uq_user_email')`

**Audit Columns:**
4. `backend/app/models/voice.py`
   - `ConversationSession`: Add `created_by: Optional[uuid.UUID]` and `updated_by: Optional[uuid.UUID]`

#### SQLModel Syntax Examples

**Multi-Tenant Unique Constraint:**
```python
from sqlalchemy import UniqueConstraint, Index

class JobStatus(SQLModel, table=True):
    __tablename__ = "job_status"
    
    id: int = Field(primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id")
    code: str = Field(max_length=50)
    name: str = Field(max_length=100)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'code', name='uq_job_status_tenant_code'),
        Index('idx_job_status_tenant', 'tenant_id'),
    )
```

**Business Logic Unique Constraint:**
```python
class JobAssignment(SQLModel, table=True):
    __tablename__ = "job_assignment"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="job.id")
    user_id: uuid.UUID = Field(foreign_key="user.id")
    is_active: bool = Field(default=True)
    
    __table_args__ = (
        UniqueConstraint('job_id', 'user_id', name='uq_job_assignment_job_user'),
        Index('idx_job_assignment_job', 'job_id'),
        Index('idx_job_assignment_user_active', 'user_id', 'is_active'),
    )
```

**Audit Columns:**
```python
class ConversationSession(SQLModel, table=True):
    __tablename__ = "conversation_session"
    
    # ... existing fields ...
    
    # NEW: Audit columns
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        description="User who created this conversation session"
    )
    updated_by: Optional[uuid.UUID] = Field(
        default=None,
        description="User who last updated this conversation session"
    )
    
    # Note: Foreign keys will be added in future phase (not in 6.0)
```

**Success Criteria for Task 1:**
- [ ] All 14 multi-tenant unique constraints added to models
- [ ] All 5 business logic unique constraints added to models
- [ ] 2 audit columns added to conversation_session
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models import *"`)

---

### Task 2: Pre-Migration Data Validation

**Effort:** 0.5 day
**Dependencies:** None (can run independently)
**CRITICAL:** Validation MUST pass before generating any migrations

#### What This Task Accomplishes

Verify that the database is ready for Phase 6.0 Task 1 migration by checking for data violations that would prevent constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation 1: Multi-Tenant Code Duplicates (MANDATORY)**

[See "Multi-Tenant Unique Constraints - Pre-Migration Validation" section above for complete query]

**Validation 2: Business Logic Duplicates (MANDATORY)**

[See "Business Logic Unique Constraints Validation" section above for complete queries]

**If ANY validation query fails:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results
- **Report** - Ask for guidance on data cleanup strategy
- **Clean** - Create remediation script
- **Re-validate** - Run all queries again

**Success Criteria for Task 2:**
- [ ] All multi-tenant duplicate queries return 0 rows
- [ ] All business logic duplicate queries return 0 rows
- [ ] Validation results documented

---

### Task 3: Task 1 Migration - Constraints & Audit Columns

**Effort:** 1 day
**Dependencies:** Task 1 (models) and Task 2 (validation) must be complete
**Migration:** 1 of 3

#### What This Task Accomplishes

Generate and apply first Alembic migration with all unique constraints and audit columns.

#### Implementation Steps

**Step 1: Generate Migration Skeleton**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_task_1_constraints_audit_columns"
```

**Step 2: Manually Construct Complete Migration**

```python
"""Phase 6.0 Task 1: Unique constraints and audit columns

Revision ID: phase_6_0_task_1_constraints
Revises: [PREVIOUS_REVISION]
Create Date: 2026-04-13
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision = 'phase_6_0_task_1_constraints'
down_revision = '[PREVIOUS_REVISION]'  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Add audit columns to conversation_session
    op.add_column('conversation_session', 
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('conversation_session', 
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Multi-tenant unique constraints (14 tables)
    op.create_unique_constraint(
        'uq_customer_lifecycle_status_tenant_code',
        'customer_lifecycle_status',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_invoice_status_tenant_code',
        'invoice_status',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_job_status_tenant_code',
        'job_status',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_payment_status_tenant_code',
        'payment_status',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_payment_type_tenant_code',
        'payment_type',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_qpl_contact_action_type_tenant_code',
        'qpl_contact_action_type',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_quote_link_status_tenant_code',
        'quote_link_status',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_quote_status_tenant_code',
        'quote_status',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_site_lifecycle_status_tenant_code',
        'site_lifecycle_status',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_subscription_status_tenant_code',
        'subscription_status',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_supplier_item_category_tenant_code',
        'supplier_item_category',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_supplier_item_uom_tenant_code',
        'supplier_item_uom',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_supplier_lifecycle_status_tenant_code',
        'supplier_lifecycle_status',
        ['tenant_id', 'code']
    )
    op.create_unique_constraint(
        'uq_tenant_user_status_tenant_code',
        'tenant_user_status',
        ['tenant_id', 'code']
    )
    
    # Business logic unique constraints (5 tables)
    op.create_unique_constraint(
        'uq_job_assignment_job_user',
        'job_assignment',
        ['job_id', 'user_id']
    )
    op.create_unique_constraint(
        'uq_payment_method_tenant_psp',
        'payment_method',
        ['tenant_id', 'psp_provider', 'psp_payment_method_id']
    )
    op.create_unique_constraint(
        'uq_psp_customer_provider_id',
        'psp_customer',
        ['psp_provider', 'psp_customer_id']
    )
    op.create_unique_constraint(
        'uq_user_preference_user_tenant',
        'user_preference',
        ['user_id', 'tenant_id']
    )
    op.create_unique_constraint(
        'uq_user_email',
        'user',
        ['email']
    )


def downgrade():
    # Drop business logic constraints
    op.drop_constraint('uq_user_email', 'user', type_='unique')
    op.drop_constraint('uq_user_preference_user_tenant', 'user_preference', type_='unique')
    op.drop_constraint('uq_psp_customer_provider_id', 'psp_customer', type_='unique')
    op.drop_constraint('uq_payment_method_tenant_psp', 'payment_method', type_='unique')
    op.drop_constraint('uq_job_assignment_job_user', 'job_assignment', type_='unique')
    
    # Drop multi-tenant constraints
    op.drop_constraint('uq_tenant_user_status_tenant_code', 'tenant_user_status', type_='unique')
    op.drop_constraint('uq_supplier_lifecycle_status_tenant_code', 'supplier_lifecycle_status', type_='unique')
    op.drop_constraint('uq_supplier_item_uom_tenant_code', 'supplier_item_uom', type_='unique')
    op.drop_constraint('uq_supplier_item_category_tenant_code', 'supplier_item_category', type_='unique')
    op.drop_constraint('uq_subscription_status_tenant_code', 'subscription_status', type_='unique')
    op.drop_constraint('uq_site_lifecycle_status_tenant_code', 'site_lifecycle_status', type_='unique')
    op.drop_constraint('uq_quote_status_tenant_code', 'quote_status', type_='unique')
    op.drop_constraint('uq_quote_link_status_tenant_code', 'quote_link_status', type_='unique')
    op.drop_constraint('uq_qpl_contact_action_type_tenant_code', 'qpl_contact_action_type', type_='unique')
    op.drop_constraint('uq_payment_type_tenant_code', 'payment_type', type_='unique')
    op.drop_constraint('uq_payment_status_tenant_code', 'payment_status', type_='unique')
    op.drop_constraint('uq_job_status_tenant_code', 'job_status', type_='unique')
    op.drop_constraint('uq_invoice_status_tenant_code', 'invoice_status', type_='unique')
    op.drop_constraint('uq_customer_lifecycle_status_tenant_code', 'customer_lifecycle_status', type_='unique')
    
    # Drop audit columns
    op.drop_column('conversation_session', 'updated_by')
    op.drop_column('conversation_session', 'created_by')
```

**Step 3: Apply Migration**
```bash
alembic upgrade head
```

**Step 4: Verify Database State**
```sql
-- Verify multi-tenant unique constraints
SELECT 
    tc.table_name,
    tc.constraint_name
FROM information_schema.table_constraints tc
WHERE tc.constraint_type = 'UNIQUE'
    AND tc.table_schema = 'public'
    AND tc.constraint_name LIKE 'uq_%_tenant_code'
ORDER BY tc.table_name;
-- Expected: 14 rows

-- Verify business logic unique constraints  
SELECT 
    tc.table_name,
    tc.constraint_name
FROM information_schema.table_constraints tc
WHERE tc.constraint_type = 'UNIQUE'
    AND tc.table_schema = 'public'
    AND tc.constraint_name IN (
        'uq_job_assignment_job_user',
        'uq_payment_method_tenant_psp',
        'uq_psp_customer_provider_id',
        'uq_user_preference_user_tenant',
        'uq_user_email'
    )
ORDER BY tc.table_name;
-- Expected: 5 rows

-- Verify audit columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'conversation_session'
    AND column_name IN ('created_by', 'updated_by')
ORDER BY column_name;
-- Expected: 2 rows
```

**Step 5: Test Migration Rollback**
```bash
alembic downgrade -1
# Verify constraints removed
alembic upgrade head
```

**Success Criteria for Task 3:**
- [ ] Migration 1 created with all constraints and columns
- [ ] Migration applies successfully
- [ ] All verification queries pass
- [ ] Migration rolls back successfully
- [ ] Migration re-applies successfully

---

### Task 4: Comprehensive Testing

**Effort:** 1.5 days
**Dependencies:** Task 3 must be complete

#### What This Task Accomplishes

Validate that all Phase 6.0 Task 1 changes work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_task_1_constraints_audit.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0 Task 1 - Constraints & Audit Columns Verification
Validates multi-tenant constraints, business logic constraints, and audit columns.

Reference: phase-6.0-db-schema-sync-10-plan.md - Task 1
"""
import pytest
from sqlalchemy.exc import IntegrityError
import uuid


class TestMultiTenantUniqueConstraints:
    """Test multi-tenant unique constraints on lookup tables"""
    
    def test_job_status_tenant_code_prevents_duplicates(self, db_session, test_tenant):
        """Verify uq_job_status_tenant_code constraint"""
        # [See example in Critical Warnings section above]
    
    def test_job_status_different_tenants_allowed(self, db_session, test_tenant, test_tenant2):
        """Test that same code across different tenants is allowed"""
        # Similar pattern but verify different tenants CAN have same code


class TestBusinessLogicUniqueConstraints:
    """Test business logic unique constraints"""
    
    def test_job_assignment_duplicate_prevention(self, db_session, job, user):
        """Verify uq_job_assignment_job_user constraint"""
        # [See example in Critical Warnings section above]
    
    def test_payment_method_psp_uniqueness(self, db_session, test_tenant):
        """Verify uq_payment_method_tenant_psp constraint"""
        # Similar pattern for payment methods


class TestAuditColumns:
    """Test audit columns on conversation_session"""
    
    def test_conversation_session_audit_columns(self, db_session, test_tenant, test_user):
        """Verify created_by and updated_by accessible"""
        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id
        )
        db_session.add(session)
        db_session.commit()
        
        assert session.created_by == test_user.id
        assert session.updated_by == test_user.id
```

**Success Criteria for Task 4:**
- [ ] Test file created with all test categories
- [ ] Multi-tenant constraint tests prevent duplicates
- [ ] Business logic constraint tests work correctly
- [ ] Audit column tests verify accessibility
- [ ] Full test suite passes: 676+/676+ unit tests, 703+/703+ total (100%)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 676+ passed (661 baseline + ~15 new tests)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 703+ passed (688 baseline + ~15 new tests)
```

### Step 2: Verify Database State

Run all verification queries from Task 3 to confirm database matches Golden Master.

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check migration was applied successfully
3. Verify constraint definitions in database
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md`

Add implementation status:

```markdown
## Implementation Status Tracking

### Phase 6.0 Task 1: Constraints & Audit Columns - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_HOURS] hours (actual)
**Priority:** HIGH

**Implementation Summary:**

- Model Verification: Updated 20+ tables across 8 model files
- Data Validation: All pre-migration validation queries passed
- Migration 1: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_task_1_constraints_audit_columns.py`]
- Test Suite: [`test_phase_6_0_task_1_constraints_audit.py`] - 15+ tests ✅
- Final Results: 676/676 unit tests (100%), 703/703 total tests (100%)

**Key Changes:**
- ✅ 14 multi-tenant unique constraints (tenant_id, code)
- ✅ 5 business logic unique constraints
- ✅ 2 audit columns (conversation_session)
- ✅ Zero regressions in existing test suite
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 1 Only:
- [ ] **Regression baseline captured** (661/661 unit, 688/688 total)
- [ ] **All multi-tenant duplicate queries returned 0 rows**
- [ ] **All business logic duplicate queries returned 0 rows**
- [ ] **All 20+ tables verified in Python models**
- [ ] **Migration 1 created and applied successfully**
- [ ] **All database verification queries passed**
- [ ] **Comprehensive tests written and passing**
- [ ] **ALL 661 existing unit tests still passing**
- [ ] **ALL 688 total tests still passing**
- [ ] **New total: 676+/676+ unit, 703+/703+ total (100%)**
- [ ] **Migration rollback tested**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` - **Comprehensive Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models (20+ tables affected)
- `backend/app/models/customer.py` - 2 multi-tenant constraints
- `backend/app/models/billing.py` - 5 constraints
- `backend/app/models/job.py` - 2 constraints
- `backend/app/models/quoting.py` - 3 multi-tenant constraints
- `backend/app/models/subscription.py` - 1 multi-tenant constraint
- `backend/app/models/supplier.py` - 3 multi-tenant constraints
- `backend/app/models/tenant.py` - 3 constraints
- `backend/app/models/voice.py` - 2 audit columns

---

## Risk Assessment

**For Task 1:**
- **Duplicate Data Risk:** HIGH (duplicates would prevent constraint creation - validated before migration)
- **Migration Complexity:** MEDIUM (19 constraints + 2 columns)
- **Application Impact:** LOW (additive changes, improves data integrity without breaking changes)
- **Rollback Complexity:** LOW (single migration, surgical rollback)
- **Mitigation:** Comprehensive pre-migration validation, extensive testing

---

## Notes

### Important Patterns to Follow
- **Pre-Migration Validation:** MUST show 0 duplicates before proceeding
- **Zero Regression:** All 661 unit + 688 total tests MUST pass
- **Audit Columns:** created_by, updated_by on conversation_session (nullable, no FKs yet)

### Task 1 Specific
- **Multi-tenant:** 14 tables get `UniqueConstraint('tenant_id', 'code')`
- **Business logic:** 5 tables get specific business unique constraints
- **Audit columns:** created_by, updated_by on conversation_session

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 6.0 plan for detailed specifications
- Verify all pre-migration validation queries passed
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Task 1 Checklist:
1. ✅ Capture baseline (661/661 unit, 688/688 total)
2. 🔍 **Verify all 20+ table definitions in Python models**
3. ✅ Verify Python syntax (`python -c "from app.models import *"`)
4. ⚠️ **CRITICAL: Run multi-tenant duplicate queries (14 tables)**
5. ⚠️ **CRITICAL: Run business logic duplicate queries (5 constraints)**
6. ⚠️ **MANDATORY: Stop if ANY validation fails**
7. 🔧 **Create Migration 1: Constraints & Audit Columns**
8. ✅ Apply Migration 1, verify constraints created
9. 🧪 **Create comprehensive test suite (constraints + audit columns)**
10. 🔄 Run regression tests (676+/676+ unit, 703+/703+ total expected)
11. ↩️ Test rollback of migration
12. 📚 Update project plan

Remember: Task 1 brings multi-tenant isolation and business logic enforcement to the database level. Validate thoroughly before migration, test extensively, and ensure zero regressions!
