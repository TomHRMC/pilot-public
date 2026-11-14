import { render, screen, fireEvent } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { TeamSettingsPage } from "@/features/settings/components/TeamSettingsPage";

vi.mock("next/navigation", () => ({ usePathname: () => "/settings/team" }));

const mockUsers = [
  {
    user_id: "u1",
    email: "tech@example.com",
    role_code: "technician",
    role_name: "Field Technician",
    permissions: [],
    joined_at: null,
    is_active: true,
  },
];

const server = setupServer(
  http.get("/api/v1/users", () => HttpResponse.json(mockUsers)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function makeAuth(): AuthContextValue {
  return {
    user: {
      id: "u-owner",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Owner",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

describe("Team Settings — role code correctness", () => {
  it("role select does NOT have 'tech' or 'operator' as option values", async () => {
    render(
      <AuthContext.Provider value={makeAuth()}>
        <QueryClientProvider client={makeQC()}>
          <TeamSettingsPage />
        </QueryClientProvider>
      </AuthContext.Provider>,
    );
    const select = await screen.findByLabelText(
      /change role for tech@example.com/i,
    );
    const options = Array.from(select.querySelectorAll("option")).map((o) =>
      o.getAttribute("value"),
    );
    expect(options).not.toContain("tech");
    expect(options).not.toContain("operator");
    expect(options).toContain("technician");
    expect(options).toContain("accountant");
  });

  it("selecting Accountant fires POST with role_code: 'accountant'", async () => {
    let capturedBody: unknown = null;
    server.use(
      http.post("/api/v1/users/u1/role", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({
          user_id: "u1",
          tenant_id: "t1",
          role_code: "accountant",
          role_name: "Accountant",
          message: "ok",
        });
      }),
    );
    render(
      <AuthContext.Provider value={makeAuth()}>
        <QueryClientProvider client={makeQC()}>
          <TeamSettingsPage />
        </QueryClientProvider>
      </AuthContext.Provider>,
    );
    const select = await screen.findByLabelText(
      /change role for tech@example.com/i,
    );
    fireEvent.change(select, { target: { value: "accountant" } });
    await vi.waitFor(() => {
      expect(capturedBody).toEqual({ role_code: "accountant" });
    });
  });
});
