# Task 10: Missing Temporal Exclusion Constraints

**Reference:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Task 10
**Authority:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`
**Type:** Phase 3 - Data Integrity
**Priority:** MEDIUM

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

This is a **Phase 3 Data Integrity task** to achieve 100% alignment between our SQLModel implementations and the Golden Master Database Schema (v2.6h JSON). This is NOT a new feature - it's surgical corrections to ensure database-level data integrity and business rule enforcement.

---

## Completed So Far

**Phase 1: Foundation (COMPLETE - March 30-31, 2026):**
- ✅ Task 1: Timezone enforcement (9 columns fixed)
- ✅ Task 2: Citext conversion for user email
- ✅ Task 3: QuickBooks identity rules on Customer table

**Phase 2: Functions & Triggers (COMPLETE - March 31, 2026):**
- ✅ Task 4: Missing PL/pgSQL functions (3 functions + 200 triggers)
- ✅ Task 5: Function naming standard compliance
- ✅ Task 6: Audit trigger coverage (85 audit triggers)
- ✅ Task 7: Operational trigger verification (293 total triggers)

**Phase 3: Data Integrity (PARTIAL):**
- ✅ Task 8: Missing unique constraints (4/4 complete)
- ✅ Task 9: Missing check constraints (9/9 complete)
- 📋 Task 10: Missing temporal exclusion constraints (THIS TASK)

**Current Test Baseline:** 490 tests passing (100%)
**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full context

---

## Current Task: Missing Temporal Exclusion Constraints

**Effort:** 1 day
**Gap Reference:** Analysis Section 3 - Missing Temporal Exclusion Constraints

Temporal versioned tables (e.g., `tenant_markup_version`, `tax_rate_version`) must prevent **overlapping active date ranges** using GIST exclusion constraints. Currently, none exist. This prevents versioning bugs where two price/markup/tax versions could be active for the same time period.

### What Needs to Be Fixed

| # | Table | Issue | Impact | Complexity |
|---|-------|-------|--------|------------|
| **1** | `tenant_markup_version` | No temporal exclusion on (tenant_id, effective_from/to) | Multiple markup versions can overlap, causing incorrect profit calculations | MEDIUM |
| **2** | `supplier_item_price` | No temporal exclusion on (supplier_item_id, tenant_id, effective_from/to) | Same supplier item can have overlapping prices for same tenant | MEDIUM |
| **3** | `tax_rate_version` | No temporal exclusion on (tax_rate_id, effective_from/to) | Tax rate versions can overlap, causing incorrect tax calculations | MEDIUM |
| **4** | `pricebook_item_version` | No temporal exclusion on (pricebook_item_id, recorded_at) | Quote prices can have overlapping effective periods | MEDIUM |
| **5** | `product_plan_version` | No temporal exclusion on (product_plan_id, effective_from/to) | SaaS pricing plans can have overlapping versions | MEDIUM |
| **6** | `product_plan_product_feature_version` | No temporal exclusion on (product_plan_product_feature_id, effective_from/to) | Feature availability periods can overlap | MEDIUM |

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** You MUST capture the current test baseline BEFORE making ANY changes. This ensures we can detect regressions.

### Step 1: Activate Virtual Environment

All Python and pytest commands MUST be run in the virtual environment:

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Regression Tests (Non-Integration)

```bash
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output to capture baseline count
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `[BASELINE_NON_INTEGRATION_COUNT] tests passing`

Example output:
```
========================== 490 passed in 45.23s ==========================
```

### Step 3: Run ALL Tests (Including Integration)

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `[BASELINE_TOTAL_COUNT] tests passing`

Example output:
```
========================== 517 passed in 62.11s ==========================
```

### Step 4: Document Your Baseline

**Write down these numbers before proceeding:**
- Non-Integration Baseline: `___/___` passing
- Total Tests Baseline: `___/___` passing

**These are your regression checkpoints. All these tests MUST still pass after your work.**

---

## Requirements

### 1. Implementation Details

#### Gap 1: `tenant_markup_version` - No Temporal Overlap

**Problem:** Two markup versions for the same tenant can have overlapping `effective_from` to `effective_to` date ranges, causing ambiguity in which markup percentage to apply for profit calculations.

**SQLModel Fix:**
```python
# backend/app/models/catalog.py
from sqlalchemy import text

class TenantMarkupVersion(SQLModel, table=True):
    __tablename__ = "tenant_markup_version"
    __table_args__ = (
        # Note: EXCLUDE constraint must be added via raw SQL in migration
        # Cannot be defined in SQLModel __table_args__ directly
    )
    # ... existing fields ...
```

**Migration SQL:**
```sql
-- Enable btree_gist extension (required for EXCLUDE constraints with mixed types)
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Pre-migration check: Find overlapping markup versions
SELECT 
    a.id AS version_a_id, 
    b.id AS version_b_id,
    a.tenant_id,
    a.effective_from AS a_start,
    a.effective_to AS a_end,
    b.effective_from AS b_start,
    b.effective_to AS b_end
FROM tenant_markup_version a
JOIN tenant_markup_version b ON a.tenant_id = b.tenant_id AND a.id < b.id
WHERE tstzrange(a.effective_from, a.effective_to, '[)') && 
      tstzrange(b.effective_from, b.effective_to, '[)');

-- Add exclusion constraint
ALTER TABLE tenant_markup_version 
ADD CONSTRAINT tmv_no_overlap 
EXCLUDE USING GIST (
  tenant_id WITH =,
  tstzrange(effective_from, effective_to, '[)') WITH &&
);
```

**What This Enforces:**
- Prevents two markup versions with overlapping date ranges for same tenant
- Example violation: Version 1 (2024-01-01 to 2024-12-31), Version 2 (2024-06-01 to 2025-06-01) → **OVERLAP REJECTED**
- `[)` means inclusive start, exclusive end (standard range notation)

---

#### Gap 2: `supplier_item_price` - No Temporal Overlap Per Tenant

**Problem:** Same supplier item can have overlapping price periods for the same tenant, causing confusion on which price to use.

**Migration SQL:**
```sql
-- Pre-migration check: Find overlapping prices
SELECT 
    a.id AS price_a_id,
    b.id AS price_b_id,
    a.supplier_item_id,
    a.tenant_id,
    a.effective_from AS a_start,
    a.effective_to AS a_end,
    b.effective_from AS b_start,
    b.effective_to AS b_end
FROM supplier_item_price a
JOIN supplier_item_price b ON 
    a.supplier_item_id = b.supplier_item_id 
    AND a.tenant_id = b.tenant_id 
    AND a.id < b.id
WHERE tstzrange(a.effective_from, a.effective_to, '[)') && 
      tstzrange(b.effective_from, b.effective_to, '[)');

-- Add exclusion constraint
ALTER TABLE supplier_item_price 
ADD CONSTRAINT sip_no_overlap_per_tenant 
EXCLUDE USING GIST (
  supplier_item_id WITH =,
  tenant_id WITH =,
  tstzrange(effective_from, effective_to, '[)') WITH &&
);
```

---

#### Gap 3: `tax_rate_version` - No Temporal Overlap

**Problem:** Tax rate versions can overlap, causing incorrect tax calculations on quotes and invoices.

**Migration SQL:**
```sql
-- Pre-migration check: Find overlapping tax rate versions
SELECT 
    a.id AS version_a_id,
    b.id AS version_b_id,
    a.tax_rate_id,
    a.effective_from AS a_start,
    a.effective_to AS a_end,
    b.effective_from AS b_start,
    b.effective_to AS b_end
FROM tax_rate_version a
JOIN tax_rate_version b ON a.tax_rate_id = b.tax_rate_id AND a.id < b.id
WHERE tstzrange(a.effective_from, a.effective_to, '[)') && 
      tstzrange(b.effective_from, b.effective_to, '[)');

-- Add exclusion constraint
ALTER TABLE tax_rate_version 
ADD CONSTRAINT tax_rate_version_no_overlap 
EXCLUDE USING GIST (
  tax_rate_id WITH =,
  tstzrange(effective_from, effective_to, '[)') WITH &&
);
```

---

#### Gap 4: `pricebook_item_version` - No Temporal Overlap

**Problem:** Pricebook item versions use `recorded_at` for open-ended versioning. Overlaps cause ambiguity in which price to apply to quotes.

**Note:** This table uses `recorded_at` as a timestamp, not a range. Exclusion constraint prevents two versions from existing simultaneously.

**Migration SQL:**
```sql
-- Pre-migration check: Find overlapping pricebook versions
-- Note: recorded_at is a point-in-time, so we're checking for exact duplicates
SELECT 
    pricebook_item_id,
    recorded_at,
    COUNT(*) as count
FROM pricebook_item_version
GROUP BY pricebook_item_id, recorded_at
HAVING COUNT(*) > 1;

-- Add exclusion constraint (prevents duplicate recorded_at for same pricebook item)
ALTER TABLE pricebook_item_version 
ADD CONSTRAINT piv_no_overlap 
EXCLUDE USING GIST (
  pricebook_item_id WITH =,
  recorded_at WITH =
);
```

---

#### Gap 5: `product_plan_version` - No Temporal Overlap

**Problem:** SaaS product plan versions can overlap, causing confusion on which pricing tier applies to subscriptions.

**Migration SQL:**
```sql
-- Pre-migration check: Find overlapping plan versions
SELECT 
    a.id AS version_a_id,
    b.id AS version_b_id,
    a.product_plan_id,
    a.effective_from AS a_start,
    a.effective_to AS a_end,
    b.effective_from AS b_start,
    b.effective_to AS b_end
FROM product_plan_version a
JOIN product_plan_version b ON a.product_plan_id = b.product_plan_id AND a.id < b.id
WHERE tstzrange(a.effective_from, a.effective_to, '[)') && 
      tstzrange(b.effective_from, b.effective_to, '[)');

-- Add exclusion constraint
ALTER TABLE product_plan_version 
ADD CONSTRAINT product_plan_version_no_overlap 
EXCLUDE USING GIST (
  product_plan_id WITH =,
  tstzrange(effective_from, effective_to, '[)') WITH &&
);
```

---

#### Gap 6: `product_plan_product_feature_version` - No Temporal Overlap

**Problem:** Feature availability periods can overlap, causing confusion on which features are included in a plan at a given time.

**Migration SQL:**
```sql
-- Pre-migration check: Find overlapping feature versions
SELECT 
    a.id AS version_a_id,
    b.id AS version_b_id,
    a.product_plan_product_feature_id,
    a.effective_from AS a_start,
    a.effective_to AS a_end,
    b.effective_from AS b_start,
    b.effective_to AS b_end
FROM product_plan_product_feature_version a
JOIN product_plan_product_feature_version b ON 
    a.product_plan_product_feature_id = b.product_plan_product_feature_id 
    AND a.id < b.id
WHERE tstzrange(a.effective_from, a.effective_to, '[)') && 
      tstzrange(b.effective_from, b.effective_to, '[)');

-- Add exclusion constraint
ALTER TABLE product_plan_product_feature_version 
ADD CONSTRAINT pppfv_no_overlap 
EXCLUDE USING GIST (
  product_plan_product_feature_id WITH =,
  tstzrange(effective_from, effective_to, '[)') WITH &&
);
```

---

### 2. Database Query Tools

**You have access to the postgres-local MCP server for direct database queries:**

```python
# Example: Check for overlapping temporal ranges
await mcp__postgres_local__query({
    "sql": """
        SELECT 
            a.id AS version_a_id, 
            b.id AS version_b_id,
            a.tenant_id,
            a.effective_from AS a_start,
            a.effective_to AS a_end,
            b.effective_from AS b_start,
            b.effective_to AS b_end
        FROM tenant_markup_version a
        JOIN tenant_markup_version b ON a.tenant_id = b.tenant_id AND a.id < b.id
        WHERE tstzrange(a.effective_from, a.effective_to, '[)') && 
              tstzrange(b.effective_from, b.effective_to, '[)');
    """
})
```

Use this tool to:
- Validate data before applying constraints (check for existing overlaps)
- Verify constraints exist after migration
- Debug migration issues
- Confirm test data state

---

### 3. Implementation Order

Execute in this exact sequence:

1. **✅ Establish Regression Baseline** (see "Before You Start" section above)

2. **Pre-Migration Data Validation**
   - Run validation queries for ALL 6 tables to check for existing overlaps
   - Clean up any overlapping data found (requires manual resolution - decide which version to keep)
   - Document any data cleanup performed
   - **CRITICAL:** Migration will FAIL if overlapping data exists

3. **Create Alembic Migration (Manual)**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "add_temporal_exclusion_constraints_task10"
   ```
   
   **Note:** Use manual revision (not autogenerate) because SQLModel doesn't support EXCLUDE constraints directly.

4. **Write Migration upgrade() Function**
   - Enable btree_gist extension (if not already enabled)
   - Add pre-migration validation checks (raise exception if overlaps found)
   - Add all 6 EXCLUDE constraints using raw SQL
   - Include clear comments explaining each constraint

5. **Write Migration downgrade() Function**
   - Drop all 6 EXCLUDE constraints in reverse order
   - Do NOT drop btree_gist extension (may be used elsewhere)

6. **Apply Migration**
   ```bash
   alembic upgrade head
   ```

7. **Create Test Suite**
   - Create `backend/tests/test_temporal_exclusion_constraints_task10.py`
   - Write comprehensive tests (see Test Requirements below)
   - **CRITICAL:** Use `session.query()` NOT `session.exec()` to avoid deprecation warnings

8. **Run New Tests**
   ```bash
   pytest tests/test_temporal_exclusion_constraints_task10.py -v
   ```

9. **Run Regression Tests** (see "After You Complete" section below)

10. **Update Documentation** (see Documentation Update section below)

---

### 4. Test Requirements

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL 490 existing tests MUST still pass** (baseline cannot regress)
- **ALL new tests MUST pass** (schema sync verification)
- **Target: Minimum 18 new tests (3 per table)**

**Test File:** `backend/tests/test_temporal_exclusion_constraints_task10.py`

**Test Standards:**

```python
"""
Test Suite: Phase 3 Task 10 - Temporal Exclusion Constraints
Tests temporal exclusion constraints from Golden Master v2.6h
Prevents overlapping date ranges in versioned tables.
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.models.catalog import TenantMarkupVersion, SupplierItemPrice, TaxRateVersion
from app.models.quoting import PricebookItemVersion
from app.models.billing import ProductPlanVersion, ProductPlanProductFeatureVersion

# ⚠️ CRITICAL: Use session.query() NOT session.exec()
# This avoids deprecation warnings

class TestTenantMarkupVersionTemporalExclusion:
    """Test temporal exclusion constraint on tenant_markup_version"""
    
    def test_non_overlapping_versions_allowed(self, session: Session, test_tenant):
        """Non-overlapping date ranges should be accepted"""
        now = datetime.now(timezone.utc)
        
        # Version 1: Jan 1 - Dec 31, 2024
        v1 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            markup_percentage_basis_points=2000,  # 20%
            effective_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            effective_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
            recorded_at=now
        )
        session.add(v1)
        session.commit()
        
        # Version 2: Jan 1, 2025 onwards (no overlap)
        v2 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            markup_percentage_basis_points=2500,  # 25%
            effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
            effective_to=datetime(2025, 12, 31, tzinfo=timezone.utc),
            recorded_at=now
        )
        session.add(v2)
        session.commit()  # Should succeed
        
        # Verify both exist
        result = session.query(TenantMarkupVersion).filter(
            TenantMarkupVersion.tenant_id == test_tenant.id
        ).all()
        assert len(result) == 2
    
    def test_overlapping_versions_rejected(self, session: Session, test_tenant):
        """Overlapping date ranges should be rejected"""
        now = datetime.now(timezone.utc)
        
        # Version 1: Jan 1 - Dec 31, 2024
        v1 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            markup_percentage_basis_points=2000,
            effective_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            effective_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
            recorded_at=now
        )
        session.add(v1)
        session.commit()
        
        # Version 2: Jun 1, 2024 - Jun 1, 2025 (OVERLAPS with v1)
        v2 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            markup_percentage_basis_points=2500,
            effective_from=datetime(2024, 6, 1, tzinfo=timezone.utc),
            effective_to=datetime(2025, 6, 1, tzinfo=timezone.utc),
            recorded_at=now
        )
        session.add(v2)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert "tmv_no_overlap" in str(exc_info.value) or "exclusion" in str(exc_info.value).lower()
    
    def test_adjacent_ranges_allowed(self, session: Session, test_tenant):
        """Adjacent but non-overlapping ranges should be allowed"""
        now = datetime.now(timezone.utc)
        
        # Version 1: Jan 1 - Jun 30, 2024
        v1 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            markup_percentage_basis_points=2000,
            effective_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            effective_to=datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
            recorded_at=now
        )
        session.add(v1)
        session.commit()
        
        # Version 2: Jul 1, 2024 onwards (adjacent, no overlap due to [) notation)
        v2 = TenantMarkupVersion(
            tenant_id=test_tenant.id,
            markup_percentage_basis_points=2500,
            effective_from=datetime(2024, 7, 1, tzinfo=timezone.utc),
            effective_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
            recorded_at=now
        )
        session.add(v2)
        session.commit()  # Should succeed
        
        result = session.query(TenantMarkupVersion).filter(
            TenantMarkupVersion.tenant_id == test_tenant.id
        ).all()
        assert len(result) == 2

# Repeat similar test classes for:
# - TestSupplierItemPriceTemporalExclusion
# - TestTaxRateVersionTemporalExclusion
# - TestPricebookItemVersionTemporalExclusion
# - TestProductPlanVersionTemporalExclusion
# - TestProductPlanProductFeatureVersionTemporalExclusion
```

**Required Test Coverage (Minimum 18 Tests - 3 per table):**
- [ ] Non-overlapping date ranges accepted (6 tests, 1 per table)
- [ ] Overlapping date ranges rejected (6 tests, 1 per table)
- [ ] Adjacent non-overlapping ranges allowed (6 tests, 1 per table)
- [ ] NULL `effective_to` handling (bonus tests for open-ended ranges)
- [ ] Different tenants can have same date ranges (multi-tenancy test for tenant_id scoped tables)

**Test Fixtures:**
Review `backend/tests/conftest.py` for available fixtures:
- `session` - Database session with auto-rollback
- `test_tenant` - Test tenant record
- `test_user` - Test user record
- Add new fixtures if needed (e.g., `test_tax_rate`, `test_supplier_item`, `test_pricebook_item`, `test_product_plan`)

---

### 5. Database Verification

**After Migration Applied:**

Use the MCP server or psql to verify constraints:

```sql
-- Verify btree_gist extension enabled
SELECT * FROM pg_extension WHERE extname = 'btree_gist';

-- Verify all 6 exclusion constraints exist
SELECT 
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conname IN (
    'tmv_no_overlap',
    'sip_no_overlap_per_tenant',
    'tax_rate_version_no_overlap',
    'piv_no_overlap',
    'product_plan_version_no_overlap',
    'pppfv_no_overlap'
)
ORDER BY conname;

-- Expected output: 6 rows with contype='x' (exclusion constraint)
-- Example:
-- tmv_no_overlap | tenant_markup_version | x | EXCLUDE USING gist (tenant_id WITH =, tstzrange(effective_from, effective_to, '[)'::text) WITH &&)
```

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all implementation and new tests pass, you MUST verify the regression baseline.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Non-Integration Tests

```bash
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:** `[490 + 18] = 508 passed` (minimum)

### Step 3: Run ALL Tests (Including Integration)

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:** `[BASELINE_TOTAL_COUNT + 18] passed` (minimum)

### Step 4: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify which tests are failing
2. Determine if they are:
   - New tests you wrote (fix them)
   - Existing tests that regressed (CRITICAL - fix immediately)
3. Fix ALL failing tests before proceeding
4. Re-run regression tests until 100% pass rate

**Regression Analysis:**
- New tests failing → Fix your test code
- Existing tests failing → Your changes broke something - ROLLBACK and fix
- Cannot achieve 100% → Create fix document (see Zero Tolerance Policy below)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md`

Find Task 10 section (line 1081) and update with:

```markdown
### Task 10: Missing Temporal Exclusion Constraints (6 Tables)

**Status:** ✅ COMPLETE (2026-04-XX)
**Effort:** 1 day (actual)
**Priority:** MEDIUM
**Gap Reference:** Analysis Section 3 - Missing Temporal Exclusion Constraints

**Completed 6 temporal exclusion constraints:**
- ✅ `tenant_markup_version` - `tmv_no_overlap`
- ✅ `supplier_item_price` - `sip_no_overlap_per_tenant`
- ✅ `tax_rate_version` - `tax_rate_version_no_overlap`
- ✅ `pricebook_item_version` - `piv_no_overlap`
- ✅ `product_plan_version` - `product_plan_version_no_overlap`
- ✅ `product_plan_product_feature_version` - `pppfv_no_overlap`

**Implementation Summary:**

#### btree_gist Extension
- Enabled PostgreSQL btree_gist extension (required for mixed-type EXCLUDE constraints)
- Allows combining equality operators (=) with range operators (&&)

#### Temporal Exclusion Constraints
All 6 constraints prevent overlapping date ranges using `tstzrange()` with `[)` notation (inclusive start, exclusive end):
- Tenant-scoped: `tenant_markup_version`, `supplier_item_price`
- Global-scoped: `tax_rate_version`, `pricebook_item_version`, `product_plan_version`, `product_plan_product_feature_version`

**Migration:** `2026_04_XX_HHMM-[hash]_add_temporal_exclusion_constraints_task10.py`
**Test Suite:** `test_temporal_exclusion_constraints_task10.py` - 18+ tests
**Final Test Results:** [508+]/[508+] tests passing (100%)

**Database Verification:**
- btree_gist extension enabled ✅
- All 6 exclusion constraints active ✅
- Pre-migration validation: 0 overlapping records found ✅
- Migration upgrade/downgrade tested successfully ✅

**Test Coverage Breakdown:**
- New tests added: 18+
- Baseline maintained: 490
- Total passing: [508+]/[508+] (100%)

**Key Implementation Notes:**
- Used manual migration (not autogenerate) because SQLModel doesn't support EXCLUDE constraints
- Pre-migration validation queries detect existing overlaps before constraint application
- `tstzrange(start, end, '[)')` uses inclusive-start, exclusive-end notation (PostgreSQL standard)
- Adjacent ranges (e.g., end=2024-12-31, start=2025-01-01) are allowed
- Different tenants can have same date ranges (tenant_id is part of exclusion key)
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] **Regression baseline captured** (non-integration and total test counts recorded)
- [ ] **btree_gist extension enabled** in database
- [ ] **Pre-migration data validation completed** (queries run for all 6 tables)
- [ ] **Zero overlapping records found** OR overlaps manually resolved
- [ ] **Manual Alembic migration created** (not autogenerate)
- [ ] **Migration includes all 6 EXCLUDE constraints**
- [ ] **Migration downgrade() fully implemented**
- [ ] **Migration applied successfully** (`alembic upgrade head` completes without errors)
- [ ] **All 18+ new tests written and passing**
- [ ] **Use session.query() in all tests** (not session.exec() - avoids deprecation warnings)
- [ ] **ALL existing tests still passing** - Zero regression
- [ ] **Non-integration tests:** 508+ passing (490 baseline + 18+ new)
- [ ] **100% test pass rate** - No failing tests
- [ ] **Database verification query** confirms all 6 constraints active
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` works)
- [ ] **Project plan document updated** with implementation summary (line 1081)

**Zero Tolerance Policy:**
- **Any failing test = INCOMPLETE**
- **Test pass rate MUST be 100%**
- **Regression baseline MUST be maintained or exceeded**
- If tests fail after 10+ attempts, create detailed fix document but mark task incomplete

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Task 10 Details (line 1081)** ⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **GOLDEN MASTER**
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations

### Backend Code (Files to Review - NOT Modify)
- `backend/app/models/catalog.py` - TenantMarkupVersion, SupplierItemPrice, TaxRateVersion
- `backend/app/models/quoting.py` - PricebookItemVersion
- `backend/app/models/billing.py` - ProductPlanVersion, ProductPlanProductFeatureVersion

**Note:** SQLModel classes do NOT need modification because EXCLUDE constraints cannot be defined in `__table_args__`. All implementation is in the migration file.

### Migration (To Create)
- `backend/migrations/versions/2026_04_XX_HHMM-*_add_temporal_exclusion_constraints_task10.py` - Manual migration

### Tests (To Create)
- `backend/tests/test_temporal_exclusion_constraints_task10.py` - 18+ tests minimum

---

## Risk Assessment

**Data Validation Risk:** HIGH
- **Risk:** Existing data may have overlapping date ranges that violate new constraints
- **Mitigation:** Run comprehensive pre-migration validation queries for all 6 tables
- **Resolution:** Manually resolve overlaps by adjusting `effective_to` dates or deleting duplicate versions

**Performance Impact:** MEDIUM
- **Impact:** GIST indexes are slower than B-tree for insert/update operations
- **Measurement:** Monitor insert/update performance on versioned tables after migration
- **Acceptable:** <10% insert performance degradation (worthwhile tradeoff for data integrity)

**Rollback Complexity:** LOW
- **Rollback:** Simple `DROP CONSTRAINT` statements in downgrade()
- **Testing:** Verify downgrade → upgrade cycle works without errors
- **Note:** Do NOT drop btree_gist extension in downgrade (may be used by other features)

**Extension Dependency:** LOW
- **Dependency:** Requires btree_gist PostgreSQL extension
- **Availability:** Built-in extension available in all PostgreSQL 9.2+ versions (we use PostgreSQL 17)
- **Production:** No additional installation required on AWS RDS

---

## Notes

- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **MCP Server Available:** Use `postgres-local` MCP server for direct database queries
- **Deprecation Warnings:** Use `session.query()` not `session.exec()` in all tests
- **Regression Testing:** Capture baseline BEFORE, verify AFTER - both non-integration and total
- **Golden Master Authority:** The JSON schema is the single source of truth
- **Zero Regression Policy:** All existing tests MUST still pass after changes
- **Manual Migration:** Use `alembic revision` (not autogenerate) for EXCLUDE constraints
- **Cost Impact:** Zero cost impact (btree_gist is free, performance impact negligible)
- **Production Safe:** Backward compatible (only adds constraints, doesn't modify data)

**Important Patterns:**
- **tstzrange() Syntax:** `tstzrange(start_column, end_column, '[)')` - inclusive start, exclusive end
- **EXCLUDE Constraint:** `EXCLUDE USING GIST (equality_column WITH =, range_column WITH &&)`
- **Pre-Migration Validation:** Always check for existing violations before adding constraints
- **Test Isolation:** Each test should create its own data to avoid interference

**If you get stuck:**
- Check the Golden Master JSON for exact specifications
- Review similar completed tasks (Tasks 8, 9) for patterns
- Use MCP server to query database state
- Verify virtual environment is activated for all commands
- Consult PostgreSQL docs on GIST indexes and EXCLUDE constraints

---

## Example Task Flow

```bash
# ============================================
# PHASE 1: ESTABLISH BASELINE
# ============================================

# 1. Activate virtual environment
cd backend
source .venv/bin/activate

# 2. Capture non-integration baseline
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 490 passed

# 3. Capture total baseline
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 517 passed

# ============================================
# PHASE 2: VALIDATE DATA
# ============================================

# 4. Check for overlapping data (all 6 tables)
# Use MCP server postgres-local to run validation queries
# Example for tenant_markup_version:
# SELECT a.id, b.id FROM tenant_markup_version a
# JOIN tenant_markup_version b ON a.tenant_id = b.tenant_id AND a.id < b.id
# WHERE tstzrange(a.effective_from, a.effective_to, '[)') && 
#       tstzrange(b.effective_from, b.effective_to, '[)');

# 5. Resolve any overlaps found
# Manually adjust effective_to dates or delete duplicate versions
# Document all cleanup performed

# ============================================
# PHASE 3: CREATE MIGRATION
# ============================================

# 6. Create manual migration
alembic revision -m "add_temporal_exclusion_constraints_task10"
# New file created: backend/migrations/versions/2026_04_XX_HHMM-HASH_add_temporal_exclusion_constraints_task10.py

# 7. Edit migration file
# - Add CREATE EXTENSION IF NOT EXISTS btree_gist in upgrade()
# - Add all 6 EXCLUDE constraints
# - Add all 6 DROP CONSTRAINT in downgrade()

# 8. Apply migration
alembic upgrade head

# ============================================
# PHASE 4: VERIFY DATABASE
# ============================================

# 9. Verify btree_gist extension (using MCP server)
# SELECT * FROM pg_extension WHERE extname = 'btree_gist';

# 10. Verify all constraints exist (using MCP server)
# SELECT conname, conrelid::regclass, contype 
# FROM pg_constraint 
# WHERE conname LIKE '%overlap%';
# Expected: 6 rows with contype='x'

# ============================================
# PHASE 5: TEST
# ============================================

# 11. Create test file
# backend/tests/test_temporal_exclusion_constraints_task10.py
# Write 18+ tests (3 per table)
# REMEMBER: Use session.query() not session.exec()

# 12. Run new tests only
pytest tests/test_temporal_exclusion_constraints_task10.py -v
# Expected: 18+ passed

# ============================================
# PHASE 6: REGRESSION VERIFICATION
# ============================================

# 13. Run non-integration regression tests
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 508+ passed (490 + 18)

# 14. Run ALL tests (full regression)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 535+ passed (517 + 18)

# 15. Verify 100% pass rate
# If any failures → FIX IMMEDIATELY

# ============================================
# PHASE 7: ROLLBACK TEST
# ============================================

# 16. Test migration reversibility
alembic downgrade -1
alembic upgrade head
pytest tests/test_temporal_exclusion_constraints_task10.py -v
# Expected: Still 18+ passed

# ============================================
# PHASE 8: DOCUMENTATION
# ============================================

# 17. Update project plan document
# Edit dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md
# Find Task 10 section (line 1081)
# Add completion details, test counts, implementation notes
```

---

## Questions to Ask

**Before starting:**
1. Have I reviewed the Golden Master JSON for ALL temporal exclusion constraints?
2. Have I captured the regression baseline (non-integration AND total test counts)?
3. Have I activated the virtual environment?
4. Do I understand the difference between autogenerate and manual migrations?
5. Do I know how to use the postgres-local MCP server for validation queries?

**During implementation:**
1. Have I run pre-migration validation queries for ALL 6 tables?
2. Have I resolved any overlapping data found?
3. Am I using manual migration (not autogenerate)?
4. Have I included CREATE EXTENSION IF NOT EXISTS btree_gist?
5. Am I using `session.query()` instead of `session.exec()` in tests?
6. Are all new tests passing?
7. Am I documenting decisions and issues as I go?

**After implementation:**
1. Did I verify btree_gist extension is enabled?
2. Did I verify all 6 constraints exist in pg_constraint?
3. Did I run BOTH non-integration and total regression tests?
4. Do I have 100% test pass rate (no failures)?
5. Did baseline tests increase by exactly the number of new tests I added?
6. Have I updated the project plan document (line 1081)?
7. Can the migration be rolled back cleanly?

---

**Ready to Begin!** 🚀

1. ✅ Capture regression baseline (non-integration and total)
2. 🔍 Validate existing data for overlaps (all 6 tables)
3. 🛠️ Create manual migration with btree_gist + 6 EXCLUDE constraints
4. 📝 Apply migration
5. ✅ Create comprehensive tests (18+ tests, use session.query())
6. 🔄 Run regression tests
7. 📚 Update project plan document (line 1081)

Remember: Virtual environment required, use postgres-local MCP server, manual migration (not autogenerate), avoid session.exec(), maintain 100% pass rate!
