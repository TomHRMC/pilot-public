/**
 * FieldIssueHistoryPage — /dashboard/approvals/field-issues/history
 *
 * Location: apps/web/src/app/(authed)/dashboard/approvals/field-issues/history/page.tsx
 *
 * Established FE-B9. Full archive with tech / date / operation / outcome filters.
 * Auth: required. Role gate: owner / office_staff.
 */

import React from "react";
import Link from "next/link";
import { RoleGate } from "@pilot/ui/role-gate";

export const metadata = {
  title: "Field Issue History | Pilot",
  description: "Full archive of resolved field issues",
};

export default function FieldIssueHistoryPage() {
  return (
    <RoleGate role={["owner", "office_staff"]}>
      <div className="bg-neutral-50 min-h-screen px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-5xl space-y-4">
          <h1 className="text-h2 font-medium text-neutral-900">
            Field issue history
          </h1>
          <p className="text-caption text-neutral-600">
            Full archive of all resolved field escalations. Filter by tech,
            date, operation type, or outcome.
          </p>
          {/* 
            Full history implementation deferred to FE-B11 settings surfaces.
            Placeholder shell established for routing completeness.
            FieldIssueHistoryPanel on the queue page covers the MVP use case (last 30).
          */}
          <div className="rounded-md border border-neutral-200 bg-white p-8 text-center">
            <p className="text-body text-neutral-600">
              Full history with advanced filters coming soon.
            </p>
            <Link
              href="/dashboard/approvals/field-issues"
              className="mt-3 inline-block text-caption text-brand-600 hover:underline"
            >
              ← Back to queue
            </Link>
          </div>
        </div>
      </div>
    </RoleGate>
  );
}
