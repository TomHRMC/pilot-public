"use client";

/**
 * PendingApprovalsWidget — Dashboard BI widget
 *
 * Location: apps/web/src/features/dashboard/components/PendingApprovalsWidget.tsx
 *
 * Shows counts of pending quote approvals + field issues.
 * RoleGated: quotes.view (owner + office_staff).
 */

import { RoleGate } from "@pilot/ui/role-gate";
import { LoadingState, EmptyState, ErrorState } from "@pilot/ui/states";
import Link from "next/link";
import { usePendingApprovals } from "../hooks/usePendingApprovals";

interface Props {
  className?: string;
}

export function PendingApprovalsWidget({ className }: Props) {
  return (
    <RoleGate role={["owner", "office_staff"]}>
      <PendingApprovalsWidgetInner className={className} />
    </RoleGate>
  );
}

function PendingApprovalsWidgetInner({ className }: Props) {
  const { data, isLoading, isError } = usePendingApprovals();

  const hasItems = data
    ? data.pending_quotes > 0 || data.pending_field_issues > 0
    : false;

  return (
    <div
      className={`rounded-lg border border-neutral-200 bg-white p-4 ${className ?? ""}`}
      data-testid="pending-approvals-widget"
    >
      <h2 className="mb-3 text-h3 text-neutral-900">Pending Approvals</h2>

      {isLoading && (
        <LoadingState type="inline" label="Loading pending approvals…" />
      )}
      {isError && (
        <ErrorState
          type="server"
          title="Failed to load"
          description="Unable to fetch pending approvals."
        />
      )}
      {!isLoading && !isError && !hasItems && (
        <EmptyState
          type="no-data"
          title="No pending approvals"
          description="All quotes and field issues have been reviewed."
        />
      )}
      {!isLoading && !isError && data && hasItems && (
        <div className="space-y-3">
          {data.pending_quotes > 0 && (
            <Link
              href="/quotes/pending"
              className="flex items-center justify-between rounded-md border border-amber-100 bg-amber-50 px-3 py-2 hover:bg-amber-100"
              data-testid="review-quotes-link"
            >
              <div>
                <p className="text-body-sm font-medium text-neutral-900">
                  Quotes pending review
                </p>
                <p className="text-caption text-neutral-500">
                  Waiting for your approval
                </p>
              </div>
              <span className="rounded-full bg-amber-500 px-2 py-0.5 text-caption font-semibold text-white">
                {data.pending_quotes}
              </span>
            </Link>
          )}
          {data.pending_field_issues > 0 && (
            <Link
              href="/dashboard/approvals/field-issues"
              className="flex items-center justify-between rounded-md border border-red-100 bg-red-50 px-3 py-2 hover:bg-red-100"
              data-testid="field-issues-link"
            >
              <div>
                <p className="text-body-sm font-medium text-neutral-900">
                  Field sync issues
                </p>
                <p className="text-caption text-neutral-500">
                  Require owner resolution
                </p>
              </div>
              <span className="rounded-full bg-red-500 px-2 py-0.5 text-caption font-semibold text-white">
                {data.pending_field_issues}
              </span>
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
