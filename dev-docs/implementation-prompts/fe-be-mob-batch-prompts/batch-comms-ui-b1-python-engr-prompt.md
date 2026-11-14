# Implementation Prompt: COMMS-UI-B1 (Part A — Backend) — Recent Communications: Search + Filter + Canonical Pagination

**Mode**: Pilot Python Engineer
**Batch**: COMMS-UI-B1 (Part A of a mixed BE + web-FE batch — **Python runs FIRST**)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 → COMMS-UI-B1
**Design doc**: none (self-contained; endpoint already exists — this batch extends it)
**Estimated session**: 2–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: COMMS-UI-B1 (Part B — React Engineer) — `batch-comms-ui-b1-react-engr-prompt.md`. Do NOT start it until this half is merged and `python export_openapi_json.py` has run.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the hard rules are non-negotiable STOPs.
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §16 (Standard Task Workflow). (No migration in this batch — §13 not required.)
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, and fixture rules.

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`). This is the handoff signal to the React Engineer.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is banned on tenant-scoped models. This batch's query is already correctly tenant-scoped via `customer_communication_thread.tenant_id` — preserve that join-based isolation.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 12 (sync routes — rules §21)**: This app is **synchronous by design**. The `/recent` + `/recent/test` handlers and `_get_recent_communications_impl` all touch the sync `Session` and MUST stay plain `def`. Do NOT "modernize" any of them to `async def` — that runs the blocking psycopg2 call on the event loop and stalls all requests.
- **Rule 13 (Pydantic v2 — rules §22)**: `RecentCommunicationsResponse` and `CommunicationSummaryItem` are Pydantic v2 models — use v2 idioms only (`model_config = ConfigDict(...)`, no `class Config`/`@validator`/`.dict()`). Every route keeps its `response_model`. No float money fields (N/A here, but the rule stands).
- **Rule 14 (Ruff — rules §23)**: Ruff 0.15 is the linter+formatter. Run `ruff check . --fix && ruff format .` before declaring done. Do not hand-order imports (isort `I` is enforced); use modern typing (`str | None`, `list[X]`).
- **Rule 16 (verify, don't assume — rules §25)**: 186 tables exist. Query `information_schema.columns` for every table this batch touches (`customer_communication_message`, `customer_communication_thread`, `customer`) before writing SQL — see the MCP pre-work below. The prompt's column names are Architect-provided; the live DB is the only authoritative source.

> **This batch adds NO new endpoint and NO migration.** It extends the query params + response shape of the **existing** `GET /api/v1/communications/recent` (and its `/recent/test` twin). Do not create a new route.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: do NOT treat them as "pre-existing" and proceed. Either (a) confirm with Tom this is a known accepted failure, OR (b) fix it before touching batch files.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` is for **read-only verification only**. Never INSERT/UPDATE/DELETE. If a query errors → STOP and ask Tom.

Run **all** of these before writing any code. They confirm the column names this batch's SQL will use (the endpoint already exists, but the live DB is the only authoritative source — the JSON schema may be stale):

```sql
-- 1. Confirm message columns used in the query + new filters (channel, direction, body, created_at, thread_id)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer_communication_message'
ORDER BY ordinal_position;

-- 2. Confirm the thread join + tenant isolation column (tenant_id, customer_id)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer_communication_thread'
ORDER BY ordinal_position;

-- 3. Confirm customer.display_name for the customer_search ilike filter
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer'
  AND column_name IN ('id', 'tenant_id', 'display_name');

-- 4. Reality check on channel values present (drives the "channel filter" design decision below)
SELECT channel, direction, count(*)
FROM customer_communication_message
GROUP BY channel, direction
ORDER BY channel, direction;
```

**Expected (verified by the Architect 2026-07-28)**:
- `customer_communication_message`: `id`, `thread_id`, `direction (text)`, `channel (text, default 'sms')`, `body (text)`, `created_at (timestamptz)` — all present.
- `customer_communication_thread`: `tenant_id`, `customer_id` — present. **Tenant isolation is via the thread join, NOT a `tenant_id` on the message table.**
- `customer.display_name` — present (`character varying`).
- Query 4 today returns **only `channel = 'sms'`** rows (inbound + outbound). There are **no email rows** in this table — email lives in the notification outbox, not here. See Design Decision D-1.

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/api/routes/communications.py         ← lines 779–919: the BETA-B1 recent-aggregate block you are extending (CommunicationSummaryItem, RecentCommunicationsResponse, _get_recent_communications_impl, both endpoints). Read lines 1–45 for imports.
backend/api/routes/customers.py              ← lines 140–210: the canonical UI-FIX-1C offset/limit + search ilike + PaginatedResponse pattern to mirror exactly
backend/tests/conftest.py                    ← available fixtures (client, test_tenant, test_user, second_tenant)
backend/tests/domains/notifications_comms/   ← existing comms tests; place new tests here
```

Also grep to find the existing tests that assert the current `/recent` shape (they will need updating for the new response shape):

```bash
grep -rn "communications/recent\|RecentCommunicationsResponse\|_get_recent_communications_impl" backend/ --include="*.py"
```

---

## Design Decisions (Do Not Re-Litigate)

| # | Decision | Rationale |
|---|---|---|
| **D-1** | **`channel` filter param is added but the data is SMS-only today.** Add `channel: str \| None` (accepts `sms`/`email`) and apply it as a `WHERE channel = :channel` when provided. Do NOT build an email data path — `customer_communication_message` only stores SMS. The param is forward-compat so the FE pill exists, but with today's data an `email` filter returns 0 rows (correct). | The launch-plan card says "SMS/Email pill." MCP confirms email is not in this table. Wiring the param without faking email data is the honest MVP move; flag to Tom that a true email feed is a separate future batch. |
| **D-2** | **Migrate the response to the canonical `offset`/`limit` + `{items, total, limit, offset}` shape** (matches `PilotPaginator` and every other UI-FIX-1C list). Drop the `page`/`page_size` params and the `page`/`page_size` response fields. | The FE `PilotPaginator` is built around `offset`/`limit`. The current `page`/`page_size` shape is the odd one out. This is a breaking change to the endpoint — that's why Part B (React) is a companion in the same batch. |
| **D-3** | **`customer_search`** is a case-insensitive `ilike` on `customer.display_name` only (single-field — the aggregate already joins `Customer`). Not the 5-field search `customers.py` uses. | The comms feed shows `customer_name` = `display_name`; searching that one field matches what the user sees. |
| **D-4** | **`sent_from` / `sent_to`** are inclusive date bounds applied to `customer_communication_message.created_at` (`>= sent_from`, `< sent_to + 1 day` OR `<= sent_to` end-of-day — use `>=`/`<=` on full timestamps; the FE sends ISO datetimes). Both optional, independent. | Standard date-range filter. `created_at` is the ordering column already. |
| **D-5** | **Keep both `/recent` (JWT, `communications.view`) and `/recent/test` (no-JWT) endpoints.** Both call the shared `_get_recent_communications_impl` — apply all new params in the shared impl so both stay in sync. | Existing pattern; the `/test` twin is required for the FE integration/E2E path. |

---

## Task 1 — Extend the response + item schemas

In `backend/api/routes/communications.py` (the BETA-B1 block, ~line 784):

1. **`CommunicationSummaryItem`** — no change needed (fields already match: `id`, `customer_id`, `customer_name`, `channel`, `direction`, `body`, `created_at`).
2. **`RecentCommunicationsResponse`** — replace `page` / `page_size` fields with `limit` / `offset` to match the canonical shape:

```python
class RecentCommunicationsResponse(BaseModel):
    """Paginated response for GET /api/v1/communications/recent (COMMS-UI-B1: canonical offset/limit)."""

    items: list[CommunicationSummaryItem]
    total: int
    limit: int
    offset: int
```

Run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` (expect the old shape tests to fail now — you fix them in Task 4).

---

## Task 2 — Extend the shared impl with filters + offset/limit

Rewrite `_get_recent_communications_impl` to accept the new params and apply them. Preserve the existing tenant-isolation join (`CustomerCommunicationThread.tenant_id == tenant_id`). Signature:

```python
def _get_recent_communications_impl(
    db: Session,
    user_context,  # AuthenticatedUser | TestUserContext
    *,
    limit: int,
    offset: int,
    customer_search: str | None = None,
    channel: str | None = None,
    sent_from: datetime | None = None,
    sent_to: datetime | None = None,
) -> RecentCommunicationsResponse:
```

Build a shared `base_where` list applied to BOTH the count and the page query so `total` reflects the filters (this is the bug-class the customers.py pattern avoids — count and page must use the same predicate):

```python
tenant_id = user_context.tenant_id

base_joins_where = [CustomerCommunicationThread.tenant_id == tenant_id]

if customer_search:
    base_joins_where.append(Customer.display_name.ilike(f"%{customer_search}%"))
if channel:
    base_joins_where.append(CustomerCommunicationMessage.channel == channel)
if sent_from:
    base_joins_where.append(CustomerCommunicationMessage.created_at >= sent_from)
if sent_to:
    base_joins_where.append(CustomerCommunicationMessage.created_at <= sent_to)
```

- The **count** query joins message → thread → customer (customer join is now required because `customer_search` filters on `display_name`) and applies `*base_joins_where`.
- The **page** query is the existing select, plus `*base_joins_where`, `.order_by(created_at.desc())`, `.offset(offset).limit(limit)`.
- Return `RecentCommunicationsResponse(items=..., total=total, limit=limit, offset=offset)`.

> **Adjust the exact ORM expressions to what you find in the file** — the existing impl already has the correct join chain and `Customer.display_name` projection; you are adding predicates + swapping pagination, not rewriting the joins from scratch.

Run: `python -m pytest -m unit -k recent --tb=short -q 2>&1 | tail -10`.

---

## Task 3 — Update both endpoint signatures

Update `get_recent_communications` (JWT) and `get_recent_communications_test` (no-JWT) to expose the new query params and pass them through to the shared impl:

```python
@router.get("/recent", response_model=RecentCommunicationsResponse, ...)
def get_recent_communications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    customer_search: str | None = Query(default=None),
    channel: str | None = Query(default=None, description="sms | email (email has no data today)"),
    sent_from: datetime | None = Query(default=None),
    sent_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("communications.view")),
) -> RecentCommunicationsResponse:
    return _get_recent_communications_impl(
        db, current_user,
        limit=limit, offset=offset,
        customer_search=customer_search, channel=channel,
        sent_from=sent_from, sent_to=sent_to,
    )
```

Mirror the same params in `get_recent_communications_test` (using `get_test_context()`).

> **No `set_audit_context_sync` needed** — these are read-only GET endpoints (no DB writes).

Run: `python -m pytest -m unit -k recent --tb=short -q 2>&1 | tail -10`.

---

## Task 4 — Update existing tests + add new filter tests

**4a. Fix existing tests** that assert the old `page`/`page_size` shape (found via the Task-0 grep). Update them to assert `limit`/`offset` and the new response fields.

**4b. Add a new test file** `backend/tests/domains/notifications_comms/test_comms_ui_b1_recent_filters.py`:

```python
import pytest

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]
```

Required coverage (use the `client` fixture + `/api/v1/communications/recent/test` no-JWT endpoint, and the `test_tenant` seeded comms scenario data — do NOT assert total counts, assert by inserted/known IDs or by filtered subset relationships):

| # | Scenario |
|---|---|
| 1 | No filters → returns `items`, `total`, `limit`, `offset` keys; `limit`/`offset` echo the request (default 50/0). |
| 2 | `offset`/`limit` paginate — page 2 (`offset=1, limit=1`) returns a different first item than page 1, and `total` is identical across both pages. |
| 3 | `customer_search` = a substring of a known seeded customer's `display_name` → every returned item's `customer_name` matches (case-insensitive); `total` ≤ unfiltered total. |
| 4 | `channel=sms` → all returned items have `channel == "sms"`; `channel=email` → `items == []` and `total == 0` (documents D-1). |
| 5 | `sent_from` set to "now + 1 day" → `items == []` (nothing in the future); `sent_to` set to "now - 10 years" → `items == []`. A window that spans the seed data → non-empty. |
| 6 | Tenant isolation: `second_tenant` context → does not see `test_tenant`'s messages (use the `/recent` JWT endpoint with `mock_cognito_jwt` for a `second_tenant` user, OR assert the impl directly with a `second_tenant` context). |

> Follow the **Test Resilience Rule**: filter your assertions by the specific customer/message identity you're targeting; never `assert len(items) == N` against the shared seeded tenant.

---

## Regenerate OpenAPI (handoff signal)

After all tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
grep -A 15 "communications/recent\"" backend/openapi_schema_map.md
```

Verify the new query params (`limit`, `offset`, `customer_search`, `channel`, `sent_from`, `sent_to`) and the `limit`/`offset` response fields appear.

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Lint + Full Suite (once, at the end)

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate (rules §23) — must be clean before the suite runs
ruff check . --fix
ruff format .

# Full suite including integration tests
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/notifications_comms/ -v 2>&1 | tail -25
echo "=== COMMS-UI-B1 (BACKEND) FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues (no unjustified `# noqa`), and the run must be free of Pydantic-v1-carryover `DeprecationWarning` noise (Rule 13).

> Any failure in either phase — including apparently pre-existing — must be fixed before the batch is done. If you cannot find the root cause → STOP and ask Tom.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — column names + SMS-only reality confirmed
- [ ] All mandatory source files read (including `customers.py` §140–210 pattern)
- [ ] `RecentCommunicationsResponse` migrated to `{items, total, limit, offset}` (Task 1)
- [ ] `_get_recent_communications_impl` accepts + applies `customer_search`, `channel`, `sent_from`, `sent_to`, `offset`, `limit`; count + page use the same predicate (Task 2)
- [ ] Both `/recent` and `/recent/test` endpoints expose the new query params (Task 3)
- [ ] Tenant isolation preserved via the thread join (no `db.get()`)
- [ ] All handlers + `_impl` remain sync `def` — no `async def` on the blocking `Session` (rules §21)
- [ ] Only Pydantic v2 idioms used; both response schemas keep `response_model` (rules §22)
- [ ] Existing `/recent`-shape tests updated to the new shape (Task 4a)
- [ ] New filter test file added — all 6 scenarios (Task 4b)
- [ ] All new tests use `pytestmark` domain + `unit` marker, `client` fixture, `test_tenant`/`second_tenant` (no hardcoded UUIDs, no total-count asserts)
- [ ] `ruff check . --fix && ruff format .` run — zero remaining issues, no unjustified `# noqa` (rules §23)
- [ ] `python export_openapi_json.py` run — new params + response fields present in `openapi_schema_map.md`
- [ ] **Phase 1**: all unit tests pass — zero failures
- [ ] **Phase 2**: full suite passes — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B + one-row entry in Appendix A
- [ ] **Handoff**: notify React Engineer that Part B may start (OpenAPI regenerated)

---

## Completion Summary

After all DoD items are complete, add a **Completion Summary** to `pilot-launch-plan.md` Appendix B using the standard template, and a one-row entry to Appendix A. End the summary with an explicit **Handoff to React Engineer** block:

> Part A complete. `GET /api/v1/communications/recent` now accepts `limit`, `offset`, `customer_search`, `channel`, `sent_from`, `sent_to` and returns `{items, total, limit, offset}`. React Engineer: run `pnpm sync-api-types` FIRST. Channel is SMS-only in the data today (D-1) — an `email` filter legitimately returns 0 rows.

## After This Task — Next Step

Hand off to `batch-comms-ui-b1-react-engr-prompt.md` (Part B).
