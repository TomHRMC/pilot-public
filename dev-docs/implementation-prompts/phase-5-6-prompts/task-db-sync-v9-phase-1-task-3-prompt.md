# Task 3: Single Alembic Migration Generation & Execution

**Reference:** `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md` - Task 3
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` - **Notification, Idempotency & Index Analysis** ⭐
- Current Live Database (Phase 5.2 Post-State)
**Type:** Phase 5.3 - Migration Generation & Execution
**Priority:** CRITICAL
**Change Type:** MIGRATION + DATA VALIDATION

---

## Context

This is **Phase 5.3 - DB Sync v#9 - Task 3**, the migration creation and execution task for a comprehensive synchronization addressing **4 major gap categories** in the physical database that don't match the Golden Master JSON.

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

**Scope for Task 3:** Create **single consolidated migration** with all 4 phases bundled - 1 column rename (data-preserving) + 3 new columns + 4 unique constraints + 7 index renames + 5 new indexes + 2 triggers across 9 tables.

**Key Principle:** ALL 4 phases MUST be bundled into a SINGLE Alembic migration to minimize database state fragmentation (per Phase 5.3 analysis requirement).

---

## What Was Completed in Previous Tasks

**Task 1 Status:** ✅ COMPLETE
- ✅ SQLModel definitions updated for 9 tables across 5 model files
- ✅ Column rename, new columns, unique constraints, index definitions added to models
- ✅ All models import successfully
- ✅ 652/652 unit tests, 679/679 total tests passing (100%)

**Task 2 Status:** ✅ COMPLETE
- ✅ All 3 idempotency duplicate queries returned 0 rows
- ✅ Both trigger functions verified to exist (`audit.log_changes`, `guard_created_fields_immutable`)
- ✅ `notification_delivery_attempt` row count stored for data preservation verification
- ✅ Validation report created - ALL CHECKS PASSED
- ✅ APPROVED to proceed with migration

**Current Baseline:** 652/652 unit tests, 679/679 total tests passing (100%)

**See:**
- `task-db-sync-v9-phase-1-task-1-prompt.md` for Task 1 details
- `task-db-sync-v9-phase-1-task-2-prompt.md` for Task 2 details
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` for comprehensive gap details

---

## Current Task: Single Alembic Migration Generation & Execution

**Effort:** 1.5 days
**Gap Reference:** Phase 5.3 Analysis - Notification/Idempotency/Index/Trigger Gaps
**Change Type:** MIGRATION + DATA VALIDATION
**Dependencies:** Tasks 1 & 2 must be complete (✅ COMPLETE)
**CRITICAL:** All 4 phases in ONE migration file

This task generates a comprehensive Alembic migration with all 4 phases bundled together, applies the migration, and verifies the database state matches the Golden Master JSON schema.

### What Needs to Be Implemented

**Migration Phases (Single File):**

| Phase | Changes | Critical Notes |
|-------|---------|---------------|
| **Phase 1: notification_delivery_attempt** | 1. Rename column: `provider_response` → `details`<br>2. Add columns: `provider_code`, `duration_ms`, `created_by`<br>3. Fix `created_at` server default<br>4. Add foreign key: `created_by` → `user.id`<br>5. Drop old indexes<br>6. Create composite index: `idx_notif_attempt_outbox_time` | **CRITICAL:** Use `ALTER COLUMN RENAME` to preserve data |
| **Phase 2: Idempotency Constraints** | 1. `invoice`: Add `uq_invoice_tenant_number`, `uq_invoice_tenant_idempotency`<br>2. `quote`: Add `uq_quote_tenant_idempotency`<br>3. `payment`: Add `uq_payment_tenant_idempotency` | **VALIDATED:** No duplicates exist (Task 2) |
| **Phase 3: Index Standardization** | 1. `conversation_session`: Add `idx_conv_session_tenant_user`<br>2. `job_time_entry`: Rename to `idx_jte_*`, add `idx_jte_started_at`<br>3. `voice_command_log`: Rename to `idx_voice_log_*`, add missing indexes | **DROP old indexes** before creating new ones |
| **Phase 4: discount_version Triggers** | 1. Create `audit_discount_version_changes` trigger<br>2. Create `trg_discount_version_guard_created_immutable` trigger | **VALIDATED:** Functions exist (Task 2) |

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

## ⚠️ CRITICAL: Phase 5.3 Task 3 Specific Warnings

**BEFORE writing ANY code, review these Task 3 critical issues:**

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

### 3. Index Drop/Create Pattern

**Critical Pattern:** When renaming indexes, use DROP old + CREATE new pattern.

**Why:** PostgreSQL does not support `ALTER INDEX ... RENAME` for changing index definitions.

**Example:**
```python
# Drop old index
op.drop_index('ix_job_time_entry_job_id')

# Create new with correct name
op.create_index('idx_jte_job', 'job_time_entry', ['job_id'])
```

---

### 4. Trigger Creation Uses op.execute()

**Critical Detail:** Alembic does not have a native trigger creation method. Use `op.execute()` with raw SQL.

**Example:**
```python
op.execute("""
    CREATE TRIGGER audit_discount_version_changes
    AFTER INSERT OR UPDATE OR DELETE ON public.discount_version
    FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
""")
```

---

### 5. Foreign Key Creation for created_by

**Critical Detail:** The `created_by` column foreign key must be created after adding the column.

**Example:**
```python
# Add column first
op.add_column(
    'notification_delivery_attempt',
    sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True)
)

# Then add foreign key
op.create_foreign_key(
    'notification_delivery_attempt_created_by_fkey',
    'notification_delivery_attempt',
    'user',
    ['created_by'],
    ['id']
)
```

---

### 6. Server Default Syntax

**Critical Syntax:** Use `sa.text('now()')` for PostgreSQL function calls.

**Example:**
```python
op.alter_column(
    'notification_delivery_attempt',
    'created_at',
    server_default=sa.text('now()')
)
```

---

## Requirements

### Step-by-Step Implementation

**Step 1: Generate Migration Skeleton**

```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_5_3_comprehensive_schema_sync"
```

This creates a new migration file in `backend/alembic/versions/` with a name like:
`YYYY_MM_DD_HHMM-[hash]_phase_5_3_comprehensive_schema_sync.py`

---

**Step 2: Manually Construct Complete Migration**

The migration file MUST include all 4 phases. Use this template:

```python
"""Phase 5.3: Comprehensive schema sync (notification + idempotency + indexes + triggers)

Revision ID: XXX_phase_5_3_comprehensive_sync
Revises: [PREVIOUS_REVISION]
Create Date: 2026-04-11

CRITICAL: This migration bundles 4 phases into a single transaction to minimize
database state fragmentation per Phase 5.3 analysis requirements.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'XXX_phase_5_3_comprehensive_sync'
down_revision = '[PREVIOUS_REVISION]'


def upgrade():
    # ========== PHASE 1: notification_delivery_attempt ==========
    
    # 1.1: Rename provider_response → details (data preservation)
    op.alter_column(
        'notification_delivery_attempt',
        'provider_response',
        new_column_name='details'
    )
    
    # 1.2: Add new columns
    op.add_column(
        'notification_delivery_attempt',
        sa.Column('provider_code', sa.String(), nullable=True)
    )
    op.add_column(
        'notification_delivery_attempt',
        sa.Column('duration_ms', sa.Integer(), nullable=True)
    )
    op.add_column(
        'notification_delivery_attempt',
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # 1.3: Add foreign key for created_by
    op.create_foreign_key(
        'notification_delivery_attempt_created_by_fkey',
        'notification_delivery_attempt',
        'user',
        ['created_by'],
        ['id']
    )
    
    # 1.4: Fix created_at server default
    op.alter_column(
        'notification_delivery_attempt',
        'created_at',
        server_default=sa.text('now()')
    )
    
    # 1.5: Drop old inefficient indexes
    op.drop_index('ix_notification_delivery_attempt_notification_outbox_id', table_name='notification_delivery_attempt')
    op.drop_index('ix_notification_delivery_attempt_tenant_id', table_name='notification_delivery_attempt')
    
    # 1.6: Create new composite index
    op.create_index(
        'idx_notif_attempt_outbox_time',
        'notification_delivery_attempt',
        ['notification_outbox_id', sa.text('attempted_at DESC')]
    )
    
    # ========== PHASE 2: Idempotency Unique Constraints ==========
    
    # 2.1: Invoice constraints
    op.create_unique_constraint(
        'uq_invoice_tenant_number',
        'invoice',
        ['tenant_id', 'invoice_number']
    )
    op.create_unique_constraint(
        'uq_invoice_tenant_idempotency',
        'invoice',
        ['tenant_id', 'idempotency_key']
    )
    
    # 2.2: Quote constraint
    op.create_unique_constraint(
        'uq_quote_tenant_idempotency',
        'quote',
        ['tenant_id', 'idempotency_key']
    )
    
    # 2.3: Payment constraint
    op.create_unique_constraint(
        'uq_payment_tenant_idempotency',
        'payment',
        ['tenant_id', 'idempotency_key']
    )
    
    # ========== PHASE 3: Index Naming Standardization ==========
    
    # 3.1: conversation_session - Add missing composite index
    op.create_index(
        'idx_conv_session_tenant_user',
        'conversation_session',
        ['tenant_id', 'user_id', sa.text('updated_at DESC')]
    )
    
    # 3.2: job_time_entry - Drop old indexes, create new with correct names
    op.drop_index('ix_job_time_entry_job_id', table_name='job_time_entry')
    op.drop_index('ix_job_time_entry_user_id', table_name='job_time_entry')
    op.create_index('idx_jte_job', 'job_time_entry', ['job_id'])
    op.create_index('idx_jte_user', 'job_time_entry', ['user_id'])
    op.create_index(
        'idx_jte_started_at',
        'job_time_entry',
        [sa.text('started_at DESC')]
    )
    
    # 3.3: voice_command_log - Drop old index, create new with correct names
    op.drop_index('ix_voice_command_log_total_latency_ms', table_name='voice_command_log')
    op.create_index(
        'idx_voice_log_tenant_time',
        'voice_command_log',
        ['tenant_id', sa.text('created_at DESC')]
    )
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
    # ========== REVERSE PHASE 4: discount_version Triggers ==========
    op.execute("DROP TRIGGER IF EXISTS trg_discount_version_guard_created_immutable ON public.discount_version;")
    op.execute("DROP TRIGGER IF EXISTS audit_discount_version_changes ON public.discount_version;")
    
    # ========== REVERSE PHASE 3: Index Naming Standardization ==========
    # voice_command_log
    op.drop_index('idx_voice_log_latency', table_name='voice_command_log')
    op.drop_index('idx_voice_log_intent', table_name='voice_command_log')
    op.drop_index('idx_voice_log_tenant_time', table_name='voice_command_log')
    op.create_index('ix_voice_command_log_total_latency_ms', 'voice_command_log', ['total_latency_ms'])
    
    # job_time_entry
    op.drop_index('idx_jte_started_at', table_name='job_time_entry')
    op.drop_index('idx_jte_user', table_name='job_time_entry')
    op.drop_index('idx_jte_job', table_name='job_time_entry')
    op.create_index('ix_job_time_entry_user_id', 'job_time_entry', ['user_id'])
    op.create_index('ix_job_time_entry_job_id', 'job_time_entry', ['job_id'])
    
    # conversation_session
    op.drop_index('idx_conv_session_tenant_user', table_name='conversation_session')
    
    # ========== REVERSE PHASE 2: Idempotency Unique Constraints ==========
    op.drop_constraint('uq_payment_tenant_idempotency', 'payment', type_='unique')
    op.drop_constraint('uq_quote_tenant_idempotency', 'quote', type_='unique')
    op.drop_constraint('uq_invoice_tenant_idempotency', 'invoice', type_='unique')
    op.drop_constraint('uq_invoice_tenant_number', 'invoice', type_='unique')
    
    # ========== REVERSE PHASE 1: notification_delivery_attempt ==========
    # Drop new composite index
    op.drop_index('idx_notif_attempt_outbox_time', table_name='notification_delivery_attempt')
    
    # Restore old indexes
    op.create_index('ix_notification_delivery_attempt_tenant_id', 'notification_delivery_attempt', ['tenant_id'])
    op.create_index('ix_notification_delivery_attempt_notification_outbox_id', 'notification_delivery_attempt', ['notification_outbox_id'])
    
    # Remove server default from created_at
    op.alter_column(
        'notification_delivery_attempt',
        'created_at',
        server_default=None
    )
    
    # Drop foreign key and new columns
    op.drop_constraint('notification_delivery_attempt_created_by_fkey', 'notification_delivery_attempt', type_='foreignkey')
    op.drop_column('notification_delivery_attempt', 'created_by')
    op.drop_column('notification_delivery_attempt', 'duration_ms')
    op.drop_column('notification_delivery_attempt', 'provider_code')
    
    # Rename column back
    op.alter_column(
        'notification_delivery_attempt',
        'details',
        new_column_name='provider_response'
    )
```

---

**Step 3: Apply Migration**

```bash
# Verify migration file looks correct
cat backend/alembic/versions/[your_migration_file].py

# Apply migration
alembic upgrade head

# Capture output for verification
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade [PREV] -> [NEW], phase_5_3_comprehensive_schema_sync
```

---

**Step 4: Verify Database State (via postgres-local MCP Server)**

Run these verification queries to confirm all changes applied correctly:

```sql
-- Verification 1: notification_delivery_attempt columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'notification_delivery_attempt'
  AND column_name IN ('details', 'provider_code', 'duration_ms', 'created_by', 'created_at')
ORDER BY column_name;
-- Expected: 5 rows with correct types and defaults

-- Verification 2: Data preservation (compare with pre-migration count from Task 2)
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

-- Verification 5: Old ix_* indexes removed
SELECT tablename, indexname
FROM pg_indexes
WHERE tablename IN ('job_time_entry', 'voice_command_log', 'notification_delivery_attempt')
  AND indexname LIKE 'ix_%'
  AND indexname NOT LIKE '%_pkey';
-- Expected: 0 rows

-- Verification 6: Triggers attached
SELECT trigger_name, event_manipulation
FROM information_schema.triggers
WHERE event_object_table = 'discount_version'
ORDER BY trigger_name;
-- Expected: 2 rows (audit and immutability triggers)
```

---

**Step 5: Test Migration Rollback**

```bash
# Test backward migration
alembic downgrade -1

# Verify constraints/indexes/triggers removed (via MCP queries - run verifications again)

# Re-apply for continued work
alembic upgrade head
```

---

## Success Criteria for Task 3

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### Migration Creation
- [ ] **Regression baseline captured** (652/652 unit, 679/679 total)
- [ ] Single migration file created with all 4 phases
- [ ] Migration includes proper revision ID and down_revision
- [ ] All `upgrade()` operations included (column rename, new columns, constraints, indexes, triggers)
- [ ] All `downgrade()` operations included (reverse order)
- [ ] Migration file syntax validated

### Migration Execution
- [ ] Migration applies successfully forward (`alembic upgrade head`)
- [ ] No errors or warnings during migration execution
- [ ] Migration output logged and reviewed

### Database Verification
- [ ] **Verification 1 passed:** `notification_delivery_attempt` has 5 new/renamed columns
- [ ] **Verification 2 passed:** Data preservation confirmed (row counts match Task 2 baseline)
- [ ] **Verification 3 passed:** All 4 idempotency unique constraints exist
- [ ] **Verification 4 passed:** All new `idx_*` indexes exist
- [ ] **Verification 5 passed:** All old `ix_*` indexes removed
- [ ] **Verification 6 passed:** Both triggers exist on `discount_version`

### Rollback Testing
- [ ] Migration rolls back successfully (`alembic downgrade -1`)
- [ ] Database returns to pre-migration state (verified via queries)
- [ ] Migration re-applies successfully (`alembic upgrade head`)

### Test Suite
- [ ] **ALL 652 existing unit tests still passing**
- [ ] **ALL 679 total tests still passing**

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After migration is applied, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 652 passed

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 679 passed
```

### Step 2: Verify Database State

Run all 6 verification queries from Step 4 to confirm database matches Golden Master.

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check migration was applied successfully
3. Verify constraint/index/trigger definitions in database
4. Fix and re-run until 100% pass rate

**If verification queries fail:**
1. Check migration output for errors
2. Verify all phases executed
3. Check database logs for constraint/index creation failures
4. Consider rollback and re-apply if needed

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` - **Comprehensive Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Previous Tasks
- `task-db-sync-v9-phase-1-task-1-prompt.md` - SQLModel updates
- `task-db-sync-v9-phase-1-task-2-prompt.md` - Pre-migration validation

### Migration Directory
- `backend/alembic/versions/` - Where new migration will be created

---

## Risk Assessment

**For Task 3:**
- **Data Loss Risk:** MEDIUM (column rename must preserve data - CRITICAL to use ALTER COLUMN RENAME)
- **Migration Failure Risk:** LOW (Task 2 validation passed - no duplicates, functions exist)
- **Rollback Complexity:** MEDIUM (single migration with multiple operations)
- **Application Impact:** LOW (additive changes, improves data integrity without breaking changes)
- **Performance Impact:** POSITIVE (indexes improve query performance, constraints prevent duplicates)
- **Mitigation:** Comprehensive verification queries, rollback testing, data preservation checks

---

## Notes

### Important Patterns to Follow
- **Data Preservation:** ALWAYS use `ALTER COLUMN RENAME` for column renames, never DROP + ADD
- **Single Migration:** ALL 4 phases in ONE file - do not split across multiple migrations
- **Index Pattern:** DROP old + CREATE new for index renames
- **Trigger Pattern:** Use `op.execute()` with raw SQL for trigger creation
- **Foreign Keys:** Add column first, then add foreign key constraint
- **Server Defaults:** Use `sa.text('now()')` for PostgreSQL functions
- **Verification:** Run all 6 verification queries after migration

### Task 3 Specific
- **Column rename:** `provider_response` → `details` (preserve all data)
- **New columns:** `provider_code`, `duration_ms`, `created_by`
- **Idempotency:** Database-level enforcement via unique constraints
- **Index convention:** `idx_*` prefix with abbreviated table names
- **Triggers:** Audit logging + immutability guards on `discount_version`
- **Atomicity:** All changes in single transaction

### If You Get Stuck
- Review Alembic documentation for migration syntax
- Check previous migration files for similar patterns
- Use `postgres-local` MCP server to check database state
- Verify migration file syntax before applying
- Check Alembic logs if migration fails
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Task 3 Checklist:
1. ✅ Capture baseline (652/652 unit, 679/679 total)
2. 🔧 **Generate migration skeleton** (`alembic revision -m "phase_5_3_comprehensive_schema_sync"`)
3. 📝 **Manually construct complete migration** (all 4 phases in one file)
4. 🔍 **Verify migration syntax** (check imports, operations, downgrade)
5. ⚠️ **Double-check column rename uses ALTER COLUMN RENAME**
6. ✅ **Apply migration** (`alembic upgrade head`)
7. 📊 **Run Verification 1:** notification_delivery_attempt columns
8. 📊 **Run Verification 2:** Data preservation (row counts)
9. 📊 **Run Verification 3:** Unique constraints exist
10. 📊 **Run Verification 4:** New indexes exist
11. 📊 **Run Verification 5:** Old indexes removed
12. 📊 **Run Verification 6:** Triggers attached
13. ↩️ **Test rollback** (`alembic downgrade -1`)
14. 🔍 **Verify rollback** (run queries to confirm state)
15. ✅ **Re-apply migration** (`alembic upgrade head`)
16. 🔄 **Run regression tests** (652/652 unit, 679/679 total expected)
17. 📚 **Document completion**

Remember: Task 3 is the **CRITICAL IMPLEMENTATION** - this is where database changes actually happen. The migration MUST be atomic (all 4 phases in one file), MUST preserve data (use ALTER COLUMN RENAME), and MUST be fully reversible (complete downgrade() function). Verify everything thoroughly before marking complete!
