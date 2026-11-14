/**
 * Calendar conflict fixtures — typed test data for MSW handlers and unit tests
 *
 * Location: apps/web/src/features/calendar-conflict/mocks/calendarConflictFixtures.ts
 *
 * All fixtures are fully typed — no type casting.
 * Used by both MSW dev handlers and integration test suites.
 */

// ─── CalendarConflictQueueItem fixtures ───────────────────────────────────────

/** Represents ConflictListItem from backend (snake_case from API) */
interface RawConflictListItem {
  id: string;
  conflict_type: "modified_modified" | "deleted_modified" | "modified_deleted";
  job_id: string;
  job_title: string | null;
  scheduled_start_at: string | null;
  urgency_score: number | null;
  pilot_modified_at: string;
  external_modified_at: string;
  resolution: string | null;
  detected_at: string;
}

export const conflictListItemFixtures: RawConflictListItem[] = [
  {
    id: "conflict-mm-1",
    conflict_type: "modified_modified",
    job_id: "job-1",
    job_title: "Panel Upgrade - Smith Residence",
    scheduled_start_at: "2026-06-01T09:00:00Z",
    urgency_score: 90,
    pilot_modified_at: "2026-05-25T10:00:00Z",
    external_modified_at: "2026-05-25T11:00:00Z",
    resolution: null,
    detected_at: "2026-05-25T12:00:00Z",
  },
  {
    id: "conflict-mm-2",
    conflict_type: "modified_modified",
    job_id: "job-2",
    job_title: "EV Charger Install - Johnson",
    scheduled_start_at: "2026-06-03T14:00:00Z",
    urgency_score: 60,
    pilot_modified_at: "2026-05-24T09:00:00Z",
    external_modified_at: "2026-05-24T10:00:00Z",
    resolution: null,
    detected_at: "2026-05-24T11:00:00Z",
  },
  {
    id: "conflict-mm-3",
    conflict_type: "modified_modified",
    job_id: "job-3",
    job_title: "Service Call - Brown",
    scheduled_start_at: "2026-06-05T08:00:00Z",
    urgency_score: 40,
    pilot_modified_at: "2026-05-23T15:00:00Z",
    external_modified_at: "2026-05-23T16:00:00Z",
    resolution: null,
    detected_at: "2026-05-23T17:00:00Z",
  },
];

/** Conflict with 5 days until expiry (amber badge) */
export const conflictWithAmberExpiryFixture: RawConflictListItem = {
  id: "conflict-expiry-amber",
  conflict_type: "modified_modified",
  job_id: "job-expiry-1",
  job_title: "Amber Expiry - 5 Days",
  scheduled_start_at: "2026-06-10T09:00:00Z",
  urgency_score: 70,
  pilot_modified_at: "2026-05-20T10:00:00Z",
  external_modified_at: "2026-05-20T11:00:00Z",
  resolution: null,
  detected_at: "2026-05-20T12:00:00Z",
};

/** Conflict with 2 days until expiry (red urgent badge) */
export const conflictWithUrgentExpiryFixture: RawConflictListItem = {
  id: "conflict-expiry-urgent",
  conflict_type: "modified_modified",
  job_id: "job-expiry-2",
  job_title: "Urgent Expiry - 2 Days",
  scheduled_start_at: "2026-06-01T09:00:00Z",
  urgency_score: 95,
  pilot_modified_at: "2026-05-22T10:00:00Z",
  external_modified_at: "2026-05-22T11:00:00Z",
  resolution: null,
  detected_at: "2026-05-22T12:00:00Z",
};

export const deletionConflictListItems: RawConflictListItem[] = [
  {
    id: "conflict-dm-1",
    conflict_type: "deleted_modified",
    job_id: "job-del-1",
    job_title: "Deleted Calendar Event - Williams",
    scheduled_start_at: "2026-06-02T10:00:00Z",
    urgency_score: 80,
    pilot_modified_at: "2026-05-25T09:00:00Z",
    external_modified_at: "2026-05-25T08:00:00Z",
    resolution: null,
    detected_at: "2026-05-25T10:00:00Z",
  },
  {
    id: "conflict-md-1",
    conflict_type: "modified_deleted",
    job_id: "job-del-2",
    job_title: "Pilot Job Deleted By Calendar - Davis",
    scheduled_start_at: "2026-06-04T11:00:00Z",
    urgency_score: 75,
    pilot_modified_at: "2026-05-24T14:00:00Z",
    external_modified_at: "2026-05-24T13:00:00Z",
    resolution: null,
    detected_at: "2026-05-24T15:00:00Z",
  },
];

// ─── ConflictDetailResponse fixtures ─────────────────────────────────────────

/** Raw API shape (snake_case) for ConflictDetailResponse */
interface RawConflictDetailResponse {
  id: string;
  conflict_type: "modified_modified" | "deleted_modified" | "modified_deleted";
  job_id: string;
  job_title: string | null;
  scheduled_start_at: string | null;
  urgency_score: number | null;
  pilot_modified_by_user_id: string | null;
  pilot_modified_by_name: string | null;
  pilot_modified_at: string;
  external_modified_at: string;
  resolution: string | null;
  resolved_by_user_id: string | null;
  resolved_at: string | null;
  auto_resolved_stale: boolean;
  pilot_snapshot: Record<string, unknown> | null;
  external_snapshot: Record<string, unknown> | null;
  base_snapshot: Record<string, unknown> | null;
  field_diffs: Array<{
    field_name: string;
    pilot_value: unknown;
    external_value: unknown;
    base_value: unknown;
    pilot_change: "unchanged" | "modified" | "added" | "removed";
    external_change: "unchanged" | "modified" | "added" | "removed";
  }>;
  detected_at: string;
  provider_display_name?: string;
}

/** Modified-modified with 5 field diffs */
export const modifiedModifiedDetailFixture: RawConflictDetailResponse = {
  id: "conflict-mm-1",
  conflict_type: "modified_modified",
  job_id: "job-1",
  job_title: "Panel Upgrade - Smith Residence",
  scheduled_start_at: "2026-06-01T09:00:00Z",
  urgency_score: 90,
  pilot_modified_by_user_id: "user-mike",
  pilot_modified_by_name: "Mike Smith",
  pilot_modified_at: "2026-05-25T10:00:00Z",
  external_modified_at: "2026-05-25T11:00:00Z",
  resolution: null,
  resolved_by_user_id: null,
  resolved_at: null,
  auto_resolved_stale: false,
  pilot_snapshot: null,
  external_snapshot: null,
  base_snapshot: null,
  field_diffs: [
    {
      field_name: "scheduled_start_at",
      pilot_value: "2026-06-01T09:00:00Z",
      external_value: "2026-06-01T10:00:00Z",
      base_value: "2026-06-01T09:00:00Z",
      pilot_change: "unchanged",
      external_change: "modified",
    },
    {
      field_name: "scheduled_end_at",
      pilot_value: "2026-06-01T11:00:00Z",
      external_value: "2026-06-01T12:00:00Z",
      base_value: "2026-06-01T11:00:00Z",
      pilot_change: "unchanged",
      external_change: "modified",
    },
    {
      field_name: "description",
      pilot_value: "200A panel upgrade",
      external_value: "200A panel upgrade - confirmed",
      base_value: "200A panel upgrade",
      pilot_change: "unchanged",
      external_change: "modified",
    },
    {
      field_name: "location",
      pilot_value: "123 Main St",
      external_value: "123 Main Street, Unit B",
      base_value: "123 Main St",
      pilot_change: "unchanged",
      external_change: "modified",
    },
    {
      field_name: "notes",
      pilot_value: null,
      external_value: "Customer requested earlier start",
      base_value: null,
      pilot_change: "unchanged",
      external_change: "added",
    },
  ],
  detected_at: "2026-05-25T12:00:00Z",
  provider_display_name: "Google Calendar",
};

/** Deleted-modified conflict (no field diffs) */
export const deletedModifiedDetailFixture: RawConflictDetailResponse = {
  id: "conflict-dm-1",
  conflict_type: "deleted_modified",
  job_id: "job-del-1",
  job_title: "Deleted Calendar Event - Williams",
  scheduled_start_at: "2026-06-02T10:00:00Z",
  urgency_score: 80,
  pilot_modified_by_user_id: "user-mike",
  pilot_modified_by_name: "Mike Smith",
  pilot_modified_at: "2026-05-25T09:00:00Z",
  external_modified_at: "2026-05-25T08:00:00Z",
  resolution: null,
  resolved_by_user_id: null,
  resolved_at: null,
  auto_resolved_stale: false,
  pilot_snapshot: null,
  external_snapshot: null,
  base_snapshot: null,
  field_diffs: [],
  detected_at: "2026-05-25T10:00:00Z",
  provider_display_name: "Google Calendar",
};

/** Modified-deleted conflict */
export const modifiedDeletedDetailFixture: RawConflictDetailResponse = {
  id: "conflict-md-1",
  conflict_type: "modified_deleted",
  job_id: "job-del-2",
  job_title: "Pilot Job Deleted By Calendar - Davis",
  scheduled_start_at: "2026-06-04T11:00:00Z",
  urgency_score: 75,
  pilot_modified_by_user_id: "user-mike",
  pilot_modified_by_name: "Mike Smith",
  pilot_modified_at: "2026-05-24T14:00:00Z",
  external_modified_at: "2026-05-24T13:00:00Z",
  resolution: null,
  resolved_by_user_id: null,
  resolved_at: null,
  auto_resolved_stale: false,
  pilot_snapshot: null,
  external_snapshot: null,
  base_snapshot: null,
  field_diffs: [],
  detected_at: "2026-05-24T15:00:00Z",
  provider_display_name: "Google Calendar",
};

/** Already-resolved conflict (read-only detail) */
export const resolvedConflictDetailFixture: RawConflictDetailResponse = {
  ...modifiedModifiedDetailFixture,
  id: "conflict-resolved-1",
  resolution: "accept_local",
  resolved_by_user_id: "user-mike",
  resolved_at: "2026-05-25T13:00:00Z",
};

/** 409 staleness response body */
export const stalenesErrorBody = {
  type: "https://pilot.app/errors/stale-conflict",
  title: "Record updated since last view",
  status: 409,
  detail:
    "Another user has updated this conflict. Review the refreshed state before resolving.",
  refreshed_state: {
    ...modifiedModifiedDetailFixture,
    // External side changed again
    field_diffs: [
      ...modifiedModifiedDetailFixture.field_diffs,
      {
        field_name: "assigned_to",
        pilot_value: "Mike Smith",
        external_value: "Jane Doe",
        base_value: "Mike Smith",
        pilot_change: "unchanged" as const,
        external_change: "modified" as const,
      },
    ],
  },
};

// ─── CalendarConnectionStatus fixtures ───────────────────────────────────────

/** Raw API shape (snake_case) */
interface RawCalendarConnectionStatus {
  is_connected: boolean;
  provider_code: string | null;
  sync_status: string | null;
  connection_status: "connected" | "syncing" | "error" | "disconnected" | null;
  connected_at: string | null;
  token_expires_at: string | null;
  last_sync_at: string | null;
  last_successful_sync_at: string | null;
  pending_conflicts_count: number;
  requires_reconnect: boolean;
}

export const connectedStatusFixture: RawCalendarConnectionStatus = {
  is_connected: true,
  provider_code: "google_calendar",
  sync_status: "idle",
  connection_status: "connected",
  connected_at: "2026-05-01T08:00:00Z",
  token_expires_at: "2026-08-01T08:00:00Z",
  last_sync_at: "2026-05-25T17:00:00Z",
  last_successful_sync_at: "2026-05-25T17:00:00Z",
  pending_conflicts_count: 3,
  requires_reconnect: false,
};

export const errorStatusFixture: RawCalendarConnectionStatus = {
  is_connected: true,
  provider_code: "google_calendar",
  sync_status: "error",
  connection_status: "error",
  connected_at: "2026-05-01T08:00:00Z",
  token_expires_at: "2026-05-20T08:00:00Z",
  last_sync_at: "2026-05-20T07:00:00Z",
  last_successful_sync_at: "2026-05-20T07:00:00Z",
  pending_conflicts_count: 5,
  requires_reconnect: true,
};

export const disconnectedStatusFixture: RawCalendarConnectionStatus = {
  is_connected: false,
  provider_code: null,
  sync_status: null,
  connection_status: "disconnected",
  connected_at: null,
  token_expires_at: null,
  last_sync_at: null,
  last_successful_sync_at: null,
  pending_conflicts_count: 0,
  requires_reconnect: false,
};
