/**
 * Team Settings Page Integration Tests — BETA-B4
 *
 * Location: apps/web/__tests__/batch_beta_v1_b4/team.test.tsx
 * Route: /settings/team
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
import { TeamSettingsPage } from "../../src/features/settings/components/TeamSettingsPage";

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

describe("TeamSettingsPage (/settings/team)", () => {
  it("renders without crashing (not 404)", () => {
    const { container } = render(<TeamSettingsPage />, {
      wrapper: makeWrapper(),
    });
    expect(container).toBeDefined();
  });

  it("shows Team heading", async () => {
    render(<TeamSettingsPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Team")).toBeDefined();
    });
  });

  it("renders user list from MSW fixture", async () => {
    render(<TeamSettingsPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("owner@example.com")).toBeDefined();
      expect(screen.getByText("tech@example.com")).toBeDefined();
    });
  });

  it("shows invite team member button", async () => {
    render(<TeamSettingsPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Invite team member")).toBeDefined();
    });
  });

  it("shows role change dropdowns for owner (useRequiresPermission mocked true)", async () => {
    render(<TeamSettingsPage />, { wrapper: makeWrapper() });
    await waitFor(() => {
      const selects = screen.getAllByRole("combobox");
      expect(selects.length).toBeGreaterThan(0);
    });
  });
});
