/**
 * SaveOnGroupCompleteIndicator — FE-B11
 *
 * Location: packages/ui/src/setting-control/SaveOnGroupCompleteIndicator.tsx
 *
 * Visual feedback for save-on-group-complete groups.
 * - Incomplete group: amber border tint + "Pick a direction…" prompt
 * - Save in-flight: spinner
 * - Just saved (< 2s): "Saved ✓" green tick
 * - Error: red error text
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */

"use client";

import React, { useEffect, useState } from "react";
import type { SaveOnGroupCompleteIndicatorProps } from "./types";

const SAVED_DISPLAY_DURATION_MS = 2000;

export function SaveOnGroupCompleteIndicator({
  groupIsComplete,
  incompleteFields,
  savedAt,
  savePending,
  error,
  incompletePrompt,
  testID,
}: SaveOnGroupCompleteIndicatorProps) {
  const [showSaved, setShowSaved] = useState(false);

  useEffect(() => {
    if (savedAt && Date.now() - savedAt < SAVED_DISPLAY_DURATION_MS) {
      setShowSaved(true);
      const timer = setTimeout(
        () => setShowSaved(false),
        SAVED_DISPLAY_DURATION_MS - (Date.now() - savedAt),
      );
      return () => clearTimeout(timer);
    }
  }, [savedAt]);

  // Nothing to render when group is clean and complete with no status
  if (groupIsComplete && !savePending && !showSaved && !error) {
    return null;
  }

  return (
    <div
      data-testid={testID ?? "save-on-group-complete-indicator"}
      className="flex items-center gap-2 mt-1"
    >
      {/* Save in-flight spinner */}
      {savePending && (
        <span
          className="flex items-center gap-1.5 text-caption text-neutral-400"
          aria-live="polite"
          data-testid={testID ? `${testID}-pending` : "group-indicator-pending"}
        >
          <span
            className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent"
            aria-hidden="true"
          />
          Saving…
        </span>
      )}

      {/* Saved confirmation tick */}
      {showSaved && !savePending && !error && (
        <span
          className="flex items-center gap-1 text-caption text-margin-600"
          aria-live="polite"
          data-testid={testID ? `${testID}-saved` : "group-indicator-saved"}
        >
          ✓ Saved
        </span>
      )}

      {/* Error state */}
      {error && !savePending && (
        <span
          className="text-caption text-fault-600"
          role="alert"
          data-testid={testID ? `${testID}-error` : "group-indicator-error"}
        >
          {error}
        </span>
      )}

      {/* Incomplete group: amber indicator */}
      {!groupIsComplete && !savePending && !error && (
        <span
          className="text-caption text-alert-600"
          data-testid={
            testID ? `${testID}-incomplete` : "group-indicator-incomplete"
          }
        >
          {incompletePrompt ?? "Complete all required fields to save."}
          {incompleteFields.length > 0 && (
            <span className="sr-only">
              {" "}
              Missing: {incompleteFields.join(", ")}
            </span>
          )}
        </span>
      )}
    </div>
  );
}
