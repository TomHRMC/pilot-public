"use client";
/**
 * useTenantUsers — Fetch all active users for the current tenant.
 *
 * Location: apps/web/src/features/users/hooks/useTenantUsers.ts
 *
 * Endpoint: GET /api/v1/users
 * Response: TenantUserWithRoleResponse[] (array, not paginated)
 * Fields: user_id, email, role_code, role_name, permissions, joined_at,
 *         is_active, first_name, last_name, display_color
 *
 * Added by: UI-FIX-2B React Engineer
 */

import { apiClient } from "@pilot/shared-api";
import { useQuery } from "@tanstack/react-query";

export interface TenantUserItem {
  user_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  display_color: string | null;
  role_code: string;
  role_name: string;
  is_active: boolean;
  /** Computed: "First Last" or email fallback */
  display_name: string;
}

export const TENANT_USERS_QUERY_KEY = ["tenant-users"] as const;

export function useTenantUsers() {
  return useQuery({
    queryKey: TENANT_USERS_QUERY_KEY,
    queryFn: async (): Promise<TenantUserItem[]> => {
      const resp = await apiClient.get("/api/v1/users");
      // GET /api/v1/users returns a plain array (not paginated)
      const rawData: unknown = resp.data;
      const rawArray: Record<string, unknown>[] = Array.isArray(rawData)
        ? (rawData as Record<string, unknown>[])
        : ((rawData as { items?: Record<string, unknown>[] }).items ?? []);
      return rawArray.map((u) => ({
        user_id: String(u.user_id ?? ""),
        email: String(u.email ?? ""),
        first_name: (u.first_name as string | null) ?? null,
        last_name: (u.last_name as string | null) ?? null,
        display_color: (u.display_color as string | null) ?? null,
        role_code: String(u.role_code ?? ""),
        role_name: String(u.role_name ?? ""),
        is_active: Boolean(u.is_active ?? true),
        display_name:
          [u.first_name as string | null, u.last_name as string | null]
            .filter(Boolean)
            .join(" ")
            .trim() || String(u.email ?? ""),
      }));
    },
    staleTime: 60_000,
  });
}
