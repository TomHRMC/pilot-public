/**
 * FieldIssueDetailPage — /dashboard/approvals/field-issues/[id]
 *
 * Location: apps/web/src/app/(authed)/dashboard/approvals/field-issues/[id]/page.tsx
 *
 * Established FE-B9. Bookmarkable URL; modal-feeling but URL-routed.
 * Auth: required. Role gate: owner / office_staff.
 * 404 if escalation not found (handled by FieldIssueDetail error state).
 */

import React from "react";
import { FieldIssueDetail } from "@/features/field-issues/components/FieldIssueDetail";

interface FieldIssueDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function FieldIssueDetailPage({
  params,
}: FieldIssueDetailPageProps) {
  const { id } = await params;

  // Role check (owner / office_staff) enforced inside FieldIssueDetail (client component)
  return <FieldIssueDetail issueId={id} testID="field-issue-detail-page" />;
}
