/**
 * WipReportPage — Top-level WIP report page component
 *
 * Location: apps/web/src/features/wip/components/WipReportPage.tsx
 *
 * Route: /reports/wip
 * Protected by RoleGate (owner | operator) — matches /reports ProfitabilityPage.
 * Owns: header band + "as of" caption + Refresh button + state switching
 * (isPending → WipSkeleton, isError → ErrorState, row_count===0 → EmptyState,
 * else → WipSummaryRow + WipJobsTable).
 *
 * Sort/order read from URL query params (?sort=&order=) and passed to useWipReport.
 * WIP is fetch-on-load only — no SSE, no polling (spec §9.4).
 *
 * Per batch-up-1-ui-design-spec.md §1, §2.1, §5 + batch-up-1-react-engr-prompt.md STEP 6.
 */

"use client";

import React from "react";
import { useSearchParams } from "next/navigation";
import { RoleGate } from "@pilot/ui/role-gate";
import { ErrorState, EmptyState } from "@pilot/ui/states";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { useWipReport, type WipSort } from "../hooks/useWipReport";
import { WipSummaryRow } from "./WipSummaryRow";
import { WipJobsTable } from "./WipJobsTable";
import { WipSkeleton } from "./WipSkeleton";
import { formatGeneratedAt } from "../lib/wip-format";

const VALID_SORTS: WipSort[] = [
  "deviation_pct",
  "projected_margin_pct",
  "actual_cost_cents",
  "scheduled_start_at",
];

function parseSortParam(value: string | null): WipSort {
  if (value && VALID_SORTS.includes(value as WipSort)) {
    return value as WipSort;
  }
  return "deviation_pct";
}

function parseOrderParam(value: string | null): "asc" | "desc" {
  return value === "asc" ? "asc" : "desc";
}

export function WipReportPage() {
  return (
    <RoleGate role={["owner", "accountant"]}>
      <WipReportPageInner />
    </RoleGate>
  );
}

function WipReportPageInner() {
  const searchParams = useSearchParams();
  const sort = parseSortParam(searchParams.get("sort"));
  const order = parseOrderParam(searchParams.get("order"));

  const query = useWipReport({ sort, order });
  const { data, isPending, isError, isFetching, refetch, error } = query;

  // Determine error type for ErrorState routing (spec §5.2)
  const errorStatus = getErrorStatus(error);
  const isPaywall = errorStatus === 402;

  return (
    <div className="flex flex-col min-h-screen bg-neutral-50">
      {/* Page header band (spec §2.1) */}
      <div className="bg-white border-b border-neutral-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-h1 font-medium text-neutral-900">
              Work-In-Progress
            </h1>
            {data?.generated_at && (
              <p className="text-caption text-neutral-500 mt-0.5">
                As of {formatGeneratedAt(data.generated_at)}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching && !isPending}
            className="inline-flex items-center gap-1.5 border border-neutral-300 text-neutral-700 bg-white rounded-md px-3 py-1.5 text-sm font-medium hover:bg-neutral-50 hover:text-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 active:bg-neutral-100 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="wip-refresh-btn"
          >
            <ArrowPathIcon
              className={`w-4 h-4 ${
                isFetching && !isPending
                  ? "animate-spin motion-reduce:animate-none"
                  : ""
              }`}
              aria-hidden="true"
            />
            Refresh
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 px-6 py-6 space-y-6 max-w-6xl mx-auto w-full">
        {isPending ? (
          <WipSkeleton />
        ) : isError ? (
          isPaywall ? (
            <ErrorState
              type="server"
              title="Billing required"
              description="WIP reports are available on an active billing plan."
            />
          ) : errorStatus === 401 ? (
            <ErrorState
              type="permission"
              title="Session expired"
              description="Your session has expired. Please sign in again."
            />
          ) : errorStatus === 422 ? (
            <ErrorState
              type="server"
              title="Invalid request"
              description="One of the filter values wasn't accepted."
              onRetry={() => refetch()}
            />
          ) : (
            <ErrorState
              type="server"
              title="Couldn't load WIP report"
              description="We couldn't reach the server. Try again."
              onRetry={() => refetch()}
            />
          )
        ) : !data || data.row_count === 0 ? (
          <EmptyState
            type="no-data"
            title="No active jobs right now"
            description="Jobs show up here once they're scheduled or in progress. The WIP report tracks every active job's projected cost against its quoted budget."
          />
        ) : (
          <>
            <WipSummaryRow summary={data.summary} />
            <WipJobsTable
              rows={data.rows}
              marginTargetPct={data.margin_target_pct}
              sort={sort}
              order={order}
            />
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Extracts HTTP status from an Axios error for ErrorState routing.
 */
function getErrorStatus(error: unknown): number | undefined {
  if (!error || typeof error !== "object") return undefined;
  // Axios error shape: error.response.status
  const response = (error as { response?: { status?: number } }).response;
  if (response?.status) return response.status;
  // RFC 7807 or other — check for status property
  const status = (error as { status?: number }).status;
  return status;
}
