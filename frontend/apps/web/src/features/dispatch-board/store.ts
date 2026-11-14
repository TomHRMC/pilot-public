/**
 * Dispatch Board — Zustand Store
 *
 * Location: apps/web/src/features/dispatch-board/store.ts
 *
 * Client state only: filter state, active view tab, active date,
 * selected job ID, conflict preview open state.
 *
 * Per pilot-react-engineer-methods.md §4:
 * "API data belongs in TanStack Query — never in Zustand."
 * Only ephemeral/cross-component/multi-step state lives here.
 *
 * Per batch-fe-b4-design.md §A.2.7
 */

import { create, type StateCreator } from "zustand";
import type { DispatchBoardJob } from "./types-stub";

// ─── Types ─────────────────────────────────────────────────────────────────────

export type DispatchViewTab = "day" | "week" | "month";

export interface DispatchBoardFilters {
  /** Selected tech IDs (empty = all visible) */
  techIds: string[];
  /** Selected statuses (empty = all visible) */
  statuses: Array<DispatchBoardJob["status"]>;
  /** DISPATCH-B3: customer.type values — person/company (was commercial/residential) */
  customerTypes: Array<"person" | "company">;
  /** Selected job types by code (empty = all visible) */
  jobTypes: string[];
  /** DISPATCH-B3: real priority values from backend — standard/urgent/emergency */
  priorities: Array<"standard" | "urgent" | "emergency">;
}

export interface DispatchBoardState {
  // ── View controls ──────────────────────────────────────────────────────────
  /** Active view tab: Day / Week / Month */
  viewTab: DispatchViewTab;
  /** Active date (YYYY-MM-DD) — drives the board's date range */
  activeDate: string;
  /**
   * Day board layout mode: 'lane' (lane-as-row) or 'tech' (tech-as-row).
   * Default 'lane'. NOT persisted — resets to 'lane' on page reload.
   * Survives Day/Week/Month view-tab switches (in-memory).
   * Per DISPATCH-B1 §E.5 / §G.6.
   */
  layoutMode: "lane" | "tech";

  // ── Filter state ──────────────────────────────────────────────────────────
  filters: DispatchBoardFilters;

  // ── Panel state ───────────────────────────────────────────────────────────
  /** ID of the currently selected job (opens JobDetailPanel) */
  selectedJobId: string | null;
  /** Whether the conflict preview pane is open */
  conflictPreviewOpen: boolean;
  /** ID of the job being moved (source of the conflict preview) */
  conflictPreviewJobId: string | null;

  // ── Actions ───────────────────────────────────────────────────────────────
  setViewTab: (tab: DispatchViewTab) => void;
  setActiveDate: (date: string) => void;
  navigatePrev: () => void;
  navigateNext: () => void;
  navigateToToday: () => void;
  /** DISPATCH-B1: Switch between lane-as-row and tech-as-row day board modes */
  setLayoutMode: (mode: "lane" | "tech") => void;

  toggleTechFilter: (techId: string) => void;
  toggleStatusFilter: (
    status: DispatchBoardFilters["statuses"][number],
  ) => void;
  toggleCustomerTypeFilter: (
    type: DispatchBoardFilters["customerTypes"][number],
  ) => void;
  toggleJobTypeFilter: (jobType: string) => void;
  togglePriorityFilter: (
    priority: DispatchBoardFilters["priorities"][number],
  ) => void;
  clearAllFilters: () => void;
  /** DISPATCH-B2: Clears only the status dimension (used by "All" status pill). */
  resetStatusFilter: () => void;

  setSelectedJobId: (jobId: string | null) => void;
  openConflictPreview: (jobId: string) => void;
  closeConflictPreview: () => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function toggleArrayItem<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter((i) => i !== item) : [...arr, item];
}

function addDays(dateStr: string, days: number): string {
  const date = new Date(dateStr);
  date.setDate(date.getDate() + days);
  return date.toISOString().split("T")[0] ?? dateStr;
}

/** Snap a YYYY-MM-DD string to the 1st of its month */
function snapToMonthStart(dateStr: string): string {
  return dateStr.slice(0, 8) + "01";
}

/** Add N calendar months to a YYYY-MM-DD string, returning the 1st of the result month */
function addCalendarMonths(dateStr: string, months: number): string {
  const d = new Date(dateStr + "T12:00:00");
  d.setDate(1); // avoid month-end overflow
  d.setMonth(d.getMonth() + months);
  return d.toISOString().split("T")[0]?.slice(0, 8) + "01";
}

/** Returns the number of days in the month containing dateStr (YYYY-MM-DD) */
export function getDaysInMonth(dateStr: string): number {
  const d = new Date(dateStr + "T12:00:00");
  return new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
}

export function getTabDays(tab: DispatchViewTab, activeDate?: string): number {
  switch (tab) {
    case "day":
      return 1;
    case "week":
      return 7;
    case "month":
      // Return the actual days in the displayed month when activeDate is known
      return activeDate ? getDaysInMonth(activeDate) : 31;
  }
}

const defaultFilters: DispatchBoardFilters = {
  techIds: [],
  statuses: [],
  customerTypes: [],
  jobTypes: [],
  priorities: [],
};

// ─── Store creator (typed with StateCreator for explicit type inference) ──────

const storeCreator: StateCreator<DispatchBoardState> = (set, get) => ({
  // ── Initial state ──────────────────────────────────────────────────────────
  viewTab: "day",
  activeDate: new Date().toISOString().split("T")[0] ?? "",
  layoutMode: "lane" as const,
  filters: defaultFilters,
  selectedJobId: null,
  conflictPreviewOpen: false,
  conflictPreviewJobId: null,

  // ── View control actions ───────────────────────────────────────────────────
  setViewTab: (tab: DispatchViewTab) =>
    set((s) => ({
      viewTab: tab,
      // When switching to month view, snap activeDate to the 1st of the month
      // so the calendar always shows a complete calendar month, not "today + 30 days".
      activeDate:
        tab === "month" ? snapToMonthStart(s.activeDate) : s.activeDate,
    })),

  setActiveDate: (date: string) => set({ activeDate: date }),

  navigatePrev: () => {
    const { activeDate, viewTab } = get();
    if (viewTab === "month") {
      set({ activeDate: addCalendarMonths(activeDate, -1) });
    } else {
      set({ activeDate: addDays(activeDate, -getTabDays(viewTab)) });
    }
  },

  navigateNext: () => {
    const { activeDate, viewTab } = get();
    if (viewTab === "month") {
      set({ activeDate: addCalendarMonths(activeDate, 1) });
    } else {
      set({ activeDate: addDays(activeDate, getTabDays(viewTab)) });
    }
  },

  navigateToToday: () => {
    const today = new Date().toISOString().split("T")[0] ?? "";
    const { viewTab } = get();
    set({
      activeDate: viewTab === "month" ? snapToMonthStart(today) : today,
    });
  },

  // DISPATCH-B1: layout mode toggle (lane|tech, default lane, not persisted)
  setLayoutMode: (mode: "lane" | "tech") => set({ layoutMode: mode }),

  // ── Filter actions ─────────────────────────────────────────────────────────
  toggleTechFilter: (techId: string) =>
    set((s) => ({
      filters: {
        ...s.filters,
        techIds: toggleArrayItem(s.filters.techIds, techId),
      },
    })),

  toggleStatusFilter: (status: DispatchBoardFilters["statuses"][number]) =>
    set((s) => ({
      filters: {
        ...s.filters,
        statuses: toggleArrayItem(s.filters.statuses, status),
      },
    })),

  toggleCustomerTypeFilter: (
    type: DispatchBoardFilters["customerTypes"][number],
  ) =>
    set((s) => ({
      filters: {
        ...s.filters,
        customerTypes: toggleArrayItem(s.filters.customerTypes, type),
      },
    })),

  toggleJobTypeFilter: (jobType: string) =>
    set((s) => ({
      filters: {
        ...s.filters,
        jobTypes: toggleArrayItem(s.filters.jobTypes, jobType),
      },
    })),

  togglePriorityFilter: (
    priority: DispatchBoardFilters["priorities"][number],
  ) =>
    set((s) => ({
      filters: {
        ...s.filters,
        priorities: toggleArrayItem(s.filters.priorities, priority),
      },
    })),

  clearAllFilters: () => set({ filters: defaultFilters }),

  // DISPATCH-B2: clears only the status dimension (used by "All" status pill)
  resetStatusFilter: () =>
    set((s) => ({ filters: { ...s.filters, statuses: [] } })),

  // ── Panel actions ──────────────────────────────────────────────────────────
  setSelectedJobId: (jobId: string | null) => set({ selectedJobId: jobId }),

  openConflictPreview: (jobId: string) =>
    set({ conflictPreviewOpen: true, conflictPreviewJobId: jobId }),

  closeConflictPreview: () =>
    set({ conflictPreviewOpen: false, conflictPreviewJobId: null }),
});

export const useDispatchBoardStore = create<DispatchBoardState>(storeCreator);
