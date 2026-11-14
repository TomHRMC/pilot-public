/**
 * In-Flight Sync Indicator — Shared Types
 *
 * Location: packages/ui/src/sync-indicator/types.ts
 *
 * Props interface locked in FE-B1. FE-B15 adds:
 *   - "background-sync" surface value
 *   - pendingItems, nextSyncAt props
 *   - narrows lastSyncedAt to Date | undefined (removes null — mobile inconsistency fixed)
 *   - useInFlightSyncStatus() data hook in packages/ui/src/hooks/useInFlightSyncStatus.ts
 *
 * Per §16.13 of mvp-arch.md: five compositional states, amber threshold
 * at 5 pending items (tenant-configurable via BE-B15).
 *
 * LOCKED API after FE-B15 — Phase 2 sync surfaces add new surface values only.
 */

/**
 * The five sync surfaces that consume <InFlightSyncIndicator>.
 * Matches arch doc §16.13 surface-specific count semantics.
 *
 * FE-B15 adds "background-sync" (previously referenced in FE-B9 notes but missing from union).
 */
export type SyncSurface =
  | "dispatch" // FE-B4: Dispatch board move optimistic locking
  | "mobile-sync" // FE-B7: Mobile offline queue → server sync
  | "calendar" // FE-B8: Calendar conflict pending changes
  | "quickbooks" // FE-B9: QuickBooks bilateral sync pending
  | "background-sync"; // FE-B15: Background sync session (OS-scheduled mobile sync)

export type SyncState =
  | "idle" // No active sync; 0 pending operations
  | "synced-pending" // Sync complete but N>0 operations queued (will sync in ~Xm)
  | "syncing" // Active sync in progress
  | "error" // Last sync attempt failed; N pending still queued
  | "paused"; // Sync explicitly paused (e.g., user paused QB sync)

export interface PendingItem {
  type: string;
  label: string;
}

export interface InFlightSyncIndicatorProps {
  surface: SyncSurface;
  /**
   * Number of operations pending sync.
   * FE-B1: passed as prop directly.
   * FE-B15: supplied by useInFlightSyncStatus(surface) data hook.
   */
  pendingCount?: number;
  /**
   * Last successful sync timestamp.
   * FE-B1: passed as prop directly.
   * FE-B15: supplied by data hook.
   *
   * NOTE: null is no longer accepted — use undefined. Mobile consumers that
   * previously passed null must coerce: `null → undefined`.
   */
  lastSyncedAt?: Date | undefined;
  /**
   * Current sync state.
   * FE-B1: passed as prop directly; defaults to 'idle'.
   * FE-B15: derived from sync_status backend service.
   */
  state?: SyncState;
  /**
   * Pending-count threshold above which the indicator dot turns amber.
   * Default: 5. Per §16.13 tenant_sync_indicator_pending_amber_threshold.
   * FE-B15 reads this from settings; FE-B1 consumers pass it directly.
   */
  amberThreshold?: number;
  /**
   * Optional handler for manual sync trigger.
   * When provided AND manualTriggerSupported is not false, renders "Sync now" link
   * in synced-pending state.
   * Not available for 'mobile-sync' or 'background-sync' (OS-scheduled).
   */
  onManualSync?: () => void;
  /**
   * Whether manual sync is supported for this surface.
   * Derived from BE-B15 manual_trigger_supported field.
   * When false, "Sync now" is not rendered even if onManualSync is provided.
   * Default: true (backward-compatible; existing consumers that pass onManualSync keep it).
   */
  manualTriggerSupported?: boolean;
  /**
   * Render a compact version (dot + count only, no text).
   * Used in header nav bar slots where space is constrained.
   */
  compact?: boolean;
  /**
   * Navigate-to-resolution-surface callback.
   * FE-B15 wires this per surface:
   *   dispatch      → router.push('/schedule#conflicts')
   *   calendar      → router.push('/settings/integrations/calendar/conflicts')
   *   quickbooks    → router.push('/settings/integrations/quickbooks/conflicts')
   *   mobile-sync   → openDrawer() (opens SyncQueueDrawer)
   *   background-sync → mobile sync queue surface
   * Rendered as a clickable wrapper in error and synced-pending states.
   */
  onResolve?: () => void;
  /**
   * Pending items for hover/tap detail tooltip. Max 5.
   * FE-B15: populated from BE-B15 pending_items field.
   */
  pendingItems?: PendingItem[];
  /**
   * Next scheduled sync time. Used for label "syncing in 2m".
   * FE-B15: populated from BE-B15 next_sync_at field.
   */
  nextSyncAt?: Date | undefined;
  testID?: string;
}
