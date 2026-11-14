/**
 * HostedByPilotFooter — C-B16 public tenant-site footer
 *
 * Location: apps/web/src/features/tenant-site-public/HostedByPilotFooter.tsx
 *
 * "Hosted by Pilot for Trades" footer. Distinct from PoweredByPilotFooter
 * (different wording: "Hosted by" vs "Powered by"). Server component.
 *
 * mkt spec §5.5: text-neutral-400 label + text-neutral-500 link.
 * WCAG 2.5.8: link uses inline-block py-1 for ≥24px tap target.
 */

import React from "react";

export function HostedByPilotFooter() {
  return (
    <footer
      className="border-t border-neutral-200 py-6"
      aria-label="Hosting provider"
    >
      <p className="text-center text-caption text-neutral-400">
        Hosted by{" "}
        <a
          href="https://pilotfortrades.com"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block py-1 text-neutral-500 underline hover:text-neutral-700 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
        >
          Pilot for Trades
        </a>
      </p>
    </footer>
  );
}
