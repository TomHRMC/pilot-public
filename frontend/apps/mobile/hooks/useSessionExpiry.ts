/**
 * useSessionExpiry — mobile
 *
 * Location: apps/mobile/hooks/useSessionExpiry.ts
 *
 * Subscribes to auth:session-expired events via a global EventEmitter
 * (React Native doesn't have window.dispatchEvent). On event: enqueues
 * a critical NotificationBanner and calls signOut() + redirects to login.
 *
 * NOTE: For React Native we use NativeEventEmitter or a shared EventEmitter
 * singleton. Since apiClient uses window.dispatchEvent (web-compatible) and
 * React Native doesn't have window, we use a simple polling-compatible
 * approach using a module-level emitter.
 *
 * FE-B2: design doc §F.3 useSessionExpiry (mobile)
 */

import { useEffect } from "react";
import { useRouter } from "expo-router";
import { useAuth } from "@pilot/ui/auth";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { sessionExpiredEmitter } from "./sessionExpiredEmitter";

export function useSessionExpiry(): void {
  const router = useRouter();
  const { signOut } = useAuth();
  const { addNotification } = useNotificationQueue();

  useEffect(() => {
    const subscription = sessionExpiredEmitter.addListener(
      "auth:session-expired",
      () => {
        addNotification({
          id: "session-expired",
          severity: "critical",
          title: "Your session expired — please sign in again.",
        });
        void signOut().then(() => {
          router.replace("/(auth)/login");
        });
      },
    );

    return () => {
      subscription.remove();
    };
  }, [router, signOut, addNotification]);
}
