/**
 * Dispatch Board — TypeScript Type Stubs (BE-B3 Not Yet In openapi.json)
 *
 * Location: apps/web/src/features/dispatch-board/types-stub.ts
 *
 * DELETE this file once `pnpm sync-api-types` delivers BE-B3 types.
 * Per batch-fe-b4-design.md §D.4
 *
 * These stubs bridge until BE-B3 endpoints land in openapi.json.
 * All /api/v1/schedule/* calls go through MSW during FE-B4 development.
 */

export interface DispatchBoardJob {
  id: string;
  title: string;
  customer_name: string;
  /** DISPATCH-B1.5: site name (e.g. "Main Office") — from Part A backend enrichment.
   * Optional because Part A may not be deployed; graceful fallback to empty string. */
  site_name?: string | null;
  site_address: string;
  scheduled_start_at: string; // ISO 8601
  scheduled_end_at: string; // ISO 8601
  tech_id: string | null;
  status:
    | "draft"
    | "scheduled"
    | "in_progress"
    | "completed"
    | "cancelled"
    | "unassigned"
    | "confirmed";
  /** DISPATCH-B3: real values from backend CLASS-B1. "standard" is the null-safety default. */
  priority: "standard" | "urgent" | "emergency";
  /** DISPATCH-B3: customer.type — "person" or "company". Was mislabeled commercial/residential. */
  customer_type: "person" | "company" | null;
  /** DISPATCH-B3: site.site_type — display-only in dispatch (not a filter dimension). */
  site_type?: "commercial" | "residential" | "industrial" | null;
  /** DISPATCH-B3: job type code for filtering — from job_types table. */
  job_type_code?: string | null;
  /** DISPATCH-B3: job type human-readable label — used for display in chips and pills. */
  job_type_label?: string | null;
  updated_at: string; // version field for staleness check
  display_color?: string; // Dynamic hex from API (tech color) — only valid inline style use
  /** DISPATCH-B1.25: role of this placement ('primary' in jobs[]; 'helper'/etc in commitments). */
  assignment_role?: string | null;
}

export interface DispatchBoardTech {
  id: string;
  tech_id: string; // both id and tech_id present per API; id is canonical
  name: string;
  display_color: string | null; // flat hex string (e.g. "#3B82F6") or null if unassigned
  avatar_url: string | null;
  eta_minutes_to_first_job?: number | null;
  /** DISPATCH-B1.25: non-primary job commitments for this tech (do NOT flatten into jobs[]). */
  commitments?: DispatchBoardJob[];
}

export interface DispatchBoardResponse {
  date: string; // YYYY-MM-DD
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
}

export interface MoveJobRequest {
  tech_id: string | null;
  scheduled_start_at: string;
  scheduled_end_at: string;
  expected_updated_at: string; // §16.4 staleness check field
}

export interface MoveJobResponse {
  id: string;
  tech_id: string | null;
  scheduled_start_at: string;
  scheduled_end_at: string;
  updated_at: string;
}

export interface SchedulingConflict {
  conflict_class: "overlap" | "availability" | "travel" | "info";
  severity: "block" | "warn" | "info";
  detail: Record<string, unknown>;
  affected_job_id: string;
  suggested_resolution: string | null;
}

export interface CheckConflictsRequest {
  tech_id: string | null;
  scheduled_start_at: string;
  scheduled_end_at: string;
}

export interface CheckConflictsResponse {
  conflicts: SchedulingConflict[];
  has_blocking_conflicts: boolean;
}

export interface DriveTimeRequest {
  segments: Array<{ from_job_id: string; to_job_id: string }>;
  date: string;
}

export interface DriveTimeSegment {
  from_job_id: string;
  to_job_id: string;
  drive_time_seconds: number;
  drive_distance_meters: number;
  is_feasible: boolean; // false when drive time > scheduled gap
  cached: boolean;
}

export interface DriveTimeResponse {
  segments: DriveTimeSegment[];
}

export interface SseBoardEvent {
  event_type:
    | "job_scheduled"
    | "job_rescheduled"
    | "job_reassigned"
    | "job_unassigned"
    | "conflict_detected"
    | "conflict_cleared"
    | "calendar_sync_status";
  job_id?: string;
  tech_id?: string;
  prev_tech_id?: string;
  new_tech_id?: string;
  scheduled_start_at?: string;
  prev_start_at?: string;
  new_start_at?: string;
  conflict_class?: SchedulingConflict["conflict_class"];
  severity?: SchedulingConflict["severity"];
}

export interface TechAvailability {
  user_id: string;
  date: string;
  work_start: string; // HH:MM
  work_end: string; // HH:MM
  pto_periods: Array<{ start: string; end: string }>;
}
