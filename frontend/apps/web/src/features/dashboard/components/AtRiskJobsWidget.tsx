"use client";

/**
 * AtRiskJobsWidget — Dashboard BI widget
 *
 * Location: apps/web/src/features/dashboard/components/AtRiskJobsWidget.tsx
 *
 * Shows top jobs where projected margin is below the tenant's margin target.
 * RoleGated: reports.view (owner + accountant only).
 */

import { RoleGate } from "@pilot/ui/role-gate";
import { LoadingState, EmptyState, ErrorState } from "@pilot/ui/states";
import Link from "next/link";
import { ArrowRightIcon } from "@heroicons/react/24/outline";
import { useAtRiskJobs } from "../hooks/useAtRiskJobs";

interface Props {
  className?: string;
}

function formatCents(cents: number): string {
  return `$${(cents / 100).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export function AtRiskJobsWidget({ className }: Props) {
  return (
    <RoleGate role={["owner", "office_staff"]}>
      <AtRiskJobsWidgetInner className={className} />
    </RoleGate>
  );
}

function AtRiskJobsWidgetInner({ className }: Props) {
  const { data, isLoading, isError } = useAtRiskJobs(5);

  return (
    <div
      className={`rounded-lg border border-neutral-200 bg-white p-4 ${className ?? ""}`}
      data-testid="at-risk-jobs-widget"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-h3 text-neutral-900">At-Risk Jobs</h2>
        <Link
          href="/jobs"
          className="text-caption text-brand-600 hover:underline"
          data-testid="view-jobs-link"
        >
          View Jobs →
        </Link>
      </div>

      {isLoading && (
        <LoadingState type="inline" label="Loading at-risk jobs…" />
      )}
      {isError && (
        <ErrorState
          type="server"
          title="Failed to load"
          description="Unable to fetch at-risk jobs."
        />
      )}
      {!isLoading && !isError && data?.jobs.length === 0 && (
        <EmptyState
          type="no-data"
          title="All jobs are on track"
          description="No jobs are currently below the margin target."
        />
      )}
      {!isLoading && !isError && data && data.jobs.length > 0 && (
        <ul className="space-y-2">
          {data.jobs.map((job) => (
            <li
              key={job.job_id}
              className="flex items-center justify-between rounded-md border border-neutral-100 px-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-body-sm font-medium text-neutral-900">
                  {job.customer_name}
                  {job.site_name ? ` — ${job.site_name}` : ""}
                </p>
                <p className="text-caption text-neutral-500">
                  {job.status_code ?? "unknown"} ·{" "}
                  <span className="font-medium">
                    {formatCents(job.actual_cost_cents)} spent
                  </span>
                  {job.quoted_budget_cents != null
                    ? ` of ${formatCents(job.quoted_budget_cents)} quoted`
                    : ""}
                </p>
              </div>
              {job.projected_margin_pct != null && (
                <span className="ml-3 shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-caption font-semibold text-red-700">
                  {job.projected_margin_pct.toFixed(1)}%
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {data && data.total > 0 && (
        <p className="mt-2 text-caption text-neutral-400">
          {data.total} job{data.total !== 1 ? "s" : ""} below margin target
        </p>
      )}

      {/* UP-1: WIP report entry-point CTA (spec §2.7) */}
      <div className="border-t border-neutral-100 mt-3 pt-3">
        <Link
          href="/reports/wip"
          className="group flex items-center justify-between w-full rounded-md px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 active:bg-brand-100"
          data-testid="wip-report-cta"
        >
          <span>View full WIP report</span>
          <ArrowRightIcon
            className="w-4 h-4 group-hover:translate-x-0.5 transition-transform motion-reduce:transition-none"
            aria-hidden="true"
          />
        </Link>
        <p className="text-caption text-neutral-400 mt-0.5 px-3">
          (with ETC projections)
        </p>
      </div>
    </div>
  );
}
