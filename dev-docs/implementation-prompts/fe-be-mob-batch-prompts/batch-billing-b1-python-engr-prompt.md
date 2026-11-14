# Implementation Prompt: BILLING-B1 (Part A) — Progress Billing: Payment Schedule Orchestration

**Mode**: Pilot Python Engineer
**Batch**: BILLING-B1 (Part A — Backend)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 → BILLING-B1
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-billing-b1-design.md` (read §A–§G in full)
**Estimated session**: 4–5 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: BILLING-B1 Part B (React) — the payment-schedule builder. It runs `pnpm sync-api-types` and consumes your contract **after** you finish. Your final step is the handoff (run `export_openapi_json.py`, commit, notify).

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-billing-b1-design.md`** — the design doc for this batch; §B (migration), §D (endpoints), §F (service + integrity rules) are the spec you implement

**Before writing any billing/invoice code — read `dev-docs/pilot-operations.md`** — covers: `is_billing_active` paywall gate, tier→plan→ppfv cascade, and the 6 subscription status codes. **Design decision (§G): progress billing is NOT subscription-tier gated for MVP** — draw-invoice generation is a normal invoice create under the existing paywall. Do NOT add a `feature_code` to these endpoints unless Tom later asks for it.

Critical rules for this batch:

- **Rule 1 / Rule 16 (verify, don't assume)**: 186 tables exist. Never guess a column/table name. Run the MCP `information_schema.columns` query for **every table you touch** (`invoice`, `quote`, `job`, `customer`, `site`, `tenant`, and your two new tables once created) before writing SQL or SQLModel fields. If MCP returns an error → **STOP and ask Tom**.
- **Rule 4 (blank migrations)**: This batch has an Alembic migration — write it **blank** (`alembic revision -m "..."`, never `--autogenerate`). Implement `downgrade()` as the exact reverse.
- **Rule 6 (`db.get()` banned)**: Every schedule/line/invoice fetch is a tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid`. **One documented exception**: none in this batch — every entity here is tenant-scoped, so `db.get()` never appears.
- **Rule 8 / RFC 7807**: All error responses use the Problem Details dict shape. Return **404** (not 403) when a schedule/line is not found in the tenant. Return **409** on edit-after-activate and re-invoice-a-drawn-line. Return **422** on sum-reconciliation residual ≠ 0.
- **Rule 9 (audit context)**: Every mutation endpoint calls `set_audit_context_sync(db, user_id=current_user.id)` before the first `db.add()`/`db.commit()`.
- **Rule 12 / §21 (sync-by-design)**: Every route, `_impl()`, and service function that touches the `Session` is a plain `def` — never `async def`. Verify against `api/routes/invoices.py` (all `def`).
- **Rule 13 / §22 (Pydantic v2)**: v2 idioms only (`model_config = ConfigDict`, `@field_validator`/`@model_validator`, `.model_dump()`). Every route has `response_model`. **Money is integer cents** — never a float. `percent` is `numeric(5,2)` in the DB and `Decimal` in Python — never do float arithmetic on it.
- **Rule 15 / §24 (mixins)**: Both new tables inherit **`StandardAuditMixin`** from `app/models/mixins.py` — never hand-declare `created_at`/`updated_at`/`created_by`/`updated_by`. Add `tenant_id` explicitly (the mixin does not provide it). All timestamps are TIMESTAMPTZ (UTC-aware).
- **Rule 11 (fix every failure)**: If any test fails during your work — even one that looks pre-existing — you fix it before declaring done. If you cannot find the root cause → STOP and ask Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: do NOT treat them as "pre-existing" and proceed. Either (a) confirm with Tom it's a known accepted failure, or (b) fix it first. You may NOT start while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` MCP is for **read-only verification only**. Never INSERT/UPDATE/DELETE through it — all data changes go through application code, seed scripts, or Alembic. If a query errors → STOP and ask Tom.

Run **all** of these via `postgres-local` MCP before writing any code. These were run by the Architect on 2026-07-28 — re-run them to confirm nothing shifted, and **note any discrepancy in your Completion Summary** (use the MCP value, not the prompt value, if they differ).

```sql
-- 1. Confirm alembic head is still the migration base. Expect: 3131f106f1b9.
SELECT version_num FROM public.alembic_version;

-- 2. Confirm BOTH new tables are absent (greenfield). Expect: [] (empty).
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('payment_schedule','payment_schedule_line')
ORDER BY table_name;

-- 3. invoice columns — confirm FK targets + that payment_schedule_line_id does NOT exist yet.
--    Expect: billing_mode (varchar NOT NULL default 'line_item'), progress_pct (numeric NULL),
--    customer_id/site_id NOT NULL, quote_id/job_id NULL, idempotency_key present, NO payment_schedule_line_id.
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
ORDER BY ordinal_position;

-- 4. Confirm the billing_mode CHECK is unchanged (no enum edit needed).
--    Expect: CHECK (billing_mode IN ('line_item','progress')).
SELECT con.conname, pg_get_constraintdef(con.oid) AS def
FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid
WHERE c.relname = 'invoice' AND con.contype = 'c' AND con.conname = 'chk_invoice_billing_mode';

-- 5. FK-target columns on quote/job/customer/site/tenant (all uuid).
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('quote','job','customer','site','tenant')
  AND column_name IN ('id','tenant_id','customer_id','site_id')
ORDER BY table_name, column_name;

-- 6. EXACT customer trigger DDL — mirror this argument style verbatim on both new tables.
--    NOTE the live event order is "AFTER INSERT OR DELETE OR UPDATE" and the audit fn is
--    schema-qualified: audit.log_changes(). set_updated_at() + guard_created_fields_immutable()
--    are in the public schema (unqualified is fine).
SELECT tgname, pg_get_triggerdef(oid) AS def
FROM pg_trigger
WHERE tgrelid = 'public.customer'::regclass AND NOT tgisinternal
ORDER BY tgname;
```

**Architect-confirmed results (2026-07-28)** — if yours differ, use yours:
- Head = `3131f106f1b9`; both new tables absent.
- `invoice` has NO `payment_schedule_line_id`; `billing_mode` varchar NOT NULL default `'line_item'`; `progress_pct` numeric NULL; `idempotency_key` varchar NULL.
- `chk_invoice_billing_mode` = `CHECK (billing_mode IN ('line_item','progress'))` — **retained as-is**.
- Audit fn is `audit.log_changes()` (schema-qualified). `set_updated_at()` + `guard_created_fields_immutable()` are `public`.

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/app/models/billing.py              ← Invoice model (StandardAuditMixin) + InvoiceLine (AppendOnlyMixin); add the 2 new models + Invoice.payment_schedule_line_id here
backend/app/models/mixins.py               ← confirm StandardAuditMixin fields (do NOT hand-declare timestamps)
backend/api/routes/invoices.py             ← router/_impl/`/test` pattern; require_permission strings; _create_invoice_impl signature; how idempotency_key flows onto Invoice
backend/api/routes/quotes.py               ← full new-entity route + `/test` twin pattern (cleaner reference than invoices for a brand-new router)
backend/api/schemas/schemas.py             ← existing InvoiceCreate/InvoiceResponse shapes; add all new PaymentSchedule* schemas + payment_schedule_line_id on InvoiceResponse
backend/migrations/versions/2026_07_27_1822-3131f106f1b9_dlc_b4_sms_brand_prefix.py  ← the current head migration — down_revision reference + blank-migration style
backend/migrations/versions/2026_07_27_1336-44fb6fed24c3_class_b1_classification.py  ← CLASS-B1: the best recent precedent for new-table + triggers + CHECKs in one blank migration
backend/tests/conftest.py                  ← available fixtures (test_tenant, test_customer, test_site, test_quote_version, second_tenant, tenant_a/tenant_b)
backend/db_models_map.md                   ← confirm model→table names before/after
backend/migrations/scripts/seed_scenario_quote_to_cash.py  ← Group D scenario owner of QTC quotes/jobs/invoices; add the progress-schedule scenario here
backend/README-seed-data.md                ← §3 (Group A–D), §6 (run order), §7 (DELETE safety + never-hardcode-scenario-UUID rule)
backend/core/test_context.py               ← TestUserContext / get_test_context for the `/test` twins
```

Also run these greps to find related code:

```bash
grep -rn "class Invoice\b" backend/app/models/ --include="*.py"
grep -rn "StandardAuditMixin" backend/app/models/billing.py
grep -rn "_create_invoice_impl\|InvoiceResponse\|billing_mode" backend/api/ --include="*.py" -l
grep -rn "set_audit_context_sync\|TestUserContext" backend/api/routes/quotes.py
```

> **The `api/schemas/` layer is separate from `app/models/`**: `app/models/billing.py` holds the SQLModel ORM classes; `api/schemas/schemas.py` holds the Pydantic request/response shapes. This batch touches **both** — the two new tables (models) AND their request/response schemas.

---

## Background / Context

Deposit + progress/milestone billing is table-stakes across every SMB field-service competitor. The `invoice` table already carries `billing_mode` (`line_item`|`progress`) and `progress_pct`, but there is **no parent table to orchestrate the draws** — today a deposit can only be a manual ad-hoc invoice.

This batch ships true tenant-controlled payment-schedule orchestration:
- **`payment_schedule`** (parent) — one schedule per quote/job, with a locked `contract_total_cents` the draws must sum to.
- **`payment_schedule_line`** (child/draw) — the individual draws. **A deposit is simply the draw with `sequence=1`** — no new `billing_mode` enum value, no special column.
- **`invoice.payment_schedule_line_id`** — nullable additive FK; a generated `progress` invoice points back at the draw it bills.

Full spec is the design doc §B–§F. This prompt operationalizes it.

---

## Task 1 — Models

In `backend/app/models/billing.py`:

1. **`PaymentSchedule(StandardAuditMixin, SQLModel, table=True)`** — columns per design §B.1:
   - `id` (uuid PK, `default_factory=uuid.uuid4`), `tenant_id` (uuid, FK `tenant.id`, NOT NULL), `quote_id` (uuid, FK `quote.id`, nullable), `job_id` (uuid, FK `job.id`, nullable), `customer_id` (uuid, FK `customer.id`, NOT NULL), `site_id` (uuid, FK `site.id`, NOT NULL), `contract_total_cents` (int, NOT NULL), `status` (str, NOT NULL, default `'draft'`), `basis_default` (str, NOT NULL, default `'percent'`), `is_active` (bool, NOT NULL, default `True`).
2. **`PaymentScheduleLine(StandardAuditMixin, SQLModel, table=True)`** — columns per design §B.2:
   - `id`, `tenant_id` (FK `tenant.id`, NOT NULL), `payment_schedule_id` (uuid, FK `payment_schedule.id`, NOT NULL), `sequence` (int, NOT NULL), `label` (str, NOT NULL), `basis` (str, NOT NULL), `percent` (`Decimal | None` → `numeric(5,2)` nullable), `amount_cents` (`int | None`, nullable), `trigger_type` (str, NOT NULL, default `'manual'`), `trigger_date` (`date | None`, nullable), `milestone_label` (`str | None`, nullable), `invoice_id` (uuid, FK `invoice.id`, nullable), `status` (str, NOT NULL, default `'pending'`), `is_active` (bool, NOT NULL, default `True`).
3. **`Invoice.payment_schedule_line_id`** — add `payment_schedule_line_id: uuid.UUID | None = Field(default=None, foreign_key="payment_schedule_line.id")` to the existing `Invoice` model.

> The CHECK constraints, indexes, unique indexes, and triggers are **created in the migration** (Task 2), not declared on the model — matches the CLASS-B1 precedent. The model only declares columns + FKs.

Then regenerate the model map:
```bash
cd <repo>/backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md
grep -E "PaymentSchedule|PaymentScheduleLine" db_models_map.md   # confirm under DB Tables
```

---

## Task 2 — Alembic Migration (blank)

### Alembic Migration Rules (methods §13)

1. Blank migration only: `alembic revision -m "billing_b1_payment_schedule"`. Never `--autogenerate`.
2. `down_revision = "3131f106f1b9"`.
3. Implement `downgrade()` as the **exact reverse**.
4. Triple-verify the full cycle after writing it.

**Three logical groups, in this DDL order** (§B — parent before child before invoice column, so the circular FK never deadlocks):

**Group 1 — `payment_schedule`** (§B.1): create table; then the 3 indexes (`ix_payment_schedule_tenant_id`, `ix_payment_schedule_quote_id`, `ix_payment_schedule_job_id`); the 2 status/basis CHECKs (`status IN ('draft','active','completed','cancelled')`, `basis_default IN ('percent','fixed_amount')`); then the 3 triggers mirroring `customer` — **use the exact DDL from MCP query 6**:

```sql
CREATE TRIGGER trg_payment_schedule_set_updated_at BEFORE UPDATE ON payment_schedule
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER audit_payment_schedule_changes AFTER INSERT OR DELETE OR UPDATE ON payment_schedule
  FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
CREATE TRIGGER trg_payment_schedule_guard_created_immutable BEFORE UPDATE ON payment_schedule
  FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();
```

> The audit fn is **`audit.log_changes()`** — schema-qualified. `set_updated_at()` and `guard_created_fields_immutable()` are unqualified (public). The live event order is `AFTER INSERT OR DELETE OR UPDATE` — mirror it exactly.

**Group 2 — `payment_schedule_line`** (§B.2): create table; the 2 conditional-NOT-NULL CHECKs verbatim from the design doc:

```sql
ALTER TABLE payment_schedule_line ADD CONSTRAINT psl_basis_amount_chk CHECK (
  (basis = 'percent'      AND percent IS NOT NULL AND amount_cents IS NULL)
  OR
  (basis = 'fixed_amount' AND amount_cents IS NOT NULL AND percent IS NULL)
);
ALTER TABLE payment_schedule_line ADD CONSTRAINT psl_trigger_detail_chk CHECK (
  (trigger_type = 'date'      AND trigger_date IS NOT NULL)
  OR
  (trigger_type = 'milestone' AND milestone_label IS NOT NULL)
  OR
  (trigger_type = 'manual')
);
```
plus the `status` CHECK (`status IN ('pending','invoiced','paid','void')`) and `trigger_type` CHECK (`trigger_type IN ('manual','date','milestone')`); the 2 plain indexes (`ix_psl_tenant_id`, `ix_psl_schedule_id`); the 2 unique indexes:

```sql
CREATE UNIQUE INDEX uq_psl_schedule_sequence ON payment_schedule_line (payment_schedule_id, sequence);
CREATE UNIQUE INDEX uq_psl_invoice_id ON payment_schedule_line (invoice_id) WHERE invoice_id IS NOT NULL;
```
then the same 3 triggers renamed for `payment_schedule_line`.

**Group 3 — `invoice.payment_schedule_line_id`** (§B.3) — additive nullable FK, **no 3-part NOT NULL pattern needed** (nullable; existing rows correctly NULL):

```sql
ALTER TABLE invoice ADD COLUMN payment_schedule_line_id uuid
  REFERENCES payment_schedule_line(id) ON DELETE SET NULL;
CREATE INDEX ix_invoice_payment_schedule_line_id ON invoice (payment_schedule_line_id);
```

**FK ON DELETE semantics** (§B): `payment_schedule.tenant_id/customer_id/site_id` → RESTRICT; `payment_schedule.quote_id/job_id` → SET NULL; `payment_schedule_line.payment_schedule_id` → **CASCADE**; `payment_schedule_line.invoice_id` → SET NULL; `invoice.payment_schedule_line_id` → SET NULL.

**`downgrade()`** — exact reverse: drop `ix_invoice_payment_schedule_line_id` + `invoice.payment_schedule_line_id`; drop `payment_schedule_line` (triggers → indexes → CHECKs → table); drop `payment_schedule` (triggers → indexes → CHECKs → table).

Then triple-verify:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current   # must show billing_b1 revision as head
```

---

## Task 3 — Pydantic Schemas

In `backend/api/schemas/schemas.py` add (§D response shapes):

- `PaymentScheduleLineCreate` / `PaymentScheduleLineUpdate` — `sequence`, `label`, `basis`, `percent` (`Decimal | None`), `amount_cents` (`int | None`), `trigger_type`, `trigger_date` (`date | None`), `milestone_label` (`str | None`). Add a `@model_validator(mode="after")` mirroring the DB CHECKs so a bad basis/trigger combo returns a clean 422 **before** hitting the DB constraint (defense in depth — but the DB CHECK is the source of truth).
- `PaymentScheduleLineResponse` — all line fields **plus** the computed `resolved_amount_cents: int`, plus `invoice_id`, `status`.
- `PaymentScheduleCreate` — `quote_id`/`job_id` (at least one required — `@model_validator`), `customer_id`, `site_id`, `contract_total_cents`, `basis_default`, optional inline `lines: list[PaymentScheduleLineCreate] = []`, `idempotency_key: str | None`.
- `PaymentScheduleUpdate` — `contract_total_cents`, `basis_default` (draft-only edits).
- `PaymentScheduleActivateRequest` — empty body model (or omit body; keep a model for forward-compat).
- `DrawInvoiceGenerateRequest` — `idempotency_key: str | None`.
- `PaymentScheduleResponse` — `id`, `quote_id`, `job_id`, `customer_id`, `site_id`, `contract_total_cents`, `status`, `basis_default`, `lines: list[PaymentScheduleLineResponse]`, computed `scheduled_total_cents: int`, computed `residual_cents: int`.
- **Add `payment_schedule_line_id: uuid.UUID | None = None` to the existing `InvoiceResponse`.**

Pydantic v2 only (`model_config = ConfigDict(from_attributes=True)` where reading ORM objects). Money integer cents; `percent` is `Decimal`.

---

## Task 4 — Service: `services/payment_schedule_service.py`

New file. No Celery (draw generation is synchronous, user-triggered). Implement per design §F:

```python
def resolve_line_amount_cents(line, contract_total_cents: int) -> int:
    """percent → round(contract_total_cents * percent/100) using Decimal; fixed_amount → amount_cents.
    Use Decimal + quantize for the percent path — never float."""

def compute_reconciliation(lines, *, contract_total_cents) -> tuple[int, int]:
    """Returns (scheduled_total_cents, residual_cents).
    Mixed basis (§F rule 2): resolve fixed_amount lines first, then distribute percent lines
    across the REMAINDER (contract_total - sum(fixed)). residual = contract_total - scheduled_total.
    Only active lines count."""

def activate_schedule(db, tenant_id, schedule_id, user_context) -> PaymentSchedule:
    """Tenant-scoped select() (never db.get). Recompute reconciliation.
    residual_cents != 0 → RFC 7807 422. Set status='active'.
    Idempotent: re-activating an already-active schedule is a no-op 200."""

def generate_draw_invoice(db, tenant_id, schedule_id, line_id, user_context, idempotency_key) -> Invoice:
    """Tenant-scoped preconditions: schedule.status=='active'; line.status=='pending';
    line.invoice_id IS NULL (rule 4 — else 409).
    Two-step write for the circular FK: (1) create Invoice(billing_mode='progress',
    payment_schedule_line_id=line.id, total_cents=resolve_line_amount_cents(...),
    customer_id/site_id/job_id from schedule, status = draft-equivalent status_id,
    progress_pct = cumulative % billed to date across the schedule), commit;
    (2) set line.invoice_id + line.status='invoiced', commit.
    Idempotency-Key (24h TTL) — a retried generation returns the SAME invoice
    (reuse the existing invoice idempotency_key mechanism — see how _create_invoice_impl stores it)."""
```

**Integrity rules (§F) — enforce at app layer, backstopped by DB:**
1. Sum reconciliation — 422 on activate if residual ≠ 0.
2. Mixed basis — fixed first, percent across remainder.
3. Deposit = `sequence=1` (convention only; no special column).
4. One invoice per draw — `uq_psl_invoice_id` + app-layer 409 on re-invoice.
5. Conditional NOT NULL — DB CHECKs + the Pydantic `@model_validator`.

> **`draft-equivalent status_id`**: invoice status is a FK to `invoice_status` (lookup), not a string. Look up the `draft` status row tenant-scoped/by code the same way `_create_invoice_impl` does — read that impl before writing this. Do NOT hardcode a status UUID.
> **`progress_pct`**: cumulative % billed to date = `sum(resolved_amount_cents of invoiced+this draw) / contract_total_cents * 100`, as `Decimal`. Store on the generated invoice for the PDF/template.

---

## Task 5 — API: `api/routes/payment_schedules.py`

New router, prefix `/api/v1/payment-schedules`, registered in `app/main.py`. Follow the `quotes.py` shared-`_impl` + `/test`-twin pattern. All routes sync `def`. Every mutation calls `set_audit_context_sync(db, user_id=current_user.id)` before writes. All fetches tenant-scoped `select()`. RFC 7807 errors (404 not-found, 409 stale/re-invoice, 422 reconciliation).

Endpoints (§D) — each mutation gets a `/test` twin via `TestUserContext` (inclusions §11):

| # | Endpoint | Method | RBAC (`require_permission`) |
|---|---|---|---|
| 1 | `/payment-schedules` | POST | `invoices.create` — create draft schedule (+ optional inline draws); **Idempotency-Key** |
| 2 | `/payment-schedules/{id}` | GET | `invoices.view` |
| 3 | `/payment-schedules/{id}` | PATCH | `invoices.update` — draft-only header edit |
| 4 | `/payment-schedules/{id}/lines` | POST | `invoices.update` — add draw (draft only) |
| 5 | `/payment-schedules/{id}/lines/{line_id}` | PATCH | `invoices.update` — edit/reorder draw (draft only) |
| 6 | `/payment-schedules/{id}/lines/{line_id}` | DELETE | `invoices.update` — soft-delete draw (draft only; set `is_active=False`) |
| 7 | `/payment-schedules/{id}/activate` | POST | `invoices.update` — reconcile → active; 422 on residual |
| 8 | `/payment-schedules/{id}/lines/{line_id}/generate-invoice` | POST | `invoices.create` — generate draw invoice; **Idempotency-Key**; 409 if already invoiced |
| 9 | `/payment-schedules` | GET | `invoices.view` — list `?quote_id=` / `?job_id=` |

`require_permission` strings confirmed against `invoices.py`: `invoices.create` / `invoices.view` / `invoices.update`. Draft-gate (endpoints 3–6): if `schedule.status != 'draft'` → **409**.

Register the router in `app/main.py` next to the other route includes (grep for `invoices` there).

---

## Seed Data Rollout (Scenario only — Group D)

Per `backend/README-seed-data.md` — read §3, §6, §7 before editing any seed script.

> **Layer 1 (core/platform) does NOT apply** — payment schedules are tenant-owned data, not platform lookups/reference rows. There are no core rows to seed. (Design §E: "scenario only".)

### Layer 2 — Scenario data (Group D)

In `seed_scenario_quote_to_cash.py` add **one `active` progress schedule** against an existing seeded quote/job (e.g. the Apex HQ install):
- `contract_total_cents` = the quote total (looked up at runtime).
- Three draws: `sequence=1` "Deposit" `fixed_amount` (e.g. $500 → `50000`); `sequence=2` "Rough-in" `percent` 50 of the remainder; `sequence=3` "Final" `percent` remainder — must reconcile to `contract_total_cents`.
- **Look up quote/job/customer/site by business key at runtime — never hardcode a scenario UUID** (README §7).
- Idempotent, value-scoped upserts (DELETE-safety §7 — include the full business key in any `mode_seed` DELETE).
- Pre-link `sequence=1` to a generated `progress` invoice so the FE has a "partially invoiced schedule" to render.

### Verification
- Confirm the schedule + 3 lines seed idempotently on a full reset+reseed (0 skipped).
- Run `pytest -m unit` after the seed change — fix any seed-resilience failures (assert-by-ID, never by count).

### README update
- Update `backend/README-seed-data.md` §4 (Current Seed State) with the new `payment_schedule` + `payment_schedule_line` scenario rows.

---

## Schema JSON Sync

After the migration runs and tests pass, record the schema in the master JSON via the path-based `backend/schema_manager.py` (read `backend/README-schema_manager.md` first). Use `set` for the two new tables and `set` for `tables.invoice.columns.payment_schedule_line_id`; `array-append` for indexes/FKs/check_constraints/triggers. **Never edit the JSON with `sed`/`awk`/inline Python.** If `schema_manager.py` errors → STOP and ask Tom.

---

## Regenerate OpenAPI + Model/Import Maps

```bash
cd <repo>/backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md          # models changed
python generate_app_import_map.py tests > app_model_imports.md  # new test files added
python export_openapi_json.py                                    # endpoints changed
grep -A 5 "payment-schedules" backend/openapi_schema_map.md      # confirm new endpoints present
```

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`. Domain folder: **`tests/domains/invoicing_billing/`**. New file(s), e.g. `test_billing_b1_payment_schedule.py`.

Every new test file:
```python
pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]
```
- Use the `client` fixture (never module-level `TestClient`) and the `/test` twins to create data.
- Use `test_tenant`/`test_customer`/`test_site`/`test_quote_version` fixtures — no hardcoded UUIDs.
- Scope every assertion by inserted IDs — never `assert len(...) == N`.
- Use `second_tenant` (or `tenant_a`/`tenant_b`) for isolation/IDOR tests.
- These endpoints are NOT entitlement-gated, so no `skip_mock_entitlement_allowed` needed.

**Required coverage (map to §D/§F):**
1. Create draft schedule with inline draws → response carries `scheduled_total_cents` + `residual_cents`.
2. `resolve_line_amount_cents` — percent and fixed paths (Decimal, correct rounding).
3. `compute_reconciliation` — mixed basis: fixed resolved first, percent across remainder; residual math.
4. Activate with residual ≠ 0 → **422**; activate with residual == 0 → `status='active'`; re-activate active → no-op 200 (idempotent).
5. Edit/add/delete a draw after activation → **409**.
6. `generate-invoice` happy path → invoice `billing_mode='progress'` + `payment_schedule_line_id` set; line `status='invoiced'`, `line.invoice_id` set; `progress_pct` correct.
7. Re-invoice a drawn line (line.invoice_id already set) → **409** (rule 4).
8. Idempotency-Key on generate-invoice → retried request returns the SAME invoice.
9. Cross-tenant: `tenant_b` fetching `tenant_a`'s schedule/line → **404** (never 403).
10. DB CHECK backstop: attempt `basis='percent'` with `amount_cents` set (bypassing the validator via `/test` raw insert path if feasible) → constraint rejects — or assert the Pydantic `@model_validator` 422s it.

---

## Final Verification

### Phase 1 — Unit Tests Only (after each task group)

```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```
All unit tests must pass before moving on. Fix any failure — including any that look pre-existing.

### Phase 2 — Lint + Full Suite (once, at the end)

```bash
cd <repo>/backend && source .venv/bin/activate
ruff check . --fix
ruff format .
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/invoicing_billing/ -v 2>&1 | tail -30
grep -A 5 "payment-schedules" backend/openapi_schema_map.md
echo "=== BILLING-B1 (Part A) FINAL VERIFICATION COMPLETE ==="
```

> Warning-clean is part of done: no unjustified `# noqa`, no Pydantic v1 carryover, no DeprecationWarning noise. Any failure in either phase must be fixed before done — no "pre-existing" exception without Tom's written OK.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) via `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All 6 MCP pre-work queries run — head `3131f106f1b9`, both tables absent, invoice/billing_mode/FK targets/customer triggers confirmed (discrepancies noted in Completion Summary)
- [ ] All mandatory source files read (including `api/schemas/schemas.py` + `seed_scenario_quote_to_cash.py`)
- [ ] **Task 1**: `PaymentSchedule` + `PaymentScheduleLine` models (StandardAuditMixin + explicit `tenant_id`); `Invoice.payment_schedule_line_id` added; `db_models_map.md` regenerated — both under DB Tables
- [ ] **Task 2**: Blank migration (down_revision `3131f106f1b9`), 3 groups, triggers mirror live `customer` DDL (audit fn schema-qualified), conditional CHECKs, unique indexes; triple-verify upgrade→downgrade→upgrade passes; `alembic current` shows new head
- [ ] **Task 3**: All `PaymentSchedule*` schemas added; `payment_schedule_line_id` on `InvoiceResponse`; Pydantic v2; money integer cents; `percent` Decimal
- [ ] **Task 4**: `payment_schedule_service.py` — resolve/reconcile/activate/generate; two-step circular-FK write; Idempotency-Key reuse; no float on money
- [ ] **Task 5**: `payment_schedules.py` router (9 endpoints + `/test` twins) registered in `app/main.py`; `require_permission` = invoices.create/view/update; draft-gate 409
- [ ] All DB-touching routes/`_impl()`/service fns are sync `def` (§21)
- [ ] `set_audit_context_sync()` at the start of every mutation endpoint
- [ ] All new errors follow RFC 7807 (404 not-found, 409 stale/re-invoice, 422 reconciliation)
- [ ] New test file(s) use `pytestmark` (domain_invoicing_billing + unit); `client` fixture; no module-level `TestClient`; `test_tenant`/`test_*` fixtures; assert-by-ID
- [ ] Seed: one active progress schedule (deposit + 2 draws) in `seed_scenario_quote_to_cash.py`, business-key lookup, idempotent; README §4 updated
- [ ] `schema_manager.py` used (path-based) for both new tables + `invoice.payment_schedule_line_id`
- [ ] `export_openapi_json.py` run — `openapi.json` + `openapi_schema_map.md` show `/payment-schedules`
- [ ] `generate_app_import_map.py tests > app_model_imports.md` run
- [ ] `ruff check . --fix && ruff format .` — zero remaining issues
- [ ] **Phase 1**: all unit tests pass
- [ ] **Phase 2**: full suite passes, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B
- [ ] Handoff performed (see below)

---

## Completion Summary

After all DoD items:
1. Add a **Completion Summary** to `pilot-launch-plan.md` Appendix B using the standard template (Completed / Mode / Baseline / Final / What Was Accomplished / Files Changed / Tests Added). Add a one-row entry to Appendix A and mark BILLING-B1 Part A ✅ in §2.0.
2. Update `README-seed-data.md` §4 with the new scenario rows (source-spec update rule).

```markdown
### BILLING-B1 (Part A — Python Engineer) — Payment Schedule Orchestration: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Migration**: <rev> — payment_schedule + payment_schedule_line + invoice.payment_schedule_line_id
**Alembic head**: <rev> (was 3131f106f1b9)
**Baseline**: X passed, Y failed
**Final**: X+N passed (+N new tests)

#### What Was Accomplished
- <bullets>

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
```

---

## After This Task — Next Step (HANDOFF to React Engineer)

BILLING-B1 is a **mixed batch — Part B (React) depends on this contract.** On completion:

1. Run `python export_openapi_json.py` (already in Phase 2) and confirm `/payment-schedules` endpoints + the `payment_schedule_line_id` field on `InvoiceResponse` appear in `openapi_schema_map.md`.
2. Commit all changes.
3. Notify the React Engineer that Part A is done — they run **`pnpm sync-api-types` first**, then implement the payment-schedule builder per `batch-billing-b1-react-engr-prompt.md`.
4. Contract summary for the handoff note: 9 endpoints under `/api/v1/payment-schedules`; `PaymentScheduleResponse` carries `lines[]` + `scheduled_total_cents` + `residual_cents`; each `PaymentScheduleLineResponse` carries `resolved_amount_cents`; generate-invoice returns a `billing_mode='progress'` invoice with `payment_schedule_line_id` set; activate 422s on residual ≠ 0; edit-after-activate + re-invoice both 409.
