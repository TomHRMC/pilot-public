/**
 * QuoteExpiredPage — FE-B14
 *
 * Location: apps/web/src/features/public-quote/QuoteExpiredPage.tsx
 *
 * Renders when backend returns 410 GONE (expired, revoked, or not found).
 * Per design doc Section E: same treatment for expired/revoked/not-found —
 * indistinguishable to the customer by design.
 *
 * Token requirements:
 *  - bg-fault-50 background
 *  - text-fault-700 heading
 *  - border-fault-200 divider
 *
 * RULE 1: No useAuth().
 * RULE 4: No client-side token validation — backend returned 410.
 */

import React from "react";
import type { ExpiredLinkMeta } from "./types";
import { PoweredByPilotFooter } from "./PoweredByPilotFooter";

interface QuoteExpiredPageProps {
  meta?: ExpiredLinkMeta;
}

export function QuoteExpiredPage({ meta }: QuoteExpiredPageProps) {
  return (
    <div
      className="min-h-screen bg-fault-50 flex flex-col"
      data-testid="quote-expired-page"
    >
      <main className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">
          <div className="rounded-xl border border-fault-200 bg-white p-8 text-center shadow-sm">
            {/* Icon */}
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-fault-100">
              <svg
                className="h-6 w-6 text-fault-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>

            <h1
              className="text-xl font-semibold text-fault-700"
              data-testid="expired-heading"
            >
              This link has expired
            </h1>
            <p className="mt-2 text-sm text-neutral-600">
              This quote link is no longer active. It may have expired, been
              revoked, or already responded to.
            </p>

            {/* Tenant contact info (when available from error response) */}
            {meta &&
              (meta.tenantName || meta.tenantPhone || meta.tenantEmail) && (
                <>
                  <div className="my-6 border-t border-fault-200" />
                  <p className="text-sm text-neutral-600">
                    Please contact{" "}
                    <strong>{meta.tenantName ?? "the contractor"}</strong>{" "}
                    directly:
                  </p>
                  <div
                    className="mt-3 flex flex-col gap-2"
                    data-testid="tenant-contact-info"
                  >
                    {meta.tenantPhone && (
                      <a
                        href={`tel:${meta.tenantPhone}`}
                        className="text-sm font-medium text-neutral-700 hover:underline"
                        data-testid="tenant-phone"
                      >
                        {meta.tenantPhone}
                      </a>
                    )}
                    {meta.tenantEmail && (
                      <a
                        href={`mailto:${meta.tenantEmail}`}
                        className="text-sm font-medium text-neutral-700 hover:underline"
                        data-testid="tenant-email"
                      >
                        {meta.tenantEmail}
                      </a>
                    )}
                  </div>
                </>
              )}
          </div>
        </div>
      </main>
      <PoweredByPilotFooter />
    </div>
  );
}
