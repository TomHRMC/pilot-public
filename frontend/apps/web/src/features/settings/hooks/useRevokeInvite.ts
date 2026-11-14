/**
 * useRevokeInvite — TEAM-INVITE-1
 *
 * Location: apps/web/src/features/settings/hooks/useRevokeInvite.ts
 *
 * Revokes an invite (sets is_active=false). Sends an Idempotency-Key header.
 * Invalidates team-invites + team-users in onSettled.
 *
 * POST /api/v1/users/invites/{invite_id}/revoke
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 33: TanStack Query v5 object-form.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { TEAM_INVITES_QUERY_KEY } from "./useTeamInvites";

type TeamInviteRevokeResponse =
  components["schemas"]["TeamInviteRevokeResponse"];

const TEAM_USERS_QUERY_KEY = ["team-users"] as const;

export function useRevokeInvite() {
  const queryClient = useQueryClient();

  return useMutation<TeamInviteRevokeResponse, Error, string>({
    mutationFn: async (inviteId) => {
      const res = await apiClient.post<TeamInviteRevokeResponse>(
        `/api/v1/users/invites/${inviteId}/revoke`,
        {},
        {
          headers: {
            "Idempotency-Key":
              typeof crypto !== "undefined" && crypto.randomUUID
                ? crypto.randomUUID()
                : `idem-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          },
        },
      );
      return res.data;
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: TEAM_INVITES_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: TEAM_USERS_QUERY_KEY });
    },
  });
}
