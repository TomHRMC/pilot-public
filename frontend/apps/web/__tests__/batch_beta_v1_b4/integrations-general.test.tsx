/**
 * Integrations General Page Integration Tests — BETA-B4
 *
 * Location: apps/web/__tests__/batch_beta_v1_b4/integrations-general.test.tsx
 * Route: /settings/integrations/general
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { handlers } from "../../src/mocks/handlers";
import { IntegrationsGeneralPage } from "../../src/features/settings/components/IntegrationsGeneralPage";

vi.mock("@pilot/ui/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useRequiresPermission: () => true,
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "user-1", email: "owner@test.com", tenantId: "tenant-1" },
    role: "owner",
    isAuthenticated: true,
    signIn: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn(),
  }),
}));

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("IntegrationsGeneralPage (/settings/integrations/general)", () => {
  it("renders without crashing (not 404)", () => {
    const { container } = render(<IntegrationsGeneralPage />, {
      wrapper: makeWrapper(),
    });
    expect(container).toBeDefined();
  });

  it("shows Integrations heading", async () => {
    render(<IntegrationsGeneralPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Integrations")).toBeDefined();
    });
  });

  it("shows QuickBooks integration card (connected from MSW)", async () => {
    render(<IntegrationsGeneralPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("QuickBooks")).toBeDefined();
    });
  });

  it("shows Calendar integration card", async () => {
    render(<IntegrationsGeneralPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Calendar")).toBeDefined();
    });
  });

  it("shows SMS integration card", async () => {
    render(<IntegrationsGeneralPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("SMS")).toBeDefined();
    });
  });
});
