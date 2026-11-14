"use client";

/**
 * useImpersonationEnd — POST /api/v1/operator/impersonation/end
 *
 * Location: apps/web/src/features/operator/hooks/useImpersonationEnd.ts
 *
 * C-B15 Part B: Ends the active impersonation session. The backend always
 * returns 200 (defensive — client state may have been cleared). The caller
 * clears the local session and triggers a full page reload to /operator/cohort
 * on settle (success or failure).
 *
 * RULE 1.1: endpoint verified in openapi_schema_map.md.
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form.
 */

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

type ImpersonationEndRequest = components["schemas"]["ImpersonationEndRequest"];
type ImpersonationEndResponse =
  components["schemas"]["ImpersonationEndResponse"];

export interface ImpersonationEndVariables {
  tenantId: string;
}

export function useImpersonationEnd() {
  return useMutation<
    ImpersonationEndResponse,
    unknown,
    ImpersonationEndVariables
  >({
    mutationFn: async (vars) => {
      const res = await apiClient.post<ImpersonationEndResponse>(
        "/api/v1/operator/impersonation/end",
        { tenant_id: vars.tenantId } satisfies ImpersonationEndRequest,
      );
      return res.data;
    },
    retry: false,
  });
}
