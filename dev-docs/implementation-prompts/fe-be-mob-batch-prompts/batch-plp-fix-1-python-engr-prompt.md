# Implementation Prompt: PLP-FIX-1 — Quote Route De-Gate + Custom Invoice Line Items

**Mode**: Pilot Python Engineer
**Batch**: PLP-FIX-1
**Source plan**: `dev-docs/analysis/PLP-testing-bugs-2026-08-30.md` — Issues 1 & 2 (backend); Issues 3 & 4 are FE batches
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-1-design.md` (v1.1 — read it first)
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: FE-B29-1 (invoice-builder `line_items[]` wiring) — depends on this batch's OpenAPI regeneration

> **v1.1 (2026-08-30) — Option B pivot (Tom decision)**: The PRD states quotes are **unlimited on every plan** (`mvp-prd.md`). The 402 fix is therefore to **remove the phantom entitlement gate from the quotes route** — NOT to seed `quotes_per_month`. **There is no migration and no seed work in this batch.** If you already created `backend/migrations/versions/2026_08_30_1706-c482cdbaab36_plp_fix1_seed_quotes_per_month_feature.py` from v1.0 of this prompt, Task 1 starts by deleting it unrun. Tom's full gate audit additionally found one stale feature code (`sms_segments`) in the SMS rollover task — fixed in Task 2.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, and fixture rules
- **`dev-docs/pilot-operations.md`** — tier→plan→ppfv cascade, `block` vs `soft` enforcement. The billing logic is NOT inferrable from the schema alone.
- **`batch-plp-fix-1-design.md`** — v1.1; §G decisions and the §H gate audit are final — do not re-open them

Critical rules for this batch:

- **Rule 1 (verify, don't guess)**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2 (model map)**: After the `app/models/billing.py` change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py app > db_models_map.md`.
- **Rule 3 (OpenAPI)**: The `InvoiceCreate` request contract changes → run `python export_openapi_json.py`.
- **Rule 5 (no module-level TestClient)**: Always use the `client` fixture from `conftest.py`.
- **Rule 6 (`db.get()` banned)**: All lookups (customer, site, quote, job, `qco_line_type`) use tenant-scoped `select()` with explicit `WHERE` clauses.
- **Rule 7 (MCP read-only)**: `postgres-local` MCP is **read-only verification only**. All data changes go through application code.
- **Rule 8 (RFC 7807)**: Every new error response uses the Problem Details dict shape — never a plain string `detail`. Return **404** (not 403) for tenant-scoped misses.
- **Rule 9 (audit context)**: `create_invoice` already calls `set_audit_context_sync()` — keep it before the first write. Do not remove it during the rework.
- **Rule 11 (no "not my fault")**: Any test failure — even one that looks pre-existing — must be fixed before declaring done, or STOP and ask Tom. This specifically includes the two entitlement test files you are repointing in Task 3.
- **Rule 12 (sync-by-design, rules §21)**: All new helpers and routes are plain `def` on the sync `Session`. Never `async def` on DB-touching code.
- **Rule 13 (Pydantic v2, rules §22)**: `ConfigDict`, `@field_validator` / `@model_validator`, `.model_dump()` only. Money is **integer cents** — never a float.
- **Rule 16 (verify-before-write SQL)**: Query `information_schema.columns` for every touched table this session before writing SQL (see MCP pre-work).
- **Phantom-gate standing rule (design §H)**: a `feature_code=` wiring may only reference a feature that (a) appears in the PRD pricing model and (b) has seeded `product_feature` + ppfv rows. This batch removes the one wiring that violated (a) and fixes the one code reference that violated (b). Do not add any new `feature_code=` wiring in this batch.

> **Engineer safety net — independent column verification (MANDATORY)**: Before writing ANY SQL statement or SQLModel field reference in this batch, run the `information_schema.columns` query for **every table you will touch**. If any column name in this prompt does not match what MCP returns → use the MCP-returned name, not the prompt's name, and note the discrepancy in your Completion Summary.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either (a) confirm with Tom that it is a known, accepted failure, or (b) fix it before touching any batch files.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. If a query fails or returns an error → STOP and ask Tom. **`postgres-prod`** requires Tom's SSH tunnel — this batch does NOT use it.

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm the legit feature set (audit baseline) — exactly these 3, nothing else
SELECT code, is_active FROM public.product_feature ORDER BY code;
-- Expected: outbound_sms_segments, schedule_lanes, voice_ai_minutes (all active)
-- If quotes_per_month appears → the v1.0 migration WAS applied; tell Tom before proceeding

-- 2. Confirm no usage rows exist under the stale code (drives Task 2 safety)
SELECT product_feature_code, count(*) FROM public.usage_ledger
GROUP BY product_feature_code ORDER BY product_feature_code;
-- Expected: outbound_sms_segments + voice_ai_minutes only; zero sms_segments rows

-- 3. Confirm alembic head (the v1.0 migration must NOT be applied)
SELECT version_num FROM public.alembic_version;
-- Expected: c8d06a6ffdd2 (if it shows c482cdbaab36 → migration was applied; STOP and ask Tom)

-- 4. Confirm qco_line_type lookup rows (line-type resolution targets for Task 5)
SELECT id, code, name FROM public.qco_line_type ORDER BY code;
-- Expected: discount, labor, material, misc, note (5 rows)

-- 5. Confirm invoice_line.qco_line_type_id is NOT NULL in the live DB (drives Task 6)
SELECT column_name, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice_line'
  AND column_name IN ('qco_line_type_id', 'source_type', 'source_id', 'position');
-- Expected: qco_line_type_id is_nullable = NO

-- 6. Confirm invoice.customer_id / site_id are NOT NULL (drives standalone-mode validation)
SELECT column_name, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
  AND column_name IN ('customer_id', 'site_id', 'quote_id', 'job_id');
-- Expected: customer_id NO, site_id NO, quote_id YES, job_id YES
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
dev-docs/architecture-design/batch-designs/batch-plp-fix-1-design.md   ← v1.1; §G decisions + §H audit are final
dev-docs/analysis/PLP-testing-bugs-2026-08-30.md                       ← the bug report (Issues 1 & 2)
backend/api/routes/quotes.py                                           ← the create_quote decorator (line ~1400) + its docstring (402 references)
backend/core/permissions.py                                            ← require_permission Step 2 (feature_code mechanics, lines ~200–310)
backend/services/entitlement_service.py                                ← check_entitlement() + get_cached_entitlement()
backend/tasks/rollover_sms_quota_periods.py                            ← the stale sms_segments lines (~85, ~107) + _rollover_impl shape
backend/services/billing_rate_service.py                               ← resolve_overage_rate (docstring line ~43)
backend/api/routes/invoices.py                                         ← _create_invoice_impl (lines ~340–620) + create_invoice / create_invoice_test wrappers + _generate_invoice_number + _compute_due_at_from_payment_terms
backend/api/schemas/schemas.py                                         ← InvoiceCreate (line ~704) + InvoiceLineResponse + InvoiceResponse shapes
backend/app/models/billing.py                                          ← Invoice + InvoiceLine (line 312)
backend/tests/conftest.py                                              ← autouse fixtures (~440–480 incl. mock_entitlement_allowed + its comment at ~458) + test_customer/test_site/test_invoice_status fixtures
backend/tests/batch_1d/test_task_1d4_entitlement_enforcement.py        ← Task 3 repoint target (mock-based framework tests)
backend/tests/integration/test_entitlement_enforcement_e2e.py          ← Task 3 rewrite target (route-level e2e → service-level)
backend/tests/domains/subscriptions_usage/test_cb14_entitlement_scenarios.py   ← service-level entitlement test pattern (direct inserts + skip_mock_entitlement_allowed)
backend/tests/batch_b11/test_a65_sms_quota.py                          ← rollover task test pattern (Task 7b)
backend/tests/domains/invoicing_billing/                               ← list the folder; read one existing invoice-creation test file for fixtures/patterns
```

> **The `api/schemas/` layer is separate from `app/models/`**: `app/models/` contains SQLModel ORM classes; `api/schemas/` contains Pydantic request/response shapes. This batch changes BOTH: the `InvoiceCreate` Pydantic schema AND the `InvoiceLine` ORM model.

Also run these greps:

```bash
grep -rn "quotes_per_month" backend/ --include="*.py"        # every remaining reference after Task 1 (app code must be zero)
grep -rn '"sms_segments"' backend/ --include="*.py"          # app-code refs must be Stripe-namespace only after Task 2
grep -rn "InvoiceLine(" backend/ --include="*.py" -l         # every construction site (Task 6 model alignment)
grep -rn "_create_invoice_impl" backend/ --include="*.py" -l # every caller of the impl
```

---

## Background / Context

Tom hit two backend bugs testing the quote→job→invoice flow (full analysis in the bug report):

**Issue 1 — Quote creation returns 402 for every tenant.** `quotes.py` enforces `require_permission("quotes.create", feature_code="quotes_per_month")`, but `quotes_per_month` was never seeded — `check_entitlement()` finds no ppfv row → `feature_not_in_plan` → 402. Root cause: the feature code was invented as the *example* when the entitlement framework was built (Task 1-D-4) and wired into the real route, but **the PRD says quotes are unlimited on every plan** (`mvp-prd.md`). The fix (Tom's decision, Option B): **remove the gate** — an unlimited feature carries no entitlement check. The entitlement framework itself stays (it legitimately gates `schedule_lanes` and meters `voice_ai_minutes` / `outbound_sms_segments`).

**Audit finding (Tom mandate)** — one more phantom code exists: `rollover_sms_quota_periods.py` writes overage usage with the pre-SD-07 code `sms_segments`, but `product_feature` holds `outbound_sms_segments` (FK target) — the overage-write path FK-violates when it fires. Zero such rows exist (never succeeded); only the zero-phones path has test coverage.

**Issue 2 — Custom invoice line items can't be saved; standalone invoices are fully blocked.** `InvoiceCreate` accepts only `quote_id` XOR `job_id`; the frontend builder already sends `customer_id` + `site_id` (silently dropped) and collects custom lines it cannot send. Latent NOT NULL bug: the job→invoice path passes `qco_line_type_id=None` (`invoices.py`) into a NOT NULL column — the `InvoiceLine` model's `| None` is model↔DB drift. The DB is truth.

---

## Task 1 — De-Gate the Quotes Route (delete the v1.0 migration)

Per design §B.1 and §D.0.

1. **Delete the v1.0 migration unrun**:
   ```bash
   cd <repo>/backend
   source .venv/bin/activate
   alembic current   # MUST show c8d06a6ffdd2 — if it shows c482cdbaab36, run `alembic downgrade -1` first, then continue
   rm migrations/versions/2026_08_30_1706-c482cdbaab36_plp_fix1_seed_quotes_per_month_feature.py
   alembic current   # still c8d06a6ffdd2
   ```

2. **Remove the feature gate** in `backend/api/routes/quotes.py` (line ~1400):

   ```python
   # BEFORE
   current_user: AuthenticatedUser = Depends(
       require_permission("quotes.create", feature_code="quotes_per_month")
   ),

   # AFTER
   current_user: AuthenticatedUser = Depends(require_permission("quotes.create")),
   ```

   Update the endpoint docstring in the same function — delete the 402/`quotes_per_month` entitlement bullet and any `"error": "usage_limit_exceeded"` example tied to it. RBAC (`quotes.create`) is unchanged.

3. **Docstring hygiene** (no behavior change): the framework docstrings use `quotes_per_month` as their example — switch the example to a genuinely gated feature:
   - `backend/core/permissions.py` (~lines 223, 242–244): example `"quotes_per_month"` → `"schedule_lanes"`.
   - `backend/services/entitlement_service.py` (line ~87): `(e.g. "quotes_per_month")` → `(e.g. "schedule_lanes")`.

4. **Sweep**: `grep -rn "quotes_per_month" backend/ --include="*.py"` — after Task 3 completes, the only remaining references may be inside test files you deliberately repointed (Task 3) — app code must be **zero**.

Intermediate unit test run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` (the two entitlement test files will fail until Task 3 — expected; note it and proceed).

---

## Task 2 — Fix the Stale `sms_segments` Code in the SMS Rollover Task

Per design §B.2. In `backend/tasks/rollover_sms_quota_periods.py`:

1. Line ~85: `resolve_overage_rate(db, tenant_id, "sms_segments")` → `"outbound_sms_segments"`.
2. Line ~107: `UsageLedger(... product_feature_code="sms_segments", ...)` → `"outbound_sms_segments"`.
3. `backend/services/billing_rate_service.py` line ~43 docstring: `'sms_segments'` → `'outbound_sms_segments'`.
4. **Do NOT touch** `"event_name": "sms_segments"` in `backend/scripts/stripe_bootstrap.py` or the `event_name="sms_segments"` strings in the C-B4/C-B14 Stripe tests — that is the external Stripe Billing Meter identifier, a different namespace (design §G-13).
5. Sweep: `grep -rn '"sms_segments"' backend/ --include="*.py"` — remaining hits must be Stripe-namespace only (bootstrap + those test files).

Intermediate unit test run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 3 — Repoint the Entitlement Test Files

The framework tests used `quotes_per_month` as their example feature. Repoint them so framework coverage survives without the phantom gate (design §G-1/§H):

1. **`backend/tests/batch_1d/test_task_1d4_entitlement_enforcement.py`** — pure-mock unit tests of `require_permission` Step 2. Rename the example: `FEATURE_CODE = "quotes_per_month"` → `FEATURE_CODE = "synthetic_metered_feature"` (and update comments referencing the quotes route). No other logic changes — these tests mock `get_cached_entitlement` and test the checker mechanics, not any real feature.

2. **`backend/tests/integration/test_entitlement_enforcement_e2e.py`** — currently seeds `mvp_entitlement_test` plan + `quotes_per_month` + ppfv + usage, then POSTs to `/api/v1/quotes` expecting 402 over-limit. That route is now de-gated, so **rewrite at the service level** following the `test_cb14_entitlement_scenarios.py` pattern: keep the self-seeded synthetic plan/feature (rename the feature to `synthetic_metered_feature`; the test inserts its own `product_feature` + ppfv + `subscription_usage` rows), call `check_entitlement(tenant_id, "synthetic_metered_feature", db_session)` directly, and assert the full decision tree — within-limit allowed, at-limit blocked with `usage_limit_exceeded` + correct `limit`/`used`, no-subscription blocked, override paths. Keep `@pytest.mark.skip_mock_entitlement_allowed` where the real service must run.

3. **`backend/tests/conftest.py`** (~line 458) — the comment explaining `mock_entitlement_allowed` references the quotes endpoint wiring. Update it: the quotes endpoint no longer carries a feature gate (PLP-FIX-1); the autouse fixture remains for any future gated-endpoint tests.

Intermediate unit test run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` — must be green again now.

---

## Task 4 — `InvoiceCreate` Schema + `_create_invoice_impl` Rework

Per design §D.1–§D.7 and §F. All decisions below are final (design §G) — do not re-open them.

### 4a. New Pydantic schema in `api/schemas/schemas.py`

```python
class InvoiceLineItemCreate(BaseModel):
    """A custom (ad_hoc) invoice line supplied at creation time."""

    description: str
    quantity: Decimal = Decimal("1")
    unit: str | None = None
    unit_price_cents: int
    qco_line_type_code: str | None = None  # default 'misc' resolved in impl

    @field_validator("description")
    @classmethod
    def _description_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("description must be non-empty")
        if len(v) > 500:
            raise ValueError("description must be ≤ 500 characters")
        return v

    @field_validator("quantity")
    @classmethod
    def _quantity_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("quantity must be > 0")
        return v

    @field_validator("unit_price_cents")
    @classmethod
    def _price_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("unit_price_cents must be >= 0")
        return v
```

### 4b. Extend `InvoiceCreate`

Add three fields (keep everything else, including the existing `validate_billing_mode_progress_pct` validator):

```python
    customer_id: UUID | None = None  # PLP-FIX-1: standalone mode
    site_id: UUID | None = None      # PLP-FIX-1: standalone mode
    line_items: list[InvoiceLineItemCreate] | None = None  # PLP-FIX-1: custom ad_hoc lines
```

### 4c. Rework `_create_invoice_impl` — three-mode resolution

Replace the quote_id/job_id XOR block with mode resolution per design §D.3:

| Mode | Condition | Behavior |
|---|---|---|
| **Quote** | `quote_id` set; `job_id`, `customer_id`, `site_id` all unset | existing quote path |
| **Job** | `job_id` set; `quote_id`, `customer_id`, `site_id` all unset | existing job path (+ Task 4d line-type fix) |
| **Standalone** | `customer_id` + `site_id` set; `quote_id`/`job_id` unset; `line_items` non-empty | new path (below) |
| **Invalid** | anything else | `400` RFC 7807 |

Mode-conflict error (use this shape):

```python
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail={
        "type": "https://errors.pilotfortrades.com/invalid-mode",
        "title": "Invalid invoice source",
        "status": 400,
        "detail": (
            "Provide exactly one invoice source: quote_id, job_id, "
            "or customer_id+site_id with at least one line_items entry."
        ),
    },
)
```

**Standalone path**: validate customer and site with tenant-scoped selects (404 RFC 7807 if either missing — never 403). Site must belong to the customer → if `site.customer_id != create_req.customer_id` → 422 RFC 7807. Create the `Invoice` with `customer_id`/`site_id` from the request, `quote_id`/`job_id` NULL, totals computed from the custom lines.

### 4d. Job-path latent NOT NULL fix (same edit site)

The job path currently passes `qco_line_type_id=None` for time-entry and expense lines (lines ~559 and ~579) — a guaranteed `IntegrityError` on commit against the live DB. Fix:

- time-entry lines → `qco_line_type_id = _resolve_qco_line_type_id(db, "labor")`
- expense lines → `qco_line_type_id = _resolve_qco_line_type_id(db, "material")`

Look each id up **once per request** (not inside the loop).

### 4e. New private helpers (sync `def` — rules §21)

```python
def _resolve_qco_line_type_id(db: Session, code: str | None) -> uuid.UUID:
    """Resolve qco_line_type.code → id (default 'misc'). 404 RFC 7807 if unknown."""
    resolved = code or "misc"
    row = db.exec(
        select(QcoLineType).where(QcoLineType.code == resolved)
    ).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Line type not found",
                "status": 404,
                "detail": f"qco_line_type code '{resolved}' does not exist.",
            },
        )
    return row.id


def _persist_custom_lines(
    line_items: list[InvoiceLineItemCreate],
    invoice_id: uuid.UUID,
    start_position: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> int:
    """Insert ad_hoc InvoiceLine rows; returns the added subtotal_cents."""
```

Each custom line: `source_type="ad_hoc"`, `source_id=None`, `position = start_position + i`, `qco_line_type_id` from `_resolve_qco_line_type_id`, `subtotal_cents = total_cents = int(round(quantity * unit_price_cents))` (compute with `Decimal` — never float math on money), all tax fields None, `is_active=True`, `tenant_id` + `created_by` set. (Verify the `QcoLineType` model import name via `db_models_map.md` / grep before use — Rule 1.)

### 4f. Wire custom lines into all three modes

After source-derived lines (quote lines / time+expense lines / none), call `_persist_custom_lines(create_req.line_items or [], …)` with `start_position` continuing after the source lines, and add the returned cents into `invoice.subtotal_cents` / `total_cents` / `balance_due_cents`. Custom lines contribute **0** tax (`tax_cents` unchanged — design §G-5). Single transaction; keep the existing `try/except` shape and the existing `set_audit_context_sync()` + idempotency handling.

The `/api/v1/invoices/test` twin calls the same `_impl` — no separate change (verify).

Intermediate unit test run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 5 — Align `InvoiceLine.qco_line_type_id` Model With the Live DB

The model declares `qco_line_type_id: uuid.UUID | None = Field(default=None, …)` but the live column is NOT NULL (MCP query 5). The DB is truth. In `backend/app/models/billing.py` (line ~345):

```python
    qco_line_type_id: uuid.UUID = Field(foreign_key="qco_line_type.id", index=True)
```

Then:

1. `grep -rn "InvoiceLine(" backend/ --include="*.py"` — every construction site must pass a value. App code is only `invoices.py` (fixed in Task 4); fix any test constructions passing None or omitting the field.
2. Check the JSON schema blueprint for the same drift:

```bash
python schema_manager.py get --path tables.invoice_line.columns.qco_line_type_id
```

If the JSON says `"nullable": true`, correct it via `schema_manager.py set` (path-based only — never edit the JSON by hand; read `backend/README-schema_manager.md` first). If `schema_manager.py` errors → STOP and ask Tom.

3. Regenerate the model maps (both print to stdout — redirect; pass the dir arg):

```bash
python generate_db_model_map.py app > db_models_map.md
python generate_app_import_map.py tests > app_model_imports.md
grep "InvoiceLine" backend/db_models_map.md
```

---

## Task 6 — Seed Data Rollout

**N/A for this batch (Option B).** No DB data is added or modified (Architect rule §11.5 applies to data-changing batches). Nothing is seeded for `quotes_per_month` — seeding it would re-arm the phantom gate. No `seed_*.py` edits; `README-seed-data.md` §4 untouched.

---

## Task 7 — Tests

Per `backend/tests/README-adding-tests.md`. Every file: `pytestmark` with domain marker + `pytest.mark.unit`; `client` fixture; `test_tenant`/`test_user` fixtures; assert by inserted IDs, never row counts; `db_session` rollback is the cleanup mechanism.

### 7a. `backend/tests/domains/sales_quoting/test_plp_fix1_quote_create_no_gate.py`

`pytestmark = [pytest.mark.domain_sales_quoting, pytest.mark.unit]` (verify the exact marker name in `pytest.ini` / a neighbor file). The de-gate regression suite:

1. **Quote create succeeds with no entitlement backing** — with `@pytest.mark.skip_mock_entitlement_allowed` (the real entitlement service would run if consulted) and the test tenant having **no subscription and no ppfv rows** for any quote feature, POST `/api/v1/quotes` as `test_user` (`mock_cognito_jwt` fixture) → 201. Before this batch this returned 402 `feature_not_in_plan`.
2. **Entitlement service is never consulted** — patch `services.entitlement_service.get_cached_entitlement` (imported lazily inside `require_permission`, so patch at the service module) with a `Mock(side_effect=AssertionError("entitlement consulted"))`, POST `/api/v1/quotes` → 201 and the mock was never called.

### 7b. `backend/tests/domains/notifications_comms/test_plp_fix1_rollover_overage_code.py`

`pytestmark = [pytest.mark.domain_notifications_comms, pytest.mark.unit]` (verify marker name; follow `test_a65_sms_quota.py` fixture patterns for phone/quota setup). The stale-code regression:

1. **Overage write uses the live feature code** — set up a tenant with an active provisioned phone and a latest `sms_quota_period` row with `overage_segments > 0`; run `_rollover_impl`; assert the inserted `UsageLedger` row (filter by the id/FK you just created — never row counts) has `product_feature_code == "outbound_sms_segments"` and the insert did not raise (it would FK-violate under the old code).
2. If `resolve_overage_rate` is exercised in that path, assert it returns the seeded `outbound_sms_segments` overage price for the tenant's plan (5 cents on charter/starter/teams) rather than raising `BillingConfigError`.

### 7c. `backend/tests/domains/invoicing_billing/test_plp_fix1_custom_invoice_lines.py`

`pytestmark = [pytest.mark.domain_invoicing_billing, pytest.mark.unit]` (verify marker name). Use the `/api/v1/invoices/test` endpoint (unauthenticated, canonical test tenant) and existing fixtures (`test_customer`, `test_site`, `test_invoice_status`; create a job via `/api/v1/jobs/test` when job mode is needed — follow the existing invoicing test patterns you read in Pre-Work).

1. **Standalone happy path** — POST with `customer_id`, `site_id`, `line_items` (2 items, one with explicit `qco_line_type_code: "labor"`, one defaulting) → 201; response `subtotal_cents`/`total_cents`/`balance_due_cents` equal the expected sum; lines persisted with `source_type = "ad_hoc"`, correct positions, correct `qco_line_type_id` values (assert the default one equals the `misc` id from the DB).
2. **Standalone without `customer_id`** → 400 (RFC 7807 body: assert `status` == 400).
3. **Standalone with `line_items: []`** → 400.
4. **Standalone with cross-tenant customer** → 404 (use `tenant_a`/`tenant_b` fixtures for a foreign customer; never 403).
5. **Site not belonging to the customer** → 422.
6. **Job invoice with custom lines appended** — job with at least one time entry (follow existing job-invoice test patterns) + 1 custom line → 201; custom line's `position` continues after the source lines.
7. **Job-path line types (latent-bug regression)** — the time-entry line has the `labor` `qco_line_type_id`, the expense line has `material` (no NULLs anywhere in the response `lines`).
8. **Quote invoice with custom lines** — quote-sourced lines first, custom lines appended after (use `test_quote_version`-based patterns from existing invoice tests).
9. **`quote_id` + `customer_id` together** → 400 invalid-mode.
10. **Unknown `qco_line_type_code`** → 404.
11. **Negative `unit_price_cents` / zero `quantity`** → 422 (Pydantic validator).

If any existing invoice/job/quote test breaks because `InvoiceLine.qco_line_type_id` is now required by the model, fix that construction site (Task 5 grep) — Rule 11 applies.

---

## Verification Checkpoints

- **After Task 1**: `alembic current` = `c8d06a6ffdd2`; migration file gone; app-code `quotes_per_month` grep = zero (after Task 3 sweep).
- **After Task 2**: app-code `"sms_segments"` grep = Stripe-namespace only.
- **After Task 3**: `pytest -m unit` green again (repointed files pass).
- **After Tasks 4–5**: `pytest -m unit` green; grep shows no `InvoiceLine(` construction without a line type.
- **After Task 7**: new test files pass individually:
  ```bash
  python -m pytest tests/domains/sales_quoting/test_plp_fix1_quote_create_no_gate.py -v 2>&1 | tail -10
  python -m pytest tests/domains/notifications_comms/test_plp_fix1_rollover_overage_code.py -v 2>&1 | tail -10
  python -m pytest tests/domains/invoicing_billing/test_plp_fix1_custom_invoice_lines.py -v 2>&1 | tail -25
  ```

---

## Regenerate OpenAPI (handoff-critical)

After all tests pass (and after the ruff gate):

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify the new fields appear in the human-readable map:

```bash
grep -B 2 -A 12 "InvoiceLineItemCreate" backend/openapi_schema_map.md
grep -B 2 -A 8 "line_items" backend/openapi_schema_map.md | head -40
```

(The quotes de-gate produces no spec-visible change — 402 was never in the response model — but the regen is still required for `InvoiceCreate`.)

### Handoff Instructions (BE → FE)

`InvoiceCreate` gained `customer_id`, `site_id`, and `line_items[]` — the OpenAPI spec changed. After `export_openapi_json.py`:

1. **Commit `backend/openapi.json` + `backend/openapi_schema_map.md`** with the batch.
2. State explicitly in your Completion Summary: **"OpenAPI updated — FE-B29-1 may run `pnpm sync-api-types`."** The React Engineer batch that wires the invoice builder's custom-line UI (resolving the TODO at `InvoiceBuilderPage.tsx`) runs `pnpm sync-api-types` as its first Pre-Work step against your regenerated spec.

### Deploy note (for Tom — include in Completion Summary)

Code-only batch: no migration, no seed converge, no Redis action. Stale `entitlement:{tenant}:quotes_per_month` cache keys (if any) expire unread within their 300 s TTL once the route stops consulting the service.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate (rules §23) — CHANGED FILES ONLY
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite — vendor/live-service suites deselected (Tom's standing instruction 2026-08-16)
python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Batch-specific spot checks
python -m pytest tests/domains/sales_quoting/test_plp_fix1_quote_create_no_gate.py tests/domains/notifications_comms/test_plp_fix1_rollover_overage_code.py tests/domains/invoicing_billing/test_plp_fix1_custom_invoice_lines.py -v 2>&1 | tail -30
grep -B 2 -A 12 "InvoiceLineItemCreate" backend/openapi_schema_map.md
grep -rn "quotes_per_month" backend/ --include="*.py" | grep -v "tests/" || echo "app code clean"

echo "=== PLP-FIX-1 FINAL VERIFICATION COMPLETE ==="
```

> **Vendor-suite inclusion call**: this batch does NOT modify Telnyx, Stripe, SendGrid, or Redis-covered code (the rollover task's * Celery/DB path changes by two string constants — no vendor client code). The vendor marker suites are **not required** for sign-off.

> **Warning-clean is part of done.** `ruff` must report no remaining issues **in your changed files** (no unjustified `# noqa`), and the pytest run must be free of `DeprecationWarning` noise. Do not run `ruff check .` against the whole codebase.

> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify a root cause → STOP and ask Tom.

---

## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 6 MCP pre-work queries run — 3 legit features confirmed; zero `sms_segments` usage rows; alembic head `c8d06a6ffdd2` confirmed (v1.0 migration NOT applied); `qco_line_type` 5 rows; `invoice_line.qco_line_type_id` NOT NULL; `invoice.customer_id`/`site_id` NOT NULL
- [ ] All mandatory source files read before writing any code (including `api/schemas/schemas.py`)
- [ ] Task 1: v1.0 migration file deleted unrun (downgrade-first if needed); `quotes.py` de-gated + docstring updated; `permissions.py` / `entitlement_service.py` docstring examples → `schedule_lanes`; app-code `quotes_per_month` grep = zero
- [ ] Task 2: both `sms_segments` lines in `rollover_sms_quota_periods.py` → `outbound_sms_segments`; `billing_rate_service.py` docstring corrected; remaining `"sms_segments"` grep = Stripe-namespace only
- [ ] Task 3: 1d4 mock tests repointed to `synthetic_metered_feature`; e2e rewritten at service level; `conftest.py` comment updated; `pytest -m unit` green
- [ ] Task 4: `InvoiceLineItemCreate` added; `InvoiceCreate` extended; three-mode validation in `_create_invoice_impl`; standalone path persists customer/site-validated invoices; custom lines persist as `ad_hoc` with resolved line types; totals include custom-line cents; job-path `labor`/`material` fix applied
- [ ] Task 5: `InvoiceLine.qco_line_type_id` model aligned to NOT NULL; all `InvoiceLine(` construction sites pass a value; `schema_manager.py get` check done (JSON corrected if drifted)
- [ ] Task 6: Seed Data Rollout confirmed N/A (no `seed_*.py` edits; README §4 untouched)
- [ ] All DB-touching routes/`_impl()`/helpers are sync `def` — no `async def` on the blocking `Session` (rules §21)
- [ ] Only Pydantic v2 idioms used; every route keeps `response_model`; money is integer cents computed via `Decimal` (rules §22)
- [ ] `set_audit_context_sync()` still called before the first write in the create endpoint (rules §9)
- [ ] All new API errors follow RFC 7807 Problem Details format; 404 (not 403) for tenant-scoped misses
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant`/`test_user` and domain fixtures (no hardcoded UUIDs)
- [ ] `@pytest.mark.skip_mock_entitlement_allowed` applied where the real entitlement service must run (7a-1, 7b, repointed e2e)
- [ ] `python generate_db_model_map.py app > db_models_map.md` and `python generate_app_import_map.py tests > app_model_imports.md` run
- [ ] `python export_openapi_json.py` run — `InvoiceLineItemCreate` + `line_items` visible in `openapi_schema_map.md`
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues in those files (including pre-existing), no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — zero failures, warning-clean; vendor marker suites confirmed not required (stated above)
- [ ] Final test count (before → after) documented
- [ ] Deploy note (code-only; no migration/seed/Redis steps) included in the Completion Summary
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)

---

## Completion Summary

After all Definition of Done items are complete, fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below. This batch has no source-spec updates beyond the prompt doc.

```markdown
### PLP-FIX-1 — Quote Route De-Gate + Custom Invoice Line Items: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Quotes route de-gated (Option B); phantom quotes_per_month wiring removed; v1.0 migration deleted unrun]
- [Stale sms_segments → outbound_sms_segments in SMS rollover task; audit §H closed]
- [InvoiceCreate line_items[] + standalone mode shipped; job-path NOT NULL latent bug fixed]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/path/to/file.py` | Created / Updated / Deleted — [what changed] |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/...` | `...` | N | ✅ |

#### Handoff

- OpenAPI regenerated: yes — FE-B29-1 may run `pnpm sync-api-types`
- Deploy note: code-only; no migration/seed/Redis steps
```

---

## After This Task — Next Step

1. Tell Tom the batch is complete (with the Completion Summary) — he deploys.
2. The follow-on **React Engineer batch (FE-B29-1)** wires the invoice builder's custom-line UI to `line_items[]` — its first Pre-Work step is `pnpm sync-api-types` against your regenerated `openapi.json`.
3. Bug-report Issues 3 (missing `/jobs/new` route) and 4 (job-create "Network error" diagnostic) are separate React Engineer batches authored from the same bug report.

---

## Appendix — Completion Summary

### PLP-FIX-1 — Quote Route De-Gate + Custom Invoice Line Items: Completion Summary

**Completed**: 2026-08-30
**Mode**: Pilot Python Engineer
**Baseline**: 4729 passed, 1 skipped, 0 failed
**Final**: 4744 passed, 1 skipped, 0 failed (+15 new tests)

#### What Was Accomplished

- **Quotes route de-gated (Option B)**: removed `feature_code="quotes_per_month"` from `require_permission("quotes.create")` in `quotes.py`. The phantom gate (never seeded, contradicts PRD §3.11 "unlimited quotes on every plan") caused HTTP 402 for every tenant. The v1.0 migration file was deleted unrun (alembic head remains `c8d06a6ffdd2`).
- **Stale `sms_segments` code fixed**: `rollover_sms_quota_periods.py` overage-write path changed from pre-SD-07 `sms_segments` → `outbound_sms_segments` (the FK-correct code). Also fixed a latent `idempotency_key` NOT NULL bug in the `UsageLedger` insert (the stale code had masked it via FK violation first). Audit §H closed.
- **InvoiceCreate `line_items[]` + standalone mode shipped**: new `InvoiceLineItemCreate` Pydantic schema + three-mode resolution (quote / job / standalone) in `_create_invoice_impl`. Custom lines persist as `ad_hoc` with resolved `qco_line_type_id`. Job-path latent NOT NULL bug fixed (`qco_line_type_id=None` → `labor`/`material`).
- **Model↔DB drift closed**: `InvoiceLine.qco_line_type_id` aligned from `uuid.UUID | None` to `uuid.UUID` (NOT NULL) to match the live DB.
- **Docstring hygiene**: `permissions.py` + `entitlement_service.py` examples switched from `quotes_per_month` → `schedule_lanes`; `billing_rate_service.py` docstring `sms_segments` → `outbound_sms_segments`.
- **Entitlement test files repointed**: 1d4 mock tests → `synthetic_metered_feature`; e2e rewritten at service level (7 decision-tree scenarios); `conftest.py` comment updated.

#### Root Cause Summary

Issue 1: `quotes_per_month` was invented as the example feature code when the entitlement framework was built (Task 1-D-4) and wired into the real quotes route, but the PRD says quotes are unlimited on every plan. The feature was never seeded → `check_entitlement()` returned `feature_not_in_plan` → 402 for all tenants. Fix: remove the gate (Option B), not seed it.

Issue 2: `InvoiceCreate` had no `line_items[]` field and enforced a `quote_id`/`job_id` XOR, blocking standalone invoices and custom lines. The job path also passed `qco_line_type_id=None` into a NOT NULL column (latent IntegrityError). Fix: three-mode resolution + custom-line persistence + line-type fix.

Audit finding: `rollover_sms_quota_periods.py` wrote `product_feature_code='sms_segments'` (pre-SD-07 code) into `usage_ledger` — FK-violated because `product_feature` holds `outbound_sms_segments`. Zero such rows existed (path never succeeded). Fix: corrected the code + added the missing `idempotency_key`.

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/2026_08_30_1706-c482cdbaab36_plp_fix1_seed_quotes_per_month_feature.py` | **Deleted** — v1.0 migration, deleted unrun (Option B pivot) |
| `backend/api/routes/quotes.py` | Updated — de-gated `create_quote` (removed `feature_code`); docstring updated; `PUBLIC_LINK_USER_ID` → lowercase (N806 fix) |
| `backend/core/permissions.py` | Updated — docstring example `quotes_per_month` → `schedule_lanes` |
| `backend/services/entitlement_service.py` | Updated — docstring example `quotes_per_month` → `schedule_lanes` |
| `backend/tasks/rollover_sms_quota_periods.py` | Updated — `sms_segments` → `outbound_sms_segments` (2 sites); added `idempotency_key` to `UsageLedger` insert; unicode fixes |
| `backend/services/billing_rate_service.py` | Updated — docstring `sms_segments` → `outbound_sms_segments` |
| `backend/api/schemas/schemas.py` | Updated — added `InvoiceLineItemCreate`; extended `InvoiceCreate` with `customer_id`/`site_id`/`line_items`; unicode fixes |
| `backend/api/routes/invoices.py` | Updated — three-mode `_create_invoice_impl` rework; `_resolve_qco_line_type_id` + `_persist_custom_lines` helpers; job-path NOT NULL fix; imports (`QcoLineType`, `Site`, `InvoiceLineItemCreate`, `Decimal`) |
| `backend/app/models/billing.py` | Updated — `InvoiceLine.qco_line_type_id` aligned to NOT NULL |
| `backend/tests/batch_1d/test_task_1d4_entitlement_enforcement.py` | Updated — `FEATURE_CODE` → `synthetic_metered_feature`; `require_permission` calls repointed |
| `backend/tests/integration/test_entitlement_enforcement_e2e.py` | **Rewritten** — route-level 402 test → service-level `check_entitlement()` decision-tree test (7 scenarios) |
| `backend/tests/conftest.py` | Updated — `mock_entitlement_allowed` comment updated (quotes route de-gated) |
| `backend/tests/domains/platform_infrastructure/test_ui_fix_1c_pagination.py` | Updated — invoice creation payload fixed (quote_id-only, no customer_id+site_id) |
| `backend/tests/domains/sales_quoting/test_plp_fix1_quote_create_no_gate.py` | **Created** — de-gate regression (2 tests) |
| `backend/tests/domains/notifications_comms/test_plp_fix1_rollover_overage_code.py` | **Created** — rollover overage-code regression (1 test) |
| `backend/tests/domains/invoicing_billing/test_plp_fix1_custom_invoice_lines.py` | **Created** — custom invoice lines suite (12 tests) |
| `backend/db_models_map.md` | Regenerated |
| `backend/app_model_imports.md` | Regenerated |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/sales_quoting/test_plp_fix1_quote_create_no_gate.py` | `domain_sales_quoting` | 2 | ✅ |
| `tests/domains/notifications_comms/test_plp_fix1_rollover_overage_code.py` | `domain_notifications_comms` | 1 | ✅ |
| `tests/domains/invoicing_billing/test_plp_fix1_custom_invoice_lines.py` | `domain_invoicing_billing` | 12 | ✅ |

#### Handoff

- **OpenAPI regenerated: yes — FE-B29-1 may run `pnpm sync-api-types`.** `InvoiceCreate` gained `customer_id`, `site_id`, and `line_items[]` (visible in `openapi_schema_map.md`).
- **Deploy note**: code-only batch — no migration, no seed converge, no Redis action. Stale `entitlement:{tenant}:quotes_per_month` cache keys (if any) expire unread within their 300 s TTL once the route stops consulting the entitlement service.
- **Vendor suites**: not required — this batch does not modify Telnyx, Stripe, SendGrid, or Redis client code (the rollover task's Celery/DB path changed by two string constants + one `idempotency_key` field — no vendor client code).
