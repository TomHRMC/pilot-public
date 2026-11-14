/**
 * RecurringJobsPage — /jobs/recurring list of recurrence rules
 *
 * Location: apps/web/src/features/jobs/components/RecurringJobsPage.tsx
 *
 * FE-B31: Shows all recurrence rules with pause/resume controls.
 * Only owner/office_staff/operator can see this (jobs.view permission).
 */

"use client";

import React from "react";
import { LoadingState, ErrorState, EmptyState, RoleGate } from "@pilot/ui";
import { useListRecurrenceRules } from "../hooks/useListRecurrenceRules";
import { useUpdateRecurrenceRule } from "../hooks/useUpdateRecurrenceRule";
import type { RecurrenceRuleListItem } from "../hooks/useListRecurrenceRules";

function RecurringRuleCard({ rule }: { rule: RecurrenceRuleListItem }) {
  const update = useUpdateRecurrenceRule(rule.id);

  const patternLabel: Record<string, string> = {
    daily: `Every ${rule.interval_count} day(s)`,
    weekly: `Every ${rule.interval_count} week(s)`,
    monthly: `Every ${rule.interval_count} month(s)`,
    annually: `Every ${rule.interval_count} year(s)`,
  };

  return (
    <div
      className="border border-neutral-200 rounded-lg p-4 flex items-center justify-between bg-white"
      data-testid="recurring-rule-card"
    >
      <div>
        <div className="flex items-center gap-2">
          <span className="text-blue-600 font-medium" aria-hidden="true">
            ↻
          </span>
          <span className="font-medium text-neutral-900">
            {rule.customer_name ?? "—"}
          </span>
          <span className="text-neutral-500 text-sm">
            {rule.site_address ?? "—"}
          </span>
        </div>
        <div className="text-sm text-neutral-600 mt-1">
          {patternLabel[rule.pattern] ?? rule.pattern}
          {rule.next_job_at &&
            ` · Next: ${new Date(rule.next_job_at).toLocaleDateString()}`}
          {rule.default_tech_display_name &&
            ` · ${rule.default_tech_display_name}`}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span
          className={`text-xs px-2 py-1 rounded-full font-medium ${
            rule.is_active
              ? "bg-green-100 text-green-700"
              : "bg-neutral-100 text-neutral-500"
          }`}
        >
          {rule.is_active ? "Active" : "Paused"}
        </span>
        <RoleGate permission="jobs.edit">
          <button
            type="button"
            onClick={() => update.mutate({ is_active: !rule.is_active })}
            disabled={update.isPending}
            data-testid={rule.is_active ? "pause-rule-btn" : "resume-rule-btn"}
            className="text-sm text-brand-600 hover:underline disabled:opacity-50"
          >
            {rule.is_active ? "Pause" : "Resume"}
          </button>
        </RoleGate>
      </div>
    </div>
  );
}

export function RecurringJobsPage() {
  const { data, isLoading, isError } = useListRecurrenceRules();

  if (isLoading) {
    return (
      <div className="p-6">
        <LoadingState type="full-page" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6">
        <ErrorState type="server" description="Could not load recurring jobs" />
      </div>
    );
  }

  if (!data?.items.length) {
    return (
      <div className="p-6">
        <EmptyState
          type="no-data"
          title="No recurring jobs"
          description="Create a recurring job from any job form to schedule automatic repeats."
        />
      </div>
    );
  }

  return (
    <RoleGate permission="jobs.view">
      <div className="p-6 max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-neutral-900">
            Recurring Jobs
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Manage repeating job schedules. Pausing a rule stops future job
            creation.
          </p>
        </div>
        <div className="space-y-3" data-testid="recurring-jobs-list">
          {data.items.map((rule) => (
            <RecurringRuleCard key={rule.id} rule={rule} />
          ))}
        </div>
      </div>
    </RoleGate>
  );
}
