/**
 * HelpSessionListItem — FE-B16
 *
 * Location: apps/web/src/features/help/components/HelpSessionListItem.tsx
 *
 * Single session row with title, relative time, outcome badge, and delete action.
 */

"use client";

import React from "react";
import type { HelpSessionSummary } from "../types";

interface HelpSessionListItemProps {
  session: HelpSessionSummary;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
}

function relativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

const OUTCOME_BADGE: Record<string, string> = {
  resolved: "bg-margin-50 text-margin-700",
  escalated: "bg-alert-50 text-alert-700",
  abandoned: "bg-neutral-100 text-neutral-500",
};

export function HelpSessionListItem({
  session,
  onSelect,
  onDelete,
}: HelpSessionListItemProps) {
  return (
    <div
      className="group flex items-start gap-2 px-3 py-2.5 hover:bg-neutral-50 rounded-md cursor-pointer transition-colors"
      data-testid={`help-session-item-${session.session_id}`}
      onClick={() => onSelect(session.session_id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onSelect(session.session_id)}
    >
      {/* Session icon */}
      <span className="mt-0.5 text-neutral-300 text-sm flex-shrink-0">💬</span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-neutral-800 truncate">
          {session.title ?? "Untitled conversation"}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-neutral-400">
            {relativeTime(session.last_activity_at)}
          </span>
          <span className="text-xs text-neutral-300">·</span>
          <span className="text-xs text-neutral-400">
            {session.message_count} messages
          </span>
          {session.outcome && (
            <>
              <span className="text-xs text-neutral-300">·</span>
              <span
                className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${OUTCOME_BADGE[session.outcome] ?? "bg-neutral-100 text-neutral-500"}`}
              >
                {session.outcome}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Delete action (appears on hover) */}
      <button
        type="button"
        aria-label={`Delete conversation: ${session.title ?? "Untitled"}`}
        data-testid={`help-session-delete-${session.session_id}`}
        onClick={(e) => {
          e.stopPropagation();
          onDelete(session.session_id);
        }}
        className="flex-shrink-0 p-1 text-neutral-300 hover:text-alert-500 opacity-0 group-hover:opacity-100 transition-all rounded"
      >
        🗑
      </button>
    </div>
  );
}
