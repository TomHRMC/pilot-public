/**
 * FE-B28 — PilotTable unit tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b28/pilot_table.test.tsx
 *
 * Tests:
 * 1. Renders table with correct number of rows
 * 2. Sort indicator shows "↕" for sortable column headers
 * 3. Sort changes to "▲" after clicking a sortable header
 * 4. Sort changes to "▼" on second click (desc)
 * 5. Non-sortable columns show no indicator
 */

import React, { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import {
  createColumnHelper,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { PilotTable } from "@/components/PilotTable";

interface TestRow {
  id: string;
  name: string;
  value: number;
}

const columnHelper = createColumnHelper<TestRow>();

const columns = [
  columnHelper.accessor("name", {
    header: "Name",
    size: 200,
    enableSorting: true,
    enableResizing: true,
    cell: (info) => info.getValue(),
  }),
  columnHelper.accessor("value", {
    header: "Value",
    size: 100,
    enableSorting: true,
    enableResizing: true,
    cell: (info) => String(info.getValue()),
  }),
  columnHelper.display({
    id: "actions",
    header: "Actions",
    size: 100,
    enableSorting: false,
    enableResizing: false,
    cell: () => <span>Action</span>,
  }),
];

const MOCK_DATA: TestRow[] = [
  { id: "1", name: "Alpha", value: 30 },
  { id: "2", name: "Beta", value: 10 },
  { id: "3", name: "Gamma", value: 20 },
];

function TestTable() {
  const [sorting, setSorting] = useState<SortingState>([]);
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: MOCK_DATA,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
  return <PilotTable table={table} />;
}

describe("PilotTable — FE-B28 shared render wrapper", () => {
  it("renders table with correct number of rows", () => {
    render(<TestTable />);
    // tbody rows (not header)
    const rows = screen.getAllByRole("row");
    // 1 header row + 3 data rows = 4
    expect(rows.length).toBe(4);
  });

  it("renders cell data correctly", () => {
    render(<TestTable />);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText("Gamma")).toBeInTheDocument();
  });

  it("shows '↕' sort indicator for sortable columns initially", () => {
    render(<TestTable />);
    // Name and Value are sortable — should show ↕
    const sortIndicators = screen.getAllByText("↕");
    expect(sortIndicators.length).toBeGreaterThanOrEqual(2);
  });

  it("shows '▲' after clicking a sortable header (asc)", () => {
    render(<TestTable />);
    const nameHeader = screen.getByText("Name").closest("th")!;
    fireEvent.click(nameHeader);
    expect(screen.getByText("▲")).toBeInTheDocument();
  });

  it("shows '▼' after clicking sortable header twice (desc)", () => {
    render(<TestTable />);
    const nameHeader = screen.getByText("Name").closest("th")!;
    fireEvent.click(nameHeader);
    fireEvent.click(nameHeader);
    expect(screen.getByText("▼")).toBeInTheDocument();
  });

  it("non-sortable Actions column shows no sort indicator", () => {
    render(<TestTable />);
    const actionsHeader = screen.getByText("Actions").closest("th")!;
    // Should not contain ↕ ▲ ▼
    expect(actionsHeader.textContent).not.toContain("↕");
    expect(actionsHeader.textContent).not.toContain("▲");
    expect(actionsHeader.textContent).not.toContain("▼");
  });
});
