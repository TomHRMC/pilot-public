/**
 * SMS Compliance Settings Page — DLC-1
 *
 * Location: apps/web/src/app/(authed)/settings/communications/sms-compliance/page.tsx
 *
 * /settings/communications/sms-compliance
 * RoleGate: owner/office_staff (applied at communications/layout.tsx level).
 *
 * RULE 9: Thin server component — no "use client", no data fetching.
 */

import React from "react";
import { TenantDlcProfileForm } from "@/features/sms-compliance/components/TenantDlcProfileForm";

export const metadata = {
  title: "SMS & 10DLC — Pilot",
  description:
    "Configure your business profile for SMS carrier compliance (10DLC/TCR).",
};

export default function SmsDlcCompliancePage() {
  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-neutral-900">
          SMS &amp; 10DLC Compliance
        </h1>
        <p className="text-sm text-neutral-500 mt-1">
          Register your business profile with the carrier network (TCR) to send
          compliant SMS messages to customers.
        </p>
      </div>
      <TenantDlcProfileForm />
    </div>
  );
}
