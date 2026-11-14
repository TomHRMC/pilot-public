/**
 * B17 Part B — SSE JWT Integration Test
 *
 * Location: apps/web/__tests__/batch_b17/sseJwt.integration.test.tsx
 *
 * Structural verification: confirms that all SSE hook consumers in the web app
 * pass a `getToken` prop to `useSseChannel` for centralized JWT auth injection.
 *
 * Per batch-b17-react-engr-prompt.md §Test Requirements — Integration test
 *
 * Why structural checks?
 *   Browser EventSource cannot send Authorization headers. The ONLY supported
 *   auth mechanism for SSE endpoints is ?token= query param — which useSseChannel
 *   appends when `getToken` is provided. A consumer that omits `getToken` silently
 *   connects unauthenticated and receives 401 errors at runtime.
 *
 * Confirmed consumers (B17 audit):
 *   - useDispatchSse         → /api/v1/scheduling/board/stream
 *   - useCalendarConflictSse → /api/v1/integrations/calendar/conflicts/stream
 *   - useFieldIssuesSse      → /api/v1/owner/field-issues/stream
 *   - useQbConflictsSse      → /api/v1/integrations/quickbooks/conflicts/stream
 *   - useCustomerCommsSse    → /api/v1/customers/{id}/comms/stream
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

// __dirname = apps/web/__tests__/batch_b17
// ../../src  = apps/web/src  ✅
// ../../../../packages/ui = frontend/packages/ui  ✅
const SRC = resolve(__dirname, "../../src");
const UI_HOOKS = resolve(__dirname, "../../../../packages/ui/src/hooks");

// ─── useSseChannel interface ──────────────────────────────────────────────────

describe("B17 SSE JWT — useSseChannel interface", () => {
  it("declares getToken as optional prop on UseSseChannelOptions", () => {
    const src = readFileSync(resolve(UI_HOOKS, "useSseChannel.ts"), "utf8");
    expect(src).toContain("getToken?:");
    expect(src).toContain("Promise<string>");
  });

  it("implements token append in openConnection (encodeURIComponent)", () => {
    const src = readFileSync(resolve(UI_HOOKS, "useSseChannel.ts"), "utf8");
    expect(src).toContain("getToken");
    expect(src).toContain("token=");
    expect(src).toContain("encodeURIComponent(token)");
  });

  it("aborts connection when getToken throws", () => {
    const src = readFileSync(resolve(UI_HOOKS, "useSseChannel.ts"), "utf8");
    // Must not open EventSource if getToken fails
    expect(src).toContain("return; // Do not open EventSource without auth");
  });
});

// ─── useDispatchSse ───────────────────────────────────────────────────────────

describe("B17 SSE JWT — useDispatchSse", () => {
  it("wires getToken prop to useSseChannel", () => {
    const src = readFileSync(
      resolve(SRC, "features/dispatch-board/hooks/useDispatchSse.ts"),
      "utf8",
    );
    expect(src).toContain("getToken");
    expect(src).toContain("getAmplifyToken");
    expect(src).toContain("useSseChannel");
  });

  it("uses getToken ?? getAmplifyToken pattern (test injection support)", () => {
    const src = readFileSync(
      resolve(SRC, "features/dispatch-board/hooks/useDispatchSse.ts"),
      "utf8",
    );
    // Must support overriding getToken for test injection
    expect(src).toContain("getToken ?? getAmplifyToken");
  });
});

// ─── useCalendarConflictSse ───────────────────────────────────────────────────

describe("B17 SSE JWT — useCalendarConflictSse", () => {
  it("wires getToken prop to useSseChannel", () => {
    const src = readFileSync(
      resolve(
        SRC,
        "features/calendar-conflict/hooks/useCalendarConflictSse.ts",
      ),
      "utf8",
    );
    expect(src).toContain("getToken");
    expect(src).toContain("getAmplifyToken");
    expect(src).toContain("useSseChannel");
  });
});

// ─── useFieldIssuesSse ────────────────────────────────────────────────────────

describe("B17 SSE JWT — useFieldIssuesSse", () => {
  it("wires getToken prop to useSseChannel", () => {
    const src = readFileSync(
      resolve(SRC, "features/field-issues/hooks/useFieldIssuesSse.ts"),
      "utf8",
    );
    expect(src).toContain("getToken");
    expect(src).toContain("getAmplifyToken");
    expect(src).toContain("useSseChannel");
  });
});

// ─── useQbConflictsSse ────────────────────────────────────────────────────────

describe("B17 SSE JWT — useQbConflictsSse", () => {
  it("wires getToken prop to useSseChannel", () => {
    const src = readFileSync(
      resolve(SRC, "features/quickbooks-conflict/hooks/useQbConflictsSse.ts"),
      "utf8",
    );
    expect(src).toContain("getToken");
    expect(src).toContain("getAmplifyToken");
    expect(src).toContain("useSseChannel");
  });
});

// ─── useCustomerCommsSse ──────────────────────────────────────────────────────

describe("B17 SSE JWT — useCustomerCommsSse", () => {
  it("wires getToken prop to useSseChannel", () => {
    const src = readFileSync(
      resolve(SRC, "features/customer-comms/hooks/useCustomerCommsSse.ts"),
      "utf8",
    );
    expect(src).toContain("getToken");
    expect(src).toContain("getAmplifyToken");
    expect(src).toContain("useSseChannel");
  });
});

// ─── Profitability hook uses date params not period shorthand ─────────────────

describe("B17 SSE JWT — useProfitability uses date params", () => {
  it("sends date_from and date_to (not period shorthand) to API", () => {
    const src = readFileSync(
      resolve(SRC, "features/profitability/hooks/useProfitability.ts"),
      "utf8",
    );
    expect(src).toContain("date_from");
    expect(src).toContain("date_to");
    expect(src).toContain("periodToDates");
    // Must NOT send period= shorthand as main param
    expect(src).not.toContain("params: { period");
  });
});
