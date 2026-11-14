# Task [TASK_NUMBER]: [TASK_NAME]

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` - Task [TASK_NUMBER]
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` - **Advanced Constraints & Performance Indexes Analysis** ⭐
- Current Live Database (Phase 5.3 Post-State)
**Type:** Phase 6.0 - Multi-Tenant Constraints + Business Logic Constraints + Partial Indexes + GiST Exclusion + Composite Indexes
**Priority:** HIGH
**Change Type:** UNIQUE CONSTRAINTS + PARTIAL INDEXES + EXCLUSION CONSTRAINTS + COMPOSITE INDEXES + AUDIT COLUMNS + TESTING

---

## Context

This is **Phase 6.0 - DB Sync v#10**, a comprehensive synchronization addressing **7 major architectural gaps** in the physical database that don't match the Golden Master JSON.

**Root Cause:** 
- Multi-tenant lookup tables missing `(tenant_id, code)` unique constraints
- Business logic unique constraints not enforced at database level
- Missing partial indexes for filtered query optimization
- No temporal overlap prevention for supplier pricing (GiST exclusion constraint)
- Missing composite indexes for common query patterns
- Redundant indexes consuming resources
- Incomplete audit columns on conversation_session

**Critical Impact:**
- **Multi-Tenant Isolation Risk:** Duplicate codes within same tenant possible (violates data integrity)
- **Business Logic Gap:** Duplicate job assignments, payment methods, user preferences allowed
- **Performance Degradation:** Missing partial indexes cause full table scans on filtered queries
- **Temporal Integrity Violation:** Overlapping price periods possible (undefined pricing)
- **Query Performance:** Missing composite indexes degrade performance as data scales
- **Audit Trail Gap:** conversation_session missing created_by/updated_by columns

**Scope:** **3 separate migrations** (Tasks 1, 2, 3) - 19 unique constraints + 2 audit columns + 5 partial indexes + 1 GiST exclusion constraint + 14 composite indexes + 1 redundant index removal across 20+ tables.

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

## Current Task: [TASK_NAME]

**Effort:** [EFFORT_ESTIMATE]
**Gap Reference:** Phase 6.0 Analysis - Multi-Tenant/Business Logic/Performance Gaps
**Change Type:** [MODEL VERIFICATION | MIGRATION + DATA VALIDATION | TESTING]

[TASK_DESCRIPTION - 2-3 sentences explaining what this task accomplishes and WHY it matters]

### What Needs to Be Fixed

[TASK_SPECIFIC_TABLE - Customize per task]

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

## ⚠️ CRITICAL: Phase 6.0 Specific Warnings

**BEFORE writing ANY code, review these Phase 6.0 critical issues:**

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

### 3. GiST Exclusion Constraint - Temporal Overlap Detection

**CRITICAL:** Before creating the GiST exclusion constraint on `supplier_item_price`, you MUST verify no overlapping price periods exist.

**Why This Matters:**
```sql
-- Example of temporal overlap (BUG!):
-- Price 1: Item A, $100, valid [2026-01-01, 2026-06-30)
-- Price 2: Item A, $120, valid [2026-03-01, 2026-09-30)  -- OVERLAPS!
-- Result: Undefined pricing from March 1 to June 30
```

**Validation Query (MANDATORY):**
```sql
-- Check for overlapping price periods
SELECT 
    a.id as price_id_1,
    b.id as price_id_2,
    a.supplier_item_id,
    a.valid_period as period_1,
    b.valid_period as period_2
FROM supplier_item_price a
JOIN supplier_item_price b 
    ON a.supplier_item_id = b.supplier_item_id
    AND a.id < b.id
    AND a.valid_period && b.valid_period;  -- && = overlap operator
-- Expected: 0 rows (no overlaps)
```

**Extension Requirement:**
```sql
-- Verify btree_gist extension exists (required for GiST exclusion constraint)
SELECT extname, extversion 
FROM pg_extension 
WHERE extname = 'btree_gist';
-- Expected: 1 row (already installed from Phase 5.2)
```

**If overlaps are found:**
- **STOP** - Do not proceed with constraint creation
- **Document** - Save query results showing overlapping periods
- **Report** - Ask for guidance on resolution strategy
- **Options:** Adjust period boundaries to eliminate overlap, or delete one of the conflicting price records
- **Re-validate** - Run query again to confirm 0 overlaps

---

### 4. Partial Indexes Use postgresql_where Parameter

**Critical Pattern:** Partial indexes require the `postgresql_where` parameter with a `text()` expression.

**Correct Syntax:**
```python
from sqlalchemy import Index, text

# ✅ CORRECT - Partial index with WHERE clause
Index(
    'idx_invoice_balance',
    'balance_due_cents',
    postgresql_where=text('balance_due_cents > 0')
)

# ✅ CORRECT - Unique partial index
Index(
    'idx_user_endpoint_primary_email',
    'user_id',
    unique=True,
    postgresql_where=text("channel='email' AND is_primary = true")
)

# ❌ WRONG - Missing postgresql_where
Index('idx_invoice_balance', 'balance_due_cents')  # This is a regular index
```

**In Alembic Migration:**
```python
op.create_index(
    'idx_invoice_balance',
    'invoice',
    ['balance_due_cents'],
    postgresql_where=text('balance_due_cents > 0')  # CRITICAL
)
```

---

### 5. GiST Exclusion Constraint Requires Raw SQL

**Critical Detail:** SQLAlchemy's `ExcludeConstraint` may not be in Alembic autogenerate. Use raw SQL.

**Alembic Pattern:**
```python
def upgrade():
    # Ensure btree_gist extension exists
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist;')
    
    # Create GiST exclusion constraint using raw SQL
    op.execute("""
        ALTER TABLE supplier_item_price
        ADD CONSTRAINT exclude_supplier_item_price_period_overlap
        EXCLUDE USING gist (
            supplier_item_id WITH =,
            valid_period WITH &&
        );
    """)

def downgrade():
    # Drop exclusion constraint
    op.execute("""
        ALTER TABLE supplier_item_price
        DROP CONSTRAINT IF EXISTS exclude_supplier_item_price_period_overlap;
    """)
```

**SQLModel Definition:**
```python
from sqlalchemy import ExcludeConstraint

# Note: This defines the intent, but Alembic may not autogenerate
__table_args__ = (
    ExcludeConstraint(
        ('supplier_item_id', '='),
        ('valid_period', '&&'),
        name='exclude_supplier_item_price_period_overlap',
        using='gist'
    ),
)
```

---

### 6. Composite Indexes with DESC Ordering Use text()

**Critical Pattern:** For descending order in composite indexes, use `text()` wrapper.

**Correct Syntax:**
```python
from sqlalchemy import Index, text

# ✅ CORRECT - Descending order with text()
Index('idx_payment_created_at', text('created_at DESC'))

# ✅ CORRECT - Composite index with DESC
Index(
    'idx_connector_run_supplier_started',
    'supplier_id',
    text('started_at DESC')
)

# ❌ WRONG - String without text() wrapper
Index('idx_payment_created_at', 'created_at DESC')  # Will fail
```

**In Alembic Migration:**
```python
op.create_index(
    'idx_payment_created_at',
    'payment',
    [text('created_at DESC')]  # CRITICAL: Use sa.text()
)
```

---

### 7. Three-Task Migration Strategy

**MANDATORY:** Phase 6.0 uses **3 separate Alembic migrations** for surgical rollback:

**Task 1 Migration:** Constraints & Audit Columns
- 14 multi-tenant unique constraints
- 5 business logic unique constraints
- 2 audit columns on conversation_session
- Risk: HIGH (existing duplicates would prevent constraint creation)

**Task 2 Migration:** Partial Indexes & Exclusion
- 5 partial indexes with WHERE clauses
- 1 GiST exclusion constraint
- 1 redundant index removal
- Risk: MEDIUM (existing overlaps would prevent constraint creation)

**Task 3 Migration:** Composite Indexes
- 4 descending created_at indexes
- 10 composite indexes
- Risk: LOW (purely additive performance optimization)

**Why Separate Migrations:**
- Atomic rollback capability
- Risk isolation (high-risk constraints separate from low-risk indexes)
- Easier troubleshooting if migration fails
- Clear task boundaries

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

### 4. Test GiST Exclusion Constraint with Temporal Overlap

**Pattern for Testing Temporal Overlap Prevention:**
```python
from psycopg2.extras import DateTimeTZRange
from datetime import datetime

def test_supplier_item_price_no_overlap(db_session, supplier_item):
    """Test that overlapping price periods are rejected"""
    
    # Create first price period
    price1 = SupplierItemPrice(
        supplier_item_id=supplier_item.id,
        valid_period=DateTimeTZRange(
            datetime(2026, 1, 1),
            datetime(2026, 6, 30)
        ),
        unit_price_cents=10000
    )
    db_session.add(price1)
    db_session.commit()
    
    # Attempt overlapping price period
    price2 = SupplierItemPrice(
        supplier_item_id=supplier_item.id,
        valid_period=DateTimeTZRange(
            datetime(2026, 3, 1),  # OVERLAPS with price1
            datetime(2026, 9, 30)
        ),
        unit_price_cents=12000
    )
    db_session.add(price2)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "exclude_supplier_item_price_period_overlap" in str(exc_info.value)
    db_session.rollback()
```

---

### 5. Test Partial Indexes with Query Plans

**Pattern for Verifying Partial Index Usage:**
```python
def test_invoice_balance_uses_partial_index(db_session, test_tenant):
    """Verify that unpaid invoices query uses partial index"""
    
    # Create mix of paid and unpaid invoices
    for i in range(10):
        invoice = Invoice(
            tenant_id=test_tenant.id,
            invoice_number=f"INV-{i:04d}",
            balance_due_cents=0 if i % 2 == 0 else 10000
        )
        db_session.add(invoice)
    db_session.commit()
    
    # Query unpaid invoices (should use partial index)
    from sqlmodel import select
    unpaid = db_session.exec(
        select(Invoice).where(Invoice.balance_due_cents > 0)
    ).all()
    
    assert len(unpaid) == 5
    
    # Optionally verify query plan uses index
    result = db_session.execute(text("""
        EXPLAIN (FORMAT JSON)
        SELECT * FROM invoice WHERE balance_due_cents > 0
    """))
    explain_output = result.scalar()
    assert "idx_invoice_balance" in str(explain_output)
```

---

## Requirements

### Phase 6.0 Task Breakdown

Phase 6.0 is divided into **3 separate Alembic migrations** for risk isolation:

#### Task 1: Constraints & Audit Columns (Migration 1)

**Scope:**
- 14 multi-tenant unique constraints: `UniqueConstraint('tenant_id', 'code')`
- 5 business logic unique constraints
- 2 audit columns: `created_by`, `updated_by` on conversation_session

**Migration Pattern:**
```python
"""Phase 6.0 Task 1: Unique constraints and audit columns

Revision ID: phase_6_0_task_1_constraints
Revises: [PREVIOUS_REVISION]
Create Date: 2026-04-13
"""

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
    # ... (repeat for all 14 tables)
    
    # Business logic unique constraints (5 tables)
    op.create_unique_constraint(
        'uq_job_assignment_job_user',
        'job_assignment',
        ['job_id', 'user_id']
    )
    # ... (repeat for all 5 constraints)
```

#### Task 2: Partial Indexes & Exclusion (Migration 2)

**Scope:**
- 5 partial indexes with `postgresql_where` clauses
- 1 GiST exclusion constraint (temporal overlap prevention)
- 1 redundant index removal

**Migration Pattern:**
```python
"""Phase 6.0 Task 2: Partial indexes and exclusion constraint

Revision ID: phase_6_0_task_2_indexes
Revises: phase_6_0_task_1_constraints
Create Date: 2026-04-13
"""

def upgrade():
    # Ensure btree_gist extension exists
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist;')
    
    # Partial indexes
    op.create_index(
        'idx_invoice_balance',
        'invoice',
        ['balance_due_cents'],
        postgresql_where=text('balance_due_cents > 0')
    )
    # ... (repeat for all 5 partial indexes)
    
    # GiST exclusion constraint (raw SQL)
    op.execute("""
        ALTER TABLE supplier_item_price
        ADD CONSTRAINT exclude_supplier_item_price_period_overlap
        EXCLUDE USING gist (
            supplier_item_id WITH =,
            valid_period WITH &&
        );
    """)
    
    # Remove redundant index
    op.drop_index('ix_conversation_message_session_id', table_name='conversation_message')
```

#### Task 3: Composite Indexes (Migration 3)

**Scope:**
- 4 descending `created_at` indexes
- 10 composite indexes for common query patterns

**Migration Pattern:**
```python
"""Phase 6.0 Task 3: Composite and sorting indexes

Revision ID: phase_6_0_task_3_composite_indexes
Revises: phase_6_0_task_2_indexes
Create Date: 2026-04-13
"""

def upgrade():
    # Descending created_at indexes
    op.create_index(
        'idx_change_order_created_at',
        'change_order',
        [text('created_at DESC')]
    )
    # ... (repeat for all 4 DESC indexes)
    
    # Composite indexes
    op.create_index(
        'idx_connector_run_supplier_started',
        'connector_run_log',
        ['supplier_id', text('started_at DESC')]
    )
    # ... (repeat for all 10 composite indexes)
```

---

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

Verify that the database is ready for Phase 6.0 migrations by checking for data violations that would prevent constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation 1: Multi-Tenant Code Duplicates (MANDATORY)**

[See "Multi-Tenant Unique Constraints - Pre-Migration Validation" section above for complete query]

**Validation 2: Business Logic Duplicates (MANDATORY)**

[See "Business Logic Unique Constraints Validation" section above for complete queries]

**Validation 3: Temporal Overlap Detection (MANDATORY)**

[See "GiST Exclusion Constraint - Temporal Overlap Detection" section above for complete query]

**Validation 4: Extension Check**

```sql
-- Verify btree_gist extension exists
SELECT extname, extversion 
FROM pg_extension 
WHERE extname = 'btree_gist';
-- Expected: 1 row
```

**If ANY validation query fails:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results
- **Report** - Ask for guidance on data cleanup strategy
- **Clean** - Create remediation script
- **Re-validate** - Run all queries again

**Success Criteria for Task 2:**
- [ ] All multi-tenant duplicate queries return 0 rows
- [ ] All business logic duplicate queries return 0 rows
- [ ] Temporal overlap query returns 0 rows
- [ ] btree_gist extension verified installed
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

Use the Task 1 migration pattern from Requirements section above.

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

### Task 4: Task 2 Migration - Partial Indexes & Exclusion

**Effort:** 0.75 day
**Dependencies:** Task 3 must be complete
**Migration:** 2 of 3

#### What This Task Accomplishes

Generate and apply second Alembic migration with partial indexes and GiST exclusion constraint.

#### Implementation Steps

Follow same pattern as Task 3, using Task 2 migration template.

**Verification Queries:**
```sql
-- Verify partial indexes
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND indexname IN (
        'idx_invoice_balance',
        'idx_job_expense_unbilled',
        'idx_user_endpoint_primary_email',
        'idx_user_endpoint_email_value_lower',
        'idx_integration_cred_expires'
    )
ORDER BY tablename, indexname;
-- Expected: 5 rows with WHERE clauses in indexdef

-- Verify exclusion constraint
SELECT 
    conname,
    pg_get_constraintdef(c.oid) as definition
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'supplier_item_price'
    AND c.contype = 'x'
    AND conname = 'exclude_supplier_item_price_period_overlap';
-- Expected: 1 row

-- Verify redundant index removed
SELECT indexname
FROM pg_indexes
WHERE tablename = 'conversation_message'
    AND indexname = 'ix_conversation_message_session_id';
-- Expected: 0 rows
```

**Success Criteria for Task 4:**
- [ ] Migration 2 created with all partial indexes and exclusion constraint
- [ ] Migration applies successfully
- [ ] All verification queries pass
- [ ] Migration rolls back successfully

---

### Task 5: Task 3 Migration - Composite Indexes

**Effort:** 0.75 day
**Dependencies:** Task 4 must be complete
**Migration:** 3 of 3

#### What This Task Accomplishes

Generate and apply third Alembic migration with composite and sorting indexes.

#### Implementation Steps

Follow same pattern as Tasks 3-4, using Task 3 migration template.

**Verification Query:**
```sql
-- Verify all composite and sorting indexes
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND indexname IN (
        'idx_change_order_created_at',
        'idx_payment_created_at',
        'idx_qpl_action_created_at',
        'idx_quote_version_created_at',
        'idx_connector_run_supplier_started',
        'idx_connector_run_supplier_status',
        'idx_invoice_line_source',
        'idx_job_assignment_user_active',
        'idx_quote_message_tenant_quote_time',
        'idx_site_tenant_customer',
        'idx_tenant_markup_category',
        'idx_tenant_user_notif_pref',
        'idx_user_sso_provider_id',
        'idx_usage_ledger_tenant_feature'
    )
ORDER BY tablename, indexname;
-- Expected: 14 rows
```

**Success Criteria for Task 5:**
- [ ] Migration 3 created with all composite indexes
- [ ] Migration applies successfully
- [ ] All verification queries pass
- [ ] Migration rolls back successfully

---

### Task 6: Comprehensive Testing

**Effort:** 1.5 days
**Dependencies:** Tasks 3, 4, 5 must be complete

#### What This Task Accomplishes

Validate that all Phase 6.0 changes work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_comprehensive_schema.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0 - Advanced Constraints & Performance Indexes Verification
Validates multi-tenant constraints, business logic constraints, partial indexes,
GiST exclusion constraints, and composite indexes.

Reference: phase-6.0-db-schema-sync-10-plan.md
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime
from psycopg2.extras import DateTimeTZRange


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


class TestPartialIndexes:
    """Test partial index query performance"""
    
    def test_invoice_balance_partial_index(self, db_session, test_tenant):
        """Verify idx_invoice_balance index used for unpaid invoices"""
        # [See example in Critical Warnings section above]


class TestGiSTExclusionConstraint:
    """Test temporal overlap prevention"""
    
    def test_supplier_item_price_no_overlap(self, db_session, supplier_item):
        """Verify exclude_supplier_item_price_period_overlap constraint"""
        # [See example in Critical Warnings section above]
    
    def test_supplier_item_price_adjacent_periods_allowed(self, db_session, supplier_item):
        """Test that adjacent (non-overlapping) periods are allowed"""
        # Similar but verify adjacent periods DO work


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

**Success Criteria for Task 6:**
- [ ] Test file created with all test categories
- [ ] Multi-tenant constraint tests prevent duplicates
- [ ] Business logic constraint tests work correctly
- [ ] Partial index tests verify query performance
- [ ] GiST exclusion tests prevent overlaps
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

Run all verification queries from Tasks 3, 4, 5 to confirm database matches Golden Master.

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check all 3 migrations were applied successfully
3. Verify constraint/index definitions in database
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md`

Add implementation status:

```markdown
## Implementation Status Tracking

### Phase 6.0: Advanced Constraints & Performance Indexes - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_DAYS] days (actual)
**Priority:** HIGH

**Implementation Summary:**

- Model Verification: Updated 20+ tables across 8 model files
- Data Validation: All pre-migration validation queries passed
- Migration 1: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_task_1_constraints_audit_columns.py`]
- Migration 2: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_task_2_partial_indexes_exclusion.py`]
- Migration 3: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_task_3_composite_indexes.py`]
- Test Suite: [`test_phase_6_0_comprehensive_schema.py`] - 15+ tests ✅
- Final Results: 676/676 unit tests (100%), 703/703 total tests (100%)

**Key Changes:**
- ✅ 14 multi-tenant unique constraints (tenant_id, code)
- ✅ 5 business logic unique constraints
- ✅ 2 audit columns (conversation_session)
- ✅ 5 partial indexes with WHERE clauses
- ✅ 1 GiST exclusion constraint (temporal overlap prevention)
- ✅ 14 composite/sorting indexes
- ✅ 1 redundant index removed
- ✅ Database state fully aligns with Golden Master JSON
- ✅ Zero regressions in existing test suite
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For ALL Phase 6.0 Tasks:
- [ ] **Regression baseline captured** (661/661 unit, 688/688 total)
- [ ] **All multi-tenant duplicate queries returned 0 rows**
- [ ] **All business logic duplicate queries returned 0 rows**
- [ ] **Temporal overlap query returned 0 rows**
- [ ] **btree_gist extension verified installed**
- [ ] **All 20+ tables verified in Python models**
- [ ] **3 separate Alembic migrations created (Tasks 1, 2, 3)**
- [ ] **Migration 1 applied successfully** (constraints + audit columns)
- [ ] **Migration 2 applied successfully** (partial indexes + exclusion)
- [ ] **Migration 3 applied successfully** (composite indexes)
- [ ] **All database verification queries passed**
- [ ] **Comprehensive tests written and passing**
- [ ] **ALL 661 existing unit tests still passing**
- [ ] **ALL 688 total tests still passing**
- [ ] **New total: 676+/676+ unit, 703+/703+ total (100%)**
- [ ] **All 3 migrations rollback tested**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` - **Comprehensive Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models (20+ tables affected)
- `backend/app/models/customer.py` - 2 multi-tenant constraints
- `backend/app/models/billing.py` - 5 constraints + 2 partial indexes
- `backend/app/models/job.py` - 2 constraints + 1 partial index + composite indexes
- `backend/app/models/quoting.py` - 3 multi-tenant constraints + composite indexes
- `backend/app/models/subscription.py` - 1 multi-tenant constraint + composite index
- `backend/app/models/supplier.py` - 3 multi-tenant constraints + exclusion constraint + composite indexes
- `backend/app/models/tenant.py` - 3 constraints + 1 partial index + composite indexes
- `backend/app/models/voice.py` - 2 audit columns
- `backend/app/models/integration.py` - 1 partial index

---

## Risk Assessment

**For Phase 6.0:**
- **Duplicate Data Risk:** MEDIUM (duplicates would prevent constraint creation - validated before migration)
- **Temporal Overlap Risk:** MEDIUM (overlaps would prevent exclusion constraint - validated before migration)
- **Migration Complexity:** MEDIUM (3 separate migrations reduce complexity per migration)
- **Application Impact:** LOW (additive changes, improves data integrity without breaking changes)
- **Rollback Complexity:** LOW (3 independent migrations, surgical rollback)
- **Performance Impact:** POSITIVE (partial indexes and composite indexes improve query performance)
- **Mitigation:** Comprehensive pre-migration validation, 3-task separation, extensive testing

---

## Notes

### Important Patterns to Follow
- **Three Migrations:** Task 1 (constraints), Task 2 (indexes+exclusion), Task 3 (composite indexes)
- **Zero Duplicates:** Pre-migration validation MUST show 0 duplicates and 0 overlaps
- **Partial Indexes:** Always use `postgresql_where=text('...')` parameter
- **GiST Exclusion:** Use raw SQL (`op.execute`) not SQLAlchemy construct
- **Composite DESC:** Use `text('created_at DESC')` not string
- **Zero Regression:** All 661 unit + 688 total tests MUST pass

### Phase 6.0 Specific
- **Multi-tenant:** 14 tables get `UniqueConstraint('tenant_id', 'code')`
- **Business logic:** 5 tables get specific business unique constraints
- **Partial indexes:** 5 indexes with WHERE clauses for filtered queries
- **Exclusion:** Temporal overlap prevention on supplier_item_price
- **Composite:** 14 indexes optimizing common query patterns
- **Audit columns:** created_by, updated_by on conversation_session

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 6.0 plan for detailed specifications
- Verify all pre-migration validation queries passed
- Check that correct migration is being created (1, 2, or 3)
- Verify partial index WHERE clauses are using `text()`
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Phase 6.0 Task Checklist:
1. ✅ Capture baseline (661/661 unit, 688/688 total)
2. 🔍 **Verify all 20+ table definitions in Python models**
3. ✅ Verify Python syntax (`python -c "from app.models import *"`)
4. ⚠️ **CRITICAL: Run multi-tenant duplicate queries (14 tables)**
5. ⚠️ **CRITICAL: Run business logic duplicate queries (5 constraints)**
6. ⚠️ **CRITICAL: Run temporal overlap query**
7. ⚠️ **CRITICAL: Verify btree_gist extension exists**
8. ⚠️ **MANDATORY: Stop if ANY validation fails**
9. 🔧 **Create Migration 1: Constraints & Audit Columns**
10. ✅ Apply Migration 1, verify constraints created
11. 🔧 **Create Migration 2: Partial Indexes & Exclusion**
12. ✅ Apply Migration 2, verify indexes and exclusion created
13. 🔧 **Create Migration 3: Composite Indexes**
14. ✅ Apply Migration 3, verify composite indexes created
15. 🧪 **Create comprehensive test suite (all gap categories)**
16. 🔄 Run regression tests (676+/676+ unit, 703+/703+ total expected)
17. ↩️ Test rollback of all 3 migrations
18. 📚 Update project plan

Remember: Phase 6.0 brings multi-tenant isolation, business logic enforcement, temporal integrity, and performance optimization through strategic index placement. Validate thoroughly before each migration, test extensively, and ensure zero regressions!
