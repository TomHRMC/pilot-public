# Implementation Prompt: BETA-B2 — Frontend API Contract Fixes

**Mode**: Pilot React Engineer  
**Batch**: BETA-B2  
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B2  
**Estimated session**: 1–2 hours  
**No design doc required** — two precise hook fixes with well-defined targets  
**Prerequisite**: BETA-B1 must be complete (backend endpoints must exist before these hooks can be verified end-to-end)

---

## ⚠️ MANDATORY STOP: Read These Rules First

Before writing a single line of code, you MUST follow the rules in:
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — read it in full

The highest-risk rules for this batch:
- **Rule 1.1**: Check `backend/openapi_schema_map.md` BEFORE writing any hook. Verify the exact params from there — not from memory, not from the issue description.
- **Rule 1.3**: Run `pnpm sync-api-types` before coding; use `@pilot/shared-types` for any response types.
- **Rule 2**: All API calls go through `apiClient`. Never raw `fetch()`.
- **Rule 3**: SSE endpoints require `?token=JWT`. Browser `EventSource` cannot send `Authorization` headers.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
```

Record the pass counts. All tests passing now must still pass at the end.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the current `backend/openapi.json`. Run it now so you have the latest types before editing any hook.

---

## Pre-Work: Verify API Contracts

Check `backend/openapi_schema_map.md` for these two endpoints before writing any code:

```bash
# Quick check — confirm the profitability endpoint params:
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
path = '/api/v1/reports/profitability'
if path in spec['paths']:
    get_op = spec['paths'][path].get('get', {})
    params = get_op.get('parameters', [])
    for p in params:
        print(p.get('name'), '| required:', p.get('required'), '| type:', p.get('schema', {}).get('type'))
else:
    print('PATH NOT FOUND - stop and ask Tom')
"
```

```bash
# Confirm the SSE board stream endpoint and verify it accepts a token param:
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
for path, methods in spec['paths'].items():
    if 'stream' in path or 'sse' in path:
        get_op = methods.get('get', {})
        params = [p.get('name') for p in get_op.get('parameters', [])]
        print(path, '| params:', params)
"
```

**If either endpoint is not found or the params don't match the issue description → STOP and ask Tom.** Do not proceed with assumptions.

---

## Pre-Work: Mandatory File Reads

Read every file below using `read_file` before writing any code. **Do not assume what is in any of these files — they may have been modified since BETA-B1.**

```
frontend/apps/web/src/features/profitability/hooks/useProfitability.ts
frontend/packages/ui/src/hooks/useSseChannel.ts
frontend/apps/web/src/features/dispatch-board/hooks/useDispatchSse.ts
```

Also search for all other `useSseChannel` consumers in the codebase so you know which ones need the `getToken` prop:

```bash
grep -r "useSseChannel" frontend/apps/ --include="*.ts" --include="*.tsx" -l
```

Read each file found. For each SSE consumer, determine: does it call a protected (auth-required) endpoint? If yes, it needs the `getToken` prop.

---

## Task 1: Fix `useProfitability.ts` — Convert Period Pills to `date_from`/`date_to`

**Issue 3.5**: `GET /api/v1/reports/profitability?period=30d` returns 422 for all period selections. The backend requires `date_from` (YYYY-MM-DD) and `date_to` (YYYY-MM-DD). The hook currently sends `?period=7d` which doesn't match the API contract.

### Step 1a: Read the actual hook file

Use `read_file` on `frontend/apps/web/src/features/profitability/hooks/useProfitability.ts`.

Understand:
- What is the current parameter being sent to the API? (`period`? something else?)
- What TypeScript type does the hook accept for the period selection?
- What query key is used for TanStack Query?
- Does it use `apiClient`? (if it still uses raw `fetch()` — fix that too per Rule 2)

### Step 1b: Implement the date conversion

Replace the `?period=` parameter with computed `date_from` and `date_to` values. Use `date-fns` for all date arithmetic.

**First, verify `date-fns` is available:**

```bash
cat frontend/apps/web/package.json | grep date-fns
```

If not installed, also check the workspace root:
```bash
cat frontend/package.json | grep date-fns
```

**Conversion logic** (implement only what `openapi_schema_map.md` / `openapi.json` confirms the backend expects):

```typescript
import { format, subDays, startOfMonth, startOfYear } from 'date-fns';

function periodToDates(period: string): { date_from: string; date_to: string } {
  const today = new Date();
  const fmt = (d: Date) => format(d, 'yyyy-MM-dd');

  switch (period) {
    case '7d':
      return { date_from: fmt(subDays(today, 7)), date_to: fmt(today) };
    case '30d':
      return { date_from: fmt(subDays(today, 30)), date_to: fmt(today) };
    case 'mtd':
      return { date_from: fmt(startOfMonth(today)), date_to: fmt(today) };
    case 'ytd':
      return { date_from: fmt(startOfYear(today)), date_to: fmt(today) };
    case 'custom':
      // Custom dates passed directly — handled in BETA-B6
      throw new Error('Custom period requires explicit date_from/date_to');
    default:
      throw new Error(`Unknown period: ${period}`);
  }
}
```

**Updated hook call** — use the converted params:

```typescript
const { date_from, date_to } = periodToDates(activePeriod);
const { data } = await apiClient.get('/api/v1/reports/profitability', {
  params: { date_from, date_to }
});
```

**TanStack Query key** — update the query key to include `date_from` and `date_to` (not `period`) so cache invalidation works correctly:

```typescript
queryKey: ['profitability', date_from, date_to]
```

### Step 1c: Handle the `custom` period (BETA-B6 scope)

The `custom` period UI is not built yet (that's BETA-B6). For now, if `period === 'custom'` is somehow selected, the hook should gracefully handle it without throwing. Add an early return or skip the API call:

```typescript
if (period === 'custom' && (!customDateFrom || !customDateTo)) {
  return; // Don't fire API call — custom UI not yet built
}
```

### Step 1d: Write unit tests

**File**: `frontend/apps/web/src/features/profitability/hooks/useProfitability.test.ts`

```typescript
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { format, subDays, startOfMonth, startOfYear } from 'date-fns';

// Test the date conversion logic independently
describe('periodToDates()', () => {
  it('converts 7d to correct date range', () => {
    const { date_from, date_to } = periodToDates('7d');
    const today = new Date();
    expect(date_to).toBe(format(today, 'yyyy-MM-dd'));
    expect(date_from).toBe(format(subDays(today, 7), 'yyyy-MM-dd'));
  });

  it('converts 30d to correct date range', () => {
    const { date_from, date_to } = periodToDates('30d');
    const today = new Date();
    expect(date_from).toBe(format(subDays(today, 30), 'yyyy-MM-dd'));
  });

  it('converts mtd to first of current month', () => {
    const { date_from } = periodToDates('mtd');
    expect(date_from).toBe(format(startOfMonth(new Date()), 'yyyy-MM-dd'));
  });

  it('converts ytd to January 1 of current year', () => {
    const { date_from } = periodToDates('ytd');
    expect(date_from).toBe(format(startOfYear(new Date()), 'yyyy-MM-dd'));
  });

  it('all outputs are valid YYYY-MM-DD format', () => {
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    for (const period of ['7d', '30d', 'mtd', 'ytd']) {
      const { date_from, date_to } = periodToDates(period);
      expect(date_from).toMatch(dateRegex);
      expect(date_to).toMatch(dateRegex);
    }
  });
});

describe('useProfitability hook', () => {
  it('sends date_from and date_to params to the API (not period)', async () => {
    // Use MSW handler to verify the params the hook sends
    // The mock should assert that request.url contains date_from= and date_to=
    // and does NOT contain period=
    // (Wire up MSW handler per the existing test pattern in this codebase)
  });

  it('does not send a request when period is custom and no dates provided', () => {
    // Verify no API call is made
  });
});
```

> **Note**: For the integration test of the hook against MSW, follow whatever MSW setup pattern is already established in `apps/web/__tests__/` — read one existing test file first to understand the setup pattern before writing new tests.

---

## Task 2: Centralize JWT in `useSseChannel` via `getToken` Prop

**Issue 3.3**: Browser `EventSource` cannot send `Authorization` headers. The `useDispatchSse` hook already manually fetches the Amplify JWT and appends `?token=JWT` before opening the SSE connection. This manual pattern must be:
1. Moved into `useSseChannel` as an optional `getToken` prop
2. Applied to all auth-required SSE consumers (not just dispatch)

### Step 2a: Read the actual `useSseChannel` implementation

Use `read_file` on `frontend/packages/ui/src/hooks/useSseChannel.ts`.

Understand:
- Current function signature and return type
- How the `EventSource` URL is constructed
- How reconnection/polling fallback works
- What the `onMessage` callback receives

### Step 2b: Add `getToken` prop to `useSseChannel`

Extend the hook's options interface with an optional `getToken` prop. When provided, the hook fetches the token asynchronously and appends `?token=<jwt>` to the URL before opening `EventSource`. When not provided, the hook opens `EventSource` with the URL as-is (for non-auth SSE endpoints, if any).

```typescript
interface SseChannelOptions {
  onMessage: (event: MessageEvent) => void;
  fallbackToPollingMs?: number;
  getToken?: () => Promise<string>;   // NEW — optional JWT getter
  eventSourceFactory?: (url: string) => EventSource;  // existing, if present
}
```

**Implementation pattern**:

```typescript
export function useSseChannel(
  path: string,
  options: SseChannelOptions
) {
  const { onMessage, fallbackToPollingMs, getToken, eventSourceFactory } = options;

  useEffect(() => {
    let es: EventSource | null = null;
    let cancelled = false;

    async function connect() {
      let url = `${process.env.NEXT_PUBLIC_API_URL}${path}`;

      // If auth required, fetch JWT and append as query param
      if (getToken) {
        try {
          const token = await getToken();
          const separator = url.includes('?') ? '&' : '?';
          url = `${url}${separator}token=${encodeURIComponent(token)}`;
        } catch (err) {
          console.error('useSseChannel: failed to get token', err);
          return; // Don't open connection without auth
        }
      }

      if (cancelled) return;

      es = eventSourceFactory ? eventSourceFactory(url) : new EventSource(url);
      es.onmessage = onMessage;
      es.onerror = () => {
        // existing reconnect/fallback logic — preserve whatever was there
      };
    }

    connect();

    return () => {
      cancelled = true;
      es?.close();
    };
  }, [path, getToken, onMessage, fallbackToPollingMs, eventSourceFactory]);
}
```

> **Important**: Preserve the existing reconnect/exponential-backoff/fallback-to-polling logic exactly as it is. You are only adding the `getToken` path — do not refactor or remove anything else.

### Step 2c: Update `useDispatchSse` to use `getToken` prop

Read `frontend/apps/web/src/features/dispatch-board/hooks/useDispatchSse.ts`.

Currently it manually fetches the JWT and appends it to the URL before calling `useSseChannel`. Update it to pass `getToken` to `useSseChannel` instead:

```typescript
// BEFORE (manual JWT pattern):
const token = await getAmplifyToken();
useSseChannel(`/api/v1/scheduling/board/stream?token=${token}`, { onMessage });

// AFTER (getToken prop pattern):
useSseChannel('/api/v1/scheduling/board/stream', {
  getToken: getAmplifyToken,  // passes the getter, not the token value
  onMessage,
});
```

> The `getToken` prop receives a **function** (the getter), not the token value itself. The hook calls the function each time it opens a connection, which is correct behavior since Amplify tokens expire and need refreshing.

### Step 2d: Audit and update all other SSE consumers

From your pre-work grep, you have a list of all files that import or call `useSseChannel`. For each one:

1. Read the file
2. Determine: does it call a backend endpoint that requires authentication (has `require_permission(...)` or `get_current_user` on the backend)?
3. If yes: add `getToken: getAmplifyToken` to the options
4. If no (public endpoint or already handled): leave as-is

**How to get `getAmplifyToken` in a consumer hook:**

```typescript
import { fetchAuthSession } from 'aws-amplify/auth';

async function getAmplifyToken(): Promise<string> {
  const session = await fetchAuthSession();
  return session.tokens?.idToken?.toString() ?? '';
}
```

This is the same pattern `useDispatchSse` already uses — verify by reading the current `useDispatchSse` file.

### Step 2e: Write unit tests for `useSseChannel`

Find the existing test file for `useSseChannel` (it should exist at `packages/ui/src/hooks/useSseChannel.test.ts` or similar). If it exists, read it before adding tests. Add:

```typescript
describe('useSseChannel with getToken', () => {
  it('appends ?token= to the URL when getToken is provided', async () => {
    const getToken = vi.fn().mockResolvedValue('test-jwt-token');
    const capturedUrls: string[] = [];

    const mockEventSourceFactory = (url: string) => {
      capturedUrls.push(url);
      return { onmessage: null, onerror: null, close: vi.fn() } as unknown as EventSource;
    };

    renderHook(() =>
      useSseChannel('/api/v1/scheduling/board/stream', {
        getToken,
        onMessage: vi.fn(),
        eventSourceFactory: mockEventSourceFactory,
      })
    );

    await waitFor(() => {
      expect(capturedUrls.length).toBeGreaterThan(0);
    });

    expect(capturedUrls[0]).toContain('?token=test-jwt-token');
    expect(capturedUrls[0]).not.toContain('?token=test-jwt-token&token=');  // no duplicates
  });

  it('opens EventSource without token when getToken is not provided', async () => {
    const capturedUrls: string[] = [];

    const mockEventSourceFactory = (url: string) => {
      capturedUrls.push(url);
      return { onmessage: null, onerror: null, close: vi.fn() } as unknown as EventSource;
    };

    renderHook(() =>
      useSseChannel('/api/v1/some/public/stream', {
        onMessage: vi.fn(),
        eventSourceFactory: mockEventSourceFactory,
      })
    );

    await waitFor(() => {
      expect(capturedUrls.length).toBeGreaterThan(0);
    });

    expect(capturedUrls[0]).not.toContain('token=');
  });

  it('does not open connection if getToken throws', async () => {
    const getToken = vi.fn().mockRejectedValue(new Error('Auth failed'));
    const mockEventSourceFactory = vi.fn();

    renderHook(() =>
      useSseChannel('/api/v1/scheduling/board/stream', {
        getToken,
        onMessage: vi.fn(),
        eventSourceFactory: mockEventSourceFactory,
      })
    );

    await waitFor(() => {
      expect(getToken).toHaveBeenCalled();
    });

    expect(mockEventSourceFactory).not.toHaveBeenCalled();
  });
});
```

---

## Post-Implementation Verification

### 1. Run the test suites

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
```

All pre-existing tests must still pass. New tests must pass.

### 2. TypeScript check

```bash
pnpm --filter @pilot/ui check-types 2>&1 | tail -5
pnpm --filter web check-types 2>&1 | tail -5
```

Zero type errors required.

### 3. Lint check

```bash
pnpm lint 2>&1 | tail -10
```

Zero `no-hardcoded-design-values` warnings required.

### 4. Manual verification (requires dev server running)

**Profitability fix (Task 1)**:
1. Open `http://localhost:3000/reports`
2. Click each period pill: 7 Days, 30 Days, MTD, YTD
3. Open browser DevTools → Network tab
4. Confirm requests go to `/api/v1/reports/profitability?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` (NOT `?period=7d`)
5. Confirm responses are 200 (not 422)

**SSE getToken fix (Task 2)**:
1. Open `http://localhost:3000/schedule`
2. Open browser DevTools → Network tab → Filter by "stream"
3. Confirm the SSE connection URL includes `?token=<jwt>` in the query string
4. Confirm no 401 or 422 errors on the SSE connection

---

## Definition of Done — BETA-B2

Update the `pilot-app-beta-fixes-v1-impl-plan.md` §9 Batch Completion Tracker once all items below are checked:

- [ ] Pre-modification regression baseline captured (test counts recorded before any changes)
- [ ] `pnpm sync-api-types` run; `api-schema.d.ts` is current
- [ ] `backend/openapi_schema_map.md` verified: profitability endpoint requires `date_from` + `date_to` (not `period`)
- [ ] All mandatory source files read before writing code (`useProfitability.ts`, `useSseChannel.ts`, `useDispatchSse.ts`, all SSE consumers)
- [ ] **Task 1**: `useProfitability.ts` sends `date_from` + `date_to` params (confirmed via Network tab or test)
- [ ] **Task 1**: All four period pills (7d, 30d, mtd, ytd) return 200 on the profitability endpoint (not 422)
- [ ] **Task 1**: `date-fns` is used for all date arithmetic (no manual UTC offset arithmetic)
- [ ] **Task 1**: `custom` period gracefully skips API call (no crash) until BETA-B6
- [ ] **Task 2**: `useSseChannel` has optional `getToken?: () => Promise<string>` prop
- [ ] **Task 2**: When `getToken` is provided, `?token=<jwt>` is appended to the URL before `EventSource` opens
- [ ] **Task 2**: When `getToken` is not provided, `EventSource` opens with the URL as-is (no regression)
- [ ] **Task 2**: `useDispatchSse` updated to use `getToken` prop instead of manual URL concatenation
- [ ] **Task 2**: All other auth-required SSE consumers audited; updated where needed
- [ ] All new tests pass with zero failures
- [ ] Zero TypeScript errors (`pnpm check-types` passes on both `@pilot/ui` and `web`)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] Update this Definition of Done list with completion checks next to each item if completed
- [ ] Final test count (before/after) documented in impl plan tracker in the source plan
- [ ] Summary of work accomplished added to new sub-section in impl plan tracker in Section 9 in the source plan after the last batch entry
