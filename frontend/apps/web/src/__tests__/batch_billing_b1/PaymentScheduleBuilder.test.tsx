/**
 * BILLING-B1 Part B — Payment Schedule Builder integration tests
 *
 * Location: apps/web/src/__tests__/batch_billing_b1/PaymentScheduleBuilder.test.tsx
 *
 * Covers the required integration scenarios from the batch prompt:
 *   1. Builder renders for owner (RBAC)
 *   2. Tech does NOT see the builder (RBAC hide-not-disable)
 *   3. State B draft → draw table + reconciliation bar render with MSW data
 *   4. ReconciliationBar shows balanced state with text (residual=0)
 *   5. Activate is enabled when residual=0; disabled when residual≠0
 *   6. Generate-invoice button opens the preview modal
 *
 * Rule 14: fresh QueryClient per test with retry: false.
 * Rule 15: MSW at the HTTP level; server.resetHandlers() in afterEach.
 * Rule 17: web assertions use toBeInTheDocument().
 */

import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { PaymentScheduleBuilder } from "@/features/billing/components/PaymentScheduleBuilder";

// Mock next/navigation (router used by the builder)
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/billing/payment-schedules",
  useSearchParams: () => new URLSearchParams(),
}));

// ── MSW server with the payment schedule handlers ────────────────────────────

const DRAFT_ID = "ps-draft-000-0000-0000-0000-000000000001";
const ACTIVE_ID = "ps-active-000-0000-0000-0000-000000000002";

function makeDraftSchedule(residualCents: number) {
  const contractTotal = 1_000_000;
  const scheduledTotal = contractTotal - residualCents;
  return {
    id: DRAFT_ID,
    tenant_id: "t-001",
    quote_id: "q-001",
    job_id: null,
    customer_id: "c-001",
    site_id: "s-001",
    contract_total_cents: contractTotal,
    status: "draft",
    basis_default: "percent",
    is_active: true,
    lines: [
      {
        id: "psl-draft-001",
        tenant_id: "t-001",
        payment_schedule_id: DRAFT_ID,
        sequence: 1,
        label: "Deposit",
        basis: "percent",
        percent: "30.00",
        amount_cents: null,
        trigger_type: "manual",
        trigger_date: null,
        milestone_label: null,
        invoice_id: null,
        status: "pending",
        is_active: true,
        resolved_amount_cents: 300_000,
      },
      {
        id: "psl-draft-002",
        tenant_id: "t-001",
        payment_schedule_id: DRAFT_ID,
        sequence: 2,
        label: "Final",
        basis: "percent",
        percent: "70.00",
        amount_cents: null,
        trigger_type: "milestone",
        trigger_date: null,
        milestone_label: "Job complete",
        invoice_id: null,
        status: "pending",
        is_active: true,
        resolved_amount_cents: residualCents === 0 ? 700_000 : 600_000,
      },
    ],
    scheduled_total_cents: scheduledTotal,
    residual_cents: residualCents,
  };
}

const ACTIVE_SCHEDULE = {
  id: ACTIVE_ID,
  tenant_id: "t-001",
  quote_id: null,
  job_id: "j-001",
  customer_id: "c-001",
  site_id: "s-001",
  contract_total_cents: 500_000,
  status: "active",
  basis_default: "percent",
  is_active: true,
  lines: [
    {
      id: "psl-active-001",
      tenant_id: "t-001",
      payment_schedule_id: ACTIVE_ID,
      sequence: 1,
      label: "Deposit",
      basis: "percent",
      percent: "50.00",
      amount_cents: null,
      trigger_type: "manual",
      trigger_date: null,
      milestone_label: null,
      invoice_id: "inv-001",
      status: "invoiced",
      is_active: true,
      resolved_amount_cents: 250_000,
    },
    {
      id: "psl-active-002",
      tenant_id: "t-001",
      payment_schedule_id: ACTIVE_ID,
      sequence: 2,
      label: "Final",
      basis: "percent",
      percent: "50.00",
      amount_cents: null,
      trigger_type: "milestone",
      trigger_date: null,
      milestone_label: "Job complete",
      invoice_id: null,
      status: "pending",
      is_active: true,
      resolved_amount_cents: 250_000,
    },
  ],
  scheduled_total_cents: 500_000,
  residual_cents: 0,
};

const server = setupServer(
  // GET detail — balanced draft (residual=0)
  http.get(`/api/v1/payment-schedules/${DRAFT_ID}`, () => {
    return HttpResponse.json(makeDraftSchedule(0));
  }),

  // GET detail — active schedule
  http.get(`/api/v1/payment-schedules/${ACTIVE_ID}`, () => {
    return HttpResponse.json(ACTIVE_SCHEDULE);
  }),

  // POST activate — succeeds (residual=0)
  http.post(`/api/v1/payment-schedules/${DRAFT_ID}/activate`, () => {
    return HttpResponse.json({ ...makeDraftSchedule(0), status: "active" });
  }),

  // POST generate-invoice — succeeds
  http.post(
    `/api/v1/payment-schedules/${ACTIVE_ID}/lines/psl-active-002/generate-invoice`,
    () => {
      return HttpResponse.json(
        {
          id: "inv-gen-001",
          tenant_id: "t-001",
          invoice_number: "INV-001",
          customer_id: "c-001",
          site_id: "s-001",
          status_code: "issued",
          total_cents: 250_000,
          balance_due_cents: 250_000,
        },
        { status: 201 },
      );
    },
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Test helpers ──────────────────────────────────────────────────────────────

function makeContext(
  role: "owner" | "office_staff" | "technician" | "accountant",
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
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderWithRole(
  ui: React.ReactElement,
  role: "owner" | "office_staff" | "technician" | "accountant",
) {
  return render(
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        <NotificationQueueProvider>{ui}</NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PaymentScheduleBuilder — integration", () => {
  it("owner sees the builder (RBAC: invoices.create)", async () => {
    renderWithRole(<PaymentScheduleBuilder scheduleId={DRAFT_ID} />, "owner");

    // Wait for the schedule to load — the status badge is unique
    await waitFor(() => {
      expect(screen.getByTestId("schedule-status-badge")).toBeInTheDocument();
    });
    expect(screen.getByTestId("schedule-status-badge")).toHaveTextContent(
      "Draft",
    );
  });

  it("tech does NOT see the builder (RBAC hide-not-disable)", () => {
    const { container } = renderWithRole(
      <PaymentScheduleBuilder scheduleId={DRAFT_ID} />,
      "technician",
    );
    // RoleGate hides the builder entirely — no schedule content rendered
    expect(
      container.querySelector('[data-testid="schedule-status-badge"]'),
    ).toBeNull();
  });

  it("State B draft renders draw table + reconciliation bar with MSW data", async () => {
    renderWithRole(<PaymentScheduleBuilder scheduleId={DRAFT_ID} />, "owner");

    // Wait for the draw table to render
    await waitFor(() => {
      expect(screen.getByTestId("draw-editor-table")).toBeInTheDocument();
    });

    // Draw labels from the fixture
    expect(screen.getByDisplayValue("Deposit")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Final")).toBeInTheDocument();

    // Reconciliation bar renders
    expect(screen.getByTestId("reconciliation-bar")).toBeInTheDocument();
  });

  it("ReconciliationBar shows balanced state text when residual=0", async () => {
    renderWithRole(<PaymentScheduleBuilder scheduleId={DRAFT_ID} />, "owner");

    await waitFor(() => {
      expect(
        screen.getByText("$0 remaining — ready to activate"),
      ).toBeInTheDocument();
    });
  });

  it("Activate button is enabled when residual=0", async () => {
    renderWithRole(<PaymentScheduleBuilder scheduleId={DRAFT_ID} />, "owner");

    await waitFor(() => {
      const activateBtn = screen.getByTestId("activate-schedule-btn");
      expect(activateBtn).not.toBeDisabled();
    });
  });

  it("Activate button is disabled when residual≠0", async () => {
    // Override the handler to return an under-allocated schedule
    server.use(
      http.get(`/api/v1/payment-schedules/${DRAFT_ID}`, () => {
        return HttpResponse.json(makeDraftSchedule(100_000));
      }),
    );

    renderWithRole(<PaymentScheduleBuilder scheduleId={DRAFT_ID} />, "owner");

    await waitFor(() => {
      const activateBtn = screen.getByTestId("activate-schedule-btn");
      expect(activateBtn).toBeDisabled();
    });

    // Under-allocated text is shown (non-color-only)
    expect(
      screen.getByText(
        /under-allocated — add draws to reach the contract total/,
      ),
    ).toBeInTheDocument();
  });

  it("State C active renders read-only rows with status badges", async () => {
    renderWithRole(<PaymentScheduleBuilder scheduleId={ACTIVE_ID} />, "owner");

    await waitFor(() => {
      expect(screen.getByTestId("schedule-status-badge")).toHaveTextContent(
        "Active",
      );
    });

    // The invoiced draw shows an invoice link
    expect(
      screen.getByTestId("draw-invoice-link-psl-active-001"),
    ).toBeInTheDocument();

    // The pending draw shows a generate-invoice button
    expect(
      screen.getByTestId("generate-invoice-btn-psl-active-002"),
    ).toBeInTheDocument();
  });

  it("Generate-invoice button opens the preview modal", async () => {
    renderWithRole(<PaymentScheduleBuilder scheduleId={ACTIVE_ID} />, "owner");

    // Wait for the active schedule to load
    await waitFor(() => {
      expect(
        screen.getByTestId("generate-invoice-btn-psl-active-002"),
      ).toBeInTheDocument();
    });

    // Click generate-invoice → modal opens
    fireEvent.click(screen.getByTestId("generate-invoice-btn-psl-active-002"));

    await waitFor(() => {
      expect(
        screen.getByTestId("generate-draw-invoice-modal"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Generate Draw Invoice")).toBeInTheDocument();
  });
});
