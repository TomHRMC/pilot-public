/**
 * TenantDlcProfileForm unit tests — DLC-1
 *
 * Location: apps/web/src/features/sms-compliance/components/__tests__/TenantDlcProfileForm.test.tsx
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import React from "react";
import { TenantDlcProfileForm } from "../TenantDlcProfileForm";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";

vi.mock("next/navigation", () => ({ usePathname: () => "/settings" }));

const MOCK_PROFILE = {
  tenant_id: "t-001",
  legal_business_name: "Smith Electrical LLC",
  dba_name: null,
  ein_masked: "**-***1234",
  hq_address_line1: null,
  hq_address_line2: null,
  hq_city: null,
  hq_state: null,
  hq_postal_code: null,
  hq_country: "US",
  support_email: null,
  support_phone: null,
  updated_at: null,
};

const server = setupServer(
  http.get("/api/v1/settings/10dlc-profile", () =>
    HttpResponse.json(MOCK_PROFILE),
  ),
  http.put("/api/v1/settings/10dlc-profile", () =>
    HttpResponse.json({ ...MOCK_PROFILE, legal_business_name: "Updated LLC" }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeAuthValue(role: PilotRole = "owner"): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "owner@example.com",
      role,
      tenantId: "t-001",
      displayName: "Owner",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function createWrapper(role: PilotRole = "owner") {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={makeAuthValue(role)}>
        <QueryClientProvider client={qc}>{children}</QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  Wrapper.displayName = "TestWrapper";
  return Wrapper;
}

describe("TenantDlcProfileForm", () => {
  it("renders without crashing", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId("dlc-profile-form")).toBeTruthy();
    });
  });

  it("pre-populates form with loaded profile data", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => {
      const input = screen.getByTestId(
        "dlc-legal-name-input",
      ) as HTMLInputElement;
      expect(input.value).toBe("Smith Electrical LLC");
    });
  });

  it("shows masked EIN from profile", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText(/\*\*-\*\*\*1234/)).toBeTruthy();
    });
  });

  it("save button is disabled when legal_business_name is empty", async () => {
    server.use(
      http.get("/api/v1/settings/10dlc-profile", () =>
        HttpResponse.json({ ...MOCK_PROFILE, legal_business_name: null }),
      ),
    );
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => {
      const btn = screen.getByTestId("dlc-save-btn") as HTMLButtonElement;
      expect(btn.disabled).toBe(true);
    });
  });

  it("shows success message after successful save", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId("dlc-profile-form"));

    fireEvent.submit(screen.getByTestId("dlc-profile-form"));
    await waitFor(() => {
      expect(screen.getByTestId("dlc-save-success")).toBeTruthy();
    });
  });

  it("shows error message when save fails", async () => {
    server.use(
      http.put("/api/v1/settings/10dlc-profile", () =>
        HttpResponse.json({ error: "server error" }, { status: 500 }),
      ),
    );
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId("dlc-profile-form"));

    fireEvent.submit(screen.getByTestId("dlc-profile-form"));
    await waitFor(() => {
      expect(screen.getByTestId("dlc-save-error")).toBeTruthy();
    });
  });

  it("form is NOT rendered for tech role (settings.manage required)", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper("technician") });
    await waitFor(() => {
      expect(screen.queryByTestId("dlc-profile-form")).toBeNull();
    });
  });
});
