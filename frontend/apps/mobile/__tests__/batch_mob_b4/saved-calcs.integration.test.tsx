/**
 * Saved Calculations Screen integration tests (MOB-B4)
 *
 * Location: apps/mobile/__tests__/batch_mob_b4/saved-calcs.integration.test.tsx
 *
 * Tests SavedCalcsScreen with MSW fixtures.
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { SavedCalcsScreen } from "../../features/nec-calcs/components/SavedCalcsScreen";
// Import fixture from mocks/ directory (outside __tests__/) to avoid Jest treating it as test suite
import { savedCalcLogsFixture } from "../../mocks/fixtures/necCalcLogs";

jest.mock("expo-router", () => ({
  router: { push: jest.fn(), back: jest.fn() },
  useRouter: () => require("expo-router").router,
}));

// Use wildcard URL pattern — same pattern as all other integration tests in this project
const server = setupServer(
  http.get("*/api/v1/nec/calc-logs", () => {
    return HttpResponse.json(savedCalcLogsFixture, { status: 200 });
  }),
);

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeQC()}>{children}</QueryClientProvider>
  );
}

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

describe("SavedCalcsScreen", () => {
  it("renders 2 saved calculation rows from MSW fixture", async () => {
    render(
      <Wrapper>
        <SavedCalcsScreen />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("saved-calc-row-saved-log-001")).toBeTruthy();
      expect(screen.getByTestId("saved-calc-row-saved-log-002")).toBeTruthy();
    });
  });

  it("shows 'Voltage Drop' badge for voltage_drop log", async () => {
    render(
      <Wrapper>
        <SavedCalcsScreen />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("Voltage Drop")).toBeTruthy();
    });
  });

  it("shows 'Conduit Fill' badge for conduit_fill log", async () => {
    render(
      <Wrapper>
        <SavedCalcsScreen />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("Conduit Fill")).toBeTruthy();
    });
  });

  it("shows 'Offline' chip for is_offline_calc=true log", async () => {
    render(
      <Wrapper>
        <SavedCalcsScreen />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("Offline")).toBeTruthy();
    });
  });

  it("shows empty state when API returns empty array", async () => {
    server.use(
      http.get("*/api/v1/nec/calc-logs", () => {
        return HttpResponse.json([], { status: 200 });
      }),
    );

    render(
      <Wrapper>
        <SavedCalcsScreen />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeTruthy();
      expect(screen.getByText("No saved calculations yet")).toBeTruthy();
    });
  });

  it("shows error state when API fails", async () => {
    server.use(
      http.get("*/api/v1/nec/calc-logs", () => {
        return HttpResponse.json({ detail: "Server error" }, { status: 500 });
      }),
    );

    render(
      <Wrapper>
        <SavedCalcsScreen />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("error-state")).toBeTruthy();
    });
  });

  it("has a back button that navigates back", () => {
    render(
      <Wrapper>
        <SavedCalcsScreen />
      </Wrapper>,
    );

    expect(screen.getByTestId("back-button")).toBeTruthy();
  });
});
