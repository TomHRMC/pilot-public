/**
 * mapConflictResponse — Adapter from real /check-conflicts response to ConflictPreviewPane shape
 *
 * Location: apps/web/src/features/dispatch-board/utils/mapConflictResponse.ts
 *
 * The backend returns:
 *   { is_feasible, conflicts: [{conflict_type, description, ...}], drive_time_to_next_minutes?, drive_time_from_prev_minutes? }
 *
 * ConflictPreviewPane expects:
 *   { conflicts: [{conflict_class, severity, detail, affected_job_id, suggested_resolution}], has_blocking_conflicts }
 *
 * Conflict type values from scheduling_service.py check_slot_feasibility:
 *   - "availability_block" → tech has PTO/unavailable block
 *   - "double_booking"     → tech already has an overlapping job
 *   - "drive_time_warning" → drive time is tight (warning, not hard block)
 *   - "drive_time"         → hard drive time conflict (is_feasible=false)
 *
 * MVP is warn-only per §13.4 — all conflicts show as warn; nothing hard-blocks the proceed button
 * except when is_feasible === false.
 *
 * Per DISPATCH-B1 design doc §D.3
 */

import type { CheckConflictsResponse, SchedulingConflict } from "../types-stub";

/** Raw conflict dict as returned by /check-conflicts */
export interface RawConflict {
  conflict_type: string;
  description?: string;
  detail?: Record<string, unknown>;
  affected_job_id?: string | null;
  suggested_resolution?: string | null;
  drive_time_minutes?: number | null;
}

/** Raw response shape from POST /api/v1/scheduling/jobs/{id}/check-conflicts */
export interface RawCheckConflictsResponse {
  is_feasible: boolean;
  conflicts: RawConflict[];
  drive_time_to_next_minutes?: number | null;
  drive_time_from_prev_minutes?: number | null;
}

/**
 * Map a raw backend conflict_type → ConflictPreviewPane conflict_class
 *
 * conflict_class values accepted by ConflictItem:
 *   "overlap" | "availability" | "travel" | "info"
 */
function mapConflictClass(
  conflictType: string,
): SchedulingConflict["conflict_class"] {
  switch (conflictType) {
    case "double_booking":
      return "overlap";
    case "availability_block":
      return "availability";
    case "drive_time":
    case "drive_time_warning":
      return "travel";
    default:
      return "info";
  }
}

/**
 * Map a raw backend conflict_type → severity.
 * MVP is warn-only (§13.4) — no hard "block" in the UI. "drive_time" makes
 * is_feasible=false which disables the proceed button, but the class is still "warn".
 */
function mapSeverity(conflictType: string): SchedulingConflict["severity"] {
  switch (conflictType) {
    case "double_booking":
    case "availability_block":
    case "drive_time":
    case "drive_time_warning":
      return "warn";
    default:
      return "info";
  }
}

/**
 * Adapt the raw /check-conflicts response to the shape ConflictPreviewPane consumes.
 *
 * has_blocking_conflicts derivation:
 *   !is_feasible && conflicts has at least one "drive_time" type.
 *   Per design doc §D.3 — MVP uses is_feasible as the blocking gate.
 */
export function mapConflictResponse(
  raw: RawCheckConflictsResponse,
): CheckConflictsResponse {
  const mappedConflicts: SchedulingConflict[] = raw.conflicts.map((c) => ({
    conflict_class: mapConflictClass(c.conflict_type),
    severity: mapSeverity(c.conflict_type),
    detail: {
      ...(c.detail ?? {}),
      conflict_type: c.conflict_type,
      description: c.description ?? "",
    },
    affected_job_id: c.affected_job_id ?? "",
    suggested_resolution: c.suggested_resolution ?? null,
  }));

  const has_blocking_conflicts =
    !raw.is_feasible &&
    raw.conflicts.some((c) => c.conflict_type === "drive_time");

  return {
    conflicts: mappedConflicts,
    has_blocking_conflicts,
  };
}
