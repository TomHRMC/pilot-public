# Batch Design: PLP-FIX-1 — Quote Entitlement Seed + Custom Invoice Line Items

**Batch**: PLP-FIX-1
**Date**: 2026-08-30
**Author**: Pilot Architect
**Source bug report**: `dev-docs/analysis/PLP-testing-bugs-2026-08-30.md` (Issues 1 & 2 of 4)
**Prompt**: `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/batch-plp-fix-1-python-engr-prompt.md`
**Platform**: Backend only (`backend/`) — API contract change requires FE type sync afterward (handoff)
**Estimated session**: 3–4 hours

> **v1.1 (2026-08-30) — Option B pivot (Tom decision)**: The PRD (`mvp-prd.md`) states **"unlimited jobs/quotes/invoices"** on every plan. Quote creation must therefore carry **no entitlement gate at all** — the fix is to **remove `feature_code="quotes_per_month"` from the quotes route**, not to seed the feature. No migration, no seed rows. Tom additionally mandated a full audit for other phantom gates: it found **one** — a stale pre-SD-07 `sms_segments` code in the SMS rollover task (now §B.2). v1.0's migration/seed approach is retained below as struck-through history; §B/§G are rewritten.

---

## A. Input Read Summary

| Input | What was read / verified | Key finding |
|---|---|---|
| `PLP-testing-bugs-2026-08-30.md` | Full bug report (Issues 1–4) | Issues 1 & 2 are backend; 3 & 4 are FE (separate batches) |
| `backend/api/routes/quotes.py` | `create_quote` decorator | `require_permission("quotes.create", feature_code="quotes_per_month")` wired but feature never seeded |
| `backend/services/entitlement_service.py` | `check_entitlement()` decision tree | Absent ppfv row → `feature_not_in_plan` → 402 for ALL tenants |
| MCP `product_feature` (columns + rows) | Live DB, 2026-08-30 | 3 features only (`outbound_sms_segments`, `schedule_lanes`, `voice_ai_minutes`); StandardAuditMixin columns confirmed (`created_at`/`updated_at` NOT NULL no default, `created_by`/`updated_by` nullable) |
| MCP `product_plan_product_feature_version` (columns + rows) | Live DB | 9 rows (3 plans × 3 features), none for `quotes_per_month`; AppendOnly (`recorded_at` default `now()`, no `updated_at`); `limit_enforcement` default `'block'` — must be set explicitly |
| MCP `product_plan` rows | Live DB | `charter_plan` active; `starter_plan`/`teams_plan` inactive but still seeded with ppfv rows (keep parity) |
| `backend/migrations/scripts/seed_core.py` | `PRODUCT_FEATURE_ROWS` | `quotes_per_month` absent — must be added (post-schema-restore recovery path) |
| `backend/migrations/scripts/seed_platform.py` | `PLAN_FEATURE_LIMITS` dict + ppfv insert loop | Dict-driven; skips feature codes not present in DB — add `quotes_per_month` entries for all 3 plans |
| `backend/api/schemas/schemas.py` | `InvoiceCreate` | No `customer_id`, no `site_id`, no `line_items[]`; XOR on `quote_id`/`job_id` |
| `backend/api/routes/invoices.py` | `_create_invoice_impl` both paths | Quote path copies `quote_line.qco_line_type_id` (safe — NOT NULL, 0 NULLs in DB). **Job path passes `qco_line_type_id=None` (lines 559, 579) into a NOT NULL column → latent IntegrityError on every job→invoice creation** |
| `backend/app/models/billing.py` | `InvoiceLine` model | Model declares `qco_line_type_id: uuid.UUID \| None` — **model↔DB drift** (DB is NOT NULL per MCP). DB is truth; fix callers + align model. `source_type` CHECK = `('quote_line','change_order_line','ad_hoc')` |
| MCP `invoice` / `invoice_line` columns | Live DB | `invoice.customer_id` + `site_id` NOT NULL → standalone invoices need both in the request; `invoice_line` full column set verified for line construction |
| MCP `qco_line_type` rows | Live DB | 5 rows: `labor`, `material`, `misc`, `discount`, `note` |
| MCP `quote_line.qco_line_type_id` | Live DB | NOT NULL; 0 existing NULLs → quote path safe, no fallback needed |
| MCP `alembic_version` | Live DB | Current head `c8d06a6ffdd2` at authoring time |
| `frontend/.../useCreateInvoice.ts` | FE payload | Already sends `customer_id` + `site_id` (silently dropped by Pydantic today) — standalone builder is 100% blocked, not just custom lines |
| `frontend/.../InvoiceBuilderPage.tsx` | Custom-line state shape | `{ description, unitPriceCents }` + TODO FE-B29-1 awaiting backend `line_items[]` field name |
| `dev-docs/pilot-operations.md` | tier→plan→ppfv cascade, `block` vs `soft` | `block` = 402 (e.g. `schedule_lanes`); `soft` = allow + meter. Quotes must never hard-block |
| `backend/tests/conftest.py` | Autouse `mock_entitlement_allowed` | Entitlement tests need `@pytest.mark.skip_mock_entitlement_allowed` |
| `backend/tests/domains/subscriptions_usage/test_cb14_entitlement_scenarios.py` | Entitlement test pattern | Direct-insert ppfv rows + `check_entitlement()` assertion pattern |
| `backend/tests/domains/subscriptions_usage/test_sd07_feature_revision.py` | Seed-state test pattern | Asserts `product_feature` / ppfv rows exist post-migration |
| `backend/python-engr-std-prompt-inclusions.md` | Full inclusion spec (all 22 sections) | Governs the prompt authored from this design |
| `mvp-prd.md` | Pricing confirmation line | **"unlimited users, unlimited jobs/quotes/invoices"** on every plan — the product truth that forces Option B (v1.1) |
| Gate audit — `feature_code=` grep across `backend/api`, `backend/services`, `backend/tasks`, `backend/core` | Every entitlement wiring | Only **one** route gate exists in the entire API (`quotes_per_month` — phantom). Service gate `schedule_lanes` (`tier_limit_enforcer.py`) is legitimate (PRD: 5/20 lanes, block). Metering writes: `voice_ai_minutes` (legit, seeded) and **`sms_segments` in `rollover_sms_quota_periods.py` — STALE pre-SD-07 code**; `usage_ledger.product_feature_code` FKs to `product_feature.code` which has no such row → the overage-write path FK-violates when it fires |
| MCP `usage_ledger` code census | Live DB | Only `outbound_sms_segments` (5 rows) + `voice_ai_minutes` (8 rows) exist — confirms the rollover task's stale-code write path has never succeeded |
| `backend/tests/batch_b11/test_a65_sms_quota.py` | Rollover task test coverage | Only the zero-phones path is tested — the overage-write path has no coverage (why the stale code survived) |

---

## B. Code-Only Batch — No Migration, No Seed Changes (Option B, v1.1)

**There is no DB change in this batch.** Quote creation is de-gated in code (§D.0); the phantom feature is never seeded.

### B.1 Delete the v1.0 migration file
The engineer created `backend/migrations/versions/2026_08_30_1706-c482cdbaab36_plp_fix1_seed_quotes_per_month_feature.py` before the Option B decision. **Delete it unrun** (it was never applied — `alembic_version` head remains `c8d06a6ffdd2`, MCP-verified 2026-08-30). If it was somehow already applied locally, `alembic downgrade -1` first, then delete.

### B.2 Audit finding folded into scope — stale `sms_segments` code
`backend/tasks/rollover_sms_quota_periods.py` references the pre-SD-07 feature code `sms_segments` twice: `resolve_overage_rate(db, tenant_id, "sms_segments")` (line ~85) and the `UsageLedger(product_feature_code="sms_segments", …)` insert (line ~107). `product_feature` holds `outbound_sms_segments` (renamed by SD-07, 2026-07-06). Both lines change to `outbound_sms_segments` — code-only, no data change (zero `sms_segments` rows exist in `usage_ledger`, MCP-verified). `billing_rate_service.py` docstring example gets the same correction for hygiene. The Stripe Billing Meter **event name** `sms_segments` (`scripts/stripe_bootstrap.py`) is an **external Stripe identifier**, not a `product_feature` code — deliberately untouched.

### B.3 Seed Data Rollout — N/A (Option B)
No DB data is added or modified by this batch (Architect rule §11.5 applies only to data-changing batches). Nothing is seeded for `quotes_per_month` — seeding it would re-arm the phantom gate. `README-seed-data.md` §4 is untouched. The §B.2 fix is a code correction against already-seeded data.

### B.4 Entitlement cache note
No Redis action needed: once the route no longer consults the entitlement service, stale `entitlement:{tenant}:quotes_per_month` keys (if any) are simply never read and expire within their 300 s TTL.

---

## C. Execution Order (v1.1)

| # | Step | Output |
|---|---|---|
| 1 | Regression baseline (`pytest -m unit`) | Recorded count |
| 2 | MCP pre-work queries (audit confirmation + invoice tables) | Confirmed state |
| 3 | Delete the unrun v1.0 migration file (§B.1); de-gate the quotes route + docstring hygiene (§D.0) | 402 failure class removed |
| 4 | Stale `sms_segments` → `outbound_sms_segments` in the rollover task + docstring (§B.2) | Overage-write path FK-safe |
| 5 | Repoint entitlement test files: 1d4 mock tests → synthetic feature code; e2e → service-level chain test; `conftest.py` comment | Framework coverage preserved without a phantom gate |
| 6 | `InvoiceLineItemCreate` + `InvoiceCreate` schema extension in `api/schemas/schemas.py` (§D) | Request contract |
| 7 | `_create_invoice_impl` rework in `api/routes/invoices.py` — three-mode validation, standalone path, custom-line persistence, job-path line-type fix (§F) | All three create paths work |
| 8 | Align `InvoiceLine.qco_line_type_id` model field with DB (NOT NULL) in `app/models/billing.py`; grep-fix any `InvoiceLine(` constructions passing None | Model↔DB drift closed |
| 9 | Tests — de-gate regression + rollover overage-write + invoice custom-lines suites | New coverage green |
| 10 | `python generate_db_model_map.py app > db_models_map.md` + `python generate_app_import_map.py tests > app_model_imports.md` + `python export_openapi_json.py` | Generated docs current |
| 11 | Phase 1 + Phase 2 gates; handoff note for FE type sync | Batch done |

---

## D. API Endpoint Changes

**No new endpoints.** Two modified surfaces: the quotes route loses its entitlement gate (§D.0), and `POST /api/v1/invoices/` + its `/api/v1/invoices/test` twin gain the extended contract (§D.1+, both call `_create_invoice_impl`).

### D.0 Quotes route de-gate (Option B, v1.1)

`backend/api/routes/quotes.py`:

```python
# BEFORE
current_user: AuthenticatedUser = Depends(
    require_permission("quotes.create", feature_code="quotes_per_month")
),

# AFTER
current_user: AuthenticatedUser = Depends(require_permission("quotes.create")),
```

- RBAC (`quotes.create` permission) is unchanged — only the Step-2 feature entitlement is dropped.
- The endpoint docstring's 402/`quotes_per_month` references are updated to match.
- Docstring examples mentioning `quotes_per_month` in `core/permissions.py` and `services/entitlement_service.py` are switched to a genuinely gated feature (`schedule_lanes`) for hygiene — the framework itself is untouched.
- No OpenAPI-visible schema change from this edit (402 was never in the response model), but `export_openapi_json.py` still runs for §D.1.

### D.1 Request contract additions (`InvoiceCreate`)
| Field | Type | Rules |
|---|---|---|
| `customer_id` | `UUID \| None` | Required in standalone mode; must exist in tenant (404 otherwise); forbidden when `quote_id` or `job_id` set (422) |
| `site_id` | `UUID \| None` | Required in standalone mode; must exist in tenant **and belong to `customer_id`** (404/422); forbidden when `quote_id` or `job_id` set (422) |
| `line_items` | `list[InvoiceLineItemCreate] \| None` | ≥1 item required in standalone mode; optional (appended) in quote/job modes |

### D.2 New schema — `InvoiceLineItemCreate`
| Field | Type | Default | Validation |
|---|---|---|---|
| `description` | `str` | — | required, non-empty after strip, ≤ 500 chars |
| `quantity` | `Decimal` | `1` | `> 0`, ≤ 3 decimal places (matches `Numeric(12,3)`) |
| `unit` | `str \| None` | `None` | e.g. `"hr"`, `"ea"` |
| `unit_price_cents` | `int` | — | required, `>= 0` (integer cents — Rule §22) |
| `qco_line_type_code` | `str \| None` | `"misc"` | must resolve to an active `qco_line_type.code` → else 404 RFC 7807 |

### D.3 Mode resolution (replaces the current XOR)
| Mode | Condition | Customer/site source | Lines |
|---|---|---|---|
| Quote | `quote_id` set, `job_id`/`customer_id`/`site_id` unset | from quote | quote lines (existing) + `line_items[]` appended |
| Job | `job_id` set, `quote_id`/`customer_id`/`site_id` unset | from job | time entries + expenses (existing) + `line_items[]` appended |
| Standalone | only `customer_id` + `site_id` set | from request (tenant-validated) | `line_items[]` only, ≥1 required |
| Invalid | everything else (no mode; both quote+job; quote+customer; job+site; standalone without lines) | — | **400** RFC 7807 `invalid-mode` |

### D.4 Custom line persistence (all modes)
`source_type='ad_hoc'`, `source_id=NULL`, `position` continuing after source-derived lines, `qco_line_type_id` resolved from `qco_line_type_code` (default `misc`), `subtotal_cents = total_cents = round(quantity × unit_price_cents)`, all tax fields `NULL`, `tax_cents` contribution `0` (tax engine integration is a later batch — §G-5), `is_active=True`, `created_by=user.id`.

### D.5 Totals
`invoice.subtotal_cents` / `total_cents` / `balance_due_cents` must include custom-line amounts in every mode (`total = subtotal + tax_cents`; custom lines add `0` tax).

### D.6 Errors (all RFC 7807)
404 for tenant-scoped customer/site/quote/job misses (never 403 — no UUID enumeration); 400 for mode conflicts; 422 for Pydantic field validation; 404 for unknown `qco_line_type_code`.

### D.7 Auth / audit
Existing `require_permission("invoices.create")` decorator and `set_audit_context_sync()` call are unchanged — engineer verifies both are present and keeps them.

---

## E. Pattern Reuse Decisions (`mvp-arch.md` §16)

| Pattern | Application |
|---|---|
| Idempotency-Key | Unchanged — existing `idempotency_key` handling on `Invoice` covers the new modes (custom lines ride inside the same transaction) |
| RFC 7807 Problem Details | All new error branches (§D.6) |
| Tenant-scoped `select()` | Customer/site/quote/job lookups all `WHERE tenant_id = :tid`; `db.get()` banned |
| Sync-by-design | All new code is plain `def` on the sync `Session` |
| AppendOnly `invoice_line` | Insert-only; no updates to existing lines |
| Audit context | `set_audit_context_sync(db, user_id=...)` before first write (already present — keep) |

No new top-level UX or architectural patterns introduced.

---

## F. Shared Module Interfaces

```python
# api/schemas/schemas.py
class InvoiceLineItemCreate(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    unit: str | None = None
    unit_price_cents: int
    qco_line_type_code: str | None = None  # default resolved to "misc" in impl

    # @field_validator("description") — non-empty after strip
    # @field_validator("quantity") — > 0
    # @field_validator("unit_price_cents") — >= 0

class InvoiceCreate(BaseModel):
    quote_id: UUID | None = None
    job_id: UUID | None = None
    customer_id: UUID | None = None        # NEW — standalone mode
    site_id: UUID | None = None            # NEW — standalone mode
    line_items: list[InvoiceLineItemCreate] | None = None  # NEW
    customer_notes: str | None = None
    terms_and_conditions: str | None = None
    due_at: datetime | None = None
    issued_at: datetime | None = None
    idempotency_key: str | None = None
    payment_terms: str | None = None
    billing_mode: str = "line_item"
    progress_pct: Decimal | None = None
    internal_memo: str | None = None
    # existing progress validator unchanged
```

```python
# api/routes/invoices.py (new private helpers, sync def)
def _resolve_qco_line_type_id(db: Session, code: str | None) -> uuid.UUID:
    """Look up qco_line_type by code (default 'misc'). 404 RFC 7807 if unknown."""

def _persist_custom_lines(
    line_items: list[InvoiceLineItemCreate],
    invoice_id: uuid.UUID,
    start_position: int,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> int:
    """Insert ad_hoc InvoiceLine rows; returns added subtotal_cents."""
```

`_create_invoice_impl` restructured: mode resolution (§D.3) → source lines per mode → `_persist_custom_lines` append → totals → commit (single transaction, existing try/except shape preserved).

**Job-path fix (same edit site)**: time-entry lines → `qco_line_type_id = <labor id>`; expense lines → `qco_line_type_id = <material id>` (looked up once per request via `_resolve_qco_line_type_id`).

**Model alignment**: `InvoiceLine.qco_line_type_id` → `uuid.UUID = Field(foreign_key="qco_line_type.id", index=True)` (no default, non-nullable) to match the live DB. Engineer greps for all `InvoiceLine(` constructions to confirm every path sets a value (only `invoices.py` creates them in app code; tests may need fixing).

**Celery**: none.

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| G-1 | ~~Charter limit for `quotes_per_month`~~ → **superseded (v1.1)** | **De-gate, don't seed (Tom, Option B).** PRD line 1005: quotes are unlimited on every plan. An unlimited feature carries no entitlement gate — remove `feature_code` from the route (§D.0). The v1.0 values (charter NULL, starter 25, teams 100) were architect-invented placeholders contradicting the PRD; the migration is deleted unrun |
| G-2 | Why not seed NULL-unlimited rows anyway (future-proofing)? | Rejected — a gate that can only ever answer "yes" is pure liability: every future plan would have to remember the row or this exact 402 returns (the bug Tom hit). If a quote limit is ever product-decided, re-adding the gate is one decorator arg + seed rows |
| G-3 | Are there other phantom gates? (Tom mandate) | **Full audit (§H): one more found** — stale pre-SD-07 `sms_segments` code in the SMS rollover task's overage-write path (FK-unsafe). Fixed in this batch (§B.2). All other entitlement touchpoints are legitimate |
| G-4 | `line_items[]` with quote/job modes | **Allowed** — appended after source-derived lines (`ad_hoc`); the invoice builder combines billable job items + custom lines on one invoice |
| G-5 | Tax on custom lines | **None this batch** — tax fields NULL, `tax_cents` contribution 0; tax-engine integration for ad-hoc lines is a later batch (recorded here so it isn't re-litigated) |
| G-6 | Standalone mode requirements | `customer_id` + `site_id` both required (DB NOT NULL), tenant-scoped, site must belong to the customer; ≥1 line item; empty custom-line standalone → 400 |
| G-7 | `quote_id` + `customer_id` together | **400 invalid-mode** — customer/site always derive from the source document; explicit+derived mixes are ambiguous |
| G-8 | Job-path `qco_line_type_id=None` | **Latent bug, fixed in this batch** — `labor` for time-entry lines, `material` for expense lines. DB NOT NULL is truth; model `\| None` is drift → model aligned to NOT NULL. DB constraint is NOT relaxed |
| G-9 | Quote path `qco_line_type_id` fallback | **Not needed** — `quote_line.qco_line_type_id` is NOT NULL with 0 NULLs in the live DB (MCP-verified) |
| G-10 | Redis entitlement cache after the de-gate | **No action** — the route stops consulting the service; stale keys expire within their 300 s TTL unread |
| G-11 | `qco_line_type_code` unknown value | 404 RFC 7807 (lookup-table miss, consistent with tenant-scoped-not-found convention) |
| G-12 | `/test` endpoint parity | The existing `/api/v1/invoices/test` twin calls the same `_create_invoice_impl` — new modes work there automatically; tests use it |
| G-13 | Stripe meter event name `sms_segments` in `stripe_bootstrap.py` / C-B4 reporting tests | **Untouched** — it is an external Stripe Billing Meter identifier registered in Stripe, not a `product_feature` code. Different namespace from the internal FK'd code fixed in §B.2 |
| G-14 | Entitlement framework itself (`core/permissions.py` Step 2, `entitlement_service.py`) | **Kept, untouched** — genuinely gates `schedule_lanes` (block, PRD 5/20 lanes) and is the mechanism for `voice_ai_minutes` / `outbound_sms_segments` soft metering. Only the phantom wiring is removed |

---

## H. Entitlement Gate Audit (Tom mandate, 2026-08-30)

Complete census of every entitlement touchpoint in the backend (grep: `feature_code=`, `check_entitlement`, `get_cached_entitlement`, `tier_limit_enforcer` across `api/`, `services/`, `tasks/`, `core/`; MCP cross-check of `product_feature`, `product_plan_product_feature_version`, `usage_ledger`):

| # | Touchpoint | Feature code | Verdict | Action |
|---|---|---|---|---|
| 1 | `quotes.py` — `require_permission("quotes.create", feature_code=…)` | `quotes_per_month` | **PHANTOM** — not in PRD pricing model; never seeded; only route gate in the entire API | **De-gate** (§D.0) |
| 2 | `services/tier_limit_enforcer.py` — lane-limit check on dispatch board | `schedule_lanes` | **LEGITIMATE** — PRD 5 Starter / 20 Teams, `block`; seeded; overrides supported | Keep |
| 3 | `api/routes/voice.py` — usage metering write | `voice_ai_minutes` | **LEGITIMATE** — PRD overage $0.05/min; seeded; 8 usage rows live | Keep |
| 4 | `tasks/rollover_sms_quota_periods.py` — overage rate + usage write | ~~`sms_segments`~~ | **STALE** — pre-SD-07 code; `product_feature` holds `outbound_sms_segments`; FK'd write would violate; zero such rows in `usage_ledger` (path never succeeded) | **Fix** (§B.2) |
| 5 | `core/permissions.py` + `services/entitlement_service.py` — framework | (parameter) | **LEGITIMATE** — the mechanism itself; docstring examples reference the phantom code | Keep; docstring hygiene (§D.0) |
| 6 | `services/billing_rate_service.py` — overage rate resolution | (parameter) | **LEGITIMATE** — rate lookup for metered overage; docstring example uses the stale code | Keep; docstring hygiene (§B.2) |
| 7 | `scripts/stripe_bootstrap.py` — Stripe meter `event_name` | `sms_segments` (Stripe namespace) | **LEGITIMATE** — external Stripe identifier, not a `product_feature` code | Keep (§G-13) |
| 8 | `api/routes/admin_tenants.py` — override upsert | (request body) | **LEGITIMATE** — platform-admin tooling for `tenant_product_feature_override` | Keep |

**Standing rule emerging from this audit**: a `feature_code=` wiring may only reference a feature that (a) appears in the PRD pricing model and (b) has seeded `product_feature` + ppfv rows. A wiring without both is a phantom gate — remove it, don't seed around it. Any future entitlement gate addition must name its PRD pricing line in the batch design.

## Handoff (post-batch)

`InvoiceCreate` gains fields → OpenAPI changes → engineer runs `python export_openapi_json.py`, commits, and the follow-on **FE batch (FE-B29-1)** runs `pnpm sync-api-types` to consume `line_items[]` in the invoice builder (resolves the TODO at `InvoiceBuilderPage.tsx`). FE Issues 3 & 4 from the bug report are separate React Engineer batches.
