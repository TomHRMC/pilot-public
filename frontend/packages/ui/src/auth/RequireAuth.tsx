/**
 * RequireAuth — route guard component (platform-agnostic)
 *
 * Location: packages/ui/src/auth/RequireAuth.tsx
 *
 * Renders `children` when the user is authenticated.
 * Redirects to `redirectTo` when not authenticated.
 *
 * Web: redirectTo = '/login'
 * Mobile: redirectTo = '/(auth)/login' (or equivalent)
 *
 * FE-B2: Added `onRedirect` prop for testable, framework-agnostic redirect.
 * Web consumer passes router.replace from next/navigation.
 * Mobile consumer passes router.replace from expo-router.
 */

"use client";

import React, { useEffect } from "react";
import { useAuth } from "./useAuth";
import type { RequireAuthProps } from "./types";

export function RequireAuth({
  children,
  redirectTo,
  onRedirect,
}: RequireAuthProps) {
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) {
      if (onRedirect) {
        onRedirect(redirectTo);
      } else if (typeof window !== "undefined") {
        // Fallback for test compatibility when no onRedirect is provided
        window.location.replace(redirectTo);
      }
    }
  }, [isAuthenticated, redirectTo, onRedirect]);

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
