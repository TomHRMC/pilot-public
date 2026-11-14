/**
 * HelpSessionListView — FE-B16
 *
 * Location: apps/web/src/features/help/components/HelpSessionListView.tsx
 *
 * Session list secondary view inside the HelpDrawer.
 * Shows sessions grouped by recency: Today / Last 7 days / Older.
 * Includes delete confirmation dialog and anonymization transparency footer.
 */

"use client";

import React, { useState } from "react";
import { useHelpSessions } from "../hooks/useHelpSessions";
import { useDeleteHelpSession } from "../hooks/useDeleteHelpSession";
import { HelpSessionListItem } from "./HelpSessionListItem";

interface HelpSessionListViewProps {
  onSelectSession: (sessionId: string) => void;
}

export function HelpSessionListView({
  onSelectSession,
}: HelpSessionListViewProps) {
  const {
    groups,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useHelpSessions();
  const deleteMutation = useDeleteHelpSession();
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const handleDeleteConfirm = () => {
    if (pendingDeleteId) {
      deleteMutation.mutate(pendingDeleteId);
      setPendingDeleteId(null);
    }
  };

  if (isLoading) {
    return (
      <div
        className="flex-1 flex items-center justify-center p-4"
        data-testid="help-sessions-loading"
      >
        <span className="text-xs text-neutral-400">Loading sessions…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="flex-1 flex flex-col items-center justify-center p-4 text-center"
        data-testid="help-sessions-error"
      >
        <p className="text-sm text-neutral-600">
          Something went wrong loading your conversations.
        </p>
        <button
          type="button"
          className="mt-2 text-xs text-brand-600 underline"
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <div
        className="flex-1 flex flex-col items-center justify-center p-4 text-center"
        data-testid="help-sessions-empty"
      >
        <p className="text-sm text-neutral-500">No conversations yet.</p>
        <p className="text-xs text-neutral-400 mt-1">
          Start a chat to get help from Pilot AI.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full" data-testid="help-session-list">
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            {/* Group header */}
            <div className="px-3 py-1">
              <span className="text-neutral-500 text-xs font-medium uppercase tracking-wide">
                {group.label}
              </span>
            </div>

            {/* Sessions in group */}
            {group.sessions.map((session) => (
              <HelpSessionListItem
                key={session.session_id}
                session={session}
                onSelect={onSelectSession}
                onDelete={setPendingDeleteId}
              />
            ))}
          </div>
        ))}

        {/* Load more */}
        {hasNextPage && (
          <button
            type="button"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            className="w-full text-xs text-brand-600 underline py-2 disabled:opacity-50"
          >
            {isFetchingNextPage ? "Loading…" : "Load more"}
          </button>
        )}
      </div>

      {/* Delete confirmation dialog */}
      {pendingDeleteId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/20"
          data-testid="help-delete-confirm-dialog"
        >
          <div className="bg-white rounded-xl shadow-lg p-5 max-w-xs w-full mx-4">
            <p className="text-sm font-medium text-neutral-800 mb-1">
              Delete conversation?
            </p>
            <p className="text-xs text-neutral-500 mb-4">
              This conversation will be deleted and can&apos;t be recovered.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => setPendingDeleteId(null)}
                className="px-3 py-1.5 text-xs text-neutral-600 hover:bg-neutral-50 rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                className="px-3 py-1.5 text-xs font-medium text-white bg-alert-600 hover:bg-alert-700 rounded-md transition-colors"
                data-testid="help-delete-confirm-btn"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
