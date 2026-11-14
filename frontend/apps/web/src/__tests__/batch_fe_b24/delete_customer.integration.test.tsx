/**
 * FE-B24 — Delete Customer Modal Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b24/delete_customer.integration.test.tsx
 *
 * Tests:
 * 1. Delete confirm button renders for owner (RoleGate)
 * 2. Delete confirm button NOT visible for tech
 * 3. Clicking cancel calls onClose
 * 4. Confirming fires DELETE /api/v1/customers/{id}
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
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
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { handlers } from "../../mocks/handlers";
import { DeleteCustomerModal } from "@/features/customers/components/DeleteCustomerModal";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/customers/c-1",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: "c-1" }),
}));

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function makeAuth(role: "owner" | "technician"): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: "user@test.com",
      role,
      tenantId: "t-1",
      displayName: "Test User",
      accessToken: "mock-token",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

const CUSTOMER_ID = "c-00000001-0000-0000-0000-000000000001";
const CUSTOMER_NAME = "Smith Electric LLC";

function renderModal(
  role: "owner" | "technician",
  open = true,
  onClose = vi.fn(),
  onSuccess = vi.fn(),
) {
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <DeleteCustomerModal
            customerId={CUSTOMER_ID}
            customerName={CUSTOMER_NAME}
            open={open}
            onClose={onClose}
            onSuccess={onSuccess}
          />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B24 Delete Customer Modal Integration", () => {
  it("1. Delete confirm button renders for owner role", async () => {
    renderModal("owner");
    // Use heading role to disambiguate from button text "Delete Customer"
    expect(
      await screen.findByRole("heading", { name: "Delete Customer" }),
    ).toBeInTheDocument();
    // Confirm button visible for owner via RoleGate
    expect(
      screen.getByTestId("confirm-delete-customer-btn"),
    ).toBeInTheDocument();
    // Confirmation text includes customer name
    expect(
      screen.getByText((content) => content.includes(CUSTOMER_NAME)),
    ).toBeInTheDocument();
  });

  it("2. Confirm delete button NOT visible for tech role (RoleGate)", async () => {
    renderModal("technician");
    // Modal still opens
    expect(
      await screen.findByRole("heading", { name: "Delete Customer" }),
    ).toBeInTheDocument();
    // RoleGate hides the button for tech
    expect(
      screen.queryByTestId("confirm-delete-customer-btn"),
    ).not.toBeInTheDocument();
  });

  it("3. Clicking Cancel calls onClose", async () => {
    const onClose = vi.fn();
    renderModal("owner", true, onClose);
    await screen.findByRole("heading", { name: "Delete Customer" });
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("4. Confirming fires DELETE /api/v1/customers/{id}", async () => {
    let deleteCalled = false;
    server.use(
      http.delete(`/api/v1/customers/${CUSTOMER_ID}`, () => {
        deleteCalled = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    renderModal("owner");
    await screen.findByRole("heading", { name: "Delete Customer" });
    fireEvent.click(screen.getByTestId("confirm-delete-customer-btn"));

    await waitFor(() => {
      expect(deleteCalled).toBe(true);
    });
  });
});
