/**
 * FieldIssuesQueue — paginated table of field issues
 *
 * Location: apps/web/src/features/field-issues/components/FieldIssuesQueue.tsx
 *
 * Established FE-B9. Renders table with filter bar; empty state when no issues.
 * SSE connection via useFieldIssuesSse for real-time updates.
 */

"use client";

import React, { useState } from "react";
import { useAuth } from "@pilot/ui/auth";
import { useFieldIssues } from "../hooks/useFieldIssues";
import { useFieldIssuesSse } from "../hooks/useFieldIssuesSse";
import { FieldIssueRow } from "./FieldIssueRow";
import { FieldIssueFilterBar } from "./FieldIssueFilterBar";
import { FieldIssueEmptyState } from "./FieldIssueEmptyState";
import { FieldIssueHistoryPanel } from "./FieldIssueHistoryPanel";
import type { FieldIssueStatus, FieldIssueOperationType } from "../types";

interface FieldIssuesQueueProps {
  testID?: string;
}

export function FieldIssuesQueue({ testID }: FieldIssuesQueueProps) {
  const { role } = useAuth();
  const [status, setStatus] = useState<FieldIssueStatus | "all">("pending");
  const [operationType, setOperationType] = useState<
    FieldIssueOperationType | undefined
  >(undefined);
  const [activeTechsOnly, setActiveTechsOnly] = useState(true);

  // SSE for real-time queue updates
  useFieldIssuesSse();

  const { data, isLoading, isError } = useFieldIssues({
    status,
    operation_type: operationType,
    active_techs_only: activeTechsOnly,
    limit: 20,
  });

  const issues = data?.issues ?? [];
  const totalPending = data?.total_pending ?? 0;

  if (role !== "owner" && role !== "office_staff") {
    return (
      <div
        className="rounded-md border border-neutral-200 bg-neutral-50 p-8 text-center text-caption text-neutral-500"
        role="alert"
        data-testid="field-issues-access-denied"
      >
        Access restricted. Only owners and office staff can view field issues.
      </div>
    );
  }

  if (isError) {
    return (
      <div
        className="rounded-md border border-fault-200 bg-fault-50 p-4 text-caption text-fault-700"
        role="alert"
      >
        Failed to load field issues. Please refresh.
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid={testID ?? "field-issues-queue"}>
      {/* Header with total count */}
      <div className="flex items-center justify-between">
        <h2 className="text-h2 font-medium text-neutral-900">
          Field issues
          {totalPending > 0 && (
            <span className="ml-2 rounded-full bg-alert-100 px-2 py-0.5 text-caption font-medium text-alert-700">
              {totalPending}
            </span>
          )}
        </h2>
      </div>

      {/* Filter bar */}
      <FieldIssueFilterBar
        status={status}
        onStatusChange={setStatus}
        operationType={operationType}
        onOperationTypeChange={setOperationType}
        activeTechsOnly={activeTechsOnly}
        onActiveTechsOnlyChange={setActiveTechsOnly}
        testID="queue-filter-bar"
      />

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-brand-600" />
        </div>
      ) : issues.length === 0 ? (
        <div className="space-y-4">
          <FieldIssueEmptyState />
          <FieldIssueHistoryPanel testID="queue-history-panel" />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-neutral-200 bg-white">
          <table className="w-full" data-testid="field-issues-table">
            <thead className="bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Tech
                </th>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Operation
                </th>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Issue
                </th>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Captured
                </th>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {issues.map((issue) => (
                <FieldIssueRow key={issue.id} issue={issue} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
