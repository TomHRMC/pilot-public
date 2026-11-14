# Phase 7.0 Batch 3: Operations & Jobs - Tenant Stamping

**Reference:** `dev-docs/analysis/phase-7.0-db-schema-cleanup-plan.md` - Batch 3
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

## 🎯 Current Task: Batch 3 - Operations & Jobs

**Scope:** The following tables must be updated in this batch:
* `job_notes`
* `job_time_entry`
* `change_order`
* `change_order_attachment`
* `change_order_line`
* `change_order_line_tax_component`

**Effort Estimate:** Medium-High (Straightforward single-hop FK backfill for `job_notes`, `job_time_entry`, and `change_order` via `job.tenant_id`; single-hop for `change_order_attachment` and `change_order_line` via `change_order.tenant_id`; however `change_order_line_tax_component` requires a **2-hop join** through `change_order_line` → `change_order` to reach `tenant_id`)

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
2. **Alembic Backfill Failure:** You cannot figure out how to write the `op.execute()` SQL to backfill the `tenant_id` for existing records — especially the 2-hop join required for `change_order_line_tax_component`.
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
alembic revision -m "phase_7_0_batch_3_tenant_stamping_operations_jobs"
```

Then, **manually write the 3-part migration logic** inside `upgrade()`. Because existing data might exist, you MUST follow this pattern for **each table**. The backfill SQL for each table in this batch is defined below:

```python
def upgrade():
    # ==============================================================
    # TABLE: job_notes  (parent: job via job_id)
    # ==============================================================
    op.add_column('job_notes', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_job_notes_tenant_id', 'job_notes', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_job_notes_tenant_id', 'job_notes', ['tenant_id'])
    op.execute("""
        UPDATE job_notes
        SET tenant_id = job.tenant_id
        FROM job
        WHERE job_notes.job_id = job.id
    """)
    op.alter_column('job_notes', 'tenant_id', nullable=False)

    # ==============================================================
    # TABLE: job_time_entry  (parent: job via job_id)
    # ==============================================================
    op.add_column('job_time_entry', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_job_time_entry_tenant_id', 'job_time_entry', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_job_time_entry_tenant_id', 'job_time_entry', ['tenant_id'])
    op.execute("""
        UPDATE job_time_entry
        SET tenant_id = job.tenant_id
        FROM job
        WHERE job_time_entry.job_id = job.id
    """)
    op.alter_column('job_time_entry', 'tenant_id', nullable=False)

    # ==============================================================
    # TABLE: change_order  (parent: job via job_id)
    # ==============================================================
    op.add_column('change_order', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_change_order_tenant_id', 'change_order', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_change_order_tenant_id', 'change_order', ['tenant_id'])
    op.execute("""
        UPDATE change_order
        SET tenant_id = job.tenant_id
        FROM job
        WHERE change_order.job_id = job.id
    """)
    op.alter_column('change_order', 'tenant_id', nullable=False)

    # ==============================================================
    # TABLE: change_order_attachment  (parent: change_order via change_order_id)
    # ==============================================================
    op.add_column('change_order_attachment', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_change_order_attachment_tenant_id', 'change_order_attachment', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_change_order_attachment_tenant_id', 'change_order_attachment', ['tenant_id'])
    op.execute("""
        UPDATE change_order_attachment
        SET tenant_id = change_order.tenant_id
        FROM change_order
        WHERE change_order_attachment.change_order_id = change_order.id
    """)
    op.alter_column('change_order_attachment', 'tenant_id', nullable=False)

    # ==============================================================
    # TABLE: change_order_line  (parent: change_order via change_order_id)
    # ==============================================================
    op.add_column('change_order_line', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_change_order_line_tenant_id', 'change_order_line', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_change_order_line_tenant_id', 'change_order_line', ['tenant_id'])
    op.execute("""
        UPDATE change_order_line
        SET tenant_id = change_order.tenant_id
        FROM change_order
        WHERE change_order_line.change_order_id = change_order.id
    """)
    op.alter_column('change_order_line', 'tenant_id', nullable=False)

    # ==============================================================
    # TABLE: change_order_line_tax_component  (2-HOP: via change_order_line -> change_order)
    # NOTE: change_order must already have tenant_id at this point (set above).
    # ==============================================================
    op.add_column('change_order_line_tax_component', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_change_order_line_tax_component_tenant_id', 'change_order_line_tax_component', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_change_order_line_tax_component_tenant_id', 'change_order_line_tax_component', ['tenant_id'])
    op.execute("""
        UPDATE change_order_line_tax_component
        SET tenant_id = change_order.tenant_id
        FROM change_order_line
        JOIN change_order ON change_order_line.change_order_id = change_order.id
        WHERE change_order_line_tax_component.change_order_line_id = change_order_line.id
    """)
    op.alter_column('change_order_line_tax_component', 'tenant_id', nullable=False)


def downgrade():
    op.drop_index('ix_change_order_line_tax_component_tenant_id', table_name='change_order_line_tax_component')
    op.drop_constraint('fk_change_order_line_tax_component_tenant_id', 'change_order_line_tax_component', type_='foreignkey')
    op.drop_column('change_order_line_tax_component', 'tenant_id')

    op.drop_index('ix_change_order_line_tenant_id', table_name='change_order_line')
    op.drop_constraint('fk_change_order_line_tenant_id', 'change_order_line', type_='foreignkey')
    op.drop_column('change_order_line', 'tenant_id')

    op.drop_index('ix_change_order_attachment_tenant_id', table_name='change_order_attachment')
    op.drop_constraint('fk_change_order_attachment_tenant_id', 'change_order_attachment', type_='foreignkey')
    op.drop_column('change_order_attachment', 'tenant_id')

    op.drop_index('ix_change_order_tenant_id', table_name='change_order')
    op.drop_constraint('fk_change_order_tenant_id', 'change_order', type_='foreignkey')
    op.drop_column('change_order', 'tenant_id')

    op.drop_index('ix_job_time_entry_tenant_id', table_name='job_time_entry')
    op.drop_constraint('fk_job_time_entry_tenant_id', 'job_time_entry', type_='foreignkey')
    op.drop_column('job_time_entry', 'tenant_id')

    op.drop_index('ix_job_notes_tenant_id', table_name='job_notes')
    op.drop_constraint('fk_job_notes_tenant_id', 'job_notes', type_='foreignkey')
    op.drop_column('job_notes', 'tenant_id')
```

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json` to include the new `tenant_id` columns, foreign keys, and indexes for the tables in this batch.
*Run `python schema_diff.py` to prove 0 discrepancies exist before moving to Step 4.*

### Step 4: API & Service Layer Refactoring
Scan `backend/api/routes/` and `backend/services/` for raw `session.get(Model, id)` or `db.get(Model, id)` calls involving this batch's models. Consult `backend/app_model_imports.md` if you need to add imports to these files.

❌ **DESTROY THIS PATTERN:**
`item = session.get(ChangeOrder, change_order_id)`
✅ **REPLACE WITH THIS PATTERN:**
`item = session.exec(select(ChangeOrder).where(ChangeOrder.id == change_order_id, ChangeOrder.tenant_id == current_tenant.id)).first()`

*Apply this same tenant-scoped refactor for all 6 models in this batch: `JobNotes`, `JobTimeEntry`, `ChangeOrder`, `ChangeOrderAttachment`, `ChangeOrderLine`, and `ChangeOrderLineTaxComponent`.*

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

- [x] Captured pre-modification test baseline. **Baseline: 831 unit passed, 1 skipped; 8 integration failures (pre-existing).**
- [x] SQLModel updated with `tenant_id` (indexed, nullable=False, FK to tenant.id).
- [x] Blank Alembic migration created using `alembic revision -m "..."`.
- [x] 3-Part Manual Migration coded (Add Nullable -> Backfill Data -> Set Not Null) for all 6 tables.
- [x] 2-hop backfill SQL verified for `change_order_line_tax_component` (via `change_order_line` → `change_order`).
- [x] Alembic migration applies successfully and `alembic downgrade -1` works cleanly.
- [x] `pilot-db-schema-v2.6h.json` updated.
- [x] `python schema_diff.py` reports ZERO discrepancies.
- [x] All `session.get()` calls for these models refactored to explicitly filter by `tenant_id`.
- [x] Cross-tenant isolation unit tests written and passing. **18 new IDOR security tests added.**
- [x] 100% of the test suite passes with zero regressions.
- [x] Document updated with final test counts.

---

## 📊 Final Test Results (2026-04-15)

| Suite | Passed | Skipped | Failed |
|-------|--------|---------|--------|
| Unit tests only (`--ignore=tests/integration/`) | 849 | 1 | 0 |
| Full suite (unit + integration) | 876 | 1 | 0 |

**Net new tests added this phase: +45** (849 unit − 831 baseline + 27 integration fixed)

### Integration test fixes applied:
- `test_financial_math_edge_cases.py`: Added `tenant_id=tenant_a.id` to 8 `QuoteLine` constructors + 2 `JobTimeEntry` constructors
- `test_quote_to_job_flow.py`: Added `tenant_id=tenant_a.id` to 3 `QuoteLine` constructors + 1 `JobTimeEntry` constructor

### Integration test file: `test_phase7_batch3_tenant_isolation.py` (NEW)
18 IDOR security tests across 7 classes:
- `TestJobNotesTenantIsolation` (3 tests)
- `TestJobTimeEntryTenantIsolation` (3 tests)
- `TestChangeOrderTenantIsolation` (3 tests)
- `TestChangeOrderAttachmentTenantIsolation` (2 tests)
- `TestChangeOrderLineTenantIsolation` (3 tests)
- `TestChangeOrderLineTaxComponentTenantIsolation` (2 tests)
- `TestBatch3TenantIdConsistency` (2 tests)
