/**
 * useJobTypes — TanStack Query hook for GET /api/v1/job-types
 *
 * Location: apps/web/src/features/jobs/hooks/useJobTypes.ts
 *
 * JOB-UI-B1: Returns the list of job types for the full-page edit form.
 * Verified in openapi_schema_map.md: GET /api/v1/job-types → JobTypeResponse[]
 *
 * RULE: Uses apiClient (never raw fetch). retry: false per Rule 14.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface JobTypeItem {
  id: string;
  code: string;
  label: string;
  sort_order: number;
  is_active: boolean;
  is_tenant_override: boolean;
}

export const JOB_TYPES_QUERY_KEY = ["job-types"] as const;

export function useJobTypes() {
  return useQuery({
    queryKey: JOB_TYPES_QUERY_KEY,
    queryFn: async (): Promise<JobTypeItem[]> => {
      const res = await apiClient.get("/api/v1/job-types");
      return res.data as JobTypeItem[];
    },
    staleTime: 5 * 60_000, // Job types rarely change — 5 min stale
    retry: false,
  });
}
