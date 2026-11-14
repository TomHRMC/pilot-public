/**
 * ActiveSessionsList — FE-B12
 *
 * Location: apps/web/src/features/account-settings/components/ActiveSessionsList.tsx
 *
 * RULE: Current session row has margin-100 "current" pill; cannot be revoked.
 * RULE: Optimistic remove on revoke; error → row reappears.
 * RULE: "Revoke all other" uses RevertToDefaultDialog for confirmation.
 *
 * Design doc Section H token audit:
 * - Current device badge: bg-margin-100 text-margin-700 text-xs
 * - Revoke all button: text-fault-600
 * - Session revoke hover: text-fault-600 hover:bg-fault-50
 */

"use client";

import React, { useState } from "react";
import { useActiveSessions } from "../hooks/useActiveSessions";
import type { ActiveSession } from "../types";

function formatRelativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMinutes = Math.floor(diffMs / 60_000);
  if (diffMinutes < 1) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
}

function SessionRow({
  session,
  onRevoke,
  isRevoking,
}: {
  session: ActiveSession;
  onRevoke: (id: string) => void;
  isRevoking: boolean;
}) {
  return (
    <div
      className="flex items-start justify-between gap-4 py-4 border-b border-neutral-100 last:border-b-0"
      data-testid={`session-row-${session.session_id}`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-neutral-800">
            {session.display_label}
          </span>
          {/* Current device badge — design doc Section H token */}
          {session.is_current && (
            <span
              className="rounded-full bg-margin-100 px-2 py-0.5 text-xs font-medium text-margin-700"
              data-testid="current-session-badge"
            >
              This device
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-neutral-500">
          {session.geolocation ?? "Unknown location"} &middot;{" "}
          {session.ip_address}
        </p>
        <p className="mt-0.5 text-xs text-neutral-400">
          Last active: {formatRelativeTime(session.last_active_at)} &middot;
          Logged in: {formatRelativeTime(session.created_at)}
        </p>
      </div>

      {/* Revoke button — absent for current session */}
      {!session.is_current && (
        <button
          type="button"
          onClick={() => onRevoke(session.session_id)}
          disabled={isRevoking}
          className="flex-shrink-0 rounded-md px-3 py-1.5 text-xs font-medium text-fault-600 hover:bg-fault-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-fault-600 focus-visible:ring-offset-1 disabled:opacity-50 transition-colors"
          data-testid={`revoke-session-${session.session_id}`}
          aria-label={`Revoke ${session.display_label} session`}
        >
          Revoke
        </button>
      )}
    </div>
  );
}

export function ActiveSessionsList() {
  const {
    sessions,
    isLoading,
    isError,
    revokeSession,
    revokeOthers,
    isRevoking,
    revokeError,
  } = useActiveSessions();

  const [showRevokeAllDialog, setShowRevokeAllDialog] = useState(false);
  const otherSessionCount = sessions.filter((s) => !s.is_current).length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin h-5 w-5 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-md bg-fault-50 border border-fault-200 p-4 text-sm text-fault-700">
        Failed to load sessions.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4" data-testid="active-sessions-list">
      {revokeError && (
        <div
          role="alert"
          className="rounded-md bg-fault-50 border border-fault-200 p-3 text-sm text-fault-700"
        >
          Couldn&apos;t revoke session &mdash; try again.
        </div>
      )}

      <div className="rounded-lg border border-neutral-200 divide-y divide-neutral-100 overflow-hidden">
        {sessions.map((session) => (
          <SessionRow
            key={session.session_id}
            session={session}
            onRevoke={revokeSession}
            isRevoking={isRevoking}
          />
        ))}
      </div>

      {/* Revoke all other sessions */}
      {otherSessionCount > 0 && (
        <button
          type="button"
          onClick={() => setShowRevokeAllDialog(true)}
          disabled={isRevoking}
          className="self-start text-sm font-medium text-fault-600 hover:text-fault-800 focus:outline-none focus:underline disabled:opacity-50"
          data-testid="revoke-all-others"
        >
          Revoke all other sessions ({otherSessionCount})
        </button>
      )}

      {/* Revoke all confirmation inline dialog */}
      {showRevokeAllDialog && (
        <div
          role="dialog"
          aria-modal="false"
          aria-label="Confirm revoke all sessions"
          className="rounded-md border border-neutral-200 bg-neutral-50 p-4"
          data-testid="revoke-all-dialog"
        >
          <p className="text-sm text-neutral-800 font-medium">
            Revoke all other sessions?
          </p>
          <p className="mt-1 text-sm text-neutral-500">
            You&apos;ll be signed out on all {otherSessionCount} other device
            {otherSessionCount === 1 ? "" : "s"}. You&apos;ll stay signed in
            here.
          </p>
          <div className="mt-3 flex items-center gap-3">
            <button
              type="button"
              onClick={async () => {
                await revokeOthers();
                setShowRevokeAllDialog(false);
              }}
              disabled={isRevoking}
              className="rounded-md bg-fault-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-fault-800 focus:outline-none disabled:opacity-50"
              data-testid="confirm-revoke-all"
            >
              {isRevoking ? "Revoking…" : "Revoke all"}
            </button>
            <button
              type="button"
              onClick={() => setShowRevokeAllDialog(false)}
              className="text-xs text-neutral-500 hover:text-neutral-700 focus:outline-none focus:underline"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
