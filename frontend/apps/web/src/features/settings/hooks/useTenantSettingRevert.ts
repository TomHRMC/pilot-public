/**
 * useTenantSettingRevert — FE-B11
 *
 * Location: apps/web/src/features/settings/hooks/useTenantSettingRevert.ts
 *
 * TanStack Query mutation: DELETE /api/v1/settings/{key}/tenant-override
 * Optimistically transitions the catalog entry to scope='system'.
 *
 * Rule 6: DELETE (not PUT with system default value) — semantically removes
 * the tenant override so future system default changes propagate.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { CatalogEntry } from "@pilot/ui";
import { SETTINGS_CATALOG_QUERY_KEY } from "./queryKeys";
import { apiClient } from "@pilot/shared-api";

interface RevertVariables {
  key: string;
  systemDefault: unknown;
}

async function revertTenantSetting(vars: RevertVariables): Promise<void> {
  await apiClient.delete(`/api/v1/settings/${vars.key}/tenant-override`);
}

export function useTenantSettingRevert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: revertTenantSetting,

    onMutate: async (vars) => {
      await queryClient.cancelQueries({ queryKey: SETTINGS_CATALOG_QUERY_KEY });

      const previousCatalog = queryClient.getQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
      );

      // Optimistically transition to scope='system' with system default value
      queryClient.setQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
        (old) =>
          (old ?? []).map((entry) =>
            entry.key === vars.key
              ? {
                  ...entry,
                  currentEffectiveValue: vars.systemDefault,
                  currentScope: "system" as const,
                  revertible: false,
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
