/**
 * TenantSiteHeader — C-B16 public tenant-site shared header
 *
 * Location: apps/web/src/features/tenant-site-public/TenantSiteHeader.tsx
 *
 * Shared header for all tenant-site pages. Renders accent bar + business name
 * + contact line. On landing: business name is H1. On legal pages: business
 * name is a link to "/" (the H1 is the page title). Server component.
 *
 * mkt spec §5.2 + §6.1: accent bar (brand-600, h-1.5), business name H1
 * (text-2xl font-bold) on landing, link on legal pages.
 */

import React from "react";
import Link from "next/link";
import { ContactLine } from "./ContactLine";

interface TenantSiteHeaderProps {
  displayName: string;
  tagline?: string | null;
  publicPhone?: string | null;
  publicEmail?: string | null;
  publicCity?: string | null;
  publicState?: string | null;
  publicAddressLine1?: string | null;
  publicPostalCode?: string | null;
  showFullAddress?: boolean;
  /** "landing" → business name is H1; "legal" → business name is a link to "/" */
  variant: "landing" | "legal";
}

export function TenantSiteHeader({
  displayName,
  tagline,
  publicPhone,
  publicEmail,
  publicCity,
  publicState,
  publicAddressLine1,
  publicPostalCode,
  showFullAddress = false,
  variant,
}: TenantSiteHeaderProps) {
  return (
    <>
      {/* Accent bar — decorative */}
      <div className="h-1.5 w-full bg-brand-600" aria-hidden="true" />

      <header className="mx-auto max-w-2xl px-6 py-6">
        {variant === "landing" ? (
          <h1 className="text-2xl font-bold text-neutral-800">{displayName}</h1>
        ) : (
          <Link
            href="/"
            aria-label={`Back to ${displayName} home`}
            className="inline-block py-1 text-2xl font-bold text-neutral-800 hover:text-neutral-900 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
          >
            {displayName}
          </Link>
        )}

        {tagline && (
          <p className="mt-1 text-body-lg text-neutral-600">{tagline}</p>
        )}

        <ContactLine
          publicPhone={publicPhone}
          publicEmail={publicEmail}
          publicCity={publicCity}
          publicState={publicState}
          publicAddressLine1={publicAddressLine1}
          publicPostalCode={publicPostalCode}
          showFullAddress={showFullAddress}
          compact={variant === "legal"}
        />
      </header>
    </>
  );
}
