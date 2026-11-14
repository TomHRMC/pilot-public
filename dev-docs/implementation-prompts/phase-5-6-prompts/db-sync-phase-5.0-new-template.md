# Task [TASK_NUMBER]: [TASK_NAME]

**Reference:** `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` - Task [TASK_NUMBER]
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/required-defaults-columns-json.md` - **Authoritative Checklist (200 fields)**
- Current Live Database (Phase 4.9 Post-State)
**Type:** Phase 5.0 - Server Defaults Enforcement
**Priority:** CRITICAL
**Change Type:** SYSTEMATIC MODEL UPDATE + MIGRATION

---

## Context

This is **Phase 5.0 - DB Sync v#6**, the most extensive synchronization phase yet. A comprehensive forensic comparison revealed a systematic architectural bug: **200 database columns** defined with defaults in the Golden Master JSON lack PostgreSQL DEFAULT clauses.

**Root Cause:** Python SQLModel definitions used Pydantic-level `default=...` instead of SQLAlchemy-level `server_default=...`, meaning defaults exist only in Python memory, not at the database layer.

**Critical Impact:**
- **Runtime Errors:** Direct SQL inserts (migrations, background jobs, admin scripts) fail with NOT NULL violations
- **Data Integrity Risk:** Application-level defaults are not enforced by the database
- **Schema Drift:** Database constraints don't match the Golden Master specification
- **Integration Failures:** External systems writing directly to the database may violate constraints

**Scope:** **200 fields across 78 tables** - This requires systematic, checklist-driven execution.

**Key Principle:** Every field in `required-defaults-columns-json.md` MUST be addressed. This is the single source of truth. No field can be skipped.

---

## What Was Completed in Previous Phases

**Phase 4.5 Status:** ✅ COMPLETE (March 30 - April 1, 2026)
- ✅ 100% alignment between physical database and Golden Master JSON achieved
- ✅ All unique, check, and temporal exclusion constraints implemented

**Phase 4.6 Status:** ✅ COMPLETE (April 1-2, 2026)
- ✅ 602/602 total tests passing (100%)
- ✅ Dual-master reconciliation completed

**Phase 4.7 Status:** ✅ COMPLETE (April 3-7, 2026)
- ✅ 636/636 total tests passing (100%)
- ✅ ENUM standardization completed (all TEXT + CHECK)

**Phase 4.8 Status:** ✅ COMPLETE (April 8, 2026)
- ✅ 658/658 total tests passing (100%)
- ✅ 18+ composite performance indexes added

**Phase 4.9 Status:** ✅ COMPLETE (April 8-9, 2026)
- ✅ 640/640 unit tests, 667/667 total tests passing (100%)
- ✅ CHECK constraint value alignment completed

**Current Baseline:** 640/640 unit tests, 667/667 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-4.9-db-schema-sync-5-plan.md` for Phase 4.9 history

---

## Current Task: [TASK_NAME]

**Effort:** [EFFORT_ESTIMATE]
**Gap Reference:** Phase 5.0 Analysis - The "Sweeping Missing Defaults Bug"
**Change Type:** [MODEL UPDATE | MIGRATION + MANUAL VERIFICATION | TESTING]

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

**Record the output of both results:** `640/640 & 667/667 tests passing` (Phase 5.0 baseline - starting from Phase 4.9 completion)

### Step 3: Document Your Baseline

**Write down both of these numbers before proceeding**

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## ⚠️ CRITICAL: Phase 5.0 Specific Warnings

**BEFORE writing ANY code, review these Phase 5.0 critical issues:**

### 1. The Authoritative Checklist is Your Bible

**File:** `dev-docs/db-design/required-defaults-columns-json.md`

**Contains:** Exactly 200 fields that MUST have `server_default=` added.

**Critical Rule:** Every field in this checklist MUST be addressed. No exceptions. No shortcuts.

**Workflow:**
```markdown
1. Open required-defaults-columns-json.md in a side panel
2. For each table, count the fields listed
3. As you update each field in the Python model, mentally check it off
4. Verify all fields for a table are complete before moving to next table
5. At the end, verify you've touched 200 fields total
```

**Common Mistake:** Assuming similar fields have the same default. Don't assume - check the checklist for EACH field.

---

### 2. Alembic Will Fail You - Manual Verification is MANDATORY

**Reality Check:** Alembic's `revision --autogenerate` is **notoriously unreliable** for detecting `server_default` additions on existing columns.

**Expected Behavior:**
- Alembic works well for NEW tables
- Alembic often **completely ignores** server_default changes on existing columns
- You should expect Alembic to miss **50-100+ fields** (25-50% of the 200)

**MANDATORY Process:**
```bash
# After alembic revision --autogenerate:
1. Open the generated migration file
2. Open required-defaults-columns-json.md side-by-side
3. For EACH table in the checklist:
   - Count fields in checklist for that table
   - Search migration file for op.alter_column() calls for that table
   - If counts DON'T MATCH → Manually write the missing op.alter_column() calls
4. Continue until all 200 fields are accounted for in the migration
```

**If You Skip This:** The migration will apply successfully, but many fields won't have defaults at the database layer. Tests will pass (Python defaults work), but direct SQL operations will fail in production.

---

### 3. String Literals Require Inner Quotes in text()

❌ **WRONG (Will Fail at Runtime):**
```python
from sqlalchemy import Column, String, text

status: str = Field(
    default="pending",
    sa_column=Column(String, server_default=text("pending"), nullable=False)
)
# ERROR: PostgreSQL interprets "pending" as a column name, not a string literal
```

✅ **CORRECT (Quotes Inside text()):**
```python
from sqlalchemy import Column, String, text

status: str = Field(
    default="pending",
    sa_column=Column(String, server_default=text("'pending'"), nullable=False)
)
# CORRECT: Single quotes INSIDE text() make it a string literal
```

**Why:** PostgreSQL requires string literals to be wrapped in single quotes. Without them, it treats the value as a column name or identifier.

**Pattern for All Strings:**
- `text("'email'")` for email
- `text("'pending'")` for pending
- `text("'US'")` for US
- `text("'USD'")` for USD

---

### 4. Keep Both Python AND Database Defaults

❌ **WRONG (Removes Python-Level Default):**
```python
# Before:
is_active: bool = Field(default=True, nullable=False)

# WRONG "fix":
is_active: bool = Field(
    # default=True,  ← DON'T DELETE THIS!
    sa_column=Column(Boolean, server_default=text("true"), nullable=False)
)
```

✅ **CORRECT (Keep Both Layers):**
```python
# Before:
is_active: bool = Field(default=True, nullable=False)

# CORRECT fix:
is_active: bool = Field(
    default=True,  # ← KEEP for Python-level compatibility
    sa_column=Column(Boolean, server_default=text("true"), nullable=False)
)
```

**Why:** We need defaults at BOTH layers:
- **Python default:** For ORM operations (application code)
- **Database default:** For direct SQL operations (migrations, admin scripts, external systems)

---

### 5. JSONB Requires ::jsonb Cast

❌ **WRONG (PostgreSQL Won't Recognize as JSONB):**
```python
permissions: dict = Field(
    default_factory=dict,
    sa_column=Column(JSONB, server_default=text("{}"), nullable=False)
)
```

✅ **CORRECT (Explicit Cast Required):**
```python
from sqlalchemy.dialects.postgresql import JSONB

permissions: dict = Field(
    default_factory=dict,
    sa_column=Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
)
# Note: '{}'::jsonb is PostgreSQL syntax for "cast {} to JSONB type"
```

**Why:** PostgreSQL needs explicit type casting for JSONB literals to distinguish them from plain text.

---

### 6. Use func.now() for DateTime, NOT text("now()")

❌ **WRONG (Creates String, Not Timestamp):**
```python
occurred_at: datetime = Field(
    default_factory=datetime.utcnow,
    sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
)
```

✅ **CORRECT (Use SQLAlchemy func.now()):**
```python
from sqlalchemy import Column, DateTime, func

occurred_at: datetime = Field(
    default_factory=datetime.utcnow,
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
)
```

**Why:** `func.now()` generates proper SQL function call. `text("now()")` creates a string literal, which PostgreSQL might misinterpret.

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
    op.alter_column(...)  # Your actual server_default additions
```

**Action After `alembic revision --autogenerate`:**
1. Open the generated migration file
2. Search for `'event'` and `schema='audit'`
3. **DELETE any `op.create_table('event', ... schema='audit')` statements**
4. **DELETE any `op.drop_table('event', ... schema='audit')` statements**
5. Verify your server_default changes are still present
6. Only then run `alembic upgrade head`

---

## Requirements

### Task 1: SQLModel Architecture - Systematic Server Default Implementation

**Effort:** 2.0 days
**Scope:** 200 fields across 78 tables

#### What This Task Accomplishes

Transform all Python models to use SQLAlchemy-level `server_default=` in addition to Pydantic-level `default=`, ensuring database-layer enforcement of default values for direct SQL operations.

#### Implementation Strategy

**File Processing Order (Dependency-Based):**
1. `backend/app/models/auth.py` - Authentication & authorization (~25 fields)
2. `backend/app/models/core.py` - Tenant, user, customer (~35 fields)
3. `backend/app/models/crm.py` - Contact, address (~20 fields)
4. `backend/app/models/quoting.py` - Quote, lines (~25 fields)
5. `backend/app/models/fulfillment.py` - Job, invoice (~40 fields)
6. `backend/app/models/catalog.py` - Products, pricing (~15 fields)
7. `backend/app/models/billing.py` - Subscriptions (~20 fields)
8. `backend/app/models/system.py` - Notifications, webhooks (~15 fields)
9. `backend/app/models/ai.py` - Voice AI (~5 fields)

**Per-File Workflow:**
```markdown
1. Open model file (e.g., auth.py)
2. Open required-defaults-columns-json.md side-by-side
3. Find all tables from that model file in the checklist
4. For each field listed:
   a. Locate Field() definition in Python model
   b. Identify data type (Boolean, Integer, String, JSONB, DateTime, tstzrange)
   c. Apply correct sa_column=Column(..., server_default=...) pattern
   d. Keep existing default= or default_factory=
   e. Verify nullable=False is set correctly
5. Add necessary imports at top of file
6. Save and move to next model file
```

#### Server Default Syntax Reference (By Data Type)

**Boolean Defaults:**
```python
from sqlalchemy import Column, Boolean, text

# TRUE default
is_active: bool = Field(
    default=True,
    sa_column=Column(Boolean, server_default=text("true"), nullable=False)
)

# FALSE default
is_default: bool = Field(
    default=False,
    sa_column=Column(Boolean, server_default=text("false"), nullable=False)
)
```

**Integer Defaults:**
```python
from sqlalchemy import Column, Integer, text

# Zero default
failed_login_count: int = Field(
    default=0,
    sa_column=Column(Integer, server_default=text("0"), nullable=False)
)

# Non-zero default
quantity: int = Field(
    default=1,
    sa_column=Column(Integer, server_default=text("1"), nullable=False)
)

# Large value default
default_labor_rate_cents: int = Field(
    default=8500,
    sa_column=Column(Integer, server_default=text("8500"), nullable=False)
)
```

**String/Text Defaults:**
```python
from sqlalchemy import Column, String, text

# CRITICAL: Single quotes INSIDE text() for string literals
status: str = Field(
    default="pending",
    sa_column=Column(String, server_default=text("'pending'"), nullable=False)
)

preferred_mfa_channel: str = Field(
    default="email",
    sa_column=Column(String, server_default=text("'email'"), nullable=False)
)

country: str = Field(
    default="US",
    sa_column=Column(String, server_default=text("'US'"), nullable=False)
)
```

**JSONB Defaults (Empty Object):**
```python
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB

# CRITICAL: Use '{}'::jsonb cast for JSONB literals
permissions: dict = Field(
    default_factory=dict,
    sa_column=Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
)

# Alternative: default={} instead of default_factory=dict
preferences: dict = Field(
    default={},
    sa_column=Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
)
```

**DateTime (Timestamp with Timezone) Defaults:**
```python
from sqlalchemy import Column, DateTime, func

# CRITICAL: Use func.now() NOT text("now()")
occurred_at: datetime = Field(
    default_factory=datetime.utcnow,
    sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
)

# Alternative: use sa_column_kwargs
started_at: datetime = Field(
    default_factory=datetime.utcnow,
    sa_column_kwargs={
        "server_default": func.now(),
        "nullable": False
    }
)
```

**tstzrange (PostgreSQL Range Type) Defaults:**
```python
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import TSTZRANGE

# Open-ended range starting now
valid_period: str = Field(
    default=None,
    sa_column=Column(
        TSTZRANGE, 
        server_default=text("tstzrange(now(), null, '[)')"), 
        nullable=False
    )
)
```

#### Required Import Statements

Add these at the top of each model file if not already present:

```python
# Standard library
from datetime import datetime
from typing import Optional, List

# SQLAlchemy imports for server defaults
from sqlalchemy import Column, Boolean, Integer, String, DateTime, text, func
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE

# SQLModel imports (existing)
from sqlmodel import Field, SQLModel, Relationship
```

#### Checklist-Driven Verification

**For Each Table:**
```markdown
Table: tenant
Checklist shows 1 field: is_active (Boolean, default: true)

✓ Located: class Tenant(SQLModel, table=True)
✓ Found field: is_active: bool = Field(default=True, nullable=False)
✓ Updated to: is_active: bool = Field(
    default=True,
    sa_column=Column(Boolean, server_default=text("true"), nullable=False)
  )
✓ Verified: Kept default=True for Python layer
✓ Verified: Added server_default for database layer
✓ Checked off in mental checklist

Move to next table...
```

**Success Criteria for Task 1:**
- [ ] All 200 fields from checklist have `server_default=` implemented
- [ ] Every field uses correct syntax for its data type
- [ ] All model files have necessary SQLAlchemy imports
- [ ] Python-level defaults remain intact
- [ ] No typos in server_default text literals
- [ ] Code passes Python syntax validation (`python -c "from app.models import *"`)

---

### Task 2: Alembic Migration Generation with Manual Verification

**Effort:** 1.0 days
**Dependencies:** Task 1 must be 100% complete

#### What This Task Accomplishes

Generate Alembic migration to apply all 200 server defaults to the physical database, with mandatory manual verification to add any op.alter_column() calls that Alembic autogenerate missed.

#### Critical Understanding: Alembic Will Miss Many Fields

**Reality:** Alembic's autogenerate is excellent for new tables but terrible for detecting server_default additions on existing columns. Budget 4-6 hours for manual verification and addition of missing fields.

#### Step-by-Step Implementation

**Step 1: Generate Initial Migration**

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "phase_5_0_add_server_defaults_200_fields"
```

**Step 2: Initial Review**

Open the generated migration file and perform quick assessment:
```bash
# Count op.alter_column calls in upgrade()
grep -c "op.alter_column" backend/migrations/versions/<migration_file>.py

# Compare to expected: 200
# If less than 150, expect heavy manual work
```

**Step 3: Systematic Verification Against Checklist**

**MANDATORY PROCESS (Cannot Skip):**

```markdown
1. Open generated migration file in editor
2. Open required-defaults-columns-json.md side-by-side
3. Create a verification spreadsheet or checklist:

Table Name | Expected Fields | Found in Migration | Missing Count | Status
-----------|-----------------|-------------------|---------------|--------
tenant     | 1               | ?                 | ?             | [ ]
tenant_settings | 4          | ?                 | ?             | [ ]
platform_role | 3            | ?                 | ?             | [ ]
...

4. For each table in checklist:
   a. Count fields listed (e.g., tenant_settings has 4 fields)
   b. Search migration for "op.alter_column('tenant_settings'"
   c. Count matches
   d. If mismatch → Add to "Missing" list
   
5. For each missing field, manually write op.alter_column()
```

**Step 4: Manual op.alter_column() Syntax Reference**

**Boolean Fields:**
```python
# In upgrade()
op.alter_column('tenant', 'is_active',
    existing_type=sa.Boolean(),
    server_default=sa.text('true'),
    existing_nullable=False)

# In downgrade()
op.alter_column('tenant', 'is_active',
    existing_type=sa.Boolean(),
    server_default=None,
    existing_nullable=False)
```

**Integer Fields:**
```python
# In upgrade()
op.alter_column('tenant_settings', 'default_labor_rate_cents',
    existing_type=sa.Integer(),
    server_default=sa.text('8500'),
    existing_nullable=False)

# In downgrade()
op.alter_column('tenant_settings', 'default_labor_rate_cents',
    existing_type=sa.Integer(),
    server_default=None,
    existing_nullable=False)
```

**String Fields:**
```python
# In upgrade()
op.alter_column('user', 'preferred_mfa_channel',
    existing_type=sa.String(),
    server_default=sa.text("'email'"),  # Note: quotes inside text()
    existing_nullable=False)

# In downgrade()
op.alter_column('user', 'preferred_mfa_channel',
    existing_type=sa.String(),
    server_default=None,
    existing_nullable=False)
```

**JSONB Fields:**
```python
# In upgrade()
op.alter_column('platform_role', 'permissions',
    existing_type=postgresql.JSONB(),
    server_default=sa.text("'{}'::jsonb"),  # Note: ::jsonb cast
    existing_nullable=False)

# In downgrade()
op.alter_column('platform_role', 'permissions',
    existing_type=postgresql.JSONB(),
    server_default=None,
    existing_nullable=False)
```

**DateTime Fields:**
```python
# In upgrade()
op.alter_column('notification_event', 'occurred_at',
    existing_type=postgresql.TIMESTAMP(timezone=True),
    server_default=sa.func.now(),  # Note: func.now() not text()
    existing_nullable=False)

# In downgrade()
op.alter_column('notification_event', 'occurred_at',
    existing_type=postgresql.TIMESTAMP(timezone=True),
    server_default=None,
    existing_nullable=False)
```

**Step 5: Migration File Organization**

Given the scale (200 fields), organize the migration clearly:

```python
"""phase_5_0_add_server_defaults_200_fields

Revision ID: <hash>
Revises: <previous_hash>
Create Date: 2026-04-09

Description:
Systematic fix for "Sweeping Missing Defaults Bug" - adds server_default to
200 fields across 78 tables to align physical database with Golden Master JSON.

Reference:
- Analysis: dev-docs/analysis/phase-5.0-db-schema-sync-6-analysis.md
- Checklist: dev-docs/db-design/required-defaults-columns-json.md
- Plan: dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # =====================================================
    # AUTH MODELS (backend/app/models/auth.py)
    # =====================================================
    
    # Table: platform_role (3 fields)
    op.alter_column('platform_role', 'permissions',
        existing_type=postgresql.JSONB(),
        server_default=sa.text("'{}'::jsonb"),
        existing_nullable=False)
    op.alter_column('platform_role', 'is_default',
        existing_type=sa.Boolean(),
        server_default=sa.text('false'),
        existing_nullable=False)
    op.alter_column('platform_role', 'is_active',
        existing_type=sa.Boolean(),
        server_default=sa.text('true'),
        existing_nullable=False)
    
    # Table: user (7 fields)
    op.alter_column('user', 'is_platform_user',
        existing_type=sa.Boolean(),
        server_default=sa.text('false'),
        existing_nullable=False)
    # ... continue for all fields ...
    
    # =====================================================
    # CORE MODELS (backend/app/models/core.py)
    # =====================================================
    
    # Table: tenant (1 field)
    op.alter_column('tenant', 'is_active',
        existing_type=sa.Boolean(),
        server_default=sa.text('true'),
        existing_nullable=False)
    
    # ... continue for all 78 tables ...


def downgrade():
    # Mirror structure: remove all server_default values
    # Process in REVERSE order of upgrade() for safety
    
    # CORE MODELS (reverse order)
    op.alter_column('tenant', 'is_active',
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False)
    
    # ... continue in reverse ...
```

**Step 6: Check for audit.event Table (MANDATORY)**

```bash
# Search the migration file
grep -n "audit" backend/migrations/versions/<migration_file>.py
grep -n "'event'" backend/migrations/versions/<migration_file>.py

# If found, DELETE those lines:
# - Any op.create_table('event', ... schema='audit')
# - Any op.drop_table('event', ... schema='audit')
# - Any index/constraint operations on audit.event
```

**Step 7: Migration Testing**

```bash
# Test forward migration
alembic upgrade head

# Verify server defaults applied (spot check)
# Use postgres-local MCP server to query:
SELECT 
    table_name, 
    column_name, 
    column_default
FROM information_schema.columns
WHERE table_name IN ('tenant', 'user', 'quote')
  AND column_name IN ('is_active', 'failed_login_count', 'currency')
ORDER BY table_name, column_name;

# Test backward migration (rollback)
alembic downgrade -1

# Verify defaults removed
# Run same query above, should show NULL for column_default

# Re-apply for continued work
alembic upgrade head
```

**Success Criteria for Task 2:**
- [ ] Migration file generated
- [ ] Systematic verification completed against checklist
- [ ] All 200 fields have op.alter_column() in upgrade()
- [ ] All 200 fields have op.alter_column(..., server_default=None) in downgrade()
- [ ] No audit.event table operations present
- [ ] Migration runs successfully forward
- [ ] Migration runs successfully backward
- [ ] Database verification confirms defaults applied

---

### Task 3: Comprehensive Testing & Verification

**Effort:** 1.0 days
**Dependencies:** Tasks 1 & 2 must be complete

#### What This Task Accomplishes

Validate that all 200 server defaults are enforced at the PostgreSQL layer (not just Python layer) using raw SQL tests that bypass the ORM.

#### Testing Strategy

Unlike previous phases, we don't need extensive unit tests for each field. Instead, focus on:
1. **Database-layer verification** - Raw SQL INSERT without values (defaults should apply)
2. **information_schema validation** - Confirm all 200 fields have non-NULL column_default
3. **Regression testing** - Ensure existing tests still pass

#### Test File Structure

**File:** `backend/tests/test_phase_5_0_server_defaults_verification.py`

**Test 1: Database-Layer Default Enforcement**
```python
"""
Test Suite: Phase 5.0 - Server Defaults Verification
Validates that defaults are enforced at PostgreSQL layer via raw SQL

Reference: phase-5.0-db-schema-sync-6-plan.md
"""
import pytest
from sqlalchemy import text
from datetime import datetime, timezone


class TestServerDefaultsEnforcedAtDatabaseLayer:
    """Verify server defaults work via raw SQL (bypassing Python ORM)"""
    
    def test_boolean_defaults_at_db_layer(self, db_session):
        """Test Boolean server defaults via raw SQL INSERT"""
        # Test: tenant.is_active defaults to TRUE
        db_session.execute(text("""
            INSERT INTO tenant (tenant_name, default_timezone)
            VALUES ('Test Tenant Bool', 'America/New_York')
            RETURNING id, is_active
        """))
        
        result = db_session.execute(text("""
            SELECT is_active FROM tenant 
            WHERE tenant_name = 'Test Tenant Bool'
        """)).fetchone()
        
        assert result[0] is True, "is_active should default to TRUE"
        db_session.rollback()
    
    def test_integer_defaults_at_db_layer(self, db_session):
        """Test Integer server defaults via raw SQL INSERT"""
        # Setup: Create tenant first
        tenant_id = db_session.execute(text("""
            INSERT INTO tenant (tenant_name, default_timezone)
            VALUES ('Test Tenant Int', 'America/New_York')
            RETURNING id
        """)).fetchone()[0]
        
        # Test: tenant_settings.default_labor_rate_cents defaults to 8500
        db_session.execute(text(f"""
            INSERT INTO tenant_settings (tenant_id)
            VALUES ({tenant_id})
        """))
        
        result = db_session.execute(text(f"""
            SELECT default_labor_rate_cents 
            FROM tenant_settings 
            WHERE tenant_id = {tenant_id}
        """)).fetchone()
        
        assert result[0] == 8500, "default_labor_rate_cents should default to 8500"
        db_session.rollback()
    
    def test_string_defaults_at_db_layer(self, db_session):
        """Test String server defaults via raw SQL INSERT"""
        # Test: address.country defaults to 'US'
        # (Requires more setup - customer, site relationships)
        # Simplified test for demonstration
        pass
    
    def test_jsonb_defaults_at_db_layer(self, db_session):
        """Test JSONB server defaults via raw SQL INSERT"""
        # Test: platform_role.permissions defaults to {}
        db_session.execute(text("""
            INSERT INTO platform_role (role_name, role_description)
            VALUES ('Test Role JSONB', 'Testing JSONB defaults')
        """))
        
        result = db_session.execute(text("""
            SELECT permissions FROM platform_role 
            WHERE role_name = 'Test Role JSONB'
        """)).fetchone()
        
        assert result[0] == {}, "permissions should default to empty object"
        db_session.rollback()
    
    def test_datetime_defaults_at_db_layer(self, db_session):
        """Test DateTime server defaults via raw SQL INSERT"""
        before_insert = datetime.now(timezone.utc)
        
        # Setup: Create notification_type
        type_id = db_session.execute(text("""
            INSERT INTO notification_type (type_name, channel)
            VALUES ('test_type_dt', 'email')
            RETURNING id
        """)).fetchone()[0]
        
        # Test: notification_event.occurred_at defaults to now()
        db_session.execute(text(f"""
            INSERT INTO notification_event (notification_type_id, tenant_id)
            VALUES ({type_id}, 1)
        """))
        
        result = db_session.execute(text(f"""
            SELECT occurred_at FROM notification_event 
            WHERE notification_type_id = {type_id}
        """)).fetchone()
        
        after_insert = datetime.now(timezone.utc)
        occurred_at = result[0]
        
        assert before_insert <= occurred_at <= after_insert, \
            "occurred_at should default to current timestamp"
        
        db_session.rollback()


class TestAllFieldsHaveServerDefaults:
    """Comprehensive check: All 200 fields have server defaults"""
    
    def test_all_200_fields_via_information_schema(self, db_session):
        """Query information_schema to verify all 200 fields have defaults"""
        
        # Load expected fields from checklist
        # (Could parse required-defaults-columns-json.md or hardcode)
        expected_defaults = [
            ('tenant', 'is_active'),
            ('tenant_settings', 'default_labor_rate_cents'),
            ('tenant_settings', 'default_billable_labor_rate_cents'),
            ('tenant_settings', 'default_quote_validity_days'),
            ('tenant_settings', 'default_invoice_terms_days'),
            # ... all 200 fields from checklist
        ]
        
        missing_defaults = []
        
        for table_name, column_name in expected_defaults:
            result = db_session.execute(text(f"""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                  AND column_name = '{column_name}'
            """)).fetchone()
            
            if result is None:
                missing_defaults.append(f"{table_name}.{column_name} (column not found)")
            elif result[0] is None:
                missing_defaults.append(f"{table_name}.{column_name} (no default)")
        
        assert len(missing_defaults) == 0, \
            f"Found {len(missing_defaults)} fields without server defaults:\n" + \
            "\n".join(missing_defaults[:10])  # Show first 10 for debugging
```

**SQL Verification Queries (Run Via MCP Server):**

```sql
-- Query 1: Count fields with server defaults
-- (Adjust to include all 200 fields from checklist)
SELECT COUNT(*) AS fields_with_defaults
FROM information_schema.columns
WHERE (table_name = 'tenant' AND column_name = 'is_active')
   OR (table_name = 'tenant_settings' AND column_name = 'default_labor_rate_cents')
   -- ... repeat for all 200 fields ...
   AND column_default IS NOT NULL;
-- Expected: 200

-- Query 2: Sample defaults verification
SELECT 
    table_name, 
    column_name, 
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('tenant', 'user', 'quote', 'invoice')
  AND column_name IN ('is_active', 'failed_login_count', 'currency', 'status')
ORDER BY table_name, column_name;

-- Query 3: Find NOT NULL columns without defaults (should be minimal)
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND is_nullable = 'NO'
  AND column_default IS NULL
  AND column_name NOT LIKE '%_id'  -- Exclude FKs
  AND column_name != 'id'  -- Exclude PKs
ORDER BY table_name, column_name;
```

**Success Criteria for Task 3:**
- [ ] Test file created: test_phase_5_0_server_defaults_verification.py
- [ ] Tests validate defaults at database layer (raw SQL)
- [ ] Tests cover all data types (Boolean, Integer, String, JSONB, DateTime)
- [ ] information_schema check verifies all 200 fields
- [ ] Full test suite passes: 643+/643+ unit, 670+/670+ total (100%)
- [ ] No regressions in existing tests

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite

```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 643+ passed (640 baseline + 3 new)

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 670+ passed (667 baseline + 3 new)
```

### Step 2: Verify Database State

```bash
# Run comprehensive SQL verification
# Use postgres-local MCP server to execute queries from Task 3
```

### Step 3: Final Validation

**If ANY tests fail:**
1. Identify failing tests
2. Check if syntax errors in server_default (missing quotes, wrong cast)
3. Verify migration applied all 200 fields
4. Fix and re-run until 100% pass rate

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md`

Find Task [TASK_NUMBER] and update with:

```markdown
### Task [TASK_NUMBER]: [TASK_NAME]

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_DAYS] days (actual)
**Priority:** CRITICAL

**Implementation Summary:**

- Model Updates: All 200 fields updated across 9 model files
- Migration: [`YYYY_MM_DD_HHMM-[hash]_phase_5_0_add_server_defaults_200_fields.py`]
- Alembic Manual Additions: [NUMBER] fields added manually (Alembic missed them)
- Test Suite: [`test_phase_5_0_server_defaults_verification.py`] - 3+ tests ✅
- Final Results: 643/643 unit tests (100%), 670/670 total tests (100%)

**Key Changes:**
- ✅ All 200 fields have server_default= at database layer
- ✅ Database state matches Golden Master JSON specification
- ✅ Direct SQL inserts now work correctly with defaults
- ✅ Zero regressions in existing test suite

**Verification:**
- All 200 fields verified via information_schema query
- Raw SQL INSERT tests confirm defaults applied at database layer
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### For ALL Phase 5.0 Tasks:
- [ ] **Regression baseline captured** (640/640 unit, 667/667 total)
- [ ] **All 200 fields from checklist addressed**
- [ ] **Every field uses correct server_default syntax for its data type**
- [ ] **Python-level defaults remain intact (both layers working)**
- [ ] **Alembic migration generated and MANUALLY VERIFIED**
- [ ] **All missing op.alter_column() calls added manually**
- [ ] **⚠️ CRITICAL: audit.event table removed from migration**
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **Verification tests written and passing**
- [ ] **ALL 640 existing unit tests still passing**
- [ ] **ALL 667 total tests still passing**
- [ ] **New total: 643/643 unit, 670/670 total (100%)**
- [ ] **information_schema confirms 200 fields have defaults**
- [ ] **Migration rollback tested** (`alembic downgrade -1`)
- [ ] **Project plan document updated**

### Task-Specific Validation:

**Task 1 (Model Updates):**
- [ ] All model files updated with server_default=
- [ ] Correct syntax for Boolean, Integer, String, JSONB, DateTime, tstzrange
- [ ] All imports added
- [ ] Python syntax valid (`python -c "from app.models import *"`)

**Task 2 (Migration):**
- [ ] Migration file generated
- [ ] Manual verification completed against checklist
- [ ] All 200 fields accounted for in migration
- [ ] Migration runs forward successfully
- [ ] Migration runs backward successfully

**Task 3 (Testing):**
- [ ] Raw SQL tests validate database-layer defaults
- [ ] information_schema check passes for all 200 fields
- [ ] Full regression suite passes

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` - **Master Plan** ⭐
- `dev-docs/analysis/phase-5.0-db-schema-sync-6-analysis.md` - Forensic Analysis
- `dev-docs/db-design/required-defaults-columns-json.md` - **Authoritative Checklist (200 fields)** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Backend Models
- `backend/app/models/auth.py`
- `backend/app/models/core.py`
- `backend/app/models/crm.py`
- `backend/app/models/quoting.py`
- `backend/app/models/fulfillment.py`
- `backend/app/models/catalog.py`
- `backend/app/models/billing.py`
- `backend/app/models/system.py`
- `backend/app/models/ai.py`

---

## Risk Assessment

**For Phase 5.0:**
- **Data Loss Risk:** NONE (only adding defaults, not modifying data)
- **Syntax Error Risk:** MEDIUM (easy to make typos in 200 fields)
- **Alembic Miss Risk:** HIGH (will miss 50-100+ fields)
- **Regression Risk:** LOW (additive changes, no breaking modifications)
- **Migration Failure Risk:** LOW (additive schema changes)
- **Rollback Complexity:** LOW (simple server_default removal)
- **Performance Impact:** NONE (defaults only affect INSERT, not queries)
- **Mitigation:** Systematic checklist process, manual verification, comprehensive testing

---

## Notes

### Important Patterns to Follow
- **Checklist is Law:** Every field in required-defaults-columns-json.md MUST be addressed
- **Manual Verification Required:** Alembic WILL miss fields - budget time for manual addition
- **Both Layers:** Keep both Python default= AND database server_default=
- **String Quotes:** `text("'value'")` not `text("value")` for strings
- **JSONB Cast:** `text("'{}'::jsonb")` not `text("{}")`for JSONB
- **DateTime func:** Use `func.now()` not `text("now()")` for timestamps
- **Zero Regression:** All 640 unit + 667 total tests MUST pass

### Phase 5.0 Specific
- **Largest sync phase yet:** 200 fields across 78 tables
- **Systematic execution:** Process files in dependency order
- **Alembic limitation:** Expect to add 50-100+ op.alter_column() manually
- **Database-first:** Defaults at PostgreSQL layer, not just Python
- **Safety operations:** Direct SQL inserts will now work correctly

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 5.0 plan for syntax reference
- Check checklist line-by-line if unsure about a field
- Search model files for similar field patterns
- Verify migration with information_schema queries
- Ask for help if spending >1 hour on single issue

---

## Example Task Flow

### For Phase 5.0 Task 1 (Model Updates):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 640 passed

# 2. Open checklist
# Open required-defaults-columns-json.md in side panel

# 3. Process first model file (auth.py)
# Edit backend/app/models/auth.py
# Find all tables from auth.py in checklist:
#   - platform_role (3 fields: permissions, is_default, is_active)
#   - user (7 fields: is_platform_user, failed_login_count, ...)
#   - user_endpoint (4 fields: is_primary, verification_status, ...)
#   - ... etc

# For each field, apply correct pattern:
# Boolean → sa_column=Column(Boolean, server_default=text("true/false"))
# Integer → sa_column=Column(Integer, server_default=text("0"))
# String → sa_column=Column(String, server_default=text("'value'"))
# JSONB → sa_column=Column(JSONB, server_default=text("'{}'::jsonb"))
# DateTime → sa_column=Column(DateTime(timezone=True), server_default=func.now())

# 4. Add imports at top of auth.py
from sqlalchemy import Column, Boolean, Integer, String, DateTime, text, func
from sqlalchemy.dialects.postgresql import JSONB

# 5. Verify syntax
python -c "from app.models.auth import *"

# 6. Move to next file (core.py) and repeat

# 7. After all 9 model files complete, verify
python -c "from app.models import *"
# Should load without errors
```

### For Phase 5.0 Task 2 (Migration):

```bash
# 1. Generate migration
alembic revision --autogenerate -m "phase_5_0_add_server_defaults_200_fields"

# 2. Open migration file
# Location: backend/migrations/versions/2026_04_09_<hash>_phase_5_0_add_server_defaults_200_fields.py

# 3. Check for audit.event (MANDATORY)
grep -n "audit" backend/migrations/versions/<file>
grep -n "'event'" backend/migrations/versions/<file>
# If found, DELETE those lines

# 4. Count op.alter_column calls
grep -c "op.alter_column" backend/migrations/versions/<file>
# If < 150, prepare for heavy manual work

# 5. Systematic verification
# Open required-defaults-columns-json.md side-by-side
# For each table:
#   - Count expected fields in checklist
#   - Search migration for that table
#   - If missing, add op.alter_column() manually

# 6. Example manual addition:
# Missing: tenant.is_active
# Add to upgrade():
op.alter_column('tenant', 'is_active',
    existing_type=sa.Boolean(),
    server_default=sa.text('true'),
    existing_nullable=False)
# Add to downgrade():
op.alter_column('tenant', 'is_active',
    existing_type=sa.Boolean(),
    server_default=None,
    existing_nullable=False)

# 7. Apply migration
alembic upgrade head

# 8. Verify (via MCP server)
SELECT column_name, column_default 
FROM information_schema.columns 
WHERE table_name = 'tenant';

# 9. Test rollback
alembic downgrade -1
alembic upgrade head
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 640/640 unit and 667/667 total baselines?
2. Do I have required-defaults-columns-json.md open and ready?
3. Do I understand the server_default syntax for each data type?
4. Am I prepared to spend 4-6 hours on manual migration verification?

**During Task 1 (Models):**
1. Am I using correct syntax for this data type?
2. Did I keep the Python-level default= ?
3. Are my string literals wrapped in single quotes inside text()?
4. Am I using func.now() not text("now()") for DateTime?
5. Did I add the ::jsonb cast for JSONB fields?

**During Task 2 (Migration):**
1. Did I remove audit.event table operations?
2. How many op.alter_column() did Alembic generate vs expected 200?
3. Have I systematically checked each table against the checklist?
4. For each missing field, did I add both upgrade() and downgrade()?
5. Does the migration run forward and backward successfully?

**After implementation:**
1. Do I have 100% test pass rate (643/643 unit, 670/670 total)?
2. Can I INSERT via raw SQL without specifying default fields?
3. Do all 200 fields show non-NULL column_default in information_schema?
4. Have I updated the project plan document?
5. Have I tested migration rollback?

---

**Ready to Begin!** 🚀

### Phase 5.0 Task Checklist:
1. ✅ Capture baseline (640/640 unit, 667/667 total)
2. 📝 **Process all 9 model files systematically using checklist**
3. 🔍 **Apply correct server_default syntax for each data type**
4. ✅ Verify Python syntax (`python -c "from app.models import *"`)
5. 🔧 **Generate Alembic migration**
6. ⚠️ **CRITICAL: Remove audit.event from migration**
7. 🔍 **MANDATORY: Manual verification against checklist (expect 50-100+ missing fields)**
8. 📝 **Add all missing op.alter_column() calls manually**
9. ✅ Apply migration (`alembic upgrade head`)
10. 🧪 **Create database-layer verification tests (raw SQL)**
11. 🔄 Run regression tests (643/643 unit, 670/670 total expected)
12. ↩️ Test rollback
13. 📚 Update project plan

Remember: Phase 5.0 is about **server defaults at the database layer**. Use the checklist religiously, expect Alembic to miss many fields, and verify everything with raw SQL tests. This is systematic, methodical work - take your time and check off each field as you go!
