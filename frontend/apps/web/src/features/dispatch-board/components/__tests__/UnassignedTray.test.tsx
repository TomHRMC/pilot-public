/**
 * UnassignedTray unit tests — DISPATCH-B1
 *
 * Tests:
 *   - renders data-testid="unassigned-tray"
 *   - shows "Unassigned (0)" + empty message when jobs.length === 0
 *   - shows chips for each job
 *   - clicking a chip calls onJobClick
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DndContext } from "@dnd-kit/core";
import { UnassignedTray } from "../UnassignedTray";
import type { DispatchBoardJob } from "../../types-stub";

const MOCK_JOBS: DispatchBoardJob[] = [
  {
    id: "job-001",
    title: "Panel upgrade",
    customer_name: "Smith Residence",
    site_address: "123 Main St",
    scheduled_start_at: "",
    scheduled_end_at: "",
    tech_id: null,
    status: "unassigned",
    priority: "standard",
    customer_type: "person",
    job_type_code: "install",
    job_type_label: "Install",
    updated_at: new Date().toISOString(),
    // B1 fields
    ...({ job_number: "JOB-001" } as unknown as Record<string, unknown>),
  } as unknown as DispatchBoardJob,
  {
    id: "job-002",
    title: "Breaker replacement",
    customer_name: "Jones Office",
    site_address: "456 Oak Ave",
    scheduled_start_at: "",
    scheduled_end_at: "",
    tech_id: null,
    status: "unassigned",
    priority: "urgent",
    customer_type: "company",
    job_type_code: "repair",
    job_type_label: "Repair",
    updated_at: new Date().toISOString(),
  } as unknown as DispatchBoardJob,
];

function renderInDndContext(ui: React.ReactElement) {
  return render(<DndContext>{ui}</DndContext>);
}

describe("UnassignedTray", () => {
  it("renders data-testid='unassigned-tray'", () => {
    renderInDndContext(<UnassignedTray jobs={[]} onJobClick={vi.fn()} />);
    expect(screen.getByTestId("unassigned-tray")).toBeInTheDocument();
  });

  it("shows 'Unassigned (0)' label when empty", () => {
    renderInDndContext(<UnassignedTray jobs={[]} onJobClick={vi.fn()} />);
    expect(screen.getByText("Unassigned (0)")).toBeInTheDocument();
  });

  it("shows italic empty message when no jobs", () => {
    renderInDndContext(<UnassignedTray jobs={[]} onJobClick={vi.fn()} />);
    expect(screen.getByText("No unassigned jobs")).toBeInTheDocument();
  });

  it("shows job count in label when jobs present", () => {
    renderInDndContext(
      <UnassignedTray jobs={MOCK_JOBS} onJobClick={vi.fn()} />,
    );
    expect(screen.getByText("Unassigned (2)")).toBeInTheDocument();
  });

  it("does NOT show empty message when jobs present", () => {
    renderInDndContext(
      <UnassignedTray jobs={MOCK_JOBS} onJobClick={vi.fn()} />,
    );
    expect(screen.queryByText("No unassigned jobs")).not.toBeInTheDocument();
  });

  it("renders a chip for each job showing customer_name", () => {
    renderInDndContext(
      <UnassignedTray jobs={MOCK_JOBS} onJobClick={vi.fn()} />,
    );
    expect(screen.getByText("Smith Residence")).toBeInTheDocument();
    expect(screen.getByText("Jones Office")).toBeInTheDocument();
  });

  it("calls onJobClick when chip is clicked", () => {
    const onJobClick = vi.fn();
    renderInDndContext(
      <UnassignedTray jobs={MOCK_JOBS} onJobClick={onJobClick} />,
    );
    // Click the first job chip's button
    const chips = screen.getAllByRole("button");
    fireEvent.click(chips[0]!);
    expect(onJobClick).toHaveBeenCalledTimes(1);
    expect(onJobClick).toHaveBeenCalledWith(MOCK_JOBS[0]);
  });
});
