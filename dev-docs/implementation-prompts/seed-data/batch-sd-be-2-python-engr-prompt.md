# Implementation Prompt: SD-BE-2 — Product Feature Revision + Email Template Copy Update

**Mode**: Pilot Python Engineer  
**Batch**: SD-BE-2  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md` §SD-07, §SD-08  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`) — seed scripts and data migrations; no new API endpoints  
**Frontend companion**: None (pricing page display changes are a separate Phase 1.5 frontend batch)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; Seed Data Coexistence Rules (v1.3) are especially relevant here

**Critical rules for this batch:**

- **Rule 4**: All Alembic migrations must be **blank** (`alembic revision -m "name"` — never `--autogenerate`). All data changes use raw `op.execute()`.
- **Rule 4b (data migrations)**: Use `SET LOCAL session_replication_role = 'replica';` at the start of any data migration that inserts into FK-constrained tables.
- **Rule 1**: Verify ALL column names and values with `postgres-local` MCP before writing any SQL. Never guess.
- **Rule 11**: Fix any test failure that appears during your work. No pre-existing exception without Tom's written confirmation.
- **Rule — No schema changes**: This batch is entirely data migration + seed script updates. No new DB columns, no new models, no new endpoints. If you find yourself adding a column → STOP and ask Tom.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. Fix any pre-existing failures or confirm with Tom before starting.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Current product_feature rows (confirm codes to add/remove)
SELECT id, code, name, description, created_at FROM public.product_feature ORDER BY code;

-- 2. Current product_plan rows (confirm plan codes)
SELECT code, name, display_name FROM public.product_plan ORDER BY code;

-- 3. Current product_plan_product_feature_version rows (confirm which will be replaced)
SELECT ppfv.id, pp.code AS plan_code, pf.code AS feature_code, ppfv.limit_value, ppfv.is_current
FROM public.product_plan_product_feature_version ppfv
JOIN public.product_plan pp ON ppfv.plan_id = pp.id
JOIN public.product_feature pf ON ppfv.feature_id = pf.id
ORDER BY pp.code, pf.code;

-- 4. Current email_template rows (confirm template_id values and categories)
SELECT template_id, display_name, category, subject_template, is_active FROM public.email_template ORDER BY template_id;

-- 5. Current notification_template rows (confirm all columns)
SELECT id, notification_type_code, channel, locale, subject, body, is_active FROM public.notification_template ORDER BY notification_type_code, channel;

-- 6. Check current Alembic head
SELECT version_num FROM public.alembic_version;

-- 7. Confirm product_plan_product_feature_version schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'product_plan_product_feature_version'
ORDER BY ordinal_position;
```

> **MCP Usage Rule**: Read-only only. If any query returns unexpected results → STOP and ask Tom.

---

## Pre-Work: Read These Source Files

```
backend/migrations/scripts/seed_platform.py    ← read FULLY — all PRODUCT_FEATURES, FEATURE_LIMITS, and notification_template sections
backend/app/models/subscription.py             ← understand ProductFeature model and feature_code references
backend/tasks/tier_limit_enforcer.py           ← understand how feature_code keys are used for enforcement
backend/migrations/scripts/data/email_templates/invoice_sent.json   ← current stub body to replace
backend/migrations/scripts/data/email_templates/quote_sent.json      ← current stub body
backend/migrations/scripts/data/email_templates/payment_received_customer.json  ← current stub
backend/migrations/scripts/data/email_templates/quote_expiring.json  ← current stub
backend/migrations/scripts/data/email_templates/payment_failed.json  ← current stub
```

Also run:
```bash
grep -rn "qb_sync_operations\|voice_ai_minutes\|data_exports" backend/ --include="*.py" -l
grep -rn "feature_code\|product_feature" backend/ --include="*.py" -l
```

---

## Background

This batch implements two approved design decisions:

- **SD-07**: The current `product_feature` set (`voice_ai_minutes`, `qb_sync_operations`, `data_exports`) is outdated. Tom approved a revised set: add `dispatch_slots` and `outbound_sms_segments`, remove `qb_sync_operations`, and rename `professional_plan` → `teams` in the DB. Limit values are also updated to match the locked GTM matrix.
- **SD-08**: All 5 customer-facing `email_template` bodies are confirmed stubs. All 9 `notification_template` rows are literal placeholder strings. The approved copy is in the design doc §SD-08 — apply it exactly.

**No new endpoints. No new models. No new DB columns.** This batch is entirely data migrations + seed script updates + JSON file updates.

---

## Task 1 — SD-07: Revise Product Feature Set + Plan Rename

### 1a. Read current state before writing anything

Run all MCP queries from Pre-Work above. Specifically:
- Get the exact `id` UUIDs for the existing 3 `product_feature` rows
- Get the exact `id` UUIDs for all `product_plan_product_feature_version` rows
- Get the exact `code` values for all `product_plan` rows

### 1b. Alembic data migration

```bash
cd <repo>/backend
alembic revision -m "sd07_revise_product_features_and_plan_rename"
```

The migration must:
1. Rename `professional_plan` → `teams` in `product_plan` (update `code` and `display_name`)
2. Remove all `product_plan_product_feature_version` rows for `qb_sync_operations`
3. Delete the `qb_sync_operations` row from `product_feature`
4. Insert `dispatch_slots` and `outbound_sms_segments` as new `product_feature` rows
5. Insert new `product_plan_product_feature_version` rows for all 3 plans × 4 features

```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Rename professional_plan → teams
    op.execute("""
        UPDATE product_plan
        SET code = 'teams', display_name = 'Teams', updated_at = NOW()
        WHERE code = 'professional_plan';
    """)

    # 2. Remove qb_sync_operations feature limit rows
    op.execute("""
        DELETE FROM product_plan_product_feature_version
        WHERE feature_id IN (
            SELECT id FROM product_feature WHERE code = 'qb_sync_operations'
        );
    """)

    # 3. Remove qb_sync_operations from product_feature
    op.execute("""
        DELETE FROM product_feature WHERE code = 'qb_sync_operations';
    """)

    # 4. Insert new product_feature rows
    op.execute("""
        INSERT INTO product_feature (id, code, name, description, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'dispatch_slots', 'Dispatch Slots', 'Maximum concurrent field technician dispatch slots', NOW(), NOW()),
            (gen_random_uuid(), 'outbound_sms_segments', 'Outbound SMS Segments', 'Outbound SMS segments per billing cycle', NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)

    # 5. Insert product_plan_product_feature_version rows for all plans × all features
    # Read the exact plan IDs and new feature IDs from the DB first
    # Limits per GTM matrix:
    #   voice_ai_minutes:      starter=60,  teams=240,  enterprise=1000
    #   dispatch_slots:        starter=5,   teams=25,   enterprise=75
    #   outbound_sms_segments: starter=100, teams=500,  enterprise=2500
    #   data_exports:          starter=0,   teams=-1,   enterprise=-1  (0=blocked, -1=unlimited)
    op.execute("""
        INSERT INTO product_plan_product_feature_version
            (id, plan_id, feature_id, limit_value, is_current, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            pp.id,
            pf.id,
            CASE
                WHEN pp.code = 'starter_plan'  AND pf.code = 'voice_ai_minutes'       THEN 60
                WHEN pp.code = 'teams'         AND pf.code = 'voice_ai_minutes'       THEN 240
                WHEN pp.code = 'enterprise_plan' AND pf.code = 'voice_ai_minutes'     THEN 1000
                WHEN pp.code = 'starter_plan'  AND pf.code = 'dispatch_slots'         THEN 5
                WHEN pp.code = 'teams'         AND pf.code = 'dispatch_slots'         THEN 25
                WHEN pp.code = 'enterprise_plan' AND pf.code = 'dispatch_slots'       THEN 75
                WHEN pp.code = 'starter_plan'  AND pf.code = 'outbound_sms_segments'  THEN 100
                WHEN pp.code = 'teams'         AND pf.code = 'outbound_sms_segments'  THEN 500
                WHEN pp.code = 'enterprise_plan' AND pf.code = 'outbound_sms_segments' THEN 2500
                WHEN pp.code = 'starter_plan'  AND pf.code = 'data_exports'           THEN 0
                WHEN pp.code = 'teams'         AND pf.code = 'data_exports'           THEN -1
                WHEN pp.code = 'enterprise_plan' AND pf.code = 'data_exports'         THEN -1
                ELSE 0
            END,
            true,
            NOW(),
            NOW()
        FROM product_plan pp
        CROSS JOIN product_feature pf
        WHERE pf.code IN ('voice_ai_minutes', 'dispatch_slots', 'outbound_sms_segments', 'data_exports')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Remove rows for new features
    op.execute("""
        DELETE FROM product_plan_product_feature_version
        WHERE feature_id IN (
            SELECT id FROM product_feature WHERE code IN ('dispatch_slots', 'outbound_sms_segments')
        );
    """)
    op.execute("""
        DELETE FROM product_feature WHERE code IN ('dispatch_slots', 'outbound_sms_segments');
    """)

    # Restore qb_sync_operations
    op.execute("""
        INSERT INTO product_feature (id, code, name, description, created_at, updated_at)
        VALUES (gen_random_uuid(), 'qb_sync_operations', 'QuickBooks Sync Operations', 'QuickBooks sync operations per billing cycle', NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)

    # Rename teams back to professional_plan
    op.execute("""
        UPDATE product_plan
        SET code = 'professional_plan', display_name = 'Professional', updated_at = NOW()
        WHERE code = 'teams';
    """)
```

> **IMPORTANT**: Before running this migration, verify the exact `product_plan` codes from MCP. The migration above uses `starter_plan` and `enterprise_plan` — confirm these match what's in the live DB. Adjust if different.

Run full cycle:
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

### 1c. Update `seed_platform.py`

Read `backend/migrations/scripts/seed_platform.py` fully before editing.

Update the `PRODUCT_FEATURES` constant:
```python
PRODUCT_FEATURES = [
    {"code": "voice_ai_minutes", "name": "Voice AI Minutes", "description": "Voice AI minutes per billing cycle"},
    {"code": "dispatch_slots", "name": "Dispatch Slots", "description": "Maximum concurrent field technician dispatch slots"},
    {"code": "outbound_sms_segments", "name": "Outbound SMS Segments", "description": "Outbound SMS segments per billing cycle"},
    {"code": "data_exports", "name": "Data Exports", "description": "Data export operations (0=blocked, -1=unlimited)"},
]
```

Update `FEATURE_LIMITS` constant (or equivalent — match the existing structure):
```python
FEATURE_LIMITS = {
    "starter_plan": {
        "voice_ai_minutes": 60,
        "dispatch_slots": 5,
        "outbound_sms_segments": 100,
        "data_exports": 0,
    },
    "teams": {
        "voice_ai_minutes": 240,
        "dispatch_slots": 25,
        "outbound_sms_segments": 500,
        "data_exports": -1,
    },
    "enterprise_plan": {
        "voice_ai_minutes": 1000,
        "dispatch_slots": 75,
        "outbound_sms_segments": 2500,
        "data_exports": -1,
    },
}
```

Update `mode_show()` and `mode_inspect()` to reflect the 4-feature set.

### 1d. Update `tier_limit_enforcer.py`

```bash
cat backend/tasks/tier_limit_enforcer.py   # read fully first
```

Update any hardcoded feature code references from `qb_sync_operations` to the new codes. Add handling for `dispatch_slots` and `outbound_sms_segments` feature checks if they follow the same enforcement pattern.

### 1e. Intermediate test run
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — SD-08: Update Email Template + Notification Template Copy

### 2a. Update 5 customer-facing email template JSON files

The full approved copy is in `batch-sd-design-sprint-design.md` §SD-08. Apply it exactly to the 5 JSON files in `backend/migrations/scripts/data/email_templates/`.

Read each current JSON file before overwriting it to ensure you use the correct JSON structure.

**Files to update** (the `variables` array changes are noted — update the JSONB array in each file):

**`invoice_sent.json`**:
- `subject_template`: `"Invoice from {{company_name}} — ${{invoice_total}} due {{due_date}}"`
- `body_html_template`: *(full HTML from design doc §SD-08 `invoice_sent` section)*
- `body_plain_template`: *(full plain text from design doc §SD-08)*
- `variables`: `["customer_name", "company_name", "invoice_total", "invoice_url", "due_date", "company_domain"]`

**`quote_sent.json`**:
- `subject_template`: `"Your quote from {{company_name}} — ${{quote_total}}"`
- `body_html_template`: *(full HTML from design doc §SD-08)*
- `body_plain_template`: *(full plain text from design doc §SD-08)*
- `variables`: `["customer_name", "company_name", "quote_total", "quote_url"]` *(unchanged)*

**`payment_received_customer.json`**:
- `subject_template`: `"Payment confirmed — ${{amount}} received by {{company_name}}"`
- `body_html_template`: *(full HTML from design doc §SD-08)*
- `body_plain_template`: *(full plain text from design doc §SD-08)*
- `variables`: `["customer_name", "company_name", "amount", "payment_date", "company_domain"]`

**`quote_expiring.json`**:
- `subject_template`: `"Your quote from {{company_name}} expires {{expires_at}}"`
- `body_html_template`: *(full HTML from design doc §SD-08)*
- `body_plain_template`: *(full plain text from design doc §SD-08)*
- `variables`: `["customer_name", "quote_url", "expires_at"]` *(unchanged)*

**`payment_failed.json`**:
- `subject_template`: `"Action needed — payment issue on your invoice from {{company_name}}"`
- `body_html_template`: *(full HTML from design doc §SD-08)*
- `body_plain_template`: *(full plain text from design doc §SD-08)*
- `variables`: `["customer_name", "invoice_url", "company_name", "company_domain"]`

> **Important**: The `seed_core.py` email template loader reads these JSON files at runtime and upserts them. After updating the JSON files, the next `seed_core.py` run will propagate the new copy. However, the production DB also has these templates (they were seeded by Alembic migration) — so also create a data migration (see 2b).

### 2b. Alembic data migration to update email template copy in existing DBs

```bash
alembic revision -m "sd08_update_email_template_copy"
```

```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Update each customer-facing template with approved copy
    # Use the EXACT same HTML/plain text as in the JSON files
    # Use parameterized-style with text() for safety with special characters

    op.execute("""
        UPDATE email_template SET
            subject_template = 'Invoice from {{company_name}} — ${{invoice_total}} due {{due_date}}',
            body_html_template = '<p>Hi {{customer_name}},</p>...',
            body_plain_template = 'Hi {{customer_name}},\n\nYour invoice from {{company_name}}...',
            variables = '["customer_name","company_name","invoice_total","invoice_url","due_date","company_domain"]'::jsonb,
            updated_at = NOW()
        WHERE template_id = 'invoice_sent';
    """)
    -- [Repeat for all 5 customer-facing templates]
    -- [Keep internal template copy unchanged]


def downgrade() -> None:
    # Restore original stub copy for each template
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        UPDATE email_template SET
            subject_template = 'Invoice from {{company_name}}',
            body_html_template = '<p>Your invoice is ready.</p>',
            body_plain_template = 'Your invoice is ready.',
            variables = '["customer_name","company_name","invoice_total","invoice_url"]'::jsonb,
            updated_at = NOW()
        WHERE template_id = 'invoice_sent';
    """)
    -- [Restore all 5]
```

> **Note on special characters in SQL strings**: Use `$$dollar-quoting$$` or escape single quotes as `''` for any apostrophes in the template copy. Python raw strings with `r"""..."""` help.

Run full cycle:
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

### 2c. Update `notification_template` rows in `seed_platform.py`

Read `backend/migrations/scripts/seed_platform.py` fully — find the `notification_template` seeding section.

Update the `body` values for all 9 rows using the draft copy from design doc §SD-08 "Notification Template Draft Copy" table:

| notification_type_code | channel | New body |
|:---|:---|:---|
| `customer_communication_sent` | email | `"A customer communication was sent to {{customer_name}} via {{channel}}."` |
| `customer_communication_sent` | in_app | `"Message sent to {{customer_name}}."` |
| `customer_communication_sent` | push | `"Message sent to {{customer_name}}."` |
| `dunning_reminder` | email | `"Invoice {{invoice_number}} for {{customer_name}} is {{days_overdue}} days overdue. Balance due: ${{amount_due}}. Review and follow up in Pilot."` |
| `dunning_reminder` | in_app | `"Invoice {{invoice_number}} is {{days_overdue}} days overdue — ${{amount_due}} outstanding."` |
| `dunning_reminder` | push | `"Overdue invoice: {{invoice_number}} — ${{amount_due}} outstanding."` |
| `quote_accepted` | email | `"{{customer_name}} accepted your quote. Log in to Pilot to create a job and schedule the work."` |
| `quote_accepted` | in_app | `"{{customer_name}} accepted your quote."` |
| `quote_accepted` | push | `"New quote acceptance from {{customer_name}}."` |

Also create an Alembic data migration to update these rows in existing DBs:
```bash
alembic revision -m "sd08_update_notification_template_copy"
```

### 2d. Intermediate test run
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
# Confirm no template-code-keyed tests broke
```

Also check for tests that assert on specific template body strings:
```bash
grep -rn "placeholder\|This is a placeholder" backend/tests/ --include="*.py"
# Any test asserting on the old placeholder text must be updated
```

---

## Test Requirements

This batch is primarily data migrations + seed script updates. Direct unit test additions are minimal, but:

### SD-07 verification tests — domain `subscriptions_usage/`

File: `backend/tests/domains/subscriptions_usage/test_sd07_feature_revision.py`

```python
pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]
```

Tests:
1. `test_dispatch_slots_feature_exists` — query `product_feature` and assert `dispatch_slots` row exists
2. `test_qb_sync_operations_removed` — assert `qb_sync_operations` row does NOT exist in `product_feature`
3. `test_teams_plan_exists` — assert `product_plan` has a row with `code='teams'`
4. `test_starter_dispatch_slots_limit_is_5` — assert `product_plan_product_feature_version` has `limit_value=5` for `starter_plan × dispatch_slots`

Note: Use `@pytest.mark.skip_mock_entitlement_allowed` on any test that exercises actual entitlement checking behavior.

### SD-08 template content sanity tests — domain `notifications_comms/`

File: `backend/tests/domains/notifications_comms/test_sd08_template_copy.py`

```python
pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]
```

Tests:
1. `test_invoice_sent_template_not_stub` — query `email_template` WHERE `template_id='invoice_sent'`; assert `body_html_template` does NOT contain `"Your invoice is ready."` (the old stub)
2. `test_dunning_reminder_notification_not_stub` — query `notification_template` WHERE `notification_type_code='dunning_reminder'`; assert `body` does NOT contain `"This is a placeholder"`
3. `test_customer_facing_templates_have_variables` — assert each of the 5 customer-facing `email_template` rows has a non-empty `variables` JSONB array

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/subscriptions_usage/ -v 2>&1 | tail -20
python -m pytest tests/domains/notifications_comms/ -v 2>&1 | tail -20
python migrations/scripts/seed_platform.py --mode inspect | grep -A 5 "notification_template"

echo "=== SD-BE-2 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

Update `dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch when each item is done:

- [ ] Pre-modification regression baseline captured using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting
- [ ] All MCP pre-work queries run — `product_feature`, `product_plan`, `email_template`, `notification_template` verified
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: Alembic migration `sd07_revise_product_features_and_plan_rename` — upgrade/downgrade verified
- [ ] **Task 1**: `professional_plan` renamed to `teams` in `product_plan`
- [ ] **Task 1**: `qb_sync_operations` removed from `product_feature` + all its `product_plan_product_feature_version` rows
- [ ] **Task 1**: `dispatch_slots` and `outbound_sms_segments` added to `product_feature`
- [ ] **Task 1**: All 3 plans × 4 features = 12 `product_plan_product_feature_version` rows inserted with correct limits
- [ ] **Task 1**: `seed_platform.py` `PRODUCT_FEATURES` and `FEATURE_LIMITS` updated
- [ ] **Task 1**: `tier_limit_enforcer.py` updated — no references to `qb_sync_operations`
- [ ] **Task 2**: 5 customer-facing email template JSON files updated with full approved copy
- [ ] **Task 2**: Alembic migration `sd08_update_email_template_copy` — upgrade/downgrade verified
- [ ] **Task 2**: Alembic migration `sd08_update_notification_template_copy` — upgrade/downgrade verified
- [ ] **Task 2**: `seed_platform.py` notification_template section updated with approved body copy
- [ ] No test asserts on old stub copy text (`"This is a placeholder"`, `"Your invoice is ready."`)
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch:

```markdown
### SD-BE-2 — Product Feature Revision + Email Template Copy Update: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- [Brief description]

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/migrations/versions/[rev]-sd07_revise_product_features_and_plan_rename.py` | Created |
| `backend/migrations/scripts/seed_platform.py` | Updated — PRODUCT_FEATURES, FEATURE_LIMITS, notification_template copy |
| `backend/migrations/scripts/data/email_templates/invoice_sent.json` | Updated — full approved copy |
| ... | ... |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/subscriptions_usage/test_sd07_feature_revision.py` | `domain_subscriptions_usage` | N | ✅ |
| `tests/domains/notifications_comms/test_sd08_template_copy.py` | `domain_notifications_comms` | N | ✅ |
```

---

## After This Task — No Downstream Dependency

SD-BE-2 is independent. No React Engineer work depends on this batch. The pricing page display updates (reflecting the revised feature set) are a separate Phase 1.5 frontend batch.
