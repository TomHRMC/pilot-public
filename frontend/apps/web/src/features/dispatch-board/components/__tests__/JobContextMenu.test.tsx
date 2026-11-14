/**
 * JobContextMenu unit tests — DISPATCH-B1
 *
 * Tests:
 *   - renders 2 menu items at cursor position when state is provided
 *   - closes on Escape key
 *   - closes on click outside
 *   - returns null when state is null
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { JobContextMenu } from "../JobContextMenu";
import type { ScheduledJob } from "../DispatchBoardLanes";

const MOCK_JOB: ScheduledJob = {
  id: "job-001",
  title: "Panel upgrade",
  customer_name: "Smith Residence",
  site_address: "123 Main St",
  scheduled_start_at: "2026-07-28T09:00:00.000Z",
  scheduled_end_at: "2026-07-28T12:00:00.000Z",
  tech_id: "tech-001",
  status: "scheduled",
  priority: "standard",
  customer_type: "person",
  job_type_code: "install",
  job_type_label: "Install",
  updated_at: new Date().toISOString(),
} as unknown as ScheduledJob;

describe("JobContextMenu", () => {
  it("renders nothing when state is null", () => {
    const { container } = render(
      <JobContextMenu
        state={null}
        onClose={vi.fn()}
        onViewJob={vi.fn()}
        onJobProperties={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders 2 menu items when state is provided", () => {
    render(
      <JobContextMenu
        state={{ x: 100, y: 200, job: MOCK_JOB }}
        onClose={vi.fn()}
        onViewJob={vi.fn()}
        onJobProperties={vi.fn()}
      />,
    );
    expect(screen.getByText("View Job")).toBeInTheDocument();
    expect(screen.getByText("Job Properties")).toBeInTheDocument();
  });

  it("renders at fixed position (role=menu)", () => {
    render(
      <JobContextMenu
        state={{ x: 150, y: 300, job: MOCK_JOB }}
        onClose={vi.fn()}
        onViewJob={vi.fn()}
        onJobProperties={vi.fn()}
      />,
    );
    const menu = screen.getByRole("menu");
    expect(menu).toBeInTheDocument();
    expect(menu).toHaveAttribute("aria-label", "Job options");
  });

  it("calls onClose + onViewJob when View Job is clicked", () => {
    const onClose = vi.fn();
    const onViewJob = vi.fn();
    render(
      <JobContextMenu
        state={{ x: 100, y: 200, job: MOCK_JOB }}
        onClose={onClose}
        onViewJob={onViewJob}
        onJobProperties={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("View Job"));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onViewJob).toHaveBeenCalledWith(MOCK_JOB);
  });

  it("calls onClose + onJobProperties when Job Properties is clicked", () => {
    const onClose = vi.fn();
    const onJobProperties = vi.fn();
    render(
      <JobContextMenu
        state={{ x: 100, y: 200, job: MOCK_JOB }}
        onClose={onClose}
        onViewJob={vi.fn()}
        onJobProperties={onJobProperties}
      />,
    );
    fireEvent.click(screen.getByText("Job Properties"));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onJobProperties).toHaveBeenCalledWith(MOCK_JOB);
  });

  it("calls onClose when Escape key is pressed", () => {
    const onClose = vi.fn();
    render(
      <JobContextMenu
        state={{ x: 100, y: 200, job: MOCK_JOB }}
        onClose={onClose}
        onViewJob={vi.fn()}
        onJobProperties={vi.fn()}
      />,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when clicking outside the menu", () => {
    const onClose = vi.fn();
    render(
      <div>
        <div data-testid="outside">outside</div>
        <JobContextMenu
          state={{ x: 100, y: 200, job: MOCK_JOB }}
          onClose={onClose}
          onViewJob={vi.fn()}
          onJobProperties={vi.fn()}
        />
      </div>,
    );
    fireEvent.mouseDown(screen.getByTestId("outside"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
