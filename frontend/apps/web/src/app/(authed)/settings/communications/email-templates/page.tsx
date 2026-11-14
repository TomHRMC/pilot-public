/**
 * Email Templates Preview Page — FE-B14
 *
 * Location: apps/web/src/app/(authed)/settings/communications/email-templates/page.tsx
 *
 * /settings/communications/email-templates
 * Owner-only: restricts to `owner` role via RoleGate.
 * RULE 8: Templates rendered server-side by BE-B15/A82 — UI does visual review only.
 */

import React from "react";
import { RoleGate } from "@pilot/ui";
import { EmailTemplatePreviewSurface } from "@/features/email-branding/EmailTemplatePreviewSurface";

export const metadata = {
  title: "Email Templates — Pilot",
  description: "Preview all 17 email templates with your branding.",
};

export default function EmailTemplatesPage() {
  return (
    <RoleGate role="owner">
      <div className="p-6 max-w-6xl">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-neutral-900">
            Email Templates
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Preview all email templates with your current branding applied.
            Customer-facing templates use your logo and brand color.
          </p>
        </div>
        <EmailTemplatePreviewSurface />
      </div>
    </RoleGate>
  );
}
