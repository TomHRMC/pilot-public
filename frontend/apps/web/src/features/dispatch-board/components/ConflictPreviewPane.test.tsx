/**
 * ConflictPreviewPane — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/components/ConflictPreviewPane.test.tsx
 * Per batch-fe-b4-design.md §I.1
 * Target: 6 tests
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { ConflictPreviewPane } from "./ConflictPreviewPane";
import type { CheckConflictsResponse } from "../types-stub";

const noConflicts: CheckConflictsResponse = {
  conflicts: [],
  has_blocking_conflicts: false,
};

const withOverlapConflict: CheckConflictsResponse = {
  conflicts: [
    {
      conflict_class: "overlap",
      severity: "warn",
      detail: { overlapping_job_title: "Other job" },
      affected_job_id: "job-2",
      suggested_resolution: "Choose a different time slot.",
    },
  ],
  has_blocking_conflicts: false,
};

const withInfoConflict: CheckConflictsResponse = {
  conflicts: [
    {
      conflict_class: "info",
      severity: "info",
      detail: {},
      affected_job_id: "job-3",
      suggested_resolution: null,
    },
  ],
  has_blocking_conflicts: false,
};

describe("ConflictPreviewPane", () => {
  it("shows 'No conflicts' when conflicts array is empty", () => {
    render(
      <ConflictPreviewPane
        conflicts={noConflicts}
        onProceed={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("No conflicts")).toBeInTheDocument();
  });

  it("shows 'overlap' conflict with red badge", () => {
    render(
      <ConflictPreviewPane
        conflicts={withOverlapConflict}
        onProceed={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Overlap")).toBeInTheDocument();
  });

  it("shows 'info' conflict with note badge", () => {
    render(
      <ConflictPreviewPane
        conflicts={withInfoConflict}
        onProceed={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Note")).toBeInTheDocument();
  });

  it("shows 'Move anyway' for warn conflicts", () => {
    render(
      <ConflictPreviewPane
        conflicts={withOverlapConflict}
        onProceed={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/Move anyway/i)).toBeInTheDocument();
  });

  it("calls onProceed when confirm clicked", () => {
    const onProceed = vi.fn();
    render(
      <ConflictPreviewPane
        conflicts={noConflicts}
        onProceed={onProceed}
        onCancel={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Confirm move"));
    expect(onProceed).toHaveBeenCalledOnce();
  });

  it("calls onCancel when Cancel clicked", () => {
    const onCancel = vi.fn();
    render(
      <ConflictPreviewPane
        conflicts={noConflicts}
        onProceed={vi.fn()}
        onCancel={onCancel}
      />,
    );
    const cancelButtons = screen.getAllByText("Cancel");
    fireEvent.click(cancelButtons[0]);
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("shows loading state", () => {
    render(
      <ConflictPreviewPane
        conflicts={null}
        isLoading={true}
        onProceed={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Checking conflicts…")).toBeInTheDocument();
  });
});
