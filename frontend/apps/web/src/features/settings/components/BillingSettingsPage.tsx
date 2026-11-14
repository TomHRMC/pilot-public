/**
 * BillingSettingsPage — BETA-B4 / STEP 4
 *
 * Location: apps/web/src/features/settings/components/BillingSettingsPage.tsx
 *
 * Displays current subscription tier, trial status, usage metrics.
 * Charter members see an "Upgrade to Teams" CTA that opens the
 * CharterUpgradeModal (C-B12). Trial/starter members see a generic
 * "Upgrade plan" button (no-op until generic tier picker is built).
 * Route: /settings/billing
 *
 * PLP-FIX-5 (Issue 8): plan-summary card now renders a status badge
 * (color + text label per §H.1 Row 2), an interval-aware price line
 * (annual vs monthly vs charter), and a renews/free-period date line.
 * Breadcrumb added above the h1. Usage bars: "Team members" is count-only
 * (no users-limit feature exists); "SMS segments" wires max from
 * limits.outboundSmsSegments.
 */

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { CreditCardIcon, ArrowRightIcon } from "@heroicons/react/24/outline";
import { RoleGate } from "@pilot/ui/role-gate";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { useTenantSubscription } from "../hooks/useTenantSubscription";
import type { PlanSummary } from "../hooks/useTenantSubscription";
import { CharterUpgradeModal } from "./CharterUpgradeModal";
import { SettingsBreadcrumb } from "./SettingsBreadcrumb";

function formatCents(cents: number): string {
  return `$${(cents / 100).toFixed(0)}`;
}

function formatMonthly(cents: number): string {
  return `$${(cents / 100).toFixed(0)}/mo`;
}

function UsageBar({
  label,
  current,
  max,
}: {
  label: string;
  current: number;
  max: number | null;
}) {
  const pct = max ? Math.min((current / max) * 100, 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-xs text-neutral-600 mb-1">
        <span>{label}</span>
        <span>
          {current} {max ? `/ ${max}` : ""}
        </span>
      </div>
      {max && (
        <div className="h-1.5 rounded-full bg-neutral-200 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${pct > 80 ? "bg-alert-500" : "bg-brand-500"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}

/**
 * PLP-FIX-5 (Issue 8) — status badge pill.
 * Token pairs per design §H.1 Row 2 / Design Decision 4.
 * Label always rendered (color-independent — WCAG 2.2 AA 1.4.1).
 */
function StatusBadge({ planSummary }: { planSummary: PlanSummary }) {
  const code = planSummary.statusCode;
  // Map: trialing → alert "Trial"; active → success "Active"; past_due → alert "Past due";
  // paused/unpaid/canceled → fault + matching label; none → neutral "No active subscription".
  const map: Record<string, { cls: string; label: string }> = {
    trialing: {
      cls: "bg-alert-100 text-alert-700",
      label: planSummary.statusName ?? "Trial",
    },
    active: {
      cls: "bg-success-100 text-success-700",
      label: planSummary.statusName ?? "Active",
    },
    past_due: {
      cls: "bg-alert-100 text-alert-700",
      label: planSummary.statusName ?? "Past due",
    },
    paused: {
      cls: "bg-fault-100 text-fault-700",
      label: planSummary.statusName ?? "Paused",
    },
    unpaid: {
      cls: "bg-fault-100 text-fault-700",
      label: planSummary.statusName ?? "Unpaid",
    },
    canceled: {
      cls: "bg-fault-100 text-fault-700",
      label: planSummary.statusName ?? "Canceled",
    },
  };
  const entry = code ? map[code] : null;
  const cls = entry?.cls ?? "bg-neutral-100 text-neutral-600";
  const label = entry?.label ?? "No active subscription";
  return (
    <span
      className={`ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}
      data-testid="plan-status-badge"
    >
      {label}
    </span>
  );
}

function BillingContent() {
  const {
    subscription,
    isLoading,
    isError,
    upgradeFromCharter,
    isUpgradingFromCharter,
    upgradeError,
  } = useTenantSubscription();
  const [showCharterUpgrade, setShowCharterUpgrade] = useState(false);
  const { addNotification } = useNotificationQueue();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin h-6 w-6 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (isError || !subscription) {
    return (
      <div className="rounded-lg border border-fault-200 bg-fault-50 p-6 text-sm text-fault-700">
        Could not load subscription details. Please refresh the page.
      </div>
    );
  }

  const {
    currentTier,
    trialEndsAt,
    usage,
    charterEligible,
    planSummary,
    limits,
  } = subscription;
  const isTrial = currentTier.isTrial;
  const isCharter = currentTier.tierName === "charter" && charterEligible;

  // ── Price line (Design Decision 5 / §G.6) ────────────────────────────────
  // annual_price_cents is the YEARLY total → "$588/yr ($49/mo)"; monthly → "$59/mo";
  // charter branch unchanged ("Your rate: $49/mo — locked"); no interval → tier monthly
  // rate as the list price.
  function renderPriceLine() {
    if (isCharter) {
      return (
        <span>
          Your rate: {formatCents(currentTier.monthlyPriceCents)}/mo — locked
        </span>
      );
    }
    if (
      planSummary.billingInterval === "annual" &&
      currentTier.annualPriceCents
    ) {
      const perMonth = currentTier.annualPriceCents / 12 / 100;
      return (
        <span>
          {formatCents(currentTier.annualPriceCents)}/yr ($
          {perMonth.toFixed(0)}/mo)
        </span>
      );
    }
    if (planSummary.billingInterval === "monthly") {
      return <span>{formatMonthly(currentTier.monthlyPriceCents)}</span>;
    }
    // No interval (trial / no row) — tier monthly rate as list price
    return <span>{formatMonthly(currentTier.monthlyPriceCents)}</span>;
  }

  // ── Date line (Design Decision 6 / §G.5) ─────────────────────────────────
  // Charter tier → free_period_ends_at labeled "Free period ends …";
  // all others → renews_at labeled "Renews …". Rendered only when non-null.
  function renderDateLine() {
    if (isCharter && planSummary.freePeriodEndsAt) {
      return (
        <p className="text-sm text-neutral-500 mt-1">
          Free period ends{" "}
          {new Date(planSummary.freePeriodEndsAt).toLocaleDateString()}
        </p>
      );
    }
    if (!isCharter && planSummary.renewsAt) {
      return (
        <p className="text-sm text-neutral-500 mt-1">
          Renews {new Date(planSummary.renewsAt).toLocaleDateString()}
        </p>
      );
    }
    return null;
  }

  async function handleCharterUpgrade(
    billingInterval: "monthly" | "annual",
  ): Promise<void> {
    await upgradeFromCharter(billingInterval);
    addNotification({
      id: `charter-upgrade-success-${Date.now()}`,
      severity: "success",
      title: "You're now on the Teams plan.",
      dismissAfterMs: 6000,
    });
    setShowCharterUpgrade(false);
  }

  return (
    <>
      {/* Trial Banner */}
      {isTrial && trialEndsAt && (
        <div className="mb-6 rounded-md bg-alert-50 border border-alert-200 px-4 py-3 text-sm text-alert-800">
          <strong>
            Trial ends {new Date(trialEndsAt).toLocaleDateString()}
          </strong>{" "}
          — upgrade to keep access to all features.
        </div>
      )}

      {/* Current Plan Card */}
      <div className="rounded-md border border-neutral-200 p-5 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">
              Current Plan
            </p>
            <p className="text-xl font-semibold text-neutral-900">
              {currentTier.displayLabel}
              <StatusBadge planSummary={planSummary} />
            </p>
            <p className="text-sm text-neutral-500 mt-1">{renderPriceLine()}</p>
            {renderDateLine()}
          </div>
          {/* Charter upgrade CTA */}
          {isCharter && (
            <button
              type="button"
              onClick={() => setShowCharterUpgrade(true)}
              className="inline-flex items-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              Upgrade to Teams
              <ArrowRightIcon className="w-4 h-4 ml-2" aria-hidden="true" />
            </button>
          )}
          {/* Trial/starter upgrade — generic (no-op until tier picker built) */}
          {!isCharter && (isTrial || currentTier.tierName === "starter") && (
            <button
              type="button"
              onClick={() => {
                addNotification({
                  id: `tier-picker-coming-soon-${Date.now()}`,
                  severity: "info",
                  title: "Tier selection coming soon.",
                  dismissAfterMs: 6000,
                });
              }}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              Upgrade plan
            </button>
          )}
        </div>
      </div>

      {/* Usage Summary */}
      <div className="rounded-md border border-neutral-200 p-5 mb-6">
        <p className="text-sm font-medium text-neutral-900 mb-4">
          Usage This Month
        </p>
        <div className="space-y-4">
          <UsageBar
            label="Team members"
            current={usage.currentUserCount ?? 0}
            max={null}
          />
          <UsageBar
            label="SMS segments"
            current={usage.currentSmsSegments ?? 0}
            max={limits.outboundSmsSegments}
          />
        </div>
      </div>

      {/* Payment Method — links to dedicated payment-method settings page */}
      <div className="rounded-md border border-neutral-200 p-5">
        <div className="flex items-start">
          <CreditCardIcon className="w-4 h-4 text-neutral-500 mr-3 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-neutral-900 mb-1">
              Payment Method
            </p>
            <p className="text-xs text-neutral-500 mb-3">
              Manage how your customers pay invoices, including Stripe Connect.
            </p>
            <Link
              href="/settings/billing/payment-method"
              className="text-sm font-medium text-brand-600 hover:underline"
            >
              Payment Method settings →
            </Link>
          </div>
        </div>
      </div>

      {/* Charter Upgrade Modal (C-B12) */}
      <CharterUpgradeModal
        isOpen={showCharterUpgrade}
        onClose={() => setShowCharterUpgrade(false)}
        onUpgrade={handleCharterUpgrade}
        isUpgrading={isUpgradingFromCharter}
        upgradeError={upgradeError}
      />
    </>
  );
}

export function BillingSettingsPage() {
  return (
    <div className="p-6 max-w-2xl">
      <SettingsBreadcrumb
        trail={[
          { label: "Settings", href: "/settings" },
          { label: "Billing & Subscription" },
        ]}
      />
      <h1 className="text-2xl font-semibold text-neutral-900 mb-6">
        Billing & Subscription
      </h1>
      <RoleGate permission="billing.view">
        <BillingContent />
      </RoleGate>
    </div>
  );
}
