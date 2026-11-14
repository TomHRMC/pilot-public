/**
 * Tenant-site layout — C-B16 shared layout for public SSR pages
 *
 * Location: apps/web/src/app/(tenant-site)/sites/[slug]/layout.tsx
 *
 * Server component. Fetches the published snapshot once (Next.js deduplicates
 * fetches within a request) and renders the shared header + footer. The
 * landing page renders its own header (H1 variant); legal pages render the
 * header in "legal" variant (business name as link).
 *
 * mkt spec §6.1: shared header + footer via layout.
 * Design Decision #2: body_paragraphs are pre-escaped plain text.
 */

import React from "react";
import { HostedByPilotFooter } from "@/features/tenant-site-public/HostedByPilotFooter";

export default async function TenantSiteLayout({
  children,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  return (
    <div className="min-h-screen bg-white">
      {/* Skip link — WCAG 2.4.1 */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-4 focus:py-2 focus:text-brand-600 focus:shadow"
      >
        Skip to main content
      </a>
      {children}
      <HostedByPilotFooter />
    </div>
  );
}
