/**
 * DispatchToolbar — Day/Week/Month tab switcher + date navigation
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx
 *
 * FE-B30: Removed "4day" tab. Now 3 tabs: Day / Week / Month.
 * Added week-specific controls (5-day/7-day toggle, week label).
 * Added month-specific controls (customer/tech chip toggle).
 *
 * Per batch-fe-b4-design.md §A.1.8 §G.5
 * Updated per batch-fe-b30-react-engr-prompt.md §STEP 2
 */

"use client";

import React from "react";
import { useMutationState } from "@tanstack/react-query";
import { InFlightSyncIndicator } from "@pilot/ui/sync-indicator";
import type { DispatchViewTab } from "../store";

interface DispatchToolbarProps {
  viewTab: DispatchViewTab;
  activeDate: string;
  sseConnected: boolean;
  lastBoardFetch: Date | null;
  onViewTabChange: (tab: DispatchViewTab) => void;
  onNavigatePrev: () => void;
  onNavigateNext: () => void;
  onNavigateToToday: () => void;
  /** FE-B15: click-to-detail — caller provides navigation to /schedule#conflicts */
  onResolveConflicts?: () => void;
  // Week-specific controls
  weekDaysToShow?: 5 | 7;
  onWeekDaysToggle?: (days: 5 | 7) => void;
  // Month-specific controls
  chipDisplayMode?: "customer" | "tech";
  onChipDisplayModeToggle?: (mode: "customer" | "tech") => void;
  // DISPATCH-B1: Day-specific Lane|Tech toggle
  layoutMode?: "lane" | "tech";
  onLayoutModeToggle?: (mode: "lane" | "tech") => void;
}

const VIEW_TABS: Array<{ value: DispatchViewTab; label: string }> = [
  { value: "day", label: "Day" },
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
];

/** Get the Monday of the week containing the given date string */
function getMondayOf(dateStr: string): Date {
  const d = new Date(dateStr + "T12:00:00");
  const day = d.getDay(); // 0=Sun, 1=Mon...
  const diff = (day + 6) % 7; // days since Monday
  d.setDate(d.getDate() - diff);
  return d;
}

/** Format week label: "Week of Mon Jul 14 – Fri Jul 18" (5-day) or "Mon Jul 14 – Sun Jul 20" (7-day) */
function formatWeekLabel(dateStr: string, daysToShow: 5 | 7): string {
  const monday = getMondayOf(dateStr);
  const end = new Date(monday);
  end.setDate(monday.getDate() + daysToShow - 1);

  const opts: Intl.DateTimeFormatOptions = {
    weekday: "short",
    month: "short",
    day: "numeric",
  };
  const startLabel = monday.toLocaleDateString("en-US", opts);
  const endLabel = end.toLocaleDateString("en-US", opts);
  return `${startLabel} – ${endLabel}`;
}

function formatDisplayDate(dateStr: string, viewTab: DispatchViewTab): string {
  const date = new Date(dateStr + "T12:00:00");
  if (viewTab === "month") {
    return date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  }
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * PillToggle — small 2-option toggle (5/7 day; customer/tech)
 */
function PillToggle<T extends string | number>({
  options,
  value,
  onChange,
}: {
  options: Array<{ value: T; label: string }>;
  value: T;
  onChange: (val: T) => void;
}) {
  return (
    <div className="bg-neutral-100 rounded-md p-0.5 inline-flex ml-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={[
            "px-2.5 py-1 text-caption font-medium rounded",
            opt.value === value
              ? "bg-white shadow-sm text-neutral-900"
              : "text-neutral-500",
          ].join(" ")}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

const PREV_LABEL: Record<DispatchViewTab, string> = {
  day: "Previous day",
  week: "Previous week",
  month: "Previous month",
};

const NEXT_LABEL: Record<DispatchViewTab, string> = {
  day: "Next day",
  week: "Next week",
  month: "Next month",
};

const TODAY_LABEL: Record<DispatchViewTab, string> = {
  day: "Today",
  week: "This Week",
  month: "Today",
};

/**
 * DispatchToolbar
 *
 * Renders the top navigation bar for the dispatch board.
 * FE-B30: 3 tabs (Day/Week/Month), week-specific controls, month chip toggle.
 */
export function DispatchToolbar({
  viewTab,
  activeDate,
  sseConnected,
  lastBoardFetch,
  onViewTabChange,
  onNavigatePrev,
  onNavigateNext,
  onNavigateToToday,
  onResolveConflicts,
  weekDaysToShow = 5,
  onWeekDaysToggle,
  chipDisplayMode = "customer",
  onChipDisplayModeToggle,
  layoutMode = "lane",
  onLayoutModeToggle,
}: DispatchToolbarProps) {
  // pendingCount: count of in-flight moveJob mutations
  const pendingMutations = useMutationState({
    filters: { mutationKey: ["moveJob"], status: "pending" },
  });
  const optimisticMoveCount = pendingMutations.length;

  const syncState = sseConnected ? "idle" : "error";

  // Compute the display label for the current date / period
  const dateLabel =
    viewTab === "week"
      ? formatWeekLabel(activeDate, weekDaysToShow)
      : formatDisplayDate(activeDate, viewTab);

  return (
    <div className="flex items-center gap-4 px-4 py-2 border-b border-neutral-200 bg-white flex-wrap">
      {/* View tab switcher */}
      <div
        className="flex items-center rounded-md border border-neutral-200 overflow-hidden"
        role="tablist"
        aria-label="Calendar view"
      >
        {VIEW_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={viewTab === tab.value}
            onClick={() => onViewTabChange(tab.value)}
            className={[
              "px-3 py-1.5 text-body font-medium",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-600",
              viewTab === tab.value
                ? "bg-brand-600 text-white"
                : "bg-white text-neutral-600 hover:bg-neutral-50",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Date navigation */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onNavigatePrev}
          className="p-1.5 rounded-md text-neutral-600 hover:bg-neutral-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          aria-label={PREV_LABEL[viewTab]}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              d="M10 4L6 8l4 4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          </svg>
        </button>

        <button
          type="button"
          onClick={onNavigateToToday}
          className="px-3 py-1 rounded-md text-body font-medium text-neutral-600 border border-neutral-200 hover:bg-neutral-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
        >
          {TODAY_LABEL[viewTab]}
        </button>

        <button
          type="button"
          onClick={onNavigateNext}
          className="p-1.5 rounded-md text-neutral-600 hover:bg-neutral-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          aria-label={NEXT_LABEL[viewTab]}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              d="M6 4l4 4-4 4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          </svg>
        </button>

        <span className="text-body font-medium text-neutral-900 min-w-48">
          {dateLabel}
        </span>

        {/* Week-specific: 5-day / 7-day pill toggle */}
        {viewTab === "week" && onWeekDaysToggle && (
          <PillToggle<5 | 7>
            options={[
              { value: 5, label: "5-day" },
              { value: 7, label: "7-day" },
            ]}
            value={weekDaysToShow}
            onChange={onWeekDaysToggle}
          />
        )}

        {/* Month-specific: Customer / Tech chip toggle */}
        {viewTab === "month" && onChipDisplayModeToggle && (
          <PillToggle<"customer" | "tech">
            options={[
              { value: "customer", label: "Customer" },
              { value: "tech", label: "Tech" },
            ]}
            value={chipDisplayMode}
            onChange={onChipDisplayModeToggle}
          />
        )}

        {/* DISPATCH-B1 / DISPATCH-B1.5: Lane | Tech toggle — Day AND Week modes */}
        {(viewTab === "day" || viewTab === "week") && onLayoutModeToggle && (
          <PillToggle<"lane" | "tech">
            options={[
              { value: "lane", label: "Lane" },
              { value: "tech", label: "Tech" },
            ]}
            value={layoutMode}
            onChange={onLayoutModeToggle}
          />
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* In-flight sync indicator */}
      <InFlightSyncIndicator
        surface="dispatch"
        pendingCount={optimisticMoveCount}
        state={optimisticMoveCount > 0 ? "syncing" : syncState}
        lastSyncedAt={lastBoardFetch ?? undefined}
        compact
        onResolve={onResolveConflicts}
      />
    </div>
  );
}
