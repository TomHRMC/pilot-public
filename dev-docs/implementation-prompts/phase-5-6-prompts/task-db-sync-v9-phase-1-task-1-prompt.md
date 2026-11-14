# Task 1: SQLModel Schema Definitions Verification

**Reference:** `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md` - Task 1
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` - **Notification, Idempotency & Index Analysis** ⭐
- Current Live Database (Phase 5.2 Post-State)
**Type:** Phase 5.3 - SQLModel Schema Verification (Pre-Migration)
**Priority:** CRITICAL
**Change Type:** MODEL UPDATES ONLY (No database changes in this task)

---

## Context

This is **Phase 5.3 - DB Sync v#9 - Task 1**, the first of 4 tasks in a comprehensive synchronization addressing **4 major gap categories** in the physical database that don't match the Golden Master JSON.

**Root Cause:** 
- Notification schema evolved in JSON master but SQLModel not updated
- Idempotency keys exist as columns but lack database-level unique constraints in models
- Index naming inconsistencies (`ix_*` vs `idx_*`) in model definitions
- Compliance triggers not attached to `discount_version` table (model verification only - triggers added in migration)

**Critical Impact:**
- **Audit Trail Gap:** Missing `created_by`, `provider_code`, `duration_ms` in notification delivery attempts
- **Financial Data Risk:** No database-level idempotency enforcement (allows duplicate invoices/quotes/payments via race conditions)
- **Performance Degradation:** Missing indexes cause O(n) queries for voice AI and job costing dashboards
- **Compliance Violation:** Missing audit/immutability triggers on temporal versioned data

**Scope for Task 1:** Verify and update Python SQLModel definitions ONLY across 9 tables in 5 model files. No database changes happen in this task - those come in Task 3 (migration creation).

**Key Principle:** This task establishes the "target state" for the models. Task 2 validates the database is ready for changes. Task 3 creates the single migration to align database with these models.

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

## Current Task: SQLModel Schema Definitions Verification

**Effort:** 0.5 days
**Gap Reference:** Phase 5.3 Analysis - Notification/Idempotency/Index/Trigger Gaps
**Change Type:** MODEL VERIFICATION ONLY

This task verifies and updates SQLModel class definitions to match the Golden Master JSON schema. You will update 9 table models across 5 Python files to include column renames, new columns, unique constraints, and standardized index definitions. This establishes the target schema state before migration creation in Task 3.

### What Needs to Be Fixed

**Model Files & Required Changes:**

| File | Table | Changes Required |
|------|-------|-----------------|
| `backend/app/models/notification.py` | `NotificationDeliveryAttempt` | 1. Rename `provider_response` → `details`<br>2. Add columns: `provider_code`, `duration_ms`, `created_by`<br>3. Fix `created_at` server default<br>4. Add foreign key: `created_by` → `user.id`<br>5. Update `__table_args__` with `idx_notif_attempt_outbox_time` index<br>6. Remove old index definitions |
| `backend/app/models/billing.py` | `Invoice` | 1. Add unique constraint: `uq_invoice_tenant_number` on `(tenant_id, invoice_number)`<br>2. Add unique constraint: `uq_invoice_tenant_idempotency` on `(tenant_id, idempotency_key)`<br>3. Standardize index names to `idx_invoice_*` |
| `backend/app/models/billing.py` | `Payment` | 1. Add unique constraint: `uq_payment_tenant_idempotency` on `(tenant_id, idempotency_key)`<br>2. Standardize index names to `idx_payment_*` |
| `backend/app/models/quoting.py` | `Quote` | 1. Add unique constraint: `uq_quote_tenant_idempotency` on `(tenant_id, idempotency_key)`<br>2. Standardize index names to `idx_quote_*` |
| `backend/app/models/quoting.py` | `DiscountVersion` | 1. Verify table exists (triggers added in Task 3, not in model) |
| `backend/app/models/voice.py` | `ConversationSession` | 1. Add composite index: `idx_conv_session_tenant_user` on `(tenant_id, user_id, updated_at DESC)`<br>2. Rename pgvector index to `idx_conv_session_embedding` |
| `backend/app/models/job.py` | `JobTimeEntry` | 1. Rename indexes to `idx_jte_*` convention<br>2. Add missing index: `idx_jte_started_at` on `(started_at DESC)` |
| `backend/app/models/voice.py` | `VoiceCommandLog` | 1. Rename indexes to `idx_voice_log_*` convention<br>2. Add indexes: `idx_voice_log_tenant_time` on `(tenant_id, created_at DESC)`<br>3. Add index: `idx_voice_log_intent` on `(intent_detected)` |

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

## ⚠️ CRITICAL: Phase 5.3 Task 1 Specific Warnings

**BEFORE writing ANY code, review these Task 1 critical issues:**

### 1. Column Rename in Model ONLY - No Data Migration Yet

**Critical Rule:** In this task, you are ONLY updating the Python model. The actual column rename in the database happens in Task 3 (migration).

**What You Do in Task 1:**
```python
# In notification.py - Update the model definition:
class NotificationDeliveryAttempt(SQLModel, table=True):
    # RENAME: provider_response → details
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Provider-specific response payload (renamed from provider_response)"
    )
```

**What Happens in Task 3:**
- The Alembic migration will use `ALTER COLUMN ... RENAME` to preserve data
- DO NOT worry about data preservation in Task 1 - just update the model

**Impact:** Updating the model name alone won't break anything because the migration hasn't run yet. The migration in Task 3 will handle the actual database rename.

---

### 2. Server Default vs Column Default

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

### 3. Foreign Key for created_by Column

**Critical Detail:** The new `created_by` column in `notification_delivery_attempt` MUST have a foreign key to `user.id`.

**SQLModel Definition:**
```python
created_by: Optional[uuid.UUID] = Field(
    default=None,
    foreign_key="user.id",  # MANDATORY
    description="User who initiated this delivery attempt"
)
```

---

### 4. Index Naming Convention: idx_* (Not ix_*)

**Critical Rule:** Phase 5.3 standardizes on `idx_<abbreviated_table>_<purpose>` naming convention.

**Examples:**
```python
# ❌ WRONG (old convention):
Index("ix_job_time_entry_job_id", "job_id")
Index("ix_job_time_entry_user_id", "user_id")
Index("ix_voice_command_log_total_latency_ms", "total_latency_ms")

# ✅ CORRECT (new convention):
Index("idx_jte_job", "job_id")
Index("idx_jte_user", "user_id")
Index("idx_voice_log_latency", "total_latency_ms")
```

**Why This Matters:**
- **Consistency:** All other indexes in the schema use `idx_*` prefix
- **Readability:** Abbreviated table names make index names shorter and clearer
- **Maintainability:** Consistent naming simplifies troubleshooting and documentation

---

### 5. Unique Constraints for Idempotency

**Critical Pattern:** All idempotency constraints MUST be on `(tenant_id, idempotency_key)` tuple.

**SQLModel Syntax:**
```python
from sqlalchemy import UniqueConstraint

class Invoice(SQLModel, table=True):
    __tablename__ = "invoice"
    
    # ... existing fields ...
    
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "invoice_number",
            name="uq_invoice_tenant_number"
        ),
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_invoice_tenant_idempotency"
        ),
        # ... existing indexes ...
    )
```

**Why:** Multi-tenant isolation requires tenant_id in all unique constraints to prevent cross-tenant conflicts.

---

### 6. Composite Index with DESC Ordering

**Critical Pattern:** Indexes that include timestamp columns MUST use DESC ordering for performance.

**SQLModel Syntax:**
```python
from sqlalchemy import Index, text

__table_args__ = (
    Index(
        "idx_conv_session_tenant_user",
        "tenant_id",
        "user_id",
        text("updated_at DESC")  # Note: text() required for DESC
    ),
    # ... other constraints/indexes ...
)
```

**Why:** Most queries sort by timestamp descending (newest first). Index must match query ordering to avoid sort operations.

---

## ⚠️ CRITICAL: Coding Agent Best Practices (From Previous Phases)

### 1. Use Correct Import Statements

**Required Imports for Task 1:**
```python
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func, text, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlmodel import Field, SQLModel, Relationship
```

---

### 2. Do NOT Modify Existing Relationships

**Pattern:** Only update `__table_args__`, column definitions, and type hints. Leave relationships untouched unless explicitly required.

```python
# ✅ CORRECT - Leave relationships alone:
class NotificationDeliveryAttempt(SQLModel, table=True):
    # ... update columns and __table_args__ ...
    
    # Do NOT modify these unless required:
    notification_outbox: Optional["NotificationOutbox"] = Relationship(back_populates="delivery_attempts")
```

---

### 3. Preserve Existing Check Constraints

**Pattern:** When updating `__table_args__`, preserve all existing check constraints.

```python
# ✅ CORRECT - Keep existing constraints:
__table_args__ = (
    # Existing check constraint (DO NOT REMOVE):
    CheckConstraint(
        "status IN ('queued','delivered','bounced','rejected','throttled','error')",
        name="notification_delivery_attempt_status_chk"
    ),
    # Add new indexes/constraints here
    Index("idx_notif_attempt_outbox_time", "notification_outbox_id", text("attempted_at DESC")),
)
```

---

### 4. Test Model Import After Changes

**Verification Pattern:**
```bash
cd backend
source .venv/bin/activate
python -c "from app.models.notification import NotificationDeliveryAttempt; print('✅ Import successful')"
python -c "from app.models.billing import Invoice, Payment; print('✅ Import successful')"
python -c "from app.models.quoting import Quote, DiscountVersion; print('✅ Import successful')"
python -c "from app.models.voice import ConversationSession, VoiceCommandLog; print('✅ Import successful')"
python -c "from app.models.job import JobTimeEntry; print('✅ Import successful')"
```

**If any import fails:** Fix syntax errors before proceeding.

---

## Requirements

### Task 1 Model Update Structure

**CRITICAL:** This task updates ONLY Python models. Database changes happen in Task 3.

### Model 1: NotificationDeliveryAttempt

**File:** `backend/app/models/notification.py`

**Required Changes:**

```python
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func, text, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlmodel import Field, SQLModel, Relationship

class NotificationDeliveryAttempt(SQLModel, table=True):
    __tablename__ = "notification_delivery_attempt"
    
    # ... existing fields (id, tenant_id, notification_outbox_id, etc.) ...
    
    # RENAMED: provider_response → details
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Provider-specific response payload (renamed from provider_response)"
    )
    
    # NEW COLUMNS:
    provider_code: Optional[str] = Field(
        default=None,
        description="Provider-specific message/transaction ID (e.g., Twilio SID)"
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
    
    # FIXED: server_default for created_at
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )
    )
    
    # ... existing relationships (DO NOT MODIFY) ...
    
    __table_args__ = (
        # Existing check constraint (PRESERVE):
        CheckConstraint(
            "status IN ('queued','delivered','bounced','rejected','throttled','error')",
            name="notification_delivery_attempt_status_chk"
        ),
        # NEW: Composite index for performance
        Index(
            "idx_notif_attempt_outbox_time",
            "notification_outbox_id",
            text("attempted_at DESC")
        ),
    )
```

---

### Model 2: Invoice

**File:** `backend/app/models/billing.py`

**Required Changes:**

```python
from sqlalchemy import UniqueConstraint, Index, text

class Invoice(SQLModel, table=True):
    __tablename__ = "invoice"
    
    # ... existing fields ...
    
    __table_args__ = (
        # NEW: Idempotency unique constraints
        UniqueConstraint(
            "tenant_id",
            "invoice_number",
            name="uq_invoice_tenant_number"
        ),
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_invoice_tenant_idempotency"
        ),
        # Standardized index names (update existing or add new):
        Index("idx_invoice_customer", "customer_id"),
        Index("idx_invoice_status_due_at", "status_id", "due_at"),
        Index("idx_invoice_created_at", text("created_at DESC")),
        Index(
            "idx_invoice_balance",
            "balance_due_cents",
            postgresql_where=text("balance_due_cents > 0")
        ),
    )
```

---

### Model 3: Payment

**File:** `backend/app/models/billing.py`

**Required Changes:**

```python
class Payment(SQLModel, table=True):
    __tablename__ = "payment"
    
    # ... existing fields ...
    
    __table_args__ = (
        # NEW: Idempotency unique constraint
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_payment_tenant_idempotency"
        ),
        # Standardized index names:
        Index("idx_payment_invoice", "invoice_id"),
        Index("idx_payment_tenant", "tenant_id"),
        Index("idx_payment_created_at", text("created_at DESC")),
    )
```

---

### Model 4: Quote

**File:** `backend/app/models/quoting.py`

**Required Changes:**

```python
class Quote(SQLModel, table=True):
    __tablename__ = "quote"
    
    # ... existing fields ...
    
    __table_args__ = (
        # NEW: Idempotency unique constraint
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_quote_tenant_idempotency"
        ),
        # Standardized index names:
        Index("idx_quote_tenant", "tenant_id"),
        Index("idx_quote_customer", "customer_id"),
        Index("idx_quote_status", "status_id"),
        Index(
            "idx_quote_tenant_status_created_at",
            "tenant_id",
            "status_id",
            text("created_at DESC")
        ),
    )
```

---

### Model 5: ConversationSession

**File:** `backend/app/models/voice.py`

**Required Changes:**

```python
class ConversationSession(SQLModel, table=True):
    __tablename__ = "conversation_session"
    
    # ... existing fields ...
    
    __table_args__ = (
        # NEW: Composite index for user session queries
        Index(
            "idx_conv_session_tenant_user",
            "tenant_id",
            "user_id",
            text("updated_at DESC")
        ),
        # RENAMED: pgvector index (update name if it exists)
        Index(
            "idx_conv_session_embedding",
            "context_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"context_embedding": "vector_cosine_ops"}
        ),
    )
```

---

### Model 6: JobTimeEntry

**File:** `backend/app/models/job.py`

**Required Changes:**

```python
class JobTimeEntry(SQLModel, table=True):
    __tablename__ = "job_time_entry"
    
    # ... existing fields ...
    
    __table_args__ = (
        # RENAMED: Standardized index names
        Index("idx_jte_job", "job_id"),
        Index("idx_jte_user", "user_id"),
        # NEW: Missing time-based index
        Index("idx_jte_started_at", text("started_at DESC")),
    )
```

---

### Model 7: VoiceCommandLog

**File:** `backend/app/models/voice.py`

**Required Changes:**

```python
class VoiceCommandLog(SQLModel, table=True):
    __tablename__ = "voice_command_log"
    
    # ... existing fields ...
    
    __table_args__ = (
        # RENAMED & NEW: Standardized index names
        Index(
            "idx_voice_log_tenant_time",
            "tenant_id",
            text("created_at DESC")
        ),
        Index("idx_voice_log_intent", "intent_detected"),
        Index("idx_voice_log_latency", "total_latency_ms"),
    )
```

---

### Model 8: DiscountVersion

**File:** `backend/app/models/quoting.py`

**Verification Only:** Ensure the model exists. Triggers will be added in Task 3 migration, not in the model itself.

---

## Success Criteria for Task 1

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] **Regression baseline captured** (652/652 unit, 679/679 total)
- [ ] `notification_delivery_attempt` model updated with:
  - [ ] Column renamed: `provider_response` → `details`
  - [ ] 3 new columns added: `provider_code`, `duration_ms`, `created_by`
  - [ ] `created_at` has `server_default=func.now()`
  - [ ] Foreign key `created_by` → `user.id` defined
  - [ ] Index `idx_notif_attempt_outbox_time` added
- [ ] `Invoice` model updated with:
  - [ ] Unique constraint `uq_invoice_tenant_number`
  - [ ] Unique constraint `uq_invoice_tenant_idempotency`
  - [ ] Indexes standardized to `idx_invoice_*`
- [ ] `Payment` model updated with:
  - [ ] Unique constraint `uq_payment_tenant_idempotency`
  - [ ] Indexes standardized to `idx_payment_*`
- [ ] `Quote` model updated with:
  - [ ] Unique constraint `uq_quote_tenant_idempotency`
  - [ ] Indexes standardized to `idx_quote_*`
- [ ] `ConversationSession` model updated with:
  - [ ] Index `idx_conv_session_tenant_user` added
  - [ ] pgvector index renamed to `idx_conv_session_embedding`
- [ ] `JobTimeEntry` model updated with:
  - [ ] Indexes renamed to `idx_jte_*` convention
  - [ ] Index `idx_jte_started_at` added
- [ ] `VoiceCommandLog` model updated with:
  - [ ] Indexes renamed to `idx_voice_log_*` convention
  - [ ] Indexes `idx_voice_log_tenant_time` and `idx_voice_log_intent` added
- [ ] `DiscountVersion` model exists (verified)
- [ ] All models import successfully (`python -c "from app.models import *"`)
- [ ] Code passes Python syntax validation
- [ ] **ALL 652 existing unit tests still passing**
- [ ] **ALL 679 total tests still passing**

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all model updates, verify tests still pass.

### Step 1: Test Model Imports

```bash
cd backend
source .venv/bin/activate

# Test each model file individually
python -c "from app.models.notification import NotificationDeliveryAttempt; print('✅ notification.py')"
python -c "from app.models.billing import Invoice, Payment; print('✅ billing.py')"
python -c "from app.models.quoting import Quote, DiscountVersion; print('✅ quoting.py')"
python -c "from app.models.voice import ConversationSession, VoiceCommandLog; print('✅ voice.py')"
python -c "from app.models.job import JobTimeEntry; print('✅ job.py')"

# Test bulk import
python -c "from app.models import *; print('✅ All models import successfully')"
```

### Step 2: Run Full Test Suite

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

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check for syntax errors in model definitions
3. Verify imports are correct
4. Fix and re-run until 100% pass rate

**If model imports fail:**
1. Check for missing imports (UniqueConstraint, Index, text, etc.)
2. Verify column definitions match existing database columns (except new ones)
3. Check __table_args__ tuple syntax (must end with comma if single item)

---

## Key Files to Review

### Golden Master
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Analysis & Planning
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` - **Comprehensive Gap Analysis** ⭐⭐⭐

### Backend Models (9 tables affected)
- `backend/app/models/notification.py` - NotificationDeliveryAttempt
- `backend/app/models/billing.py` - Invoice, Payment
- `backend/app/models/quoting.py` - Quote, DiscountVersion
- `backend/app/models/voice.py` - ConversationSession, VoiceCommandLog
- `backend/app/models/job.py` - JobTimeEntry

---

## Risk Assessment

**For Task 1:**
- **Syntax Error Risk:** MEDIUM (complex __table_args__ definitions)
- **Import Error Risk:** LOW (standard SQLModel patterns)
- **Test Regression Risk:** LOW (model changes only, no DB changes yet)
- **Mitigation:** Incremental updates with import testing after each model file

---

## Notes

### Important Patterns to Follow
- **Model Changes Only:** No database operations in Task 1 - just Python code
- **Preserve Existing:** Keep all existing columns, relationships, and constraints
- **Standardize Naming:** Use `idx_*` prefix for all new indexes
- **Server Defaults:** Use `server_default=func.now()` not `default_factory`
- **Multi-Tenant Constraints:** All unique constraints must include `tenant_id`
- **Import Testing:** Test imports after each model file update

### Task 1 Specific
- **Column rename:** Update model only - migration handles database rename
- **New columns:** Define in model with correct types and foreign keys
- **Unique constraints:** Use `UniqueConstraint()` in `__table_args__`
- **Index naming:** Abbreviated table names + purpose (e.g., `idx_jte_job`)
- **DESC ordering:** Use `text("column_name DESC")` for timestamp indexes

### If You Get Stuck
- Review existing model definitions for similar patterns
- Check SQLAlchemy/SQLModel documentation for constraint syntax
- Verify all required imports are present
- Test model imports individually before running full test suite
- Ask for help if spending >20 minutes on syntax errors

---

**Ready to Begin!** 🚀

### Task 1 Checklist:
1. ✅ Capture baseline (652/652 unit, 679/679 total)
2. 🔍 **Update notification.py - NotificationDeliveryAttempt model**
3. ✅ Test import: `python -c "from app.models.notification import NotificationDeliveryAttempt"`
4. 🔍 **Update billing.py - Invoice model**
5. 🔍 **Update billing.py - Payment model**
6. ✅ Test import: `python -c "from app.models.billing import Invoice, Payment"`
7. 🔍 **Update quoting.py - Quote model**
8. 🔍 **Verify quoting.py - DiscountVersion model exists**
9. ✅ Test import: `python -c "from app.models.quoting import Quote, DiscountVersion"`
10. 🔍 **Update voice.py - ConversationSession model**
11. 🔍 **Update voice.py - VoiceCommandLog model**
12. ✅ Test import: `python -c "from app.models.voice import ConversationSession, VoiceCommandLog"`
13. 🔍 **Update job.py - JobTimeEntry model**
14. ✅ Test import: `python -c "from app.models.job import JobTimeEntry"`
15. ✅ **Test bulk import: `python -c "from app.models import *"`**
16. 🔄 **Run regression tests (652/652 unit, 679/679 total expected)**
17. 📚 **Document completion**

Remember: Task 1 is about updating Python models to match the target schema. No database changes occur until Task 3 creates the migration. Focus on correct syntax, proper imports, and maintaining test passing status!
