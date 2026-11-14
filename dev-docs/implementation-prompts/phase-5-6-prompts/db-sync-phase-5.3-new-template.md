# Task [TASK_NUMBER]: [TASK_NAME]

**Reference:** `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md` - Task [TASK_NUMBER]
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` - **Notification, Idempotency & Index Analysis** ⭐
- Current Live Database (Phase 5.2 Post-State)
**Type:** Phase 5.3 - Notification Schema + Idempotency Constraints + Index Standardization + Triggers
**Priority:** CRITICAL
**Change Type:** SCHEMA SYNC + CONSTRAINT FIX + INDEX CREATION + TRIGGER RESTORATION + TESTING

---

## Context

This is **Phase 5.3 - DB Sync v#9**, a comprehensive synchronization addressing **4 major gap categories** in the physical database that don't match the Golden Master JSON.

**Root Cause:** 
- Notification schema evolved in JSON master but SQLModel not updated
- Idempotency keys exist as columns but lack database-level unique constraints
- Index naming inconsistencies (`ix_*` vs `idx_*`) and missing performance indexes
- Compliance triggers not attached to `discount_version` table

**Critical Impact:**
- **Audit Trail Gap:** Missing `created_by`, `provider_code`, `duration_ms` in notification delivery attempts
- **Financial Data Risk:** No database-level idempotency enforcement (allows duplicate invoices/quotes/payments via race conditions)
- **Performance Degradation:** Missing indexes cause O(n) queries for voice AI and job costing dashboards
- **Compliance Violation:** Missing audit/immutability triggers on temporal versioned data

**Scope:** **Single consolidated migration** - 1 column rename (data-preserving) + 3 new columns + 4 unique constraints + 7 index renames + 5 new indexes + 2 triggers across 9 tables.

**Key Principle:** ALL 4 phases MUST be bundled into a SINGLE Alembic migration to minimize database state fragmentation (per Phase 5.3 analysis requirement).

---

## What Was Completed in Previous Phases

**Phase 5.2 Status:** ✅ COMPLETE (April 11, 2026)
- ✅ 2 exclusion constraints fixed (COALESCE logic + tenant_id parameter)
- ✅ 3 performance indexes added (webhook worker queue + dashboard queries)
- ✅ 652/652 unit tests, 679/679 total tests passing (100%)
- ✅ Database schema aligned with Golden Master for exclusion constraints

**Current Baseline:** 652/652 unit tests, 679/679 total tests passing (100%)

**Previous Phases:**
- **Phase 4.5-4.9:** ✅ COMPLETE - Full schema synchronization
- **Phase 5.0:** ✅ COMPLETE - Server defaults enforcement
- **Phase 5.1:** ✅ COMPLETE - Missing unique constraints & foreign keys
- **Phase 5.2:** ✅ COMPLETE - Exclusion constraints & critical indexes

**See:**
- `dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md` for Phase 5.2 history
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` for comprehensive gap details

---

## Current Task: [TASK_NAME]

**Effort:** [EFFORT_ESTIMATE]
**Gap Reference:** Phase 5.3 Analysis - Notification/Idempotency/Index/Trigger Gaps
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

**Record the output of both results:** `652/652 & 679/679 tests passing` (Phase 5.3 baseline - starting from Phase 5.2 completion)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 5.3 Specific Warnings

**BEFORE writing ANY code, review these Phase 5.3 critical issues:**

### 1. Column Rename MUST Preserve Data - Use ALTER COLUMN

**Critical Rule:** When renaming `provider_response` → `details`, you MUST use `ALTER COLUMN ... RENAME` to preserve historical data.

**Why This Matters:**
```sql
-- ❌ WRONG - This will DELETE ALL provider_response data:
ALTER TABLE notification_delivery_attempt DROP COLUMN provider_response;
ALTER TABLE notification_delivery_attempt ADD COLUMN details JSONB;

-- ✅ CORRECT - This preserves all data:
ALTER TABLE notification_delivery_attempt 
RENAME COLUMN provider_response TO details;
```

**Impact:** The `provider_response` column contains historical notification provider payloads (Twilio responses, SendGrid responses, etc.). Losing this data would destroy the audit trail.

**Verification:** After migration, row count of `details` column should equal pre-migration row count of `provider_response`.

---

### 2. Single Migration Requirement - ALL 4 Phases in ONE File

**MANDATORY:** Per the Phase 5.3 analysis, all 4 phases MUST be bundled into a single Alembic migration file.

**Why:** Minimizes database state fragmentation and ensures atomic application of all changes.

**Migration Structure:**
```python
def upgrade():
    # ========== PHASE 1: notification_delivery_attempt ==========
    # Column rename, new columns, server default, indexes
    
    # ========== PHASE 2: Idempotency Unique Constraints ==========
    # invoice, quote, payment constraints
    
    # ========== PHASE 3: Index Naming Standardization ==========
    # conversation_session, job_time_entry, voice_command_log
    
    # ========== PHASE 4: discount_version Triggers ==========
    # Audit and immutability triggers
```

**Impact:** If migration is split into multiple files, rollback becomes complex and database state may be inconsistent between phases.

---

### 3. Idempotency Constraint Pre-Migration Validation is MANDATORY

**CRITICAL:** Before creating unique constraints on `(tenant_id, idempotency_key)`, you MUST verify no duplicate idempotency keys exist.

**Validation Queries (MANDATORY):**
```sql
-- Check invoice duplicates
SELECT tenant_id, idempotency_key, COUNT(*) as count
FROM invoice
WHERE idempotency_key IS NOT NULL
GROUP BY tenant_id, idempotency_key
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Check quote duplicates
SELECT tenant_id, idempotency_key, COUNT(*) as count
FROM quote
WHERE idempotency_key IS NOT NULL
GROUP BY tenant_id, idempotency_key
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Check payment duplicates
SELECT tenant_id, idempotency_key, COUNT(*) as count
FROM payment
WHERE idempotency_key IS NOT NULL
GROUP BY tenant_id, idempotency_key
HAVING COUNT(*) > 1;
-- Expected: 0 rows
```

**If ANY query returns rows > 0:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results showing duplicate idempotency keys
- **Report** - Ask for guidance on data cleanup strategy
- **Options:** Delete duplicates, nullify idempotency_key on newer records, or generate new unique keys
- **Re-validate** - Run all queries again to confirm 0 violations

---

### 4. Trigger Function Dependencies Must Exist

**CRITICAL:** Before creating triggers on `discount_version`, verify the trigger functions exist.

**Verification Queries:**
```sql
-- Check audit.log_changes() function exists
SELECT proname, pronargs
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'audit' AND p.proname = 'log_changes';
-- Expected: 1 row

-- Check guard_created_fields_immutable() function exists
SELECT proname, pronargs
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public' AND p.proname = 'guard_created_fields_immutable';
-- Expected: 1 row
```

**If functions are missing:** This indicates a deeper schema issue. Escalate immediately - do not proceed with trigger creation.

---

### 5. Index Naming Convention: idx_* (Not ix_*)

**Critical Rule:** Phase 5.3 standardizes on `idx_<abbreviated_table>_<purpose>` naming convention.

**Examples:**
```sql
-- ❌ WRONG (old convention):
ix_job_time_entry_job_id
ix_job_time_entry_user_id
ix_voice_command_log_total_latency_ms

-- ✅ CORRECT (new convention):
idx_jte_job
idx_jte_user
idx_voice_log_latency
```

**Why This Matters:**
- **Consistency:** All other indexes in the schema use `idx_*` prefix
- **Readability:** Abbreviated table names make index names shorter and clearer
- **Maintainability:** Consistent naming simplifies troubleshooting and documentation

**Implementation:** Drop old `ix_*` indexes and create new `idx_*` indexes in the same migration.

---

### 6. Server Default vs Column Default

**Critical Difference:** `server_default` runs at DATABASE level, `default` runs at APPLICATION level.

**Phase 5.3 Fix:**
```python
# ❌ WRONG - Application-level default (not enforced by DB):
created_at: datetime = Field(default_factory=datetime.utcnow)

# ✅ CORRECT - Database-level default (enforced at DB layer):
created_at: datetime = Field(
    sa_column=Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
)
```

**Why:** `server_default` ensures the database ALWAYS sets `created_at` even if the application forgets to provide it. Critical for audit compliance.

---

### 7. Foreign Key for created_by Column

**Critical Detail:** The new `created_by` column in `notification_delivery_attempt` MUST have a foreign key to `user.id`.

**SQLModel Definition:**
```python
created_by: Optional[uuid.UUID] = Field(
    default=None,
    foreign_key="user.id",  # MANDATORY
    description="User who initiated this delivery attempt"
)
```

**Migration:**
```python
# Add foreign key constraint
op.create_foreign_key(
    'notification_delivery_attempt_created_by_fkey',
    'notification_delivery_attempt',
    'user',
    ['created_by'],
    ['id']
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

### 3. Test Unique Constraints with pytest.raises(IntegrityError)

**Pattern for Testing Idempotency Key Uniqueness:**
```python
import pytest
from sqlalchemy.exc import IntegrityError

def test_invoice_idempotency_key_prevents_duplicates(db_session, test_tenant):
    # Insert first invoice
    invoice1 = Invoice(
        tenant_id=test_tenant.id,
        invoice_number="INV-001",
        idempotency_key="unique-key-123",
        # ... other required fields
    )
    db_session.add(invoice1)
    db_session.commit()
    
    # Attempt duplicate idempotency key (should fail)
    invoice2 = Invoice(
        tenant_id=test_tenant.id,
        invoice_number="INV-002",
        idempotency_key="unique-key-123",  # DUPLICATE
        # ... other required fields
    )
    db_session.add(invoice2)
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "uq_invoice_tenant_idempotency" in str(exc_info.value)
    db_session.rollback()
```

---

### 4. Verify Trigger Functionality with UPDATE Attempts

**Pattern for Testing Immutability Triggers:**
```python
def test_discount_version_created_at_immutable(db_session, discount_version_record):
    """Verify immutability guard trigger prevents created_at modification"""
    
    original_created_at = discount_version_record.created_at
    
    # Attempt to modify created_at (should fail)
    discount_version_record.created_at = datetime.utcnow()
    
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "immutable" in str(exc_info.value).lower()
    db_session.rollback()
```

---

## Requirements

### Single Migration File Structure

**CRITICAL:** All tasks must contribute to a SINGLE Alembic migration file with this structure:

```python
"""Phase 5.3: Comprehensive schema sync (notification + idempotency + indexes + triggers)

Revision ID: XXX_phase_5_3_comprehensive_sync
Revises: [PREVIOUS_REVISION]
Create Date: 2026-04-11

CRITICAL: This migration bundles 4 phases into a single transaction to minimize
database state fragmentation per Phase 5.3 analysis requirements.
"""

def upgrade():
    # ========== PHASE 1: notification_delivery_attempt ==========
    # 1.1: Rename provider_response → details (data preservation)
    op.alter_column('notification_delivery_attempt', 'provider_response', new_column_name='details')
    
    # 1.2: Add new columns
    op.add_column('notification_delivery_attempt', sa.Column('provider_code', sa.String(), nullable=True))
    op.add_column('notification_delivery_attempt', sa.Column('duration_ms', sa.Integer(), nullable=True))
    op.add_column('notification_delivery_attempt', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    
    # 1.3: Add foreign key for created_by
    op.create_foreign_key(
        'notification_delivery_attempt_created_by_fkey',
        'notification_delivery_attempt', 'user', ['created_by'], ['id']
    )
    
    # 1.4: Fix created_at server default
    op.alter_column('notification_delivery_attempt', 'created_at', server_default=sa.text('now()'))
    
    # 1.5: Drop old inefficient indexes
    op.drop_index('ix_notification_delivery_attempt_notification_outbox_id')
    op.drop_index('ix_notification_delivery_attempt_tenant_id')
    
    # 1.6: Create new composite index
    op.create_index(
        'idx_notif_attempt_outbox_time',
        'notification_delivery_attempt',
        ['notification_outbox_id', sa.text('attempted_at DESC')]
    )
    
    # ========== PHASE 2: Idempotency Unique Constraints ==========
    # 2.1: Invoice constraints
    op.create_unique_constraint('uq_invoice_tenant_number', 'invoice', ['tenant_id', 'invoice_number'])
    op.create_unique_constraint('uq_invoice_tenant_idempotency', 'invoice', ['tenant_id', 'idempotency_key'])
    
    # 2.2: Quote constraint
    op.create_unique_constraint('uq_quote_tenant_idempotency', 'quote', ['tenant_id', 'idempotency_key'])
    
    # 2.3: Payment constraint
    op.create_unique_constraint('uq_payment_tenant_idempotency', 'payment', ['tenant_id', 'idempotency_key'])
    
    # ========== PHASE 3: Index Naming Standardization ==========
    # 3.1: conversation_session - Add missing composite index
    op.create_index(
        'idx_conv_session_tenant_user',
        'conversation_session',
        ['tenant_id', 'user_id', sa.text('updated_at DESC')]
    )
    
    # 3.2: job_time_entry - Drop old indexes, create new with correct names
    op.drop_index('ix_job_time_entry_job_id')
    op.drop_index('ix_job_time_entry_user_id')
    op.create_index('idx_jte_job', 'job_time_entry', ['job_id'])
    op.create_index('idx_jte_user', 'job_time_entry', ['user_id'])
    op.create_index('idx_jte_started_at', 'job_time_entry', [sa.text('started_at DESC')])
    
    # 3.3: voice_command_log - Drop old index, create new with correct names
    op.drop_index('ix_voice_command_log_total_latency_ms')
    op.create_index('idx_voice_log_tenant_time', 'voice_command_log', ['tenant_id', sa.text('created_at DESC')])
    op.create_index('idx_voice_log_intent', 'voice_command_log', ['intent_detected'])
    op.create_index('idx_voice_log_latency', 'voice_command_log', ['total_latency_ms'])
    
    # ========== PHASE 4: discount_version Triggers ==========
    # 4.1: Attach audit trigger
    op.execute("""
        CREATE TRIGGER audit_discount_version_changes
        AFTER INSERT OR UPDATE OR DELETE ON public.discount_version
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    
    # 4.2: Attach immutability guard trigger
    op.execute("""
        CREATE TRIGGER trg_discount_version_guard_created_immutable
        BEFORE UPDATE ON public.discount_version
        FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
    """)


def downgrade():
    # Reverse all operations in reverse order
    # (See Phase 5.3 plan for complete downgrade operations)
```

---

### Task 1: SQLModel Schema Definitions Verification

**Effort:** 0.5 days
**Scope:** Verify schema changes across 9 tables in Python models

#### What This Task Accomplishes

Confirm that all Phase 5.3 changes are correctly defined in the Python SQLModel definitions. Update models with column renames, new columns, unique constraints, indexes, and verify trigger function existence.

#### Tables to Check

**Model Files & Required Changes:**

1. **`backend/app/models/notification.py`** - `NotificationDeliveryAttempt`
   - **Rename:** `provider_response` → `details`
   - **Add:** `provider_code`, `duration_ms`, `created_by` columns
   - **Fix:** `created_at` server default
   - **Update:** `__table_args__` with composite index `idx_notif_attempt_outbox_time`

2. **`backend/app/models/billing.py`** - `Invoice`
   - **Add:** Unique constraints `uq_invoice_tenant_number` and `uq_invoice_tenant_idempotency`
   - **Update:** Standardize index names to `idx_invoice_*`

3. **`backend/app/models/quoting.py`** - `Quote`
   - **Add:** Unique constraint `uq_quote_tenant_idempotency`
   - **Update:** Standardize index names to `idx_quote_*`

4. **`backend/app/models/billing.py`** - `Payment`
   - **Add:** Unique constraint `uq_payment_tenant_idempotency`
   - **Update:** Standardize index names to `idx_payment_*`

5. **`backend/app/models/voice.py`** - `ConversationSession`
   - **Add:** Composite index `idx_conv_session_tenant_user`
   - **Rename:** pgvector index to `idx_conv_session_embedding`

6. **`backend/app/models/job.py`** - `JobTimeEntry`
   - **Rename:** Indexes to `idx_jte_*` convention
   - **Add:** Missing index `idx_jte_started_at`

7. **`backend/app/models/voice.py`** - `VoiceCommandLog`
   - **Rename:** Indexes to `idx_voice_log_*` convention
   - **Add:** Missing indexes `idx_voice_log_tenant_time` and `idx_voice_log_intent`

8. **`backend/app/models/quoting.py`** - `DiscountVersion`
   - **Verify:** Table exists (triggers will be added in migration, not in model)

#### SQLModel Syntax Examples

**Column Rename + New Columns + Server Default:**
```python
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlmodel import Field

class NotificationDeliveryAttempt(SQLModel, table=True):
    __tablename__ = "notification_delivery_attempt"
    
    # RENAMED: provider_response → details
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Provider-specific response payload"
    )
    
    # NEW COLUMNS
    provider_code: Optional[str] = Field(
        default=None,
        description="Provider-specific message/transaction ID"
    )
    duration_ms: Optional[int] = Field(
        default=None,
        description="Time taken for delivery attempt in milliseconds"
    )
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user.id",
        description="User who initiated this delivery attempt"
    )
    
    # FIXED: server_default
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )
    )
    
    __table_args__ = (
        # Check constraint (existing)
        CheckConstraint(
            "status IN ('queued','delivered','bounced','rejected','throttled','error')",
            name="notification_delivery_attempt_status_chk"
        ),
        # NEW: Composite index
        Index("idx_notif_attempt_outbox_time", "notification_outbox_id", text("attempted_at DESC")),
    )
```

**Unique Constraints for Idempotency:**
```python
from sqlalchemy import UniqueConstraint

class Invoice(SQLModel, table=True):
    __tablename__ = "invoice"
    
    # ... existing fields ...
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_tenant_number"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_invoice_tenant_idempotency"),
        Index("idx_invoice_customer", "customer_id"),
        Index("idx_invoice_status_due_at", "status_id", "due_at"),
        Index("idx_invoice_created_at", text("created_at DESC")),
        Index("idx_invoice_balance", "balance_due_cents", postgresql_where=text("balance_due_cents > 0")),
    )
```

**Index Naming Standardization:**
```python
class JobTimeEntry(SQLModel, table=True):
    __tablename__ = "job_time_entry"
    
    # ... existing fields ...
    
    __table_args__ = (
        Index("idx_jte_job", "job_id"),
        Index("idx_jte_user", "user_id"),
        Index("idx_jte_started_at", text("started_at DESC")),
    )
```

**Success Criteria for Task 1:**
- [ ] notification_delivery_attempt model updated with rename + 3 new columns + server default + index
- [ ] Invoice, Quote, Payment models have idempotency unique constraints
- [ ] conversation_session, job_time_entry, voice_command_log models have standardized index names
- [ ] All models have correct `idx_*` naming convention
- [ ] Code passes Python syntax validation
- [ ] All models import successfully (`python -c "from app.models import *"`)

---

### Task 2: Pre-Migration Data Validation

**Effort:** 0.25 days
**Dependencies:** None (can run independently)
**CRITICAL:** Validation MUST pass before generating migration

#### What This Task Accomplishes

Verify that the database is ready for Phase 5.3 migration by checking for data violations that would prevent constraint creation or trigger attachment.

#### Validation Queries (Run via postgres-local MCP Server)

**Validation 1: Idempotency Key Duplicates (MANDATORY)**

```sql
-- Check invoice duplicates
SELECT tenant_id, idempotency_key, array_agg(id) as invoice_ids, COUNT(*) as count
FROM invoice
WHERE idempotency_key IS NOT NULL
GROUP BY tenant_id, idempotency_key
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Check quote duplicates
SELECT tenant_id, idempotency_key, array_agg(id) as quote_ids, COUNT(*) as count
FROM quote
WHERE idempotency_key IS NOT NULL
GROUP BY tenant_id, idempotency_key
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Check payment duplicates
SELECT tenant_id, idempotency_key, array_agg(id) as payment_ids, COUNT(*) as count
FROM payment
WHERE idempotency_key IS NOT NULL
GROUP BY tenant_id, idempotency_key
HAVING COUNT(*) > 1;
-- Expected: 0 rows
```

**Validation 2: Trigger Function Existence (MANDATORY)**

```sql
-- Check audit.log_changes() function exists
SELECT n.nspname || '.' || p.proname as function_name, 'EXISTS' as status
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'audit' AND p.proname = 'log_changes';
-- Expected: 1 row

-- Check guard_created_fields_immutable() function exists
SELECT n.nspname || '.' || p.proname as function_name, 'EXISTS' as status
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public' AND p.proname = 'guard_created_fields_immutable';
-- Expected: 1 row
```

**Validation 3: notification_delivery_attempt Row Count (For Data Preservation Verification)**

```sql
-- Count existing records and provider_response values
SELECT 
    COUNT(*) as total_records,
    COUNT(provider_response) as records_with_provider_response
FROM notification_delivery_attempt;
-- Store these numbers for post-migration verification
```

**If ANY validation query fails:**
- **STOP** - Do not proceed with migration
- **Document** - Save query results
- **Report** - Ask for guidance on data cleanup strategy
- **Clean** - Create remediation script
- **Re-validate** - Run all queries again

**Success Criteria for Task 2:**
- [ ] All 3 idempotency duplicate queries return 0 rows
- [ ] Both trigger function queries return 1 row each
- [ ] Row count stored for data preservation verification
- [ ] Validation results documented

---

### Task 3: Single Alembic Migration Generation & Execution

**Effort:** 1.5 days
**Dependencies:** Tasks 1 & 2 must be complete
**CRITICAL:** All 4 phases in ONE migration file

#### What This Task Accomplishes

Generate comprehensive Alembic migration with all 4 phases bundled together, apply migration, and verify database state matches Golden Master.

#### Step-by-Step Implementation

**Step 1: Generate Migration Skeleton**

```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_5_3_comprehensive_schema_sync"
```

**Step 2: Manually Construct Complete Migration**

The migration file MUST include all 4 phases. Use the template from the Requirements section above as the structure.

**Key Manual Edits Required:**
1. Column rename uses `op.alter_column()` with `new_column_name` parameter
2. Server default uses `op.alter_column()` with `server_default` parameter
3. Unique constraints use `op.create_unique_constraint()`
4. Index renames use `op.drop_index()` + `op.create_index()` pairs
5. Triggers use `op.execute()` with raw SQL

**Step 3: Apply Migration**

```bash
# Apply migration
alembic upgrade head

# Capture output for verification
```

**Step 4: Verify Database State (via postgres-local MCP Server)**

```sql
-- Verification 1: notification_delivery_attempt columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'notification_delivery_attempt'
  AND column_name IN ('details', 'provider_code', 'duration_ms', 'created_by', 'created_at')
ORDER BY column_name;
-- Expected: 5 rows with correct types and defaults

-- Verification 2: Data preservation (compare with pre-migration count)
SELECT COUNT(*) as total_records, COUNT(details) as records_with_details
FROM notification_delivery_attempt;
-- Expected: Same row counts as pre-migration provider_response

-- Verification 3: Unique constraints exist
SELECT conname, pg_get_constraintdef(c.oid) as definition
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname IN ('invoice', 'quote', 'payment') AND c.contype = 'u'
  AND conname LIKE 'uq_%_idempotency'
ORDER BY conname;
-- Expected: 4 rows (invoice has 2, quote has 1, payment has 1)

-- Verification 4: Indexes renamed/created
SELECT tablename, indexname
FROM pg_indexes
WHERE tablename IN ('conversation_session', 'job_time_entry', 'voice_command_log', 'notification_delivery_attempt')
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
-- Expected: All new idx_* indexes exist, no old ix_* indexes

-- Verification 5: Triggers attached
SELECT trigger_name, event_manipulation
FROM information_schema.triggers
WHERE event_object_table = 'discount_version'
ORDER BY trigger_name;
-- Expected: 2 rows (audit and immutability triggers)
```

**Step 5: Test Migration Rollback**

```bash
# Test backward migration
alembic downgrade -1

# Verify constraints/indexes/triggers removed (via MCP queries)

# Re-apply for continued work
alembic upgrade head
```

**Success Criteria for Task 3:**
- [ ] Single migration file created with all 4 phases
- [ ] Migration applies successfully forward
- [ ] All 5 verification queries pass
- [ ] Data preservation confirmed (row counts match)
- [ ] Migration rolls back successfully
- [ ] Migration re-applies successfully

---

### Task 4: Comprehensive Testing - Constraints, Indexes, Triggers

**Effort:** 1 day
**Dependencies:** Task 3 must be complete

#### What This Task Accomplishes

Validate that:
1. Unique constraints prevent duplicate idempotency keys
2. Index renames don't break query performance
3. Triggers enforce audit logging and immutability
4. New columns are accessible and functional

#### Test File Structure

**File:** `backend/tests/test_phase_5_3_comprehensive_sync.py`

**Test Categories:**

```python
"""
Test Suite: Phase 5.3 - Comprehensive Schema Sync Verification
Validates notification schema, idempotency constraints, index standardization, and triggers

Reference: phase-5.3-db-schema-sync-9-plan.md
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime


class TestPhase1NotificationSchema:
    """Verify notification_delivery_attempt schema changes"""
    
    def test_details_column_exists_and_accessible(self, db_session):
        """Verify provider_response renamed to details"""
        # Insert record with details column
        db_session.execute(text("""
            INSERT INTO notification_delivery_attempt 
            (notification_outbox_id, tenant_id, attempt_no, status, provider, details)
            VALUES (:outbox_id, :tenant_id, 1, 'delivered', 'twilio', 
                    '{"message_sid": "SM12345"}'::jsonb)
        """), {
            "outbox_id": uuid.uuid4(),
            "tenant_id": uuid.uuid4()
        })
        db_session.commit()
        
        # Verify details accessible
        result = db_session.execute(text("""
            SELECT details->>'message_sid' as sid
            FROM notification_delivery_attempt
            WHERE provider = 'twilio'
            LIMIT 1
        """))
        row = result.first()
        assert row[0] == "SM12345"
    
    def test_new_columns_accessible(self, db_session):
        """Verify provider_code, duration_ms, created_by columns work"""
        user_id = uuid.uuid4()
        
        db_session.execute(text("""
            INSERT INTO notification_delivery_attempt 
            (notification_outbox_id, tenant_id, attempt_no, status, provider,
             provider_code, duration_ms, created_by)
            VALUES (:outbox_id, :tenant_id, 1, 'delivered', 'sendgrid',
                    'SG-MSG-123', 250, :user_id)
        """), {
            "outbox_id": uuid.uuid4(),
            "tenant_id": uuid.uuid4(),
            "user_id": user_id
        })
        db_session.commit()


class TestPhase2IdempotencyConstraints:
    """Verify idempotency unique constraints prevent duplicates"""
    
    def test_invoice_idempotency_key_prevents_duplicates(self, db_session, test_tenant):
        """Verify uq_invoice_tenant_idempotency constraint"""
        # Insert first invoice
        db_session.execute(text("""
            INSERT INTO invoice (id, tenant_id, invoice_number, idempotency_key, 
                                 customer_id, status_id, total_cents)
            VALUES (:id, :tenant_id, 'INV-001', 'key-123', :customer_id, 1, 10000)
        """), {
            "id": uuid.uuid4(),
            "tenant_id": test_tenant.id,
            "customer_id": uuid.uuid4()
        })
        db_session.commit()
        
        # Attempt duplicate idempotency key (should fail)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(text("""
                INSERT INTO invoice (id, tenant_id, invoice_number, idempotency_key,
                                     customer_id, status_id, total_cents)
                VALUES (:id, :tenant_id, 'INV-002', 'key-123', :customer_id, 1, 20000)
            """), {
                "id": uuid.uuid4(),
                "tenant_id": test_tenant.id,
                "customer_id": uuid.uuid4()
            })
            db_session.commit()
        
        assert "uq_invoice_tenant_idempotency" in str(exc_info.value)
        db_session.rollback()
    
    def test_quote_idempotency_key_prevents_duplicates(self, db_session, test_tenant):
        """Verify uq_quote_tenant_idempotency constraint"""
        # Similar to invoice test...
    
    def test_payment_idempotency_key_prevents_duplicates(self, db_session, test_tenant):
        """Verify uq_payment_tenant_idempotency constraint"""
        # Similar to invoice test...


class TestPhase3IndexStandardization:
    """Verify index renames and new indexes improve performance"""
    
    def test_conversation_session_composite_index_used(self, db_session, test_tenant):
        """Verify idx_conv_session_tenant_user index"""
        result = db_session.execute(text("""
            EXPLAIN (FORMAT JSON)
            SELECT * FROM conversation_session
            WHERE tenant_id = :tenant_id AND user_id = :user_id
            ORDER BY updated_at DESC
            LIMIT 10
        """), {"tenant_id": test_tenant.id, "user_id": uuid.uuid4()})
        
        explain_output = result.scalar()
        assert "idx_conv_session_tenant_user" in str(explain_output)
    
    def test_job_time_entry_indexes_standardized(self, db_session):
        """Verify idx_jte_* indexes exist and work"""
        # Verify old ix_* indexes removed
        result = db_session.execute(text("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE tablename = 'job_time_entry' AND indexname LIKE 'ix_job_time_entry_%'
        """))
        assert result.scalar() == 0
        
        # Verify new idx_jte_* indexes exist
        result = db_session.execute(text("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE tablename = 'job_time_entry' AND indexname LIKE 'idx_jte_%'
        """))
        assert result.scalar() == 3  # job, user, started_at


class TestPhase4DiscountVersionTriggers:
    """Verify audit and immutability triggers on discount_version"""
    
    def test_discount_version_created_at_immutable(self, db_session, discount_version_record):
        """Verify immutability guard trigger prevents created_at modification"""
        original_created_at = discount_version_record.created_at
        
        # Attempt to modify created_at (should fail)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(text("""
                UPDATE discount_version
                SET created_at = NOW()
                WHERE id = :id
            """), {"id": discount_version_record.id})
            db_session.commit()
        
        assert "immutable" in str(exc_info.value).lower()
        db_session.rollback()
    
    def test_discount_version_audit_logging(self, db_session, discount_version_record):
        """Verify audit trigger logs changes to audit.logged_actions"""
        # Update discount_version
        db_session.execute(text("""
            UPDATE discount_version
            SET notes = 'Updated notes'
            WHERE id = :id
        """), {"id": discount_version_record.id})
        db_session.commit()
        
        # Verify audit log entry created
        result = db_session.execute(text("""
            SELECT COUNT(*) FROM audit.logged_actions
            WHERE table_name = 'discount_version' AND row_id = :id::text
        """), {"id": discount_version_record.id})
        
        assert result.scalar() > 0
```

**Success Criteria for Task 4:**
- [ ] Test file created with all 4 phase categories
- [ ] Idempotency constraint tests prevent duplicates
- [ ] Index standardization tests confirm naming and usage
- [ ] Trigger tests verify immutability and audit logging
- [ ] Full test suite passes: 660+/660+ unit tests, 687+/687+ total (100%)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 660+ passed (652 baseline + ~8 new tests)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 687+ passed (679 baseline + ~8 new tests)
```

### Step 2: Verify Database State

Run all verification queries from Task 3, Step 4 to confirm database matches Golden Master.

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check migration was applied successfully
3. Verify constraint/index/trigger definitions in database
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md`

Add implementation status at the end of the plan document:

```markdown
## Implementation Status Tracking

### Phase 5.3: Comprehensive Schema Sync - ✅ COMPLETE

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_DAYS] days (actual)
**Priority:** CRITICAL

**Implementation Summary:**

- Model Verification: Updated 9 tables across 5 model files
- Data Validation: All pre-migration validation queries passed (0 duplicates, trigger functions exist)
- Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_5_3_comprehensive_schema_sync.py`]
- Test Suite: [`test_phase_5_3_comprehensive_sync.py`] - 8+ tests ✅
- Final Results: 660/660 unit tests (100%), 687/687 total tests (100%)

**Key Changes:**
- ✅ notification_delivery_attempt: Column renamed (provider_response→details), 3 columns added, server default fixed, index optimized
- ✅ Invoice, Quote, Payment: Idempotency unique constraints added
- ✅ conversation_session, job_time_entry, voice_command_log: Indexes renamed/added
- ✅ discount_version: Audit and immutability triggers attached
- ✅ Database state fully aligns with Golden Master JSON
- ✅ Zero regressions in existing test suite
- ✅ Single cohesive migration applied successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For ALL Phase 5.3 Tasks:
- [ ] **Regression baseline captured** (652/652 unit, 679/679 total)
- [ ] **All 3 idempotency duplicate queries returned 0 rows**
- [ ] **Both trigger function verification queries returned 1 row each**
- [ ] **notification_delivery_attempt row count stored for verification**
- [ ] **All 9 tables verified in Python models**
- [ ] **Single Alembic migration file created with all 4 phases**
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 5 database verification queries passed**
- [ ] **Data preservation confirmed** (row counts match pre-migration)
- [ ] **Comprehensive tests written and passing**
- [ ] **ALL 652 existing unit tests still passing**
- [ ] **ALL 679 total tests still passing**
- [ ] **New total: 660+/660+ unit, 687+/687+ total (100%)**
- [ ] **Migration rollback tested** (`alembic downgrade -1`)
- [ ] **Project plan document updated**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` - **Comprehensive Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models (9 tables affected)
- `backend/app/models/notification.py` - notification_delivery_attempt
- `backend/app/models/billing.py` - Invoice, Payment
- `backend/app/models/quoting.py` - Quote, DiscountVersion
- `backend/app/models/voice.py` - ConversationSession, VoiceCommandLog
- `backend/app/models/job.py` - JobTimeEntry

---

## Risk Assessment

**For Phase 5.3:**
- **Data Loss Risk:** MEDIUM (column rename must preserve data - CRITICAL to use ALTER COLUMN RENAME)
- **Duplicate Data Risk:** LOW (idempotency duplicates unlikely in test environment)
- **Trigger Function Risk:** LOW (functions should exist from previous schema setup)
- **Migration Complexity:** HIGH (4 phases in single migration - requires careful testing)
- **Application Impact:** LOW (additive changes, improves data integrity without breaking changes)
- **Rollback Complexity:** MEDIUM (single migration with multiple operations)
- **Performance Impact:** POSITIVE (indexes improve query performance, constraints prevent duplicates)
- **Mitigation:** Comprehensive pre-migration validation, data preservation verification, extensive testing

---

## Notes

### Important Patterns to Follow
- **Data Preservation:** ALWAYS use `ALTER COLUMN RENAME` for column renames, never DROP + ADD
- **Single Migration:** ALL 4 phases in ONE file - do not split across multiple migrations
- **Zero Duplicates:** Pre-migration validation MUST show 0 duplicate idempotency keys
- **Trigger Functions:** Verify functions exist before creating triggers
- **Index Naming:** Use `idx_<abbreviated_table>_<purpose>` convention consistently
- **Server Defaults:** Use `server_default` not `default` for database-level enforcement
- **Zero Regression:** All 652 unit + 679 total tests MUST pass

### Phase 5.3 Specific
- **Column rename:** provider_response → details (preserve all data)
- **New columns:** provider_code, duration_ms, created_by
- **Idempotency:** Database-level enforcement via unique constraints
- **Index convention:** idx_* prefix with abbreviated table names
- **Triggers:** Audit logging + immutability guards on discount_version

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 5.3 plan for detailed specifications
- Verify all pre-migration validation queries passed
- Check migration file has all 4 phases
- Verify data preservation (row counts match)
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Phase 5.3 Task Checklist:
1. ✅ Capture baseline (652/652 unit, 679/679 total)
2. 🔍 **Verify all 9 table definitions in Python models**
3. ✅ Verify Python syntax (`python -c "from app.models import *"`)
4. ⚠️ **CRITICAL: Run all 3 idempotency duplicate queries via MCP server**
5. ⚠️ **CRITICAL: Verify both trigger functions exist**
6. ⚠️ **CRITICAL: Store notification_delivery_attempt row count**
7. ⚠️ **MANDATORY: Stop if ANY validation fails**
8. 🔧 **Create single Alembic migration with all 4 phases**
9. 🔍 **Verify migration has all operations (column rename + constraints + indexes + triggers)**
10. ✅ Apply migration (`alembic upgrade head`)
11. ✅ **Verify data preservation (row counts match)**
12. ✅ **Run all 5 database verification queries**
13. 🧪 **Create comprehensive test suite (all 4 phases)**
14. 🔄 Run regression tests (660+/660+ unit, 687+/687+ total expected)
15. ↩️ Test rollback
16. 📚 Update project plan

Remember: Phase 5.3 is the MOST COMPLEX sync to date - it bundles notification schema changes, financial data integrity constraints, performance optimizations, and compliance triggers into ONE atomic migration. Validate everything before applying, verify data preservation, and test thoroughly!
