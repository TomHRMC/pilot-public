/**
 * useResolveCalendarConflict — mutation hook with staleness retry
 *
 * Location: apps/web/src/features/calendar-conflict/hooks/useResolveCalendarConflict.ts
 *
 * POST /api/v1/integrations/calendar/conflicts/{id}/resolve
 * Composes useStalenessRetry for the 409 path.
 * onConflict returns null (forces dialog open, no auto-retry — owner must review updated diff).
 *
 * On success: invalidates ['calendar-conflicts'], ['calendar-conflict', id], ['calendar-status'].
 *
 * Pattern ref: design doc batch-fe-b8-design.md §C.3; mvp-arch.md §16.4
 */

import { useQueryClient } from "@tanstack/react-query";
import { useStalenessRetry } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";
import type { CalendarConflictDetail } from "@pilot/ui";
import type { ConflictResolveRequest, ConflictResolveResponse } from "../types";

export interface ResolveConflictVariables extends ConflictResolveRequest {
  conflictId: string;
}

async function resolveConflict(
  vars: ResolveConflictVariables,
): Promise<ConflictResolveResponse> {
  const { conflictId, ...body } = vars;
  const res = await apiClient.post<ConflictResolveResponse>(
    `/api/v1/integrations/calendar/conflicts/${encodeURIComponent(conflictId)}/resolve`,
    body,
  );
  return res.data;
}

export function useResolveCalendarConflict(conflictId: string) {
  const queryClient = useQueryClient();

  const {
    mutate,
    mutateAsync,
    isStalenessDialogOpen,
    StalenessDialog,
    ...rest
  } = useStalenessRetry<
    ResolveConflictVariables,
    ConflictResolveResponse,
    CalendarConflictDetail
  >({
    mutationFn: resolveConflict,
    // onConflict returns null → force dialog open, no auto-retry.
    // Owner must review updated diff and re-submit explicitly.
    onConflict: () => null,
    renderConflictContent: ({ refreshedState }) => {
      // The parent page will receive the refreshed state via isStalenessDialogOpen
      // and re-render IntegrationConflictResolver with the updated conflict.
      // We return null here; the parent handles the refreshed view.
      void refreshedState;
      return null;
    },
    mutationOptions: {
      onSuccess: () => {
        void queryClient.invalidateQueries({
          queryKey: ["calendar-conflicts"],
        });
        void queryClient.invalidateQueries({
          queryKey: ["calendar-conflict", conflictId],
        });
        void queryClient.invalidateQueries({
          queryKey: ["calendar-status"],
        });
      },
    },
  });

  return {
    mutate,
    mutateAsync,
    isStalenessDialogOpen,
    StalenessDialog,
    ...rest,
  };
}
