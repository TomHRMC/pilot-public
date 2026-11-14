# Phase 9.0 Batch [BATCH_NUMBER]: [BATCH_NAME] - Deletion Pathways

**Reference:** `dev-docs/analysis/phase-9.0-db-schema-sync-plan.md` - Batch [BATCH_NUMBER]
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Find which `.py` file contains each table.
**Type:** Phase 9.0 - Data Lifecycle & Deletion Pathways
**Priority:** CRITICAL COMPLIANCE
**Change Type:** ORM UPDATES + SCHEMA CONSTRAINTS + DB TRIGGERS + TESTING

---

## 📑 Context

This is **Phase 9.0 - Deletion Pathways & Data Lifecycle**. We are solving two critical data integrity issues:
1. **Financial Hard-Delete Vulnerability (Batch 1):** Hazardous `ON DELETE CASCADE` rules on financial/audit tables risk permanent data loss. We are locking these down to `RESTRICT`.
2. **Soft-Delete Zombies (Batch 2):** The application uses `is_active` for soft deletes, but the database lacks triggers to cascade this state to child records. We are adding DB-level triggers to keep parent/child `is_active` states perfectly synchronized.

**Your Goal:** Execute the scope for this specific batch safely, ensuring referential integrity and complete test coverage.

---

## 🎯 Current Task: Batch [BATCH_NUMBER] - [BATCH_NAME]

**Scope:** Apply the following rules or triggers to the tables in this batch:
[LIST_SPECIFIC_TABLES_AND_RULES_FOR_THIS_BATCH]

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

## ⚠️ CRITICAL: Coding Agent Best Practices

**DO NOT ignore these codebase-specific rules. Doing so will break the app and fail tests.**

### 1. Always Use the Virtual Environment
Any time you run `pytest`, `alembic`, or `python`, you MUST ensure you are in the `backend/` directory with the `.venv` activated.

### 2. Use `db_session` NOT `session` in Tests
❌ **WRONG:** `def test_example(session: Session, test_tenant):`
✅ **CORRECT:** `def test_example(db_session: Session, test_tenant):`

### 3. Use SQLModel `select()` with `exec()` NOT `query()`
❌ **WRONG:** `user = db_session.query(User).filter(User.email == "test@example.com").first()`
✅ **CORRECT:** `user = db_session.exec(select(User).where(User.email == "test@example.com")).first()`

### 4. Correct SQLModel Pattern for Foreign Key `ondelete`
SQLModel's `sa_column_kwargs` passes arguments to `Column()`, but `ondelete` belongs on `ForeignKey()`. You must explicitly declare the `sa_column` to set deletion rules.

❌ **WRONG:** ```python
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", sa_column_kwargs={"ondelete": "RESTRICT"})
```

✅ **CORRECT:**
```python
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

tenant_id: uuid.UUID = Field(
    sa_column=Column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
)
```

---

## 🏗️ The 4-Step Execution Loop

Execute these 4 steps sequentially. Do not skip steps.

### Step 1: ORM Model Updates
Locate the models using `backend/db_models_map.md`. 
* **If Batch 1 (RESTRICT):** Update the `Field(...)` to use the explicit `sa_column=Column(..., ForeignKey(..., ondelete="RESTRICT"))` pattern as shown in Best Practice #4.
* **If Batch 2 (Triggers):** Ensure all relevant models have an `is_active: bool = Field(default=True)` column.

### Step 2: Manual Database Migration (Alembic)
❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs. Generate a **blank** migration:
```bash
alembic revision -m "phase_9_0_batch_[X]_deletion_[domain]"
```

Manually write the logic inside `upgrade()` and `downgrade()`. 
**NOTE:** Make sure you check alembic history (`alembic history`) and get the previous migration so that you can fix `down_revision` in the migration file.

* **Batch 1 Pattern:** `op.drop_constraint(...)` then `op.create_foreign_key(..., ondelete='RESTRICT')`.
* **Batch 2 Pattern:** Use `op.execute(""" CREATE OR REPLACE FUNCTION ... """)` and `op.execute(""" CREATE TRIGGER ... """)`.

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json`. Update the `"foreign_keys"` rules or add the new `"triggers"` to the JSON objects.

*Ask the user to run `python schema_diff.py --group-by environment`* to prove 0 discrepancies exist and give you the results. This is because the user will need to dump the db schema file, then copy it over to the dev-docs/db-design/ folder, then run the schema diff script.

### Step 4: Regression & Pathway Testing
Run the Pytest suite. Additionally, you **MUST** write explicit tests for the deletion pathways introduced in this batch. 

**Batch 1 Test Pattern (Hard-Delete Prevention):**
```python
def test_financial_record_hard_delete_restricted(db_session, test_tenant, test_invoice):
    """Ensure deleting a tenant with an invoice throws an IntegrityError."""
    from sqlalchemy.exc import IntegrityError
    
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()
    
    assert "fk_invoice_tenant" in str(exc_info.value)
    db_session.rollback()
```

**Batch 2 Test Pattern (Soft-Delete Cascade):**
*CRITICAL: You must write a test like this for EVERY SINGLE parent table and ALL of their corresponding child tables in this batch.*
```python
def test_invoice_soft_delete_cascades_to_lines(db_session, test_invoice, test_invoice_line):
    """Ensure soft-deleting the parent automatically soft-deletes the child via DB trigger."""
    # 1. Soft delete the parent
    test_invoice.is_active = False
    db_session.add(test_invoice)
    db_session.commit()
    
    # 2. Refresh the child from the database to capture the trigger's effect
    db_session.refresh(test_invoice_line)
    
    # 3. Assert the child is now soft-deleted
    assert test_invoice_line.is_active is False
```

---

## ✅ Definition of Done (Checklist)

- [ ] Captured pre-modification test baseline.
- [ ] SQLModel updated appropriately (sa_column with ForeignKey RESTRICT, or is_active fields).
- [ ] `alembic history` checked and `down_revision` confirmed correct.
- [ ] Blank Alembic migration created and manually coded.
- [ ] Alembic migration applies successfully and `alembic downgrade -1` works cleanly.
- [ ] `pilot-db-schema-v2.6h.json` updated with new rules/triggers.
- [ ] User ran `python schema_diff.py` and reported ZERO discrepancies.
- [ ] Extensive tests written for **all** parent/child pathways in this batch.
- [ ] 100% of the test suite passes with zero regressions.
