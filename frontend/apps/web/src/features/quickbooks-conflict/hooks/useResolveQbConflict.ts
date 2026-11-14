/**
 * useResolveQbConflict — mutation hook for QB conflict resolution
 *
 * Location: apps/web/src/features/quickbooks-conflict/hooks/useResolveQbConflict.ts
 *
 * Established FE-B9. POST /api/v1/integrations/quickbooks/conflicts/{id}/resolve
 * Composes useStalenessRetry; handles auto-recovery 409 scenario.
 *
 * RULE 3: NO voice resolution for QB. This hook has no voice confirm state.
 * RULE 4: server-side diff is canonical.
 */

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useStalenessRetry } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";
import type { QbConflictResolveRequest } from "../types";
import { QB_CONFLICTS_QUERY_KEY } from "./useQbConflicts";
import { QB_CONFLICT_DETAIL_QUERY_KEY } from "./useQbConflictDetail";

export interface UseResolveQbConflictOptions {
  conflictId: string;
  /** Called on auto_recovered 409 — show success toast + navigate to queue */
  onAutoRecovered: (message: string) => void;
}

interface Qb409Response {
  staleness_type: "auto_recovered";
  message: string;
}

async function resolveQbConflict(
  conflictId: string,
  body: QbConflictResolveRequest,
): Promise<void> {
  const payload = {
    resolution: body.resolution,
    expected_pilot_modified_at: body.expected_pilot_modified_at,
    expected_external_modified_at: body.expected_external_modified_at,
    ...(body.per_field_selections
      ? { per_field_selections: body.per_field_selections }
      : {}),
  };

  await apiClient.post(
    `/api/v1/integrations/quickbooks/conflicts/${conflictId}/resolve`,
    payload,
  );
}

export function useResolveQbConflict({
  conflictId,
  onAutoRecovered,
}: UseResolveQbConflictOptions) {
  const queryClient = useQueryClient();

  const handle409 = useCallback(
    (refreshedState: Qb409Response): QbConflictResolveRequest | null => {
      if (refreshedState.staleness_type === "auto_recovered") {
        // Success toast + navigate to queue — no dialog
        onAutoRecovered(refreshedState.message);
        void queryClient.invalidateQueries({
          queryKey: QB_CONFLICTS_QUERY_KEY({}),
        });
        return null;
      }
      return null;
    },
    [queryClient, onAutoRecovered],
  );

  const { mutate, isStalenessDialogOpen, StalenessDialog, mutation } =
    useStalenessRetry<QbConflictResolveRequest, void, Qb409Response>({
      mutationFn: (vars) => resolveQbConflict(conflictId, vars),
      onConflict: handle409,
      dialogTitle:
        "This QuickBooks record was updated while you were viewing it.",
      mutationOptions: {
        onSuccess: () => {
          void queryClient.invalidateQueries({
            queryKey: QB_CONFLICTS_QUERY_KEY({}),
          });
          void queryClient.invalidateQueries({
            queryKey: QB_CONFLICT_DETAIL_QUERY_KEY(conflictId),
          });
        },
      },
    });

  return {
    resolve: mutate,
    isResolving: mutation.isPending,
    isStalenessDialogOpen,
    StalenessDialog,
  };
}
