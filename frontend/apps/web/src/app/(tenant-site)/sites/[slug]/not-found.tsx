/**
 * Tenant-site not-found — C-B16 neutral 404 state
 *
 * Location: apps/web/src/app/(tenant-site)/sites/[slug]/not-found.tsx
 *
 * Server component. Triggered when the public API returns 404
 * `site_not_found` (unknown slug AND non-published — no existence leak).
 *
 * Design Decision #5: neutral, Pilot-branded only — NO "Hosted by" footer
 * (footer would leak that a site could exist at the slug).
 * mkt spec §7: noindex, no accent bar, no header.
 */

import React from "react";
import type { Metadata } from "next";
import { NotFoundState } from "@/features/tenant-site-public/NotFoundState";

export const metadata: Metadata = {
  title: "Page not found",
  robots: { index: false, follow: true },
};

export default function NotFound() {
  return <NotFoundState />;
}
