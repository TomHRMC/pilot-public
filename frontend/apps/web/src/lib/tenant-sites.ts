/**
 * tenant-sites — C-B16 server-side public snapshot fetcher
 *
 * Location: apps/web/src/lib/tenant-sites.ts
 *
 * Server-only fetcher for the public tenant-site endpoint. Uses `fetch()`
 * with Next.js cache (`revalidate: 300`) — this is the ONE intentional
 * exception to RULE 2 (Design Decision #1): the public tenant-site pages are
 * unauthenticated SSR Server Components. `apiClient` (Axios/browser) cannot
 * run server-side and has no browser session.
 *
 * Returns the published snapshot or calls `notFound()` on 404/non-OK.
 * No existence leak — 404 for both unknown slugs and non-published sites.
 */

import { notFound } from "next/navigation";
import type { components } from "@pilot/shared-types";

type PublicTenantSiteResponse =
  components["schemas"]["PublicTenantSiteResponse"];

/**
 * Fetches the published tenant-site snapshot server-side.
 *
 * @param slug — the tenant-site slug (from the [slug] route param)
 * @returns the published snapshot payload
 * @throws calls notFound() (which renders not-found.tsx) on 404 or any error
 */
export async function fetchTenantSite(
  slug: string,
): Promise<PublicTenantSiteResponse> {
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const apiUrl = `${apiBase}/api/v1/public/tenant-sites/${encodeURIComponent(slug)}`;

  try {
    const res = await fetch(apiUrl, {
      next: { revalidate: 300 },
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      // 404 (site_not_found) or any other error → safe fallback to not-found
      // No existence leak — same neutral 404 for unknown + non-published
      notFound();
    }

    return (await res.json()) as PublicTenantSiteResponse;
  } catch {
    // Network error or notFound() thrown — safe fallback
    notFound();
  }
}
