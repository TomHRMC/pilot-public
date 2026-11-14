/**
 * DeletionConflictView — layout for deletion-type conflicts
 *
 * Location: packages/ui/src/integration-conflict-resolver/DeletionConflictView.tsx
 *
 * Renders verb-button pairs for deleted_modified and modified_deleted conflict types.
 * No DiffView — deletion conflicts do not have a field-level diff.
 *
 * Verb pairs (per design doc §Decision 2):
 *   deleted_modified: "Restore the Job from Calendar" (primary) /
 *                     "Delete from Calendar Too" (secondary-destructive)
 *   modified_deleted: "Recreate the Calendar Event" (primary) /
 *                     "Delete the Pilot Job" (secondary-destructive)
 *
 * Tokens: bg-alert-50, border-alert-200, text-alert-700 (amber info banner);
 *         bg-brand-600 (primary button); border-fault-200 text-fault-700 (destructive).
 */

import React from "react";
import type { DeletionConflictViewProps, CalendarResolution } from "./types";

interface VerbPair {
  primaryLabel: string;
  primaryResolution: CalendarResolution;
  destructiveLabel: string;
  destructiveResolution: CalendarResolution;
  bannerText: string;
}

const VERB_PAIRS: Record<"deleted_modified" | "modified_deleted", VerbPair> = {
  deleted_modified: {
    primaryLabel: "Restore the Job from Calendar",
    primaryResolution: "restore_from_calendar",
    destructiveLabel: "Delete from Calendar Too",
    destructiveResolution: "delete_calendar_too",
    bannerText:
      "The calendar event was deleted externally. The Pilot job still exists. Choose how to proceed.",
  },
  modified_deleted: {
    primaryLabel: "Recreate the Calendar Event",
    primaryResolution: "recreate_calendar_event",
    destructiveLabel: "Delete the Pilot Job",
    destructiveResolution: "delete_pilot_job",
    bannerText:
      "The Pilot job was modified, but the calendar event was deleted. Choose how to proceed.",
  },
};

export function DeletionConflictView({
  conflictType,
  jobTitle,
  onResolve,
  isResolving,
  onResolveLater,
  testID,
}: DeletionConflictViewProps) {
  const verbKey = conflictType as "deleted_modified" | "modified_deleted";
  const verbs = VERB_PAIRS[verbKey];

  if (!verbs) return null;

  return (
    <div data-testid={testID ?? "deletion-conflict-view"} className="space-y-6">
      {/* Context banner */}
      <div
        className="flex items-start gap-3 rounded-lg border border-alert-200 bg-alert-50 p-4"
        role="alert"
      >
        {/* Warning icon using currentColor from text-alert-700 */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="mt-0.5 h-5 w-5 flex-shrink-0 text-alert-600"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
            clipRule="evenodd"
          />
        </svg>
        <div className="space-y-1">
          <p className="text-body font-medium text-alert-700">
            Deletion Conflict
            {jobTitle ? `: ${jobTitle}` : ""}
          </p>
          <p className="text-caption text-alert-600">{verbs.bannerText}</p>
        </div>
      </div>

      {/* Action buttons */}
      <div className="space-y-3">
        {/* Primary action */}
        <button
          type="button"
          disabled={isResolving}
          onClick={() => onResolve(verbs.primaryResolution)}
          className="flex w-full items-center justify-center rounded-md bg-brand-600 px-4 py-3 text-body font-medium text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          aria-busy={isResolving}
          data-testid="deletion-primary-btn"
        >
          {isResolving ? (
            <span className="flex items-center gap-2">
              <svg
                className="h-4 w-4 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Resolving…
            </span>
          ) : (
            verbs.primaryLabel
          )}
        </button>

        {/* Destructive secondary action */}
        <button
          type="button"
          disabled={isResolving}
          onClick={() => onResolve(verbs.destructiveResolution)}
          className="flex w-full items-center justify-center rounded-md border border-fault-200 bg-white px-4 py-3 text-body font-medium text-fault-700 hover:bg-fault-50 focus:outline-none focus:ring-2 focus:ring-fault-200 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          aria-busy={isResolving}
          data-testid="deletion-destructive-btn"
        >
          {verbs.destructiveLabel}
        </button>

        {/* Escape hatch */}
        <button
          type="button"
          disabled={isResolving}
          onClick={onResolveLater}
          className="flex w-full items-center justify-center px-4 py-2 text-caption text-neutral-600 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
          data-testid="deletion-resolve-later-btn"
        >
          Resolve later
        </button>
      </div>
    </div>
  );
}
