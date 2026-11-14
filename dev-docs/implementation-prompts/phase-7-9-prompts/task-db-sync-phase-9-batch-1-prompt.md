# Phase 9.0 Batch 1: The Hard-Delete Lockdown - Deletion Pathways

**Reference:** `dev-docs/analysis/phase-9.0-db-schema-data-lifecycle-plan.md` - Batch 1
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Find which `.py` file contains each table.
**Type:** Phase 9.0 - Data Lifecycle & Deletion Pathways
**Priority:** CRITICAL COMPLIANCE
**Change Type:** ORM UPDATES + SCHEMA CONSTRAINTS + DB TRIGGERS + TESTING

---

## 📑 Context

This is **Phase 9.0 - Deletion Pathways & Data Lifecycle**. We are solving two critical data integrity issues:
1. **Financial Hard-Delete Vulnerability (Batch 1 — THIS BATCH):** Hazardous `ON DELETE CASCADE` rules on financial/audit tables risk permanent data loss. We are locking these down to `RESTRICT`.
2. **Soft-Delete Zombies (Batch 2):** The application uses `is_active` for soft deletes, but the database lacks triggers to cascade this state to child records. We are adding DB-level triggers to keep parent/child `is_active` states perfectly synchronized.

**Your Goal:** Execute the scope for **Batch 1 ONLY** safely, ensuring referential integrity and complete test coverage. **Do NOT proceed to Batch 2.**

---

## 🎯 Current Task: Batch 1 - The Hard-Delete Lockdown

**Scope:** Convert 14 critical financial and CRM-adjacent foreign key constraints from their current `CASCADE` or implicit `NO ACTION` rules to explicit `ON DELETE RESTRICT`. This prevents any hard-delete of a parent entity (e.g., a `tenant` or `customer`) from silently destroying financial records.

Apply `ON DELETE RESTRICT` to the following tables and their FK relationships:

| # | Table | Foreign Key Column(s) | References | Current Rule → New Rule |
|---|-------|-----------------------|------------|-------------------------|
| 1 | `quote` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 2 | `quote` | `customer_id` | `customer.id` | CASCADE → **RESTRICT** |
| 3 | `quote_version` | `quote_id` | `quote.id` | CASCADE → **RESTRICT** |
| 4 | `quote_version` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 5 | `quote_line` | `quote_version_id` | `quote_version.id` | CASCADE → **RESTRICT** |
| 6 | `quote_line` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 7 | `quote_line_tax_component` | `quote_line_id` | `quote_line.id` | CASCADE → **RESTRICT** |
| 8 | `quote_line_tax_component` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 9 | `quote_message` | `quote_id` | `quote.id` | CASCADE → **RESTRICT** |
| 10 | `quote_message` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 11 | `invoice` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 12 | `invoice` | `customer_id` | `customer.id` | CASCADE → **RESTRICT** |
| 13 | `invoice_line` | `invoice_id` | `invoice.id` | CASCADE → **RESTRICT** |
| 14 | `invoice_line` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 15 | `invoice_line_tax_component` | `invoice_line_id` | `invoice_line.id` | CASCADE → **RESTRICT** |
| 16 | `invoice_line_tax_component` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 17 | `subscription` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 18 | `subscription` | `customer_id` | `customer.id` | CASCADE → **RESTRICT** |
| 19 | `usage_ledger` | `tenant_id` | `tenant.id` | NO ACTION → **RESTRICT** |
| 20 | `usage_ledger` | `subscription_id` | `subscription.id` | NO ACTION → **RESTRICT** |
| 21 | `payment_status` | `invoice_id` | `invoice.id` | CASCADE → **RESTRICT** |
| 22 | `payment_status` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 23 | `quote_status` | `quote_id` | `quote.id` | CASCADE → **RESTRICT** |
| 24 | `quote_status` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 25 | `quote_public_link` | `quote_version_id` | `quote_version.id` | CASCADE → **RESTRICT** |
| 26 | `quote_public_link` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |
| 27 | `quote_public_link_contact_action` | `quote_public_link_id` | `quote_public_link.id` | CASCADE → **RESTRICT** |
| 28 | `quote_public_link_contact_action` | `tenant_id` | `tenant.id` | CASCADE → **RESTRICT** |

> **Note:** For each table, verify the exact existing constraint name from `pilot-db-schema-v2.6h.json` before writing the Alembic migration — you must `DROP` the constraint by its exact name before re-creating it with `RESTRICT`.

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

### 4. Stop & Rollback Conditions
Halt execution immediately if:
- Converting a rule to `RESTRICT` breaks an existing unit test that implicitly relies on `CASCADE` to clean up test data. **Do not delete the test.** Refactor it to explicitly delete or soft-delete child records before deleting the parent.
- Any migration fails to apply cleanly with `alembic upgrade head`.

---

## 🏗️ The 4-Step Execution Loop

Execute these 4 steps sequentially. Do not skip steps.

### Step 1: ORM Model Updates

Locate the models using `backend/db_models_map.md`.

For **every** FK column listed in the scope table above, update the `Field(...)` definition in the SQLModel class to include the `RESTRICT` ondelete rule:

```python
# BEFORE (example — existing pattern):
tenant_id: uuid.UUID = Field(foreign_key="tenant.id")

# AFTER (apply to all FK columns in scope):
tenant_id: uuid.UUID = Field(
    foreign_key="tenant.id",
    sa_column_kwargs={"ondelete": "RESTRICT"},
)
```

Apply this pattern to **all 14 tables** and **all in-scope FK columns** listed above. Use `backend/db_models_map.md` to locate the correct `.py` file for each table.

---

### Step 2: Manual Database Migration (Alembic)

❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs. Generate a **blank** migration:

```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_9_0_batch_1_hard_delete_lockdown"
```

**Check history first** to confirm the correct `down_revision`:
```bash
alembic history
```

Manually write the logic inside `upgrade()` and `downgrade()` using this exact pattern for every constraint in scope:

```python
# upgrade() — Batch 1 Pattern:
def upgrade() -> None:
    # --- quote table ---
    op.drop_constraint("fk_quote_tenant_id", "quote", type_="foreignkey")
    op.create_foreign_key(
        "fk_quote_tenant_id", "quote", "tenant", ["tenant_id"], ["id"], ondelete="RESTRICT"
    )
    op.drop_constraint("fk_quote_customer_id", "quote", type_="foreignkey")
    op.create_foreign_key(
        "fk_quote_customer_id", "quote", "customer", ["customer_id"], ["id"], ondelete="RESTRICT"
    )
    # ... repeat for all 28 constraints listed in scope ...

# downgrade() — Revert to CASCADE / NO ACTION as appropriate:
def downgrade() -> None:
    op.drop_constraint("fk_quote_tenant_id", "quote", type_="foreignkey")
    op.create_foreign_key(
        "fk_quote_tenant_id", "quote", "tenant", ["tenant_id"], ["id"], ondelete="CASCADE"
    )
    # ... repeat reversals for all constraints ...
```

> **Important:** Verify the exact existing constraint names from `dev-docs/db-design/pilot-db-schema-v2.6h.json` before writing the migration. Constraint names in the live DB must match exactly.

Apply and verify the migration:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

---

### Step 3: Master Blueprint Sync

Update `dev-docs/db-design/pilot-db-schema-v2.6h.json`.

For each of the 14 tables in scope, locate the table's `"foreign_keys"` array and update the relevant FK entry's `"ondelete"` value from `"CASCADE"` (or `"NO ACTION"`) to `"RESTRICT"`. Example:

```json
// BEFORE:
{
  "constrained_columns": ["tenant_id"],
  "referred_table": "tenant",
  "ondelete": "CASCADE"
}

// AFTER:
{
  "constrained_columns": ["tenant_id"],
  "referred_table": "tenant",
  "ondelete": "RESTRICT"
}
```

*Ask the user to run `python schema_diff.py --group-by environment`* to prove 0 discrepancies exist and give you the results. This is because the user will need to dump the db schema file, then copy it over to the `dev-docs/db-design/` folder, then run the schema diff script.

---

### Step 4: Regression & Pathway Testing

Run the unit test suite to confirm zero regressions:

```bash
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

Additionally, you **MUST** write explicit hard-delete prevention tests for **every parent/child pathway** introduced in this batch. Place these tests in the most relevant existing test file for each domain, or create a new file `tests/unit/test_phase_9_0_batch_1_deletion_pathways.py`.

**Test Pattern (Hard-Delete Prevention — apply for every parent table in scope):**

```python
import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

# --- quote table ---
def test_tenant_hard_delete_blocked_by_quote(db_session, test_tenant, test_quote):
    """Ensure deleting a tenant with an associated quote raises IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_customer_hard_delete_blocked_by_quote(db_session, test_tenant, test_customer, test_quote):
    """Ensure deleting a customer with an associated quote raises IntegrityError (RESTRICT)."""
    db_session.delete(test_customer)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- quote_version table ---
def test_quote_hard_delete_blocked_by_quote_version(db_session, test_quote, test_quote_version):
    """Ensure deleting a quote with a version raises IntegrityError (RESTRICT)."""
    db_session.delete(test_quote)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- quote_line table ---
def test_quote_version_hard_delete_blocked_by_quote_line(db_session, test_quote_version, test_quote_line):
    """Ensure deleting a quote_version with a line raises IntegrityError (RESTRICT)."""
    db_session.delete(test_quote_version)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- quote_line_tax_component table ---
def test_quote_line_hard_delete_blocked_by_tax_component(db_session, test_quote_line, test_quote_line_tax_component):
    """Ensure deleting a quote_line with a tax component raises IntegrityError (RESTRICT)."""
    db_session.delete(test_quote_line)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- quote_message table ---
def test_quote_hard_delete_blocked_by_quote_message(db_session, test_quote, test_quote_message):
    """Ensure deleting a quote with a message raises IntegrityError (RESTRICT)."""
    db_session.delete(test_quote)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- invoice table ---
def test_tenant_hard_delete_blocked_by_invoice(db_session, test_tenant, test_invoice):
    """Ensure deleting a tenant with an invoice raises IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_customer_hard_delete_blocked_by_invoice(db_session, test_customer, test_invoice):
    """Ensure deleting a customer with an invoice raises IntegrityError (RESTRICT)."""
    db_session.delete(test_customer)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- invoice_line table ---
def test_invoice_hard_delete_blocked_by_invoice_line(db_session, test_invoice, test_invoice_line):
    """Ensure deleting an invoice with lines raises IntegrityError (RESTRICT)."""
    db_session.delete(test_invoice)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- invoice_line_tax_component table ---
def test_invoice_line_hard_delete_blocked_by_tax_component(db_session, test_invoice_line, test_invoice_line_tax_component):
    """Ensure deleting an invoice_line with a tax component raises IntegrityError (RESTRICT)."""
    db_session.delete(test_invoice_line)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- subscription table ---
def test_tenant_hard_delete_blocked_by_subscription(db_session, test_tenant, test_subscription):
    """Ensure deleting a tenant with a subscription raises IntegrityError (RESTRICT)."""
    db_session.delete(test_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_customer_hard_delete_blocked_by_subscription(db_session, test_customer, test_subscription):
    """Ensure deleting a customer with a subscription raises IntegrityError (RESTRICT)."""
    db_session.delete(test_customer)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- usage_ledger table ---
def test_subscription_hard_delete_blocked_by_usage_ledger(db_session, test_subscription, test_usage_ledger):
    """Ensure deleting a subscription with ledger entries raises IntegrityError (RESTRICT)."""
    db_session.delete(test_subscription)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- payment_status table ---
def test_invoice_hard_delete_blocked_by_payment_status(db_session, test_invoice, test_payment_status):
    """Ensure deleting an invoice with a payment_status raises IntegrityError (RESTRICT)."""
    db_session.delete(test_invoice)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- quote_status table ---
def test_quote_hard_delete_blocked_by_quote_status(db_session, test_quote, test_quote_status):
    """Ensure deleting a quote with a quote_status raises IntegrityError (RESTRICT)."""
    db_session.delete(test_quote)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- quote_public_link table ---
def test_quote_version_hard_delete_blocked_by_public_link(db_session, test_quote_version, test_quote_public_link):
    """Ensure deleting a quote_version with a public link raises IntegrityError (RESTRICT)."""
    db_session.delete(test_quote_version)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# --- quote_public_link_contact_action table ---
def test_public_link_hard_delete_blocked_by_contact_action(db_session, test_quote_public_link, test_quote_public_link_contact_action):
    """Ensure deleting a quote_public_link with contact actions raises IntegrityError (RESTRICT)."""
    db_session.delete(test_quote_public_link)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
```

Once all unit tests pass, run the full suite including integration tests:
```bash
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

---

## ✅ Definition of Done (Checklist)

- [ ] Captured pre-modification test baseline (unit tests + integration tests).
- [ ] All 14 in-scope SQLModel classes updated with `sa_column_kwargs={"ondelete": "RESTRICT"}` for every FK column.
- [ ] `alembic history` checked and `down_revision` confirmed correct.
- [ ] Blank Alembic migration `phase_9_0_batch_1_hard_delete_lockdown` created and manually coded with all 28 constraint drop/recreate pairs.
- [ ] Alembic migration applies successfully (`alembic upgrade head`) and reverts cleanly (`alembic downgrade -1`).
- [ ] `pilot-db-schema-v2.6h.json` updated — all 28 FK `"ondelete"` values changed to `"RESTRICT"`.
- [ ] User ran `python schema_diff.py --group-by environment` and reported **ZERO** discrepancies.
- [ ] Hard-delete prevention tests written for **all** parent/child pathways in this batch (minimum 17 test cases as shown above).
- [ ] 100% of the unit test suite passes with zero regressions.
- [ ] 100% of the integration test suite passes with zero regressions.
- [ ] **DO NOT start Batch 2 (Soft-Delete Triggers) until all items above are checked off.**
