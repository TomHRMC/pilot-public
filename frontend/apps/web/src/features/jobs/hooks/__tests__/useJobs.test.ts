/**
 * useJobs unit tests — UI-FIX-1C
 *
 * Location: apps/web/src/features/jobs/hooks/__tests__/useJobs.test.ts
 *
 * UI-FIX-1C: JOBS_QUERY_KEY is now a function accepting UseJobsOptions.
 */

import { JOBS_QUERY_KEY } from "../useJobs";

describe("useJobs — query key", () => {
  it("constructs correct query key with no options", () => {
    const key = JOBS_QUERY_KEY();
    expect(key[0]).toBe("jobs");
    expect(key[1]).toMatchObject({});
  });

  it("constructs correct query key with offset + limit", () => {
    const key = JOBS_QUERY_KEY({ offset: 0, limit: 25 });
    expect(key[0]).toBe("jobs");
    expect(key[1]).toMatchObject({ offset: 0, limit: 25 });
  });

  it("query key differs when offset changes", () => {
    const k1 = JOBS_QUERY_KEY({ offset: 0, limit: 25 });
    const k2 = JOBS_QUERY_KEY({ offset: 25, limit: 25 });
    expect(k1).not.toEqual(k2);
  });

  it("query key differs when status changes", () => {
    const k1 = JOBS_QUERY_KEY({ status: "draft" });
    const k2 = JOBS_QUERY_KEY({ status: "completed" });
    expect(k1).not.toEqual(k2);
  });

  it("query key differs when customer_search changes", () => {
    const k1 = JOBS_QUERY_KEY({ customer_search: "Smith" });
    const k2 = JOBS_QUERY_KEY({ customer_search: "Jones" });
    expect(k1).not.toEqual(k2);
  });

  it("query key includes all filter params", () => {
    const key = JOBS_QUERY_KEY({
      offset: 0,
      limit: 25,
      status: "scheduled",
      customer_search: "Smith",
      scheduled_from: "2026-01-01",
      scheduled_to: "2026-12-31",
    });
    expect(key[1]).toMatchObject({
      offset: 0,
      limit: 25,
      status: "scheduled",
      customer_search: "Smith",
      scheduled_from: "2026-01-01",
      scheduled_to: "2026-12-31",
    });
  });

  it("dispatch board params (tech_id, scheduled_date) are preserved in key", () => {
    const key = JOBS_QUERY_KEY({
      tech_id: "user-123",
      scheduled_date: "2026-07-18",
    });
    expect(key[1]).toMatchObject({
      tech_id: "user-123",
      scheduled_date: "2026-07-18",
    });
  });

  // UI-FIX-2D: customer_id param
  it("query key includes customer_id when provided", () => {
    const key = JOBS_QUERY_KEY({ customer_id: "cust-1" });
    expect(key[1]).toMatchObject({ customer_id: "cust-1" });
  });

  it("query key differs when customer_id changes", () => {
    const k1 = JOBS_QUERY_KEY({ customer_id: "cust-1" });
    const k2 = JOBS_QUERY_KEY({ customer_id: "cust-2" });
    expect(k1).not.toEqual(k2);
  });

  it("query key with customer_id differs from key without customer_id", () => {
    const k1 = JOBS_QUERY_KEY({ offset: 0, limit: 25 });
    const k2 = JOBS_QUERY_KEY({ offset: 0, limit: 25, customer_id: "cust-1" });
    expect(k1).not.toEqual(k2);
  });
});
