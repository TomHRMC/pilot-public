/**
 * Public Invoice Route — /i/[token]
 *
 * Location: apps/web/src/app/i/[token]/page.tsx
 *
 * RULE 1 — CRITICAL: This file MUST NEVER import or call:
 *   - useAuth()
 *   - RequireAuth
 *   - RoleGate
 *   - Any auth-related hook or component
 *
 * Customers access this URL from their email — no Pilot account required.
 * Authentication is solely the signed token (RULE 4).
 *
 * SEO: noindex/nofollow — customer-specific document.
 */

import React from "react";
import type { Metadata } from "next";
import { PublicInvoicePage } from "@/features/public-invoice/PublicInvoicePage";

interface InvoicePageProps {
  params: Promise<{ token: string }>;
}

export async function generateMetadata({
  params,
}: InvoicePageProps): Promise<Metadata> {
  const { token } = await params;

  try {
    // Use NEXT_PUBLIC_API_URL — same variable as the /api/v1/* rewrite proxy in
    // next.config.ts. Falls back to empty string → TypeError caught below → generic
    // metadata returned, never a 500.
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/public/invoices/${token}`,
      { next: { revalidate: 0 } },
    );

    if (res.ok) {
      const data = (await res.json()) as {
        tenant_name?: string;
        amount_due_cents?: number;
        currency?: string;
      };
      const tenantName = data.tenant_name ?? "Your contractor";
      const amountFormatted = data.amount_due_cents
        ? new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: data.currency ?? "USD",
          }).format(data.amount_due_cents / 100)
        : "";

      return {
        title: `Invoice from ${tenantName}${amountFormatted ? ` — ${amountFormatted} due` : ""}`,
        description: `View and pay your invoice from ${tenantName}.`,
        robots: "noindex, nofollow",
      };
    }
  } catch {
    // Fall through to generic metadata
  }

  return {
    title: "View Your Invoice",
    description: "View and pay your invoice.",
    robots: "noindex, nofollow",
  };
}

export default async function InvoicePage({ params }: InvoicePageProps) {
  const { token } = await params;
  return <PublicInvoicePage token={token} />;
}
