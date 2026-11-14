"use client";

/**
 * StatusPill — subscription-status pill (four-class severity, §16.6)
 *
 * Location: apps/web/src/components/operator/StatusPill.tsx
 *
 * C-B15 Part B: Color-independent status indicator (icon + text label,
 * never color alone — WCAG 1.4.1). Reused by TenantSelector (§4.4) and
 * ImpersonationConfirmModal (§5.6).
 *
 * RULE 5: zero hex codes. RULE 15: WCAG 2.2 AA (color-independent).
 */

import React from "react";
import {
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  PauseIcon,
  MinusCircleIcon,
} from "@heroicons/react/24/outline";

type HeroIcon = React.ElementType<{
  className?: string;
  "aria-hidden"?: boolean | "false" | "true";
}>;

interface StatusPillConfig {
  icon: HeroIcon;
  label: string;
  classes: string;
}

const STATUS_CONFIG: Record<string, StatusPillConfig> = {
  active: {
    icon: CheckCircleIcon,
    label: "Active",
    classes: "bg-margin-100 text-margin-700",
  },
  trialing: {
    icon: ClockIcon,
    label: "Trialing",
    classes: "bg-blue-100 text-blue-700",
  },
  past_due: {
    icon: ExclamationCircleIcon,
    label: "Past due",
    classes: "bg-alert-100 text-alert-700",
  },
  incomplete: {
    icon: ExclamationCircleIcon,
    label: "Incomplete",
    classes: "bg-alert-100 text-alert-700",
  },
  paused: {
    icon: PauseIcon,
    label: "Paused",
    classes: "bg-neutral-100 text-neutral-500",
  },
  canceled: {
    icon: MinusCircleIcon,
    label: "Canceled",
    classes: "bg-neutral-100 text-neutral-500",
  },
};

const NULL_CONFIG: StatusPillConfig = {
  icon: MinusCircleIcon,
  label: "No subscription",
  classes: "bg-neutral-100 text-neutral-500",
};

export function getStatusLabel(status: string | null): string {
  if (status === null) return NULL_CONFIG.label;
  return STATUS_CONFIG[status]?.label ?? status;
}

export function StatusPill({ status }: { status: string | null }) {
  const config =
    status === null ? NULL_CONFIG : (STATUS_CONFIG[status] ?? NULL_CONFIG);
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-caption font-medium ${config.classes}`}
    >
      <Icon className="w-3.5 h-3.5" aria-hidden="true" />
      {config.label}
    </span>
  );
}
