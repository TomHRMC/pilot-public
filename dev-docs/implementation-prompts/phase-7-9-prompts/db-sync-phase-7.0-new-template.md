# Phase 7.0 Batch [BATCH_NUMBER]: [BATCH_NAME] - Tenant Stamping

**Reference:** `dev-docs/analysis/phase-7.0-db-schema-sync-plan.md` - Batch [BATCH_NUMBER]
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Use this to find which `.py` file contains each table.
- `backend/app_model_imports.md` - Use this to ensure you are importing models correctly without causing circular dependencies.
**Type:** Phase 7.0 - Multi-Tenancy Security Hardening
**Priority:** CRITICAL SECURITY
**Change Type:** SCHEMA DENORMALIZATION + DATA MIGRATION + API REFACTORING + SECURITY TESTING

---

## 📑 Context

This is **Phase 7.0 - Tenant Stamping**. We are mitigating High-Severity Insecure Direct Object Reference (IDOR) vulnerabilities. Because our PostgreSQL database does not use Row-Level Security (RLS), tenant isolation relies 100% on the application layer. 

Currently, several polymorphic and deep-hierarchy tables lack a `tenant_id` column. If a malicious user guesses a valid UUID for one of these records, `session.get()` will return it, crossing the tenant boundary.

**The Solution:** We are denormalizing the schema by stamping a non-nullable `tenant_id` foreign key onto all vulnerable child tables, and refactoring the API to mandate tenant-scoped queries.

---

## 🎯 Current Task: Batch [BATCH_NUMBER] - [BATCH_NAME]

**Scope:** The following tables must be updated in this batch:
[LIST_SPECIFIC_TABLES_FOR_THIS_BATCH]

**Effort Estimate:** [EFFORT_ESTIMATE]

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** Capture the current test baseline BEFORE making ANY changes. **You must always use the virtual environment for Python/Pytest commands.**

### Step 1: Activate Virtual Environment (REQUIRED FOR ALL TERMINAL COMMANDS)
```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run ALL Tests (Current Baseline)
```bash
# Run full test suite but without the integration tests FIRST
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Run all tests SECOND
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

### Step 3: Document Your Baseline
**Record the output of both results before proceeding.** This is your regression checkpoint. ALL these tests MUST still pass after your work.

---

## ⚠️ CRITICAL: Coding Agent Best Practices (From Previous Phases)

**DO NOT ignore these codebase-specific rules. Doing so will break the app and fail tests.**

### 1. Always Use the Virtual Environment
Any time you run `pytest`, `alembic`, or `python`, you MUST ensure you are in the `backend/` directory with the `.venv` activated.

### 2. Use `db_session` NOT `session` in Tests
❌ **WRONG:** `def test_example(session: Session, test_tenant):`
✅ **CORRECT:** `def test_example(db_session: Session, test_tenant):`
*Why: The pytest fixture is explicitly named `db_session` in `backend/tests/conftest.py`.*

### 3. Use SQLModel `select()` with `exec()` NOT `query()`
❌ **WRONG (Creates Deprecation Warnings):**
`user = db_session.query(User).filter(User.email == "test@example.com").first()`
✅ **CORRECT (SQLModel Pattern):**
`user = db_session.exec(select(User).where(User.email == "test@example.com")).first()`

### 4. Cross-Tenant IDOR Test Pattern
When writing security validation tests for Phase 7.0, follow this pattern:
```python
def test_cross_tenant_access_blocked(client_tenant_a, test_tenant_b_record):
    """Test that Tenant A receives a 404 when requesting Tenant B's record."""
    response = client_tenant_a.get(f"/api/v1/records/{test_tenant_b_record.id}")
    assert response.status_code == 404 # 404 is preferred over 403 to prevent ID enumeration
```

---

## ⚠️ CRITICAL WARNINGS & STOP CONDITIONS

**DO NOT PROCEED if any of the following occur. Stop and ask the user for guidance:**
1. **Circular Import Crash:** Adding the `Tenant` relationship breaks FastAPI startup. (Mitigation: reference `backend/app_model_imports.md` and use string references `foreign_key="tenant.id"`).
2. **Alembic Backfill Failure:** You cannot figure out how to write the `op.execute()` SQL to backfill the `tenant_id` for existing records.
3. **Test Regressions:** Refactoring `session.get()` causes unrelated tests to fail.

---

## 🏗️ The 5-Step Execution Loop

You must execute the following 5 steps sequentially. Do not skip steps.

### Step 1: ORM Model Updates
Consult `backend/db_models_map.md` to locate the exact file for each table in this batch. Update their SQLModel definitions.
```python
# REQUIRED FIELD DEFINITION:
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
```
*Verify that the app still boots after adding these fields (no circular import loops).*

### Step 2: Manual Database Migration (Alembic)
❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs or "ghost" changes. 

Instead, generate a **blank** migration:
```bash
alembic revision -m "phase_7_0_batch_[X]_tenant_stamping_[domain]"
```

Then, **manually write the 3-part migration logic** inside `upgrade()`. Because existing data might exist, you MUST follow this pattern:

```python
def upgrade():
    # 1. Add tenant_id as nullable=True
    op.add_column('target_table', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_target_table_tenant_id', 'target_table', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_target_table_tenant_id', 'target_table', ['tenant_id'])

    # 2. Write an op.execute() SQL statement to backfill the tenant_id by joining up to the parent entity
    op.execute("""
        UPDATE target_table 
        SET tenant_id = parent_table.tenant_id 
        FROM parent_table 
        WHERE target_table.parent_id = parent_table.id
    """)

    # 3. Alter the tenant_id column to be nullable=False
    op.alter_column('target_table', 'tenant_id', nullable=False)

def downgrade():
    op.drop_index('ix_target_table_tenant_id', table_name='target_table')
    op.drop_constraint('fk_target_table_tenant_id', 'target_table', type_='foreignkey')
    op.drop_column('target_table', 'tenant_id')
```

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json` to include the new `tenant_id` columns, foreign keys, and indexes for the tables in this batch.
*Run `python schema_diff.py` to prove 0 discrepancies exist before moving to Step 4.*

### Step 4: API & Service Layer Refactoring
Scan `backend/api/routes/` and `backend/services/` for raw `session.get(Model, id)` or `db.get(Model, id)` calls involving this batch's models. Consult `backend/app_model_imports.md` if you need to add imports to these files.

❌ **DESTROY THIS PATTERN:**
`item = session.get(QuoteLine, line_id)`
✅ **REPLACE WITH THIS PATTERN:**
`item = session.exec(select(QuoteLine).where(QuoteLine.id == line_id, QuoteLine.tenant_id == current_tenant.id)).first()`

*Ensure all `POST`/creation logic explicitly injects the `tenant_id` upon object creation.*

### Step 5: Security Validation & Testing
Ensure the existing test suite passes, then write explicit cross-tenant isolation tests for this batch's routes (using the IDOR Test Pattern from the Best Practices section).

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite
```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
```

### Step 2: Final Validation
If ANY tests fail, identify the failing tests, fix the logic (likely a missed `tenant_id` injection during object creation), and re-run until 100% pass rate is achieved.

---

## ✅ Definition of Done (Checklist)

- [ ] Captured pre-modification test baseline.
- [ ] SQLModel updated with `tenant_id` (indexed, nullable=False, FK to tenant.id).
- [ ] Blank Alembic migration created using `alembic revision -m "..."`.
- [ ] 3-Part Manual Migration coded (Add Nullable -> Backfill Data -> Set Not Null).
- [ ] Alembic migration applies successfully and `alembic downgrade -1` works cleanly.
- [ ] `pilot-db-schema-v2.6h.json` updated.
- [ ] `python schema_diff.py` reports ZERO discrepancies.
- [ ] All `session.get()` calls for these models refactored to explicitly filter by `tenant_id`.
- [ ] Cross-tenant isolation unit tests written and passing.
- [ ] 100% of the test suite passes with zero regressions.
- [ ] Document updated with final test counts.
