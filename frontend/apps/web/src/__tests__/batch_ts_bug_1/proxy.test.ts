/**
 * proxy.test — TS-BUG-1 proxy function unit tests
 *
 * Location: apps/web/src/__tests__/batch_ts_bug_1/proxy.test.ts
 *
 * Tests the exported `proxy` function from src/proxy.ts (Next.js 16 file
 * convention, migrated from middleware.ts). Covers:
 *   - Tenant-host rewrite (prod domain)
 *   - Tenant-host rewrite (dev localhost)
 *   - ?__slug= override
 *   - Non-sites host no-op
 *   - Reserved-slug no-op
 *   - Env-var fallback to localhost
 *
 * The pure parseSitesHost logic is covered exhaustively in
 * lib/__tests__/tenant-site-host.test.ts (untouched by this batch).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Minimal NextRequest mock. proxy.ts reads request.nextUrl.{hostname, pathname,
 * searchParams} and calls request.nextUrl.clone() then sets .pathname on the
 * clone before passing it to NextResponse.rewrite().
 *
 * The clone must be an independent mutable object whose toString()/href
 * reflects the rewritten pathname.
 */
function makeNextUrl(hostname: string, pathname: string, search: string) {
  const params = new URLSearchParams(search);
  return {
    hostname,
    pathname,
    searchParams: params,
    clone() {
      const copy = makeNextUrl(hostname, pathname, search);
      return copy;
    },
    get href() {
      const u = new URL("https://example.com");
      u.pathname = this.pathname;
      u.search = this.searchParams.toString();
      u.hostname = this.hostname;
      return u.toString();
    },
    set href(v: string) {
      const u = new URL(v);
      this.pathname = u.pathname;
      this.hostname = u.hostname;
    },
    toString() {
      return this.href;
    },
  };
}

function makeRequest(
  hostname: string,
  pathname = "/",
  search = "",
): NextRequest {
  return {
    nextUrl: makeNextUrl(hostname, pathname, search),
    headers: new Headers({ host: hostname }),
  } as unknown as NextRequest;
}

// Mock next/server — proxy.ts imports NextResponse + NextRequest from here.
vi.mock("next/server", () => ({
  NextResponse: {
    rewrite: vi.fn((url: unknown) => ({ status: 200, url })),
    next: vi.fn(() => ({ status: 200 })),
  },
}));

import proxy from "../../proxy";

/** Extract the string URL from whatever NextResponse.rewrite received. */
function getRewriteUrl(): string {
  const calls = (NextResponse.rewrite as ReturnType<typeof vi.fn>).mock.calls;
  if (calls.length === 0) return "";
  const arg = calls[0][0];
  if (typeof arg === "string") return arg;
  if (arg && typeof arg.toString === "function") return arg.toString();
  if (arg && typeof arg.href === "string") return arg.href;
  return String(arg);
}

describe("proxy (TS-BUG-1) — host-rewrite proxy function", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "localhost";
  });

  it("rewrites a tenant host on the prod domain to /sites/{slug}", () => {
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "p4tsites.com";
    const req = makeRequest("langelec.p4tsites.com", "/");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec");
  });

  it("rewrites a tenant host on localhost (dev) to /sites/{slug}", () => {
    const req = makeRequest("langelec.localhost", "/");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec");
  });

  it("preserves the pathname in the rewrite", () => {
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "p4tsites.com";
    const req = makeRequest("langelec.p4tsites.com", "/privacy");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec/privacy");
  });

  it("?__slug= override rewrites to /sites/{slug} and strips the param", () => {
    const req = makeRequest("localhost", "/", "__slug=langelec");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec");
    expect(getRewriteUrl()).not.toContain("__slug");
  });

  it("non-sites host (apex) is a no-op → NextResponse.next()", () => {
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "p4tsites.com";
    const req = makeRequest("p4tsites.com", "/");
    proxy(req);
    expect(NextResponse.next).toHaveBeenCalledTimes(1);
    expect(NextResponse.rewrite).not.toHaveBeenCalled();
  });

  it("non-sites host (www) is a no-op → NextResponse.next()", () => {
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "p4tsites.com";
    const req = makeRequest("www.p4tsites.com", "/");
    proxy(req);
    expect(NextResponse.next).toHaveBeenCalledTimes(1);
    expect(NextResponse.rewrite).not.toHaveBeenCalled();
  });

  it("reserved slug (api) is a no-op → NextResponse.next()", () => {
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "p4tsites.com";
    const req = makeRequest("api.p4tsites.com", "/");
    proxy(req);
    expect(NextResponse.next).toHaveBeenCalledTimes(1);
    expect(NextResponse.rewrite).not.toHaveBeenCalled();
  });

  it("non-matching domain (pilotfortrades.com) is a no-op", () => {
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "p4tsites.com";
    const req = makeRequest("pilotfortrades.com", "/");
    proxy(req);
    expect(NextResponse.next).toHaveBeenCalledTimes(1);
    expect(NextResponse.rewrite).not.toHaveBeenCalled();
  });

  it("falls back to localhost when env var is unset and host is *.localhost", () => {
    delete process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN;
    delete process.env.TENANT_SITES_DOMAIN;
    const req = makeRequest("langelec.localhost", "/");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec");
  });

  // TS-BUG-1: multi-domain fallback — the real prod root cause is that
  // Next.js inlines process.env at build time. If the env var is baked in as
  // "localhost" (stale build cache), the proxy must STILL detect
  // {slug}.p4tsites.com by trying p4tsites.com as a fallback domain.
  it("detects p4tsites.com host even when env var is baked as localhost", () => {
    // Simulate the prod failure: env var inlined as "localhost" at build time
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "localhost";
    delete process.env.TENANT_SITES_DOMAIN;
    const req = makeRequest("langelec.p4tsites.com", "/");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec");
  });

  it("detects localhost host even when env var is baked as p4tsites.com", () => {
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "p4tsites.com";
    delete process.env.TENANT_SITES_DOMAIN;
    const req = makeRequest("langelec.localhost", "/");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec");
  });

  it("infers p4tsites.com domain when env vars are unset", () => {
    delete process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN;
    delete process.env.TENANT_SITES_DOMAIN;
    const req = makeRequest("langelec.p4tsites.com", "/");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec");
  });

  // TS-BUG-1: non-public TENANT_SITES_DOMAIN takes priority over NEXT_PUBLIC_
  it("uses TENANT_SITES_DOMAIN (non-public) when set — takes priority over NEXT_PUBLIC_", () => {
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "stale.example.com";
    process.env.TENANT_SITES_DOMAIN = "p4tsites.com";
    const req = makeRequest("langelec.p4tsites.com", "/");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec");
  });

  it("falls back to NEXT_PUBLIC_TENANT_SITES_DOMAIN when TENANT_SITES_DOMAIN is unset", () => {
    delete process.env.TENANT_SITES_DOMAIN;
    process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN = "p4tsites.com";
    const req = makeRequest("langelec.p4tsites.com", "/");
    proxy(req);
    expect(NextResponse.rewrite).toHaveBeenCalledTimes(1);
    expect(getRewriteUrl()).toContain("/sites/langelec");
  });
});
