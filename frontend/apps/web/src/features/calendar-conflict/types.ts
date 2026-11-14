/**
 * Calendar conflict feature types — web
 *
 * Location: apps/web/src/features/calendar-conflict/types.ts
 *
 * CamelCase types derived from the backend API.
 * Normalization functions (snake_case → camelCase) are co-located here.
 */

import type {
  CalendarConflictDetail,
  CalendarApiFieldDiff,
  CalendarConnectionStatus,
} from "@pilot/ui";

// ─── Re-export shared types ───────────────────────────────────────────────────

export type {
  CalendarConflictDetail,
  CalendarApiFieldDiff,
  CalendarConnectionStatus,
};

export type { CalendarResolution, ConflictType } from "@pilot/ui";

// ─── Queue item type ──────────────────────────────────────────────────────────

export interface CalendarConflictQueueItem {
  id: string;
  conflictType: "modified_modified" | "deleted_modified" | "modified_deleted";
  jobId: string;
  jobTitle: string | null;
  scheduledStartAt: string | null;
  urgencyScore: number | null;
  pilotModifiedAt: string;
  externalModifiedAt: string;
  resolution: string | null;
  detectedAt: string;
}

export interface CalendarConflictsResponse {
  conflicts: CalendarConflictQueueItem[];
  nextCursor: string | null;
  totalPending: number;
}

export interface CalendarConflictsParams {
  status?: "pending" | "resolved" | "all";
  cursor?: string;
  limit?: number;
}

// ─── Resolve request/response ─────────────────────────────────────────────────

export interface ConflictResolveRequest {
  resolution: string;
  expected_pilot_modified_at: string;
  expected_external_modified_at: string;
}

export interface ConflictResolveResponse {
  id: string;
  resolution: string;
  resolved_at: string;
  resolved_by_user_id: string;
}

// ─── SSE event types ──────────────────────────────────────────────────────────

export interface CalendarSseEvent {
  type: "conflict_detected" | "conflict_resolved" | "calendar_sync_status";
  conflict_id?: string;
  job_id?: string;
  resolution?: string;
  connection_status?: string;
  pending_conflicts_count?: number;
}

// ─── Normalization functions ──────────────────────────────────────────────────

/** Normalize raw API conflict list item (snake_case) → CalendarConflictQueueItem */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeConflictListItem(raw: any): CalendarConflictQueueItem {
  return {
    id: raw.id as string,
    conflictType:
      raw.conflict_type as CalendarConflictQueueItem["conflictType"],
    jobId: raw.job_id as string,
    jobTitle: raw.job_title as string | null,
    scheduledStartAt: raw.scheduled_start_at as string | null,
    urgencyScore: raw.urgency_score as number | null,
    pilotModifiedAt: raw.pilot_modified_at as string,
    externalModifiedAt: raw.external_modified_at as string,
    resolution: raw.resolution as string | null,
    detectedAt: raw.detected_at as string,
  };
}

/** Normalize raw API field diff (snake_case) → CalendarApiFieldDiff */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeFieldDiff(raw: any): CalendarApiFieldDiff {
  return {
    fieldName: raw.field_name as string,
    pilotValue: raw.pilot_value,
    externalValue: raw.external_value,
    baseValue: raw.base_value,
    pilotChange: raw.pilot_change as CalendarApiFieldDiff["pilotChange"],
    externalChange:
      raw.external_change as CalendarApiFieldDiff["externalChange"],
  };
}

/** Normalize raw API conflict detail (snake_case) → CalendarConflictDetail */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeConflictDetail(raw: any): CalendarConflictDetail {
  return {
    id: raw.id as string,
    conflictType: raw.conflict_type as CalendarConflictDetail["conflictType"],
    jobId: raw.job_id as string,
    jobTitle: raw.job_title as string | null,
    scheduledStartAt: raw.scheduled_start_at as string | null,
    urgencyScore: raw.urgency_score as number | null,
    pilotModifiedByUserId: raw.pilot_modified_by_user_id as string | null,
    pilotModifiedByName: raw.pilot_modified_by_name as string | null,
    pilotModifiedAt: raw.pilot_modified_at as string,
    externalModifiedAt: raw.external_modified_at as string,
    resolution: raw.resolution as CalendarConflictDetail["resolution"],
    resolvedByUserId: raw.resolved_by_user_id as string | null,
    resolvedAt: raw.resolved_at as string | null,
    autoResolvedStale: raw.auto_resolved_stale as boolean,
    pilotSnapshot: raw.pilot_snapshot as Record<string, unknown> | null,
    externalSnapshot: raw.external_snapshot as Record<string, unknown> | null,
    baseSnapshot: raw.base_snapshot as Record<string, unknown> | null,
    fieldDiffs: Array.isArray(raw.field_diffs)
      ? raw.field_diffs.map((d: unknown) => normalizeFieldDiff(d))
      : [],
    detectedAt: raw.detected_at as string,
    providerDisplayName: raw.provider_display_name as string | undefined,
  };
}

/** Normalize raw API CalendarConnectionStatus (snake_case) → CalendarConnectionStatus */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeConnectionStatus(raw: any): CalendarConnectionStatus {
  return {
    isConnected: raw.is_connected as boolean,
    providerCode: raw.provider_code as string | null,
    syncStatus: raw.sync_status as string | null,
    connectionStatus:
      raw.connection_status as CalendarConnectionStatus["connectionStatus"],
    connectedAt: raw.connected_at as string | null,
    tokenExpiresAt: raw.token_expires_at as string | null,
    lastSyncAt: raw.last_sync_at as string | null,
    lastSuccessfulSyncAt: raw.last_successful_sync_at as string | null,
    pendingConflictsCount: raw.pending_conflicts_count as number,
    requiresReconnect: raw.requires_reconnect as boolean,
  };
}
