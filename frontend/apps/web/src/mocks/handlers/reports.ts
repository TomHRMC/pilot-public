/**
 * MSW Handlers — /api/v1/reports/* stubs for FE-B4
 *
 * Location: apps/web/src/mocks/handlers/reports.ts
 *
 * Stubs the profitability reports endpoint.
 * Already in openapi.json (line 15178 per design doc) — real types available.
 *
 * Per batch-fe-b4-design.md §D.3
 */

import { http, HttpResponse } from "msw";

export const reportsHandlers = [
  // GET /api/v1/reports/profitability
  // BETA-B2: accepts date_from + date_to (YYYY-MM-DD) instead of ?period shorthand
  http.get("/api/v1/reports/profitability", ({ request }) => {
    const url = new URL(request.url);

    // BETA-B2: backend requires date_from + date_to, not period shorthand
    const dateFrom = url.searchParams.get("date_from");
    const dateTo = url.searchParams.get("date_to");

    // Derive a rough period label for job-count scaling (used in chart threshold tests)
    // date_from and date_to are YYYY-MM-DD; compute diff in days
    let jobCount = 12; // default (≈30d)
    if (dateFrom && dateTo) {
      const diffMs = new Date(dateTo).getTime() - new Date(dateFrom).getTime();
      const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
      jobCount = diffDays <= 7 ? 4 : diffDays <= 31 ? 12 : 8;
    }

    // Derive period label for the response body (for backward compat with test assertions)
    const period = dateFrom && dateTo ? `${dateFrom}__${dateTo}` : "30d";

    const closedJobs = Array.from({ length: jobCount }, (_, i) => ({
      id: `closed-job-${i + 1}`,
      title: `Completed job ${i + 1}`,
      close_date: new Date(Date.now() - i * 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0],
      revenue_cents: Math.round(150000 + Math.random() * 500000),
      margin_pct: Math.round(5 + Math.random() * 35),
      margin_bucket: (["below-low", "low", "medium", "high"] as const)[i % 4],
    }));

    return HttpResponse.json({
      period,
      closed_jobs: closedJobs,
      summary: {
        total_revenue_cents: closedJobs.reduce(
          (s, j) => s + j.revenue_cents,
          0,
        ),
        total_profit_cents: 285000,
        avg_margin_pct: 24.5,
        period_over_period_revenue_delta_pct: 12.3,
        period_over_period_profit_delta_pct: 8.1,
        period_over_period_margin_delta_pct: -1.2,
      },
      margin_distribution: {
        "below-low": closedJobs.filter((j) => j.margin_bucket === "below-low")
          .length,
        low: closedJobs.filter((j) => j.margin_bucket === "low").length,
        medium: closedJobs.filter((j) => j.margin_bucket === "medium").length,
        high: closedJobs.filter((j) => j.margin_bucket === "high").length,
      },
    });
  }),

  // GET /api/v1/settings/reports (margin bucket config)
  http.get("/api/v1/settings/reports", () => {
    return HttpResponse.json({
      margin_bucket_boundaries: [10, 20, 30], // default per design doc §G.7
      margin_target_pct: 20,
    });
  }),
];
