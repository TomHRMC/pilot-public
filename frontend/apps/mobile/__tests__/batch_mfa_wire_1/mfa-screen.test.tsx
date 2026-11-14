/**
 * MFA host screen tests — MFA-WIRE-1 Part C
 *
 * Location: apps/mobile/__tests__/batch_mfa_wire_1/mfa-screen.test.tsx
 *
 * Verifies the four data states (loading skeleton, error retry, empty, populated),
 * SMS disclosure preservation, and wizard allowedPaths pass-through.
 *
 * Uses Jest (jest-expo) + @testing-library/react-native.
 * Mobile assertions: .toBeTruthy(), NOT toBeInTheDocument().
 */
// Set API base URL so the wizard's raw fetch uses an absolute URL (MSW wildcard match)
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

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/users/me/mfa-status", () =>
    HttpResponse.json({
      enrolled_methods: [],
      tenant_policy_required: false,
      grace_period_active: false,
      grace_ends_at: null,
      enforcement_activated: false,
    }),
  ),
  // enroll-start/confirm/recovery-codes handlers (for wizard interaction)
  http.post("*/api/v1/users/me/mfa/methods/totp/enroll-start", () =>
    HttpResponse.json({
      method_type: "totp",
      qr_code_uri: "otpauth://totp/Pilot?secret=JBSWY3DPEHPK3PXP&issuer=Pilot",
      secret: "JBSWY3DPEHPK3PXP",
    }),
  ),
  http.post("*/api/v1/users/me/mfa/methods/sms/enroll-start", () =>
    HttpResponse.json({
      method_type: "sms",
      destination_masked: "•••0001",
    }),
  ),
  http.post(
    "*/api/v1/users/me/mfa/methods/:methodType/enroll-confirm",
    async ({ request, params }) => {
      const body = (await request.json()) as { code?: string };
      const methodType = params.methodType as string;
      if (body.code === "000000") {
        return HttpResponse.json(
          { code: "mfa_code_invalid", detail: "Mismatch" },
          { status: 400 },
        );
      }
      return HttpResponse.json(
        { method_id: `${methodType}-001`, enrolled_at: "2026-08-17T12:00:00Z" },
        { status: 201 },
      );
    },
  ),
  http.post("*/api/v1/users/me/mfa/recovery-codes/generate", () =>
    HttpResponse.json(
      { codes: ["ABCD-1234", "EFGH-5678"], set_id: "rc-001" },
      { status: 201 },
    ),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
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

describe("MFA host screen (MFA-WIRE-1 Part C)", () => {
  it("renders skeleton rows on loading state", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId("mfa-status-skeleton")).toBeTruthy();
    });
  });

  it("renders error text + retry button on error state", async () => {
    server.use(
      http.get("*/api/v1/users/me/mfa-status", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );

    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId("mfa-status-retry")).toBeTruthy();
    });

    expect(screen.getByText(/Could not load MFA status/i)).toBeTruthy();
  });

  it("renders empty state when no methods enrolled", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId("no-methods-text")).toBeTruthy();
    });

    expect(screen.getByText("No methods enrolled.")).toBeTruthy();
  });

  it("renders populated state with enrolled methods", async () => {
    server.use(
      http.get("*/api/v1/users/me/mfa-status", () =>
        HttpResponse.json({
          enrolled_methods: ["totp"],
          tenant_policy_required: false,
          grace_period_active: false,
          grace_ends_at: null,
          enforcement_activated: false,
        }),
      ),
    );

    render(<MfaScreen />, { wrapper: createWrapper() });

    // The enrolled-methods Text node is composite: ["•", " ", "Authenticator app (TOTP)"].
    // getByText with an exact string does not match composite children — use a regex.
    await waitFor(() => {
      expect(screen.getByText(/Authenticator app \(TOTP\)/)).toBeTruthy();
    });
  });

  it("SMS disclosure is always rendered (10DLC compliance)", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId("sms-disclosure")).toBeTruthy();
    });

    expect(screen.getByText(/SMS verification/i)).toBeTruthy();
    expect(screen.getByTestId("sms-privacy-policy-link")).toBeTruthy();
  });

  it("Add button renders in empty state", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId("add-mfa-method-btn")).toBeTruthy();
    });
  });

  it("wizard receives allowedPaths when Add button is pressed", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId("add-mfa-method-btn")).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId("add-mfa-method-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("mfa-wizard-container")).toBeTruthy();
    });

    // Wizard renders with totp + sms options (allowedPaths filter)
    // The chooser step shows both options immediately
    await waitFor(() => {
      expect(screen.getByTestId("mfa-path-totp")).toBeTruthy();
      expect(screen.getByTestId("mfa-path-sms")).toBeTruthy();
    });
  });
});
