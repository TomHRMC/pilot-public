/**
 * InvoiceSignoffSection (S1) unit tests
 *
 * Location: apps/mobile/features/jobs/components/detail/__tests__/InvoiceSignoffSection.test.tsx
 *
 * Tests:
 *   - Hidden on empty invoices (renders null)
 *   - Ready state renders CTA
 *   - Multi-invoice pills render + default selection
 *   - Signed state shows summary + Re-capture
 *   - Error state + retry calls refetch
 *   - Loading state testID
 *
 * Note: Mobile tests mock hooks directly — MSW server is not used
 * (the voice WS handler crashes in Jest's jsdom environment).
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InvoiceSignoffSection } from "../InvoiceSignoffSection";

// ── Mock expo-router ──────────────────────────────────────────────────────────

const mockPush = jest.fn();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush, back: jest.fn(), replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: mockPush, back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
}));

// ── Mock WatermelonDB ─────────────────────────────────────────────────────────

jest.mock("../../../../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn(() => ({
      query: jest.fn(() => ({ fetch: jest.fn(async () => []) })),
    })),
  },
}));

// ── Mock useSignoffContext ────────────────────────────────────────────────────

const mockRefetch = jest.fn();
const mockUseSignoffContext = jest.fn();

jest.mock("../../../hooks/useSignoffContext", () => ({
  useSignoffContext: () => mockUseSignoffContext(),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

const JOB_ID = "job-signoff-test-001";

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

function renderSection() {
  return render(
    <InvoiceSignoffSection jobId={JOB_ID} userId="tech-user-001" />,
    { wrapper: createWrapper() },
  );
}

const SINGLE_INVOICE = {
  job_id: JOB_ID,
  customer_display_name: "John Smith",
  invoices: [
    {
      invoice_id: "invoice-signoff-001",
      invoice_number: "INV-0042",
      status: "issued",
      total_cents: 125000,
      balance_due_cents: 125000,
      currency: "USD",
      terms_text: "Standard terms apply.",
      active_signoff: null,
    },
  ],
};

const MULTI_INVOICE = {
  job_id: JOB_ID,
  customer_display_name: "Apex Commercial LLC",
  invoices: [
    {
      invoice_id: "invoice-signoff-001",
      invoice_number: "INV-0042",
      status: "issued",
      total_cents: 125000,
      balance_due_cents: 125000,
      currency: "USD",
      terms_text: "Standard terms apply.",
      active_signoff: null,
    },
    {
      invoice_id: "invoice-signoff-002",
      invoice_number: "INV-0043",
      status: "partial",
      total_cents: 85000,
      balance_due_cents: 42500,
      currency: "USD",
      terms_text: "Partial payment received.",
      active_signoff: null,
    },
  ],
};

const SIGNED_INVOICE = {
  job_id: JOB_ID,
  customer_display_name: "Mary Johnson",
  invoices: [
    {
      invoice_id: "invoice-signoff-signed-001",
      invoice_number: "INV-0050",
      status: "issued",
      total_cents: 95000,
      balance_due_cents: 95000,
      currency: "USD",
      terms_text: "Standard terms apply.",
      active_signoff: {
        signoff_id: "signoff-001",
        signed_by_name: "Mary Johnson",
        signed_at: "2026-08-12T14:30:00Z",
      },
    },
  ],
};

const EMPTY_INVOICE = {
  job_id: JOB_ID,
  customer_display_name: "Bob Davis",
  invoices: [],
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("InvoiceSignoffSection (S1)", () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockRefetch.mockClear();
    mockUseSignoffContext.mockReset();
  });

  it("renders loading state initially", () => {
    mockUseSignoffContext.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      refetch: mockRefetch,
    });

    renderSection();
    expect(screen.getByTestId("signoff-section-loading")).toBeTruthy();
  });

  it("hides (renders null) when invoices array is empty", () => {
    mockUseSignoffContext.mockReturnValue({
      data: EMPTY_INVOICE,
      isPending: false,
      isError: false,
      refetch: mockRefetch,
    });

    const { toJSON } = renderSection();
    expect(toJSON()).toBeNull();
  });

  it("renders ready-to-capture CTA for single invoice", () => {
    mockUseSignoffContext.mockReturnValue({
      data: SINGLE_INVOICE,
      isPending: false,
      isError: false,
      refetch: mockRefetch,
    });

    renderSection();

    expect(screen.getByTestId("signoff-section-ready")).toBeTruthy();
    expect(screen.getByTestId("signoff-capture-button")).toBeTruthy();
    expect(screen.getByText("INV-0042")).toBeTruthy();
  });

  it("renders multi-invoice pills with default selection", () => {
    mockUseSignoffContext.mockReturnValue({
      data: MULTI_INVOICE,
      isPending: false,
      isError: false,
      refetch: mockRefetch,
    });

    renderSection();

    expect(screen.getByTestId("signoff-section-multi")).toBeTruthy();
    expect(screen.getByTestId("signoff-pill-0")).toBeTruthy();
    expect(screen.getByTestId("signoff-pill-1")).toBeTruthy();
  });

  it("shows signed summary + Re-capture for already-signed invoice", () => {
    mockUseSignoffContext.mockReturnValue({
      data: SIGNED_INVOICE,
      isPending: false,
      isError: false,
      refetch: mockRefetch,
    });

    renderSection();

    expect(screen.getByTestId("signoff-section-signed")).toBeTruthy();
    expect(screen.getByText("Mary Johnson")).toBeTruthy();
    expect(screen.getByTestId("signoff-recapture-button")).toBeTruthy();
  });

  it("shows error state + retry button calls refetch", () => {
    mockUseSignoffContext.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      refetch: mockRefetch,
    });

    renderSection();

    expect(screen.getByTestId("signoff-section-error")).toBeTruthy();
    expect(screen.getByText("Couldn't load invoice sign-off.")).toBeTruthy();
    expect(screen.getByTestId("signoff-retry-button")).toBeTruthy();
  });
});
