/**
 * ETCDrillDown — Unit Tests
 *
 * Location: apps/web/src/features/profitability/components/ETCDrillDown.test.tsx
 * Per batch-fe-b4-design.md §I.1
 * Target: 6 tests
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { ETCDrillDown } from "../../dispatch-board/components/ETCDrillDown";
import type { QuoteLine } from "../../dispatch-board/hooks/useJobDetail";

const quoteLines: QuoteLine[] = [
  {
    id: "line-1",
    description: "Labor — Panel upgrade",
    quoted_hours: 10,
    actual_hours: 8,
    remaining_hours: 2,
    tech_breakdowns: [{ tech_id: "tech-1", tech_name: "Mike Chen", hours: 8 }],
  },
  {
    id: "line-2",
    description: "Labor — Conduit run",
    quoted_hours: 4,
    actual_hours: 5.5,
    remaining_hours: 0,
    tech_breakdowns: [],
  },
];

describe("ETCDrillDown", () => {
  it("renders empty state when no quote lines", () => {
    render(<ETCDrillDown quoteLines={[]} />);
    expect(screen.getByText("No ETC data available")).toBeInTheDocument();
  });

  it("renders quote line descriptions", () => {
    render(<ETCDrillDown quoteLines={quoteLines} />);
    expect(screen.getByText("Labor — Panel upgrade")).toBeInTheDocument();
    expect(screen.getByText("Labor — Conduit run")).toBeInTheDocument();
  });

  it("shows quoted hours for each line", () => {
    render(<ETCDrillDown quoteLines={quoteLines} />);
    expect(screen.getByText("10.0h")).toBeInTheDocument();
    expect(screen.getByText("4.0h")).toBeInTheDocument();
  });

  it("shows actual hours for each line", () => {
    render(<ETCDrillDown quoteLines={quoteLines} />);
    // actual hours: 8.0h and 5.5h
    expect(screen.getByText("8.0h")).toBeInTheDocument();
    expect(screen.getByText("5.5h")).toBeInTheDocument();
  });

  it("highlights over-quote line", () => {
    const { container } = render(<ETCDrillDown quoteLines={quoteLines} />);
    // Line 2 is over-quote (5.5 > 4.0)
    const overQuoteRow = container.querySelector("tr.bg-fault-50");
    expect(overQuoteRow).toBeInTheDocument();
  });

  it("expands tech breakdown on row toggle click", () => {
    render(<ETCDrillDown quoteLines={quoteLines} />);

    // Panel upgrade has a tech breakdown — click expand button
    const expandButton = screen.getAllByRole("button")[0];
    expect(expandButton).toBeInTheDocument();

    fireEvent.click(expandButton);

    // Tech breakdown should now be visible
    expect(screen.getByText("Mike Chen")).toBeInTheDocument();
  });

  it("calls onLineSelect when row is toggled", () => {
    const onLineSelect = vi.fn();
    render(
      <ETCDrillDown quoteLines={quoteLines} onLineSelect={onLineSelect} />,
    );

    const expandButton = screen.getAllByRole("button")[0];
    fireEvent.click(expandButton);

    expect(onLineSelect).toHaveBeenCalledWith("line-1");
  });
});
