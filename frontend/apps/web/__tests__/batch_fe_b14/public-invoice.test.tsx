/**
 * FE-B14 Integration Tests — Public Invoice Page
 *
 * Location: apps/web/__tests__/batch_fe_b14/public-invoice.test.tsx
 *
 * Tests for the full public invoice page including:
 * - State-aware: paid, partial, unpaid
 * - AmountSelector: full/adjusted amount, variance, validation
 * - RULE 6: PaymentIntent created with ACTUAL amount
 * - RULE 7: Comments go to /payment-intent, NOT comms threads
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { InvoiceAmountSelector } from "../../src/features/public-invoice/InvoiceAmountSelector";
import { InvoicePaidState } from "../../src/features/public-invoice/InvoicePaidState";
import { InvoicePartialPaidState } from "../../src/features/public-invoice/InvoicePartialPaidState";
import { derivePaymentVariance } from "../../src/features/public-invoice/types";
import type { AmountSelectorState } from "../../src/features/public-invoice/types";

// ─── InvoicePaidState ──────────────────────────────────────────────────────────

describe("InvoicePaidState", () => {
  it("renders PAID status badge with margin-50 background", () => {
    render(
      <InvoicePaidState
        amountPaidCents={386583}
        currency="USD"
        tenantName="Acme Electric"
      />,
    );
    const state = screen.getByTestId("invoice-paid-state");
    expect(state.className).toContain("bg-margin-50");
    expect(screen.getByTestId("paid-badge")).toHaveTextContent("Paid in full");
  });

  it("renders the paid amount correctly", () => {
    render(
      <InvoicePaidState
        amountPaidCents={386583}
        currency="USD"
        tenantName="Acme Electric"
      />,
    );
    expect(screen.getByTestId("paid-badge").closest("div")).toHaveTextContent(
      "$3,865.83",
    );
  });
});

// ─── InvoicePartialPaidState ───────────────────────────────────────────────────

describe("InvoicePartialPaidState", () => {
  const mockOnPayRemaining = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders remaining balance correctly", () => {
    render(
      <InvoicePartialPaidState
        amountPaidCents={200000}
        amountDueCents={186583}
        invoiceTotalCents={386583}
        currency="USD"
        onPayRemaining={mockOnPayRemaining}
      />,
    );
    expect(screen.getByTestId("remaining-balance")).toHaveTextContent(
      "$1,865.83",
    );
  });

  it("renders pay remaining CTA button", () => {
    render(
      <InvoicePartialPaidState
        amountPaidCents={200000}
        amountDueCents={186583}
        invoiceTotalCents={386583}
        currency="USD"
        onPayRemaining={mockOnPayRemaining}
      />,
    );
    const btn = screen.getByTestId("pay-remaining-button");
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent("Pay remaining");
  });

  it("calls onPayRemaining when CTA is clicked", () => {
    render(
      <InvoicePartialPaidState
        amountPaidCents={200000}
        amountDueCents={186583}
        invoiceTotalCents={386583}
        currency="USD"
        onPayRemaining={mockOnPayRemaining}
      />,
    );
    fireEvent.click(screen.getByTestId("pay-remaining-button"));
    expect(mockOnPayRemaining).toHaveBeenCalled();
  });
});

// ─── InvoiceAmountSelector ─────────────────────────────────────────────────────

describe("InvoiceAmountSelector", () => {
  const invoiceAmountDueCents = 386583;
  const invoiceTotalCents = 386583;

  const defaultState: AmountSelectorState = {
    adjusting: false,
    customAmountCents: invoiceAmountDueCents,
    comment: "",
    commentError: null,
    amountError: null,
  };

  const mockOnStateChange = vi.fn();
  const mockOnContinue = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows full amount pre-filled by default (not adjusting)", () => {
    render(
      <InvoiceAmountSelector
        invoiceAmountDueCents={invoiceAmountDueCents}
        invoiceTotalCents={invoiceTotalCents}
        tenantName="Acme Electric"
        state={defaultState}
        onStateChange={mockOnStateChange}
        onContinue={mockOnContinue}
      />,
    );
    expect(screen.getByTestId("full-amount-display")).toBeInTheDocument();
    expect(screen.queryByTestId("custom-amount-input")).not.toBeInTheDocument();
  });

  it("shows variance row when adjusting and custom amount entered", () => {
    const adjustingState: AmountSelectorState = {
      adjusting: true,
      customAmountCents: 200000,
      comment: "Partial payment",
      commentError: null,
      amountError: null,
    };

    render(
      <InvoiceAmountSelector
        invoiceAmountDueCents={invoiceAmountDueCents}
        invoiceTotalCents={invoiceTotalCents}
        tenantName="Acme Electric"
        state={adjustingState}
        onStateChange={mockOnStateChange}
        onContinue={mockOnContinue}
      />,
    );
    expect(screen.getByTestId("variance-display")).toBeInTheDocument();
  });

  it("blocks submission when adjusting and comment is empty (RULE 7 frontgate)", async () => {
    const adjustingNoComment: AmountSelectorState = {
      adjusting: true,
      customAmountCents: 200000,
      comment: "",
      commentError: null,
      amountError: null,
    };

    render(
      <InvoiceAmountSelector
        invoiceAmountDueCents={invoiceAmountDueCents}
        invoiceTotalCents={invoiceTotalCents}
        tenantName="Acme Electric"
        state={adjustingNoComment}
        onStateChange={mockOnStateChange}
        onContinue={mockOnContinue}
      />,
    );
    fireEvent.click(screen.getByTestId("continue-to-payment-button"));
    // onContinue should NOT be called — frontend validation blocks it
    expect(mockOnContinue).not.toHaveBeenCalled();
    // onStateChange called with commentError
    expect(mockOnStateChange).toHaveBeenCalledWith(
      expect.objectContaining({ commentError: expect.any(String) }),
    );
  });

  it("blocks submission when selectedAmountCents <= 0", () => {
    const zeroAmountState: AmountSelectorState = {
      adjusting: true,
      customAmountCents: 0,
      comment: "test",
      commentError: null,
      amountError: null,
    };

    render(
      <InvoiceAmountSelector
        invoiceAmountDueCents={invoiceAmountDueCents}
        invoiceTotalCents={invoiceTotalCents}
        tenantName="Acme Electric"
        state={zeroAmountState}
        onStateChange={mockOnStateChange}
        onContinue={mockOnContinue}
      />,
    );
    // Submit the form directly (fireEvent.click on type="submit" doesn't trigger form.onSubmit in jsdom)
    const form = screen.getByTestId("invoice-amount-selector");
    fireEvent.submit(form);
    expect(mockOnContinue).not.toHaveBeenCalled();
    expect(mockOnStateChange).toHaveBeenCalledWith(
      expect.objectContaining({ amountError: expect.any(String) }),
    );
  });

  it("comment textarea does NOT appear when NOT adjusting", () => {
    render(
      <InvoiceAmountSelector
        invoiceAmountDueCents={invoiceAmountDueCents}
        invoiceTotalCents={invoiceTotalCents}
        tenantName="Acme Electric"
        state={defaultState}
        onStateChange={mockOnStateChange}
        onContinue={mockOnContinue}
      />,
    );
    expect(
      screen.queryByTestId("variance-comment-field"),
    ).not.toBeInTheDocument();
  });

  it("calls onContinue with selectedAmountCents when full amount (RULE 6 verification)", () => {
    render(
      <InvoiceAmountSelector
        invoiceAmountDueCents={invoiceAmountDueCents}
        invoiceTotalCents={invoiceTotalCents}
        tenantName="Acme Electric"
        state={defaultState}
        onStateChange={mockOnStateChange}
        onContinue={mockOnContinue}
      />,
    );
    fireEvent.click(screen.getByTestId("continue-to-payment-button"));
    // RULE 6: Called with the actual selected amount (full invoice amount here)
    expect(mockOnContinue).toHaveBeenCalledWith(
      invoiceAmountDueCents,
      undefined,
    );
  });
});

// ─── derivePaymentVariance utility ────────────────────────────────────────────

describe("derivePaymentVariance", () => {
  it("computes negative variance for partial payment", () => {
    const { varianceCents, remainingCents, isOverpayment } =
      derivePaymentVariance(200000, 386583);
    expect(varianceCents).toBe(200000 - 386583);
    expect(remainingCents).toBe(186583);
    expect(isOverpayment).toBe(false);
  });

  it("computes positive variance for overpayment", () => {
    const { varianceCents, remainingCents, isOverpayment } =
      derivePaymentVariance(400000, 386583);
    expect(varianceCents).toBe(13417);
    expect(remainingCents).toBe(0); // no remaining on overpayment
    expect(isOverpayment).toBe(true);
  });

  it("computes zero variance for exact amount", () => {
    const { varianceCents, remainingCents, isOverpayment } =
      derivePaymentVariance(386583, 386583);
    expect(varianceCents).toBe(0);
    expect(remainingCents).toBe(0);
    expect(isOverpayment).toBe(false);
  });
});
