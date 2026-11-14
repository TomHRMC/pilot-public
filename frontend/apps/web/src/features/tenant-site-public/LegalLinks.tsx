/**
 * LegalLinks — C-B16 public tenant-site legal nav
 *
 * Location: apps/web/src/features/tenant-site-public/LegalLinks.tsx
 *
 * Nav with Privacy Policy + Terms of Service links. Server component.
 * Links are relative to the tenant subdomain root (/privacy, /terms).
 *
 * mkt spec §5.4: brand-600 links, middle-dot separator.
 * WCAG 2.5.8: links use inline-block py-1 for ≥24px tap targets.
 */

import React from "react";
import Link from "next/link";

export function LegalLinks() {
  return (
    <nav
      aria-label="Legal documents"
      className="mt-8 border-t border-neutral-200 pt-6"
    >
      <ul className="flex items-center gap-2 text-body">
        <li>
          <Link
            href="/privacy"
            className="inline-block py-1 text-brand-600 underline hover:text-brand-800 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
          >
            Privacy Policy
          </Link>
        </li>
        <li aria-hidden="true" className="text-neutral-400">
          ·
        </li>
        <li>
          <Link
            href="/terms"
            className="inline-block py-1 text-brand-600 underline hover:text-brand-800 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
          >
            Terms of Service
          </Link>
        </li>
      </ul>
    </nav>
  );
}
