/**
 * IntegrationConflictResolver — shared types
 *
 * Location: packages/ui/src/integration-conflict-resolver/types.ts
 *
 * ⚠️ LOCKED after FE-B8. FE-B9 may only extend via optional additive props.
 * Do NOT rename, remove, or change semantics of existing types.
 */

// ─── Core data types ──────────────────────────────────────────────────────────

/** Conflict types for bilateral integration conflicts */
export type ConflictType =
  | "modified_modified"
  | "deleted_modified"
  | "modified_deleted";

/** Resolution values for calendar conflicts */
export type CalendarResolution =
  | "accept_local"
  | "accept_remote"
  | "restore_from_calendar"
  | "delete_calendar_too"
  | "recreate_calendar_event"
  | "delete_pilot_job";

/**
 * Camel-cased field diff entry from the calendar conflict API response.
 * Mirrors FieldDiffResponse from backend/api/routes/calendar_conflicts.py.
 */
export interface CalendarApiFieldDiff {
  fieldName: string;
  pilotValue: unknown;
  externalValue: unknown;
  baseValue: unknown;
  pilotChange: "unchanged" | "modified" | "added" | "removed";
  externalChange: "unchanged" | "modified" | "added" | "removed";
}

/**
 * Full calendar conflict detail (camelCase, from GET /api/v1/integrations/calendar/conflicts/{id}).
 * Maps 1:1 to ConflictDetailResponse from backend/api/routes/calendar_conflicts.py.
 */
export interface CalendarConflictDetail {
  id: string;
  conflictType: ConflictType;
  jobId: string;
  jobTitle: string | null;
  scheduledStartAt: string | null;
  urgencyScore: number | null;
  pilotModifiedByUserId: string | null;
  pilotModifiedByName: string | null;
  pilotModifiedAt: string;
  externalModifiedAt: string;
  resolution: CalendarResolution | null;
  resolvedByUserId: string | null;
  resolvedAt: string | null;
  autoResolvedStale: boolean;
  pilotSnapshot: Record<string, unknown> | null;
  externalSnapshot: Record<string, unknown> | null;
  baseSnapshot: Record<string, unknown> | null;
  fieldDiffs: CalendarApiFieldDiff[];
  detectedAt: string;
  /** Display name for the external provider (e.g., "Google Calendar", "Outlook") */
  providerDisplayName?: string;
}

/**
 * QuickBooks conflict detail — FE-B9 full definition.
 * Replaces the placeholder stub. masterDirection pre-computed by backend.
 */
export interface QbConflictDetail {
  id: string;
  conflictType: ConflictType;
  entityType: "customer" | "quote" | "invoice" | "expense";
  entityId: string;
  entityDisplayName: string;
  masterDirection: "pilot" | "external";
  pilotModifiedAt: string;
  externalModifiedAt: string;
  pilotModifiedByUserId: string | null;
  pilotModifiedByName: string | null;
  fieldDiffs: QbFieldDiff[];
  financialDeltaCents: number | null;
  pilotAmountCents: number | null;
  qbAmountCents: number | null;
  arImpactDescription: string | null;
  taxPeriodWarning: string | null;
  qbTransactionUrl: string | null;
  resolution: "accept_local" | "accept_remote" | "per_field" | null;
  resolvedAt: string | null;
  autoResolvedStale: boolean;
  [key: string]: unknown;
}

/**
 * QB field diff entry (from backend A49 payload).
 * pilot_value / external_value are the raw values; normalizeQbFieldDiffs() maps to DiffField.
 */
export interface QbFieldDiff {
  fieldName: string;
  pilot_value: unknown;
  external_value: unknown;
  changeType: "modified" | "added" | "removed" | "unchanged";
}

/**
 * Field issue detail — FE-B9.
 * Used when IntegrationConflictResolver is used for mobile escalation review.
 */
export interface FieldIssueDetail {
  id: string;
  conflictType: ConflictType;
  operationType: "time_entry" | "expense" | "photo" | "status_change" | "loto";
  techId: string;
  techName: string;
  explainerCopy: string;
  fieldDiffs: FieldIssueDiff[];
  resolution: "accept_tech" | "accept_server" | "per_field" | null;
  resolvedAt: string | null;
  expectedServerStateHash: string;
  [key: string]: unknown;
}

/**
 * Field issue diff entry (from backend A47 payload).
 */
export interface FieldIssueDiff {
  fieldName: string;
  techValue: unknown;
  serverValue: unknown;
  changeType: "modified" | "added" | "removed" | "unchanged";
}

/**
 * Per-field selection — shared by both field issues and QB conflict resolution.
 * Exported from packages/ui/src/index.ts (locked for FE-B11 and FE-B16).
 *
 * FE-B9 introduces per-field resolution for both conflict surfaces.
 * Field issue context: chosenSide 'tech' | 'server'
 * QB conflict context: chosenSide 'pilot' | 'external' (same shape, different semantics)
 */
export interface PerFieldSelection {
  fieldName: string;
  chosenSide: "tech" | "server" | "pilot" | "external";
}

// ─── Component prop types ─────────────────────────────────────────────────────

/**
 * Props for <ConflictTypeLabel>.
 */
export interface ConflictTypeLabelProps {
  conflictType: ConflictType;
  /** Test ID for e2e and unit tests */
  testID?: string;
}

/**
 * Props for <ExpiryCountdownBadge>.
 */
export interface ExpiryCountdownBadgeProps {
  /** Days until auto-expiry. null = auto-expiry disabled; renders nothing. */
  daysUntilExpiry: number | null | undefined;
  /** Test ID for e2e and unit tests */
  testID?: string;
}

/**
 * Props for <DeletionConflictView>.
 */
export interface DeletionConflictViewProps {
  conflictType: "deleted_modified" | "modified_deleted";
  jobTitle: string | null;
  onResolve: (resolution: CalendarResolution) => void;
  isResolving: boolean;
  onResolveLater: () => void;
  /** Test ID for e2e and unit tests */
  testID?: string;
}

/**
 * <IntegrationConflictResolver> — Locked public API
 *
 * Location: packages/ui/src/integration-conflict-resolver/IntegrationConflictResolver.tsx
 *
 * ⚠️ INTERFACE LOCKED after FE-B8 ships.
 * FE-B9 may add OPTIONAL props via backward-compatible extension only.
 * Renaming or removing existing props requires multi-batch impact review.
 *
 * FE-B9 extension points:
 *   - renderDomainSpecificFields: inject QB-specific financial_delta_cents / tax_period_warning
 *   - providerDisplayName: "QuickBooks" instead of "Google Calendar"
 *   - Any new props MUST be optional with sensible defaults
 */
export interface IntegrationConflictResolverProps<
  T extends CalendarConflictDetail | QbConflictDetail | FieldIssueDetail =
    CalendarConflictDetail,
> {
  /**
   * The integration type. Drives default labels, verb buttons for deletion
   * conflicts, and voice route-to-web messaging.
   * FE-B9 extends with 'quickbooks'.
   */
  integration: "calendar" | "quickbooks";

  /**
   * The fully-resolved conflict detail (includes field_diffs).
   * The parent page fetches this via its own hook.
   * The resolver is purely presentational — no internal fetching.
   */
  conflict: T;

  /**
   * Called when the owner selects a resolution.
   * The parent page's useResolveCalendarConflict hook handles the actual mutation.
   * The resolver communicates the choice upward via this callback.
   */
  onResolve: (resolution: string) => void;

  /**
   * True when the resolve mutation is in-flight.
   * Disables action buttons and shows spinner.
   */
  isResolving: boolean;

  /**
   * Called when the owner clicks "Resolve later" escape hatch.
   */
  onResolveLater: () => void;

  /**
   * The provider display name for the right-column header.
   * Defaults: calendar → from conflict.providerDisplayName or 'Google Calendar';
   *            quickbooks → 'QuickBooks'
   * Must be read from the integration record, never hardcoded.
   */
  providerDisplayName?: string;

  /**
   * FE-B9 extension slot: render QB-specific fields (financial_delta_cents,
   * tax_period_warning) below the standard DiffView.
   * Calendar integration passes undefined.
   */
  renderDomainSpecificFields?: (conflict: T) => React.ReactNode;

  /**
   * Days until auto-expiry. Drives ExpiryCountdownBadge in the detail header.
   * null when auto-expiry is disabled for this tenant.
   */
  daysUntilExpiry?: number | null;

  /** Test ID for e2e and unit tests */
  testID?: string;

  // ─── FE-B9 ADDITIVE OPTIONAL PROPS ──────────────────────────────────────────

  /**
   * Column ordering for the two-column diff.
   * 'pilot' (default) → Pilot on left (read-leftward primacy = Pilot is master).
   * 'external' → external system on left (QB is master for invoices).
   *
   * FE-B8 calendar usage does not pass this prop → defaults to 'pilot' → zero behavior change.
   */
  masterDirection?: "pilot" | "external";

  /**
   * Whether per-field resolution is supported for this conflict type.
   * Default: false (preserves FE-B8 calendar behavior — calendar is always accept-one-side).
   * Set true for field issues and QB conflicts.
   *
   * When true, "Choose field by field →" button is shown below the diff.
   * Per-field picker does NOT appear for deletion conflicts (all-or-nothing).
   */
  supportsPerFieldResolution?: boolean;

  /**
   * Per-field selections state — managed by parent page.
   * Passed down when supportsPerFieldResolution=true.
   */
  perFieldSelections?: PerFieldSelection[];

  /**
   * Callback when user changes a per-field selection radio.
   * Parent page manages the selections state array.
   */
  onPerFieldSelectionChange?: (selections: PerFieldSelection[]) => void;
}

// ─── CalendarSyncStatusRow types ──────────────────────────────────────────────

/**
 * Camel-cased calendar connection status (from GET /api/v1/integrations/calendar/status).
 * Maps to CalendarConnectionStatus from backend/api/routes/calendar_integration.py.
 */
export interface CalendarConnectionStatus {
  isConnected: boolean;
  providerCode: string | null;
  syncStatus: string | null;
  connectionStatus: "connected" | "syncing" | "error" | "disconnected" | null;
  connectedAt: string | null;
  tokenExpiresAt: string | null;
  lastSyncAt: string | null;
  lastSuccessfulSyncAt: string | null;
  pendingConflictsCount: number;
  requiresReconnect: boolean;
}

/**
 * Props for <CalendarSyncStatusRow> (mobile).
 */
export interface CalendarSyncStatusRowProps {
  /** The resolved CalendarConnectionStatus data (caller fetches, passes down) */
  status: CalendarConnectionStatus | undefined;

  /** True while useCalendarStatus is loading */
  isLoading: boolean;

  /** Deep-link URL to open on web when owner taps the row */
  resolveWebUrl: string;

  /**
   * FE-B15 additive: pending conflict count from useInFlightSyncStatus("calendar").
   * When provided, shown in subtitle: "N conflicts to resolve → web".
   * Falls back to status.pendingConflictsCount if not provided.
   */
  pendingCount?: number;

  /** Test ID for e2e and unit tests */
  testID?: string;
}
