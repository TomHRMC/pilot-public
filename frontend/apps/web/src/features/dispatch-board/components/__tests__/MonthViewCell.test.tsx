/**
 * MonthViewCell — Unit Tests (BETA-B7)
 *
 * Location: apps/web/src/features/dispatch-board/components/__tests__/MonthViewCell.test.tsx
 * Per batch-beta-v1-fixes-b7-design.md §J.3
 * Updated FE-B30: max chips changed from 3 to 2; chips show customer_name (customer mode default)
 *
 * Tests:
 * 1. Renders date number for in-range cell
 * 2. Today cell has brand highlight class
 * 3. Renders up to 2 job chips; 3+ jobs → 2 chips + "+N more" (FE-B30: 3→2 max)
 * 4. Padding cell (null dateStr) renders nothing interactive
 * 5. Out-of-range cell is not interactive
 * 6. Click on in-range cell calls onDrillDown with dateStr
 * 7. Click on padding cell does NOT call onDrillDown
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { MonthViewCell } from "../MonthViewCell";
import type { DispatchBoardJob } from "../../types-stub";

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

const DATE_STR = "2026-06-15";

describe("MonthViewCell — Unit Tests (BETA-B7 §J.3)", () => {
  it("renders date number for in-range cell", () => {
    render(
      <MonthViewCell
        dateStr={DATE_STR}
        jobs={[]}
        isToday={false}
        isInRange
        onDrillDown={vi.fn()}
      />,
    );
    // Day 15 — leading zero stripped
    expect(screen.getByText("15")).toBeInTheDocument();
  });

  it("today cell has bg-brand-600 class wrapping the date number", () => {
    render(
      <MonthViewCell
        dateStr={DATE_STR}
        jobs={[]}
        isToday
        isInRange
        onDrillDown={vi.fn()}
      />,
    );
    const todayBadge = screen.getByText("15");
    expect(todayBadge).toHaveClass("bg-brand-600");
    expect(todayBadge).toHaveClass("text-white");
    expect(todayBadge).toHaveClass("rounded-full");
  });

  it("renders up to 2 job chips (FE-B30: max reduced from 3 to 2)", () => {
    // FE-B30: max chips = 2. With 3 jobs, show 2 chips + "+1 more"
    const jobs = [
      makeJob("a", DATE_STR, "Acme Corp"),
      makeJob("b", DATE_STR, "Beta LLC"),
      makeJob("c", DATE_STR, "Gamma Inc"),
    ];
    render(
      <MonthViewCell
        dateStr={DATE_STR}
        jobs={jobs}
        isToday={false}
        isInRange
        onDrillDown={vi.fn()}
      />,
    );
    // Chips show customer_name in customer mode (default)
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("Beta LLC")).toBeInTheDocument();
    // Third chip overflows — not visible as chip
    expect(screen.queryByText("Gamma Inc")).not.toBeInTheDocument();
    expect(screen.getByText("+1 more")).toBeInTheDocument();
  });

  it("renders 2 chips + '+N more' when jobs.length > 2 (FE-B30)", () => {
    // FE-B30: 4 jobs → 2 chips + "+2 more"
    const jobs = [
      makeJob("a", DATE_STR, "Alpha Co"),
      makeJob("b", DATE_STR, "Beta Co"),
      makeJob("c", DATE_STR, "Gamma Co"),
      makeJob("d", DATE_STR, "Delta Co"),
    ];
    render(
      <MonthViewCell
        dateStr={DATE_STR}
        jobs={jobs}
        isToday={false}
        isInRange
        onDrillDown={vi.fn()}
      />,
    );
    expect(screen.getByText("Alpha Co")).toBeInTheDocument();
    expect(screen.getByText("Beta Co")).toBeInTheDocument();
    expect(screen.queryByText("Gamma Co")).not.toBeInTheDocument();
    expect(screen.queryByText("Delta Co")).not.toBeInTheDocument();
    expect(screen.getByText("+2 more")).toBeInTheDocument();
  });

  it("padding cell (dateStr=null) renders nothing interactive (aria-hidden)", () => {
    const { container } = render(
      <MonthViewCell
        dateStr={null}
        jobs={[]}
        isToday={false}
        isInRange={false}
        onDrillDown={vi.fn()}
      />,
    );
    const cell = container.firstChild as HTMLElement;
    expect(cell).toHaveAttribute("aria-hidden", "true");
    // No date number or job chips
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("out-of-range cell (isInRange=false) is not interactive", () => {
    const { container } = render(
      <MonthViewCell
        dateStr={DATE_STR}
        jobs={[]}
        isToday={false}
        isInRange={false}
        onDrillDown={vi.fn()}
      />,
    );
    const cell = container.firstChild as HTMLElement;
    expect(cell).toHaveAttribute("aria-hidden", "true");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("click on in-range cell calls onDrillDown with dateStr", () => {
    const onDrillDown = vi.fn();
    render(
      <MonthViewCell
        dateStr={DATE_STR}
        jobs={[]}
        isToday={false}
        isInRange
        onDrillDown={onDrillDown}
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(onDrillDown).toHaveBeenCalledWith(DATE_STR);
    expect(onDrillDown).toHaveBeenCalledTimes(1);
  });

  it("click on padding cell (null dateStr) does NOT call onDrillDown", () => {
    const onDrillDown = vi.fn();
    const { container } = render(
      <MonthViewCell
        dateStr={null}
        jobs={[]}
        isToday={false}
        isInRange={false}
        onDrillDown={onDrillDown}
      />,
    );
    // Click the padding cell element directly
    fireEvent.click(container.firstChild as HTMLElement);
    expect(onDrillDown).not.toHaveBeenCalled();
  });
});
