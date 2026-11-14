/**
 * jobDetailHandlers — MSW handlers for job detail endpoints (MOB-B2)
 *
 * Location: apps/mobile/mocks/handlers/jobDetailHandlers.ts
 *
 * Covers:
 *   GET /api/v1/jobs/:jobId
 *   GET /api/v1/jobs/:jobId/time-entries
 *   GET /api/v1/jobs/:jobId/expenses
 *   GET /api/v1/jobs/:jobId/notes
 *   GET /api/v1/jobs/:jobId/loto-confirmations
 *   GET /api/v1/jobs/:jobId/change-orders
 *   GET /api/v1/jobs/:jobId/projected-margin
 *
 * Fixture jobId "job-today-001" aligns with JOB_TODAY_1 from jobsHandlers.ts
 * so integration tests can navigate list → detail.
 *
 * projected-margin response shape: open object (openapi.json shows
 * "additionalProperties: true" — no named schema). Fixture provides
 * margin_percent, quoted_hours, actual_hours, cost_delta_cents.
 */

import { http, HttpResponse } from "msw";

const BASE = "*/api/v1";

const TODAY = new Date().toISOString().slice(0, 10);

/** Primary fixture job id — matches JOB_TODAY_1.id in jobsHandlers.ts */
export const DETAIL_JOB_ID = "job-today-001";
export const DETAIL_USER_ID = "tech-user-001";
export const DETAIL_TENANT_ID = "tenant-001";
export const DETAIL_CUSTOMER_ID = "customer-001";

// ── Job detail ────────────────────────────────────────────────────────────────

export const getJobDetail = http.get(`${BASE}/jobs/:jobId`, ({ params }) => {
  const { jobId } = params as { jobId: string };
  return HttpResponse.json({
    id: jobId,
    tenant_id: DETAIL_TENANT_ID,
    customer_id: DETAIL_CUSTOMER_ID,
    site_id: "site-001",
    status_id: "status-scheduled",
    scheduled_start_at: `${TODAY}T09:00:00Z`,
    scheduled_end_at: `${TODAY}T12:00:00Z`,
    estimated_duration_minutes: 180,
  });
});

export const getJobDetailError = http.get(`${BASE}/jobs/:jobId`, () => {
  return HttpResponse.json(
    { detail: "Internal server error" },
    { status: 500 },
  );
});

// ── Time entries ──────────────────────────────────────────────────────────────

/** Default fixture: one active entry (ended_at=null) for DETAIL_USER_ID */
export const getJobTimeEntries = http.get(
  `${BASE}/jobs/:jobId/time-entries`,
  () => {
    return HttpResponse.json([
      {
        id: "time-entry-001",
        job_id: DETAIL_JOB_ID,
        user_id: DETAIL_USER_ID,
        started_at: `${TODAY}T09:00:00Z`,
        ended_at: null,
        hours: null,
        notes: null,
        hourly_rate_cents: 8500,
      },
    ]);
  },
);

/** Fixture: all entries closed (clocked out) */
export const getJobTimeEntriesClockedOut = http.get(
  `${BASE}/jobs/:jobId/time-entries`,
  () => {
    return HttpResponse.json([
      {
        id: "time-entry-001",
        job_id: DETAIL_JOB_ID,
        user_id: DETAIL_USER_ID,
        started_at: `${TODAY}T09:00:00Z`,
        ended_at: `${TODAY}T11:00:00Z`,
        hours: 2,
        notes: null,
        hourly_rate_cents: 8500,
      },
    ]);
  },
);

/** Fixture: empty list (never clocked in) */
export const getJobTimeEntriesEmpty = http.get(
  `${BASE}/jobs/:jobId/time-entries`,
  () => {
    return HttpResponse.json([]);
  },
);

// ── Expenses ──────────────────────────────────────────────────────────────────

export const getJobExpenses = http.get(`${BASE}/jobs/:jobId/expenses`, () => {
  return HttpResponse.json([
    {
      id: "expense-001",
      tenant_id: DETAIL_TENANT_ID,
      job_id: DETAIL_JOB_ID,
      job_expense_category_code: "materials",
      description: "12 AWG wire",
      vendor_name: null,
      incurred_at: TODAY,
      cost_cents: 4500,
    },
    {
      id: "expense-002",
      tenant_id: DETAIL_TENANT_ID,
      job_id: DETAIL_JOB_ID,
      job_expense_category_code: "tools",
      description: "Drill bit set",
      vendor_name: null,
      incurred_at: TODAY,
      cost_cents: 2800,
    },
  ]);
});

// ── Notes ─────────────────────────────────────────────────────────────────────

export const getJobNotes = http.get(`${BASE}/jobs/:jobId/notes`, () => {
  return HttpResponse.json({
    id: "notes-001",
    tenant_id: DETAIL_TENANT_ID,
    job_id: DETAIL_JOB_ID,
    notes: "Found additional wiring issue near panel. Need 20A breaker.",
    audio_object_key: null,
    customer_visible: false,
    client_capture_at: `${TODAY}T09:30:00Z`,
    server_received_at: `${TODAY}T09:30:05Z`,
  });
});

export const getJobNotesEmpty = http.get(`${BASE}/jobs/:jobId/notes`, () => {
  return HttpResponse.json(null, { status: 404 });
});

// ── LOTO confirmations ────────────────────────────────────────────────────────

/** Default: no confirmations (user needs to confirm all 3) */
export const getJobLotoEmpty = http.get(
  `${BASE}/jobs/:jobId/loto-confirmations`,
  () => {
    return HttpResponse.json([]);
  },
);

/** Fixture: first check type confirmed */
export const getJobLotoOneConfirmed = http.get(
  `${BASE}/jobs/:jobId/loto-confirmations`,
  () => {
    return HttpResponse.json([
      {
        id: "loto-001",
        tenant_id: DETAIL_TENANT_ID,
        job_id: DETAIL_JOB_ID,
        user_id: DETAIL_USER_ID,
        check_type: "lockout_points",
        confirmed_at: `${TODAY}T09:05:00Z`,
        client_capture_at: `${TODAY}T09:05:00Z`,
        server_received_at: `${TODAY}T09:05:03Z`,
        is_active: true,
      },
    ]);
  },
);

/** Default registered handler: no confirmations */
export const getJobLotoConfirmations = getJobLotoEmpty;

// ── Change orders ─────────────────────────────────────────────────────────────

export const getJobChangeOrders = http.get(
  `${BASE}/jobs/:jobId/change-orders`,
  () => {
    return HttpResponse.json([
      {
        id: "co-001",
        tenant_id: DETAIL_TENANT_ID,
        job_id: DETAIL_JOB_ID,
        description: "Panel upgrade addition",
        subtotal_cents: 32000,
        tax_cents: 2880,
        total_cents: 34880,
        is_active: true,
      },
    ]);
  },
);

// ── Projected margin ──────────────────────────────────────────────────────────
// openapi.json response: open object (additionalProperties: true).
// Fixture provides known fields from backend service logic.

export const getJobProjectedMargin = http.get(
  `${BASE}/jobs/:jobId/projected-margin`,
  () => {
    return HttpResponse.json({
      margin_percent: 38,
      quoted_hours: 3,
      actual_hours: 2.5,
      cost_delta_cents: 4200,
      etc_hours_remaining: 0.5,
    });
  },
);

// ── Handler array ─────────────────────────────────────────────────────────────

export const jobDetailHandlers = [
  getJobDetail,
  getJobTimeEntries,
  getJobExpenses,
  getJobNotes,
  getJobLotoConfirmations,
  getJobChangeOrders,
  getJobProjectedMargin,
];
