/**
 * Email Branding MSW Handlers — FE-B14
 *
 * Location: apps/web/src/mocks/handlers/emailBrandingHandlers.ts
 *
 * Covers BE-B15 / A82:
 *  - GET   /api/v1/settings/email-branding
 *  - PATCH /api/v1/settings/email-branding
 *  - POST  /api/v1/settings/email-branding/logo-upload-url
 *  - POST  /api/v1/settings/email-branding/preview
 *  - POST  /api/v1/settings/email-branding/test-send
 *
 * RULE 8: Email templates are server-rendered — UI does visual review only.
 */

import { http, HttpResponse } from "msw";
import {
  EMAIL_BRANDING_WITH_LOGO,
  EMAIL_BRANDING_LOGO_UPLOAD_URL,
  EMAIL_BRANDING_TEST_SEND_SUCCESS,
  EMAIL_TEMPLATE_PREVIEW_QUOTE_SENT,
  EMAIL_TEMPLATE_PREVIEW_INVOICE_SENT,
  EMAIL_TEMPLATE_PREVIEW_WELCOME,
  makeGenericPreview,
} from "../../features/public-pages/mocks/publicPageFixtures";

const BRANDING_API = "/api/v1/settings/email-branding";

// Mutable in-process branding state (simulates PATCH persistence)
interface BrandingState {
  tenant_id: string;
  logo_url: string | null;
  brand_color_hex: string | null;
  email_signature: string | null;
  custom_footer: string | null;
}
let currentBranding: BrandingState = { ...EMAIL_BRANDING_WITH_LOGO };

export const emailBrandingHandlers = [
  // ─── GET email branding ───────────────────────────────────────────────────

  http.get(BRANDING_API, () => {
    return HttpResponse.json(currentBranding);
  }),

  // ─── PATCH email branding ─────────────────────────────────────────────────

  http.patch(BRANDING_API, async ({ request }) => {
    const body = (await request.json()) as {
      logo_s3_path?: string | null;
      brand_color_hex?: string | null;
      email_signature?: string | null;
      custom_footer?: string | null;
    };

    // Validate hex format if provided
    if (body.brand_color_hex !== undefined && body.brand_color_hex !== null) {
      const hexPattern = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
      if (!hexPattern.test(body.brand_color_hex)) {
        return HttpResponse.json(
          { detail: "Invalid hex color format. Must be #RGB or #RRGGBB." },
          { status: 422 },
        );
      }
    }

    // Validate signature length
    if (body.email_signature && body.email_signature.length > 500) {
      return HttpResponse.json(
        { detail: "Email signature must be 500 characters or fewer." },
        { status: 422 },
      );
    }

    // Validate footer length
    if (body.custom_footer && body.custom_footer.length > 200) {
      return HttpResponse.json(
        { detail: "Custom footer must be 200 characters or fewer." },
        { status: 422 },
      );
    }

    // Apply PATCH semantics
    currentBranding = {
      ...currentBranding,
      ...(body.logo_s3_path !== undefined && {
        logo_url: body.logo_s3_path
          ? `https://cdn.example.com/${body.logo_s3_path}`
          : null,
      }),
      ...(body.brand_color_hex !== undefined && {
        brand_color_hex: body.brand_color_hex,
      }),
      ...(body.email_signature !== undefined && {
        email_signature: body.email_signature,
      }),
      ...(body.custom_footer !== undefined && {
        custom_footer: body.custom_footer,
      }),
    };

    return HttpResponse.json(currentBranding);
  }),

  // ─── POST logo upload URL ──────────────────────────────────────────────────

  http.post(`${BRANDING_API}/logo-upload-url`, async ({ request }) => {
    const body = (await request.json()) as {
      content_type?: string;
      file_size_bytes?: number;
    };

    const allowedTypes = ["image/png", "image/jpeg", "image/webp", "image/gif"];
    if (!body.content_type || !allowedTypes.includes(body.content_type)) {
      return HttpResponse.json(
        { detail: "Unsupported file type. Upload a PNG, JPEG, WebP, or GIF." },
        { status: 422 },
      );
    }

    const maxSizeBytes = 5 * 1024 * 1024; // 5 MB
    if (body.file_size_bytes && body.file_size_bytes > maxSizeBytes) {
      return HttpResponse.json(
        { detail: "Logo must be smaller than 5 MB." },
        { status: 422 },
      );
    }

    return HttpResponse.json(EMAIL_BRANDING_LOGO_UPLOAD_URL);
  }),

  // ─── POST email template preview ─────────────────────────────────────────

  http.post(`${BRANDING_API}/preview`, async ({ request }) => {
    const body = (await request.json()) as { template_id?: string };

    if (!body.template_id) {
      return HttpResponse.json(
        { detail: "template_id is required." },
        { status: 422 },
      );
    }

    // Map known templates to fixture previews
    const previewMap: Record<string, object> = {
      quote_sent: EMAIL_TEMPLATE_PREVIEW_QUOTE_SENT,
      invoice_sent: EMAIL_TEMPLATE_PREVIEW_INVOICE_SENT,
      welcome: EMAIL_TEMPLATE_PREVIEW_WELCOME,
    };

    const validTemplateIds = [
      "welcome",
      "email_verification",
      "quote_sent",
      "quote_accepted",
      "quote_declined",
      "quote_expiring_soon",
      "invoice_sent",
      "payment_received_tenant",
      "payment_received_customer",
      "payment_failed",
      "subscription_renewal_receipt",
      "subscription_payment_failed",
      "trial_expiring_soon",
      "trial_expired",
      "password_reset",
      "mfa_reset_by_owner",
      "data_export_ready",
    ];

    if (!validTemplateIds.includes(body.template_id)) {
      return HttpResponse.json(
        { detail: `Unknown template_id: ${body.template_id}` },
        { status: 404 },
      );
    }

    const preview =
      previewMap[body.template_id] ?? makeGenericPreview(body.template_id);

    return HttpResponse.json(preview);
  }),

  // ─── POST test-send ──────────────────────────────────────────────────────

  http.post(`${BRANDING_API}/test-send`, () => {
    return HttpResponse.json(EMAIL_BRANDING_TEST_SEND_SUCCESS);
  }),
];
