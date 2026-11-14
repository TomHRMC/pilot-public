/**
 * ContactLine — C-B16 public tenant-site contact line
 *
 * Location: apps/web/src/features/tenant-site-public/ContactLine.tsx
 *
 * Renders phone/email/city-state/address with Heroicons. Conditional
 * rendering based on available fields. Server component (no "use client").
 *
 * mkt spec §5.2: icons are decorative (aria-hidden), text labels convey meaning.
 * WCAG 2.5.8: links use inline-block py-1 for ≥24px tap targets.
 */

import React from "react";
import {
  PhoneIcon,
  EnvelopeIcon,
  MapPinIcon,
} from "@heroicons/react/24/outline";

interface ContactLineProps {
  publicPhone?: string | null;
  publicEmail?: string | null;
  publicCity?: string | null;
  publicState?: string | null;
  publicAddressLine1?: string | null;
  publicPostalCode?: string | null;
  showFullAddress?: boolean;
  /** Compact mode for legal page headers — omits email */
  compact?: boolean;
}

export function ContactLine({
  publicPhone,
  publicEmail,
  publicCity,
  publicState,
  publicAddressLine1,
  publicPostalCode,
  showFullAddress = false,
  compact = false,
}: ContactLineProps) {
  const hasPhone = Boolean(publicPhone);
  const hasEmail = !compact && Boolean(publicEmail);
  const cityState = [publicCity, publicState].filter(Boolean).join(", ");
  const hasCityState = Boolean(cityState);
  const hasAddress = showFullAddress && Boolean(publicAddressLine1);

  if (!hasPhone && !hasEmail && !hasCityState && !hasAddress) {
    return null;
  }

  return (
    <ul className="mt-4 flex flex-col gap-1 text-body text-neutral-700 sm:flex-row sm:gap-6">
      {hasPhone && (
        <li className="flex items-center gap-2">
          <PhoneIcon className="h-4 w-4 text-neutral-400" aria-hidden="true" />
          <a
            href={`tel:${publicPhone}`}
            className="inline-block py-1 text-neutral-700 hover:text-neutral-900 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
          >
            {publicPhone}
          </a>
        </li>
      )}
      {hasEmail && (
        <li className="flex items-center gap-2">
          <EnvelopeIcon
            className="h-4 w-4 text-neutral-400"
            aria-hidden="true"
          />
          <a
            href={`mailto:${publicEmail}`}
            className="inline-block py-1 text-neutral-700 hover:text-neutral-900 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
          >
            {publicEmail}
          </a>
        </li>
      )}
      {hasCityState && (
        <li className="flex items-center gap-2">
          <MapPinIcon className="h-4 w-4 text-neutral-400" aria-hidden="true" />
          <span className="py-1 text-neutral-600">{cityState}</span>
        </li>
      )}
      {hasAddress && (
        <li className="flex items-center gap-2">
          <MapPinIcon className="h-4 w-4 text-neutral-400" aria-hidden="true" />
          <span className="py-1 text-neutral-600">
            {publicAddressLine1}
            {publicPostalCode ? `, ${publicPostalCode}` : ""}
          </span>
        </li>
      )}
    </ul>
  );
}
