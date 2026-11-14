/**
 * ChecklistItem — Single row: icon + label + action button + optional skip link
 *
 * Location: apps/web/src/features/onboarding/components/ChecklistItem.tsx
 *
 * Token audit (Section H):
 *  - Completed item checkmark: text-margin-600
 *  - Completed label text: line-through text-neutral-400
 *  - Skipped item: text-neutral-400 italic
 */

"use client";

import React from "react";
import type {
  ChecklistItemConfig,
  OnboardingChecklistState,
  SkippableChecklistItem,
} from "../types";

interface ChecklistItemProps {
  config: ChecklistItemConfig;
  state: OnboardingChecklistState;
  onSkip?: (item: SkippableChecklistItem) => void;
  isSkipPending?: boolean;
}

function getItemStatus(
  config: ChecklistItemConfig,
  state: OnboardingChecklistState,
): "complete" | "skipped" | "incomplete" {
  const value = state[config.key];
  if (value === true) return "complete";
  if (config.skippedKey && state[config.skippedKey] === true) return "skipped";
  return "incomplete";
}

export function ChecklistItem({
  config,
  state,
  onSkip,
  isSkipPending = false,
}: ChecklistItemProps) {
  const status = getItemStatus(config, state);

  return (
    <li
      className="flex items-center gap-3 py-2"
      data-testid={`checklist-item-${config.key}`}
    >
      {/* Status icon */}
      <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
        {status === "complete" ? (
          <svg
            className="w-5 h-5 text-margin-600"
            fill="none"
            viewBox="0 0 20 20"
            aria-label="Completed"
            data-testid={`checklist-check-${config.key}`}
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
        ) : status === "skipped" ? (
          <svg
            className="w-5 h-5 text-neutral-300"
            fill="none"
            viewBox="0 0 20 20"
            aria-label="Skipped"
            data-testid={`checklist-skip-icon-${config.key}`}
          >
            <circle
              cx="10"
              cy="10"
              r="9"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeDasharray="4 2"
            />
          </svg>
        ) : (
          <div
            className="w-4 h-4 rounded-full border-2 border-neutral-300"
            aria-label="Incomplete"
            data-testid={`checklist-incomplete-${config.key}`}
          />
        )}
      </div>

      {/* Label + description */}
      <div className="flex-1 min-w-0">
        <span
          className={`text-sm font-medium ${
            status === "complete"
              ? "line-through text-neutral-400"
              : status === "skipped"
                ? "text-neutral-400 italic"
                : "text-neutral-900"
          }`}
          data-testid={`checklist-label-${config.key}`}
        >
          {config.label}
          {status === "skipped" && (
            <span className="ml-1.5 text-xs text-neutral-400 not-italic">
              (skipped)
            </span>
          )}
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Action button (incomplete items only, non-auto-complete) */}
        {status === "incomplete" &&
          !config.isAutoComplete &&
          config.actionRoute && (
            <a
              href={config.actionRoute}
              className="text-xs font-medium text-brand-600 hover:text-brand-800 focus:outline-none focus-visible:underline"
              data-testid={`checklist-action-${config.key}`}
            >
              {config.actionLabel} →
            </a>
          )}

        {/* Skip link */}
        {status === "incomplete" && config.isSkippable && onSkip && (
          <button
            type="button"
            onClick={() => onSkip(config.key as SkippableChecklistItem)}
            disabled={isSkipPending}
            data-testid={`checklist-skip-${config.key}`}
            className={`
              text-xs text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:underline
              ${isSkipPending ? "opacity-50 cursor-not-allowed" : ""}
            `}
          >
            Skip
          </button>
        )}
      </div>
    </li>
  );
}
