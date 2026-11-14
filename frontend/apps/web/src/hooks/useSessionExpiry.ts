/**
 * useSessionExpiry — web
 *
 * Location: apps/web/src/hooks/useSessionExpiry.ts
 *
 * Subscribes to the `auth:session-expired` custom event emitted by apiClient
 * on unrecoverable 401 (refresh failed). On event: enqueues a critical
 * NotificationBanner and calls signOut() + redirects to /login.
 *
 * Usage: call once at the top of the authenticated layout.
 * No return value — side-effects only.
 *
 * FE-B2: Part of the session expiry flow described in design doc §A.2 and §F.3
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@pilot/ui/auth";
import { useNotificationQueue } from "@pilot/ui/notification-banner";

export function useSessionExpiry(): void {
  const router = useRouter();
  const { signOut } = useAuth();
  const { addNotification } = useNotificationQueue();

  useEffect(() => {
    async function handleSessionExpired() {
      addNotification({
        id: "session-expired",
        severity: "critical",
        title: "Your session expired — please sign in again.",
        detail: undefined,
      });
      await signOut();
      router.replace("/login");
    }

    const listener = () => {
      void handleSessionExpired();
    };

    window.addEventListener("auth:session-expired", listener);
    return () => {
      window.removeEventListener("auth:session-expired", listener);
    };
  }, [router, signOut, addNotification]);
}
