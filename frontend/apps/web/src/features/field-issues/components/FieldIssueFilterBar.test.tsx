/**
 * FieldIssueFilterBar unit tests — FE-B9
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import { FieldIssueFilterBar } from "./FieldIssueFilterBar";

const defaultProps = {
  status: "pending" as const,
  onStatusChange: vi.fn(),
  operationType: undefined,
  onOperationTypeChange: vi.fn(),
  activeTechsOnly: true,
  onActiveTechsOnlyChange: vi.fn(),
};

describe("FieldIssueFilterBar", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders status filter chips", () => {
    render(<FieldIssueFilterBar {...defaultProps} />);
    expect(screen.getByTestId("status-filter-pending")).toBeInTheDocument();
    expect(
      screen.getByTestId("status-filter-auto_recovered"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("status-filter-stale")).toBeInTheDocument();
    expect(screen.getByTestId("status-filter-all")).toBeInTheDocument();
  });

  it("active-techs chip is ON by default", () => {
    render(<FieldIssueFilterBar {...defaultProps} activeTechsOnly={true} />);
    const toggle = screen.getByTestId(
      "active-techs-only-toggle",
    ) as HTMLInputElement;
    expect(toggle.checked).toBe(true);
  });

  it("active-techs chip is OFF when activeTechsOnly=false", () => {
    render(<FieldIssueFilterBar {...defaultProps} activeTechsOnly={false} />);
    const toggle = screen.getByTestId(
      "active-techs-only-toggle",
    ) as HTMLInputElement;
    expect(toggle.checked).toBe(false);
  });

  it("calls onActiveTechsOnlyChange when checkbox toggled", () => {
    render(<FieldIssueFilterBar {...defaultProps} />);
    fireEvent.click(screen.getByTestId("active-techs-only-toggle"));
    expect(defaultProps.onActiveTechsOnlyChange).toHaveBeenCalledWith(false);
  });

  it("operation-type chips emit correct filter value", () => {
    render(<FieldIssueFilterBar {...defaultProps} />);
    fireEvent.click(screen.getByTestId("operation-type-expense"));
    expect(defaultProps.onOperationTypeChange).toHaveBeenCalledWith("expense");
  });

  it("clicking same operation type again clears filter", () => {
    render(<FieldIssueFilterBar {...defaultProps} operationType="expense" />);
    fireEvent.click(screen.getByTestId("operation-type-expense"));
    expect(defaultProps.onOperationTypeChange).toHaveBeenCalledWith(undefined);
  });

  it("status chip emits correct status value on click", () => {
    render(<FieldIssueFilterBar {...defaultProps} />);
    fireEvent.click(screen.getByTestId("status-filter-stale"));
    expect(defaultProps.onStatusChange).toHaveBeenCalledWith("stale");
  });

  it("renders all 5 operation type chips", () => {
    render(<FieldIssueFilterBar {...defaultProps} />);
    expect(screen.getByTestId("operation-type-time_entry")).toBeInTheDocument();
    expect(screen.getByTestId("operation-type-expense")).toBeInTheDocument();
    expect(screen.getByTestId("operation-type-photo")).toBeInTheDocument();
    expect(
      screen.getByTestId("operation-type-status_change"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("operation-type-loto")).toBeInTheDocument();
  });
});
