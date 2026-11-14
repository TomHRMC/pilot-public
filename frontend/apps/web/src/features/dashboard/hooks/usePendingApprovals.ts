/**
 * usePendingApprovals — Dashboard BI hook
 *
 * Location: apps/web/src/features/dashboard/hooks/usePendingApprovals.ts
 *
 * GET /api/v1/dashboard/pending-approvals-summary
 * Endpoint verified in backend/openapi_schema_map.md (FE-B23 Part A).
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface PendingApprovalsSummary {
  pending_quotes: number;
  pending_field_issues: number;
}

export function usePendingApprovals() {
  return useQuery<PendingApprovalsSummary>({
    queryKey: ["dashboard-pending-approvals"],
    queryFn: async () => {
      const res = await apiClient.get(
        "/api/v1/dashboard/pending-approvals-summary",
      );
      return res.data as PendingApprovalsSummary;
    },
    staleTime: 30_000,
  });
}
