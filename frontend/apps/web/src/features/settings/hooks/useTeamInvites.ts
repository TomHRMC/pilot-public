/**
 * useTeamInvites — TEAM-INVITE-1
 *
 * Location: apps/web/src/features/settings/hooks/useTeamInvites.ts
 *
 * Lists all tenant invites (all states). The backend computes the `status`
 * field — we do NOT recompute it client-side.
 *
 * GET /api/v1/users/invites
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 33: TanStack Query v5 object-form; colocated query key.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

type TeamInviteListItem = components["schemas"]["TeamInviteListItem"];

export const TEAM_INVITES_QUERY_KEY = ["team-invites"] as const;

export type TeamInvite = TeamInviteListItem;

export function useTeamInvites() {
  return useQuery({
    queryKey: TEAM_INVITES_QUERY_KEY,
    queryFn: async (): Promise<TeamInviteListItem[]> => {
      const res = await apiClient.get<TeamInviteListItem[]>(
        "/api/v1/users/invites",
      );
      return res.data;
    },
    staleTime: 30_000,
  });
}
