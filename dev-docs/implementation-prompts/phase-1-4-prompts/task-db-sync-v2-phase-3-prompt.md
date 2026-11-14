# Task 9-10: Phase 3 - Data Type Alignment

**Reference:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - Phase 3, Tasks 9-10
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - Production SQL Dump
**Type:** Phase 3 - Data Type Alignment
**Priority:** MEDIUM (consistency)
**Change Type:** DOCUMENTATION (Task 9) + MIGRATION (Task 10)

---

## Context

This is **Phase 4.6 - DB Sync v#2**, Phase 3 - a follow-up reconciliation after completing Phase 4.5. The SQL database uses **PostgreSQL ENUMs** for several fields, but the JSON schema defines them as `text`. Additionally, some VARCHAR length limits in SQL don't match the JSON schema's unlimited text fields.

**Key Principle:** This is about **reconciliation and documentation**, not new features. Phase 3 includes one documentation task (Task 9) and one optional migration task (Task 10).

---

## What Was Completed in Phase 4.5, Phase 1 & Phase 2

**Phase 4.5 Status:** ✅ COMPLETE (March 30 - April 1, 2026)
- ✅ 572/572 tests passing (100%)
- ✅ 100% alignment between physical database and Golden Master JSON achieved
- ✅ All unique, check, and temporal exclusion constraints implemented
- ✅ All 293 triggers verified and functional

**Phase 1 Status:** ✅ COMPLETE (April 2, 2026)
- ✅ `discount_version` table added (Task 1)
- ✅ 4 missing check constraints enforced (Task 2)
- ✅ Email regex standardized to SQL standard (Task 3)
- ✅ 569/569 tests passing (555 baseline + 14 new = 100%)

**Phase 2 Status:** ✅ COMPLETE (April 2, 2026)
- ✅ 7 function optimizations backported from SQL to JSON (Tasks 4-8)
- ✅ `clock_timestamp()`, `is_active` filters, payment table queries, race condition guards
- ✅ 569/569 tests passing (100% - no regression)

**Current Baseline:** 569/569 tests passing (100%)

**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full Phase 4.5 history

---

## Current Task: Phase 3 - Data Type Alignment

**Effort:** 1-2 days
**Gap Reference:** Phase 4.6 Analysis - Section 2 (Column & Data Type Discrepancies)
**Change Type:** DOCUMENTATION (Task 9) + MIGRATION (Task 10)

This phase addresses data type inconsistencies between the JSON schema and SQL database. The primary focus is **documenting design decisions** and optionally **removing arbitrary VARCHAR limits**.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **9** | ENUM vs TEXT Strategy | SQL uses ENUMs, JSON uses TEXT + CHECK | Document | LOW |
| **10** | `quote_acceptance` columns | VARCHAR limits vs unlimited TEXT | JSON→SQL | LOW |

### Tools Available

You have access to the postgres-local MCP server to query the DB directly, in read-only mode.

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
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output to capture baseline count
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `569/569 tests passing` (Phase 3 baseline)

### Step 3: Document Your Baseline

**Write down this number before proceeding:**
- Baseline: `569/569` passing

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## Requirements

### 1. Implementation Details

This phase consists of 2 tasks: one documentation task (Task 9) and one optional migration task (Task 10).

---

#### Task 9: Document ENUM vs TEXT Design Decision

**Problem:** The JSON schema defines several fields as `text` with CHECK constraints, but the SQL database uses PostgreSQL ENUMs.

**Affected Fields:**
1. `customer.type` - JSON: `text`, SQL: `public.customertype` ENUM
2. `user.preferred_mfa_channel` - JSON: `text`, SQL: `public.preferredmfachannel` ENUM

**Design Decision to Document:**

**Approach A: PostgreSQL ENUMs (SQL Database)**
- ✅ Pros: Stricter type safety, better performance, visible in schema
- ❌ Cons: Harder to modify (requires migration), Alembic autogenerate issues

**Approach B: TEXT + CHECK Constraints (JSON Schema)**
- ✅ Pros: Easier to modify (just update constraint), SQLModel friendly
- ❌ Cons: Less performant, not self-documenting

**Recommendation:** **Standardize on TEXT + CHECK constraints** (JSON approach)

**Rationale:**
- Phase 4.5 already implemented CHECK constraints for all enum fields
- SQLModel doesn't support PostgreSQL ENUMs well (autogenerate issues)
- Flexibility more important than micro-optimizations for MVP
- CHECK constraints provide same validation guarantee as ENUMs

**SQL Database Reality (What's Currently Working):**
```sql
-- Production SQL uses ENUMs
CREATE TYPE public.customertype AS ENUM ('residential', 'commercial', 'industrial');
CREATE TYPE public.preferredmfachannel AS ENUM ('sms', 'email', 'voice');

ALTER TABLE customer
  ALTER COLUMN type TYPE public.customertype;

ALTER TABLE "user"
  ALTER COLUMN preferred_mfa_channel TYPE public.preferredmfachannel;
```

**JSON Schema Reality (What's Documented):**
```json
{
  "tables": [
    {
      "name": "customer",
      "columns": [
        {"name": "type", "type": "text", "nullable": false}
      ],
      "check_constraints": [
        {
          "name": "customer_type_chk",
          "expression": "type IN ('residential', 'commercial', 'industrial')"
        }
      ]
    }
  ]
}
```

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED (Yet)**
- The database currently uses ENUMs (working fine)
- The JSON schema documents TEXT + CHECK (also valid)
- This task is about **documenting the design decision** for future alignment
- A future migration could convert ENUMs → TEXT (optional, not required for MVP)

**Deliverables:**

**Create Design Document:**

File: `dev-docs/db-design/enum-vs-text-design-decision.md`

```markdown
# ENUM vs TEXT Design Decision

**Date:** April 2, 2026
**Status:** ✅ APPROVED - TEXT + CHECK Constraints Standard
**Context:** Phase 4.6 DB Sync v2 - Task 9

---

## Problem Statement

The AevoFab database schema has **inconsistent data type strategies** for enumerated fields:

- **SQL Database:** Uses PostgreSQL ENUMs (`public.customertype`, `public.preferredmfachannel`)
- **JSON Schema:** Uses `text` columns with CHECK constraints

This creates drift between the Golden Master JSON and the production SQL database.

---

## Approaches Considered

### Approach A: PostgreSQL ENUMs

**Implementation:**
```sql
CREATE TYPE public.customertype AS ENUM ('residential', 'commercial', 'industrial');
ALTER TABLE customer ALTER COLUMN type TYPE public.customertype;
```

**Pros:**
- ✅ Stricter type safety (invalid values rejected at database level)
- ✅ Better performance (ENUMs stored as integers internally)
- ✅ Self-documenting schema (valid values visible in `\dT+` output)
- ✅ Visible in database schema dumps

**Cons:**
- ❌ Harder to modify (requires `ALTER TYPE ... ADD VALUE` migration)
- ❌ Cannot remove ENUM values without recreating type
- ❌ Alembic autogenerate has poor ENUM support
- ❌ SQLModel doesn't map Python Enums to PostgreSQL ENUMs cleanly
- ❌ Requires custom types in multiple places (SQLModel, Alembic, JSON schema)

---

### Approach B: TEXT + CHECK Constraints

**Implementation:**
```sql
ALTER TABLE customer ALTER COLUMN type TYPE text;
ALTER TABLE customer ADD CONSTRAINT customer_type_chk
  CHECK (type IN ('residential', 'commercial', 'industrial'));
```

**Pros:**
- ✅ Easier to modify (just update CHECK constraint)
- ✅ SQLModel friendly (standard `str` type in Python)
- ✅ Alembic autogenerate works perfectly
- ✅ Same validation guarantee as ENUMs
- ✅ Can add/remove values with simple constraint replacement

**Cons:**
- ❌ Slightly less performant (text comparison vs integer comparison)
- ❌ Not self-documenting (must query constraints to see valid values)
- ❌ Requires CHECK constraint discipline (must remember to add them)

---

## Decision: TEXT + CHECK Constraints (Approach B)

**Recommendation:** **Standardize on TEXT + CHECK constraints** across the entire schema.

**Primary Rationale:**

1. **SQLModel Compatibility:** Our application uses SQLModel/SQLAlchemy, which has poor support for PostgreSQL ENUMs. TEXT + CHECK is the standard pattern.

2. **Phase 4.5 Precedent:** We already implemented CHECK constraints for all enum fields in Phase 4.5. Continuing this pattern maintains consistency.

3. **Flexibility > Micro-optimization:** For an MVP with <100 customers, the performance difference is negligible. The ability to quickly modify enum values is more important.

4. **Same Validation Guarantee:** CHECK constraints provide the exact same data integrity guarantee as ENUMs.

5. **Alembic Autogenerate:** TEXT + CHECK works seamlessly with `alembic revision --autogenerate`. ENUMs require manual migration editing.

---

## Affected Fields

| Table | Column | Current SQL | Target Standard | Migration Needed? |
|-------|--------|-------------|-----------------|-------------------|
| `customer` | `type` | `public.customertype` ENUM | `text` + CHECK | Optional (future) |
| `user` | `preferred_mfa_channel` | `public.preferredmfachannel` ENUM | `text` + CHECK | Optional (future) |

**Note:** Both approaches are currently working. The database has ENUMs, the JSON schema documents TEXT + CHECK. This is acceptable drift for now.

---

## Migration Strategy (Optional - Future Work)

**If we decide to align SQL with JSON schema:**

```sql
-- 1. Add CHECK constraints first (idempotent - already exist from Phase 4.5)
ALTER TABLE customer
ADD CONSTRAINT customer_type_chk
CHECK (type IN ('residential', 'commercial', 'industrial'));

ALTER TABLE "user"
ADD CONSTRAINT user_preferred_mfa_channel_chk
CHECK (preferred_mfa_channel IN ('sms', 'email', 'voice'));

-- 2. Convert ENUM columns to TEXT
ALTER TABLE customer
  ALTER COLUMN type TYPE text;

ALTER TABLE "user"
  ALTER COLUMN preferred_mfa_channel TYPE text;

-- 3. Drop unused ENUM types
DROP TYPE IF EXISTS public.customertype;
DROP TYPE IF EXISTS public.preferredmfachannel;
```

**Risk Assessment:**
- **Data Migration Risk:** NONE (TEXT is superset of ENUM values)
- **Application Risk:** LOW (Python code uses strings, not Enum types)
- **Rollback Risk:** MEDIUM (need to recreate ENUMs if rolled back)

**Recommendation:** **Defer this migration** until after MVP launch. Current setup is working fine.

---

## Implementation Guidelines

### For New Enum Fields:

**Do This:**
```python
# backend/app/models/example.py
from sqlalchemy import CheckConstraint

class Example(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'completed')",
            name='example_status_chk'
        ),
    )
    
    status: str = Field(nullable=False)
```

**Not This:**
```python
# ❌ Don't create new PostgreSQL ENUMs
# CREATE TYPE public.examplestatus AS ENUM ('pending', 'active', 'completed');
```

### For Modifying Enum Values:

**Do This:**
```sql
-- Drop old constraint
ALTER TABLE example DROP CONSTRAINT example_status_chk;

-- Add new constraint with updated values
ALTER TABLE example ADD CONSTRAINT example_status_chk
  CHECK (status IN ('pending', 'active', 'completed', 'cancelled'));
```

**Not This:**
```sql
-- ❌ Don't use ALTER TYPE (requires exclusive lock, can't remove values)
-- ALTER TYPE public.examplestatus ADD VALUE 'cancelled';
```

---

## Success Criteria

- [x] Design decision documented (this file)
- [x] Rationale clearly explained
- [x] Team aligned on TEXT + CHECK standard
- [x] Implementation guidelines provided
- [x] No immediate migration required (drift is acceptable)

---

## References

- **Phase 4.5 Tasks:** All enum fields already have CHECK constraints
- **SQLModel Docs:** No official PostgreSQL ENUM support
- **Golden Master JSON:** `pilot-db-schema-v2.6h.json`
- **SQL Dump:** `aevofab-db-schema-dump-phase-4.6.sql`

---

**End of Design Decision Document**
```

**JSON Schema Update (Optional - Add Comment):**

Update `dev-docs/db-design/pilot-db-schema-v2.6h.json` metadata section:

```json
{
  "metadata": {
    "version": "2.6h",
    "design_decisions": [
      {
        "topic": "ENUM vs TEXT",
        "decision": "Use TEXT + CHECK constraints instead of PostgreSQL ENUMs",
        "rationale": "SQLModel compatibility, easier modification, same validation guarantee",
        "document": "dev-docs/db-design/enum-vs-text-design-decision.md",
        "date": "2026-04-02"
      }
    ]
  }
}
```

**Success Criteria:**
- [ ] Design document created with full rationale
- [ ] All affected fields listed in document
- [ ] Implementation guidelines provided
- [ ] Optional JSON metadata update completed
- [ ] All 569 tests still passing (documentation-only change)

---

#### Task 10: Align VARCHAR Lengths with JSON Schema (Optional Migration)

**Problem:** The JSON schema uses unlimited `text` fields, but the SQL database has arbitrary VARCHAR length limits on `quote_acceptance` table.

**Affected Fields:**
1. `quote_acceptance.accepted_by_email` - JSON: `citext`, SQL: `varchar(255)`
2. `quote_acceptance.accepted_by_name` - JSON: `text`, SQL: `varchar(255)`
3. `quote_acceptance.acceptance_notes` - JSON: `text`, SQL: `varchar(1000)`

**Analysis:**
- **`citext` vs `varchar(255)`**: Both work, but `citext` is more correct for email (case-insensitive)
- **`text` vs `varchar(255)`**: Functionally identical in PostgreSQL (no performance difference)
- **`text` vs `varchar(1000)`**: VARCHAR length limit is arbitrary (notes should be unlimited)

**Recommendation:** **Align SQL with JSON** (remove VARCHAR limits)

**SQL Database Reality (What's Currently Working):**
```sql
-- Production SQL (from phase-4.6 dump)
CREATE TABLE quote_acceptance (
    id uuid PRIMARY KEY,
    accepted_by_email character varying(255),
    accepted_by_name character varying(255),
    acceptance_notes character varying(1000),
    -- ... other columns ...
);
```

**JSON Schema Target (What Should Exist):**
```json
{
  "name": "quote_acceptance",
  "columns": [
    {"name": "accepted_by_email", "type": "citext", "nullable": true},
    {"name": "accepted_by_name", "type": "text", "nullable": false},
    {"name": "acceptance_notes", "type": "text", "nullable": true}
  ]
}
```

**SQLModel Implementation:**

**File:** `backend/app/models/quoting.py`

```python
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import CITEXT

class QuoteAcceptance(TenantIsolatedMixin, SQLModel, table=True):
    """
    Quote Acceptance - Customer acceptance of quote
    
    Tracks when and how a customer accepted a quote.
    """
    __tablename__ = "quote_acceptance"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quote_id: uuid.UUID = Field(foreign_key="quote.id", nullable=False)
    
    # Email should be case-insensitive, unlimited length
    accepted_by_email: str | None = Field(
        default=None,
        sa_column=Column(CITEXT, nullable=True)
    )
    
    # Name and notes should be unlimited text
    accepted_by_name: str = Field(nullable=False)
    acceptance_notes: str | None = Field(default=None)
    
    # ... rest of model ...
```

**Migration SQL:**

**Generate Migration:**
```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "align_quote_acceptance_varchar_lengths_task10"
```

**Expected Migration Content:**
```sql
-- Upgrade
def upgrade() -> None:
    # Convert varchar(255) to citext for email
    op.alter_column('quote_acceptance', 'accepted_by_email',
                    type_=sa.dialects.postgresql.CITEXT(),
                    existing_type=sa.VARCHAR(length=255),
                    existing_nullable=True)
    
    # Convert varchar(255) to text for name
    op.alter_column('quote_acceptance', 'accepted_by_name',
                    type_=sa.Text(),
                    existing_type=sa.VARCHAR(length=255),
                    existing_nullable=False)
    
    # Convert varchar(1000) to text for notes
    op.alter_column('quote_acceptance', 'acceptance_notes',
                    type_=sa.Text(),
                    existing_type=sa.VARCHAR(length=1000),
                    existing_nullable=True)

-- Downgrade
def downgrade() -> None:
    # Revert to varchar limits
    op.alter_column('quote_acceptance', 'accepted_by_email',
                    type_=sa.VARCHAR(length=255),
                    existing_type=sa.dialects.postgresql.CITEXT(),
                    existing_nullable=True)
    
    op.alter_column('quote_acceptance', 'accepted_by_name',
                    type_=sa.VARCHAR(length=255),
                    existing_type=sa.Text(),
                    existing_nullable=False)
    
    op.alter_column('quote_acceptance', 'acceptance_notes',
                    type_=sa.VARCHAR(length=1000),
                    existing_type=sa.Text(),
                    existing_nullable=True)
```

**Database Verification Query:**
```sql
-- Verify column types after migration
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    udt_name
FROM information_schema.columns
WHERE table_name = 'quote_acceptance'
  AND column_name IN ('accepted_by_email', 'accepted_by_name', 'acceptance_notes')
ORDER BY column_name;

-- Expected results:
-- accepted_by_email  | USER-DEFINED | NULL | citext
-- accepted_by_name   | text         | NULL | text
-- acceptance_notes   | text         | NULL | text
```

**Pre-Migration Data Validation:**
```sql
-- Check for data that would be truncated (should return 0 rows)
SELECT id, accepted_by_email, LENGTH(accepted_by_email) as email_len
FROM quote_acceptance
WHERE LENGTH(accepted_by_email) > 255;

SELECT id, accepted_by_name, LENGTH(accepted_by_name) as name_len
FROM quote_acceptance
WHERE LENGTH(accepted_by_name) > 255;

SELECT id, acceptance_notes, LENGTH(acceptance_notes) as notes_len
FROM quote_acceptance
WHERE LENGTH(acceptance_notes) > 1000;

-- Expected: 0 rows for all queries (no data would be truncated)
```

**Test Coverage:**

**Create:** `backend/tests/test_quote_acceptance_varchar_alignment_task10.py`

**Minimum 6 Tests Required:**

```python
"""
Test Suite: Phase 4.6 Task 10 - Quote Acceptance VARCHAR Alignment
Tests removal of arbitrary VARCHAR limits on quote_acceptance table
"""
import pytest
from sqlmodel import Session
from sqlalchemy import text

from app.models.quoting import QuoteAcceptance, Quote


class TestQuoteAcceptanceColumnTypes:
    """Test quote_acceptance column types match JSON schema"""
    
    def test_accepted_by_email_is_citext(self, session: Session):
        """Verify accepted_by_email uses citext (case-insensitive)"""
        result = session.execute(text("""
            SELECT udt_name
            FROM information_schema.columns
            WHERE table_name = 'quote_acceptance'
              AND column_name = 'accepted_by_email'
        """))
        assert result.scalar() == 'citext'
    
    def test_accepted_by_name_is_text(self, session: Session):
        """Verify accepted_by_name uses unlimited text"""
        result = session.execute(text("""
            SELECT data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'quote_acceptance'
              AND column_name = 'accepted_by_name'
        """))
        row = result.fetchone()
        assert row[0] == 'text'
        assert row[1] is None  # No length limit
    
    def test_acceptance_notes_is_text(self, session: Session):
        """Verify acceptance_notes uses unlimited text"""
        result = session.execute(text("""
            SELECT data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'quote_acceptance'
              AND column_name = 'acceptance_notes'
        """))
        row = result.fetchone()
        assert row[0] == 'text'
        assert row[1] is None  # No length limit


class TestQuoteAcceptanceVarcharLimitsRemoved:
    """Test that VARCHAR limits have been removed"""
    
    def test_long_email_accepted(self, session: Session, test_tenant, test_quote):
        """Email longer than 255 characters should be accepted"""
        long_email = "a" * 250 + "@example.com"  # 262 chars
        acceptance = QuoteAcceptance(
            tenant_id=test_tenant.id,
            quote_id=test_quote.id,
            accepted_by_email=long_email,
            accepted_by_name="Test User"
        )
        session.add(acceptance)
        session.commit()
        
        result = session.query(QuoteAcceptance).filter(
            QuoteAcceptance.id == acceptance.id
        ).first()
        assert result.accepted_by_email == long_email
        assert len(result.accepted_by_email) > 255
    
    def test_long_name_accepted(self, session: Session, test_tenant, test_quote):
        """Name longer than 255 characters should be accepted"""
        long_name = "A" * 300  # 300 chars
        acceptance = QuoteAcceptance(
            tenant_id=test_tenant.id,
            quote_id=test_quote.id,
            accepted_by_email="test@example.com",
            accepted_by_name=long_name
        )
        session.add(acceptance)
        session.commit()
        
        result = session.query(QuoteAcceptance).filter(
            QuoteAcceptance.id == acceptance.id
        ).first()
        assert result.accepted_by_name == long_name
        assert len(result.accepted_by_name) > 255
    
    def test_long_notes_accepted(self, session: Session, test_tenant, test_quote):
        """Notes longer than 1000 characters should be accepted"""
        long_notes = "N" * 1500  # 1500 chars
        acceptance = QuoteAcceptance(
            tenant_id=test_tenant.id,
            quote_id=test_quote.id,
            accepted_by_email="test@example.com",
            accepted_by_name="Test User",
            acceptance_notes=long_notes
        )
        session.add(acceptance)
        session.commit()
        
        result = session.query(QuoteAcceptance).filter(
            QuoteAcceptance.id == acceptance.id
        ).first()
        assert result.acceptance_notes == long_notes
        assert len(result.acceptance_notes) > 1000
```

**Note:** You'll need to verify that `test_quote` fixture exists in `conftest.py`.

---

### 2. Implementation Order

**For Phase 3 (2 Tasks):**

1. **✅ Establish Regression Baseline** (569/569 tests)

2. **Task 9: Document ENUM vs TEXT (Documentation Only)**
   - Create design decision document
   - Add rationale and implementation guidelines
   - Optional: Update JSON schema metadata
   - Verify no code changes needed (documentation only)

3. **Task 10: Align VARCHAR Lengths (Optional Migration)**
   - **Pre-Migration Data Validation**
     - Run validation queries to check for data >255 or >1000 chars
     - Expected: 0 violations (current limits are generous)
   - **Update SQLModel Class**
     - Modify `backend/app/models/quoting.py`
   - **Generate Alembic Migration**
     ```bash
     cd backend
     source .venv/bin/activate
     alembic revision --autogenerate -m "align_quote_acceptance_varchar_lengths_task10"
     ```
   - **Review & Enhance Migration**
     - Verify all 3 column type changes captured
     - Ensure downgrade() reverts to varchar limits
   - **Apply Migration**
     ```bash
     alembic upgrade head
     ```
   - **Create Test Suite**
     - Create `backend/tests/test_quote_acceptance_varchar_alignment_task10.py`
     - Use `session.query()` NOT `session.exec()` (avoid deprecation warnings)
   - **Run New Tests**
     ```bash
     pytest tests/test_quote_acceptance_varchar_alignment_task10.py -v
     ```

4. **Run Regression Tests** (see "After You Complete" section)

5. **Update Documentation**

---

### 3. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 569 existing tests MUST still pass**
- **New tests (Task 10) MUST pass**
- **Target: 100% pass rate**

#### For Task 9 (Documentation Only)

**No New Tests Required:**
- This is a design decision document only
- No code or database changes
- Verify 569/569 tests still pass (no regression)

#### For Task 10 (Migration Task)

**Test File:** `backend/tests/test_quote_acceptance_varchar_alignment_task10.py`

**Required Coverage (Minimum 6 Tests):**
- Test column types are correct (citext, text, text) - 3 tests
- Test long values accepted (>255, >255, >1000) - 3 tests

**Test Patterns to Follow:**
- Review `backend/tests/test_check_constraints_task2.py`
- Use fixtures from `backend/tests/conftest.py`
- Use `session.query()` NOT `session.exec()`

---

### 4. Documentation Tracking

**For Task 9 (Design Decision):**

Create: `dev-docs/db-design/enum-vs-text-design-decision.md`

**Document Structure:**
- Problem Statement
- Approaches Considered (ENUMs vs TEXT + CHECK)
- Decision (TEXT + CHECK)
- Rationale (5+ reasons)
- Affected Fields (table with migration status)
- Migration Strategy (optional future work)
- Implementation Guidelines (for new fields)
- Success Criteria
- References

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
# Run ALL tests (excluding integration)
pytest --ignore=tests/integration/ tests/ -v

# Concise output
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:**
- **For Task 9 (documentation only):** `569 passed` (no change)
- **For Task 10 (migration):** `575 passed` (569 baseline + 6 new)

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md`

Find Phase 3, Tasks 9-10 and update with:

```markdown
## 📊 Phase 3: Data Type Alignment

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Timeline:** 1-2 days (actual: X days)
**Priority:** MEDIUM (consistency)

**Implementation Summary:**

### Task 9: Document ENUM vs TEXT Design Decision (SQL → JSON)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual: X hours)
**Change Type:** DOCUMENTATION

**Implementation Summary:**
- Created: `dev-docs/db-design/enum-vs-text-design-decision.md`
- Decision: Standardize on TEXT + CHECK constraints (not PostgreSQL ENUMs)
- Rationale: SQLModel compatibility, easier modification, same validation guarantee
- Test Results: 569/569 tests passing (100% - no regression)

**Key Changes:**
- ✅ Design decision fully documented with pros/cons analysis
- ✅ Affected fields listed (`customer.type`, `user.preferred_mfa_channel`)
- ✅ Implementation guidelines provided for future enum fields
- ✅ Optional migration strategy documented (deferred for now)

**Verification:**
- Design document reviewed and approved
- No database changes needed (drift is acceptable)
- Team aligned on TEXT + CHECK standard

---

### Task 10: Align VARCHAR Lengths with JSON Schema (JSON → SQL)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual: X hours)
**Change Type:** MIGRATION

**Implementation Summary:**
- Modified: `backend/app/models/quoting.py`
- Migration: `YYYY_MM_DD_HHMM-[hash]_align_quote_acceptance_varchar_lengths_task10.py`
- Test Suite: `test_quote_acceptance_varchar_alignment_task10.py` - 6 tests ✅
- Final Results: 575/575 tests passing (100%)

**Key Changes:**
- ✅ `accepted_by_email` converted from `varchar(255)` to `citext`
- ✅ `accepted_by_name` converted from `varchar(255)` to `text`
- ✅ `acceptance_notes` converted from `varchar(1000)` to `text`
- ✅ Pre-migration validation: 0 data truncation risks found
- ✅ All columns now match JSON schema (unlimited text)

**Verification:**
- Column types verified via information_schema query
- Long value tests pass (>255 chars email/name, >1000 chars notes)
- Migration rollback tested successfully
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING PHASE 3 AS DONE:**

### For Task 9 (Documentation):
- [ ] **Design decision document created** (`enum-vs-text-design-decision.md`)
- [ ] **Pros/cons analysis completed** for both approaches
- [ ] **Recommendation documented** (TEXT + CHECK standard)
- [ ] **Rationale clearly explained** (5+ reasons)
- [ ] **Affected fields listed** (customer.type, user.preferred_mfa_channel)
- [ ] **Implementation guidelines provided** for future enum fields
- [ ] **Optional migration strategy documented** (future work)
- [ ] **ALL 569 tests still passing** (no changes)

### For Task 10 (Migration):
- [ ] **Regression baseline captured** (569/569 tests)
- [ ] **Pre-migration data validation completed** (0 truncation risks)
- [ ] **SQLModel class updated** with CITEXT and text types
- [ ] **Alembic migration created** using autogenerate
- [ ] **Migration applied successfully** (`alembic upgrade head`)
- [ ] **All 6 new tests written and passing**
- [ ] **ALL 569 existing tests still passing**
- [ ] **New total: 575/575 passing (100%)**
- [ ] **Database verification query confirms** column types correct
- [ ] **Migration rollback tested** (`alembic downgrade -1`)
- [ ] **Project plan document updated**

### For Phase 3 Overall:
- [ ] **Both tasks complete** (documentation + optional migration)
- [ ] **Zero data type discrepancies** between JSON and SQL
- [ ] **100% test pass rate** (575/575 if migration done, 569/569 if deferred)
- [ ] **Zero regression** - All existing tests maintained
- [ ] **Design decisions documented** for future reference

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - **Phase 3, Tasks 9-10** ⭐
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-analysis.md` - Forensic Analysis (Section 2)
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - **Production SQL Dump**

### Backend Code
- `backend/app/models/quoting.py` - QuoteAcceptance model (Task 10)
- `backend/app/models/crm.py` - Customer model (ENUM reference)
- `backend/app/models/core.py` - User model (ENUM reference)

### Tests (Reference for Patterns)
- `backend/tests/test_check_constraints_task2.py`
- `backend/tests/conftest.py` - Test fixtures

---

## Risk Assessment

### Task 9 Risks

**Documentation Risk:** NONE
- Pure documentation task
- No code or database changes
- Zero functional impact

### Task 10 Risks

**Data Migration Risk:** VERY LOW
- VARCHAR → TEXT is safe (TEXT is superset)
- varchar(255) → citext preserves all data
- No data truncation possible
- **Mitigation:** Pre-migration validation queries confirm no data >255 or >1000 chars

**Type Conversion Risk:** LOW
- PostgreSQL handles VARCHAR → TEXT seamlessly
- CITEXT extension already installed (used in other tables)
- **Mitigation:** Database verification query after migration

**Regression Risk:** LOW
- Only affects quote_acceptance table
- Existing tests use short values (won't break)
- New tests verify long values work
- **Mitigation:** Maintain 569/569 baseline, add 6 new tests

**Rollback Risk:** VERY LOW
- Downgrade simply adds VARCHAR limits back
- No data loss (TEXT contains all varchar data)
- **Mitigation:** Test rollback before marking complete

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Deprecation Warnings:** Use `session.query()` not `session.exec()` in tests
- **Dual Master Strategy:** JSON is documentation authority, SQL dump is runtime authority
- **Zero Regression Policy:** All 569 existing tests MUST pass after changes

### Phase 3 Specific
- **Task 9 is documentation only** - no code or database changes
- **Task 10 is optional** - can be deferred if time is tight
- **ENUM vs TEXT is strategic decision** - affects all future enum fields
- **VARCHAR limits are cosmetic** - no functional impact on MVP
- **Test consistency critical** - new tests must match existing patterns

### Design Decision Guidelines
- **ENUMs are not banned** - they work fine, we just prefer TEXT + CHECK
- **Existing ENUMs can stay** - no urgency to convert them
- **Future fields should use TEXT + CHECK** - maintain consistency
- **CHECK constraints are mandatory** - same validation guarantee as ENUMs

### If You Get Stuck
- Check the SQL dump for current column types
- Review Phase 4.5 for CHECK constraint patterns
- Use `postgres-local` MCP server to query database
- Task 10 migration is optional - can skip if problematic
- Remember: Phase 3 is MEDIUM priority (consistency, not correctness)

---

## Example Task Flow

### For Task 9 (Documentation Task):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep passed | tail -1
# Record: 569 passed

# 2. Create design decision document
# [Create dev-docs/db-design/enum-vs-text-design-decision.md]
# Copy template from task description above

# 3. Fill in all sections
# - Problem Statement
# - Approaches Considered
# - Decision & Rationale
# - Affected Fields
# - Migration Strategy
# - Implementation Guidelines

# 4. Optional: Update JSON metadata
# [Edit dev-docs/db-design/pilot-db-schema-v2.6h.json]
# Add design_decisions array to metadata

# 5. Regression check (should be identical)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep passed | tail -1
# Expected: 569 passed (no change)

# 6. Update docs
# [Edit phase-4.6-db-schema-sync-2-plan.md - mark Task 9 complete]
```

### For Task 10 (Migration Task):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep passed | tail -1
# Record: 569 passed

# 2. Pre-migration validation
# Run SQL queries to check for data >255 or >1000 chars
# Expected: 0 rows (no violations)

# 3. Update SQLModel
# [Edit backend/app/models/quoting.py]
# Update QuoteAcceptance class with CITEXT and text types

# 4. Generate migration
alembic revision --autogenerate -m "align_quote_acceptance_varchar_lengths_task10"

# 5. Review migration
# Verify all 3 column changes captured
# Ensure downgrade() reverts correctly

# 6. Apply migration
alembic upgrade head

# 7. Verify database changes
# Run information_schema query to confirm column types

# 8. Create test suite
# [Create backend/tests/test_quote_acceptance_varchar_alignment_task10.py]

# 9. Run new tests
pytest tests/test_quote_acceptance_varchar_alignment_task10.py -v

# 10. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep passed | tail -1
# Expected: 575 passed (569 + 6 new)

# 11. Rollback test
alembic downgrade -1
alembic upgrade head

# 12. Update docs
# [Edit phase-4.6-db-schema-sync-2-plan.md - mark Task 10 complete]
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 569/569 baseline?
2. For Task 9: Do I understand the ENUM vs TEXT tradeoffs?
3. For Task 10: Is this migration necessary for MVP? (it's optional)
4. For Task 10: Have I run pre-migration validation queries?

**During implementation:**
1. For Task 9: Have I explained the rationale clearly? (5+ reasons)
2. For Task 9: Have I provided implementation guidelines for future fields?
3. For Task 10: Am I using `session.query()` (not `session.exec()`) in tests?
4. For Task 10: Does my migration include proper downgrade()?

**After implementation:**
1. For Task 9: Have I documented all affected fields?
2. For Task 10: Do I have 100% test pass rate (575/575)?
3. For Task 10: Have I tested migration rollback?
4. Have I updated the project plan document?
5. Is the design decision clear enough for future developers?

---

**Ready to Begin Phase 3!** 🚀

### Phase 3 Task Checklist:

1. ✅ **Task 9: ENUM vs TEXT Design Decision**
   - Capture baseline (569/569)
   - Create design decision document
   - Document all rationale and guidelines
   - Optional: Update JSON metadata
   - Verify 569/569 tests still pass (no changes)

2. ✅ **Task 10: VARCHAR Alignment (Optional)**
   - Pre-migration validation (check for long values)
   - Update QuoteAcceptance model
   - Generate and apply migration
   - Create 6 comprehensive tests
   - Run regression tests (expect 575/575)

3. 📚 **Update Documentation**
   - Mark Phase 3 complete in roadmap
   - Document both tasks
   - Summarize test results

Remember: Phase 3 is about **data type consistency** and **documenting design decisions**. Task 9 is pure documentation. Task 10 is optional but recommended for full JSON-SQL alignment. Both are MEDIUM priority (nice-to-have, not critical for MVP).
