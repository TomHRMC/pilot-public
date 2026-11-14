# Task 2: Partial Indexes & Exclusion Constraint

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` - Task 2
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` - **Advanced Constraints & Performance Indexes Analysis** ⭐
- Current Live Database (Phase 6.0 Task 1 Post-State)
**Type:** Phase 6.0 - Partial Indexes + GiST Exclusion Constraint + Index Cleanup
**Priority:** HIGH
**Change Type:** PARTIAL INDEXES + EXCLUSION CONSTRAINT + INDEX REMOVAL

---

## Context

This is **Phase 6.0 Task 2 - DB Sync v#10**, the second of three tasks implementing comprehensive database constraints and performance optimizations.

**Root Cause:** 
- Missing partial indexes for filtered query optimization
- No temporal overlap prevention for supplier pricing (GiST exclusion constraint)
- Redundant indexes consuming resources

**Critical Impact:**
- **Performance Degradation:** Missing partial indexes cause full table scans on filtered queries
- **Temporal Integrity Violation:** Overlapping price periods possible (undefined pricing)
- **Resource Waste:** Redundant indexes consume disk space and slow down writes

**Scope:** **1 migration** - 5 partial indexes + 1 GiST exclusion constraint + 1 redundant index removal across 6 tables.

**Key Principle:** Phase 6.0 uses **3 separate Alembic migrations** (one per task) for surgical rollback capability and risk isolation.

---

## What Was Completed in Previous Phases

**Phase 6.0 Task 1 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 14 multi-tenant unique constraints added (tenant_id, code)
- ✅ 5 business logic unique constraints added
- ✅ 2 audit columns added (conversation_session: created_by, updated_by)
- ✅ 677/677 unit tests, 704/704 total tests passing (100%)

**Current Baseline:** 677/677 unit tests, 704/704 total tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement
- **Phase 5.1:** ✅ COMPLETE - Missing unique constraints & foreign keys
- **Phase 5.2:** ✅ COMPLETE - Exclusion constraints & critical indexes
- **Phase 5.3:** ✅ COMPLETE - Notification schema + idempotency + index standardization + triggers
- **Phase 6.0 Task 1:** ✅ COMPLETE - Constraints & audit columns

**See:**
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` for Phase 6.0 master plan
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` for comprehensive gap details

---

## Current Task: Partial Indexes & Exclusion Constraint

**Effort:** 1.5-2 hours
**Gap Reference:** Phase 6.0 Analysis - Performance & Temporal Integrity Gaps
**Change Type:** MODEL VERIFICATION + MIGRATION + DATA VALIDATION

This task implements performance-optimized partial indexes for common filtered queries and enforces temporal integrity on supplier pricing through a GiST exclusion constraint.

### What Needs to Be Fixed

**Partial Indexes (5 indexes):**

| Table | Index Name | Columns | WHERE Clause | Impact |
|-------|-----------|---------|--------------|--------|
| `invoice` | `idx_invoice_balance` | `balance_due_cents` | `balance_due_cents > 0` | Optimize unpaid invoice queries (80% smaller index) |
| `job_expense` | `idx_job_expense_unbilled` | `job_id` | `is_billable = true AND invoice_line_id IS NULL` | Optimize unbilled expense queries |
| `user_endpoint` | `idx_user_endpoint_primary_email` | `user_id` | `channel='email' AND is_primary = true` | Enforce one primary email per user (UNIQUE) |
| `user_endpoint` | `idx_user_endpoint_email_value_lower` | `lower(value)` | `channel='email' AND is_primary = true` | Case-insensitive email uniqueness (UNIQUE) |
| `integration_credential` | `idx_integration_cred_expires` | `expires_at` | `expires_at IS NOT NULL` | Optimize credential expiration checks |

**GiST Exclusion Constraint (1 constraint):**

| Table | Constraint Name | Exclusion Rule | Impact |
|-------|----------------|----------------|--------|
| `supplier_item_price` | `exclude_supplier_item_price_period_overlap` | `(supplier_item_id WITH =, valid_period WITH &&)` | Prevent overlapping price periods |

**Index Removal (1 index):**

| Table | Index to Drop | Reason |
|-------|--------------|--------|
| `conversation_message` | `ix_conversation_message_session_id` | Redundant (composite index `idx_conv_msg_session_time` already covers this) |

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

**Record the output of both results:** `677/677 & 704/704 tests passing` (Phase 6.0 Task 2 baseline - starting from Task 1 completion)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 6.0 Task 2 Specific Warnings

**BEFORE writing ANY code, review these critical Task 2 issues:**

### 1. Partial Indexes Use postgresql_where Parameter

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
from sqlalchemy import text

op.create_index(
    'idx_invoice_balance',
    'invoice',
    ['balance_due_cents'],
    postgresql_where=text('balance_due_cents > 0')  # CRITICAL
)
```

---

### 2. GiST Exclusion Constraint - Temporal Overlap Detection

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

### 3. GiST Exclusion Constraint Requires Raw SQL

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

### 4. Partial Index with Function - Use text() Wrapper

**Critical Pattern:** For indexes on expressions (like `lower(value)`), use `text()` wrapper.

**Correct Syntax:**
```python
from sqlalchemy import Index, text

# ✅ CORRECT - Index on expression with text()
Index(
    'idx_user_endpoint_email_value_lower',
    text('lower(value)'),
    unique=True,
    postgresql_where=text("channel='email' AND is_primary = true")
)

# ❌ WRONG - String without text() wrapper
Index('idx_user_endpoint_email_value_lower', 'lower(value)')  # Will fail
```

**In Alembic Migration:**
```python
op.create_index(
    'idx_user_endpoint_email_value_lower',
    'user_endpoint',
    [text('lower(value)')],  # CRITICAL: Use sa.text()
    unique=True,
    postgresql_where=text("channel='email' AND is_primary = true")
)
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

### 3. Test GiST Exclusion Constraint with Temporal Overlap

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

### 4. Test Partial Indexes with Query Plans

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

### Task 1: SQLModel Schema Definitions Verification

**Effort:** 0.5 hour
**Scope:** Update model definitions across 6 tables

#### What This Task Accomplishes

Update Python SQLModel definitions with partial indexes and GiST exclusion constraint. Note that Alembic may not autogenerate the exclusion constraint, so raw SQL will be used in migration.

#### Tables to Update (Task 2)

**Model Files & Required Changes:**

1. `backend/app/models/billing.py`
   - `Invoice`: Add partial index `idx_invoice_balance` on `balance_due_cents` WHERE `balance_due_cents > 0`

2. `backend/app/models/job.py`
   - `JobExpense`: Add partial index `idx_job_expense_unbilled` on `job_id` WHERE `is_billable = true AND invoice_line_id IS NULL`

3. `backend/app/models/tenant.py`
   - `UserEndpoint`: Add 2 partial unique indexes:
     - `idx_user_endpoint_primary_email` on `user_id` WHERE `channel='email' AND is_primary = true`
     - `idx_user_endpoint_email_value_lower` on `lower(value)` WHERE `channel='email' AND is_primary = true`

4. `backend/app/models/integration.py`
   - `IntegrationCredential`: Add partial index `idx_integration_cred_expires` on `expires_at` WHERE `expires_at IS NOT NULL`

5. `backend/app/models/supplier.py`
   - `SupplierItemPrice`: Add GiST exclusion constraint `exclude_supplier_item_price_period_overlap`

6. `backend/app/models/voice.py`
   - `ConversationMessage`: Verify `ix_conversation_message_session_id` will be dropped (no model change needed)

#### SQLModel Syntax Examples

**Partial Index (Simple):**
```python
from sqlalchemy import Index, text

class Invoice(SQLModel, table=True):
    __tablename__ = "invoice"
    
    # ... existing fields ...
    balance_due_cents: int = Field(default=0)
    
    __table_args__ = (
        Index(
            'idx_invoice_balance',
            'balance_due_cents',
            postgresql_where=text('balance_due_cents > 0')
        ),
        # ... other indexes/constraints ...
    )
```

**Partial Unique Index:**
```python
class UserEndpoint(SQLModel, table=True):
    __tablename__ = "user_endpoint"
    
    # ... existing fields ...
    
    __table_args__ = (
        Index(
            'idx_user_endpoint_primary_email',
            'user_id',
            unique=True,
            postgresql_where=text("channel='email' AND is_primary = true")
        ),
        Index(
            'idx_user_endpoint_email_value_lower',
            text('lower(value)'),
            unique=True,
            postgresql_where=text("channel='email' AND is_primary = true")
        ),
        # ... other indexes/constraints ...
    )
```

**GiST Exclusion Constraint:**
```python
from sqlalchemy import ExcludeConstraint

class SupplierItemPrice(SQLModel, table=True):
    __tablename__ = "supplier_item_price"
    
    # ... existing fields ...
    
    __table_args__ = (
        ExcludeConstraint(
            ('supplier_item_id', '='),
            ('valid_period', '&&'),
            name='exclude_supplier_item_price_period_overlap',
            using='gist'
        ),
        # ... other indexes/constraints ...
    )
```

**Success Criteria for Task 1:**
- [ ] All 5 partial indexes added to models
- [ ] GiST exclusion constraint added to supplier_item_price model
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models import *"`)

---

### Task 2: Pre-Migration Data Validation

**Effort:** 0.25 hour
**Dependencies:** None (can run independently)
**CRITICAL:** Validation MUST pass before generating migration

#### What This Task Accomplishes

Verify that the database is ready for Phase 6.0 Task 2 migration by checking for temporal overlaps that would prevent constraint creation.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation 1: Temporal Overlap Detection (MANDATORY)**

[See "GiST Exclusion Constraint - Temporal Overlap Detection" section above for complete query]

**Validation 2: Extension Check (MANDATORY)**

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
- **Report** - Ask for guidance on resolution strategy
- **Clean** - Remediate data issues
- **Re-validate** - Run all queries again

**Success Criteria for Task 2:**
- [ ] Temporal overlap query returns 0 rows
- [ ] btree_gist extension verified installed
- [ ] Validation results documented

---

### Task 3: Task 2 Migration - Partial Indexes & Exclusion

**Effort:** 1 hour
**Dependencies:** Task 1 (models) and Task 2 (validation) must be complete
**Migration:** 2 of 3

#### What This Task Accomplishes

Generate and apply second Alembic migration with partial indexes, GiST exclusion constraint, and redundant index removal.

#### Implementation Steps

**Step 1: Generate Migration Skeleton**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_task_2_partial_indexes_exclusion"
```

**Step 2: Manually Construct Complete Migration**

```python
"""Phase 6.0 Task 2: Partial indexes and exclusion constraint

Revision ID: phase_6_0_task_2_indexes
Revises: [PREVIOUS_REVISION]
Create Date: 2026-04-13
"""

import sqlalchemy as sa
from sqlalchemy import text
from alembic import op

# revision identifiers, used by Alembic.
revision = 'phase_6_0_task_2_indexes'
down_revision = '[PREVIOUS_REVISION]'  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Ensure btree_gist extension exists (required for exclusion constraint)
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist;')
    
    # Partial Indexes
    op.create_index(
        'idx_invoice_balance',
        'invoice',
        ['balance_due_cents'],
        postgresql_where=text('balance_due_cents > 0')
    )
    
    op.create_index(
        'idx_job_expense_unbilled',
        'job_expense',
        ['job_id'],
        postgresql_where=text('is_billable = true AND invoice_line_id IS NULL')
    )
    
    op.create_index(
        'idx_user_endpoint_primary_email',
        'user_endpoint',
        ['user_id'],
        unique=True,
        postgresql_where=text("channel='email' AND is_primary = true")
    )
    
    op.create_index(
        'idx_user_endpoint_email_value_lower',
        'user_endpoint',
        [text('lower(value)')],
        unique=True,
        postgresql_where=text("channel='email' AND is_primary = true")
    )
    
    op.create_index(
        'idx_integration_cred_expires',
        'integration_credential',
        ['expires_at'],
        postgresql_where=text('expires_at IS NOT NULL')
    )
    
    # GiST Exclusion Constraint (raw SQL)
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


def downgrade():
    # Restore redundant index
    op.create_index(
        'ix_conversation_message_session_id',
        'conversation_message',
        ['session_id']
    )
    
    # Drop exclusion constraint
    op.execute("""
        ALTER TABLE supplier_item_price
        DROP CONSTRAINT IF EXISTS exclude_supplier_item_price_period_overlap;
    """)
    
    # Drop partial indexes
    op.drop_index('idx_integration_cred_expires', table_name='integration_credential')
    op.drop_index('idx_user_endpoint_email_value_lower', table_name='user_endpoint')
    op.drop_index('idx_user_endpoint_primary_email', table_name='user_endpoint')
    op.drop_index('idx_job_expense_unbilled', table_name='job_expense')
    op.drop_index('idx_invoice_balance', table_name='invoice')
```

**Step 3: Apply Migration**
```bash
alembic upgrade head
```

**Step 4: Verify Database State**
```sql
-- Verify partial indexes exist with WHERE clauses
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

-- Verify exclusion constraint exists
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

**Step 5: Test Migration Rollback**
```bash
alembic downgrade -1
# Verify indexes/constraints removed
alembic upgrade head
```

**Success Criteria for Task 3:**
- [ ] Migration 2 created with all partial indexes and exclusion constraint
- [ ] Migration applies successfully
- [ ] All verification queries pass
- [ ] Migration rolls back successfully
- [ ] Migration re-applies successfully

---

### Task 4: Comprehensive Testing

**Effort:** 1 hour
**Dependencies:** Task 3 must be complete

#### What This Task Accomplishes

Validate that all Phase 6.0 Task 2 changes work correctly through comprehensive automated tests.

#### Test File Structure

**File:** `backend/tests/test_phase_6_0_task_2_indexes_exclusion.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0 Task 2 - Partial Indexes & Exclusion Constraint Verification
Validates partial indexes, GiST exclusion constraint, and redundant index removal.

Reference: phase-6.0-db-schema-sync-10-plan.md - Task 2
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from psycopg2.extras import DateTimeTZRange


class TestPartialIndexes:
    """Test partial index query performance"""
    
    def test_invoice_balance_partial_index(self, db_session, test_tenant):
        """Verify idx_invoice_balance index used for unpaid invoices"""
        # [See example in Critical Warnings section above]
    
    def test_job_expense_unbilled_partial_index(self, db_session, job):
        """Verify idx_job_expense_unbilled index used for unbilled expenses"""
        # Similar pattern for job expenses


class TestGiSTExclusionConstraint:
    """Test temporal overlap prevention"""
    
    def test_supplier_item_price_no_overlap(self, db_session, supplier_item):
        """Verify exclude_supplier_item_price_period_overlap constraint"""
        # [See example in Critical Warnings section above]
    
    def test_supplier_item_price_adjacent_periods_allowed(self, db_session, supplier_item):
        """Test that adjacent (non-overlapping) periods are allowed"""
        # Similar but verify adjacent periods DO work


class TestIndexRemoval:
    """Test redundant index removal"""
    
    def test_redundant_index_removed(self, db_session):
        """Verify ix_conversation_message_session_id no longer exists"""
        result = db_session.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'conversation_message'
                AND indexname = 'ix_conversation_message_session_id'
        """))
        assert result.fetchone() is None
```

**Success Criteria for Task 4:**
- [ ] Test file created with all test categories
- [ ] Partial index tests verify query optimization
- [ ] GiST exclusion tests prevent overlaps
- [ ] Index removal test confirms cleanup
- [ ] Full test suite passes: 682+/682+ unit tests, 709+/709+ total (100%)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 682+ passed (677 baseline + ~5 new tests)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 709+ passed (704 baseline + ~5 new tests)
```

### Step 2: Verify Database State

Run all verification queries from Task 3 to confirm database matches Golden Master.

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check migration was applied successfully
3. Verify index/constraint definitions in database
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md`

Add implementation status:

```markdown
### Phase 6.0 Task 2: Partial Indexes & Exclusion - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_HOURS] hours (actual)
**Priority:** HIGH

**Implementation Summary:**

- Model Verification: Updated 6 tables across 5 model files
- Data Validation: Temporal overlap validation passed (0 overlaps found)
- Migration 2: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_task_2_partial_indexes_exclusion.py`]
- Test Suite: [`test_phase_6_0_task_2_indexes_exclusion.py`] - 5+ tests ✅
- Final Results: 682/682 unit tests (100%), 709/709 total tests (100%)

**Key Changes:**
- ✅ 5 partial indexes with WHERE clauses
- ✅ 1 GiST exclusion constraint (temporal overlap prevention)
- ✅ 1 redundant index removed
- ✅ Zero regressions in existing test suite
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 2 Only:
- [ ] **Regression baseline captured** (677/677 unit, 704/704 total)
- [ ] **Temporal overlap query returned 0 rows**
- [ ] **btree_gist extension verified installed**
- [ ] **All 6 tables verified in Python models**
- [ ] **Migration 2 created and applied successfully**
- [ ] **All database verification queries passed**
- [ ] **Comprehensive tests written and passing**
- [ ] **ALL 677 existing unit tests still passing**
- [ ] **ALL 704 total tests still passing**
- [ ] **New total: 682+/682+ unit, 709+/709+ total (100%)**
- [ ] **Migration rollback tested**
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` - **Comprehensive Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models (6 tables affected)
- `backend/app/models/billing.py` - 1 partial index
- `backend/app/models/job.py` - 1 partial index
- `backend/app/models/tenant.py` - 2 partial unique indexes
- `backend/app/models/integration.py` - 1 partial index
- `backend/app/models/supplier.py` - 1 GiST exclusion constraint
- `backend/app/models/voice.py` - 1 redundant index removal

---

## Risk Assessment

**For Task 2:**
- **Temporal Overlap Risk:** MEDIUM (existing overlaps would prevent constraint creation - validated before migration)
- **Migration Complexity:** MEDIUM (5 partial indexes + 1 exclusion constraint + 1 removal)
- **Application Impact:** LOW (additive performance optimization, no breaking changes)
- **Rollback Complexity:** LOW (single migration, surgical rollback)
- **Performance Impact:** POSITIVE (partial indexes improve query performance)
- **Mitigation:** Pre-migration validation, extensive testing

---

## Notes

### Important Patterns to Follow
- **Partial Indexes:** Always use `postgresql_where=text('...')` parameter
- **GiST Exclusion:** Use raw SQL (`op.execute`) not SQLAlchemy construct
- **Expression Indexes:** Use `text('lower(value)')` for function-based indexes
- **Zero Regression:** All 677 unit + 704 total tests MUST pass

### Task 2 Specific
- **Partial indexes:** 5 indexes with WHERE clauses for filtered queries
- **Exclusion:** Temporal overlap prevention on supplier_item_price
- **Extension:** btree_gist required (already installed from Phase 5.2)
- **Cleanup:** Remove redundant ix_conversation_message_session_id

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 6.0 plan for detailed specifications
- Verify temporal overlap validation query passed
- Verify btree_gist extension exists
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Task 2 Checklist:
1. ✅ Capture baseline (677/677 unit, 704/704 total)
2. 🔍 **Verify all 6 table definitions in Python models**
3. ✅ Verify Python syntax (`python -c "from app.models import *"`)
4. ⚠️ **CRITICAL: Run temporal overlap query**
5. ⚠️ **CRITICAL: Verify btree_gist extension exists**
6. ⚠️ **MANDATORY: Stop if ANY validation fails**
7. 🔧 **Create Migration 2: Partial Indexes & Exclusion**
8. ✅ Apply Migration 2, verify indexes and exclusion created
9. 🧪 **Create comprehensive test suite (partial indexes + exclusion + removal)**
10. 🔄 Run regression tests (682+/682+ unit, 709+/709+ total expected)
11. ↩️ Test rollback of migration
12. 📚 Update project plan

Remember: Task 2 brings performance optimization through partial indexes and temporal integrity through GiST exclusion constraints. Validate thoroughly before migration, test extensively, and ensure zero regressions!
