/**
 * OverpaymentReviewBanner unit tests — CE-1 Part C
 *
 * Location: apps/web/src/features/invoices/components/__tests__/OverpaymentReviewBanner.test.tsx
 *
 * Tests: hidden with no variance, active with unresolved (headline, comment),
 *        resolved collapsed line, RBAC (owner sees Resolve; office_staff does not).
 * RULE: Fresh QueryClient per test with retry: false (§14).
 * RULE: AuthContext.Provider for RBAC (§15).
 * RULE: Never mock apiClient (§15).
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { OverpaymentReviewBanner } from "../OverpaymentReviewBanner";
import type { PaymentSummaryEntry } from "../../hooks/useInvoice";

import type { PilotRole } from "@pilot/ui/auth";

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

const NO_VARIANCE_PAYMENT: PaymentSummaryEntry = {
  id: "pay-001",
  amount_cents: 50000,
  paid_at: "2026-08-12T10:00:00Z",
  paid_via: "card",
  psp_provider: null,
  customer_payment_comment: null,
  status_id: "ps-001",
  amount_variance_cents: 0,
  variance_resolution: null,
  variance_resolution_note: null,
  variance_resolved_at: null,
  variance_resolved_by_user_id: null,
};

const UNRESOLVED_OVERPAYMENT: PaymentSummaryEntry = {
  id: "pay-002",
  amount_cents: 60000,
  paid_at: "2026-08-12T10:00:00Z",
  paid_via: "card",
  psp_provider: null,
  customer_payment_comment: "Customer overpaid by mistake",
  status_id: "ps-001",
  amount_variance_cents: 1500,
  variance_resolution: null,
  variance_resolution_note: null,
  variance_resolved_at: null,
  variance_resolved_by_user_id: null,
};

const RESOLVED_OVERPAYMENT: PaymentSummaryEntry = {
  ...UNRESOLVED_OVERPAYMENT,
  id: "pay-003",
  variance_resolution: "credit",
  variance_resolution_note: "Applied as credit",
  variance_resolved_at: "2026-08-13T10:00:00Z",
  variance_resolved_by_user_id: "u-001",
};

describe("OverpaymentReviewBanner", () => {
  it("renders nothing when no payment has variance", () => {
    const { container } = render(
      <OverpaymentReviewBanner
        invoiceId="inv-001"
        payments={[NO_VARIANCE_PAYMENT]}
      />,
      { wrapper: createWrapper() },
    );

    expect(container.firstChild).toBeNull();
  });

  it("renders active banner with headline and customer comment for unresolved overpayment", () => {
    render(
      <OverpaymentReviewBanner
        invoiceId="inv-001"
        payments={[UNRESOLVED_OVERPAYMENT]}
      />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByTestId("overpayment-review-banner")).toBeInTheDocument();
    expect(screen.getByTestId("overpayment-headline")).toHaveTextContent(
      "Customer paid $15.00 over invoice total — review.",
    );
    expect(
      screen.getByTestId("overpayment-customer-comment"),
    ).toHaveTextContent("Customer note: Customer overpaid by mistake");
  });

  it("shows Resolve button for owner (invoices.update)", () => {
    render(
      <OverpaymentReviewBanner
        invoiceId="inv-001"
        payments={[UNRESOLVED_OVERPAYMENT]}
      />,
      { wrapper: createWrapper("owner") },
    );

    expect(screen.getByTestId("resolve-variance-btn")).toBeInTheDocument();
  });

  it("hides Resolve button for office_staff (no invoices.update per ADR-0010)", () => {
    render(
      <OverpaymentReviewBanner
        invoiceId="inv-001"
        payments={[UNRESOLVED_OVERPAYMENT]}
      />,
      { wrapper: createWrapper("office_staff") },
    );

    expect(
      screen.queryByTestId("resolve-variance-btn"),
    ).not.toBeInTheDocument();
  });

  it("renders resolved collapsed line when all overpayments are resolved", () => {
    render(
      <OverpaymentReviewBanner
        invoiceId="inv-001"
        payments={[RESOLVED_OVERPAYMENT]}
      />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByTestId("overpayment-resolved-line")).toBeInTheDocument();
    expect(screen.getByTestId("overpayment-resolved-line")).toHaveTextContent(
      "credit forward",
    );
    expect(
      screen.queryByTestId("overpayment-review-banner"),
    ).not.toBeInTheDocument();
  });
});
