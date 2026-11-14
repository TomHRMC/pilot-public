# Implementation Prompt: B17 — API Contract Fixes (Part B — Frontend)

**Mode**: Pilot React Engineer  
**Batch**: B17 Part B (Frontend)  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — B17  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-b17-design.md`  
**Estimated session**: 1–2 hours  
**Platform**: Web (`apps/web`) + Shared UI (`packages/ui`)  
**Backend companion**: B17 Part A (Python Engineer) — **must be complete before starting this prompt**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-b17-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. B17 Part A must have run `python export_openapi_json.py` — if the new endpoints are not in the map, stop and confirm Part A is complete.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design doc.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 3**: SSE endpoints require `?token=JWT` — browser `EventSource` cannot send `Authorization` headers. This batch centralizes that pattern.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component.
- **Rule 8**: No new npm dependencies without first checking `package.json`. `date-fns` should already be available — verify before using.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching.
- **Rule 10**: If ANY test fails during your work — even pre-existing — **you must fix it before declaring the batch done**.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §F — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| `getToken` prop on `useSseChannel` | Optional prop `getToken?: () => Promise<string>` — appends JWT to URL | Browser `EventSource` cannot send auth headers — must use query param |
| `periodToDates()` helper | Plain `Date` arithmetic — no external library | `date-fns` may not be installed; plain arithmetic works and has no dependency risk |
| `useDispatchSse` treatment | If it manually appends token, refactor to use `getToken` prop instead | Prevents double-appending the token |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Shared UI package
pnpm --filter @pilot/ui test 2>&1 | tail -5

# Web app
pnpm --filter web test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom that it is a known failure, or fix it before starting.

---

## Pre-Work: Sync API Types

**This step is mandatory and must be first.**

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the backend `openapi.json` updated by B17 Part A.

> **If `pnpm sync-api-types` fails**: B17 Part A may not be complete. Stop and confirm with the Python Engineer before proceeding.

---

## Pre-Work: Verify Endpoints

Verify the new B17 Part A endpoints appear in the backend spec before writing any code:

```bash
grep -A 3 "communications/recent" backend/openapi_schema_map.md
grep -A 3 "job-expense-categories" backend/openapi_schema_map.md

# Verify PATCH (not PUT) for email-branding
python3 -c "
import json
spec = json.load(open('openapi.json'))
eb = spec['paths'].get('/api/v1/settings/email-branding', {})
print('email-branding methods:', list(eb.keys()))
"
```

**If an endpoint is NOT in `openapi_schema_map.md` → STOP. Do not proceed. Ask Tom whether B17 Part A is complete.**

| Hook | Endpoint | Verified |
|---|---|---|
| `useProfitability` | `GET /api/v1/reports/profitability?date_from=&date_to=` | ✅ Confirm before writing |

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/profitability/hooks/useProfitability.ts
  ← understand current param shape before modifying

frontend/apps/web/src/features/dispatch-board/hooks/useDispatchSse.ts
  ← reference implementation for JWT-appended SSE connection

packages/ui/src/sse/useSseChannel.ts (verify path first — see find command below)
  ← current hook signature before adding getToken prop

frontend/apps/web/src/mocks/handlers/index.ts
  ← understand how to register any new MSW handlers

packages/ui/src/index.ts
  ← confirm what is already exported before adding anything
```

Also run these before assuming file locations:

```bash
# Find useSseChannel
find frontend/packages -name "useSseChannel*" | head -5
find frontend/apps -name "useSseChannel*" | head -5

# Find all SSE hook consumers (MUST audit all of these)
grep -r "EventSource\|useSseChannel" frontend/apps/ frontend/packages/ --include="*.ts" --include="*.tsx" -l

# Find useProfitability
find frontend/apps/web -name "useProfitability*" | head -5

# Confirm date-fns availability
grep '"date-fns"' frontend/apps/web/package.json frontend/packages/ui/package.json 2>/dev/null
```

---

## Context: What This Batch Does

| Task | File | Change |
|---|---|---|
| B1 | `useProfitability.ts` | Replace `?period=` param with computed `?date_from=&date_to=` |
| B2 | `useSseChannel.ts` | Add `getToken?: () => Promise<string>` prop; append JWT when provided |
| B3 | All SSE hook consumers | Pass `getToken` prop to `useSseChannel` |

---

## Task B1 — Fix `useProfitability` Hook

**File**: `apps/web/src/features/profitability/hooks/useProfitability.ts`

Read the file first. Add a `periodToDates()` helper and use it to convert the period pill to `date_from`/`date_to` params.

> Read before modifying. Adjust the below to match what you actually find in the file.

**Helper** (plain `Date` arithmetic — no external library dependency):

```typescript
function periodToDates(period: string): { date_from: string; date_to: string } {
  const today = new Date();
  const fmt = (d: Date): string => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  switch (period) {
    case '7d': {
      const from = new Date(today);
      from.setDate(from.getDate() - 7);
      return { date_from: fmt(from), date_to: fmt(today) };
    }
    case '30d': {
      const from = new Date(today);
      from.setDate(from.getDate() - 30);
      return { date_from: fmt(from), date_to: fmt(today) };
    }
    case 'mtd': {
      const from = new Date(today.getFullYear(), today.getMonth(), 1);
      return { date_from: fmt(from), date_to: fmt(today) };
    }
    case 'ytd': {
      const from = new Date(today.getFullYear(), 0, 1);
      return { date_from: fmt(from), date_to: fmt(today) };
    }
    default: {
      const from = new Date(today);
      from.setDate(from.getDate() - 30);
      return { date_from: fmt(from), date_to: fmt(today) };
    }
  }
}
```

In the hook body, replace the `?period=` param:

```typescript
// BEFORE (broken — backend expects date_from/date_to):
const params = { period: selectedPeriod };

// AFTER (correct):
const { date_from, date_to } = periodToDates(selectedPeriod);
const params = { date_from, date_to };
```

**Intermediate check after B1**:
```bash
pnpm --filter web test -- --testPathPattern="useProfitability|profitability" 2>&1 | tail -8
```

---

## Task B2 — Add `getToken` Prop to `useSseChannel`

**File**: the path found by `find frontend/packages -name "useSseChannel*"` (verify exact path first)

Read the file completely before modifying. Preserve all existing behavior — `getToken` is optional and any hook not passing it must continue to work identically.

> Adjust the below to match the actual interface and implementation pattern you find.

**Interface change** (add `getToken` to the options interface):

```typescript
interface UseSseChannelOptions {
  getToken?: () => Promise<string>;   // NEW — fetch JWT, appended as ?token= to URL
  // ... preserve all existing options
}
```

**Implementation** (inside the `useEffect` that creates the `EventSource`):

```typescript
const openConnection = async () => {
  let finalUrl = url;

  if (options?.getToken) {
    try {
      const token = await options.getToken();
      const separator = url.includes('?') ? '&' : '?';
      finalUrl = `${url}${separator}token=${encodeURIComponent(token)}`;
    } catch (err) {
      console.error('[useSseChannel] Failed to fetch token:', err);
      return; // Don't open without auth
    }
  }

  // ... rest of existing EventSource creation logic
};
```

> **Important**: Read the existing hook implementation before adding this. The above is an approximation — integrate `getToken` into whatever pattern the hook already uses for connection setup. Do not restructure the hook; just add the JWT-fetch step before `new EventSource(url)`.

**Intermediate check after B2**:
```bash
pnpm --filter @pilot/ui test 2>&1 | tail -8
```

---

## Task B3 — Update All SSE Hook Consumers

For each file found in the Pre-Work grep, add the `getToken` prop.

**Standard `getToken` function** (use this in every consumer):

```typescript
import { fetchAuthSession } from 'aws-amplify/auth';

const getToken = async (): Promise<string> => {
  const session = await fetchAuthSession();
  return session.tokens?.accessToken?.toString() ?? '';
};
```

**Pattern for each consumer**:

```typescript
// Read the existing hook call first. Then add getToken:
const { } = useSseChannel('/api/v1/some/stream', {
  // ... existing options ...
  getToken,  // NEW
});
```

**`useDispatchSse` special handling**: Read this file first. It may already manually append `?token=`. If so:
- Option A: Refactor it to use the new `getToken` prop (removes duplication — preferred)
- Option B: If the manual approach is deeply intertwined, add `getToken` in addition and ensure the token is not appended twice

Confirm the behavior by checking the network requests in the dispatch board SSE connection — there must be exactly one `token=` param.

**Intermediate check after B3**:
```bash
pnpm --filter web test 2>&1 | tail -8
```

---

## Test Requirements

### Platform: Web (`apps/web`) + Shared UI (`packages/ui`)

- Route files are thin server components — no `"use client"` on route files
- Use `vi.mock()` (Vitest), not `jest.mock()`
- Mock `next/navigation` in any web component test that uses routing:
  ```typescript
  vi.mock("next/navigation", () => ({ usePathname: () => "/reports" }));
  ```
- Use `toBeInTheDocument()` (not `.toBeTruthy()`) for web assertions

### TanStack Query Setup

Always use `retry: false`:

```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

Never share a `QueryClient` instance across tests.

### Test files to create

**B1 — `useProfitability` tests** (`apps/web/src/features/profitability/hooks/__tests__/useProfitability.b17.test.ts`):
- Returns correct `date_from`/`date_to` for each period pill
- `periodToDates('7d')` produces dates 7 days apart ending today
- `periodToDates('mtd')` produces first of current month as `date_from`
- `periodToDates('ytd')` produces Jan 1 of current year as `date_from`

**B2 — `useSseChannel` tests** (in `packages/ui/src/sse/__tests__/` — check if test file exists):
- When `getToken` is not provided, URL is unchanged
- When `getToken` is provided, `?token=<value>` is appended to URL
- When `getToken` throws, connection is not opened

**Integration test** (`apps/web/src/__tests__/batch_b17/sseJwt.integration.test.tsx`):
- All SSE hook files audited by grep have `getToken` prop passed (structural check — verify imports)

### MSW handlers

For B17 Part B, no new MSW handlers are needed — existing profitability handlers should already respond to `?date_from=&date_to=` params (they typically accept any params). Verify:
```bash
cat frontend/apps/web/src/mocks/handlers/index.ts | grep -A 3 "profitability"
```

If the profitability mock handler rejects the `date_from`/`date_to` params, update it to accept them.

---

## Final Verification

### Phase 1 — Targeted tests (run after each task during development)

```bash
cd <repo>/frontend

# After B1:
pnpm --filter web test -- --testPathPattern="useProfitability|profitability" 2>&1 | tail -8

# After B2:
pnpm --filter @pilot/ui test 2>&1 | tail -8

# After B3:
pnpm --filter web test 2>&1 | tail -8
```

Fix any failure before moving to the next task.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== B17 PART B FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.**

---

## Definition of Done — B17 Part B

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 milestone checklist when each item is done:

- [ ] Pre-modification regression baseline captured for `@pilot/ui` and `web` (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design doc fully read (all sections A–I)
- [ ] All mandatory source files read before modifying (`useProfitability.ts`, `useSseChannel.ts`, `useDispatchSse.ts`, `mocks/handlers/index.ts`)
- [ ] All endpoint URLs verified in `openapi_schema_map.md`
- [ ] SSE hook consumer grep completed — full list of files to update captured
- [ ] **B1**: `useProfitability` — `?period=` replaced with `?date_from=&date_to=`; `periodToDates()` helper added; unit tests pass
- [ ] **B2**: `useSseChannel` — `getToken?: () => Promise<string>` prop added; appends `?token=` when provided; existing consumers without `getToken` unaffected
- [ ] **B3**: ALL SSE hook consumers found by grep pass `getToken`; `useDispatchSse` does not double-append token
- [ ] Profitability MSW handler accepts `date_from`/`date_to` params (updated if needed)
- [ ] `useProfitability` unit tests pass (`periodToDates` correctness)
- [ ] `useSseChannel` unit tests pass (with/without `getToken`)
- [ ] Integration test `sseJwt.integration.test.tsx` passes
- [ ] No regressions in `@pilot/ui` test suite
- [ ] No regressions in `web` test suite
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` passes)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification command passes** (`=== B17 PART B FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== B17 PART B FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — B17 Part B using this format:

```markdown
### B17 Part B — Frontend Hook Fixes: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (ui) | X passed (web)
**Final**: X+N passed (ui) | X+N passed (web) (+N new tests)

#### What Was Accomplished

- Fixed `useProfitability` to send `?date_from=&date_to=` — reports page no longer 422s
- Added `getToken` prop to `useSseChannel` — JWT now centrally appended to all SSE connections
- Updated N SSE hook consumers to pass `getToken` prop

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/features/profitability/hooks/useProfitability.ts` | Updated — periodToDates helper + date param conversion |
| `packages/ui/src/sse/useSseChannel.ts` | Updated — getToken prop added |
| `apps/web/src/features/dispatch-board/hooks/useDispatchSse.ts` | Updated — getToken prop |
| `apps/web/src/features/calendar-conflict/hooks/useCalendarConflictSse.ts` | Updated — getToken prop |
| `apps/web/src/features/field-issues/hooks/useFieldIssuesSse.ts` | Updated — getToken prop |
| `apps/web/src/features/quickbooks-conflict/hooks/useQbConflictsSse.ts` | Updated — getToken prop |
| `apps/web/src/features/customer-comms/hooks/useCustomerCommsSse.ts` | Updated — getToken prop |
| ... | ... |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `apps/web/src/features/profitability/hooks/__tests__/useProfitability.b17.test.ts` | Unit | N | ✅ |
| `packages/ui/src/sse/__tests__/useSseChannel.b17.test.ts` | Unit | N | ✅ |
| `apps/web/src/__tests__/batch_b17/sseJwt.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Batch

B17 is fully complete. The following surfaces should now work:
- `/reports` page — all period selections return data (no 422)
- `/comms` page — loads recent communications list
- Dashboard `RecentCustomerMessagesWidget` — shows SMS history for owners
- SSE-powered pages (dispatch board, calendar conflicts, QB conflicts, field issues, customer comms) — maintain authenticated real-time updates

**Next batch**: `batch-fe-b18-react-engr-prompt.md` — Customer Create/Edit + Site Management + Customer Detail. FE-B18 depends on B17 Part A (`mobile_phone` in `CustomerResponse`) being complete.
