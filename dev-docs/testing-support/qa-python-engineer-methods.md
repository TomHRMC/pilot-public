# 🧪 QA Python Engineer Methods — Pilot for Trades Test Playbook

**Version**: 1.1 | **Owner**: QA Python Engineer (with Pilot Architect) | **Referenced by**: `.roomodes` — `pilot-qa-python-engineer` customInstructions #2
**Updated**: 2026-08-20 — pytest invocations modernized to the canonical two-phase gate (`pytest -m unit --tb=no -q | tail -5`); §6 naming updated to the `tests/domains/` standard. §§3.3–4 (soft-delete cascade, anti-regression, trigger recursion-guard patterns) remain the canonical trigger-testing reference. **Broader refresh** — scope expansion beyond the Phase 9.0 soft-delete origin + full reconciliation with `backend/tests/README-adding-tests.md` — is folded into **BE-TESTS-MAINT** (launch plan §2.1 Order 6).

---

## 1. Environment Setup (Mandatory Before Any Test Run)

You **must always** activate the virtual environment before running `pytest`, `alembic`, or any `python` command. Failure to do so will produce false failures due to missing dependencies.

```bash
cd backend
source .venv/bin/activate
```

> ⚠️ Every terminal session requires this. Do not assume the venv is already active.

---

## 2. The 3-Phase Test Process

Follow these three phases in strict order. Do **not** collapse phases or skip steps.

### Phase 1 — Establish the Regression Baseline (Before Any Changes)

Run **both** commands and record their output **before touching any code or migration**:

```bash
# Unit tests only (fast baseline — no integration tests)
pytest -m unit --tb=no -q 2>&1 | tail -5

# Full suite (unit + integration — for baseline capture only)
pytest tests/ --tb=short -q 2>&1 | tail -5
```

Record the exact pass/fail counts. This is your **immutable baseline**. All tests that pass now must still pass at the end of Phase 3.

---

### Phase 2 — Development Loop (Unit Tests Only)

While implementing changes, **only run unit tests**. Do not run integration tests during active development — they are slow, stateful, and will obscure the root cause of failures.

```bash
# Run only unit tests — use this command throughout development
pytest -m unit --tb=no -q 2>&1 | tail -5
```

Iterate until **100% of unit tests pass** with zero regressions before proceeding.

---

### Phase 3 — Final Full-Suite Verification (After All Unit Tests Pass)

Only after all unit tests pass, run the complete suite including integration tests:

```bash
# Final verification — run only when all unit tests are green
pytest tests/ --tb=short -q 2>&1 | tail -5
```

This is the **gate check** before documenting results or marking a task complete.

---

## 3. Test Design Patterns (Mandatory — Do Not Deviate)

### 3.1 Fixture: Use `db_session`, NOT `session`

❌ **WRONG:**
```python
def test_example(session: Session, test_tenant):
```

✅ **CORRECT:**
```python
def test_example(db_session: Session, test_tenant):
```

The `db_session` fixture is the project-standard transactional fixture. Using `session` directly will cause fixture-scope errors or leave dirty state.

---

### 3.2 Querying: Use SQLModel `select()` + `exec()`, NOT `query()`

❌ **WRONG:**
```python
user = db_session.query(User).filter(User.email == "test@example.com").first()
```

✅ **CORRECT:**
```python
from sqlmodel import select

user = db_session.exec(select(User).where(User.email == "test@example.com")).first()
```

The project uses **SQLModel**, not raw SQLAlchemy ORM query API. Using `.query()` will raise `AttributeError` at runtime.

---

### 3.3 Soft-Delete Field Pattern

Every model in scope must have this field. Check before adding — only add if it is missing:

```python
is_active: bool = Field(default=True)
```

---

### 3.4 Soft-Delete Cascade Test Pattern

When testing DB-level `AFTER UPDATE` triggers that cascade `is_active = false` from parent to child, follow this exact 3-step pattern for every test:

```python
def test_parent_soft_delete_cascades_to_child(db_session, test_tenant, test_parent, test_child):
    """Ensure soft-deleting a parent automatically soft-deletes its child via DB trigger."""

    # Step 1: Soft-delete the parent
    test_parent.is_active = False
    db_session.add(test_parent)
    db_session.commit()

    # Step 2: Refresh the child from the DB to capture the trigger's effect
    db_session.refresh(test_child)

    # Step 3: Assert the child is now soft-deleted
    assert test_child.is_active is False, "DB trigger did not cascade soft-delete from parent to child."
```

> **Why `db_session.refresh()`?** The DB trigger updates the child row directly in PostgreSQL. The SQLModel session holds a stale in-memory object. `refresh()` re-fetches from the DB so the assertion reflects the true persisted state.

---

### 3.5 Anti-Regression Test Pattern (No False Positives)

For every soft-delete cascade tested, also write one anti-regression test proving the trigger does **not** fire when `is_active` does not change:

```python
def test_parent_update_non_is_active_does_not_cascade(db_session, test_tenant, test_parent, test_child):
    """Ensure updating a non-is_active field on parent does NOT soft-delete child."""
    # Mutate a non-is_active field to force a flush without changing is_active
    test_parent.updated_at = test_parent.updated_at  # no-op update
    db_session.add(test_parent)
    db_session.commit()

    db_session.refresh(test_child)

    # Child must still be active — trigger must NOT have fired
    assert test_child.is_active is True, "Trigger fired incorrectly when is_active did not change."
```

---

## 4. Trigger Infinite Recursion Guard

Every PostgreSQL `AFTER UPDATE` trigger created for soft-delete cascades **must** include the `WHEN` clause guard and a matching body-level `IF` check:

```sql
-- Trigger definition: WHEN clause prevents the trigger firing again
-- when the child record is updated (avoiding parent→child→parent loops)
CREATE TRIGGER trg_soft_delete_parent_to_child
AFTER UPDATE OF is_active ON parent_table
FOR EACH ROW
WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
EXECUTE FUNCTION cascade_soft_delete_to_child_table();
```

```sql
-- Function body: secondary guard for future misuse protection
BEGIN
    IF NEW.is_active = false AND OLD.is_active = true THEN
        UPDATE child_table
        SET is_active = false
        WHERE fk_column = NEW.id
          AND is_active = true;  -- Only update still-active children
    END IF;
    RETURN NEW;
END;
```

The `AND is_active = true` filter on the `UPDATE` statement prevents already-soft-deleted children from being re-touched, which further breaks any potential recursion chain.

---

## 5. Stop & Rollback Conditions

Halt immediately and do **not** proceed if any of the following occur:

| Condition | Action |
|-----------|--------|
| A soft-delete trigger causes **infinite recursion** | Remove the trigger, fix the `WHEN` clause guard, re-apply |
| An **existing unit test breaks** due to a trigger firing during test teardown | Inspect and fix the test fixture — **do NOT delete the test** |
| An Alembic migration fails to apply cleanly with `alembic upgrade head` | Roll back with `alembic downgrade -1`, fix the SQL, re-apply |
| Any previously passing test now fails after your changes | Treat as a regression — find root cause before continuing |

---

## 6. Test File Naming & Placement Convention

New test files must follow the domain-folder standard defined in `backend/tests/README-adding-tests.md`:

```
tests/domains/{domain}/test_{feature_or_entity}_{action}.py
```

**Rules** (per README-adding-tests):
- Always place new tests in an **existing** `tests/domains/<domain>/` folder — never create a new `batch_*`, `phase_*`, or new domain folder without explicit approval
- Name files `test_<feature_or_entity>_<action>.py` (e.g., `test_quote_approval_webhook.py`)
- Identify the owning batch in the file's docstring, not in the path

**Example (soft-delete pathway tests):**
```
tests/domains/audit_compliance/test_soft_delete_pathways.py
```

Every test file must:
- Cover **every single parent→child relationship** in scope (minimum one test per pathway)
- Include at least **one anti-regression test** per hierarchy
- Use `db_session`, `test_tenant`, and relevant model fixtures for all tests
- Include docstrings on every test function describing what is being verified and why

---

## 7. Minimum Test Coverage Requirements

For any soft-delete cascade work, the following minimums apply:

| Requirement | Minimum Count |
|-------------|---------------|
| Tests per parent→child trigger pathway | 1 positive cascade test |
| Anti-regression tests | 1 per hierarchy group |
| Unit test pass rate before Phase 3 | 100% |
| Integration test pass rate at Phase 3 | 100% (matching baseline) |

---

## 8. Documenting Results

After Phase 3 completes successfully, document the final outcome with:

1. **Baseline counts** (from Phase 1 capture)
2. **Final counts** (from Phase 3 full suite run)
3. **New tests added** (file name, test function names, count)
4. **Any fixtures added or modified** (with rationale)
5. **Migration applied** (alembic revision ID confirmed with `alembic history`)
6. **Definition of Done checklist** verified item by item

Do not mark a task complete until the Phase 3 full suite passes and results are documented.
