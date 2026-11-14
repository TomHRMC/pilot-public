# Batch B17 Design — API Contract Fixes + Missing Endpoints

**Batch**: B17 (Mixed — Python Engineer then React Engineer)  
**Date**: June 16, 2026  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference gap analysis**: `dev-docs/analysis/pilot-app-pre-wkstm-3-mvp-ui-api-gap-analysis.md`  
**Gaps addressed**: §3.1, §3.2, §3.3, §3.4, §3.5, §3.6, §3.7, §3.8, §3.9, §3.11, §3.12, §3.13

---

## Overview

B17 is the unblocking batch. It fixes broken API contracts and adds missing endpoints that cause P0 failures in the web app today:
- **Reports page**: 422 on every call (wrong parameter shape)
- **Comms page**: 404 on page load (endpoint doesn't exist)
- **Dashboard widget**: 403 for all owners (wildcard permission bug)
- **Mobile owner tab**: 404 on field issues summary (endpoint missing)
- **Public invoice view**: S1 HTTP violation (GET writes to DB)
- **Quotes list**: Degraded (no server-side filter, no human-readable fields)
- **Customer views**: Missing phone number across all surfaces
- **Mobile expense logging**: Hardcoded categories (no lookup endpoint)
- **SSE connections**: JWT not centralized (6+ hooks broken)

**Part A** (Python Engineer): All backend fixes and new endpoints.  
**Part B** (React Engineer): Two frontend hook fixes — run only after Part A closes and `pnpm sync-api-types` is executed.

---

## A. Input Read Summary

| Input | Verified |
|---|---|
| Gap analysis §3.1–§3.13 | ✅ Read |
| `mvp-prd.md` §3.3, §3.6, §3.7, §3.8, §3.10 | ✅ Read |
| `mvp-arch.md` §7 (API Design), §16.13 (SSE pattern) | ✅ Read |
| `16-api-audit-findings.md` S1–S3 findings | ✅ Read |
| `fe-ui-testing-open-issues-v1.md` §3.1–§3.6 | ✅ Read |
| Live DB schema — `job_expense_category` table | ✅ Verified: 3 rows (`materials`, `equipment`, `permits`) |
| `backend/api/routes/customers.py` — `CustomerResponse` schema | ✅ Read: `mobile_phone` stored in model, not in response |
| `backend/api/routes/invoices.py` — GET write side effect | ✅ Confirmed: `link.used_count += 1` on GET |
| `backend/api/routes/quotes.py` — `QuoteListItem` schema | ✅ Confirmed: no `status_code` or `customer_name` fields |
| `backend/api/routes/communications.py` — send endpoint status code | ✅ Confirmed: returns 200, should be 201 |
| `backend/api/routes/tenant_email_branding.py` — PUT vs PATCH | ✅ Confirmed: PUT with all-Optional fields (partial update semantics) |
| `packages/ui/src/sse/useSseChannel.ts` — SSE hook | ✅ Confirmed: no `getToken` prop; JWT not appended |
| `apps/web/src/features/profitability/hooks/useProfitability.ts` — params | ✅ Confirmed: sends `?period=7d`; backend expects `?date_from=&date_to=` |

---

## B. Migration Plan

### B.1 Schema Changes

**No Alembic migrations required.** All B17 changes are:
- New API endpoints (Python code only)
- Schema field additions to Pydantic response models (Python code only)
- HTTP method/status code corrections (Python code only)
- Frontend hook fixes (TypeScript code only)

The `job_expense_category` table already has 3 rows seeded by `seed_missing_lookup_tables_batch_1` migration. No new data migration needed.

### B.2 Pre-Implementation Verification (MCP Queries)

Before implementing, verify these live DB states:

```sql
-- 1. Confirm job_expense_category rows exist
SELECT code, name FROM public.job_expense_category ORDER BY code;
-- Expected: equipment, materials, permits

-- 2. Confirm Customer model has mobile_phone column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'customer' AND column_name = 'mobile_phone';

-- 3. Confirm notifications_outbox FK to notification_channel works
SELECT code FROM public.notification_channel ORDER BY code;
-- Expected: email, in_app, push, sms

-- 4. Check communications routes — what endpoints exist
-- (code inspection only — no DB query needed)
```

---

## C. Execution Order

### Part A — Python Engineer (runs first; must complete before Part B)

| # | Task | File(s) | Dependency |
|---|---|---|---|
| A1 | Fix wildcard permission bug — `has_permission(["*"], "X")` | `core/permissions.py` | None — fix first, unblocks A2 testing |
| A2 | Add `GET /api/v1/communications/recent` endpoint | `api/routes/communications.py` | A1 |
| A3 | Fix owner 403 on `GET /api/v1/dashboard/widgets/recent-customer-messages` | `api/routes/dashboard.py` | A1 |
| A4 | Add `GET /api/v1/owner/field-issues/summary` endpoint | `api/routes/owner_escalations.py` | None |
| A5 | Move usage tracking from GET → POST on public invoice view | `api/routes/invoices.py` | None |
| A6 | Change `PUT /api/v1/settings/email-branding` → PATCH | `api/routes/tenant_email_branding.py` | None |
| A7 | Add `status_code=201` to `POST /api/v1/communications/send` | `api/routes/communications.py` | None |
| A8 | Add `GET /api/v1/job-expense-categories` endpoint | New route or `api/routes/catalog.py` | None |
| A9 | Add `?status=` filter + `status_code` + `customer_name` to `GET /api/v1/quotes/` | `api/routes/quotes.py` | None |
| A10 | Add `mobile_phone` to `CustomerResponse` Pydantic schema | `api/schemas/schemas.py` or inline | None |
| A11 | Add `SoftDeleteResponse` shared model + apply to 5 DELETE endpoints | `api/schemas/schemas.py`, `customers.py`, `addresses.py`, `contacts.py`, `scheduling.py` | None |
| A12 | Run `pytest -q` — zero new failures | All | After A1–A11 |
| — | **HANDOFF**: run `cd frontend && pnpm sync-api-types` | — | After A12 passes |

### Part B — React Engineer (runs after Part A handoff + `pnpm sync-api-types`)

| # | Task | File(s) | Dependency |
|---|---|---|---|
| B1 | Fix `useProfitability` hook — compute `date_from`/`date_to` from period pill | `apps/web/src/features/profitability/hooks/useProfitability.ts` | Part A complete |
| B2 | Centralize SSE JWT in `useSseChannel` — add `getToken?: () => Promise<string>` prop | `packages/ui/src/sse/useSseChannel.ts` (or equivalent path) | Part A complete |
| B3 | Update all 6 SSE hook consumers to use `getToken` prop | `useCalendarConflictSse.ts`, `useFieldIssuesSse.ts`, `useQbConflictsSse.ts`, `useCustomerCommsSse.ts`, `notification_sse` hooks | B2 |
| B4 | Run `pnpm build` + `pnpm test` — zero failures | All | After B1–B3 |

---

## D. New API Endpoints

### D.1 `GET /api/v1/communications/recent`

**Purpose**: Aggregate recent customer communications across all customers for the tenant. Consumed by `/comms` page and `RecentCustomerMessagesWidget` on dashboard.  
**Auth**: JWT required  
**RBAC**: `communications.view`  

**Request**:
```
GET /api/v1/communications/recent?page=1&page_size=50
```

**Response** (HTTP 200):
```json
{
  "items": [
    {
      "communication_id": "uuid",
      "customer_id": "uuid",
      "customer_name": "Tom Johnson",
      "rendered_message": "I'm on my way — ETA 20 minutes.",
      "actual_channel": "sms",
      "status": "sent",
      "sent_at": "2026-06-16T14:30:00Z"
    }
  ],
  "total": 12
}
```

**Implementation notes**:
- Query `CustomerCommunication` (or `NotificationOutbox`) joined to `Customer` for `customer_name`
- Filter by `tenant_id` (tenant isolation)
- Order by `sent_at DESC`
- Offset pagination: `skip = (page - 1) * page_size`
- Cursor-based preferred if list grows; offset acceptable for MVP
- `customer_name` = `customer.display_name`

**Pydantic schema**:
```python
class RecentCommunicationItem(BaseModel):
    communication_id: UUID
    customer_id: UUID
    customer_name: str
    rendered_message: str
    actual_channel: str
    status: str
    sent_at: datetime | None

class RecentCommunicationsResponse(BaseModel):
    items: list[RecentCommunicationItem]
    total: int
```

---

### D.2 `GET /api/v1/owner/field-issues/summary`

**Purpose**: Return count of pending mobile sync conflicts awaiting owner resolution. Consumed by mobile `FieldIssuesSyncStatusSection`.  
**Auth**: JWT required  
**RBAC**: `field_issue.view`  

**Request**:
```
GET /api/v1/owner/field-issues/summary
```

**Response** (HTTP 200):
```json
{
  "pending_count": 3
}
```

**Implementation notes**:
- Query `MobileSyncConflict` (or `OwnerEscalation`) where `severity = 'owner_escalation'` AND `status = 'pending'` AND `tenant_id = current_user.tenant_id`
- Confirm exact table name and column names from live DB before implementing
- `routes/owner_escalations.py` likely already has the model import

**Pydantic schema**:
```python
class FieldIssuesSummaryResponse(BaseModel):
    pending_count: int
```

---

### D.3 `GET /api/v1/job-expense-categories`

**Purpose**: Return the list of job expense categories for the tenant. Consumed by mobile `ExpenseSection` to replace hardcoded list.  
**Auth**: JWT required  
**RBAC**: `jobs.view` (or `expenses.view` if that permission exists)  

**Request**:
```
GET /api/v1/job-expense-categories
```

**Response** (HTTP 200):
```json
{
  "categories": [
    { "code": "materials", "name": "Materials", "is_default": true },
    { "code": "equipment", "name": "Equipment", "is_default": false },
    { "code": "permits", "name": "Permits", "is_default": false }
  ]
}
```

**Implementation notes**:
- Query `job_expense_category` table: global rows (`tenant_id IS NULL`) plus tenant-specific rows (`tenant_id = current_user.tenant_id`), ordered by `name ASC`
- Tenant-specific rows shadow global rows of the same `code` (same pattern as other lookup tables)
- If `job_expense_category` table does not have a `routes/` home yet, add to `routes/catalog.py` or create `routes/job_expense_categories.py`

**Pydantic schema**:
```python
class JobExpenseCategoryItem(BaseModel):
    code: str
    name: str
    is_default: bool

class JobExpenseCategoriesResponse(BaseModel):
    categories: list[JobExpenseCategoryItem]
```

---

### D.4 Changes to Existing Endpoints

#### D.4.1 `GET /api/v1/quotes/` — Add denormalized fields + server-side filter

**Current**: Returns `QuoteListItem` with `id`, `customer_id`, `status_id`, `total_cents`. No filter params.  
**After B17**:

Add query param:
```
GET /api/v1/quotes/?status=draft&skip=0&limit=100
```

Extend `QuoteListItem` response schema:
```python
class QuoteListItem(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str          # NEW — denormalized from Customer JOIN
    status_id: UUID
    status_code: str            # NEW — denormalized from QuoteStatus JOIN
    total_cents: int
    created_at: datetime
    expires_at: datetime | None
```

**Implementation notes**:
- Add `?status=` query param to `_list_quotes_impl()` — filter by `QuoteStatus.code`
- JOIN `Customer` to get `display_name` as `customer_name`
- JOIN `QuoteStatus` to get `code` as `status_code`
- Both JOINs must respect tenant isolation (`Customer.tenant_id == tenant_id`)
- `customer_name` = `customer.display_name` (matches existing CRM pattern)

#### D.4.2 `GET /api/v1/customers/{id}` — Add `mobile_phone` to `CustomerResponse`

Add field to `CustomerResponse` Pydantic schema:
```python
class CustomerResponse(BaseModel):
    # ... existing fields ...
    mobile_phone: str | None    # NEW
```

No DB change needed — column already exists on `Customer` model. Only the Pydantic schema needs updating.

#### D.4.3 `GET /api/v1/public/invoices/{token}` — Remove write side effects

**Current**: Handler increments `link.used_count` and stamps `link.last_used_at` on every GET (S1 HTTP violation per PRD FIND-148).  
**After B17**: Remove those writes from the GET handler entirely. They are already (or should be) present in `POST /api/v1/public/invoices/{token}/pay`.

```python
# REMOVE from _get_public_invoice_impl():
link.used_count += 1           # ← DELETE
link.last_used_at = datetime.now(UTC)  # ← DELETE
db.commit()                    # ← only if no other writes remain
```

Verify that `POST /pay` handler already increments `used_count` and stamps `last_used_at`. If not, add there.

#### D.4.4 `PUT /api/v1/settings/email-branding` → `PATCH`

In `backend/api/routes/tenant_email_branding.py`:
```python
# Line ~232: change
@router.put("")
# to:
@router.patch("")
```

Also update the test mirror endpoint at line ~181 if it uses `PUT`:
```python
@router.put("/test")  # → @router.patch("/test")
```

No schema changes — `EmailBrandingUpdate` already uses all-Optional fields, which is correct for PATCH.

#### D.4.5 `POST /api/v1/communications/send` — Add `status_code=201`

```python
@router.post("/send", status_code=status.HTTP_201_CREATED)
```

Also update test mirror endpoint:
```python
@router.post("/send/test", status_code=status.HTTP_201_CREATED)
```

#### D.4.6 Add `SoftDeleteResponse` shared model

Create in `api/schemas/schemas.py`:
```python
class SoftDeleteResponse(BaseModel):
    message: str
    id: UUID
```

Apply to these 5 endpoints by adding `response_model=SoftDeleteResponse` to decorator and ensuring the handler returns `{"message": "...", "id": str(record.id)}`:
- `DELETE /api/v1/customers/{customer_id}`
- `DELETE /api/v1/addresses/{address_id}`
- `DELETE /api/v1/contacts/{contact_id}`
- `DELETE /api/v1/scheduling/tech-availability/{record_id}`
- `DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{assignment_id}`

---

## E. Pattern Reuse Decisions

| Pattern (per `mvp-arch.md` §16) | Applied in B17 |
|---|---|
| **Tenant Isolation** (`tenant_id` filter on all queries) | All new endpoints: `communications/recent`, `field-issues/summary`, `job-expense-categories`, quotes list denormalization |
| **RBAC `require_permission()` decorator** | All new endpoints — permission check on every new route |
| **RFC 7807 Error Format** | All new endpoints return RFC 7807 on error |
| **`SoftDeleteResponse` shared model** | New shared model applied to 5 existing soft-delete DELETE endpoints |
| **Cursor-Based Pagination** (`mvp-arch.md` §7.8) | `communications/recent` uses offset for MVP; note for future cursor migration |
| **SSE `?token=JWT` pattern** (`mvp-arch.md` §16.13) | Centralized in `useSseChannel` via `getToken` prop (Part B) |

---

## F. Shared Module Interfaces

### F.1 `useSseChannel` — New `getToken` Prop (React Engineer, Part B)

**Location**: `packages/ui/src/sse/useSseChannel.ts` (verify exact path before implementing)

**Current signature** (approximate):
```typescript
function useSseChannel(url: string, options?: UseSseChannelOptions): SseChannelReturn
```

**After B17**:
```typescript
interface UseSseChannelOptions {
  getToken?: () => Promise<string>;  // NEW — if provided, fetches JWT and appends ?token=
  enabled?: boolean;
  onMessage?: (event: MessageEvent) => void;
}

function useSseChannel(url: string, options?: UseSseChannelOptions): SseChannelReturn
```

**Implementation**: When `getToken` is provided, the hook should:
1. Call `await getToken()` before opening `EventSource`
2. Append `?token=${jwt}` to the URL
3. Re-open connection when token expires (token rotation)

**Standard `getToken` implementation** for all consumers:
```typescript
import { fetchAuthSession } from 'aws-amplify/auth';

const getToken = async () => {
  const session = await fetchAuthSession();
  return session.tokens?.accessToken?.toString() ?? '';
};
```

### F.2 `useProfitability` — Period-to-Date Conversion (React Engineer, Part B)

**Location**: `apps/web/src/features/profitability/hooks/useProfitability.ts`

**Current**: Sends `?period=7d` — backend returns 422.

**After B17**: Convert period pill value to `date_from` / `date_to` before API call:

```typescript
function periodToDates(period: string): { date_from: string; date_to: string } {
  const today = new Date();
  const fmt = (d: Date) => d.toISOString().split('T')[0]; // YYYY-MM-DD
  
  switch (period) {
    case '7d':
      return { date_from: fmt(subDays(today, 7)), date_to: fmt(today) };
    case '30d':
      return { date_from: fmt(subDays(today, 30)), date_to: fmt(today) };
    case 'mtd':
      return { date_from: fmt(startOfMonth(today)), date_to: fmt(today) };
    case 'ytd':
      return { date_from: fmt(startOfYear(today)), date_to: fmt(today) };
    default:
      return { date_from: fmt(subDays(today, 30)), date_to: fmt(today) };
  }
}
```

Use `date-fns` helpers (`subDays`, `startOfMonth`, `startOfYear`) — already in the frontend dependency tree. If not, use plain `Date` arithmetic.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Where does `GET /api/v1/communications/recent` query from?** | Query `customer_communication` or `notification_outbox` table — whichever stores the rendered message body and `sent_at`. Check live DB: if `customer_communication` exists and has `rendered_body`, use that. If not, use `notification_outbox` joined to `customer`. Confirm before coding. |
| **What is the exact table name for mobile sync conflicts?** | Run: `SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%sync_conflict%' OR table_name LIKE '%escalation%' ORDER BY table_name;` before implementing `field-issues/summary`. Use that table name. |
| **Does `has_permission(["*"], "X")` bug affect all wildcard matches or just one?** | Test with: `assert has_permission(["*"], "invoices.view") is True` in `core/permissions.py` unit test. If the assertion fails, the wildcard matching is broken globally. Fix the implementation and add the unit test. |
| **Should `job-expense-categories` be a new route file or appended to `catalog.py`?** | Append to `catalog.py` if it already imports `job_expense_category` model. Otherwise create `routes/job_expense_categories.py` and register in `app/main.py`. Check imports before deciding. |
| **Does `POST /public/invoices/{token}/pay` already track `used_count`?** | Read `invoices.py` `_pay_public_invoice_impl()` — if `used_count` tracking is there, just remove it from GET. If not, add it to POST before removing from GET. Never have a period where neither tracks it. |
| **What is the exact path to `useSseChannel`?** | Run `find frontend -name "useSseChannel*"` before implementing Part B. Verify current prop signature before adding `getToken`. |
| **Which SSE hooks need the `getToken` update?** | Audit these files: `useCalendarConflictSse.ts`, `useFieldIssuesSse.ts`, `useQbConflictsSse.ts`, `useCustomerCommsSse.ts`, and any other file that uses `EventSource` or `useSseChannel`. Use `grep -r "EventSource\|useSseChannel" frontend/apps/ --include="*.ts" --include="*.tsx"` to find all consumers. |

---

## H. Surface Mockup Reference (Part B — Frontend only)

No new UI surfaces are added in B17. B17 is entirely API fixes and hook corrections. The surfaces that will become functional after B17 (but are not designed in this batch):

| Surface | Currently | After B17 |
|---|---|---|
| `/reports` page | 422 on every period | Returns data ✅ |
| `/comms` page | 404 on load | Loads communications list ✅ |
| Dashboard `RecentCustomerMessagesWidget` | 403 / empty | Shows recent SMS ✅ |
| Mobile Owner tab `FieldIssuesSyncStatusSection` | 404 | Shows pending count ✅ |
| Mobile `ExpenseSection` | 5 hardcoded categories | Fetches from API ✅ (after MOB-B6) |
| Customer views (web + mobile) | No phone number | `mobile_phone` displayed ✅ |

---

## I. Component Manifest (Part B — Frontend)

| Component / Hook | Path | Change Type |
|---|---|---|
| `useProfitability` | `apps/web/src/features/profitability/hooks/useProfitability.ts` | **Modify** — add `periodToDates()` helper; remove `?period=` param; send `?date_from=&date_to=` |
| `useSseChannel` | `packages/ui/src/sse/useSseChannel.ts` *(verify path)* | **Modify** — add `getToken?: () => Promise<string>` option; append JWT to URL when provided |
| `useCalendarConflictSse` | `apps/web/src/features/calendar-conflict/hooks/useCalendarConflictSse.ts` | **Modify** — pass `getToken` to `useSseChannel` |
| `useFieldIssuesSse` | `apps/web/src/features/field-issues/hooks/useFieldIssuesSse.ts` | **Modify** — pass `getToken` to `useSseChannel` |
| `useQbConflictsSse` | `apps/web/src/features/quickbooks-conflict/hooks/useQbConflictsSse.ts` | **Modify** — pass `getToken` to `useSseChannel` |
| `useCustomerCommsSse` | `apps/web/src/features/customer-comms/hooks/useCustomerCommsSse.ts` | **Modify** — pass `getToken` to `useSseChannel` |
| *(any other SSE hook found by grep)* | *(varies)* | **Modify** — pass `getToken` |

---

## Acceptance Criteria

### Part A (Python Engineer)
- [ ] `GET /api/v1/communications/recent?page=1&page_size=50` returns 200 with `items` array for a tenant with communications data
- [ ] `GET /api/v1/dashboard/widgets/recent-customer-messages` returns 200 for owner (not 403)
- [ ] `GET /api/v1/owner/field-issues/summary` returns 200 with `{ "pending_count": N }`
- [ ] `GET /api/v1/job-expense-categories` returns 200 with array of `{ code, name, is_default }`
- [ ] `GET /api/v1/public/invoices/{token}` no longer writes to DB (verified by checking `invoice_public_link.used_count` before/after two GET calls — count should not increment)
- [ ] `PATCH /api/v1/settings/email-branding` returns 200 (was PUT)
- [ ] `PUT /api/v1/settings/email-branding` returns 405 Method Not Allowed (old method rejected)
- [ ] `POST /api/v1/communications/send` returns 201 (not 200)
- [ ] `GET /api/v1/quotes/?status=draft` returns only draft quotes
- [ ] `GET /api/v1/quotes/` response items include `status_code` and `customer_name` fields
- [ ] `GET /api/v1/customers/{id}` response includes `mobile_phone` field
- [ ] `DELETE /api/v1/customers/{id}` response matches `SoftDeleteResponse` schema (`message` + `id`)
- [ ] Same for addresses, contacts, tech-availability, job-assignment DELETE endpoints
- [ ] `pytest -q` passes with zero new failures
- [ ] `python backend/export_openapi_json.py` regenerates `openapi.json` cleanly

### Part B (React Engineer — after `pnpm sync-api-types`)
- [ ] `/reports` page with "7 Day" period selected loads without 422 error
- [ ] `/reports` page with "30 Day", "MTD", "YTD" all load without error
- [ ] `pnpm sync-api-types` completes without error
- [ ] All SSE-dependent pages (dispatch board, calendar conflicts, field issues, QB conflicts, customer comms) maintain their real-time update behavior
- [ ] `pnpm build` passes with zero type errors
- [ ] `pnpm test` passes with zero new failures
