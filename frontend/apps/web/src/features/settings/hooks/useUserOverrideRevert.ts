/**
 * useUserOverrideRevert — FE-B11
 *
 * Location: apps/web/src/features/settings/hooks/useUserOverrideRevert.ts
 *
 * TanStack Query mutation: DELETE /api/v1/settings/{key}/user-override
 * Reverts the user override to inherit tenant/system value.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { CatalogEntry } from "@pilot/ui";
import { SETTINGS_CATALOG_QUERY_KEY } from "./queryKeys";
import { apiClient } from "@pilot/shared-api";

interface UserOverrideRevertVariables {
  key: string;
  tenantDefault: unknown;
}

async function revertUserOverride(vars: UserOverrideRevertVariables) {
  const res = await apiClient.delete(
    `/api/v1/settings/${vars.key}/user-override`,
  );

  return res.data;
}

export function useUserOverrideRevert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: revertUserOverride,

    onMutate: async (vars) => {
      await queryClient.cancelQueries({ queryKey: SETTINGS_CATALOG_QUERY_KEY });

      const previousCatalog = queryClient.getQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
      );

      queryClient.setQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
        (old) =>
          (old ?? []).map((entry) =>
            entry.key === vars.key
              ? {
                  ...entry,
                  currentEffectiveValue: vars.tenantDefault,
                  currentScope: "tenant" as const,
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
