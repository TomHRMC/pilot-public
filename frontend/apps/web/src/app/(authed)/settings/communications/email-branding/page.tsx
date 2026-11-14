/**
 * Email Branding Settings Page — FE-B14
 *
 * Location: apps/web/src/app/(authed)/settings/communications/email-branding/page.tsx
 *
 * /settings/communications/email-branding
 * RoleGate: owner/office_staff (applied at communications/layout.tsx level).
 */

import React from "react";
import { EmailBrandingSettingsPanel } from "@/features/email-branding/EmailBrandingSettingsPanel";

export const metadata = {
  title: "Email Branding — Pilot",
  description: "Customize how your emails appear to customers.",
};

export default function EmailBrandingPage() {
  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-neutral-900">
          Email Branding
        </h1>
        <p className="text-sm text-neutral-500 mt-1">
          Customize your logo, brand color, and email content that customers
          see.
        </p>
      </div>
      <EmailBrandingSettingsPanel />
    </div>
  );
}
