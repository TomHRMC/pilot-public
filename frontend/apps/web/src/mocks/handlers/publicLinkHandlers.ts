/**
 * Public Link MSW Handlers — FE-B14
 *
 * Location: apps/web/src/mocks/handlers/publicLinkHandlers.ts
 *
 * Covers BE-B15 / A80–A83:
 *  - GET  /api/v1/public/quotes/{signed_token}
 *  - POST /api/v1/public/quotes/{signed_token}/accept
 *  - POST /api/v1/public/quotes/{signed_token}/decline
 *  - GET  /api/v1/public/invoices/{signed_token}
 *  - POST /api/v1/public/invoices/{signed_token}/payment-intent
 *  - POST /api/v1/public/invoices/{signed_token}/confirm-payment
 *
 * RULE 1: No JWT required — these are unauthenticated endpoints.
 * RULE 7: Customer comments are entity-bound; NOT routed to comms threads.
 */

import { http, HttpResponse } from "msw";
import {
  PUBLIC_QUOTE_ACTIVE,
  PUBLIC_QUOTE_ACCEPTED,
  PUBLIC_QUOTE_DECLINED,
  QUOTE_ACCEPT_SUCCESS,
  QUOTE_DECLINE_SUCCESS,
  PUBLIC_INVOICE_UNPAID,
  PUBLIC_INVOICE_PAID,
  PUBLIC_INVOICE_PARTIAL,
  STRIPE_ONE_TIME_PAYMENT_INTENT,
  STRIPE_PAYMENT_INTENT_DECLINED,
  PAYMENT_CONFIRM_ADVISORY,
} from "../../features/public-pages/mocks/publicPageFixtures";

const PUBLIC_API = "/api/v1/public";

// Simulate accepted/declined state transitions in-process
const quoteStateOverrides = new Map<string, "accepted" | "declined">();

export const publicLinkHandlers = [
  // ─── GET public quote ────────────────────────────────────────────────────

  http.get(`${PUBLIC_API}/quotes/:signedToken`, ({ params }) => {
    const { signedToken } = params as { signedToken: string };

    // Simulate tampered/invalid token (401)
    if (signedToken === "invalid-token") {
      return HttpResponse.json(
        { detail: "Invalid or tampered link." },
        { status: 401 },
      );
    }

    // Simulate expired/revoked token (410)
    if (signedToken === "expired-token") {
      return HttpResponse.json(
        {
          detail: "This link has expired.",
          tenant_name: "Acme Electric LLC",
          tenant_phone: "(555) 123-4567",
          tenant_email: "hello@acme-electric.example.com",
        },
        { status: 410 },
      );
    }

    // Simulate accepted state (in-process state override)
    if (quoteStateOverrides.get(signedToken) === "accepted") {
      return HttpResponse.json(PUBLIC_QUOTE_ACCEPTED);
    }
    if (quoteStateOverrides.get(signedToken) === "declined") {
      return HttpResponse.json(PUBLIC_QUOTE_DECLINED);
    }

    // Return already-accepted quote by token prefix
    if (signedToken.startsWith("accepted-")) {
      return HttpResponse.json(PUBLIC_QUOTE_ACCEPTED);
    }

    // Return already-declined quote by token prefix
    if (signedToken.startsWith("declined-")) {
      return HttpResponse.json(PUBLIC_QUOTE_DECLINED);
    }

    // Default: active quote
    return HttpResponse.json(PUBLIC_QUOTE_ACTIVE);
  }),

  // ─── POST accept quote ────────────────────────────────────────────────────

  http.post(`${PUBLIC_API}/quotes/:signedToken/accept`, async ({ params }) => {
    const { signedToken } = params as { signedToken: string };

    // 410 for expired token
    if (signedToken === "expired-token") {
      return HttpResponse.json(
        { detail: "This link has expired." },
        { status: 410 },
      );
    }

    // 409 if already accepted/declined
    if (
      quoteStateOverrides.get(signedToken) === "accepted" ||
      quoteStateOverrides.get(signedToken) === "declined" ||
      signedToken.startsWith("accepted-") ||
      signedToken.startsWith("declined-")
    ) {
      return HttpResponse.json(
        { detail: "This quote has already been responded to." },
        { status: 409 },
      );
    }

    // Mark as accepted in-process
    quoteStateOverrides.set(signedToken, "accepted");

    return HttpResponse.json(QUOTE_ACCEPT_SUCCESS);
  }),

  // ─── POST decline quote ───────────────────────────────────────────────────

  http.post(
    `${PUBLIC_API}/quotes/:signedToken/decline`,
    async ({ params, request }) => {
      const { signedToken } = params as { signedToken: string };

      // 410 for expired token
      if (signedToken === "expired-token") {
        return HttpResponse.json(
          { detail: "This link has expired." },
          { status: 410 },
        );
      }

      // 409 if already responded
      if (
        quoteStateOverrides.get(signedToken) === "accepted" ||
        quoteStateOverrides.get(signedToken) === "declined"
      ) {
        return HttpResponse.json(
          { detail: "This quote has already been responded to." },
          { status: 409 },
        );
      }

      const body = (await request.json()) as {
        reason?: string;
        comment?: string;
      };

      // 422 for invalid reason
      const validReasons = [
        "pricing",
        "scope",
        "timing",
        "other_contractor",
        "other",
      ];
      if (!body.reason || !validReasons.includes(body.reason)) {
        return HttpResponse.json(
          { detail: "Invalid decline reason." },
          { status: 422 },
        );
      }

      // Mark as declined in-process
      quoteStateOverrides.set(signedToken, "declined");

      return HttpResponse.json(QUOTE_DECLINE_SUCCESS);
    },
  ),

  // ─── GET public invoice ────────────────────────────────────────────────────

  http.get(`${PUBLIC_API}/invoices/:signedToken`, ({ params }) => {
    const { signedToken } = params as { signedToken: string };

    // 401 for tampered token
    if (signedToken === "invalid-token") {
      return HttpResponse.json(
        { detail: "Invalid or tampered link." },
        { status: 401 },
      );
    }

    // 410 for expired token
    if (signedToken === "expired-token") {
      return HttpResponse.json(
        {
          detail: "This link has expired.",
          tenant_name: "Acme Electric LLC",
          tenant_phone: "(555) 123-4567",
          tenant_email: "hello@acme-electric.example.com",
        },
        { status: 410 },
      );
    }

    // Paid invoice by token prefix
    if (signedToken.startsWith("paid-")) {
      return HttpResponse.json(PUBLIC_INVOICE_PAID);
    }

    // Partially paid invoice by token prefix
    if (signedToken.startsWith("partial-")) {
      return HttpResponse.json(PUBLIC_INVOICE_PARTIAL);
    }

    // Default: unpaid invoice
    return HttpResponse.json(PUBLIC_INVOICE_UNPAID);
  }),

  // ─── POST payment-intent ──────────────────────────────────────────────────

  http.post(
    `${PUBLIC_API}/invoices/:signedToken/payment-intent`,
    async ({ params, request }) => {
      const { signedToken } = params as { signedToken: string };

      // 410 for expired
      if (signedToken === "expired-token") {
        return HttpResponse.json(
          { detail: "This link has expired." },
          { status: 410 },
        );
      }

      const body = (await request.json()) as {
        amount_cents?: number;
        comment?: string;
      };

      // 422 for amount <= 0
      if (!body.amount_cents || body.amount_cents <= 0) {
        return HttpResponse.json(
          { detail: "Amount must be greater than $0." },
          { status: 422 },
        );
      }

      // 422 if amount differs from invoice total and comment is missing
      const invoiceTotalCents = PUBLIC_INVOICE_UNPAID.invoice_total_cents;
      if (body.amount_cents !== invoiceTotalCents && !body.comment) {
        return HttpResponse.json(
          { detail: "A comment is required when paying a different amount." },
          { status: 422 },
        );
      }

      // Simulate declined card for test token
      if (signedToken === "decline-card-token") {
        return HttpResponse.json(STRIPE_PAYMENT_INTENT_DECLINED, {
          status: 402,
        });
      }

      return HttpResponse.json(STRIPE_ONE_TIME_PAYMENT_INTENT);
    },
  ),

  // ─── POST confirm-payment (advisory) ─────────────────────────────────────

  http.post(
    `${PUBLIC_API}/invoices/:signedToken/confirm-payment`,
    async ({ params }) => {
      const { signedToken } = params as { signedToken: string };

      // 410 for expired
      if (signedToken === "expired-token") {
        return HttpResponse.json(
          { detail: "This link has expired." },
          { status: 410 },
        );
      }

      return HttpResponse.json(PAYMENT_CONFIRM_ADVISORY);
    },
  ),
];
