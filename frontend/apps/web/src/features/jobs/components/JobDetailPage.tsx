/**
 * JobDetailPage — Job detail with profitability widget + 5 tabs
 *
 * Location: apps/web/src/features/jobs/components/JobDetailPage.tsx
 *
 * Layout:
 *   1. <JobDetailHeader />  — breadcrumb, status, dates, title
 *   2. Priority + job_type read-only chips (JOB-UI-B1)
 *   3. Job actions bar — Edit Job routes to /jobs/{id}/edit (JOB-UI-B1)
 *   4. <JobProfitabilityWidget />  — persistent above tabs
 *   5. Tab bar: [Profitability | Time Entries | Expenses | Change Orders | Notes]
 *   6. Active tab content
 *   7. "Convert to Invoice" — shown for terminal job statuses only (gated to invoices.create)
 *
 * JOB-UI-B1: Edit Job button now routes to /jobs/{id}/edit (full-page edit).
 * JobEditModal stays on the dispatch board as the schedule-only quick edit.
 */

"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { RoleGate } from "@pilot/ui";
import { JobDetailHeader } from "./JobDetailHeader";
import { JobProfitabilityWidget } from "./JobProfitabilityWidget";
import { TechAssignmentSection } from "./TechAssignmentSection";
import { JobTimeEntriesTab } from "./JobTimeEntriesTab";
import { JobExpensesTab } from "./JobExpensesTab";
import { JobChangeOrdersTab } from "./JobChangeOrdersTab";
import { JobNotesTab } from "./JobNotesTab";
import { useJob } from "../hooks/useJob";

interface JobDetailPageProps {
  jobId: string;
}

type TabId =
  | "profitability"
  | "time-entries"
  | "expenses"
  | "change-orders"
  | "notes";

const TABS: { id: TabId; label: string }[] = [
  { id: "profitability", label: "Profitability" },
  { id: "time-entries", label: "Time Entries" },
  { id: "expenses", label: "Expenses" },
  { id: "change-orders", label: "Change Orders" },
  { id: "notes", label: "Notes" },
];

/** Statuses where "Create Invoice" button should appear */
const TERMINAL_STATUSES = new Set(["completed", "invoice_pending"]);

// ── JOB-UI-B1: Priority chip ──────────────────────────────────────────────────

function PriorityChip({ priority }: { priority: string }) {
  // emergency=fault, urgent=warn, standard=neutral (per DISPATCH-B3 convention)
  const colorMap: Record<string, string> = {
    emergency: "bg-fault-100 text-fault-700",
    urgent: "bg-warn-100 text-warn-700",
    standard: "bg-neutral-100 text-neutral-600",
  };
  const labelMap: Record<string, string> = {
    emergency: "Emergency",
    urgent: "Urgent",
    standard: "Standard",
  };
  const colorClass = colorMap[priority] ?? colorMap.standard;
  const label = labelMap[priority] ?? priority;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}
      data-testid="job-priority-chip"
    >
      {label}
    </span>
  );
}

// ── JOB-UI-B1: Job type chip ──────────────────────────────────────────────────

function JobTypeChip({ label }: { label: string }) {
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600"
      data-testid="job-type-chip"
    >
      {label}
    </span>
  );
}

function isTerminalStatus(statusId: string): boolean {
  return TERMINAL_STATUSES.has(statusId);
}
function ProfitabilitySummaryTab() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-neutral-500">
        The profitability summary above shows real-time labor and material
        actuals versus estimates, plus projected final margin.
      </p>
      <p className="text-sm text-neutral-500">
        Use the Time Entries and Expenses tabs to view detailed cost breakdowns.
      </p>
    </div>
  );
}

export function JobDetailPage({ jobId }: JobDetailPageProps) {
  const [activeTab, setActiveTab] = useState<TabId>("profitability");
  const router = useRouter();
  const { data: job } = useJob(jobId);

  const showConvertButton = job
    ? isTerminalStatus(job.status_code ?? "")
    : false;

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header — breadcrumb + status + dates + title (JOB-UI-B1) */}
      <JobDetailHeader jobId={jobId} />

      {/* JOB-UI-B1: Priority + job_type read-only chips + Edit Job → full page */}
      {job && (
        <div className="px-6 py-2 bg-white border-b border-neutral-100 flex items-center gap-3 justify-between">
          {/* Left: priority + job_type chips */}
          <div className="flex items-center gap-2">
            {job.priority && <PriorityChip priority={job.priority} />}
            {job.job_type_label && <JobTypeChip label={job.job_type_label} />}
          </div>
          {/* Right: Edit Job button — routes to full-page edit */}
          <RoleGate permission="jobs.edit">
            <button
              onClick={() => router.push(`/jobs/${jobId}/edit`)}
              data-testid="edit-job-btn"
              className="px-4 py-1.5 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
            >
              Edit Job
            </button>
          </RoleGate>
        </div>
      )}

      {/* Tech assignment — always visible, not in a tab */}
      {/* PLP-FIX-11 (INV-BUG-18): wrap the entire Technicians wrapper (header +
          section) in RoleGate permission="schedule.view_all" so a role lacking
          the grant sees neither the bare <h4> nor the section. Pre-FIX-11 the
          header rendered outside the child's gate → bare "Technicians" label
          for accountant. RoleGate is already imported (line 23). */}
      <RoleGate permission="schedule.view_all">
        <div className="px-6 py-3 border-b border-neutral-100 bg-white">
          <h4 className="text-sm font-semibold text-neutral-700 mb-2">
            Technicians
          </h4>
          <TechAssignmentSection jobId={jobId} />
        </div>
      </RoleGate>

      {/* Profitability widget — always visible */}
      <JobProfitabilityWidget jobId={jobId} />

      {/* Tab bar */}
      <div className="bg-white border-b border-neutral-200 px-6">
        <nav className="flex gap-0" aria-label="Job sections">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-brand-600 text-brand-700"
                  : "border-transparent text-neutral-600 hover:text-neutral-900 hover:border-neutral-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="px-6 py-5 max-w-5xl">
        {activeTab === "profitability" && <ProfitabilitySummaryTab />}
        {activeTab === "time-entries" && <JobTimeEntriesTab jobId={jobId} />}
        {activeTab === "expenses" && <JobExpensesTab jobId={jobId} />}
        {activeTab === "change-orders" && <JobChangeOrdersTab jobId={jobId} />}
        {activeTab === "notes" && <JobNotesTab jobId={jobId} />}
      </div>

      {/* Create Invoice — bottom of page, terminal status only */}
      {showConvertButton && (
        <div
          className="fixed bottom-0 right-0 p-4 bg-white border-t border-neutral-200 shadow-lg"
          style={{ width: "calc(100% - 14rem)" }}
        >
          <div className="flex justify-end max-w-5xl mx-auto">
            <RoleGate permission="invoices.create">
              <button
                onClick={() => router.push(`/invoices/new?job_id=${jobId}`)}
                data-testid="convert-to-invoice-btn"
                className="px-5 py-2.5 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors"
              >
                Create Invoice
              </button>
            </RoleGate>
          </div>
        </div>
      )}
    </div>
  );
}
