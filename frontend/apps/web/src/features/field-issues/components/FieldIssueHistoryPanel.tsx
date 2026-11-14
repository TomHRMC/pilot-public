/**
 * FieldIssueHistoryPanel — last 30 resolved escalations
 *
 * Location: apps/web/src/features/field-issues/components/FieldIssueHistoryPanel.tsx
 *
 * Established FE-B9. Expandable panel shown below queue and on empty state.
 * Links to /dashboard/approvals/field-issues/history for full archive.
 */

"use client";

import React, { useState } from "react";
import Link from "next/link";
import type { FieldIssueQueueItem } from "../types";

interface FieldIssueHistoryPanelProps {
  resolvedIssues?: FieldIssueQueueItem[];
  isLoading?: boolean;
  testID?: string;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function FieldIssueHistoryPanel({
  resolvedIssues = [],
  isLoading = false,
  testID,
}: FieldIssueHistoryPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div
      className="rounded-md border border-neutral-200 bg-neutral-50"
      data-testid={testID ?? "field-issue-history-panel"}
    >
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between px-4 py-3 text-caption font-medium text-neutral-700 hover:bg-neutral-100"
        aria-expanded={isExpanded}
        data-testid="history-panel-toggle"
      >
        <span>Recent history (last 30 resolved)</span>
        <span aria-hidden="true">{isExpanded ? "▾" : "▸"}</span>
      </button>

      {isExpanded && (
        <div
          className="border-t border-neutral-200"
          data-testid="history-panel-content"
        >
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 border-t-brand-600" />
            </div>
          ) : resolvedIssues.length === 0 ? (
            <p className="px-4 py-6 text-caption text-neutral-600 text-center">
              No resolved issues in the last 30 days.
            </p>
          ) : (
            <ul className="divide-y divide-neutral-100">
              {resolvedIssues.map((issue) => (
                <li
                  key={issue.id}
                  className="flex items-center justify-between px-4 py-2"
                >
                  <div>
                    <span className="text-caption font-medium text-neutral-900">
                      {issue.techName}
                    </span>
                    <span className="ml-2 text-caption text-neutral-500">
                      {issue.operationType.replace("_", " ")}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-caption text-neutral-500">
                      {formatDate(issue.escalatedAt)}
                    </span>
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-caption font-medium ${
                        issue.status === "auto_recovered"
                          ? "bg-margin-100 text-margin-700"
                          : "bg-neutral-100 text-neutral-600"
                      }`}
                    >
                      {issue.status === "auto_recovered"
                        ? "Auto-recovered"
                        : "Resolved"}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="border-t border-neutral-200 px-4 py-3">
            <Link
              href="/dashboard/approvals/field-issues/history"
              className="text-caption text-brand-600 hover:text-brand-700 hover:underline"
              data-testid="view-full-history-link"
            >
              View full history →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
