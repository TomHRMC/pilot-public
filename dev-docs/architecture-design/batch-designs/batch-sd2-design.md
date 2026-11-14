# Batch SD-2 Design — Seed Data & Lookup Table Cleanup

**Mode**: Pilot Python Engineer  
**Batch**: SD-2  
**Plan link**: `dev-docs/analysis/pilot-launch-plan.md`  
**Design doc**: this file  
**Estimate**: 3–4 hours  
**Platform**: Backend only  
**Frontend companion**: None

---

## A. Input Read Summary

| Input | What was verified |
|:---|:---|
| MCP: `payment_status` live rows | 4 rows: canceled, failed, pending, succeeded — no `refunded` |
| MCP: `payment` columns | Has `refunded_amount_cents` (NOT NULL, int) + `refunded_at` (nullable timestamptz) from SD-05 — these are being removed |
| MCP: `quote_status` live rows | 9 rows — no `void` |
| MCP: `invoice_status` live rows | 5 rows — no `partial` |
| MCP: `qco_line_type` live rows | 4 rows: discount, labor, material, misc — no `note` |
| MCP: `currency` live rows | 4 rows: CAD, EUR, GBP, USD — all `is_active=True` |
| MCP: `notification_type` live rows | 3 rows: customer_communication_sent, dunning_reminder, quote_accepted |
| MCP: `notification_type` schema | columns: code, tenant_id (nullable), audience, name, description, is_active |
| MCP: `qco_line_type` schema | columns: id, tenant_id (nullable), code, name, is_default, is_active, qb_item_name_hint |
| Code audit: services using unseed notification_type codes | `api/routes/scheduling.py`: job_assigned, schedule_changed; `services/quickbooks_sync.py`: qb_sync_conflict; `tasks/auto_expire_qb_conflicts.py`: qb_conflict_pre_warning; `services/gps_variance_service.py`: gps_variance_alert (inline fallback); `tasks/check_system_template_updates.py`: system_template_updated (inline fallback) |
| Code audit: SD-05 refund columns | `refunded_amount_cents`, `refunded_at` in `payment` table; `_handle_refund_event()` in `stripe_subscriptions.py` |
| `seed_core.py` `PRODUCT_FEATURE_ROWS` | data_exports row present — needs removal from script + DB |
| `seed_platform.py` `PLAN_FEATURE_LIMITS` | No `data_exports` key in any plan — already removed from ppfv. Only seed_core.py has the orphaned row. |

---

## B. Migration Plan

### Migrations required (in execution order)

| # | Migration name | Type | Description |
|:---|:---|:---|:---|
| 1 | `sd2_deactivate_currencies` | data | UPDATE currency SET is_active=False WHERE code IN ('CAD','EUR','GBP') |
| 2 | `sd2_add_quote_status_void` | data | INSERT quote_status code='void', is_terminal=True |
| 3 | `sd2_add_invoice_status_partial` | data | INSERT invoice_status code='partial', is_terminal=False |
| 4 | `sd2_add_payment_status_refunded` | data | INSERT payment_status code='refunded', is_terminal=True |
| 5 | `sd2_refund_model_swap` | schema + data | DROP payment.refunded_amount_cents + refunded_at; no data to migrate (no live refunds) |
| 6 | `sd2_add_qco_line_type_note` | data | INSERT qco_line_type code='note', name='Note', qb_item_name_hint=NULL |
| 7 | `sd2_add_notification_types` | data | INSERT 6 missing notification_type rows |
| 8 | `sd2_remove_data_exports_feature` | data | DELETE FROM product_feature WHERE code='data_exports' |

### Pre-migration MCP verification queries

Run before writing any migration SQL:

```sql
-- Verify payment columns to be dropped still exist
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment'
  AND column_name IN ('refunded_amount_cents', 'refunded_at');

-- Verify no live refund data to migrate (expect 0 rows)
SELECT COUNT(*) FROM public.payment WHERE refunded_amount_cents > 0;

-- Verify data_exports row exists before deleting
SELECT code, name FROM public.product_feature WHERE code = 'data_exports';

-- Verify qco_line_type doesn't already have 'note'
SELECT 1 FROM public.qco_line_type WHERE code = 'note' AND tenant_id IS NULL;

-- Verify notification_type schema before INSERT
SELECT column_name, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_type'
ORDER BY ordinal_position;
```

### 3-part NOT NULL pattern for new rows

All new lookup rows must use `ON CONFLICT DO NOTHING` for idempotency. All tables use `StandardAuditMixin` — `created_at` and `updated_at` are NOT NULL with no server default, so every INSERT must include `NOW(), NOW()`.

---

## C. Execution Order

| Step | File | Action |
|:---|:---|:---|
| 1 | Establish baseline | `pytest -m unit --tb=no -q \| tail -5` |
| 2 | MCP pre-work queries | Run all 5 queries above |
| 3 | Write + run migration 1 | Deactivate CAD/EUR/GBP |
| 4 | Write + run migration 2 | Add quote_status `void` |
| 5 | Write + run migration 3 | Add invoice_status `partial` |
| 6 | Write + run migration 4 | Add payment_status `refunded` |
| 7 | Write + run migration 5 | Drop refund columns from `payment` |
| 8 | Update `Payment` SQLModel | Remove `refunded_amount_cents` + `refunded_at` fields |
| 9 | Update `stripe_subscriptions.py` | Rewrite `_handle_refund_event()` to create negative-amount payment row |
| 10 | Write + run migration 6 | Add `qco_line_type` `note` |
| 11 | Write + run migration 7 | Add 6 `notification_type` rows |
| 12 | Remove service fallbacks | 4 services / tasks — replace get-or-create with hard lookup |
| 13 | Write + run migration 8 | Delete `product_feature` `data_exports` |
| 14 | Update `seed_core.py` | Reflect all 8 changes in seed script |
| 15 | Fix test inconsistency | `test_a41_photo_upload_pipeline.py` |
| 16 | Phase 1 test gate | `pytest -m unit --tb=short -q` |
| 17 | Phase 2 test gate | Full canonical suite |

---

## D. Data Changes (no new API endpoints)

This batch has no new API endpoints. All changes are data migrations and service-layer code fixes.

### D-1. `currency` — deactivate non-USD

```sql
UPDATE public.currency
SET is_active = False, updated_at = NOW()
WHERE code IN ('CAD', 'EUR', 'GBP');
```

**`seed_core.py` update**: Change `is_active: True` → `is_active: False` for CAD, EUR, GBP in `SIMPLE_CODE_TABLES["currency"]["rows"]`.

---

### D-2. `quote_status` — add `void`

New row: a quote that was created but never sent and is being cancelled. Terminal state.

```sql
INSERT INTO public.quote_status
(code, name, is_default, is_terminal, is_active, tenant_id, created_at, updated_at)
VALUES ('void', 'Void', False, True, True, NULL, NOW(), NOW())
ON CONFLICT DO NOTHING;
```

**`seed_core.py` update**: Add `void` row to `TENANT_NULLABLE_CODE_TABLES["quote_status"]["rows"]`.

**UI note for React Engineer** (follow-on batch): The quote actions menu should offer "Void Quote" for quotes in `draft`, `pending`, or `pending_approval` states.

---

### D-3. `invoice_status` — add `partial`

New row: invoice has received at least one payment but the full balance is not yet settled. Not terminal — still open for collection.

```sql
INSERT INTO public.invoice_status
(code, name, is_default, is_terminal, is_active, tenant_id, created_at, updated_at)
VALUES ('partial', 'Partially Paid', False, False, True, NULL, NOW(), NOW())
ON CONFLICT DO NOTHING;
```

**`seed_core.py` update**: Add `partial` row to `TENANT_NULLABLE_CODE_TABLES["invoice_status"]["rows"]`.

**Application logic update** (`services/stripe_payment_intents.py`): After any payment is posted, the system must calculate remaining balance and transition invoice status:
- `remaining = invoice.total_cents - SUM(payment.amount_cents WHERE status_code='succeeded' AND is_active=True)`
- If `remaining > 0` AND `remaining < invoice.total_cents` → set `invoice.status_code = 'partial'`
- If `remaining == 0` → set `invoice.status_code = 'paid'`

This logic already exists in `stripe_payment_intents.py` for the `paid` transition — extend it to also handle `partial`.

---

### D-4. `payment_status` — add `refunded`

New row: payment was succeeded and a full or partial refund was subsequently processed. Terminal state.

```sql
INSERT INTO public.payment_status
(code, name, is_default, is_terminal, is_active, tenant_id, created_at, updated_at)
VALUES ('refunded', 'Refunded', False, True, True, NULL, NOW(), NOW())
ON CONFLICT DO NOTHING;
```

**`seed_core.py` update**: Add `refunded` row to `TENANT_NULLABLE_CODE_TABLES["payment_status"]["rows"]`.

---

### D-5. Refund model: switch from columns to negative-amount payment row

**Current model (SD-05)**: Refunds are tracked as metadata columns (`refunded_amount_cents`, `refunded_at`) on the original `payment` row.

**New model**: A refund creates a **new `payment` row** with `amount_cents = -(refund_amount)` and `status_code = 'refunded'`. The original payment row stays as `succeeded`. Net revenue = `SUM(amount_cents)` across all payment rows for an invoice.

**Advantages**: Clean accounting ledger — sum of all rows = net received. No derived-state columns needed.

#### Migration: Drop refund columns from `payment`

```sql
-- Pre-check: confirm no live refund data
SELECT COUNT(*) FROM public.payment WHERE refunded_amount_cents > 0;
-- Expected: 0 (no production data; these columns were added in SD-05 recently)

ALTER TABLE public.payment DROP COLUMN IF EXISTS refunded_amount_cents;
ALTER TABLE public.payment DROP COLUMN IF EXISTS refunded_at;
```

#### `Payment` SQLModel update (`app/models/billing.py`)

Remove the two fields:
```python
# DELETE these lines:
refunded_amount_cents: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
refunded_at: AwareDatetime | None = Field(default=None)
```

Run `python generate_db_model_map.py` after model change.

#### `stripe_subscriptions.py` — `_handle_refund_event()` rewrite

Replace the current logic that updates the existing payment row with:

```python
def _handle_refund_event(db: Session, event_data: dict) -> None:
    """
    Create a negative-amount payment row for a Stripe refund.
    Fires on charge.refunded and refund.created events.
    The original succeeded payment row is NOT modified.
    """
    charge = event_data.get("object", {})
    amount_refunded = charge.get("amount_refunded", 0)
    stripe_pi_id = charge.get("payment_intent")

    if not stripe_pi_id or not amount_refunded:
        return

    # Find the original payment row
    original = db.exec(
        select(Payment).where(Payment.stripe_payment_intent_id == stripe_pi_id)
    ).first()
    if not original:
        logger.warning(f"_handle_refund_event: no payment found for pi={stripe_pi_id}")
        return

    # Look up 'refunded' status
    refunded_status = db.exec(
        select(PaymentStatus).where(PaymentStatus.code == "refunded", PaymentStatus.tenant_id == None)
    ).first()
    if not refunded_status:
        logger.error("_handle_refund_event: 'refunded' payment_status not seeded")
        return

    # Create the negative-amount refund row
    refund_row = Payment(
        tenant_id=original.tenant_id,
        invoice_id=original.invoice_id,
        amount_cents=-amount_refunded,
        payment_method_id=original.payment_method_id,
        status_id=refunded_status.id,
        paid_at=datetime.now(UTC),
        psp_provider=original.psp_provider,
        psp_payment_id=charge.get("id"),  # Stripe charge ID
        paid_via="stripe",
        is_active=True,
    )
    db.add(refund_row)
    db.commit()
```

---

### D-6. `qco_line_type` — add `note`

New row: display-only text block on a quote or change order. No price, no QB mapping. Allows the owner to insert section headers, terms notes, or clarifying text between line items.

```sql
INSERT INTO public.qco_line_type
(code, name, is_default, is_active, qb_item_name_hint, tenant_id, created_at, updated_at)
VALUES ('note', 'Note', False, True, NULL, NULL, NOW(), NOW())
ON CONFLICT DO NOTHING;
```

**`seed_core.py` update**: Add `note` row to `TENANT_NULLABLE_CODE_TABLES["qco_line_type"]["rows"]`. Set `qb_item_name_hint: None`.

---

### D-7. `notification_type` — add 6 missing rows

Six notification type codes are used in production service code but not formally seeded. Services currently use a get-or-create fallback that silently creates malformed rows on first run. This batch seeds them properly and removes the fallback.

| Code | Name | Audience | Used in |
|:---|:---|:---|:---|
| `job_assigned` | Job Assigned | tenant | `api/routes/scheduling.py` |
| `schedule_changed` | Schedule Changed | tenant | `api/routes/scheduling.py` |
| `qb_sync_conflict` | QB Sync Conflict | tenant | `services/quickbooks_sync.py` |
| `qb_conflict_pre_warning` | QB Conflict Pre-Warning | tenant | `tasks/auto_expire_qb_conflicts.py` |
| `gps_variance_alert` | GPS Variance Alert | tenant | `services/gps_variance_service.py` |
| `system_template_updated` | System Template Updated | tenant | `tasks/check_system_template_updates.py` |

```sql
INSERT INTO public.notification_type
(code, tenant_id, audience, name, description, is_active, created_at, updated_at)
VALUES
  ('job_assigned', NULL, 'tenant', 'Job Assigned', 'Fired when a technician is assigned to a job', True, NOW(), NOW()),
  ('schedule_changed', NULL, 'tenant', 'Schedule Changed', 'Fired when a job schedule is updated', True, NOW(), NOW()),
  ('qb_sync_conflict', NULL, 'tenant', 'QB Sync Conflict', 'Fired when a QuickBooks sync conflict is detected', True, NOW(), NOW()),
  ('qb_conflict_pre_warning', NULL, 'tenant', 'QB Conflict Pre-Warning', 'Fired before a QB conflict auto-expires', True, NOW(), NOW()),
  ('gps_variance_alert', NULL, 'tenant', 'GPS Variance Alert', 'Fired when a tech clock-in GPS is far from the job site', True, NOW(), NOW()),
  ('system_template_updated', NULL, 'tenant', 'System Template Updated', 'Fired when a system communication template is updated', True, NOW(), NOW())
ON CONFLICT DO NOTHING;
```

**`seed_core.py` update**: Add all 6 rows to `TENANT_NULLABLE_CODE_TABLES["notification_type"]["rows"]`.

#### Service fallback removal

Replace get-or-create patterns in the following files with a hard lookup:

**Pattern to replace**:
```python
notification_event = db.exec(select(NotificationEvent).where(...code == "xyz")).first()
if not notification_event:
    notification_event = NotificationEvent(code="xyz", ...)  # ← GET-OR-CREATE FALLBACK
    db.add(notification_event)
    db.flush()
```

**Pattern to use instead**:
```python
notification_type = db.exec(
    select(NotificationType).where(NotificationType.code == "xyz", NotificationType.tenant_id == None)
).first()
if not notification_type:
    logger.error("notification_type 'xyz' not seeded — run seed_core.py")
    return  # Graceful skip — not a hard error for background tasks
```

Apply to:
- `services/gps_variance_service.py` — `_enqueue_gps_variance_notification()` function
- `tasks/check_system_template_updates.py` — `check_system_template_updates()` function
- `services/quickbooks_sync.py` — QB conflict notification path
- `tasks/auto_expire_qb_conflicts.py` — pre-warning notification path

---

### D-8. `product_feature` — remove `data_exports`

Data exports are not metered for billing. The `data_exports` row in `product_feature` is orphaned — it was removed from `product_plan_product_feature_version` in SD-07 (MKT-B11) but the feature definition row was never deleted from `product_feature`.

```sql
-- Verify no ppfv rows reference data_exports (expect 0)
SELECT COUNT(*) FROM public.product_plan_product_feature_version WHERE product_feature_code = 'data_exports';

-- Delete the orphaned row
DELETE FROM public.product_feature WHERE code = 'data_exports';
```

**`seed_core.py` update**: Remove `data_exports` dict from `PRODUCT_FEATURE_ROWS`. After removal, `PRODUCT_FEATURE_ROWS` will have 3 rows: `dispatch_slots`, `outbound_sms_segments`, `voice_ai_minutes`.

---

## E. Pattern Reuse Decisions

| Pattern | Applied? | Notes |
|:---|:---|:---|
| `ON CONFLICT DO NOTHING` idempotency | Yes | All 6 data migrations use it |
| `StandardAuditMixin` explicit timestamps | Yes | All INSERTs include `created_at=NOW(), updated_at=NOW()` |
| Tenant-scoped lookup with `tenant_id IS NULL` | Yes | All global lookup rows use `tenant_id IS NULL` filter |
| Hard lookup + graceful return for background tasks | Yes | Services replaced with `return` on missing type (not hard crash) |

---

## F. Shared Module Interfaces

### `app/models/billing.py` — `Payment` model

Remove fields:
```python
# Remove both of these:
refunded_amount_cents: int = ...
refunded_at: AwareDatetime | None = ...
```

After removal, run `python generate_db_model_map.py`.

### `services/stripe_subscriptions.py` — `_handle_refund_event()`

Full rewrite per §D-5 above. No signature change — still called from the Stripe webhook dispatcher on `charge.refunded` and `refund.created`.

### `seed_core.py` — 6 data changes

After completing all migrations, update `seed_core.py` to match:

| Change | Location in script |
|:---|:---|
| CAD/EUR/GBP `is_active: False` | `SIMPLE_CODE_TABLES["currency"]["rows"]` |
| Add `void` to `quote_status` | `TENANT_NULLABLE_CODE_TABLES["quote_status"]["rows"]` |
| Add `partial` to `invoice_status` | `TENANT_NULLABLE_CODE_TABLES["invoice_status"]["rows"]` |
| Add `refunded` to `payment_status` | `TENANT_NULLABLE_CODE_TABLES["payment_status"]["rows"]` |
| Add `note` to `qco_line_type` | `TENANT_NULLABLE_CODE_TABLES["qco_line_type"]["rows"]` |
| Add 6 rows to `notification_type` | `TENANT_NULLABLE_CODE_TABLES["notification_type"]["rows"]` |
| Remove `data_exports` | `PRODUCT_FEATURE_ROWS` — remove the dict entirely |

---

## G. Open Questions Resolved

| Question | Resolution |
|:---|:---|
| Refund model: columns vs. negative row | **Negative-amount payment row** — approved by Tom 2026-07-13 |
| `invoice_status partial` — is it terminal? | **No** — invoice is still open and collectible |
| `quote_status void` — is it terminal? | **Yes** — a voided quote cannot be recovered |
| `payment_status refunded` — is it terminal? | **Yes** — a refund is a final event |
| Service fallbacks on missing notification_type | **Graceful return** for background tasks (not hard crash) — avoids task failure on seeding gap |
| `data_exports` in ppfv — any rows left? | **Confirmed 0** via MCP. Safe to delete the feature definition row. |
| `tax_rate_version` tenant_id scoping | **Deferred** — separate design task (larger schema + service change) |
| `platform_setting_catalog` key audit | **Deferred** — separate verification task |
| `sync_conflict_classification_matrix` audit | **Deferred** — separate verification task |

---

## Product Notes (Non-Implementation)

### Phase 2 Gap: Per-customer communication template preferences

**Current state**: Customer opt-out of SMS is all-or-nothing at the carrier level (`customer.sms_opted_out`). There is no per-template opt-in/opt-out — a customer cannot say "send me `job_complete` but not `invoice_sent`."

**Phase 2 requirement**: A customer preference layer per `customer_comm_template_type` code, allowing granular opt-in/opt-out per message type. This requires a `customer_comm_preference` table with `(customer_id, template_code, channel, opted_in: bool)`.

**Tracking**: Log in the Phase 2 backlog — not part of this batch.

### Invoice reminder schedule — where defaults are stored

The dunning reminder schedule is configured via `platform_setting`:
- `invoice_reminder_days_1` = 1 (day overdue)
- `invoice_reminder_days_2` = 7 (days overdue)
- `invoice_reminder_days_3` = 14 (days overdue)

These are stored as null-tenant default rows in `platform_setting` (keyed by `platform_setting_catalog.key`). Tenants can override per-tenant via the Settings UI. At runtime, `services/setting_resolver.py` resolves the effective value: tenant-specific row if present, otherwise the null-tenant platform default. The Celery task `tasks/dunning.py` reads these three keys at runtime.

---

## Test Cleanup

### `test_a41_photo_upload_pipeline.py` — orphaned expense category code

**File**: `backend/tests/batch_b7b/test_a41_photo_upload_pipeline.py`

**Problem**: Line 718 uses `job_expense_category_code="other"` — but `other` is not a seeded `job_expense_category` code. The seeded codes are `materials`, `equipment`, `permits`.

**Fix**: Change `"other"` to `"materials"` (the most appropriate category for the test context).

---

## Definition of Done

**Phase 1** (unit tests only):
```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```
Zero new failures vs. baseline.

**Phase 2** (full suite):
```bash
python -m pytest --tb=short -q 2>&1 | tail -10
```
Zero new failures vs. baseline.

**Completion criteria checklist**:
- [ ] All 8 Alembic migrations applied and stamped
- [ ] `seed_core.py` updated for all 6 data changes (no code changes to seed orchestration)
- [ ] `Payment` SQLModel has `refunded_amount_cents` and `refunded_at` removed
- [ ] `stripe_subscriptions.py` `_handle_refund_event()` creates negative-amount payment row
- [ ] `invoice_status partial` transition logic added to `stripe_payment_intents.py`
- [ ] 4 services/tasks have get-or-create fallback replaced with hard lookup + graceful return
- [ ] `test_a41_photo_upload_pipeline.py` expense category code fixed
- [ ] `python generate_db_model_map.py` run after model changes
- [ ] Phase 1 gate: 0 new failures
- [ ] Phase 2 gate: 0 new failures

---

## Completion Summary Template

```
## SD-2 Completion Summary

**Completed**: [date]
**Baseline**: [N] passed, [N] failed
**Final**: [N] passed, [N] failed

**Migrations applied** (8):
- [list each]

**seed_core.py changes**: [describe]
**Service changes**: [list files]
**Test fixes**: [list files]
```
