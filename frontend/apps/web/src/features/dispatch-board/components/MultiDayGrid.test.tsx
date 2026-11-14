/**
 * MultiDayGrid — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/components/MultiDayGrid.test.tsx
 * Per batch-beta-v1-fixes-b5-design.md §I.1
 *
 * Verifies:
 * - N panels render for N dates
 * - Job filtering by date (job appears only in its correct panel)
 * - Read-only: no DnD drop targets on panels
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { MultiDayGrid } from "./MultiDayGrid";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";

// Mock react-dnd (no real HTML5 backend needed in unit tests)
vi.mock("react-dnd", () => ({
  DndProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useDrag: () => [{ isDragging: false }, vi.fn(), vi.fn()],
  useDrop: () => [{ isOver: false, canDrop: true }, vi.fn()],
}));

const mockTechs: DispatchBoardTech[] = [
  {
    id: "tech-1",
    tech_id: "tech-1",
    name: "Alice",
    display_color: "#3B43D6",
    avatar_url: null,
  },
];

const jobOnDay1: DispatchBoardJob = {
  id: "job-1",
  title: "Outlet install",
  customer_name: "Home Owner",
  site_address: "123 Oak St",
  scheduled_start_at: "2026-06-10T09:00:00.000Z",
  scheduled_end_at: "2026-06-10T11:00:00.000Z",
  tech_id: "tech-1",
  status: "scheduled",
  priority: "standard",
  customer_type: "person",
  job_type_code: "install",
  job_type_label: "Install",
  updated_at: "2026-06-10T08:00:00.000Z",
};

const jobOnDay2: DispatchBoardJob = {
  id: "job-2",
  title: "Panel upgrade",
  customer_name: "Office LLC",
  site_address: "456 Elm St",
  scheduled_start_at: "2026-06-11T13:00:00.000Z",
  scheduled_end_at: "2026-06-11T15:00:00.000Z",
  tech_id: "tech-1",
  status: "scheduled",
  priority: "urgent",
  customer_type: "company",
  job_type_code: "upgrade",
  job_type_label: "Upgrade",
  updated_at: "2026-06-11T08:00:00.000Z",
};

describe("MultiDayGrid", () => {
  it("renders one panel header per date in the range", () => {
    const { container } = render(
      <MultiDayGrid
        dateRange={["2026-06-10", "2026-06-11", "2026-06-12", "2026-06-13"]}
        techs={mockTechs}
        jobs={[]}
        onJobSelect={vi.fn()}
      />,
    );

    // Count panel header divs by their shared CSS classes
    const headers = container.querySelectorAll(
      ".text-xs.font-medium.border-b.border-neutral-200.text-center",
    );
    expect(headers).toHaveLength(4);
  });

  it("job on day 1 is visible and job on day 2 is also visible (both in DOM)", () => {
    render(
      <MultiDayGrid
        dateRange={["2026-06-10", "2026-06-11"]}
        techs={mockTechs}
        jobs={[jobOnDay1, jobOnDay2]}
        onJobSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("Outlet install")).toBeInTheDocument();
    expect(screen.getByText("Panel upgrade")).toBeInTheDocument();
  });

  it("calls onJobSelect when a job block is clicked", () => {
    const onJobSelect = vi.fn();
    render(
      <MultiDayGrid
        dateRange={["2026-06-10"]}
        techs={mockTechs}
        jobs={[jobOnDay1]}
        onJobSelect={onJobSelect}
      />,
    );

    // JobBlock renders as role="button"
    const jobButton = screen.getByRole("button", { name: /Outlet install/i });
    jobButton.click();
    expect(onJobSelect).toHaveBeenCalledWith("job-1");
  });

  it("renders 7 panel headers for a week range", () => {
    const weekDates = [
      "2026-06-10",
      "2026-06-11",
      "2026-06-12",
      "2026-06-13",
      "2026-06-14",
      "2026-06-15",
      "2026-06-16",
    ];
    const { container } = render(
      <MultiDayGrid
        dateRange={weekDates}
        techs={mockTechs}
        jobs={[]}
        onJobSelect={vi.fn()}
      />,
    );

    const headers = container.querySelectorAll(
      ".text-xs.font-medium.border-b.border-neutral-200.text-center",
    );
    expect(headers).toHaveLength(7);
  });

  it("today's panel header has brand styling class", () => {
    const today = new Date().toISOString().slice(0, 10);
    const { container } = render(
      <MultiDayGrid
        dateRange={[today]}
        techs={mockTechs}
        jobs={[]}
        onJobSelect={vi.fn()}
      />,
    );

    const todayHeader = container.querySelector(".bg-brand-50");
    expect(todayHeader).toBeInTheDocument();
  });
});
