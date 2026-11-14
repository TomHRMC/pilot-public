/**
 * useMobileSettingsCatalog — FE-B11 Mobile
 *
 * Location: apps/mobile/features/settings/hooks/useMobileSettingsCatalog.ts
 *
 * TanStack Query: GET /api/v1/settings/catalog
 * staleTime: 10 min (mobile reads less frequently than web's 5 min)
 * gcTime: 60 min
 */

import { useQuery } from "@tanstack/react-query";
import type { CatalogEntry } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";

export const MOBILE_SETTINGS_CATALOG_QUERY_KEY = ["settings-catalog"] as const;

// Inline raw types (snake_case from backend — avoids cross-app import)
interface CatalogEntryRaw {
  key: string;
  label: string;
  description: string;
  sub_surface_path: string;
  data_type: "boolean" | "integer" | "decimal" | "string" | "array";
  validation_rules: { min?: number; max?: number; allowed_values?: string[] };
  system_default: unknown;
  current_effective_value: unknown;
  current_scope: "user" | "tenant" | "system" | "fallback";
  revertible: boolean;
  requires_role: string | null;
  allows_user_override: boolean;
}

interface CatalogResponseRaw {
  settings: CatalogEntryRaw[];
}

function normalizeEntry(raw: CatalogEntryRaw): CatalogEntry {
  return {
    key: raw.key,
    label: raw.label,
    description: raw.description,
    subSurfacePath: raw.sub_surface_path,
    dataType: raw.data_type,
    validationRules: {
      min: raw.validation_rules.min,
      max: raw.validation_rules.max,
      allowedValues: raw.validation_rules.allowed_values,
    },
    systemDefault: raw.system_default,
    currentEffectiveValue: raw.current_effective_value,
    currentScope: raw.current_scope,
    revertible: raw.revertible,
    requiresRole: raw.requires_role,
    allowsUserOverride: raw.allows_user_override,
  };
}

async function fetchSettingsCatalog(): Promise<CatalogEntry[]> {
  const res = await apiClient.get<CatalogResponseRaw>(
    "/api/v1/settings/catalog",
  );
  return res.data.settings.map(normalizeEntry);
}

export interface UseMobileSettingsCatalogReturn {
  catalog: CatalogEntry[];
  catalogMap: Map<string, CatalogEntry>;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  getCatalogEntry: (key: string) => CatalogEntry | undefined;
}

export function useMobileSettingsCatalog(): UseMobileSettingsCatalogReturn {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: MOBILE_SETTINGS_CATALOG_QUERY_KEY,
    queryFn: fetchSettingsCatalog,
    staleTime: 10 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const catalog = data ?? [];
  const catalogMap = new Map(catalog.map((e) => [e.key, e]));

  return {
    catalog,
    catalogMap,
    isLoading,
    isError,
    error: error as Error | null,
    getCatalogEntry: (key) => catalogMap.get(key),
  };
}
