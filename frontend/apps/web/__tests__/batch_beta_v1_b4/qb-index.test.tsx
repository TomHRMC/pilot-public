/**
 * QB Integration Index Page Integration Tests — BETA-B4
 *
 * Location: apps/web/__tests__/batch_beta_v1_b4/qb-index.test.tsx
 * Route: /settings/integrations/quickbooks
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
import { QbIntegrationIndexPage } from "../../src/features/settings/components/QbIntegrationIndexPage";

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

describe("QbIntegrationIndexPage (/settings/integrations/quickbooks)", () => {
  it("renders without crashing (not 404)", () => {
    const { container } = render(<QbIntegrationIndexPage />, {
      wrapper: makeWrapper(),
    });
    expect(container).toBeDefined();
  });

  it("shows QuickBooks Integration heading", async () => {
    render(<QbIntegrationIndexPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("QuickBooks Integration")).toBeDefined();
    });
  });

  it("shows connected state with company name from MSW fixture", async () => {
    render(<QbIntegrationIndexPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText(/Acme Electric LLC/i)).toBeDefined();
    });
  });

  it("shows disconnect button when connected", async () => {
    render(<QbIntegrationIndexPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Disconnect")).toBeDefined();
    });
  });

  it("shows links to auto-expiry and conflicts sub-pages", async () => {
    render(<QbIntegrationIndexPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Auto-expiry & sync settings")).toBeDefined();
      expect(screen.getByText("View conflicts")).toBeDefined();
    });
  });
});
