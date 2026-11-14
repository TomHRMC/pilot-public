/**
 * useMobileOnboarding — First-time detection for mobile onboarding flow
 *
 * Location: apps/mobile/hooks/useMobileOnboarding.ts
 *
 * Design doc Section D.6: On every app launch after authentication,
 * reads GET /api/v1/users/me/devices/{deviceId}/push-permission.
 * If permission_state === 'not_asked' → routes to (onboarding)/welcome.
 * Otherwise → goes directly to (tabs)/(home).
 *
 * device_id is stable across app restarts via expo-secure-store.
 */

import { useState, useEffect, useCallback } from "react";
import * as SecureStore from "expo-secure-store";
import { apiClient } from "@pilot/shared-api";

const DEVICE_ID_KEY = "pilot_device_id";

async function getOrCreateDeviceId(): Promise<string> {
  let deviceId = await SecureStore.getItemAsync(DEVICE_ID_KEY);
  if (!deviceId) {
    deviceId = `${Date.now().toString(36)}-${Math.random().toString(36).substring(2)}`;
    await SecureStore.setItemAsync(DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
}

export interface UseMobileOnboardingReturn {
  shouldShowOnboarding: boolean;
  isChecking: boolean;
  deviceId: string | null;
}

export function useMobileOnboarding(): UseMobileOnboardingReturn {
  const [shouldShowOnboarding, setShouldShowOnboarding] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [deviceId, setDeviceId] = useState<string | null>(null);

  const checkOnboardingStatus = useCallback(async () => {
    setIsChecking(true);
    try {
      const id = await getOrCreateDeviceId();
      setDeviceId(id);

      const response = await apiClient.get(
        `/api/v1/users/me/devices/${id}/push-permission`,
      );
      const permissionState = response.data?.permission_state;

      // Only show onboarding if the OS permission has never been asked
      setShouldShowOnboarding(permissionState === "not_asked");
    } catch {
      // On error (e.g., new device not registered yet): show onboarding
      setShouldShowOnboarding(true);
    } finally {
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    checkOnboardingStatus();
  }, [checkOnboardingStatus]);

  return { shouldShowOnboarding, isChecking, deviceId };
}
