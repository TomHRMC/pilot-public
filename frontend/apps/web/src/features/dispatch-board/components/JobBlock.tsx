/**
 * JobBlock — Shared draggable job card for dispatch board views
 *
 * Location: apps/web/src/features/dispatch-board/components/JobBlock.tsx
 *
 * Extracted from DispatchBoardLanes.tsx so both DispatchBoardLanes and
 * DispatchGridDayView can import the same component. No visual changes.
 *
 * Added: onContextMenu prop for right-click → JobContextMenu.
 *
 * Backward-compat exports for deprecated DispatchGrid/DispatchGridColumn:
 *   - JobBlock (alias for DraggableJobBlock, note: not the react-dnd variant)
 *   - JOB_BLOCK_DND_TYPE (legacy constant)
 *   - JobBlockDragItem (legacy type)
 *
 * Per DISPATCH-B1 design doc §I / UI spec §Surface 1 §Implementation Notes §3
 */

"use client";

import React from "react";
import { useDraggable } from "@dnd-kit/core";
import type { ScheduledJob } from "./DispatchBoardLanes";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DraggableJobBlockProps {
  job: ScheduledJob;
  left: number;
  width: number;
  onClick: (job: ScheduledJob) => void;
  /** DISPATCH-B1: right-click handler → JobContextMenu */
  onContextMenu?: (e: React.MouseEvent, job: ScheduledJob) => void;
  /**
   * DISPATCH-B1.25: 'primary' (default) = draggable, 'commitment' = read-only chip.
   * Commitment variant: muted style, cursor-default, no @dnd-kit drag listeners.
   * Role badge rendered from job.assignment_role.
   */
  variant?: "primary" | "commitment";
}

// ─── Status color map ─────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-neutral-50 border-neutral-300 text-neutral-600",
  scheduled: "bg-brand-50 border-brand-300 text-brand-700",
  in_progress: "bg-alert-50 border-alert-300 text-alert-700",
  completed: "bg-margin-50 border-margin-300 text-margin-700",
  cancelled: "bg-fault-50 border-fault-300 text-fault-600",
};

// ─── DraggableJobBlock ────────────────────────────────────────────────────────

/**
 * DraggableJobBlock
 *
 * Absolutely-positioned card for a scheduled job on the dispatch board grid.
 * Used by both DispatchBoardLanes (lane-mode) and DispatchGridDayView (tech-mode).
 * Positioning (left, width) is computed by the parent and passed as props.
 *
 * Left-click  → onClick (opens JobPropertiesPanel)
 * Right-click → onContextMenu (opens JobContextMenu)
 * Drag ≥8px   → @dnd-kit DragOverlay activates (parent DndContext handles this)
 *
 * DISPATCH-B1.25: variant="commitment" — read-only chip, no drag, role badge.
 * useDraggable is always called (hooks can't be conditional) but listeners/attributes
 * are only applied when variant === 'primary'.
 */
export function DraggableJobBlock({
  job,
  left,
  width,
  onClick,
  onContextMenu,
  variant = "primary",
}: DraggableJobBlockProps) {
  // Always call useDraggable — hooks must not be conditional.
  // For commitment variant we simply omit the returned listeners/attributes.
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `${variant === "commitment" ? "commitment-" : ""}${job.id}`,
    data: { job },
    disabled: variant === "commitment",
  });

  const isCommitment = variant === "commitment";

  const colorCls = isCommitment
    ? "bg-neutral-50 border-dashed border-neutral-300 text-neutral-500"
    : (STATUS_COLORS[job.status] ??
      "bg-neutral-50 border-neutral-300 text-neutral-600");

  // label: prefer title (forward-compat) then job_number, then fallback
  const primaryLabel = (job as unknown as { job_number?: string }).job_number
    ? ((job as unknown as { title?: string | null; job_number: string })
        .title ?? (job as unknown as { job_number: string }).job_number)
    : job.title;

  // DISPATCH-B1.25: capitalize assignment_role for badge display ("helper" → "Helper")
  const roleBadge =
    isCommitment &&
    (job as unknown as { assignment_role?: string | null }).assignment_role
      ? (() => {
          const role = (job as unknown as { assignment_role: string })
            .assignment_role;
          return role.charAt(0).toUpperCase() + role.slice(1);
        })()
      : null;

  return (
    <div
      ref={setNodeRef}
      // Only attach drag listeners/attributes for primary blocks
      {...(isCommitment ? {} : attributes)}
      {...(isCommitment ? {} : listeners)}
      role="button"
      tabIndex={0}
      aria-label={`Job: ${primaryLabel}${isCommitment ? " (commitment)" : ""}`}
      onClick={(e) => {
        e.stopPropagation();
        onClick(job);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.stopPropagation();
          onClick(job);
        }
      }}
      onContextMenu={
        onContextMenu
          ? (e) => {
              e.preventDefault();
              onContextMenu(e, job);
            }
          : undefined
      }
      style={{
        position: "absolute",
        left: `${left}px`,
        width: `${Math.max(width - 4, 20)}px`,
        top: "4px",
        bottom: "4px",
      }}
      className={`
        border rounded px-2 py-1 select-none overflow-hidden relative
        text-caption font-medium
        transition-opacity
        ${isCommitment ? "cursor-default opacity-90" : "cursor-grab"}
        ${colorCls}
        ${!isCommitment && isDragging ? "opacity-30" : ""}
        focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:outline-none
      `}
    >
      <p className="truncate text-caption font-semibold leading-tight">
        {primaryLabel}
      </p>
      {job.customer_name && (
        <p className="truncate text-caption opacity-75">{job.customer_name}</p>
      )}
      {/* DISPATCH-B1.25: role badge for commitment chips */}
      {roleBadge && (
        <span
          data-testid="role-badge"
          className="absolute top-0.5 right-0.5 bg-neutral-100 text-neutral-600 rounded px-1 text-caption leading-none"
        >
          {roleBadge}
        </span>
      )}
    </div>
  );
}

// ─── Backward-compat exports for deprecated DispatchGrid / DispatchGridColumn ─
// These files are @deprecated but still compile.
// Exporting stubs here avoids breaking the build until they are deleted.

/**
 * @deprecated — Use DraggableJobBlock. Legacy react-dnd JobBlock alias.
 * DispatchGrid.tsx / DispatchGridColumn.tsx import this.
 */
export const JobBlock = DraggableJobBlock;

/** @deprecated — Legacy react-dnd drag type constant. No-op in @dnd-kit world. */
export const JOB_BLOCK_DND_TYPE = "JOB_BLOCK" as const;

/** @deprecated — Legacy react-dnd drag item type used by DispatchGrid/Column. */
export interface JobBlockDragItem {
  jobId: string;
  techId: string | null;
  scheduledStartAt: string;
  scheduledEndAt: string;
}
