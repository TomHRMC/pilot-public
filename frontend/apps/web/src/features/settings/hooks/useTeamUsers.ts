/**
 * useTeamUsers — BETA-B4 / STEP 3
 *
 * Location: apps/web/src/features/settings/hooks/useTeamUsers.ts
 *
 * Manages tenant user list + role assignment.
 * GET /api/v1/users — list all users in tenant
 * POST /api/v1/users/{user_id}/role — assign new role
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface TeamUser {
  userId: string;
  email: string;
  roleCode: string;
  roleName: string;
  permissions: string[];
  joinedAt: string | null;
  isActive: boolean;
}

interface TeamUserRaw {
  user_id: string;
  email: string;
  role_code: string;
  role_name: string;
  permissions: string[];
  joined_at: string | null;
  is_active: boolean;
}

export interface UseTeamUsersReturn {
  users: TeamUser[];
  isLoading: boolean;
  isError: boolean;
  assignRole: (userId: string, roleCode: string) => Promise<void>;
  isAssigning: boolean;
}

const QUERY_KEY = ["team-users"] as const;

function normalizeUser(raw: TeamUserRaw): TeamUser {
  return {
    userId: raw.user_id,
    email: raw.email,
    roleCode: raw.role_code,
    roleName: raw.role_name,
    permissions: raw.permissions ?? [],
    joinedAt: raw.joined_at,
    isActive: raw.is_active,
  };
}

export function useTeamUsers(): UseTeamUsersReturn {
  const qc = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async (): Promise<TeamUser[]> => {
      const res = await apiClient.get<TeamUserRaw[]>("/api/v1/users");
      return res.data.map(normalizeUser);
    },
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: async ({
      userId,
      roleCode,
    }: {
      userId: string;
      roleCode: string;
    }) => {
      await apiClient.post(`/api/v1/users/${userId}/role`, {
        role_code: roleCode,
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  return {
    users: data ?? [],
    isLoading,
    isError,
    assignRole: async (userId, roleCode) => {
      await mutation.mutateAsync({ userId, roleCode });
    },
    isAssigning: mutation.isPending,
  };
}
