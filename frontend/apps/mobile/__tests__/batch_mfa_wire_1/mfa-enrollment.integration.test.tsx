/**
 * MFA Enrollment Integration Test — MFA-WIRE-1 Part C
 *
 * Location: apps/mobile/__tests__/batch_mfa_wire_1/mfa-enrollment.integration.test.tsx
 *
 * Full TOTP enrollment walk through the host screen:
 *   chooser → setup → verify → complete
 * Asserts the enroll-confirm request body contains the 6-digit code,
 * and onComplete behavior via the host screen's refetch.
 *
 * Uses Jest (jest-expo) + @testing-library/react-native.
 *
 * MSW (setupServer from msw/node) intercepts BOTH:
 *   - the host screen's apiClient (Axios — uses Node http, which MSW patches)
 *   - the wizard's raw fetch (X-Cognito-Access-Token header — design §G-Q7)
 * Per Rule 15 + the batch Test Requirements: never mock the API layer directly.
 * Mobile handlers use the star-slash-api-v1 wildcard prefix (Rule 18) because
 * the mobile apiClient.baseURL is an absolute LAN URL.
 */
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

// ── Import the screen AFTER mocks ─────────────────────────────────────────────

import MfaScreen from "../../app/(tabs)/(home)/settings/my-account/security/mfa";

// Set API base URL so the wizard's raw fetch uses an absolute URL (MSW wildcard match)
process.env.EXPO_PUBLIC_API_URL = "http://localhost:8000";

// ── Expo Router mock (Rule 16b) ───────────────────────────────────────────────

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: jest.fn(), back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
}));

// ── WatermelonDB mock (Rule 16b) ──────────────────────────────────────────────

jest.mock("../../database", () => ({
  database: {
    write: jest.fn((fn: () => unknown) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn: (r: Record<string, unknown>) => void) => {
        const record = { id: "mock-id", localSyncStatus: "pending" };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));

// ── Mock aws-amplify/auth (wizard dynamic import) ────────────────────────────

jest.mock("aws-amplify/auth", () => ({
  fetchAuthSession: jest.fn().mockResolvedValue({
    tokens: {
      accessToken: { toString: () => "mock-access-token" },
      idToken: { toString: () => "mock-id-token" },
    },
  }),
}));

// ── Request capture (module-level — reset per test) ───────────────────────────

let confirmRequestBody: { code?: string } | null = null;
let mfaStatusRequests = 0;

// ── MSW server (Rule 18: star-slash wildcard prefix for mobile) ─────────────

const server = setupServer(
  // mfa-status — empty (first enrollment)
  http.get("*/api/v1/users/me/mfa-status", () => {
    mfaStatusRequests++;
    return HttpResponse.json({
      enrolled_methods: [],
      tenant_policy_required: false,
      grace_period_active: false,
      grace_ends_at: null,
      enforcement_activated: false,
    });
  }),

  // enroll-start — TOTP
  http.post("*/api/v1/users/me/mfa/methods/totp/enroll-start", () =>
    HttpResponse.json({
      method_type: "totp",
      qr_code_uri:
        "otpauth://totp/PilotForTrades:dev@pilot.local?secret=JBSWY3DPEHPK3PXP&issuer=PilotForTrades",
      secret: "JBSWY3DPEHPK3PXP",
    }),
  ),

  // enroll-start — SMS
  http.post("*/api/v1/users/me/mfa/methods/sms/enroll-start", () =>
    HttpResponse.json({
      method_type: "sms",
      destination_masked: "•••0001",
    }),
  ),

  // enroll-confirm — captures the request body; 000000 → 400 mfa_code_invalid
  http.post(
    "*/api/v1/users/me/mfa/methods/:methodType/enroll-confirm",
    async ({ request }) => {
      const body = (await request.json()) as { code?: string };
      confirmRequestBody = body;

      if (body.code === "000000") {
        return HttpResponse.json(
          { code: "mfa_code_invalid", detail: "That code didn't match." },
          { status: 400 },
        );
      }

      return HttpResponse.json(
        {
          method_id: "totp-method-0001",
          enrolled_at: "2026-08-17T12:00:00Z",
        },
        { status: 201 },
      );
    },
  ),

  // recovery-codes/generate
  http.post("*/api/v1/users/me/mfa/recovery-codes/generate", () =>
    HttpResponse.json(
      {
        codes: ["ABCD-1234", "EFGH-5678", "IJKL-9012", "MNOP-3456"],
        set_id: "rc-set-0001",
      },
      { status: 201 },
    ),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
beforeEach(() => {
  confirmRequestBody = null;
  mfaStatusRequests = 0;
});
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Query wrapper (Rule 14: retry: false) ─────────────────────────────────────

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("MFA Enrollment Integration (MFA-WIRE-1 Part C)", () => {
  it("full TOTP enrollment: chooser → setup → verify → complete", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    // Wait for the host screen to load (empty state)
    await waitFor(() => {
      expect(screen.getByTestId("add-mfa-method-btn")).toBeTruthy();
    });

    // Press Add → wizard appears
    fireEvent.press(screen.getByTestId("add-mfa-method-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("mfa-wizard-container")).toBeTruthy();
    });

    // Step 1: Chooser — select TOTP
    expect(screen.getByTestId("mfa-path-totp")).toBeTruthy();
    fireEvent.press(screen.getByTestId("mfa-path-totp"));

    // Step 2: Setup — wait for the secret to actually load (not "Loading…")
    await waitFor(() => {
      const secret = screen.getByTestId("totp-secret");
      expect(secret.props.children).toContain("JBSW");
    });

    // Continue → verify
    fireEvent.press(screen.getByTestId("mfa-wizard-next"));

    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-input")).toBeTruthy();
    });

    // Step 3: Verify — enter 6-digit code
    fireEvent.changeText(screen.getByTestId("mfa-code-input"), "123456");

    // Press Verify
    fireEvent.press(screen.getByTestId("mfa-wizard-next"));

    // Assert the enroll-confirm request body contains the 6-digit code
    await waitFor(() => {
      expect(confirmRequestBody).not.toBeNull();
    });
    expect(confirmRequestBody!.code).toBe("123456");

    // Step 4: Complete — recovery codes shown (first enrollment)
    await waitFor(() => {
      expect(screen.getByTestId("recovery-codes-container")).toBeTruthy();
    });

    // Finish is disabled until acknowledgment.
    // React Native's Pressable consumes `disabled` internally and does not
    // forward it to the host View props — assert via accessibilityState.disabled
    // (WCAG 4.1.2: the disabled state must be exposed to assistive technology).
    const finishBtn = screen.getByTestId("mfa-wizard-finish");
    expect(finishBtn.props.accessibilityState?.disabled).toBe(true);

    // Acknowledge
    fireEvent.press(screen.getByTestId("recovery-codes-ack"));

    // Finish
    await waitFor(() => {
      expect(
        screen.getByTestId("mfa-wizard-finish").props.accessibilityState
          ?.disabled,
      ).toBe(false);
    });

    fireEvent.press(screen.getByTestId("mfa-wizard-finish"));

    // After finish, the wizard closes and the host screen refetches mfa-status
    await waitFor(() => {
      expect(mfaStatusRequests).toBeGreaterThan(1);
    });
  }, 30000);

  it("wrong code shows inline error and stays on verify step", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId("add-mfa-method-btn")).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId("add-mfa-method-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("mfa-wizard-container")).toBeTruthy();
    });

    // Select TOTP
    fireEvent.press(screen.getByTestId("mfa-path-totp"));

    // Wait for the secret to actually load
    await waitFor(() => {
      const secret = screen.getByTestId("totp-secret");
      expect(secret.props.children).toContain("JBSW");
    });

    // Continue → verify
    fireEvent.press(screen.getByTestId("mfa-wizard-next"));

    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-input")).toBeTruthy();
    });

    // Enter wrong code
    fireEvent.changeText(screen.getByTestId("mfa-code-input"), "000000");
    fireEvent.press(screen.getByTestId("mfa-wizard-next"));

    // Inline error appears
    await waitFor(() => {
      expect(screen.getByTestId("mfa-code-error")).toBeTruthy();
    });

    expect(screen.getByTestId("mfa-code-error").props.children).toContain(
      "That code didn't match",
    );

    // Still on verify step (code input still visible)
    expect(screen.getByTestId("mfa-code-input")).toBeTruthy();
  }, 30000);
});
