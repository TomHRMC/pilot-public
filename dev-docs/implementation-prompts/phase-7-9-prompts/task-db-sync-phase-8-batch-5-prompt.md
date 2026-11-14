# Phase 8.0 Batch 5: Billing & Subscriptions - FK Indexing

**Reference:** `dev-docs/analysis/phase-8.0-db-schema-fk-indexes-plan.md` - Batch 5
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Find which `.py` file contains each table.
**Type:** Phase 8.0 - Performance Optimization
**Priority:** HIGH
**Change Type:** ORM UPDATES + SCHEMA INDEXING + JSON SYNC

---

## 📑 Context

This is **Phase 8.0 - Structural Foreign Key Indexing**. PostgreSQL does not automatically index Foreign Keys. An audit revealed critical structural Foreign Keys across our schema that are missing indexes, causing sequential table scans during JOINs and cascading deletes.

**Your Goal:** Add B-Tree indexes to the structural Foreign Keys for the tables in this batch. **Do NOT index `created_by` or `updated_by` columns.** We are only indexing structural relationships (e.g., `tenant_id`, `product_plan_code`, `payment_method_id`).

> **Note:** `invoice_status`, `payment_status`, `payment_type`, `subscription_status`, `product_plan`, `product_plan_version`, and `product_feature` are in the Batch 5 domain scope but were **not flagged by the audit** as having missing structural FK indexes. No action is required for those seven tables.

---

## 🎯 Current Task: Batch 5 - Billing & Subscriptions

**Scope:** Apply indexes to the following Foreign Key columns in this batch:

### `invoice`
| FK Column | References Table | New Index Name |
|---|---|---|
| `currency` | `currency` | `ix_invoice_currency` |

### `invoice_line`
| FK Column | References Table | New Index Name |
|---|---|---|
| `qco_line_type_id` | `qco_line_type` | `ix_invoice_line_qco_line_type_id` |
| `taxability_code` | `taxability_code` | `ix_invoice_line_taxability_code` |
| `pricebook_item_id` | `pricebook_item` | `ix_invoice_line_pricebook_item_id` |

### `payment`
| FK Column | References Table | New Index Name |
|---|---|---|
| `status_id` | `payment_status` | `ix_payment_status_id` |
| `payment_method_id` | `payment_method` | `ix_payment_payment_method_id` |
| `connector_config_id` | `connector_config` | `ix_payment_connector_config_id` |

### `payment_method`
| FK Column | References Table | New Index Name |
|---|---|---|
| `payment_type_id` | `payment_type` | `ix_payment_method_payment_type_id` |
| `billing_address_id` | `address` | `ix_payment_method_billing_address_id` |

### `psp_customer`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_psp_customer_tenant_id` |

### `psp_transaction_log`
| FK Column | References Table | New Index Name |
|---|---|---|
| `app_service_id` | `app_service` | `ix_psp_transaction_log_app_service_id` |

### `subscription`
| FK Column | References Table | New Index Name |
|---|---|---|
| `product_plan_code` | `product_plan` | `ix_subscription_product_plan_code` |
| `status_id` | `subscription_status` | `ix_subscription_status_id` |

### `subscription_usage`
| FK Column | References Table | New Index Name |
|---|---|---|
| `product_feature_code` | `product_feature` | `ix_subscription_usage_product_feature_code` |

### `usage_ledger`
| FK Column | References Table | New Index Name |
|---|---|---|
| `product_feature_code` | `product_feature` | `ix_usage_ledger_product_feature_code` |

### `product_plan_product_feature_version`
| FK Column | References Table | New Index Name |
|---|---|---|
| `product_feature_code` | `product_feature` | `ix_product_plan_product_feature_version_product_feature_code` |

### `tenant_product_feature_override`
| FK Column | References Table | New Index Name |
|---|---|---|
| `product_feature_code` | `product_feature` | `ix_tenant_product_feature_override_product_feature_code` |

### `discount_version`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_discount_version_tenant_id` |

**Total indexes to create in this batch: 18**

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
# invoice model
currency: str = Field(foreign_key="currency.code", index=True)

# invoice_line model
qco_line_type_id: int = Field(foreign_key="qco_line_type.id", index=True)
taxability_code: str = Field(foreign_key="taxability_code.code", index=True)
pricebook_item_id: uuid.UUID = Field(foreign_key="pricebook_item.id", index=True)

# payment model
status_id: int = Field(foreign_key="payment_status.id", index=True)
payment_method_id: uuid.UUID = Field(foreign_key="payment_method.id", index=True)
connector_config_id: uuid.UUID = Field(foreign_key="connector_config.id", index=True)

# payment_method model
payment_type_id: int = Field(foreign_key="payment_type.id", index=True)
billing_address_id: uuid.UUID = Field(foreign_key="address.id", index=True)

# psp_customer model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# psp_transaction_log model
app_service_id: uuid.UUID = Field(foreign_key="app_service.id", index=True)

# subscription model
product_plan_code: str = Field(foreign_key="product_plan.code", index=True)
status_id: int = Field(foreign_key="subscription_status.id", index=True)

# subscription_usage model
product_feature_code: str = Field(foreign_key="product_feature.code", index=True)

# usage_ledger model
product_feature_code: str = Field(foreign_key="product_feature.code", index=True)

# product_plan_product_feature_version model
product_feature_code: str = Field(foreign_key="product_feature.code", index=True)

# tenant_product_feature_override model
product_feature_code: str = Field(foreign_key="product_feature.code", index=True)

# discount_version model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
```

### Step 2: Manual Database Migration (Alembic)
❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs. Generate a **blank** migration:
```bash
alembic revision -m "phase_8_0_batch_5_indexes_billing_subscriptions"
```

NOTE: Make sure you check `alembic history` and get the previous migration so that you can fix `down_revision` in the migration file.

Manually write **all 18 index creation calls** inside `upgrade()` and the corresponding `drop_index` calls inside `downgrade()`:

```python
def upgrade():
    # --- invoice ---
    op.create_index('ix_invoice_currency', 'invoice', ['currency'])

    # --- invoice_line ---
    op.create_index('ix_invoice_line_qco_line_type_id', 'invoice_line', ['qco_line_type_id'])
    op.create_index('ix_invoice_line_taxability_code', 'invoice_line', ['taxability_code'])
    op.create_index('ix_invoice_line_pricebook_item_id', 'invoice_line', ['pricebook_item_id'])

    # --- payment ---
    op.create_index('ix_payment_status_id', 'payment', ['status_id'])
    op.create_index('ix_payment_payment_method_id', 'payment', ['payment_method_id'])
    op.create_index('ix_payment_connector_config_id', 'payment', ['connector_config_id'])

    # --- payment_method ---
    op.create_index('ix_payment_method_payment_type_id', 'payment_method', ['payment_type_id'])
    op.create_index('ix_payment_method_billing_address_id', 'payment_method', ['billing_address_id'])

    # --- psp_customer ---
    op.create_index('ix_psp_customer_tenant_id', 'psp_customer', ['tenant_id'])

    # --- psp_transaction_log ---
    op.create_index('ix_psp_transaction_log_app_service_id', 'psp_transaction_log', ['app_service_id'])

    # --- subscription ---
    op.create_index('ix_subscription_product_plan_code', 'subscription', ['product_plan_code'])
    op.create_index('ix_subscription_status_id', 'subscription', ['status_id'])

    # --- subscription_usage ---
    op.create_index('ix_subscription_usage_product_feature_code', 'subscription_usage', ['product_feature_code'])

    # --- usage_ledger ---
    op.create_index('ix_usage_ledger_product_feature_code', 'usage_ledger', ['product_feature_code'])

    # --- product_plan_product_feature_version ---
    op.create_index('ix_product_plan_product_feature_version_product_feature_code', 'product_plan_product_feature_version', ['product_feature_code'])

    # --- tenant_product_feature_override ---
    op.create_index('ix_tenant_product_feature_override_product_feature_code', 'tenant_product_feature_override', ['product_feature_code'])

    # --- discount_version ---
    op.create_index('ix_discount_version_tenant_id', 'discount_version', ['tenant_id'])


def downgrade():
    op.drop_index('ix_invoice_currency', table_name='invoice')
    op.drop_index('ix_invoice_line_qco_line_type_id', table_name='invoice_line')
    op.drop_index('ix_invoice_line_taxability_code', table_name='invoice_line')
    op.drop_index('ix_invoice_line_pricebook_item_id', table_name='invoice_line')
    op.drop_index('ix_payment_status_id', table_name='payment')
    op.drop_index('ix_payment_payment_method_id', table_name='payment')
    op.drop_index('ix_payment_connector_config_id', table_name='payment')
    op.drop_index('ix_payment_method_payment_type_id', table_name='payment_method')
    op.drop_index('ix_payment_method_billing_address_id', table_name='payment_method')
    op.drop_index('ix_psp_customer_tenant_id', table_name='psp_customer')
    op.drop_index('ix_psp_transaction_log_app_service_id', table_name='psp_transaction_log')
    op.drop_index('ix_subscription_product_plan_code', table_name='subscription')
    op.drop_index('ix_subscription_status_id', table_name='subscription')
    op.drop_index('ix_subscription_usage_product_feature_code', table_name='subscription_usage')
    op.drop_index('ix_usage_ledger_product_feature_code', table_name='usage_ledger')
    op.drop_index('ix_product_plan_product_feature_version_product_feature_code', table_name='product_plan_product_feature_version')
    op.drop_index('ix_tenant_product_feature_override_product_feature_code', table_name='tenant_product_feature_override')
    op.drop_index('ix_discount_version_tenant_id', table_name='discount_version')
```

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json`. Inside each affected table, add the new index to the `"indexes"` array.

✅ **CORRECT JSON PATTERN** (example for `invoice_line`):
```json
"indexes": [
  {
    "name": "ix_invoice_line_qco_line_type_id",
    "definition": "CREATE INDEX ix_invoice_line_qco_line_type_id ON public.invoice_line USING btree (qco_line_type_id)"
  },
  {
    "name": "ix_invoice_line_taxability_code",
    "definition": "CREATE INDEX ix_invoice_line_taxability_code ON public.invoice_line USING btree (taxability_code)"
  },
  {
    "name": "ix_invoice_line_pricebook_item_id",
    "definition": "CREATE INDEX ix_invoice_line_pricebook_item_id ON public.invoice_line USING btree (pricebook_item_id)"
  }
]
```

Apply this pattern for every index in the scope table above — **18 total index entries** across 13 tables.

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

- [x] Captured pre-modification test baseline.
- [x] SQLModel updated with `index=True` for all 18 target FK columns across 13 tables.
- [x] Blank Alembic migration created (`phase_8_0_batch_5_indexes_billing_subscriptions`) and manually coded with all 18 `op.create_index` calls.
- [x] Alembic migration applies successfully (`alembic upgrade head`) and `alembic downgrade -1` works cleanly.
- [x] `pilot-db-schema-v2.6h.json` updated with explicit `CREATE INDEX` definitions for all 18 new indexes.
- [ ] `python schema_diff.py` reports ZERO discrepancies. *(Requires user to dump DB schema and run diff script)*
- [x] 100% of the test suite passes with zero regressions.
- [x] Document updated with final test counts.

Final Test Counts:
Unit tests: 872 passed, 1 skipped
All tests: 899 passed, 1 skipped (0 failures)
