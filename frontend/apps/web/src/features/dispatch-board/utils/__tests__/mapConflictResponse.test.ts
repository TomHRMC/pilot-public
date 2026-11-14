/**
 * mapConflictResponse unit tests — DISPATCH-B1
 *
 * Tests:
 *   - maps {is_feasible, conflicts[]} → ConflictPreviewPane shape
 *   - has_blocking_conflicts derivation
 *   - conflict_type → conflict_class/severity mapping
 */

import { describe, it, expect } from "vitest";
import {
  mapConflictResponse,
  type RawCheckConflictsResponse,
} from "../mapConflictResponse";

describe("mapConflictResponse", () => {
  it("maps empty conflicts → no conflicts, has_blocking_conflicts=false", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: true,
      conflicts: [],
    };
    const result = mapConflictResponse(raw);
    expect(result.conflicts).toHaveLength(0);
    expect(result.has_blocking_conflicts).toBe(false);
  });

  it("maps double_booking conflict_type → conflict_class='overlap', severity='warn'", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: false,
      conflicts: [
        {
          conflict_type: "double_booking",
          description: "Tech already has a job at this time",
          affected_job_id: "job-existing-001",
        },
      ],
    };
    const result = mapConflictResponse(raw);
    expect(result.conflicts).toHaveLength(1);
    expect(result.conflicts[0]?.conflict_class).toBe("overlap");
    expect(result.conflicts[0]?.severity).toBe("warn");
  });

  it("maps availability_block → conflict_class='availability', severity='warn'", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: false,
      conflicts: [
        {
          conflict_type: "availability_block",
          description: "Tech has PTO",
        },
      ],
    };
    const result = mapConflictResponse(raw);
    expect(result.conflicts[0]?.conflict_class).toBe("availability");
    expect(result.conflicts[0]?.severity).toBe("warn");
  });

  it("maps drive_time → conflict_class='travel', severity='warn'", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: false,
      conflicts: [
        {
          conflict_type: "drive_time",
          description: "Not enough drive time",
        },
      ],
    };
    const result = mapConflictResponse(raw);
    expect(result.conflicts[0]?.conflict_class).toBe("travel");
    expect(result.conflicts[0]?.severity).toBe("warn");
  });

  it("maps drive_time_warning → conflict_class='travel', severity='warn'", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: true,
      conflicts: [
        {
          conflict_type: "drive_time_warning",
          description: "Drive time is tight",
        },
      ],
    };
    const result = mapConflictResponse(raw);
    expect(result.conflicts[0]?.conflict_class).toBe("travel");
    expect(result.conflicts[0]?.severity).toBe("warn");
  });

  it("derives has_blocking_conflicts=true when !is_feasible and drive_time conflict present", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: false,
      conflicts: [{ conflict_type: "drive_time", description: "Hard block" }],
    };
    const result = mapConflictResponse(raw);
    expect(result.has_blocking_conflicts).toBe(true);
  });

  it("derives has_blocking_conflicts=false when !is_feasible but no drive_time conflict", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: false,
      conflicts: [{ conflict_type: "double_booking", description: "Overlap" }],
    };
    const result = mapConflictResponse(raw);
    expect(result.has_blocking_conflicts).toBe(false);
  });

  it("derives has_blocking_conflicts=false when is_feasible=true even with conflicts", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: true,
      conflicts: [
        { conflict_type: "drive_time_warning", description: "Warning" },
      ],
    };
    const result = mapConflictResponse(raw);
    expect(result.has_blocking_conflicts).toBe(false);
  });

  it("preserves affected_job_id and suggested_resolution", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: true,
      conflicts: [
        {
          conflict_type: "double_booking",
          affected_job_id: "job-abc",
          suggested_resolution: "Move to later slot",
        },
      ],
    };
    const result = mapConflictResponse(raw);
    expect(result.conflicts[0]?.affected_job_id).toBe("job-abc");
    expect(result.conflicts[0]?.suggested_resolution).toBe(
      "Move to later slot",
    );
  });

  it("maps unknown conflict_type → conflict_class='info', severity='info'", () => {
    const raw: RawCheckConflictsResponse = {
      is_feasible: true,
      conflicts: [{ conflict_type: "unknown_future_type" }],
    };
    const result = mapConflictResponse(raw);
    expect(result.conflicts[0]?.conflict_class).toBe("info");
    expect(result.conflicts[0]?.severity).toBe("info");
  });
});
