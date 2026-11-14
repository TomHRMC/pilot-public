/**
 * useResolveFieldIssue — mutation hook for field issue resolution
 *
 * Location: apps/web/src/features/field-issues/hooks/useResolveFieldIssue.ts
 *
 * Established FE-B9. POST /api/v1/owner/field-issues/{id}/resolve
 * Composes useStalenessRetry; handles three 409 subtypes:
 *   server_changed  → StalenessRefreshDialog opens (refreshed diff)
 *   auto_recovered  → success NotificationBanner; navigate to queue
 *   stale           → info NotificationBanner; navigate to queue
 *
 * RULE 4: server-side diff is canonical; never compute diffs client-side.
 */

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useStalenessRetry } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";
import type {
  FieldIssueResolveRequest,
  FieldIssueDetail,
  FieldIssue409Response,
} from "../types";
import { FIELD_ISSUES_QUERY_KEY } from "./useFieldIssues";
import { FIELD_ISSUE_DETAIL_QUERY_KEY } from "./useFieldIssueDetail";

export type ResolveFieldIssueResult =
  | { outcome: "success" }
  | { outcome: "auto_recovered"; message: string }
  | { outcome: "stale"; message: string }
  | { outcome: "server_changed"; refreshedIssue: FieldIssueDetail };

export interface UseResolveFieldIssueOptions {
  issueId: string;
  /** Called on auto_recovered or stale — navigate back to queue */
  onBannerOutcome: (
    outcome: "auto_recovered" | "stale",
    message: string,
  ) => void;
}

async function resolveFieldIssue(
  issueId: string,
  body: FieldIssueResolveRequest,
): Promise<void> {
  const payload = {
    resolution: body.resolution,
    expected_server_state_hash: body.expected_server_state_hash,
    ...(body.per_field_selections
      ? { per_field_selections: body.per_field_selections }
      : {}),
  };

  await apiClient.post(
    `/api/v1/owner/mobile-sync-escalations/${issueId}/resolve`,
    payload,
  );
}

export function useResolveFieldIssue({
  issueId,
  onBannerOutcome,
}: UseResolveFieldIssueOptions) {
  const queryClient = useQueryClient();

  const handle409 = useCallback(
    (
      refreshedState: FieldIssue409Response,
    ): FieldIssueResolveRequest | null => {
      if (refreshedState.staleness_type === "auto_recovered") {
        // No dialog — success banner + navigate to queue
        onBannerOutcome("auto_recovered", refreshedState.message);
        void queryClient.invalidateQueries({
          queryKey: FIELD_ISSUES_QUERY_KEY({}),
        });
        return null;
      }

      if (refreshedState.staleness_type === "stale") {
        // No dialog — info banner + navigate to queue
        onBannerOutcome("stale", refreshedState.message);
        void queryClient.invalidateQueries({
          queryKey: FIELD_ISSUES_QUERY_KEY({}),
        });
        return null;
      }

      // server_changed → return null to keep StalenessDialog open for user decision
      // The refreshed_issue data will be shown in the dialog via renderConflictContent
      if (refreshedState.staleness_type === "server_changed") {
        // Invalidate detail cache to pick up refreshed data
        void queryClient.invalidateQueries({
          queryKey: FIELD_ISSUE_DETAIL_QUERY_KEY(issueId),
        });
        return null; // Opens StalenessRefreshDialog
      }

      return null;
    },
    [queryClient, issueId, onBannerOutcome],
  );

  const { mutate, isStalenessDialogOpen, StalenessDialog, mutation } =
    useStalenessRetry<FieldIssueResolveRequest, void, FieldIssue409Response>({
      mutationFn: (vars) => resolveFieldIssue(issueId, vars),
      onConflict: handle409,
      dialogTitle: "This issue has been updated. Review and pick again.",
      mutationOptions: {
        onSuccess: () => {
          // Invalidate list + detail caches on successful resolve
          void queryClient.invalidateQueries({
            queryKey: FIELD_ISSUES_QUERY_KEY({}),
          });
          void queryClient.invalidateQueries({
            queryKey: FIELD_ISSUE_DETAIL_QUERY_KEY(issueId),
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
