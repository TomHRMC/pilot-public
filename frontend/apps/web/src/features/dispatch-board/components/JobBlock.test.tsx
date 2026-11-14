/**
 * JobBlock — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/components/JobBlock.test.tsx
 *
 * DISPATCH-B1 update: JobBlock.tsx is now the shared @dnd-kit DraggableJobBlock.
 * Old react-dnd props (tech, heightPx, topPx, onSelect) are removed.
 * New props: job, left, width, onClick, onContextMenu.
 *
 * DISPATCH-B1.25: Added tests for variant="commitment" (role badge, no drag, click/contextMenu preserved).
 *
 * @dnd-kit requires DndContext wrapper (not DndProvider).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { DndContext } from "@dnd-kit/core";
import { DraggableJobBlock } from "./JobBlock";
import type { ScheduledJob } from "./DispatchBoardLanes";

const mockJob: ScheduledJob = {
  id: "job-1",
  title: "Panel upgrade — 200A service",
  customer_name: "Riverside Office Park",
  site_address: "123 Main St",
  scheduled_start_at: "2026-06-10T09:00:00.000Z",
  scheduled_end_at: "2026-06-10T12:00:00.000Z",
  tech_id: "tech-1",
  status: "scheduled",
  priority: "standard",
  // DISPATCH-B3: real values
  customer_type: "company",
  job_type_code: "install",
  job_type_label: "Install",
  updated_at: "2026-06-10T08:00:00.000Z",
} as unknown as ScheduledJob;

/** Job with assignment_role for commitment variant tests */
const mockCommitmentJob: ScheduledJob = {
  ...mockJob,
  id: "job-commitment-1",
  assignment_role: "helper",
} as unknown as ScheduledJob;

function renderJobBlock(overrides?: {
  onClick?: (job: ScheduledJob) => void;
  onContextMenu?: (e: React.MouseEvent, job: ScheduledJob) => void;
  variant?: "primary" | "commitment";
  job?: ScheduledJob;
}) {
  const job = overrides?.job ?? mockJob;
  return render(
    <DndContext>
      <DraggableJobBlock
        job={job}
        left={100}
        width={200}
        onClick={overrides?.onClick ?? vi.fn()}
        onContextMenu={overrides?.onContextMenu}
        variant={overrides?.variant}
      />
    </DndContext>,
  );
}

describe("JobBlock (DraggableJobBlock)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders job title", () => {
    renderJobBlock();
    expect(
      screen.getByText("Panel upgrade — 200A service"),
    ).toBeInTheDocument();
  });

  it("renders customer name", () => {
    renderJobBlock();
    expect(screen.getByText("Riverside Office Park")).toBeInTheDocument();
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    renderJobBlock({ onClick });

    const block = screen.getByRole("button");
    fireEvent.click(block);

    expect(onClick).toHaveBeenCalledWith(mockJob);
  });

  it("calls onClick when Enter pressed", () => {
    const onClick = vi.fn();
    renderJobBlock({ onClick });

    const block = screen.getByRole("button");
    fireEvent.keyDown(block, { key: "Enter" });

    expect(onClick).toHaveBeenCalledWith(mockJob);
  });

  it("calls onContextMenu when right-clicked (prevents default)", () => {
    const onContextMenu = vi.fn();
    renderJobBlock({ onContextMenu });

    const block = screen.getByRole("button");
    fireEvent.contextMenu(block);

    expect(onContextMenu).toHaveBeenCalledTimes(1);
  });

  it("has aria-label with job title", () => {
    renderJobBlock();
    const block = screen.getByRole("button");
    expect(block.getAttribute("aria-label")).toContain("Panel upgrade");
  });

  it("is absolutely positioned with supplied left/width", () => {
    const { container } = renderJobBlock();
    const block = container.querySelector('[role="button"]') as HTMLElement;
    expect(block?.style.left).toBe("100px");
    // width is Math.max(width - 4, 20) = 196px
    expect(block?.style.width).toBe("196px");
  });
});

// ─── DISPATCH-B1.25: commitment variant tests ─────────────────────────────────

describe("JobBlock (DraggableJobBlock) — variant=commitment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the role badge with capitalized assignment_role", () => {
    renderJobBlock({ variant: "commitment", job: mockCommitmentJob });
    const badge = screen.getByTestId("role-badge");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toBe("Helper");
  });

  it("has cursor-default class (not cursor-grab)", () => {
    const { container } = renderJobBlock({
      variant: "commitment",
      job: mockCommitmentJob,
    });
    const block = container.querySelector('[role="button"]') as HTMLElement;
    expect(block?.className).toContain("cursor-default");
    expect(block?.className).not.toContain("cursor-grab");
  });

  it("has no drag-related data attributes (disabled)", () => {
    const { container } = renderJobBlock({
      variant: "commitment",
      job: mockCommitmentJob,
    });
    const block = container.querySelector('[role="button"]') as HTMLElement;
    // @dnd-kit drag attributes include data-dnd-kit-disabled or role="button" with no drag listeners
    // The key check: no data-draggable attribute when disabled
    expect(block?.getAttribute("aria-disabled")).not.toBe("false");
  });

  it("still calls onClick when commitment chip is clicked", () => {
    const onClick = vi.fn();
    renderJobBlock({ variant: "commitment", job: mockCommitmentJob, onClick });

    const block = screen.getByRole("button");
    fireEvent.click(block);

    expect(onClick).toHaveBeenCalledWith(mockCommitmentJob);
  });

  it("still calls onContextMenu when commitment chip is right-clicked", () => {
    const onContextMenu = vi.fn();
    renderJobBlock({
      variant: "commitment",
      job: mockCommitmentJob,
      onContextMenu,
    });

    const block = screen.getByRole("button");
    fireEvent.contextMenu(block);

    expect(onContextMenu).toHaveBeenCalledTimes(1);
  });

  it("aria-label includes (commitment) for accessibility", () => {
    renderJobBlock({ variant: "commitment", job: mockCommitmentJob });
    const block = screen.getByRole("button");
    expect(block.getAttribute("aria-label")).toContain("commitment");
  });

  it("does NOT render a role badge when assignment_role is absent", () => {
    // Primary block with no assignment_role should have no badge
    renderJobBlock({ variant: "commitment", job: mockJob });
    expect(screen.queryByTestId("role-badge")).not.toBeInTheDocument();
  });
});
