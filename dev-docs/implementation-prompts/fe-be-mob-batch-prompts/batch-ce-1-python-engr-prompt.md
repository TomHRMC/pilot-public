# Implementation Prompt: CE-1 (Part A) — Invoice Sign-Off Capture + Overpayment Variance Resolution (Backend)

**Mode**: Pilot Python Engineer
**Batch**: CE-1 — Part A (Backend)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 CE-1 (Beta Execution Order 1)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ce-1-design.md` — **read §0 (scope reconciliation), §B (DDL), §D (endpoints), §G (resolved decisions R1–R10) before any code**
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/`)
**Frontend companions**: `batch-ce-1-react-native-engr-prompt.md` (mobile capture) + CE-1 web React prompt (invoice detail display + overpayment banner) — **both are blocked until this batch merges and `pnpm sync-api-types` runs** (Rule 9.3 handoff, see final section)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-ce-1-design.md`** — the binding design. If anything in this prompt conflicts with it, the design doc wins — note the conflict in your Completion Summary.

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py app > db_models_map.md`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 4**: All Alembic migrations must be **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format. Plain-string `detail` is banned. Return **404 (not 403)** when a tenant-scoped record is not found (prevents UUID enumeration).
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before the first `db.add()`/`db.commit()`. Without it `actor_id` is NULL in `audit_log`.
- **Rule 12 (sync-by-design, §21)**: Every DB-touching route and `_impl()` is a plain `def`. **Never** `async def` a handler that touches the sync `Session` — psycopg2 on the event loop stalls all requests.
- **Rule 13 (Pydantic v2, §22)**: `ConfigDict` / `@field_validator` / `.model_dump()` only; every route has `response_model`; money is always integer cents.
- **Rule 14 (Ruff, §23)**: Phase 2 lint runs against **changed files only**; fix ALL errors in those files including pre-existing ones.
- **Rule 15 (audit mixins, §24)**: `InvoiceSignoff` inherits `StandardAuditMixin` — never hand-declare `created_at`/`updated_at`; add `tenant_id` explicitly. The migration DDL must carry **all four** audit columns (`created_at`, `updated_at`, `created_by`, `updated_by`).
- **Rule 16 (verify, don't assume, §25)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.
- **Idempotency (arch §7.6)**: `POST /invoices/{invoice_id}/signoff` is executed **offline-queued by the mobile app** — it MUST accept the `Idempotency-Key` header and be replay-safe via the `uq_invoice_signoff_tenant_idempotency` unique index. Follow the established pattern in `utils/idempotency.py` + `_create_invoice_impl`.

**Payment refund model (SD-2 permanent design):**
Refunds = new negative-amount payment row (`amount_cents < 0`, `status = refunded`). The `payment.refunded_amount_cents` / `payment.refunded_at` columns were deliberately dropped by migration `44b8d8f15789`. Do NOT add them back. Do NOT query for them in MCP checks. This batch's `resolve-variance` endpoint is **record-keeping only** — it never creates payment rows and never calls Stripe (design §G-R6).

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either (a) confirm with Tom that this is a known, accepted failure, or (b) fix it before touching any batch files. You may NOT start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries (`postgres-local`)

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: `postgres-local` is **read-only verification only** — never INSERT/UPDATE/DELETE. All data changes go through migrations, seed scripts, or application code. On any error → STOP and ask Tom. (`postgres-prod` exists but requires Tom's SSH tunnel — this batch does not use it.)

```sql
-- 1. Confirm the new table does NOT exist (greenfield — anything returned = STOP)
SELECT tablename FROM pg_tables
WHERE schemaname IN ('public','audit') AND tablename ILIKE '%signoff%';

-- 2. payment columns — confirm the four variance columns exist and the four NEW columns do NOT
--    (expect: amount_variance_cents, customer_payment_comment, stripe_payment_intent_id, paid_via present;
--     expect ABSENT: variance_resolution, variance_resolution_note, variance_resolved_at, variance_resolved_by_user_id)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment' ORDER BY ordinal_position;

-- 3. invoice columns used by the endpoints (invoice_number, total_cents, balance_due_cents,
--    currency, status_id, job_id, customer_id, terms_and_conditions, is_active)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice' ORDER BY ordinal_position;

-- 4. invoice_status codes — signable statuses resolve by CODE at runtime; never hardcode these UUIDs
SELECT code, id, is_terminal FROM public.invoice_status ORDER BY code;
--    (expect: draft[default], issued, partial, paid[terminal], void[terminal], writeoff[terminal])

-- 5. job + customer columns for the signoff-context response (customer display-name expression)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name IN ('job','customer') ORDER BY table_name, ordinal_position;

-- 6. Current alembic head (your migration chains off this)
SELECT version_num FROM public.alembic_version;
```

> **Engineer safety net (MANDATORY)**: Before writing ANY SQL/SQLModel field reference, re-run the `information_schema.columns` query for the table you are about to touch. If any column name in this prompt differs from MCP → use the MCP-returned name and note the discrepancy in your Completion Summary. Do NOT ask for a prompt re-issue — correct inline and proceed.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
dev-docs/architecture-design/batch-designs/batch-ce-1-design.md   ← binding design (§B DDL, §D contracts, §G decisions)
backend/app/models/billing.py                                     ← Invoice (153–309), Payment (443–517); where InvoiceSignoff lands
backend/app/models/mixins.py                                      ← StandardAuditMixin — what it provides (all 4 audit cols) and what it doesn't (tenant_id)
backend/api/routes/invoices.py                                    ← house `_impl` + authenticated/`/test`-twin pattern; _create_invoice_impl idempotency; _record_payment_impl
backend/api/routes/jobs.py                                        ← require_permission("jobs.update"/"jobs.view") usage; how job detail composes its customer display name (mirror that exact expression in D.1)
backend/api/schemas/schemas.py                                    ← PaymentResponse (773–785 — you extend it), InvoiceResponse
backend/services/s3_service.py                                    ← module contract: "Do not call boto3 S3 directly from route or task code"; bucket = settings.AWS_S3_PHOTOS_BUCKET_NAME; _s3_client() mock seam
backend/utils/idempotency.py                                      ← established Idempotency-Key handling
backend/core/test_context.py                                      ← TestUserContext / get_test_context for /test twins
backend/tests/conftest.py                                         ← available fixtures (do not re-declare)
backend/migrations/versions/<newest file>                         ← migration pattern reference (find via: ls -t backend/migrations/versions/*.py | head -3)
backend/README-seed-data.md                                       ← §3 (Group A–D), §6 (run order), §7 (DELETE safety rule) — required before touching seed scripts
```

Also run these greps to locate related code:

```bash
grep -rn "amount_variance_cents" backend/ --include="*.py" -l          # every consumer of the variance field
grep -rn "_s3_client\|moto" backend/tests --include="*.py" -l          # established S3 mock pattern (photo tests)
grep -rn "set_audit_context_sync" backend/api/routes/invoices.py       # audit-context call sites
grep -rn "Idempotency" backend/api/routes/invoices.py                  # header handling precedent
```

---

## Background / Context

CE-1 delivers two customer-facing money moments (design §0 reconciles the half-stale plan card — the public-page "Pay remaining" CTA is **already built**; do not touch `public_invoices.py`):

1. **Invoice sign-off capture** (greenfield): a field tech captures the customer's signature on a mobile canvas at job completion, bound to the job's invoice via `invoice.job_id`. Transport is **base64-PNG inline in the request body** (offline-first, design §G-R5) — the server decodes, validates, uploads to S3, and writes the row. Re-capture **supersedes** the prior row (§G-R4). Mobile is offline-queued → the endpoint must be replay-safe.
2. **Overpayment variance resolution** (PRD §3.6 line 381 / arch §18.5 line 4115): overpaid payments (`amount_variance_cents > 0`) must be reviewable in the web UI. This batch adds the resolution columns + endpoint. It is **record-keeping only** — no Stripe refund execution, no QB credit memo (§G-R6), no new payment rows (SD-2 refund model is untouched).

**RBAC decisions (design §G-R3 — do not "fix" these)**: capture rides `jobs.update`, context rides `jobs.view` (technicians hold these; they are excluded from all `invoices.*` per design-system §8). Web display rides `invoices.view`; variance resolution rides `invoices.update`.

---

## Task 1 — Alembic Migration: `invoice_signoff` table + `payment` variance-resolution columns

**Create a blank migration** chained off the current head (MCP query 6):

```bash
cd <repo>/backend && source .venv/bin/activate
alembic revision -m "ce1_invoice_signoff_and_payment_variance_resolution"
```

Implement `upgrade()` with raw `op.execute()` using **exactly** this DDL (design §B — all names MCP-verified 2026-08-12; re-verify per the safety-net rule):

```sql
CREATE TABLE public.invoice_signoff (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             UUID NOT NULL REFERENCES public.tenant (id),
    invoice_id            UUID NOT NULL REFERENCES public.invoice (id),
    signed_by_name        VARCHAR(200) NOT NULL,
    signature_object_key  VARCHAR(500) NOT NULL,
    terms_acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
    signed_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    client_capture_at     TIMESTAMPTZ NULL,
    captured_by_user_id   UUID NOT NULL REFERENCES public."user" (id),
    superseded_at         TIMESTAMPTZ NULL,
    idempotency_key       VARCHAR(100) NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by            UUID NULL,
    updated_by            UUID NULL,
    CONSTRAINT ck_invoice_signoff_terms CHECK (terms_acknowledged = TRUE)
);

CREATE UNIQUE INDEX uq_invoice_signoff_one_active
    ON public.invoice_signoff (invoice_id) WHERE superseded_at IS NULL;

CREATE INDEX ix_invoice_signoff_tenant_invoice
    ON public.invoice_signoff (tenant_id, invoice_id);

CREATE UNIQUE INDEX uq_invoice_signoff_tenant_idempotency
    ON public.invoice_signoff (tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

ALTER TABLE public.payment ADD COLUMN variance_resolution VARCHAR(20) NULL;
ALTER TABLE public.payment ADD COLUMN variance_resolution_note TEXT NULL;
ALTER TABLE public.payment ADD COLUMN variance_resolved_at TIMESTAMPTZ NULL;
ALTER TABLE public.payment ADD COLUMN variance_resolved_by_user_id UUID NULL REFERENCES public."user" (id);
ALTER TABLE public.payment ADD CONSTRAINT ck_payment_variance_resolution
    CHECK (variance_resolution IS NULL OR variance_resolution IN ('credit', 'refund_offline', 'writeoff'));
```

Rules:
- Start `upgrade()` with `op.execute("SET LOCAL session_replication_role = 'replica';")` only if you also write data (you do not here — schema only; follow the newest migration's header convention regardless).
- `updated_at` trigger/app-managed handling: copy the convention from the newest migration file exactly.
- **Implement `downgrade()`** — exact reverse (drop constraint + 4 payment columns; drop 3 indexes; drop table).
- No 3-part NOT NULL dance — all new `payment` columns are nullable; the new table's NOT NULLs are safe by construction (design §B).
- Test the full cycle: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` → `alembic current` shows your revision.

Intermediate check: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 2 — SQLModel: `InvoiceSignoff` + `Payment` field additions

In `backend/app/models/billing.py`:

```python
class InvoiceSignoff(StandardAuditMixin, SQLModel, table=True):
    """CE-1 — Customer signature captured at invoice sign-off (mobile, offline-first).

    One active row per invoice (partial unique index uq_invoice_signoff_one_active);
    re-capture supersedes the prior row. The signature PNG lives in S3 at
    signature_object_key; the row carries metadata only.
    """

    __tablename__ = "invoice_signoff"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    invoice_id: uuid.UUID = Field(foreign_key="invoice.id", nullable=False)
    signed_by_name: str = Field(max_length=200, nullable=False)
    signature_object_key: str = Field(max_length=500, nullable=False)
    terms_acknowledged: bool = Field(default=False, nullable=False)
    signed_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    client_capture_at: AwareDatetime | None = Field(default=None, nullable=True)
    captured_by_user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    superseded_at: AwareDatetime | None = Field(default=None, nullable=True)
    idempotency_key: str | None = Field(default=None, max_length=100, nullable=True)
```

Match the file's existing conventions exactly (sa_column for FKs/indexes where neighbors use them, `AwareDatetime` import, UTC-aware defaults — copy from `Invoice`/`Payment` in the same file; the model above is a sketch, not gospel — neighbor conventions win). Add the four `Payment` fields mirroring the DDL (`variance_resolution: str | None` max_length=20, `variance_resolution_note: str | None`, `variance_resolved_at: AwareDatetime | None`, `variance_resolved_by_user_id: uuid.UUID | None` FK `user.id`).

Register the model in `app/models/__init__.py` (F401 on your line is expected — suppressed by `per-file-ignores`; do NOT add `# noqa`).

Regenerate: `python generate_db_model_map.py app > db_models_map.md` → verify `grep "InvoiceSignoff" db_models_map.md`.

---

## Task 3 — `s3_service.py` helpers

Append to `backend/services/s3_service.py` (the module contract bans direct boto3 S3 calls from routes — all S3 goes through here):

```python
def build_signature_object_key(tenant_id: str, invoice_id: str, signoff_id: str) -> str:
    """Return 'signatures/{tenant_id}/{invoice_id}/{signoff_id}.png' (cf. build_photo_object_key)."""

def put_signature_object(object_key: str, png_bytes: bytes) -> None:
    """put_object to settings.AWS_S3_PHOTOS_BUCKET_NAME, ContentType='image/png'.
    Raises ClientError on failure (caller maps to 502 RFC 7807)."""

def generate_presigned_get_url(object_key: str, expires_in: int = 3600) -> str:
    """Presigned GET against the photos bucket (precedent: user_profile.py get_object call)."""
```

Use `_s3_client()` and `settings.AWS_S3_PHOTOS_BUCKET_NAME` — the same bucket constant as `create_multipart_upload()`.

---

## Task 4 — Pydantic schemas

New file `backend/api/schemas/invoice_signoff.py` (Pydantic v2 only):

- `DEFAULT_SIGNOFF_TERMS: str` — module constant; concise work-acceptance + payment-acknowledgement sentence used when `invoice.terms_and_conditions` is NULL (design §D.1).
- `InvoiceSignoffCreateRequest` — `signed_by_name: str` (Field min_length=1, max_length=200), `terms_acknowledged: Literal[True]` (rejects false at the schema layer), `signature_png_base64: str` (min_length=1), `client_capture_at: datetime | None = None`.
- `InvoiceSignoffSummary` — `signoff_id: UUID`, `signed_by_name: str`, `signed_at: datetime`.
- `InvoiceSignoffResponse` — summary fields + `invoice_id`, `client_capture_at: datetime | None`, `captured_by_user_id: UUID`, `signature_url: str` (presigned GET, 1h TTL).
- `SignoffContextInvoice` — `invoice_id`, `invoice_number: str`, `status: str` (the code), `total_cents: int`, `balance_due_cents: int`, `currency: str`, `terms_text: str`, `active_signoff: InvoiceSignoffSummary | None`.
- `SignoffContextResponse` — `job_id: UUID`, `customer_display_name: str`, `invoices: list[SignoffContextInvoice]`.

In `backend/api/schemas/schemas.py`: extend `PaymentResponse` (773–785) additively — `variance_resolution: str | None = None`, `variance_resolution_note: str | None = None`, `variance_resolved_at: datetime | None = None`, `variance_resolved_by_user_id: UUID | None = None`. Add `ResolveVarianceRequest` beside it — `resolution: Literal["credit", "refund_offline", "writeoff"]`, `note: str | None = Field(default=None, max_length=1000)`.

Check the grepped `amount_variance_cents` consumers: if a separate payment-list/payment-detail schema feeds the invoice-detail payment history, extend it identically so the web banner can read resolution state (design §I Part C).

---

## Task 5 — Sign-off endpoints (D.1–D.3) + `/test` twins

Follow the house `_impl(user_context: AuthenticatedUser | TestUserContext)` pattern from `invoices.py` exactly. All DB-touching functions are sync `def`. All mutations call `set_audit_context_sync()` first. All fetches are tenant-scoped `select()` (no `db.get()`). RFC 7807 for every error; 404-not-403 on tenant-scoped miss.

### D.1 — `GET /api/v1/jobs/{job_id}/signoff-context` → add to `jobs.py`

- Auth: `require_permission("jobs.view")`.
- Tenant-scoped job fetch (404 on miss). Customer display name: **mirror the exact expression the job-detail endpoint already uses** (from your jobs.py read — do not invent a new name composition).
- Signable invoices: `invoice.job_id == job_id`, `is_active.is_(True)`, status code IN `('issued','partial')` — resolve `status_id` by code from `invoice_status` at query time (**never hardcode the UUIDs** from MCP query 4). Order newest first (`created_at DESC`).
- Per invoice: `terms_text = invoice.terms_and_conditions or DEFAULT_SIGNOFF_TERMS`; `active_signoff` = latest row `WHERE superseded_at IS NULL` (or None).
- `/test` twin via `get_test_context`.

### D.2 — `POST /api/v1/invoices/{invoice_id}/signoff` → add to `invoices.py`

- Auth: `require_permission("jobs.update")` (deliberate — design §G-R3).
- `Idempotency-Key` header required (missing → 400 RFC 7807), handled per `utils/idempotency.py` precedent; DB backstop is `uq_invoice_signoff_tenant_idempotency` — on integrity-conflict replay, return the **existing** row with 200 (§15.4 replay semantics).
- Server flow (single transaction; S3 put **before** commit):
  1. Tenant-scoped invoice fetch → 404.
  2. Status guard: invoice status code must be `issued`/`partial` → else 422 (`https://errors.pilotfortrades.com/validation`, detail names the current status).
  3. `base64.b64decode(..., validate=True)` → must start with PNG magic bytes `\x89PNG\r\n\x1a\n` and decoded size ≤ 2 MB → else 422.
  4. `signoff_id = uuid4()`; `object_key = build_signature_object_key(...)`; `put_signature_object(object_key, png_bytes)` → on `ClientError`: rollback, raise 502 (`title: "Signature storage unavailable"`).
  5. Supersede: `UPDATE invoice_signoff SET superseded_at = now() WHERE invoice_id = :iid AND tenant_id = :tid AND superseded_at IS NULL`.
  6. Insert row (`idempotency_key` from header, `signed_at = now()`, `client_capture_at` from body, `captured_by_user_id = user_context.id`).
  7. On `uq_invoice_signoff_one_active` race → 409 RFC 7807 (§16.4 409-and-refresh; client refetches context).
- Response 200 `InvoiceSignoffResponse` with fresh `generate_presigned_get_url(object_key)`.
- `/test` twin via `get_test_context`. S3 in tests: mock at `_s3_client` per the established photo-test pattern (from your grep) — never hit real S3.

### D.3 — `GET /api/v1/invoices/{invoice_id}/signoff` → add to `invoices.py`

- Auth: `require_permission("invoices.view")`.
- Latest active signoff or `{"signoff": null}`; include `superseded_count` (count of superseded rows for the invoice) and a fresh presigned `signature_url` when present.
- `/test` twin.

Intermediate check: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 6 — Variance-resolution endpoint (D.4) + `/test` twin

`POST /api/v1/payments/{payment_id}/resolve-variance` → add to `invoices.py` (payments live in this file — see `_record_payment_impl`).

- Auth: `require_permission("invoices.update")`.
- Tenant-scoped payment fetch → 404. Guards, in order:
  1. `amount_cents > 0` (refund rows are negative per SD-2 and can never be overpayments) → 422.
  2. `amount_variance_cents is not None and amount_variance_cents > 0` → else 422 ("no overpayment to resolve").
  3. `variance_resolved_at is None` → else **409** with the current `variance_resolution` in the problem detail (§16.4; doubles as the natural-key replay guard — no `Idempotency-Key` header needed on this online-only endpoint).
- Set `variance_resolution`, `variance_resolution_note`, `variance_resolved_at = now()`, `variance_resolved_by_user_id = user.id`; commit; return the extended `PaymentResponse`.
- **Never** create payment rows, call Stripe, or enqueue QB work (design §G-R6).
- `/test` twin.

---

## Task 7 — Tests

Per `backend/tests/README-adding-tests.md`. Domain folder: **`tests/domains/invoicing_billing/`** (both files), `pytestmark = [pytest.mark.domain_invoicing_billing, pytest.mark.unit]`. Scope assertions by inserted IDs (never counts); use fixtures (`test_tenant`, `test_user`, `tenant_a`/`tenant_b` for cross-tenant); S3 mocked at `_s3_client`; use the seeded `issued`/`partial` status rows — look them up by code, never hardcode UUIDs. Create invoices in the states you need by inserting rows scoped to your test (seed data is present — never mutate seed rows).

New file `tests/domains/invoicing_billing/test_ce1_invoice_signoff.py`:
1. Create sign-off happy path (via `/test` twin) → 200, row active, object key `signatures/{tenant}/{invoice}/{id}.png`, `put_signature_object` called with PNG bytes, response has presigned `signature_url`.
2. Replay safety: same `Idempotency-Key` twice → second call returns the original row; exactly one row for that key.
3. Re-capture supersedes: second capture (new key) → first row `superseded_at` set, second active; `GET signoff` returns the new one with `superseded_count == 1`.
4. Validation: bad base64 → 422; non-PNG bytes → 422; `terms_acknowledged: false` → 422; empty name → 422; draft-status invoice → 422; missing `Idempotency-Key` → 400.
5. RBAC/tenancy: cross-tenant invoice id → 404 (tenant_b invoice hit with tenant_a context); missing permission → 403 on the authenticated route.
6. Signoff-context: job with an `issued` invoice returns it with `terms_text` fallback applied and `active_signoff` null; job with only `draft` invoices → empty `invoices` list; multi-invoice ordering newest-first.
7. S3 failure path: `_s3_client` mock raises `ClientError` on put → 502 and **no row written** (verify via tenant-scoped select).

New file `tests/domains/invoicing_billing/test_ce1_variance_resolution.py`:
8. Resolve happy path: overpaid payment (`amount_cents=11500, amount_variance_cents=1500`) → 200, fields set, `resolved_by` = calling user.
9. Already resolved → 409, problem detail carries the existing resolution.
10. `amount_variance_cents` NULL / ≤ 0 → 422. Negative-amount (refund) payment row → 422.
11. Invalid `resolution` value → 422 (schema). Cross-tenant payment → 404. `invoices.update`-less role → 403.
12. Extended `PaymentResponse` serialization includes the four new fields (assert keys present on the resolve response).

Intermediate check after each file: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`. Then regenerate the import map (new test files): `python generate_app_import_map.py tests > app_model_imports.md`.

---

## Task 8 — Seed Data Rollout (Scenario layer)

Per `backend/README-seed-data.md` §3/§6/§7 (already in your mandatory reads) and design §B.5. **Layer 1 (core/platform) does not apply** — no new lookup values.

In the scenario seed script that owns invoice/payment data (identify via `grep -rn "amount_variance_cents\|record_payment" backend/migrations/scripts/seed_scenario_*.py`):
1. **Overpaid payment**: one demo invoice payment with `amount_variance_cents = 1500`, `variance_resolution = NULL` → populates the web review banner in dev.
2. **Sign-off row**: one `invoice_signoff` row on a completed-job invoice (look up FKs by business key at runtime — never hardcode scenario UUIDs), object key per `build_signature_object_key` shape; write a tiny valid PNG via `put_signature_object` wrapped in try/except — on S3 failure log + skip the object but keep the row.
3. **Idempotency**: value-scoped DELETE-then-INSERT per README §7 — the signoff DELETE matches `invoice_id` of the exact row being re-seeded; the payment change is an UPDATE scoped to the exact seeded payment `id`. Never tenant-wide or class-scoped DELETEs in `mode_seed`.

Verification: `python migrations/scripts/seed_core.py --mode inspect` runs clean → `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` green (fix any seed-resilience breakage by scoping assertions, never by deleting seed rows). Update `backend/README-seed-data.md` §4 Current Seed State.

---

## Task 9 — Regeneration + Schema JSON Sync + Handoff

1. **Schema JSON** (path-based only — never edit the JSON directly; read `backend/README-schema_manager.md` first): add `tables.invoice_signoff` (columns, indexes incl. both partial unique indexes, FKs, CHECK) and the four `tables.payment.columns.*` entries + `ck_payment_variance_resolution` via `python schema_manager.py set --path … --payload tmp.json`. `--payload` from a temp file for complex objects; `rm` the temp file. On any `schema_manager.py` error → STOP and ask Tom with the exact command + error.
2. **Model map** (already done in Task 2) + **import map** (Task 7).
3. **OpenAPI**: `python export_openapi_json.py` → verify `grep -A 5 "signoff" backend/openapi_schema_map.md` and `grep -A 5 "resolve-variance" backend/openapi_schema_map.md`.
4. **Handoff (Rule 9.3 — this batch unblocks two frontend engineers)**: commit everything, then state in your Completion Summary: "OpenAPI regenerated — RN Engineer + React Engineer may now run `pnpm sync-api-types`." The mobile prompt consumes `SignoffContextResponse` / `InvoiceSignoffCreateRequest`; the web prompt consumes the extended `PaymentResponse` / `InvoiceSignoffResponse`.

---

## Final Verification

### Phase 1 — Unit tests only (during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Lint (changed files only) + Full suite (once, at the very end)

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite (stripe + telnyx live suites deselected per Tom, consistent with C-B14-FIX)
python -m pytest -m "not requires_stripe and not requires_telnyx" --tb=short -q 2>&1 | tail -10

# Batch spot checks
python -m pytest tests/domains/invoicing_billing/test_ce1_invoice_signoff.py tests/domains/invoicing_billing/test_ce1_variance_resolution.py -v 2>&1 | tail -25
grep -A 5 "signoff" backend/openapi_schema_map.md
grep "InvoiceSignoff" backend/db_models_map.md

echo "=== CE-1 PART A FINAL VERIFICATION COMPLETE ==="
```

Any failure in either phase must be fixed before done — no "pre-existing failure" exception without Tom's written confirmation. Ruff zero remaining issues in changed files; pytest warning-clean (no Pydantic v1 / deprecation noise).

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All 6 MCP pre-work queries run — `invoice_signoff` absent; `payment` has variance cols but NOT the 4 new ones; `invoice_status` codes confirmed; alembic head recorded (rules §25)
- [ ] All mandatory source files read (including `api/schemas/schemas.py` + `README-seed-data.md` §3/§6/§7)
- [ ] Task 1 migration written blank, `downgrade()` exact-reverse, full cycle tested (`upgrade → downgrade -1 → upgrade`, `alembic current` shows new head)
- [ ] Task 2 `InvoiceSignoff` inherits `StandardAuditMixin` + explicit `tenant_id`; `db_models_map.md` regenerated and shows the model
- [ ] Task 3 S3 helpers in `s3_service.py` (no direct boto3 S3 in routes)
- [ ] Task 4 schemas added; `PaymentResponse` extension additive-only
- [ ] Task 5 D.1–D.3 + `/test` twins implemented; all sync `def`; tenant-scoped selects; `set_audit_context_sync()` on mutations; RFC 7807 everywhere; 404-not-403
- [ ] Task 6 D.4 + `/test` twin; guards in order (positive amount → variance>0 → unresolved→409); no Stripe/QB/payment-row side effects
- [ ] Task 7 both test files green with `pytestmark` domain+unit, fixtures only, insert-scoped assertions, S3 mocked
- [ ] Task 8 seed rollout applied (overpaid payment + signoff row, value-scoped deletes); `seed_core.py --mode inspect` clean; `README-seed-data.md` §4 updated
- [ ] Task 9 schema JSON via `schema_manager.py` (no direct edits); `export_openapi_json.py` run; both endpoints visible in `openapi_schema_map.md`
- [ ] `ruff check --fix && ruff format` on changed files only — zero remaining issues (rules §23)
- [ ] **Phase 1**: all unit tests pass
- [ ] **Phase 2**: full suite (`-m "not requires_stripe and not requires_telnyx"`) passes, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix C, including the Rule 9.3 handoff line

---

## Completion Summary

After all DoD items are complete, add a Completion Summary to `dev-docs/analysis/pilot-launch-plan.md` **Appendix C** using this exact format:

```markdown
### CE-1 (Part A) — Invoice Sign-Off + Variance Resolution (Backend): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- …

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|

#### Seed Data Rollout
- …

#### Handoff
- OpenAPI regenerated — RN Engineer + React Engineer may now run `pnpm sync-api-types`.
```

---

## After This Task — Next Step

This is **Part A of 3** (design §C). When done: commit + push, then report back. The Architect then releases (in order): ① `batch-ce-1-react-native-engr-prompt.md` (mobile capture — Tom-approved design spec + Expo dependency already approved 2026-08-12), ② the CE-1 web React prompt (invoice detail sign-off card + overpayment banner — pending web-ui designer spec). Do not start frontend work yourself.
