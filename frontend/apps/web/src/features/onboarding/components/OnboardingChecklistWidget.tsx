/**
 * OnboardingChecklistWidget — Dashboard widget: server-driven setup checklist
 *
 * Location: apps/web/src/features/onboarding/components/OnboardingChecklistWidget.tsx
 *
 * Design doc Decision 4: server-driven; 30s stale; refetchOnWindowFocus.
 * Widget disappears when checklistDismissedPermanently=true OR all items complete/skipped.
 * Hidden state collapses to compact pill with "Show" affordance.
 */

"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { ChecklistItem } from "./ChecklistItem";
import { MessagingSetupChecklistItem } from "./MessagingSetupChecklistItem";
import { useChecklistMutations } from "../hooks/useChecklistMutations";
import { CHECKLIST_ITEMS, isChecklistComplete } from "../types";
import type {
  OnboardingChecklistState,
  SkippableChecklistItem,
} from "../types";

interface OnboardingChecklistWidgetProps {
  tenantId: string;
  checklistState: OnboardingChecklistState;
  /** C-B5: Charter-only messaging setup item is rendered only for charter tier */
  tierName?: string;
}

function countCompleteOrSkipped(state: OnboardingChecklistState): number {
  return CHECKLIST_ITEMS.filter((item) => {
    const value = state[item.key];
    const skipped = item.skippedKey ? state[item.skippedKey] : false;
    return value === true || skipped === true;
  }).length;
}

export function OnboardingChecklistWidget({
  tenantId,
  checklistState,
  tierName,
}: OnboardingChecklistWidgetProps) {
  const router = useRouter();
  const { skipItem, hideChecklist, dismissChecklist } =
    useChecklistMutations(tenantId);

  // Widget disappears when permanently dismissed OR all complete
  if (
    checklistState.checklistDismissedPermanently ||
    isChecklistComplete(checklistState)
  ) {
    return null;
  }

  const doneCount = countCompleteOrSkipped(checklistState);
  const totalCount = CHECKLIST_ITEMS.length;

  // Hidden state: compact pill
  if (checklistState.checklistHidden) {
    return (
      <div
        className="flex items-center justify-between rounded-lg bg-white border border-neutral-200 px-4 py-2 text-sm shadow-sm"
        data-testid="checklist-widget-pill"
      >
        <span className="text-neutral-700 font-medium">
          Setup checklist ({doneCount} of {totalCount} done)
        </span>
        <button
          type="button"
          onClick={() => hideChecklist.mutate(false)}
          disabled={hideChecklist.isPending}
          className="text-brand-600 hover:text-brand-800 text-sm focus:outline-none focus-visible:underline"
          data-testid="checklist-show-button"
        >
          Show
        </button>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden"
      data-testid="checklist-widget"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-100">
        <div className="flex flex-col gap-0.5">
          <h2 className="text-sm font-semibold text-neutral-900">
            Complete your setup
          </h2>
          <p className="text-xs text-neutral-500">
            {doneCount} of {totalCount} tasks done
          </p>
        </div>

        {/* Progress bar */}
        <div className="flex items-center gap-3">
          <div className="w-24 h-1.5 rounded-full bg-neutral-100">
            <div
              className="h-1.5 rounded-full bg-brand-600 transition-all"
              style={{ width: `${(doneCount / totalCount) * 100}%` }}
              data-testid="checklist-progress-bar"
            />
          </div>
          <span className="text-xs text-neutral-500">
            {Math.round((doneCount / totalCount) * 100)}%
          </span>
        </div>
      </div>

      {/* Checklist items */}
      <ul
        className="px-5 divide-y divide-neutral-50"
        data-testid="checklist-items"
      >
        {CHECKLIST_ITEMS.map((item) => {
          // C-B5: messagingSetup is Charter-only — skip for non-charter tiers
          if (item.key === "messagingSetup" && tierName !== "charter") {
            return null;
          }
          // C-B5: messagingSetup uses a specialized component with cost disclosure
          if (item.key === "messagingSetup" && tierName === "charter") {
            return (
              <MessagingSetupChecklistItem
                key={item.key}
                isComplete={checklistState.messagingSetup}
                onNavigate={(route) => router.push(route)}
              />
            );
          }
          return (
            <ChecklistItem
              key={item.key}
              config={item}
              state={checklistState}
              onSkip={
                item.isSkippable
                  ? (skippableItem: SkippableChecklistItem) =>
                      skipItem.mutate(skippableItem)
                  : undefined
              }
              isSkipPending={skipItem.isPending}
            />
          );
        })}
      </ul>

      {/* Footer: hide / dismiss controls */}
      <div className="flex items-center justify-end gap-4 px-5 py-3 border-t border-neutral-50 bg-neutral-50">
        <button
          type="button"
          onClick={() => hideChecklist.mutate(true)}
          disabled={hideChecklist.isPending}
          className="text-xs text-neutral-500 hover:text-neutral-700 focus:outline-none focus-visible:underline"
          data-testid="checklist-hide-button"
        >
          Hide
        </button>
        <button
          type="button"
          onClick={() => dismissChecklist.mutate()}
          disabled={dismissChecklist.isPending}
          className="text-xs text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:underline"
          data-testid="checklist-dismiss-button"
        >
          Don&apos;t show again
        </button>
      </div>
    </div>
  );
}
