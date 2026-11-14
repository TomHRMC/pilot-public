/**
 * My Account screen integration tests (MOB-B10)
 *
 * Endpoint: GET/PATCH /api/v1/users/me/profile
 * Verifies: renders all 5 fields, email read-only, save-on-blur PATCH, "Saved ✓" feedback
 */
import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import MyAccountScreen from "../../app/(tabs)/(home)/settings/my-account";

// ── Expo Router mock ─────────────────────────────────────────────────────────

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

// ── MSW server ───────────────────────────────────────────────────────────────

const MOCK_PROFILE = {
  id: "00000000-0000-0000-0000-000000000001",
  first_name: "Tom",
  last_name: "Owner",
  email: "dev@pilot.local",
  phone_number: "+13035550001",
  time_zone: "America/Denver",
  profile_photo_s3_key: null,
  language_preference: "en",
};

let lastPatchBody: Record<string, unknown> | null = null;

const server = setupServer(
  http.get("*/api/v1/users/me/profile", () => HttpResponse.json(MOCK_PROFILE)),
  http.patch("*/api/v1/users/me/profile", async ({ request }) => {
    lastPatchBody = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...MOCK_PROFILE, ...lastPatchBody });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  lastPatchBody = null;
});
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

describe("MyAccountScreen", () => {
  it("renders with testID='my-account-screen'", async () => {
    render(<MyAccountScreen />, { wrapper: createWrapper() });
    await waitFor(() =>
      expect(screen.getByTestId("my-account-screen")).toBeTruthy(),
    );
  });

  it("renders all 5 field labels: First name, Last name, Email, Phone number, Timezone", async () => {
    render(<MyAccountScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("my-account-screen")).toBeTruthy(),
    );

    expect(screen.getByText("First name")).toBeTruthy();
    expect(screen.getByText("Last name")).toBeTruthy();
    expect(screen.getByText("Email")).toBeTruthy();
    expect(screen.getByText("Phone number")).toBeTruthy();
    expect(screen.getByText("Timezone")).toBeTruthy();
  });

  it("first name input is pre-populated with MSW mock data ('Tom')", async () => {
    render(<MyAccountScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("first-name-input")).toBeTruthy(),
    );

    const input = screen.getByTestId("first-name-input");
    expect(input.props.defaultValue).toBe("Tom");
  });

  it("email field is not editable (editable={false})", async () => {
    render(<MyAccountScreen />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByTestId("email-input")).toBeTruthy());

    const emailInput = screen.getByTestId("email-input");
    expect(emailInput.props.editable).toBe(false);
  });

  it("endEditing on first name input fires PATCH /api/v1/users/me/profile with updated value", async () => {
    render(<MyAccountScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("first-name-input")).toBeTruthy(),
    );

    await act(async () => {
      fireEvent(screen.getByTestId("first-name-input"), "endEditing", {
        nativeEvent: { text: "Thomas" },
      });
    });

    await waitFor(() =>
      expect(lastPatchBody).toEqual({ first_name: "Thomas" }),
    );
  });

  it("'Saved ✓' confirmation text visible after successful PATCH", async () => {
    render(<MyAccountScreen />, { wrapper: createWrapper() });

    await waitFor(() =>
      expect(screen.getByTestId("first-name-input")).toBeTruthy(),
    );

    await act(async () => {
      fireEvent(screen.getByTestId("first-name-input"), "endEditing", {
        nativeEvent: { text: "Thomas" },
      });
    });

    await waitFor(() =>
      expect(screen.getByTestId("first-name-saved")).toBeTruthy(),
    );
    expect(screen.getByText("Saved ✓")).toBeTruthy();
  });
});
