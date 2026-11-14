/**
 * SendQuotePreviewModal unit tests — FE-B19
 *
 * Location: apps/web/src/features/quotes/components/__tests__/SendQuotePreviewModal.test.tsx
 *
 * Platform: Web (Vitest + @testing-library/react)
 *
 * Always-preview-before-send invariant:
 *   - "Cancel" must call onClose WITHOUT calling onConfirm
 *   - "Confirm Send" calls onConfirm
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SendQuotePreviewModal } from "../SendQuotePreviewModal";

const BASE_PROPS = {
  open: true,
  quoteId: "q-00000001-0000-0000-0000-000000000001",
  customerEmail: "mike@smithelectrical.example.com",
  customerName: "Smith Electrical",
  onClose: vi.fn(),
  onConfirm: vi.fn(),
  isConfirming: false,
};

beforeEach(() => {
  BASE_PROPS.onClose.mockClear();
  BASE_PROPS.onConfirm.mockClear();
});

describe("SendQuotePreviewModal", () => {
  it("does not render anything when open=false", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} open={false} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders the dialog when open=true", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows recipient customer name", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} />);
    expect(screen.getByText(/Smith Electrical/i)).toBeInTheDocument();
  });

  it("shows recipient customer email", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} />);
    expect(screen.getByText(/mike@smithelectrical\.com/i)).toBeInTheDocument();
  });

  it("shows the quote ID short prefix", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} />);
    // quoteId.slice(0,8) = "q-000000"
    expect(screen.getAllByText(/q-000000/i).length).toBeGreaterThan(0);
  });

  it("Cancel button calls onClose WITHOUT calling onConfirm", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} />);
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(BASE_PROPS.onClose).toHaveBeenCalledOnce();
    expect(BASE_PROPS.onConfirm).not.toHaveBeenCalled();
  });

  it("Confirm Send button calls onConfirm", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} />);
    fireEvent.click(screen.getByRole("button", { name: /confirm send/i }));
    expect(BASE_PROPS.onConfirm).toHaveBeenCalledOnce();
  });

  it("Confirm Send button is disabled when isConfirming=true", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} isConfirming={true} />);
    const confirmBtn = screen.getByRole("button", { name: /sending/i });
    expect(confirmBtn).toBeDisabled();
  });

  it("shows warning when customerEmail is null", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} customerEmail={null} />);
    expect(screen.getByText(/no email address on file/i)).toBeInTheDocument();
  });

  it("Confirm Send is disabled when customerEmail is null", () => {
    render(<SendQuotePreviewModal {...BASE_PROPS} customerEmail={null} />);
    const confirmBtn = screen.getByRole("button", { name: /confirm send/i });
    expect(confirmBtn).toBeDisabled();
  });
});
