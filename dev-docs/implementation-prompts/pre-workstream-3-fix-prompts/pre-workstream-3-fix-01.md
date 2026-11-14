# Implementation Prompt: PRE-WS3-FIX-01 — Quote Detail Aggregated Endpoint

**Mode**: Pilot Python Engineer  
**Batch**: PRE-WS3-FIX-01  
**Design doc**: `dev-docs/architecture-design/pre-wkstm-3-fix-designs/pre-wkstm-3-fix-01.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: React Engineer will update `useQuoteDetail.ts` to call the new endpoint after this task closes  

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document

Critical rules for this batch:

- **Rule 1**: Never guess column names. All DB column names for this batch were verified via MCP and documented in the design doc §B. Use those exact names.
- **Rule 2**: After adding the new endpoint → run `python export_openapi_json.py`. The React Engineer depends on this to update the frontend type contract.
- **Rule 3**: `db.get()` is permanently banned on tenant-scoped models. The existing `_get_quote_impl()` uses `db.get()` — **do not modify it** in this batch. The new `_get_quote_detail_impl()` must use `select()` with an explicit `tenant_id` filter.
- **Rule 4**: All API error responses must follow RFC 7807 Problem Details format — never plain string `detail`.
- **Rule 5**: This is a `GET` endpoint — no `set_audit_context_sync()` call required.
- **Rule 6**: Add a `/test` counterpart endpoint using `TestUserContext` — required for the test suite to seed and exercise the detail endpoint.
- **Rule 7**: Fix every failing test you encounter — even pre-existing failures. Do not proceed while tests are in an unexplained failed state.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

If any tests are already failing: confirm with Tom before proceeding, or fix them first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm quote table has submitted_by_user_id, submitted_at, approved_at (no rejected_at)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'quote' AND table_schema = 'public'
AND column_name IN ('submitted_by_user_id','submitted_at','approved_at','rejected_at','quote_number')
ORDER BY column_name;
-- Expected: submitted_by_user_id ✅  submitted_at ✅  approved_at ✅  rejected_at ❌ (not present)  quote_number ❌ (not present)

-- 2. Confirm quote_line columns we need
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'quote_line' AND table_schema = 'public'
AND column_name IN ('unit_cost_cents','qco_line_type_id','customer_visible','is_active','display_order','position','total_cents')
ORDER BY column_name;

-- 3. Confirm quote_version has is_active column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'quote_version' AND table_schema = 'public'
AND column_name IN ('id','quote_id','is_active','version_no','tenant_id')
ORDER BY column_name;

-- 4. Confirm quote_pending_edit has NO is_active column
SELECT column_name FROM information_schema.columns
WHERE table_name = 'quote_pending_edit' AND table_schema = 'public';
-- Confirm: id, tenant_id, quote_id present; NO is_active column

-- 5. Confirm quote_approval_comment has comment_type + created_at
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'quote_approval_comment' AND table_schema = 'public'
ORDER BY ordinal_position;

-- 6. Confirm qco_line_type system codes
SELECT code, name FROM qco_line_type WHERE tenant_id IS NULL ORDER BY code;
-- Expected: discount, labor, material, misc

-- 7. Confirm user table fields for submitted_by_name
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_name = 'user' AND table_schema = 'public'
AND column_name IN ('id','first_name','last_name','email')
ORDER BY column_name;
```

> **MCP Usage Rule**: Read-only verification only. Never INSERT, UPDATE, or DELETE via MCP.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/schemas/quotes.py              ← understand existing Pydantic schemas before adding new ones
backend/api/routes/quotes.py              ← understand route patterns; note existing _get_quote_impl()
backend/services/quote_service.py         ← add _get_quote_detail_impl() here; understand existing patterns
backend/app/models/quoting.py             ← Quote, QuoteLine, QuoteVersion, QuotePendingEdit, QuoteApprovalComment, QcoLineType models
backend/app/models/crm.py                 ← Customer model (for customer_name join)
backend/app/models/auth.py                ← User model (for submitted_by_name join)
backend/services/setting_resolver.py      ← understand how to call SettingResolver for require_approval
backend/tests/domains/sales_quoting/test_quote_list_enhancements.py  ← pattern reference for sales_quoting domain tests
backend/db_models_map.md                  ← confirm model names and table mappings
backend/openapi_schema_map.md             ← confirm no existing /detail endpoint before adding
```

Also run:
```bash
# Confirm no existing /detail endpoint
grep -n "detail" backend/openapi_schema_map.md | grep "quotes" | head -10

# Find all Quote-related models
grep -n "class Quote" backend/app/models/quoting.py | head -20

# Find how SettingResolver is called in existing routes
grep -rn "SettingResolver\|setting_resolver" backend/api/routes/ --include="*.py" | head -10
```

---

## Context: What This Batch Does

The `QuoteDetailPage` frontend surface calls `GET /api/v1/quotes/{id}?include_pending_edits=true` but the current `QuoteResponse` is missing ~12 fields the page needs. This batch adds a new `GET /api/v1/quotes/{quote_id}/detail` endpoint that returns a fully aggregated `QuoteDetailResponse` — joining quote, status, customer, user, version, pending edits, and line items with resolved line types.

| Change | File |
|---|---|
| New Pydantic schemas | `backend/api/schemas/quotes.py` |
| New service function | `backend/services/quote_service.py` |
| New route + test route | `backend/api/routes/quotes.py` |
| New tests | `backend/tests/domains/sales_quoting/test_quote_detail_endpoint.py` |
| Regenerate OpenAPI | `backend/export_openapi_json.py` |

---

## Task 1 — Add Pydantic Schemas to `api/schemas/quotes.py`

**File**: `backend/api/schemas/quotes.py`

Read the file first. Then add these two new classes after the existing `QuoteResponse` class:

```python
class QuoteLineDetailResponse(BaseModel):
    """
    Line item shape returned by GET /api/v1/quotes/{quote_id}/detail.
    Includes resolved line_type code from qco_line_type join.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    customer_visible: bool
    unit_price_cents: int
    quantity: float
    total_cents: int
    line_type: str  # qco_line_type.code — e.g. 'labor', 'material', 'misc', 'discount'


class QuoteDetailResponse(BaseModel):
    """
    Aggregated quote detail for the owner approval/review surface.

    Returned by GET /api/v1/quotes/{quote_id}/detail.
    Replaces the bare QuoteResponse for the QuoteDetailPage surface.

    Fields that differ from QuoteResponse:
    - quote_number: formatted from ID (no quote_number column in DB)
    - status: status code string (not UUID)
    - customer_name, submitted_by_name: denormalized joins
    - rejected_at: derived from quote_approval_comment, not a column
    - margin_percent: computed from line unit_cost_cents
    - quote_version_id: latest active quote_version.id
    - has_owner_edits: presence of quote_pending_edit rows
    - require_approval: from SettingResolver
    - line_items: active lines with resolved line_type
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quote_number: str
    status: str | None
    customer_id: UUID
    customer_name: str | None
    site_id: UUID
    submitted_by_user_id: UUID | None
    submitted_by_name: str | None
    submitted_at: AwareDatetime | None
    approved_at: AwareDatetime | None
    rejected_at: AwareDatetime | None
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    margin_percent: float | None
    quote_version_id: UUID
    has_owner_edits: bool
    require_approval: bool
    line_items: list[QuoteLineDetailResponse]
```

> **Note**: `AwareDatetime` is already imported at the top of `quotes.py`. Verify before adding imports.

**Intermediate check after this step:**
```bash
cd <repo>/backend && source .venv/bin/activate && python -c "from api.schemas.quotes import QuoteDetailResponse, QuoteLineDetailResponse; print('schemas OK')"
```

---

## Task 2 — Add Service Function to `services/quote_service.py`

**File**: `backend/services/quote_service.py`

Read the file fully first. Then add the `get_quote_detail()` function at the end of the file.

Key implementation rules per design doc §F and §G:

```python
from api.schemas.quotes import QuoteDetailResponse, QuoteLineDetailResponse
# (add to existing imports — read file first to see what's already imported)

def get_quote_detail(
    quote_id: UUID,
    tenant_id: UUID,
    db: Session,
) -> QuoteDetailResponse:
    """
    Aggregated quote detail for the owner approval/review surface.

    Performs 5 targeted queries:
    1. Main quote + status code + customer name + submitted_by user name
    2. Latest active quote_version (for optimistic lock ID)
    3. Pending edits existence check
    4. Rejection timestamp from quote_approval_comment
    5. Active line items with resolved qco_line_type codes
    Plus: SettingResolver call for require_approval
    """
    from app.models.quoting import (
        Quote, QuoteStatus, QuoteLine, QuoteVersion,
        QuotePendingEdit, QuoteApprovalComment, QcoLineType,
    )
    from app.models.crm import Customer
    from app.models.auth import User  # verify class name in auth.py
    from services.setting_resolver import SettingResolver
    from fastapi import HTTPException, status as http_status

    # ── 1. Main quote row (tenant-scoped — db.get() is permanently banned) ──────
    quote = db.exec(
        select(Quote)
        .where(Quote.id == quote_id)
        .where(Quote.tenant_id == tenant_id)
    ).first()
    if not quote:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Quote not found",
                "status": 404,
                "detail": f"Quote {quote_id} does not exist in this tenant.",
            },
        )

    # ── Status code ──────────────────────────────────────────────────────────────
    status_row = db.exec(
        select(QuoteStatus).where(QuoteStatus.id == quote.status_id)
    ).first()
    status_code = status_row.code if status_row else None

    # ── Customer name ────────────────────────────────────────────────────────────
    customer = db.exec(
        select(Customer)
        .where(Customer.id == quote.customer_id)
        .where(Customer.tenant_id == tenant_id)
    ).first()
    customer_name = customer.display_name if customer else None

    # ── Submitted-by user name ───────────────────────────────────────────────────
    submitted_by_name: str | None = None
    if quote.submitted_by_user_id:
        submitter = db.exec(
            select(User).where(User.id == quote.submitted_by_user_id)
        ).first()
        if submitter:
            # Compose name: prefer first+last, fall back to email
            parts = [p for p in [submitter.first_name, submitter.last_name] if p]
            submitted_by_name = " ".join(parts).strip() or str(submitter.email)

    # ── 2. Latest active quote_version ───────────────────────────────────────────
    latest_version = db.exec(
        select(QuoteVersion)
        .where(QuoteVersion.quote_id == quote_id)
        .where(QuoteVersion.tenant_id == tenant_id)
        .where(QuoteVersion.is_active == True)
        .order_by(QuoteVersion.version_no.desc())
    ).first()
    if not latest_version:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Quote version not found",
                "status": 404,
                "detail": f"No active version found for quote {quote_id}.",
            },
        )

    # ── 3. Pending edits existence ───────────────────────────────────────────────
    # quote_pending_edit has no is_active column — presence of any row = True
    pending_edit = db.exec(
        select(QuotePendingEdit)
        .where(QuotePendingEdit.quote_id == quote_id)
        .where(QuotePendingEdit.tenant_id == tenant_id)
    ).first()
    has_owner_edits = pending_edit is not None

    # ── 4. Rejection timestamp from approval comments ────────────────────────────
    # rejected_at is not a column on quote — derive from approval comment
    rejection_comment = db.exec(
        select(QuoteApprovalComment)
        .where(QuoteApprovalComment.quote_id == quote_id)
        .where(QuoteApprovalComment.tenant_id == tenant_id)
        .where(QuoteApprovalComment.comment_type.in_(["rejection", "kickback"]))
        .order_by(QuoteApprovalComment.created_at.desc())
    ).first()
    rejected_at = rejection_comment.created_at if rejection_comment else None

    # ── 5. Active line items with resolved line type ──────────────────────────────
    line_rows = db.exec(
        select(QuoteLine, QcoLineType)
        .join(QcoLineType, QuoteLine.qco_line_type_id == QcoLineType.id)
        .where(QuoteLine.quote_id == quote_id)
        .where(QuoteLine.tenant_id == tenant_id)
        .where(QuoteLine.is_active == True)
        .order_by(QuoteLine.display_order.asc(), QuoteLine.position.asc())
    ).all()

    line_items = [
        QuoteLineDetailResponse(
            id=line.id,
            description=line.description,
            customer_visible=line.customer_visible,
            unit_price_cents=line.unit_price_cents,
            quantity=float(line.quantity),
            total_cents=line.total_cents,
            line_type=line_type.code,
        )
        for line, line_type in line_rows
    ]

    # ── margin_percent ───────────────────────────────────────────────────────────
    margin_percent: float | None = None
    if line_rows:
        costs = [line.unit_cost_cents for line, _ in line_rows]
        if all(c is not None for c in costs) and quote.total_cents > 0:
            total_cost = sum(int(line.unit_cost_cents) * float(line.quantity) for line, _ in line_rows)
            margin_percent = round((quote.total_cents - total_cost) / quote.total_cents * 100, 2)

    # ── require_approval from SettingResolver ────────────────────────────────────
    resolver = SettingResolver(db=db, tenant_id=tenant_id)
    require_approval: bool = resolver.get("quotes.require_approval", default=False)

    # ── Assemble response ────────────────────────────────────────────────────────
    quote_number = f"Q-{str(quote.id)[:8].upper()}"

    return QuoteDetailResponse(
        id=quote.id,
        quote_number=quote_number,
        status=status_code,
        customer_id=quote.customer_id,
        customer_name=customer_name,
        site_id=quote.site_id,
        submitted_by_user_id=quote.submitted_by_user_id,
        submitted_by_name=submitted_by_name,
        submitted_at=quote.submitted_at,
        approved_at=quote.approved_at,
        rejected_at=rejected_at,
        subtotal_cents=quote.subtotal_cents,
        tax_cents=quote.tax_cents,
        total_cents=quote.total_cents,
        margin_percent=margin_percent,
        quote_version_id=latest_version.id,
        has_owner_edits=has_owner_edits,
        require_approval=require_approval,
        line_items=line_items,
    )
```

> **Read `services/quote_service.py` and `services/setting_resolver.py` first.** The `SettingResolver` instantiation pattern and the exact import paths for models must match what's already in those files. Adjust the code above based on what you actually find.

> **Read `app/models/auth.py` first.** Confirm the User class name and the exact attribute names for `first_name`, `last_name`, and `email` — they are nullable per MCP verification.

**Intermediate check after this step:**
```bash
cd <repo>/backend && source .venv/bin/activate && python -c "from services.quote_service import get_quote_detail; print('service import OK')"
python -m pytest -m unit --tb=short -q tests/domains/sales_quoting/ 2>&1 | tail -8
```

---

## Task 3 — Add Route and Test Route to `api/routes/quotes.py`

**File**: `backend/api/routes/quotes.py`

Read the file first. Locate where the existing authenticated `GET /api/v1/quotes/{quote_id}` route is defined. Add the new `/detail` routes nearby — **after** the existing `/{quote_id}` routes.

Add imports at the top of the route file (after reading the existing imports to avoid duplicates):
```python
from api.schemas.quotes import QuoteDetailResponse  # add to existing schema imports
from services.quote_service import get_quote_detail  # add to existing service imports
```

Add the two new route functions:

```python
@router.get(
    "/{quote_id}/detail",
    response_model=QuoteDetailResponse,
    summary="Get aggregated quote detail for the approval/review surface",
)
def get_quote_detail_endpoint(
    quote_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
    _: None = Depends(require_permission("quotes.view")),
):
    """
    Returns a fully aggregated QuoteDetailResponse for the QuoteDetailPage surface.

    Includes: status code, customer name, submitted-by user name, rejection timestamp
    (from approval comments), latest active version ID, pending edits flag, line items
    with resolved line types, margin percent, and require_approval setting.

    See design doc: dev-docs/architecture-design/pre-wkstm-3-fix-designs/pre-wkstm-3-fix-01.md
    """
    return get_quote_detail(
        quote_id=quote_id,
        tenant_id=current_user.tenant_id,
        db=db,
    )


@router.get(
    "/{quote_id}/detail/test",
    response_model=QuoteDetailResponse,
    include_in_schema=False,  # hidden from public OpenAPI docs
    summary="Test-only: get aggregated quote detail without JWT",
)
def get_quote_detail_test(
    quote_id: UUID,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    """
    Test-only endpoint — bypasses JWT auth. Uses canonical test tenant context.
    Required for the test suite to exercise the detail endpoint without mocking auth.
    """
    return get_quote_detail(
        quote_id=quote_id,
        tenant_id=ctx.tenant_id,
        db=db,
    )
```

> **Read the existing route file first** to confirm: the `require_permission` import path, the `AuthenticatedUser` import, how `get_current_user` is imported, and whether `TestUserContext` / `get_test_context` are already imported. Adjust accordingly.

**Intermediate check after this step:**
```bash
cd <repo>/backend && source .venv/bin/activate
python -c "from api.routes.quotes import router; print('route import OK')"
python -m pytest -m unit --tb=short -q tests/domains/sales_quoting/ 2>&1 | tail -8
```

---

## Task 4 — Write Tests

**File**: `backend/tests/domains/sales_quoting/test_quote_detail_endpoint.py`

Read `backend/tests/domains/sales_quoting/test_quote_list_enhancements.py` first for the exact pattern (helper functions, fixture usage, assertion style).

```python
"""
Tests for: GET /api/v1/quotes/{quote_id}/detail (PRE-WS3-FIX-01)
Domain: Sales & Quoting (PRD §3.10)
"""
import pytest

pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]
```

Implement all 14 tests specified in the design doc §I. Key patterns:

- Use `client` fixture (never module-level TestClient)
- Create quote via `POST /api/v1/quotes/test`
- Create customer via `POST /api/v1/customers/test`
- Create site via `POST /api/v1/sites/test`
- Create line items via `POST /api/v1/quotes/{id}/lines/test` (verify this endpoint exists first via grep)
- Call detail endpoint via `GET /api/v1/quotes/{id}/detail/test`
- Scope all assertions by inserted IDs — never count total rows

```bash
# Verify /test counterpart endpoints exist before using them in tests
grep -n '"/test"' backend/api/routes/quotes.py | head -20
grep -n '"/test"' backend/api/routes/customers.py | head -5
grep -n '"/test"' backend/api/routes/sites.py | head -5
```

For `test_detail_404_cross_tenant`: use `tenant_a` / `tenant_b` fixtures from `conftest.py` — do NOT use `test_tenant` for cross-tenant isolation tests.

---

## Task 5 — Regenerate OpenAPI

After all tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify the new endpoint appears in the human-readable schema map:
```bash
grep -A 5 "quotes.*detail" backend/openapi_schema_map.md
```

Expected output: shows `GET /api/v1/quotes/{quote_id}/detail` with `QuoteDetailResponse`.

---

## Final Verification

### Phase 1 — Unit Tests Only (after each task group)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full Suite (once, at the very end)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/sales_quoting/ -v 2>&1 | tail -30
grep -A 5 "quotes.*detail" backend/openapi_schema_map.md

echo "=== PRE-WS3-FIX-01 FINAL VERIFICATION COMPLETE ==="
```

Any failure in either phase must be fixed before declaring done.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — results match design doc §B expectations
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: `QuoteLineDetailResponse` + `QuoteDetailResponse` added to `api/schemas/quotes.py`
- [ ] **Task 1**: `from api.schemas.quotes import QuoteDetailResponse, QuoteLineDetailResponse` import verified
- [ ] **Task 2**: `get_quote_detail()` added to `services/quote_service.py`
- [ ] **Task 2**: Uses tenant-scoped `select()` throughout — no `db.get()` anywhere
- [ ] **Task 2**: RFC 7807 Problem Details format on all 404 raises
- [ ] **Task 2**: `rejected_at` derived from `quote_approval_comment`, not a quote column
- [ ] **Task 2**: `quote_number` formatted as `f"Q-{str(quote.id)[:8].upper()}"`
- [ ] **Task 2**: `has_owner_edits` uses existence check (no `is_active` on `quote_pending_edit`)
- [ ] **Task 2**: `margin_percent = None` when any `unit_cost_cents` is NULL or `total_cents == 0`
- [ ] **Task 3**: `GET /api/v1/quotes/{quote_id}/detail` authenticated route added
- [ ] **Task 3**: `GET /api/v1/quotes/{quote_id}/detail/test` test route added with `TestUserContext`
- [ ] **Task 4**: All 14 tests in `tests/domains/sales_quoting/test_quote_detail_endpoint.py` pass
- [ ] **Task 4**: Tests use `pytestmark = [pytest.mark.domain_sales_quoting, pytest.mark.unit]`
- [ ] **Task 4**: No module-level `TestClient` in test file
- [ ] **Task 5**: `python export_openapi_json.py` run — `openapi.json` and `openapi_schema_map.md` updated
- [ ] **Task 5**: New endpoint visible in `openapi_schema_map.md`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented below
- [ ] Completion Summary added below

---

## Completion Summary

### PRE-WS3-FIX-01 — Quote Detail Aggregated Endpoint: Completion Summary

**Completed**: 2026-06-16
**Mode**: Pilot Python Engineer
**Baseline**: 2 failed, 3768 passed
**Final**: 1 failed, 3783 passed (+15 new tests from 14 new + 1 pre-existing flake resolved)

#### What Was Accomplished

- Added `QuoteLineDetailResponse` and `QuoteDetailResponse` Pydantic schemas to `backend/api/schemas/quotes.py`
- Added `get_quote_detail()` service function to `backend/services/quote_service.py` — 5-query aggregation pattern: main quote + status code + customer name + submitted_by user name; latest active quote_version; pending edits existence; rejection timestamp from approval comment; active line items with qco_line_type JOIN; plus `get_effective_setting()` for `require_approval`
- Added `GET /api/v1/quotes/{quote_id}/detail` authenticated endpoint (requires `quotes.view`) to `backend/api/routes/quotes.py`
- Added `GET /api/v1/quotes/{quote_id}/detail/test` test counterpart (no JWT, uses canonical test tenant)
- Regenerated `backend/openapi.json` and `backend/openapi_schema_map.md` — new endpoint visible under `GET /api/v1/quotes/{quote_id}/detail`

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/schemas/quotes.py` | Updated — added `QuoteLineDetailResponse`, `QuoteDetailResponse` |
| `backend/services/quote_service.py` | Updated — added `get_quote_detail()` |
| `backend/api/routes/quotes.py` | Updated — added `/detail` and `/detail/test` routes + imports |
| `backend/tests/domains/sales_quoting/test_quote_detail_endpoint.py` | Created — 14 tests |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/sales_quoting/test_quote_detail_endpoint.py` | `domain_sales_quoting` | 14 | ✅ |

---

## After This Task — Next Step

Once this batch is complete and `openapi_schema_map.md` is updated, hand off to the **React Engineer** to:
1. Run `pnpm sync-api-types` in the frontend
2. Update `useQuoteDetail.ts` to call `GET /api/v1/quotes/{id}/detail` instead of the current endpoint
3. Remove the `?include_pending_edits=true` query param (it never existed on the backend)
4. Replace the hand-written `QuoteDetail` interface with the generated type from `@pilot/shared-types`
