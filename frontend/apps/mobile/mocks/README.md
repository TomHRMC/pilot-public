# Mobile MSW Mocks — House Documentation

**Location**: `apps/mobile/mocks/`
**Batch**: TEST-UPLIFT-1C (2026-08-28)

---

## 1. Two Opt-In Patterns (Per-File, Never Global)

Mobile tests use **per-file opt-in** MSW servers — `jest.setup.ts` does NOT
start a global server (design §G Q4). Choose one of these two patterns:

### Pattern A — Shared Server (default-fixture coverage)

Use when your test needs the default barrel handlers (e.g. a screen that
fetches from multiple endpoints):

```typescript
import { server } from "../../mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Per-test override:
server.use(
  http.get("*/api/v1/my-endpoint", () =>
    HttpResponse.json({ error: "x" }, { status: 500 }),
  ),
);
```

### Pattern B — Per-File Inline Server (bespoke flows)

Use when your test needs custom fixtures that differ from the barrel defaults:

```typescript
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

const server = setupServer(
  http.get("*/api/v1/my-endpoint", () => HttpResponse.json({ ... })),
);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

**When to use which**: Pattern A for broad integration tests that exercise
multiple barrel handlers. Pattern B for unit tests with bespoke fixtures or
error-path assertions.

---

## 2. Wildcard Prefix Rule (Rule 18)

`apiClient.baseURL` in the mobile app is an absolute URL (LAN IP like
`http://192.168.1.50:8000`). Relative-path handlers silently miss every
request. **Every mobile handler MUST use the `*/api/v1/...` wildcard prefix:**

```typescript
// ❌ BANNED — silently misses all apiClient requests
http.get("/api/v1/jobs/", handler);

// ✅ REQUIRED — matches requests to any origin
http.get("*/api/v1/jobs/", handler);
```

---

## 3. Why `voice.ws.ts` Is Isolated

`mocks/handlers/voice.ws.ts` contains the MSW WebSocket handler for
`/api/v1/voice/stream`. It uses `ws.link(...)` which **instantiates at
module-evaluation time**. If the Jest barrel (`handlers/index.ts`) imported
it, any Jest import of the barrel would evaluate MSW's WebSocket machinery
in the Node/jsdom environment, poisoning the shared server.

**The barrel is HTTP-only.** `mocks/browser.ts` composes the WS handler
itself for the dev runtime (`setupWorker(...handlers, voiceWsHandler)`).

**NEVER import `voice.ws.ts` from any Jest test or from `handlers/index.ts`.**

---

## 4. The No-apiClient-Mock Rule

**Never mock `@pilot/shared-api` directly** (`jest.mock("@pilot/shared-api", ...)`).
MSW intercepts at the HTTP level and is the only correct approach
(react-engineer-rules §9, inclusions §9).

This is enforced by a permanent anti-regression ratchet:
`apps/mobile/__tests__/meta/noApiClientMock.test.ts` scans all mobile test
files for the banned pattern and fails on any hit not in the checked-in
baseline (`no_api_client_mock_baseline.json`). The baseline ships as `{}` —
full closure was achieved in TEST-UPLIFT-1C.

---

## 5. `getApiProblem` for Error-Path Assertions

For error-path tests, MSW handlers return RFC 7807 error bodies. The shared
normalizer `getApiProblem` (from `@pilot/shared-api`) is RN-safe (no DOM
APIs) and parses all three FastAPI error shapes:

```typescript
import { getApiProblem } from "@pilot/shared-api";

// MSW handler returns RFC 7807:
server.use(
  http.get("*/api/v1/my-endpoint", () =>
    HttpResponse.json(
      {
        type: "about:blank",
        title: "Server Error",
        status: 500,
        detail: "server error",
      },
      { status: 500 },
    ),
  ),
);

// In the test, the hook's error state is set by Axios rejecting the response.
// getApiProblem can normalize the error if the code under test parses it.
```

---

## 6. Jest Exit Hygiene (`--forceExit` House Standard)

The mobile `test` script carries `--forceExit`
(`apps/mobile/package.json`: `"test": "jest --passWithNoTests --forceExit"`).

**Why**: MSW 2.x + Jest has a known upstream open-handle issue —
`server.close()` does not fully drain the Node event loop, so the CLI would
hang 5+ minutes AFTER all tests pass ("Jest did not exit" / "worker process
has failed to exit gracefully"). Tests take 1–3s each; the CLI never returns.

**Safety property**: `--forceExit` runs ALL tests to completion first and only
truncates the post-run event-loop drain — it cannot skip or shorten execution.

**Never** "fix" the hang by deleting `server.close()` / `resetHandlers()` —
those keep per-file isolation intact; the flag handles the drain.

**Diagnosing a REAL hang** (a test never completes — not the post-run drain):
run `pnpm --filter mobile test -- --detectOpenHandles` to find the leaked
handle (unclosed WS / DB connection / timer) and fix the source instead of
masking it.

---

## 7. Known Benign Warning: `[apiClient] fetchAuthSession threw`

Every MSW-intercepted request logs this console.warn under Jest
(`ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING_FLAG`): the apiClient request
interceptor's dynamic `import("aws-amplify/auth")` fails because Jest doesn't
run with `--experimental-vm-modules`. The interceptor's catch lets the request
proceed WITHOUT a JWT — MSW handlers match on URL/method and ignore
`Authorization`, so **every test passes correctly. Benign — verified
2026-08-28** (React Engineer + Architect). It became visible only because
TEST-UPLIFT-1C removed the wholesale `jest.mock("@pilot/shared-api")` blocks
that previously prevented the interceptor from ever running.

Suppression via `jest.mock("aws-amplify/auth")` / `moduleNameMapper` / mock
files does NOT work — Node's native `import()` bypasses Jest's module system.
Proper-fix options (vm-modules flag / static-import refactor / import→require
transformer) are tracked to BE-TESTS-MAINT — see
`frontend/react-engr-std-prompt-inclusions.md` §10.2 (which also covers the
benign W2 Babel loose-mode warnings).
