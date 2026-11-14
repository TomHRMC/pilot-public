/**
 * SendInvoicePreviewModal unit tests — FE-B22
 *
 * Location: apps/web/src/features/invoices/components/__tests__/SendInvoicePreviewModal.test.tsx
 *
 * Key invariant tested: "Cancel" does NOT call onConfirm — always-preview-before-send enforced.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SendInvoicePreviewModal } from "../SendInvoicePreviewModal";

const BASE_PROPS = {
  open: true,
  invoiceId: "inv-00000001-0000-0000-0000-000000000001",
  invoiceNumber: "INV-20260616-0001",
  customerEmail: "smith@example.com",
  onClose: vi.fn(),
  onConfirm: vi.fn(),
  isConfirming: false,
};

describe("SendInvoicePreviewModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing when open=false", () => {
    const { container } = render(
      <SendInvoicePreviewModal {...BASE_PROPS} open={false} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders invoice number in preview when open=true", () => {
    render(<SendInvoicePreviewModal {...BASE_PROPS} />);
    // Invoice number appears in multiple places — check at least one exists
    const elements = screen.getAllByText("INV-20260616-0001");
    expect(elements.length).toBeGreaterThan(0);
  });

  it("renders customer email in recipient row", () => {
    render(<SendInvoicePreviewModal {...BASE_PROPS} />);
    expect(screen.getByText("smith@example.com")).toBeTruthy();
  });

  it("shows 'no email on file' warning when customerEmail is null", () => {
    render(<SendInvoicePreviewModal {...BASE_PROPS} customerEmail={null} />);
    expect(screen.getByText(/no email on file/i)).toBeTruthy();
  });

  it("Cancel calls onClose WITHOUT calling onConfirm — always-preview-before-send invariant", () => {
    render(<SendInvoicePreviewModal {...BASE_PROPS} />);
    fireEvent.click(screen.getByText("Cancel"));
    expect(BASE_PROPS.onClose).toHaveBeenCalledTimes(1);
    expect(BASE_PROPS.onConfirm).not.toHaveBeenCalled();
  });

  it("Confirm Send calls onConfirm", () => {
    render(<SendInvoicePreviewModal {...BASE_PROPS} />);
    fireEvent.click(screen.getByText("Confirm Send"));
    expect(BASE_PROPS.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("Confirm Send is disabled when customerEmail is null", () => {
    render(<SendInvoicePreviewModal {...BASE_PROPS} customerEmail={null} />);
    const confirmBtn = screen.getByText("Confirm Send").closest("button");
    expect(confirmBtn?.disabled).toBe(true);
  });

  it("shows 'Sending…' when isConfirming=true", () => {
    render(<SendInvoicePreviewModal {...BASE_PROPS} isConfirming={true} />);
    expect(screen.getByText("Sending…")).toBeTruthy();
  });

  it("Cancel is disabled when isConfirming=true", () => {
    render(<SendInvoicePreviewModal {...BASE_PROPS} isConfirming={true} />);
    const cancelBtn = screen.getByText("Cancel").closest("button");
    expect(cancelBtn?.disabled).toBe(true);
  });
});
