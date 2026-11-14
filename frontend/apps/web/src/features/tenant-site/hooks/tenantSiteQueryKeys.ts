/**
 * tenantSiteQueryKeys — C-B16 colocated query key factory
 *
 * Location: apps/web/src/features/tenant-site/hooks/tenantSiteQueryKeys.ts
 *
 * RULE 33 (TanStack Query v5): structured keys including every queryFn variable.
 * All tenant-site queries are namespaced under ["tenant-site", ...].
 */

export const tenantSiteKeys = {
  all: ["tenant-site"] as const,
  config: ["tenant-site", "config"] as const,
  slugAvailability: (slug: string) =>
    ["tenant-site", "slug-availability", slug] as const,
};
