/**
 * usePushTokenRegistration — MOB-B8 Part B
 *
 * Location: apps/mobile/hooks/usePushTokenRegistration.ts
 *
 * Registers the device's Expo push token with the backend on app mount.
 * Uses upsert — safe to call on every app open (server deduplicates by device_id).
 * Silent failure: push registration is best-effort and must never block app startup.
 *
 * Endpoint: POST /api/v1/mobile/push-tokens (confirmed in openapi_schema_map.md)
 */

import { useEffect } from "react";
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { apiClient } from "@pilot/shared-api";

const DEVICE_ID_KEY = "pilot_device_id";

async function getOrCreateDeviceId(): Promise<string> {
  const existing = await AsyncStorage.getItem(DEVICE_ID_KEY);
  if (existing) return existing;
  const newId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  await AsyncStorage.setItem(DEVICE_ID_KEY, newId);
  return newId;
}

export function usePushTokenRegistration(): void {
  useEffect(() => {
    // Guard: only run on native (iOS/Android) or web mock auth dev builds.
    // On native, Platform.OS === 'ios' | 'android'; skip on 'web' — no native push.
    if (Platform.OS === "web") return;

    const register = async () => {
      try {
        // 1. Check notification permission — skip silently if not granted
        const { status } = await Notifications.getPermissionsAsync();
        if (status !== "granted") return;

        // 2. Retrieve the Expo push token
        const tokenData = await Notifications.getExpoPushTokenAsync();
        const pushToken = tokenData.data;

        // 3. Get or create a stable device ID stored in AsyncStorage
        const deviceId = await getOrCreateDeviceId();

        // 4. Determine platform string for backend
        const platform: "ios" | "android" =
          Platform.OS === "ios" ? "ios" : "android";

        // 5. Register with backend (upsert — safe to call every app open)
        await apiClient.post("/api/v1/mobile/push-tokens", {
          device_id: deviceId,
          platform,
          push_token: pushToken,
        });
      } catch (err) {
        // Silent failure — push registration is best-effort; never block app startup
        console.warn("[usePushTokenRegistration] failed:", err);
      }
    };

    register();
  }, []); // runs once on mount
}
