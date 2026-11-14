/**
 * Auth API hooks — TanStack Query hooks for auth-related FastAPI endpoints
 *
 * Location: packages/shared-api/src/auth.ts
 *
 * FE-B2: useGetCurrentUser fetches the authenticated user profile from
 * GET /api/v1/users/me/permissions — returns role_code + tenant_id from local DB.
 *
 * Authorization model: Cognito is identity-only; role comes from the DB.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CurrentUserApiResponse {
  user_id: string;
  tenant_id: string;
  email: string;
  display_name: string;
  /** Role from local DB — NOT from Cognito JWT claims */
  role: "owner" | "tech" | "office_staff" | "operator";
}

// Internal shape from /api/v1/users/me/permissions
interface UserPermissionsApiResponse {
  user_id: string;
  tenant_id: string;
  role_code: "owner" | "tech" | "office_staff" | "operator";
  role_name: string;
  permissions: string[];
}

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const AUTH_QUERY_KEYS = {
  currentUser: ["auth", "currentUser"] as const,
};

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * useGetCurrentUser
 *
 * Fetches the authenticated user role from the backend DB via
 * GET /api/v1/users/me/permissions. Used after successful login
 * to hydrate role into TanStack Query cache before redirect.
 *
 * staleTime: 5 min — role doesn't change mid-session.
 * retry: false — don't retry auth errors (401 means session is invalid).
 */
export function useGetCurrentUser() {
  return useQuery({
    queryKey: AUTH_QUERY_KEYS.currentUser,
    queryFn: async (): Promise<CurrentUserApiResponse> => {
      const { data } = await apiClient.get<UserPermissionsApiResponse>(
        "/api/v1/users/me/permissions",
      );
      return {
        user_id: data.user_id,
        tenant_id: data.tenant_id,
        // role_code comes from local DB — not from Cognito JWT claims
        role: data.role_code,
        email: "",
        display_name: data.role_name,
      };
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
