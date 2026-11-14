/**
 * Security Index Integration Tests — BETA-B4
 *
 * Location: apps/web/__tests__/batch_beta_v1_b4/security-index.test.tsx
 * Route: /settings/my-account/security
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
import { SecurityIndexPage } from "../../src/features/account-settings/components/SecurityIndexPage";

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

describe("SecurityIndexPage (/settings/my-account/security)", () => {
  it("renders without crashing (not 404)", () => {
    const { container } = render(<SecurityIndexPage />, {
      wrapper: makeWrapper(),
    });
    expect(container).toBeDefined();
  });

  it("shows Security heading", async () => {
    render(<SecurityIndexPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Security")).toBeDefined();
    });
  });

  it("shows navigation cards for MFA, sessions, password, data export", async () => {
    render(<SecurityIndexPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Multi-Factor Authentication")).toBeDefined();
      expect(screen.getByText("Active Sessions")).toBeDefined();
      expect(screen.getByText("Password")).toBeDefined();
      expect(screen.getByText("Data Export")).toBeDefined();
    });
  });
});
