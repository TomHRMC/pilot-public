/**
 * useBackgroundSyncStatus — reads background sync state from SyncOrchestrator + AsyncStorage
 *
 * Location: apps/mobile/features/offline-sync/hooks/useBackgroundSyncStatus.ts
 *
 * Established FE-B9. RULE 5: Pure observer — no OS API calls.
 * Reads SyncOrchestrator internal state + AsyncStorage telemetry.
 * NOT in TanStack Query — local device state only.
 *
 * AsyncStorage key: @pilot/bg_sync_last_attempt
 */

import { useState, useEffect } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface BackgroundSyncStatus {
  state:
    | "recent_success"
    | "recent_success_no_work"
    | "recent_failed"
    | "disabled"
    | "never_run"
    | "no_permission";
  lastAttemptAt: Date | null;
  itemsSynced: number | null;
  retryCount: number;
}

export interface BgSyncTelemetry {
  state: BackgroundSyncStatus["state"];
  lastAttemptAt: string | null; // ISO string
  itemsSynced: number | null;
  retryCount: number;
}

const BG_SYNC_STORAGE_KEY = "@pilot/bg_sync_last_attempt";

const DEFAULT_STATUS: BackgroundSyncStatus = {
  state: "never_run",
  lastAttemptAt: null,
  itemsSynced: null,
  retryCount: 0,
};

// ─── Hook ──────────────────────────────────────────────────────────────────────

/**
 * Reads background sync state from AsyncStorage telemetry.
 * RULE 5: Does NOT call OS APIs, APNs/FCM, or WorkManager.
 * Updates every 30s to keep display fresh.
 */
export function useBackgroundSyncStatus(): BackgroundSyncStatus {
  const [status, setStatus] = useState<BackgroundSyncStatus>(DEFAULT_STATUS);

  const loadStatus = async () => {
    try {
      const raw = await AsyncStorage.getItem(BG_SYNC_STORAGE_KEY);
      if (!raw) {
        setStatus(DEFAULT_STATUS);
        return;
      }

      const telemetry = JSON.parse(raw) as BgSyncTelemetry;
      setStatus({
        state: telemetry.state,
        lastAttemptAt: telemetry.lastAttemptAt
          ? new Date(telemetry.lastAttemptAt)
          : null,
        itemsSynced: telemetry.itemsSynced,
        retryCount: telemetry.retryCount ?? 0,
      });
    } catch {
      // AsyncStorage read failure — show default (never_run)
      setStatus(DEFAULT_STATUS);
    }
  };

  useEffect(() => {
    void loadStatus();

    // Refresh every 30 seconds to keep display current
    const interval = setInterval(() => {
      void loadStatus();
    }, 30_000);

    return () => clearInterval(interval);
  }, []);

  return status;
}
