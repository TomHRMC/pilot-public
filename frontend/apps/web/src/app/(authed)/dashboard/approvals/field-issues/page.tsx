/**
 * FieldIssuesQueuePage — /dashboard/approvals/field-issues
 *
 * Location: apps/web/src/app/(authed)/dashboard/approvals/field-issues/page.tsx
 *
 * Established FE-B9. Tab 2 on Approvals shell (alongside Quotes tab).
 * Auth: required (handled by (authed) layout).
 * Role gate: owner / office_staff (accountant maps to office_staff in PilotRole).
 */

import React from "react";
import { FieldIssuesQueue } from "@/features/field-issues/components/FieldIssuesQueue";

export const metadata = {
  title: "Field Issues | Pilot",
  description:
    "Review and resolve mobile capture conflicts from your field techs",
};

export default function FieldIssuesQueuePage() {
  return (
    <div className="bg-neutral-50 min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      {/* Role check (owner / office_staff) is enforced inside FieldIssuesQueue */}
      <FieldIssuesQueue testID="field-issues-queue-page" />
    </div>
  );
}
