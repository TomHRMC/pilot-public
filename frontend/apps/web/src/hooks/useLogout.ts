/**
 * useLogout — web
 *
 * Location: apps/web/src/hooks/useLogout.ts
 *
 * Clears JWT, clears TanStack Query cache, redirects to /login?signedOut=true.
 * Design doc §G.6: silent redirect + 6-second info banner on login page.
 *
 * FE-B2: logout wiring (web)
 */

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@pilot/ui/auth";

export function useLogout(): { logout: () => Promise<void> } {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { signOut } = useAuth();

  const logout = useCallback(async () => {
    // Clear all cached tenant data before redirect
    queryClient.clear();
    await signOut();
    router.replace("/login?signedOut=true");
  }, [router, queryClient, signOut]);

  return { logout };
}
