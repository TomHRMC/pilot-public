/**
 * JobTimeEntriesTab — time entries list + add form
 *
 * Location: apps/web/src/features/jobs/components/JobTimeEntriesTab.tsx
 *
 * "+ Add Time Entry" button gated to jobs.edit (owner, office_staff, operator).
 * Hours auto-calculated from start/end time.
 */

"use client";

import React, { useState } from "react";
import { EmptyState, RoleGate } from "@pilot/ui";
import { useJobTimeEntries } from "../hooks/useJobTimeEntries";
import { useAddTimeEntry } from "../hooks/useAddTimeEntry";

interface JobTimeEntriesTabProps {
  jobId: string;
}

function centsToDisplay(cents: number | null): string {
  if (cents == null) return "—";
  return `$${(cents / 100).toFixed(2)}`;
}

function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** Calculate hours from start + end ISO strings. Returns null if either is missing. */
function calculateHours(start: string, end: string): number | null {
  if (!start || !end) return null;
  const diff =
    (new Date(end).getTime() - new Date(start).getTime()) / (1000 * 60 * 60);
  return diff > 0 ? Math.round(diff * 100) / 100 : null;
}

interface AddTimeEntryFormProps {
  jobId: string;
  onCancel: () => void;
}

function AddTimeEntryForm({ jobId, onCancel }: AddTimeEntryFormProps) {
  const [startedAt, setStartedAt] = useState("");
  const [endedAt, setEndedAt] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { mutate: addEntry, isPending } = useAddTimeEntry(jobId);

  const calculatedHours =
    startedAt && endedAt ? calculateHours(startedAt, endedAt) : null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!startedAt) {
      setError("Start time is required.");
      return;
    }
    setError(null);
    addEntry(
      {
        started_at: new Date(startedAt).toISOString(),
        ended_at: endedAt ? new Date(endedAt).toISOString() : null,
        hours: calculatedHours,
        notes: notes || null,
      },
      { onSuccess: onCancel },
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-3 p-4 bg-neutral-50 rounded-lg border border-neutral-200 space-y-3"
    >
      <h4 className="text-sm font-semibold text-neutral-700">Add Time Entry</h4>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-neutral-500 mb-1">
            Start Time *
          </label>
          <input
            type="datetime-local"
            value={startedAt}
            onChange={(e) => setStartedAt(e.target.value)}
            required
            className="w-full px-2 py-1.5 border border-neutral-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div>
          <label className="block text-xs text-neutral-500 mb-1">
            End Time
          </label>
          <input
            type="datetime-local"
            value={endedAt}
            onChange={(e) => setEndedAt(e.target.value)}
            className="w-full px-2 py-1.5 border border-neutral-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      {calculatedHours !== null && (
        <p className="text-xs text-neutral-500">
          Calculated hours: <strong>{calculatedHours}</strong>
        </p>
      )}

      <div>
        <label className="block text-xs text-neutral-500 mb-1">
          Notes (optional)
        </label>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="What work was done?"
          className="w-full px-2 py-1.5 border border-neutral-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={isPending}
          className="px-3 py-1.5 bg-brand-600 text-white text-sm rounded hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? "Saving…" : "Add Entry"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 bg-white border border-neutral-300 text-neutral-700 text-sm rounded hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export function JobTimeEntriesTab({ jobId }: JobTimeEntriesTabProps) {
  const [showForm, setShowForm] = useState(false);
  const { data: entries = [], isLoading } = useJobTimeEntries(jobId);

  if (isLoading) {
    return (
      <div className="py-6 text-center text-sm text-neutral-500">
        Loading time entries…
      </div>
    );
  }

  return (
    <div>
      {/* Header row */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-neutral-700">
          Time Entries ({entries.length})
        </h3>
        <RoleGate permission="jobs.edit">
          <button
            onClick={() => setShowForm((v) => !v)}
            data-testid="add-time-entry-btn"
            className="text-sm text-brand-600 hover:text-brand-800 font-medium"
          >
            + Add Time Entry
          </button>
        </RoleGate>
      </div>

      {/* Add form */}
      {showForm && (
        <AddTimeEntryForm jobId={jobId} onCancel={() => setShowForm(false)} />
      )}

      {/* List or empty state */}
      {entries.length === 0 ? (
        <EmptyState
          type="no-data"
          title="No time entries yet"
          description="Time entries are added by field techs via the mobile app, or manually here."
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
          <table className="w-full">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Start
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  End
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Hours
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Rate
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Total
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Notes
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50"
                >
                  <td className="px-3 py-2.5 text-sm text-neutral-900">
                    {formatDateTime(entry.started_at)}
                  </td>
                  <td className="px-3 py-2.5 text-sm text-neutral-600">
                    {entry.ended_at ? formatDateTime(entry.ended_at) : "—"}
                  </td>
                  <td className="px-3 py-2.5 text-sm text-neutral-900 font-medium">
                    {entry.hours ?? "—"}h
                  </td>
                  <td className="px-3 py-2.5 text-sm text-neutral-600">
                    {entry.hourly_rate_cents
                      ? `$${(entry.hourly_rate_cents / 100).toFixed(0)}/hr`
                      : "—"}
                  </td>
                  <td className="px-3 py-2.5 text-sm text-neutral-900 font-medium">
                    {centsToDisplay(entry.total_cost_cents)}
                  </td>
                  <td className="px-3 py-2.5 text-sm text-neutral-500">
                    {entry.notes ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
