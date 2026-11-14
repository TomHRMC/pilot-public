"use client";

/**
 * useImpersonationStart — POST /api/v1/operator/impersonation/start
 *
 * Location: apps/web/src/features/operator/hooks/useImpersonationStart.ts
 *
 * C-B15 Part B: Starts an impersonation session as the selected tenant's
 * owner. On success, the caller writes the session to the impersonation
 * store and triggers a full page reload to /dashboard.
 *
 * RULE 1.1: endpoint verified in openapi_schema_map.md.
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form.
 */

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

type ImpersonationStartRequest =
  components["schemas"]["ImpersonationStartRequest"];
type ImpersonationSessionResponse =
  components["schemas"]["ImpersonationSessionResponse"];

export interface ImpersonationStartVariables {
  tenantId: string;
}

export function useImpersonationStart() {
  return useMutation<
    ImpersonationSessionResponse,
    unknown,
    ImpersonationStartVariables
  >({
    mutationFn: async (vars) => {
      const res = await apiClient.post<ImpersonationSessionResponse>(
        "/api/v1/operator/impersonation/start",
        { tenant_id: vars.tenantId } satisfies ImpersonationStartRequest,
      );
      return res.data;
    },
    retry: false,
  });
}
