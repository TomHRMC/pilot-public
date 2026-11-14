/**
 * useUserOverrideWrite — FE-B11
 *
 * Location: apps/web/src/features/settings/hooks/useUserOverrideWrite.ts
 *
 * TanStack Query mutation: PUT /api/v1/settings/{key}/user-override
 * Optimistic update: immediately apply new user value.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { CatalogEntry } from "@pilot/ui";
import { SETTINGS_CATALOG_QUERY_KEY } from "./queryKeys";
import { apiClient } from "@pilot/shared-api";

interface UserOverrideWriteVariables {
  key: string;
  value: unknown;
}

async function writeUserOverride(vars: UserOverrideWriteVariables) {
  const res = await apiClient.put(
    `/api/v1/settings/${vars.key}/user-override`,
    { value: vars.value },
  );

  return res.data;
}

export function useUserOverrideWrite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: writeUserOverride,

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
                  currentEffectiveValue: vars.value,
                  currentScope: "user" as const,
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
