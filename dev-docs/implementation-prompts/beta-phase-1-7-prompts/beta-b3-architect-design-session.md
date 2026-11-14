# Architect Design Session Prompt: BETA-B3 — Web List/Index Pages

**Paste this entire prompt into a fresh Pilot Architect chat session.**

---

## Your Task

Produce the batch design document `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b3-design.md` for BETA-B3.

This is a Phase 1 Surface Design Session per the Standard Architecture Design Workflow in `dev-docs/architecture-design/pilot-architect-methods.md`. No implementation happens here — the output is the design doc that the React Engineer will execute against.

---

## Background: What BETA-B3 Fixes

During beta testing, the following web app routes render only an `<h1>` heading stub with no content. These are the primary navigation landing pages every user sees after login. The goal is to make them functional so beta data population can begin.

| Route | Current State | Priority |
|---|---|---|
| `/customers` | `<h1>Customers</h1>` stub | P1 |
| `/quotes` | `<h1>Quotes</h1>` stub | P1 |
| `/invoices` | `<h1>Invoices</h1>` stub | P1 |
| `/comms` | `<h1>Comms</h1>` stub | P2 |
| `/notifications` | `<h1>Notifications</h1>` stub | P3 |
| `/operations` | `<h1>Operations</h1>` stub | P3 |
| `/sync` | `<h1>Sync & Storage</h1>` stub | P3 |

**Important context**: Sub-routes already have real content — `/customers/[id]/comms` (FE-B6/B10), `/quotes/pending` + `/quotes/[id]` (FE-B5), `/reports` renders `<ProfitabilityPage>` (FE-B4). Only the top-level index/list pages are stubs.

Source issue: `dev-docs/testing-support/fe-ui-testing-open-issues-v1.md` §2.3 (second item)  
Source plan: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B3

---

## Phase 1: Required Reads (Complete ALL Before Writing the Design Doc)

### Step 1: Read the source files for existing stubs

```
frontend/apps/web/src/app/(authed)/customers/page.tsx
frontend/apps/web/src/app/(authed)/quotes/page.tsx
frontend/apps/web/src/app/(authed)/invoices/page.tsx
frontend/apps/web/src/app/(authed)/comms/page.tsx
frontend/apps/web/src/app/(authed)/notifications/page.tsx
frontend/apps/web/src/app/(authed)/operations/page.tsx
frontend/apps/web/src/app/(authed)/sync/page.tsx
```

Confirm each is genuinely a stub (no real content). Note any that already have partial implementations.

### Step 2: Read existing feature folders for these surfaces

```
frontend/apps/web/src/features/
```

List all subdirectories. Then read the following hooks if they exist:
- Any file matching `*customer*` in `features/`
- Any file matching `*quote*` in `features/`
- Any file matching `*invoice*` in `features/`
- Any file matching `*comm*` in `features/comms/` or `features/customer-comms/`
- Any file matching `*notification*` in `features/`

Specifically check: do these hooks already exist?
- `features/customers/hooks/useCustomers.ts` (or similar)
- `features/quotes/hooks/useQuotes.ts` (or similar)
- `features/invoices/hooks/useInvoices.ts` (or similar)

If a hook already exists, you must not create a duplicate. If it does not exist, you will specify its creation in the design doc.

### Step 3: Verify API endpoints from `backend/openapi_schema_map.md`

Read `backend/openapi_schema_map.md`. Find and document the exact details for:

1. **Customer list endpoint** — path, required/optional params, response shape (especially: what fields does a list item have? `id`, `display_name`, `type`, pagination?)
2. **Quotes list endpoint** — path, params (status filter?), response shape
3. **Invoices list endpoint** — path, params (status filter?), response shape
4. **Communications/recent endpoint** — path, params, response shape (this was added in BETA-B1; confirm it exists)
5. **Notifications list endpoint** — path, params, response shape (check if any in-app notification list endpoint exists)

If any endpoint is NOT found in `openapi_schema_map.md`, also check `backend/openapi.json` directly:
```bash
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
for p in spec['paths']:
    if any(kw in p for kw in ['customer', 'quote', 'invoice', 'communication', 'notification']):
        print(p)
"
```

**If an endpoint does not exist in `openapi.json`, it does not exist.** Document this gap — the design doc must specify the MSW handler needed for development against mock data.

### Step 4: Read the shared component catalog for reusable components

```
frontend/packages/ui/src/index.ts
```

Find and note which of these are available (they must be used rather than recreated):
- `<EmptyState>` — FE-B1
- `<LoadingState>` — FE-B1
- `<ErrorState>` — FE-B1
- `<RoleGate>` / `useRequiresPermission()` — FE-B0

Also check if there are any existing shared table/list components in `packages/ui/src/`:
```bash
ls frontend/packages/ui/src/
```

### Step 5: Read the permissions registry

```
frontend/packages/ui/src/role-gate/permissions.ts
```

For each surface, identify the correct permission key:
- What permission does `/customers` require? (`customers.view`?)
- What permission does `/quotes` require? (`quotes.view`?)
- What permission does `/invoices` require? (`invoices.view`?)
- What permission does `/comms` require? (`communications.view`?)
- What permission does `/notifications` require? (all roles?)

### Step 6: Read an existing complete list page as a pattern reference

Read the profitability page (the only complete list-type surface built in FE-B4):
```
frontend/apps/web/src/app/(authed)/reports/page.tsx
frontend/apps/web/src/features/profitability/components/ProfitabilityPage.tsx
```

This shows the pattern: page route imports and renders a feature-scoped page component. Follow this pattern.

Also read one existing feature folder hook to understand the apiClient pattern:
```
frontend/apps/web/src/features/profitability/hooks/useProfitability.ts
```

---

## Phase 2: Design Decisions to Make and Document

After completing all reads, make and document the following decisions in the design doc:

### Decision 1: Minimum Viable List Scope Per Surface

For each route, determine the minimum viable content that makes it "not a stub" and useful for beta testing:

- **`/customers`** — minimum: searchable list with `display_name`, `type`, count badge, link to `/customers/[id]`
- **`/quotes`** — minimum: list with quote number, customer name, status pill, total, link to `/quotes/[id]`; filter by status (pending_approval, sent, draft)
- **`/invoices`** — minimum: list with invoice number, customer name, status pill, amount due, link to `/invoices/[id]`
- **`/comms`** — minimum: recent communications list (if BETA-B1 endpoint exists); or `<EmptyState>` with message "Communications are available per customer" if aggregate endpoint doesn't exist
- **`/notifications`** — minimum: if no notifications list endpoint exists, render a meaningful page (not a stub) with `<EmptyState>` or a redirect note; if endpoint exists, render notification list
- **`/operations`** — minimum: determine if this should redirect to `/settings/operations` or have its own content; check if there are operations-specific routes/pages that make sense as a landing
- **`/sync`** — same as operations — should it redirect to `/settings/sync-storage` or have its own page?

### Decision 2: Pagination Strategy

Does the backend return cursor-based or offset-based pagination? Determine from `openapi.json`. Document the chosen pagination component strategy (infinite scroll, numbered pages, or simple "Load More").

### Decision 3: Search/Filter Implementation

For Customers and Quotes:
- Does the backend list endpoint support `?search=` or `?status=` query params?
- If yes: implement search input / filter pills
- If no: implement client-side filtering as a fallback (or defer filtering to a later batch)

### Decision 4: Routing for P3 surfaces (`/operations`, `/sync`, `/notifications`)

Determine for each whether to:
- (a) Redirect to the equivalent settings page (simplest MVP approach)
- (b) Build a real content page

The `/operations` and `/sync` routes were added to the sidebar as top-level nav items. Check if there are any existing routes under `/settings/operations/` or `/settings/sync-storage/` that have content — if so, a redirect is cleanest. If not, a simple summary page.

---

## Phase 3: Write the Design Document

**Output file**: `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b3-design.md`

The design doc MUST contain sections A through I per the standard batch design format:

### A. Component Implementation Plan

For each new component, specify:
- Component name
- File path (must follow `apps/web/src/features/{kebab-surface}/components/{ComponentName}.tsx`)
- Props interface (TypeScript)
- Parent surface

**For every component listed as "new"**: confirm via `grep` or directory listing that it does not already exist before listing it.

### B. Execution Order

List all surfaces and components in implementation order with one-line dependency rationale for each. P1 surfaces first, P3 last.

### C. New Routes

For each route being implemented:
- File path (`apps/web/src/app/(authed)/...`)
- Auth requirement
- RBAC permission gate (exact permission key from `permissions.ts`)

### D. API Endpoint Consumption

For each surface:
- Exact endpoint path (verified from `openapi_schema_map.md` or `openapi.json`)
- TanStack Query hook (existing hook to reuse, or new hook to create with proposed name and location)
- MSW handler required? (yes if backend endpoint was added in BETA-B1 and may not be stable yet, or if endpoint doesn't exist)
- Query key (exact array)

### E. Pattern Reuse Decisions

For each shared component used:
- Which component (e.g., `<EmptyState>`, `<LoadingState>`)
- Import path
- Props to pass

### F. Shared Module Interfaces

If any new shared hook is being created (e.g., `useCustomers()` if it doesn't exist), specify its full TypeScript signature:
- Location (should be in `apps/web/src/features/{surface}/hooks/`)
- Input params
- Return type
- Example call

### G. Open Questions Resolved

Document any open questions from the design process and the decision made:
- e.g., "Does `/operations` get its own page or redirect? Decision: redirect to `/settings/operations/margin-buckets` (first operations settings page)"
- e.g., "Are `/notifications`, `/operations`, `/sync` needed for P1 beta testing? Decision: build minimal stub with EmptyState if no endpoint; redirect if settings page exists"

### H. External Dependency Status

For each surface, note if it depends on:
- BETA-B1 endpoints being complete (customer comms endpoint)
- `pnpm sync-api-types` being current
- Any other prerequisite

### I. Test Plan

Per surface:
- Unit test files (component name + file location)
- Integration test file (in `apps/web/__tests__/batch_beta_v1_b3/`)
- What the integration test covers (primary flow, empty state, error state, RBAC)
- axe-core accessibility check required on every surface

---

## Design Doc Quality Gates

Before finalizing the design doc, verify:

- [ ] Every component listed as "new" was confirmed via `read_file` or `grep` to not already exist
- [ ] Every API endpoint listed was verified from `openapi_schema_map.md` or `openapi.json` — no invented paths
- [ ] Every permission key is from the actual `permissions.ts` file — no invented keys
- [ ] Every shared component import path resolves to a real file in `packages/ui/src/`
- [ ] P3 surfaces (`/notifications`, `/operations`, `/sync`) have a clear decision documented — not left as "TBD"
- [ ] The MSW handler section covers any endpoint added in BETA-B1 (since BETA-B2 may not be complete yet)
- [ ] Implementation order in Section B is feasible: P1 surfaces (customers, quotes, invoices) can all be built independently; P2 (comms) depends on BETA-B1 communications endpoint; P3 depends on whether redirect or content page decision is made

---

## Output

The completed design doc at:  
**`dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b3-design.md`**

Once this design doc is complete and reviewed by Tom, it becomes the input for the BETA-B3 React Engineer implementation prompt.
