"use client";

/**
 * ProvisioningStatusIndicator — C-B9
 *
 * Location: apps/web/src/components/settings/messaging/ProvisioningStatusIndicator.tsx
 *
 * Visual state machine progress indicator. Shows which steps are done,
 * in-progress, and remaining. Always visible once provisioning has started.
 *
 * UI spec §4.7. WCAG 2.2 AA: color-independent (CheckIcon/ArrowPathIcon/XMarkIcon),
 * prefers-reduced-motion fallback.
 * RULE 5: zero hex codes. RULE 11: no hand-memo.
 */

import React from "react";
import {
  CheckIcon,
  ArrowPathIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import type {
  MessagingStatus,
  StepState,
  EntityType,
} from "@/features/messaging/types";

export interface ProvisioningStatusIndicatorProps {
  status: MessagingStatus;
  entityType: EntityType;
}

interface StepDef {
  label: string;
  key: string;
}

const STEPS: StepDef[] = [
  { label: "Brand", key: "brand" },
  { label: "Payment", key: "payment" },
  { label: "Verify", key: "verify" },
  { label: "Campaign", key: "campaign" },
  { label: "Number", key: "number" },
  { label: "Activate", key: "activate" },
  { label: "Active", key: "active" },
];

/** Maps a status to the state of each step (7 steps). */
function getStepStates(status: MessagingStatus): StepState[] {
  // Returns array of 7 StepState values
  const map: Record<MessagingStatus, StepState[]> = {
    not_started: [
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
    ],
    quoting: [
      "in-progress",
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
    ],
    awaiting_payment: [
      "done",
      "in-progress",
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
    ],
    payment_failed: [
      "done",
      "error",
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
    ],
    brand_submitted: [
      "done",
      "done",
      "in-progress",
      "pending",
      "pending",
      "pending",
      "pending",
    ],
    awaiting_otp: [
      "done",
      "done",
      "in-progress",
      "pending",
      "pending",
      "pending",
      "pending",
    ],
    brand_verified: [
      "done",
      "done",
      "done",
      "in-progress",
      "pending",
      "pending",
      "pending",
    ],
    campaign_submitted: [
      "done",
      "done",
      "done",
      "in-progress",
      "pending",
      "pending",
      "pending",
    ],
    awaiting_number_selection: [
      "done",
      "done",
      "done",
      "done",
      "in-progress",
      "pending",
      "pending",
    ],
    number_assigned: [
      "done",
      "done",
      "done",
      "done",
      "done",
      "in-progress",
      "pending",
    ],
    active: ["done", "done", "done", "done", "done", "done", "done"],
    brand_rejected: [
      "error",
      "done",
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
    ],
    campaign_rejected: [
      "done",
      "done",
      "done",
      "error",
      "pending",
      "pending",
      "pending",
    ],
    suspended: ["done", "done", "done", "done", "done", "done", "error"],
  };
  return (
    map[status] ?? [
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
      "pending",
    ]
  );
}

function StepIcon({ state }: { state: StepState }) {
  if (state === "done") {
    return <CheckIcon className="w-5 h-5" />;
  }
  if (state === "in-progress") {
    return (
      <ArrowPathIcon className="w-4 h-4 animate-spin motion-reduce:animate-none" />
    );
  }
  if (state === "error") {
    return <XMarkIcon className="w-5 h-5" />;
  }
  return null; // pending — number shown instead
}

function stepCircleClass(state: StepState): string {
  if (state === "done") return "bg-margin-100 text-margin-700";
  if (state === "in-progress") return "bg-brand-100 text-brand-700";
  if (state === "error") return "bg-fault-100 text-fault-600";
  return "bg-neutral-100 text-neutral-400";
}

function stepLabelClass(state: StepState): string {
  if (state === "done")
    return "text-xs text-neutral-900 mt-1 text-center font-medium";
  if (state === "in-progress")
    return "text-xs text-brand-700 mt-1 text-center font-medium";
  if (state === "error")
    return "text-xs text-fault-600 mt-1 text-center font-medium";
  return "text-xs text-neutral-500 mt-1 text-center";
}

function connectorClass(leftState: StepState): string {
  if (leftState === "done") return "bg-margin-400";
  return "bg-neutral-200";
}

function srText(label: string, state: StepState): string {
  if (state === "done") return `${label}: complete`;
  if (state === "in-progress") return `${label}: in progress`;
  if (state === "error") return `${label}: error`;
  return `${label}: pending`;
}

export function ProvisioningStatusIndicator({
  status,
}: ProvisioningStatusIndicatorProps) {
  const stepStates = getStepStates(status);

  return (
    <ol
      role="list"
      aria-label="Provisioning progress"
      className="flex items-center justify-between w-full py-4"
      data-testid="provisioning-status-indicator"
    >
      {stepStates.map((state, index) => {
        const step = STEPS[index];
        const isLast = index === stepStates.length - 1;
        return (
          <React.Fragment key={step.key}>
            <li
              className="flex flex-col items-center shrink-0"
              aria-current={state === "in-progress" ? "step" : undefined}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${stepCircleClass(
                  state,
                )}`}
              >
                {state === "pending" ? index + 1 : <StepIcon state={state} />}
              </div>
              <span className={stepLabelClass(state)}>{step.label}</span>
              <span className="sr-only">{srText(step.label, state)}</span>
            </li>
            {!isLast && (
              <div
                className={`flex-1 h-0.5 ${connectorClass(state)} mx-1 mb-5`}
                aria-hidden="true"
              />
            )}
          </React.Fragment>
        );
      })}
    </ol>
  );
}
