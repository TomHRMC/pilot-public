/**
 * useResendInvite — TEAM-INVITE-1
 *
 * Location: apps/web/src/features/settings/hooks/useResendInvite.ts
 *
 * Resends an invite (rotates token + resets expiry). Sends an Idempotency-Key
 * header. Invalidates team-invites + team-users in onSettled.
 *
 * POST /api/v1/users/invites/{invite_id}/resend
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 33: TanStack Query v5 object-form.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { TEAM_INVITES_QUERY_KEY } from "./useTeamInvites";

type TeamInviteResendResponse =
  components["schemas"]["TeamInviteResendResponse"];

const TEAM_USERS_QUERY_KEY = ["team-users"] as const;

export function useResendInvite() {
  const queryClient = useQueryClient();

  return useMutation<TeamInviteResendResponse, Error, string>({
    mutationFn: async (inviteId) => {
      const res = await apiClient.post<TeamInviteResendResponse>(
        `/api/v1/users/invites/${inviteId}/resend`,
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
