/**
 * TechFilterPopover — "Techs ▾" compact multi-select popover for FilterBar
 *
 * Location: apps/web/src/features/dispatch-board/components/TechFilterPopover.tsx
 *
 * Button trigger + count badge + checkbox panel.
 * Dismissal: outside-click (mousedown) + Escape + scroll-close,
 * reused from JobContextMenu.tsx.
 *
 * All-when-empty semantics: selectedTechIds=[] means all techs visible.
 *
 * DISPATCH-B2 — new component
 * Per batch-dispatch-b2-design.md §H + §F
 */

"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { ChevronDownIcon } from "@heroicons/react/24/outline";
import type { DispatchBoardTech } from "../types-stub";

export interface TechFilterPopoverProps {
  techs: DispatchBoardTech[];
  /** Empty array = all techs visible (empty-array-means-all semantics) */
  selectedTechIds: string[];
  onToggleTech: (id: string) => void;
}

/**
 * TechFilterPopover
 *
 * "Techs ▾" button with optional count badge.
 * Opens a checkbox panel listing each tech with color dot + name.
 * Closes on outside-click / Escape / scroll — same pattern as JobContextMenu.
 */
export function TechFilterPopover({
  techs,
  selectedTechIds,
  onToggleTech,
}: TechFilterPopoverProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, close]);

  // Close on outside mousedown
  useEffect(() => {
    if (!open) return;
    function handleMouseDown(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        close();
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [open, close]);

  // Close on scroll
  useEffect(() => {
    if (!open) return;
    document.addEventListener("scroll", close, { capture: true });
    return () =>
      document.removeEventListener("scroll", close, { capture: true });
  }, [open, close]);

  const badgeCount = selectedTechIds.length;

  return (
    <div ref={containerRef} className="relative">
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        className="inline-flex items-center gap-1 px-2.5 py-1 text-caption font-medium rounded-md border border-neutral-200 text-neutral-700 hover:bg-neutral-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
      >
        Techs
        {badgeCount > 0 && (
          <span className="text-caption text-neutral-500 tabular-nums">
            · {badgeCount}
          </span>
        )}
        <ChevronDownIcon
          className="w-3.5 h-3.5 text-neutral-400"
          aria-hidden="true"
        />
      </button>

      {/* Popover panel */}
      {open && (
        <div
          role="menu"
          className="absolute z-50 mt-1 w-56 rounded-md border border-neutral-200 bg-white shadow-lg p-1"
        >
          {techs.length === 0 && (
            <p className="px-2 py-1.5 text-caption text-neutral-400 italic">
              No techs available
            </p>
          )}
          {techs.map((tech) => {
            // All-when-empty: unchecked only if there are selections AND this id is NOT in them
            const checked =
              selectedTechIds.length === 0 || selectedTechIds.includes(tech.id);

            return (
              <label
                key={tech.id}
                className="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer hover:bg-neutral-50"
                role="menuitem"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggleTech(tech.id)}
                  className="w-3.5 h-3.5 rounded-sm border-neutral-300 text-brand-600 focus:ring-brand-600 focus:ring-offset-0 focus:ring-1 cursor-pointer"
                />
                {/* Data-driven tech color dot — only allowed inline style */}
                {tech.display_color && (
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: tech.display_color }}
                    aria-hidden="true"
                  />
                )}
                <span className="text-caption text-neutral-700 flex-1 truncate">
                  {tech.name}
                </span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
