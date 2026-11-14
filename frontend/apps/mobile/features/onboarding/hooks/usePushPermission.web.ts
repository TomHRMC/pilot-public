/**
 * usePushPermission — Web stub (no-op)
 *
 * Location: apps/mobile/features/onboarding/hooks/usePushPermission.web.ts
 *
 * Metro resolves this file instead of usePushPermission.ts when bundling for web.
 * expo-notifications' web shim (ServerRegistrationModule.web.js) calls
 * localStorage.getItem synchronously at module load time, which crashes in Node.js
 * during Metro bundling. This stub prevents expo-notifications from being
 * evaluated at all on the web platform.
 *
 * Push notifications are a native-only feature — this stub returns a no-op
 * that renders the onboarding screen without push permission functionality.
 */

export type PushPermissionState =
  | "not_asked"
  | "granted"
  | "denied_by_user_choice"
  | "denied_by_os"
  | "revoked_in_settings";

export interface UsePushPermissionReturn {
  permissionState: PushPermissionState;
  bannerShouldAppear: boolean;
  isLoading: boolean;
  error: string | null;
  requestPermission: () => Promise<PushPermissionState>;
  deferPermission: () => Promise<void>;
  openNotificationSettings: () => void;
}

/**
 * Web no-op — push notifications are native-only.
 * Returns stable state values; callbacks are no-ops.
 */
export function usePushPermission(): UsePushPermissionReturn {
  return {
    permissionState: "not_asked",
    bannerShouldAppear: false,
    isLoading: false,
    error: null,
    requestPermission: async () => "not_asked" as const,
    deferPermission: async () => {},
    openNotificationSettings: () => {},
  };
}
