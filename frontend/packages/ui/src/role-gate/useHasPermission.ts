/**
 * useHasPermission — server-authoritative permission check hook
 *
 * Location: packages/ui/src/role-gate/useHasPermission.ts
 *
 * PLP-FIX-7: Reads the server-set permissions array from the auth context
 * and delegates to hasPermission() (wildcard matcher). This is the primary
 * gating hook — useRequiresPermission and RoleGate both delegate here.
 *
 * Defensive fallback: when user != null but permissions.length === 0
 * (should not occur outside mock mode), falls back to the static
 * ROLE_PERMISSION_MAP and logs a console warning once.
 *
 * Usage:
 *   const canViewReports = useHasPermission("reports.view");
 *   {canViewReports && <ReportsContent />}
 */

import { useAuth } from "../auth/useAuth";
import { hasPermission, ROLE_PERMISSION_MAP } from "./permissions";

// Track whether the fallback warning has been emitted (once per session).
let fallbackWarningEmitted = false;

export function useHasPermission(key: string): boolean {
  const { user, permissions } = useAuth();

  if (user === null) return false;

  // Primary path: server-authoritative permissions (when provided)
  if (permissions && permissions.length > 0) {
    return hasPermission(permissions, key);
  }

  // Defensive fallback: user is set but no server permissions loaded
  // (undefined or empty). This occurs in test mocks that don't set
  // permissions, and should not occur in production (the provider always
  // sets it). Fall back to the static map and warn once.
  if (!fallbackWarningEmitted) {
    console.warn(
      "[useHasPermission] User is authenticated but permissions array is empty. " +
        "Falling back to static ROLE_PERMISSION_MAP. This should not occur in production.",
    );
    fallbackWarningEmitted = true;
  }

  return ROLE_PERMISSION_MAP[user.role].has(key as never);
}
