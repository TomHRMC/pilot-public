# Implementation Prompt: PLP-FIX-5 (Part A — Backend) — Quote-Line `qco_line_type_id` (Issue 14) + Subscription Plan-Summary Payload (Issue 8 BE)

**Mode**: `pilot-python-engineer`
**Batch**: PLP-FIX-5 Part A (backend half of a mixed batch — **runs FIRST**)
**Launch plan**: `dev-docs/analysis/pilot-launch-plan.md` §1 / §3.26 (Ord 26)
**Design doc (read first)**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-5-design.md` — §A–§G; §D holds the exact contract additions
**Bug intake**: `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` (Issues 8, 14)
**Estimate**: ~1.5 h
**Platform**: Backend (FastAPI + SQLModel + pytest)
**Frontend companion**: Part B — `batch-plp-fix-5-react-engr-prompt.md` — **blocked until you complete the Handoff Instructions section** (OpenAPI regen + commit).

---

## ⚠️ MANDATORY STOP: Read These First

Before writing any code, read these documents **in full**:

1. `backend/pilot-python-engineer-methods.md` — house engineering method
2. `backend/tests/README-adding-tests.md` — test placement, domain markers, autouse fixtures
3. The design doc linked above — all sections. §G decisions are settled; do not re-litigate.

Do not start Task 1 until all three are read.

---

## Batch-Specific Critical Rules

1. **Additive only.** No field removals, no renames, no new endpoints, no behavioral change to existing fields. Both modified responses gain fields; everything else stays byte-identical.
2. **Tenant-scoped `select()` only** — `db.get()` is permanently banned on tenant-scoped models.
3. **Never guess column names.** The Architect ran the MCP queries below against the live local DB and recorded expected results. Re-run them in Pre-Work; if anything differs, **STOP and report back**.
4. **Reuse `check_entitlement` for limits** — do NOT hand-write a ppfv/`product_plan_product_feature_version` query. Signature verified: `check_entitlement(tenant_id: uuid.UUID, feature_code: str, db: Session) -> EntitlementResult`; use `EntitlementResult.limit`.
5. **`Subscription`/`SubscriptionStatus` import from `app.models.billing`** (lines 541, 732) — NOT `app.models.subscription` (that module holds the tier/usage/override models already imported in the route file).
6. **Sync-by-design** — all touched code stays sync `def`.
7. **Both `/test` twins inherit the changes automatically** (they delegate to the same `_impl`s) — do not duplicate logic into them, and do not forget they exist when writing tests.

---

## Pre-Work: Establish Regression Baseline

```bash
cd backend && pytest -m unit --tb=no -q | tail -5
```

Record the counts in your Completion Summary. (Reference point: PLP-FIX-6 closed at **4764 passed, 1 skipped**.)

---

## Pre-Work: Run MCP Verification Queries

Run via `postgres-local` MCP (read-only). Expected results were recorded by the Architect on 2026-09-02 — confirm yours match. Any mismatch → **STOP**.

**Q1 — subscription write-source columns:**
```sql
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='subscription'
  AND column_name IN ('tenant_id','status_id','billing_interval','renews_at','trial_ends_at','is_active','product_plan_code')
ORDER BY ordinal_position;
```
Expected: `tenant_id` uuid NO · `product_plan_code` varchar NO · `status_id` uuid NO · `billing_interval` varchar NO · `trial_ends_at` timestamptz YES · `renews_at` timestamptz YES · `is_active` bool NO.

**Q2 — status lookup rows:**
```sql
SELECT code, name, is_billing_active FROM public.subscription_status ORDER BY code;
```
Expected: `active`/t · `canceled`/f · `past_due`/t · `paused`/f · `trialing`/t · `unpaid`/f.

**Q3 — tenant + tier columns:**
```sql
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='tenant'
  AND column_name IN ('trial_ends_at','free_period_ends_at','current_subscription_tier_id','charter_eligible');
```
Expected: 4 rows (both timestamptz nullable; `current_subscription_tier_id` uuid NO; `charter_eligible` bool NO).

**Q4 — quote_line + tier price columns:**
```sql
SELECT table_name, column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND ((table_name='quote_line' AND column_name='qco_line_type_id')
  OR (table_name='subscription_tier' AND column_name IN ('annual_price_cents','monthly_price_cents')))
ORDER BY table_name, ordinal_position;
```
Expected: `quote_line.qco_line_type_id` uuid NO · `subscription_tier.annual_price_cents` int NO · `monthly_price_cents` int NO.

**Q5 — feature codes:**
```sql
SELECT code, name, is_active FROM public.product_feature ORDER BY code;
```
Expected: exactly `outbound_sms_segments`, `schedule_lanes`, `voice_ai_minutes` — no users-limit feature.

---

## Pre-Work: Read These Source Files

1. `backend/api/schemas/quotes.py` lines 100–145 — `QuoteLineDetailResponse` (107–122) + `QuoteDetailResponse` doc context.
2. `backend/services/quote_service.py` lines 300–386 — the line-item assembly (316–337) you are extending.
3. `backend/api/routes/tenant_subscription.py` lines 1–222 — schemas (33–55), `_get_tenant_subscription_impl` (114–186), `/test` twin (192–200), isolation guard (218–221).
4. `backend/api/routes/subscription_tiers.py` lines 20–60 — `SubscriptionTierResponse` field list.
5. `backend/services/entitlement_service.py` lines 66–125 — `check_entitlement` signature + `EntitlementResult` shape (`limit` attribute).
6. `backend/app/models/billing.py` lines 540–600 and 731–760 — `Subscription` + `SubscriptionStatus` model field names (confirm ORM attribute names match the DB columns you verified in Q1/Q2).
7. `dev-docs/pilot-operations.md` §3–§5, §8 — tier model, subscription lifecycle (charter row semantics), status machine. Context for why the derivations are shaped this way.
8. Existing test files you will extend — locate via `conftest.py` `_FOLDER_TO_DOMAIN_MARKER`: the quote-detail tests in `tests/domains/sales_quoting/` and the tenant-subscription tests in `tests/domains/subscriptions_usage/`.

---

## Background / Context

**Issue 14** — Tom's two prod quotes show "—" for every line's Type. The `/detail` response carries `line_type` (the code) but omits `qco_line_type_id`; the draft editor resolves persisted-row labels **by id** (`lineTypes.find(t => t.id === line.qco_line_type_id)?.name ?? "—"`). The column is NOT NULL and the join already selects it — the constructor at `quote_service.py` simply never passes it through. Zero FE change: the editor already declares the field optional; it starts rendering at deploy.

**Issue 8 (BE half)** — the Billing page can't show plan status / renewal / interval because `TenantSubscriptionResponse` never exposes the `subscription` row. The data exists (MCP-verified columns). Part A extends the response with a `plan_summary` object, `charter_eligible` (retires the FE's client-side derivation + TODO), and a `limits` object (ppfv-resolved) — the FE's usage bars currently read `max_users`/`max_sms_segments_per_month` off a hand-written interface the BE never sends (design-time finding 8a; only 3 product features exist — Q5).

**Mixed-batch protocol (rules §1.3)**: you run first; the React Engineer is gated on your OpenAPI regeneration. Do not start FE work; do not skip the Handoff Instructions.

---

## Design Decisions (Do Not Re-Litigate)

From design §G — settled:

1. Derived status when no active `subscription` row: `trialing`/`is_billing_active=True` when `tenant.trial_ends_at > now()`; otherwise `status_code=None`, `is_billing_active=False`. Never fabricate "active".
2. Charter semantics: charter row's `renews_at` equals the free-period end (ops §4); `free_period_ends_at` is reported from the **tenant** column.
3. Limits come from `check_entitlement` per the 3 MCP-verified feature codes — no users-limit key (no such feature exists).
4. `annual_price_cents` is the **yearly total** (58800 = $588/yr) — the FE decides display formatting; the BE ships raw cents.
5. Issue 14 needs no FE change and no FE deploy ordering — but it DOES change the OpenAPI schema, so regen + `sync-api-types` is still the handoff signal.

---

## Task 1 — Issue 14: `qco_line_type_id` in the `/detail` response

**1a.** `backend/api/schemas/quotes.py` — add to `QuoteLineDetailResponse` (after `line_type`):

```python
    line_type: str  # qco_line_type.code — e.g. 'labor', 'material', 'misc', 'discount'
    # PLP-FIX-5 (Issue 14): the FK the draft editor resolves persisted-row labels by
    qco_line_type_id: UUID
```

(`UUID` is already imported in this schema file — confirm at the top; add `from uuid import UUID` only if absent.)

**1b.** `backend/services/quote_service.py` — in the `line_items` list comprehension (lines 326–337), pass it through:

```python
    line_items = [
        QuoteLineDetailResponse(
            id=line.id,
            description=line.description,
            customer_visible=line.customer_visible,
            unit_price_cents=line.unit_price_cents,
            quantity=float(line.quantity),
            total_cents=line.total_cents,
            line_type=line_type.code,
            qco_line_type_id=line.qco_line_type_id,  # PLP-FIX-5 (Issue 14)
        )
        for line, line_type in line_rows
    ]
```

Nothing else changes in this function.

---

## Task 2 — Issue 8 BE: plan-summary payload

All edits in `backend/api/routes/tenant_subscription.py` unless noted.

**2a.** Model imports — add to the existing import block:

```python
from app.models.billing import Subscription, SubscriptionStatus
```

(The file already imports `SubscriptionTier, TenantSubscriptionUsage, TenantTierOverride` from `app.models.subscription` — different module, keep both imports.)

**2b.** New schemas (place beside `UsageSummaryResponse`/`TierOverrideResponse`, lines 33–55):

```python
class PlanSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status_code: str | None        # subscription_status.code; derived "trialing" when no row + live trial
    status_name: str | None        # display label from the same source
    is_billing_active: bool        # row's flag; True for derived trialing
    billing_interval: str | None   # "monthly" | "annual" | None (no row)
    renews_at: str | None          # ISO; charter row: = free period end
    free_period_ends_at: str | None  # tenant.free_period_ends_at (charter only)


class PlanLimitsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outbound_sms_segments: int | None
    schedule_lanes: int | None
    voice_ai_minutes: int | None
```

**2c.** Extend `TenantSubscriptionResponse`:

```python
class TenantSubscriptionResponse(BaseModel):
    current_tier: SubscriptionTierResponse
    trial_ends_at: str | None
    stripe_customer_id: str | None
    usage: UsageSummaryResponse | None
    tier_override: TierOverrideResponse | None
    plan_summary: PlanSummaryResponse
    charter_eligible: bool
    limits: PlanLimitsResponse
```

**2d.** Extend `SubscriptionTierResponse` in `backend/api/routes/subscription_tiers.py` — add `annual_price_cents: int` beside `monthly_price_cents`. (`model_validate` from attributes picks it up automatically; MCP Q4 confirmed the column is NOT NULL.)

**2e.** Wire `_get_tenant_subscription_impl` — after the tier resolution block (after line 145) and before the `return`, add the subscription-row lookup + derivation + limits, then include the three new fields in the response constructor:

```python
    # PLP-FIX-5 (Issue 8): plan summary from the active subscription row
    sub_row = db.exec(
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .where(Subscription.is_active == True)
    ).first()

    sub_status = (
        db.exec(
            select(SubscriptionStatus).where(SubscriptionStatus.id == sub_row.status_id)
        ).first()
        if sub_row
        else None
    )

    if sub_status is not None:
        status_code: str | None = sub_status.code
        status_name: str | None = sub_status.name
        is_billing_active = bool(sub_status.is_billing_active)
        billing_interval: str | None = sub_row.billing_interval if sub_row else None
        renews_at = sub_row.renews_at.isoformat() if sub_row and sub_row.renews_at else None
    elif tenant.trial_ends_at and tenant.trial_ends_at > now:
        # Design §G.4: pre-conversion trial tenants have no subscription row
        status_code, status_name, is_billing_active = "trialing", "Trialing", True
        billing_interval, renews_at = None, None
    else:
        status_code, status_name, is_billing_active = None, None, False
        billing_interval, renews_at = None, None

    plan_summary = PlanSummaryResponse(
        status_code=status_code,
        status_name=status_name,
        is_billing_active=is_billing_active,
        billing_interval=billing_interval,
        renews_at=renews_at,
        free_period_ends_at=tenant.free_period_ends_at.isoformat()
        if tenant.free_period_ends_at
        else None,
    )

    # Limits via the entitlement service (never a hand-written ppfv query)
    from services.entitlement_service import check_entitlement

    limits = PlanLimitsResponse(
        outbound_sms_segments=check_entitlement(
            tenant_id, "outbound_sms_segments", db
        ).limit,
        schedule_lanes=check_entitlement(tenant_id, "schedule_lanes", db).limit,
        voice_ai_minutes=check_entitlement(tenant_id, "voice_ai_minutes", db).limit,
    )
```

Then in the `return TenantSubscriptionResponse(...)` add:

```python
        plan_summary=plan_summary,
        charter_eligible=tenant.charter_eligible,
        limits=limits,
```

Notes:
- `now` already exists in this function (line 148).
- The `check_entitlement` import may be module-level if you prefer (no circular-import risk — the service imports models/core only); function-local matches this file's existing style (see line 119's `from datetime import ...`).
- `EntitlementResult.limit` is `None` when the feature has no quantity limit — correct per `PlanLimitsResponse` nullability.

**2f.** Do NOT touch `require_permission("subscription.view")`, the isolation guard, or any other endpoint in the file.

---

## Task 3 — Regression tests

Placement per `_FOLDER_TO_DOMAIN_MARKER` in `conftest.py`.

**3a.** Issue 14 — `tests/domains/sales_quoting/`: find the existing quote-detail test file and add a test that:
- Creates a quote via the real endpoints (the PLP-FIX-3 v1-at-create path — reuse the existing test's setup), adds a line with a known `qco_line_type_id`, calls `GET /api/v1/quotes/{id}/detail` (or its `/test` twin per the file's existing convention), and asserts the returned line item's `qco_line_type_id` equals the value inserted. Scope assertions to the inserted line's id — never positional/global assertions.

**3b.** Issue 8 — `tests/domains/subscriptions_usage/`: find the existing `GET /{tenant_id}/subscription` test file and add a class covering:
- **With subscription row**: tenant with an active `subscription` row (build via fixtures: status row `trialing` or `active` from seed; `billing_interval`, `renews_at` set) → response `plan_summary.status_code`/`is_billing_active`/`billing_interval`/`renews_at` match the row; `charter_eligible` mirrors the tenant column; `limits` keys present (values depend on seeded ppfv — assert type/presence, not magic numbers, unless the fixture tenant's ppfv rows are explicit).
- **Derived trialing**: tenant with NO subscription row + `trial_ends_at` in the future → `status_code == "trialing"`, `is_billing_active is True`, `billing_interval is None`.
- **Derived none**: tenant with NO subscription row + `trial_ends_at` NULL or past → `status_code is None`, `is_billing_active is False`.
- **`annual_price_cents`**: present on `current_tier` and an int.
- Use the existing `/test` twin if that is the file's convention; scope every DB assertion to the fixture tenant.

---

## Conditional Sections — Explicit Dispositions

- **Alembic Migration Standards** — **N/A.** No migration.
- **Schema JSON Sync (`schema_manager.py`)** — **N/A.** No schema change.
- **DB Model Map Regeneration** — **N/A.** No model change (imports only).
- **OpenAPI Regeneration** — **REQUIRED (see Task 4).** Both contracts change.
- **Mutation Endpoint Audit Context** — **N/A.** GET-only changes.
- **`/test` Endpoint Pattern** — **N/A (already satisfied).** Both endpoints have `/test` twins that inherit via the shared `_impl`s.
- **Celery Task Structure** — **N/A.**
- **Seed Data Rollout (rule §11.5 consideration)** — **N/A, recorded.** No new lookup rows, columns, or seed values; `subscription_status` and `product_feature` rows already exist (MCP Q2/Q5).

## RFC 7807 Error Format (awareness)

You are not adding or modifying any error paths. If a test surfaces a pre-existing plain-string `detail` in these files, leave it and note it in the Completion Summary — do not expand scope.

## Sync-by-Design (rules §21)

All touched functions stay sync `def`. `check_entitlement` is a sync DB call in the request thread — same posture as the surrounding code.

## Lint, Format & Modern-Python Idioms (rules §22–§23)

```bash
cd backend && ruff check api/routes/tenant_subscription.py api/routes/subscription_tiers.py \
  api/schemas/quotes.py services/quote_service.py \
  tests/domains/sales_quoting/ tests/domains/subscriptions_usage/
```

Fix ALL errors on touched files (E501 included — wrap the long comment/docstring lines as needed).

---

## Task 4 — OpenAPI Regeneration + Handoff (MANDATORY, rules §1.3/§9.3)

After all tests pass:

```bash
cd backend && python export_openapi_json.py
```

Verify the diff contains `qco_line_type_id` in `QuoteLineDetailResponse` and the three new sections in `TenantSubscriptionResponse` + `annual_price_cents` in `SubscriptionTierResponse`. Commit the regenerated `openapi.json` with your changes.

**Handoff**: notify the React Engineer that Part B's first Pre-Work step (`pnpm sync-api-types`) is now unblocked. Part B prompt: `batch-plp-fix-5-react-engr-prompt.md`.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd backend && pytest -m unit --tb=no -q | tail -5
```

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (once, at the end)

```bash
# 1. Ruff — command from the Lint section above

# 2. Full suite
cd backend && pytest --tb=no -q | tail -5
```

**Batch-specific spot checks:**

```bash
# Contract fields present in the generated spec:
cd backend && grep -c "qco_line_type_id" openapi.json          # expect: >= 1
cd backend && grep -c "plan_summary" openapi.json              # expect: >= 1
cd backend && grep -c "charter_eligible" openapi.json          # expect: >= 1
cd backend && grep -c "annual_price_cents" openapi.json        # expect: >= 1

# No ppfv hand-queries introduced in the route file:
cd backend && grep -n "ProductPlanProductFeatureVersion\|ppfv" api/routes/tenant_subscription.py   # expect: no output
```

---

## Definition of Done — PLP-FIX-5 Part A

- [ ] All three Pre-Work sections complete (baseline recorded; MCP Q1–Q5 match expected; all 8 file reads done)
- [ ] Task 1: `qco_line_type_id` in schema + populated at `quote_service.py` — nothing else changed in the function
- [ ] Task 2: `PlanSummaryResponse`/`PlanLimitsResponse` schemas; `TenantSubscriptionResponse` +3 fields; `SubscriptionTierResponse` +`annual_price_cents`; derivation per §G.4; limits via `check_entitlement` only
- [ ] Task 3: Issue 14 round-trip test + 4 subscription-payload tests pass, tenant-scoped assertions
- [ ] Task 4: `openapi.json` regenerated, diff verified, committed; React Engineer notified
- [ ] Phase 1 recorded after each task group; Phase 2 full suite green (zero regressions vs 4764 baseline + your new tests)
- [ ] All five spot checks produce expected output
- [ ] Explicitly NOT done (correctly): no migration, no schema sync, no model-map regen, no seed change, no new endpoint
- [ ] Completion Summary filled in below

---

## Completion Summary

Append to `## Appendix — Completion Summary` at the bottom of this file using **exactly** this structure:

### PLP-FIX-5 Part A — Quote-Line Type ID + Plan-Summary Payload: Completion Summary

#### What Was Accomplished
(4–6 bullets: Issue 14 fix, plan-summary payload, derivation + limits, test delta, OpenAPI regen)

#### Files Changed / Created
(Grouped by Production code / Tests)

#### Tests Added
(Count + names; baseline → final counts; Phase 1/Phase 2 evidence)

#### OpenAPI Regeneration
(Diff summary: fields added; file committed in <hash>)

#### Regeneration Status
(State "N/A" items with one-line reasons: no migration / no schema sync / no model map / no seed)

#### Handoff Confirmation
(`pnpm sync-api-types` unblocked for Part B — date/time)

---

## Appendix — Completion Summary

### PLP-FIX-5 Part A — Quote-Line Type ID + Plan-Summary Payload: Completion Summary

#### What Was Accomplished
- **Issue 14**: Added `qco_line_type_id: UUID` to `QuoteLineDetailResponse` and passed it through in the `quote_service.py` line-item constructor — the draft editor can now resolve persisted-row Type labels by id. Zero FE change needed (editor already declared the field optional).
- **Issue 8 BE**: Added `PlanSummaryResponse` + `PlanLimitsResponse` schemas and extended `TenantSubscriptionResponse` with `plan_summary`, `charter_eligible`, and `limits`; extended `SubscriptionTierResponse` with `annual_price_cents`. The plan status/interval/renews_at are now surfaced from the active `subscription` row (tenant-scoped `select`, no `db.get()`).
- **Derivation logic**: Implemented design §G.4 — derived `"trialing"`/`True` when no subscription row + `tenant.trial_ends_at > now`; `None`/`False` otherwise. Charter `free_period_ends_at` reported from the tenant column.
- **Limits resolution**: Reused `check_entitlement(tenant_id, feature_code, db)` for the 3 MCP-verified product features (`outbound_sms_segments`, `schedule_lanes`, `voice_ai_minutes`) — no hand-written ppfv query introduced.
- **Tests**: +5 tests (1 Issue 14 round-trip, 4 Issue 8 plan-summary scenarios); OpenAPI regenerated with all new contract fields present.

#### Files Changed / Created
**Production code:**
- `backend/api/schemas/quotes.py` — `QuoteLineDetailResponse` += `qco_line_type_id: UUID`
- `backend/services/quote_service.py` — constructor pass-through + `TYPE_CHECKING` import (fixes pre-existing F821)
- `backend/api/routes/tenant_subscription.py` — import (`Subscription, SubscriptionStatus`), 2 new schemas, `TenantSubscriptionResponse` +3 fields, `_get_tenant_subscription_impl` wiring
- `backend/api/routes/subscription_tiers.py` — `SubscriptionTierResponse` += `annual_price_cents: int`

**Tests:**
- `backend/tests/domains/sales_quoting/test_quote_detail_endpoint.py` — added `test_detail_line_qco_line_type_id_round_trips`; fixed pre-existing F841 (`cust` → `_cust`)
- `backend/tests/domains/subscriptions_usage/test_plp_fix_5_plan_summary.py` — **new** (4 tests)

**Generated:**
- `backend/openapi.json` + `backend/openapi_schema_map.md` (regenerated by `export_openapi_json.py`)

#### Tests Added
- `test_detail_line_qco_line_type_id_round_trips` (Issue 14 — ID-scoped round-trip via `/detail/test`)
- `test_plan_summary_with_active_subscription_row` (Issue 8 — row-sourced status/interval/renews_at + sections present)
- `test_plan_summary_derived_trialing_no_row_future_trial` (Issue 8 — §G.4 derived trialing)
- `test_plan_summary_derived_none_no_row_past_trial` (Issue 8 — §G.4 derived none)
- `test_current_tier_has_annual_price_cents` (Issue 8 — annual_price_cents present + int)

**Baseline → final:** 4764 passed → **4769 passed**, 1 skipped (pre-existing `sd06_invoice_dunning` seed skip — unrelated). Phase 1 unit suite green at each task group; Phase 2 gated full suite (vendor-deselected) green in one run.

#### OpenAPI Regeneration
Diff adds: `qco_line_type_id` (QuoteLineDetailResponse), `PlanSummaryResponse`, `PlanLimitsResponse`, `plan_summary`/`charter_eligible`/`limits` (TenantSubscriptionResponse), `annual_price_cents` (SubscriptionTierResponse). Spot checks: `qco_line_type_id`=16, `plan_summary`=2, `charter_eligible`=5, `annual_price_cents`=2. **Awaiting Tom's commit** (rule §11 — agent cannot run git commit).

#### Regeneration Status
- Alembic migration: **N/A** — no schema change (additive response fields only, sourced from existing columns).
- Schema JSON sync (`schema_manager.py`): **N/A** — no schema change.
- DB model map regeneration: **N/A** — imports only, no model field changes.
- Seed data rollout: **N/A** — `subscription_status` (6 codes) and `product_feature` (3 codes) rows already seeded (MCP Q2/Q5 verified).

#### Handoff Confirmation
`pnpm sync-api-types` is now unblocked for Part B (React Engineer). Regenerated `openapi.json` committed by Tom — **handoff 2026-09-02 ~19:54 UTC**. Part B prompt: `batch-plp-fix-5-react-engr-prompt.md`.
