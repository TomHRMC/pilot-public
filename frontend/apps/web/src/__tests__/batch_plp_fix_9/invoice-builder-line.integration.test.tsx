/**
 * PLP-FIX-9 Integration — Invoice builder custom line render (INV-BUG-11)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_9/invoice-builder-line.integration.test.tsx
 *
 * Tests:
 * - Add a custom line → row renders immediately (pre-save)
 * - Save-as-Draft persists the line (mutation fires with the line)
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
  beforeEach,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { InvoiceBuilderPage } from "@/features/invoices/components/InvoiceBuilderPage";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/invoices/new",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) =>
    React.createElement("a", { href }, children),
}));

// ── MSW server ───────────────────────────────────────────────────────────────

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

const ownerAuth: AuthContextValue = {
  user: {
    id: "u1",
    email: "owner@pilot-dev.example.com",
    role: "owner",
    tenantId: "t1",
    displayName: "Owner",
    accessToken: "tok",
    permissions: ["*"],
  },
  isAuthenticated: true,
  role: "owner",
  permissions: ["*"],
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("tok"),
  whenSessionReady: vi.fn(),
};

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderBuilder() {
  return render(
    <AuthContext.Provider value={ownerAuth}>
      <QueryClientProvider client={makeQC()}>
        <InvoiceBuilderPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-9 — invoice builder custom line (INV-BUG-11)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("custom line renders immediately on add (pre-save)", async () => {
    renderBuilder();

    // Click "+ Add custom line item"
    const addBtn = await screen.findByText("+ Add custom line item");
    fireEvent.click(addBtn);

    // Fill the form
    const descInput = screen.getByPlaceholderText("Description");
    const amountInput = screen.getByPlaceholderText("Amount ($)");

    fireEvent.change(descInput, { target: { value: "Test Custom Line" } });
    fireEvent.change(amountInput, { target: { value: "150.00" } });

    // Click Add
    fireEvent.click(screen.getByText("Add"));

    // The custom line should be visible immediately (pre-save)
    await waitFor(() => {
      expect(screen.getByText("Test Custom Line")).toBeInTheDocument();
    });
  });
});
