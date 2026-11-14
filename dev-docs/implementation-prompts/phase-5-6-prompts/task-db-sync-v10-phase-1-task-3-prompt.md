# Task 3: Task 3 Migration - Composite Indexes

**Reference:** `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` - Task 3
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` - **Advanced Constraints & Performance Indexes Analysis** ⭐
- Current Live Database (Phase 6.0 Task 2 Post-State)
**Type:** Phase 6.0 - Composite Indexes Migration (3 of 3)
**Priority:** MEDIUM
**Change Type:** COMPOSITE INDEXES + SORTING INDEXES

---

## Context

This is **Phase 6.0 Task 3 - Composite Indexes**, the final migration in the Phase 6.0 series implementing **14 performance-optimized indexes** for common query patterns.

**Root Cause:** 
- Missing composite indexes for multi-column query patterns
- Missing descending `created_at` indexes for time-sorted queries
- Query planner forced to use suboptimal index combinations or sequential scans

**Critical Impact:**
- **Query Performance:** Common queries performing full table scans or inefficient index combinations
- **Scalability Risk:** Performance degradation as data volume grows
- **User Experience:** Slow dashboard loads, delayed reports, poor mobile app responsiveness

**Scope:** **1 migration** - 4 descending `created_at` indexes + 10 composite indexes across 10 tables.

**Key Principle:** Task 3 is the **lowest-risk migration** in Phase 6.0 - purely additive performance optimization with no data integrity changes.

---

## What Was Completed in Previous Tasks

**Phase 6.0 Task 1 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 14 multi-tenant unique constraints (tenant_id, code)
- ✅ 5 business logic unique constraints
- ✅ 2 audit columns on conversation_session (created_by, updated_by)
- ✅ 16 new tests passing
- ✅ 677/677 unit tests, 704/704 total tests passing (100%)

**Phase 6.0 Task 2 Status:** ✅ COMPLETE (April 13, 2026)
- ✅ 4 partial indexes with WHERE clauses (2 pre-existed)
- ✅ 1 GiST exclusion constraint (temporal overlap prevention)
- ✅ 1 redundant index removed
- ✅ 12 new tests passing
- ✅ 689/689 unit tests, 716/716 total tests passing (100%)

**Current Baseline:** 689/689 unit tests, 716/716 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` for Phase 6.0 complete plan
- `dev-docs/implementation-prompts/task-db-sync-v10-phase-1-task-1-prompt.md` for Task 1 details
- `dev-docs/implementation-prompts/task-db-sync-v10-phase-1-task-2-prompt.md` for Task 2 details

---

## Current Task: Task 3 Migration - Composite Indexes

**Effort:** 0.75 day
**Gap Reference:** Phase 6.0 Analysis - Category 5: Composite & Sorting Indexes
**Change Type:** MIGRATION + TESTING

This task implements the final set of performance-optimized indexes for Phase 6.0, focusing on common query patterns identified through application usage analysis.

### What Needs to Be Fixed

**Descending Created-At Indexes (4 tables):**

| Table | Index Name | Definition | Query Pattern |
|-------|-----------|------------|---------------|
| `change_order` | `idx_change_order_created_at` | `text('created_at DESC')` | Recent change orders sorted by time |
| `payment` | `idx_payment_created_at` | `text('created_at DESC')` | Recent payments dashboard |
| `quote_public_link_contact_action` | `idx_qpl_action_created_at` | `text('created_at DESC')` | Quote link activity timeline |
| `quote_version` | `idx_quote_version_created_at` | `text('created_at DESC')` | Quote revision history |

**Composite Indexes (10 tables):**

| Table | Index Name | Columns | Business Use Case |
|-------|-----------|---------|-------------------|
| `connector_run_log` | `idx_connector_run_supplier_started` | `supplier_id`, `text('started_at DESC')` | Supplier sync history |
| `connector_run_log` | `idx_connector_run_supplier_status` | `supplier_id`, `status`, `text('started_at DESC')` | Failed sync monitoring |
| `invoice_line` | `idx_invoice_line_source` | `source_type`, `source_id` | Polymorphic source lookup |
| `job_assignment` | `idx_job_assignment_user_active` | `user_id`, `is_active` | User's active jobs |
| `quote_message` | `idx_quote_message_tenant_quote_time` | `tenant_id`, `quote_id`, `text('created_at DESC')` | Quote conversation thread |
| `site` | `idx_site_tenant_customer` | `tenant_id`, `customer_id` | Customer sites list |
| `tenant_markup_version` | `idx_tenant_markup_category` | `tenant_id`, `job_expense_category_code` | Markup history by category |
| `tenant_user_notification_pref` | `idx_tenant_user_notif_pref` | `tenant_id`, `user_id` | User notification settings |
| `user_sso_identity` | `idx_user_sso_provider_id` | `sso_provider_code`, `provider_user_id` | SSO login lookup |
| `usage_ledger` | `idx_usage_ledger_tenant_feature` | `tenant_id`, `product_feature_code`, `is_reported` | Usage billing aggregation |

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

**Record the output of both results:** `689/689 & 716/716 tests passing` (Phase 6.0 Task 2 completion baseline)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 6.0 Task 3 Specific Warnings

**BEFORE writing ANY code, review these Task 3 critical issues:**

### 1. Composite Indexes with DESC Ordering Use text()

**CRITICAL Pattern:** For descending order in composite indexes, use `text()` wrapper.

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

# ✅ CORRECT - Three-column composite with DESC
Index(
    'idx_quote_message_tenant_quote_time',
    'tenant_id',
    'quote_id',
    text('created_at DESC')
)

# ❌ WRONG - String without text() wrapper
Index('idx_payment_created_at', 'created_at DESC')  # Will fail
```

**In Alembic Migration:**
```python
from sqlalchemy import text

op.create_index(
    'idx_payment_created_at',
    'payment',
    [text('created_at DESC')]  # CRITICAL: Use sa.text()
)

op.create_index(
    'idx_connector_run_supplier_started',
    'connector_run_log',
    ['supplier_id', text('started_at DESC')]  # Mixed regular + DESC
)
```

---

### 2. Index Naming Convention Must Match AevoFab Standards

**CRITICAL:** All indexes MUST follow the `idx_*` naming convention.

**Pattern:**
- Descending time indexes: `idx_{table}_created_at` or `idx_{table}_{column}_created_at`
- Composite indexes: `idx_{table}_{purpose}` (descriptive purpose, not just column names)

**Examples:**
```python
# ✅ CORRECT
Index('idx_connector_run_supplier_started', ...)  # Descriptive
Index('idx_quote_message_tenant_quote_time', ...)  # Clear purpose
Index('idx_usage_ledger_tenant_feature', ...)     # Business context

# ❌ WRONG
Index('connector_run_idx', ...)              # Wrong prefix
Index('idx_connector_run_log_supplier_id_started_at_desc', ...)  # Too verbose
```

---

### 3. Model Updates Must Include All Indexes in __table_args__

**Pattern:**
```python
from sqlalchemy import Index, text

class ConnectorRunLog(SQLModel, table=True):
    __tablename__ = "connector_run_log"
    
    # ... field definitions ...
    
    __table_args__ = (
        # Existing indexes
        Index('idx_connector_run_tenant', 'tenant_id'),
        
        # NEW: Task 3 indexes
        Index(
            'idx_connector_run_supplier_started',
            'supplier_id',
            text('started_at DESC')
        ),
        Index(
            'idx_connector_run_supplier_status',
            'supplier_id',
            'status',
            text('started_at DESC')
        ),
    )
```

**CRITICAL:** Do not forget to import `text` from `sqlalchemy`:
```python
from sqlalchemy import Index, text  # text is REQUIRED for DESC
```

---

### 4. Migration Must Be Standalone (Migration 3 of 3)

**MANDATORY:** Task 3 is the **third and final migration** in Phase 6.0.

**Migration Pattern:**
```python
"""Phase 6.0 Task 3: Composite and sorting indexes

Revision ID: phase_6_0_task_3_composite_indexes
Revises: phase_6_0_task_2_indexes  # MUST revise Task 2
Create Date: 2026-04-13
"""

from alembic import op
from sqlalchemy import text

def upgrade():
    # Descending created_at indexes (4)
    op.create_index(
        'idx_change_order_created_at',
        'change_order',
        [text('created_at DESC')]
    )
    # ... (repeat for all 4 DESC indexes)
    
    # Composite indexes (10)
    op.create_index(
        'idx_connector_run_supplier_started',
        'connector_run_log',
        ['supplier_id', text('started_at DESC')]
    )
    # ... (repeat for all 10 composite indexes)

def downgrade():
    # Drop all indexes in reverse order
    # ... (full downgrade implementation)
```

---

### 5. No Data Validation Required (Low Risk)

**Good News:** Unlike Tasks 1 and 2, Task 3 requires **NO pre-migration data validation**.

**Why:**
- Indexes are purely additive (no constraints)
- No risk of data violations
- No risk of temporal overlaps
- No risk of duplicate data

**You can proceed directly to migration creation.**

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

### 3. Test Index Usage with Query Plans (Optional)

**Pattern for Verifying Index Usage:**
```python
from sqlalchemy import text

def test_connector_run_uses_composite_index(db_session, supplier):
    """Verify that supplier sync history query uses composite index"""
    
    # Create test data
    for i in range(10):
        log = ConnectorRunLog(
            supplier_id=supplier.id,
            status='success' if i % 2 == 0 else 'failed',
            started_at=datetime.utcnow() - timedelta(hours=i)
        )
        db_session.add(log)
    db_session.commit()
    
    # Query recent runs (should use composite index)
    from sqlmodel import select
    recent_runs = db_session.exec(
        select(ConnectorRunLog)
        .where(ConnectorRunLog.supplier_id == supplier.id)
        .order_by(ConnectorRunLog.started_at.desc())
        .limit(5)
    ).all()
    
    assert len(recent_runs) == 5
    
    # Optionally verify query plan uses index
    result = db_session.execute(text("""
        EXPLAIN (FORMAT JSON)
        SELECT * FROM connector_run_log 
        WHERE supplier_id = :supplier_id 
        ORDER BY started_at DESC 
        LIMIT 5
    """), {"supplier_id": str(supplier.id)})
    explain_output = result.scalar()
    assert "idx_connector_run_supplier_started" in str(explain_output)
```

---

## Requirements

### Task 3: Composite Indexes (Migration 3 of 3)

**Objective**: Implement all composite and sorting indexes for performance optimization

**Scope**:
- 4 descending `created_at` indexes
- 10 composite indexes for common query patterns

**Estimated Duration**: 0.75 day

**Files to Update**:
1. `backend/app/models/job.py` - 2 indexes
2. `backend/app/models/billing.py` - 2 indexes
3. `backend/app/models/quoting.py` - 3 indexes
4. `backend/app/models/supplier.py` - 2 indexes
5. `backend/app/models/customer.py` - 1 index
6. `backend/app/models/tenant.py` - 3 indexes
7. `backend/app/models/subscription.py` - 1 index

---

### Step 1: Update SQLModel Definitions

**Add indexes to `__table_args__` in model files:**

#### File 1: `backend/app/models/job.py`

**ChangeOrder:**
```python
from sqlalchemy import Index, text

class ChangeOrder(SQLModel, table=True):
    __tablename__ = "change_order"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Descending created_at
        Index('idx_change_order_created_at', text('created_at DESC')),
    )
```

**JobAssignment:**
```python
class JobAssignment(SQLModel, table=True):
    __tablename__ = "job_assignment"
    
    # ... existing fields ...
    
    __table_args__ = (
        # Task 1 constraint
        UniqueConstraint('job_id', 'user_id', name='uq_job_assignment_job_user'),
        
        # ... existing indexes ...
        
        # NEW: Task 3 - Composite index for active jobs by user
        Index('idx_job_assignment_user_active', 'user_id', 'is_active'),
    )
```

#### File 2: `backend/app/models/billing.py`

**Payment:**
```python
class Payment(SQLModel, table=True):
    __tablename__ = "payment"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Descending created_at
        Index('idx_payment_created_at', text('created_at DESC')),
    )
```

**InvoiceLine:**
```python
class InvoiceLine(SQLModel, table=True):
    __tablename__ = "invoice_line"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Polymorphic source lookup
        Index('idx_invoice_line_source', 'source_type', 'source_id'),
    )
```

#### File 3: `backend/app/models/quoting.py`

**QuotePublicLinkContactAction:**
```python
class QuotePublicLinkContactAction(SQLModel, table=True):
    __tablename__ = "quote_public_link_contact_action"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Descending created_at
        Index('idx_qpl_action_created_at', text('created_at DESC')),
    )
```

**QuoteVersion:**
```python
class QuoteVersion(SQLModel, table=True):
    __tablename__ = "quote_version"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Descending created_at
        Index('idx_quote_version_created_at', text('created_at DESC')),
    )
```

**QuoteMessage:**
```python
class QuoteMessage(SQLModel, table=True):
    __tablename__ = "quote_message"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Quote conversation thread
        Index(
            'idx_quote_message_tenant_quote_time',
            'tenant_id',
            'quote_id',
            text('created_at DESC')
        ),
    )
```

#### File 4: `backend/app/models/supplier.py`

**ConnectorRunLog:**
```python
class ConnectorRunLog(SQLModel, table=True):
    __tablename__ = "connector_run_log"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Supplier sync history
        Index(
            'idx_connector_run_supplier_started',
            'supplier_id',
            text('started_at DESC')
        ),
        Index(
            'idx_connector_run_supplier_status',
            'supplier_id',
            'status',
            text('started_at DESC')
        ),
    )
```

#### File 5: `backend/app/models/customer.py`

**Site:**
```python
class Site(SQLModel, table=True):
    __tablename__ = "site"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Customer sites lookup
        Index('idx_site_tenant_customer', 'tenant_id', 'customer_id'),
    )
```

#### File 6: `backend/app/models/tenant.py`

**TenantMarkupVersion:**
```python
class TenantMarkupVersion(SQLModel, table=True):
    __tablename__ = "tenant_markup_version"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Markup history by category
        Index('idx_tenant_markup_category', 'tenant_id', 'job_expense_category_code'),
    )
```

**TenantUserNotificationPref:**
```python
class TenantUserNotificationPref(SQLModel, table=True):
    __tablename__ = "tenant_user_notification_pref"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - User notification settings
        Index('idx_tenant_user_notif_pref', 'tenant_id', 'user_id'),
    )
```

**UserSsoIdentity:**
```python
class UserSsoIdentity(SQLModel, table=True):
    __tablename__ = "user_sso_identity"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - SSO login lookup
        Index('idx_user_sso_provider_id', 'sso_provider_code', 'provider_user_id'),
    )
```

#### File 7: `backend/app/models/subscription.py`

**UsageLedger:**
```python
class UsageLedger(SQLModel, table=True):
    __tablename__ = "usage_ledger"
    
    # ... existing fields ...
    
    __table_args__ = (
        # ... existing indexes ...
        
        # NEW: Task 3 - Usage billing aggregation
        Index('idx_usage_ledger_tenant_feature', 'tenant_id', 'product_feature_code', 'is_reported'),
    )
```

**Success Criteria for Step 1:**
- [ ] All 14 indexes added to appropriate model files
- [ ] All imports include `from sqlalchemy import Index, text`
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models import *"`)

---

### Step 2: Generate Alembic Migration

**Generate Migration Skeleton:**
```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_6_0_task_3_composite_indexes"
```

**Manually Construct Complete Migration:**

```python
"""Phase 6.0 Task 3: Composite and sorting indexes

Revision ID: phase_6_0_task_3_composite_indexes
Revises: [PREVIOUS_REVISION_FROM_TASK_2]
Create Date: 2026-04-13
"""

from alembic import op
from sqlalchemy import text

# Revision identifiers
revision = 'phase_6_0_task_3_composite_indexes'
down_revision = '[PREVIOUS_REVISION_FROM_TASK_2]'  # From Task 2
branch_labels = None
depends_on = None


def upgrade():
    # ========== DESCENDING CREATED_AT INDEXES (4) ==========
    
    op.create_index(
        'idx_change_order_created_at',
        'change_order',
        [text('created_at DESC')]
    )
    
    op.create_index(
        'idx_payment_created_at',
        'payment',
        [text('created_at DESC')]
    )
    
    op.create_index(
        'idx_qpl_action_created_at',
        'quote_public_link_contact_action',
        [text('created_at DESC')]
    )
    
    op.create_index(
        'idx_quote_version_created_at',
        'quote_version',
        [text('created_at DESC')]
    )
    
    # ========== COMPOSITE INDEXES (10) ==========
    
    # Connector run log: Supplier sync history
    op.create_index(
        'idx_connector_run_supplier_started',
        'connector_run_log',
        ['supplier_id', text('started_at DESC')]
    )
    
    # Connector run log: Failed sync monitoring
    op.create_index(
        'idx_connector_run_supplier_status',
        'connector_run_log',
        ['supplier_id', 'status', text('started_at DESC')]
    )
    
    # Invoice line: Polymorphic source lookup
    op.create_index(
        'idx_invoice_line_source',
        'invoice_line',
        ['source_type', 'source_id']
    )
    
    # Job assignment: User's active jobs
    op.create_index(
        'idx_job_assignment_user_active',
        'job_assignment',
        ['user_id', 'is_active']
    )
    
    # Quote message: Quote conversation thread
    op.create_index(
        'idx_quote_message_tenant_quote_time',
        'quote_message',
        ['tenant_id', 'quote_id', text('created_at DESC')]
    )
    
    # Site: Customer sites list
    op.create_index(
        'idx_site_tenant_customer',
        'site',
        ['tenant_id', 'customer_id']
    )
    
    # Tenant markup version: Markup history by category
    op.create_index(
        'idx_tenant_markup_category',
        'tenant_markup_version',
        ['tenant_id', 'job_expense_category_code']
    )
    
    # Tenant user notification pref: User notification settings
    op.create_index(
        'idx_tenant_user_notif_pref',
        'tenant_user_notification_pref',
        ['tenant_id', 'user_id']
    )
    
    # User SSO identity: SSO login lookup
    op.create_index(
        'idx_user_sso_provider_id',
        'user_sso_identity',
        ['sso_provider_code', 'provider_user_id']
    )
    
    # Usage ledger: Usage billing aggregation
    op.create_index(
        'idx_usage_ledger_tenant_feature',
        'usage_ledger',
        ['tenant_id', 'product_feature_code', 'is_reported']
    )


def downgrade():
    # Drop all indexes in reverse order
    
    op.drop_index('idx_usage_ledger_tenant_feature', table_name='usage_ledger')
    op.drop_index('idx_user_sso_provider_id', table_name='user_sso_identity')
    op.drop_index('idx_tenant_user_notif_pref', table_name='tenant_user_notification_pref')
    op.drop_index('idx_tenant_markup_category', table_name='tenant_markup_version')
    op.drop_index('idx_site_tenant_customer', table_name='site')
    op.drop_index('idx_quote_message_tenant_quote_time', table_name='quote_message')
    op.drop_index('idx_job_assignment_user_active', table_name='job_assignment')
    op.drop_index('idx_invoice_line_source', table_name='invoice_line')
    op.drop_index('idx_connector_run_supplier_status', table_name='connector_run_log')
    op.drop_index('idx_connector_run_supplier_started', table_name='connector_run_log')
    
    op.drop_index('idx_quote_version_created_at', table_name='quote_version')
    op.drop_index('idx_qpl_action_created_at', table_name='quote_public_link_contact_action')
    op.drop_index('idx_payment_created_at', table_name='payment')
    op.drop_index('idx_change_order_created_at', table_name='change_order')
```

**Success Criteria for Step 2:**
- [ ] Migration file created with correct revision chain
- [ ] All 14 indexes included in upgrade()
- [ ] All indexes use correct `text()` wrapper for DESC columns
- [ ] Complete downgrade() implementation
- [ ] Migration file passes Python syntax check

---

### Step 3: Apply Migration

**Apply Migration:**
```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade [TASK_2_REV] -> [TASK_3_REV], phase_6_0_task_3_composite_indexes
```

**Success Criteria for Step 3:**
- [ ] Migration applies without errors
- [ ] No warnings about index creation failures
- [ ] Alembic current shows Task 3 revision as head

---

### Step 4: Verify Database State

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

**Verify DESC Ordering:**
```sql
-- Verify DESC indexes contain 'DESC' in definition
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND indexname IN (
        'idx_change_order_created_at',
        'idx_payment_created_at',
        'idx_qpl_action_created_at',
        'idx_quote_version_created_at'
    )
    AND indexdef LIKE '%DESC%'
ORDER BY indexname;
-- Expected: 4 rows (all should contain DESC)
```

**Success Criteria for Step 4:**
- [ ] All 14 indexes exist in database
- [ ] All 4 DESC indexes contain DESC in definition
- [ ] Index names follow `idx_*` convention
- [ ] No duplicate or misnamed indexes

---

### Step 5: Test Migration Rollback

**Test Rollback:**
```bash
alembic downgrade -1
```

**Verify indexes removed:**
```sql
SELECT COUNT(*) as removed_count
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
    );
-- Expected: 0 (all removed)
```

**Re-apply Migration:**
```bash
alembic upgrade head
```

**Success Criteria for Step 5:**
- [ ] Migration rolls back successfully
- [ ] All 14 indexes removed during downgrade
- [ ] Migration re-applies successfully
- [ ] All 14 indexes re-created

---

### Step 6: Comprehensive Testing

**Create Test File:** `backend/tests/test_phase_6_0_task_3_composite_indexes.py`

**Test Categories:**

```python
"""
Test Suite: Phase 6.0 Task 3 - Composite Indexes Verification
Validates composite and sorting indexes for common query patterns.

Reference: phase-6.0-db-schema-sync-10-plan.md - Task 3
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlmodel import select


class TestDescendingCreatedAtIndexes:
    """Test descending created_at indexes"""
    
    def test_change_order_created_at_index_exists(self, db_session):
        """Verify idx_change_order_created_at index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'change_order'
                AND indexname = 'idx_change_order_created_at'
        """))
        assert result.scalar() == 'idx_change_order_created_at'
    
    def test_payment_created_at_index_exists(self, db_session):
        """Verify idx_payment_created_at index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'payment'
                AND indexname = 'idx_payment_created_at'
        """))
        assert result.scalar() == 'idx_payment_created_at'
    
    def test_qpl_action_created_at_index_exists(self, db_session):
        """Verify idx_qpl_action_created_at index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'quote_public_link_contact_action'
                AND indexname = 'idx_qpl_action_created_at'
        """))
        assert result.scalar() == 'idx_qpl_action_created_at'
    
    def test_quote_version_created_at_index_exists(self, db_session):
        """Verify idx_quote_version_created_at index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'quote_version'
                AND indexname = 'idx_quote_version_created_at'
        """))
        assert result.scalar() == 'idx_quote_version_created_at'


class TestCompositeIndexes:
    """Test composite indexes for query performance"""
    
    def test_connector_run_supplier_started_index_exists(self, db_session):
        """Verify idx_connector_run_supplier_started index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'connector_run_log'
                AND indexname = 'idx_connector_run_supplier_started'
        """))
        assert result.scalar() == 'idx_connector_run_supplier_started'
    
    def test_connector_run_supplier_status_index_exists(self, db_session):
        """Verify idx_connector_run_supplier_status index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'connector_run_log'
                AND indexname = 'idx_connector_run_supplier_status'
        """))
        assert result.scalar() == 'idx_connector_run_supplier_status'
    
    def test_invoice_line_source_index_exists(self, db_session):
        """Verify idx_invoice_line_source index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'invoice_line'
                AND indexname = 'idx_invoice_line_source'
        """))
        assert result.scalar() == 'idx_invoice_line_source'
    
    def test_job_assignment_user_active_index_exists(self, db_session):
        """Verify idx_job_assignment_user_active index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'job_assignment'
                AND indexname = 'idx_job_assignment_user_active'
        """))
        assert result.scalar() == 'idx_job_assignment_user_active'
    
    def test_quote_message_tenant_quote_time_index_exists(self, db_session):
        """Verify idx_quote_message_tenant_quote_time index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'quote_message'
                AND indexname = 'idx_quote_message_tenant_quote_time'
        """))
        assert result.scalar() == 'idx_quote_message_tenant_quote_time'
    
    def test_site_tenant_customer_index_exists(self, db_session):
        """Verify idx_site_tenant_customer index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'site'
                AND indexname = 'idx_site_tenant_customer'
        """))
        assert result.scalar() == 'idx_site_tenant_customer'
    
    def test_tenant_markup_category_index_exists(self, db_session):
        """Verify idx_tenant_markup_category index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'tenant_markup_version'
                AND indexname = 'idx_tenant_markup_category'
        """))
        assert result.scalar() == 'idx_tenant_markup_category'
    
    def test_tenant_user_notif_pref_index_exists(self, db_session):
        """Verify idx_tenant_user_notif_pref index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'tenant_user_notification_pref'
                AND indexname = 'idx_tenant_user_notif_pref'
        """))
        assert result.scalar() == 'idx_tenant_user_notif_pref'
    
    def test_user_sso_provider_id_index_exists(self, db_session):
        """Verify idx_user_sso_provider_id index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'user_sso_identity'
                AND indexname = 'idx_user_sso_provider_id'
        """))
        assert result.scalar() == 'idx_user_sso_provider_id'
    
    def test_usage_ledger_tenant_feature_index_exists(self, db_session):
        """Verify idx_usage_ledger_tenant_feature index exists"""
        result = db_session.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'usage_ledger'
                AND indexname = 'idx_usage_ledger_tenant_feature'
        """))
        assert result.scalar() == 'idx_usage_ledger_tenant_feature'


class TestIndexCount:
    """Test total index count for Task 3"""
    
    def test_all_task_3_indexes_created(self, db_session):
        """Verify all 14 Task 3 indexes exist"""
        result = db_session.execute(text("""
            SELECT COUNT(*) as total_indexes
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
        """))
        assert result.scalar() == 14
```

**Success Criteria for Step 6:**
- [ ] Test file created with 14+ tests
- [ ] All index existence tests pass
- [ ] Total index count test passes
- [ ] Full test suite passes: 703+/703+ unit tests, 730+/730+ total (100%)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 703+ passed (689 baseline + ~14 new tests)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 730+ passed (716 baseline + ~14 new tests)
```

### Step 2: Verify Database State

Run all verification queries from Step 4 to confirm database matches Golden Master.

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check migration was applied successfully
3. Verify index definitions in database
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md`

Add Task 3 implementation status:

```markdown
### Phase 6.0 Task 3: Composite Indexes - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_HOURS] hours (actual)
**Priority:** MEDIUM

**Implementation Summary:**

- Model Updates: Updated 7 model files with 14 new indexes
- Migration 3: [`YYYY_MM_DD_HHMM-[hash]_phase_6_0_task_3_composite_indexes.py`]
- Test Suite: [`test_phase_6_0_task_3_composite_indexes.py`] - 14+ tests ✅
- Final Results: 703/703 unit tests (100%), 730/730 total tests (100%)

**Key Changes:**
- ✅ 4 descending created_at indexes for time-sorted queries
- ✅ 10 composite indexes for common query patterns
- ✅ All indexes follow `idx_*` naming convention
- ✅ Zero regressions in existing test suite
- ✅ Migration rollback tested successfully

**Baseline:** 689 unit tests, 716 total tests → **New:** 703 unit tests (+14), 730 total tests (+14)

---

## Phase 6.0 Overall: Advanced Constraints & Performance Indexes - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Total Effort:** [TOTAL_HOURS] hours across 3 tasks
**Priority:** HIGH

**Complete Implementation Summary:**

- **Task 1:** 14 multi-tenant + 5 business logic unique constraints + 2 audit columns
- **Task 2:** 5 partial indexes + 1 GiST exclusion constraint + 1 redundant index removal
- **Task 3:** 4 descending created_at + 10 composite indexes

**Final Results:**
- 703/703 unit tests (100%), 730/730 total tests (100%)
- Database state fully aligns with Golden Master JSON v2.6h
- Zero regressions across all 3 migrations
- All performance optimizations implemented

**Database Changes Summary:**
- ✅ 19 unique constraints added (multi-tenant + business logic)
- ✅ 2 audit columns added (conversation_session)
- ✅ 5 partial indexes with WHERE clauses
- ✅ 1 GiST exclusion constraint (temporal overlap prevention)
- ✅ 14 composite/sorting indexes
- ✅ 1 redundant index removed
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For Task 3 Specifically:
- [ ] **Regression baseline captured** (689/689 unit, 716/716 total)
- [ ] **All 7 model files updated with indexes**
- [ ] **All imports include `from sqlalchemy import Index, text`**
- [ ] **Migration 3 created with correct revision chain**
- [ ] **All 14 indexes use correct `text()` wrapper for DESC**
- [ ] **Migration 3 applied successfully**
- [ ] **All database verification queries passed**
- [ ] **All 14 indexes exist with correct names**
- [ ] **Test file created with 14+ tests**
- [ ] **ALL 689 existing unit tests still passing**
- [ ] **ALL 716 total tests still passing**
- [ ] **New total: 703+/703+ unit, 730+/730+ total (100%)**
- [ ] **Migration rollback tested successfully**
- [ ] **Project plan document updated**

### For Phase 6.0 Overall:
- [ ] **All 3 migrations (Tasks 1, 2, 3) applied successfully**
- [ ] **Database schema matches Golden Master JSON for Phase 6.0 scope**
- [ ] **Zero test failures in regression suite**
- [ ] **Performance improvements verified**
- [ ] **Documentation updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-6.0-db-schema-sync-10-analysis.md` - **Gap Analysis** ⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models (7 files affected)
- `backend/app/models/job.py` - 2 indexes
- `backend/app/models/billing.py` - 2 indexes
- `backend/app/models/quoting.py` - 3 indexes
- `backend/app/models/supplier.py` - 2 indexes
- `backend/app/models/customer.py` - 1 index
- `backend/app/models/tenant.py` - 3 indexes
- `backend/app/models/subscription.py` - 1 index

---

## Risk Assessment

**For Task 3:**
- **Data Risk:** NONE (no constraints, purely additive indexes)
- **Migration Complexity:** LOW (standard index creation)
- **Application Impact:** POSITIVE (improved query performance)
- **Rollback Complexity:** LOW (simple DROP INDEX operations)
- **Performance Impact:** POSITIVE (14 optimized indexes)
- **Mitigation:** Standard testing, no special precautions needed

---

## Notes

### Important Patterns to Follow
- **DESC Ordering:** Always use `text('created_at DESC')` not string
- **Composite Indexes:** Order columns from most to least selective
- **Index Naming:** Follow `idx_{table}_{purpose}` convention
- **Zero Regression:** All 689 unit + 716 total tests MUST pass

### Task 3 Specific
- **Low Risk:** No data validation required (unlike Tasks 1 and 2)
- **Performance Focus:** All indexes designed for specific query patterns
- **Testing:** Verify index existence, optionally verify query plan usage
- **Rollback:** Simple DROP INDEX, no data cleanup needed

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 6.0 plan for detailed index specifications
- Verify `text()` wrapper used for all DESC columns
- Check that index names follow `idx_*` convention
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Task 3 Checklist:
1. ✅ Capture baseline (689/689 unit, 716/716 total)
2. 🔍 Update 7 model files with 14 indexes
3. ✅ Verify all imports include `from sqlalchemy import Index, text`
4. ✅ Verify Python syntax (`python -c "from app.models import *"`)
5. 🔧 **Generate Migration 3: Composite Indexes**
6. ✅ Apply Migration 3, verify all 14 indexes created
7. ✅ Verify all indexes use correct `text()` wrapper for DESC
8. 🧪 **Create comprehensive test suite (14+ tests)**
9. 🔄 Run regression tests (703+/703+ unit, 730+/730+ total expected)
10. ↩️ Test rollback of Migration 3
11. 📚 Update project plan with Task 3 completion
12. 🎉 **Celebrate Phase 6.0 completion!**

Remember: Task 3 brings performance optimization to critical query patterns. This is the final step in Phase 6.0, completing the comprehensive schema alignment with the Golden Master JSON. Test thoroughly and ensure zero regressions!
