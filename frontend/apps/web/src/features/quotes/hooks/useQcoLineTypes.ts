/**
 * useQcoLineTypes — GET /api/v1/qco-line-types
 *
 * Location: apps/web/src/features/quotes/hooks/useQcoLineTypes.ts
 *
 * PLP-FIX-2: replaces the hardcoded QCO_LINE_TYPES / DEFAULT_LINE_TYPE_ID
 * constants (dev-seed UUIDs) that caused Issue 5 on the pre-release AWS environment (FK violation 500).
 * UUIDs differ per environment BY DESIGN — always resolve from the API;
 * `code` is the only stable cross-environment key.
 *
 * Verified in backend/openapi_schema_map.md (ships with PLP-FIX-2 Part A).
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type QcoLineType = components["schemas"]["QcoLineTypeResponse"];

export const QCO_LINE_TYPES_QUERY_KEY = ["qco-line-types"] as const;

export function useQcoLineTypes() {
  return useQuery({
    queryKey: QCO_LINE_TYPES_QUERY_KEY,
    queryFn: async (): Promise<QcoLineType[]> => {
      const res = await apiClient.get("/api/v1/qco-line-types");
      return res.data as QcoLineType[];
    },
    staleTime: 60 * 60 * 1000, // reference data — deliberate 1h stale (rules §33)
  });
}

/**
 * Default resolution: code "misc" → is_default row → first row.
 * Preserves the pre-PLP-FIX-2 builder default (misc) without hardcoding a UUID.
 */
export function resolveDefaultLineTypeId(types: QcoLineType[]): string | null {
  if (types.length === 0) return null;
  return (
    types.find((t) => t.code === "misc")?.id ??
    types.find((t) => t.is_default)?.id ??
    types[0]!.id
  );
}
