/**
 * DispatchGridColumn — Unit Tests (onDrop optional)
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchGridColumn.test.tsx
 * Per batch-beta-v1-fixes-b5-design.md §I.1
 *
 * Verifies:
 * - Column renders without onDrop (read-only mode — no crash)
 * - Column renders with onDrop (Day view mode)
 * - Job blocks are rendered within the column
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { DispatchGridColumn } from "./DispatchGridColumn";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";

// Mock react-dnd
vi.mock("react-dnd", () => ({
  DndProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useDrag: () => [{ isDragging: false }, vi.fn(), vi.fn()],
  useDrop: () => [{ isOver: false, canDrop: true }, vi.fn()],
}));

const mockTech: DispatchBoardTech = {
  id: "tech-1",
  tech_id: "tech-1",
  name: "Alice Chen",
  display_color: "#3B43D6",
  avatar_url: null,
};

const mockJob: DispatchBoardJob = {
  id: "job-1",
  title: "Circuit breaker replacement",
  customer_name: "Home Owner",
  site_address: "123 Oak St",
  scheduled_start_at: "2026-06-10T09:00:00.000Z",
  scheduled_end_at: "2026-06-10T11:00:00.000Z",
  tech_id: "tech-1",
  status: "scheduled",
  priority: "standard",
  customer_type: "person",
  job_type_code: "repair",
  job_type_label: "Repair",
  updated_at: "2026-06-10T08:00:00.000Z",
};

describe("DispatchGridColumn", () => {
  it("renders without onDrop (read-only mode) without crashing", () => {
    // Should NOT throw when onDrop is omitted
    expect(() => {
      render(
        <DndProvider backend={HTML5Backend}>
          <DispatchGridColumn
            tech={mockTech}
            jobs={[]}
            onJobSelect={vi.fn()}
            // onDrop intentionally omitted
          />
        </DndProvider>,
      );
    }).not.toThrow();
  });

  it("renders the tech column header when tech is provided", () => {
    const { container } = render(
      <DndProvider backend={HTML5Backend}>
        <DispatchGridColumn tech={mockTech} jobs={[]} onJobSelect={vi.fn()} />
      </DndProvider>,
    );
    // TechColumnHeader may render name in separate child elements
    expect(container.textContent).toContain("Alice");
  });

  it("renders Unassigned column header when tech is null", () => {
    render(
      <DndProvider backend={HTML5Backend}>
        <DispatchGridColumn
          tech={null}
          jobs={[]}
          isUnassigned
          onJobSelect={vi.fn()}
        />
      </DndProvider>,
    );
    expect(screen.getByText("Unassigned")).toBeInTheDocument();
  });

  it("renders job block for a tech-assigned job", () => {
    render(
      <DndProvider backend={HTML5Backend}>
        <DispatchGridColumn
          tech={mockTech}
          jobs={[mockJob]}
          onJobSelect={vi.fn()}
        />
      </DndProvider>,
    );
    expect(screen.getByText("Circuit breaker replacement")).toBeInTheDocument();
  });

  it("renders with onDrop provided (Day view mode) without crashing", () => {
    const onDrop = vi.fn();
    expect(() => {
      render(
        <DndProvider backend={HTML5Backend}>
          <DispatchGridColumn
            tech={mockTech}
            jobs={[]}
            onDrop={onDrop}
            onJobSelect={vi.fn()}
          />
        </DndProvider>,
      );
    }).not.toThrow();
  });
});
