/**
 * tenant-site-host — C-B16 host-rewrite pure logic
 *
 * Location: apps/apps/web/src/lib/tenant-site-host.ts
 *
 * Pure, testable function that extracts a tenant-site slug from a hostname.
 * Used by src/middleware.ts to rewrite `{slug}.{TENANT_SITES_DOMAIN}` →
 * `/sites/{slug}{pathname}`.
 *
 * Design §G-13:
 *   - Matches `{slug}.{NEXT_PUBLIC_TENANT_SITES_DOMAIN}` (prod)
 *   - Matches `{slug}.localhost` or `{slug}.localhost:3000` (dev)
 *   - Rejects apex / www / reserved hosts
 *   - Supports `?__slug=` dev override (handled in middleware, not here)
 *
 * This module has NO side effects and NO Next.js imports — fully testable
 * in Vitest.
 */

/** Reserved host labels that must never be treated as tenant slugs. */
export const RESERVED_HOST_LABELS = new Set([
  "www",
  "api",
  "app",
  "mail",
  "smtp",
  "support",
  "help",
  "admin",
  "pilot",
  "p4t",
  "pilotfortrades",
  "staging",
  "dev",
  "qa",
  "test",
  "status",
  "billing",
  "login",
  "signup",
  "marketing",
  "cdn",
  "assets",
]);

/** DNS-label regex matching ck_tenant_site_slug_format. */
const SLUG_REGEX = /^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$/;

export interface ParsedSitesHost {
  slug: string;
}

/**
 * Extracts the tenant-site slug from a hostname.
 *
 * @param hostname — the request hostname (e.g. "lang-electric.p4tsites.com",
 *                   "lang-electric.localhost", "lang-electric.localhost:3000").
 *                   Port is stripped internally.
 * @param sitesDomain — the configured TENANT_SITES_BASE_DOMAIN (e.g.
 *                      "p4tsites.com" in prod, "localhost" in dev). When
 *                      "localhost", any `*.localhost` host is treated as a
 *                      sites host.
 * @returns `{ slug }` if the host is a valid tenant-site host, `null`
 *          otherwise (apex, www, reserved, non-matching domain, invalid slug).
 */
export function parseSitesHost(
  hostname: string,
  sitesDomain: string,
): ParsedSitesHost | null {
  if (!hostname || !sitesDomain) return null;

  // Strip port (e.g. "lang-electric.localhost:3000" → "lang-electric.localhost")
  const hostWithoutPort = hostname.split(":")[0];
  const domain = sitesDomain.split(":")[0];

  // Dev mode: sitesDomain is "localhost" — match {slug}.localhost
  if (domain === "localhost") {
    if (!hostWithoutPort.endsWith(".localhost")) return null;
    const slug = hostWithoutPort.slice(0, -".localhost".length);
    return validateSlug(slug);
  }

  // Prod mode: match {slug}.{sitesDomain}
  const suffix = `.${domain}`;
  if (!hostWithoutPort.endsWith(suffix)) return null;

  // Reject apex (host === domain) and www
  if (hostWithoutPort === domain) return null;

  const slug = hostWithoutPort.slice(0, -suffix.length);

  // Reject multi-level subdomains (e.g. "foo.bar.p4tsites.com" → slug="foo.bar" → invalid)
  if (slug.includes(".")) return null;

  return validateSlug(slug);
}

function validateSlug(slug: string): ParsedSitesHost | null {
  if (!slug) return null;
  if (RESERVED_HOST_LABELS.has(slug)) return null;
  if (!SLUG_REGEX.test(slug)) return null;
  return { slug };
}
