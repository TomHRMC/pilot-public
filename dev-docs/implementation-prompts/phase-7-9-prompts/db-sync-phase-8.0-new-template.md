# Phase 8.0 Batch [BATCH_NUMBER]: [BATCH_NAME] - FK Indexing

**Reference:** `dev-docs/analysis/phase-8.0-db-schema-sync-plan.md` - Batch [BATCH_NUMBER]
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Find which `.py` file contains each table.
**Type:** Phase 8.0 - Performance Optimization
**Priority:** HIGH
**Change Type:** ORM UPDATES + SCHEMA INDEXING + JSON SYNC

---

## 📑 Context

This is **Phase 8.0 - Structural Foreign Key Indexing**. PostgreSQL does not automatically index Foreign Keys. An audit revealed critical structural Foreign Keys across our schema that are missing indexes, causing sequential table scans during JOINs and cascading deletes.

**Your Goal:** Add B-Tree indexes to the structural Foreign Keys for the tables in this batch. **Do NOT index `created_by` or `updated_by` columns.** We are only indexing structural relationships (e.g., `tenant_id`, `customer_id`, `quote_id`).

---

## 🎯 Current Task: Batch [BATCH_NUMBER] - [BATCH_NAME]

**Scope:** Apply indexes to the following Foreign Key columns in this batch:
[LIST_SPECIFIC_TABLES_AND_COLUMNS_FOR_THIS_BATCH]

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** Capture the current test baseline BEFORE making ANY changes. **You must always use the virtual environment for Python/Pytest commands.**

### Step 1: Activate Virtual Environment
In order to run any python, pytest or similar commands, you must always activate the virtual environment.

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run ALL Tests (Current Baseline)
Run both of these to get the baseline, but only run the unit tests and not the integration tests when testing and determining failures and errors. Only once all unit tests are passing do you want to then run the integration tests too.

```bash
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```
**Record the output.** ALL these tests MUST still pass after your work.

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

---

## 🏗️ The 4-Step Execution Loop

Execute these 4 steps sequentially. Do not skip steps.

### Step 1: ORM Model Updates
Locate the models in `backend/app/models/` using the model map. Update the specific `Field(...)` definitions to include `index=True`.

✅ **CORRECT PATTERN:**
```python
customer_id: uuid.UUID = Field(foreign_key="customer.id", index=True)
```

### Step 2: Manual Database Migration (Alembic)
❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs. Generate a **blank** migration:
```bash
alembic revision -m "phase_8_0_batch_[X]_indexes_[domain]"
```

Manually write the index creation logic inside `upgrade()`:
```python
def upgrade():
    # Example format: op.create_index('ix_table_name_column_name', 'table_name', ['column_name'])
    op.create_index('ix_site_customer_id', 'site', ['customer_id'])

def downgrade():
    op.drop_index('ix_site_customer_id', table_name='site')
```
NOTE: Make sure you check alembic history and get the previous migration so that you can fix down_revision in the migration file.

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json`. Inside the specific table, add the new index to the `"indexes"` array.

✅ **CORRECT JSON PATTERN:**
```json
"indexes": [
  {
    "name": "ix_site_customer_id",
    "definition": "(customer_id)"
  }
]
```
*Ask the user to run `python schema_diff.py --group-by environment`* to prove 0 discrepancies exist and give you the results. This is because the user will need to dump the db schema file, then copy it over to the dev-docs/db-design/ folder, then run the schema diff script.

### Step 4: Regression Testing
Run the Pytest suite to ensure no syntax errors or model initialization failures occurred.

---

## ✅ Definition of Done (Checklist)

- [ ] Captured pre-modification test baseline.
- [ ] SQLModel updated with `index=True` for target FKs.
- [ ] Blank Alembic migration created and manually coded with `op.create_index`.
- [ ] Alembic migration applies successfully and `alembic downgrade -1` works cleanly.
- [ ] `pilot-db-schema-v2.6h.json` updated with explicit `CREATE INDEX` definitions.
- [ ] `python schema_diff.py` reports ZERO discrepancies.
- [ ] 100% of the test suite passes with zero regressions.
