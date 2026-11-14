/**
 * useQbConflicts — TanStack Query list hook for QB conflicts
 *
 * Location: apps/web/src/features/quickbooks-conflict/hooks/useQbConflicts.ts
 *
 * Established FE-B9. GET /api/v1/integrations/quickbooks/conflicts
 * Cache: 30s staleTime; refetchOnWindowFocus; cursor-paginated.
 * Query key: ['qb-conflicts', params]
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type {
  QbConflictsParams,
  QbConflictsResponse,
  QbConflictQueueItem,
} from "../types";

export const QB_CONFLICTS_QUERY_KEY = (params: QbConflictsParams) =>
  ["qb-conflicts", params] as const;

async function fetchQbConflicts(
  params: QbConflictsParams,
): Promise<QbConflictsResponse> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.entity_type) query.set("entity_type", params.entity_type);
  if (params.cursor) query.set("cursor", params.cursor);
  if (params.limit) query.set("limit", String(params.limit));

  const res = await apiClient.get(
    `/api/v1/integrations/quickbooks/conflicts?${query.toString()}`,
  );

  const data = res.data as {
    conflicts: unknown[];
    next_cursor: string | null;
    total_pending: number;
  };

  const conflicts = data.conflicts.map((c) => {
    const raw = c as Record<string, unknown>;
    return {
      id: raw.id as string,
      entityType: raw.entity_type as QbConflictQueueItem["entityType"],
      entityId: raw.entity_id as string,
      entityDisplayName: raw.entity_display_name as string,
      conflictType: raw.conflict_type as QbConflictQueueItem["conflictType"],
      masterDirection:
        raw.master_direction as QbConflictQueueItem["masterDirection"],
      pilotModifiedAt: raw.pilot_modified_at as string,
      externalModifiedAt: raw.external_modified_at as string,
      financialDeltaCents: raw.financial_delta_cents as number | null,
      resolution: raw.resolution as QbConflictQueueItem["resolution"],
      detectedAt: raw.detected_at as string,
      daysUntilExpiry: raw.days_until_expiry as number | null,
    } satisfies QbConflictQueueItem;
  });

  return {
    conflicts,
    next_cursor: data.next_cursor,
    total_pending: data.total_pending,
  };
}

export function useQbConflicts(params: QbConflictsParams = {}) {
  return useQuery({
    queryKey: QB_CONFLICTS_QUERY_KEY(params),
    queryFn: () => fetchQbConflicts(params),
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });
}
