# Phase 8.0 Batch 6: Communications, Integrations & AI - FK Indexing

**Reference:** `dev-docs/analysis/phase-8.0-db-schema-fk-indexes-plan.md` - Batch 6
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Find which `.py` file contains each table.
**Type:** Phase 8.0 - Performance Optimization
**Priority:** HIGH
**Change Type:** ORM UPDATES + SCHEMA INDEXING + JSON SYNC

---

## 📑 Context

This is **Phase 8.0 - Structural Foreign Key Indexing**. PostgreSQL does not automatically index Foreign Keys. An audit revealed critical structural Foreign Keys across our schema that are missing indexes, causing sequential table scans during JOINs and cascading deletes.

**Your Goal:** Add B-Tree indexes to the structural Foreign Keys for the tables in this batch. **Do NOT index `created_by` or `updated_by` columns.** We are only indexing structural relationships (e.g., `tenant_id`, `user_id`, `app_service_id`).

> **Note:** `notification_channel`, `tenant_notification_default`, `webhook_event_type`, `connector_config`, and `conversation_message` are in the Batch 6 domain scope but were **not flagged by the audit** as having missing structural FK indexes. No action is required for those five tables.

---

## 🎯 Current Task: Batch 6 - Communications, Integrations & AI

**Scope:** Apply indexes to the following Foreign Key columns in this batch:

### `notification_type`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_notification_type_tenant_id` |

### `notification_template`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_notification_template_tenant_id` |
| `notification_type_code` | `notification_type` | `ix_notification_template_notification_type_code` |

### `notification_event`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_notification_event_tenant_id` |
| `notification_type_code` | `notification_type` | `ix_notification_event_notification_type_code` |
| `entity_type_code` | `entity_type` | `ix_notification_event_entity_type_code` |

### `notification_outbox`
| FK Column | References Table | New Index Name |
|---|---|---|
| `notification_event_id` | `notification_event` | `ix_notification_outbox_notification_event_id` |
| `contact_endpoint_id` | `contact_endpoint` | `ix_notification_outbox_contact_endpoint_id` |
| `user_endpoint_id` | `user_endpoint` | `ix_notification_outbox_user_endpoint_id` |
| `recipient_contact_id` | `contact` | `ix_notification_outbox_recipient_contact_id` |
| `recipient_user_id` | `user` | `ix_notification_outbox_recipient_user_id` |

### `notification_delivery_attempt`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_notification_delivery_attempt_tenant_id` |

### `tenant_user_notification_pref`
| FK Column | References Table | New Index Name |
|---|---|---|
| `user_id` | `user` | `ix_tenant_user_notification_pref_user_id` |

### `webhook_event`
| FK Column | References Table | New Index Name |
|---|---|---|
| `event_type_code` | `webhook_event_type` | `ix_webhook_event_event_type_code` |

### `webhook_delivery_attempt`
| FK Column | References Table | New Index Name |
|---|---|---|
| `webhook_endpoint_id` | `webhook_endpoint` | `ix_webhook_delivery_attempt_webhook_endpoint_id` |

### `integration_credential`
| FK Column | References Table | New Index Name |
|---|---|---|
| `initiated_by_user_id` | `user` | `ix_integration_credential_initiated_by_user_id` |

### `integration_sync_mapping`
| FK Column | References Table | New Index Name |
|---|---|---|
| `tenant_id` | `tenant` | `ix_integration_sync_mapping_tenant_id` |

### `integration_sync_conflict`
| FK Column | References Table | New Index Name |
|---|---|---|
| `app_service_id` | `app_service` | `ix_integration_sync_conflict_app_service_id` |
| `entity_type_code` | `entity_type` | `ix_integration_sync_conflict_entity_type_code` |
| `resolved_by` | `user` | `ix_integration_sync_conflict_resolved_by` |

### `integration_sync_log`
| FK Column | References Table | New Index Name |
|---|---|---|
| `app_service_id` | `app_service` | `ix_integration_sync_log_app_service_id` |

### `conversation_session`
| FK Column | References Table | New Index Name |
|---|---|---|
| `user_id` | `user` | `ix_conversation_session_user_id` |

### `voice_command_log`
| FK Column | References Table | New Index Name |
|---|---|---|
| `user_id` | `user` | `ix_voice_command_log_user_id` |
| `message_id` | `conversation_message` | `ix_voice_command_log_message_id` |

**Total indexes to create in this batch: 24**

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
# notification_type model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# notification_template model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
notification_type_code: str = Field(foreign_key="notification_type.code", index=True)

# notification_event model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
notification_type_code: str = Field(foreign_key="notification_type.code", index=True)
entity_type_code: str = Field(foreign_key="entity_type.code", index=True)

# notification_outbox model
notification_event_id: uuid.UUID = Field(foreign_key="notification_event.id", index=True)
contact_endpoint_id: Optional[uuid.UUID] = Field(foreign_key="contact_endpoint.id", index=True)
user_endpoint_id: Optional[uuid.UUID] = Field(foreign_key="user_endpoint.id", index=True)
recipient_contact_id: Optional[uuid.UUID] = Field(foreign_key="contact.id", index=True)
recipient_user_id: Optional[uuid.UUID] = Field(foreign_key="user.id", index=True)

# notification_delivery_attempt model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# tenant_user_notification_pref model
user_id: uuid.UUID = Field(foreign_key="user.id", index=True)

# webhook_event model
event_type_code: str = Field(foreign_key="webhook_event_type.code", index=True)

# webhook_delivery_attempt model
webhook_endpoint_id: uuid.UUID = Field(foreign_key="webhook_endpoint.id", index=True)

# integration_credential model
initiated_by_user_id: uuid.UUID = Field(foreign_key="user.id", index=True)

# integration_sync_mapping model
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)

# integration_sync_conflict model
app_service_id: uuid.UUID = Field(foreign_key="app_service.id", index=True)
entity_type_code: str = Field(foreign_key="entity_type.code", index=True)
resolved_by: Optional[uuid.UUID] = Field(foreign_key="user.id", index=True)

# integration_sync_log model
app_service_id: uuid.UUID = Field(foreign_key="app_service.id", index=True)

# conversation_session model
user_id: uuid.UUID = Field(foreign_key="user.id", index=True)

# voice_command_log model
user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
message_id: uuid.UUID = Field(foreign_key="conversation_message.id", index=True)
```

### Step 2: Manual Database Migration (Alembic)
❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs. Generate a **blank** migration:
```bash
alembic revision -m "phase_8_0_batch_6_indexes_communications_integrations_ai"
```

NOTE: Make sure you check `alembic history` and get the previous migration so that you can fix `down_revision` in the migration file.

Manually write **all 24 index creation calls** inside `upgrade()` and the corresponding `drop_index` calls inside `downgrade()`:

```python
def upgrade():
    # --- notification_type ---
    op.create_index('ix_notification_type_tenant_id', 'notification_type', ['tenant_id'])

    # --- notification_template ---
    op.create_index('ix_notification_template_tenant_id', 'notification_template', ['tenant_id'])
    op.create_index('ix_notification_template_notification_type_code', 'notification_template', ['notification_type_code'])

    # --- notification_event ---
    op.create_index('ix_notification_event_tenant_id', 'notification_event', ['tenant_id'])
    op.create_index('ix_notification_event_notification_type_code', 'notification_event', ['notification_type_code'])
    op.create_index('ix_notification_event_entity_type_code', 'notification_event', ['entity_type_code'])

    # --- notification_outbox ---
    op.create_index('ix_notification_outbox_notification_event_id', 'notification_outbox', ['notification_event_id'])
    op.create_index('ix_notification_outbox_contact_endpoint_id', 'notification_outbox', ['contact_endpoint_id'])
    op.create_index('ix_notification_outbox_user_endpoint_id', 'notification_outbox', ['user_endpoint_id'])
    op.create_index('ix_notification_outbox_recipient_contact_id', 'notification_outbox', ['recipient_contact_id'])
    op.create_index('ix_notification_outbox_recipient_user_id', 'notification_outbox', ['recipient_user_id'])

    # --- notification_delivery_attempt ---
    op.create_index('ix_notification_delivery_attempt_tenant_id', 'notification_delivery_attempt', ['tenant_id'])

    # --- tenant_user_notification_pref ---
    op.create_index('ix_tenant_user_notification_pref_user_id', 'tenant_user_notification_pref', ['user_id'])

    # --- webhook_event ---
    op.create_index('ix_webhook_event_event_type_code', 'webhook_event', ['event_type_code'])

    # --- webhook_delivery_attempt ---
    op.create_index('ix_webhook_delivery_attempt_webhook_endpoint_id', 'webhook_delivery_attempt', ['webhook_endpoint_id'])

    # --- integration_credential ---
    op.create_index('ix_integration_credential_initiated_by_user_id', 'integration_credential', ['initiated_by_user_id'])

    # --- integration_sync_mapping ---
    op.create_index('ix_integration_sync_mapping_tenant_id', 'integration_sync_mapping', ['tenant_id'])

    # --- integration_sync_conflict ---
    op.create_index('ix_integration_sync_conflict_app_service_id', 'integration_sync_conflict', ['app_service_id'])
    op.create_index('ix_integration_sync_conflict_entity_type_code', 'integration_sync_conflict', ['entity_type_code'])
    op.create_index('ix_integration_sync_conflict_resolved_by', 'integration_sync_conflict', ['resolved_by'])

    # --- integration_sync_log ---
    op.create_index('ix_integration_sync_log_app_service_id', 'integration_sync_log', ['app_service_id'])

    # --- conversation_session ---
    op.create_index('ix_conversation_session_user_id', 'conversation_session', ['user_id'])

    # --- voice_command_log ---
    op.create_index('ix_voice_command_log_user_id', 'voice_command_log', ['user_id'])
    op.create_index('ix_voice_command_log_message_id', 'voice_command_log', ['message_id'])


def downgrade():
    op.drop_index('ix_notification_type_tenant_id', table_name='notification_type')
    op.drop_index('ix_notification_template_tenant_id', table_name='notification_template')
    op.drop_index('ix_notification_template_notification_type_code', table_name='notification_template')
    op.drop_index('ix_notification_event_tenant_id', table_name='notification_event')
    op.drop_index('ix_notification_event_notification_type_code', table_name='notification_event')
    op.drop_index('ix_notification_event_entity_type_code', table_name='notification_event')
    op.drop_index('ix_notification_outbox_notification_event_id', table_name='notification_outbox')
    op.drop_index('ix_notification_outbox_contact_endpoint_id', table_name='notification_outbox')
    op.drop_index('ix_notification_outbox_user_endpoint_id', table_name='notification_outbox')
    op.drop_index('ix_notification_outbox_recipient_contact_id', table_name='notification_outbox')
    op.drop_index('ix_notification_outbox_recipient_user_id', table_name='notification_outbox')
    op.drop_index('ix_notification_delivery_attempt_tenant_id', table_name='notification_delivery_attempt')
    op.drop_index('ix_tenant_user_notification_pref_user_id', table_name='tenant_user_notification_pref')
    op.drop_index('ix_webhook_event_event_type_code', table_name='webhook_event')
    op.drop_index('ix_webhook_delivery_attempt_webhook_endpoint_id', table_name='webhook_delivery_attempt')
    op.drop_index('ix_integration_credential_initiated_by_user_id', table_name='integration_credential')
    op.drop_index('ix_integration_sync_mapping_tenant_id', table_name='integration_sync_mapping')
    op.drop_index('ix_integration_sync_conflict_app_service_id', table_name='integration_sync_conflict')
    op.drop_index('ix_integration_sync_conflict_entity_type_code', table_name='integration_sync_conflict')
    op.drop_index('ix_integration_sync_conflict_resolved_by', table_name='integration_sync_conflict')
    op.drop_index('ix_integration_sync_log_app_service_id', table_name='integration_sync_log')
    op.drop_index('ix_conversation_session_user_id', table_name='conversation_session')
    op.drop_index('ix_voice_command_log_user_id', table_name='voice_command_log')
    op.drop_index('ix_voice_command_log_message_id', table_name='voice_command_log')
```

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json`. Inside each affected table, add the new index to the `"indexes"` array.

✅ **CORRECT JSON PATTERN** (example for `notification_outbox`):
```json
"indexes": [
  {
    "name": "ix_notification_outbox_notification_event_id",
    "definition": "CREATE INDEX ix_notification_outbox_notification_event_id ON public.notification_outbox USING btree (notification_event_id)"
  },
  {
    "name": "ix_notification_outbox_contact_endpoint_id",
    "definition": "CREATE INDEX ix_notification_outbox_contact_endpoint_id ON public.notification_outbox USING btree (contact_endpoint_id)"
  },
  {
    "name": "ix_notification_outbox_user_endpoint_id",
    "definition": "CREATE INDEX ix_notification_outbox_user_endpoint_id ON public.notification_outbox USING btree (user_endpoint_id)"
  },
  {
    "name": "ix_notification_outbox_recipient_contact_id",
    "definition": "CREATE INDEX ix_notification_outbox_recipient_contact_id ON public.notification_outbox USING btree (recipient_contact_id)"
  },
  {
    "name": "ix_notification_outbox_recipient_user_id",
    "definition": "CREATE INDEX ix_notification_outbox_recipient_user_id ON public.notification_outbox USING btree (recipient_user_id)"
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
- [ ] Blank Alembic migration created (`phase_8_0_batch_6_indexes_communications_integrations_ai`) and manually coded with all 24 `op.create_index` calls.
- [ ] Alembic migration applies successfully (`alembic upgrade head`) and `alembic downgrade -1` works cleanly.
- [ ] `pilot-db-schema-v2.6h.json` updated with explicit `CREATE INDEX` definitions for all 24 new indexes.
- [ ] `python schema_diff.py` reports ZERO discrepancies. *(Requires user to dump DB schema and run diff script)*
- [ ] 100% of the test suite passes with zero regressions.
- [ ] Document updated with final test counts.
