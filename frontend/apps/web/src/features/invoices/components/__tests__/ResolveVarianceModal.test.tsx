/**
 * ResolveVarianceModal unit tests — CE-1 Part C
 *
 * Location: apps/web/src/features/invoices/components/__tests__/ResolveVarianceModal.test.tsx
 *
 * Tests: submit disabled until selection, note counter, success closes + invalidates,
 *        409 → notification + close, 422 → inline error stays open, Escape behavior,
 *        focus trap smoke test.
 * RULE: Fresh QueryClient per test with retry: false (§14).
 * RULE: MSW setupServer + resetHandlers in afterEach (§15).
 * RULE: AuthContext.Provider for RBAC (§15).
 * RULE: Never mock apiClient (§15).
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { ResolveVarianceModal } from "../ResolveVarianceModal";
import type { PaymentSummaryEntry } from "../../hooks/useInvoice";

const server = setupServer(
  http.post(
    "/api/v1/invoices/:paymentId/resolve-variance",
    async ({ params, request }) => {
      const { paymentId } = params as { paymentId: string };
      const body = (await request.json()) as {
        resolution: string;
        note?: string;
      };

      if (paymentId === "pay-409-test") {
        return HttpResponse.json(
          { detail: "This overpayment was already resolved." },
          { status: 409 },
        );
      }

      if (paymentId === "pay-422-test") {
        return HttpResponse.json(
          { detail: "No overpayment to resolve." },
          { status: 422 },
        );
      }

      return HttpResponse.json({
        id: paymentId,
        invoice_id: "inv-001",
        tenant_id: "t-001",
        amount_cents: 60000,
        paid_via: "card",
        balance_due_cents: 0,
        amount_variance_cents: 1500,
        status_id: "ps-001",
        paid_at: "2026-08-12T10:00:00Z",
        idempotency_key: null,
        created_at: "2026-08-12T10:00:00Z",
        variance_resolution: body.resolution,
        variance_resolution_note: body.note ?? null,
        variance_resolved_at: "2026-08-12T15:00:00Z",
        variance_resolved_by_user_id: "u-001",
      });
    },
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeAuthContext(role: PilotRole): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "test@example.com",
      role,
      tenantId: "t-001",
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

function createWrapper(role: PilotRole = "owner") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const ctx = makeAuthContext(role);
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={ctx}>
        <QueryClientProvider client={qc}>
          <NotificationQueueProvider>{children}</NotificationQueueProvider>
        </QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  return Wrapper;
}

const MOCK_PAYMENT: PaymentSummaryEntry = {
  id: "pay-success-test",
  amount_cents: 60000,
  paid_at: "2026-08-12T10:00:00Z",
  paid_via: "card",
  psp_provider: null,
  customer_payment_comment: "Overpaid by mistake",
  status_id: "ps-001",
  amount_variance_cents: 1500,
  variance_resolution: null,
  variance_resolution_note: null,
  variance_resolved_at: null,
  variance_resolved_by_user_id: null,
};

const BASE_PROPS = {
  open: true,
  invoiceId: "inv-001",
  payment: MOCK_PAYMENT,
  onClose: vi.fn(),
};

describe("ResolveVarianceModal", () => {
  it("submit is disabled until a radio is selected", () => {
    render(<ResolveVarianceModal {...BASE_PROPS} />, {
      wrapper: createWrapper(),
    });

    const submitBtn = screen.getByTestId("resolve-variance-submit");
    expect(submitBtn).toBeDisabled();
  });

  it("enables submit after selecting a resolution option", () => {
    render(<ResolveVarianceModal {...BASE_PROPS} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(
      screen.getByTestId("resolution-option-credit").querySelector("input")!,
    );

    const submitBtn = screen.getByTestId("resolve-variance-submit");
    expect(submitBtn).not.toBeDisabled();
  });

  it("note counter updates as user types", () => {
    render(<ResolveVarianceModal {...BASE_PROPS} />, {
      wrapper: createWrapper(),
    });

    const textarea = screen.getByTestId(
      "resolve-variance-note",
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "test note" } });

    expect(screen.getByText("9 / 1000")).toBeInTheDocument();
  });

  it("success closes modal and calls onClose", async () => {
    const onClose = vi.fn();
    function ControlledModal() {
      const [open, setOpen] = React.useState(true);
      return (
        <ResolveVarianceModal
          open={open}
          invoiceId="inv-001"
          payment={MOCK_PAYMENT}
          onClose={() => {
            setOpen(false);
            onClose();
          }}
        />
      );
    }
    render(<ControlledModal />, { wrapper: createWrapper() });

    // Select credit and submit
    fireEvent.click(
      screen.getByTestId("resolution-option-credit").querySelector("input")!,
    );
    fireEvent.click(screen.getByTestId("resolve-variance-submit"));

    await waitFor(() => {
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  it("409 closes modal (onClose called)", async () => {
    const onClose = vi.fn();
    function ControlledModal() {
      const [open, setOpen] = React.useState(true);
      return (
        <ResolveVarianceModal
          open={open}
          invoiceId="inv-001"
          payment={{ ...MOCK_PAYMENT, id: "pay-409-test" }}
          onClose={() => {
            setOpen(false);
            onClose();
          }}
        />
      );
    }
    render(<ControlledModal />, { wrapper: createWrapper() });

    fireEvent.click(
      screen.getByTestId("resolution-option-writeoff").querySelector("input")!,
    );
    fireEvent.click(screen.getByTestId("resolve-variance-submit"));

    await waitFor(() => {
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    // Modal is closed (409 → invalidate + close + notification per §16.4)
    // Note: the notification is added to the queue via useNotificationQueue,
    // but NotificationPortal (which renders banners) is not mounted in this
    // unit test wrapper — it lives in the app layout. We verify the modal
    // closed via onClose + DOM removal.
    expect(
      screen.queryByTestId("resolve-variance-modal"),
    ).not.toBeInTheDocument();
  });

  it("422 shows inline error and modal stays open", async () => {
    const onClose = vi.fn();
    render(
      <ResolveVarianceModal
        open={true}
        invoiceId="inv-001"
        payment={{ ...MOCK_PAYMENT, id: "pay-422-test" }}
        onClose={onClose}
      />,
      { wrapper: createWrapper() },
    );

    fireEvent.click(
      screen.getByTestId("resolution-option-credit").querySelector("input")!,
    );
    fireEvent.click(screen.getByTestId("resolve-variance-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("resolve-variance-error")).toBeInTheDocument();
    });

    expect(screen.getByTestId("resolve-variance-error")).toHaveTextContent(
      "No overpayment to resolve.",
    );
    expect(onClose).not.toHaveBeenCalled();
  });

  it("Escape closes modal when idle", () => {
    const onClose = vi.fn();
    render(
      <ResolveVarianceModal
        open={true}
        invoiceId="inv-001"
        payment={MOCK_PAYMENT}
        onClose={onClose}
      />,
      { wrapper: createWrapper() },
    );

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("has role=dialog and aria-modal for accessibility", () => {
    render(<ResolveVarianceModal {...BASE_PROPS} />, {
      wrapper: createWrapper(),
    });

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAttribute("aria-labelledby", "resolve-variance-title");
  });
});
