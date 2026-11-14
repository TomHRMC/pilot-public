"use client";

/**
 * SignupCompletionGuard — SIGNUP-UI-FIX-1
 *
 * Location: apps/web/src/components/SignupCompletionGuard.tsx
 *
 * Rendered inside (authed)/layout.tsx after RequireAuth. Fetches
 * GET /api/v1/signup/{tenantId}/state. If signup_state !== 'complete',
 * redirects to the correct wizard step. This prevents a partially-onboarded
 * user from landing on /dashboard with an incomplete tenant setup.
 *
 * - Only fires when user.tenantId is available (post-login).
 * - Uses TanStack Query with staleTime: 0 (always refetch on mount — signup
 *   state is short-lived and changes during onboarding).
 * - Renders null while checking (the layout shows nothing for a brief moment).
 * - On fetch error: fail open to dashboard (don't block a fully-onboarded user
 *   if the signup endpoint is temporarily unavailable).
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import {
  signupStateToStep,
  stepToUrl,
  type WizardSignupState,
} from "@/features/signup/types";

export function SignupCompletionGuard({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user } = useAuth();
  const tenantId = user?.tenantId;

  const { data, isPending, isError } = useQuery({
    queryKey: ["signup-state-guard", tenantId],
    queryFn: async () => {
      const res = await apiClient.get<{
        signup_state: WizardSignupState;
      }>(`/api/v1/signup/${tenantId}/state`);
      return res.data;
    },
    enabled: !!tenantId,
    staleTime: 0, // always refetch on mount
    retry: false,
  });

  useEffect(() => {
    if (!tenantId || isPending) return;

    if (isError) {
      // Fail open — let the user through to the dashboard. A fully-onboarded
      // user should not be blocked by a transient signup-state endpoint failure.
      return;
    }

    const currentState = data?.signup_state;
    if (currentState && currentState !== "complete") {
      const targetStep = signupStateToStep[currentState];
      const targetUrl = stepToUrl[targetStep] ?? "/signup/account";
      router.replace(targetUrl);
    }
  }, [tenantId, isPending, isError, data, router]);

  // While checking (and user has a tenantId), render nothing to prevent
  // flashing the dashboard before the redirect fires.
  if (tenantId && isPending) {
    return null;
  }

  // If no tenantId (shouldn't happen post-RequireAuth, but defensive),
  // or state is complete, or we're failing open — render children.
  return <>{children}</>;
}
