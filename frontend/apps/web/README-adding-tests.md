# Adding Tests to the Pilot Web App Test Suite

**Version**: 1.0
**Date**: June 6, 2026
**Audience**: AI agents and engineers adding, updating, or debugging web app tests
**Test framework**: Vitest + jsdom + Testing Library + MSW + Playwright (e2e)

---

## Quick Rules

1. **Integration tests go in `__tests__/batch_{N}/`** — never in a new root-level folder
2. **Unit tests are co-located** with the component or hook they test (e.g., `MyComponent.test.tsx` next to `MyComponent.tsx`)
3. **Always use MSW for API mocking** — never mock `apiClient`, `fetch`, or `axios` directly
4. **Always set `retry: false`** on `QueryClient` in tests — prevents infinite retry loops in test env
5. **Never hardcode design token values** in tests — those are enforced by ESLint, not test assertions
6. **Run the baseline before any changes** — record test count; verify zero delta after implementation

---

## How to Run Tests

### ⚠️ Token-efficient output — always append tail

To minimize output token consumption, always append `| tail -N` to test commands:

```bash
# The canonical full-suite verification command (run from workspace root)
cd <repo>/frontend

pnpm --filter @pilot/ui check-types && \
pnpm --filter web check-types && \
pnpm --filter @pilot/ui lint && \
pnpm --filter web lint && \
echo "=== TYPE+LINT PASS ===" && \
pnpm --filter @pilot/ui test 2>&1 | tail -6 && \
pnpm --filter web test 2>&1 | tail -6 && \
echo "=== WEB FINAL VERIFICATION COMPLETE ==="
```

### Targeted runs (web only)

```bash
cd <repo>/frontend

# All web tests (fastest — use during development)
pnpm --filter web test 2>&1 | tail -6

# Web tests with output (debugging a specific failure)
pnpm --filter web test -- --reporter=verbose 2>&1 | tail -30

# Run a single test file
pnpm --filter web test -- __tests__/batch_fe_b5/quote-approval.integration.test.tsx 2>&1 | tail -10

# Run tests matching a pattern (grep)
pnpm --filter web test -- --reporter=verbose -t "owner approves" 2>&1 | tail -15

# Run a specific batch folder
pnpm --filter web test -- __tests__/batch_fe_b4/ 2>&1 | tail -10

# Type check only (fast — no test runner needed)
pnpm --filter web check-types

# Lint only
pnpm --filter web lint
```

### Capture regression baseline (always before making changes)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```

Record the exact output line (e.g., `Tests 127 passed (127) | Suites 34 passed (34)`). After changes, re-run and verify the delta matches exactly what you added.

---

## Where to Put New Tests

### Unit tests — co-located with source

```
frontend/apps/web/src/
  features/
    quote-approval/
      QuoteApprovalSurface.tsx
      QuoteApprovalSurface.test.tsx    ← unit test lives here
      hooks/
        useQuoteApproval.ts
        useQuoteApproval.test.ts       ← hook unit test lives here
```

### Integration tests — `__tests__/batch_{N}/`

```
frontend/apps/web/__tests__/
  batch_fe_b4/                         ← named after the batch that created it
    dispatch-board.integration.test.tsx
  batch_fe_b5/
    quote-approval.integration.test.tsx
  batch_beta_b3/                       ← beta fix batches
    ...
  test-utils/                          ← shared test utilities (render wrappers, etc.)
    renderWithProviders.tsx
    msw-server.ts
```

**Rule**: Never create a new root-level directory under `__tests__/`. Use `batch_{N}` naming for all new integration test folders. The `test-utils/` folder is for shared helpers only.

### E2E tests — `e2e/batch_{N}/`

```
frontend/apps/web/e2e/
  batch_fe_b5/
    quote-approval.e2e.spec.ts
```

---

## Minimum Viable Test File Templates

### Unit test (co-located)

```tsx
// apps/web/src/features/my-feature/MyComponent.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MyComponent } from "./MyComponent";

describe("<MyComponent>", () => {
  it("renders with required props", () => {
    render(<MyComponent label="Hello" />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("calls onPress when button clicked", async () => {
    const user = userEvent.setup();
    const onPress = vi.fn();
    render(<MyComponent label="Click me" onPress={onPress} />);
    await user.click(screen.getByRole("button", { name: /click me/i }));
    expect(onPress).toHaveBeenCalledOnce();
  });

  it("renders error state when error prop provided", () => {
    render(<MyComponent label="Hello" error="Something went wrong" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });
});
```

### Integration test (with TanStack Query + MSW)

```tsx
// apps/web/__tests__/batch_fe_b{N}/my-surface.integration.test.tsx
import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MySurface } from "@/features/my-feature/MySurface";

// ── MSW server setup ───────────────────────────────────────────────────────
const server = setupServer(
  http.get("/api/v1/my-resource", () =>
    HttpResponse.json([{ id: "r1", name: "Item 1" }]),
  ),
  http.post("/api/v1/my-resource", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: "r-new", ...body }, { status: 201 });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Test helper ────────────────────────────────────────────────────────────
function renderWithQuery(ui: React.ReactElement) {
  // ALWAYS set retry: false — prevents infinite retries in test env
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────
describe("MySurface — integration", () => {
  it("renders items from API", async () => {
    renderWithQuery(<MySurface />);
    expect(await screen.findByText("Item 1")).toBeInTheDocument();
  });

  it("shows loading state before data arrives", () => {
    // Delay the handler to test loading state
    server.use(
      http.get("/api/v1/my-resource", async () => {
        await new Promise((r) => setTimeout(r, 100));
        return HttpResponse.json([]);
      }),
    );
    renderWithQuery(<MySurface />);
    expect(screen.getByRole("status")).toBeInTheDocument(); // loading indicator
  });

  it("shows error state on API failure", async () => {
    server.use(
      http.get("/api/v1/my-resource", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );
    renderWithQuery(<MySurface />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("shows empty state when no items", async () => {
    server.use(http.get("/api/v1/my-resource", () => HttpResponse.json([])));
    renderWithQuery(<MySurface />);
    expect(await screen.findByText(/no items/i)).toBeInTheDocument();
  });
});
```

### MSW handler file (for shared test fixtures)

```typescript
// apps/web/src/mocks/handlers/myResourceHandlers.ts
import { http, HttpResponse } from "msw";
import type { components } from "@pilot/shared-types";

type MyResourceResponse = components["schemas"]["MyResourceResponse"];

export const myResourceHandlers = [
  http.get("/api/v1/my-resource", () =>
    HttpResponse.json<MyResourceResponse[]>([
      { id: "r1", name: "Item 1", status: "active" },
      { id: "r2", name: "Item 2", status: "draft" },
    ]),
  ),
];
```

---

## Key Test Utilities Available

### Vitest globals (no import needed)

`describe`, `it`, `expect`, `vi`, `beforeAll`, `afterAll`, `beforeEach`, `afterEach` — all available globally via `vitest.config.ts` `globals: true`.

### Testing Library

```typescript
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
// Always prefer userEvent over fireEvent for interactive tests
```

### `vitest.setup.ts` (already configured)

The setup file configures `@testing-library/jest-dom` matchers. These are available in all tests:

```typescript
// Available without imports:
expect(element).toBeInTheDocument();
expect(element).toBeVisible();
expect(element).toHaveTextContent("...");
expect(element).toHaveRole("button");
expect(element).toBeDisabled();
```

### Shared test-utils (use if available)

```typescript
// apps/web/__tests__/test-utils/ — check for existing render wrappers
import { renderWithProviders } from "../test-utils/renderWithProviders";
```

---

## MSW Rules

### In tests: always use `setupServer` from `msw/node`

```typescript
import { setupServer } from "msw/node"; // ← node, not browser
import { http, HttpResponse } from "msw";

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers()); // ← reset per-test overrides
afterAll(() => server.close());
```

### Per-test handler overrides

```typescript
it("handles 404", async () => {
  server.use(
    http.get("/api/v1/quotes/q1", () =>
      HttpResponse.json({ detail: "Not found" }, { status: 404 }),
    ),
  );
  // test runs with this override
});
// After the test, server.resetHandlers() restores the defaults
```

### Never mock `apiClient` directly

```typescript
// ❌ WRONG — bypasses the real HTTP layer; doesn't test real request params
vi.mock("@pilot/shared-api", () => ({
  apiClient: { get: vi.fn().mockResolvedValue({ data: [] }) },
}));

// ✅ CORRECT — MSW intercepts at the HTTP level; tests real request construction
server.use(http.get("/api/v1/quotes", () => HttpResponse.json([])));
```

---

## TanStack Query Testing Rules

### Always `retry: false`

```typescript
// ❌ WRONG — default retry=3 causes tests to wait 3+ retries before failing
const queryClient = new QueryClient();

// ✅ CORRECT — fail fast in tests
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});
```

### Always create a fresh `QueryClient` per test

```typescript
// ❌ WRONG — shared cache bleeds between tests
const queryClient = new QueryClient(...);  // module level

// ✅ CORRECT — fresh cache per test
function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({ ... });  // new instance each call
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}
```

### Use `findBy*` (async) not `getBy*` for async data

```typescript
// ❌ WRONG — synchronous; fails before data loads
expect(screen.getByText("Item 1")).toBeInTheDocument();

// ✅ CORRECT — waits for element to appear (up to 1s default)
expect(await screen.findByText("Item 1")).toBeInTheDocument();
```

---

## TypeScript & Lint Rules

Tests must pass the same type check + lint rules as production code:

```bash
# Type check (run before committing tests)
pnpm --filter web check-types

# Lint (must be zero warnings)
pnpm --filter web lint
```

**Common lint failures in tests:**

- `no-hardcoded-design-values` — don't assert on hex colors or pixel values
- `@typescript-eslint/no-explicit-any` — avoid `as any` casts in test assertions

---

## What NOT to Do

- ❌ **Do not put integration tests co-located** with source files — they belong in `__tests__/batch_{N}/`
- ❌ **Do not mock `apiClient` or `fetch` directly** — use MSW to intercept at the HTTP layer
- ❌ **Do not use `getBy*` for async data** — always use `findBy*` (async-aware)
- ❌ **Do not use `fireEvent` for user interactions** — use `userEvent` from `@testing-library/user-event`
- ❌ **Do not forget `server.resetHandlers()` in `afterEach`** — handler overrides leak between tests
- ❌ **Do not use `retry` defaults on QueryClient** — always set `retry: false` in test setup
- ❌ **Do not create a new root-level directory under `__tests__/`** — use `batch_{N}` naming
- ❌ **Do not import from `msw/browser` in tests** — always `msw/node`
- ❌ **Do not skip the regression baseline step** — always record test count before changes

---

## Test File Naming Convention

| Test Type           | Location               | Pattern                           |
| ------------------- | ---------------------- | --------------------------------- |
| Component unit test | Co-located with source | `MyComponent.test.tsx`            |
| Hook unit test      | Co-located with source | `useMyHook.test.ts`               |
| Utility unit test   | Co-located with source | `myUtil.test.ts`                  |
| Integration test    | `__tests__/batch_{N}/` | `my-surface.integration.test.tsx` |
| E2E test            | `e2e/batch_{N}/`       | `my-flow.e2e.spec.ts`             |

---

## E2E Tests (Playwright)

E2E tests require the Next.js dev server and a running backend. They are not run in CI by default.

```bash
# Run all web e2e tests (requires running server)
pnpm --filter web e2e

# Run a specific e2e spec
pnpm --filter web exec playwright test e2e/batch_fe_b5/quote-approval.e2e.spec.ts

# Run in headed mode (see browser)
pnpm --filter web exec playwright test --headed
```

See [`apps/web/README-playwright.md`](README-playwright.md) for Playwright setup and auth configuration.

---

## Relationship to `pilot-react-engineer-methods.md` §14

This README is the authoritative source for web test mechanics. [`dev-docs/architecture-design/pilot-react-engineer-methods.md`](../../../dev-docs/architecture-design/pilot-react-engineer-methods.md) §14 provides the strategic overview (test layers, coverage requirements, growth targets). When there is a conflict, this README takes precedence for mechanics (commands, file locations, setup patterns).
