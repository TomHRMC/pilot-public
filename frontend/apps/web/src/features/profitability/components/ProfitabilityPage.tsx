/**
 * ProfitabilityPage — Top-level profitability reports surface
 *
 * Location: apps/web/src/features/profitability/components/ProfitabilityPage.tsx
 *
 * Route: /reports
 * Protected by RoleGate (owner | operator).
 * Composes: PeriodSelector + MetricsCardRow + LiveJobsSection + ClosedJobsSection.
 *
 * Per batch-fe-b4-design.md §A.2.6
 *
 * BETA-B6: Added custom date range state. When period === 'custom', the
 * custom dates are passed to useProfitability instead of a period shorthand.
 * The API is NOT fired until both customDateFrom and customDateTo are set.
 */

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { RoleGate } from "@pilot/ui/role-gate";
import {
  useProfitability,
  type ProfitabilityPeriod,
} from "../hooks/useProfitability";
import { PeriodSelector } from "./PeriodSelector";
import { MetricsCardRow } from "./MetricsCardRow";
import { ClosedJobsSection } from "./ClosedJobsSection";
import { BriefcaseIcon, ArrowRightIcon } from "@heroicons/react/24/outline";

/**
 * ProfitabilityPage
 *
 * Renders the /reports route content.
 * Composes the canonical period selector + metric cards + live + closed sections.
 */
export function ProfitabilityPage() {
  const [period, setPeriod] = useState<ProfitabilityPeriod>("30d");
  // BETA-B6: custom date range state — only used when period === 'custom'
  const [customDateFrom, setCustomDateFrom] = useState("");
  const [customDateTo, setCustomDateTo] = useState("");

  const { data, isLoading, isError } = useProfitability({
    period,
    customDateFrom: period === "custom" ? customDateFrom : undefined,
    customDateTo: period === "custom" ? customDateTo : undefined,
  });

  function handleCustomDatesChange(from: string, to: string) {
    setCustomDateFrom(from);
    setCustomDateTo(to);
  }

  // When switching away from custom, reset the stored dates so they don't
  // leak into a future custom selection if the user picks new dates.
  function handlePeriodChange(next: ProfitabilityPeriod) {
    if (next !== "custom") {
      setCustomDateFrom("");
      setCustomDateTo("");
    }
    setPeriod(next);
  }

  // When period is custom and dates are incomplete, show a prompt rather
  // than loading/error states (the API is disabled by useProfitability).
  const awaitingCustomDates =
    period === "custom" && (!customDateFrom || !customDateTo);

  return (
    // PLP-FIX-7: Gate on reports.view (server-authoritative) instead of
    // role={["owner", "accountant"]}. office_staff holds reports.view in prod
    // but was excluded by the role-based gate → blank page (INV-BUG root cause).
    <RoleGate permission="reports.view">
      <div className="flex flex-col min-h-screen bg-neutral-50">
        {/* Page header */}
        <div className="bg-white border-b border-neutral-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-h1 font-medium text-neutral-900">
                Profitability
              </h1>
              <p className="text-body text-neutral-600 mt-0.5">
                Track margins, hours, and revenue across your jobs.
              </p>
            </div>
            <PeriodSelector
              value={period}
              onChange={handlePeriodChange}
              customDateFrom={customDateFrom}
              customDateTo={customDateTo}
              onCustomDatesChange={handleCustomDatesChange}
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 px-6 py-6 space-y-6 max-w-6xl mx-auto w-full">
          {awaitingCustomDates ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-body text-neutral-500">
                Select a start and end date to load your custom report.
              </p>
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="text-body text-neutral-400">
                Loading profitability data…
              </div>
            </div>
          ) : isError || !data || !data.summary ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-body text-neutral-500">
                No profitability data available.
              </p>
            </div>
          ) : (
            <>
              {/* Summary metrics */}
              <MetricsCardRow summary={data.summary} />

              {/* UP-1: WIP pointer card (replaces dead LiveJobsSection — spec §5.7) */}
              <div className="rounded-lg border border-neutral-200 bg-white p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <BriefcaseIcon
                    className="w-5 h-5 text-neutral-500"
                    aria-hidden="true"
                  />
                  <div>
                    <h3 className="text-h3 font-medium text-neutral-900">
                      Active jobs & WIP
                    </h3>
                    <p className="text-caption text-neutral-500">
                      Track projected cost vs quoted budget for every active job
                      — with ETC.
                    </p>
                  </div>
                </div>
                <Link
                  href="/reports/wip"
                  className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded"
                  data-testid="reports-wip-pointer"
                >
                  View WIP report
                  <ArrowRightIcon className="w-4 h-4" aria-hidden="true" />
                </Link>
              </div>

              {/* Closed jobs + charts */}
              <ClosedJobsSection
                jobs={data.closed_jobs}
                distribution={data.margin_distribution}
              />
            </>
          )}
        </div>
      </div>
    </RoleGate>
  );
}
