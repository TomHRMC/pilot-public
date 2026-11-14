/**
 * FE-B24 — Invoice Create Modal Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b24/invoice_create_modal.integration.test.tsx
 *
 * Tests:
 * 1. Invoice create modal renders with form fields (not empty)
 * 2. due_at date input visible
 * 3. Customer notes textarea visible
 * 4. Submit fires POST /api/v1/invoices/
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
import { InvoiceCreateModal } from "@/features/invoices/components/InvoiceCreateModal";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/invoices",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
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

function makeAuth(): AuthContextValue {
  return {
    user: {
      id: "u-1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t-1",
      displayName: "Test Owner",
      accessToken: "mock-token",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function renderModal(onClose = vi.fn(), onSuccess = vi.fn()) {
  return render(
    <AuthContext.Provider value={makeAuth()}>
      <QueryClientProvider client={makeQC()}>
        <NotificationQueueProvider>
          <InvoiceCreateModal
            open={true}
            onClose={onClose}
            onSuccess={onSuccess}
          />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("FE-B24 Invoice Create Modal Integration", () => {
  it("1. Invoice create modal renders with form fields (not empty stub)", async () => {
    renderModal();
    // Heading is always visible; form fields appear after loading completes
    expect(
      await screen.findByRole("heading", { name: "Create Invoice" }),
    ).toBeInTheDocument();
    // Job dropdown — wait for loading to finish
    expect(await screen.findByTestId("invoice-job-select")).toBeInTheDocument();
    expect(screen.getByTestId("invoice-quote-select")).toBeInTheDocument();
  });

  it("2. due_at date input visible", async () => {
    renderModal();
    await screen.findByRole("heading", { name: "Create Invoice" });
    expect(
      await screen.findByTestId("invoice-due-at-input"),
    ).toBeInTheDocument();
  });

  it("3. Customer notes textarea visible", async () => {
    renderModal();
    await screen.findByRole("heading", { name: "Create Invoice" });
    expect(
      await screen.findByTestId("invoice-customer-notes-textarea"),
    ).toBeInTheDocument();
  });

  it("4. Submit fires POST /api/v1/invoices/", async () => {
    let capturedBody: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/invoices/", async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: "inv-b24-test",
            tenant_id: "t-1",
            invoice_number: "INV-B24-001",
            customer_id: "c-1",
            site_id: null,
            status_id: "st-draft",
            status_code: "draft",
            quote_id: null,
            job_id: null,
            issued_at: new Date().toISOString(),
            due_at: null,
            subtotal_cents: 0,
            tax_cents: 0,
            total_cents: 0,
            balance_due_cents: 0,
            currency: "USD",
            customer_notes: capturedBody?.customer_notes ?? null,
            terms_and_conditions: null,
            pdf_object_key: null,
            is_active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            created_by: null,
            updated_by: null,
            lines: [],
          },
          { status: 201 },
        );
      }),
    );

    renderModal();
    // Wait for form to be ready
    const notesTextarea = await screen.findByTestId(
      "invoice-customer-notes-textarea",
    );
    fireEvent.change(notesTextarea, { target: { value: "Test note" } });
    fireEvent.click(screen.getByTestId("invoice-create-submit-btn"));

    await waitFor(() => {
      expect(capturedBody).not.toBeNull();
    });
  });
});
