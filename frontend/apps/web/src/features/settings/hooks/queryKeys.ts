/**
 * queryKeys.ts — FE-B11
 *
 * Shared TanStack Query key constants for the settings domain.
 * Defined in their own file to avoid circular imports between mutation hooks
 * and the catalog query hook.
 */

export const SETTINGS_CATALOG_QUERY_KEY = ["settings-catalog"] as const;
