# Task 3: Comprehensive Database-Layer Verification

**Reference:** `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` - Task 3
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/required-defaults-columns-json.md` - **Authoritative Checklist (200 fields)**
- Current Live Database (Phase 5.0 Post-Migration State)
**Type:** Phase 5.0 - Server Defaults Verification
**Priority:** CRITICAL
**Change Type:** DATABASE VERIFICATION (DB-DIRECT QUERIES)

---

## Context

This is **Phase 5.0 - DB Sync v#6 - Task 3**, the final verification phase. Tasks 1 and 2 have been completed:

- ✅ **Task 1:** All 200 SQLModel fields updated with `server_default=` 
- ✅ **Task 2:** Migration generated, manually verified, and applied successfully (198/200 fields with server defaults)
- ✅ **Unit Tests:** All 640/640 unit tests passing (100%)
- ✅ **Integration Tests:** All 27/27 integration tests passing

**Current Task:** Validate that server defaults are **actually enforced at the PostgreSQL layer** through direct database queries, bypassing the Python ORM entirely.

**Critical Focus:** Since the unit tests already validate ORM behavior and are passing, this task focuses exclusively on **database-level verification** using raw SQL queries to prove that defaults exist in the PostgreSQL schema itself, not just in Python code.

---

## What Was Completed in Previous Tasks

**Task 1 Status:** ✅ COMPLETE (April 9, 2026)
- 200/200 fields updated across 9 model files
- All Python models have `server_default=` implemented
- Syntax validated for all data types

**Task 2 Status:** ✅ COMPLETE (April 9, 2026)
- Migration: `2026_04_09_1230-cfdeb13d3b22_phase_5_0_add_server_defaults_200_fields.py`
- 198 fields with server defaults applied (197 ALTER + 1 ADD)
- Migration tested forward, backward, and re-applied successfully
- 2 missing columns identified: `entity_type.is_default`, `notification_delivery_attempt.retryable`

**Current Baseline:** 640/640 unit tests, 667/667 total tests passing (100%)

---

## Current Task: Database-Layer Verification

**Effort:** 0.5-1.0 days
**Gap Reference:** Phase 5.0 Analysis - Server Defaults Enforcement
**Change Type:** DATABASE VERIFICATION ONLY (Read-Only Operations)

This task validates that the 198 server defaults are enforced at the PostgreSQL layer through direct database inspection and testing, completely bypassing the Python application layer.

### What Needs to Be Verified

**Primary Verification Methods:**

1. **`information_schema` Inspection** - Query PostgreSQL metadata to confirm `column_default` is non-NULL for all 198 fields
2. **Raw SQL INSERT Tests** - Execute INSERT statements without values for default fields to prove database enforces them
3. **Schema Dump Comparison** - Compare pre/post schema dumps to document the changes
4. **Missing Columns Analysis** - Verify the 2 missing columns are documented and explained

### Tools Available

- You have access to the postgres-local MCP server to query the DB directly, in read-only mode.
- Remember that you do not need to insert any '\n' characters in the sql when creating it for the mcp server.

---

## ⚠️ BEFORE YOU START - Verify Current State

**CRITICAL:** Confirm the current database and test baseline BEFORE proceeding.

### Step 1: Verify Migration is Applied

```bash
cd backend
source .venv/bin/activate

# Check Alembic current revision
alembic current
# Expected: cfdeb13d3b22 (head) - phase_5_0_add_server_defaults_200_fields
```

### Step 2: Verify Test Baseline (Already Passing)

```bash
# Run unit tests only (concise output)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
# Expected: 640 passed

# Run all tests (concise output)
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
# Expected: 667 passed
```

**Note:** You've already confirmed these are passing. This task does NOT require writing new unit tests. Focus on **database verification only**.

---

## ⚠️ CRITICAL: Task 3 Specific Guidelines

### 1. This is DB-Direct Verification, NOT Application Testing

**What This Task IS:**
- ✅ Querying `information_schema.columns` to verify `column_default` exists
- ✅ Running raw SQL INSERT statements to prove defaults work at database layer
- ✅ Comparing schema dumps to document changes
- ✅ Generating verification reports for documentation

**What This Task IS NOT:**
- ❌ Writing new Python unit tests (already complete and passing)
- ❌ Testing ORM behavior (already validated by existing tests)
- ❌ Modifying application code or models (Task 1 already complete)
- ❌ Changing the migration (Task 2 already complete and applied)

---

### 2. Use MCP Postgres Server for Direct Database Queries

**You have read-only access to query the database directly:**

```sql
-- Example: Check server defaults via information_schema
SELECT 
    table_name, 
    column_name, 
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'tenant'
  AND column_name = 'is_active';
```

**Critical Rule:** All verification queries must go through the MCP server. Do NOT use psql commands or application code for verification.

---

### 3. Focus on the 198 Fields That Have Defaults

**From Task 2 completion report:**
- **198 fields** successfully have server defaults in the database
- **2 fields missing** (columns don't exist yet):
  - `entity_type.is_default` - Column does not exist in database
  - `notification_delivery_attempt.retryable` - Column does not exist in database

**Verification Target:** Confirm all **198 existing fields** have correct server defaults.

---

### 4. Organize Verification by Data Type

**Boolean Defaults (Majority):**
- `true` or `false`
- Example: `tenant.is_active` → `true`

**Integer Defaults:**
- Numeric values: `0`, `1`, `8500`, etc.
- Example: `tenant_settings.default_labor_rate_cents` → `8500`

**String Defaults:**
- Single-quoted strings: `'email'`, `'US'`, `'pending'`
- Example: `user.preferred_mfa_channel` → `'email'::character varying`

**JSONB Defaults:**
- Empty object with cast: `'{}'::jsonb`
- Example: `platform_role.permissions` → `'{}'::jsonb`

**DateTime Defaults:**
- Current timestamp function: `now()`
- Example: `notification_event.occurred_at` → `now()`

**tstzrange Defaults:**
- Open-ended range: `tstzrange(now(), NULL, '[)'::text)`
- Example: `tenant_markup_version.valid_period` → `tstzrange(now(), NULL, '[)'::text)`

---

## Requirements

### Verification Task: Database-Layer Server Defaults Validation

**Effort:** 0.5-1.0 days
**Scope:** 198 fields across 78 tables (2 missing columns documented separately)

#### What This Task Accomplishes

Prove beyond doubt that server defaults are enforced at the PostgreSQL layer by:
1. Querying database metadata to confirm defaults exist
2. Testing raw SQL inserts to prove defaults are applied
3. Documenting the verification results for the project plan

#### Implementation Strategy

**Phase A: information_schema Verification (Primary Method)**

**Step 1: Query All 198 Fields**

Use the MCP postgres server to execute comprehensive metadata query:

```sql
-- Query: Count fields with server defaults
SELECT 
    COUNT(*) AS fields_with_defaults
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_default IS NOT NULL
  AND (
    -- Auth models (14 fields)
    (table_name = 'tenant_user_role' AND column_name IN ('permissions', 'is_default', 'is_active')) OR
    (table_name = 'tenant_domain' AND column_name = 'is_active') OR
    (table_name = 'tenant_user_invite' AND column_name IN ('permissions', 'issued_at')) OR
    (table_name = 'auth_refresh_token' AND column_name = 'issued_at') OR
    (table_name = 'auth_mfa_otp' AND column_name IN ('issued_at', 'attempt_count')) OR
    (table_name = 'auth_password_history' AND column_name = 'changed_at') OR
    (table_name = 'sso_provider' AND column_name IN ('is_default', 'is_active')) OR
    (table_name = 'jwk_status' AND column_name IN ('is_default', 'is_signable')) OR
    
    -- Core models (15 fields)
    (table_name = 'platform_role' AND column_name IN ('permissions', 'is_default', 'is_active')) OR
    (table_name = 'user' AND column_name IN ('is_platform_user', 'failed_login_count', 'require_password_reset', 'mfa_enforced', 'preferred_mfa_channel')) OR
    (table_name = 'user_preference' AND column_name = 'permissions') OR
    (table_name = 'tenant' AND column_name = 'is_active') OR
    (table_name = 'tenant_settings' AND column_name IN ('default_labor_rate_cents', 'default_billable_labor_rate_cents', 'default_quote_validity_days', 'default_invoice_terms_days')) OR
    (table_name = 'user_endpoint' AND column_name IN ('is_primary', 'verification_status', 'consent_status')) OR
    
    -- CRM models (20 fields)
    (table_name = 'customer_lifecycle_status' AND column_name IN ('is_default', 'is_active')) OR
    (table_name = 'site_lifecycle_status' AND column_name IN ('is_default', 'is_active')) OR
    (table_name = 'address_type' AND column_name IN ('is_default', 'is_active')) OR
    (table_name = 'contact_type' AND column_name IN ('is_default', 'is_active')) OR
    (table_name = 'customer' AND column_name IN ('is_active', 'type')) OR
    (table_name = 'site' AND column_name = 'is_active') OR
    (table_name = 'contact' AND column_name = 'is_active') OR
    (table_name = 'address' AND column_name = 'country') OR
    (table_name = 'entity_contact' AND column_name = 'is_primary') OR
    (table_name = 'entity_address' AND column_name = 'is_primary') OR
    (table_name = 'contact_endpoint' AND column_name IN ('is_primary', 'verification_status', 'consent_status')) OR
    
    -- Continue for all remaining model files...
    -- (Quoting: 37 fields, Fulfillment: 14 fields, Billing: 37 fields, Catalog: 14 fields, System: 46 fields, AI: 3 fields)
    
    -- Note: Exclude entity_type.is_default and notification_delivery_attempt.retryable (columns don't exist)
  );
-- Expected Result: 198 (or close to it, accounting for any edge cases)
```

**Step 2: Sample Verification by Data Type**

Query specific examples for each data type:

```sql
-- Boolean defaults
SELECT table_name, column_name, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('tenant', 'platform_role', 'user', 'customer')
  AND column_name IN ('is_active', 'is_default', 'is_platform_user')
ORDER BY table_name, column_name;

-- Integer defaults
SELECT table_name, column_name, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('tenant_settings', 'user', 'quote_line')
  AND column_name IN ('default_labor_rate_cents', 'failed_login_count', 'quantity')
ORDER BY table_name, column_name;

-- String defaults
SELECT table_name, column_name, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('user', 'customer', 'address', 'subscription')
  AND column_name IN ('preferred_mfa_channel', 'type', 'country', 'billing_interval')
ORDER BY table_name, column_name;

-- JSONB defaults
SELECT table_name, column_name, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('platform_role', 'tenant_user_role', 'user_preference')
  AND column_name = 'permissions'
ORDER BY table_name, column_name;

-- DateTime defaults
SELECT table_name, column_name, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('notification_event', 'auth_refresh_token', 'webhook_event')
  AND column_name IN ('occurred_at', 'issued_at')
ORDER BY table_name, column_name;
```

**Step 3: Identify Any Missing Defaults**

Query to find fields that should have defaults but don't:

```sql
-- Find NOT NULL columns without defaults (excluding PKs and FKs)
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
  AND column_name NOT IN ('tenant_name', 'role_name', 'type_name', 'channel', 'default_timezone')  -- Exclude known required fields
ORDER BY table_name, column_name;
```

---

**Phase B: Raw SQL INSERT Verification (Proof of Database Enforcement)**

**Note:** These are **read-only verification queries** wrapped in transactions with ROLLBACK. No data is permanently inserted.

**Test 1: Boolean Default (tenant.is_active = TRUE)**

```sql
-- Verify tenant.is_active defaults to TRUE via raw SQL
BEGIN;

INSERT INTO tenant (tenant_name, default_timezone)
VALUES ('Test Verification Tenant', 'America/New_York')
RETURNING id, is_active;

-- Expected: Returns new id and is_active = true

ROLLBACK;
```

**Test 2: Integer Default (tenant_settings.default_labor_rate_cents = 8500)**

```sql
-- Verify integer default via raw SQL
BEGIN;

-- Create tenant first
WITH new_tenant AS (
  INSERT INTO tenant (tenant_name, default_timezone)
  VALUES ('Test Tenant for Settings', 'America/New_York')
  RETURNING id
)
INSERT INTO tenant_settings (tenant_id)
SELECT id FROM new_tenant
RETURNING tenant_id, default_labor_rate_cents, default_billable_labor_rate_cents;

-- Expected: default_labor_rate_cents = 8500, default_billable_labor_rate_cents = 10200

ROLLBACK;
```

**Test 3: String Default (user.preferred_mfa_channel = 'email')**

```sql
-- Note: User table has complex dependencies (tenant, role, etc.)
-- Verify via information_schema instead of INSERT
SELECT column_default
FROM information_schema.columns
WHERE table_name = 'user' AND column_name = 'preferred_mfa_channel';

-- Expected: 'email'::character varying
```

**Test 4: JSONB Default (platform_role.permissions = '{}')**

```sql
-- Verify JSONB default via raw SQL
BEGIN;

INSERT INTO platform_role (role_name, role_description)
VALUES ('Test Verification Role', 'Testing JSONB defaults')
RETURNING id, permissions;

-- Expected: Returns new id and permissions = {}

ROLLBACK;
```

**Test 5: DateTime Default (notification_event.occurred_at = now())**

```sql
-- Verify DateTime default via raw SQL
BEGIN;

-- Create notification_type first
WITH new_type AS (
  INSERT INTO notification_type (type_name, channel)
  VALUES ('test_verification_type', 'email')
  RETURNING id
),
new_tenant AS (
  INSERT INTO tenant (tenant_name, default_timezone)
  VALUES ('Test Verification Tenant DT', 'America/New_York')
  RETURNING id
)
INSERT INTO notification_event (notification_type_id, tenant_id)
SELECT nt.id, t.id FROM new_type nt, new_tenant t
RETURNING id, occurred_at;

-- Expected: occurred_at is current timestamp (within a few seconds of now)

ROLLBACK;
```

---

**Phase C: Documentation & Reporting**

**Step 1: Generate Verification Summary**

Create a verification report documenting:

1. **Total Fields Verified:** 198/200 (2 columns don't exist yet)
2. **Verification Method:** `information_schema` queries + raw SQL INSERT tests
3. **Pass/Fail Status:** All 198 fields have correct server defaults
4. **Missing Columns:** `entity_type.is_default`, `notification_delivery_attempt.retryable`
5. **Data Type Breakdown:** Boolean (X), Integer (X), String (X), JSONB (X), DateTime (X), tstzrange (X)

**Step 2: Schema Dump Comparison (Optional)**

If needed, generate pre/post schema dumps to show the changes:

```bash
# Generate post-migration schema dump
pg_dump pilot_dev --schema-only --no-owner --no-acl > \
  dev-docs/db-design/aevofab-db-schema-dump-phase-5.0-post.sql

# Compare to pre-migration (Phase 4.9 post)
diff -u \
  dev-docs/db-design/aevofab-db-schema-dump-phase-4.9-post.sql \
  dev-docs/db-design/aevofab-db-schema-dump-phase-5.0-post.sql \
  > dev-docs/db-design/phase-5.0-schema-changes.diff
```

**Step 3: Update Project Plan**

Update `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` with verification results:

```markdown
### Task 3: Comprehensive Database-Layer Verification

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual)
**Priority:** CRITICAL

**Verification Summary:**

- **Total Fields:** 198/200 verified (2 columns don't exist in database)
- **Verification Method:** Direct `information_schema` queries + raw SQL INSERT tests
- **Data Type Coverage:** Boolean (X), Integer (X), String (X), JSONB (X), DateTime (X), tstzrange (X)
- **Pass Rate:** 100% (all 198 existing fields have correct server defaults)
- **Missing Columns:** `entity_type.is_default`, `notification_delivery_attempt.retryable` (documented, will be added when parent tables are created)

**Verification Evidence:**
- information_schema query confirms 198 fields with non-NULL column_default
- Raw SQL INSERT tests prove database enforces defaults without application layer
- Schema dump comparison shows all DEFAULT clauses added correctly

**Key Findings:**
- ✅ All Boolean defaults using `true`/`false` syntax
- ✅ All Integer defaults using numeric literals
- ✅ All String defaults using single-quoted literals
- ✅ All JSONB defaults using `'{}'::jsonb` cast
- ✅ All DateTime defaults using `now()` function
- ✅ All tstzrange defaults using `tstzrange(now(), NULL, '[)')` syntax

**Test Results:**
- Unit tests: 640/640 passing (100%)
- Total tests: 667/667 passing (100%)
- Zero regressions from Phase 5.0 changes
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

### Database Verification:
- [ ] **information_schema query confirms 198 fields have server defaults**
- [ ] **Sample verification by data type (Boolean, Integer, String, JSONB, DateTime, tstzrange)**
- [ ] **Raw SQL INSERT tests prove defaults work at database layer**
- [ ] **2 missing columns documented and explained** (`entity_type.is_default`, `notification_delivery_attempt.retryable`)
- [ ] **No unexpected fields missing defaults** (excluding PKs, FKs, and required input fields)

### Documentation:
- [ ] **Verification report created** (summary of findings)
- [ ] **Project plan updated** with Task 3 completion status
- [ ] **Schema dump comparison generated** (optional, if needed for records)
- [ ] **All verification queries documented** (for future reference)

### Test Baseline Confirmation:
- [ ] **Unit tests still passing:** 640/640 (100%)
- [ ] **Total tests still passing:** 667/667 (100%)
- [ ] **Zero regressions from verification work**

---

## Key Verification Queries

### Master Query: All 198 Fields

**Use this query to get a complete list of all fields with server defaults:**

```sql
SELECT 
    table_name,
    column_name,
    column_default,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_default IS NOT NULL
  AND table_name IN (
    -- Auth models
    'tenant_user_role', 'tenant_domain', 'tenant_user_invite', 'auth_refresh_token',
    'auth_mfa_otp', 'auth_password_history', 'sso_provider', 'jwk_status',
    -- Core models
    'platform_role', 'user', 'user_preference', 'tenant', 'tenant_settings', 'user_endpoint',
    -- CRM models
    'customer_lifecycle_status', 'site_lifecycle_status', 'address_type', 'contact_type',
    'customer', 'site', 'contact', 'address', 'entity_contact', 'entity_address', 'contact_endpoint',
    -- Quoting models
    'quote_status', 'qco_line_type', 'taxability_code', 'quote_link_status',
    'pricebook_item', 'pricebook_item_version', 'quote', 'quote_version', 'quote_line',
    'quote_public_link', 'qpl_contact_action_type', 'quote_public_link_contact_action',
    'quote_acceptance', 'change_order', 'change_order_line',
    -- Fulfillment models
    'job_status', 'job', 'job_notes', 'job_assignment', 'job_expense_category', 'job_expense',
    -- Billing models
    'currency', 'invoice_status', 'invoice', 'invoice_line', 'invoice_line_tax_component',
    'payment_status', 'payment', 'payment_type', 'subscription_status', 'subscription',
    'subscription_usage', 'usage_ledger', 'product_plan', 'product_plan_version',
    'product_feature', 'product_plan_product_feature_version', 'tenant_product_feature_override',
    -- Catalog models
    'supplier_lifecycle_status', 'supplier', 'supplier_item_category', 'supplier_item_uom',
    'supplier_item', 'supplier_item_price', 'pricing_cache', 'tenant_markup_version',
    'tax_rate_version', 'discount_version',
    -- System models
    'webhook_endpoint', 'webhook_event', 'notification_outbox', 'integration_sync_log',
    'connector_config', 'connector_run_log', 'app_service_category', 'app_service_provider',
    'app_service', 'integration_credential', 'integration_sync_mapping',
    'integration_sync_conflict', 'notification_channel', 'notification_type',
    'contact_notification_pref', 'tenant_user_notification_pref', 'tenant_notification_default',
    'notification_template', 'notification_event', 'webhook_event_type',
    'webhook_delivery_attempt', 'idempotency_key',
    -- AI models
    'conversation_session', 'voice_command_log'
  )
ORDER BY table_name, column_name;
```

**Expected Result:** 198 rows (all fields with server defaults, excluding the 2 missing columns)

---

## Risk Assessment

**For Task 3:**
- **Database Access Risk:** LOW (read-only queries, transactions with ROLLBACK)
- **Test Failure Risk:** NONE (no new tests being written, existing tests already passing)
- **Data Corruption Risk:** NONE (verification only, no writes)
- **Time Risk:** LOW (straightforward SQL queries)
- **Documentation Risk:** LOW (clear template for reporting)

---

## Notes

### Important Patterns to Follow
- **Use MCP Postgres Server:** All queries through MCP, not direct psql
- **Read-Only Operations:** All INSERT tests wrapped in BEGIN/ROLLBACK
- **Focus on Database Layer:** Don't re-test ORM behavior (already validated)
- **Document Missing Columns:** The 2 missing columns are expected and should be documented, not fixed in this task

### Task 3 Specific
- **No New Unit Tests Required:** Existing tests already validate application behavior
- **Verification ≠ Testing:** This is about proving database state, not testing code
- **Raw SQL is the Point:** We're proving defaults work without Python/SQLModel
- **198, not 200:** Two columns don't exist yet, so target is 198 verified fields

### If You Get Stuck
- Use MCP server to explore database schema interactively
- Review Task 2 completion report for context on missing columns
- Check `required-defaults-columns-json.md` for expected values
- Focus on `information_schema` queries over complex INSERT tests

---

## Example Verification Flow

### For Task 3 (Database Verification):

```bash
# 1. Verify migration is current
cd backend
source .venv/bin/activate
alembic current
# Expected: cfdeb13d3b22 (head)

# 2. Use MCP Postgres Server for verification queries
# (All queries executed through tool, not command line)

# 3. Query 1: Count total fields with defaults
# Execute via MCP: SELECT COUNT(*) FROM information_schema.columns WHERE...
# Expected: ~198

# 4. Query 2: Sample by data type
# Execute via MCP: Boolean, Integer, String, JSONB, DateTime samples
# Expected: All show correct default syntax

# 5. Query 3: Raw SQL INSERT tests (with ROLLBACK)
# Execute via MCP: Test tenant.is_active, tenant_settings defaults, etc.
# Expected: Defaults applied without specifying values

# 6. Document results in project plan
# Update phase-5.0-db-schema-sync-6-plan.md Task 3 section

# 7. Confirm no regressions
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 640 passed (no change from baseline)
```

---

## Questions to Ask

**Before starting:**
1. Has the migration been applied? (Verify with `alembic current`)
2. Are the unit tests still passing? (Should be 640/640)
3. Do I have access to the MCP postgres server for queries?

**During verification:**
1. How many fields show up with non-NULL column_default? (Target: ~198)
2. Are all data types represented correctly? (Boolean, Integer, String, JSONB, DateTime, tstzrange)
3. Do raw SQL INSERT tests work without specifying default fields?
4. Are the 2 missing columns documented properly?

**After verification:**
1. Did I document all findings in the project plan?
2. Are the test results still 640/640 unit, 667/667 total?
3. Have I created a clear verification summary for future reference?

---

**Ready to Verify!** 🔍

### Task 3 Verification Checklist:
1. ✅ Verify migration is applied (`alembic current`)
2. ✅ Confirm test baseline (640/640 unit, 667/667 total)
3. 🔍 **Execute information_schema master query (all 198 fields)**
4. 🔍 **Sample verification by data type (Boolean, Integer, String, JSONB, DateTime)**
5. 🔍 **Run raw SQL INSERT tests (with ROLLBACK)**
6. 📝 **Document 2 missing columns** (entity_type.is_default, notification_delivery_attempt.retryable)
7. 📊 **Create verification summary report**
8. 📚 **Update project plan with Task 3 completion**
9. ✅ **Confirm no regressions** (640/640 unit, 667/667 total still passing)

Remember: This task is about **proving database-layer enforcement** through direct SQL verification. Focus on `information_schema` queries and raw SQL INSERT tests. The unit tests already validate ORM behavior, so no new application tests are needed!
