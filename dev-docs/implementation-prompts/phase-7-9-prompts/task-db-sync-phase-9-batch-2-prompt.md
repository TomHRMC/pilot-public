# Phase 9.0 Batch 2: Soft-Delete Synchronization - Deletion Pathways

**Reference:** `dev-docs/analysis/phase-9.0-db-schema-data-lifecycle-plan.md` - Batch 2
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Find which `.py` file contains each table.
**Type:** Phase 9.0 - Data Lifecycle & Deletion Pathways
**Priority:** CRITICAL COMPLIANCE
**Change Type:** ORM UPDATES + SCHEMA CONSTRAINTS + DB TRIGGERS + TESTING

---

## 📑 Context

This is **Phase 9.0 - Deletion Pathways & Data Lifecycle**. We are solving two critical data integrity issues:
1. **Financial Hard-Delete Vulnerability (Batch 1 — COMPLETE):** Hazardous `ON DELETE CASCADE` rules on financial/audit tables were locked down to `RESTRICT`. **This is already done.**
2. **Soft-Delete Zombies (Batch 2 — THIS BATCH):** The application uses `is_active` for soft deletes, but the database lacks triggers to cascade this state to child records. We are adding DB-level `plpgsql` triggers to keep parent/child `is_active` states perfectly synchronized.

**Your Goal:** Execute the scope for **Batch 2 ONLY** safely, ensuring soft-delete cascade integrity across all 4 domain hierarchies, with complete test coverage proving each trigger fires correctly.

> ⚠️ **Prerequisite:** Batch 1 must be fully verified and merged before starting this batch. Confirm with the user that Batch 1 is complete.

---

## 🎯 Current Task: Batch 2 - Soft-Delete Synchronization

**Scope:** Create PostgreSQL `AFTER UPDATE` triggers that automatically cascade `is_active = false` from parent records to all of their direct children when the parent is soft-deleted. The following 4 domain hierarchies must be fully covered.

### Hierarchy A — Core CRM

| Level | Parent Table | FK Column on Child | Child Table |
|-------|--------------|--------------------|-------------|
| 1 | `customer` | `customer_id` | `site` |
| 2 | `site` | `site_id` | `contact` |
| 3 | `contact` | `contact_id` | `address` |

### Hierarchy B — Sales

| Level | Parent Table | FK Column on Child | Child Table |
|-------|--------------|--------------------|-------------|
| 1 | `quote` | `quote_id` | `quote_line` |
| 2 | `quote_line` | `quote_line_id` | `quote_line_tax_component` |

### Hierarchy C — Billing

| Level | Parent Table | FK Column on Child | Child Table |
|-------|--------------|--------------------|-------------|
| 1 | `invoice` | `invoice_id` | `invoice_line` |
| 2 | `invoice_line` | `invoice_line_id` | `invoice_line_tax_component` |

### Hierarchy D — Fulfillment

| Level | Parent Table | FK Column on Child | Child Table |
|-------|--------------|--------------------|-------------|
| 1 | `job` | `job_id` | `change_order` |
| 2 | `change_order` | `change_order_id` | `change_order_line` |
| 3 | `change_order_line` | `change_order_line_id` | `job_expense` |

> **Note:** Before writing the migration, verify the **exact FK column names** for each child table from `dev-docs/db-design/pilot-db-schema-v2.6h.json`. The column names listed above are the expected names — confirm them and adjust if the schema shows differently.

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

### 4. Correct SQLModel Pattern for `is_active`
Ensure every model in scope has this field. If it already exists, do not add it again — only add it if it is missing.

```python
is_active: bool = Field(default=True)
```

### 5. Stop & Rollback Conditions
Halt execution immediately if:
- Any soft-delete trigger causes **infinite recursion** (e.g., a trigger on `invoice` fires a trigger on `invoice_line` that fires back on `invoice`). Prevent this by using the `WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)` condition on every trigger — this ensures the trigger only fires on a change from `true` to `false` and not again when the child is updated.
- Any existing unit test breaks as a result of a trigger firing unexpectedly during test teardown. Inspect the test fixture to understand why and fix the fixture — **do not delete the test**.
- Any migration fails to apply cleanly with `alembic upgrade head`.

---

## 🏗️ The 4-Step Execution Loop

Execute these 4 steps sequentially. Do not skip steps.

### Step 1: ORM Model Updates

Locate the models using `backend/db_models_map.md`.

For **every** table listed in the 4 hierarchies above, verify that the SQLModel class has an `is_active` field. Add it if it is missing. The correct pattern:

```python
# Verify this exists on every parent and child model in scope:
is_active: bool = Field(default=True)
```

**Tables to check (13 total):**
`customer`, `site`, `contact`, `address`, `quote`, `quote_line`, `quote_line_tax_component`, `invoice`, `invoice_line`, `invoice_line_tax_component`, `job`, `change_order`, `change_order_line`, `job_expense`

---

### Step 2: Manual Database Migration (Alembic)

❌ **DO NOT USE `--autogenerate`.** Generate a **blank** migration:

```bash
cd backend
source .venv/bin/activate
alembic revision -m "phase_9_0_batch_2_soft_delete_sync_triggers"
```

**Check history first** to confirm the correct `down_revision`:
```bash
alembic history
```

Manually write the logic inside `upgrade()` and `downgrade()`. You will create **10 trigger functions and 10 triggers** — one for each parent→child relationship across all 4 hierarchies.

**The Reusable `plpgsql` Trigger Function Pattern:**

Each trigger function follows this same template. The only things that change are: the child table name and the FK column name on the child that references the parent's `id`.

```sql
-- Pattern for a single parent → child relationship:
CREATE OR REPLACE FUNCTION cascade_soft_delete_to_{child_table}()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Only fire when is_active transitions from TRUE to FALSE.
    -- The WHEN clause on the trigger already filters this, but we
    -- double-check here to guard against future misuse.
    IF NEW.is_active = false AND OLD.is_active = true THEN
        UPDATE {child_table}
        SET is_active = false
        WHERE {fk_column_on_child} = NEW.id
          AND is_active = true;  -- Only update children that are still active
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_soft_delete_{parent_table}_to_{child_table}
AFTER UPDATE OF is_active ON {parent_table}
FOR EACH ROW
WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
EXECUTE FUNCTION cascade_soft_delete_to_{child_table}();
```

**Full `upgrade()` — All 10 Triggers (fill in exact FK column names from schema JSON):**

```python
def upgrade() -> None:
    # =========================================================
    # HIERARCHY A: Core CRM
    # customer → site → contact → address
    # =========================================================

    # --- Level 1: customer → site ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_site()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE site SET is_active = false
                WHERE customer_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_customer_to_site
        AFTER UPDATE OF is_active ON customer
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_site();
    """)

    # --- Level 2: site → contact ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_contact()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE contact SET is_active = false
                WHERE site_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_site_to_contact
        AFTER UPDATE OF is_active ON site
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_contact();
    """)

    # --- Level 3: contact → address ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_address()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE address SET is_active = false
                WHERE contact_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_contact_to_address
        AFTER UPDATE OF is_active ON contact
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_address();
    """)

    # =========================================================
    # HIERARCHY B: Sales
    # quote → quote_line → quote_line_tax_component
    # =========================================================

    # --- Level 1: quote → quote_line ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_quote_line()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE quote_line SET is_active = false
                WHERE quote_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_quote_to_quote_line
        AFTER UPDATE OF is_active ON quote
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_quote_line();
    """)

    # --- Level 2: quote_line → quote_line_tax_component ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_quote_line_tax_component()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE quote_line_tax_component SET is_active = false
                WHERE quote_line_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_quote_line_to_tax_component
        AFTER UPDATE OF is_active ON quote_line
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_quote_line_tax_component();
    """)

    # =========================================================
    # HIERARCHY C: Billing
    # invoice → invoice_line → invoice_line_tax_component
    # =========================================================

    # --- Level 1: invoice → invoice_line ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_invoice_line()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE invoice_line SET is_active = false
                WHERE invoice_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_invoice_to_invoice_line
        AFTER UPDATE OF is_active ON invoice
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_invoice_line();
    """)

    # --- Level 2: invoice_line → invoice_line_tax_component ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_invoice_line_tax_component()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE invoice_line_tax_component SET is_active = false
                WHERE invoice_line_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_invoice_line_to_tax_component
        AFTER UPDATE OF is_active ON invoice_line
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_invoice_line_tax_component();
    """)

    # =========================================================
    # HIERARCHY D: Fulfillment
    # job → change_order → change_order_line → job_expense
    # =========================================================

    # --- Level 1: job → change_order ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_change_order()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE change_order SET is_active = false
                WHERE job_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_job_to_change_order
        AFTER UPDATE OF is_active ON job
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_change_order();
    """)

    # --- Level 2: change_order → change_order_line ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_change_order_line()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE change_order_line SET is_active = false
                WHERE change_order_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_change_order_to_change_order_line
        AFTER UPDATE OF is_active ON change_order
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_change_order_line();
    """)

    # --- Level 3: change_order_line → job_expense ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_job_expense()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE job_expense SET is_active = false
                WHERE change_order_line_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_change_order_line_to_job_expense
        AFTER UPDATE OF is_active ON change_order_line
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_job_expense();
    """)
```

**Full `downgrade()` — Drop all triggers and functions in reverse order:**

```python
def downgrade() -> None:
    # Drop triggers first, then the functions they depend on.

    # Hierarchy D — Fulfillment
    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_change_order_line_to_job_expense ON change_order_line;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_job_expense();")

    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_change_order_to_change_order_line ON change_order;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_change_order_line();")

    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_job_to_change_order ON job;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_change_order();")

    # Hierarchy C — Billing
    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_invoice_line_to_tax_component ON invoice_line;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_invoice_line_tax_component();")

    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_invoice_to_invoice_line ON invoice;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_invoice_line();")

    # Hierarchy B — Sales
    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_quote_line_to_tax_component ON quote_line;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_quote_line_tax_component();")

    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_quote_to_quote_line ON quote;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_quote_line();")

    # Hierarchy A — Core CRM
    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_contact_to_address ON contact;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_address();")

    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_site_to_contact ON site;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_contact();")

    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_customer_to_site ON site;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_site();")
```

Apply and verify the migration:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

---

### Step 3: Master Blueprint Sync

Update `dev-docs/db-design/pilot-db-schema-v2.6h.json`.

For each of the **10 parent tables** that now have a trigger, add a new `"triggers"` array entry (or append to an existing one) inside that table's JSON object. Follow this pattern:

```json
// Example — adding the trigger entry to the "customer" table object:
{
  "table": "customer",
  "columns": [ ... ],
  "foreign_keys": [ ... ],
  "triggers": [
    {
      "name": "trg_soft_delete_customer_to_site",
      "event": "AFTER UPDATE OF is_active",
      "timing": "FOR EACH ROW",
      "condition": "OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false",
      "function": "cascade_soft_delete_to_site()",
      "purpose": "Soft-delete cascade: customer → site"
    }
  ]
}
```

Add a matching entry for all 10 triggers across their respective parent tables:
- `customer` → `trg_soft_delete_customer_to_site`
- `site` → `trg_soft_delete_site_to_contact`
- `contact` → `trg_soft_delete_contact_to_address`
- `quote` → `trg_soft_delete_quote_to_quote_line`
- `quote_line` → `trg_soft_delete_quote_line_to_tax_component`
- `invoice` → `trg_soft_delete_invoice_to_invoice_line`
- `invoice_line` → `trg_soft_delete_invoice_line_to_tax_component`
- `job` → `trg_soft_delete_job_to_change_order`
- `change_order` → `trg_soft_delete_change_order_to_change_order_line`
- `change_order_line` → `trg_soft_delete_change_order_line_to_job_expense`

*Ask the user to run `python schema_diff.py --group-by environment`* to prove 0 discrepancies exist and give you the results. This is because the user will need to dump the db schema file, then copy it over to the `dev-docs/db-design/` folder, then run the schema diff script.

---

### Step 4: Regression & Pathway Testing

Run the unit test suite to confirm zero regressions:

```bash
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

Additionally, you **MUST** write explicit soft-delete cascade tests for **every single parent→child pathway** in this batch. Place all tests in a new file: `tests/unit/test_phase_9_0_batch_2_soft_delete_pathways.py`.

**CRITICAL:** You must write **one test per parent→child pair** (10 tests minimum). Each test must:
1. Soft-delete the **parent** by setting `is_active = False` and committing.
2. `db_session.refresh()` the **child** object to pull in the trigger's effect from the DB.
3. Assert that the **child's** `is_active` is now `False`.

```python
import pytest
from sqlmodel import select

# ===========================================================
# HIERARCHY A: Core CRM
# customer → site → contact → address
# ===========================================================

def test_customer_soft_delete_cascades_to_site(db_session, test_tenant, test_customer, test_site):
    """Ensure soft-deleting a customer automatically soft-deletes its child sites via DB trigger."""
    # 1. Soft-delete the parent
    test_customer.is_active = False
    db_session.add(test_customer)
    db_session.commit()

    # 2. Refresh the child from the DB to capture the trigger's effect
    db_session.refresh(test_site)

    # 3. Assert the child is now soft-deleted
    assert test_site.is_active is False, "DB trigger did not cascade soft-delete from customer to site."


def test_site_soft_delete_cascades_to_contact(db_session, test_tenant, test_site, test_contact):
    """Ensure soft-deleting a site automatically soft-deletes its child contacts via DB trigger."""
    test_site.is_active = False
    db_session.add(test_site)
    db_session.commit()

    db_session.refresh(test_contact)

    assert test_contact.is_active is False, "DB trigger did not cascade soft-delete from site to contact."


def test_contact_soft_delete_cascades_to_address(db_session, test_tenant, test_contact, test_address):
    """Ensure soft-deleting a contact automatically soft-deletes its child addresses via DB trigger."""
    test_contact.is_active = False
    db_session.add(test_contact)
    db_session.commit()

    db_session.refresh(test_address)

    assert test_address.is_active is False, "DB trigger did not cascade soft-delete from contact to address."


# ===========================================================
# HIERARCHY B: Sales
# quote → quote_line → quote_line_tax_component
# ===========================================================

def test_quote_soft_delete_cascades_to_quote_line(db_session, test_tenant, test_quote, test_quote_line):
    """Ensure soft-deleting a quote automatically soft-deletes its child quote_lines via DB trigger."""
    test_quote.is_active = False
    db_session.add(test_quote)
    db_session.commit()

    db_session.refresh(test_quote_line)

    assert test_quote_line.is_active is False, "DB trigger did not cascade soft-delete from quote to quote_line."


def test_quote_line_soft_delete_cascades_to_tax_component(
    db_session, test_tenant, test_quote_line, test_quote_line_tax_component
):
    """Ensure soft-deleting a quote_line automatically soft-deletes its tax components via DB trigger."""
    test_quote_line.is_active = False
    db_session.add(test_quote_line)
    db_session.commit()

    db_session.refresh(test_quote_line_tax_component)

    assert test_quote_line_tax_component.is_active is False, (
        "DB trigger did not cascade soft-delete from quote_line to quote_line_tax_component."
    )


# ===========================================================
# HIERARCHY C: Billing
# invoice → invoice_line → invoice_line_tax_component
# ===========================================================

def test_invoice_soft_delete_cascades_to_invoice_line(
    db_session, test_tenant, test_invoice, test_invoice_line
):
    """Ensure soft-deleting an invoice automatically soft-deletes its child invoice_lines via DB trigger."""
    test_invoice.is_active = False
    db_session.add(test_invoice)
    db_session.commit()

    db_session.refresh(test_invoice_line)

    assert test_invoice_line.is_active is False, "DB trigger did not cascade soft-delete from invoice to invoice_line."


def test_invoice_line_soft_delete_cascades_to_tax_component(
    db_session, test_tenant, test_invoice_line, test_invoice_line_tax_component
):
    """Ensure soft-deleting an invoice_line automatically soft-deletes its tax components via DB trigger."""
    test_invoice_line.is_active = False
    db_session.add(test_invoice_line)
    db_session.commit()

    db_session.refresh(test_invoice_line_tax_component)

    assert test_invoice_line_tax_component.is_active is False, (
        "DB trigger did not cascade soft-delete from invoice_line to invoice_line_tax_component."
    )


# ===========================================================
# HIERARCHY D: Fulfillment
# job → change_order → change_order_line → job_expense
# ===========================================================

def test_job_soft_delete_cascades_to_change_order(
    db_session, test_tenant, test_job, test_change_order
):
    """Ensure soft-deleting a job automatically soft-deletes its child change_orders via DB trigger."""
    test_job.is_active = False
    db_session.add(test_job)
    db_session.commit()

    db_session.refresh(test_change_order)

    assert test_change_order.is_active is False, "DB trigger did not cascade soft-delete from job to change_order."


def test_change_order_soft_delete_cascades_to_change_order_line(
    db_session, test_tenant, test_change_order, test_change_order_line
):
    """Ensure soft-deleting a change_order automatically soft-deletes its lines via DB trigger."""
    test_change_order.is_active = False
    db_session.add(test_change_order)
    db_session.commit()

    db_session.refresh(test_change_order_line)

    assert test_change_order_line.is_active is False, (
        "DB trigger did not cascade soft-delete from change_order to change_order_line."
    )


def test_change_order_line_soft_delete_cascades_to_job_expense(
    db_session, test_tenant, test_change_order_line, test_job_expense
):
    """Ensure soft-deleting a change_order_line automatically soft-deletes its job_expenses via DB trigger."""
    test_change_order_line.is_active = False
    db_session.add(test_change_order_line)
    db_session.commit()

    db_session.refresh(test_job_expense)

    assert test_job_expense.is_active is False, (
        "DB trigger did not cascade soft-delete from change_order_line to job_expense."
    )


# ===========================================================
# ANTI-REGRESSION: Confirm triggers do NOT fire when is_active
# stays TRUE (i.e., no false positives)
# ===========================================================

def test_customer_update_non_is_active_does_not_cascade(db_session, test_tenant, test_customer, test_site):
    """Ensure that updating a non-is_active field on customer does NOT soft-delete child sites."""
    # Mutate a non-is_active field (adjust to a real field on the customer model)
    test_customer.updated_at = test_customer.updated_at  # no-op update to force flush
    db_session.add(test_customer)
    db_session.commit()

    db_session.refresh(test_site)

    # Child should still be active — trigger must NOT have fired
    assert test_site.is_active is True, "Trigger fired incorrectly when is_active did not change."
```

Once all unit tests pass, run the full suite including integration tests:
```bash
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

---

## ✅ Definition of Done (Checklist)

- [ ] Confirmed with user that **Batch 1 is fully verified and merged** before starting.
- [ ] Captured pre-modification test baseline (unit tests + integration tests).
- [ ] All 14 in-scope SQLModel classes verified to have `is_active: bool = Field(default=True)`. Added where missing.
- [ ] `alembic history` checked and `down_revision` confirmed correct.
- [ ] Blank Alembic migration `phase_9_0_batch_2_soft_delete_sync_triggers` created and manually coded with all 10 trigger function + trigger pairs.
- [ ] All FK column names verified against `dev-docs/db-design/pilot-db-schema-v2.6h.json` before writing migration SQL.
- [ ] Alembic migration applies successfully (`alembic upgrade head`) and reverts cleanly (`alembic downgrade -1`).
- [ ] `pilot-db-schema-v2.6h.json` updated — all 10 parent tables have a `"triggers"` entry added.
- [ ] User ran `python schema_diff.py --group-by environment` and reported **ZERO** discrepancies.
- [ ] Soft-delete cascade tests written for **all 10 parent→child pathways** in this batch, plus 1 anti-regression test.
- [ ] Tests placed in `tests/unit/test_phase_9_0_batch_2_soft_delete_pathways.py`.
- [ ] 100% of the unit test suite passes with zero regressions.
- [ ] 100% of the integration test suite passes with zero regressions.
- [ ] **Infinite recursion guard confirmed:** Every trigger uses `WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)` and every function body checks `IF NEW.is_active = false AND OLD.is_active = true`.
