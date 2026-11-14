/**
 * QbConflictRow unit tests — FE-B9
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { QbConflictRow } from "./QbConflictRow";
import type { QbConflictQueueItem } from "../types";

const baseConflict: QbConflictQueueItem = {
  id: "qb-1",
  entityType: "invoice",
  entityId: "inv-1",
  entityDisplayName: "Invoice #INV-001",
  conflictType: "modified_modified",
  masterDirection: "external",
  pilotModifiedAt: "2026-05-25T09:00:00Z",
  externalModifiedAt: "2026-05-25T08:00:00Z",
  financialDeltaCents: 5000,
  resolution: null,
  detectedAt: "2026-05-25T09:05:00Z",
  daysUntilExpiry: null,
};

describe("QbConflictRow", () => {
  it("renders Invoice entity type pill with brand token classes", () => {
    render(
      <table>
        <tbody>
          <QbConflictRow conflict={baseConflict} />
        </tbody>
      </table>,
    );
    const pill = screen.getByTestId("entity-type-pill-invoice");
    expect(pill).toBeInTheDocument();
    expect(pill.className).toContain("bg-brand-100");
    expect(pill.className).toContain("text-brand-700");
    expect(pill).toHaveTextContent("Invoice");
  });

  it("renders Customer entity type pill with neutral token classes", () => {
    const customerConflict = {
      ...baseConflict,
      entityType: "customer" as const,
      entityId: "cust-1",
    };
    render(
      <table>
        <tbody>
          <QbConflictRow conflict={customerConflict} />
        </tbody>
      </table>,
    );
    const pill = screen.getByTestId("entity-type-pill-customer");
    expect(pill.className).toContain("bg-neutral-100");
    expect(pill.className).toContain("text-neutral-700");
    expect(pill).toHaveTextContent("Customer");
  });

  it("renders Quote entity type pill with neutral token classes", () => {
    const quoteConflict = {
      ...baseConflict,
      entityType: "quote" as const,
      entityId: "quote-1",
    };
    render(
      <table>
        <tbody>
          <QbConflictRow conflict={quoteConflict} />
        </tbody>
      </table>,
    );
    const pill = screen.getByTestId("entity-type-pill-quote");
    expect(pill.className).toContain("bg-neutral-100");
    expect(pill).toHaveTextContent("Quote");
  });

  it("renders Expense entity type pill", () => {
    const expenseConflict = { ...baseConflict, entityType: "expense" as const };
    render(
      <table>
        <tbody>
          <QbConflictRow conflict={expenseConflict} />
        </tbody>
      </table>,
    );
    expect(screen.getByTestId("entity-type-pill-expense")).toHaveTextContent(
      "Expense",
    );
  });

  it("renders ExpiryCountdownBadge when daysUntilExpiry <= 7", () => {
    const expiringConflict = { ...baseConflict, daysUntilExpiry: 5 };
    render(
      <table>
        <tbody>
          <QbConflictRow conflict={expiringConflict} />
        </tbody>
      </table>,
    );
    // ExpiryCountdownBadge should be rendered
    expect(screen.getByText(/day/i)).toBeInTheDocument();
  });

  it("does NOT render ExpiryCountdownBadge when daysUntilExpiry is null", () => {
    render(
      <table>
        <tbody>
          <QbConflictRow
            conflict={{ ...baseConflict, daysUntilExpiry: null }}
          />
        </tbody>
      </table>,
    );
    expect(screen.queryByText(/day/i)).not.toBeInTheDocument();
  });

  it("renders financial delta for invoice type", () => {
    render(
      <table>
        <tbody>
          <QbConflictRow conflict={baseConflict} />
        </tbody>
      </table>,
    );
    expect(screen.getByText(/delta/i)).toBeInTheDocument();
  });

  it("renders '—' for non-invoice types with no financial delta", () => {
    const customerConflict = {
      ...baseConflict,
      entityType: "customer" as const,
      financialDeltaCents: null,
    };
    render(
      <table>
        <tbody>
          <QbConflictRow conflict={customerConflict} />
        </tbody>
      </table>,
    );
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders resolve link to correct URL", () => {
    render(
      <table>
        <tbody>
          <QbConflictRow conflict={baseConflict} />
        </tbody>
      </table>,
    );
    const link = screen.getByTestId("resolve-link-qb-1");
    expect(link).toHaveAttribute(
      "href",
      "/settings/integrations/quickbooks/conflicts/qb-1",
    );
  });
});
