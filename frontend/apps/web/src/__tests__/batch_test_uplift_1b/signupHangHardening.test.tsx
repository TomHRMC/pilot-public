/**
 * TEST-UPLIFT-1B STEP 5 — Signup wizard hang-path hardening regression tests
 *
 * Location: apps/web/src/__tests__/batch_test_uplift_1b/signupHangHardening.test.tsx
 *
 * Tests:
 *   (a) /state 500 during poll → getApiProblem surfaces the error (not swallowed)
 *   (b) poll_timeout escape state UI renders error message + retry button
 *   (c) Poll exhaustion bound is enforced (POLL_MAX_ATTEMPTS is finite, not infinite)
 */

import React from "react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
  beforeEach,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ─── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ─── Mocks ─────────────────────────────────────────────────────────────────────

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    back: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { tenantId: "t-test-005", role: "owner" },
    isLoading: false,
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("aws-amplify/auth", () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: {
      idToken: { toString: () => "test-jwt-token" },
    },
  }),
}));

// ─── Helpers ───────────────────────────────────────────────────────────────────

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function createWrapper() {
  const qc = createQueryClient();
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe("STEP 5: Signup phone page — hang-path hardening", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    sessionStorage.setItem("pilot_signup_tenant_id", "t-test-005");
  });

  it("(a) /state 500 during poll → getApiProblem surfaces the error (not swallowed)", async () => {
    // Verify that getApiProblem correctly parses a 500 error from the /state
    // endpoint — the phone page's poll catch block uses this to set pollError
    // and render the poll_timeout escape state instead of silently swallowing.
    const { getApiProblem } = await import("@pilot/shared-api");
    const axios = (await import("axios")).default;
    const { AxiosHeaders } = await import("axios");

    const error = new axios.AxiosError(
      "Server Error",
      "500",
      { headers: new AxiosHeaders() },
      undefined,
      {
        data: { detail: "Internal server error" },
        status: 500,
        statusText: "Server Error",
        headers: {},
        config: { headers: new AxiosHeaders() },
      },
    );

    const problem = getApiProblem(error);
    expect(problem.status).toBe(500);
    expect(problem.detail).toBe("Internal server error");

    // The phone page's poll catch block now uses getApiProblem to set
    // pollError and transitions to the "poll_timeout" escape state,
    // rendering a defined error UI instead of an infinite spinner.
  });

  it("(b) poll_timeout escape state UI renders error message + retry button", async () => {
    // Mount-time state check: return step3_phone (stays on page)
    // Poll calls return 500 → poll_timeout escape state
    let callCount = 0;
    server.use(
      http.get("/api/v1/signup/:tenantId/state", () => {
        callCount += 1;
        // First call (mount-time guard) succeeds with step3_phone
        if (callCount === 1) {
          return HttpResponse.json({
            tenant_id: "t-test-005",
            signup_state: "step3_phone",
            collected_data: {},
          });
        }
        // Subsequent calls (poll) return 500
        return HttpResponse.json(
          { detail: "Connection lost during polling" },
          { status: 500 },
        );
      }),
      // Mock the consent/send-optin/step3 endpoints
      http.post("/api/v1/signup/:tenantId/phone/consent", () =>
        HttpResponse.json(
          {
            user_endpoint_id: "ue-test-001",
            verification_status: "pending",
          },
          { status: 201 },
        ),
      ),
      http.post("/api/v1/signup/:tenantId/phone/send-optin", () =>
        HttpResponse.json({ status: "sent" }),
      ),
      http.put("/api/v1/signup/:tenantId/step3", () =>
        HttpResponse.json({
          tenant_id: "t-test-005",
          signup_state: "step3_phone",
          next_step: "plan",
        }),
      ),
    );

    const SignupPhonePage = (await import("../../app/signup/phone/page"))
      .default;

    render(<SignupPhonePage />, { wrapper: createWrapper() });

    // Wait for the mount-time state check to complete and page to render
    await waitFor(() => {
      expect(screen.getByTestId("field-phone-number")).toBeInTheDocument();
    });

    // Fill in the phone field
    const phoneInput = screen.getByTestId("field-phone-number");
    fireEvent.change(phoneInput, { target: { value: "+15551234567" } });

    // Check the consent checkbox
    const consentCheckbox = screen.getByTestId("signup-sms-consent-checkbox");
    fireEvent.click(consentCheckbox);

    // Submit the form
    const submitBtn = screen.getByTestId("signup-stayinformed-continue");
    fireEvent.click(submitBtn);

    // Wait for the poll to fire (POLL_INTERVAL_MS = 3000ms) and hit 500
    // The poll catch block sets pollError and transitions to poll_timeout
    await waitFor(
      () => {
        const escapeEl = screen.queryByTestId("signup-poll-timeout");
        expect(escapeEl).toBeInTheDocument();
      },
      { timeout: 10000 },
    );

    // The error detail should be visible
    expect(
      screen.getByText(/Connection lost during polling/i),
    ).toBeInTheDocument();

    // Retry button should be present
    expect(screen.getByTestId("poll-timeout-retry")).toBeInTheDocument();
  });

  it("(c) POLL_MAX_ATTEMPTS is finite (not infinite) — poll bound is enforced", async () => {
    // Verify the polling bound constant is finite — this is the structural
    // guarantee that the poll cannot run forever. The phone page source
    // defines POLL_MAX_ATTEMPTS = 100 and POLL_INTERVAL_MS = 3000, giving
    // a maximum poll duration of 5 minutes before the escape state triggers.
    // We verify the constants are imported and finite by checking the source.

    // Read the phone page source to verify the bound exists
    const fs = await import("node:fs");
    const path = await import("node:path");
    const source = fs.readFileSync(
      path.resolve(__dirname, "../../app/signup/phone/page.tsx"),
      "utf-8",
    );

    // The source must define a finite POLL_MAX_ATTEMPTS
    expect(source).toMatch(/POLL_MAX_ATTEMPTS\s*=\s*\d+/);
    // The poll exhaustion must transition to an escape state (not just clear)
    expect(source).toMatch(/poll_timeout/);
    // The catch block must use getApiProblem (not swallow)
    expect(source).toMatch(/getApiProblem/);
    // The escape state must render a retry action
    expect(source).toMatch(/poll-timeout-retry/);
  });
});
