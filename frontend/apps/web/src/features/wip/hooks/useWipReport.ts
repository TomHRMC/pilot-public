/**
 * useWipReport — TanStack Query v5 hook for the WIP report
 *
 * Location: apps/web/src/features/wip/hooks/useWipReport.ts
 *
 * GET /api/v1/reports/wip — returns active jobs with ETC-projected cost vs quoted budget.
 * WIP is a snapshot computed on-request (no SSE, no polling). The only refresh is the
 * manual Refresh button calling query.refetch() (spec §9.4).
 *
 * Types come from @pilot/shared-types (post pnpm sync-api-types) — never hand-typed.
 *
 * Per batch-up-1-ui-design-spec.md §9.1 + batch-up-1-react-engr-prompt.md STEP 1.
 */

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

type WipReportResponse = components["schemas"]["WipReportResponse"];

export type WipSort =
  | "deviation_pct"
  | "projected_margin_pct"
  | "actual_cost_cents"
  | "scheduled_start_at";

export interface UseWipReportOptions {
  /** CSV of job_status.code values; default "scheduled,in_progress" */
  status?: string;
  /** Sort field; default "deviation_pct" */
  sort?: WipSort;
  /** Sort order; default "desc" */
  order?: "asc" | "desc";
}

export const WIP_QUERY_KEY = (o: UseWipReportOptions) =>
  [
    "wip-report",
    o.status ?? "scheduled,in_progress",
    o.sort ?? "deviation_pct",
    o.order ?? "desc",
  ] as const;

async function fetchWipReport(
  options: UseWipReportOptions,
): Promise<WipReportResponse> {
  const res = await apiClient.get("/api/v1/reports/wip", {
    params: {
      status: options.status,
      sort: options.sort,
      order: options.order,
    },
  });
  return res.data as WipReportResponse;
}

export function useWipReport(options: UseWipReportOptions = {}) {
  return useQuery({
    queryKey: WIP_QUERY_KEY(options),
    queryFn: () => fetchWipReport(options),
    retry: false, // spec §5.2 — user controls retry via <ErrorState>
    staleTime: 60_000, // 1 min — WIP is a snapshot; don't refetch aggressively
    refetchOnWindowFocus: false, // not a live surface
    placeholderData: keepPreviousData, // keep table visible while re-sorting
  });
}
