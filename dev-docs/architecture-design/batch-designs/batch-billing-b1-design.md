# Batch Design: BILLING-B1 — Progress Billing: Payment Schedule Orchestration

**Batch**: BILLING-B1
**Type**: Mixed (BE + web FE) — **Python Engineer runs first**, then React Engineer
**Engineers**: Pilot Python Engineer (Part A) → Pilot React Engineer (Part B)
**Author**: Pilot Architect
**Date**: 2026-07-28
**Status**: Ready for Tom review → Python Engineer
**Source plan**: `pilot-launch-plan.md §2.3` → BILLING-B1
**Design reference**: `competitor-billing-modes-analysis.md §5.3` (Founder-approved architecture, July 24, 2026)
**Frontend companion**: BILLING-B1 Part B (React) — consumes the Part A contract after `pnpm sync-api-types`

> **Origin**: Deposit + progress/milestone billing is table-stakes across every SMB field-service competitor (HCP, Jobber, Workiz, Service Fusion, FieldEdge — see §3 of the analysis). The live `invoice` table already carries the `billing_mode` CHECK (`line_item` | `progress`) and a `progress_pct` column, but there is **no parent table to orchestrate the draws** — today a deposit can only be modeled as a manual ad-hoc invoice. This batch ships true tenant-controlled payment-schedule orchestration. **A deposit is modeled as the first draw (`sequence=1`) — no new `billing_mode` enum value.**

---

## A. Input Read Summary

| Input | Why | Key takeaway (MCP-verified 2026-07-28 against live `pilot_dev`) |
|---|---|---|
| `postgres-local` MCP — alembic head | Migration base | Head = **`3131f106f1b9`** (DLC-B4). |
| MCP — `payment_schedule` / `payment_schedule_line` existence | Confirm clean slate | Neither table exists — greenfield. |
| MCP — `invoice` columns | Confirm FK target + retained columns | `invoice` has `id`, `tenant_id` (NOT NULL), `customer_id` (NOT NULL), `site_id` (NOT NULL), `job_id` (NULL), `quote_id` (NULL), `billing_mode` (varchar NOT NULL default `'line_item'`), `progress_pct` (numeric NULL), `total_cents`, `subtotal_cents`, `status_id` (NOT NULL), `is_active` (NOT NULL). **No `payment_schedule_line_id` yet.** |
| MCP — `chk_invoice_billing_mode` | Confirm no enum change needed | `CHECK (billing_mode IN ('line_item','progress'))` — **retained as-is**; `progress` invoices will carry `payment_schedule_line_id`, `line_item` leave it NULL. |
| MCP — `quote` / `job` columns | FK targets for the schedule parent | Both have `id`, `tenant_id`, `customer_id`, `site_id` (all uuid). Schedule can originate at either quote or job stage. |
| MCP — trigger functions | Exact names for new tables | Available: `set_updated_at`, `guard_created_fields_immutable`, and **`audit.log_changes()`** (schema-qualified — audit trigger lives in the `audit` schema). |
| MCP — `customer` trigger DDL | Mirror pattern for new tables | `audit_customer_changes AFTER INSERT OR DELETE OR UPDATE … EXECUTE FUNCTION audit.log_changes()`; `trg_customer_set_updated_at BEFORE UPDATE … set_updated_at()`; `trg_customer_guard_created_immutable BEFORE UPDATE … guard_created_fields_immutable()`. |
| `billing.py` `Invoice` model | Model + mixin pattern | `Invoice(StandardAuditMixin, SQLModel, table=True)`; `InvoiceLine` uses `AppendOnlyMixin`. New tables use `StandardAuditMixin`. |
| `invoices.py` routes | Endpoint + `_impl` + `/test` pattern | `router = APIRouter()`; shared `_create_invoice_impl`; `/test` twins; `require_permission("invoices.create"/"invoices.view"/"invoices.update")`. |
| `batch-class-b1-design.md` | Recent new-table precedent | TEXT+CHECK (not PG ENUM); nullable-tenant not needed here (these are tenant-owned, not platform lookups); partial-index pattern; trigger mirroring; seed core+scenario dual rollout. |
| `README-seed-data.md` | Seed rollout | Group D scenario scripts (`seed_scenario_quote_to_cash.py`) own the invoices; a progress-schedule scenario is added there. |
| `pilot-operations.md` | Billing paywall context | `is_billing_active` gates the API; draw-invoice generation is a normal invoice create — no subscription-tier gate on progress billing for MVP (flag to Tom if he wants it tier-gated). |

---

## B. Migration Plan

**One Alembic migration** (blank, per Rule 4). Base revision **`3131f106f1b9`**. Three logical groups. Full upgrade → downgrade → upgrade triple-verify required.

> **Engineer pre-work**: before writing trigger DDL, re-run `SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid='public.customer'::regclass AND NOT tgisinternal` and mirror the argument style **exactly** (note the audit function is `audit.log_changes()` — schema-qualified). Re-confirm alembic head is still `3131f106f1b9`; if another batch landed first, rebase.

### B.1 — `payment_schedule` (parent table)

One schedule per quote/job billed in draws. `StandardAuditMixin` (`created_at/updated_at/created_by/updated_by`).

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | uuid PK | NO | `default_factory=uuid.uuid4` |
| `tenant_id` | uuid FK→`tenant.id` ON DELETE RESTRICT | NO | tenant-scoped (never `db.get()`) |
| `quote_id` | uuid FK→`quote.id` ON DELETE SET NULL | YES | schedule may originate at quote stage |
| `job_id` | uuid FK→`job.id` ON DELETE SET NULL | YES | or at job stage |
| `customer_id` | uuid FK→`customer.id` ON DELETE RESTRICT | NO | denormalized for tenant-scoped queries |
| `site_id` | uuid FK→`site.id` ON DELETE RESTRICT | NO | denormalized |
| `contract_total_cents` | integer | NO | the total the draws must sum to |
| `status` | text | NO | CHECK `status IN ('draft','active','completed','cancelled')`; server_default `'draft'` |
| `basis_default` | text | NO | CHECK `basis_default IN ('percent','fixed_amount')`; server_default `'percent'` |
| `is_active` | boolean | NO | server_default `true` (soft-delete convention) |
| `created_at/updated_at/created_by/updated_by` | (StandardAuditMixin) | | |

Indexes:
```sql
CREATE INDEX ix_payment_schedule_tenant_id ON payment_schedule (tenant_id);
CREATE INDEX ix_payment_schedule_quote_id  ON payment_schedule (quote_id);
CREATE INDEX ix_payment_schedule_job_id    ON payment_schedule (job_id);
```

Triggers (mirror `customer`, audit fn is schema-qualified):
```sql
CREATE TRIGGER trg_payment_schedule_set_updated_at BEFORE UPDATE ON payment_schedule
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER audit_payment_schedule_changes AFTER INSERT OR UPDATE OR DELETE ON payment_schedule
  FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
CREATE TRIGGER trg_payment_schedule_guard_created_immutable BEFORE UPDATE ON payment_schedule
  FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
```

### B.2 — `payment_schedule_line` (child / draw table)

The individual draws the tenant structures. `StandardAuditMixin`.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | uuid PK | NO | |
| `tenant_id` | uuid FK→`tenant.id` ON DELETE RESTRICT | NO | tenant-scoped |
| `payment_schedule_id` | uuid FK→`payment_schedule.id` ON DELETE CASCADE | NO | parent; CASCADE — draws die with the schedule |
| `sequence` | integer | NO | draw order; **`sequence=1` is the deposit by convention** (no special column) |
| `label` | text | NO | free text — "Deposit", "Rough-in complete", "Final" |
| `basis` | text | NO | CHECK `basis IN ('percent','fixed_amount')` |
| `percent` | numeric(5,2) | YES | required when `basis='percent'` — see CHECK below |
| `amount_cents` | integer | YES | required when `basis='fixed_amount'` — see CHECK below |
| `trigger_type` | text | NO | CHECK `trigger_type IN ('manual','date','milestone')`; server_default `'manual'` |
| `trigger_date` | date | YES | required when `trigger_type='date'` — see CHECK below |
| `milestone_label` | text | YES | free text when `trigger_type='milestone'` |
| `invoice_id` | uuid FK→`invoice.id` ON DELETE SET NULL | YES | set when this draw is invoiced |
| `status` | text | NO | CHECK `status IN ('pending','invoiced','paid','void')`; server_default `'pending'` |
| `is_active` | boolean | NO | server_default `true` |
| `created_at/updated_at/created_by/updated_by` | (StandardAuditMixin) | | |

**Conditional-NOT-NULL enforced by CHECK constraints** (the "3-part pattern" here is a single table-level CHECK since these are new columns on a new table — no backfill needed):
```sql
-- basis drives which amount column is required
ALTER TABLE payment_schedule_line ADD CONSTRAINT psl_basis_amount_chk CHECK (
  (basis = 'percent'      AND percent IS NOT NULL AND amount_cents IS NULL)
  OR
  (basis = 'fixed_amount' AND amount_cents IS NOT NULL AND percent IS NULL)
);
-- trigger_type drives which trigger detail is required
ALTER TABLE payment_schedule_line ADD CONSTRAINT psl_trigger_detail_chk CHECK (
  (trigger_type = 'date'      AND trigger_date IS NOT NULL)
  OR
  (trigger_type = 'milestone' AND milestone_label IS NOT NULL)
  OR
  (trigger_type = 'manual')
);
```

Indexes + uniqueness:
```sql
CREATE INDEX ix_psl_tenant_id ON payment_schedule_line (tenant_id);
CREATE INDEX ix_psl_schedule_id ON payment_schedule_line (payment_schedule_id);
-- draw order unique within a schedule
CREATE UNIQUE INDEX uq_psl_schedule_sequence
  ON payment_schedule_line (payment_schedule_id, sequence);
-- one invoice per draw (Integrity rule 4) — partial (invoice_id nullable)
CREATE UNIQUE INDEX uq_psl_invoice_id
  ON payment_schedule_line (invoice_id) WHERE invoice_id IS NOT NULL;
```

Triggers: same three as B.1, renamed for `payment_schedule_line`.

### B.3 — `invoice.payment_schedule_line_id` (nullable FK — additive, no backfill)

The `invoice` table has existing rows, but this column is **nullable and additive** — no 3-part NOT NULL pattern needed (all existing invoices are `line_item`, so NULL is correct for them):

```sql
ALTER TABLE invoice ADD COLUMN payment_schedule_line_id uuid
  REFERENCES payment_schedule_line(id) ON DELETE SET NULL;
CREATE INDEX ix_invoice_payment_schedule_line_id ON invoice (payment_schedule_line_id);
```

> **Circular-FK note**: `payment_schedule_line.invoice_id → invoice.id` AND `invoice.payment_schedule_line_id → payment_schedule_line.id` form a cycle. Both FKs are **nullable** and both are `ON DELETE SET NULL`, so no ordering deadlock: create the schedule + lines first (invoice_id NULL), then on draw-invoicing create the invoice (payment_schedule_line_id set) and back-fill `payment_schedule_line.invoice_id`. Document this in the service (§F). The migration creates `payment_schedule_line` before adding the invoice column, so DDL ordering is: create parent → create line → alter invoice.

- The existing `billing_mode` (`line_item`|`progress`) and `progress_pct` columns are **retained unchanged** — no enum edit.
- `progress` invoices carry `payment_schedule_line_id`; `line_item` invoices leave it NULL.
- `progress_pct` on a generated progress invoice reflects cumulative % billed to date across the schedule (for the invoice PDF/template).

### B.4 — Downgrade

Exact reverse: drop `ix_invoice_payment_schedule_line_id` + `invoice.payment_schedule_line_id` FK/column; drop `payment_schedule_line` triggers + indexes + CHECKs + table; drop `payment_schedule` triggers + indexes + table.

### B.5 — Post-migration required steps
- `alembic upgrade head → downgrade -1 → upgrade head` (triple-verify).
- `python generate_db_model_map.py` (new `PaymentSchedule` + `PaymentScheduleLine` models + `Invoice` field).
- `python schema_manager.py` CRUD to record both new tables + `invoice.payment_schedule_line_id` in the master JSON.
- `python export_openapi_json.py` (new endpoints + schema changes).

---

## C. Execution Order

| # | Step | Files |
|---|---|---|
| 1 | Models: `PaymentSchedule` + `PaymentScheduleLine` (new) in `billing.py`; add `Invoice.payment_schedule_line_id` nullable FK | `app/models/billing.py` |
| 2 | Alembic migration (§B, 3 groups: parent → child → invoice column; triggers + CHECKs) | `migrations/versions/…billing_b1_payment_schedule.py` |
| 3 | Run migration triple-verify; `generate_db_model_map.py` | — |
| 4 | Pydantic schemas: `PaymentScheduleCreate/Update/Response`, `PaymentScheduleLineCreate/Update/Response`, `PaymentScheduleActivateRequest`, `DrawInvoiceGenerateRequest`; add `payment_schedule_line_id` to `InvoiceResponse` | `api/schemas/schemas.py` |
| 5 | Service: `services/payment_schedule_service.py` — reconciliation, activation, draw-invoice generation (§F) | new `services/payment_schedule_service.py` |
| 6 | API: new `api/routes/payment_schedules.py` — CRUD on schedules + lines, activate, generate-draw-invoice (§D) + `/test` twins; register router in `app/main.py` | `api/routes/payment_schedules.py`, `app/main.py` |
| 7 | Seed — Group D: one progress-schedule scenario in `seed_scenario_quote_to_cash.py` (deposit + 2 draws against an existing quote/job) | `migrations/scripts/seed_scenario_quote_to_cash.py` |
| 8 | `export_openapi_json.py`; `schema_manager.py`; tests (`tests/domains/invoicing_billing/`) | — |
| — | **HANDOFF** → React Engineer (Part B) after `export_openapi_json.py` + commit | — |

---

## D. New API Endpoints

All under a new `api/routes/payment_schedules.py`, prefix `/api/v1/payment-schedules`. Every mutation calls `set_audit_context_sync(db, user_id=current_user.id)` before writes. All tenant-scoped `select()` (no `db.get()`). RFC 7807 errors. Every create/mutation `/test` twin via `TestUserContext` (inclusions §11). Idempotency-Key on the two POSTs the mobile app may fire offline (draw-invoice generation + schedule create).

| # | Endpoint | Method | RBAC | Purpose |
|---|---|---|---|---|
| 1 | `/payment-schedules` | POST | `invoices.create` | Create a draft schedule (with optional inline draws) for a quote or job. |
| 2 | `/payment-schedules/{id}` | GET | `invoices.view` | Fetch schedule + its lines (tenant-scoped). |
| 3 | `/payment-schedules/{id}` | PATCH | `invoices.update` | Edit draft schedule header (`contract_total_cents`, `basis_default`) — only while `status='draft'`. |
| 4 | `/payment-schedules/{id}/lines` | POST | `invoices.update` | Add a draw to a draft schedule. |
| 5 | `/payment-schedules/{id}/lines/{line_id}` | PATCH | `invoices.update` | Edit/reorder a draw (draft only). |
| 6 | `/payment-schedules/{id}/lines/{line_id}` | DELETE | `invoices.update` | Soft-delete a draw (draft only). |
| 7 | `/payment-schedules/{id}/activate` | POST | `invoices.update` | Validate sum reconciliation → set `status='active'`. 422 on residual mismatch. |
| 8 | `/payment-schedules/{id}/lines/{line_id}/generate-invoice` | POST | `invoices.create` | Generate the draw's `progress` invoice; set `line.invoice_id` + `line.status='invoiced'`; **Idempotency-Key**. |
| 9 | `/payment-schedules` | GET | `invoices.view` | List schedules for a quote/job (`?quote_id=` / `?job_id=`). |

**Response shapes** (schemas in `api/schemas/schemas.py`):
```
PaymentScheduleLineResponse:
  { id, payment_schedule_id, sequence, label, basis, percent, amount_cents,
    resolved_amount_cents, trigger_type, trigger_date, milestone_label,
    invoice_id, status }
PaymentScheduleResponse:
  { id, quote_id, job_id, customer_id, site_id, contract_total_cents,
    status, basis_default, lines: PaymentScheduleLineResponse[],
    scheduled_total_cents, residual_cents }
```
- `resolved_amount_cents` = the computed cents for the draw (percent resolved against `contract_total_cents`, or the fixed `amount_cents`).
- `scheduled_total_cents` = sum of all active lines' resolved amounts; `residual_cents` = `contract_total_cents − scheduled_total_cents` (must be 0 to activate).

**Error codes**: 404 (schedule/line not found in tenant — never 403); 409 (edit attempt when `status != 'draft'`; re-invoicing a draw that already has an active invoice — Integrity rule 4); 422 (sum reconciliation residual ≠ 0 on activate; invalid basis/trigger combos caught by CHECK → surfaced as RFC 7807).

> **No new `billing_mode` enum value** — the draw-invoice generator creates an invoice with `billing_mode='progress'` + `payment_schedule_line_id` set.

---

## E. Pattern Reuse Decisions

| Pattern (`mvp-arch.md §16` / methods) | Applies | How |
|---|---|---|
| TEXT + CHECK (not PG ENUM) | ✅ | All `status`/`basis`/`trigger_type` columns — matches `customer.type` / CLASS-B1 precedent. |
| Mandatory triggers on new tables (audit/updated_at/immutable) | ✅ | Both new tables mirror `customer`'s trigger set (audit fn schema-qualified `audit.log_changes()`). |
| Additive nullable FK (no 3-part NOT NULL) | ✅ | `invoice.payment_schedule_line_id` — nullable, existing rows correctly NULL. |
| Conditional-NOT-NULL via table CHECK | ✅ | `psl_basis_amount_chk`, `psl_trigger_detail_chk` (analysis §5.3.3 rule 5). |
| `db.get()` ban | ✅ | All schedule/line/invoice fetches tenant-scoped `select()`. |
| Idempotency-Key (methods §9.3) | ✅ | Draw-invoice generation + schedule create — mobile-offline safe POSTs. |
| Always-preview-before-send | ✅ (FE) | Generating each draw invoice previews before dispatch (analysis §5.3.5). |
| Track-changes diff | ✅ (FE) | Editing a draft schedule pre-activation. |
| Optimistic UI | ✅ (FE) | Adding/reordering draws. |
| 409-and-refresh (pre-commit staleness) | ✅ | Edit-after-activate + re-invoice-a-drawn-line both return 409. |
| `/test` endpoint for new entity (inclusions §11) | ✅ | All mutations get `/test` twins. |
| Seed core + scenario dual rollout | ✅ (scenario only) | No platform/core rows (schedules are tenant-owned, not lookups); Group D scenario adds one progress schedule. |

---

## F. Shared Module Interfaces & Integrity Logic

New `services/payment_schedule_service.py`. No Celery tasks (draw generation is synchronous, user-triggered).

```python
def resolve_line_amount_cents(line: PaymentScheduleLine, contract_total_cents: int) -> int:
    """percent → round(contract_total_cents * percent/100); fixed_amount → amount_cents."""

def compute_reconciliation(schedule, lines, *, contract_total_cents) -> tuple[int, int]:
    """
    Returns (scheduled_total_cents, residual_cents).
    Mixed basis: resolve fixed_amount lines first, then distribute percent lines
    across the REMAINDER (contract_total - sum(fixed)), per analysis §5.3.3 rule 2.
    residual = contract_total_cents - scheduled_total_cents.
    """

def activate_schedule(db, schedule_id, user_context) -> PaymentSchedule:
    """
    Tenant-scoped fetch (select, not db.get). Recompute reconciliation.
    If residual_cents != 0 → RFC 7807 422 (over/under-billing guard, rule 1).
    Set status='active'. Idempotent: re-activating an already-active schedule is a no-op 200.
    """

def generate_draw_invoice(db, schedule_id, line_id, user_context, idempotency_key) -> Invoice:
    """
    Preconditions (tenant-scoped): schedule.status == 'active'; line.status == 'pending';
    line.invoice_id IS NULL (rule 4 — one invoice per draw; else 409).
    Creates Invoice(billing_mode='progress', payment_schedule_line_id=line.id,
      total_cents=resolve_line_amount_cents(line, schedule.contract_total_cents),
      customer_id/site_id/job_id from schedule, status=draft-equivalent,
      progress_pct = cumulative % billed to date across the schedule).
    Then set line.invoice_id + line.status='invoiced'. Two-step write resolves the
    circular FK (create invoice with the line FK, then back-fill line.invoice_id).
    Idempotency-Key (24h TTL) — a retried generation returns the same invoice.
    """
```

**Integrity rules (analysis §5.3.3), enforced at app + DB layer:**
1. **Sum reconciliation** — draws must sum to `contract_total_cents` on activation (app-layer `activate_schedule` 422 guard).
2. **Mixed basis allowed** — resolve fixed amounts first, distribute percent across the remainder.
3. **Deposit convention** — `sequence=1` = deposit in UI/PDF; no special column.
4. **One invoice per draw** — `uq_psl_invoice_id` partial unique + app-layer 409 on re-invoice (void the prior invoice first).
5. **Conditional NOT NULL** — `percent`/`amount_cents` + `trigger_date`/`milestone_label` via table CHECKs.

**Seed rollout (Group D only)**: In `seed_scenario_quote_to_cash.py`, add one `active` progress schedule against an existing seeded quote/job (e.g. Apex HQ install): `contract_total_cents` = the quote total; three draws — `sequence=1` "Deposit" `fixed_amount` (e.g. $500), `sequence=2` "Rough-in" `percent` 50 of remainder, `sequence=3` "Final" `percent` remainder. Look up quote/job/customer/site by business key at runtime (never hardcode scenario UUIDs — README §7). Idempotent value-scoped upserts. One draw (`sequence=1`) may be pre-linked to a generated progress invoice to give the FE a "partially invoiced schedule" to render.

---

## G. Open Questions Resolved

| Q | Resolution |
|---|---|
| New `billing_mode` enum value for deposit/progress-draw? | **No.** Deposit = `sequence=1` draw; draw invoices are `billing_mode='progress'` + `payment_schedule_line_id`. `chk_invoice_billing_mode` unchanged. (Founder-approved, analysis §5.1.) |
| Where does the schedule originate — quote or job? | **Either.** Both `quote_id` and `job_id` are nullable FKs on `payment_schedule`; a schedule references whichever stage created it (may carry both once a quote converts to a job). |
| Circular FK (`invoice ↔ payment_schedule_line`)? | Both FKs nullable + `ON DELETE SET NULL`. Two-step write in `generate_draw_invoice` (create invoice with line FK, then back-fill `line.invoice_id`). No DDL deadlock — child table created before the invoice column is added. |
| `contract_total_cents` source? | Denormalized integer on the schedule, seeded from the quote/job total at creation; the reconciliation guard enforces draws sum to it. Not a live FK to `quote.total_cents` (the quote can change post-schedule; the schedule locks its own contract total). |
| Mixed percent + fixed draws? | **Allowed** (rule 2) — fixed resolved first, percent distributed across the remainder. |
| Subscription-tier gate on progress billing? | **Not for MVP** — draw generation is a normal invoice create under the existing `is_billing_active` paywall. Flag to Tom if progress billing should be a paid-tier feature later (`require_permission(..., feature_code=...)`). |
| Delete/void semantics | Draft schedule: draws soft-delete freely. Active schedule: editing draws blocked (409); voiding a draw's invoice returns the line to `pending` (re-invoiceable). Cancelling a schedule sets `status='cancelled'`; `ON DELETE CASCADE` on lines only fires on hard-delete (not used at runtime — soft-delete via `is_active`). |
| AIA / retainage / cost-plus / unit-price | **Deferred** (enterprise — analysis §5.2). Not in scope. |
| Recurring/membership billing | **Separate sibling** (`service_agreement`) — Phase 1.5 discovery doc, not this batch (analysis §6). |

---

## H. Part B — Frontend Scope (React Engineer, after handoff)

> Full detail goes in `batch-billing-b1-react-engr-prompt.md` after Part A closes. Summary for planning:

- **Surface**: a **Payment Schedule builder** on the invoice/quote flow — draw editor (add/reorder/remove draws, percent or fixed, deposit as `sequence=1`), live reconciliation (`scheduled_total` vs `contract_total`, residual banner), activate action, and a per-draw "Generate invoice" action (always-preview-before-send).
- **§16 patterns consumed**: track-changes diff (draft editing), optimistic UI (draw add/reorder), always-preview-before-send (draw invoice), idempotency key (generate-invoice POST), 409-and-refresh (edit-after-activate).
- **Hooks**: `usePaymentSchedule`, `useCreatePaymentSchedule`, `useUpdateScheduleLine`, `useActivateSchedule`, `useGenerateDrawInvoice` — all via `apiClient`, types from `@pilot/shared-types` after `pnpm sync-api-types`.
- **RBAC**: builder gated `invoices.create` / `invoices.update` via `<RoleGate>`.
- **Component manifest** (Part B): `PaymentScheduleBuilder`, `DrawRow`, `ReconciliationBar`, `GenerateDrawInvoiceButton` in `apps/web/src/features/invoices/` (or a new `features/billing/`). Deposit is a labeled `sequence=1` `DrawRow`, not a separate component.

---

## Handoff

BILLING-B1 (this doc) → **Python Engineer first** (Part A: §B–§F). On completion the engineer runs `python export_openapi_json.py`, commits, and notifies the React Engineer. Part B (the payment-schedule builder) then runs `pnpm sync-api-types` and consumes the contract.

*Authored by Pilot Architect, 2026-07-28. All schema facts MCP-verified against live `pilot_dev` (alembic head `3131f106f1b9`; both new tables absent; `chk_invoice_billing_mode` = `line_item|progress`; audit trigger fn = `audit.log_changes()`). No PG ENUMs — TEXT+CHECK. Cost impact: zero (pure relational + app logic on existing RDS + Fargate — analysis §5.3.4).*
