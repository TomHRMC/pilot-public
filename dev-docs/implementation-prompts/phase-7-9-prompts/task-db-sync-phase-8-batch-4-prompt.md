# Phase 8.0 Batch 4: Quoting & Jobs - FK Indexing

**Reference:** `dev-docs/analysis/phase-8.0-db-schema-fk-indexes-plan.md` - Batch 4
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Find which `.py` file contains each table.
**Type:** Phase 8.0 - Performance Optimization
**Priority:** HIGH
**Change Type:** ORM UPDATES + SCHEMA INDEXING + JSON SYNC

---

## 📑 Context

This is **Phase 8.0 - Structural Foreign Key Indexing**. PostgreSQL does not automatically index Foreign Keys. An audit revealed critical structural Foreign Keys across our schema that are missing indexes, causing sequential table scans during JOINs and cascading deletes.

**Your Goal:** Add B-Tree indexes to the structural Foreign Keys for the tables in this batch. **Do NOT index `created_by` or `updated_by` columns.** We are only indexing structural relationships (e.g., `tenant_id`, `quote_id`, `supplier_id`).

> **Note:** `job`, `job_notes`, `job_time_entry`, `change_order`, and `change_order_attachment` are in the Batch 4 domain scope but were **not flagged by the audit** as having missing structural FK indexes. No action is required for those five tables.

---

## 🎯 Current Task: Batch 4 - Quoting & Jobs

**Scope:** Apply indexes to the following Foreign Key columns in this batch:

### `quote`
| FK Column | References Table | New Index Name |
|---|---|---|
| `currency` | `currency` | `ix_quote_currency` |

### `qco_line_type`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_qco_line_type_tenant_id` |

### `quote_line`
| FK Column | References Table | New Index Name |
|---|---|---|
| `qco_line_type_id` | `qco_line_type` | `ix_quote_line_qco_line_type_id` |
| `supplier_id` | `supplier` | `ix_quote_line_supplier_id` |
| `supplier_item_id` | `supplier_item` | `ix_quote_line_supplier_item_id` |
| `taxability_code` | `taxability_code` | `ix_quote_line_taxability_code` |
| `pricebook_item_id` | `pricebook_item` | `ix_quote_line_pricebook_item_id` |

### `quote_public_link`
| FK Column | References Table | New Index Name |
|---|---|---|
| `contact_id` | `contact` | `ix_quote_public_link_contact_id` |
| `quote_id` | `quote` | `ix_quote_public_link_quote_id` |
| `status_id` | `quote_link_status` | `ix_quote_public_link_status_id` |

### `quote_message`
| FK Column | References Table | New Index Name |
|---|---|---|
| `quote_id` | `quote` | `ix_quote_message_quote_id` |
| `contact_id` | `contact` | `ix_quote_message_contact_id` |

### `job_attachment`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_job_attachment_tenant_id` |

### `job_expense_category`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_job_expense_category_tenant_id` |

### `job_expense`
| FK Column | References Table | New Index Name |
|---|---|---|
| `job_expense_category_code` | `job_expense_category` | `ix_job_expense_job_expense_category_code` |
| `invoice_line_id` | `invoice_line` | `ix_job_expense_invoice_line_id` |

### `job_assignment`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_job_assignment_tenant_id` |

### `change_order_line`
| FK Column | References Table | New Index Name |
|---|---|---|
| `qco_line_type_id` | `qco_line_type` | `ix_change_order_line_qco_line_type_id` |
| `supplier_id` | `supplier` | `ix_change_order_line_supplier_id` |
| `supplier_item_id` | `supplier_item` | `ix_change_order_line_supplier_item_id` |
| `taxability_code` | `taxability_code` | `ix_change_order_line_taxability_code` |
| `pricebook_item_id` | `pricebook_item` | `ix_change_order_line_pricebook_item_id` |

**Total indexes to create in this batch: 22**

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

Apply `index=True` to every FK column listed in the scope table above. Example entries for this batch:

```python
# quote model
currency: str = Field(foreign_key="currency.code", index=True)

# qco_line_type model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# quote_line model
qco_line_type_id: int = Field(foreign_key="qco_line_type.id", index=True)
supplier_id: uuid.UUID = Field(foreign_key="supplier.id", index=True)
supplier_item_id: uuid.UUID = Field(foreign_key="supplier_item.id", index=True)
taxability_code: str = Field(foreign_key="taxability_code.code", index=True)
pricebook_item_id: uuid.UUID = Field(foreign_key="pricebook_item.id", index=True)

# quote_public_link model
contact_id: uuid.UUID = Field(foreign_key="contact.id", index=True)
quote_id: uuid.UUID = Field(foreign_key="quote.id", index=True)
status_id: int = Field(foreign_key="quote_link_status.id", index=True)

# quote_message model
quote_id: uuid.UUID = Field(foreign_key="quote.id", index=True)
contact_id: uuid.UUID = Field(foreign_key="contact.id", index=True)

# job_attachment model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# job_expense_category model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# job_expense model
job_expense_category_code: str = Field(foreign_key="job_expense_category.code", index=True)
invoice_line_id: uuid.UUID = Field(foreign_key="invoice_line.id", index=True)

# job_assignment model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# change_order_line model
qco_line_type_id: int = Field(foreign_key="qco_line_type.id", index=True)
supplier_id: uuid.UUID = Field(foreign_key="supplier.id", index=True)
supplier_item_id: uuid.UUID = Field(foreign_key="supplier_item.id", index=True)
taxability_code: str = Field(foreign_key="taxability_code.code", index=True)
pricebook_item_id: uuid.UUID = Field(foreign_key="pricebook_item.id", index=True)
```

### Step 2: Manual Database Migration (Alembic)
❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs. Generate a **blank** migration:
```bash
alembic revision -m "phase_8_0_batch_4_indexes_quoting_jobs"
```

NOTE: Make sure you check `alembic history` and get the previous migration so that you can fix `down_revision` in the migration file.

Manually write **all 22 index creation calls** inside `upgrade()` and the corresponding `drop_index` calls inside `downgrade()`:

```python
def upgrade():
    # --- quote ---
    op.create_index('ix_quote_currency', 'quote', ['currency'])

    # --- qco_line_type ---
    op.create_index('ix_qco_line_type_tenant_id', 'qco_line_type', ['tenant_id'])

    # --- quote_line ---
    op.create_index('ix_quote_line_qco_line_type_id', 'quote_line', ['qco_line_type_id'])
    op.create_index('ix_quote_line_supplier_id', 'quote_line', ['supplier_id'])
    op.create_index('ix_quote_line_supplier_item_id', 'quote_line', ['supplier_item_id'])
    op.create_index('ix_quote_line_taxability_code', 'quote_line', ['taxability_code'])
    op.create_index('ix_quote_line_pricebook_item_id', 'quote_line', ['pricebook_item_id'])

    # --- quote_public_link ---
    op.create_index('ix_quote_public_link_contact_id', 'quote_public_link', ['contact_id'])
    op.create_index('ix_quote_public_link_quote_id', 'quote_public_link', ['quote_id'])
    op.create_index('ix_quote_public_link_status_id', 'quote_public_link', ['status_id'])

    # --- quote_message ---
    op.create_index('ix_quote_message_quote_id', 'quote_message', ['quote_id'])
    op.create_index('ix_quote_message_contact_id', 'quote_message', ['contact_id'])

    # --- job_attachment ---
    op.create_index('ix_job_attachment_tenant_id', 'job_attachment', ['tenant_id'])

    # --- job_expense_category ---
    op.create_index('ix_job_expense_category_tenant_id', 'job_expense_category', ['tenant_id'])

    # --- job_expense ---
    op.create_index('ix_job_expense_job_expense_category_code', 'job_expense', ['job_expense_category_code'])
    op.create_index('ix_job_expense_invoice_line_id', 'job_expense', ['invoice_line_id'])

    # --- job_assignment ---
    op.create_index('ix_job_assignment_tenant_id', 'job_assignment', ['tenant_id'])

    # --- change_order_line ---
    op.create_index('ix_change_order_line_qco_line_type_id', 'change_order_line', ['qco_line_type_id'])
    op.create_index('ix_change_order_line_supplier_id', 'change_order_line', ['supplier_id'])
    op.create_index('ix_change_order_line_supplier_item_id', 'change_order_line', ['supplier_item_id'])
    op.create_index('ix_change_order_line_taxability_code', 'change_order_line', ['taxability_code'])
    op.create_index('ix_change_order_line_pricebook_item_id', 'change_order_line', ['pricebook_item_id'])


def downgrade():
    op.drop_index('ix_quote_currency', table_name='quote')
    op.drop_index('ix_qco_line_type_tenant_id', table_name='qco_line_type')
    op.drop_index('ix_quote_line_qco_line_type_id', table_name='quote_line')
    op.drop_index('ix_quote_line_supplier_id', table_name='quote_line')
    op.drop_index('ix_quote_line_supplier_item_id', table_name='quote_line')
    op.drop_index('ix_quote_line_taxability_code', table_name='quote_line')
    op.drop_index('ix_quote_line_pricebook_item_id', table_name='quote_line')
    op.drop_index('ix_quote_public_link_contact_id', table_name='quote_public_link')
    op.drop_index('ix_quote_public_link_quote_id', table_name='quote_public_link')
    op.drop_index('ix_quote_public_link_status_id', table_name='quote_public_link')
    op.drop_index('ix_quote_message_quote_id', table_name='quote_message')
    op.drop_index('ix_quote_message_contact_id', table_name='quote_message')
    op.drop_index('ix_job_attachment_tenant_id', table_name='job_attachment')
    op.drop_index('ix_job_expense_category_tenant_id', table_name='job_expense_category')
    op.drop_index('ix_job_expense_job_expense_category_code', table_name='job_expense')
    op.drop_index('ix_job_expense_invoice_line_id', table_name='job_expense')
    op.drop_index('ix_job_assignment_tenant_id', table_name='job_assignment')
    op.drop_index('ix_change_order_line_qco_line_type_id', table_name='change_order_line')
    op.drop_index('ix_change_order_line_supplier_id', table_name='change_order_line')
    op.drop_index('ix_change_order_line_supplier_item_id', table_name='change_order_line')
    op.drop_index('ix_change_order_line_taxability_code', table_name='change_order_line')
    op.drop_index('ix_change_order_line_pricebook_item_id', table_name='change_order_line')
```

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json`. Inside each affected table, add the new index to the `"indexes"` array.

✅ **CORRECT JSON PATTERN** (example for `quote_line`):
```json
"indexes": [
  {
    "name": "ix_quote_line_qco_line_type_id",
    "definition": "CREATE INDEX ix_quote_line_qco_line_type_id ON public.quote_line USING btree (qco_line_type_id)"
  },
  {
    "name": "ix_quote_line_supplier_id",
    "definition": "CREATE INDEX ix_quote_line_supplier_id ON public.quote_line USING btree (supplier_id)"
  },
  {
    "name": "ix_quote_line_supplier_item_id",
    "definition": "CREATE INDEX ix_quote_line_supplier_item_id ON public.quote_line USING btree (supplier_item_id)"
  },
  {
    "name": "ix_quote_line_taxability_code",
    "definition": "CREATE INDEX ix_quote_line_taxability_code ON public.quote_line USING btree (taxability_code)"
  },
  {
    "name": "ix_quote_line_pricebook_item_id",
    "definition": "CREATE INDEX ix_quote_line_pricebook_item_id ON public.quote_line USING btree (pricebook_item_id)"
  }
]
```

Apply this pattern for every index in the scope table above — **22 total index entries** across 10 tables.

*Ask the user to run `python schema_diff.py --group-by environment`* to prove 0 discrepancies exist and give you the results. This is because the user will need to dump the db schema file, then copy it over to the `dev-docs/db-design/` folder, then run the schema diff script.

### Step 4: Regression Testing
Run the Pytest suite to ensure no syntax errors or model initialization failures occurred.

```bash
cd backend
source .venv/bin/activate

# Unit tests only first
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# All tests once unit tests are green
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

---

## 🛑 Stop & Rollback Conditions

**Immediately halt and notify the user if:**
1. `alembic upgrade head` fails because an index with that name already exists. Run `alembic downgrade -1` and investigate.
2. Generating the JSON discrepancy report shows unexpected missing constraints or dropped columns.

---

## ✅ Definition of Done (Checklist)

- [ ] Captured pre-modification test baseline.
- [ ] SQLModel updated with `index=True` for all 22 target FK columns across 10 tables.
- [ ] Blank Alembic migration created (`phase_8_0_batch_4_indexes_quoting_jobs`) and manually coded with all 22 `op.create_index` calls.
- [ ] Alembic migration applies successfully (`alembic upgrade head`) and `alembic downgrade -1` works cleanly.
- [ ] `pilot-db-schema-v2.6h.json` updated with explicit `CREATE INDEX` definitions for all 22 new indexes.
- [ ] `python schema_diff.py` reports ZERO discrepancies.
- [ ] 100% of the test suite passes with zero regressions.
- [ ] Document updated with final test counts.

Final Test Counts:
Unit tests: ___ passed, ___ skipped
All tests: ___ passed, ___ skipped (0 failures)
