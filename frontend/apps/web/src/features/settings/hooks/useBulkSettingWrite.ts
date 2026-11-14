/**
 * useBulkSettingWrite — FE-B11
 *
 * Location: apps/web/src/features/settings/hooks/useBulkSettingWrite.ts
 *
 * TanStack Query mutation: PUT /api/v1/settings/bulk
 * Used exclusively by useFormSaveStrategy({ mode: 'group' }) when a group completes.
 * Invalidates catalog on success.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { CatalogEntry } from "@pilot/ui";
import { SETTINGS_CATALOG_QUERY_KEY } from "./queryKeys";
import { apiClient } from "@pilot/shared-api";

interface BulkWriteVariables {
  values: Record<string, unknown>;
}

interface BulkWriteResponse {
  updated: string[];
  results: Array<{
    key: string;
    value: unknown;
    effective_value: unknown;
    scope: string;
    updated_at: string;
  }>;
}

async function bulkWriteSettings(
  vars: BulkWriteVariables,
): Promise<BulkWriteResponse> {
  const res = await apiClient.put<BulkWriteResponse>("/api/v1/settings/bulk", {
    values: vars.values,
  });
  return res.data;
}

export function useBulkSettingWrite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: bulkWriteSettings,

    onMutate: async (vars) => {
      await queryClient.cancelQueries({ queryKey: SETTINGS_CATALOG_QUERY_KEY });

      const previousCatalog = queryClient.getQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
      );

      // Optimistic update: apply all values
      queryClient.setQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
        (old) =>
          (old ?? []).map((entry) =>
            vars.values[entry.key] !== undefined
              ? {
                  ...entry,
                  currentEffectiveValue: vars.values[entry.key],
                  currentScope: "tenant" as const,
                  revertible: true,
                }
              : entry,
          ),
      );

      return { previousCatalog };
    },

    onError: (_err, _vars, context) => {
      if (context?.previousCatalog) {
        queryClient.setQueryData(
          SETTINGS_CATALOG_QUERY_KEY,
          context.previousCatalog,
        );
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_CATALOG_QUERY_KEY });
    },
  });
}
