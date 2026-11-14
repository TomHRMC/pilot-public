/**
 * jobsHandlers — MSW handlers for GET /api/v1/jobs/ (mobile, MOB-B1)
 *
 * Location: apps/mobile/mocks/handlers/jobsHandlers.ts
 *
 * Fixtures:
 *   - 2 today-jobs (same tech, scheduled today)
 *   - 1 upcoming job (3 days from now, same tech)
 *   - 1 job with scheduled_start_at = null → excluded by useTechJobsList
 *   - 1 job assigned to a different tech → excluded when ?tech_id= is applied
 *
 * Note: Until MOB-B1-BE ships, this handler ignores ?tech_id and
 * ?scheduled_date params and returns the full fixture set. Tests that need
 * filtering behaviour mock at the hook level.
 */

import { http, HttpResponse } from "msw";
import type { JobListItem } from "../../features/jobs/job-types";

const BASE = "*/api/v1";

const TODAY = new Date().toISOString().slice(0, 10);
const THREE_DAYS = new Date(Date.now() + 3 * 86_400_000)
  .toISOString()
  .slice(0, 10);

/** Shared tech id used across fixtures */
export const MOCK_TECH_ID = "tech-user-001";
export const OTHER_TECH_ID = "tech-user-002";

export const JOB_TODAY_1: JobListItem = {
  id: "job-today-001",
  tenant_id: "tenant-001",
  customer_id: "customer-001",
  site_id: "site-001",
  status_id: "status-scheduled",
  status_code: "scheduled",
  customer_name: "Acme Electric",
  scheduled_start_at: `${TODAY}T09:00:00Z`,
  scheduled_end_at: `${TODAY}T12:00:00Z`,
  estimated_duration_minutes: 180,
  // MOB-B9: triggers recurring badge + banner in tests
  recurrence_rule_id: "rule-mock-001",
};

export const JOB_TODAY_2: JobListItem = {
  id: "job-today-002",
  tenant_id: "tenant-001",
  customer_id: "customer-002",
  site_id: "site-002",
  status_id: "status-in-progress",
  status_code: "in_progress",
  customer_name: "Smith Residence",
  scheduled_start_at: `${TODAY}T13:00:00Z`,
  scheduled_end_at: `${TODAY}T15:00:00Z`,
  estimated_duration_minutes: 120,
};

export const JOB_UPCOMING_1: JobListItem = {
  id: "job-upcoming-001",
  tenant_id: "tenant-001",
  customer_id: "customer-003",
  site_id: "site-003",
  status_id: "status-scheduled",
  status_code: "scheduled",
  customer_name: "Jones Commercial",
  scheduled_start_at: `${THREE_DAYS}T08:00:00Z`,
  scheduled_end_at: `${THREE_DAYS}T12:00:00Z`,
  estimated_duration_minutes: 240,
};

/** Unscheduled job — should be excluded from both sections */
export const JOB_UNSCHEDULED: JobListItem = {
  id: "job-unscheduled-001",
  tenant_id: "tenant-001",
  customer_id: "customer-004",
  site_id: "site-004",
  status_id: "status-scheduled",
  status_code: "scheduled",
  customer_name: "Parker Enterprises",
  scheduled_start_at: null,
  scheduled_end_at: null,
  estimated_duration_minutes: null,
};

/** All jobs the handler returns — full fixture including unscheduled */
export const ALL_JOB_FIXTURES: JobListItem[] = [
  JOB_TODAY_1,
  JOB_TODAY_2,
  JOB_UPCOMING_1,
  JOB_UNSCHEDULED,
];

// Backend returns PaginatedJobListResponse { items, total, limit, offset }
// See openapi.json#/components/schemas/PaginatedJobListResponse
export const getJobsList = http.get(`${BASE}/jobs/`, () => {
  return HttpResponse.json({
    items: ALL_JOB_FIXTURES,
    total: ALL_JOB_FIXTURES.length,
    limit: 50,
    offset: 0,
  });
});

export const getJobsListEmpty = http.get(`${BASE}/jobs/`, () => {
  return HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 });
});

export const getJobsListError = http.get(`${BASE}/jobs/`, () => {
  return HttpResponse.json(
    { detail: "Internal server error" },
    { status: 500 },
  );
});

export const jobsHandlers = [getJobsList];
