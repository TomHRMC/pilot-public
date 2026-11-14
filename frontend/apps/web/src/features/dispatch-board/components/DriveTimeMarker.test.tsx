/**
 * DriveTimeMarker — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/components/DriveTimeMarker.test.tsx
 * Per batch-fe-b4-design.md §I.1
 * Target: 5 tests
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { DriveTimeMarker } from "./DriveTimeMarker";
import type { DriveTimeSegment } from "../types-stub";

const normalSegment: DriveTimeSegment = {
  from_job_id: "job-1",
  to_job_id: "job-2",
  drive_time_seconds: 900, // 15 min
  drive_distance_meters: 5000,
  is_feasible: true,
  cached: false,
};

const infeasibleSegment: DriveTimeSegment = {
  ...normalSegment,
  drive_time_seconds: 4500, // 75 min — exceeds any reasonable gap
  is_feasible: false,
};

describe("DriveTimeMarker", () => {
  it("renders drive time in minutes for normal segment", () => {
    render(
      <DriveTimeMarker segment={normalSegment} topPx={100} gapSeconds={3600} />,
    );
    expect(screen.getByText(/15 min/i)).toBeInTheDocument();
  });

  it("shows 'Infeasible' for infeasible drive time", () => {
    render(
      <DriveTimeMarker
        segment={infeasibleSegment}
        topPx={100}
        gapSeconds={1800}
      />,
    );
    expect(screen.getByText(/Infeasible/i)).toBeInTheDocument();
  });

  it("shows 'Tight' when drive time > 80% of gap", () => {
    render(
      <DriveTimeMarker
        segment={{ ...normalSegment, drive_time_seconds: 2800 }}
        topPx={100}
        gapSeconds={3000} // 2800 > 3000 * 0.8 = 2400
      />,
    );
    expect(screen.getByText(/Tight/i)).toBeInTheDocument();
  });

  it("shows loading placeholder when isLoading=true", () => {
    render(
      <DriveTimeMarker
        segment={null}
        topPx={100}
        gapSeconds={3600}
        isLoading={true}
      />,
    );
    // Loading shows "…" placeholder
    expect(screen.getByText(/🚗/)).toBeInTheDocument();
  });

  it("shows unavailable placeholder when isUnavailable=true", () => {
    render(
      <DriveTimeMarker
        segment={null}
        topPx={100}
        gapSeconds={3600}
        isUnavailable={true}
      />,
    );
    expect(screen.getByText(/–/)).toBeInTheDocument();
  });
});
