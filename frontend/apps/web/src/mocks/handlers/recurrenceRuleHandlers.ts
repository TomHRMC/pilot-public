/**
 * MSW Handlers — /api/v1/job-recurrence-rules/* stubs
 *
 * Location: apps/web/src/mocks/handlers/recurrenceRuleHandlers.ts
 *
 * FE-B31: Covers all 4 recurrence rule endpoints.
 * RULE: Never mutate module-level fixture arrays.
 */

import { http, HttpResponse } from "msw";

// ── Fixture data (read-only — never mutate in handlers) ───────────────────────

export const MOCK_RECURRENCE_RULES = [
  {
    id: "rule-001",
    tenant_id: "tenant-1",
    customer_id: "cust-1",
    site_id: "site-1",
    pattern: "weekly",
    interval_count: 1,
    starts_on: "2026-06-01",
    ends_on: null,
    max_occurrences: null,
    occurrences_created: 3,
    next_job_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    is_active: true,
    customer_name: "Johnson Electrical",
    site_address: "123 Main St, Denver CO",
    default_tech_user_id: "user-tech-1",
    default_tech_display_name: "Jane Smith",
  },
  {
    id: "rule-002",
    tenant_id: "tenant-1",
    customer_id: "cust-2",
    site_id: "site-2",
    pattern: "monthly",
    interval_count: 1,
    starts_on: "2026-05-15",
    ends_on: null,
    max_occurrences: null,
    occurrences_created: 1,
    next_job_at: null,
    is_active: false,
    customer_name: "Smith Residence",
    site_address: "456 Oak Ave, Denver CO",
    default_tech_user_id: null,
    default_tech_display_name: null,
  },
];

// ── Handlers ─────────────────────────────────────────────────────────────────

export const recurrenceRuleHandlers = [
  // GET /api/v1/job-recurrence-rules/
  http.get("/api/v1/job-recurrence-rules/", () =>
    HttpResponse.json({ items: MOCK_RECURRENCE_RULES, total: 2 }),
  ),

  // POST /api/v1/job-recurrence-rules/
  http.post("/api/v1/job-recurrence-rules/", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "rule-new-001",
        tenant_id: "tenant-1",
        customer_id: body.customer_id ?? "cust-1",
        site_id: body.site_id ?? "site-1",
        pattern: body.pattern ?? "weekly",
        interval_count: body.interval_count ?? 1,
        starts_on: body.starts_on ?? new Date().toISOString().slice(0, 10),
        ends_on: body.ends_on ?? null,
        max_occurrences: body.max_occurrences ?? null,
        occurrences_created: 1,
        next_job_at: new Date(
          Date.now() + 7 * 24 * 60 * 60 * 1000,
        ).toISOString(),
        is_active: true,
        first_job_id: "job-new-001",
      },
      { status: 201 },
    );
  }),

  // PATCH /api/v1/job-recurrence-rules/:ruleId
  http.patch(
    "/api/v1/job-recurrence-rules/:ruleId",
    async ({ request, params }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const rule =
        MOCK_RECURRENCE_RULES.find((r) => r.id === params.ruleId) ??
        MOCK_RECURRENCE_RULES[0];
      return HttpResponse.json({ ...rule, ...body });
    },
  ),

  // DELETE /api/v1/job-recurrence-rules/:ruleId
  http.delete(
    "/api/v1/job-recurrence-rules/:ruleId",
    () => new HttpResponse(null, { status: 204 }),
  ),
];
