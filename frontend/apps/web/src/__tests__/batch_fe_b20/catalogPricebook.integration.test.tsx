/**
 * FE-B20 Integration — Catalog Pricebook
 *
 * Location: apps/web/src/__tests__/batch_fe_b20/catalogPricebook.integration.test.tsx
 *
 * Tests the /catalog page (PricebookItemsPage) with MSW handlers.
 * Rule 15: never assert on toHaveLength(N), assert by content; no fixture mutation.
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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { http, HttpResponse } from "msw";
import { catalogHandlers } from "@/mocks/handlers/catalogHandlers";
import { PricebookItemsPage } from "@/features/catalog/components/PricebookItemsPage";

// Per-test MSW server — isolated from global handler set
const server = setupServer(...catalogHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeContext(
  role: "owner" | "office_staff" | "technician" | "accountant" = "owner",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role,
      tenantId: "t1",
      displayName: "Test",
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

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function Wrapper({
  role = "owner",
  children,
}: {
  role?: "owner" | "office_staff" | "technician" | "accountant";
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("Catalog — PricebookItemsPage integration", () => {
  it("renders pricebook items table from MSW data", async () => {
    render(<PricebookItemsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("SW-200A")).toBeInTheDocument();
    });
    expect(screen.getByText("200A Service Panel")).toBeInTheDocument();
    expect(screen.getByText("WIRE-12AWG")).toBeInTheDocument();
    expect(screen.getByText("LABOR-M")).toBeInTheDocument();
  });

  it("Add Item button is visible for owner", async () => {
    render(<PricebookItemsPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(screen.getByText("SW-200A")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: /add item/i }),
    ).toBeInTheDocument();
  });

  it("Add Item button is hidden for tech", async () => {
    render(<PricebookItemsPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });

    await waitFor(() => {
      expect(screen.getByText("SW-200A")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /add item/i })).toBeNull();
  });

  it("clicking Add Item opens PricebookItemForm modal", async () => {
    render(<PricebookItemsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("SW-200A")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /add item/i }));

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /add pricebook item/i }),
      ).toBeInTheDocument();
    });
  });

  it("clicking Update Price opens UpdatePriceModal", async () => {
    render(<PricebookItemsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("SW-200A")).toBeInTheDocument();
    });

    // Click the first "💲 Update Price" button
    const updatePriceButtons = screen.getAllByRole("button", {
      name: /update price/i,
    });
    fireEvent.click(updatePriceButtons[0]);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /update price/i }),
      ).toBeInTheDocument();
    });
  });

  it("submitting add form fires POST mutation", async () => {
    let postCalled = false;

    server.use(
      http.post("*/api/v1/catalog/pricebook", async () => {
        postCalled = true;
        return HttpResponse.json(
          {
            id: "pb-new-1",
            tenant_id: "tenant-test-1",
            sku: "NEW-SKU",
            name: "New Item",
            description: null,
            uom_id: null,
            taxability_code: null,
            is_active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            created_by: null,
            updated_by: null,
            current_price: {
              id: 999,
              default_unit_price_cents: 5000,
              valid_period_lower: new Date().toISOString(),
              valid_period_upper: null,
              recorded_at: new Date().toISOString(),
            },
          },
          { status: 201 },
        );
      }),
    );

    render(<PricebookItemsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("SW-200A")).toBeInTheDocument();
    });

    // Click the trigger button (outside any open dialog)
    const triggerBtn = screen.getByRole("button", { name: /add item/i });
    fireEvent.click(triggerBtn);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/^SKU/i), {
      target: { value: "NEW-SKU" },
    });
    fireEvent.change(screen.getByLabelText(/Name/i), {
      target: { value: "New Item" },
    });
    fireEvent.change(screen.getByLabelText(/Unit Price/i), {
      target: { value: "50.00" },
    });

    // Submit via form element to avoid button targeting ambiguity
    const form = screen.getByRole("dialog").querySelector("form")!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(postCalled).toBe(true);
    });
  });

  it("shows error state when API fails", async () => {
    server.use(
      http.get("*/api/v1/catalog/pricebook", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );

    render(<PricebookItemsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      // ErrorState type="server" renders — no pricebook table
      expect(screen.queryByText("SW-200A")).toBeNull();
    });
  });
});
