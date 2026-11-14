/**
 * useActiveSessions — TanStack Query hook
 *
 * Location: apps/web/src/features/account-settings/hooks/useActiveSessions.ts
 *
 * RULE: Optimistic remove on session revoke (pattern from FE-B7).
 * RULE: Current session cannot be revoked via the list.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { ActiveSession, RevokeOthersResponse } from "../types";
import { apiClient } from "@pilot/shared-api";

const SESSIONS_KEY = ["users", "me", "sessions"] as const;
const BASE = "/api/v1/users/me/sessions";

async function fetchSessions(): Promise<ActiveSession[]> {
  const res = await apiClient.get(BASE);
  return res.data as ActiveSession[];
}

export function useActiveSessions() {
  const queryClient = useQueryClient();

  const {
    data: sessions = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: SESSIONS_KEY,
    queryFn: fetchSessions,
    staleTime: 30_000,
  });

  // Revoke single session — optimistic remove
  const revokeMutation = useMutation({
    mutationFn: async (sessionId: string) => {
      await apiClient.delete(`${BASE}/${sessionId}`);
    },
    onMutate: async (sessionId) => {
      await queryClient.cancelQueries({ queryKey: SESSIONS_KEY });
      const previous = queryClient.getQueryData<ActiveSession[]>(SESSIONS_KEY);
      queryClient.setQueryData<ActiveSession[]>(
        SESSIONS_KEY,
        (old) => old?.filter((s) => s.session_id !== sessionId) ?? [],
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(SESSIONS_KEY, context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: SESSIONS_KEY });
    },
  });

  // Revoke all other sessions
  const revokeOthersMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`${BASE}/revoke-others`);
      return res.data as RevokeOthersResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SESSIONS_KEY });
    },
  });

  return {
    sessions,
    isLoading,
    isError,
    revokeSession: async (sessionId: string) => {
      await revokeMutation.mutateAsync(sessionId);
    },
    revokeOthers: async () => {
      await revokeOthersMutation.mutateAsync();
    },
    isRevoking: revokeMutation.isPending || revokeOthersMutation.isPending,
    revokeError: revokeMutation.error ?? revokeOthersMutation.error,
  };
}
