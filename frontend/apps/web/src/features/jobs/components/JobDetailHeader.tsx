/**
 * JobDetailHeader — job breadcrumb, status badge, customer, site, dates
 *
 * Location: apps/web/src/features/jobs/components/JobDetailHeader.tsx
 *
 * FE-B26: Fixed 3 UUID display bugs:
 *   1. Breadcrumb now shows job_number (not raw UUID)
 *   2. StatusBadge now accepts statusCode (not statusId UUID)
 *   3. Site display now shows site_name (not site_id UUID)
 *   Added: customer_name display + quote link
 * JOB-UI-B1: Breadcrumb + page heading shows title (fallback to job_number).
 */

"use client";

import React from "react";
import Link from "next/link";
import { LoadingState } from "@pilot/ui";
import { useJob } from "../hooks/useJob";

interface JobDetailHeaderProps {
  jobId: string;
}

function StatusBadge({ statusCode }: { statusCode: string }) {
  const colorMap: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-700",
    scheduled: "bg-blue-100 text-blue-700",
    in_progress: "bg-yellow-100 text-yellow-800",
    completed: "bg-green-100 text-green-700",
    invoice_pending: "bg-purple-100 text-purple-700",
    cancelled: "bg-red-100 text-red-700",
  };

  const labelMap: Record<string, string> = {
    draft: "Draft",
    scheduled: "Scheduled",
    in_progress: "In Progress",
    completed: "Completed",
    invoice_pending: "Invoice Pending",
    cancelled: "Cancelled",
  };

  const colorClass = colorMap[statusCode] ?? "bg-neutral-100 text-neutral-700";
  const label =
    labelMap[statusCode] ??
    statusCode.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}

export function JobDetailHeader({ jobId }: JobDetailHeaderProps) {
  const { data: job, isLoading } = useJob(jobId);

  if (isLoading) {
    return (
      <div className="px-6 pt-6 pb-4 border-b border-neutral-200">
        <LoadingState type="inline" label="Loading job details…" />
      </div>
    );
  }

  if (!job) return null;

  const scheduledDate = job.scheduled_start_at
    ? new Date(job.scheduled_start_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  // JOB-UI-B1: Show title when present; fallback to job_number for breadcrumb + heading
  const displayTitle =
    job.title ?? job.job_number ?? `Job ${jobId.slice(0, 8)}…`;

  return (
    <div className="px-6 pt-6 pb-4 border-b border-neutral-200 bg-white">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-neutral-500 mb-3">
        <Link href="/jobs" className="hover:text-neutral-700 transition-colors">
          Jobs
        </Link>
        <span>/</span>
        {/* JOB-UI-B1: Show title (fallback to job_number) instead of raw UUID */}
        <span
          className="text-neutral-900 font-medium"
          data-testid="job-detail-header-title"
        >
          {displayTitle}
        </span>
      </nav>

      {/* JOB-UI-B1: Page heading shows title when present */}
      {job.title && (
        <h1
          className="text-xl font-semibold text-neutral-900 mb-2"
          data-testid="job-detail-heading"
        >
          {job.title}
        </h1>
      )}

      {/* Status + dates + site + customer */}
      <div className="flex flex-wrap items-center gap-3">
        {/* FE-B26: Use status_code (not status_id UUID) */}
        <StatusBadge statusCode={job.status_code ?? job.status_id} />
        {scheduledDate && (
          <span className="text-sm text-neutral-600">📅 {scheduledDate}</span>
        )}
        {/* FE-B26: Show site_name instead of site_id UUID */}
        {job.site_name && (
          <span className="text-sm text-neutral-500">📍 {job.site_name}</span>
        )}
        {/* FE-B26: Show customer name */}
        {job.customer_name && (
          <span className="text-sm font-medium text-neutral-700">
            {job.customer_name}
          </span>
        )}
        {/* FE-B26: Link to originating quote if present */}
        {job.quote_id && (
          <Link
            href={`/quotes/${job.quote_id}`}
            className="text-sm text-brand-600 hover:text-brand-800 transition-colors"
          >
            View Quote →
          </Link>
        )}
      </div>
    </div>
  );
}
