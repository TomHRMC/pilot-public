/**
 * InvoiceLineItemsTable unit tests — FE-B22
 *
 * Location: apps/web/src/features/invoices/components/__tests__/InvoiceLineItemsTable.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect } from "vitest";
import { InvoiceLineItemsTable } from "../InvoiceLineItemsTable";
import type { InvoiceLineResponse } from "../../hooks/useInvoice";

const MOCK_LINES: InvoiceLineResponse[] = [
  {
    id: "il-0001",
    invoice_id: "inv-0001",
    source_type: "catalog_item",
    source_id: "ci-0001",
    description: "200A Service Panel Upgrade",
    quantity: 1,
    unit_price_cents: 45000,
    subtotal_cents: 45000,
    tax_amount_cents: 3713,
    total_cents: 48713,
    sort_order: 0,
  },
  {
    id: "il-0002",
    invoice_id: "inv-0001",
    source_type: "catalog_item",
    source_id: "ci-0002",
    description: "Wire, 12 AWG 100ft",
    quantity: 100,
    unit_price_cents: 85,
    subtotal_cents: 8500,
    tax_amount_cents: 701,
    total_cents: 9201,
    sort_order: 1,
  },
];

describe("InvoiceLineItemsTable", () => {
  it("renders all line item descriptions", () => {
    render(
      <InvoiceLineItemsTable
        lines={MOCK_LINES}
        subtotalCents={53500}
        taxCents={4414}
        totalCents={57914}
      />,
    );
    expect(screen.getByText("200A Service Panel Upgrade")).toBeTruthy();
    expect(screen.getByText("Wire, 12 AWG 100ft")).toBeTruthy();
  });

  it("renders quantity for each line", () => {
    render(
      <InvoiceLineItemsTable
        lines={MOCK_LINES}
        subtotalCents={53500}
        taxCents={4414}
        totalCents={57914}
      />,
    );
    expect(screen.getByText("1")).toBeTruthy();
    expect(screen.getByText("100")).toBeTruthy();
  });

  it("renders footer with correct grand total", () => {
    render(
      <InvoiceLineItemsTable
        lines={MOCK_LINES}
        subtotalCents={53500}
        taxCents={4414}
        totalCents={57914}
      />,
    );
    const totalEl = screen.getByTestId("invoice-total");
    expect(totalEl.textContent).toContain("579.14");
  });

  it("renders footer with correct subtotal", () => {
    render(
      <InvoiceLineItemsTable
        lines={MOCK_LINES}
        subtotalCents={53500}
        taxCents={4414}
        totalCents={57914}
      />,
    );
    const subtotalEl = screen.getByTestId("invoice-subtotal");
    expect(subtotalEl.textContent).toContain("535.00");
  });

  it("shows empty state when lines array is empty", () => {
    render(
      <InvoiceLineItemsTable
        lines={[]}
        subtotalCents={0}
        taxCents={0}
        totalCents={0}
      />,
    );
    expect(screen.getByText(/no line items/i)).toBeTruthy();
  });
});
