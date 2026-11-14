/**
 * PendingQuoteCard unit tests
 *
 * Location: apps/web/src/features/quote-approval/components/__tests__/PendingQuoteCard.test.tsx
 *
 * Updated to match real QuoteListItem API shape (GET /api/v1/quotes).
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect } from "vitest";
import { PendingQuoteCard } from "../PendingQuoteCard";
import type { PendingQuoteSummary } from "../../hooks/usePendingQuotes";

function makeQuote(
  overrides: Partial<PendingQuoteSummary> = {},
): PendingQuoteSummary {
  return {
    id: "quote-uuid-1",
    quote_number: "Q-2025-001",
    title: "Panel Upgrade",
    status_code: "pending_approval",
    customer_id: "cust-1",
    customer_name: "Johnson Electric",
    total_cents: 450000,
    subtotal_cents: 420000,
    tax_cents: 30000,
    ...overrides,
  };
}

describe("PendingQuoteCard", () => {
  it("renders quote number", () => {
    render(<PendingQuoteCard quote={makeQuote()} />);
    expect(screen.getByText("#Q-2025-001")).toBeTruthy();
  });

  it("renders customer name", () => {
    render(<PendingQuoteCard quote={makeQuote()} />);
    expect(screen.getByText("Johnson Electric")).toBeTruthy();
  });

  it("renders formatted total", () => {
    render(<PendingQuoteCard quote={makeQuote()} />);
    expect(screen.getByText("$4,500")).toBeTruthy();
  });

  it("renders quote title when present", () => {
    render(<PendingQuoteCard quote={makeQuote({ title: "Panel Upgrade" })} />);
    expect(screen.getByText("Panel Upgrade")).toBeTruthy();
  });

  it("renders Review link pointing to quote detail", () => {
    render(<PendingQuoteCard quote={makeQuote()} />);
    const link = screen.getByRole("link", { name: /review/i });
    expect(link.getAttribute("href")).toBe("/quotes/quote-uuid-1");
  });

  it("renders fallback display name when quote_number is null", () => {
    render(<PendingQuoteCard quote={makeQuote({ quote_number: null })} />);
    expect(screen.getByText(/Quote quote-uu/)).toBeTruthy();
  });

  it("renders 'Unknown customer' when customer_name is null", () => {
    render(<PendingQuoteCard quote={makeQuote({ customer_name: null })} />);
    expect(screen.getAllByText("Unknown customer").length).toBeGreaterThan(0);
  });
});
