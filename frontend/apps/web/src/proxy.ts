/**
 * proxy — TS-BUG-1 host-rewrite proxy (Next.js 16 file convention)
 *
 * Location: apps/web/src/proxy.ts
 *
 * Migrated from src/middleware.ts (C-B16) per the Next.js 16 rename:
 * middleware.ts → proxy.ts, exported function middleware → proxy.
 * Reference: https://nextjs.org/docs/app/api-reference/file-conventions/proxy
 *
 * This is the app's ONLY proxy/middleware. It runs for every matched request.
 * Its sole job: detect tenant-site hosts (`{slug}.{TENANT_SITES_DOMAIN}` or
 * `{slug}.localhost` in dev) and rewrite them to the `(tenant-site)/sites/[slug]`
 * route group, preserving the URL path.
 *
 * TS-BUG-1 root cause (confirmed via 3 post-deploy probe iterations):
 *
 * The original `middleware.ts` was migrated to `proxy.ts` (Next.js 16 file
 * convention rename). But the login wall persisted across 3 deploys because
 * the real root cause was NOT the file convention or env vars — it was that
 * `request.nextUrl.hostname` does NOT reflect the original Host header in
 * production behind an AWS ALB. The Next.js standalone server constructs
 * `nextUrl` from the incoming request, but the `hostname` property may be
 * the container's bind address (`0.0.0.0`) or the ALB's internal hostname,
 * not `langelec.p4tsites.com`. The `?__slug=` override worked because it
 * reads `searchParams` (not `hostname`), which is always correct.
 *
 * Final fix: read the `Host` header directly from `request.headers.get("host")`
 * as the primary source, with `request.nextUrl.hostname` as fallback. Combined
 * with a multi-domain fallback (tries `p4tsites.com` and `localhost` even if
 * env vars are stale), the proxy is bulletproof against:
 *   - H1: middleware.ts → proxy.ts file convention (fixed by migration)
 *   - H2: env var inlining at build time (fixed by multi-domain fallback)
 *   - H4 (actual root cause): nextUrl.hostname not reflecting Host header
 *     behind ALB (fixed by reading Host header directly)
 *
 * Design §G-13 + §I (unchanged from C-B16):
 *   - The matcher is scoped to exclude all existing app paths: api/, _next/,
 *     i/, q/, login, signup, operator, and all (authed) paths. The proxy
 *     is a NO-OP for the entire existing app.
 *   - Supports `?__slug=` dev override for testing without DNS.
 *   - On non-match → NextResponse.next() (untouched).
 *
 * This proxy does NOT touch auth, API, or any existing route.
 */

import { NextResponse, type NextRequest } from "next/server";
import { parseSitesHost } from "./lib/tenant-site-host";

export default function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;

  // TS-BUG-1: request.nextUrl.hostname may not reflect the original Host header
  // in production behind an ALB. Read the Host header directly as the primary
  // source, falling back to nextUrl.hostname.
  const hostname =
    request.headers.get("host")?.split(":")[0] ?? request.nextUrl.hostname;

  // Dev override: ?__slug= forces a slug (design §G-13)
  const overrideSlug = searchParams.get("__slug");
  if (overrideSlug) {
    // Rewrite to /sites/{slug}{pathname} — strip the __slug param
    const url = request.nextUrl.clone();
    url.pathname = `/sites/${overrideSlug}${pathname}`;
    url.searchParams.delete("__slug");
    return NextResponse.rewrite(url);
  }

  // TS-BUG-1: Next.js inlines process.env.* at BUILD time in the proxy/middleware
  // bundle — even for non-NEXT_PUBLIC_ vars. If the build-arg is missing, stale,
  // or the Docker build cache reuses an old layer, the env var is baked in as
  // undefined/localhost and NO runtime override can fix it.
  //
  // The bulletproof fix: try parseSitesHost with multiple candidate domains.
  // Even if the env var is baked in as "localhost" at build time, the proxy will
  // still detect {slug}.p4tsites.com as a tenant host by trying p4tsites.com
  // as a fallback domain. This makes the proxy work regardless of env var state.
  const envDomain =
    process.env.TENANT_SITES_DOMAIN ??
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN ??
    "localhost";

  // Candidate domains to try, in priority order:
  //   1. The env var value (may be correct or stale)
  //   2. "p4tsites.com" (prod fallback — always try this)
  //   3. "localhost" (dev fallback — always try this)
  const candidateDomains = [envDomain, "p4tsites.com", "localhost"];

  let parsed: { slug: string } | null = null;
  for (const domain of candidateDomains) {
    parsed = parseSitesHost(hostname, domain);
    if (parsed) break;
  }

  if (!parsed) {
    // Not a tenant-site host — pass through untouched
    return NextResponse.next();
  }

  // Rewrite to the (tenant-site) route group: /sites/{slug}{pathname}
  const url = request.nextUrl.clone();
  url.pathname = `/sites/${parsed.slug}${pathname}`;
  return NextResponse.rewrite(url);
}

/**
 * Matcher — scoped to sites domains ONLY.
 *
 * The matcher excludes all existing app paths so the proxy is a no-op
 * for the entire current application:
 *   - /api/*        → excluded (API routes)
 *   - /_next/*      → excluded (Next.js internals)
 *   - /i/*          → excluded (public invoice pay)
 *   - /q/*          → excluded (public quote viewer)
 *   - /login, /signup → excluded (auth pages)
 *   - /operator/*   → excluded (operator console)
 *   - /settings/*, /jobs/*, /schedule/*, /customers/*, /quotes/*, /invoices/*,
 *     /catalog/*, /reports/*, /dashboard/*, /communications/*, /billing/*,
 *     /team/*, /notifications/*, /onboarding/*, /voice-ai/*, /comms/*
 *     → excluded (all authenticated app routes)
 *
 * The proxy only fires on paths that could be tenant-site paths:
 *   - / (root — landing page)
 *   - /privacy, /terms (legal pages)
 *   - /sites/* (direct access, e.g. dev override)
 *
 * Even when it fires, parseSitesHost returns null for non-sites hosts,
 * so the proxy is a no-op for localhost:3000 (the dev app) and
 * pilotfortrades.com (marketing).
 */
export const config = {
  matcher: [
    /*
     * Match root + /privacy + /terms + /sites/* — the only paths a
     * tenant-site subdomain would serve. Everything else is excluded.
     */
    "/",
    "/privacy",
    "/terms",
    "/sites/:path*",
  ],
};
