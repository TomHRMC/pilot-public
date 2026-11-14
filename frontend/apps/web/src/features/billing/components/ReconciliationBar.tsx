/**
 * ReconciliationBar — displays scheduled vs contract total + residual banner
 *
 * Location: apps/web/src/features/billing/components/ReconciliationBar.tsx
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §3.11).
 *
 * Presentational component. Displays three backend-computed values from
 * PaymentScheduleResponse: scheduled_total_cents, contract_total_cents,
 * residual_cents. NEVER recomputes them (design doc §F).
 *
 * Three color-independent states (WCAG 1.4.1) — each pairs color + text + icon:
 *   - Balanced (residual === 0): margin tokens + CheckCircleIcon
 *   - Under-allocated (residual > 0): alert tokens + ExclamationTriangleIcon
 *   - Over-allocated (residual < 0): fault tokens + ExclamationCircleIcon
 *
 * The progress bar is a SECONDARY signal; the text banner is primary.
 * Money = integer cents / 100, USD. Never raw cents.
 *
 * React Compiler (§32): no hand-memoization; component is pure.
 */

"use client";

import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
} from "@heroicons/react/24/solid";

interface ReconciliationBarProps {
  scheduledTotalCents: number;
  contractTotalCents: number;
  residualCents: number;
  /** When true (status='completed'), shows the completed treatment */
  isCompleted?: boolean;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

type ReconciliationState = "balanced" | "under" | "over";

function deriveState(residualCents: number): ReconciliationState {
  if (residualCents === 0) return "balanced";
  if (residualCents > 0) return "under";
  return "over";
}

const STATE_CONFIG: Record<
  ReconciliationState,
  {
    bannerClasses: string;
    barClasses: string;
    Icon: typeof CheckCircleIcon;
    text: (residual: number) => string;
  }
> = {
  balanced: {
    bannerClasses: "bg-margin-50 border-margin-200 text-margin-700",
    barClasses: "bg-margin-500",
    Icon: CheckCircleIcon,
    text: () => "$0 remaining — ready to activate",
  },
  under: {
    bannerClasses: "bg-alert-50 border-alert-200 text-alert-700",
    barClasses: "bg-alert-500",
    Icon: ExclamationTriangleIcon,
    text: (residual) =>
      `${formatCents(residual)} under-allocated — add draws to reach the contract total`,
  },
  over: {
    bannerClasses: "bg-fault-50 border-fault-200 text-fault-600",
    barClasses: "bg-fault-500",
    Icon: ExclamationCircleIcon,
    text: (residual) =>
      `${formatCents(Math.abs(residual))} over-allocated — reduce draws to match the contract total`,
  },
};

export function ReconciliationBar({
  scheduledTotalCents,
  contractTotalCents,
  residualCents,
  isCompleted = false,
}: ReconciliationBarProps) {
  const state = deriveState(residualCents);
  const config = STATE_CONFIG[state];
  const { Icon } = config;

  // Progress bar width — the only client-derived value (clamped 0–100).
  // Secondary signal; the text banner is primary (WCAG 1.4.1).
  const progressPct =
    contractTotalCents > 0
      ? Math.min(
          100,
          Math.max(0, (scheduledTotalCents / contractTotalCents) * 100),
        )
      : 0;

  // Completed state overrides the banner text
  const bannerText = isCompleted
    ? "Schedule completed — all draws invoiced"
    : config.text(residualCents);

  return (
    <section
      className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4 scroll-mt-16"
      aria-label="Payment schedule reconciliation"
      data-testid="reconciliation-bar"
    >
      {/* Row 1: scheduled | progress bar | contract */}
      <div className="flex items-center justify-between">
        <div className="flex items-baseline">
          <span className="text-sm text-neutral-500">Scheduled</span>
          <span
            className="text-h3 font-semibold text-neutral-900 ml-2"
            data-testid="scheduled-total"
          >
            {formatCents(scheduledTotalCents)}
          </span>
        </div>
        <div
          className="flex-1 mx-6 h-2 rounded-full bg-neutral-100 overflow-hidden"
          role="progressbar"
          aria-valuenow={Math.round(progressPct)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Scheduled vs contract total progress"
        >
          <div
            className={`h-full rounded-full transition-colors duration-200 ease-in-out ${config.barClasses}`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <div className="flex items-baseline">
          <span className="text-sm text-neutral-500">Contract</span>
          <span
            className="text-h3 font-semibold text-neutral-900 ml-2"
            data-testid="contract-total"
          >
            {formatCents(contractTotalCents)}
          </span>
        </div>
      </div>

      {/* Row 2: residual banner — color + text + icon (never color-only) */}
      <div
        className={`mt-4 rounded-md border px-4 py-3 flex items-center gap-2 transition-colors duration-200 ease-in-out ${config.bannerClasses}`}
        role="status"
        data-testid="residual-banner"
        data-state={state}
      >
        <Icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium">{bannerText}</span>
      </div>
    </section>
  );
}
