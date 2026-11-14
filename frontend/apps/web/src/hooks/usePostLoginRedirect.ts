/**
 * usePostLoginRedirect — web
 *
 * Location: apps/web/src/hooks/usePostLoginRedirect.ts
 *
 * Centralizes role → route mapping. Called after successful login to redirect
 * to the correct destination. For `technician` role on web: signs out and
 * shows an info banner explaining that web is for owners and office staff.
 *
 * C-B11 Part B: After Cognito auth, calls GET /api/v1/operator/auth/me to
 * determine user_type. Platform users are redirected to their redirect_to
 * (typically /operator/cohort). Tenant users go to /dashboard. The auth/me
 * call is best-effort — if it fails, we fall back to the role-based map.
 *
 * PLP-FIX-7: accountant route corrected from /operator/cohort (ADR-0010
 * rename artifact) to /dashboard. Unknown-role fallback no longer defaults
 * to /dashboard — instead signs out + error notification + /login (never
 * default-route to a privileged landing).
 *
 * Role → Route mapping (fallback when auth/me is unavailable):
 *   owner        → /dashboard
 *   technician   → /login (blocked + info banner + sign out after 5s)
 *   office_staff → /dashboard
 *   accountant   → /dashboard
 */

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@pilot/ui/auth";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { apiClient } from "@pilot/shared-api";
import type { PilotRole } from "@pilot/ui/auth";
import type { AuthMeResponse } from "@/features/auth/hooks/useAuthMe";

const ROLE_ROUTE_MAP: Record<Exclude<PilotRole, "technician">, string> = {
  owner: "/dashboard",
  office_staff: "/dashboard",
  // PLP-FIX-7: corrected from /operator/cohort (ADR-0010 rename artifact).
  accountant: "/dashboard",
};

export function usePostLoginRedirect(): {
  redirectForRole: (role: PilotRole) => void;
} {
  const router = useRouter();
  const { signOut } = useAuth();
  const { addNotification } = useNotificationQueue();

  const redirectForRole = useCallback(
    (role: PilotRole) => {
      if (role === "technician") {
        addNotification({
          id: "tech-web-blocked",
          severity: "info",
          title: "The Pilot web app is for owners and office staff.",
          detail: "Please use the mobile app.",
        });
        // Sign out after 5 seconds and redirect to login
        setTimeout(() => {
          void signOut().then(() => {
            router.replace("/login");
          });
        }, 5000);
        return;
      }

      // PLP-FIX-7: Unknown role must never default-route to a privileged
      // landing. If the role is not in ROLE_ROUTE_MAP, sign out + error.
      if (!(role in ROLE_ROUTE_MAP)) {
        addNotification({
          id: "unknown-role-blocked",
          severity: "error",
          title: "Sign-in failed. Please try again.",
          detail:
            "Unrecognized account role. Contact support if this persists.",
        });
        void signOut().then(() => {
          router.replace("/login");
        });
        return;
      }

      // C-B11: Call GET /api/v1/operator/auth/me to get the server-authoritative
      // redirect target. This handles platform users (redirect_to=/operator/cohort)
      // and tenant users (redirect_to=/dashboard). If the call fails, fall back
      // to the role-based map so login never dead-ends.
      void apiClient
        .get<AuthMeResponse>("/api/v1/operator/auth/me")
        .then((res) => {
          const target = res.data.redirect_to || ROLE_ROUTE_MAP[role];
          router.replace(target);
        })
        .catch(() => {
          // Fallback to role-based routing — never dead-end the user
          router.replace(ROLE_ROUTE_MAP[role]);
        });
    },
    [router, signOut, addNotification],
  );

  return { redirectForRole };
}
