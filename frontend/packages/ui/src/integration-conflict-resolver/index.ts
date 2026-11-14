/**
 * integration-conflict-resolver — barrel export
 *
 * ⚠️ Interface locked after FE-B8. FE-B9 may only extend via optional additive props.
 */

export { IntegrationConflictResolver } from "./IntegrationConflictResolver";
export { DeletionConflictView } from "./DeletionConflictView";
export { ExpiryCountdownBadge } from "./ExpiryCountdownBadge";
export { ConflictTypeLabel } from "./ConflictTypeLabel";
export type {
  IntegrationConflictResolverProps,
  DeletionConflictViewProps,
  ExpiryCountdownBadgeProps,
  ConflictTypeLabelProps,
  CalendarConflictDetail,
  CalendarApiFieldDiff,
  CalendarResolution,
  CalendarConnectionStatus,
  CalendarSyncStatusRowProps,
  ConflictType,
  QbConflictDetail,
  // FE-B9 additions — locked for FE-B11/FE-B15/FE-B16
  QbFieldDiff,
  FieldIssueDetail,
  FieldIssueDiff,
  PerFieldSelection,
} from "./types";
