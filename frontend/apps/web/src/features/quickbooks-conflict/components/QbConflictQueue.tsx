/**
 * QbConflictQueue — paginated table of QB conflicts
 *
 * Location: apps/web/src/features/quickbooks-conflict/components/QbConflictQueue.tsx
 *
 * Established FE-B9. Default sort: invoice > quote > customer/expense, then detection time.
 * InFlightSyncIndicator surface="quickbooks" (RULE I.1 for FE-B15).
 */

"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { InFlightSyncIndicator, useInFlightSyncStatus } from "@pilot/ui";
import { useQbConflicts } from "../hooks/useQbConflicts";
import { useQbConflictsSse } from "../hooks/useQbConflictsSse";
import { QbConflictRow } from "./QbConflictRow";
import { QbConflictFilterBar } from "./QbConflictFilterBar";
import { QbConflictEmptyState } from "./QbConflictEmptyState";
import type { QbEntityType } from "../types";

interface QbConflictQueueProps {
  testID?: string;
}

export function QbConflictQueue({ testID }: QbConflictQueueProps) {
  const router = useRouter();
  const [entityType, setEntityType] = useState<QbEntityType | undefined>(
    undefined,
  );
  const [masterFilter, setMasterFilter] = useState<
    "pilot" | "external" | undefined
  >(undefined);

  // SSE for real-time queue updates
  useQbConflictsSse();

  // FE-B15: unified sync status from BE-B15 (replaces static decoration)
  const syncStatus = useInFlightSyncStatus("quickbooks");

  const { data, isLoading, isError } = useQbConflicts({
    status: "pending",
    entity_type: entityType,
    limit: 20,
  });

  const conflicts = data?.conflicts ?? [];
  const totalPending = data?.total_pending ?? 0;

  // Apply master direction filter client-side (not in API params)
  const filteredConflicts = masterFilter
    ? conflicts.filter((c) => c.masterDirection === masterFilter)
    : conflicts;

  if (isError) {
    return (
      <div
        className="rounded-md border border-fault-200 bg-fault-50 p-4 text-caption text-fault-700"
        role="alert"
      >
        Failed to load QuickBooks conflicts. Please refresh.
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid={testID ?? "qb-conflict-queue"}>
      {/* Header with count + InFlightSyncIndicator (FE-B15: wired to useInFlightSyncStatus) */}
      <div className="flex items-center justify-between">
        <h2 className="text-h2 font-medium text-neutral-900">
          QuickBooks conflicts
          {totalPending > 0 && (
            <span className="ml-2 rounded-full bg-alert-100 px-2 py-0.5 text-caption font-medium text-alert-700">
              {totalPending}
            </span>
          )}
        </h2>
        <InFlightSyncIndicator
          surface="quickbooks"
          state={syncStatus.state}
          pendingCount={syncStatus.pendingCount}
          pendingItems={syncStatus.pendingItems}
          lastSyncedAt={syncStatus.lastSyncedAt}
          nextSyncAt={syncStatus.nextSyncAt}
          amberThreshold={syncStatus.amberThreshold}
          manualTriggerSupported={syncStatus.manualTriggerSupported}
          onResolve={() => {
            router.push("/settings/integrations/quickbooks/conflicts");
          }}
          compact={true}
          testID="qb-inflight-sync-indicator"
        />
      </div>

      {/* Filter bar */}
      <QbConflictFilterBar
        entityType={entityType}
        onEntityTypeChange={setEntityType}
        masterFilter={masterFilter}
        onMasterFilterChange={setMasterFilter}
        testID="qb-filter-bar"
      />

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-brand-600" />
        </div>
      ) : filteredConflicts.length === 0 ? (
        <QbConflictEmptyState testID="qb-empty-state" />
      ) : (
        <div className="overflow-x-auto rounded-md border border-neutral-200 bg-white">
          <table className="w-full" data-testid="qb-conflicts-table">
            <thead className="bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Entity
                </th>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Type
                </th>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Financial
                </th>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Detected
                </th>
                <th className="px-4 py-3 text-left text-caption font-medium text-neutral-600">
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredConflicts.map((conflict) => (
                <QbConflictRow key={conflict.id} conflict={conflict} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
