/**
 * tenantSiteHandlers — C-B16 MSW handlers
 *
 * Location: apps/web/src/mocks/handlers/tenantSiteHandlers.ts
 *
 * Mocks all 6 tenant-site endpoints:
 *   GET    /api/v1/tenant-site
 *   PUT    /api/v1/tenant-site
 *   GET    /api/v1/tenant-site/slug-availability?slug=
 *   POST   /api/v1/tenant-site/publish
 *   POST   /api/v1/tenant-site/unpublish
 *   GET    /api/v1/public/tenant-sites/:slug
 *
 * The publish handler includes a 409 `website_overwrite_requires_confirmation`
 * branch that tests override via `server.use(...)`.
 *
 * RULE 18: web app uses relative paths (apiClient.baseURL → localhost:8000, same origin).
 */

import { http, HttpResponse } from "msw";

// ── Shared mock state (module-level — tests must not mutate; use server.use overrides) ──

const MOCK_DEFAULTS = {
  display_name: "Lang Electric",
  display_name_source: "tenant_override",
  public_email: "office@langelectric.example",
  public_email_source: "tenant_override",
  public_phone: "+15551234567",
  public_phone_source: "tenant_override",
  public_city: "Richmond",
  public_city_source: "tenant_override",
  public_state: "VA",
  public_state_source: "tenant_override",
};

const MOCK_SITE = {
  id: "00000000-0000-0000-0000-000000000001",
  tenant_id: "00000000-0000-0000-0000-0000000000a1",
  slug: "lang-electric",
  site_kind: "hosted_compliance",
  status: "draft",
  display_name: "Lang Electric",
  tagline: "Residential & commercial electrical — Richmond, VA",
  public_email: "office@langelectric.example",
  public_phone: "+15551234567",
  public_city: "Richmond",
  public_state: "VA",
  public_address_line1: null,
  public_postal_code: null,
  show_full_address: false,
  template_version: "v1",
  published_at: null,
  unpublished_at: null,
  kit_sent_at: null,
  website_auto_populated: false,
  idempotency_key: null,
  site_url: null,
  requirements_emailed_at: null,
};

const RESERVED_SLUGS = new Set([
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

const SLUG_REGEX = /^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$/;

function checkSlug(slug: string): {
  available: boolean;
  reason: string | null;
  suggestion: string | null;
} {
  if (!slug || !SLUG_REGEX.test(slug)) {
    return { available: false, reason: "invalid", suggestion: null };
  }
  if (RESERVED_SLUGS.has(slug)) {
    return { available: false, reason: "reserved", suggestion: null };
  }
  if (slug === "taken") {
    return { available: false, reason: "taken", suggestion: "taken-2" };
  }
  return { available: true, reason: null, suggestion: null };
}

export const tenantSiteHandlers = [
  // ── GET /api/v1/tenant-site ──────────────────────────────────────────────
  http.get("/api/v1/tenant-site", () => {
    return HttpResponse.json({
      configured: false,
      site: null,
      defaults: MOCK_DEFAULTS,
    });
  }),

  // ── PUT /api/v1/tenant-site ──────────────────────────────────────────────
  http.put("/api/v1/tenant-site", async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Record<
      string,
      unknown
    >;
    const slug = (body.slug as string) ?? "lang-electric";
    const slugCheck = checkSlug(slug);
    if (!slugCheck.available && slugCheck.reason === "taken") {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/slug-taken",
          title: "Slug is already in use",
          status: 409,
          detail: `The slug "${slug}" is already taken by another tenant.`,
          instance: "/api/v1/tenant-site",
        },
        { status: 409 },
      );
    }
    if (!slugCheck.available && slugCheck.reason === "invalid") {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/slug-invalid",
          title: "Invalid slug format",
          status: 422,
          detail:
            "Slug must be lowercase letters, numbers, and hyphens. Must start and end with a letter or number.",
          instance: "/api/v1/tenant-site",
        },
        { status: 422 },
      );
    }
    if (!slugCheck.available && slugCheck.reason === "reserved") {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/slug-reserved",
          title: "Slug is reserved",
          status: 422,
          detail: `The slug "${slug}" is reserved and cannot be used.`,
          instance: "/api/v1/tenant-site",
        },
        { status: 422 },
      );
    }
    return HttpResponse.json({
      ...MOCK_SITE,
      ...body,
      slug,
      status: "draft",
    });
  }),

  // ── GET /api/v1/tenant-site/slug-availability?slug= ───────────────────────
  http.get("/api/v1/tenant-site/slug-availability", ({ request }) => {
    const url = new URL(request.url);
    const slug = url.searchParams.get("slug") ?? "";
    const result = checkSlug(slug);
    return HttpResponse.json(result);
  }),

  // ── POST /api/v1/tenant-site/publish ─────────────────────────────────────
  // Default: success. Tests override with the 409 branch via server.use(...).
  http.post("/api/v1/tenant-site/publish", async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Record<
      string,
      unknown
    >;
    const confirmOverwrite = body.confirm_website_overwrite === true;
    return HttpResponse.json({
      ...MOCK_SITE,
      status: "published",
      published_at: new Date().toISOString(),
      website_auto_populated: true,
      site_url: "https://lang-electric.p4tsites.com",
      website_action: "set",
      brand_status: "none",
      brand_guidance:
        "Your hosted site URL will be used on first brand submission.",
      requirements_emailed_at: null,
      // Include confirm flag echo for test assertions
      ...(confirmOverwrite ? { confirm_website_overwrite: true } : {}),
    });
  }),

  // ── POST /api/v1/tenant-site/unpublish ───────────────────────────────────
  http.post("/api/v1/tenant-site/unpublish", () => {
    return HttpResponse.json({
      ...MOCK_SITE,
      status: "unpublished",
      unpublished_at: new Date().toISOString(),
      warning:
        "The URL on your 10DLC profile was NOT cleared. If your brand is live, the carrier may still check this URL.",
    });
  }),

  // ── GET /api/v1/public/tenant-sites/:slug ────────────────────────────────
  http.get("/api/v1/public/tenant-sites/:slug", ({ params }) => {
    const slug = params.slug as string;
    if (slug === "not-found" || slug === "unpublished") {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/site-not-found",
          title: "Site not found",
          status: 404,
          detail: "No published site exists at this URL.",
          instance: `/api/v1/public/tenant-sites/${slug}`,
        },
        { status: 404 },
      );
    }
    return HttpResponse.json({
      slug,
      display_name: "Lang Electric",
      tagline: "Residential & commercial electrical — Richmond, VA",
      public_email: "office@langelectric.example",
      public_phone: "+15551234567",
      public_city: "Richmond",
      public_state: "VA",
      public_address_line1: null,
      public_postal_code: null,
      template_version: "v1",
      published_at: "2026-08-14T01:23:45Z",
      pages: {
        landing: {
          heading: "Lang Electric",
          body_paragraphs: [
            "Lang Electric has been serving the Richmond metro area since 2015.",
            "We specialize in residential panel upgrades, commercial tenant build-outs, and EV charger installations.",
          ],
          contact_lines: [
            "(555) 123-4567",
            "office@langelectric.example",
            "Richmond, VA",
          ],
        },
        privacy: {
          title: "Privacy Policy",
          body_paragraphs: [
            "This privacy policy describes how Lang Electric collects, uses, and protects your information.",
            "SMS Communications: We may send you text messages regarding appointment confirmations, service updates, and account alerts. Message frequency varies but is typically no more than 5 messages per month.",
            "Message and data rates may apply.",
            "To opt out, reply STOP to any message. For help, reply HELP.",
            "We do not share mobile information with third parties for marketing or promotional purposes.",
          ],
        },
        terms: {
          title: "Terms of Service",
          body_paragraphs: [
            "These terms govern the use of Lang Electric's services.",
            "SMS Terms: By providing your phone number, you consent to receive SMS messages related to your service appointments and account. Standard message and data rates may apply.",
            "To stop receiving messages, reply STOP. For assistance, reply HELP.",
          ],
        },
      },
    });
  }),
];
