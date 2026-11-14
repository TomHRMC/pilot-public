/**
 * useCreateInvite — TEAM-INVITE-1
 *
 * Location: apps/web/src/features/settings/hooks/useCreateInvite.ts
 *
 * Creates + sends a team invite. Sends an Idempotency-Key header (UUID v4).
 * Surfaces RFC 7807 409 bodies (invite_pending_exists, invite_user_exists)
 * to the dialog via getApiProblem (the house RFC 7807 normalizer).
 *
 * PLP-FIX-7: Replaced the hand-rolled envelope parser with getApiProblem.
 * The house convention is FastAPI's nested form: body = {"detail": {type,
 * title, status, detail, invite_id?}}. getApiProblem unwraps the nested
 * `detail` object (Shape A). The `invite_id` passthrough is read from the
 * unwrapped payload (it lives inside the nested detail dict, not at the
 * top level).
 *
 * POST /api/v1/users/invites
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 33: TanStack Query v5 object-form; invalidates team-invites + team-users
 *          in onSettled (acceptance-side consistency).
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, getApiProblem, isAxiosError } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { TEAM_INVITES_QUERY_KEY } from "./useTeamInvites";

type TeamInviteCreateRequest = components["schemas"]["TeamInviteCreateRequest"];
type TeamInviteResponse = components["schemas"]["TeamInviteResponse"];

const TEAM_USERS_QUERY_KEY = ["team-users"] as const;

export interface CreateInviteError {
  type: string;
  title: string;
  status: number;
  detail: string;
  invite_id?: string;
}

export function useCreateInvite() {
  const queryClient = useQueryClient();

  return useMutation<
    TeamInviteResponse,
    CreateInviteError,
    TeamInviteCreateRequest
  >({
    mutationFn: async (payload) => {
      try {
        const res = await apiClient.post<TeamInviteResponse>(
          "/api/v1/users/invites",
          payload,
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
      } catch (error) {
        // PLP-FIX-7: Use the house getApiProblem helper to unwrap the nested
        // RFC 7807 envelope. It handles all three FastAPI body shapes and
        // never throws. The `invite_id` passthrough lives inside the nested
        // detail dict — extract it from the raw response data.
        const problem = getApiProblem(error);

        // Extract invite_id from the nested detail object (Shape A) or the
        // top-level body (MSW fixtures that don't nest). getApiProblem doesn't
        // surface arbitrary extension fields, so we read it directly.
        let invite_id: string | undefined;
        if (isAxiosError(error) && error.response) {
          const data = error.response.data as Record<string, unknown>;
          const detail = data?.detail;
          if (detail && typeof detail === "object" && !Array.isArray(detail)) {
            const nested = detail as Record<string, unknown>;
            invite_id =
              typeof nested.invite_id === "string"
                ? nested.invite_id
                : undefined;
          } else if (typeof data.invite_id === "string") {
            invite_id = data.invite_id;
          }
        }

        throw {
          type: problem.type ?? "",
          title: problem.title ?? "",
          status: problem.status,
          detail: problem.detail ?? "Something went wrong.",
          invite_id,
        } as CreateInviteError;
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: TEAM_INVITES_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: TEAM_USERS_QUERY_KEY });
    },
  });
}
