# Phase 7.0 Batch 5: Communications & Webhooks - Tenant Stamping

**Reference:** `dev-docs/analysis/phase-7.0-db-schema-cleanup-plan.md` - Batch 5
**Authority & Reference Maps:**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `backend/db_models_map.md` - Use this to find which `.py` file contains each table.
- `backend/app_model_imports.md` - Use this to ensure you are importing models correctly without causing circular dependencies.
**Type:** Phase 7.0 - Multi-Tenancy Security Hardening
**Priority:** CRITICAL SECURITY
**Change Type:** SCHEMA DENORMALIZATION + DATA MIGRATION + API REFACTORING + SECURITY TESTING

---

## 📑 Context

This is **Phase 7.0 - Tenant Stamping** — the **final batch**. We are mitigating High-Severity Insecure Direct Object Reference (IDOR) vulnerabilities. Because our PostgreSQL database does not use Row-Level Security (RLS), tenant isolation relies 100% on the application layer.

Currently, several polymorphic and deep-hierarchy tables lack a `tenant_id` column. If a malicious user guesses a valid UUID for one of these records, `session.get()` will return it, crossing the tenant boundary.

**The Solution:** We are denormalizing the schema by stamping a non-nullable `tenant_id` foreign key onto all vulnerable child tables, and refactoring the API to mandate tenant-scoped queries.

---

## 🎯 Current Task: Batch 5 - Communications & Webhooks

**Scope:** The following tables must be updated in this batch:
* `conversation_message`
* `webhook_delivery_attempt`

**Effort Estimate:** Medium. Both tables are straightforward single-hop FK backfills:
- `conversation_message` → backfill via `conversation_session` (join on `session_id`)
- `webhook_delivery_attempt` → backfill via `webhook_endpoint` (join on `webhook_endpoint_id`)

> ⚠️ **Critical Architecture Note for `webhook_delivery_attempt`:** The `webhook_event` table has a **nullable** `tenant_id` column and must **NOT** be used as the backfill source. Use `webhook_endpoint.tenant_id` exclusively — it is non-nullable and guaranteed to resolve for all records.

> ⚠️ **Critical Model Note for `webhook_delivery_attempt`:** This table's primary key `id` is a **serial INTEGER**, not a UUID. This is different from all previous Batch tables. Do not alter the `id` field. Only add the `tenant_id` UUID column.

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** Capture the current test baseline BEFORE making ANY changes. **You must always use the virtual environment for Python/Pytest commands.**

### Step 1: Activate Virtual Environment (REQUIRED FOR ALL TERMINAL COMMANDS)
```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run ALL Tests (Current Baseline)
```bash
# Run full test suite but without the integration tests FIRST
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5

# Run all tests SECOND
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

### Step 3: Document Your Baseline
**Record the output of both results before proceeding.** This is your regression checkpoint. ALL these tests MUST still pass after your work.

> 📊 **Expected Baseline (from Batch 4 completion):** `887 passed, 1 skipped`

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

### 4. Cross-Tenant IDOR Test Pattern
When writing security validation tests for Phase 7.0, follow this pattern:
```python
def test_cross_tenant_access_blocked(client_tenant_a, test_tenant_b_record):
    """Test that Tenant A receives a 404 when requesting Tenant B's record."""
    response = client_tenant_a.get(f"/api/v1/records/{test_tenant_b_record.id}")
    assert response.status_code == 404 # 404 is preferred over 403 to prevent ID enumeration
```

---

## ⚠️ CRITICAL WARNINGS & STOP CONDITIONS

**DO NOT PROCEED if any of the following occur. Stop and ask the user for guidance:**
1. **Circular Import Crash:** Adding the `Tenant` relationship breaks FastAPI startup. (Mitigation: reference `backend/app_model_imports.md` and use string references `foreign_key="tenant.id"`).
2. **Alembic Backfill Failure:** The `op.execute()` SQL fails to resolve `tenant_id` for existing `webhook_delivery_attempt` records. If any row has a `webhook_endpoint_id` that references a deleted endpoint, a NULL constraint violation will occur during the `nullable=False` alter. Stop and report.
3. **Test Regressions:** Refactoring `session.get()` causes unrelated tests to fail.

---

## 🏗️ The 5-Step Execution Loop

You must execute the following 5 steps sequentially. Do not skip steps.

### Step 1: ORM Model Updates
Consult `backend/db_models_map.md` to locate the exact file for each table in this batch. Update their SQLModel definitions.
```python
# REQUIRED FIELD DEFINITION (for both models):
tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
```
*Verify that the app still boots after adding these fields (no circular import loops).*

> ⚠️ **Reminder:** `WebhookDeliveryAttempt` uses an integer `id` (serial). Do not touch the `id` field definition. Only add `tenant_id`.

### Step 2: Manual Database Migration (Alembic)
❌ **DO NOT USE `--autogenerate`.** Autogenerate frequently pulls in unrelated schema diffs or "ghost" changes.

Instead, generate a **blank** migration:
```bash
alembic revision -m "phase_7_0_batch_5_tenant_stamping_communications_webhooks"
```

Then, **manually write the 3-part migration logic** inside `upgrade()`. The backfill SQL for each table in this batch is defined below:

```python
def upgrade():
    # ==============================================================
    # TABLE: conversation_message
    # Parent: conversation_session via session_id (1-hop)
    # conversation_session.tenant_id is NON-NULLABLE — safe to join.
    # ==============================================================
    op.add_column('conversation_message', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_conversation_message_tenant_id', 'conversation_message', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_conversation_message_tenant_id', 'conversation_message', ['tenant_id'])
    op.execute("""
        UPDATE conversation_message
        SET tenant_id = conversation_session.tenant_id
        FROM conversation_session
        WHERE conversation_message.session_id = conversation_session.id
    """)
    op.alter_column('conversation_message', 'tenant_id', nullable=False)

    # ==============================================================
    # TABLE: webhook_delivery_attempt
    # Parent: webhook_endpoint via webhook_endpoint_id (1-hop)
    # webhook_endpoint.tenant_id is NON-NULLABLE — safe to join.
    # ⚠️ DO NOT use webhook_event as the join source — its tenant_id is NULLABLE.
    # ⚠️ id is a serial INTEGER — do NOT alter or reference id as UUID.
    # ==============================================================
    op.add_column('webhook_delivery_attempt', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_webhook_delivery_attempt_tenant_id', 'webhook_delivery_attempt', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_webhook_delivery_attempt_tenant_id', 'webhook_delivery_attempt', ['tenant_id'])
    op.execute("""
        UPDATE webhook_delivery_attempt
        SET tenant_id = webhook_endpoint.tenant_id
        FROM webhook_endpoint
        WHERE webhook_delivery_attempt.webhook_endpoint_id = webhook_endpoint.id
    """)
    op.alter_column('webhook_delivery_attempt', 'tenant_id', nullable=False)


def downgrade():
    op.drop_index('ix_webhook_delivery_attempt_tenant_id', table_name='webhook_delivery_attempt')
    op.drop_constraint('fk_webhook_delivery_attempt_tenant_id', 'webhook_delivery_attempt', type_='foreignkey')
    op.drop_column('webhook_delivery_attempt', 'tenant_id')

    op.drop_index('ix_conversation_message_tenant_id', table_name='conversation_message')
    op.drop_constraint('fk_conversation_message_tenant_id', 'conversation_message', type_='foreignkey')
    op.drop_column('conversation_message', 'tenant_id')
```

### Step 3: Master Blueprint Sync
Update `pilot-db-schema-v2.6h.json` to include the new `tenant_id` columns, foreign keys, and indexes for the tables in this batch.
*Run `python schema_diff.py` to prove 0 discrepancies exist before moving to Step 4.*

### Step 4: API & Service Layer Refactoring
Scan `backend/api/routes/` and `backend/services/` for raw `session.get(Model, id)` or `db.get(Model, id)` calls involving this batch's models. Consult `backend/app_model_imports.md` if you need to add imports to these files.

❌ **DESTROY THIS PATTERN:**
`msg = session.get(ConversationMessage, message_id)`
`attempt = session.get(WebhookDeliveryAttempt, attempt_id)`

✅ **REPLACE WITH THIS PATTERN:**
`msg = session.exec(select(ConversationMessage).where(ConversationMessage.id == message_id, ConversationMessage.tenant_id == current_tenant.id)).first()`
`attempt = session.exec(select(WebhookDeliveryAttempt).where(WebhookDeliveryAttempt.id == attempt_id, WebhookDeliveryAttempt.tenant_id == current_tenant.id)).first()`

*Ensure all `POST`/creation logic for both models explicitly injects the `tenant_id` upon object creation.*

### Step 5: Security Validation & Testing
Ensure the existing test suite passes, then write explicit cross-tenant isolation tests for this batch's routes (using the IDOR Test Pattern from the Best Practices section). Create the new test file at: `backend/tests/test_phase7_batch5_tenant_isolation.py`

Suggested tests to cover:
- `test_conversation_message_has_tenant_id` — assert ORM field exists and is non-nullable
- `test_webhook_delivery_attempt_has_tenant_id` — assert ORM field exists and is non-nullable
- `test_cross_tenant_conversation_message_blocked` — Tenant A receives 404 for Tenant B's message ID
- `test_cross_tenant_webhook_delivery_attempt_blocked` — Tenant A receives 404 for Tenant B's attempt ID
- `test_conversation_message_creation_stamps_tenant_id` — POST to create a message auto-injects tenant_id
- `test_webhook_delivery_attempt_creation_stamps_tenant_id` — creation auto-injects tenant_id

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Run Full Test Suite
```bash
cd backend
source .venv/bin/activate

# Run unit tests (no integration)
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1

# Run all tests
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
```

### Step 2: Final Validation
If ANY tests fail, identify the failing tests, fix the logic (likely a missed `tenant_id` injection during object creation), and re-run until 100% pass rate is achieved.

---

## ✅ Definition of Done (Checklist)

- [ ] Captured pre-modification test baseline. **Baseline: 887 passed, 1 skipped**
- [ ] SQLModel updated with `tenant_id` (indexed, nullable=False, FK to tenant.id) for `ConversationMessage`.
- [ ] SQLModel updated with `tenant_id` (indexed, nullable=False, FK to tenant.id) for `WebhookDeliveryAttempt` (integer `id` left untouched).
- [ ] Blank Alembic migration created using `alembic revision -m "phase_7_0_batch_5_tenant_stamping_communications_webhooks"`.
- [ ] 3-Part Manual Migration coded (Add Nullable → Backfill Data → Set Not Null) for both tables.
- [ ] `conversation_message` backfill SQL verified: joins `conversation_session` on `session_id`.
- [ ] `webhook_delivery_attempt` backfill SQL verified: joins `webhook_endpoint` on `webhook_endpoint_id` (**NOT** `webhook_event`).
- [ ] Alembic migration applies successfully and `alembic downgrade -1` works cleanly.
- [ ] `pilot-db-schema-v2.6h.json` updated for both tables (columns, FKs, indexes).
- [ ] `python schema_diff.py` reports ZERO discrepancies.
- [ ] All `session.get()` calls for `ConversationMessage` and `WebhookDeliveryAttempt` refactored to explicitly filter by `tenant_id`.
- [ ] Cross-tenant isolation unit tests written in `tests/test_phase7_batch5_tenant_isolation.py` and passing.
- [ ] 100% of the test suite passes with zero regressions.
- [ ] `dev-docs/analysis/phase-7.0-db-schema-cleanup-plan.md` updated — mark Batch 5 as ✅ COMPLETE with migration filename and test file reference.
- [ ] Document updated with final test counts.
