# Task 2: Pre-Migration Data Validation

**Reference:** `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md` - Task 2
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` - **Notification, Idempotency & Index Analysis** ⭐
- Current Live Database (Phase 5.2 Post-State)
**Type:** Phase 5.3 - Pre-Migration Data Validation
**Priority:** CRITICAL
**Change Type:** DATA VALIDATION + CONSTRAINT READINESS CHECK

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

## Current Task: Pre-Migration Data Validation

**Effort:** 0.25 days
**Gap Reference:** Phase 5.3 Analysis - Notification/Idempotency/Index/Trigger Gaps
**Change Type:** DATA VALIDATION + CONSTRAINT READINESS CHECK
**Dependencies:** None (can run independently)
**CRITICAL:** Validation MUST pass before generating migration

This task verifies that the database is ready for Phase 5.3 migration by checking for data violations that would prevent constraint creation or trigger attachment. All validation queries MUST return expected results before proceeding to Task 3 (migration generation).

### What Needs to Be Validated

**Critical Pre-Flight Checks:**

| Validation | Query Type | Expected Result | Failure Impact |
|------------|-----------|-----------------|----------------|
| **Invoice Idempotency Duplicates** | SELECT with GROUP BY HAVING | 0 rows | Migration fails - cannot create unique constraint |
| **Quote Idempotency Duplicates** | SELECT with GROUP BY HAVING | 0 rows | Migration fails - cannot create unique constraint |
| **Payment Idempotency Duplicates** | SELECT with GROUP BY HAVING | 0 rows | Migration fails - cannot create unique constraint |
| **Trigger Function: `audit.log_changes()`** | pg_proc query | 1 row (function exists) | Migration fails - trigger creation blocked |
| **Trigger Function: `guard_created_fields_immutable()`** | pg_proc query | 1 row (function exists) | Migration fails - trigger creation blocked |
| **Data Preservation Baseline** | Row count query | Store count for verification | Cannot verify data preservation post-migration |

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

### 1. Idempotency Constraint Pre-Migration Validation is MANDATORY

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

### 2. Trigger Function Dependencies Must Exist

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

### 3. Data Preservation Baseline (For Column Rename Verification)

**CRITICAL:** Store row count before migration to verify data preservation after column rename.

**Validation Query:**
```sql
-- Count existing records and provider_response values
SELECT 
    COUNT(*) as total_records,
    COUNT(provider_response) as records_with_provider_response
FROM notification_delivery_attempt;
-- Store these numbers for post-migration verification
```

**Why This Matters:**
- The `provider_response` column will be renamed to `details` in the migration
- Data MUST be preserved (not dropped and recreated)
- Post-migration, `COUNT(details)` should equal pre-migration `COUNT(provider_response)`

---

## Requirements

### Validation Queries (Run via postgres-local MCP Server)

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

---

## ⚠️ CRITICAL: Coding Agent Best Practices (From Previous Phases)

### 1. Use MCP Server Correctly

When using the `postgres-local` MCP server:
- ✅ **CORRECT:** Single-line SQL (no `\n` characters)
- ❌ **WRONG:** Multi-line SQL with escaped newlines

**Example:**
```python
# ✅ CORRECT - Single line
mcp.query("SELECT tenant_id, idempotency_key, COUNT(*) FROM invoice WHERE idempotency_key IS NOT NULL GROUP BY tenant_id, idempotency_key HAVING COUNT(*) > 1")

# ❌ WRONG - Multi-line with \n
mcp.query("SELECT tenant_id, idempotency_key\nFROM invoice\nWHERE...")
```

---

### 2. Document All Validation Results

Create a validation report documenting:
1. Each query executed
2. Expected result
3. Actual result
4. Pass/Fail status
5. Any remediation needed

**Format:**
```markdown
## Phase 5.3 Pre-Migration Validation Report

**Date:** YYYY-MM-DD
**Database:** [database name]
**Baseline Tests:** 652/652 unit, 679/679 total

### Validation 1: Invoice Idempotency Duplicates
- **Query:** SELECT tenant_id, idempotency_key, COUNT(*) ...
- **Expected:** 0 rows
- **Actual:** 0 rows
- **Status:** ✅ PASS

### Validation 2: Quote Idempotency Duplicates
- **Query:** SELECT tenant_id, idempotency_key, COUNT(*) ...
- **Expected:** 0 rows
- **Actual:** 0 rows
- **Status:** ✅ PASS

[... continue for all validations ...]

## Final Recommendation

- [ ] ALL validations passed - PROCEED to Task 3 (Migration Generation)
- [ ] BLOCKED - Remediation required (see details above)
```

---

## Success Criteria for Task 2

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### Data Validation
- [ ] **Regression baseline captured** (652/652 unit, 679/679 total)
- [ ] **Invoice idempotency duplicate query returned 0 rows**
- [ ] **Quote idempotency duplicate query returned 0 rows**
- [ ] **Payment idempotency duplicate query returned 0 rows**
- [ ] **`audit.log_changes()` function verification returned 1 row**
- [ ] **`guard_created_fields_immutable()` function verification returned 1 row**
- [ ] **`notification_delivery_attempt` row count stored for verification**

### Documentation
- [ ] **Validation report created** with all query results
- [ ] **All pass/fail statuses documented**
- [ ] **Baseline counts recorded** for post-migration verification
- [ ] **Any remediation needs identified and documented**

### Ready State
- [ ] **If ALL validations passed:** APPROVED to proceed to Task 3
- [ ] **If ANY validation failed:** BLOCKED - remediation plan created

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md` - **Master Plan** ⭐⭐⭐
- `dev-docs/analysis/phase-5.3-db-schema-sync-9-analysis.md` - **Comprehensive Gap Analysis** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Database Tables (3 tables with idempotency keys)
- `backend/app/models/billing.py` - Invoice, Payment
- `backend/app/models/quoting.py` - Quote

---

## Risk Assessment

**For Task 2 (Pre-Migration Validation):**
- **Duplicate Data Risk:** MEDIUM (idempotency duplicates possible in test environment)
- **Trigger Function Risk:** LOW (functions should exist from previous schema setup)
- **False Negative Risk:** LOW (queries are straightforward SELECT statements)
- **Blocking Risk:** MEDIUM (if validation fails, Task 3 cannot proceed)
- **Mitigation:** Clear escalation path for any failures, remediation options documented

---

## Notes

### Important Patterns to Follow
- **Zero Duplicates:** Pre-migration validation MUST show 0 duplicate idempotency keys
- **Trigger Functions:** Verify functions exist before creating triggers
- **Data Preservation:** Store baseline counts for post-migration verification
- **MCP Server:** Use single-line SQL without `\n` characters
- **Documentation:** Create comprehensive validation report

### Task 2 Specific
- **No Code Changes:** This task only runs queries and documents results
- **No Migration:** Migration creation happens in Task 3
- **Blocking Task:** Task 3 cannot start until Task 2 passes
- **Remediation:** If validation fails, create cleanup plan before proceeding

### If You Get Stuck
- Use `postgres-local` MCP server to check database state
- Review Phase 5.3 plan for detailed specifications
- Verify all validation queries are correct
- Check for typos in table/column names
- Ask for help if spending >30 minutes on single issue

---

**Ready to Begin!** 🚀

### Task 2 Checklist:
1. ✅ Capture baseline (652/652 unit, 679/679 total)
2. 🔍 **Run invoice idempotency duplicate query via MCP server**
3. 🔍 **Run quote idempotency duplicate query via MCP server**
4. 🔍 **Run payment idempotency duplicate query via MCP server**
5. 🔍 **Verify `audit.log_changes()` function exists**
6. 🔍 **Verify `guard_created_fields_immutable()` function exists**
7. 🔍 **Store `notification_delivery_attempt` row count**
8. 📝 **Create validation report with all results**
9. ⚠️ **If ANY validation fails: STOP and create remediation plan**
10. ✅ **If ALL validations pass: Document approval to proceed to Task 3**

Remember: This task is a **CRITICAL GATEKEEPER** - if validation fails, the entire Phase 5.3 migration will fail. Take time to verify each query returns expected results and document everything thoroughly!
