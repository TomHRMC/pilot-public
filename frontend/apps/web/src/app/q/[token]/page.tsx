/**
 * Public Quote Route — /q/[token]
 *
 * Location: apps/web/src/app/q/[token]/page.tsx
 *
 * RULE 1 — CRITICAL: This file MUST NEVER import or call:
 *   - useAuth()
 *   - RequireAuth
 *   - RoleGate
 *   - Any auth-related hook or component
 *
 * This route is outside the (authed) layout group.
 * Customers access this URL directly from their email — they have NO Pilot account.
 * Authentication is provided solely by the signed token in the URL path (RULE 4).
 *
 * SEO: noindex/nofollow — customer-specific document, must not be indexed.
 */

import React from "react";
import type { Metadata } from "next";
import { PublicQuotePage } from "@/features/public-quote/PublicQuotePage";

interface QuotePageProps {
  params: Promise<{ token: string }>;
}

export async function generateMetadata({
  params,
}: QuotePageProps): Promise<Metadata> {
  const { token } = await params;

  try {
    // Fetch quote data for metadata — gracefully fall back on failure.
    // Use NEXT_PUBLIC_API_URL — same variable as the /api/v1/* rewrite proxy in
    // next.config.ts. Falls back to empty string → TypeError caught below → generic
    // metadata returned, never a 500.
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/public/quotes/${token}`,
      { next: { revalidate: 0 } }, // no caching — customer-specific
    );

    if (res.ok) {
      const data = (await res.json()) as {
        tenant_name?: string;
        quote_total_cents?: number;
        currency?: string;
      };
      const tenantName = data.tenant_name ?? "Your contractor";
      const totalFormatted = data.quote_total_cents
        ? new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: data.currency ?? "USD",
          }).format(data.quote_total_cents / 100)
        : "";

      return {
        title: `Quote from ${tenantName}${totalFormatted ? ` — ${totalFormatted}` : ""}`,
        description: `View and accept or decline your quote from ${tenantName}.`,
        robots: "noindex, nofollow",
      };
    }
  } catch {
    // Fall through to generic metadata
  }

  return {
    title: "View Your Quote",
    description: "View and respond to your quote.",
    robots: "noindex, nofollow",
  };
}

export default async function QuotePage({ params }: QuotePageProps) {
  const { token } = await params;
  return <PublicQuotePage token={token} />;
}
