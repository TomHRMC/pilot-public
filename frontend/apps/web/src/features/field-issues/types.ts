/**
 * Field Issues — TypeScript types
 *
 * Location: apps/web/src/features/field-issues/types.ts
 *
 * Established FE-B9. Mirrors backend A47 FieldIssueListResponse / FieldIssueDetailResponse.
 * Server-side diff is canonical — never compute diffs client-side (Rule 4).
 */

// ─── Core enums ───────────────────────────────────────────────────────────────

export type FieldIssueStatus = "pending" | "auto_recovered" | "stale";

export type FieldIssueOperationType =
  | "time_entry"
  | "expense"
  | "photo"
  | "status_change"
  | "loto";

export type FieldIssueConflictType =
  | "modified_modified"
  | "deleted_modified"
  | "modified_deleted";

export type FieldIssueResolution =
  | "accept_tech"
  | "accept_server"
  | "per_field";

// ─── Diff types ───────────────────────────────────────────────────────────────

export interface FieldIssueDiff {
  fieldName: string;
  techValue: unknown;
  serverValue: unknown;
  changeType: "modified" | "added" | "removed" | "unchanged";
  techChange: "modified" | "added" | "removed" | "unchanged";
  serverChange: "modified" | "added" | "removed" | "unchanged";
}

// ─── Per-field selection (shared with QB) ─────────────────────────────────────

export interface PerFieldSelection {
  field_name: string;
  chosen_side: "tech" | "server";
}

// ─── Queue item (list endpoint) ───────────────────────────────────────────────

export interface FieldIssueQueueItem {
  id: string;
  status: FieldIssueStatus;
  operationType: FieldIssueOperationType;
  techId: string;
  techName: string;
  capturedAt: string;
  escalatedAt: string;
  explainerSummary: string; // short version for queue row
  conflictType: FieldIssueConflictType;
}

// ─── Detail (detail endpoint) ─────────────────────────────────────────────────

export interface FieldIssueDetail {
  id: string;
  status: FieldIssueStatus;
  operationType: FieldIssueOperationType;
  techId: string;
  techName: string;
  techLastActiveAt: string | null;
  capturedAt: string;
  syncAttemptedAt: string;
  escalatedAt: string;
  /** Server-generated plain-language explanation — render verbatim (Rule 4 / design doc C.2) */
  explainerCopy: string;
  techSnapshot: Record<string, unknown> | null;
  serverSnapshot: Record<string, unknown> | null;
  fieldDiffs: FieldIssueDiff[];
  conflictType: FieldIssueConflictType;
  resolution: FieldIssueResolution | null;
  resolvedByUserId: string | null;
  resolvedAt: string | null;
  /** Staleness check token from detail response — sent back on resolve */
  expectedServerStateHash: string;
}

// ─── API request/response types ───────────────────────────────────────────────

export interface FieldIssuesParams {
  status?: FieldIssueStatus | "all";
  operation_type?: FieldIssueOperationType;
  active_techs_only?: boolean;
  cursor?: string;
  limit?: number;
}

export interface FieldIssuesResponse {
  issues: FieldIssueQueueItem[];
  next_cursor: string | null;
  total_pending: number;
}

export interface FieldIssueResolveRequest {
  resolution: FieldIssueResolution;
  per_field_selections?: PerFieldSelection[];
  expected_server_state_hash: string;
}

// ─── 409 staleness response types ─────────────────────────────────────────────

export type FieldIssue409Response =
  | { staleness_type: "server_changed"; refreshed_issue: FieldIssueDetail }
  | { staleness_type: "auto_recovered"; message: string }
  | { staleness_type: "stale"; message: string };

// ─── Voice state machine (field issues only — NOT QB) ─────────────────────────

export type VoiceFieldIssueResolutionState =
  | { phase: "idle" }
  | { phase: "identifying"; issueIdentifier: string }
  | {
      phase: "confirming";
      issueId: string;
      chosenResolution: FieldIssueResolution;
      readbackText: string;
    }
  | { phase: "committed"; issueId: string; resolution: FieldIssueResolution }
  | {
      phase: "cancelled";
      reason:
        | "user_cancelled"
        | "staleness_detected"
        | "deletion_redirect"
        | "permission_revoked_redirect";
    };

// ─── Summary (mobile) ─────────────────────────────────────────────────────────

export interface FieldIssuesSummary {
  pending_count: number;
}
