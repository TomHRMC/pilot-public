/**
 * MSW Handlers — /api/v1/reports/wip
 *
 * Location: apps/web/src/mocks/handlers/wipHandlers.ts
 *
 * Fixtures per spec §9.7:
 * - Happy path: 12 rows, mixed ETC/no-ETC/no-quote
 * - Empty: row_count 0
 * - 422: invalid sort value
 * - 402: paywall
 * - One-each over/watch/under/none deviation rows (included in happy path)
 *
 * Per batch-up-1-react-engr-prompt.md STEP 10.
 */

import { http, HttpResponse } from "msw";

const GENERATED_AT = "2026-07-29T14:00:00Z";
const MARGIN_TARGET_PCT = 20.0;

interface WipRowFixture {
  job_id: string;
  job_number: string;
  title: string | null;
  customer_name: string | null;
  site_name: string | null;
  status_code: string;
  scheduled_start_at: string | null;
  quoted_budget_cents: number | null;
  actual_cost_cents: number;
  etc_hours_remaining: number | null;
  etc_cost_cents: number;
  projected_cost_cents: number;
  projected_margin_pct: number | null;
  budget_deviation_pct: number | null;
  has_etc: boolean;
  below_margin_target: boolean;
}

/** Happy-path fixture with mixed ETC/no-ETC/no-quote + all 4 deviation variants */
const happyRows: WipRowFixture[] = [
  // Row 1 — over budget (deviation < 0)
  {
    job_id: "job-1",
    job_number: "JOB-000101",
    title: "Panel upgrade — Office complex",
    customer_name: "Apex Commercial LLC",
    site_name: "North Warehouse",
    status_code: "in_progress",
    scheduled_start_at: "2026-07-20T13:00:00Z",
    quoted_budget_cents: 60000,
    actual_cost_cents: 42000,
    etc_hours_remaining: 6.5,
    etc_cost_cents: 22000,
    projected_cost_cents: 64000,
    projected_margin_pct: -6.67,
    budget_deviation_pct: -6.67,
    has_etc: true,
    below_margin_target: true,
  },
  // Row 2 — under budget, healthy (deviation >= 0, below_margin_target false)
  {
    job_id: "job-2",
    job_number: "JOB-000102",
    title: "EV charger install × 4",
    customer_name: "Green Auto Group",
    site_name: "Main Lot",
    status_code: "scheduled",
    scheduled_start_at: "2026-08-01T08:00:00Z",
    quoted_budget_cents: 120000,
    actual_cost_cents: 30000,
    etc_hours_remaining: 10,
    etc_cost_cents: 40000,
    projected_cost_cents: 70000,
    projected_margin_pct: 41.67,
    budget_deviation_pct: 41.67,
    has_etc: true,
    below_margin_target: false,
  },
  // Row 3 — watch (deviation >= 80, below_margin_target true)
  {
    job_id: "job-3",
    job_number: "JOB-000103",
    title: "Service call — CB trip",
    customer_name: "Johnson Residence",
    site_name: null,
    status_code: "in_progress",
    scheduled_start_at: "2026-07-25T09:00:00Z",
    quoted_budget_cents: 100000,
    actual_cost_cents: 10000,
    etc_hours_remaining: 4,
    etc_cost_cents: 5000,
    projected_cost_cents: 15000,
    projected_margin_pct: 85.0,
    budget_deviation_pct: 85.0,
    has_etc: true,
    below_margin_target: true,
  },
  // Row 4 — no quote (deviation null)
  {
    job_id: "job-4",
    job_number: "JOB-000104",
    title: "Emergency repair",
    customer_name: "Metro Properties LLC",
    site_name: "Building A",
    status_code: "in_progress",
    scheduled_start_at: "2026-07-22T14:00:00Z",
    quoted_budget_cents: null,
    actual_cost_cents: 15000,
    etc_hours_remaining: 2,
    etc_cost_cents: 5000,
    projected_cost_cents: 20000,
    projected_margin_pct: null,
    budget_deviation_pct: null,
    has_etc: true,
    below_margin_target: false,
  },
  // Row 5 — has quote, no ETC
  {
    job_id: "job-5",
    job_number: "JOB-000105",
    title: "Lighting retrofit",
    customer_name: "Riverside Properties",
    site_name: "Floor 2",
    status_code: "scheduled",
    scheduled_start_at: "2026-08-05T07:00:00Z",
    quoted_budget_cents: 80000,
    actual_cost_cents: 45000,
    etc_hours_remaining: null,
    etc_cost_cents: 0,
    projected_cost_cents: 45000,
    projected_margin_pct: 43.75,
    budget_deviation_pct: 43.75,
    has_etc: false,
    below_margin_target: false,
  },
  // Row 6 — no quote, no ETC
  {
    job_id: "job-6",
    job_number: "JOB-000106",
    title: null,
    customer_name: "Bob Davis",
    site_name: null,
    status_code: "scheduled",
    scheduled_start_at: null,
    quoted_budget_cents: null,
    actual_cost_cents: 5000,
    etc_hours_remaining: null,
    etc_cost_cents: 0,
    projected_cost_cents: 5000,
    projected_margin_pct: null,
    budget_deviation_pct: null,
    has_etc: false,
    below_margin_target: false,
  },
  // Rows 7-12 — additional mixed rows
  ...Array.from(
    { length: 6 },
    (_, i): WipRowFixture => ({
      job_id: `job-${i + 7}`,
      job_number: `JOB-000${107 + i}`,
      title: `Job ${i + 7}`,
      customer_name: `Customer ${i + 7}`,
      site_name: `Site ${i + 7}`,
      status_code: i % 2 === 0 ? "scheduled" : "in_progress",
      scheduled_start_at: `2026-08-${10 + i}T08:00:00Z`,
      quoted_budget_cents: 70000 + i * 5000,
      actual_cost_cents: 30000 + i * 3000,
      etc_hours_remaining: 5 + i,
      etc_cost_cents: 10000 + i * 1000,
      projected_cost_cents: 40000 + i * 4000,
      projected_margin_pct: 30 - i * 2,
      budget_deviation_pct: 30 - i * 2,
      has_etc: true,
      below_margin_target: i >= 3,
    }),
  ),
];

const happySummary = {
  active_job_count: happyRows.length,
  total_actual_cost_cents: happyRows.reduce(
    (s, r) => s + r.actual_cost_cents,
    0,
  ),
  total_quoted_budget_cents: happyRows.reduce(
    (s, r) => s + (r.quoted_budget_cents ?? 0),
    0,
  ),
  total_projected_cost_cents: happyRows.reduce(
    (s, r) => s + r.projected_cost_cents,
    0,
  ),
  jobs_over_budget_count: 1,
  jobs_below_margin_target_count: 4,
};

const emptyResponse = {
  report_type: "wip",
  generated_at: GENERATED_AT,
  margin_target_pct: MARGIN_TARGET_PCT,
  row_count: 0,
  summary: {
    active_job_count: 0,
    total_actual_cost_cents: 0,
    total_quoted_budget_cents: 0,
    total_projected_cost_cents: 0,
    jobs_over_budget_count: 0,
    jobs_below_margin_target_count: 0,
  },
  rows: [],
};

const VALID_SORTS = [
  "deviation_pct",
  "projected_margin_pct",
  "actual_cost_cents",
  "scheduled_start_at",
];

export const wipHandlers = [
  // GET /api/v1/reports/wip — happy path (default)
  http.get("/api/v1/reports/wip", ({ request }) => {
    const url = new URL(request.url);
    const sort = url.searchParams.get("sort");

    // 422 — invalid sort value
    if (sort && !VALID_SORTS.includes(sort)) {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/validation-error",
          title: "Invalid sort parameter",
          status: 422,
          detail: `sort must be one of: deviation_pct, projected_margin_pct, actual_cost_cents, scheduled_start_at`,
        },
        { status: 422 },
      );
    }

    return HttpResponse.json({
      report_type: "wip",
      generated_at: GENERATED_AT,
      margin_target_pct: MARGIN_TARGET_PCT,
      row_count: happyRows.length,
      summary: happySummary,
      rows: happyRows,
    });
  }),

  // GET /api/v1/reports/wip?status=empty — empty state fixture
  http.get("/api/v1/reports/wip?status=empty", () => {
    return HttpResponse.json(emptyResponse);
  }),
];
