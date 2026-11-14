/**
 * useQbConflictDetail — TanStack Query detail hook for QB conflict
 *
 * Location: apps/web/src/features/quickbooks-conflict/hooks/useQbConflictDetail.ts
 *
 * Established FE-B9. GET /api/v1/integrations/quickbooks/conflicts/{id}
 * Cache: 0s staleTime; always refetch on focus.
 * Query key: ['qb-conflict', id]
 */

import { useQuery } from "@tanstack/react-query";
import type { QbConflictDetail, QbFieldDiff } from "../types";
import { apiClient } from "@pilot/shared-api";

export const QB_CONFLICT_DETAIL_QUERY_KEY = (id: string) =>
  ["qb-conflict", id] as const;

async function fetchQbConflictDetail(id: string): Promise<QbConflictDetail> {
  const res = await apiClient.get(
    `/api/v1/integrations/quickbooks/conflicts/${id}`,
  );

  const raw = res.data as Record<string, unknown>;

  // Normalize field_diffs from backend A49 format
  const fieldDiffs = ((raw.field_diffs as unknown[]) ?? []).map((d) => {
    const diff = d as Record<string, unknown>;
    return {
      fieldName: diff.field_name as string,
      pilot_value: diff.pilot_value,
      external_value: diff.external_value,
      changeType: diff.change_type as QbFieldDiff["changeType"],
    } satisfies QbFieldDiff;
  });

  return {
    id: raw.id as string,
    entityType: raw.entity_type as QbConflictDetail["entityType"],
    entityId: raw.entity_id as string,
    entityDisplayName: raw.entity_display_name as string,
    conflictType: raw.conflict_type as QbConflictDetail["conflictType"],
    masterDirection:
      raw.master_direction as QbConflictDetail["masterDirection"],
    pilotModifiedAt: raw.pilot_modified_at as string,
    externalModifiedAt: raw.external_modified_at as string,
    pilotModifiedByUserId: raw.pilot_modified_by_user_id as string | null,
    pilotModifiedByName: raw.pilot_modified_by_name as string | null,
    fieldDiffs,
    financialDeltaCents: raw.financial_delta_cents as number | null,
    pilotAmountCents: raw.pilot_amount_cents as number | null,
    qbAmountCents: raw.qb_amount_cents as number | null,
    arImpactDescription: raw.ar_impact_description as string | null,
    taxPeriodWarning: raw.tax_period_warning as string | null,
    qbTransactionUrl: raw.qb_transaction_url as string | null,
    resolution: raw.resolution as QbConflictDetail["resolution"],
    resolvedAt: raw.resolved_at as string | null,
    autoResolvedStale: raw.auto_resolved_stale as boolean,
  };
}

export function useQbConflictDetail(id: string) {
  return useQuery({
    queryKey: QB_CONFLICT_DETAIL_QUERY_KEY(id),
    queryFn: () => fetchQbConflictDetail(id),
    staleTime: 0,
    refetchOnWindowFocus: true,
    enabled: Boolean(id),
  });
}
