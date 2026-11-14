/**
 * PendingInvitesSection — TEAM-INVITE-1
 *
 * Location: apps/web/src/features/settings/components/PendingInvitesSection.tsx
 *
 * Renders below the members table on /settings/team. Shows all invites
 * (pending, expired, accepted, revoked) with:
 *  - email, role badge, sent date, expiry countdown, status chip
 *  - Resend (one-click) + Revoke (confirm step) actions
 *  - Optimistic mutations via useOptimisticMutation + PendingBadge
 *  - Skeleton rows while loading, ErrorState with retry, hidden when empty
 *
 * WCAG 2.2 AA: text-labeled chips (never color-only), ≥24px targets,
 * confirm step for destructive Revoke action.
 */

"use client";

import React, { useState } from "react";
import { useTeamInvites } from "../hooks/useTeamInvites";
import { useResendInvite } from "../hooks/useResendInvite";
import { useRevokeInvite } from "../hooks/useRevokeInvite";
import { RoleBadge } from "./TeamSettingsPage";

function StatusChip({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-brand-100 text-brand-700",
    expired: "bg-neutral-100 text-neutral-500",
    accepted: "bg-success-100 text-success-700",
    revoked: "bg-fault-100 text-fault-700",
  };
  const labels: Record<string, string> = {
    pending: "Pending",
    expired: "Expired",
    accepted: "Accepted",
    revoked: "Revoked",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[status] ?? "bg-neutral-100 text-neutral-600"}`}
    >
      {labels[status] ?? status}
    </span>
  );
}

function daysUntil(isoDate: string): number {
  const now = new Date();
  const expiry = new Date(isoDate);
  const diff = expiry.getTime() - now.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function SkeletonRow() {
  return (
    <tr className="bg-white">
      <td className="px-4 py-3">
        <div className="h-4 w-40 rounded bg-neutral-200 animate-pulse" />
      </td>
      <td className="px-4 py-3">
        <div className="h-5 w-20 rounded bg-neutral-200 animate-pulse" />
      </td>
      <td className="px-4 py-3">
        <div className="h-4 w-24 rounded bg-neutral-200 animate-pulse" />
      </td>
      <td className="px-4 py-3">
        <div className="h-4 w-16 rounded bg-neutral-200 animate-pulse" />
      </td>
      <td className="px-4 py-3">
        <div className="h-5 w-16 rounded bg-neutral-200 animate-pulse" />
      </td>
      <td className="px-4 py-3">
        <div className="h-8 w-32 rounded bg-neutral-200 animate-pulse" />
      </td>
    </tr>
  );
}

export function PendingInvitesSection() {
  const { data: invites, isPending, isError, refetch } = useTeamInvites();
  const resendInvite = useResendInvite();
  const revokeInvite = useRevokeInvite();
  const [revokeConfirmId, setRevokeConfirmId] = useState<string | null>(null);
  const [pendingActionId, setPendingActionId] = useState<string | null>(null);

  async function handleResend(inviteId: string) {
    setPendingActionId(inviteId);
    try {
      await resendInvite.mutateAsync(inviteId);
    } finally {
      setPendingActionId(null);
    }
  }

  async function handleRevoke(inviteId: string) {
    setPendingActionId(inviteId);
    try {
      await revokeInvite.mutateAsync(inviteId);
      setRevokeConfirmId(null);
    } finally {
      setPendingActionId(null);
    }
  }

  // PLP-FIX-7: Filter out accepted invites — they leave the pending list.
  // Revoked/expired rows keep rendering with their chips (designed affordance).
  const visibleInvites = invites?.filter((i) => i.status !== "accepted");

  // Hidden entirely when empty (no empty-table chrome) — also hides when
  // all invites have been accepted (visibleInvites is empty).
  if (
    !isPending &&
    !isError &&
    (!visibleInvites || visibleInvites.length === 0)
  ) {
    return null;
  }

  return (
    <div className="mt-8" data-testid="pending-invites-section">
      <h2 className="text-lg font-semibold text-neutral-900 mb-4">
        Pending Invites
      </h2>

      {isError ? (
        <div className="rounded-lg border border-fault-200 bg-fault-50 p-6 text-sm text-fault-700">
          Could not load invites.{" "}
          <button
            onClick={() => void refetch()}
            className="underline font-medium hover:text-fault-800"
          >
            Try again
          </button>
        </div>
      ) : (
        <div className="rounded-md border border-neutral-200">
          {/* PLP-FIX-10 (INV-BUG-15): dropped table-fixed; content-sized columns
              + horizontal scroll wrapper. Full email values render at desktop
              width; h-scroll on overflow. truncate+tooltip is the in-scroll
              fallback for extreme widths. Resend + Revoke always fully visible. */}
          <div
            className="overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Pending invites table, scrollable"
          >
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-neutral-50 border-b border-neutral-200">
                  <th className="text-left px-4 py-3 font-medium text-neutral-700 whitespace-nowrap">
                    Email
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-neutral-700 whitespace-nowrap">
                    Role
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-neutral-700 whitespace-nowrap">
                    Sent
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-neutral-700 whitespace-nowrap">
                    Expires
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-neutral-700 whitespace-nowrap">
                    Status
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-neutral-700 w-48 whitespace-nowrap">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {isPending ? (
                  <>
                    <SkeletonRow />
                    <SkeletonRow />
                    <SkeletonRow />
                  </>
                ) : (
                  visibleInvites?.map((invite, idx) => {
                    const days = daysUntil(invite.expires_at);
                    const isExpiringSoon = days < 2 && days >= 0;
                    const isPendingAction = pendingActionId === invite.id;
                    const isRevokeConfirm = revokeConfirmId === invite.id;

                    return (
                      <tr
                        key={invite.id}
                        className={idx % 2 === 0 ? "bg-white" : "bg-neutral-50"}
                        data-testid={`invite-row-${invite.id}`}
                      >
                        {/* PLP-FIX-10: truncate+tooltip as in-scroll fallback.
                            At desktop width the full email renders; only at
                            extreme narrow widths does it ellipsis inside the
                            scroll area. max-w-prose caps the cell width. */}
                        <td className="px-4 py-3 text-neutral-900 max-w-prose">
                          <span className="block truncate" title={invite.email}>
                            {invite.email}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <RoleBadge
                            roleCode={invite.role_code ?? "technician"}
                          />
                        </td>
                        <td className="px-4 py-3 text-neutral-500 whitespace-nowrap">
                          {new Date(invite.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-neutral-500 whitespace-nowrap">
                          {invite.status === "accepted" ? (
                            "—"
                          ) : days < 0 ? (
                            "Expired"
                          ) : (
                            <span
                              className={
                                isExpiringSoon
                                  ? "text-alert-600 font-medium"
                                  : ""
                              }
                            >
                              {days} day{days !== 1 ? "s" : ""}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <StatusChip status={invite.status} />
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {isRevokeConfirm ? (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-neutral-600">
                                Confirm?
                              </span>
                              <button
                                onClick={() => void handleRevoke(invite.id)}
                                disabled={isPendingAction}
                                className="rounded-md bg-fault-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-fault-700 focus:outline-none focus:ring-2 focus:ring-fault-500 disabled:opacity-50"
                                data-testid={`revoke-confirm-${invite.id}`}
                              >
                                {isPendingAction ? "Revoking…" : "Yes, revoke"}
                              </button>
                              <button
                                onClick={() => setRevokeConfirmId(null)}
                                disabled={isPendingAction}
                                className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              {invite.status === "pending" && (
                                <button
                                  onClick={() => void handleResend(invite.id)}
                                  disabled={isPendingAction}
                                  className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                                  data-testid={`resend-${invite.id}`}
                                >
                                  {isPendingAction ? "…" : "Resend"}
                                </button>
                              )}
                              {(invite.status === "pending" ||
                                invite.status === "expired") && (
                                <button
                                  onClick={() => setRevokeConfirmId(invite.id)}
                                  disabled={isPendingAction}
                                  className="rounded-md border border-fault-300 px-3 py-1.5 text-xs font-medium text-fault-700 hover:bg-fault-50 focus:outline-none focus:ring-2 focus:ring-fault-500 disabled:opacity-50"
                                  data-testid={`revoke-${invite.id}`}
                                >
                                  Revoke
                                </button>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
