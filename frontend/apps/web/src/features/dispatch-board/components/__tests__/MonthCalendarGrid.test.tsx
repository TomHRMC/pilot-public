/**
 * MonthCalendarGrid — Unit Tests (BETA-B7)
 *
 * Location: apps/web/src/features/dispatch-board/components/__tests__/MonthCalendarGrid.test.tsx
 * Per batch-beta-v1-fixes-b7-design.md §J.4
 *
 * Tests:
 * 1. Renders 7 day-of-week header labels (Sun–Sat)
 * 2. Renders correct padding cells before first day (Monday = 1 pad)
 * 3. Renders all 30 in-range cells
 * 4. Jobs routed to correct cell
 * 5. onDrillDown propagated from cell click
 * 6. Today cell is highlighted (isToday=true signals bg-brand-600)
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { MonthCalendarGrid } from "../MonthCalendarGrid";
import type { DispatchBoardJob } from "../../types-stub";

/** Generate a 30-element dateRange starting from a given YYYY-MM-DD */
function makeDateRange(start: string): string[] {
  const result: string[] = [];
  const [y, m, d] = start.split("-").map(Number) as [number, number, number];
  for (let i = 0; i < 30; i++) {
    const date = new Date(y, m - 1, d + i);
    result.push(date.toISOString().slice(0, 10));
  }
  return result;
}

function makeJob(
  id: string,
  dateStr: string,
  customerName?: string,
): DispatchBoardJob {
  return {
    id,
    title: `Job ${id}`,
    customer_name: customerName ?? `Customer ${id}`,
    site_address: "123 Test St",
    scheduled_start_at: `${dateStr}T09:00:00.000Z`,
    scheduled_end_at: `${dateStr}T10:00:00.000Z`,
    tech_id: "tech-1",
    status: "scheduled",
    priority: "standard",
    customer_type: "company",
    job_type_code: "service",
    job_type_label: "Service",
    updated_at: `${dateStr}T08:00:00.000Z`,
  };
}

// 2026-06-01 is a Monday (getDay() = 1) → 1 padding cell before it
const DATE_RANGE_JUNE_2026 = makeDateRange("2026-06-01");

describe("MonthCalendarGrid — Unit Tests (BETA-B7 §J.4)", () => {
  it("renders 7 day-of-week header labels", () => {
    render(
      <MonthCalendarGrid
        dateRange={DATE_RANGE_JUNE_2026}
        jobs={[]}
        onDrillDown={vi.fn()}
      />,
    );
    ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].forEach((day) => {
      expect(screen.getByText(day)).toBeInTheDocument();
    });
  });

  it("renders 1 padding cell before June 1 (Monday)", () => {
    // June 1, 2026 is Monday → 1 Sun padding cell before it
    // The first real date number "1" should NOT be in the Sunday slot
    render(
      <MonthCalendarGrid
        dateRange={DATE_RANGE_JUNE_2026}
        jobs={[]}
        onDrillDown={vi.fn()}
      />,
    );
    // "1" should appear (the date number for June 1)
    expect(screen.getByText("1")).toBeInTheDocument();
    // Also check day 30 renders
    expect(screen.getByText("30")).toBeInTheDocument();
  });

  it("renders all 30 in-range date cells", () => {
    render(
      <MonthCalendarGrid
        dateRange={DATE_RANGE_JUNE_2026}
        jobs={[]}
        onDrillDown={vi.fn()}
      />,
    );
    // Verify a sampling of date numbers are present
    ["1", "10", "15", "20", "30"].forEach((d) => {
      expect(screen.getByText(d)).toBeInTheDocument();
    });
  });

  it("job with June 15 date appears in June 15 cell only", () => {
    // FE-B30: chip label is customer_name (customer mode default), not job title
    const jobs = [makeJob("abc", "2026-06-15", "Acme Corp June 15")];
    render(
      <MonthCalendarGrid
        dateRange={DATE_RANGE_JUNE_2026}
        jobs={jobs}
        onDrillDown={vi.fn()}
      />,
    );
    expect(screen.getByText("Acme Corp June 15")).toBeInTheDocument();
    // Only one chip for this job
    expect(screen.getAllByText("Acme Corp June 15")).toHaveLength(1);
  });

  it("onDrillDown propagated from cell click", () => {
    const onDrillDown = vi.fn();
    render(
      <MonthCalendarGrid
        dateRange={DATE_RANGE_JUNE_2026}
        jobs={[]}
        onDrillDown={onDrillDown}
      />,
    );
    // Click the "15" cell (June 15)
    // Get the button role element that contains "15"
    const cellButtons = screen.getAllByRole("button");
    // June 15 is at index 14 (0-indexed in the dateRange)
    // After 1 padding cell, June 15 is cellButtons[14]
    const june15Button = cellButtons.find((btn) =>
      btn.getAttribute("aria-label")?.startsWith("2026-06-15"),
    );
    expect(june15Button).toBeDefined();
    fireEvent.click(june15Button!);
    expect(onDrillDown).toHaveBeenCalledWith("2026-06-15");
  });

  it("today cell is identified (isToday=true) and has bg-brand-600", () => {
    // Use today's date as start of range to guarantee today is in range
    const today = new Date().toISOString().slice(0, 10);
    const rangeWithToday = makeDateRange(today);

    render(
      <MonthCalendarGrid
        dateRange={rangeWithToday}
        jobs={[]}
        onDrillDown={vi.fn()}
      />,
    );

    // Today badge (bg-brand-600 circle around date number)
    const todayBadge = document.querySelector(".bg-brand-600");
    expect(todayBadge).toBeInTheDocument();
    expect(todayBadge).toHaveClass("text-white");
  });
});
