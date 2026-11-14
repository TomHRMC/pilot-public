/**
 * TenantBrandedHeader — FE-B14
 *
 * Location: apps/web/src/features/public-quote/TenantBrandedHeader.tsx
 *
 * Shared by both public quote and public invoice pages.
 *
 * RULE 5: Tenant brand color is applied as CSS custom property (--tenant-brand),
 *         NOT as a Tailwind class. Never use bg-brand-* for tenant colors.
 * RULE 1: No useAuth() — this is a component for unauthenticated pages.
 */

import React from "react";
import Image from "next/image";
import type { PublicTenantBranding } from "./types";

interface TenantBrandedHeaderProps {
  tenantName: string;
  branding: PublicTenantBranding;
}

export function TenantBrandedHeader({
  tenantName,
  branding,
}: TenantBrandedHeaderProps) {
  // RULE 5: Tenant brand color applied as CSS custom property, NOT Tailwind class
  const brandStyle = {
    "--tenant-brand": branding.brandColorHex,
  } as React.CSSProperties;

  return (
    <header
      className="w-full"
      style={brandStyle}
      data-testid="tenant-branded-header"
    >
      {/* Tenant accent bar — uses CSS variable for tenant color */}
      <div
        className="h-1.5 w-full"
        style={{ backgroundColor: "var(--tenant-brand)" }}
        data-testid="tenant-accent-bar"
      />

      {/* Header content */}
      <div className="mx-auto max-w-2xl px-6 py-6 flex items-center gap-4">
        {branding.logoUrl ? (
          <Image
            src={branding.logoUrl}
            alt={`${tenantName} logo`}
            width={160}
            height={40}
            className="h-10 object-contain"
            data-testid="tenant-logo"
            unoptimized
          />
        ) : (
          <span
            className="text-xl font-bold text-neutral-800"
            data-testid="tenant-name-fallback"
          >
            {tenantName}
          </span>
        )}

        {/* "From [tenant name]" label when logo present */}
        {branding.logoUrl && (
          <span className="text-sm text-neutral-500">
            From <strong className="text-neutral-700">{tenantName}</strong>
          </span>
        )}
      </div>
    </header>
  );
}
