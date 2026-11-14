/**
 * Sync Indicator — Public API barrel
 * Location: packages/ui/src/sync-indicator/index.ts
 *
 * FE-B15: Adds PendingItem and InFlightSyncStatus exports.
 * useInFlightSyncStatus hook is exported from packages/ui/src/hooks/
 * and re-exported from packages/ui/src/index.ts.
 */

// Default web export
export { InFlightSyncIndicator } from "./web/InFlightSyncIndicator";

// Type exports
export type {
  InFlightSyncIndicatorProps,
  SyncSurface,
  SyncState,
  PendingItem,
} from "./types";
