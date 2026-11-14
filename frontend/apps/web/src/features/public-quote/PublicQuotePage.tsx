/**
 * PublicQuotePage — FE-B14
 *
 * Location: apps/web/src/features/public-quote/PublicQuotePage.tsx
 *
 * Client component: fetches quote data via the signed token and orchestrates
 * the full public quote page UI state machine.
 *
 * RULE 1 — CRITICAL: This component NEVER calls useAuth(), RequireAuth,
 *           RoleGate, or any auth-related hook. Public quotes are accessed
 *           by customers who have no Pilot account.
 * RULE 4: Signed URL is the ONLY authentication. Token passed to backend as
 *          URL path param. Backend validates the HMAC signature.
 * RULE 5: Tenant brand color applied as CSS custom property, never Tailwind class.
 */

"use client";

import React, { useCallback, useEffect, useState } from "react";
import { parseProblemBody } from "@pilot/shared-api";
import type {
  PublicQuoteData,
  QuoteActionState,
  DeclineReason,
  ExpiredLinkMeta,
} from "./types";
import { TenantBrandedHeader } from "./TenantBrandedHeader";
import { PoweredByPilotFooter } from "./PoweredByPilotFooter";
import { QuoteLineItemsTable } from "./QuoteLineItemsTable";
import { QuoteAcceptModal } from "./QuoteAcceptModal";
import { QuoteDeclineModal } from "./QuoteDeclineModal";
import { QuoteAcceptedState } from "./QuoteAcceptedState";
import { QuoteDeclinedState } from "./QuoteDeclinedState";
import { QuoteExpiredPage } from "./QuoteExpiredPage";

// Normalize snake_case API response to camelCase
function normalizeQuoteData(raw: Record<string, unknown>): PublicQuoteData {
  const branding = raw.branding as {
    logo_url: string | null;
    brand_color_hex: string | null;
  };
  const lineItems = (raw.line_items as Array<Record<string, unknown>>).map(
    (item) => ({
      description: item.description as string,
      quantity: item.quantity as string,
      unitPriceCents: item.unit_price_cents as number,
      totalCents: item.total_cents as number,
    }),
  );

  return {
    quoteId: raw.quote_id as string,
    tenantName: raw.tenant_name as string,
    customerName: raw.customer_name as string,
    quoteTotalCents: raw.quote_total_cents as number,
    currency: (raw.currency as string) ?? "USD",
    lineItems,
    status: raw.status as PublicQuoteData["status"],
    expiresAt: (raw.expires_at as string | null) ?? null,
    branding: {
      logoUrl: branding.logo_url,
      // eslint-disable-next-line pilot/no-hardcoded-design-values
      brandColorHex: branding.brand_color_hex ?? "#3B43D6",
    },
    customerAcceptanceComment:
      (raw.customer_acceptance_comment as string | null) ?? null,
    customerDeclineComment:
      (raw.customer_decline_comment as string | null) ?? null,
  };
}

type PageState =
  | { phase: "loading" }
  | { phase: "error-expired"; meta?: ExpiredLinkMeta }
  | { phase: "error-invalid" }
  | { phase: "error-generic"; message: string }
  | { phase: "ready"; quote: PublicQuoteData };

interface PublicQuotePageProps {
  token: string;
}

export function PublicQuotePage({ token }: PublicQuotePageProps) {
  const [pageState, setPageState] = useState<PageState>({ phase: "loading" });
  const [overlay, setOverlay] = useState<"none" | "accept" | "decline">("none");
  const [actionState, setActionState] = useState<QuoteActionState>({
    phase: "idle",
  });

  // RULE 1: NO useAuth() — this function uses no auth context whatsoever
  const fetchQuote = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/public/quotes/${token}`);

      if (res.status === 410) {
        const data = (await res.json()) as {
          tenant_name?: string;
          tenant_phone?: string;
          tenant_email?: string;
        };
        setPageState({
          phase: "error-expired",
          meta: {
            tenantName: data.tenant_name,
            tenantPhone: data.tenant_phone,
            tenantEmail: data.tenant_email,
          },
        });
        return;
      }

      if (res.status === 401 || res.status === 404) {
        setPageState({ phase: "error-invalid" });
        return;
      }

      if (!res.ok) {
        const errorData = (await res.json().catch(() => null)) as unknown;
        const problem = parseProblemBody(res.status, errorData);
        setPageState({
          phase: "error-generic",
          message: problem.detail ?? `Error ${res.status}`,
        });
        return;
      }

      const data = (await res.json()) as Record<string, unknown>;
      const quote = normalizeQuoteData(data);
      setPageState({ phase: "ready", quote });
    } catch {
      setPageState({
        phase: "error-generic",
        message: "Could not load quote. Check your connection and try again.",
      });
    }
  }, [token]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchQuote();
  }, [fetchQuote]);

  async function handleAccept(comment?: string) {
    setActionState({ phase: "submitting" });
    try {
      const res = await fetch(`/api/v1/public/quotes/${token}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment }),
      });

      if (res.status === 409) {
        // Already accepted/declined — refresh the page state
        setOverlay("none");
        void fetchQuote();
        return;
      }

      if (!res.ok) {
        const err = (await res.json()) as { detail?: string };
        setActionState({ phase: "error", message: err.detail });
        return;
      }

      const data = (await res.json()) as { accepted_at?: string };
      setActionState({ phase: "success", acceptedAt: data.accepted_at });
      setOverlay("none");
      void fetchQuote();
    } catch {
      setActionState({
        phase: "error",
        message: "Could not submit. Please try again.",
      });
    }
  }

  async function handleDecline(reason: DeclineReason, comment?: string) {
    setActionState({ phase: "submitting" });
    try {
      const res = await fetch(`/api/v1/public/quotes/${token}/decline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason, comment }),
      });

      if (res.status === 409) {
        setOverlay("none");
        void fetchQuote();
        return;
      }

      if (!res.ok) {
        const err = (await res.json()) as { detail?: string };
        setActionState({ phase: "error", message: err.detail });
        return;
      }

      const data = (await res.json()) as { declined_at?: string };
      setActionState({ phase: "success", declinedAt: data.declined_at });
      setOverlay("none");
      void fetchQuote();
    } catch {
      setActionState({
        phase: "error",
        message: "Could not submit. Please try again.",
      });
    }
  }

  // ─── Loading ──────────────────────────────────────────────────────────────
  if (pageState.phase === "loading") {
    return (
      <div
        className="min-h-screen bg-neutral-50 flex items-center justify-center"
        data-testid="quote-loading"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-2 border-neutral-300 border-t-neutral-700 animate-spin" />
          <p className="text-sm text-neutral-500">Loading quote…</p>
        </div>
      </div>
    );
  }

  // ─── Error: 410 Expired / revoked ─────────────────────────────────────────
  if (pageState.phase === "error-expired") {
    return <QuoteExpiredPage meta={pageState.meta} />;
  }

  // ─── Error: 401 Invalid / tampered token ──────────────────────────────────
  if (pageState.phase === "error-invalid") {
    return (
      <div
        className="min-h-screen bg-fault-50 flex flex-col"
        data-testid="quote-invalid-page"
      >
        <main className="flex-1 flex items-center justify-center px-4 py-16">
          <div className="w-full max-w-md rounded-xl border border-fault-200 bg-white p-8 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-fault-600">
              Invalid link
            </h1>
            <p className="mt-2 text-sm text-neutral-600">
              This link is invalid or has been tampered with. Please check the
              link in your email and try again.
            </p>
          </div>
        </main>
        <PoweredByPilotFooter />
      </div>
    );
  }

  // ─── Error: generic ───────────────────────────────────────────────────────
  if (pageState.phase === "error-generic") {
    return (
      <div
        className="min-h-screen bg-neutral-50 flex flex-col"
        data-testid="quote-error-page"
      >
        <main className="flex-1 flex items-center justify-center px-4 py-16">
          <div className="w-full max-w-md rounded-xl border border-neutral-200 bg-white p-8 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-neutral-800">
              Something went wrong
            </h1>
            <p className="mt-2 text-sm text-neutral-500">{pageState.message}</p>
            <button
              onClick={() => {
                setPageState({ phase: "loading" });
                void fetchQuote();
              }}
              className="mt-4 rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
            >
              Try again
            </button>
          </div>
        </main>
        <PoweredByPilotFooter />
      </div>
    );
  }

  const { quote } = pageState;

  // RULE 5: Tenant color applied as CSS variable on page root
  const tenantBrandStyle = {
    "--tenant-brand": quote.branding.brandColorHex,
  } as React.CSSProperties;

  return (
    <div
      className="min-h-screen bg-neutral-50 flex flex-col"
      style={tenantBrandStyle}
      data-testid="public-quote-page"
    >
      {/* Overlays */}
      {overlay === "accept" && (
        <QuoteAcceptModal
          tenantName={quote.tenantName}
          onConfirm={handleAccept}
          onCancel={() => {
            setOverlay("none");
            setActionState({ phase: "idle" });
          }}
          actionState={actionState}
        />
      )}
      {overlay === "decline" && (
        <QuoteDeclineModal
          tenantName={quote.tenantName}
          onConfirm={handleDecline}
          onCancel={() => {
            setOverlay("none");
            setActionState({ phase: "idle" });
          }}
          actionState={actionState}
        />
      )}

      {/* Header */}
      <TenantBrandedHeader
        tenantName={quote.tenantName}
        branding={quote.branding}
      />

      {/* Main content */}
      <main className="flex-1 mx-auto w-full max-w-2xl px-4 py-8 flex flex-col gap-6">
        {/* Quote header */}
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Quote for {quote.customerName}
          </h1>
          {quote.expiresAt && quote.status === "sent" && (
            <p className="mt-1 text-sm text-neutral-500">
              Valid until{" "}
              {new Intl.DateTimeFormat("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              }).format(new Date(quote.expiresAt))}
            </p>
          )}
        </div>

        {/* State-aware revisit: accepted */}
        {quote.status === "accepted" && (
          <QuoteAcceptedState
            customerComment={quote.customerAcceptanceComment}
          />
        )}

        {/* State-aware revisit: declined */}
        {quote.status === "declined" && (
          <QuoteDeclinedState customerComment={quote.customerDeclineComment} />
        )}

        {/* Line items table */}
        <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
          <QuoteLineItemsTable
            lineItems={quote.lineItems}
            currency={quote.currency}
            quoteTotalCents={quote.quoteTotalCents}
          />
        </div>

        {/* Accept / Decline CTA — only for 'sent' status */}
        {quote.status === "sent" && (
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => {
                setActionState({ phase: "idle" });
                setOverlay("accept");
              }}
              className="flex-1 rounded-lg py-3 px-6 text-sm font-semibold text-white"
              style={{ backgroundColor: "var(--tenant-brand)" }}
              data-testid="accept-quote-button"
            >
              Accept quote
            </button>
            <button
              onClick={() => {
                setActionState({ phase: "idle" });
                setOverlay("decline");
              }}
              className="flex-1 rounded-lg border border-neutral-300 py-3 px-6 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              data-testid="decline-quote-button"
            >
              Decline
            </button>
          </div>
        )}
      </main>

      <PoweredByPilotFooter />
    </div>
  );
}
