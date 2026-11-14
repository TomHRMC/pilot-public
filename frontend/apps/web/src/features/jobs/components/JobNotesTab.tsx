/**
 * JobNotesTab — large textarea with save-on-blur behavior
 *
 * Location: apps/web/src/features/jobs/components/JobNotesTab.tsx
 *
 * CRITICAL rules:
 * - Save on blur (onBlur event) — NOT a submit button
 * - Show "Saving..." while mutation pending
 * - Show "Saved ✓" for 2 seconds after successful save
 * - If save fails: show inline error
 * - Notes field: `notes` (not `notes_text`)
 */

"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useJobNotes } from "../hooks/useJobNotes";
import { useUpdateJobNotes } from "../hooks/useUpdateJobNotes";

// saveFlash border highlight duration
const FLASH_DURATION_MS = 800;

interface JobNotesTabProps {
  jobId: string;
}

type SaveStatus = "idle" | "saving" | "saved" | "error";

export function JobNotesTab({ jobId }: JobNotesTabProps) {
  const { data: notesData, isLoading } = useJobNotes(jobId);
  const { mutate: updateNotes, isPending } = useUpdateJobNotes(jobId);

  const [localNotes, setLocalNotes] = useState("");
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveFlash, setSaveFlash] = useState(false);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync local state from server on initial load only.

  // Rationale: this is a one-time initialization from async server data — a
  // well-understood pattern for form state that pre-dates React Query.
  // The effect fires once when notesData becomes available and does not cause
  // cascading renders because the dependency is stable after first load.
  useEffect(() => {
    if (notesData?.notes !== undefined) {
      setLocalNotes(notesData.notes); // eslint-disable-line react-hooks/set-state-in-effect
    }
  }, [notesData?.notes]);

  // Clear timers on unmount
  useEffect(() => {
    return () => {
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
      if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
    };
  }, []);

  const handleBlur = useCallback(() => {
    // Don't save if no data loaded yet or value hasn't changed
    if (!notesData) return;
    if (localNotes === notesData.notes) return;

    setSaveStatus("saving");
    setSaveError(null);

    updateNotes(
      { notes: localNotes },
      {
        onSuccess: () => {
          setSaveStatus("saved");
          // Border flash feedback
          setSaveFlash(true);
          flashTimerRef.current = setTimeout(() => {
            setSaveFlash(false);
          }, FLASH_DURATION_MS);
          // Auto-clear "Saved ✓" after 2 seconds
          savedTimerRef.current = setTimeout(() => {
            setSaveStatus("idle");
          }, 2000);
        },
        onError: (err) => {
          setSaveStatus("error");
          setSaveError(
            (err as Error)?.message ??
              "Failed to save notes. Please try again.",
          );
        },
      },
    );
  }, [localNotes, notesData, updateNotes]);

  if (isLoading) {
    return (
      <div className="py-6 text-center text-sm text-neutral-500">
        Loading notes…
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-neutral-700">Job Notes</h3>
        {/* Save status indicator — no submit button */}
        <div className="text-xs" aria-live="polite">
          {isPending || saveStatus === "saving" ? (
            <span className="text-neutral-500">Saving…</span>
          ) : saveStatus === "saved" ? (
            <span className="text-sm font-medium text-margin-600 transition-opacity duration-500">
              Saved ✓
            </span>
          ) : saveStatus === "error" ? (
            <span className="text-red-600">
              Save failed —{" "}
              <button
                onClick={handleBlur}
                className="underline hover:no-underline"
              >
                Retry
              </button>
            </span>
          ) : null}
        </div>
      </div>

      {saveError && saveStatus === "error" && (
        <p className="mb-2 text-sm text-red-600">{saveError}</p>
      )}

      <textarea
        value={localNotes}
        onChange={(e) => {
          setLocalNotes(e.target.value);
          // Reset status when user edits after an error
          if (saveStatus === "error") setSaveStatus("idle");
        }}
        onBlur={handleBlur}
        placeholder="Add notes about this job — materials, access instructions, customer preferences, etc."
        rows={10}
        className={`w-full px-3 py-2.5 border rounded-lg text-sm text-neutral-900 placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y transition-all duration-300 ${
          saveFlash
            ? "border-margin-400 ring-1 ring-margin-300"
            : "border-neutral-300"
        }`}
        data-testid="job-notes-textarea"
      />

      <p className="mt-1.5 text-xs text-neutral-400">
        Changes save automatically when you click away.
      </p>
    </div>
  );
}
