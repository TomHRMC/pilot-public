"use client";
// "use no memo" — useReactTable() returns functions that cannot be memoized
// safely (same as PilotTable.tsx). The React Compiler skips this component.
"use no memo";

/**
 * CohortDashboardClient — orchestrator
 *
 * Location: apps/web/src/components/operator/cohort/CohortDashboardClient.tsx
 *
 * C-B11 Part B: Orchestrates the operator cohort dashboard page.
 * 1. useAuthMe() — get platform user permissions (for action visibility)
 * 2. useCohortOverview() — fetch cohort data
 * 3. Loading → skeleton, Error → ErrorState, Empty → EmptyState
 * 4. Success → header + summary strip + table + modals
 *
 * Auth gating: wrapped in RequireAuth (platform-level route, not under (authed)).
 *
 * RULE 5: zero hex codes. RULE 11: no hand-memo.
 * RULE 14: client-side data fetching. RULE 15: WCAG 2.2 AA.
 */

import React, { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  type ColumnDef,
} from "@tanstack/react-table";
import { CheckCircleIcon, LockClosedIcon } from "@heroicons/react/24/outline";
import { EmptyState, ErrorState } from "@pilot/ui/states";
import { PilotTable } from "@/components/PilotTable";
import { useCohortOverview } from "@/features/operator/hooks/useCohortOverview";
import { useAuthMe } from "@/features/auth/hooks/useAuthMe";
import {
  getCohortRowClassName,
  renderMemberCell,
  renderDaysLeftCell,
  renderStripeStatusCell,
  renderCardCell,
  renderMessagingStatusCell,
  renderCustomerCountCell,
  renderInvoiceCountCell,
  renderLastJobCell,
  renderActionsCell,
  type CohortMember,
} from "./CohortMemberRow";
// renderAlertCell is not imported — the alert column is rendered inline
// in the column def to keep the icon+text pairing visible in the table config.
import { ExtendFreePeriodModal } from "./ExtendFreePeriodModal";
import { CloseCohortButton } from "./CloseCohortButton";

// ── Platform permission mapping ──────────────────────────────────────────────

const PLATFORM_WRITE_PERMISSIONS: Record<string, string[]> = {
  owner: [
    "tenants",
    "users",
    "suppliers",
    "billing",
    "jwks",
    "plans",
    "notifications",
  ],
  support: ["tenants", "users", "billing", "notifications"],
  accountant: [],
};

function canExtend(platformRoleCode: string | null | undefined): boolean {
  if (!platformRoleCode) return false;
  const perms = PLATFORM_WRITE_PERMISSIONS[platformRoleCode] ?? [];
  return perms.includes("tenants") || perms.includes("billing");
}

function canCloseCohort(platformRoleCode: string | null | undefined): boolean {
  if (!platformRoleCode) return false;
  const perms = PLATFORM_WRITE_PERMISSIONS[platformRoleCode] ?? [];
  return perms.includes("billing");
}

// ── Column definitions ────────────────────────────────────────────────────────

function buildColumns(
  canExtendAction: boolean,
  onExtend: (tenantId: string) => void,
): ColumnDef<CohortMember>[] {
  // NOTE: We use plain ColumnDef objects (not columnHelper.accessor) because
  // TanStack Table's columnHelper.accessor infers TValue from the key, and
  // mixing accessor columns (TValue=string|number|boolean|null) with display
  // columns (TValue=unknown) causes a variance error in the array type.
  // Plain objects with accessorKey + a cast on the array is the standard fix.
  return [
    {
      id: "member",
      header: "Member",
      size: 220,
      cell: ({ row }) => renderMemberCell(row.original),
    },
    {
      accessorKey: "days_remaining",
      header: "Days left",
      size: 90,
      cell: ({ row }) => renderDaysLeftCell(row.original),
    },
    {
      accessorKey: "stripe_status",
      header: "Stripe",
      size: 110,
      cell: ({ row }) => renderStripeStatusCell(row.original),
    },
    {
      accessorKey: "has_payment_method",
      header: "Card",
      size: 70,
      cell: ({ row }) => renderCardCell(row.original),
    },
    {
      accessorKey: "messaging_status",
      header: "10DLC",
      size: 120,
      cell: ({ row }) => renderMessagingStatusCell(row.original),
    },
    {
      accessorKey: "customer_count",
      header: "Customers",
      size: 100,
      cell: ({ row }) => renderCustomerCountCell(row.original),
    },
    {
      accessorKey: "invoice_count",
      header: "Invoices",
      size: 100,
      cell: ({ row }) => renderInvoiceCountCell(row.original),
    },
    {
      accessorKey: "days_since_last_job",
      header: "Last job",
      size: 100,
      cell: ({ row }) => renderLastJobCell(row.original),
    },
    {
      accessorKey: "alert_level",
      header: "Alert",
      size: 140,
      cell: ({ row }) => (
        <span className="inline-flex items-center gap-1.5 text-sm">
          {row.original.alert_level === "red" && (
            <span className="inline-flex items-center gap-1.5 text-fault-600 text-sm font-medium">
              Activation risk
            </span>
          )}
          {row.original.alert_level === "amber" && (
            <span className="inline-flex items-center gap-1.5 text-alert-700 text-sm font-medium">
              Expiring soon
            </span>
          )}
          {row.original.alert_level === "none" && (
            <span className="inline-flex items-center gap-1.5 text-margin-600 text-sm">
              Healthy
            </span>
          )}
        </span>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      size: 100,
      cell: ({ row }) =>
        renderActionsCell(row.original, canExtendAction, onExtend),
    },
  ] as ColumnDef<CohortMember>[];
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CohortDashboardClient() {
  const { data: cohortData, isPending, isError, refetch } = useCohortOverview();
  const { data: authMeData } = useAuthMe();

  const [extendTenantId, setExtendTenantId] = useState<string | null>(null);
  const [sorting, setSorting] = useState<SortingState>([]);

  const platformRoleCode = authMeData?.platform_role_code ?? null;
  const canExtendAction = canExtend(platformRoleCode);
  const canClose = canCloseCohort(platformRoleCode);

  const columns = useMemo(
    () => buildColumns(canExtendAction, setExtendTenantId),
    [canExtendAction],
  );

  // eslint-disable-next-line react-hooks/incompatible-library -- useReactTable returns functions that cannot be memoized; "use no memo" opts out of the compiler, this disables the lint rule
  const table = useReactTable({
    data: cohortData?.members ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const extendMember = extendTenantId
    ? cohortData?.members.find((m) => m.tenant_id === extendTenantId)
    : null;

  return (
    <div className="flex flex-col h-screen">
      {/* Page header — C-B15: simplified (shell layout provides logo + Operator badge) */}
      <header className="h-16 bg-white border-b border-neutral-200 px-6 flex items-center justify-between sticky top-0 z-20 shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-h2 font-semibold text-neutral-900">
            Charter Cohort
          </h1>
        </div>
        <div>
          {canClose ? (
            <CloseCohortButton
              cohortIsActive={cohortData?.cohort_is_active ?? false}
              memberCount={cohortData?.members.length ?? 0}
            />
          ) : null}
        </div>
      </header>

      {/* Content area */}
      <div className="flex-1 overflow-auto bg-neutral-50 p-6">
        {/* Loading state — skeleton */}
        {isPending && (
          <div className="space-y-4">
            <div className="h-12 bg-neutral-100 animate-pulse rounded-lg" />
            <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
              {Array.from({ length: 8 }).map((_, i) => (
                <div
                  key={i}
                  className="h-12 bg-neutral-100 animate-pulse border-b border-neutral-100"
                />
              ))}
            </div>
          </div>
        )}

        {/* Error state */}
        {isError && (
          <ErrorState
            type="server"
            title="Could not load cohort data"
            description="Check your connection and try again."
            onRetry={() => void refetch()}
          />
        )}

        {/* Success state */}
        {cohortData && (
          <>
            {/* Cohort summary strip */}
            <div className="bg-white rounded-lg border border-neutral-200 shadow-sm px-4 py-3 mb-4 flex items-center gap-6">
              <span className="text-sm font-medium text-neutral-900">
                {cohortData.cohort_tier_name}
              </span>
              <span className="text-sm text-neutral-500">
                {cohortData.members.length} / {cohortData.signup_cap} members
              </span>
              {cohortData.cohort_is_active ? (
                <span className="inline-flex items-center gap-1 bg-margin-50 text-margin-700 rounded-full px-2.5 py-0.5 text-caption font-medium">
                  <CheckCircleIcon className="w-4 h-4" />
                  Cohort open
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 bg-neutral-100 text-neutral-500 rounded-full px-2.5 py-0.5 text-caption font-medium">
                  <LockClosedIcon className="w-4 h-4" />
                  Cohort closed
                </span>
              )}
            </div>

            {/* Empty state */}
            {cohortData.members.length === 0 ? (
              <EmptyState
                type="no-data"
                title="No Charter members yet"
                description="Members will appear here when they sign up."
              />
            ) : (
              /* Cohort table */
              <PilotTable
                table={table}
                tableDataTestId="cohort-table"
                getRowClassName={(row) => getCohortRowClassName(row)}
                getRowDataTestId={(row) => `cohort-row-${row.tenant_id}`}
              />
            )}
          </>
        )}
      </div>

      {/* Extend modal */}
      {extendMember && (
        <ExtendFreePeriodModal
          member={extendMember}
          onClose={() => setExtendTenantId(null)}
        />
      )}
    </div>
  );
}
