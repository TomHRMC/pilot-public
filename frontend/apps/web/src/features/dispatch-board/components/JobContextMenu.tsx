/**
 * JobContextMenu — Shared right-click context menu for dispatch board job cards
 *
 * Location: apps/web/src/features/dispatch-board/components/JobContextMenu.tsx
 *
 * Extracted from DispatchWeekView's inline right-click menu pattern.
 * Rendered ONCE in DispatchBoardPage — not inside each row component.
 * Closes on: Escape key, click outside, scroll.
 *
 * Per DISPATCH-B1 UI spec §Surface 5
 */

"use client";

import React, { useEffect, useRef } from "react";
import {
  ArrowTopRightOnSquareIcon,
  AdjustmentsHorizontalIcon,
} from "@heroicons/react/24/outline";
import type { ScheduledJob } from "./DispatchBoardLanes";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface JobContextMenuState {
  x: number;
  y: number;
  job: ScheduledJob;
}

export interface JobContextMenuProps {
  state: JobContextMenuState | null;
  onClose: () => void;
  onViewJob: (job: ScheduledJob) => void;
  onJobProperties: (job: ScheduledJob) => void;
}

// ─── JobContextMenu ───────────────────────────────────────────────────────────

/**
 * JobContextMenu
 *
 * Fixed-position right-click menu. Returns null when state is null.
 * Mounts at (state.x, state.y) in viewport coordinates.
 */
export function JobContextMenu({
  state,
  onClose,
  onViewJob,
  onJobProperties,
}: JobContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on Escape key
  useEffect(() => {
    if (!state) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [state, onClose]);

  // Close on click outside
  useEffect(() => {
    if (!state) return;

    function handleMouseDown(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [state, onClose]);

  // Close on scroll
  useEffect(() => {
    if (!state) return;
    document.addEventListener("scroll", onClose, { capture: true });
    return () =>
      document.removeEventListener("scroll", onClose, { capture: true });
  }, [state, onClose]);

  // Focus first item when menu opens
  useEffect(() => {
    if (!state) return;
    const firstItem =
      menuRef.current?.querySelector<HTMLButtonElement>('[role="menuitem"]');
    firstItem?.focus();
  }, [state]);

  if (!state) return null;

  return (
    <div
      ref={menuRef}
      role="menu"
      aria-label="Job options"
      style={{
        position: "fixed",
        top: state.y,
        left: state.x,
        zIndex: 50,
      }}
      className="w-44 bg-white border border-neutral-200 shadow-lg rounded-md py-1"
    >
      {/* View Job */}
      <button
        type="button"
        role="menuitem"
        className="w-full text-left px-3 py-1.5 text-sm text-neutral-700 hover:bg-brand-50 hover:text-brand-700 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-600 flex items-center"
        onClick={() => {
          onClose();
          onViewJob(state.job);
        }}
      >
        <ArrowTopRightOnSquareIcon
          className="w-4 h-4 mr-2 flex-shrink-0"
          aria-hidden="true"
        />
        View Job
      </button>

      {/* Job Properties */}
      <button
        type="button"
        role="menuitem"
        className="w-full text-left px-3 py-1.5 text-sm text-neutral-700 hover:bg-brand-50 hover:text-brand-700 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-600 flex items-center"
        onClick={() => {
          onClose();
          onJobProperties(state.job);
        }}
      >
        <AdjustmentsHorizontalIcon
          className="w-4 h-4 mr-2 flex-shrink-0"
          aria-hidden="true"
        />
        Job Properties
      </button>
    </div>
  );
}
