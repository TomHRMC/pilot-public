/**
 * SyncQueueStore — Zustand store for sync state UI
 *
 * Location: apps/mobile/features/offline-sync/store.ts
 *
 * Bridges the SyncOrchestrator (database layer) to the UI layer.
 * SyncOrchestrator calls store.setSyncState() via its onStateChange callback.
 * UI components read from this store to get current sync state.
 *
 * MOB-B6: Added triggerSync / setTriggerSync so SyncOrchestrator can register
 * its sync() method and the SyncPendingScreen can call it manually.
 *
 * Per batch-fe-b7-design.md Section F.6.
 */

import { create } from "zustand";
import type { SyncState } from "../../database/sync/types";

export interface SyncQueueStore {
  /** Whether the sync queue bottom-sheet drawer is open */
  isDrawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;

  /** Current sync state from SyncOrchestrator — updated via onStateChange callback */
  syncState: SyncState;
  setSyncState: (state: SyncState) => void;

  /**
   * ID of the conflict currently requiring tech review.
   * Set by SyncOrchestrator.onTechResolvableConflict callback.
   * Cleared when ConflictResolutionScreen resolves it.
   */
  activeConflictId: string | null;
  setActiveConflictId: (id: string | null) => void;

  /**
   * Manual sync trigger — registered by SyncOrchestrator on init.
   * Calling this runs SyncOrchestrator.sync('manual').
   * Null until SyncOrchestrator registers itself via setTriggerSync().
   */
  triggerSync: (() => Promise<void>) | null;
  setTriggerSync: (fn: () => Promise<void>) => void;
}

export const useSyncQueueStore = create<SyncQueueStore>((set) => ({
  isDrawerOpen: false,
  openDrawer: () => set({ isDrawerOpen: true }),
  closeDrawer: () => set({ isDrawerOpen: false }),

  syncState: {
    status: "idle",
    pendingCount: 0,
    lastSyncedAt: null,
  },
  setSyncState: (state) => set({ syncState: state }),

  activeConflictId: null,
  setActiveConflictId: (id) => set({ activeConflictId: id }),

  triggerSync: null,
  setTriggerSync: (fn) => set({ triggerSync: fn }),
}));
