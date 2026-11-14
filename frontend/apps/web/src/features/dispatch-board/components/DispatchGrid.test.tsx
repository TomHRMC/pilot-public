/**
 * DispatchGrid — Unit Tests (view routing)
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchGrid.test.tsx
 * Per batch-beta-v1-fixes-b5-design.md §I.1
 * Updated BETA-B7: month branch now routes to MonthCalendarGrid
 * Updated FE-B30: removed "4day" view mode (DispatchViewTab is now "day"|"week"|"month")
 *
 * Verifies:
 * - No viewMode prop → day path (DispatchGridDayView)
 * - viewMode='week' → MultiDayGrid
 * - viewMode='month' → MonthCalendarGrid (BETA-B7: replaces MonthDeferredState)
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { DispatchGrid } from "./DispatchGrid";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";

// Mock react-dnd
vi.mock("react-dnd", () => ({
  DndProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useDrag: () => [{ isDragging: false }, vi.fn(), vi.fn()],
  useDrop: () => [{ isOver: false, canDrop: true }, vi.fn()],
}));

// Mock child components to keep assertions focused on routing
vi.mock("./MultiDayGrid", () => ({
  MultiDayGrid: ({ dateRange }: { dateRange: string[] }) => (
    <div data-testid="multi-day-grid" data-date-count={dateRange.length} />
  ),
}));

// BETA-B7: MonthCalendarGrid replaces MonthDeferredState in the month branch
vi.mock("./MonthCalendarGrid", () => ({
  MonthCalendarGrid: ({ dateRange }: { dateRange: string[] }) => (
    <div data-testid="month-calendar-grid" data-date-count={dateRange.length} />
  ),
}));

vi.mock("../hooks/useCheckConflicts", () => ({
  useCheckConflicts: () => ({
    mutate: vi.fn(),
    data: null,
    isPending: false,
    reset: vi.fn(),
  }),
}));

const mockTechs: DispatchBoardTech[] = [];
const mockJobs: DispatchBoardJob[] = [];
const baseProps = {
  techs: mockTechs,
  jobs: mockJobs,
  activeDate: "2026-06-10",
  onJobSelect: vi.fn(),
  onMoveJob: vi.fn(),
};

describe("DispatchGrid — view routing", () => {
  it("no viewMode prop → renders day view (not MultiDayGrid, not MonthCalendarGrid)", () => {
    render(<DispatchGrid {...baseProps} />);
    expect(screen.queryByTestId("multi-day-grid")).not.toBeInTheDocument();
    expect(screen.queryByTestId("month-calendar-grid")).not.toBeInTheDocument();
  });

  it("viewMode='day' explicitly → renders day view", () => {
    render(<DispatchGrid {...baseProps} viewMode="day" />);
    expect(screen.queryByTestId("multi-day-grid")).not.toBeInTheDocument();
    expect(screen.queryByTestId("month-calendar-grid")).not.toBeInTheDocument();
  });

  it("viewMode='week' → renders MultiDayGrid with 7 dates", () => {
    const dateRange = [
      "2026-06-10",
      "2026-06-11",
      "2026-06-12",
      "2026-06-13",
      "2026-06-14",
      "2026-06-15",
      "2026-06-16",
    ];
    render(
      <DispatchGrid {...baseProps} viewMode="week" dateRange={dateRange} />,
    );
    const grid = screen.getByTestId("multi-day-grid");
    expect(grid).toBeInTheDocument();
    expect(grid.getAttribute("data-date-count")).toBe("7");
  });

  it("viewMode='month' → renders MonthCalendarGrid (BETA-B7: replaces MonthDeferredState)", () => {
    const dateRange = Array.from({ length: 30 }, (_, i) => {
      const d = new Date("2026-06-01");
      d.setDate(d.getDate() + i);
      return d.toISOString().slice(0, 10);
    });
    render(
      <DispatchGrid {...baseProps} viewMode="month" dateRange={dateRange} />,
    );
    expect(screen.getByTestId("month-calendar-grid")).toBeInTheDocument();
    expect(screen.queryByTestId("multi-day-grid")).not.toBeInTheDocument();
    // "Month view coming soon" is no longer rendered
    expect(
      screen.queryByText("Month view coming soon"),
    ).not.toBeInTheDocument();
  });

  it("viewMode='week' without dateRange → falls back to [activeDate]", () => {
    render(<DispatchGrid {...baseProps} viewMode="week" />);
    const grid = screen.getByTestId("multi-day-grid");
    expect(grid).toBeInTheDocument();
    // Falls back to [activeDate] — 1 date panel
    expect(grid.getAttribute("data-date-count")).toBe("1");
  });
});
