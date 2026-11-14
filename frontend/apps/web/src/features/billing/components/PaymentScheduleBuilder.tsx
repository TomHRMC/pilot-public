/**
 * PaymentScheduleBuilder — container orchestrating all 4 product states + 4 data states
 *
 * Location: apps/web/src/features/billing/components/PaymentScheduleBuilder.tsx
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §1.6, §2, §6).
 *
 * Product states (driven by schedule.status):
 *   A — Empty (no schedule yet) → <FirstTimeUserState> + start CTA
 *   B — Draft (fully editable) → DrawRow table + ReconciliationBar + Activate
 *   C — Active (structure locked) → read-only rows + per-draw lifecycle
 *   D — Completed/Cancelled (read-only summary)
 *
 * Data states (TanStack Query):
 *   isPending → skeleton matching the table shape
 *   isError   → <ErrorState> with retry
 *   empty     → State A
 *   populated → State B/C/D per status
 *
 * RBAC: wrapped in <RoleGate permission="invoices.create"> (owner/office see
 * the builder; techs hidden). Edit/activate actions inside the content are
 * further gated by the parent route's <RoleGate permission="invoices.update">
 * for owner-only editing (the content component renders edit controls only
 * when isDraft=true, and the route wraps the whole builder in
 * invoices.update for the detail/edit path).
 *
 * React Compiler (§32): no hand-memoization; component is pure.
 * Rule 14 (§35): client-side fetching via apiClient + TanStack Query.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CurrencyDollarIcon } from "@heroicons/react/24/outline";
import { PlusIcon as PlusIconSolid } from "@heroicons/react/24/solid";
import { RoleGate } from "@pilot/ui/role-gate";
import { ErrorState } from "@pilot/ui/states";
import { usePaymentSchedule } from "../hooks/usePaymentSchedule";
import { usePaymentSchedules } from "../hooks/usePaymentSchedules";
import { useCreatePaymentSchedule } from "../hooks/useCreatePaymentSchedule";
import { PaymentScheduleBuilderContent } from "./PaymentScheduleBuilderContent";
import { formatCents } from "../utils/format";

interface PaymentScheduleBuilderProps {
  /** When provided, fetch + edit an existing schedule. */
  scheduleId?: string;
  /** When true, this is the "new" route — look up by quote_id/job_id, or show State A. */
  mode?: "new";
  /** Quote ID for the new route (seeds contract_total_cents). */
  quoteId?: string;
  /** Job ID for the new route (seeds contract_total_cents). */
  jobId?: string;
  /** Pre-seeded contract total (from the quote/job total). */
  contractTotalCents?: number;
  /** Customer ID (required for create). */
  customerId?: string;
  /** Site ID (required for create). */
  siteId?: string;
  /** Customer name for display. */
  customerName?: string;
  /** Site label for display. */
  siteLabel?: string;
}

export function PaymentScheduleBuilder(props: PaymentScheduleBuilderProps) {
  return (
    <RoleGate permission="invoices.create">
      <PaymentScheduleBuilderInner {...props} />
    </RoleGate>
  );
}

function PaymentScheduleBuilderInner({
  scheduleId,
  mode,
  quoteId,
  jobId,
  contractTotalCents,
  customerId,
  siteId,
  customerName,
  siteLabel,
}: PaymentScheduleBuilderProps) {
  const router = useRouter();
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  // ── Detail mode: fetch the existing schedule ─────────────────────────────
  const detailQuery = usePaymentSchedule(scheduleId ?? "", {
    enabled: !!scheduleId && mode !== "new",
  });

  // ── New mode: look up if a schedule already exists for this quote/job ────
  const listQuery = usePaymentSchedules({
    quote_id: mode === "new" ? quoteId : undefined,
    job_id: mode === "new" ? jobId : undefined,
    enabled: mode === "new" && (!!quoteId || !!jobId),
  });

  const createMutation = useCreatePaymentSchedule({
    onSuccess: (schedule) => {
      // Navigate to the detail/edit route for the newly created schedule.
      router.push(`/billing/payment-schedules/${schedule.id}`);
    },
    onError: () => {
      setErrorDetail(
        "Could not create the payment schedule. Please try again.",
      );
    },
  });

  // ── Data state: isPending (skeleton) ─────────────────────────────────────
  const isPending =
    (detailQuery.isPending && !detailQuery.data) ||
    (mode === "new" && listQuery.isPending && !listQuery.data);

  if (isPending) {
    return <ScheduleSkeleton />;
  }

  // ── Data state: isError ──────────────────────────────────────────────────
  if (detailQuery.isError && !detailQuery.data) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <ErrorState
          type="server"
          title="Could not load payment schedule"
          description="Check your connection and try again."
          onRetry={() => void detailQuery.refetch()}
        />
      </div>
    );
  }

  if (mode === "new" && listQuery.isError && !listQuery.data) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <ErrorState
          type="server"
          title="Could not load payment schedules"
          description="Check your connection and try again."
          onRetry={() => void listQuery.refetch()}
        />
      </div>
    );
  }

  // ── New mode: if a schedule already exists, redirect to its detail page ──
  if (mode === "new" && listQuery.data && listQuery.data.items.length > 0) {
    const existing = listQuery.data.items[0];
    // Redirect to the detail page (client-side)
    if (typeof window !== "undefined") {
      router.replace(`/billing/payment-schedules/${existing.id}`);
    }
    return <ScheduleSkeleton />;
  }

  // ── Detail mode: populated → render content (State B/C/D) ────────────────
  if (detailQuery.data) {
    return (
      <>
        {errorDetail && (
          <div
            role="alert"
            className="fixed top-16 left-1/2 -translate-x-1/2 z-50 bg-fault-50 border border-fault-200 text-fault-600 rounded-md px-4 py-3 text-sm font-medium shadow-lg"
            data-testid="schedule-error-banner"
          >
            {errorDetail}
          </div>
        )}
        <PaymentScheduleBuilderContent
          schedule={detailQuery.data}
          customerName={customerName}
          siteLabel={siteLabel}
          onNotifyError={(detail) => setErrorDetail(detail)}
        />
      </>
    );
  }

  // ── New mode: no existing schedule → State A (empty) ─────────────────────
  if (mode === "new") {
    return (
      <div className="max-w-5xl mx-auto p-6">
        {errorDetail && (
          <div
            role="alert"
            className="mb-4 bg-fault-50 border border-fault-200 text-fault-600 rounded-md px-4 py-3 text-sm font-medium"
            data-testid="schedule-error-banner"
          >
            {errorDetail}
          </div>
        )}
        <div className="bg-white border border-neutral-200 rounded-lg shadow-sm p-10 text-center">
          <CurrencyDollarIcon
            className="w-12 h-12 text-brand-500 mx-auto"
            aria-hidden="true"
          />
          <h2 className="text-h2 font-semibold text-neutral-900 mt-4">
            Set up a payment schedule
          </h2>
          <p className="text-body text-neutral-500 mt-2 max-w-md mx-auto">
            Break this job into draws — a deposit, progress payments, and a
            final payment. Each draw becomes its own invoice when its milestone
            is reached. The draws must sum to the contract total before you can
            activate the schedule.
          </p>
          <button
            type="button"
            onClick={() => {
              if (!customerId || !siteId || !contractTotalCents) {
                setErrorDetail(
                  "Customer, site, and contract total are required to create a schedule.",
                );
                return;
              }
              createMutation.mutate({
                customer_id: customerId,
                site_id: siteId,
                contract_total_cents: contractTotalCents,
                basis_default: "percent",
                lines: [
                  {
                    sequence: 1,
                    label: "Deposit",
                    basis: "percent",
                    trigger_type: "manual",
                  },
                ],
                quote_id: quoteId ?? null,
                job_id: jobId ?? null,
              });
            }}
            disabled={createMutation.isPending}
            className="inline-flex items-center gap-1.5 mt-6 bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:opacity-50"
            data-testid="create-schedule-cta"
          >
            <PlusIconSolid className="w-4 h-4" aria-hidden="true" />
            {createMutation.isPending ? "Creating…" : "Set up payment schedule"}
          </button>
          {contractTotalCents != null && (
            <p className="text-caption text-neutral-500 mt-3">
              Contract total will be seeded from the {quoteId ? "quote" : "job"}{" "}
              total:{" "}
              <span className="font-medium">
                {formatCents(contractTotalCents)}
              </span>
              .
            </p>
          )}
        </div>
      </div>
    );
  }

  // Fallback (should not reach here)
  return <ScheduleSkeleton />;
}

// ── Skeleton (data state: isPending) ──────────────────────────────────────────
function ScheduleSkeleton() {
  return (
    <div
      className="max-w-5xl mx-auto p-6 pb-24"
      data-testid="schedule-skeleton"
    >
      {/* Header card skeleton */}
      <div className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4">
        <div className="flex items-center justify-between">
          <div className="animate-pulse bg-neutral-100 rounded h-6 w-48" />
          <div className="animate-pulse bg-neutral-100 rounded h-6 w-32" />
        </div>
        <div className="flex items-center gap-6 mt-3">
          <div className="animate-pulse bg-neutral-100 rounded h-4 w-40" />
          <div className="animate-pulse bg-neutral-100 rounded h-4 w-32" />
        </div>
      </div>
      {/* Table skeleton */}
      <div className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4">
        <div className="rounded-md border border-neutral-200 overflow-hidden">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="animate-pulse bg-neutral-100 h-14 border-b border-neutral-100"
            />
          ))}
        </div>
      </div>
      {/* Reconciliation bar skeleton */}
      <div className="animate-pulse bg-neutral-100 rounded-lg h-16" />
    </div>
  );
}
