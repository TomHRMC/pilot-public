"use client";
/**
 * TechAssignmentSection — Multi-tech assignment UI used on both
 * dispatch board Properties panel and Job Detail page.
 *
 * Location: apps/web/src/features/jobs/components/TechAssignmentSection.tsx
 *
 * Features:
 *   - Colored avatar list with initials
 *   - "Lead" badge for primary assignment
 *   - ✕ remove button (RoleGate: schedule.manage)
 *   - "+ Add technician" inline dropdown (RoleGate: schedule.manage)
 *   - Role auto-computation: first addition = primary, subsequent = helper
 *   - Re-fetch (not optimistic update) after every add/remove
 *
 * PLP-FIX-10 (INV-BUG-10a):
 *   - Section gated on schedule.view_all (hidden for accountant who lacks it)
 *   - Assignments-query 403 → render null (defense-in-depth; 403 ≠ 5xx)
 *   - ErrorState reserved for non-403 failures only
 *
 * Added by: UI-FIX-2B React Engineer
 */

import React from "react";
import { LoadingState, ErrorState, RoleGate } from "@pilot/ui";
import { useHasPermission } from "@pilot/ui/role-gate";
import { isAxiosError } from "@pilot/shared-api";
import { useJobAssignments } from "../hooks/useJobAssignments";
import { useAddJobAssignment } from "../hooks/useAddJobAssignment";
import { useRemoveJobAssignment } from "../hooks/useRemoveJobAssignment";
import { useTenantUsers } from "../../users/hooks/useTenantUsers";

interface TechAssignmentSectionProps {
  jobId: string;
  /** Called after any add or remove completes — parent can re-fetch job data */
  onAssignmentChanged?: () => void;
}

export function TechAssignmentSection({
  jobId,
  onAssignmentChanged,
}: TechAssignmentSectionProps) {
  // PLP-FIX-10 (INV-BUG-10a): Section-level gate on schedule.view_all.
  // Accountant lacks this grant → entire section hidden (not ErrorState).
  // office_staff holds both view_all + manage → full read/write.
  const canViewSchedule = useHasPermission("schedule.view_all");

  const {
    data: assignments = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useJobAssignments(jobId);

  // PLP-FIX-10 (INV-BUG-10a): Defense-in-depth on the assignments query.
  // GET /jobs/{id}/assignments is schedule.view_all-gated. A 403 here means
  // the user lacks the grant — render null, never ErrorState. ErrorState
  // is reserved for genuine 5xx failures only (403 ≠ 5xx per FIX-9 §G.7).
  const assignmentsForbidden =
    isError && isAxiosError(error) && error.response?.status === 403;

  // PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): accountant's *.view
  // wildcard covers users.view (suffix matcher; BE gate roles.py:292-294),
  // so useTenantUsers 200s for accountant post-grant. The usersForbidden
  // defense below guards any future role lacking users.view — when a 403
  // occurs, assignments render read-only (no picker, no ErrorState).
  // ErrorState is reserved for genuine 5xx on the assignments query only.
  const {
    data: allUsers = [],
    isError: usersError,
    error: usersErr,
  } = useTenantUsers();
  const usersForbidden =
    usersError && isAxiosError(usersErr) && usersErr.response?.status === 403;

  const addMutation = useAddJobAssignment(jobId);
  const removeMutation = useRemoveJobAssignment(jobId);

  // Already-assigned user IDs (for filtering picker)
  const assignedUserIds = new Set(
    assignments.map((a: { user_id: string }) => a.user_id),
  );

  // Available users = active users not already assigned
  const availableUsers = allUsers.filter(
    (u) => u.is_active && !assignedUserIds.has(u.user_id),
  );

  // Role auto-computation: first tech = primary, subsequent = helper
  const nextRole = assignments.length === 0 ? "primary" : "helper";

  const handleAdd = async (userId: string) => {
    if (!userId) return;
    await addMutation.mutateAsync({ user_id: userId, role: nextRole });
    await refetch();
    onAssignmentChanged?.();
  };

  const handleRemove = async (assignmentId: string) => {
    await removeMutation.mutateAsync(assignmentId);
    await refetch();
    onAssignmentChanged?.();
  };

  // PLP-FIX-10: Section hidden for roles lacking schedule.view_all.
  // Hooks above run unconditionally (Rules of Hooks); early return precedes JSX.
  if (!canViewSchedule) return null;

  if (isLoading)
    return <LoadingState type="inline" label="Loading technicians…" />;

  // PLP-FIX-10: 403 on assignments → render null (defense-in-depth).
  if (assignmentsForbidden) return null;

  if (isError)
    return (
      <ErrorState
        type="server"
        description="Failed to load technicians"
        onRetry={() => refetch()}
      />
    );

  return (
    <div
      className="space-y-2"
      data-testid="tech-assignment-section"
      data-users-forbidden={usersForbidden || undefined}
    >
      {assignments.length === 0 && (
        <p className="text-caption text-neutral-400 italic">
          No technician assigned
        </p>
      )}

      {assignments.map(
        (assignment: {
          id: string;
          user_id: string;
          role: "primary" | "helper";
        }) => {
          const user = allUsers.find((u) => u.user_id === assignment.user_id);
          const isPrimary = assignment.role === "primary";
          // display_color comes from the API — gray-500 hex is the fallback when unset
          // eslint-disable-next-line pilot/no-hardcoded-design-values
          const color = user?.display_color ?? "#6B7280";
          const name = user?.display_name ?? assignment.user_id;
          const initials = name
            .split(" ")
            .map((w: string) => w[0])
            .join("")
            .slice(0, 2)
            .toUpperCase();

          return (
            <div
              key={assignment.id}
              className="flex items-center gap-2"
              data-testid={`tech-row-${assignment.id}`}
            >
              {/* Colored avatar */}
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-white text-caption font-semibold"
                style={{ backgroundColor: color }}
                aria-hidden="true"
              >
                {initials}
              </div>

              <span className="text-caption text-neutral-800 flex-1">
                {name}
              </span>

              {isPrimary && (
                <span
                  className="text-caption text-brand-600 font-medium"
                  data-testid={`lead-badge-${assignment.id}`}
                >
                  Lead
                </span>
              )}

              <RoleGate permission="schedule.manage">
                <button
                  type="button"
                  onClick={() => handleRemove(assignment.id)}
                  className="text-neutral-400 hover:text-fault-600 text-caption px-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded transition-colors"
                  aria-label={`Remove ${name}`}
                  disabled={removeMutation.isPending}
                  data-testid={`remove-btn-${assignment.id}`}
                >
                  ✕
                </button>
              </RoleGate>
            </div>
          );
        },
      )}

      <RoleGate permission="schedule.manage">
        {availableUsers.length > 0 && (
          <div className="mt-2">
            <select
              className="text-caption border border-neutral-200 rounded px-2 py-1 text-neutral-600 w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 transition-colors"
              value=""
              onChange={(e) => {
                handleAdd(e.target.value);
              }}
              disabled={addMutation.isPending}
              aria-label="Add technician"
              data-testid="add-tech-select"
            >
              <option value="">+ Add technician</option>
              {availableUsers.map((u) => (
                <option key={u.user_id} value={u.user_id}>
                  {u.display_name}
                </option>
              ))}
            </select>
          </div>
        )}
      </RoleGate>
    </div>
  );
}
