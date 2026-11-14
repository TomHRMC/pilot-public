/**
 * useSettingsCatalog — FE-B11
 *
 * Location: apps/web/src/features/settings/hooks/useSettingsCatalog.ts
 *
 * TanStack Query: GET /api/v1/settings/catalog
 * Returns CatalogEntry[] normalized to camelCase.
 * Cache: staleTime 5 min, gcTime 30 min, no refetch on window focus.
 *
 * Convenience selectors: getCatalogEntry(key), getCatalogEntriesForPath(path)
 */

import { useQuery } from "@tanstack/react-query";
import type { CatalogEntry } from "@pilot/ui";
import { SETTINGS_CATALOG_QUERY_KEY } from "./queryKeys";
import { apiClient } from "@pilot/shared-api";

export { SETTINGS_CATALOG_QUERY_KEY };

const SETTINGS_CATALOG_STALE_MS = 5 * 60 * 1000;
const SETTINGS_CATALOG_GC_MS = 30 * 60 * 1000;

// ─── Raw types (snake_case from backend) ─────────────────────────────────────
// Inlined here to avoid importing from mocks/settingsFixtures in production code.

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

// ─── Normalizer: snake_case → camelCase ──────────────────────────────────────

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
  const res = await apiClient.get("/api/v1/settings/catalog");
  const data: CatalogResponseRaw = res.data;
  return data.settings.map(normalizeEntry);
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export interface UseSettingsCatalogReturn {
  catalog: CatalogEntry[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  getCatalogEntry: (key: string) => CatalogEntry | undefined;
  getCatalogEntriesForPath: (subSurfacePath: string) => CatalogEntry[];
  refetch: () => void;
}

export function useSettingsCatalog(): UseSettingsCatalogReturn {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: SETTINGS_CATALOG_QUERY_KEY,
    queryFn: fetchSettingsCatalog,
    staleTime: SETTINGS_CATALOG_STALE_MS,
    gcTime: SETTINGS_CATALOG_GC_MS,
    refetchOnWindowFocus: false,
  });

  const catalog = data ?? [];

  const getCatalogEntry = (key: string): CatalogEntry | undefined =>
    catalog.find((e) => e.key === key);

  const getCatalogEntriesForPath = (subSurfacePath: string): CatalogEntry[] =>
    catalog.filter((e) => e.subSurfacePath === subSurfacePath);

  return {
    catalog,
    isLoading,
    isError,
    error: error as Error | null,
    getCatalogEntry,
    getCatalogEntriesForPath,
    refetch,
  };
}
