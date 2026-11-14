/**
 * useMoveJob — Dispatch board job move mutation with staleness retry
 *
 * Location: apps/web/src/features/dispatch-board/hooks/useMoveJob.ts
 *
 * DISPATCH-B1: Rewritten to use the real /scheduling/jobs/{id}/move endpoint.
 * Single atomic reassign+reschedule — the old reschedule/assign split is removed.
 *
 * POST /api/v1/scheduling/jobs/{id}/move
 * Body: { tech_user_id, scheduled_start_at, scheduled_end_at, expected_job_version, expected_assignment_version? }
 * Response: { job_id, job_version, assignment_id, assignment_version, tech_user_id, scheduled_start_at, scheduled_end_at, conflicts[] }
 * 409 body (RFC7807): { ..., current_job_version, current_state: { scheduled_start_at, scheduled_end_at } }
 *
 * mutationKey: ["moveJob"] — the toolbar's InFlightSyncIndicator counts this key; do NOT rename.
 *
 * Per DISPATCH-B1 design doc §D.2, §E (pattern §16.4 pre-commit staleness)
 */

"use client";

import React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useStalenessRetry } from "@pilot/ui/hooks";
import { DISPATCH_BOARD_QUERY_KEY } from "./useDispatchBoard";
import { apiClient } from "@pilot/shared-api";

// ─── Request / Response types ────────────────────────────────────────────────

export interface MoveJobVariables {
  jobId: string;
  tech_user_id: string;
  scheduled_start_at: string; // ISO 8601
  scheduled_end_at: string; // ISO 8601
  expected_job_version: number; // optimistic lock version from DispatchBoardJobEntry.version
  expected_assignment_version?: number | null; // from DispatchBoardJobEntry.assignment_version
}

export interface MoveJobResponse {
  job_id: string;
  job_version: number;
  assignment_id: string;
  assignment_version: number;
  tech_user_id: string;
  scheduled_start_at: string;
  scheduled_end_at: string;
  conflicts: unknown[];
}

/** Shape of the 409 RFC7807 body for /move */
interface RefreshedJobState {
  current_job_version: number;
  current_state: {
    scheduled_start_at: string;
    scheduled_end_at: string;
  };
}

// ─── Mutation function ────────────────────────────────────────────────────────

async function moveJobFn(
  variables: MoveJobVariables,
): Promise<MoveJobResponse> {
  const {
    jobId,
    tech_user_id,
    scheduled_start_at,
    scheduled_end_at,
    expected_job_version,
    expected_assignment_version,
  } = variables;

  const body: Record<string, unknown> = {
    tech_user_id,
    scheduled_start_at,
    scheduled_end_at,
    expected_job_version,
  };
  if (expected_assignment_version != null) {
    body.expected_assignment_version = expected_assignment_version;
  }

  const res = await apiClient.post<MoveJobResponse>(
    `/api/v1/scheduling/jobs/${jobId}/move`,
    body,
  );
  return res.data;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useMoveJob(activeDate: string, endDate: string) {
  const queryClient = useQueryClient();

  const {
    mutate,
    mutateAsync,
    isStalenessDialogOpen,
    StalenessDialog,
    mutation,
  } = useStalenessRetry<MoveJobVariables, MoveJobResponse, RefreshedJobState>({
    mutationFn: moveJobFn,

    // When 409 received: re-send with the refreshed job version from the RFC7807 body
    onConflict: (refreshedState, previousVariables) => ({
      ...previousVariables,
      scheduled_start_at:
        refreshedState.current_state?.scheduled_start_at ??
        previousVariables.scheduled_start_at,
      scheduled_end_at:
        refreshedState.current_state?.scheduled_end_at ??
        previousVariables.scheduled_end_at,
      expected_job_version: refreshedState.current_job_version,
    }),

    // Show refreshed slot info in the staleness dialog
    renderConflictContent: ({ refreshedState }) =>
      React.createElement(
        "div",
        { className: "text-body text-neutral-600 space-y-2" },
        React.createElement(
          "p",
          null,
          "The job was updated since you loaded the board. Current schedule:",
        ),
        React.createElement(
          "ul",
          { className: "list-disc pl-4 space-y-1" },
          refreshedState.current_state?.scheduled_start_at &&
            React.createElement(
              "li",
              null,
              `Start: ${new Date(refreshedState.current_state.scheduled_start_at).toLocaleString()}`,
            ),
          refreshedState.current_state?.scheduled_end_at &&
            React.createElement(
              "li",
              null,
              `End: ${new Date(refreshedState.current_state.scheduled_end_at).toLocaleString()}`,
            ),
        ),
      ),

    mutationOptions: {
      mutationKey: ["moveJob"],

      onMutate: async (variables) => {
        // Optimistic update: apply move to cached board data immediately
        await queryClient.cancelQueries({
          queryKey: DISPATCH_BOARD_QUERY_KEY(activeDate, endDate),
        });

        const previousBoard = queryClient.getQueryData(
          DISPATCH_BOARD_QUERY_KEY(activeDate, endDate),
        );

        queryClient.setQueryData(
          DISPATCH_BOARD_QUERY_KEY(activeDate, endDate),
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (old: any) => {
            if (!old) return old;
            return {
              ...old,
              jobs: old.jobs.map(
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (job: any) =>
                  job.id === variables.jobId
                    ? {
                        ...job,
                        tech_id: variables.tech_user_id,
                        scheduled_start_at: variables.scheduled_start_at,
                        scheduled_end_at: variables.scheduled_end_at,
                      }
                    : job,
              ),
            };
          },
        );

        return { previousBoard };
      },

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      onError: (_err, _variables, context: any) => {
        // Rollback optimistic update on non-409 errors
        if (context?.previousBoard) {
          queryClient.setQueryData(
            DISPATCH_BOARD_QUERY_KEY(activeDate, endDate),
            context.previousBoard,
          );
        }
      },

      onSettled: () => {
        // Always refetch after mutation settles to ensure consistency
        queryClient.invalidateQueries({
          queryKey: ["dispatch-board"],
        });
      },
    },
  });

  return {
    moveJob: mutate,
    moveJobAsync: mutateAsync,
    isStalenessDialogOpen,
    StalenessDialog,
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
  };
}
