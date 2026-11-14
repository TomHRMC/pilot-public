/**
 * PLP-FIX-2 Integration — Invoice Custom Lines Persist (FE-B29-1)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_2/invoice_custom_lines_persist.integration.test.tsx
 *
 * FE-B29-1 integration: invoice builder — add a custom line ("Electrical part",
 * $5.00), Save Draft → POST /api/v1/invoices/ body includes
 * line_items: [{ description: "Electrical part", quantity: 1, unit_price_cents: 500 }]
 * and no qco_line_type_code (backend defaults 'misc' by code).
 *
 * Approach: mocks useCreateInvoice to capture the payload directly, avoiding
 * the fragile combobox + custom-line-form UI interaction in jsdom (the page
 * renders 4 instances of the form due to responsive layouts).
 */

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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotUser } from "@pilot/ui/auth";
import { InvoiceBuilderPage } from "@/features/invoices/components/InvoiceBuilderPage";

// ── Navigation mock ──────────────────────────────────────────────────────────

const mockPush = vi.fn();
const mockBack = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack }),
  usePathname: () => "/invoices/new",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

// ── Mock useCreateInvoice to capture the payload ──────────────────────────────

let capturedPayload: Record<string, unknown> | null = null;

vi.mock("@/features/invoices/hooks/useCreateInvoice", () => ({
  useCreateInvoice: ({
    onSuccess,
  }: {
    onSuccess?: (invoice: unknown) => void;
  }) => ({
    mutate: (payload: Record<string, unknown>) => {
      capturedPayload = payload;
      // Simulate success — call onSuccess with a mock invoice
      onSuccess?.({ id: "inv-new-001", invoice_number: "INV-001" });
    },
    isPending: false,
  }),
}));

// ── MSW ───────────────────────────────────────────────────────────────────────

const server = setupServer(
  // GET /api/v1/customers/ — paginated for CustomerCombobox
  http.get("/api/v1/customers/", () =>
    HttpResponse.json({
      items: [
        {
          id: "c-00000001",
          tenant_id: "t-00000001",
          type: "company",
          display_name: "Acme Electric",
          first_name: null,
          last_name: null,
          company_name: "Acme Electric",
          email: null,
          mobile_phone: null,
        },
      ],
      total: 1,
      limit: 200,
      offset: 0,
    }),
  ),
  // GET /api/v1/sites/ — filtered by customer_id for SiteCombobox
  http.get("/api/v1/sites/", ({ request }) => {
    const url = new URL(request.url);
    if (url.searchParams.get("customer_id") === "c-00000001") {
      return HttpResponse.json([
        {
          id: "s-00000001",
          customer_id: "c-00000001",
          name: "Main Site",
          address: null,
          is_active: true,
        },
      ]);
    }
    return HttpResponse.json([]);
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  capturedPayload = null;
});
afterAll(() => server.close());

// ── Auth helpers ──────────────────────────────────────────────────────────────

function makeAuthValue(): AuthContextValue {
  const user: PilotUser = {
    id: "u-00000001",
    email: "test@pilot.example.com",
    role: "owner",
    tenantId: "t-00000001",
    displayName: "Test User",
    accessToken: "mock-token",
  };
  return {
    user,
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={makeAuthValue()}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  TestWrapper.displayName = "TestWrapper";
  return TestWrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PLP-FIX-2 / FE-B29-1 — Invoice Custom Lines Persist", () => {
  it("Save Draft with a custom line → POST body includes line_items with description, quantity, unit_price_cents and no qco_line_type_code", async () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });

    // Select customer — wait for CustomerCombobox to load
    const customerSearchInput =
      await screen.findByPlaceholderText(/search customers/i);
    fireEvent.change(customerSearchInput, { target: { value: "Acme" } });
    // CustomerCombobox uses onMouseDown on <li role="option">
    const customerOption = await screen.findByRole("option", {
      name: /Acme Electric/i,
    });
    fireEvent.mouseDown(customerOption);

    // Select site — SiteCombobox needs to load sites and then be focused to open
    const siteInput = await screen.findByRole("combobox", { name: /site/i });
    await waitFor(() => {
      expect(siteInput).not.toBeDisabled();
    });
    fireEvent.focus(siteInput);
    fireEvent.change(siteInput, { target: { value: "Main" } });
    const siteOption = await screen.findByRole("option", { name: "Main Site" });
    fireEvent.mouseDown(siteOption);

    // Click "+ Add custom line item"
    const addCustomLineBtns = screen.getAllByRole("button", {
      name: /\+ Add custom line item/i,
    });
    fireEvent.click(addCustomLineBtns[0]!);

    // Fill in the custom line form — use fireEvent.change for one-shot value setting
    const descInputs = await screen.findAllByPlaceholderText("Description");
    fireEvent.change(descInputs[0]!, { target: { value: "Electrical part" } });

    const amountInputs = screen.getAllByPlaceholderText("Amount ($)");
    fireEvent.change(amountInputs[0]!, { target: { value: "5" } });

    // Click "Add" to commit the custom line
    const addBtns = screen.getAllByRole("button", { name: /^add$/i });
    fireEvent.click(addBtns[0]!);

    // Click Save as Draft — the custom line may or may not be visible in the UI
    // (4 responsive instances make jsdom interaction fragile), but the state
    // should be set. The captured payload will prove whether line_items was sent.
    const saveButtons = screen.getAllByRole("button", {
      name: /Save as Draft/i,
    });
    fireEvent.click(saveButtons[0]!);

    // Verify the captured payload includes line_items
    await waitFor(() => expect(capturedPayload).not.toBeNull());

    const lineItems = capturedPayload!.line_items as Array<
      Record<string, unknown>
    > | null;
    expect(lineItems).not.toBeNull();
    expect(lineItems).toHaveLength(1);
    expect(lineItems![0]!.description).toBe("Electrical part");
    expect(lineItems![0]!.quantity).toBe(1);
    expect(lineItems![0]!.unit_price_cents).toBe(500);

    // PLP-FIX-2: qco_line_type_code must NOT be sent (backend defaults 'misc' by code)
    expect(lineItems![0]!.qco_line_type_code).toBeUndefined();
  });

  it("Save Draft with no custom lines → POST body has line_items: null", async () => {
    const Wrapper = createWrapper();
    render(<InvoiceBuilderPage />, { wrapper: Wrapper });

    // Select customer
    const customerSearchInput =
      await screen.findByPlaceholderText(/search customers/i);
    fireEvent.change(customerSearchInput, { target: { value: "Acme" } });
    const customerOption = await screen.findByRole("option", {
      name: /Acme Electric/i,
    });
    fireEvent.mouseDown(customerOption);

    // Select site
    const siteInput = await screen.findByRole("combobox", { name: /site/i });
    await waitFor(() => {
      expect(siteInput).not.toBeDisabled();
    });
    fireEvent.focus(siteInput);
    fireEvent.change(siteInput, { target: { value: "Main" } });
    const siteOption = await screen.findByRole("option", { name: "Main Site" });
    fireEvent.mouseDown(siteOption);

    // Click Save as Draft (no custom lines added)
    const saveButtons = screen.getAllByRole("button", {
      name: /Save as Draft/i,
    });
    fireEvent.click(saveButtons[0]!);

    await waitFor(() => expect(capturedPayload).not.toBeNull());
    // With no custom lines, line_items should be null
    expect(capturedPayload!.line_items).toBeNull();
  });
});
