/**
 * usePostLoginRedirect — mobile
 *
 * Location: apps/mobile/hooks/usePostLoginRedirect.ts
 *
 * Centralizes role → navigation mapping for mobile. Called after successful
 * login to navigate to the correct destination.
 *
 * All roles navigate to the Home tab (tabs)/index.
 * Mobile has no web-only restriction for tech role.
 *
 * FE-B2: design doc §F.4 usePostLoginRedirect (mobile)
 */

import { useCallback } from "react";
import { useRouter } from "expo-router";
import type { PilotRole } from "@pilot/ui/auth";

export function usePostLoginRedirect(): {
  navigateForRole: (role: PilotRole) => void;
} {
  const router = useRouter();

  const navigateForRole = useCallback(
    (_role: PilotRole) => {
      // All roles land on the Home tab on mobile.
      // The home tab is the (home) route group — not an index.tsx in (tabs)/.
      // Cast to `never` to satisfy Expo Router's strict generated route types
      // while keeping the intended navigation target.
      router.replace("/(tabs)/(home)" as never);
    },
    [router],
  );

  return { navigateForRole };
}
