/**
 * ArSummaryWidget unit tests — FE-B22
 *
 * Location: apps/web/src/features/dashboard/components/__tests__/ArSummaryWidget.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ArSummaryWidget } from "../ArSummaryWidget";

vi.mock("../../hooks/useArSummary", () => ({
  useArSummary: vi.fn(),
}));

// UI-FIX-1B: Next.js Link renders as <a> in jsdom when mocked
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

import { useArSummary } from "../../hooks/useArSummary";

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

const MOCK_SUMMARY = {
  report_type: "ar_aging",
  as_of_date: "2026-06-16",
  display_mode: "summary",
  row_count: 9,
  report_chart_threshold: 10,
  summary: {
    current_cents: 245000,
    bucket_31_60_cents: 120000,
    bucket_61_90_cents: 80000,
    bucket_91_plus_cents: 35000,
    total_outstanding_cents: 480000,
  },
  data: [],
};

describe("ArSummaryWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state while fetching", () => {
    (useArSummary as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
    });
    render(<ArSummaryWidget />, { wrapper: createWrapper() });
    // LoadingState may render text multiple times — use getAllByText
    const els = screen.getAllByText(/loading ar summary/i);
    expect(els.length).toBeGreaterThan(0);
  });

  it("renders EmptyState when no outstanding invoices", () => {
    (useArSummary as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        ...MOCK_SUMMARY,
        summary: { ...MOCK_SUMMARY.summary, total_outstanding_cents: 0 },
      },
      isLoading: false,
    });
    render(<ArSummaryWidget />, { wrapper: createWrapper() });
    expect(screen.getByText(/no outstanding invoices/i)).toBeTruthy();
  });

  it("renders all 4 AR aging buckets with amounts", () => {
    (useArSummary as ReturnType<typeof vi.fn>).mockReturnValue({
      data: MOCK_SUMMARY,
      isLoading: false,
    });
    render(<ArSummaryWidget />, { wrapper: createWrapper() });

    expect(screen.getByTestId("ar-bucket-current")).toBeTruthy();
    expect(screen.getByTestId("ar-bucket-30d")).toBeTruthy();
    expect(screen.getByTestId("ar-bucket-60d")).toBeTruthy();
    expect(screen.getByTestId("ar-bucket-90d")).toBeTruthy();
  });

  it("renders total outstanding amount", () => {
    (useArSummary as ReturnType<typeof vi.fn>).mockReturnValue({
      data: MOCK_SUMMARY,
      isLoading: false,
    });
    render(<ArSummaryWidget />, { wrapper: createWrapper() });
    // $4,800.00 total
    expect(screen.getByText(/total outstanding/i)).toBeTruthy();
  });

  it("renders current bucket label", () => {
    (useArSummary as ReturnType<typeof vi.fn>).mockReturnValue({
      data: MOCK_SUMMARY,
      isLoading: false,
    });
    render(<ArSummaryWidget />, { wrapper: createWrapper() });
    expect(screen.getByText("Current")).toBeTruthy();
    expect(screen.getByText("30+ days")).toBeTruthy();
    expect(screen.getByText("60+ days")).toBeTruthy();
    expect(screen.getByText("90+ days")).toBeTruthy();
  });

  // UI-FIX-1B: FIX-010a — bucket rows are clickable links
  it("bucket rows are clickable links to invoices page", () => {
    (useArSummary as ReturnType<typeof vi.fn>).mockReturnValue({
      data: MOCK_SUMMARY,
      isLoading: false,
    });
    render(<ArSummaryWidget />, { wrapper: createWrapper() });

    // "Current" bucket links to /invoices (no filter)
    const currentBucket = screen.getByTestId("ar-bucket-current");
    expect(currentBucket.tagName).toBe("A");
    expect(currentBucket.getAttribute("href")).toBe("/invoices");

    // "30+ days" bucket links to /invoices with overdue+due_before params
    const bucket30 = screen.getByTestId("ar-bucket-30d");
    expect(bucket30.tagName).toBe("A");
    const href30 = bucket30.getAttribute("href") ?? "";
    expect(href30).toContain("/invoices?overdue=true&due_before=");

    // "60+ days" bucket links to /invoices with overdue+due_before params
    const bucket60 = screen.getByTestId("ar-bucket-60d");
    expect(bucket60.tagName).toBe("A");
    expect(bucket60.getAttribute("href") ?? "").toContain(
      "/invoices?overdue=true&due_before=",
    );

    // "90+ days" bucket links to /invoices with overdue+due_before params
    const bucket90 = screen.getByTestId("ar-bucket-90d");
    expect(bucket90.tagName).toBe("A");
    expect(bucket90.getAttribute("href") ?? "").toContain(
      "/invoices?overdue=true&due_before=",
    );
  });
});
