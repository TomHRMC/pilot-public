/**
 * TeamSettingsPage — TEAM-INVITE-1
 *
 * Location: apps/web/src/features/settings/components/TeamSettingsPage.tsx
 *
 * Lists all tenant users with role badges; owner can reassign roles.
 * Owner can invite new team members via InviteMemberDialog.
 * Pending invites shown below the members table via PendingInvitesSection.
 * Route: /settings/team
 *
 * TEAM-INVITE-1 changes:
 *   - Replaced P0 "coming soon" InviteDialog with production InviteMemberDialog
 *   - Re-gated manage affordances from "settings.manage" to "users.manage"
 *   - Added PendingInvitesSection below the members table
 */

"use client";

import React, { useState } from "react";
import { RoleGate, useRequiresPermission } from "@pilot/ui/role-gate";
import { useTeamUsers } from "../hooks/useTeamUsers";
import { InviteMemberDialog } from "./InviteMemberDialog";
import { PendingInvitesSection } from "./PendingInvitesSection";

const ROLE_OPTIONS = [
  { value: "owner", label: "Owner" },
  { value: "office_staff", label: "Office Staff" },
  { value: "technician", label: "Technician" },
  { value: "accountant", label: "Accountant" },
];

export function RoleBadge({ roleCode }: { roleCode: string }) {
  const labels: Record<string, string> = {
    owner: "Owner",
    office_staff: "Office Staff",
    technician: "Technician",
    accountant: "Accountant",
  };
  const colors: Record<string, string> = {
    owner: "bg-brand-100 text-brand-700",
    office_staff: "bg-neutral-100 text-neutral-700",
    technician: "bg-success-100 text-success-700",
    accountant: "bg-alert-100 text-alert-700",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[roleCode] ?? "bg-neutral-100 text-neutral-600"}`}
    >
      {labels[roleCode] ?? roleCode}
    </span>
  );
}

function TeamContent() {
  const { users, isLoading, isError, assignRole, isAssigning } = useTeamUsers();
  const canManage = useRequiresPermission("users.manage");
  const [showInviteDialog, setShowInviteDialog] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin h-6 w-6 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-fault-200 bg-fault-50 p-6 text-sm text-fault-700">
        Could not load team members. Please refresh the page.
      </div>
    );
  }

  return (
    <>
      {showInviteDialog && (
        <InviteMemberDialog onClose={() => setShowInviteDialog(false)} />
      )}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Team</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Manage your team members and their roles.
          </p>
        </div>
        {canManage && (
          <button
            onClick={() => setShowInviteDialog(true)}
            className="rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
            data-testid="invite-team-member-button"
          >
            Invite team member
          </button>
        )}
      </div>

      {/* PLP-FIX-10 (INV-BUG-15): content-sized columns + horizontal scroll.
          Dropped overflow-hidden from the border wrapper; the scroll region
          carries the rounded border. whitespace-nowrap on cells that must not
          wrap. Full email values render at desktop width; h-scroll on overflow. */}
      <div className="rounded-md border border-neutral-200">
        <div
          className="overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Team members table, scrollable"
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
                  Joined
                </th>
                {canManage && (
                  <th className="text-left px-4 py-3 font-medium text-neutral-700 whitespace-nowrap">
                    Change Role
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {users.map((user, idx) => (
                <tr
                  key={user.userId}
                  className={idx % 2 === 0 ? "bg-white" : "bg-neutral-50"}
                >
                  <td className="px-4 py-3 text-neutral-900 whitespace-nowrap">
                    {user.email}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <RoleBadge roleCode={user.roleCode} />
                  </td>
                  <td className="px-4 py-3 text-neutral-500 whitespace-nowrap">
                    {user.joinedAt
                      ? new Date(user.joinedAt).toLocaleDateString()
                      : "—"}
                  </td>
                  {canManage && (
                    <td className="px-4 py-3 whitespace-nowrap">
                      <select
                        value={user.roleCode}
                        disabled={isAssigning}
                        onChange={(e) =>
                          void assignRole(user.userId, e.target.value)
                        }
                        aria-label={`Change role for ${user.email}`}
                        className="rounded border border-neutral-300 bg-white px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                      >
                        {ROLE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {users.length === 0 && (
          <p className="text-center py-8 text-sm text-neutral-500">
            No team members found.
          </p>
        )}
      </div>

      {canManage && <PendingInvitesSection />}
    </>
  );
}

export function TeamSettingsPage() {
  // PLP-FIX-7: Outer gate on users.view — office_staff sees Team (read-only).
  // Manage affordances (invite button, role reassign) gated on users.manage
  // inside TeamContent via canManage. Previously gated on users.manage which
  // hid the entire page for office_staff (over-hide).
  return (
    <div className="p-6 max-w-4xl">
      <RoleGate permission="users.view">
        <TeamContent />
      </RoleGate>
    </div>
  );
}
