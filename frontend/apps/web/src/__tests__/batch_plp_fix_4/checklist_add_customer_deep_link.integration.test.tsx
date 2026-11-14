/**
 * PLP-FIX-4 Integration: Checklist Add-Customer deep-link
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_4/checklist_add_customer_deep_link.integration.test.tsx
 *
 * Verifies:
 *  1. CustomersPage with ?add=1 opens the create modal
 *  2. Closing the modal calls router.replace("/customers") to clear the param
 *  3. types.ts CHECKLIST_ITEMS has no /customers/new route remaining
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";

// Mock useCustomers hook
vi.mock("../../features/customers/hooks/useCustomers", () => ({
  useCustomers: vi.fn(() => ({
    data: { items: [], total: 0, limit: 20, offset: 0 },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
  CUSTOMERS_QUERY_KEY: () => ["customers"],
}));

// Mock CreateCustomerModal to observe open state
vi.mock("../../features/customers/components/CreateCustomerModal", () => ({
  CreateCustomerModal: ({
    open,
    onClose,
  }: {
    open: boolean;
    onClose: () => void;
  }) =>
    open ? (
      <div data-testid="create-customer-modal">
        <button data-testid="modal-close" onClick={onClose}>
          Close
        </button>
      </div>
    ) : null,
}));

// Mock next/navigation with ?add=1
const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("add=1"),
  useRouter: () => ({ replace, push: vi.fn(), back: vi.fn() }),
}));

import { CustomersPage } from "../../features/customers/components/CustomersPage";
import { CHECKLIST_ITEMS } from "../../features/onboarding/types";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

const authValue: AuthContextValue = {
  user: {
    id: "u-1",
    email: "test@test.com",
    role: "owner",
    tenantId: "t-1",
    displayName: "Test",
    accessToken: "tok",
  },
  isAuthenticated: true,
  role: "owner",
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("tok"),
};

function renderPage() {
  return render(
    <AuthContext.Provider value={authValue}>
      <QueryClientProvider client={makeQueryClient()}>
        <CustomersPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("PLP-FIX-4 — Checklist Add-Customer deep-link", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens create modal when ?add=1 is present", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("create-customer-modal")).toBeInTheDocument();
    });
  });

  it("clears the param via router.replace on modal close", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("create-customer-modal")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("modal-close"));
    expect(replace).toHaveBeenCalledWith("/customers");
  });

  it("CHECKLIST_ITEMS has no /customers/new route remaining", () => {
    const firstCustomerItem = CHECKLIST_ITEMS.find(
      (item) => item.key === "firstCustomerAdded",
    );
    expect(firstCustomerItem).toBeDefined();
    expect(firstCustomerItem!.actionRoute).toBe("/customers?add=1");
    // Grep-guard: no item routes to /customers/new
    const hasOldRoute = CHECKLIST_ITEMS.some(
      (item) => item.actionRoute === "/customers/new",
    );
    expect(hasOldRoute).toBe(false);
  });
});
