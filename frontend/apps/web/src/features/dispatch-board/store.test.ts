/**
 * useDispatchBoardStore — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/store.test.ts
 * Per batch-fe-b4-design.md §I.1
 * Target: 6 tests
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useDispatchBoardStore } from "./store";

// Reset store between tests
beforeEach(() => {
  useDispatchBoardStore.setState({
    viewTab: "day",
    activeDate: new Date().toISOString().split("T")[0] ?? "",
    filters: {
      techIds: [],
      statuses: [],
      customerTypes: [],
      jobTypes: [],
      priorities: [],
    },
    selectedJobId: null,
    conflictPreviewOpen: false,
    conflictPreviewJobId: null,
  });
});

describe("useDispatchBoardStore", () => {
  it("setViewTab updates viewTab", () => {
    useDispatchBoardStore.getState().setViewTab("week");
    expect(useDispatchBoardStore.getState().viewTab).toBe("week");
  });

  it("setActiveDate updates activeDate", () => {
    useDispatchBoardStore.getState().setActiveDate("2026-06-15");
    expect(useDispatchBoardStore.getState().activeDate).toBe("2026-06-15");
  });

  it("toggleTechFilter adds and removes tech IDs", () => {
    const store = useDispatchBoardStore.getState();

    store.toggleTechFilter("tech-1");
    expect(useDispatchBoardStore.getState().filters.techIds).toContain(
      "tech-1",
    );

    store.toggleTechFilter("tech-1");
    expect(useDispatchBoardStore.getState().filters.techIds).not.toContain(
      "tech-1",
    );
  });

  it("navigateToToday sets activeDate to today", () => {
    const today = new Date().toISOString().split("T")[0] ?? "";
    useDispatchBoardStore.getState().setActiveDate("2026-01-01");
    useDispatchBoardStore.getState().navigateToToday();
    expect(useDispatchBoardStore.getState().activeDate).toBe(today);
  });

  it("setSelectedJobId updates selectedJobId", () => {
    useDispatchBoardStore.getState().setSelectedJobId("job-123");
    expect(useDispatchBoardStore.getState().selectedJobId).toBe("job-123");

    useDispatchBoardStore.getState().setSelectedJobId(null);
    expect(useDispatchBoardStore.getState().selectedJobId).toBeNull();
  });

  it("openConflictPreview and closeConflictPreview toggle state", () => {
    useDispatchBoardStore.getState().openConflictPreview("job-456");
    expect(useDispatchBoardStore.getState().conflictPreviewOpen).toBe(true);
    expect(useDispatchBoardStore.getState().conflictPreviewJobId).toBe(
      "job-456",
    );

    useDispatchBoardStore.getState().closeConflictPreview();
    expect(useDispatchBoardStore.getState().conflictPreviewOpen).toBe(false);
    expect(useDispatchBoardStore.getState().conflictPreviewJobId).toBeNull();
  });

  it("clearAllFilters resets all filter arrays", () => {
    useDispatchBoardStore.getState().toggleTechFilter("tech-1");
    // DISPATCH-B3: "urgent" (was "rush")
    useDispatchBoardStore.getState().togglePriorityFilter("urgent");
    useDispatchBoardStore.getState().clearAllFilters();

    const { filters } = useDispatchBoardStore.getState();
    expect(filters.techIds).toHaveLength(0);
    expect(filters.priorities).toHaveLength(0);
  });
});
