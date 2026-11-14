/**
 * WipSummaryRow — Unit Tests
 *
 * Location: apps/web/src/features/wip/components/__tests__/WipSummaryRow.test.tsx
 *
 * Verifies the 4 metric values render from a mock summary.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { WipSummaryRow } from "../WipSummaryRow";

const mockSummary = {
  active_job_count: 12,
  total_actual_cost_cents: 480000,
  total_quoted_budget_cents: 720000,
  total_projected_cost_cents: 610000,
  jobs_over_budget_count: 3,
  jobs_below_margin_target_count: 4,
};

describe("WipSummaryRow", () => {
  it("renders all 4 metric card labels", () => {
    render(<WipSummaryRow summary={mockSummary} />);
    expect(screen.getByText("Active Jobs")).toBeTruthy();
    expect(screen.getByText("Over Budget")).toBeTruthy();
    expect(screen.getByText("Below Margin Target")).toBeTruthy();
    expect(screen.getByText("Projected vs Budget")).toBeTruthy();
  });

  it("renders the active job count", () => {
    render(<WipSummaryRow summary={mockSummary} />);
    expect(screen.getByText("12")).toBeTruthy();
  });

  it("renders the over budget count", () => {
    render(<WipSummaryRow summary={mockSummary} />);
    expect(screen.getByText("3")).toBeTruthy();
  });

  it("renders the below margin target count", () => {
    render(<WipSummaryRow summary={mockSummary} />);
    expect(screen.getByText("4")).toBeTruthy();
  });

  it("renders projected vs budget as formatted currency", () => {
    render(<WipSummaryRow summary={mockSummary} />);
    // $6,100 projected, $7,200 budget
    expect(screen.getByText("$6,100")).toBeTruthy();
    expect(screen.getByText("of $7,200 budget")).toBeTruthy();
  });

  it("shows 'No quoted budgets' when total_quoted_budget_cents is 0", () => {
    render(
      <WipSummaryRow
        summary={{ ...mockSummary, total_quoted_budget_cents: 0 }}
      />,
    );
    expect(screen.getByText("No quoted budgets")).toBeTruthy();
  });
});
