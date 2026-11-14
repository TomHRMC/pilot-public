# Implementation Prompt: SD-BE-1 — Payment Refund Columns, Invoice Dunning Enhancement, Seed Data

**Mode**: Pilot Python Engineer  
**Batch**: SD-BE-1  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd-design-sprint-design.md` §SD-05, §SD-06, §SD-09  
**Estimated session**: 3–5 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: SD-FE-1 (React Engineer fixes `InvoicesPage.tsx` — runs after this batch closes and `pnpm sync-api-types` is confirmed)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 4**: All Alembic migrations must be **blank** (`alembic revision -m "name"` — never `--autogenerate`). Data changes use raw `op.execute()`. Schema column additions use `op.add_column()`.
- **Rule 4b (3-Part NOT NULL Pattern)**: `refunded_amount_cents` has `DEFAULT 0` so it is safe as NOT NULL. Use `op.add_column()` with `server_default='0'` to satisfy existing rows without a backfill step.
- **Rule 11**: If ANY test fails during your work — fix it before declaring the batch done. No "pre-existing failure" exception without Tom's written confirmation.
- **Rule — Seed script safety**: After adding any seed script data, run `pytest -m unit --tb=short -q | tail -10` to confirm zero new test failures. Seed data coexistence is a known source of breakage.
- **Rule — No `db.get()` on tenant-scoped models**: Always use `select()` with explicit `WHERE tenant_id = :tid`.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: confirm with Tom before proceeding. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm payment table current columns (verify no refunded_* cols exist yet)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment'
ORDER BY ordinal_position;

-- 2. Confirm invoice table current columns (verify no last_reminder_sent_at or reminder_count)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
ORDER BY ordinal_position;

-- 3. Confirm platform_setting_catalog current row count and confirm invoice_reminder keys don't exist
SELECT key, value_type, category FROM public.platform_setting_catalog
WHERE key LIKE '%reminder%' OR key LIKE '%invoice%'
ORDER BY key;

-- 4. Check current Alembic head
SELECT version_num FROM public.alembic_version;

-- 5. Verify discount_version schema before seeding
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'discount_version'
ORDER BY ordinal_position;

-- 6. Verify quote_template current 3 rows (Alembic-seeded)
SELECT id, name, tenant_id, created_at FROM public.quote_template ORDER BY created_at;

-- 7. Check supplier_item_price schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'supplier_item_price'
ORDER BY ordinal_position;
```

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE. If a query fails → STOP and ask Tom.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/billing.py              ← understand Payment model, StandardAuditMixin usage
backend/app/models/invoicing.py            ← understand Invoice model before adding columns  
backend/tasks/dunning.py                   ← read the FULL existing task before modifying
backend/migrations/scripts/seed_core.py   ← understand the existing quote_template section + SIMPLE/TENANT tables
backend/migrations/scripts/seed_test_tenant.py  ← understand labor_rate_version and markup patterns before adding discount_version
backend/migrations/scripts/seed_platform.py ← understand platform_setting patterns before adding new keys
backend/migrations/scripts/reset_dev_db.py  ← understand SCENARIOS dict and GROUP_D_TABLES before extending
backend/migrations/scripts/_db_utils.py    ← understand the session context manager pattern
backend/tests/README-adding-tests.md       ← Seed Data Coexistence Rules section (v1.3) — mandatory
```

Also grep for related patterns:
```bash
grep -rn "charge.refunded\|refund.created\|payment_intent.partially_refunded" backend/ --include="*.py" -l
grep -rn "dunning\|send_overdue" backend/ --include="*.py" -l
grep -rn "payment_status\|payment_method" backend/app/models/ --include="*.py"
```

---

## Background

This batch implements three design decisions from `batch-sd-design-sprint-design.md`:

- **SD-05**: Stripe refunds need to be tracked on the `payment` row — add `refunded_amount_cents` + `refunded_at` columns and update the Stripe webhook handler.
- **SD-06B**: The existing `dunning.py` task sends internal owner notifications only; it needs enhancement to also send customer-facing SMS reminders + track reminder state on `invoice`. Three new `platform_setting_catalog` keys control the schedule.
- **SD-09**: Add seed data for `discount_version` (Group C), `supplier`/`supplier_item`/`supplier_item_price` (new Group D script), and `quote_template` recovery in `seed_core.py` (Group A).

---

## Task 1 — SD-05: Add Refund Columns to `payment`

### 1a. Alembic migration

```bash
cd <repo>/backend
alembic revision -m "sd05_add_refund_columns_to_payment"
```

In the generated migration file:

```python
def upgrade() -> None:
    # refunded_amount_cents: NOT NULL with server_default='0' — safe for existing rows
    op.add_column(
        "payment",
        sa.Column(
            "refunded_amount_cents",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # refunded_at: nullable — NULL means no refund processed
    op.add_column(
        "payment",
        sa.Column("refunded_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment", "refunded_at")
    op.drop_column("payment", "refunded_amount_cents")
```

Run the full migration cycle:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current   # must show new head revision
```

### 1b. Update the `Payment` SQLModel

In `backend/app/models/billing.py` (or wherever `Payment` is defined — verify with `grep -rn "class Payment" backend/app/models/`):

Add after the existing `payment_method_id` / `status_id` fields:
```python
refunded_amount_cents: int = Field(default=0, description="Total refunded amount in cents (0 = no refund)")
refunded_at: datetime | None = Field(default=None, description="Timestamp of most recent refund event")
```

After the model change, regenerate:
```bash
python generate_db_model_map.py
grep "Payment" backend/db_models_map.md   # confirm refunded_amount_cents appears
```

### 1c. Update Stripe webhook handler

Locate the Stripe webhook handler:
```bash
grep -rn "charge.refunded\|webhook" backend/ --include="*.py" -l
```

In the handler that processes `charge.refunded` and `refund.created` events, add:

```python
# In the charge.refunded / refund.created event handler — adjust to match existing pattern
elif event_type in ("charge.refunded", "refund.created"):
    # Get the payment_intent ID from the Stripe event
    payment_intent_id = event.data.object.get("payment_intent")
    if not payment_intent_id:
        return {"status": "skipped", "reason": "no payment_intent on event"}

    # Find the payment row by Stripe payment intent ID — tenant-scoped
    payment = db.exec(
        select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
    ).first()

    if payment:
        refund_amount_cents = event.data.object.get("amount_refunded", 0)
        payment.refunded_amount_cents = refund_amount_cents
        payment.refunded_at = datetime.now(UTC)
        db.add(payment)
        db.commit()
        logger.info(f"Recorded refund: payment {payment.id}, refunded_amount_cents={refund_amount_cents}")
```

> **Note**: Read the existing webhook handler file fully before modifying — adjust the pattern to match whatever event dispatch pattern is already in use (e.g., `if/elif` on `event_type`, or a dict dispatch table).

### 1d. Intermediate test run
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
# Must match or exceed baseline. Fix any failures before proceeding.
```

---

## Task 2 — SD-06B: Enhance Invoice Dunning + New Invoice Columns

### 2a. Alembic migration — new invoice columns + platform settings

```bash
alembic revision -m "sd06_invoice_reminder_columns_and_platform_settings"
```

```python
def upgrade() -> None:
    # --- Invoice reminder tracking columns ---
    op.add_column(
        "invoice",
        sa.Column("last_reminder_sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "invoice",
        sa.Column(
            "reminder_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # --- New platform_setting_catalog keys for tenant-configurable reminder schedule ---
    # Use SET LOCAL session_replication_role = 'replica' to bypass FK triggers on data inserts
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO platform_setting_catalog (key, value_type, category, tenant_editable, description, default_value, created_at, updated_at)
        VALUES
            ('invoice_reminder_days_1', 'integer', 'billing', true, 'Days overdue before first invoice reminder fires', '1', NOW(), NOW()),
            ('invoice_reminder_days_2', 'integer', 'billing', true, 'Days overdue before second invoice reminder fires', '7', NOW(), NOW()),
            ('invoice_reminder_days_3', 'integer', 'billing', true, 'Days overdue before final invoice reminder fires', '14', NOW(), NOW())
        ON CONFLICT (key) DO NOTHING;
    """)
    # Insert null-tenant default platform_setting rows for each new key
    op.execute("""
        INSERT INTO platform_setting (catalog_key, tenant_id, value, created_at, updated_at)
        SELECT key, NULL, default_value, NOW(), NOW()
        FROM platform_setting_catalog
        WHERE key IN ('invoice_reminder_days_1', 'invoice_reminder_days_2', 'invoice_reminder_days_3')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        DELETE FROM platform_setting WHERE catalog_key IN (
            'invoice_reminder_days_1', 'invoice_reminder_days_2', 'invoice_reminder_days_3'
        ) AND tenant_id IS NULL;
    """)
    op.execute("""
        DELETE FROM platform_setting_catalog WHERE key IN (
            'invoice_reminder_days_1', 'invoice_reminder_days_2', 'invoice_reminder_days_3'
        );
    """)
    op.drop_column("invoice", "reminder_count")
    op.drop_column("invoice", "last_reminder_sent_at")
```

> **MCP pre-check**: Before writing the `platform_setting` insert, run:
> ```sql
> SELECT column_name FROM information_schema.columns
> WHERE table_schema = 'public' AND table_name = 'platform_setting'
> ORDER BY ordinal_position;
> ```
> Verify the exact column names in `platform_setting` (may be `catalog_key` FK or another name). Adjust the SQL if different.

Run full cycle after writing:
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

### 2b. Update `Invoice` SQLModel

Add after existing `invoice` fields:
```python
last_reminder_sent_at: datetime | None = Field(default=None)
reminder_count: int = Field(default=0)
```

Regenerate:
```bash
python generate_db_model_map.py
python schema_manager.py --help   # CRUD script — read available commands first, then use appropriate command
```

### 2c. Update `seed_core.py` — add 3 new `platform_setting_catalog` keys

Read `backend/migrations/scripts/seed_core.py` fully before editing. Find the `platform_setting_catalog` section and add the 3 new rows using `ON CONFLICT (key) DO NOTHING`. Also add corresponding null-tenant `platform_setting` default rows.

### 2d. Enhance `dunning.py`

Read `backend/tasks/dunning.py` fully before modifying.

The current task only sends `notification_outbox` rows to the **tenant owner**. Enhance it to:

1. **Throttle by `last_reminder_sent_at`**: Skip any invoice where `last_reminder_sent_at IS NOT NULL AND last_reminder_sent_at > NOW() - INTERVAL '1 day'`
2. **Respect the 3-threshold schedule**: Only fire when the invoice is at the 1d, 7d, or 14d overdue threshold (use `platform_setting_catalog` values — query via `select(PlatformSetting).where(PlatformSetting.catalog_key.in_(['invoice_reminder_days_1', ...]))`
3. **Send customer-facing SMS**: After the internal owner notification, also send a customer SMS via the `payment_reminder` `communication_template` code. Look up the customer's primary phone number. If no phone number → skip customer SMS, still send owner notification.
4. **Update `last_reminder_sent_at` and `reminder_count`**: After sending, increment `invoice.reminder_count` and set `invoice.last_reminder_sent_at = now`.
5. **Change Beat schedule**: Update the Celery Beat config (in `core/celery_app.py` or wherever beat schedules are defined) from every-60-minutes to once-daily at 09:00 UTC.

> **Two-layer Celery task pattern**: Business logic goes in `_send_overdue_invoice_reminders_impl(db)`. The `@celery_app.task` wrapper creates the session and calls `_impl`. Reference `backend/tasks/profitability_rollup.py` for this pattern.

### 2e. Add `GET /invoices?overdue=true` query parameter

Find the `GET /api/v1/invoices` route. Add an optional `overdue: bool = Query(default=False)` parameter. When `overdue=True`, filter results where:
```sql
due_at < NOW() AND status_code NOT IN ('paid', 'void', 'writeoff')
```

This uses the existing `invoice_status` join pattern. No new endpoint — just a new query param on the existing list endpoint.

After adding the param:
```bash
python export_openapi_json.py
grep -A 3 "overdue" backend/openapi_schema_map.md
# Confirm ?overdue appears on the invoices endpoint
```

### 2f. Intermediate test run
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 3 — SD-09: Seed Data for Empty Functional Tables

### 3a. Add `quote_template` to `seed_core.py`

Read `backend/migrations/scripts/seed_core.py` fully. Find the Group A section.

The 3 existing `quote_template` rows are Alembic-owned (confirmed: `created_at = 2026-05-01T11:10:45.578Z` matches migration `29384efbde55`). Their `tenant_id IS NULL` (system templates).

Before writing any insert, run MCP to get exact current row data:
```sql
SELECT id, name, style, category, is_active, is_system_template, current_version, tenant_id, created_at
FROM public.quote_template ORDER BY created_at;
```

Add a `seed_quote_templates()` function that uses `INSERT ... ON CONFLICT (id) DO NOTHING` with the exact UUIDs from the MCP query above. Add to `mode_seed()`, `mode_show()`, and `mode_inspect()`.

### 3b. Add `discount_version` to `seed_test_tenant.py`

Read `backend/migrations/scripts/seed_test_tenant.py` fully — especially the `labor_rate_version` and `tenant_markup_version` sections.

`discount_version` schema (confirmed via MCP):
- `id BIGINT` (AppendOnly PK — use `DEFAULT nextval(...)` or rely on serial; check the sequence name with MCP)
- `tenant_id UUID` (nullable — use test tenant UUID `00000000-0000-0000-0000-000000000001`)
- `code VARCHAR NOT NULL`
- `pct_off NUMERIC` (nullable) — only set if `amount_off_cents` is NULL
- `amount_off_cents INTEGER` (nullable) — only set if `pct_off` is NULL
- `valid_period TSTZRANGE NOT NULL`
- `recorded_at TIMESTAMPTZ NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`, `created_by UUID nullable`

**CHECK constraint**: exactly one of `pct_off` or `amount_off_cents` must be non-null.

**No GiST exclusion constraint** (confirmed via MCP `pg_constraint` query) — inserting multiple rows for the same tenant is safe.

Before writing, run:
```sql
SELECT column_name, column_default FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'discount_version'
ORDER BY ordinal_position;
```

Seed 2 rows:
1. Code `SUMMER_PROMO` — `pct_off=10`, `amount_off_cents=NULL`, `valid_period = tstzrange('2024-06-01', '2024-08-31')` (closed past range)
2. Code `NEW_CUSTOMER` — `pct_off=NULL`, `amount_off_cents=2500`, `valid_period = tstzrange('2026-01-01', NULL)` (open-ended)

Use `ON CONFLICT DO NOTHING` — key on `(tenant_id, code)` if a unique constraint exists, otherwise key on `code` + `tenant_id IS NOT DISTINCT FROM '00000000-0000-0000-0000-000000000001'`.

> **MCP check first**: Run `SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'public.discount_version'::regclass;` to find the exact unique constraint before writing.

Add to `mode_seed()`, `mode_show()`, and `mode_inspect()`.

### 3c. Create `seed_scenario_supplier_catalog.py`

Create a new Group D script at `backend/migrations/scripts/seed_scenario_supplier_catalog.py`.

**Before writing any INSERT**: verify exact schema for each table:
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name IN ('supplier', 'supplier_item', 'supplier_item_price')
ORDER BY table_name, ordinal_position;
```

**Pattern**: Follow `seed_scenario_dispatch.py` exactly — same `mode_seed()`, `mode_show()`, `mode_inspect()`, `--reset` flag pattern, and 3-second countdown on reset.

**What to seed**:

**`supplier`** (1 row):
- Name: `Wesco Distribution`
- `lifecycle_status_code`: `active` (confirm this is the correct FK lookup — run `SELECT code FROM public.supplier_lifecycle_status;`)
- Test tenant UUID: `00000000-0000-0000-0000-000000000001`
- `is_active=True`

**`supplier_item`** (5 rows — verify supplier_item FK column names from MCP before writing):
1. `12 AWG THHN Wire` — category `wire_cable`, uom `foot`
2. `1/2" EMT Conduit` — category `conduit_raceway`, uom `foot`
3. `Square D QO115 15A Breaker` — category `dist_equip`, uom `each`
4. `Standard Duplex Outlet` — category `wiring_devices`, uom `each`
5. `1/2" EMT Coupling` — category `fittings`, uom `each`

**`supplier_item_price`** (5 rows — one per item): Before writing, run MCP to get full column list for `supplier_item_price`. Verify if date-range `valid_period` or GiST constraints exist via `pg_constraint`. Seed with approximate market prices (adjust based on actual column names from MCP):
1. Wire 12 AWG: `unit_price_cents=89` (per foot)
2. EMT Conduit: `unit_price_cents=175` (per 10-foot stick — or per foot if column is per-unit; check MCP)
3. Breaker: `unit_price_cents=1250`
4. Outlet: `unit_price_cents=225`
5. Coupling: `unit_price_cents=85`

Register in `reset_dev_db.py`:
- Add `"supplier_catalog": "seed_scenario_supplier_catalog"` to `SCENARIOS` dict
- Add `"supplier"`, `"supplier_item"`, `"supplier_item_price"` to `GROUP_D_TABLES` deletion order (check FK dependencies — price before item before supplier)

### 3d. Run seed scripts to verify
```bash
cd <repo>/backend
source .venv/bin/activate
python migrations/scripts/seed_core.py --mode inspect | grep quote_template
python migrations/scripts/seed_test_tenant.py --mode inspect | grep discount
python migrations/scripts/seed_scenario_supplier_catalog.py --mode show
python migrations/scripts/seed_scenario_supplier_catalog.py  # run seed
python migrations/scripts/seed_scenario_supplier_catalog.py --mode inspect
```

### 3e. Intermediate test run
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
# Any new failures from seed coexistence must be fixed NOW
```

---

## Test Requirements

### SD-05 tests — domain `invoicing_billing/`

File: `backend/tests/domains/invoicing_billing/test_sd05_payment_refund.py`

```python
pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]
```

Tests to include:
1. `test_refunded_amount_cents_default_is_zero` — create a payment via `/test` endpoint; assert `refunded_amount_cents == 0`
2. `test_charge_refunded_webhook_writes_columns` — POST a synthetic `charge.refunded` event to the webhook endpoint; assert the payment row has updated `refunded_amount_cents` and `refunded_at IS NOT NULL`
3. `test_partial_refund_does_not_change_status` — after a partial refund webhook, assert `payment.status_code` is still `succeeded`

### SD-06B tests — domain `invoicing_billing/`

File: `backend/tests/domains/invoicing_billing/test_sd06_invoice_dunning.py`

```python
pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]
```

Tests to include:
1. `test_overdue_invoice_filter_param` — GET `/invoices?overdue=true`; assert only invoices where `due_at < now` and `status_code NOT IN ('paid','void','writeoff')` are returned. Use `second_tenant` to avoid seed data interference.
2. `test_dunning_skips_recently_reminded_invoice` — create an invoice with `last_reminder_sent_at = NOW() - 1 hour`; run `_send_overdue_invoice_reminders_impl(db)`; assert the invoice is not re-notified
3. `test_dunning_updates_reminder_count` — create an overdue invoice with no `last_reminder_sent_at`; run `_impl`; assert `reminder_count == 1` and `last_reminder_sent_at IS NOT NULL`

### SD-09 seed coexistence tests

After running seed scripts, run full unit suite and fix any failures:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Alembic Migration Standards

Per `pilot-python-engineer-methods.md` §13:

1. **Always use blank migrations** — never `alembic revision --autogenerate`
2. **Implement `downgrade()`** — must exactly reverse `upgrade()`
3. **Test the full cycle**: `upgrade head → downgrade -1 → upgrade head → alembic current`
4. **Use `ON CONFLICT DO NOTHING`** for all seed data INSERTs
5. **Use `SET LOCAL session_replication_role = 'replica';`** for data migrations that bypass FK triggers

---

## Schema JSON Sync

After all migrations run and tests pass:

```bash
cd <repo>/backend
python schema_manager.py --help   # CRUD script — read available commands first (set, delete, inspect, etc.)
# Then use the appropriate CRUD command for the new columns
```

---

## OpenAPI Regeneration

After adding `?overdue=true` to the invoices endpoint:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
grep -A 3 "overdue" backend/openapi_schema_map.md
```

---

## DB Model Map Regeneration

After any model change (`Payment`, `Invoice`):

```bash
cd <repo>/backend
python generate_db_model_map.py
grep "refunded_amount_cents\|last_reminder_sent_at" backend/db_models_map.md
```

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before Phase 2.

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/invoicing_billing/ -v 2>&1 | tail -20
grep -A 3 "overdue" backend/openapi_schema_map.md
python migrations/scripts/seed_core.py --mode inspect | grep quote_template
python migrations/scripts/seed_scenario_supplier_catalog.py --mode inspect

echo "=== SD-BE-1 FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.**

---

## Definition of Done

Update `dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch when each item is done:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — `payment` and `invoice` schemas verified, `quote_template` rows confirmed
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: Alembic migration `sd05_add_refund_columns_to_payment` — upgrade/downgrade verified
- [ ] **Task 1**: `Payment` model updated — `refunded_amount_cents`, `refunded_at` fields added
- [ ] **Task 1**: Stripe `charge.refunded` / `refund.created` webhook handler updated
- [ ] **Task 2**: Alembic migration `sd06_invoice_reminder_columns_and_platform_settings` — upgrade/downgrade verified
- [ ] **Task 2**: `Invoice` model updated — `last_reminder_sent_at`, `reminder_count` added
- [ ] **Task 2**: `seed_core.py` updated — 3 new `platform_setting_catalog` keys added
- [ ] **Task 2**: `dunning.py` enhanced — throttle logic, customer SMS, reminder_count tracking, daily Beat schedule
- [ ] **Task 2**: `GET /invoices?overdue=true` query param added to invoices endpoint
- [ ] **Task 3**: `seed_core.py` updated — `quote_template` 3 Alembic-owned rows added
- [ ] **Task 3**: `seed_test_tenant.py` updated — 2 `discount_version` rows added
- [ ] **Task 3**: `seed_scenario_supplier_catalog.py` created — 1 supplier + 5 items + 5 prices; registered in `reset_dev_db.py`
- [ ] `python generate_db_model_map.py` run — `db_models_map.md` updated
- [ ] `python schema_manager.py --help` run; then appropriate CRUD command used — `pilot-db-schema-v2.6h.json` updated
- [ ] `python export_openapi_json.py` run — `openapi.json` and `openapi_schema_map.md` updated; `?overdue` visible
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] Seed coexistence verified — zero new unit test failures after running seed scripts
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including integration tests
- [ ] Final test count (before → after) documented
- [ ] Handoff: run `python export_openapi_json.py`, commit, notify React Engineer that SD-FE-1 (InvoicesPage fix) is unblocked

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` §P1 Seed Data Batch using this format:

```markdown
### SD-BE-1 — Payment Refund Columns, Invoice Dunning Enhancement, Seed Data: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- [Brief description]

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/migrations/versions/[rev]-sd05_add_refund_columns_to_payment.py` | Created |
| ... | ... |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/invoicing_billing/test_sd05_payment_refund.py` | `domain_invoicing_billing` | N | ✅ |
```

---

## After This Task — Next Step

After `python export_openapi_json.py` is confirmed and this batch is committed:
1. Notify the React Engineer that **SD-FE-1** is unblocked — they need to fix `InvoicesPage.tsx` using the corrected `"issued"` status code and the new `?overdue=true` endpoint
2. **SD-BE-2** can run in parallel — it is independent of this batch
