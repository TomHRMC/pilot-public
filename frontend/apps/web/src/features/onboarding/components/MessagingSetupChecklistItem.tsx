/**
 * MessagingSetupChecklistItem — Charter-only 10DLC messaging setup checklist row
 *
 * Location: apps/web/src/features/onboarding/components/MessagingSetupChecklistItem.tsx
 *
 * C-B5: A specialized checklist row that extends the ChecklistItem visual pattern
 * with a secondary cost-disclosure line. Rendered conditionally by the widget
 * when the tenant is on the Charter tier.
 *
 * Why a new component instead of extending ChecklistItem: The cost disclosure
 * is a multi-line secondary description that the existing ChecklistItem
 * description field doesn't support. Adding a secondaryDescription prop would
 * change the interface for all 8 existing items.
 */

"use client";

import React from "react";
import { InformationCircleIcon } from "@heroicons/react/24/outline";

interface MessagingSetupChecklistItemProps {
  isComplete: boolean;
  onNavigate: (route: string) => void;
}

const ACTION_ROUTE = "/settings/communications/sms-compliance";

export function MessagingSetupChecklistItem({
  isComplete,
  onNavigate,
}: MessagingSetupChecklistItemProps): React.ReactElement {
  return (
    <li
      className="flex items-start gap-3 py-2"
      data-testid="checklist-item-messagingSetup"
    >
      {/* Status icon */}
      <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center mt-0.5">
        {isComplete ? (
          <svg
            className="w-5 h-5 text-margin-600"
            fill="none"
            viewBox="0 0 20 20"
            aria-label="Completed"
            data-testid="checklist-check-messagingSetup"
          >
            <circle
              cx="10"
              cy="10"
              r="9"
              stroke="currentColor"
              strokeWidth="1.5"
            />
            <path
              d="M6 10l3 3 5-5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ) : (
          <div
            className="w-4 h-4 rounded-full border-2 border-neutral-300"
            aria-label="Incomplete"
            data-testid="checklist-incomplete-messagingSetup"
          />
        )}
      </div>

      {/* Label + cost disclosure */}
      <div className="flex-1 min-w-0">
        <span
          className={`text-sm font-medium ${
            isComplete ? "line-through text-neutral-400" : "text-neutral-900"
          }`}
          data-testid="checklist-label-messagingSetup"
        >
          Set up text messaging
        </span>

        {/* Cost disclosure */}
        <div className="flex items-start gap-1.5 mt-1">
          <InformationCircleIcon className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-neutral-500">
            Carrier registration costs, which vary between $21–$29 upfront and
            $3–$13 monthly (est.), depending on your business setup. This amount
            will go directly to the phone carrier - we don&apos;t take any of
            it.
          </p>
        </div>
      </div>

      {/* Action link (incomplete only) */}
      {!isComplete && (
        <a
          href={ACTION_ROUTE}
          onClick={(e) => {
            e.preventDefault();
            onNavigate(ACTION_ROUTE);
          }}
          className="text-xs font-medium text-brand-600 hover:text-brand-800 focus:outline-none focus-visible:underline min-h-[24px] py-1 flex-shrink-0"
          data-testid="checklist-action-messagingSetup"
        >
          Set up →
        </a>
      )}
    </li>
  );
}
