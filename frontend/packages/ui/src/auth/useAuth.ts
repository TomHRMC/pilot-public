/**
 * useAuth — reads from AuthContext
 *
 * Location: packages/ui/src/auth/useAuth.ts
 *
 * Must be called inside <AuthProvider>. Throws a descriptive error
 * (in development) if used outside the provider boundary.
 */

import { useContext } from "react";
import { AuthContext } from "./AuthProvider";
import type { AuthContextValue } from "./types";

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);

  if (ctx === null) {
    throw new Error(
      "[useAuth] must be used inside <AuthProvider>. " +
        "Ensure your component tree is wrapped with <AuthProvider>.",
    );
  }

  return ctx;
}
