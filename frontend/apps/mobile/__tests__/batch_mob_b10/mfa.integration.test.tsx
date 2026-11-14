/**
 * MFA enrollment screen integration tests (MOB-B10)
 *
 * Verifies: enrolled methods display, empty state, wizard toggle, 10DLC SMS disclosure
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
import MfaScreen from "../../app/(tabs)/(home)/settings/my-account/security/mfa";

// ── Expo Router mock ──────────────────────────────────────────────────────────

const mockPush = jest.fn();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush, back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: mockPush, back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
}));
beforeEach(() => mockPush.mockClear());

// ── WatermelonDB mock ─────────────────────────────────────────────────────────

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

// ── MFAEnrollmentWizard mock ──────────────────────────────────────────────────
// Mock @pilot/ui to avoid loading the full wizard in test environment

jest.mock("@pilot/ui", () => {
  const React = require("react");
  const { View, Text } = require("react-native");
  return {
    MFAEnrollmentWizard: ({
      testID,
      onComplete,
      onCancel,
    }: {
      testID?: string;
      onComplete?: () => void;
      onCancel?: () => void;
    }) =>
      React.createElement(
        View,
        { testID: testID ?? "mfa-enrollment-wizard" },
        React.createElement(Text, null, "MFAEnrollmentWizard"),
      ),
  };
});

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
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Query wrapper ─────────────────────────────────────────────────────────────

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("MfaScreen", () => {
  it("renders with testID='mfa-screen'", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByTestId("mfa-screen")).toBeTruthy());
  });

  it("shows 'No methods enrolled.' when MSW returns empty enrolled_methods", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("no-methods-text")).toBeTruthy(),
    );
    expect(screen.getByText("No methods enrolled.")).toBeTruthy();
  });

  it("shows 'Authenticator app (TOTP)' when MSW returns ['totp']", async () => {
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

    await waitFor(() =>
      expect(screen.getByText("• Authenticator app (TOTP)")).toBeTruthy(),
    );
  });

  it("'Add authentication method' button is visible", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("add-mfa-method-btn")).toBeTruthy(),
    );
    expect(screen.getByText("Add authentication method")).toBeTruthy();
  });

  it("pressing 'Add authentication method' shows mfa-wizard-container", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("add-mfa-method-btn")).toBeTruthy(),
    );

    fireEvent.press(screen.getByTestId("add-mfa-method-btn"));

    expect(screen.getByTestId("mfa-wizard-container")).toBeTruthy();
  });

  it("SMS disclosure testID='sms-disclosure' is always visible (before pressing add button)", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByTestId("mfa-screen")).toBeTruthy());

    expect(screen.getByTestId("sms-disclosure")).toBeTruthy();
  });

  it("'Message and data rates may apply' text is visible in SMS disclosure", async () => {
    render(<MfaScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("sms-disclosure")).toBeTruthy(),
    );

    expect(screen.getByText(/Message and data rates may apply/)).toBeTruthy();
  });
});
