/**
 * Public Page Fixtures — FE-B14
 *
 * Location: apps/web/src/features/public-pages/mocks/publicPageFixtures.ts
 *
 * Fixtures for MSW handlers covering:
 *  - Public quote: active, expired
 *  - Public invoice: unpaid, paid, partially paid
 *  - Stripe PaymentIntent: success, card declined
 *  - Customer comment: success
 *  - Email branding: with logo, defaults
 *  - Email template: list + preview
 */

// ─── Public Quote Fixtures ────────────────────────────────────────────────────

export const PUBLIC_QUOTE_ACTIVE = {
  quote_id: "quote-00000000-0000-0000-0000-000000000001",
  tenant_name: "Acme Electric LLC",
  customer_name: "Mike Johnson",
  quote_total_cents: 386583,
  currency: "USD",
  line_items: [
    {
      description: "Panel Upgrade — 200A Main Service",
      quantity: "1",
      unit_price_cents: 185000,
      total_cents: 185000,
    },
    {
      description: "Circuit Installation — Kitchen (20A GFCI)",
      quantity: "3",
      unit_price_cents: 42500,
      total_cents: 127500,
    },
    {
      description: "Smoke / CO Detector Installation",
      quantity: "4",
      unit_price_cents: 12500,
      total_cents: 50000,
    },
    {
      description: "Permit & Inspection Fee",
      quantity: "1",
      unit_price_cents: 24083,
      total_cents: 24083,
    },
  ],
  status: "sent",
  expires_at: new Date(Date.now() + 60 * 24 * 60 * 60 * 1000).toISOString(),
  branding: {
    logo_url: "https://cdn.example.com/logos/acme-electric.png",
    // eslint-disable-next-line pilot/no-hardcoded-design-values
    brand_color_hex: "#E05A2B",
  },
  customer_acceptance_comment: null,
  customer_decline_comment: null,
};

export const PUBLIC_QUOTE_EXPIRED = {
  quote_id: "quote-00000000-0000-0000-0000-000000000002",
  tenant_name: "Acme Electric LLC",
  customer_name: "Sarah Chen",
  quote_total_cents: 124500,
  currency: "USD",
  line_items: [
    {
      description: "Outlet Replacement (GFCI)",
      quantity: "5",
      unit_price_cents: 24900,
      total_cents: 124500,
    },
  ],
  status: "expired",
  expires_at: new Date(Date.now() - 91 * 24 * 60 * 60 * 1000).toISOString(),
  branding: {
    logo_url: null,
    // eslint-disable-next-line pilot/no-hardcoded-design-values
    brand_color_hex: "#3B43D6",
  },
  customer_acceptance_comment: null,
  customer_decline_comment: null,
};

export const PUBLIC_QUOTE_ACCEPTED = {
  ...PUBLIC_QUOTE_ACTIVE,
  quote_id: "quote-00000000-0000-0000-0000-000000000003",
  status: "accepted",
  customer_acceptance_comment: "Looks good, please proceed!",
  customer_decline_comment: null,
};

export const PUBLIC_QUOTE_DECLINED = {
  ...PUBLIC_QUOTE_ACTIVE,
  quote_id: "quote-00000000-0000-0000-0000-000000000004",
  status: "declined",
  customer_acceptance_comment: null,
  customer_decline_comment: "The pricing is a bit high for our budget.",
};

export const QUOTE_ACCEPT_SUCCESS = {
  status: "accepted",
  accepted_at: new Date().toISOString(),
};

export const QUOTE_DECLINE_SUCCESS = {
  status: "declined",
  declined_at: new Date().toISOString(),
};

// ─── Public Invoice Fixtures ──────────────────────────────────────────────────

export const PUBLIC_INVOICE_UNPAID = {
  invoice_id: "inv-00000000-0000-0000-0000-000000000001",
  tenant_name: "Acme Electric LLC",
  customer_name: "Mike Johnson",
  invoice_total_cents: 386583,
  amount_paid_cents: 0,
  amount_due_cents: 386583,
  currency: "USD",
  line_items: [
    {
      description: "Panel Upgrade — 200A Main Service",
      quantity: "1",
      unit_price_cents: 185000,
      total_cents: 185000,
    },
    {
      description: "Circuit Installation — Kitchen (20A GFCI)",
      quantity: "3",
      unit_price_cents: 42500,
      total_cents: 127500,
    },
    {
      description: "Smoke / CO Detector Installation",
      quantity: "4",
      unit_price_cents: 12500,
      total_cents: 50000,
    },
    {
      description: "Permit & Inspection Fee",
      quantity: "1",
      unit_price_cents: 24083,
      total_cents: 24083,
    },
  ],
  status: "unpaid",
  due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  branding: {
    logo_url: "https://cdn.example.com/logos/acme-electric.png",
    // eslint-disable-next-line pilot/no-hardcoded-design-values
    brand_color_hex: "#E05A2B",
  },
  // STRIPE-CONNECT-1-C: card-payment capability + manual-payment contact fields.
  // Default fixture = enabled with both contact fields present; per-test server.use
  // overrides cover disabled / phone-only / email-only / both-null variants.
  card_payments_enabled: true,
  payment_unavailable_reason: null,
  tenant_phone: "(804) 555-0142",
  tenant_email: "billing@example.com",
};

export const PUBLIC_INVOICE_PAID = {
  ...PUBLIC_INVOICE_UNPAID,
  invoice_id: "inv-00000000-0000-0000-0000-000000000002",
  amount_paid_cents: 386583,
  amount_due_cents: 0,
  status: "paid",
};

export const PUBLIC_INVOICE_PARTIAL = {
  ...PUBLIC_INVOICE_UNPAID,
  invoice_id: "inv-00000000-0000-0000-0000-000000000003",
  amount_paid_cents: 200000,
  amount_due_cents: 186583,
  status: "partial",
};

// ─── Stripe PaymentIntent Fixtures ────────────────────────────────────────────

export const STRIPE_ONE_TIME_PAYMENT_INTENT = {
  client_secret: "pi_3test_secret_abcdefghijklmnop",
  payment_intent_id: "pi_3test_abcdefghijklmnop",
};

export const STRIPE_PAYMENT_INTENT_DECLINED = {
  detail: "Your card was declined.",
  code: "card_declined",
  decline_code: "card_declined",
};

export const PAYMENT_CONFIRM_ADVISORY = {
  status: "pending_confirmation",
};

// ─── Email Branding Fixtures ──────────────────────────────────────────────────

export const EMAIL_BRANDING_WITH_LOGO = {
  tenant_id: "tenant-00000000-0000-0000-0000-000000000001",
  logo_url: "https://cdn.example.com/logos/acme-electric.png",
  // eslint-disable-next-line pilot/no-hardcoded-design-values
  brand_color_hex: "#E05A2B",
  email_signature: "Mike Thompson\nAcme Electric LLC\n(555) 123-4567",
  custom_footer:
    "Licensed & Insured · Serving the Greater Metro Area · License #EL-12345",
};

export const EMAIL_BRANDING_DEFAULTS = {
  tenant_id: "tenant-00000000-0000-0000-0000-000000000002",
  logo_url: null,
  brand_color_hex: null,
  email_signature: null,
  custom_footer: null,
};

export const EMAIL_BRANDING_LOGO_UPLOAD_URL = {
  upload_url:
    "https://s3.amazonaws.com/pilot-logos/acme-electric.png?X-Amz-Signature=test",
  s3_path: "tenant-logos/acme-electric.png",
};

export const EMAIL_BRANDING_TEST_SEND_SUCCESS = {
  status: "sent",
  to: "mike@acme-electric.example.com",
};

// ─── Email Template Fixtures ──────────────────────────────────────────────────

export const EMAIL_TEMPLATE_PREVIEW_QUOTE_SENT = {
  subject: "Quote from Acme Electric LLC — Panel Upgrade — 200A",
  body_html: `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Quote from Acme Electric LLC</title></head>
<body style="font-family: sans-serif; color: #333; max-width: 560px; margin: 0 auto; padding: 24px;">
  <div style="background-color: #E05A2B; padding: 24px; border-radius: 8px 8px 0 0;">
    <img src="https://cdn.example.com/logos/acme-electric.png" alt="Acme Electric LLC" style="height: 40px; object-fit: contain;" />
  </div>
  <div style="background: #fff; padding: 32px; border: 1px solid #e5e7eb; border-top: none;">
    <h1 style="font-size: 22px; margin-top: 0;">Hi Mike Johnson,</h1>
    <p>We've prepared a quote for you for Panel Upgrade — 200A Main Service.</p>
    <p><strong>Quote total: $3,865.83</strong></p>
    <p>This quote expires on {{quote_expiry_date}}.</p>
    <div style="margin: 32px 0; text-align: center;">
      <a href="{{quote_url}}" style="background-color: #E05A2B; color: #fff; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-weight: 600;">View & Accept Quote</a>
    </div>
    <p style="color: #6b7280; font-size: 14px;">Mike Thompson<br>Acme Electric LLC<br>(555) 123-4567</p>
  </div>
  <div style="padding: 16px; text-align: center; color: #9ca3af; font-size: 12px;">
    Licensed &amp; Insured · Serving the Greater Metro Area · License #EL-12345<br>
    <br>Powered by <a href="https://pilotfortrades.com" style="color: #9ca3af;">Pilot for Trades</a>
  </div>
</body>
</html>`,
  body_plain:
    "Hi Mike Johnson,\n\nWe've prepared a quote for you. View it at {{quote_url}}\n\nMike Thompson\nAcme Electric LLC",
};

export const EMAIL_TEMPLATE_PREVIEW_INVOICE_SENT = {
  subject: "Invoice from Acme Electric LLC — INV-2026-001",
  body_html: `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Invoice from Acme Electric LLC</title></head>
<body style="font-family: sans-serif; color: #333; max-width: 560px; margin: 0 auto; padding: 24px;">
  <div style="background-color: #E05A2B; padding: 24px; border-radius: 8px 8px 0 0;">
    <img src="https://cdn.example.com/logos/acme-electric.png" alt="Acme Electric LLC" style="height: 40px; object-fit: contain;" />
  </div>
  <div style="background: #fff; padding: 32px; border: 1px solid #e5e7eb; border-top: none;">
    <h1 style="font-size: 22px; margin-top: 0;">Invoice INV-2026-001</h1>
    <p>Amount due: <strong>$3,865.83</strong></p>
    <p>Due date: {{due_date}}</p>
    <div style="margin: 32px 0; text-align: center;">
      <a href="{{invoice_url}}" style="background-color: #E05A2B; color: #fff; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-weight: 600;">Pay Invoice</a>
    </div>
  </div>
</body>
</html>`,
  body_plain:
    "Invoice INV-2026-001\nAmount due: $3,865.83\nPay at {{invoice_url}}",
};

export const EMAIL_TEMPLATE_PREVIEW_WELCOME = {
  subject: "Welcome to Pilot for Trades",
  body_html: `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Welcome to Pilot for Trades</title></head>
<body style="font-family: sans-serif; color: #333; max-width: 560px; margin: 0 auto; padding: 24px;">
  <div style="background-color: #3B43D6; padding: 24px; border-radius: 8px 8px 0 0; text-align: center;">
    <h1 style="color: #fff; margin: 0;">Pilot for Trades</h1>
  </div>
  <div style="background: #fff; padding: 32px; border: 1px solid #e5e7eb; border-top: none;">
    <h2>Welcome, {{owner_name}}!</h2>
    <p>Your Pilot account is ready. Start your 14-day free trial today.</p>
    <div style="margin: 32px 0; text-align: center;">
      <a href="{{dashboard_url}}" style="background-color: #3B43D6; color: #fff; padding: 14px 28px; border-radius: 6px; text-decoration: none; font-weight: 600;">Go to Dashboard</a>
    </div>
  </div>
</body>
</html>`,
  body_plain:
    "Welcome to Pilot for Trades, {{owner_name}}!\n\nVisit {{dashboard_url}} to get started.",
};

// Generic preview for all other templates
export function makeGenericPreview(templateId: string) {
  return {
    subject: `[Preview] ${templateId.replace(/_/g, " ")} email`,
    body_html: `<!DOCTYPE html><html><body style="font-family:sans-serif;padding:32px;max-width:560px;margin:0 auto;">
<h1 style="color:#3B43D6;">${templateId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} Template</h1>
<p>This is a preview of the <strong>${templateId}</strong> email template.</p>
<p>Placeholder variables: <code>{{tenant_name}}</code>, <code>{{customer_name}}</code>, etc.</p>
<p style="color:#9ca3af;font-size:12px;margin-top:48px;text-align:center;">Powered by <a href="https://pilotfortrades.com" style="color:#9ca3af;">Pilot for Trades</a></p>
</body></html>`,
    body_plain: `Preview of ${templateId} template.\nPowered by Pilot for Trades.`,
  };
}
