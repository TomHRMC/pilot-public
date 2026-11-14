/**
 * Security index screen integration tests (MOB-B10)
 *
 * Verifies: MFA nav card, Password card, method count, navigation push
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
import SecurityIndexScreen from "../../app/(tabs)/(home)/settings/my-account/security";

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

describe("SecurityIndexScreen", () => {
  it("renders with testID='security-index-screen'", async () => {
    render(<SecurityIndexScreen />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("security-index-screen")).toBeTruthy(),
    );
  });

  it("'Two-Factor Authentication' text is visible", async () => {
    render(<SecurityIndexScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("security-index-screen")).toBeTruthy(),
    );

    expect(screen.getByText("Two-Factor Authentication")).toBeTruthy();
  });

  it("MFA card shows '0 methods enrolled' when MSW returns empty array", async () => {
    render(<SecurityIndexScreen />, { wrapper: createWrapper() });

    // Wait until the async MFA status query resolves and description updates from "Loading…"
    await waitFor(() =>
      expect(screen.getByText("No methods enrolled — tap to add")).toBeTruthy(),
    );
  });

  it("'Password' card and 'Manage on the web app' subtitle are visible", async () => {
    render(<SecurityIndexScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("security-index-screen")).toBeTruthy(),
    );

    expect(screen.getByText("Password")).toBeTruthy();
    expect(screen.getByText("Manage on the web app")).toBeTruthy();
  });

  it("pressing MFA card calls router.push with security/mfa path", async () => {
    render(<SecurityIndexScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("mfa-nav-card")).toBeTruthy(),
    );

    fireEvent.press(screen.getByTestId("mfa-nav-card"));

    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("security/mfa"),
    );
  });
});
