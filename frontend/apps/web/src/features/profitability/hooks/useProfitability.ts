/**
 * useProfitability — TanStack Query hook for profitability reports
 *
 * Location: apps/web/src/features/profitability/hooks/useProfitability.ts
 *
 * GET /api/v1/reports/profitability with date_from + date_to params.
 * Backend requires YYYY-MM-DD strings — NOT a ?period= shorthand.
 *
 * BETA-B2 fix (Issue 3.5): replaced `?period=7d` with date_from / date_to
 * per openapi.json which lists date_from + date_to as required params.
 *
 * POST-BETA fix: The real API returns ProfitabilityReportResponse
 * (a flat `data: ProfitabilityRow[]` aggregated array — verified against
 * openapi.json / backend/api/schemas/reports.py). The frontend UI was built
 * against a richer planned shape that was never implemented server-side.
 * adaptProfitabilityResponse() bridges the gap client-side.
 *
 * Per batch-fe-b4-design.md §A.2.7
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { format, subDays, startOfMonth, startOfYear } from "date-fns";

export type ProfitabilityPeriod = "7d" | "30d" | "mtd" | "ytd" | "custom";

// ─── Raw API types (matches openapi.json ProfitabilityReportResponse) ─────────

type MarginBucket = "below-low" | "low" | "medium" | "high";

interface RawProfitabilityRow {
  group_key: string;
  group_label: string; // contains job_number (e.g. JOB-000001) when group_by=job (B19)
  /** B19: customer display name from profitability JOIN */
  customer_name?: string | null;
  job_count: number;
  quoted_total_cents: number;
  actual_labor_cost_cents: number;
  actual_material_cost_cents: number;
  actual_profit_cents: number;
  margin_pct: number | null;
  margin_bucket: string | null;
  below_margin_target: boolean;
}

interface RawProfitabilityResponse {
  report_type: string;
  date_from: string;
  date_to: string;
  display_mode: string;
  row_count: number;
  report_chart_threshold: number;
  data: RawProfitabilityRow[];
}

// ─── UI-facing types (consumed by MetricsCardRow, ClosedJobsSection, etc.) ───

export interface ClosedJob {
  id: string;
  title: string; // group_label — kept for backward compat
  /** B19: human-readable job identifier (e.g. JOB-000001); group_label when group_by=job */
  job_number: string | null;
  /** B19: customer display name from profitability JOIN */
  customer_name: string | null;
  close_date: string;
  revenue_cents: number;
  margin_pct: number;
  margin_bucket: MarginBucket;
}

export interface ProfitabilitySummary {
  total_revenue_cents: number;
  total_profit_cents: number;
  avg_margin_pct: number;
  period_over_period_revenue_delta_pct: number;
  period_over_period_profit_delta_pct: number;
  period_over_period_margin_delta_pct: number;
}

export interface MarginDistribution {
  "below-low": number;
  low: number;
  medium: number;
  high: number;
}

export interface ProfitabilityResponse {
  period: string;
  closed_jobs: ClosedJob[];
  summary: ProfitabilitySummary;
  margin_distribution: MarginDistribution;
}

// ─── Client-side adapter ──────────────────────────────────────────────────────

const VALID_BUCKETS = new Set<MarginBucket>([
  "below-low",
  "low",
  "medium",
  "high",
]);

function toMarginBucket(raw: string | null | undefined): MarginBucket {
  if (raw && VALID_BUCKETS.has(raw as MarginBucket)) return raw as MarginBucket;
  return "low";
}

/**
 * Adapts the real backend ProfitabilityReportResponse (flat aggregated rows)
 * into the richer ProfitabilityResponse shape expected by the UI components.
 *
 * Notes:
 * - period_over_period_*: always 0 — the API does not return a prior-period
 *   baseline; delta badges will show "↑ 0.0% vs prev period" until the backend
 *   adds comparison data.
 */
function adaptProfitabilityResponse(
  raw: RawProfitabilityResponse,
): ProfitabilityResponse {
  const rows = raw.data ?? [];

  // Summary — derived from aggregated rows
  const total_revenue_cents = rows.reduce(
    (sum, r) => sum + r.quoted_total_cents,
    0,
  );
  const total_profit_cents = rows.reduce(
    (sum, r) => sum + r.actual_profit_cents,
    0,
  );
  const marginsWithData = rows
    .map((r) => r.margin_pct)
    .filter((m): m is number => m !== null);
  const avg_margin_pct =
    marginsWithData.length > 0
      ? marginsWithData.reduce((s, m) => s + m, 0) / marginsWithData.length
      : 0;

  const summary: ProfitabilitySummary = {
    total_revenue_cents,
    total_profit_cents,
    avg_margin_pct,
    // API provides no prior-period baseline; deltas shown as 0 until backend adds it
    period_over_period_revenue_delta_pct: 0,
    period_over_period_profit_delta_pct: 0,
    period_over_period_margin_delta_pct: 0,
  };

  // closed_jobs — map each aggregated row
  const closed_jobs: ClosedJob[] = rows.map((r) => ({
    id: r.group_key,
    title: r.group_label,
    // B19: group_label IS the job_number (JOB-000001 format) when group_by=job
    job_number: r.group_label ?? null,
    customer_name: r.customer_name ?? null,
    close_date: raw.date_to,
    revenue_cents: r.quoted_total_cents,
    margin_pct: r.margin_pct ?? 0,
    margin_bucket: toMarginBucket(r.margin_bucket),
  }));

  // margin_distribution — count rows per bucket
  const margin_distribution: MarginDistribution = {
    "below-low": 0,
    low: 0,
    medium: 0,
    high: 0,
  };
  for (const r of rows) {
    const bucket = toMarginBucket(r.margin_bucket);
    margin_distribution[bucket] += 1;
  }

  return {
    period: `${raw.date_from}/${raw.date_to}`,
    closed_jobs,
    summary,
    margin_distribution,
  };
}

/**
 * Converts a period shorthand into YYYY-MM-DD date_from / date_to strings
 * that the backend /api/v1/reports/profitability endpoint accepts.
 *
 * Exported so unit tests can exercise the conversion logic independently.
 */
export function periodToDates(period: Exclude<ProfitabilityPeriod, "custom">): {
  date_from: string;
  date_to: string;
} {
  const today = new Date();
  const fmt = (d: Date) => format(d, "yyyy-MM-dd");

  switch (period) {
    case "7d":
      return { date_from: fmt(subDays(today, 7)), date_to: fmt(today) };
    case "30d":
      return { date_from: fmt(subDays(today, 30)), date_to: fmt(today) };
    case "mtd":
      return { date_from: fmt(startOfMonth(today)), date_to: fmt(today) };
    case "ytd":
      return { date_from: fmt(startOfYear(today)), date_to: fmt(today) };
    default: {
      const _exhaustive: never = period;
      throw new Error(`Unknown period: ${String(_exhaustive)}`);
    }
  }
}

async function fetchProfitability(
  date_from: string,
  date_to: string,
): Promise<ProfitabilityResponse> {
  const res = await apiClient.get(`/api/v1/reports/profitability`, {
    params: { date_from, date_to },
  });
  return adaptProfitabilityResponse(res.data as RawProfitabilityResponse);
}

export const PROFITABILITY_QUERY_KEY = (date_from: string, date_to: string) =>
  ["profitability", date_from, date_to] as const;

export interface UseProfitabilityOptions {
  period: ProfitabilityPeriod;
  /**
   * Only used when period === 'custom'. Both must be provided to fire the query.
   * Custom date range UI is deferred to BETA-B6.
   */
  customDateFrom?: string;
  customDateTo?: string;
}

export function useProfitability({
  period,
  customDateFrom,
  customDateTo,
}: UseProfitabilityOptions) {
  // Custom period requires explicit dates (BETA-B6 builds the picker).
  // If custom is selected without dates, skip the API call gracefully.
  const isCustomWithoutDates =
    period === "custom" && (!customDateFrom || !customDateTo);

  const { date_from, date_to } =
    period === "custom"
      ? {
          date_from: customDateFrom ?? "",
          date_to: customDateTo ?? "",
        }
      : periodToDates(period);

  return useQuery({
    queryKey: PROFITABILITY_QUERY_KEY(date_from, date_to),
    queryFn: () => fetchProfitability(date_from, date_to),
    enabled: !isCustomWithoutDates,
    staleTime: 2 * 60_000, // 2 minutes
    refetchOnWindowFocus: true,
  });
}

// ─── Backwards-compatible overload for callers passing period as positional arg ──
// (Existing callers use: useProfitability(period) — support both call signatures.)
export function useProfitabilityByPeriod(period: ProfitabilityPeriod) {
  return useProfitability({ period });
}
