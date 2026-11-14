/**
 * backgroundSync — MOB-B8 Part B
 *
 * Location: apps/mobile/lib/backgroundSync.ts
 *
 * Registers the PILOT_BACKGROUND_SYNC background task with expo-task-manager.
 * MUST be imported in app/_layout.tsx before TaskManager/BackgroundFetch usage
 * so the task definition is registered before the OS first invokes it.
 *
 * Task budget: 25s max (iOS BGAppRefreshTask hard limit is 30s; 5s buffer).
 *
 * Conflict handling in background: auto-resolve only (design doc §G).
 * Cannot show conflict UI when app is closed — defer to foreground.
 */

import { Platform } from "react-native";
import * as TaskManager from "expo-task-manager";
import * as BackgroundFetch from "expo-background-fetch";
import NetInfo from "@react-native-community/netinfo";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { apiClient } from "@pilot/shared-api";
import { SyncOrchestrator } from "../database/sync/orchestrator";

export const BACKGROUND_SYNC_TASK_NAME = "PILOT_BACKGROUND_SYNC";

/** Maximum time budget — leave 5s buffer below iOS 30s hard cap */
const BACKGROUND_SYNC_TIMEOUT_MS = 25_000;

const DEVICE_ID_KEY = "pilot_device_id";
const WIFI_ONLY_CACHE_KEY = "pilot_bg_sync_wifi_only";

// Only define the task on native — web does not support BGAppRefresh or WorkManager.
// On web the import is a no-op (TaskManager.defineTask is a no-op on web platform).
if (Platform.OS !== "web") {
  TaskManager.defineTask(BACKGROUND_SYNC_TASK_NAME, async () => {
    try {
      // 1. Check connectivity — skip if offline
      const netState = await NetInfo.fetch();
      if (!netState.isConnected) {
        return BackgroundFetch.BackgroundFetchResult.NoData;
      }

      // 2. WiFi-only check (client-side enforcement, MVP: reads cached AsyncStorage)
      //    Default: allow sync on cache miss (safe fallback per design doc §G)
      const wifiOnlyCached = await AsyncStorage.getItem(WIFI_ONLY_CACHE_KEY);
      if (wifiOnlyCached === "true" && netState.type !== "wifi") {
        return BackgroundFetch.BackgroundFetchResult.NoData;
      }

      // 3. Get stable device ID (created by usePushTokenRegistration on first open)
      const deviceId =
        (await AsyncStorage.getItem(DEVICE_ID_KEY)) ?? "background-device";

      // 4. Lazily require the database singleton to avoid crashing the web bundle.
      //    (WatermelonDB's SQLiteAdapter is native-only — see database/index.ts §adapter)
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { database } = require("../database") as {
        database: import("@nozbe/watermelondb").Database;
      };

      // 5. Instantiate orchestrator using the module-level apiClient singleton.
      //    apiClient satisfies the { post, get } shape required by SyncOrchestrator.
      const orchestrator = new SyncOrchestrator({
        database,
        // apiClient from @pilot/shared-api is an Axios instance whose .post/.get
        // signatures are compatible with SyncOrchestrator's internal ApiClient type.
        apiClient: apiClient as unknown as ConstructorParameters<
          typeof SyncOrchestrator
        >[0]["apiClient"],
        deviceId,
      });

      // 6. Run sync with a hard timeout so we never exceed iOS BGAppRefreshTask limit
      await Promise.race([
        orchestrator.sync("background"),
        new Promise<never>((_, reject) =>
          setTimeout(
            () => reject(new Error("background sync timeout")),
            BACKGROUND_SYNC_TIMEOUT_MS,
          ),
        ),
      ]);

      return BackgroundFetch.BackgroundFetchResult.NewData;
    } catch (err) {
      console.warn("[BACKGROUND_SYNC] error:", err);
      return BackgroundFetch.BackgroundFetchResult.Failed;
    }
  });
}
