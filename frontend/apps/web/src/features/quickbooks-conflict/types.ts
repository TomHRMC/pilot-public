/**
 * QuickBooks Conflict — TypeScript types
 *
 * Location: apps/web/src/features/quickbooks-conflict/types.ts
 *
 * Established FE-B9. Mirrors backend A49 QbConflictListResponse / QbConflictDetailResponse.
 * Server-side diff is canonical — use normalizeQbFieldDiffs() (Rule 4).
 *
 * ⚠️ ARCHITECTURE RULE 3: NO voice resolve state machine here.
 * QB conflicts are web-resolution only. Voice → READ-ONLY STATUS QUERY only.
 */

// ─── Core enums ───────────────────────────────────────────────────────────────

export type QbEntityType = "customer" | "quote" | "invoice" | "expense";

export type QbConflictType =
  | "modified_modified"
  | "deleted_modified"
  | "modified_deleted";

/** 'pilot' = Pilot on left (master), 'external' = QB on left (master) */
export type QbMasterDirection = "pilot" | "external";

export type QbResolution = "accept_local" | "accept_remote" | "per_field";

// ─── QB field diff (from backend A49) ────────────────────────────────────────

export interface QbFieldDiff {
  fieldName: string;
  pilot_value: unknown;
  external_value: unknown;
  changeType: "modified" | "added" | "removed" | "unchanged";
}

// ─── Per-field selection (shared with field issues) ───────────────────────────

export interface QbPerFieldSelection {
  field_name: string;
  chosen_side: "pilot" | "external";
}

// ─── Queue item (list endpoint) ───────────────────────────────────────────────

export interface QbConflictQueueItem {
  id: string;
  entityType: QbEntityType;
  entityId: string;
  entityDisplayName: string;
  conflictType: QbConflictType;
  masterDirection: QbMasterDirection;
  pilotModifiedAt: string;
  externalModifiedAt: string;
  /** Non-null only for invoice entity type */
  financialDeltaCents: number | null;
  resolution: QbResolution | null;
  detectedAt: string;
  daysUntilExpiry: number | null;
}

// ─── Detail (detail endpoint) ─────────────────────────────────────────────────

export interface QbConflictDetail {
  id: string;
  entityType: QbEntityType;
  entityId: string;
  entityDisplayName: string;
  conflictType: QbConflictType;
  /** Pre-computed by backend per entity type (Decision 3 / Table in design doc §3) */
  masterDirection: QbMasterDirection;
  pilotModifiedAt: string;
  externalModifiedAt: string;
  pilotModifiedByUserId: string | null;
  pilotModifiedByName: string | null;
  fieldDiffs: QbFieldDiff[];
  // ─── Invoice-specific (null for non-invoice types) ───
  financialDeltaCents: number | null;
  pilotAmountCents: number | null;
  qbAmountCents: number | null;
  arImpactDescription: string | null;
  taxPeriodWarning: string | null;
  qbTransactionUrl: string | null;
  // ─── Resolution state ───
  resolution: QbResolution | null;
  resolvedAt: string | null;
  autoResolvedStale: boolean;
}

// ─── API request/response types ───────────────────────────────────────────────

export interface QbConflictsParams {
  status?: "pending" | "resolved" | "all";
  entity_type?: QbEntityType;
  cursor?: string;
  limit?: number;
}

export interface QbConflictsResponse {
  conflicts: QbConflictQueueItem[];
  next_cursor: string | null;
  total_pending: number;
}

export interface QbConflictResolveRequest {
  resolution: QbResolution;
  per_field_selections?: QbPerFieldSelection[];
  expected_pilot_modified_at: string;
  expected_external_modified_at: string;
}
