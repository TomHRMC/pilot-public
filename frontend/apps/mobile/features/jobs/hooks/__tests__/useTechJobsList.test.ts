/**
 * useTechJobsList unit tests (MOB-B1)
 *
 * Location: apps/mobile/features/jobs/hooks/__tests__/useTechJobsList.test.ts
 *
 * Tests the client-side filtering logic: today/upcoming split, null exclusion.
 * Hook calls are tested via the integration test against MSW.
 */

import {
  filterTodaysJobs,
  filterUpcomingJobs,
} from "../useTechJobsList.helpers";
import type { JobListItem } from "../../job-types";

// ── Helper for creating test fixtures ─────────────────────────────────────────

function makeJob(overrides: Partial<JobListItem>): JobListItem {
  return {
    id: "job-001",
    tenant_id: "tenant-001",
    customer_id: "customer-001",
    site_id: "site-001",
    status_id: "status-001",
    status_code: "scheduled",
    customer_name: "Test Customer",
    scheduled_start_at: null,
    scheduled_end_at: null,
    estimated_duration_minutes: null,
    ...overrides,
  };
}

function toIso(dateStr: string, hour = 9): string {
  return `${dateStr}T${String(hour).padStart(2, "0")}:00:00Z`;
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const TODAY = new Date().toISOString().slice(0, 10);
const TOMORROW = new Date(Date.now() + 1 * 86_400_000)
  .toISOString()
  .slice(0, 10);
const IN_3_DAYS = new Date(Date.now() + 3 * 86_400_000)
  .toISOString()
  .slice(0, 10);
const IN_7_DAYS = new Date(Date.now() + 7 * 86_400_000)
  .toISOString()
  .slice(0, 10);
const IN_8_DAYS = new Date(Date.now() + 8 * 86_400_000)
  .toISOString()
  .slice(0, 10);

describe("filterTodaysJobs", () => {
  it("includes jobs scheduled today", () => {
    const job = makeJob({ scheduled_start_at: toIso(TODAY) });
    expect(filterTodaysJobs([job], TODAY)).toHaveLength(1);
  });

  it("excludes jobs with null scheduled_start_at", () => {
    const job = makeJob({ scheduled_start_at: null });
    expect(filterTodaysJobs([job], TODAY)).toHaveLength(0);
  });

  it("excludes jobs scheduled tomorrow", () => {
    const job = makeJob({ scheduled_start_at: toIso(TOMORROW) });
    expect(filterTodaysJobs([job], TODAY)).toHaveLength(0);
  });

  it("includes multiple today jobs", () => {
    const jobs = [
      makeJob({ id: "a", scheduled_start_at: toIso(TODAY, 9) }),
      makeJob({ id: "b", scheduled_start_at: toIso(TODAY, 13) }),
    ];
    expect(filterTodaysJobs(jobs, TODAY)).toHaveLength(2);
  });
});

describe("filterUpcomingJobs", () => {
  it("includes jobs tomorrow", () => {
    const job = makeJob({ scheduled_start_at: toIso(TOMORROW) });
    expect(filterUpcomingJobs([job], TODAY)).toHaveLength(1);
  });

  it("includes jobs in 3 days", () => {
    const job = makeJob({ scheduled_start_at: toIso(IN_3_DAYS) });
    expect(filterUpcomingJobs([job], TODAY)).toHaveLength(1);
  });

  it("includes jobs exactly 7 days out", () => {
    const job = makeJob({ scheduled_start_at: toIso(IN_7_DAYS) });
    expect(filterUpcomingJobs([job], TODAY)).toHaveLength(1);
  });

  it("excludes jobs 8+ days out", () => {
    const job = makeJob({ scheduled_start_at: toIso(IN_8_DAYS) });
    expect(filterUpcomingJobs([job], TODAY)).toHaveLength(0);
  });

  it("excludes today's jobs from upcoming", () => {
    const job = makeJob({ scheduled_start_at: toIso(TODAY) });
    expect(filterUpcomingJobs([job], TODAY)).toHaveLength(0);
  });

  it("excludes jobs with null scheduled_start_at", () => {
    const job = makeJob({ scheduled_start_at: null });
    expect(filterUpcomingJobs([job], TODAY)).toHaveLength(0);
  });
});
