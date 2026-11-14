# Task 11 & 12: Phase 4 - Documentation & Naming Alignment

**Reference:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - Phase 4, Tasks 11 & 12
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - Production SQL Dump
**Type:** Phase 4 - Documentation & Naming Alignment
**Priority:** LOW (documentation only)
**Change Type:** JSON_UPDATE + DOCUMENTATION

---

## Context

This is **Phase 4.6 - DB Sync v#2**, a follow-up reconciliation after completing Phase 4.5. Phase 4 focuses on **documentation alignment only** - no database migrations required.

**Key Principle:** This is about **documentation completeness**, not functional changes. The database already has all correct implementations; we're updating the JSON schema to reflect production reality.

---

## What Was Completed in Phase 4.5

**Phase 4.5 Status:** ✅ COMPLETE (March 30 - April 1, 2026)
- ✅ 572/572 tests passing (100%)
- ✅ 100% alignment between physical database and Golden Master JSON achieved
- ✅ All unique, check, and temporal exclusion constraints implemented
- ✅ All 293 triggers verified and functional

**Current Baseline:** 575/575 tests passing (100%)

**What Was Completed in Phase 4.6 So Far:**
- ✅ Phase 1: COMPLETE (3/3 tasks) - discount_version table, check constraints, email regex
- ✅ Phase 2: COMPLETE (5/5 tasks) - Function optimizations backported to JSON
- ✅ Phase 3: COMPLETE (2/2 tasks) - Data type alignment, VARCHAR standardization

**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full Phase 4.5 history

---

## Current Tasks: Phase 4 - Documentation & Naming Alignment

**Combined Effort:** 1 day
**Gap Reference:** Phase 4.6 Analysis - Section 3 (Audit Functions) & Section 6 (Naming Conventions)
**Change Type:** JSON_UPDATE + DOCUMENTATION

This phase completes the final documentation gaps between the JSON schema and the production SQL database. Both tasks are documentation-only updates that make the JSON schema a complete and accurate representation of the production database.

### Task 11: Add Missing Audit Functions to JSON Schema

**Problem:** The SQL database contains 2 audit functions that are fully implemented and actively used by 85+ triggers, but these functions are not documented in the JSON schema:
1. `audit.log_changes()` - Standard audit logging (UUID primary keys)
2. `audit.log_changes_code_pk()` - Audit logging for code-based primary keys

**Why This Matters:** The JSON schema should be the complete documentation source. Without these functions documented, developers cannot understand the full audit system.

### Task 12: Standardize FK/Index Naming Conventions

**Problem:** The JSON schema originally specified strict naming conventions (`fk_table_ref`, `idx_table_col`), but the SQL database uses ORM-generated names (`table_ref_fkey`, `ix_table_col`).

**Decision:** Accept the SQL database naming conventions as the standard. Renaming 100+ constraints is risky and provides no functional benefit.

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `audit.log_changes()` | Function definition missing from JSON | SQL→JSON | LOW |
| **2** | `audit.log_changes_code_pk()` | Function definition missing from JSON | SQL→JSON | LOW |
| **3** | Audit triggers (85+) | Trigger definitions not documented in JSON | SQL→JSON | LOW |
| **4** | FK/Index names | JSON uses `fk_*`/`idx_*`, SQL uses `*_fkey`/`ix_*` | SQL→JSON | LOW |

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

**Record the output:** `575/575 tests passing` (Phase 4.6 baseline after Phase 3 completion)

### Step 3: Document Your Baseline

**Write down this number before proceeding:**
- Baseline: `575/575` passing

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## Requirements

### 1. Implementation Details - Task 11: Audit Functions

**Problem:** The audit system is fully functional but not documented in the JSON schema.

**SQL Database Reality (What's Actually Working):**

**Function 1: `audit.log_changes()`**
```sql
-- Production SQL (from phase-4.6 dump)
CREATE OR REPLACE FUNCTION audit.log_changes()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'audit'
AS $$
DECLARE
    audit_row audit.record_history;
    excluded_cols text[] := ARRAY[]::text[];
    recorded_at timestamptz;
BEGIN
    -- Function body (extract from SQL dump)
    -- Handles UUID primary keys
    -- Logs INSERT/UPDATE/DELETE operations
    -- Uses TG_TABLE_NAME, TG_OP, etc.
END;
$$;
```

**Function 2: `audit.log_changes_code_pk()`**
```sql
-- Production SQL (from phase-4.6 dump)
CREATE OR REPLACE FUNCTION audit.log_changes_code_pk()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'audit'
AS $$
DECLARE
    audit_row audit.record_history;
    excluded_cols text[] := ARRAY[]::text[];
    recorded_at timestamptz;
BEGIN
    -- Function body (extract from SQL dump)
    -- Handles code-based primary keys (e.g., service.code)
    -- Otherwise identical to log_changes()
END;
$$;
```

**JSON Schema Gap (What's Missing in JSON):**
The `pilot-db-schema-v2.6h.json` `functions` array does not contain these two audit functions.

**JSON Schema Fix Required:**
```json
{
  "functions": [
    {
      "schema": "audit",
      "name": "log_changes",
      "returns": "trigger",
      "language": "plpgsql",
      "security": "definer",
      "search_path": "public, audit",
      "body": "-- [FULL FUNCTION BODY FROM SQL DUMP]"
    },
    {
      "schema": "audit",
      "name": "log_changes_code_pk",
      "returns": "trigger",
      "language": "plpgsql",
      "security": "definer",
      "search_path": "public, audit",
      "body": "-- [FULL FUNCTION BODY FROM SQL DUMP]"
    }
  ]
}
```

**Audit Triggers to Document (Optional):**
All 85+ triggers named `audit_<table>_changes` should optionally be added to the JSON schema's `triggers` array for completeness.

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED**
- The database already has the correct implementation
- This is a JSON documentation update only
- No `alembic revision` required
- Verification is comparing JSON to SQL dump

---

### 2. Implementation Details - Task 12: Naming Conventions

**Problem:** The JSON schema specifies one naming convention, but the SQL database uses a different (ORM-generated) convention.

**SQL Database Reality (ORM-Generated Names):**
```sql
-- Foreign Keys: <table>_<column>_fkey
ALTER TABLE quote
ADD CONSTRAINT quote_tenant_id_fkey
FOREIGN KEY (tenant_id) REFERENCES tenant(id);

-- Indexes: ix_<table>_<column>
CREATE INDEX ix_quote_tenant_id ON quote(tenant_id);
```

**JSON Schema Gap (Idealized Names):**
```json
{
  "foreign_keys": [
    {"name": "fk_quote_tenant"}  // ← JSON standard (not used in SQL)
  ],
  "indexes": [
    {"name": "idx_quote_tenant_id"}  // ← JSON standard (not used in SQL)
  ]
}
```

**Decision:** **Accept SQL naming as standard** - Do not rename 100+ constraints

**JSON Schema Fix Required:**
1. **Update Naming Convention Documentation:**
   - Add a `design_decisions` entry explaining ORM-generated naming acceptance
   - Document the actual patterns: `*_fkey`, `ix_*`, `*_key` (unique), `*_check`

2. **Update FK/Index Names in JSON:**
   - Update all foreign key names to match SQL reality (e.g., `quote_tenant_id_fkey`)
   - Update all index names to match SQL reality (e.g., `ix_quote_tenant_id`)

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED**
- The database already has correct (ORM-generated) names
- This is a JSON documentation update only
- No renaming of constraints required

---

### 3. Implementation Order

**For JSON_UPDATE Tasks (Phase 4):**

1. **✅ Establish Regression Baseline** (575/575 tests)
2. **Extract Audit Functions from SQL Dump**
   - Read `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql`
   - Locate `audit.log_changes()` function definition (search for "CREATE OR REPLACE FUNCTION audit.log_changes")
   - Locate `audit.log_changes_code_pk()` function definition
   - Copy complete function bodies including all DECLARE variables and logic
3. **Update JSON Schema - Audit Functions**
   - Open `dev-docs/db-design/pilot-db-schema-v2.6h.json`
   - Add both audit functions to the `functions` array
   - Ensure proper JSON escaping for function bodies (newlines, quotes)
   - Place near other audit-related definitions if present
4. **Optional: Document Audit Triggers**
   - Extract all trigger names matching pattern `audit_*_changes` from SQL dump
   - Add to JSON schema `triggers` array if time permits
5. **Update JSON Schema - Naming Conventions**
   - Add design decision to `design_decisions` array explaining ORM naming acceptance
   - Review all FK names in JSON schema and update to match SQL patterns
   - Review all index names in JSON schema and update to match SQL patterns
   - Document accepted patterns: `*_fkey`, `ix_*`, `*_key`, `*_check`, `*_excl`
6. **Document JSON Changes** (see "JSON Change Tracking" section below)
7. **Verify Database (No Changes Expected)**
   ```sql
   -- Confirm audit functions exist
   SELECT proname, prosrc FROM pg_proc 
   WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'audit')
   AND proname IN ('log_changes', 'log_changes_code_pk');
   
   -- Count audit triggers
   SELECT COUNT(*) FROM pg_trigger WHERE tgname LIKE 'audit_%_changes';
   ```
8. **Run Existing Tests (Verify No Regression)**
   ```bash
   pytest --ignore=tests/integration/ tests/ -v
   # Expected: 575/575 passing (no change)
   ```
9. **Update Documentation**

---

### 4. Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 575 existing tests MUST still pass**
- **No new tests required** (documentation-only changes)
- **Target: 100% pass rate**

**For JSON_UPDATE Tasks (Phase 4):**

**No New Tests Required**
- The database logic already works (proven by 575/575 passing tests)
- This is documentation alignment only
- Audit functions have been working in production since Phase 4.5

**Verification Tests (Manual):**
- Use postgres-local MCP to confirm audit functions exist
- Verify function definitions match JSON updates
- Confirm naming conventions match between JSON and SQL

---

### 5. JSON Change Tracking

**For JSON_UPDATE Tasks:** Provide a summary of all JSON changes for manual review.

**Format:**
```markdown
## JSON Schema Changes for Tasks 11 & 12

**File:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`

### Task 11: Audit Functions Added

1. **Function: `audit.log_changes`**
   - **Location:** `functions` array (near other audit functions)
   - **Before:** MISSING
   - **After:** Complete function definition backported from SQL dump
   - **Reason:** Document production-tested audit logging for UUID primary keys
   - **Lines:** [X] (approx)

2. **Function: `audit.log_changes_code_pk`**
   - **Location:** `functions` array (near other audit functions)
   - **Before:** MISSING
   - **After:** Complete function definition backported from SQL dump
   - **Reason:** Document production-tested audit logging for code primary keys
   - **Lines:** [Y] (approx)

3. **Optional: Audit Triggers (85+)**
   - **Location:** `triggers` array (if added)
   - **Before:** Missing trigger documentation
   - **After:** All `audit_*_changes` triggers documented
   - **Reason:** Complete documentation of audit system

### Task 12: Naming Conventions Updated

1. **Design Decision: ORM Naming Acceptance**
   - **Location:** `design_decisions` array
   - **Before:** Idealized naming convention (`fk_*`, `idx_*`)
   - **After:** Documented acceptance of ORM-generated names
   - **Reason:** Accept production reality, avoid risky renames

2. **Foreign Key Names**
   - **Location:** Throughout JSON schema in `foreign_keys` arrays
   - **Before:** `fk_<table>_<ref>` pattern
   - **After:** `<table>_<column>_fkey` pattern (ORM standard)
   - **Count:** ~[X] foreign keys updated
   - **Reason:** Align with SQL database reality

3. **Index Names**
   - **Location:** Throughout JSON schema in `indexes` arrays
   - **Before:** `idx_<table>_<column>` pattern
   - **After:** `ix_<table>_<column>` pattern (Alembic standard)
   - **Count:** ~[Y] indexes updated
   - **Reason:** Align with SQL database reality

### Verification:

- [ ] All JSON changes align with `aevofab-db-schema-dump-phase-4.6.sql`
- [ ] No functional database changes made (JSON doc only)
- [ ] All 575 tests still passing (no regression)
- [ ] Audit functions verified in database via MCP query
- [ ] FK/Index names sampled and verified to match SQL
```

**⚠️ USER REVIEW REQUIRED:**
The founder will manually review these JSON changes against the SQL dump to confirm accuracy.

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
- **For JSON_UPDATE tasks:** `575 passed` (no change)

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

**For JSON_UPDATE tasks:**
- If existing tests fail → Your JSON changes revealed a mismatch (investigate)
- If tests still pass → JSON documentation is correct

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md`

Find Phase 4, Tasks 11 & 12 and update with:

```markdown
### Task 11: Add Missing Audit Functions to JSON Schema

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Change Type:** JSON_UPDATE

**Implementation Summary:**

- Updated: `pilot-db-schema-v2.6h.json`
- Functions Added: `audit.log_changes`, `audit.log_changes_code_pk`
- Triggers Documented: [X] audit triggers (if added)
- Database: No changes (already correct)
- Final Results: 575/575 tests passing (100% - no regression)

**Key Changes:**
- ✅ Documented `audit.log_changes()` function from SQL dump
- ✅ Documented `audit.log_changes_code_pk()` function from SQL dump
- ✅ [Optional] Added all 85+ audit trigger definitions to JSON

**Verification:**
- Database functions verified via postgres-local MCP server
- Function definitions match SQL dump exactly
- All 575 tests passing (no regression)

---

### Task 12: Standardize FK/Index Naming Conventions

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Change Type:** JSON_UPDATE + DOCUMENTATION

**Implementation Summary:**

- Updated: `pilot-db-schema-v2.6h.json`
- Design Decision: Documented ORM naming acceptance
- FK Names Updated: ~[X] foreign keys aligned to SQL
- Index Names Updated: ~[Y] indexes aligned to SQL
- Database: No changes (already correct)
- Final Results: 575/575 tests passing (100% - no regression)

**Key Changes:**
- ✅ Added design decision explaining ORM naming convention acceptance
- ✅ Updated FK names from `fk_*` to `*_fkey` pattern
- ✅ Updated index names from `idx_*` to `ix_*` pattern
- ✅ Documented accepted patterns: `*_fkey`, `ix_*`, `*_key`, `*_check`

**Verification:**
- Sampled 10+ FK/index names verified to match SQL dump
- Design decision documented in JSON schema
- All 575 tests passing (no regression)
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASKS AS DONE:**

### For Task 11: Audit Functions
- [ ] **Regression baseline captured** (575/575 tests)
- [ ] **SQL dump reviewed** for both audit functions
- [ ] **JSON schema updated** with `audit.log_changes()` definition
- [ ] **JSON schema updated** with `audit.log_changes_code_pk()` definition
- [ ] **Optional: Audit triggers documented** in JSON schema
- [ ] **JSON changes documented** for manual review
- [ ] **Database verification confirms** both functions exist (via MCP)
- [ ] **ALL 575 tests still passing** (no regression)

### For Task 12: Naming Conventions
- [ ] **Regression baseline captured** (575/575 tests)
- [ ] **Design decision documented** explaining ORM naming acceptance
- [ ] **FK names updated** to match SQL patterns (`*_fkey`)
- [ ] **Index names updated** to match SQL patterns (`ix_*`)
- [ ] **Naming patterns documented** in design_decisions
- [ ] **JSON changes documented** for manual review
- [ ] **Database verification** sampled (10+ FK/index names match SQL)
- [ ] **ALL 575 tests still passing** (no regression)

### For Both Tasks (Phase 4 Complete):
- [ ] **100% test pass rate** - No failing tests
- [ ] **Zero regression** - Baseline maintained at 575/575
- [ ] **JSON schema is complete** - All production functions documented
- [ ] **Project plan document updated** with completion status

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - **Tasks 11 & 12 Details** ⭐
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON** ⭐
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - **Production SQL Dump** ⭐

### Migrations (Reference for Audit Functions)
- `backend/migrations/versions/2026_03_30_2102-df5b8f15d58e_fix_audit_log_changes_function.py` - audit.log_changes()
- `backend/migrations/versions/2026_03_30_2108-e13a4e2ff3dd_fix_audit_log_changes_code_pk_function.py` - audit.log_changes_code_pk()

---

## Risk Assessment

**Data Validation Risk:** LOW
- No database changes
- JSON documentation update only
- **Mitigation:** None needed (documentation-only)

**Regression Risk:** LOW
- No code changes
- Database already has correct implementations
- **Mitigation:** Verify 575/575 baseline maintained

**JSON Documentation Risk:** LOW
- JSON changes might not perfectly match SQL reality
- **Mitigation:** Founder manually reviews all JSON changes against SQL dump

**Naming Convention Risk:** VERY LOW
- Accepting existing SQL names (no renames)
- **Mitigation:** Sample verification of 10+ names

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Dual Master Strategy:** JSON is documentation authority, SQL dump is runtime authority
- **Phase 4 = Documentation Only:** NO database migrations for this phase
- **Zero Regression Policy:** All 575 existing tests MUST pass after changes

### Phase 4 Specific
- **This is documentation completion** - making JSON schema comprehensive
- **Database is correct** - all functions already work in production
- **Simple work** - extract from SQL, paste into JSON (with proper escaping)
- **No testing required** - existing tests prove database correctness

### If You Get Stuck
- Check the SQL dump for exact production definitions
- Use `postgres-local` MCP server to query database
- Verify JSON syntax is valid after edits (no trailing commas, proper escaping)
- For audit functions: search SQL dump for "CREATE OR REPLACE FUNCTION audit."
- For naming: sample 5-10 FKs/indexes to understand the pattern

---

## Example Task Flow

### For JSON_UPDATE Tasks (Phase 4):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep passed | tail -1
# Record: 575 passed

# 2. Extract audit functions from SQL dump
grep -A 100 "CREATE OR REPLACE FUNCTION audit.log_changes()" \
  dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql

grep -A 100 "CREATE OR REPLACE FUNCTION audit.log_changes_code_pk()" \
  dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql

# 3. Update JSON schema
# [Edit dev-docs/db-design/pilot-db-schema-v2.6h.json]
# Add both functions to "functions" array
# Escape newlines and quotes properly for JSON

# 4. Extract FK/index names pattern
grep "CONSTRAINT.*_fkey" dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql | head -10
grep "CREATE INDEX ix_" dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql | head -10

# 5. Update JSON schema naming conventions
# [Edit dev-docs/db-design/pilot-db-schema-v2.6h.json]
# Add design decision for ORM naming
# Update FK/index names throughout

# 6. Document changes
# [Create JSON change summary for founder review]

# 7. Verify database (no changes expected)
# [Use postgres-local MCP to confirm functions exist]

# 8. Regression check
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep passed | tail -1
# Expected: 575 passed (no change)

# 9. Update docs
# [Edit phase-4.6-db-schema-sync-2-plan.md]
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 575/575 baseline?
2. Do I have access to the SQL dump file?
3. Can I use the postgres-local MCP server to verify database functions?

**During implementation:**
1. Am I properly escaping function bodies for JSON (newlines as `\n`, quotes as `\"`)?
2. For naming conventions: Have I sampled enough FK/index names to understand the pattern?
3. Am I documenting all changes for founder review?

**After implementation:**
1. Do I have 100% test pass rate (575/575)?
2. Did baseline stay at 575/575 (no regression)?
3. Have I updated the project plan document?
4. Have I provided a clear change list for founder review?
5. Can I verify audit functions exist in database via MCP?

---

**Ready to Begin!** 🚀

### JSON_UPDATE Task Checklist (Phase 4):
1. ✅ Capture baseline (575/575)
2. 📖 Extract audit functions from SQL dump
3. ✏️ Update JSON schema with audit functions
4. 📖 Extract FK/index naming patterns from SQL
5. ✏️ Update JSON schema with ORM naming conventions
6. 📋 Document JSON changes for review
7. ✅ Verify database via MCP (no changes)
8. 🔄 Run regression tests (expect 575/575)
9. 📚 Update project plan

Remember: Phase 4 is **documentation completion** only. Keep it simple, extract from SQL, paste into JSON, and document thoroughly!
