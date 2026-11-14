# Task 2: Alembic Migration Generation with Manual Verification

**Reference:** `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` - Task 2
**Authority (Golden Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/required-defaults-columns-json.md` - **Authoritative Checklist (200 fields)**
- Current Live Database (Phase 4.9 Post-State)
**Type:** Phase 5.0 - Server Defaults Enforcement
**Priority:** CRITICAL
**Change Type:** MIGRATION + MANUAL VERIFICATION

---

## Context

This is **Phase 5.0 - DB Sync v#6, Task 2**, continuing the systematic fix for the "Sweeping Missing Defaults Bug". Task 1 has been completed - all 200 Python model fields now have `server_default=` definitions. Task 2 generates the Alembic migration to apply these defaults to the physical PostgreSQL database.

**Critical Understanding:** Alembic's `--autogenerate` feature is **notoriously unreliable** for detecting `server_default` additions on existing columns. It works well for new tables but often **completely ignores** server_default changes on existing columns.

**Expected Behavior:**
- Alembic will likely detect only 50-100 of the 200 fields (25-50% success rate)
- You should expect to manually write 100-150+ `op.alter_column()` calls
- Budget 4-6 hours for manual verification and addition of missing fields

**MANDATORY Process:** Systematic verification of every field in `required-defaults-columns-json.md` against the generated migration file, manually adding any missing `op.alter_column()` calls.

---

## What Was Completed in Previous Tasks

**Phase 5.0 - Task 1 Status:** ✅ COMPLETE (April 9, 2026)
- ✅ All 200 fields updated across 9 model files
- ✅ All model files import successfully without errors
- ✅ Correct `server_default=` syntax applied for all data types
- ✅ Python-level defaults retained for application compatibility

**Current Baseline:** 640/640 unit tests, 667/667 total tests passing (100%)

**See:**
- `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` for full Phase 5.0 context

---

## Current Task: Alembic Migration Generation with Manual Verification

**Effort:** 1.0 days
**Gap Reference:** Phase 5.0 Analysis - Alembic Autogenerate Limitations
**Change Type:** MIGRATION + MANUAL VERIFICATION

Generate Alembic migration to apply all 200 server defaults to the physical database, with **mandatory manual verification** to add any `op.alter_column()` calls that Alembic autogenerate missed. This ensures every field from the checklist has a corresponding database-layer default.

### What Needs to Be Done

**Primary Objective:** Create a complete migration file that adds `server_default` to all 200 fields in PostgreSQL.

**Challenge:** Alembic's autogenerate will miss 50-70% of fields, requiring extensive manual intervention.

**Required Actions:**
1. Generate initial migration with `alembic revision --autogenerate`
2. **MANDATORY: Remove any `audit.event` table operations** (Alembic bug)
3. **MANDATORY: Systematic verification** against `required-defaults-columns-json.md`
4. Manually write `op.alter_column()` for every missed field
5. Organize migration with clear section comments
6. Test forward migration (`alembic upgrade head`)
7. Test backward migration (`alembic downgrade -1`)
8. Verify defaults applied via SQL queries

### Tools Available

- You have access to the postgres-local MCP server to query the DB directly, in read-only mode.
- Remember that you do not need to insert any '\n' characters in the sql when creating it for the mcp server.

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** Verify the current state BEFORE generating migration.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Verify Task 1 Completion

```bash
# Verify all models import successfully
python -c "from app.models import *; print('✅ All models loaded successfully')"
```

**Expected:** No import errors, successful load message

### Step 3: Check Current Alembic State

```bash
# Verify database is at latest migration
alembic current

# Should show the most recent migration from Phase 4.9
```

---

## ⚠️ CRITICAL: Phase 5.0 Task 2 Specific Warnings

**BEFORE generating migration, review these critical issues:**

### 1. Alembic Will Miss Many Fields - This is Expected

**Reality Check:** Alembic's `--autogenerate` is excellent for new tables but terrible for detecting server_default additions on existing columns.

**Expected Miss Rate:** 50-70% of the 200 fields

**Count Check After Generation:**
```bash
# After generating migration, count op.alter_column calls
grep -c "op.alter_column" backend/migrations/versions/<migration_file>.py

# If less than 150, expect heavy manual work
# Target: 200 (one per field)
```

**Do NOT panic when Alembic misses fields.** This is normal and expected. The manual verification process catches everything.

---

### 2. MANDATORY: Remove audit.event Table Operations

❌ **COMMON ALEMBIC BUG:**
```python
# Alembic autogenerate sometimes incorrectly wants to create audit.event
def upgrade():
    op.create_table('event',  # ❌ This table already exists!
        sa.Column('id', sa.BigInteger(), nullable=False),
        ...
        schema='audit'
    )
```

✅ **CORRECT (Remove Before Running Migration):**
```python
def upgrade():
    # op.create_table('event', ...) ← DELETED
    # Only include your actual schema changes
    op.alter_column(...)  # Your actual server_default additions
```

**MANDATORY Check After Generation:**
```bash
# Search the migration file
grep -n "audit" backend/migrations/versions/<migration_file>.py
grep -n "'event'" backend/migrations/versions/<migration_file>.py

# If found, DELETE these operations:
# - Any op.create_table('event', ... schema='audit')
# - Any op.drop_table('event', ... schema='audit')
# - Any index/constraint operations on audit.event
```

---

### 3. Manual Verification is NOT Optional

**Process (CANNOT Be Skipped):**

```markdown
1. Open generated migration file in editor
2. Open required-defaults-columns-json.md side-by-side
3. Create verification tracking (spreadsheet or checklist):

Table Name          | Expected Fields | Found in Migration | Missing Count | Status
--------------------|-----------------|-------------------|---------------|--------
tenant              | 1               | ?                 | ?             | [ ]
tenant_settings     | 4               | ?                 | ?             | [ ]
platform_role       | 3               | ?                 | ?             | [ ]
user                | 7               | ?                 | ?             | [ ]
...                 | ...             | ...               | ...           | [ ]

4. For each table in checklist:
   a. Count expected fields (from required-defaults-columns-json.md)
   b. Search migration for "op.alter_column('<table_name>'"
   c. Count actual matches in migration
   d. If counts DON'T MATCH → Add to "Missing" list

5. For each missing field, manually write op.alter_column()
   (See syntax reference below)

6. Verify total: Should have ~200 op.alter_column() calls in upgrade()
```

---

### 4. Migration File Organization Matters

Given the scale (200 fields), organize clearly by model file:

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

def upgrade():
    # =====================================================
    # AUTH MODELS (backend/app/models/auth.py)
    # =====================================================
    
    # Table: platform_role (3 fields)
    op.alter_column('platform_role', 'permissions', ...)
    op.alter_column('platform_role', 'is_default', ...)
    op.alter_column('platform_role', 'is_active', ...)
    
    # Table: user (7 fields)
    op.alter_column('user', 'is_platform_user', ...)
    # ... etc
    
    # =====================================================
    # CORE MODELS (backend/app/models/core.py)
    # =====================================================
    
    # Table: tenant (1 field)
    op.alter_column('tenant', 'is_active', ...)
    
    # ... continue for all 78 tables ...


def downgrade():
    # Mirror structure: remove all server_default values
    # Process in REVERSE order of upgrade() for safety
    pass
```

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

## Step-by-Step Implementation

### Step 1: Generate Initial Migration

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "phase_5_0_add_server_defaults_200_fields"
```

**Expected Output:** New migration file in `backend/migrations/versions/` with timestamp and hash prefix.

**Example Filename:** `2026_04_09_1630-abc123def456_phase_5_0_add_server_defaults_200_fields.py`

---

### Step 2: MANDATORY - Check for audit.event Bug

```bash
# Immediately after generation, search for audit.event
grep -n "audit" backend/migrations/versions/<migration_file>.py
grep -n "'event'" backend/migrations/versions/<migration_file>.py
```

**If Found:**
1. Open migration file in editor
2. Locate any `op.create_table('event', ... schema='audit')` 
3. Locate any `op.drop_table('event', ... schema='audit')`
4. **DELETE these entire operation blocks**
5. Save file

**This step is MANDATORY.** The audit.event table already exists and must not be recreated.

---

### Step 3: Initial Assessment

```bash
# Count op.alter_column calls in upgrade()
grep -c "op.alter_column" backend/migrations/versions/<migration_file>.py

# Expected: 200 (reality: probably 50-100)
```

**If count is less than 150:** Prepare for significant manual work (4-6 hours).

**If count is 150-180:** Moderate manual work needed (2-3 hours).

**If count is 180-200:** Lucky day! Minimal manual work (1 hour).

---

### Step 4: Systematic Verification Against Checklist

**MANDATORY PROCESS:**

Open two documents side-by-side:
1. Generated migration file
2. `dev-docs/db-design/required-defaults-columns-json.md`

**For Each Table in Checklist:**

```markdown
Example: tenant_settings table

Checklist shows 4 fields:
  - default_labor_rate_cents (Integer, 8500)
  - default_billable_labor_rate_cents (Integer, 9500)
  - default_quote_validity_days (Integer, 30)
  - default_invoice_terms_days (Integer, 30)

Migration search:
  grep "tenant_settings" <migration_file>.py

Found in migration: 2 fields (default_labor_rate_cents, default_quote_validity_days)

Missing: 2 fields → Must manually add op.alter_column() for these
```

**Create tracking checklist or spreadsheet** to systematically verify all 78 tables.

---

### Step 5: Manual op.alter_column() Syntax Reference

For each missing field, add the appropriate `op.alter_column()` call:

**Boolean Defaults:**
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

**Integer Defaults:**
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

**String Defaults:**
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

**JSONB Defaults:**
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

**DateTime Defaults:**
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

**tstzrange Defaults:**
```python
# In upgrade()
op.alter_column('tenant_markup_version', 'valid_period',
    existing_type=postgresql.TSTZRANGE(),
    server_default=sa.text("tstzrange(now(), null, '[)')"),
    existing_nullable=False)

# In downgrade()
op.alter_column('tenant_markup_version', 'valid_period',
    existing_type=postgresql.TSTZRANGE(),
    server_default=None,
    existing_nullable=False)
```

---

### Step 6: Organize Migration File

**Add clear section headers** to improve readability:

```python
def upgrade():
    # =====================================================
    # AUTH MODELS (backend/app/models/auth.py)
    # Expected: 14 fields across multiple tables
    # =====================================================
    
    # Table: platform_role (3 fields)
    op.alter_column('platform_role', 'permissions', ...)
    op.alter_column('platform_role', 'is_default', ...)
    op.alter_column('platform_role', 'is_active', ...)
    
    # Table: user (7 fields)
    # ... etc
    
    # =====================================================
    # CORE MODELS (backend/app/models/core.py)
    # Expected: 15 fields across multiple tables
    # =====================================================
    
    # ... continue for all model files
```

**Benefits:**
- Easy to verify completeness per model file
- Clear structure for code review
- Easier to debug if issues arise

---

### Step 7: Test Forward Migration

```bash
# Apply migration to database
alembic upgrade head
```

**Expected:** Migration runs successfully without errors.

**If errors occur:**
- Check for syntax errors in op.alter_column() calls
- Verify table/column names match database exactly
- Check for missing imports (postgresql.JSONB, etc.)

---

### Step 8: Verify Defaults Applied (Database Verification)

Use postgres-local MCP server to query `information_schema`:

```sql
-- Spot check: Verify sample defaults
SELECT 
    table_name, 
    column_name, 
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('tenant', 'user', 'quote', 'invoice')
  AND column_name IN ('is_active', 'failed_login_count', 'currency', 'status')
ORDER BY table_name, column_name;

-- Expected: All should have non-NULL column_default values
```

**More comprehensive verification:**

```sql
-- Count how many of the 200 fields now have defaults
-- (Build this query from required-defaults-columns-json.md)
SELECT COUNT(*) AS fields_with_defaults
FROM information_schema.columns
WHERE (table_name = 'tenant' AND column_name = 'is_active')
   OR (table_name = 'tenant_settings' AND column_name = 'default_labor_rate_cents')
   -- ... add all 200 fields from checklist ...
   AND column_default IS NOT NULL;

-- Expected: 200
```

---

### Step 9: Test Backward Migration (Rollback)

```bash
# Test rollback to previous state
alembic downgrade -1
```

**Expected:** Migration rolls back successfully.

**Verification after rollback:**
```sql
-- Verify defaults were removed
SELECT 
    table_name, 
    column_name, 
    column_default
FROM information_schema.columns
WHERE table_name IN ('tenant', 'user', 'quote')
  AND column_name IN ('is_active', 'failed_login_count', 'currency')
ORDER BY table_name, column_name;

-- Expected: column_default should be NULL for these fields
```

---

### Step 10: Re-apply Migration

```bash
# Re-apply for continued work
alembic upgrade head
```

**This completes the migration testing cycle.**

---

## Success Criteria for Task 2

- [ ] Migration file generated with `alembic revision --autogenerate`
- [ ] **CRITICAL:** All `audit.event` table operations removed from migration
- [ ] Systematic verification completed against `required-defaults-columns-json.md`
- [ ] All 200 fields have `op.alter_column()` in `upgrade()` function
- [ ] All 200 fields have `op.alter_column(..., server_default=None)` in `downgrade()` function
- [ ] Migration file organized with clear section comments by model file
- [ ] Migration runs successfully forward (`alembic upgrade head`)
- [ ] Migration runs successfully backward (`alembic downgrade -1`)
- [ ] Database verification confirms defaults applied (SQL queries)
- [ ] Spot-check verification: Sample fields show correct defaults in `information_schema`

---

## 🎯 AFTER YOU COMPLETE - Verify Migration Success

**CRITICAL:** After migration is applied, verify the database state.

### Step 1: Run Database Verification Queries

Use postgres-local MCP server to execute verification queries:

```sql
-- Query 1: Spot check sample defaults by data type
SELECT 
    table_name, 
    column_name, 
    column_default,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE (table_name = 'tenant' AND column_name = 'is_active')           -- Boolean: true
   OR (table_name = 'platform_role' AND column_name = 'is_default')   -- Boolean: false
   OR (table_name = 'user' AND column_name = 'failed_login_count')    -- Integer: 0
   OR (table_name = 'tenant_settings' AND column_name = 'default_labor_rate_cents')  -- Integer: 8500
   OR (table_name = 'user' AND column_name = 'preferred_mfa_channel') -- String: 'email'
   OR (table_name = 'platform_role' AND column_name = 'permissions')  -- JSONB: '{}'::jsonb
ORDER BY table_name, column_name;

-- Expected: All should have non-NULL column_default matching expected values
```

```sql
-- Query 2: Find any NOT NULL columns without defaults
-- (Should be minimal - only PKs, FKs, and fields requiring explicit values)
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
  AND column_name != 'id'          -- Exclude PKs
ORDER BY table_name, column_name;
```

### Step 2: Test Raw SQL Insert (Bypassing ORM)

```sql
-- Test that defaults work via raw SQL
BEGIN;

-- Test 1: Boolean default
INSERT INTO tenant (tenant_name, default_timezone)
VALUES ('Test Tenant Task 2', 'America/New_York')
RETURNING id, is_active;
-- Expected: is_active should be TRUE

-- Test 2: Integer default
INSERT INTO tenant_settings (tenant_id)
VALUES ((SELECT id FROM tenant WHERE tenant_name = 'Test Tenant Task 2'))
RETURNING tenant_id, default_labor_rate_cents;
-- Expected: default_labor_rate_cents should be 8500

-- Test 3: JSONB default
INSERT INTO platform_role (role_name, role_description)
VALUES ('Test Role Task 2', 'Testing defaults')
RETURNING id, permissions;
-- Expected: permissions should be {}

ROLLBACK;  -- Clean up test data
```

### Step 3: Document Migration Details

**Record the following:**
- Migration filename: `2026_04_09_<time>-<hash>_phase_5_0_add_server_defaults_200_fields.py`
- Total `op.alter_column()` calls in upgrade(): 200
- Alembic auto-detected: [COUNT]
- Manually added: [COUNT]
- Migration test: ✅ PASSED forward and backward
- Database verification: ✅ All 200 fields have defaults

---

## Documentation Update

**File to Update:** `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md`

Find Task 2 section and update with:

```markdown
## ⚠️ Task 2: Alembic Migration Generation with Manual Verification

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** [ACTUAL_HOURS] hours (actual)
**Priority:** CRITICAL

**Implementation Summary:**

- Migration File: `2026_04_09_<time>-<hash>_phase_5_0_add_server_defaults_200_fields.py`
- Alembic Auto-Detected: [COUNT] fields
- Manually Added: [COUNT] fields (Alembic missed these)
- Total op.alter_column() Calls: 200 (100%)
- Migration Test: ✅ Forward and backward tested successfully
- Database Verification: ✅ All 200 fields confirmed via information_schema

**Key Actions:**
- ✅ Generated migration with alembic revision --autogenerate
- ✅ Removed audit.event table operations (Alembic bug)
- ✅ Systematic verification against required-defaults-columns-json.md
- ✅ Manually added [COUNT] missing op.alter_column() calls
- ✅ Migration organized with clear section headers
- ✅ Database defaults verified via SQL queries
- ✅ Rollback tested successfully

**Verification:**
- All 200 fields have server_default at database layer
- Raw SQL INSERT tests pass (defaults applied)
- Migration rollback works correctly
```

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-5.0-db-schema-sync-6-plan.md` - **Master Plan** ⭐
- `dev-docs/db-design/required-defaults-columns-json.md` - **Authoritative Checklist (200 fields)** ⭐⭐⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON

### Migration Location
- `backend/migrations/versions/` - Generated migration will be here

---

## Risk Assessment

**For Task 2:**
- **Data Loss Risk:** NONE (only adding defaults, not modifying data)
- **Alembic Miss Risk:** **HIGH** (expect 50-100+ fields missed by autogenerate)
- **Manual Error Risk:** MEDIUM (200 fields to verify manually)
- **Migration Failure Risk:** LOW (additive schema changes)
- **Rollback Complexity:** LOW (simple server_default removal)
- **Performance Impact:** NONE (defaults only affect INSERT, not queries)
- **Mitigation:** Systematic checklist verification, comprehensive SQL testing

---

## Notes

### Important Patterns to Follow
- **Checklist is Law:** Every field in required-defaults-columns-json.md MUST be in migration
- **Alembic Will Fail:** Expect to manually add 50-100+ fields - this is normal
- **audit.event Bug:** ALWAYS check for and remove audit.event operations
- **String Syntax:** `sa.text("'value'")` for strings (quotes inside)
- **JSONB Syntax:** `sa.text("'{}'::jsonb")` for JSONB (cast required)
- **DateTime Syntax:** `sa.func.now()` for timestamps (not text)
- **Verify Everything:** Use SQL queries to confirm defaults applied

### Task 2 Specific
- **Manual work is expected:** Budget 4-6 hours for verification and additions
- **Systematic approach:** Don't rush - verify every table against checklist
- **Test thoroughly:** Forward, backward, and SQL verification all required
- **Clear organization:** Group by model file for easier verification

### If You Get Stuck
- Check syntax reference for specific data type
- Verify field exists in required-defaults-columns-json.md
- Search for similar examples in the migration file
- Test migration in small batches if needed (comment out sections)
- Use postgres-local MCP to query database state
- Ask for help if spending >1 hour on a single issue

---

## Example Task Flow

### For Task 2 (Migration):

```bash
# 1. Generate migration
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "phase_5_0_add_server_defaults_200_fields"

# 2. Open migration file
# Location: backend/migrations/versions/2026_04_09_<time>-<hash>_phase_5_0_add_server_defaults_200_fields.py

# 3. MANDATORY: Check for audit.event bug
grep -n "audit" backend/migrations/versions/<file>
grep -n "'event'" backend/migrations/versions/<file>
# If found, DELETE those operation blocks

# 4. Count initial detection
grep -c "op.alter_column" backend/migrations/versions/<file>
# Expected: 50-100 (Alembic will miss many)

# 5. Systematic verification
# Open required-defaults-columns-json.md side-by-side
# For each table:
#   - Count expected fields in checklist
#   - Search migration for that table: grep "table_name" <file>
#   - Count actual fields found
#   - If mismatch → add missing fields manually

# 6. Manual addition example (if tenant.is_active is missing):
# In upgrade():
op.alter_column('tenant', 'is_active',
    existing_type=sa.Boolean(),
    server_default=sa.text('true'),
    existing_nullable=False)

# In downgrade():
op.alter_column('tenant', 'is_active',
    existing_type=sa.Boolean(),
    server_default=None,
    existing_nullable=False)

# 7. Apply migration
alembic upgrade head

# 8. Verify via SQL (using postgres-local MCP)
SELECT column_name, column_default 
FROM information_schema.columns 
WHERE table_name = 'tenant';

# 9. Test rollback
alembic downgrade -1
alembic upgrade head

# 10. Document completion
```

---

## Questions to Ask

**Before starting:**
1. Did Task 1 complete successfully (all models import)?
2. Do I have required-defaults-columns-json.md open and ready?
3. Am I prepared for 4-6 hours of manual verification work?

**During migration generation:**
1. Did I remove all audit.event table operations?
2. How many fields did Alembic auto-detect vs. expected 200?
3. For each table, do counts match between checklist and migration?
4. Am I using correct syntax for each data type?

**During testing:**
1. Does migration run forward successfully?
2. Do SQL queries show defaults applied?
3. Does rollback work correctly?
4. Can I INSERT via raw SQL without specifying default fields?

**After implementation:**
1. Do I have 200 op.alter_column() calls in upgrade()?
2. Do I have 200 op.alter_column() calls in downgrade()?
3. Have I verified all 200 fields via information_schema?
4. Did I update the project plan document?

---

**Ready to Begin Task 2!** 🚀

### Task 2 Checklist:
1. ✅ Verify Task 1 complete (all models import)
2. 🔧 Generate migration with `alembic revision --autogenerate`
3. ⚠️ **CRITICAL: Remove audit.event operations**
4. 📊 Count initial Alembic detection (expect 50-100 of 200)
5. 📝 **MANDATORY: Open required-defaults-columns-json.md side-by-side**
6. 🔍 **Systematic verification: Table by table against checklist**
7. ✍️ **Manually add missing op.alter_column() calls (expect 100-150)**
8. 📁 Organize migration with section headers by model file
9. ✅ Test forward: `alembic upgrade head`
10. 🧪 Verify via SQL: Query information_schema
11. ↩️ Test backward: `alembic downgrade -1`
12. 🔄 Re-apply: `alembic upgrade head`
13. 📚 Update project plan document

Remember: Task 2 is about **migration generation with MANDATORY manual verification**. Alembic will miss 50-70% of fields - this is expected and normal. Use the checklist religiously, verify every table systematically, and test thoroughly with SQL queries. Budget 4-6 hours for this task!
