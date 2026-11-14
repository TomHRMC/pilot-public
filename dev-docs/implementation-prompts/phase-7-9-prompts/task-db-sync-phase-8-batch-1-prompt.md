# Phase 8.0 Batch 1: Tenant, Auth & User Management - FK Indexing

**Reference:** `dev-docs/analysis/phase-8.0-db-schema-fk-indexes-plan.md` - Batch 1
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Find which `.py` file contains each table.
**Type:** Phase 8.0 - Performance Optimization
**Priority:** HIGH
**Change Type:** ORM UPDATES + SCHEMA INDEXING + JSON SYNC

---

## 📑 Context

This is **Phase 8.0 - Structural Foreign Key Indexing**. PostgreSQL does not automatically index Foreign Keys. An audit revealed critical structural Foreign Keys across our schema that are missing indexes, causing sequential table scans during JOINs and cascading deletes.

**Your Goal:** Add B-Tree indexes to the structural Foreign Keys for the tables in this batch. **Do NOT index `created_by` or `updated_by` columns.** We are only indexing structural relationships (e.g., `tenant_id`, `user_id`, `role_code`).

---

## 🎯 Current Task: Batch 1 - Tenant, Auth & User Management

**Scope:** Apply indexes to the following Foreign Key columns in this batch:

### `user`
| FK Column | References Table | New Index Name |
|---|---|---|
| `platform_role_code` | `platform_role` | `ix_user_platform_role_code` |

### `user_preference`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_user_preference_tenant_id` |

### `tenant_user`
| FK Column | References Table | New Index Name |
|---|---|---|
| `role_code` | `tenant_user_role` | `ix_tenant_user_role_code` |
| `status_id` | `tenant_user_status` | `ix_tenant_user_status_id` |
| `suspended_by` | `user` | `ix_tenant_user_suspended_by` |

### `tenant_user_invite`
| FK Column | References Table | New Index Name |
|---|---|---|
| `invited_by` | `user` | `ix_tenant_user_invite_invited_by` |

### `password_policy`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_password_policy_tenant_id` |

### `auth_refresh_token`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_auth_refresh_token_tenant_id` |
| `user_id` | `user` | `ix_auth_refresh_token_user_id` |

### `auth_password_reset`
| FK Column | References Table | New Index Name |
|---|---|---|
| `user_id` | `user` | `ix_auth_password_reset_user_id` |
| `contact_id` | `contact` | `ix_auth_password_reset_contact_id` |

### `auth_email_verification`
| FK Column | References Table | New Index Name |
|---|---|---|
| `user_id` | `user` | `ix_auth_email_verification_user_id` |
| `contact_id` | `contact` | `ix_auth_email_verification_contact_id` |

### `auth_mfa_otp`
| FK Column | References Table | New Index Name |
|---|---|---|
| `user_id` | `user` | `ix_auth_mfa_otp_user_id` |
| `contact_id` | `contact` | `ix_auth_mfa_otp_contact_id` |
| `user_endpoint_id` | `user_endpoint` | `ix_auth_mfa_otp_user_endpoint_id` |

### `auth_password_history`
| FK Column | References Table | New Index Name |
|---|---|---|
| `user_id` | `user` | `ix_auth_password_history_user_id` |
| `contact_id` | `contact` | `ix_auth_password_history_contact_id` |

### `auth_api_token`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_auth_api_token_tenant_id` |
| `user_id` | `user` | `ix_auth_api_token_user_id` |

### `auth_jwk`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_auth_jwk_tenant_id` |
| `jwk_status_id` | `jwk_status` | `ix_auth_jwk_jwk_status_id` |

### `idempotency_key`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_idempotency_key_tenant_id` |
| `user_id` | `user` | `ix_idempotency_key_user_id` |

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
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
```

Apply `index=True` to every FK column listed in the scope table above. Example entries for this batch:

```python
# user model
platform_role_code: str = Field(foreign_key="platform_role.code", index=True)

# user_preference model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# tenant_user model
role_code: str = Field(foreign_key="tenant_user_role.code", index=True)
status_id: int = Field(foreign_key="tenant_user_status.id", index=True)
suspended_by: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", index=True)

# tenant_user_invite model
invited_by: uuid.UUID = Field(foreign_key="user.id", index=True)

# password_policy model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# auth_refresh_token model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
user_id: uuid.UUID = Field(foreign_key="user.id", index=True)

# auth_password_reset model
user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", index=True)
contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contact.id", index=True)

# auth_email_verification model
user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", index=True)
contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contact.id", index=True)

# auth_mfa_otp model
user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", index=True)
contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contact.id", index=True)
user_endpoint_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user_endpoint.id", index=True)

# auth_password_history model
user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", index=True)
contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contact.id", index=True)

# auth_api_token model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
user_id: uuid.UUID = Field(foreign_key="user.id", index=True)

# auth_jwk model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
jwk_status_id: int = Field(foreign_key="jwk_status.id", index=True)

# idempotency_key model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", index=True)
```

### Step 2: Manual Database Migration (Alembic)
❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs. Generate a **blank** migration:
```bash
alembic revision -m "phase_8_0_batch_1_indexes_tenant_auth_user"
```

Manually write **all 22 index creation calls** inside `upgrade()` and the corresponding `drop_index` calls inside `downgrade()`:

```python
def upgrade():
    # --- user ---
    op.create_index('ix_user_platform_role_code', 'user', ['platform_role_code'])

    # --- user_preference ---
    op.create_index('ix_user_preference_tenant_id', 'user_preference', ['tenant_id'])

    # --- tenant_user ---
    op.create_index('ix_tenant_user_role_code', 'tenant_user', ['role_code'])
    op.create_index('ix_tenant_user_status_id', 'tenant_user', ['status_id'])
    op.create_index('ix_tenant_user_suspended_by', 'tenant_user', ['suspended_by'])

    # --- tenant_user_invite ---
    op.create_index('ix_tenant_user_invite_invited_by', 'tenant_user_invite', ['invited_by'])

    # --- password_policy ---
    op.create_index('ix_password_policy_tenant_id', 'password_policy', ['tenant_id'])

    # --- auth_refresh_token ---
    op.create_index('ix_auth_refresh_token_tenant_id', 'auth_refresh_token', ['tenant_id'])
    op.create_index('ix_auth_refresh_token_user_id', 'auth_refresh_token', ['user_id'])

    # --- auth_password_reset ---
    op.create_index('ix_auth_password_reset_user_id', 'auth_password_reset', ['user_id'])
    op.create_index('ix_auth_password_reset_contact_id', 'auth_password_reset', ['contact_id'])

    # --- auth_email_verification ---
    op.create_index('ix_auth_email_verification_user_id', 'auth_email_verification', ['user_id'])
    op.create_index('ix_auth_email_verification_contact_id', 'auth_email_verification', ['contact_id'])

    # --- auth_mfa_otp ---
    op.create_index('ix_auth_mfa_otp_user_id', 'auth_mfa_otp', ['user_id'])
    op.create_index('ix_auth_mfa_otp_contact_id', 'auth_mfa_otp', ['contact_id'])
    op.create_index('ix_auth_mfa_otp_user_endpoint_id', 'auth_mfa_otp', ['user_endpoint_id'])

    # --- auth_password_history ---
    op.create_index('ix_auth_password_history_user_id', 'auth_password_history', ['user_id'])
    op.create_index('ix_auth_password_history_contact_id', 'auth_password_history', ['contact_id'])

    # --- auth_api_token ---
    op.create_index('ix_auth_api_token_tenant_id', 'auth_api_token', ['tenant_id'])
    op.create_index('ix_auth_api_token_user_id', 'auth_api_token', ['user_id'])

    # --- auth_jwk ---
    op.create_index('ix_auth_jwk_tenant_id', 'auth_jwk', ['tenant_id'])
    op.create_index('ix_auth_jwk_jwk_status_id', 'auth_jwk', ['jwk_status_id'])

    # --- idempotency_key ---
    op.create_index('ix_idempotency_key_tenant_id', 'idempotency_key', ['tenant_id'])
    op.create_index('ix_idempotency_key_user_id', 'idempotency_key', ['user_id'])


def downgrade():
    op.drop_index('ix_user_platform_role_code', table_name='user')
    op.drop_index('ix_user_preference_tenant_id', table_name='user_preference')
    op.drop_index('ix_tenant_user_role_code', table_name='tenant_user')
    op.drop_index('ix_tenant_user_status_id', table_name='tenant_user')
    op.drop_index('ix_tenant_user_suspended_by', table_name='tenant_user')
    op.drop_index('ix_tenant_user_invite_invited_by', table_name='tenant_user_invite')
    op.drop_index('ix_password_policy_tenant_id', table_name='password_policy')
    op.drop_index('ix_auth_refresh_token_tenant_id', table_name='auth_refresh_token')
    op.drop_index('ix_auth_refresh_token_user_id', table_name='auth_refresh_token')
    op.drop_index('ix_auth_password_reset_user_id', table_name='auth_password_reset')
    op.drop_index('ix_auth_password_reset_contact_id', table_name='auth_password_reset')
    op.drop_index('ix_auth_email_verification_user_id', table_name='auth_email_verification')
    op.drop_index('ix_auth_email_verification_contact_id', table_name='auth_email_verification')
    op.drop_index('ix_auth_mfa_otp_user_id', table_name='auth_mfa_otp')
    op.drop_index('ix_auth_mfa_otp_contact_id', table_name='auth_mfa_otp')
    op.drop_index('ix_auth_mfa_otp_user_endpoint_id', table_name='auth_mfa_otp')
    op.drop_index('ix_auth_password_history_user_id', table_name='auth_password_history')
    op.drop_index('ix_auth_password_history_contact_id', table_name='auth_password_history')
    op.drop_index('ix_auth_api_token_tenant_id', table_name='auth_api_token')
    op.drop_index('ix_auth_api_token_user_id', table_name='auth_api_token')
    op.drop_index('ix_auth_jwk_tenant_id', table_name='auth_jwk')
    op.drop_index('ix_auth_jwk_jwk_status_id', table_name='auth_jwk')
    op.drop_index('ix_idempotency_key_tenant_id', table_name='idempotency_key')
    op.drop_index('ix_idempotency_key_user_id', table_name='idempotency_key')
```

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json`. Inside each affected table, add the new index to the `"indexes"` array.

✅ **CORRECT JSON PATTERN** (example for `auth_refresh_token`):
```json
"indexes": [
  {
    "name": "ix_auth_refresh_token_tenant_id",
    "definition": "CREATE INDEX ix_auth_refresh_token_tenant_id ON public.auth_refresh_token USING btree (tenant_id)"
  },
  {
    "name": "ix_auth_refresh_token_user_id",
    "definition": "CREATE INDEX ix_auth_refresh_token_user_id ON public.auth_refresh_token USING btree (user_id)"
  }
]
```

Apply this pattern for every index in the scope table above — **24 total index entries** across 14 tables.

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
- [ ] SQLModel updated with `index=True` for all 24 target FK columns across 14 tables.
- [ ] Blank Alembic migration created (`phase_8_0_batch_1_indexes_tenant_auth_user`) and manually coded with all 24 `op.create_index` calls.
- [ ] Alembic migration applies successfully (`alembic upgrade head`) and `alembic downgrade -1` works cleanly.
- [ ] `pilot-db-schema-v2.6h.json` updated with explicit `CREATE INDEX` definitions for all 24 new indexes.
- [ ] `python schema_diff.py` reports ZERO discrepancies.
- [ ] 100% of the test suite passes with zero regressions.
- [ ] Document updated with final test counts.

Final Test Counts:
Unit tests: 872 passed, 1 skipped
All tests: 900 passed, 1 skipped (0 failures — fixed test_voice_multi_turn_e2e.py: added tenant_id to all ConversationMessage instantiations)
