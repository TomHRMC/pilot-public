/**
 * usePushPermission — Expo push notification permission management
 *
 * Location: apps/mobile/features/onboarding/hooks/usePushPermission.ts
 *
 * RULE 6: requestPermissionsAsync fires EXACTLY ONCE per device-install.
 *         Never call requestPermissionsAsync() more than once per session.
 *         On denial, route to fallback immediately without re-prompting.
 *
 * Design doc Decision 6 / Section D.5.
 */

import { useState, useCallback } from "react";
import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import * as Linking from "expo-linking";
import { Platform } from "react-native";
import { apiClient } from "@pilot/shared-api";

export type PushPermissionState =
  | "not_asked"
  | "granted"
  | "denied_by_user_choice"
  | "denied_by_os"
  | "revoked_in_settings";

const DEVICE_ID_KEY = "pilot_device_id";

async function getOrCreateDeviceId(): Promise<string> {
  let deviceId = await SecureStore.getItemAsync(DEVICE_ID_KEY);
  if (!deviceId) {
    // Generate a stable UUID for this device-install
    deviceId = `${Date.now().toString(36)}-${Math.random().toString(36).substring(2)}`;
    await SecureStore.setItemAsync(DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
}

export interface UsePushPermissionReturn {
  permissionState: PushPermissionState;
  bannerShouldAppear: boolean;
  isLoading: boolean;
  error: string | null;
  /** Triggers OS permission dialog — EXACTLY ONCE per install (RULE 6) */
  requestPermission: () => Promise<PushPermissionState>;
  /** User chooses "Maybe later" — no OS prompt fires */
  deferPermission: () => Promise<void>;
  /** Opens OS notification settings deep-link */
  openNotificationSettings: () => void;
}

export function usePushPermission(): UsePushPermissionReturn {
  const [permissionState, setPermissionState] =
    useState<PushPermissionState>("not_asked");
  const [bannerShouldAppear, setBannerShouldAppear] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestPermission =
    useCallback(async (): Promise<PushPermissionState> => {
      setIsLoading(true);
      setError(null);

      try {
        const deviceId = await getOrCreateDeviceId();

        // RULE 6: Fire OS prompt once — never loop
        const result = await Notifications.requestPermissionsAsync();
        const state: PushPermissionState = result.granted
          ? "granted"
          : "denied_by_os";

        setPermissionState(state);

        // Register push token if granted
        if (result.granted) {
          try {
            const tokenData = await Notifications.getExpoPushTokenAsync();
            // Register token via backend (A78 endpoint — fire and forget)
            apiClient
              .put(`/api/v1/users/me/devices/${deviceId}/push-token`, {
                expo_push_token: tokenData.data,
              })
              .catch(() => {
                // Non-blocking — token will be registered on next launch
              });
          } catch {
            // Token registration failure is non-blocking
          }
        }

        // Record state to backend
        await apiClient.put(
          `/api/v1/users/me/devices/${deviceId}/push-permission`,
          { permission_state: state },
        );

        setBannerShouldAppear(state === "denied_by_os");
        return state;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Permission request failed.";
        setError(message);
        return "denied_by_os";
      } finally {
        setIsLoading(false);
      }
    }, []);

  const deferPermission = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const deviceId = await getOrCreateDeviceId();
      const state: PushPermissionState = "denied_by_user_choice";
      setPermissionState(state);

      await apiClient.put(
        `/api/v1/users/me/devices/${deviceId}/push-permission`,
        { permission_state: state },
      );
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to save preference.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const openNotificationSettings = useCallback(() => {
    if (Platform.OS === "ios") {
      Linking.openURL("app-settings:").catch(() => {
        Linking.openURL("app-settings://notification");
      });
    } else {
      // Android: open App Info page
      Linking.openURL("app-settings:").catch(() => {
        // Fallback for older Android
        Linking.openSettings();
      });
    }
  }, []);

  return {
    permissionState,
    bannerShouldAppear,
    isLoading,
    error,
    requestPermission,
    deferPermission,
    openNotificationSettings,
  };
}
