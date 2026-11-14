# Task 5: Add Missing DEFAULT Values (35+ Columns)

**Reference:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - Phase 4, Task 5
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - Production SQL Dump (Phase 4.6 Baseline)
**Type:** Phase 4 - Data Integrity (Defaults)
**Priority:** HIGH
**Change Type:** MIGRATION

---

## Context

This is **Phase 4.7 - DB Sync v#3**, a third forensic reconciliation after completing Phases 4.5 and 4.6. A comprehensive comparison between the latest SQL dump (`aevofab-db-schema-dump-phase-4.6-post.sql`) and the Golden Master JSON revealed **5 major remaining discrepancies** requiring final alignment before production deployment.

**Key Focus Areas:**
1. **Enumerated type standardization** (ENUM → TEXT + CHECK)
2. **Integer capacity risks** (Foreign key type mismatches)
3. **Unique indexing logic** (Broken email uniqueness constraint)
4. **Data integrity enforcement** (Missing defaults and constraints) ← **THIS TASK**
5. **Function/trigger alignment** (Database vs JSON discrepancies)

**Key Principle:** This phase focuses on **architectural decisions** and **implementation gaps** that need final resolution, not new features.

---

## What Was Completed in Previous Phases

**Phase 4.5 Status:** ✅ COMPLETE (March 30 - April 1, 2026)
- ✅ 572/572 tests passing (100%)
- ✅ 100% alignment between physical database and Golden Master JSON achieved
- ✅ All unique, check, and temporal exclusion constraints implemented
- ✅ All 293 triggers verified and functional

**Phase 4.6 Status:** ✅ COMPLETE (April 1-2, 2026)
- ✅ 575/575 unit tests passing (100%)
- ✅ 602/602 total tests passing (100%)
- ✅ Dual-master reconciliation completed
- ✅ Function logic and constraint backporting from SQL to JSON

**Phase 4.7 Progress:**
- ✅ Task 1: customer.type ENUM → TEXT (582/582 unit, 609/609 total)
- ✅ Task 2: user.preferred_mfa_channel ENUM → TEXT (591/591 unit, 618/618 total)
- ✅ Task 3: Fix tax_rate_version_id FK types (597/597 unit, 624/624 total)
- ✅ Task 4: Fix ux_global_primary_email index (602/602 unit, 629/629 total)

**Current Baseline:** 602/602 unit tests, 629/629 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for Phase 4.5 history
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` for Phase 4.6 history

---

## Current Task: Add Missing DEFAULT Values (35+ Columns)

**Effort:** 1-2 days
**Gap Reference:** Phase 4.7 Analysis - Enforce Data Integrity (Defaults)
**Change Type:** MIGRATION

The JSON schema defines DEFAULT values for 35+ columns across multiple tables, but these are **not enforced at the database level**. Application code must explicitly set these values, which is error-prone and creates a fail-safe risk. Database-level defaults ensure data consistency even if application logic fails to set values correctly.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `tenant_settings` | 4 rate/terms defaults missing | JSON→SQL | LOW |
| **2** | `job` | 3 financial tracking defaults missing | JSON→SQL | LOW |
| **3** | `quote` / `change_order` | Subtotal/tax/total/currency defaults missing | JSON→SQL | LOW |
| **4** | `invoice_line` / `quote_line` / `change_order_line` | Quantity/price/total defaults missing | JSON→SQL | LOW |
| **5** | `job_expense` | is_billable default missing | JSON→SQL | LOW |
| **6** | `notification_outbox` | 3 operational defaults missing | JSON→SQL | LOW |
| **7** | `webhook_delivery_attempt` | 2 attempt tracking defaults missing | JSON→SQL | LOW |
| **8** | `idempotency_key` | status default missing | JSON→SQL | LOW |
| **9** | `integration_sync_mapping` | sync_preference default missing | JSON→SQL | LOW |
| **10** | `integration_sync_conflict` | status default missing | JSON→SQL | LOW |
| **11** | `subscription` | 3 billing defaults missing | JSON→SQL | LOW |
| **12** | `subscription_usage` | used_quantity default missing | JSON→SQL | LOW |
| **13** | `usage_ledger` | 2 usage tracking defaults missing | JSON→SQL | LOW |
| **14** | `voice_command_log` | is_successful default missing | JSON→SQL | LOW |
| **15** | `connector_run_log` | 2 run tracking defaults missing | JSON→SQL | LOW |

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

**Record the output of both results:** `602/602 & 629/629 tests passing` (Phase 4.7 baseline - after Task 4)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Coding Agent Best Practices

**BEFORE writing ANY code, review these common errors from previous phases:**

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

**Why:** The pytest fixture is named `db_session` in `backend/tests/conftest.py`. Using `session` will cause fixture not found errors.

**Action:** Search existing tests to confirm: `grep -r "def test_.*db_session" backend/tests/` shows 217 tests use `db_session`.

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

**Why:** SQLModel uses `select()` + `exec()` pattern, not SQLAlchemy's `query()` API. The `query()` method generates deprecation warnings.

**Action:** Review existing tests for patterns: `backend/tests/test_citext_email.py` shows correct usage.

---

### 3. ALWAYS Check Alembic Autogenerate for `audit.event` Table

❌ **COMMON MIGRATION ERROR:**
```python
# Alembic autogenerate sometimes incorrectly wants to create audit.event
def upgrade():
    op.create_table('event',  # This table already exists!
        sa.Column('id', sa.BigInteger(), nullable=False),
        ...
        schema='audit'
    )
```

✅ **CORRECT (Remove Before Running Migration):**
```python
def upgrade():
    # op.create_table('event', ...) <- REMOVED
    # Only include your actual schema changes
    op.add_constraint(...)  # Your actual changes
```

**Downgrade:** Also, don't forget to remove the audit.event from the downgrade method too.

**Why:** The `audit.event` table was created in Phase 4.5 and exists in the database. Alembic autogenerate sometimes detects it as missing due to schema search path issues.

**Action After `alembic revision --autogenerate`:**
1. Open the generated migration file
2. Search for `'event'` and `schema='audit'`
3. **DELETE any `op.create_table('event', ... schema='audit')` statements in upgrade**
4. **DELETE any `op.drop_table('event', ... schema='audit')` statements in downgrade**
5. **DELETE any indexes or constraints as well from the event table that aren't included in your task**
6. Verify your actual changes are still present
7. Only then run `alembic upgrade head`

---

### 4. Use Explicit `sa_column` for Type Overrides

❌ **WRONG (Type Mismatch Between Model and DB):**
```python
class MyTable(SQLModel, table=True):
    # Python int maps to INTEGER by default, but you need BIGINT
    big_number: int = Field(foreign_key="other_table.id")
```

✅ **CORRECT (Explicit Type Control):**
```python
from sqlalchemy import Column, BigInteger

class MyTable(SQLModel, table=True):
    # Explicitly specify BIGINT via sa_column
    big_number: int = Field(
        foreign_key="other_table.id",
        sa_column=Column(BigInteger, nullable=False)
    )
```

**Why:** SQLModel's default type mapping for `int` is `INTEGER` (32-bit). If the parent table uses `BIGINT` (64-bit), you must explicitly specify the column type.

**Action:** Review `backend/app/models/quoting.py` and search for `sa_column=Column(BigInteger` to see examples.

---

### 5. Test NULL Handling for Nullable Constraints

❌ **INCOMPLETE TEST (Doesn't Test NULL):**
```python
def test_channel_valid(db_session, test_user):
    """Test valid channel values"""
    endpoint = UserEndpoint(channel='email', value='test@example.com')
    db_session.add(endpoint)
    db_session.commit()
    # Missing: What if channel is NULL?
```

✅ **COMPLETE TEST (Tests NULL if Nullable):**
```python
def test_channel_valid(db_session, test_user):
    """Test valid channel values"""
    endpoint = UserEndpoint(channel='email', value='test@example.com')
    db_session.add(endpoint)
    db_session.commit()

def test_channel_null_allowed(db_session, test_user):
    """Test NULL channel allowed (if nullable=True)"""
    endpoint = UserEndpoint(channel=None, value='test@example.com')
    db_session.add(endpoint)
    db_session.commit()  # Should succeed if nullable
```

**Why:** If a field is nullable, you must test that NULL values are accepted. If it's NOT nullable, test that NULL is rejected.

**Action:** For CHECK constraints with nullable fields, always include `field IS NULL OR field IN (...)` in the constraint.

---

### 6. Pre-Migration Data Validation is MANDATORY

❌ **WRONG (Apply Constraint Without Checking Data):**
```python
def upgrade():
    # Directly add constraint - might fail if existing data invalid!
    op.create_check_constraint(
        'user_email_chk',
        'user',
        "email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'"
    )
```

✅ **CORRECT (Validate Data First, Clean if Needed):**
```python
# BEFORE migration, run validation query:
# SELECT email FROM "user"
# WHERE email IS NOT NULL
#   AND email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
# If rows returned, fix data before running migration

def upgrade():
    # Only add constraint after confirming data is clean
    op.create_check_constraint(...)
```

**Why:** Adding a CHECK constraint when existing data violates it will cause the migration to fail. Always validate first.

**Action:** Include validation queries in the migration file as comments. Run them manually before `alembic upgrade`.

### 7. Use the text() wrapper for new SQL

SQLAlchemy requires explicit text() wrapper for raw SQL.

---

## Requirements

### 1. Implementation Details

#### For MIGRATION Tasks (This Task is a Migration)

**Problem:** The JSON schema defines DEFAULT values for 35+ columns across multiple tables, but these are not enforced at the database level. Application code must explicitly set these values, which is error-prone.

**Missing Defaults by Category:**

**Tenant Settings (4 defaults):**
```python
# backend/app/models/catalog.py
class TenantSettings(TenantIsolatedMixin, SQLModel, table=True):
    default_labor_rate_cents: int = Field(default=8500, nullable=False)  # $85.00/hr
    default_billable_labor_rate_cents: int = Field(default=15000, nullable=False)  # $150.00/hr
    default_quote_validity_days: int = Field(default=30, nullable=False)
    default_invoice_terms_days: int = Field(default=0, nullable=False)  # Due on receipt
```

**Job Financials (3 defaults):**
```python
# backend/app/models/fulfillment.py
class Job(TenantIsolatedMixin, SQLModel, table=True):
    actual_labor_cost_cents: int = Field(default=0, nullable=False)
    actual_material_cost_cents: int = Field(default=0, nullable=False)
    actual_profit_cents: int = Field(default=0, nullable=False)
```

**Quote/Change Order Totals (4 defaults each = 8 total):**
```python
# backend/app/models/quoting.py
class Quote(TenantIsolatedMixin, SQLModel, table=True):
    subtotal_cents: int = Field(default=0, nullable=False)
    tax_cents: int = Field(default=0, nullable=False)
    total_cents: int = Field(default=0, nullable=False)
    currency: str = Field(default='USD', nullable=False)

class ChangeOrder(TenantIsolatedMixin, SQLModel, table=True):
    subtotal_cents: int = Field(default=0, nullable=False)
    tax_cents: int = Field(default=0, nullable=False)
    total_cents: int = Field(default=0, nullable=False)
    currency: str = Field(default='USD', nullable=False)
```

**Line Item Defaults (4 defaults × 3 tables = 12 total):**
```python
# backend/app/models/fulfillment.py
class InvoiceLine(TenantIsolatedMixin, SQLModel, table=True):
    quantity: Decimal = Field(default=Decimal("1"), nullable=False)
    unit_price_cents: int = Field(default=0, nullable=False)
    total_cents: int = Field(default=0, nullable=False)
    subtotal_cents: int = Field(default=0, nullable=False)

# backend/app/models/quoting.py
class QuoteLine(TenantIsolatedMixin, SQLModel, table=True):
    quantity: Decimal = Field(default=Decimal("1"), nullable=False)
    unit_price_cents: int = Field(default=0, nullable=False)
    total_cents: int = Field(default=0, nullable=False)
    subtotal_cents: int = Field(default=0, nullable=False)

class ChangeOrderLine(TenantIsolatedMixin, SQLModel, table=True):
    quantity: Decimal = Field(default=Decimal("1"), nullable=False)
    unit_price_cents: int = Field(default=0, nullable=False)
    total_cents: int = Field(default=0, nullable=False)
    subtotal_cents: int = Field(default=0, nullable=False)
```

**System/Operational Defaults (8 defaults):**
```python
# backend/app/models/fulfillment.py
class JobExpense(TenantIsolatedMixin, SQLModel, table=True):
    is_billable: bool = Field(default=True, nullable=False)

# backend/app/models/system.py
class NotificationOutbox(TenantIsolatedMixin, SQLModel, table=True):
    attempt_count: int = Field(default=0, nullable=False)
    priority: int = Field(default=5, nullable=False)
    status: str = Field(default='pending', nullable=False)

class WebhookDeliveryAttempt(TenantIsolatedMixin, SQLModel, table=True):
    attempt_no: int = Field(default=1, nullable=False)
    status: str = Field(default='pending', nullable=False)

class IdempotencyKey(TenantIsolatedMixin, SQLModel, table=True):
    status: str = Field(default='in_progress', nullable=False)

class IntegrationSyncMapping(TenantIsolatedMixin, SQLModel, table=True):
    sync_preference: str = Field(default='aevofab_master', nullable=False)

class IntegrationSyncConflict(TenantIsolatedMixin, SQLModel, table=True):
    status: str = Field(default='pending', nullable=False)
```

**Billing/Subscription Defaults (6 defaults):**
```python
# backend/app/models/billing.py
class Subscription(TenantIsolatedMixin, SQLModel, table=True):
    quantity_seats: int = Field(default=1, nullable=False)
    billing_interval: str = Field(default='monthly', nullable=False)
    cancel_at_period_end: bool = Field(default=False, nullable=False)

class SubscriptionUsage(TenantIsolatedMixin, SQLModel, table=True):
    used_quantity: int = Field(default=0, nullable=False)

class UsageLedger(TenantIsolatedMixin, SQLModel, table=True):
    quantity: int = Field(default=1, nullable=False)
    is_reported: bool = Field(default=False, nullable=False)
```

**Voice AI Defaults (3 defaults):**
```python
# backend/app/models/voice_ai.py
class VoiceCommandLog(TenantIsolatedMixin, SQLModel, table=True):
    is_successful: bool = Field(default=True, nullable=False)

# backend/app/models/system.py
class ConnectorRunLog(TenantIsolatedMixin, SQLModel, table=True):
    status: str = Field(default='running', nullable=False)
    items_fetched: int = Field(default=0, nullable=False)
```

**Migration SQL:**
```sql
-- Pre-migration validation
-- Query database to verify no NULL values exist where defaults will be set
SELECT 
    'tenant_settings' AS table_name,
    COUNT(*) AS null_count
FROM tenant_settings
WHERE default_labor_rate_cents IS NULL
   OR default_billable_labor_rate_cents IS NULL
   OR default_quote_validity_days IS NULL
   OR default_invoice_terms_days IS NULL
UNION ALL
SELECT 'job', COUNT(*)
FROM job
WHERE actual_labor_cost_cents IS NULL
   OR actual_material_cost_cents IS NULL
   OR actual_profit_cents IS NULL
-- ... repeat for all tables/columns ...
;

-- Add DEFAULT values (upgrade)
-- Tenant Settings
ALTER TABLE tenant_settings ALTER COLUMN default_labor_rate_cents SET DEFAULT 8500;
ALTER TABLE tenant_settings ALTER COLUMN default_billable_labor_rate_cents SET DEFAULT 15000;
ALTER TABLE tenant_settings ALTER COLUMN default_quote_validity_days SET DEFAULT 30;
ALTER TABLE tenant_settings ALTER COLUMN default_invoice_terms_days SET DEFAULT 0;

-- Job Financials
ALTER TABLE job ALTER COLUMN actual_labor_cost_cents SET DEFAULT 0;
ALTER TABLE job ALTER COLUMN actual_material_cost_cents SET DEFAULT 0;
ALTER TABLE job ALTER COLUMN actual_profit_cents SET DEFAULT 0;

-- Quote/Change Order Totals
ALTER TABLE quote ALTER COLUMN subtotal_cents SET DEFAULT 0;
ALTER TABLE quote ALTER COLUMN tax_cents SET DEFAULT 0;
ALTER TABLE quote ALTER COLUMN total_cents SET DEFAULT 0;
ALTER TABLE quote ALTER COLUMN currency SET DEFAULT 'USD';

ALTER TABLE change_order ALTER COLUMN subtotal_cents SET DEFAULT 0;
ALTER TABLE change_order ALTER COLUMN tax_cents SET DEFAULT 0;
ALTER TABLE change_order ALTER COLUMN total_cents SET DEFAULT 0;
ALTER TABLE change_order ALTER COLUMN currency SET DEFAULT 'USD';

-- Line Item Defaults (3 tables)
ALTER TABLE invoice_line ALTER COLUMN quantity SET DEFAULT 1;
ALTER TABLE invoice_line ALTER COLUMN unit_price_cents SET DEFAULT 0;
ALTER TABLE invoice_line ALTER COLUMN total_cents SET DEFAULT 0;
ALTER TABLE invoice_line ALTER COLUMN subtotal_cents SET DEFAULT 0;

ALTER TABLE quote_line ALTER COLUMN quantity SET DEFAULT 1;
ALTER TABLE quote_line ALTER COLUMN unit_price_cents SET DEFAULT 0;
ALTER TABLE quote_line ALTER COLUMN total_cents SET DEFAULT 0;
ALTER TABLE quote_line ALTER COLUMN subtotal_cents SET DEFAULT 0;

ALTER TABLE change_order_line ALTER COLUMN quantity SET DEFAULT 1;
ALTER TABLE change_order_line ALTER COLUMN unit_price_cents SET DEFAULT 0;
ALTER TABLE change_order_line ALTER COLUMN total_cents SET DEFAULT 0;
ALTER TABLE change_order_line ALTER COLUMN subtotal_cents SET DEFAULT 0;

-- System/Operational
ALTER TABLE job_expense ALTER COLUMN is_billable SET DEFAULT true;
ALTER TABLE notification_outbox ALTER COLUMN attempt_count SET DEFAULT 0;
ALTER TABLE notification_outbox ALTER COLUMN priority SET DEFAULT 5;
ALTER TABLE notification_outbox ALTER COLUMN status SET DEFAULT 'pending';
ALTER TABLE webhook_delivery_attempt ALTER COLUMN attempt_no SET DEFAULT 1;
ALTER TABLE webhook_delivery_attempt ALTER COLUMN status SET DEFAULT 'pending';
ALTER TABLE idempotency_key ALTER COLUMN status SET DEFAULT 'in_progress';
ALTER TABLE integration_sync_mapping ALTER COLUMN sync_preference SET DEFAULT 'aevofab_master';
ALTER TABLE integration_sync_conflict ALTER COLUMN status SET DEFAULT 'pending';

-- Billing/Subscription
ALTER TABLE subscription ALTER COLUMN quantity_seats SET DEFAULT 1;
ALTER TABLE subscription ALTER COLUMN billing_interval SET DEFAULT 'monthly';
ALTER TABLE subscription ALTER COLUMN cancel_at_period_end SET DEFAULT false;
ALTER TABLE subscription_usage ALTER COLUMN used_quantity SET DEFAULT 0;
ALTER TABLE usage_ledger ALTER COLUMN quantity SET DEFAULT 1;
ALTER TABLE usage_ledger ALTER COLUMN is_reported SET DEFAULT false;

-- Voice AI
ALTER TABLE voice_command_log ALTER COLUMN is_successful SET DEFAULT true;
ALTER TABLE connector_run_log ALTER COLUMN status SET DEFAULT 'running';
ALTER TABLE connector_run_log ALTER COLUMN items_fetched SET DEFAULT 0;

-- Migration downgrade()
-- Remove all defaults (reverse order for safety)
ALTER TABLE connector_run_log ALTER COLUMN items_fetched DROP DEFAULT;
ALTER TABLE connector_run_log ALTER COLUMN status DROP DEFAULT;
ALTER TABLE voice_command_log ALTER COLUMN is_successful DROP DEFAULT;
ALTER TABLE usage_ledger ALTER COLUMN is_reported DROP DEFAULT;
ALTER TABLE usage_ledger ALTER COLUMN quantity DROP DEFAULT;
ALTER TABLE subscription_usage ALTER COLUMN used_quantity DROP DEFAULT;
ALTER TABLE subscription ALTER COLUMN cancel_at_period_end DROP DEFAULT;
ALTER TABLE subscription ALTER COLUMN billing_interval DROP DEFAULT;
ALTER TABLE subscription ALTER COLUMN quantity_seats DROP DEFAULT;
ALTER TABLE integration_sync_conflict ALTER COLUMN status DROP DEFAULT;
ALTER TABLE integration_sync_mapping ALTER COLUMN sync_preference DROP DEFAULT;
ALTER TABLE idempotency_key ALTER COLUMN status DROP DEFAULT;
ALTER TABLE webhook_delivery_attempt ALTER COLUMN status DROP DEFAULT;
ALTER TABLE webhook_delivery_attempt ALTER COLUMN attempt_no DROP DEFAULT;
ALTER TABLE notification_outbox ALTER COLUMN status DROP DEFAULT;
ALTER TABLE notification_outbox ALTER COLUMN priority DROP DEFAULT;
ALTER TABLE notification_outbox ALTER COLUMN attempt_count DROP DEFAULT;
ALTER TABLE job_expense ALTER COLUMN is_billable DROP DEFAULT;
ALTER TABLE change_order_line ALTER COLUMN subtotal_cents DROP DEFAULT;
ALTER TABLE change_order_line ALTER COLUMN total_cents DROP DEFAULT;
ALTER TABLE change_order_line ALTER COLUMN unit_price_cents DROP DEFAULT;
ALTER TABLE change_order_line ALTER COLUMN quantity DROP DEFAULT;
ALTER TABLE quote_line ALTER COLUMN subtotal_cents DROP DEFAULT;
ALTER TABLE quote_line ALTER COLUMN total_cents DROP DEFAULT;
ALTER TABLE quote_line ALTER COLUMN unit_price_cents DROP DEFAULT;
ALTER TABLE quote_line ALTER COLUMN quantity DROP DEFAULT;
ALTER TABLE invoice_line ALTER COLUMN subtotal_cents DROP DEFAULT;
ALTER TABLE invoice_line ALTER COLUMN total_cents DROP DEFAULT;
ALTER TABLE invoice_line ALTER COLUMN unit_price_cents DROP DEFAULT;
ALTER TABLE invoice_line ALTER COLUMN quantity DROP DEFAULT;
ALTER TABLE change_order ALTER COLUMN currency DROP DEFAULT;
ALTER TABLE change_order ALTER COLUMN total_cents DROP DEFAULT;
ALTER TABLE change_order ALTER COLUMN tax_cents DROP DEFAULT;
ALTER TABLE change_order ALTER COLUMN subtotal_cents DROP DEFAULT;
ALTER TABLE quote ALTER COLUMN currency DROP DEFAULT;
ALTER TABLE quote ALTER COLUMN total_cents DROP DEFAULT;
ALTER TABLE quote ALTER COLUMN tax_cents DROP DEFAULT;
ALTER TABLE quote ALTER COLUMN subtotal_cents DROP DEFAULT;
ALTER TABLE job ALTER COLUMN actual_profit_cents DROP DEFAULT;
ALTER TABLE job ALTER COLUMN actual_material_cost_cents DROP DEFAULT;
ALTER TABLE job ALTER COLUMN actual_labor_cost_cents DROP DEFAULT;
ALTER TABLE tenant_settings ALTER COLUMN default_invoice_terms_days DROP DEFAULT;
ALTER TABLE tenant_settings ALTER COLUMN default_quote_validity_days DROP DEFAULT;
ALTER TABLE tenant_settings ALTER COLUMN default_billable_labor_rate_cents DROP DEFAULT;
ALTER TABLE tenant_settings ALTER COLUMN default_labor_rate_cents DROP DEFAULT;
```

**Database Verification Query:**
```sql
-- Verify defaults exist after migration
SELECT 
    table_name,
    column_name,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
    'tenant_settings', 'job', 'quote', 'change_order',
    'invoice_line', 'quote_line', 'change_order_line',
    'job_expense', 'notification_outbox', 'webhook_delivery_attempt',
    'idempotency_key', 'integration_sync_mapping', 'integration_sync_conflict',
    'subscription', 'subscription_usage', 'usage_ledger',
    'voice_command_log', 'connector_run_log'
  )
  AND column_default IS NOT NULL
ORDER BY table_name, column_name;
```

---

### 2. Implementation Order

**For MIGRATION Tasks (This Task):**

1. **✅ Establish Regression Baseline** (602/602 unit, 629/629 total tests)
2. **Pre-Migration Data Validation**
   - Run validation queries
   - Verify no NULL values where defaults will be set
3. **Update SQLModel Classes**
   - Modify `backend/app/models/catalog.py` - TenantSettings
   - Modify `backend/app/models/fulfillment.py` - Job, InvoiceLine, JobExpense
   - Modify `backend/app/models/quoting.py` - Quote, QuoteLine, ChangeOrder, ChangeOrderLine
   - Modify `backend/app/models/system.py` - NotificationOutbox, WebhookDeliveryAttempt, IdempotencyKey, IntegrationSyncMapping, IntegrationSyncConflict, ConnectorRunLog
   - Modify `backend/app/models/billing.py` - Subscription, SubscriptionUsage, UsageLedger
   - Modify `backend/app/models/voice_ai.py` - VoiceCommandLog
4. **Generate Alembic Migration**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "phase_4_7_add_missing_default_values_task5"
   ```
5. **Review & Enhance Migration**
   - ⚠️ **CRITICAL: Check for and remove audit.event table operations**
   - Verify all 35+ DEFAULT changes captured
   - Add pre-migration validation queries as comments
   - Ensure downgrade() removes all defaults
6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suite**
   - Create `backend/tests/test_phase_4_7_default_values.py`
   - Use `db_session` parameter (NOT `session`)
   - Use `select()/exec()` pattern (NOT `query()`)
8. **Run New Tests**
   ```bash
   pytest tests/test_phase_4_7_default_values.py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 602 existing unit tests MUST still pass**
- **ALL 629 total tests (including integration) MUST still pass**
- **New tests MUST pass**
- **Target: 100% pass rate on both test suites**

#### Test File: `backend/tests/test_phase_4_7_default_values.py`

**Required Coverage (Minimum 35+ Tests - one per default):**
```python
"""
Test Suite: Phase 4.7 Task 5 - Add Missing DEFAULT Values
Tests database-level default values - final schema alignment for production deployment

Reference: phase-4.7-db-schema-sync-3-plan.md - Task 5
"""
import pytest
from decimal import Decimal
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.catalog import TenantSettings
from app.models.fulfillment import Job, InvoiceLine, JobExpense
from app.models.quoting import Quote, QuoteLine, ChangeOrder, ChangeOrderLine
from app.models.system import (
    NotificationOutbox, WebhookDeliveryAttempt, IdempotencyKey,
    IntegrationSyncMapping, IntegrationSyncConflict, ConnectorRunLog
)
from app.models.billing import Subscription, SubscriptionUsage, UsageLedger
from app.models.voice_ai import VoiceCommandLog

# ✅ CORRECT: Use db_session parameter and select()/exec() pattern

class TestTenantSettingsDefaults:
    """Test DEFAULT values for tenant_settings table"""
    
    def test_default_labor_rate_cents_default(self, db_session: Session, test_tenant):
        """Test default_labor_rate_cents has database default"""
        # Create without specifying field - should use default
        settings = TenantSettings(tenant_id=test_tenant.id)
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        assert settings.default_labor_rate_cents == 8500  # $85.00/hr
    
    def test_default_billable_labor_rate_cents_default(self, db_session: Session, test_tenant):
        """Test default_billable_labor_rate_cents has database default"""
        settings = TenantSettings(tenant_id=test_tenant.id)
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        assert settings.default_billable_labor_rate_cents == 15000  # $150.00/hr
    
    def test_default_quote_validity_days_default(self, db_session: Session, test_tenant):
        """Test default_quote_validity_days has database default"""
        settings = TenantSettings(tenant_id=test_tenant.id)
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        assert settings.default_quote_validity_days == 30
    
    def test_default_invoice_terms_days_default(self, db_session: Session, test_tenant):
        """Test default_invoice_terms_days has database default"""
        settings = TenantSettings(tenant_id=test_tenant.id)
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        assert settings.default_invoice_terms_days == 0  # Due on receipt


class TestJobFinancialDefaults:
    """Test DEFAULT values for job financial tracking"""
    
    def test_actual_labor_cost_cents_default(self, db_session: Session, test_tenant, test_customer, test_site):
        """Test actual_labor_cost_cents has database default"""
        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status='scheduled'
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.actual_labor_cost_cents == 0
    
    def test_actual_material_cost_cents_default(self, db_session: Session, test_tenant, test_customer, test_site):
        """Test actual_material_cost_cents has database default"""
        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status='scheduled'
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.actual_material_cost_cents == 0
    
    def test_actual_profit_cents_default(self, db_session: Session, test_tenant, test_customer, test_site):
        """Test actual_profit_cents has database default"""
        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status='scheduled'
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.actual_profit_cents == 0


class TestQuoteTotalsDefaults:
    """Test DEFAULT values for quote totals"""
    
    def test_quote_subtotal_default(self, db_session: Session, test_tenant, test_customer, test_site):
        """Test quote.subtotal_cents has database default"""
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id
        )
        db_session.add(quote)
        db_session.commit()
        db_session.refresh(quote)
        
        assert quote.subtotal_cents == 0
    
    def test_quote_tax_default(self, db_session: Session, test_tenant, test_customer, test_site):
        """Test quote.tax_cents has database default"""
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id
        )
        db_session.add(quote)
        db_session.commit()
        db_session.refresh(quote)
        
        assert quote.tax_cents == 0
    
    def test_quote_total_default(self, db_session: Session, test_tenant, test_customer, test_site):
        """Test quote.total_cents has database default"""
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id
        )
        db_session.add(quote)
        db_session.commit()
        db_session.refresh(quote)
        
        assert quote.total_cents == 0
    
    def test_quote_currency_default(self, db_session: Session, test_tenant, test_customer, test_site):
        """Test quote.currency has database default"""
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id
        )
        db_session.add(quote)
        db_session.commit()
        db_session.refresh(quote)
        
        assert quote.currency == 'USD'


# Similar test classes for:
# - TestChangeOrderTotalsDefaults
# - TestLineItemDefaults (invoice_line, quote_line, change_order_line)
# - TestSystemOperationalDefaults
# - TestBillingDefaults
# - TestVoiceAIDefaults

# ... (Add all remaining test classes following same pattern)
```

**Test Patterns to Follow:**
- Review `backend/tests/test_check_constraints_task9.py` - Shows proper constraint testing
- Review `backend/tests/test_citext_email.py` - Shows select()/exec() pattern
- Use fixtures from `backend/tests/conftest.py`

**Common Test Fixtures Available:**
- `db_session` - Database session (use this, NOT `session`)
- `test_tenant` - Pre-created tenant for testing
- `test_user` - Pre-created user linked to test_tenant
- `test_customer` - Pre-created customer
- `test_site` - Pre-created site
- `utc_now` - Timezone-aware current timestamp function

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Full Test Suite

```bash
# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:**
- **Unit tests:** `[602 + NEW_TEST_COUNT] passed` (no regressions + new defaults tests)
- **Total tests:** `[629 + NEW_TEST_COUNT] passed` (no regressions + new defaults tests)

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For this MIGRATION task:**
- If new tests fail → Fix implementation or test logic
- If existing tests fail → Your migration broke something (rollback and fix)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md`

Find Phase 4, Task 5 and update with:

```markdown
### Task 5: Add Missing DEFAULT Values (35+ Columns)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 1-2 days (actual)
**Change Type:** MIGRATION

**Implementation Summary:**

- Modified: `backend/app/models/catalog.py` - TenantSettings (4 defaults)
- Modified: `backend/app/models/fulfillment.py` - Job (3), InvoiceLine (4), JobExpense (1)
- Modified: `backend/app/models/quoting.py` - Quote (4), QuoteLine (4), ChangeOrder (4), ChangeOrderLine (4)
- Modified: `backend/app/models/system.py` - 8 models with operational defaults
- Modified: `backend/app/models/billing.py` - Subscription (3), SubscriptionUsage (1), UsageLedger (2)
- Modified: `backend/app/models/voice_ai.py` - VoiceCommandLog (1)
- Migration: `YYYY_MM_DD_HHMM-[hash]_phase_4_7_add_missing_default_values_task5.py`
- Test Suite: `test_phase_4_7_default_values.py` - [X] tests ✅
- Final Results: [602 + X]/[602 + X] unit tests passing (100%), [629 + X]/[629 + X] total tests passing (100%)

**Key Changes:**
- ✅ Added 35+ database-level DEFAULT values across 15+ tables
- ✅ Tenant settings rate/terms defaults (8500, 15000, 30, 0)
- ✅ Job financial tracking defaults (0, 0, 0)
- ✅ Quote/invoice/change order totals defaults (0, 0, 0, 'USD')
- ✅ Line item quantity/price defaults (1, 0, 0, 0)
- ✅ System operational defaults (0, 5, 'pending', 1, 'pending', 'in_progress', etc.)
- ✅ Billing/subscription defaults (1, 'monthly', false, 0, 1, false)
- ✅ Voice AI defaults (true, 'running', 0)
- ✅ Application can now omit these fields in INSERT statements safely

**Verification:**
- All 35+ defaults verified via information_schema.columns query
- Application code no longer required to set default values explicitly
- Database enforces sensible defaults even if application logic fails
- Migration rollback tested successfully (downgrade → upgrade)
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For MIGRATION Tasks (This Task):
- [ ] **Regression baseline captured** (602/602 unit, 629/629 total tests)
- [ ] **Pre-migration data validation completed** (no NULL values where defaults will be set)
- [ ] **SQLModel classes updated** across 7 model files with correct Field(default=...) values
- [ ] **Used `db_session` parameter** (not `session`) in tests
- [ ] **Used `select()/exec()` pattern** (not `query()`) in tests
- [ ] **Alembic migration created** using autogenerate
- [ ] **⚠️ CRITICAL: Checked migration for `audit.event` table** and removed if present
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 35+ new tests written and passing** (one per DEFAULT value)
- [ ] **Tests use `db_session` parameter** and `select()/exec()` pattern
- [ ] **ALL 602 existing unit tests still passing**
- [ ] **ALL 629 total tests still passing** (including integration)
- [ ] **New total: [602 + X]/[602 + X] unit passing, [629 + X]/[629 + X] total passing (100%)**
- [ ] **Database verification query confirms** all 35+ defaults active
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` again)
- [ ] **Project plan document updated**

### For ALL Tasks:
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained or exceeded

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md` - **Task 5 Details** ⭐
- `dev-docs/analysis/phase-4.7-db-schema-sync-3-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6-post.sql` - **Production SQL Dump (Phase 4.6 Baseline)**

### Backend Code (Models to Update)
- `backend/app/models/catalog.py` - TenantSettings
- `backend/app/models/fulfillment.py` - Job, InvoiceLine, JobExpense
- `backend/app/models/quoting.py` - Quote, QuoteLine, ChangeOrder, ChangeOrderLine
- `backend/app/models/system.py` - NotificationOutbox, WebhookDeliveryAttempt, IdempotencyKey, IntegrationSyncMapping, IntegrationSyncConflict, ConnectorRunLog
- `backend/app/models/billing.py` - Subscription, SubscriptionUsage, UsageLedger
- `backend/app/models/voice_ai.py` - VoiceCommandLog

### Tests (Reference for Patterns)
- `backend/tests/test_check_constraints_task9.py` - CHECK constraint patterns
- `backend/tests/test_citext_email.py` - Correct `select()/exec()` usage
- `backend/tests/conftest.py` - Test fixtures (`db_session`, `test_tenant`, etc.)

---

## Risk Assessment

**Data Validation Risk:** LOW
- Adding defaults doesn't affect existing data
- No risk of constraint violations
- **Mitigation:** Pre-migration validation confirms no NULL values where defaults required

**Regression Risk:** LOW
- Defaults are metadata-only changes (no data modification)
- Existing application code continues to work
- **Mitigation:** Maintain 602/629 baseline, test after migration, check alembic for audit.event

**Application Risk:** LOW (IMPROVEMENT)
- Defaults improve reliability by removing need for explicit value setting
- Fail-safe against application bugs
- **Mitigation:** Test that defaults are applied correctly for new records

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `db_session` Parameter:** NOT `session` (pytest fixture naming)
- **Use `select()/exec()` Pattern:** NOT `query()` (SQLModel standard, no deprecation warnings)
- **Check Alembic Migrations:** ALWAYS remove `audit.event` table creation if autogenerated
- **Dual Master Strategy:** JSON is documentation authority, SQL dump is runtime authority
- **Zero Regression Policy:** All 602 unit + 629 total tests MUST pass after changes

### Phase 4.7 Task 5 Specific
- **35+ defaults to add** - Systematic approach required across 15+ tables
- **Low-risk migration** - Defaults are metadata-only, no data changes
- **Test comprehensively** - One test per default value minimum
- **Pre-validate data** - Ensure no NULL values where defaults will be set
- **Group defaults logically** - By functional area (tenant settings, financials, etc.)
- **Document defaults clearly** - Comment why each default value was chosen

### If You Get Stuck
- Check the JSON schema for exact default values
- Review Phase 4.7 Tasks 1-4 for migration patterns
- Use `postgres-local` MCP server to query current defaults
- Search existing models for Field(default=...) patterns
- Review conftest.py for test fixture usage
- Remember: Defaults improve reliability, this is a safety enhancement

---

## Example Task Flow

### For MIGRATION Tasks (This Task):

```bash
# 1. Baseline - Capture starting point
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 602 passed

# Run all tests (including integration)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 629 passed

# 2. Pre-migration data validation
# Query for NULL values where defaults will be set
# Use postgres-local MCP server or psql to run validation queries

# 3. Update SQLModel classes (7 files)
# Edit backend/app/models/catalog.py - TenantSettings
# Edit backend/app/models/fulfillment.py - Job, InvoiceLine, JobExpense
# Edit backend/app/models/quoting.py - Quote, QuoteLine, ChangeOrder, ChangeOrderLine
# Edit backend/app/models/system.py - 8 models
# Edit backend/app/models/billing.py - 3 models
# Edit backend/app/models/voice_ai.py - VoiceCommandLog
# Add Field(default=...) for all 35+ fields

# 4. Generate migration
alembic revision --autogenerate -m "phase_4_7_add_missing_default_values_task5"

# 5. ⚠️ CRITICAL: Review migration file
# Open backend/migrations/versions/[timestamp]_phase_4_7_add_missing_default_values_task5.py
# Search for 'audit' and 'event'
# DELETE any op.create_table('event', ... schema='audit') blocks
# Verify all 35+ ALTER COLUMN ... SET DEFAULT statements present
# Add pre-migration validation queries as comments

# 6. Apply migration
alembic upgrade head

# 7. Create test suite
# Create backend/tests/test_phase_4_7_default_values.py
# - Use db_session: Session parameter
# - Use select() with exec()
# - Test all 35+ defaults

# 8. Run new tests
pytest tests/test_phase_4_7_default_values.py -v
# All new tests should pass

# 9. Regression check - Ensure no breaks
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [602 + X] passed

pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [629 + X] passed

# 10. Rollback test - Verify downgrade works
alembic downgrade -1
alembic upgrade head
pytest tests/ -v  # Should still pass

# 11. Update docs
# Edit dev-docs/analysis/phase-4.7-db-schema-sync-3-plan.md
# Mark task as complete with test results
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 602/602 unit and 629/629 total baselines?
2. Have I identified all 35+ fields that need defaults?
3. Do I understand which models need to be updated (7 files)?
4. Have I validated existing data has no NULLs where defaults will be set?

**During implementation:**
1. Am I using `db_session` parameter (NOT `session`) in tests?
2. Am I using `select()/exec()` pattern (NOT `query()`) in tests?
3. After running `alembic revision --autogenerate`, did I check for and remove `audit.event` table creation?
4. Have I verified all 35+ ALTER COLUMN ... SET DEFAULT statements are in the migration?
5. Are my tests comprehensive (one test per default minimum)?

**After implementation:**
1. Do I have 100% test pass rate on BOTH unit tests (602+X) and total tests (629+X)?
2. Did baseline increase by exactly the tests I added?
3. Have I verified all defaults exist via information_schema query?
4. Have I updated the project plan document?
5. Have I tested migration rollback (`alembic downgrade -1`)?

---

**Ready to Begin!** 🚀

### MIGRATION Task Checklist (This Task):
1. ✅ Capture baseline (602/602 unit, 629/629 total)
2. 🔍 Validate existing data (no NULLs where defaults required)
3. 🛠️ Update 7 SQLModel files with Field(default=...)
4. 📝 Generate migration (`alembic revision --autogenerate`)
5. ⚠️ **CRITICAL: Remove `audit.event` table from migration if present**
6. ✅ Apply migration (`alembic upgrade head`)
7. 🧪 Create comprehensive tests (35+ tests for 35+ defaults)
8. 🔄 Run regression tests (602+X unit, 629+X total)
9. ↩️ Test rollback (`alembic downgrade -1`, then `upgrade head`)
10. 📚 Update project plan

Remember: Phase 4.7 Task 5 is about **database-level fail-safes** - adding defaults ensures data consistency even when application code fails. This is a safety enhancement with low risk and high value for production deployment!
