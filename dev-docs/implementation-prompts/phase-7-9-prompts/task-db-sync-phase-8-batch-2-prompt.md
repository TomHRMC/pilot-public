# Phase 8.0 Batch 2: CRM & Contacts - FK Indexing

**Reference:** `dev-docs/analysis/phase-8.0-db-schema-fk-indexes-plan.md` - Batch 2
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Find which `.py` file contains each table.
**Type:** Phase 8.0 - Performance Optimization
**Priority:** HIGH
**Change Type:** ORM UPDATES + SCHEMA INDEXING + JSON SYNC

---

## 📑 Context

This is **Phase 8.0 - Structural Foreign Key Indexing**. PostgreSQL does not automatically index Foreign Keys. An audit revealed critical structural Foreign Keys across our schema that are missing indexes, causing sequential table scans during JOINs and cascading deletes.

**Your Goal:** Add B-Tree indexes to the structural Foreign Keys for the tables in this batch. **Do NOT index `created_by` or `updated_by` columns.** We are only indexing structural relationships (e.g., `tenant_id`, `customer_id`, `contact_type_code`).

---

## 🎯 Current Task: Batch 2 - CRM & Contacts

**Scope:** Apply indexes to the following Foreign Key columns in this batch:

### `customer`
| FK Column | References Table | New Index Name |
|---|---|---|
| `lifecycle_status_id` | `customer_lifecycle_status` | `ix_customer_lifecycle_status_id` |

### `site`
| FK Column | References Table | New Index Name |
|---|---|---|
| `customer_id` | `customer` | `ix_site_customer_id` |
| `lifecycle_status_id` | `site_lifecycle_status` | `ix_site_lifecycle_status_id` |

### `contact_type`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_contact_type_tenant_id` |

### `entity_contact`
| FK Column | References Table | New Index Name |
|---|---|---|
| `contact_type_code` | `contact_type` | `ix_entity_contact_contact_type_code` |

### `address_type`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_address_type_tenant_id` |

### `entity_address`
| FK Column | References Table | New Index Name |
|---|---|---|
| `address_type_code` | `address_type` | `ix_entity_address_address_type_code` |

### `quote_public_link_contact_action`
| FK Column | References Table | New Index Name |
|---|---|---|
| `qpl_contact_action_type_id` | `qpl_contact_action_type` | `ix_quote_public_link_contact_action_qpl_contact_action_type_id` |

### `quote_acceptance`
| FK Column | References Table | New Index Name |
|---|---|---|
| `contact_id` | `contact` | `ix_quote_acceptance_contact_id` |
| `accepted_by_user_id` | `user` | `ix_quote_acceptance_accepted_by_user_id` |
| `quote_public_link_id` | `quote_public_link` | `ix_quote_acceptance_quote_public_link_id` |

**Total indexes to create in this batch: 11**

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
# customer model
lifecycle_status_id: int = Field(foreign_key="customer_lifecycle_status.id", index=True)

# site model
customer_id: uuid.UUID = Field(foreign_key="customer.id", index=True)
lifecycle_status_id: int = Field(foreign_key="site_lifecycle_status.id", index=True)

# contact_type model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# entity_contact model
contact_type_code: str = Field(foreign_key="contact_type.code", index=True)

# address_type model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# entity_address model
address_type_code: str = Field(foreign_key="address_type.code", index=True)

# quote_public_link_contact_action model
qpl_contact_action_type_id: int = Field(foreign_key="qpl_contact_action_type.id", index=True)

# quote_acceptance model
contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contact.id", index=True)
accepted_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", index=True)
quote_public_link_id: uuid.UUID = Field(foreign_key="quote_public_link.id", index=True)
```

### Step 2: Manual Database Migration (Alembic)
❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs. Generate a **blank** migration:
```bash
alembic revision -m "phase_8_0_batch_2_indexes_crm_contacts"
```

Manually write **all 11 index creation calls** inside `upgrade()` and the corresponding `drop_index` calls inside `downgrade()`:

```python
def upgrade():
    # --- customer ---
    op.create_index('ix_customer_lifecycle_status_id', 'customer', ['lifecycle_status_id'])

    # --- site ---
    op.create_index('ix_site_customer_id', 'site', ['customer_id'])
    op.create_index('ix_site_lifecycle_status_id', 'site', ['lifecycle_status_id'])

    # --- contact_type ---
    op.create_index('ix_contact_type_tenant_id', 'contact_type', ['tenant_id'])

    # --- entity_contact ---
    op.create_index('ix_entity_contact_contact_type_code', 'entity_contact', ['contact_type_code'])

    # --- address_type ---
    op.create_index('ix_address_type_tenant_id', 'address_type', ['tenant_id'])

    # --- entity_address ---
    op.create_index('ix_entity_address_address_type_code', 'entity_address', ['address_type_code'])

    # --- quote_public_link_contact_action ---
    op.create_index('ix_quote_public_link_contact_action_qpl_contact_action_type_id', 'quote_public_link_contact_action', ['qpl_contact_action_type_id'])

    # --- quote_acceptance ---
    op.create_index('ix_quote_acceptance_contact_id', 'quote_acceptance', ['contact_id'])
    op.create_index('ix_quote_acceptance_accepted_by_user_id', 'quote_acceptance', ['accepted_by_user_id'])
    op.create_index('ix_quote_acceptance_quote_public_link_id', 'quote_acceptance', ['quote_public_link_id'])


def downgrade():
    op.drop_index('ix_customer_lifecycle_status_id', table_name='customer')
    op.drop_index('ix_site_customer_id', table_name='site')
    op.drop_index('ix_site_lifecycle_status_id', table_name='site')
    op.drop_index('ix_contact_type_tenant_id', table_name='contact_type')
    op.drop_index('ix_entity_contact_contact_type_code', table_name='entity_contact')
    op.drop_index('ix_address_type_tenant_id', table_name='address_type')
    op.drop_index('ix_entity_address_address_type_code', table_name='entity_address')
    op.drop_index('ix_quote_public_link_contact_action_qpl_contact_action_type_id', table_name='quote_public_link_contact_action')
    op.drop_index('ix_quote_acceptance_contact_id', table_name='quote_acceptance')
    op.drop_index('ix_quote_acceptance_accepted_by_user_id', table_name='quote_acceptance')
    op.drop_index('ix_quote_acceptance_quote_public_link_id', table_name='quote_acceptance')
```

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json`. Inside each affected table, add the new index to the `"indexes"` array.

✅ **CORRECT JSON PATTERN** (example for `site`):
```json
"indexes": [
  {
    "name": "ix_site_customer_id",
    "definition": "CREATE INDEX ix_site_customer_id ON public.site USING btree (customer_id)"
  },
  {
    "name": "ix_site_lifecycle_status_id",
    "definition": "CREATE INDEX ix_site_lifecycle_status_id ON public.site USING btree (lifecycle_status_id)"
  }
]
```

Apply this pattern for every index in the scope table above — **11 total index entries** across 8 tables.

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
- [ ] SQLModel updated with `index=True` for all 11 target FK columns across 8 tables.
- [ ] Blank Alembic migration created (`phase_8_0_batch_2_indexes_crm_contacts`) and manually coded with all 11 `op.create_index` calls.
- [ ] Alembic migration applies successfully (`alembic upgrade head`) and `alembic downgrade -1` works cleanly.
- [ ] `pilot-db-schema-v2.6h.json` updated with explicit `CREATE INDEX` definitions for all 11 new indexes.
- [ ] `python schema_diff.py` reports ZERO discrepancies.
- [ ] 100% of the test suite passes with zero regressions.
- [ ] Document updated with final test counts.

Final Test Counts:
Unit tests: 872 passed, 1 skipped
All tests: 899 passed, 1 skipped (0 failures)
