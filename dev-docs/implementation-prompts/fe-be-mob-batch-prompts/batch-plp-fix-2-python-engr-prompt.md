# Implementation Prompt: PLP-FIX-2 (Part A — Backend) — `GET /api/v1/qco-line-types` + Quote-Line FK Hardening

**Mode**: Pilot Python Engineer
**Batch**: PLP-FIX-2 — Part A (Backend) of a mixed batch (runs FIRST per architect-rules §1.3)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.22
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-2-design.md` — read sections A–G in full
**Bug report**: `dev-docs/analysis/PLP-testing-bugs-2026-08-30.md` — Issue 5
**Estimated session**: 1.5–2 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: `batch-plp-fix-2-react-engr-prompt.md` (Part B — starts ONLY after this batch closes and `pnpm sync-api-types` delivers `QcoLineTypeResponse`)
**Branch**: `feature/plp-founder-mvp-batches` (current head `1d3bb4d7`)
**Test baseline**: **4744 passed, 1 skipped, 0 failed** (PLP-FIX-1 close)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — in full
- **`backend/README-adding-tests.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-plp-fix-2-design.md`** — every section (A–I)

Critical rules for this batch:

- **Rule 4 (`db.get()` banned on tenant-scoped models)**: the new validation query in `_create_quote_line_impl` MUST use `select()` with an explicit tenant predicate (`tenant_id == :tid OR tenant_id IS NULL`), never `db.get(QcoLineType, id)`.
- **Rule 13 (RFC 7807)**: the new 404 raise MUST use the detail-dict shape (`type`/`title`/`status`/`detail`). Plain-string `detail` is banned for new code.
- **Rule 17 (phantom-gate rule)**: the new endpoint carries **RBAC only** (`require_permission("quotes.view")`) — **NO `feature_code`**. QCO line types are not a PRD §3.11 priced feature. Do not add one "for consistency."
- **Rule 17b**: a new entity route requires a `/test` counterpart — Task 2 includes it.
- **Rule 21 (sync-by-design)**: plain `def` route + sync `Session`. Never `async def` with the blocking session.
- **Rule 22/23**: Pydantic v2 idioms; Ruff clean on changed files (fix ALL errors in files you touch).
- **Test isolation (Rule 16)**: assert by `code` (stable), never by total row count or hardcoded UUID — seed data varies by environment **by design** (that is the entire lesson of Issue 5).

---

## Background / Context

Production smoke testing after PLP-FIX-1 hit **Issue 5**: quote "Save Draft" → "Network Error" + ASGI `ForeignKeyViolation: quote_line_qco_line_type_id_fkey` on key `bb1588c7-…`. Root cause chain:

1. `qco_line_type` rows are seeded **independently per environment** — dev and prod have different UUIDs for the same `code` (`labor`, `material`, `misc`, `discount`, `note`; all `tenant_id NULL` platform rows).
2. The frontend `LineItemEditor.tsx` hardcoded **dev** UUIDs — so prod quote-line inserts referenced nonexistent UUIDs.
3. No `GET` endpoint exists for line types, so the frontend had no alternative.
4. `_create_quote_line_impl` inserts `qco_line_type_id` **unchecked** → the FK violation surfaces as a raw 500 ASGI traceback at `db.flush()` instead of a diagnosable API error.

This batch (Part A) ships the backend half: the read-only lookup endpoint the frontend will consume, plus validate-before-insert hardening so a bad type UUID can never again become a 500. Part B (React Engineer) then deletes the hardcoded UUIDs.

**No migration. No seed changes. No DB data changes of any kind.** Every environment already has the 5 platform rows — codes are the stable cross-environment key.

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Endpoint placement | New route file `api/routes/qco_line_types.py` at prefix `/api/v1/qco-line-types` | `quotes` router's `/{quote_id}` segment makes static sub-paths order-fragile; lookup precedent is standalone (`job-types`, `job-expense-categories`) |
| Permission | `quotes.view`, no `feature_code` | Phantom-gate rule; consumers are quote-building surfaces |
| Merge rule | Platform (`tenant_id IS NULL`) ∪ tenant rows, tenant wins on `code`, `is_active=true` only, sorted by `name` | Mirrors CLASS-B1 `job_types.py` exactly (no `sort_order` column on this table) |
| Response fields | `id, code, name, is_default, is_active, is_tenant_override` — **exclude** `qb_item_name_hint` | Hint is an internal QB-mapping concern, not a client contract |
| Hardening status code | **404** (not 422) | Resource-reference miss; anti-enumeration; consistent with adjacent `Quote not found` 404 |
| Invoices path | **Unchanged** | `_persist_custom_lines` resolves `misc` by **code** (PLP-FIX-1) — environment-safe already |
| Seed/migration | **None** | Environments own their UUIDs; codes are the contract |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/backend
source .venv/bin/activate
pytest -m unit --tb=no -q | tail -5
```

Record the exact counts (expected: **4744 passed, 1 skipped**). These must still pass at the end of the batch.

> **If any tests are already failing before you start**: do NOT treat them as "pre-existing" and proceed. Fix them or confirm with Tom before writing any batch code.

## Pre-Work: Run MCP Verification Queries

Using the `postgres-local` MCP server (read-only — verification only), run ALL of these before writing any SQL or SQLModel references:

```sql
-- 1. qco_line_type columns (design-time result: id, tenant_id [nullable], code,
--    name, is_default, is_active, qb_item_name_hint + created_at/updated_at/created_by/updated_by)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'qco_line_type'
ORDER BY ordinal_position;

-- 2. Platform rows (design-time result: 5 rows, all tenant_id NULL, all active:
--    labor [is_default=true], material, misc, discount, note)
SELECT id, tenant_id, code, name, is_default, is_active
FROM public.qco_line_type
ORDER BY tenant_id NULLS FIRST, code;

-- 3. Confirm the FK that fired in prod (name + column) so the hardening targets the right relationship
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.quote_line'::regclass
  AND contype = 'f'
  AND conname LIKE '%qco_line_type%';
```

If any result differs materially from the design-time values noted → **STOP and ask Tom** before proceeding.

Also verify no route already serves this (expect zero matches):

```bash
grep -rn "qco-line-types\|qco_line_types" <repo>/backend/api/ <repo>/backend/app/main.py
grep -n "qco-line-types" <repo>/backend/openapi_schema_map.md
```

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

| File | Why |
|---|---|
| `backend/api/routes/job_types.py` (full — 87 lines) | **The pattern to copy**: `_list_*_impl` + auth route + `/test` twin, platform∪tenant merge, `is_tenant_override` flag |
| `backend/api/routes/quotes.py` lines 387–538 (`_create_quote_line_impl`) and 1072–1128 (`create_quote_line_test`) | The FK hardening insertion point and the `/test` twin that also flows through the impl |
| `backend/api/schemas/quotes.py` lines 160–235 (`QuoteLineCreate`/`QuoteLineResponse`) | Where `QcoLineTypeResponse` will live (quote-domain schema file) |
| `backend/api/schemas/schemas.py` lines 291–306 (`JobTypeResponse`) | Response-schema shape to mirror |
| `backend/app/models/quoting.py` lines 76–107 (`QcoLineType`) | Model fields; note `tenant_id` nullable (platform = NULL) |
| `backend/app/main.py` lines 16–100 (imports) and 153–175 (router registrations) | Where to add the import + `include_router` |
| `backend/tests/domains/sales_quoting/test_plp_fix1_quote_create_no_gate.py` (full) | Authenticated-path fixture pattern (`setup_test_user`, `mock_cognito_jwt_verify`, `skip_mock_entitlement_allowed`) |
| `backend/tests/domains/sales_quoting/test_quote_detail_endpoint.py` lines 1–100 | Existing quote-line `/test` setup pattern in this domain folder |
| `backend/tests/domains/field_operations/test_class_b1_job_priority_type.py` lines 49–117 | Lookup-endpoint test pattern (platform defaults / tenant override shadows / inactive excluded) |

---

## Task 1 — `QcoLineTypeResponse` schema

**File**: `backend/api/schemas/quotes.py` — add near `QuoteLineCreate` (after the `--- Quote Lines ---` section header is fine).

```python
class QcoLineTypeResponse(BaseModel):
    """PLP-FIX-2: response for a single QCO line-type lookup entry.

    Platform rows (tenant_id IS NULL) are visible to every tenant; a tenant
    row with the same code shadows the platform row (is_tenant_override=True).
    ``qb_item_name_hint`` is intentionally excluded — internal QB concern.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    is_default: bool
    is_active: bool
    is_tenant_override: bool = False
```

Confirm the file's existing imports cover `ConfigDict`, `BaseModel`, `UUID` (they do — used by neighboring classes).

## Task 2 — New route file `api/routes/qco_line_types.py`

**File (new)**: `backend/api/routes/qco_line_types.py`

Copy the structure of `backend/api/routes/job_types.py` **1:1** — same impl/route/test-twin layout, same merge logic, adjusted for this model (`name` instead of `label`; **no `sort_order`** — sort by `name` only):

```python
"""PLP-FIX-2: GET /api/v1/qco-line-types — list active QCO line types (platform defaults ∪ tenant overrides).

Tenant rows override platform rows on matching code.
Read-only lookup — no create/edit endpoints in this batch.
Created so the frontend never hardcodes per-environment seed UUIDs again (Issue 5).
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from api.schemas.quotes import QcoLineTypeResponse
from app.models.quoting import QcoLineType
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


def _list_qco_line_types_impl(
    db: Session,
    tenant_id,
) -> list[QcoLineTypeResponse]:
    """Shared logic — called by both authenticated and test endpoints.

    Resolution rule (identical to job_types):
    1. Fetch ALL active platform rows (tenant_id IS NULL).
    2. Fetch ALL active tenant-specific rows for this tenant.
    3. Build a dict keyed by code — tenant row wins on conflict.
    4. Return sorted by name (no sort_order column on this table).
    """
    platform_rows = db.exec(
        select(QcoLineType)
        .where(QcoLineType.tenant_id == None)
        .where(QcoLineType.is_active == True)
    ).all()

    tenant_rows = db.exec(
        select(QcoLineType)
        .where(QcoLineType.tenant_id == tenant_id)
        .where(QcoLineType.is_active == True)
    ).all()

    merged: dict[str, tuple[QcoLineType, bool]] = {}
    for row in platform_rows:
        merged[row.code] = (row, False)
    for row in tenant_rows:
        merged[row.code] = (row, True)

    sorted_entries = sorted(merged.values(), key=lambda x: x[0].name)

    return [
        QcoLineTypeResponse(
            id=row.id,
            code=row.code,
            name=row.name,
            is_default=row.is_default,
            is_active=row.is_active,
            is_tenant_override=is_override,
        )
        for row, is_override in sorted_entries
    ]


@router.get("", response_model=list[QcoLineTypeResponse])
def list_qco_line_types(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
) -> list[QcoLineTypeResponse]:
    """List active QCO line types (platform defaults + tenant overrides, tenant wins on code)."""
    return _list_qco_line_types_impl(db, current_user.tenant_id)


@router.get("/test", response_model=list[QcoLineTypeResponse])
def list_qco_line_types_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> list[QcoLineTypeResponse]:
    """Test-only endpoint — bypasses JWT, uses canonical test tenant."""
    return _list_qco_line_types_impl(db, ctx.tenant_id)
```

> Adjust imports to match what you actually find in `job_types.py` — the example above was derived from it, but read both files first.

## Task 3 — Register the router in `app/main.py`

**File**: `backend/app/main.py`

1. Add `qco_line_types,` to the `from api.routes import (...)` block — alphabetical position (after `public_tenant_sites,` / before `quote_templates,`).
2. Add the registration immediately after the `quotes` router registration (~line 168):

```python
app.include_router(
    qco_line_types.router,
    prefix="/api/v1/qco-line-types",
    tags=["quotes"],
)  # PLP-FIX-2: QCO line-type lookup (platform defaults ∪ tenant overrides, read-only)
```

## Task 4 — FK hardening in `_create_quote_line_impl`

**File**: `backend/api/routes/quotes.py`

Insert the validation **immediately after the quote ownership check** (~line 414, before the `unit_price_cents` line) so a bad type UUID fails fast with zero side effects:

```python
    quote = db.get(Quote, quote_id)
    if not quote or quote.tenant_id != user_context.tenant_id:
        raise HTTPException(status_code=404, detail="Quote not found")

    # PLP-FIX-2: validate the line type BEFORE any insert — a bad UUID previously
    # surfaced as a raw 500 ForeignKeyViolation at db.flush() (prod Issue 5).
    # Platform rows (tenant_id IS NULL) are valid for every tenant.
    if line_in.qco_line_type_id is not None:
        line_type = db.exec(
            select(QcoLineType).where(
                QcoLineType.id == line_in.qco_line_type_id,
                (QcoLineType.tenant_id == user_context.tenant_id)
                | (QcoLineType.tenant_id == None),
                QcoLineType.is_active == True,
            )
        ).first()
        if not line_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://errors.pilotfortrades.com/not-found",
                    "title": "Line type not found",
                    "status": 404,
                    "detail": f"qco_line_type_id {line_in.qco_line_type_id} does not exist or is not active.",
                },
            )
```

Notes:

- `QcoLineType` is **already imported** in this file (verify against the `from app.models.quoting import (...)` block at lines 47–63; add it if absent).
- `select`, `status`, `HTTPException` are already imported.
- Do **not** change the pre-existing `detail="Quote not found"` string two lines above (mechanical-uplift ban — TEST-UPLIFT-1A owns that class).
- Both the authenticated (`POST /{quote_id}/lines`) and `/test` (`POST /{quote_id}/lines/test`) endpoints flow through this impl — one change covers both.
- Do **not** add the same guard to `_persist_custom_lines` in `invoices.py` — it resolves by code (`misc`), which is environment-safe (Design §G.6).

---

## Alembic Migration Standards

**N/A — this batch has no migration.** Alembic head stays `c8d06a6ffdd2`. Stated explicitly so the absence is verifiable.

## Schema JSON Sync

**N/A — no DB schema change.** `pilot-db-schema-v2.6h.json` untouched (no `schema_manager.py` run).

## DB Model Map Regeneration

**N/A — no model added or modified.** `QcoLineType` already exists in `backend/app/models/quoting.py` and is already in `db_models_map.md`.

## Mutation Endpoint Audit Context

**N/A for new code** — the only new endpoint is a GET. The hardened path (`POST /quotes/{id}/lines`) already runs inside the existing endpoint's audit-context chain; no new mutation endpoint is introduced.

## Seed Data Rollout (Core + Scenario)

**N/A — this batch adds/modifies zero DB rows, columns, tables, enums, or lookup values** (architect-rules §11.5 acknowledgment). `qco_line_type` already carries its 5 platform rows in every environment; the batch's premise is that codes — not UUIDs — are the cross-environment contract. No `seed_core.py` / `seed_platform.py` / `seed_scenario_*.py` changes; no `README-seed-data.md` §4 update.

## RFC 7807 Error Format (awareness)

All new error responses use RFC 7807 Problem Details. The frontend `apiClient` parses this format to drive severity routing. Task 4's 404 uses the required detail-dict shape; plain-string `detail` is banned for new code. Return `404` (not `403`) for scoped misses — prevents UUID enumeration.

## Sync-by-Design (rules §21)

The new route is a plain `def` with a sync `Session` — FastAPI offloads to a threadpool. Never `async def` a route that uses the blocking session.

---

## Test Requirements

**New file**: `backend/tests/domains/sales_quoting/test_plp_fix2_qco_line_types.py`

```python
pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]
```

Domain folder mapping: `sales_quoting` (PRD §3.10). Autouse fixtures (from conftest — already active, do not re-create):

| Fixture | Behavior | Skip marker |
|---|---|---|
| `mock_entitlement_allowed` | Auto-allows all entitlement checks in unit tests | `@pytest.mark.skip_mock_entitlement_allowed` |
| `mock_cognito_jwt_verify` | Auto-mocks Cognito JWT verification | `@pytest.mark.skip_mock_cognito_jwt_verify` |

Test cases (copy the patterns from the three test files in Pre-Work reads — `/test` twins need no auth; the one authenticated-path test uses `setup_test_user(client, db_session)` from `tests.test_phase2`):

| # | Test | Pattern source |
|---|---|---|
| 1 | `GET /api/v1/qco-line-types/test` → 200; response codes include `{labor, material, misc, discount, note}` — **assert by code, never by count or UUID** (Rule 16) | CLASS-B1 `test_returns_platform_defaults` |
| 2 | Exactly one row has `is_default=True` and its code is `labor` (documents current seed truth) | same |
| 3 | Tenant override shadows platform: insert a `QcoLineType` row for `test_tenant.id` with `code="misc"`, different name → response has exactly ONE `misc` row, the tenant's, `is_tenant_override is True`. Set `created_at`/`updated_at` explicitly per the CLASS-B1 pattern | CLASS-B1 `test_tenant_override_shadows_platform` |
| 4 | Inactive rows excluded: insert platform (`tenant_id=None`) row with unique code + `is_active=False` → its code absent from response | CLASS-B1 `test_inactive_rows_excluded` |
| 5 | Authenticated path smoke: `setup_test_user` → `GET /api/v1/qco-line-types` with headers → 200, same shape | PLP-FIX-1 test file |
| 6 | **FK hardening — the Issue-5 regression test**: create quote via `/api/v1/quotes/test` (use the existing setup pattern in `test_quote_detail_endpoint.py` lines 1–100), then `POST /api/v1/quotes/{id}/lines/test` with `"qco_line_type_id": str(uuid.uuid4())` → **404**, and the body is RFC 7807: `detail["status"] == 404`, `detail["title"] == "Line type not found"`, `detail["type"]` startswith `https://errors.pilotfortrades.com/` | this batch |
| 7 | Happy path unchanged: same setup, POST the line with the **real** `misc` type id (query it from `qco_line_type` by `code="misc"` via `db_session` — never hardcode a UUID) → 201 | `test_quote_detail_endpoint.py` |

**Test resilience rules that matter here**: tests 3, 4, 6, 7 scope assertions by inserted IDs/codes; nothing asserts on total counts; nothing hardcodes a seed UUID.

Run after Tasks 1–4 (Phase 1):

```bash
cd <repo>/backend
source .venv/bin/activate
pytest tests/domains/sales_quoting/test_plp_fix2_qco_line_types.py -v --tb=short 2>&1 | tail -20
pytest tests/domains/sales_quoting/ -m unit --tb=no -q 2>&1 | tail -5
```

---

## Regenerate OpenAPI

**Required — new endpoint added.** From `backend/` with the venv active:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Then verify the endpoint landed:

```bash
grep -n "qco-line-types" openapi.json | head -5
grep -n "QcoLineTypeResponse" openapi.json | head -3
```

Regenerate `openapi_schema_map.md` per the house process (same script generates it, or follow the documented regen step in `backend/README-adding-tests.md` if separate).

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
pytest -m unit --tb=no -q | tail -5
```

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# 1. Ruff — changed files only (backend/-relative paths; fix ALL errors)
ruff check api/routes/qco_line_types.py api/routes/quotes.py api/schemas/quotes.py app/main.py tests/domains/sales_quoting/test_plp_fix2_qco_line_types.py --fix
ruff format api/routes/qco_line_types.py api/routes/quotes.py api/schemas/quotes.py app/main.py tests/domains/sales_quoting/test_plp_fix2_qco_line_types.py

# 2. Full suite minus slow vendor/live-service markers
pytest -m "not integration and not e2e and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis" --tb=no -q | tail -5
```

Expected: baseline (4744) **+7 new tests** = 4751 passed, 1 skipped, 0 failed.

Batch-specific spot checks:

```bash
# New endpoint appears in the app
grep -n "qco-line-types" openapi.json | head -3

# No feature_code wired anywhere in the new route file (phantom-gate rule)
grep -n "feature_code" api/routes/qco_line_types.py   # expect: no output
```

Any failure in either phase must be fixed before declaring the batch done — including failures that appear pre-existing. If you cannot identify the root cause → STOP and ask Tom.

---

## Definition of Done — PLP-FIX-2 Part A

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (4744 passed / 1 skipped / 0 failed, or deltas explained to Tom)
- [ ] All 3 MCP verification queries run; results match design-time values (or Tom consulted)
- [ ] Zero-match grep confirmed no existing `qco-line-types` route
- [ ] Design doc sections A–G read before writing any code
- [ ] All 9 Pre-Work source files read before modifying
- [ ] **Task 1**: `QcoLineTypeResponse` added to `api/schemas/quotes.py`
- [ ] **Task 2**: `api/routes/qco_line_types.py` created (impl + auth GET + `/test` twin; no `feature_code`)
- [ ] **Task 3**: router registered in `app/main.py` (import + `include_router` after quotes)
- [ ] **Task 4**: validate-before-insert guard in `_create_quote_line_impl` (RFC 7807 404; tenant-scoped `select()`; pre-existing string-detail 404 untouched)
- [ ] No migration created; no seed script touched; no schema JSON change; no model-map change
- [ ] New test file `tests/domains/sales_quoting/test_plp_fix2_qco_line_types.py` — all 7 tests pass
- [ ] Tests assert by code/inserted-ID — zero hardcoded seed UUIDs, zero total-count assertions
- [ ] `python export_openapi_json.py` run; `qco-line-types` + `QcoLineTypeResponse` verified in `openapi.json`; `openapi_schema_map.md` regenerated
- [ ] Phase 1: `pytest -m unit --tb=no -q` passes with zero regressions
- [ ] Phase 2: Ruff clean on all 5 changed files + full vendor-deselected suite passes (4751/1/0 expected)
- [ ] Handoff Instructions (below) completed
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)

---

## Handoff Instructions (to React Engineer — MANDATORY, architect-rules §1.3/§9.3)

Part B (`batch-plp-fix-2-react-engr-prompt.md`) is gated on this batch. Before declaring Part A done:

1. Run `python export_openapi_json.py` (already in DoD) and confirm `QcoLineTypeResponse` is in `openapi.json`.
2. Commit all backend changes to `feature/plp-founder-mvp-batches` with a message referencing PLP-FIX-2.
3. Notify Tom that Part A is closed — Part B's first Pre-Work step is `pnpm sync-api-types`, which must deliver `components["schemas"]["QcoLineTypeResponse"]` into `packages/shared-types/src/api-schema.d.ts`.
4. **Deploy note for Tom**: the backend must deploy BEFORE the frontend — Part B's new hook calls `GET /api/v1/qco-line-types`, which 404s until this ships.

---

## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix below using the exact format.
2. This batch closes no task tracked in another source spec (the bug report is an analysis doc, not a tracker) — no external spec headers to flip.

## Appendix — Completion Summary

### PLP-FIX-2 Part A — QCO Line-Type Endpoint + FK Hardening: Completion Summary

**Completed**: 2026-09-01
**Mode**: Pilot Python Engineer
**Baseline**: 4744 passed, 1 skipped, 0 failed
**Final**: 4751 passed, 1 skipped, 0 failed (+7 new tests)

#### What Was Accomplished

- New `GET /api/v1/qco-line-types` lookup endpoint (+ `/test` twin) — platform defaults + tenant overrides, tenant wins on `code`, sorted by `name`, `is_active=true` only, `qb_item_name_hint` excluded from response
- Validate-before-insert hardening on quote-line creation in `_create_quote_line_impl` — RFC 7807 404 replaces the raw 500 `ForeignKeyViolation` that surfaced in prod (Issue 5)
- Root cause of prod Issue 5 (frontend-observed) addressed at the API layer: a bad `qco_line_type_id` now fails fast with a diagnosable 404 before any `db.add()`/`db.flush()`
- No migration, no seed changes, no schema JSON change, no model-map regeneration — codes are the cross-environment contract, every environment already has the 5 platform rows

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/schemas/quotes.py` | Created — `QcoLineTypeResponse` (Pydantic v2, `from_attributes=True`, excludes `qb_item_name_hint`) |
| `backend/api/routes/qco_line_types.py` | Created — `_list_qco_line_types_impl` + auth `GET ""` + `GET "/test"` twin; RBAC-only `quotes.view`, no `feature_code` |
| `backend/app/main.py` | Updated — `qco_line_types` import (alphabetical) + `include_router` at `/api/v1/qco-line-types` after the `quotes` router |
| `backend/api/routes/quotes.py` | Updated — `QcoLineType` added to import block; validate-before-insert guard in `_create_quote_line_impl` (tenant-scoped `select()`, RFC 7807 404) |
| `backend/tests/domains/sales_quoting/test_plp_fix2_qco_line_types.py` | Created — 7 tests (5 lookup + 2 FK hardening) |
| `backend/openapi.json` / `backend/openapi_schema_map.md` | Regenerated via `export_openapi_json.py` — both `/api/v1/qco-line-types` paths + `QcoLineTypeResponse` schema verified present |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `tests/domains/sales_quoting/test_plp_fix2_qco_line_types.py` | Unit | 7 | ✅ |

#### Test Details

| # | Test | Verifies |
|---|---|---|
| 1 | `test_returns_platform_defaults` | `/test` returns 200; codes ⊇ {labor, material, misc, discount, note} — asserted by code, not UUID/count |
| 2 | `test_exactly_one_default_and_it_is_labor` | Exactly one `is_default=True` row, code=`labor` (documents seed truth) |
| 3 | `test_tenant_override_shadows_platform` | Tenant `misc` override → exactly 1 `misc` row, tenant's name, `is_tenant_override=True` |
| 4 | `test_inactive_rows_excluded` | Inactive platform row (unique code) absent from response |
| 5 | `test_authenticated_path_smoke` | Authenticated `GET /api/v1/qco-line-types` with `setup_test_user` headers → 200, same shape |
| 6 | `test_bad_line_type_id_returns_rfc7807_404` | **Issue 5 regression** — random UUID → 404 RFC 7807 (`status=404`, `title="Line type not found"`, `type` startswith `https://errors.pilotfortrades.com/`) |
| 7 | `test_happy_path_with_real_misc_type_id` | Real `misc` id (queried by code via `db_session`, never hardcoded) → 201 |

#### Verification Results

- **Phase 1 (unit)**: `pytest -m unit --tb=no -q` → 4751 passed, 1 skipped, 96 deselected (47.44s)
- **Phase 2 (full vendor-deselected)**: `pytest -m "not integration and not e2e and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis" --tb=no -q` → 4751 passed, 1 skipped, 96 deselected (48.89s)
- **Ruff**: `ruff check` on all 5 changed files → "All checks passed!" (after fixing 2 RUF003 ambiguous-unicode-comment warnings — replaced `∪` with `+`)
- **Phantom-gate spot check**: `grep -n "feature_code" api/routes/qco_line_types.py` → no output (exit 1) — no phantom gate wired
- **OpenAPI**: `grep "qco-line-types" openapi.json` → both `/api/v1/qco-line-types` and `/api/v1/qco-line-types/test` present; `QcoLineTypeResponse` schema present at `#/components/schemas/QcoLineTypeResponse`
- **MCP verification**: `qco_line_type` columns, 5 platform rows (all `tenant_id NULL`, all active, `labor` is default), and `quote_line_qco_line_type_id_fkey` all confirmed against `postgres-local` before any code was written

#### Handoff to React Engineer (Part B)

Part B (`batch-plp-fix-2-react-engr-prompt.md`) is gated on this batch. Before declaring Part A closed:

1. ✅ `python export_openapi_json.py` run — `QcoLineTypeResponse` is in `openapi.json`
2. ⏳ Tom to commit all backend changes to `feature/plp-founder-mvp-batches` with a message referencing PLP-FIX-2
3. ⏳ Tom to notify that Part A is closed — Part B's first Pre-Work step is `pnpm sync-api-types`, which must deliver `components["schemas"]["QcoLineTypeResponse"]` into `packages/shared-types/src/api-schema.d.ts`
4. ⏳ **Deploy note for Tom**: the backend must deploy BEFORE the frontend — Part B's new hook calls `GET /api/v1/qco-line-types`, which 404s until this ships
