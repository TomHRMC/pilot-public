/**
 * NotFoundState — C-B16 public tenant-site 404 neutral state
 *
 * Location: apps/web/src/features/tenant-site-public/NotFoundState.tsx
 *
 * Neutral, Pilot-branded 404 page. NO tenant branding, NO "Hosted by" footer
 * (Design Decision #5 — footer would leak that a site could exist at the slug).
 * Server component.
 *
 * mkt spec §7: bg-neutral-50, centered, "Page not found" H1, link to
 * pilotfortrades.com. noindex via not-found.tsx metadata.
 */

import React from "react";

export function NotFoundState() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-neutral-50 px-6">
      <div className="max-w-md text-center">
        <h1 className="mb-4 text-2xl font-bold text-neutral-800">
          Page not found
        </h1>
        <p className="mb-6 text-body-lg text-neutral-600">
          The page you are looking for does not exist or is no longer available.
        </p>
        <a
          href="https://pilotfortrades.com"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block py-1 text-body-lg font-medium text-brand-600 underline hover:text-brand-800 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
        >
          Visit Pilot for Trades →
        </a>
      </div>
    </main>
  );
}
