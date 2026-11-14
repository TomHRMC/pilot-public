/**
 * PoweredByPilotFooter — FE-B14
 *
 * Location: apps/web/src/features/public-quote/PoweredByPilotFooter.tsx
 *
 * Shared by both public quote and public invoice pages.
 * Renders at the bottom of every public page regardless of tenant branding.
 *
 * Token requirements (Section H.3):
 *  - text-neutral-400 for footer text
 *  - text-neutral-500 hover:text-neutral-700 for the link
 *
 * RULE 1: No useAuth() — unauthenticated surface.
 */

import React from "react";

export function PoweredByPilotFooter() {
  return (
    <footer className="w-full py-6" data-testid="powered-by-pilot-footer">
      <p className="text-center text-xs text-neutral-400">
        Powered by{" "}
        <a
          href="https://pilotfortrades.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-neutral-500 hover:text-neutral-700 underline"
        >
          Pilot for Trades
        </a>
      </p>
    </footer>
  );
}
