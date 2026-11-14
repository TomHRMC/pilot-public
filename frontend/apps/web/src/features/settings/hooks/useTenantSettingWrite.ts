/**
 * useTenantSettingWrite — FE-B11
 *
 * Location: apps/web/src/features/settings/hooks/useTenantSettingWrite.ts
 *
 * TanStack Query mutation: PUT /api/v1/settings/{key}
 * Optimistic update pattern (arch doc §16.8 / Rule 7):
 *   onMutate: update catalog cache immediately
 *   onError: rollback to previous cache state
 *   onSettled: invalidate catalog to get server-confirmed state
 *
 * Uses standard TanStack Query mutation — NOT useOptimisticMutation from FE-B7
 * (that is for WatermelonDB offline entities).
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { CatalogEntry } from "@pilot/ui";
import { SETTINGS_CATALOG_QUERY_KEY } from "./queryKeys";
import { apiClient } from "@pilot/shared-api";

interface TenantSettingWriteVariables {
  key: string;
  value: unknown;
  expectedUpdatedAt?: string;
}

interface TenantSettingWriteResponse {
  key: string;
  value: unknown;
  effective_value: unknown;
  scope: string;
  updated_at: string;
  pending_quote_count?: number;
}

async function writeTenantSetting(
  vars: TenantSettingWriteVariables,
): Promise<TenantSettingWriteResponse> {
  const res = await apiClient.put<TenantSettingWriteResponse>(
    `/api/v1/settings/${vars.key}`,
    {
      value: vars.value,
      ...(vars.expectedUpdatedAt
        ? { expected_updated_at: vars.expectedUpdatedAt }
        : {}),
    },
  );
  return res.data;
}

export function useTenantSettingWrite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: writeTenantSetting,

    onMutate: async (vars) => {
      // Cancel any in-flight catalog refetch
      await queryClient.cancelQueries({ queryKey: SETTINGS_CATALOG_QUERY_KEY });

      // Snapshot previous catalog
      const previousCatalog = queryClient.getQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
      );

      // Optimistic update: immediately reflect new value + scope='tenant'
      queryClient.setQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
        (old) =>
          (old ?? []).map((entry) =>
            entry.key === vars.key
              ? {
                  ...entry,
                  currentEffectiveValue: vars.value,
                  currentScope: "tenant" as const,
                  revertible: true,
                }
              : entry,
          ),
      );

      return { previousCatalog };
    },

    onError: (_err, _vars, context) => {
      // Rollback to previous catalog state
      if (context?.previousCatalog) {
        queryClient.setQueryData(
          SETTINGS_CATALOG_QUERY_KEY,
          context.previousCatalog,
        );
      }
    },

    onSettled: () => {
      // Always invalidate to get server-confirmed state
      queryClient.invalidateQueries({ queryKey: SETTINGS_CATALOG_QUERY_KEY });
    },
  });
}
