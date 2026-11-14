/**
 * WipJobsTable — Sortable active-jobs table composing <PilotTable>
 *
 * Location: apps/web/src/features/wip/components/WipJobsTable.tsx
 *
 * Sort is SERVER-SIDE — the API sorts via sort/order params. TanStack Table is used
 * only for rendering + sort header interaction (no getSortedRowModel). Sort state lives
 * in URL query params (?sort=&order=) so it survives refresh/back and is shareable
 * (spec §6.2, §9.2).
 *
 * Only 3 columns are sortable in the UI: Deviation (default), Margin, Actual Cost.
 * scheduled_start_at is API-only (no header) per spec §6.2 note.
 *
 * Sort indicator: PilotTable's built-in unicode glyph (▲/▼/↕) is used as an acceptable
 * interim per spec §4. A follow-up should parameterize PilotTable to accept Heroicons.
 *
 * aria-sort + scope="col" are added via a post-render useEffect (interim until
 * PilotTable is enhanced to accept these natively — spec Accessibility Notes).
 *
 * Per batch-up-1-ui-design-spec.md §2.3 + Accessibility Notes.
 */

"use client";

import React from "react";
import {
  createColumnHelper,
  getCoreRowModel,
  useReactTable,
  type SortingState,
  type OnChangeFn,
} from "@tanstack/react-table";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { InformationCircleIcon } from "@heroicons/react/24/outline";
import type { components } from "@pilot/shared-types";
import { PilotTable } from "@/components/PilotTable";
import { DeviationBadge } from "./DeviationBadge";
import { formatCents, formatPct } from "../lib/wip-format";
import type { WipSort } from "../hooks/useWipReport";

type WipReportRow = components["schemas"]["WipReportRow"];

interface WipJobsTableProps {
  rows: WipReportRow[];
  marginTargetPct: number;
  /** Current sort field (from URL) */
  sort: WipSort;
  /** Current sort order (from URL) */
  order: "asc" | "desc";
}

const columnHelper = createColumnHelper<WipReportRow>();

/** Maps TanStack column id → API sort param */
const COLUMN_TO_API_SORT: Record<string, WipSort> = {
  budget_deviation_pct: "deviation_pct",
  projected_margin_pct: "projected_margin_pct",
  actual_cost_cents: "actual_cost_cents",
};

/** Maps API sort param → TanStack column id */
const API_SORT_TO_COLUMN: Record<string, string> = {
  deviation_pct: "budget_deviation_pct",
  projected_margin_pct: "projected_margin_pct",
  actual_cost_cents: "actual_cost_cents",
};

/** Status badge for scheduled / in_progress (spec §2.4) */
function StatusBadge({ statusCode }: { statusCode: string }) {
  const isScheduled = statusCode === "scheduled";
  const isInProgress = statusCode === "in_progress";
  const label = isScheduled
    ? "Scheduled"
    : isInProgress
      ? "In Progress"
      : statusCode;
  const classes = isScheduled
    ? "bg-blue-100 text-blue-700"
    : isInProgress
      ? "bg-alert-100 text-alert-700"
      : "bg-neutral-100 text-neutral-700";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-caption font-medium ${classes}`}
    >
      {label}
    </span>
  );
}

export function WipJobsTable({
  rows,
  marginTargetPct,
  sort,
  order,
}: WipJobsTableProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // TanStack sorting state — derived from URL (server-side sort, not client)
  const activeColumnId = API_SORT_TO_COLUMN[sort] ?? "budget_deviation_pct";
  const sorting: SortingState = [
    { id: activeColumnId, desc: order === "desc" },
  ];

  // Intercept TanStack sort toggle → update URL params
  const onSortingChange: OnChangeFn<SortingState> = (updater) => {
    const next = typeof updater === "function" ? updater(sorting) : updater;
    if (next.length > 0) {
      const { id, desc } = next[0];
      const apiSort = COLUMN_TO_API_SORT[id];
      if (apiSort) {
        const params = new URLSearchParams(searchParams.toString());
        params.set("sort", apiSort);
        params.set("order", desc ? "desc" : "asc");
        router.replace(`${pathname}?${params.toString()}`);
      }
    }
  };

  const columns = [
    // Col 1 — Job (job_number + title)
    columnHelper.accessor("job_number", {
      id: "job_number",
      header: "Job",
      size: 18,
      enableSorting: false,
      cell: (info) => {
        const row = info.row.original;
        return (
          <div>
            <p className="text-sm font-medium text-neutral-900">
              {row.job_number}
            </p>
            {row.title && (
              <p className="text-caption text-neutral-500">{row.title}</p>
            )}
          </div>
        );
      },
    }),
    // Col 2 — Customer / Site
    columnHelper.accessor("customer_name", {
      id: "customer_site",
      header: "Customer / Site",
      size: 16,
      enableSorting: false,
      cell: (info) => {
        const row = info.row.original;
        return (
          <div>
            <p className="text-sm text-neutral-900">
              {row.customer_name ?? "—"}
            </p>
            {row.site_name && (
              <p className="text-caption text-neutral-500">{row.site_name}</p>
            )}
          </div>
        );
      },
    }),
    // Col 3 — Status
    columnHelper.accessor("status_code", {
      id: "status",
      header: "Status",
      size: 10,
      enableSorting: false,
      cell: (info) => <StatusBadge statusCode={info.getValue()} />,
    }),
    // Col 4 — Quoted Budget
    columnHelper.accessor("quoted_budget_cents", {
      id: "quoted_budget",
      header: "Quoted Budget",
      size: 11,
      enableSorting: false,
      cell: (info) => {
        const val = info.getValue();
        return (
          <span
            className={`block text-right tabular-nums ${
              val == null ? "text-neutral-400" : "text-neutral-900"
            }`}
          >
            {formatCents(val)}
          </span>
        );
      },
    }),
    // Col 5 — Actual Cost (sortable)
    columnHelper.accessor("actual_cost_cents", {
      id: "actual_cost_cents",
      header: "Actual Cost",
      size: 11,
      enableSorting: true,
      cell: (info) => (
        <span className="block text-right tabular-nums text-neutral-900">
          {formatCents(info.getValue())}
        </span>
      ),
    }),
    // Col 6 — ETC
    columnHelper.accessor("etc_cost_cents", {
      id: "etc",
      header: "ETC",
      size: 12,
      enableSorting: false,
      cell: (info) => {
        const row = info.row.original;
        if (!row.has_etc) {
          return (
            <span className="inline-flex items-center gap-1 text-caption text-neutral-400">
              No ETC
              <InformationCircleIcon
                className="w-4 h-4 text-neutral-400"
                aria-hidden="true"
              />
            </span>
          );
        }
        return (
          <div className="text-right">
            {row.etc_hours_remaining != null && (
              <p className="text-sm text-neutral-700 tabular-nums">
                {row.etc_hours_remaining}h
              </p>
            )}
            <p className="text-caption text-neutral-500 tabular-nums">
              {formatCents(row.etc_cost_cents)}
            </p>
          </div>
        );
      },
    }),
    // Col 7 — Projected Cost
    columnHelper.accessor("projected_cost_cents", {
      id: "projected_cost",
      header: "Projected Cost",
      size: 11,
      enableSorting: false,
      cell: (info) => (
        <span className="block text-right tabular-nums text-neutral-900">
          {formatCents(info.getValue())}
        </span>
      ),
    }),
    // Col 8 — Deviation (sortable, default)
    columnHelper.accessor("budget_deviation_pct", {
      id: "budget_deviation_pct",
      header: "Deviation",
      size: 11,
      enableSorting: true,
      cell: (info) => {
        const row = info.row.original;
        return (
          <DeviationBadge
            budgetDeviationPct={info.getValue()}
            belowMarginTarget={row.below_margin_target}
            marginTargetPct={marginTargetPct}
          />
        );
      },
    }),
    // Col 9 — Margin (sortable)
    columnHelper.accessor("projected_margin_pct", {
      id: "projected_margin_pct",
      header: "Margin",
      size: 11,
      enableSorting: true,
      cell: (info) => {
        const val = info.getValue();
        return (
          <span
            className={`block text-right tabular-nums ${
              val == null ? "text-neutral-400" : "text-neutral-900"
            }`}
          >
            {formatPct(val)}
          </span>
        );
      },
    }),
  ];

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    enableSortingRemoval: false,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange,
  });

  // Post-render enhancement: add aria-sort + scope="col" to th elements.
  // Interim until PilotTable is enhanced to accept these natively (spec Accessibility Notes).
  const containerRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const ths = container.querySelectorAll("th");
    ths.forEach((th) => {
      th.setAttribute("scope", "col");
      const text = th.textContent?.trim() ?? "";
      let columnId: string | null = null;
      if (text.startsWith("Deviation")) columnId = "budget_deviation_pct";
      else if (text.startsWith("Margin")) columnId = "projected_margin_pct";
      else if (text.startsWith("Actual Cost")) columnId = "actual_cost_cents";

      if (columnId && COLUMN_TO_API_SORT[columnId]) {
        const apiSort = COLUMN_TO_API_SORT[columnId];
        if (sort === apiSort) {
          th.setAttribute(
            "aria-sort",
            order === "desc" ? "descending" : "ascending",
          );
        } else {
          th.setAttribute("aria-sort", "none");
        }
      }
    });
  }, [table, sort, order]);

  return (
    <div ref={containerRef} className="scroll-mt-16">
      <PilotTable
        table={table}
        tableDataTestId="wip-jobs-table"
        getRowDataTestId={(row) => `wip-row-${row.job_id}`}
      />
    </div>
  );
}
