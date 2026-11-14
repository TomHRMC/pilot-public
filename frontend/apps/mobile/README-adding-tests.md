# Adding Tests to the Pilot Mobile App Test Suite

**Version**: 1.0
**Date**: June 6, 2026
**Audience**: AI agents and engineers adding, updating, or debugging mobile app tests
**Test framework**: Jest (jest-expo preset) + Testing Library React Native + MSW + Maestro (e2e)

---

## Quick Rules

1. **Integration tests go in `__tests__/batch_{N}/`** — never in a new root-level folder
2. **Unit tests are co-located** with the component or hook they test
3. **Always use MSW for API mocking** — never mock `apiClient` or `fetch` directly
4. **Always set `retry: false`** on `QueryClient` in tests — prevents infinite retry loops
5. **WatermelonDB must be mocked in tests** — real database writes are not allowed in unit/integration tests
6. **Run the baseline before any changes** — record exact test count; verify delta matches what you added

---

## How to Run Tests

### ⚠️ Token-efficient output — always append tail

To minimize output token consumption, always append `2>&1 | tail -N` to test commands:

```bash
# The canonical full-suite verification command (run from workspace root)
cd <repo>/frontend

pnpm --filter @pilot/ui check-types && \
pnpm --filter web check-types && \
pnpm --filter mobile build && \
pnpm --filter @pilot/ui lint && \
pnpm --filter web lint && \
pnpm --filter mobile lint && \
echo "=== TYPE+LINT PASS ===" && \
pnpm --filter @pilot/ui test 2>&1 | tail -6 && \
pnpm --filter web test 2>&1 | tail -6 && \
pnpm --filter mobile test 2>&1 | tail -8 && \
echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> **Note**: `pnpm --filter mobile build` runs `tsc --noEmit` (see `package.json` scripts). This is the mobile type-check step — there is no separate `check-types` script.

### Targeted runs (mobile only)

```bash
cd <repo>/frontend

# All mobile tests (use during development)
pnpm --filter mobile test 2>&1 | tail -8

# Mobile tests with verbose output (debugging a failure)
pnpm --filter mobile test -- --verbose 2>&1 | tail -30

# Run a single test file
pnpm --filter mobile test -- features/jobs/components/__tests__/JobCardRow.test.tsx 2>&1 | tail -10

# Run tests matching a pattern (grep)
pnpm --filter mobile test -- --testNamePattern="renders customer name" 2>&1 | tail -15

# Run a specific batch folder
pnpm --filter mobile test -- __tests__/batch_mob_b1/ 2>&1 | tail -10

# Type check only (no test runner)
pnpm --filter mobile build 2>&1 | tail -10

# Lint only
pnpm --filter mobile lint 2>&1 | tail -10

# Watch mode (interactive development)
pnpm --filter mobile test:watch
```

### Capture regression baseline (always before making changes)

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact output lines. Example output to record:

```
Test Suites: 57 passed, 57 total
Tests:       369 passed, 369 total
```

After changes, re-run and verify the suite/test delta matches exactly what you added.

---

## Where to Put New Tests

### Unit tests — co-located with source

```
frontend/apps/mobile/features/
  jobs/
    components/
      JobCardRow.tsx
      __tests__/
        JobCardRow.test.tsx          ← component unit test
    hooks/
      useTechJobsList.ts
      __tests__/
        useTechJobsList.test.ts      ← hook unit test
    utils/
      calcVoltageDrop.ts
      calcVoltageDrop.test.ts        ← utility unit test (may be co-located directly)
```

### Integration tests — `__tests__/batch_{N}/`

```
frontend/apps/mobile/__tests__/
  batch_mob_b1/                      ← named after the batch that created it
    jobs-tab.integration.test.tsx
  batch_mob_b2/
    job-detail.integration.test.tsx
    sync-screen.integration.test.tsx
  batch_fe_b7/                       ← historical FE batch tests
    ...
  batch_mob_b3/
    customers-tab.integration.test.tsx
```

**Rule**: Never create a new root-level directory under `__tests__/`. Use `batch_{N}` naming for all new integration test folders.

### E2E tests — `e2e/` (Maestro)

```
frontend/apps/mobile/e2e/
  batch_fe_b3/
    voice-quote-creation.flow.yaml
```

---

## Minimum Viable Test File Templates

### Unit test — component (co-located in `__tests__/`)

```tsx
// features/my-feature/components/__tests__/MyComponent.test.tsx
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { MyComponent } from "../MyComponent";

describe("<MyComponent>", () => {
  it("renders with required props", () => {
    render(<MyComponent label="Hello" onPress={jest.fn()} />);
    expect(screen.getByText("Hello")).toBeTruthy();
  });

  it("calls onPress when pressed", () => {
    const onPress = jest.fn();
    render(<MyComponent label="Click me" onPress={onPress} />);
    fireEvent.press(screen.getByText("Click me"));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it("applies testID for e2e targeting", () => {
    render(
      <MyComponent label="Hello" onPress={jest.fn()} testID="my-component" />,
    );
    expect(screen.getByTestId("my-component")).toBeTruthy();
  });
});
```

### Unit test — hook (TanStack Query + MSW)

```typescript
// features/my-feature/hooks/__tests__/useMyHook.test.ts
import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { useMyHook } from "../useMyHook";
import React from "react";

const server = setupServer(
  http.get("/api/v1/my-resource", () =>
    HttpResponse.json([{ id: "r1", name: "Item 1" }])
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("useMyHook", () => {
  it("fetches and returns data", async () => {
    const { result } = renderHook(() => useMyHook(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data![0].name).toBe("Item 1");
  });

  it("calls the correct endpoint", async () => {
    let requestUrl = "";
    server.use(
      http.get("/api/v1/my-resource", ({ request }) => {
        requestUrl = request.url;
        return HttpResponse.json([]);
      })
    );
    const { result } = renderHook(() => useMyHook(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(requestUrl).toContain("/api/v1/my-resource");
  });

  it("handles API error gracefully", async () => {
    server.use(
      http.get("/api/v1/my-resource", () =>
        HttpResponse.json({ detail: "Error" }, { status: 500 })
      )
    );
    const { result } = renderHook(() => useMyHook(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
```

### Integration test — screen (co-located MSW + full render)

```tsx
// __tests__/batch_mob_b{N}/my-screen.integration.test.tsx
import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { MyTabScreen } from "@/features/my-feature/components/MyTabScreen";

// Use the shared MSW handlers from the project's mocks directory
// (or define inline for tests that need specific behavior)
const server = setupServer(
  http.get("/api/v1/my-resource", () =>
    HttpResponse.json([
      { id: "r1", name: "Item 1", status: "active" },
      { id: "r2", name: "Item 2", status: "draft" },
    ]),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Mock Expo Router — screens use router.push for navigation
const mockPush = jest.fn();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush, back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: mockPush, back: jest.fn() },
}));

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("MyTabScreen — integration", () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it("renders items from API", async () => {
    renderWithQuery(<MyTabScreen />);
    expect(await screen.findByText("Item 1")).toBeTruthy();
    expect(screen.getByText("Item 2")).toBeTruthy();
  });

  it("shows loading state before data arrives", () => {
    renderWithQuery(<MyTabScreen />);
    // Loading indicator visible synchronously before data loads
    expect(screen.getByTestId("loading-indicator")).toBeTruthy();
  });

  it("shows error state on API failure", async () => {
    server.use(
      http.get("/api/v1/my-resource", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );
    renderWithQuery(<MyTabScreen />);
    expect(await screen.findByText(/failed to load/i)).toBeTruthy();
  });

  it("shows empty state when API returns no items", async () => {
    server.use(http.get("/api/v1/my-resource", () => HttpResponse.json([])));
    renderWithQuery(<MyTabScreen />);
    expect(await screen.findByText(/no items/i)).toBeTruthy();
  });

  it("navigates on item press", async () => {
    renderWithQuery(<MyTabScreen />);
    await screen.findByText("Item 1");
    fireEvent.press(screen.getByText("Item 1"));
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("r1"));
  });

  it("pull-to-refresh triggers refetch", async () => {
    renderWithQuery(<MyTabScreen />);
    await screen.findByText("Item 1");
    const list = screen.getByTestId("my-flatlist");
    fireEvent(list, "refresh");
    // After refresh, data should still be visible
    expect(await screen.findByText("Item 1")).toBeTruthy();
  });
});
```

---

## MSW Rules

### In tests: always use `setupServer` from `msw/node`

```typescript
import { setupServer } from "msw/node"; // ← node, not browser
import { http, HttpResponse } from "msw";

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers()); // ← critical — resets per-test overrides
afterAll(() => server.close());
```

### Shared MSW handlers (register in `mocks/handlers/index.ts`)

```typescript
// mocks/handlers/myFeatureHandlers.ts
import { http, HttpResponse } from "msw";

export const myFeatureHandlers = [
  http.get("/api/v1/my-resource", () =>
    HttpResponse.json([{ id: "r1", name: "Test Item" }]),
  ),
];

// mocks/handlers/index.ts
import { myFeatureHandlers } from "./myFeatureHandlers";
export const handlers = [
  ...existingHandlers,
  ...myFeatureHandlers, // register here for server.ts (used by all tests)
];
```

### Never mock `apiClient` directly

```typescript
// ❌ WRONG — bypasses HTTP layer; doesn't test real request construction
jest.mock("@pilot/shared-api", () => ({
  apiClient: { get: jest.fn().mockResolvedValue({ data: [] }) },
}));

// ✅ CORRECT — MSW intercepts at the HTTP level
server.use(http.get("/api/v1/my-resource", () => HttpResponse.json([])));
```

---

## WatermelonDB Mock Rules

WatermelonDB **must not** write to a real database in tests. Mock it at the module level.

### Standard WatermelonDB mock (for offline-write hooks)

```typescript
// In your test file or a shared setup file:
jest.mock("../../../database", () => ({
  database: {
    write: jest.fn((fn) => fn()), // execute the callback synchronously
    get: jest.fn(() => ({
      create: jest.fn((fn) => {
        const record = {
          id: "mock-id",
          localSyncStatus: "pending",
        };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));
```

### Testing WatermelonDB write hooks

```typescript
// features/offline-sync/hooks/__tests__/useCreateExpense.test.ts
import { renderHook, act } from "@testing-library/react-native";
import { useCreateExpense } from "../useCreateExpense";

// Mock the database module
jest.mock("../../../database", () => ({
  database: {
    write: jest.fn((fn) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn) => {
        const record = { id: "expense-1", localSyncStatus: "pending" };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));

describe("useCreateExpense", () => {
  it("creates expense with pending sync status", async () => {
    const { result } = renderHook(() => useCreateExpense());

    await act(async () => {
      await result.current.create({
        jobId: "job-1",
        userId: "user-1",
        jobExpenseCategoryCode: "materials",
        costCents: 4500,
        isBillable: true,
        incurredAt: new Date(),
      });
    });

    expect(result.current.isPending).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
```

---

## Expo Router Mock Rules

All screens that use Expo Router navigation must mock it in tests:

```typescript
const mockPush = jest.fn();
const mockBack = jest.fn();
const mockReplace = jest.fn();

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack, replace: mockReplace }),
  useLocalSearchParams: () => ({ id: "test-id" }), // adjust params per test
  router: { push: mockPush, back: mockBack, replace: mockReplace },
  Link: ({ children, href }: { children: React.ReactNode; href: string }) =>
    children,
}));

// Clear between tests
beforeEach(() => {
  mockPush.mockClear();
  mockBack.mockClear();
  mockReplace.mockClear();
});

// Assert navigation
expect(mockPush).toHaveBeenCalledWith("/(tabs)/jobs/job-1");
```

---

## TanStack Query Testing Rules

### Always `retry: false`

```typescript
// ❌ WRONG — default retry=3 causes test timeouts
const queryClient = new QueryClient();

// ✅ CORRECT — fail fast
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});
```

### Create a fresh `QueryClient` per test via wrapper

```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// Usage in renderHook:
const { result } = renderHook(() => useMyHook(), { wrapper: createWrapper() });

// Usage in render:
render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MyScreen /></QueryClientProvider>);
```

### Use `waitFor` or `findBy*` for async assertions

```typescript
// ❌ WRONG — synchronous assertion fails before data loads
expect(screen.getByText("Item 1")).toBeTruthy();

// ✅ CORRECT — waits up to 1000ms for element to appear
expect(await screen.findByText("Item 1")).toBeTruthy();

// ✅ ALSO CORRECT — explicit waitFor
await waitFor(() => expect(screen.getByText("Item 1")).toBeTruthy());
```

---

## Testing Library — Mobile vs Web Differences

| Concern           | Web (Vitest + jsdom)     | Mobile (Jest + RN)                  |
| ----------------- | ------------------------ | ----------------------------------- |
| Import            | `@testing-library/react` | `@testing-library/react-native`     |
| Element assertion | `toBeInTheDocument()`    | `.toBeTruthy()` or `not.toBeNull()` |
| User events       | `userEvent.click(el)`    | `fireEvent.press(el)`               |
| Async wait        | `findByText()`           | `findByText()`                      |
| Accessibility     | `getByRole("button")`    | `getByRole("button")` (same API)    |
| testID            | `data-testid="..."`      | `testID="..."` prop                 |

### Useful RN-specific assertions

```typescript
// Check text is visible
expect(screen.getByText("Hello")).toBeTruthy();

// Check testID exists
expect(screen.getByTestId("my-component")).toBeTruthy();

// Check multiple items
expect(screen.getAllByTestId("list-item")).toHaveLength(3);

// Query (no throw if missing)
expect(screen.queryByText("Shouldn't be here")).toBeNull();

// RBAC: element should NOT be present
expect(screen.queryByTestId("owner-only-section")).toBeNull();
```

---

## `@pilot/shared-api` Import Path

```typescript
// ✅ CORRECT — from the package
import { apiClient } from "@pilot/shared-api";

// The moduleNameMapper in package.json resolves this to:
// packages/shared-api/src/index.ts
```

---

## TypeScript & Lint Rules

Tests must pass the same checks as production code:

```bash
# Type check (tsc --noEmit via the build script)
pnpm --filter mobile build 2>&1 | tail -10

# Lint
pnpm --filter mobile lint 2>&1 | tail -10
```

**Common issues in mobile tests:**

- `as any` casts — avoid in test assertions; use proper typing or `unknown` cast
- Missing `React` import — some test environments require explicit `import React from "react"`

---

## What NOT to Do

- ❌ **Do not put integration tests co-located** with source files — they belong in `__tests__/batch_{N}/`
- ❌ **Do not mock `apiClient` directly** — use MSW to intercept at the HTTP layer
- ❌ **Do not write to a real WatermelonDB** — always mock `database` module in tests
- ❌ **Do not use `retry` defaults on QueryClient** — always set `retry: false` in test setup
- ❌ **Do not use `getBy*` for async data** — always use `findBy*` or `waitFor()`
- ❌ **Do not forget `server.resetHandlers()` in `afterEach`** — handler overrides leak between tests
- ❌ **Do not import from `msw/browser`** — always use `msw/node` in Jest tests
- ❌ **Do not forget to mock `expo-router`** — any screen with navigation needs the mock
- ❌ **Do not create a new root-level directory under `__tests__/`** — use `batch_{N}` naming
- ❌ **Do not skip the regression baseline step** — always record test count before changes

---

## Test File Naming Convention

| Test Type           | Location                             | Pattern                          |
| ------------------- | ------------------------------------ | -------------------------------- |
| Component unit test | `features/.../components/__tests__/` | `MyComponent.test.tsx`           |
| Hook unit test      | `features/.../hooks/__tests__/`      | `useMyHook.test.ts`              |
| Utility unit test   | Co-located or in `utils/`            | `myUtil.test.ts`                 |
| Integration test    | `__tests__/batch_{N}/`               | `my-screen.integration.test.tsx` |
| E2E test            | `e2e/batch_{N}/`                     | `my-flow.flow.yaml` (Maestro)    |

---

## E2E Tests (Maestro)

```yaml
# e2e/batch_mob_b{N}/my-feature.flow.yaml
appId: com.pilotfortrades.mobile
---
- launchApp:
    clearState: true
- tapOn:
    text: "Sign In"
- inputText: "tech@test-tenant.com"
- tapOn:
    text: "Password"
- inputText: "TestPassword123!"
- tapOn: "Submit"
- assertVisible: "Jobs"
- tapOn:
    id: "menu-jobs"
- assertVisible: "Today"
```

Run Maestro e2e tests:

```bash
# Requires Maestro CLI installed and simulator running
cd frontend/apps/mobile
maestro test e2e/batch_mob_b{N}/my-feature.flow.yaml
```

See [`apps/mobile/README-maestro.md`](README-maestro.md) for Maestro setup.

---

## Relationship to `pilot-react-engineer-methods.md` §14

This README is the authoritative source for mobile test mechanics. [`dev-docs/architecture-design/pilot-react-engineer-methods.md`](../../../dev-docs/architecture-design/pilot-react-engineer-methods.md) §14 provides the strategic overview (test layers, coverage requirements, growth targets). When there is a conflict, this README takes precedence for mechanics (commands, file locations, setup patterns).
