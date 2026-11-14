/**
 * useFieldIssueDetail — TanStack Query detail hook for field issue
 *
 * Location: apps/web/src/features/field-issues/hooks/useFieldIssueDetail.ts
 *
 * Established FE-B9. GET /api/v1/owner/field-issues/{id}
 * Cache: 0s staleTime; always refetch on focus.
 * Query key: ['field-issue', id]
 */

import { useQuery } from "@tanstack/react-query";
import type { FieldIssueDetail, FieldIssueDiff } from "../types";
import { apiClient } from "@pilot/shared-api";

export const FIELD_ISSUE_DETAIL_QUERY_KEY = (id: string) =>
  ["field-issue", id] as const;

async function fetchFieldIssueDetail(id: string): Promise<FieldIssueDetail> {
  const res = await apiClient.get(
    `/api/v1/owner/mobile-sync-escalations/${id}`,
  );

  const raw = res.data as Record<string, unknown>;

  // Normalize snake_case → camelCase
  const fieldDiffs = ((raw.field_diffs as unknown[]) ?? []).map((d) => {
    const diff = d as Record<string, unknown>;
    return {
      fieldName: diff.field_name as string,
      techValue: diff.tech_value,
      serverValue: diff.server_value,
      changeType: diff.change_type as FieldIssueDiff["changeType"],
      techChange: diff.tech_change as FieldIssueDiff["techChange"],
      serverChange: diff.server_change as FieldIssueDiff["serverChange"],
    } satisfies FieldIssueDiff;
  });

  return {
    id: raw.id as string,
    status: raw.status as FieldIssueDetail["status"],
    operationType: raw.operation_type as FieldIssueDetail["operationType"],
    techId: raw.tech_id as string,
    techName: raw.tech_name as string,
    techLastActiveAt: raw.tech_last_active_at as string | null,
    capturedAt: raw.captured_at as string,
    syncAttemptedAt: raw.sync_attempted_at as string,
    escalatedAt: raw.escalated_at as string,
    explainerCopy: raw.explainer_copy as string,
    techSnapshot: raw.tech_snapshot as Record<string, unknown> | null,
    serverSnapshot: raw.server_snapshot as Record<string, unknown> | null,
    fieldDiffs,
    conflictType: raw.conflict_type as FieldIssueDetail["conflictType"],
    resolution: raw.resolution as FieldIssueDetail["resolution"],
    resolvedByUserId: raw.resolved_by_user_id as string | null,
    resolvedAt: raw.resolved_at as string | null,
    expectedServerStateHash: raw.expected_server_state_hash as string,
  };
}

export function useFieldIssueDetail(id: string) {
  return useQuery({
    queryKey: FIELD_ISSUE_DETAIL_QUERY_KEY(id),
    queryFn: () => fetchFieldIssueDetail(id),
    staleTime: 0, // Always refetch on focus for latest state
    refetchOnWindowFocus: true,
    enabled: Boolean(id),
  });
}
