/**
 * useRequiresPermission — inline permission check hook
 *
 * Location: packages/ui/src/role-gate/useRequiresPermission.ts
 *
 * PLP-FIX-7: Now delegates to useHasPermission (server-authoritative path).
 * The PermissionKey union is retained for compile-time call-site documentation;
 * the matcher boundary accepts string (server may emit keys not in the union).
 *
 * Returns a boolean indicating whether the authenticated user holds
 * the given permission. Use for conditional rendering without a wrapper:
 *
 *   const canApprove = useRequiresPermission('quotes.approve');
 *   {canApprove && <ApproveButton />}
 */

import { useHasPermission } from "./useHasPermission";
import type { PermissionKey } from "./permissions";

export function useRequiresPermission(permission: PermissionKey): boolean {
  return useHasPermission(permission);
}
