/**
 * QuoteApprovalActionBar unit tests
 *
 * Location: apps/web/src/features/quote-approval/components/__tests__/QuoteApprovalActionBar.test.tsx
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { QuoteApprovalActionBar } from "../QuoteApprovalActionBar";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const baseProps = {
  quoteId: "quote-uuid-1",
  pendingEditCount: 0,
  requireApproval: true,
  isApproving: false,
  lineItems: [],
  onApprove: vi.fn(),
  onApproveWithEdits: vi.fn(),
};

describe("QuoteApprovalActionBar", () => {
  it("renders Approve button when no pending edits", () => {
    render(<QuoteApprovalActionBar {...baseProps} />, { wrapper });
    expect(screen.getByTestId("approve-btn")).toBeTruthy();
    expect(screen.queryByTestId("approve-with-edits-btn")).toBeNull();
  });

  it("renders Approve with N edits button when pendingEditCount > 0", () => {
    render(<QuoteApprovalActionBar {...baseProps} pendingEditCount={2} />, {
      wrapper,
    });
    expect(screen.getByTestId("approve-with-edits-btn")).toBeTruthy();
    expect(screen.queryByTestId("approve-btn")).toBeNull();
    expect(screen.getByText(/approve with 2 edit/i)).toBeTruthy();
  });

  it("Approve button calls onApprove handler", () => {
    const onApprove = vi.fn();
    render(<QuoteApprovalActionBar {...baseProps} onApprove={onApprove} />, {
      wrapper,
    });
    fireEvent.click(screen.getByTestId("approve-btn"));
    expect(onApprove).toHaveBeenCalledOnce();
  });

  it("Approve-with-edits calls onApproveWithEdits handler", () => {
    const onApproveWithEdits = vi.fn();
    render(
      <QuoteApprovalActionBar
        {...baseProps}
        pendingEditCount={1}
        onApproveWithEdits={onApproveWithEdits}
      />,
      { wrapper },
    );
    fireEvent.click(screen.getByTestId("approve-with-edits-btn"));
    expect(onApproveWithEdits).toHaveBeenCalledOnce();
  });

  it("does NOT render when requireApproval=false", () => {
    const { container } = render(
      <QuoteApprovalActionBar {...baseProps} requireApproval={false} />,
      { wrapper },
    );
    expect(container.firstChild).toBeNull();
  });

  it("all buttons are disabled when isApproving=true", () => {
    render(<QuoteApprovalActionBar {...baseProps} isApproving />, { wrapper });
    const approveBtn = screen.getByTestId("approve-btn");
    expect(approveBtn).toBeDisabled();
  });

  it("renders Kick Back button", () => {
    render(<QuoteApprovalActionBar {...baseProps} />, { wrapper });
    expect(screen.getByTestId("kickback-btn")).toBeTruthy();
  });

  it("renders Reject button", () => {
    render(<QuoteApprovalActionBar {...baseProps} />, { wrapper });
    expect(screen.getByTestId("reject-btn")).toBeTruthy();
  });
});
