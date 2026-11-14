/**
 * RoleGate — hide-not-disable RBAC wrapper
 *
 * Location: packages/ui/src/role-gate/RoleGate.tsx
 *
 * Renders `children` only when the authenticated user's role matches
 * the `role` prop OR holds the specified `permission`.
 * Returns null otherwise — content is absent from DOM.
 *
 * Usage (role-based):
 *   <RoleGate role="owner">
 *     <OwnerOnlyContent />
 *   </RoleGate>
 *
 *   // Array of roles — renders if user has ANY of the listed roles:
 *   <RoleGate role={['owner', 'office_staff']}>
 *     <AdminContent />
 *   </RoleGate>
 *
 * Usage (permission-based — BETA-B3+):
 *   <RoleGate permission="quotes.view">
 *     <QuotesContent />
 *   </RoleGate>
 *
 * Provide either `role` or `permission` — not both. If both are provided,
 * `permission` takes precedence.
 */

import React from "react";
import { useAuth } from "../auth/useAuth";
import type { PilotRole } from "../auth/types";
import { useHasPermission } from "./useHasPermission";

export interface RoleGateProps {
  /** If array, renders if user has ANY of the listed roles */
  role?: PilotRole | PilotRole[];
  /**
   * Permission key checked via useHasPermission (server-authoritative).
   * Accepts any string — the server may emit keys not in the PermissionKey
   * union (e.g. `schedule.view_all`). PLP-FIX-10: widened from PermissionKey
   * to string to match useHasPermission's `key: string` signature.
   * If provided, renders if the authenticated user holds this permission.
   * Takes precedence over `role` when both are provided.
   */
  permission?: string;
  children: React.ReactNode;
}

export function RoleGate({
  role,
  permission,
  children,
}: RoleGateProps): React.ReactElement | null {
  const { role: userRole } = useAuth();
  // PLP-FIX-7: Always call the hook (Rules of Hooks) — pass a no-op key
  // when permission is not specified so the hook is unconditionally invoked.
  const hasPerm = useHasPermission(permission ?? "");

  if (userRole === null) return null;

  // PLP-FIX-7: Permission-based check via server-authoritative path.
  if (permission !== undefined) {
    if (!hasPerm) return null;
    return <>{children}</>;
  }

  // Role-based check (original behaviour)
  if (role !== undefined) {
    const allowedRoles = Array.isArray(role) ? role : [role];
    if (!allowedRoles.includes(userRole)) return null;
  }

  return <>{children}</>;
}
