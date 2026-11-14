/**
 * Settings > Help & About page — FE-B16
 *
 * Location: apps/web/src/app/(authed)/settings/help-and-about/page.tsx
 *
 * Route: /settings/help-and-about
 * Auth: all authenticated users
 */

import type { Metadata } from "next";
import { HelpAboutPage } from "../../../../features/help/components/HelpAboutPage";

export const metadata: Metadata = {
  title: "Help & About — Pilot",
};

export default function HelpAndAboutPage() {
  return (
    <div className="px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-neutral-900">Help & About</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Get help, view your conversation history, and learn about Pilot.
        </p>
      </div>
      <HelpAboutPage />
    </div>
  );
}
