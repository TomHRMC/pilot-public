/**
 * DLC-1 integration tests — 10DLC profile settings surface
 *
 * Location: apps/web/src/__tests__/batch_dlc_1/dlc-profile.integration.test.tsx
 *
 * Rule 14: QueryClient with retry:false in every test.
 * Rule 15: per-test MSW overrides; server.resetHandlers() in afterEach.
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
import { TenantDlcProfileForm } from "@/features/sms-compliance/components/TenantDlcProfileForm";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/communications/sms-compliance",
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
}));

const MOCK_DLC_PROFILE = {
  tenant_id: "t-test-001",
  legal_business_name: "Smith Electrical LLC",
  dba_name: null,
  ein_masked: "**-***1234",
  hq_address_line1: "123 Main Street",
  hq_address_line2: null,
  hq_city: "Denver",
  hq_state: "CO",
  hq_postal_code: "80202",
  hq_country: "US",
  support_email: "support@smithelectrical.example.com",
  support_phone: "+13035550000",
  updated_at: "2026-07-05T18:00:00Z",
};

const server = setupServer(
  http.get("/api/v1/settings/10dlc-profile", () =>
    HttpResponse.json(MOCK_DLC_PROFILE),
  ),
  http.put("/api/v1/settings/10dlc-profile", async ({ request }) => {
    const body = (await request.json()) as typeof MOCK_DLC_PROFILE;
    return HttpResponse.json({ ...MOCK_DLC_PROFILE, ...body });
  }),
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
      tenantId: "t-test-001",
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

function renderWithProviders(role: PilotRole = "owner") {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <AuthContext.Provider value={makeAuthValue(role)}>
      <QueryClientProvider client={qc}>
        <TenantDlcProfileForm />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("DLC-1 Integration — 10DLC Profile Settings", () => {
  it("1. Settings surface renders TenantDlcProfileForm without crashing", async () => {
    renderWithProviders("owner");
    // LoadingState renders first, then form after data loads
    await waitFor(() => {
      expect(screen.getByTestId("dlc-profile-form")).toBeTruthy();
    });
  });

  it("2. RBAC: owner sees the 10DLC form", async () => {
    renderWithProviders("owner");
    await waitFor(() => {
      expect(screen.getByTestId("dlc-profile-form")).toBeTruthy();
    });
  });

  it("2. RBAC: tech role does NOT see the 10DLC form (settings.manage required)", async () => {
    renderWithProviders("technician");
    // Wait for data to load — form still won't appear due to RoleGate
    await waitFor(() => {
      // The heading renders (outside RoleGate), but not the form
      expect(screen.queryByTestId("dlc-profile-form")).toBeNull();
    });
  });

  it("3. Form pre-populates from MSW mock data", async () => {
    renderWithProviders("owner");
    await waitFor(() => {
      const legalNameInput = screen.getByTestId(
        "dlc-legal-name-input",
      ) as HTMLInputElement;
      expect(legalNameInput.value).toBe("Smith Electrical LLC");
    });
    const cityInput = screen.getByTestId("dlc-city-input") as HTMLInputElement;
    expect(cityInput.value).toBe("Denver");
    const stateInput = screen.getByTestId(
      "dlc-state-input",
    ) as HTMLInputElement;
    expect(stateInput.value).toBe("CO");
  });

  it("4. Successful PUT fires the correct endpoint and shows success", async () => {
    renderWithProviders("owner");
    await waitFor(() => screen.getByTestId("dlc-profile-form"));

    // Submit the form with existing data
    fireEvent.submit(screen.getByTestId("dlc-profile-form"));

    await waitFor(() => {
      expect(screen.getByTestId("dlc-save-success")).toBeTruthy();
    });
  });
});
