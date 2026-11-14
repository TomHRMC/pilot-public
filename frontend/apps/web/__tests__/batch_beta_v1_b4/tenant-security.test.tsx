/**
 * Tenant Security Page Integration Tests — BETA-B4
 *
 * Location: apps/web/__tests__/batch_beta_v1_b4/tenant-security.test.tsx
 * Route: /settings/security
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
import { TenantSecurityPage } from "../../src/features/settings/components/TenantSecurityPage";

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

describe("TenantSecurityPage (/settings/security)", () => {
  it("renders without crashing (not 404)", () => {
    const { container } = render(<TenantSecurityPage />, {
      wrapper: makeWrapper(),
    });
    expect(container).toBeDefined();
  });

  it("shows Security & MFA heading", async () => {
    render(<TenantSecurityPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Security & MFA")).toBeDefined();
    });
  });

  it("shows MFA required toggle", async () => {
    render(<TenantSecurityPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Require MFA for all users")).toBeDefined();
    });
  });

  it("toggle has correct initial state from MSW (false)", async () => {
    render(<TenantSecurityPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      const toggle = screen.getByRole("switch", {
        name: "Require MFA for all users",
      });
      expect(toggle.getAttribute("aria-checked")).toBe("false");
    });
  });
});
