/**
 * ReconciliationBar unit tests
 *
 * Location: apps/web/src/features/billing/components/__tests__/ReconciliationBar.test.tsx
 *
 * BILLING-B1 Part B — asserts on TEXT labels (not color) for the three
 * reconciliation states (WCAG 1.4.1 — color is never the only signal).
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReconciliationBar } from "../ReconciliationBar";

describe("ReconciliationBar", () => {
  const CONTRACT = 1_000_000; // $10,000

  it("shows balanced state with text when residual === 0", () => {
    render(
      <ReconciliationBar
        scheduledTotalCents={1_000_000}
        contractTotalCents={CONTRACT}
        residualCents={0}
      />,
    );
    expect(
      screen.getByText("$0 remaining — ready to activate"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("residual-banner")).toHaveAttribute(
      "data-state",
      "balanced",
    );
  });

  it("shows under-allocated state with text when residual > 0", () => {
    render(
      <ReconciliationBar
        scheduledTotalCents={700_000}
        contractTotalCents={CONTRACT}
        residualCents={300_000}
      />,
    );
    expect(
      screen.getByText(
        "$3,000.00 under-allocated — add draws to reach the contract total",
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId("residual-banner")).toHaveAttribute(
      "data-state",
      "under",
    );
  });

  it("shows over-allocated state with text when residual < 0", () => {
    render(
      <ReconciliationBar
        scheduledTotalCents={1_200_000}
        contractTotalCents={CONTRACT}
        residualCents={-200_000}
      />,
    );
    expect(
      screen.getByText(
        "$2,000.00 over-allocated — reduce draws to match the contract total",
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId("residual-banner")).toHaveAttribute(
      "data-state",
      "over",
    );
  });

  it("displays scheduled and contract totals as formatted USD", () => {
    render(
      <ReconciliationBar
        scheduledTotalCents={750_000}
        contractTotalCents={1_000_000}
        residualCents={250_000}
      />,
    );
    expect(screen.getByTestId("scheduled-total")).toHaveTextContent(
      "$7,500.00",
    );
    expect(screen.getByTestId("contract-total")).toHaveTextContent(
      "$10,000.00",
    );
  });

  it("shows completed treatment text when isCompleted=true", () => {
    render(
      <ReconciliationBar
        scheduledTotalCents={1_000_000}
        contractTotalCents={CONTRACT}
        residualCents={0}
        isCompleted
      />,
    );
    expect(
      screen.getByText("Schedule completed — all draws invoiced"),
    ).toBeInTheDocument();
  });
});
