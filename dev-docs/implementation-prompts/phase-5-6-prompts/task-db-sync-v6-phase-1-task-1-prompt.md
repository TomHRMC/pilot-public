# Task 1: SQLModel Architecture - Systematic Server Default Implementation

**Reference:** `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` - Task 1
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/required-defaults-columns-json.md` - **Authoritative Checklist (200 fields)** ⭐⭐⭐
- Current Live Database (Phase 4.9 Post-State)
**Type:** Phase 5.0 - Server Defaults Enforcement
**Priority:** CRITICAL
**Change Type:** SYSTEMATIC MODEL UPDATE

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

## Current Task: SQLModel Architecture - Systematic Server Default Implementation

**Effort:** 2.0 days
**Gap Reference:** Phase 5.0 Analysis - The "Sweeping Missing Defaults Bug"
**Change Type:** MODEL UPDATE

Transform all Python SQLModel definitions to use SQLAlchemy-level `server_default=` in addition to Pydantic-level `default=`, ensuring database-layer enforcement of default values for direct SQL operations. This fixes the architectural bug where 200 fields have defaults only in Python memory, not at the PostgreSQL schema level.

### What Needs to Be Fixed

**Affected Model Files & Estimated Field Count:**

| Model File | Tables Affected | Approx. Fields | Priority |
|------------|----------------|----------------|----------|
| `backend/app/models/auth.py` | platform_role, user, user_endpoint, etc. | ~25 fields | HIGH |
| `backend/app/models/core.py` | tenant, tenant_settings, customer, supplier | ~35 fields | CRITICAL |
| `backend/app/models/crm.py` | contact, address, entity relationships | ~20 fields | HIGH |
| `backend/app/models/quoting.py` | quote, quote_line, acceptance | ~25 fields | HIGH |
| `backend/app/models/fulfillment.py` | job, invoice, payment, time_entry | ~40 fields | HIGH |
| `backend/app/models/catalog.py` | product, pricing, supplier relationships | ~15 fields | MEDIUM |
| `backend/app/models/billing.py` | subscription, usage_tracking | ~20 fields | MEDIUM |
| `backend/app/models/system.py` | notification_outbox, webhook, connector | ~15 fields | MEDIUM |
| `backend/app/models/ai.py` | voice_conversation_session | ~5 fields | LOW |
| **TOTAL** | **78 tables** | **200 fields** | **CRITICAL** |

**⚠️ CRITICAL:** The authoritative list is in `required-defaults-columns-json.md`. Use this table for planning, but verify every field against the checklist.

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

### 2. String Literals Require Inner Quotes in text()

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

### 3. Keep Both Python AND Database Defaults

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

### 4. JSONB Requires ::jsonb Cast

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

### 5. Use func.now() for DateTime, NOT text("now()")

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

## Implementation Strategy

### File Processing Order (Dependency-Based)

Process model files systematically in this order:

1. `backend/app/models/auth.py` - Authentication & authorization (~25 fields)
2. `backend/app/models/core.py` - Tenant, user, customer (~35 fields)
3. `backend/app/models/crm.py` - Contact, address (~20 fields)
4. `backend/app/models/quoting.py` - Quote, lines (~25 fields)
5. `backend/app/models/fulfillment.py` - Job, invoice (~40 fields)
6. `backend/app/models/catalog.py` - Products, pricing (~15 fields)
7. `backend/app/models/billing.py` - Subscriptions (~20 fields)
8. `backend/app/models/system.py` - Notifications, webhooks (~15 fields)
9. `backend/app/models/ai.py` - Voice AI (~5 fields)

### Per-File Workflow

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

### Server Default Syntax Reference (By Data Type)

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

### Required Import Statements

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

### Checklist-Driven Verification

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

---

## Success Criteria for Task 1

- [ ] All 200 fields from checklist have `server_default=` implemented
- [ ] Every field uses correct syntax for its data type
- [ ] All model files have necessary SQLAlchemy imports
- [ ] Python-level defaults remain intact
- [ ] No typos in server_default text literals
- [ ] Code passes Python syntax validation (`python -c "from app.models import *"`)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Python Syntax Check

```bash
cd backend
source .venv/bin/activate
python -c "from app.models import *; print('✅ All models loaded successfully')"
```

**Expected:** No import errors, successful load message

### Step 2: Verify Model Changes

Use the postgres-local MCP server to spot-check that model definitions are correct (this doesn't verify the database yet, just that the Python syntax is valid):

```python
# Quick verification that imports work
python -c "
from app.models.core import Tenant
from app.models.auth import PlatformRole
print('✅ Models import successfully')
"
```

### Step 3: Document Completion

**Write down:**
- Total fields updated: 200/200
- Model files modified: 9/9
- Import errors: 0
- Syntax validation: ✅ PASSED

**This completes Task 1. Task 2 (Migration Generation) will follow.**

---

## Documentation Update

**After Task 1 Completion:**

No documentation updates needed yet. Task 1 is model updates only. Documentation will be updated after Task 3 (Testing) is complete.

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

**For Task 1:**
- **Data Loss Risk:** NONE (only modifying Python code, no database changes yet)
- **Syntax Error Risk:** MEDIUM (easy to make typos in 200 fields)
- **Import Error Risk:** LOW (straightforward imports)
- **Regression Risk:** NONE (no tests run until migration in Task 2)
- **Rollback Complexity:** TRIVIAL (git revert if needed)
- **Mitigation:** Systematic checklist process, frequent syntax validation

---

## Notes

### Important Patterns to Follow
- **Checklist is Law:** Every field in required-defaults-columns-json.md MUST be addressed
- **Both Layers:** Keep both Python default= AND database server_default=
- **String Quotes:** `text("'value'")` not `text("value")` for strings
- **JSONB Cast:** `text("'{}'::jsonb")` not `text("{}")`for JSONB
- **DateTime func:** Use `func.now()` not `text("now()")` for timestamps
- **Frequent Validation:** Run Python syntax checks after each file

### Task 1 Specific
- **No database changes:** This task only updates Python models
- **No migration yet:** Migration generation happens in Task 2
- **No tests yet:** Testing happens in Task 3
- **Focus on accuracy:** Take time to verify each field against checklist

### If You Get Stuck
- Check syntax reference for the specific data type
- Verify against the checklist line-by-line
- Search model files for similar field patterns
- Run Python syntax validation frequently to catch errors early
- Ask for help if spending >30 minutes on a single field

---

## Example Task Flow

### For Task 1 (Model Updates):

```bash
# 1. Baseline - Verify current state
cd backend
source .venv/bin/activate

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

---

## Questions to Ask

**Before starting:**
1. Do I have required-defaults-columns-json.md open and ready?
2. Do I understand the server_default syntax for each data type?
3. Am I prepared to work through 200 fields systematically?

**During Task 1 (Models):**
1. Am I using correct syntax for this data type?
2. Did I keep the Python-level default= ?
3. Are my string literals wrapped in single quotes inside text()?
4. Am I using func.now() not text("now()") for DateTime?
5. Did I add the ::jsonb cast for JSONB fields?

**After implementation:**
1. Do all models import without errors?
2. Have I updated all 200 fields from the checklist?
3. Did I add all necessary SQLAlchemy imports to each file?

---

**Ready to Begin Task 1!** 🚀

### Task 1 Checklist:
1. ✅ Capture baseline (verify models load)
2. 📝 **Open required-defaults-columns-json.md side-by-side**
3. 📝 **Process all 9 model files systematically using checklist**
4. 🔍 **Apply correct server_default syntax for each data type**
5. ✅ Verify Python syntax after each file (`python -c "from app.models.<file> import *"`)
6. ✅ Final verification (`python -c "from app.models import *"`)
7. 📚 Record completion: 200/200 fields updated

Remember: Task 1 is about **model updates only**. Use the checklist religiously, apply the correct syntax for each data type, and verify frequently with Python imports. This is systematic, methodical work - take your time and check off each field as you go!
