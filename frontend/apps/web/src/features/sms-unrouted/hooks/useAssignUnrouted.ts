/**
 * useAssignUnrouted — Mutation to assign an unrouted message to a customer + tech
 *
 * Location: apps/web/src/features/sms-unrouted/hooks/useAssignUnrouted.ts
 *
 * API: POST /api/v1/communications/unrouted/{id}/assign
 * Cache invalidation: ['unrouted-messages'] on success
 *
 * Design doc Section C.9, A.2.3
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

interface UnroutedAssignRequest {
  customer_id: string;
  tech_id: string;
}

interface UnroutedAssignResponse {
  thread_id: string;
  message_id: string;
  customer_name: string;
  tech_name: string;
}

async function assignUnrouted(
  id: string,
  request: UnroutedAssignRequest,
): Promise<UnroutedAssignResponse> {
  const res = await apiClient.post(
    `/api/v1/communications/unrouted/${id}/assign`,
    request,
  );
  return res.data as UnroutedAssignResponse;
}

export function useAssignUnrouted() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      request,
    }: {
      id: string;
      request: UnroutedAssignRequest;
    }) => assignUnrouted(id, request),
    onSuccess: () => {
      // Entry removed from unrouted queue
      void queryClient.invalidateQueries({ queryKey: ["unrouted-messages"] });
    },
  });
}
