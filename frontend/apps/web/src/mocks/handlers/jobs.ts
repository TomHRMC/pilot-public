/**
 * MSW Handlers — /api/v1/jobs/* stubs
 *
 * Location: apps/web/src/mocks/handlers/jobs.ts
 *
 * Extended in FE-B21 to add full job detail endpoints:
 * - GET /api/v1/jobs/ (list)
 * - GET /api/v1/jobs/:job_id (detail)
 * - time-entries, expenses, change-orders, notes, projected-margin
 *
 * Original FE-B4 handler for projected-margin preserved below.
 * JOB-UI-B1: Job fixtures carry title/priority/job_type_code/job_type_label.
 *   job-4 has title=null to test the job_number fallback.
 * JOB-UI-B1: Added GET /api/v1/job-types handler (≥3 types).
 * RULE: Never mutate module-level fixture arrays. POST handlers return new items.
 */

import { http, HttpResponse } from "msw";

// ── JOB-UI-B1: Job type fixtures ──────────────────────────────────────────────

export const JOB_TYPE_FIXTURES = [
  {
    id: "jt-1",
    code: "service",
    label: "Service Call",
    sort_order: 1,
    is_active: true,
    is_tenant_override: false,
  },
  {
    id: "jt-2",
    code: "installation",
    label: "Installation",
    sort_order: 2,
    is_active: true,
    is_tenant_override: false,
  },
  {
    id: "jt-3",
    code: "inspection",
    label: "Inspection",
    sort_order: 3,
    is_active: true,
    is_tenant_override: false,
  },
];

// ── Fixture data (read-only — never mutate in handlers) ───────────────────────

const JOB_LIST_FIXTURES = [
  {
    id: "job-1",
    tenant_id: "tenant-1",
    customer_id: "cust-1",
    site_id: "site-1",
    status_id: "status-in-progress",
    status_code: "in_progress",
    customer_name: "Johnson Electrical",
    job_number: "JOB-000001",
    // JOB-UI-B1: has a title — renders title in Title column
    title: "Panel Upgrade — Johnson HQ",
    priority: "urgent",
    job_type_id: "jt-1",
    job_type_code: "service",
    job_type_label: "Service Call",
    scheduled_start_at: "2026-06-16T09:00:00Z",
    scheduled_end_at: "2026-06-16T17:00:00Z",
    estimated_duration_minutes: 480,
  },
  {
    id: "job-2",
    tenant_id: "tenant-1",
    customer_id: "cust-2",
    site_id: "site-2",
    status_id: "status-scheduled",
    status_code: "scheduled",
    customer_name: "Smith Residence",
    job_number: "JOB-000002",
    // JOB-UI-B1: also has title
    title: "Outlet Installation — Smith",
    priority: "standard",
    job_type_id: "jt-2",
    job_type_code: "installation",
    job_type_label: "Installation",
    scheduled_start_at: "2026-06-17T14:00:00Z",
    scheduled_end_at: "2026-06-17T18:00:00Z",
    estimated_duration_minutes: 240,
  },
  {
    id: "job-3",
    tenant_id: "tenant-1",
    customer_id: "cust-3",
    site_id: "site-3",
    status_id: "status-completed",
    status_code: "completed",
    customer_name: "Martinez Properties",
    job_number: "JOB-000003",
    // JOB-UI-B1: emergency priority
    title: "Emergency Panel Replacement",
    priority: "emergency",
    job_type_id: "jt-1",
    job_type_code: "service",
    job_type_label: "Service Call",
    scheduled_start_at: "2026-06-14T08:00:00Z",
    scheduled_end_at: "2026-06-14T16:00:00Z",
    estimated_duration_minutes: 480,
  },
  {
    id: "job-4",
    tenant_id: "tenant-1",
    customer_id: "cust-4",
    site_id: "site-4",
    status_id: "status-draft",
    status_code: "draft",
    customer_name: "Thompson Commercial",
    job_number: "JOB-000004",
    // JOB-UI-B1: title=null → Title column falls back to job_number
    title: null,
    priority: "standard",
    job_type_id: null,
    job_type_code: null,
    job_type_label: null,
    scheduled_start_at: null,
    scheduled_end_at: null,
    estimated_duration_minutes: null,
  },
];

const JOB_DETAIL_FIXTURES: Record<string, object> = {
  "job-1": {
    id: "job-1",
    tenant_id: "tenant-1",
    customer_id: "cust-1",
    site_id: "site-1",
    status_id: "status-in-progress",
    /** B19: denormalized status code for FE-B26 display fixes */
    status_code: "in_progress",
    job_number: "JOB-000001",
    site_name: "Johnson Site",
    customer_name: "Johnson Electrical",
    // JOB-UI-B1: title + priority + job_type
    title: "Panel Upgrade — Johnson HQ",
    priority: "urgent",
    job_type_id: "jt-1",
    job_type_code: "service",
    job_type_label: "Service Call",
    scheduled_start_at: "2026-06-16T09:00:00Z",
    scheduled_end_at: "2026-06-16T17:00:00Z",
    estimated_duration_minutes: 480,
    external_calendar_event_id: null,
    actual_labor_cost_cents: 36000,
    actual_material_cost_cents: 20000,
    actual_profit_cents: 12000,
    is_active: true,
  },
  "job-2": {
    id: "job-2",
    tenant_id: "tenant-1",
    customer_id: "cust-2",
    site_id: "site-2",
    status_id: "status-scheduled",
    status_code: "scheduled",
    job_number: "JOB-000002",
    site_name: "Smith Site",
    customer_name: "Smith Residence",
    // JOB-UI-B1: title + priority + job_type
    title: "Outlet Installation — Smith",
    priority: "standard",
    job_type_id: "jt-2",
    job_type_code: "installation",
    job_type_label: "Installation",
    scheduled_start_at: "2026-06-17T14:00:00Z",
    scheduled_end_at: "2026-06-17T18:00:00Z",
    estimated_duration_minutes: 240,
    external_calendar_event_id: null,
    actual_labor_cost_cents: 0,
    actual_material_cost_cents: 0,
    actual_profit_cents: 0,
    is_active: true,
  },
  "job-3": {
    id: "job-3",
    tenant_id: "tenant-1",
    customer_id: "cust-3",
    site_id: "site-3",
    status_id: "status-completed",
    /** B19: denormalized status code for FE-B26 display fixes */
    status_code: "completed",
    job_number: "JOB-000003",
    site_name: "Martinez Site",
    customer_name: "Martinez Properties",
    // JOB-UI-B1: title + priority + job_type
    title: "Emergency Panel Replacement",
    priority: "emergency",
    job_type_id: "jt-1",
    job_type_code: "service",
    job_type_label: "Service Call",
    scheduled_start_at: "2026-06-14T08:00:00Z",
    scheduled_end_at: "2026-06-14T16:00:00Z",
    estimated_duration_minutes: 480,
    external_calendar_event_id: null,
    actual_labor_cost_cents: 48000,
    actual_material_cost_cents: 30000,
    actual_profit_cents: 22000,
    is_active: true,
  },
  // JOB-UI-B1: job-4 — title=null, tests fallback to job_number
  "job-4": {
    id: "job-4",
    tenant_id: "tenant-1",
    customer_id: "cust-4",
    site_id: "site-4",
    status_id: "status-draft",
    status_code: "draft",
    job_number: "JOB-000004",
    site_name: "Thompson Site",
    customer_name: "Thompson Commercial",
    title: null,
    priority: "standard",
    job_type_id: null,
    job_type_code: null,
    job_type_label: null,
    scheduled_start_at: null,
    scheduled_end_at: null,
    estimated_duration_minutes: null,
    external_calendar_event_id: null,
    actual_labor_cost_cents: 0,
    actual_material_cost_cents: 0,
    actual_profit_cents: 0,
    is_active: true,
  },
};

const JOB_TIME_ENTRIES_FIXTURES: Record<string, object[]> = {
  "job-1": [
    {
      id: "te-1",
      job_id: "job-1",
      user_id: "user-tech-1",
      started_at: "2026-06-16T09:00:00Z",
      ended_at: "2026-06-16T13:00:00Z",
      hours: 4,
      notes: "Panel work",
      hourly_rate_cents: 9000,
      total_cost_cents: 36000,
      hours_remaining_estimate: 2,
      hours_remaining_was_overridden: false,
      override_note: null,
      quote_line_id: null,
      etc_captured_at: "2026-06-16T13:00:00Z",
    },
  ],
  "job-3": [
    {
      id: "te-2",
      job_id: "job-3",
      user_id: "user-tech-1",
      started_at: "2026-06-14T08:00:00Z",
      ended_at: "2026-06-14T16:00:00Z",
      hours: 8,
      notes: "Full day install",
      hourly_rate_cents: 6000,
      total_cost_cents: 48000,
      hours_remaining_estimate: 0,
      hours_remaining_was_overridden: false,
      override_note: null,
      quote_line_id: null,
      etc_captured_at: "2026-06-14T16:00:00Z",
    },
  ],
};

const JOB_EXPENSES_FIXTURES: Record<string, object[]> = {
  "job-1": [
    {
      id: "exp-1",
      tenant_id: "tenant-1",
      job_id: "job-1",
      job_expense_category_code: "material",
      description: "Wire connectors",
      vendor_name: "Home Depot",
      incurred_at: "2026-06-16",
      cost_cents: 5000,
      markup_pct: 15,
      markup_amt_cents: 750,
      billable_cents: 5750,
      is_billable: true,
    },
  ],
  "job-3": [
    {
      id: "exp-2",
      tenant_id: "tenant-1",
      job_id: "job-3",
      job_expense_category_code: "material",
      description: "200A panel",
      vendor_name: "Wholesale Electric",
      incurred_at: "2026-06-14",
      cost_cents: 30000,
      markup_pct: 20,
      markup_amt_cents: 6000,
      billable_cents: 36000,
      is_billable: true,
    },
  ],
};

const JOB_CHANGE_ORDERS_FIXTURES: Record<string, object[]> = {
  "job-1": [
    {
      id: "co-1",
      tenant_id: "tenant-1",
      job_id: "job-1",
      description: "Add outdoor GFCI outlets (3)",
      subtotal_cents: 45000,
      tax_cents: 3600,
      total_cents: 48600,
      is_active: true,
    },
  ],
};

const JOB_NOTES_FIXTURES: Record<string, object> = {
  "job-1": {
    id: "notes-1",
    tenant_id: "tenant-1",
    job_id: "job-1",
    notes:
      "Customer requested extra outlets on north wall. Access through basement confirmed.",
    audio_object_key: null,
    customer_visible: false,
    client_capture_at: null,
    server_received_at: "2026-06-16T10:00:00Z",
    created_at: "2026-06-16T10:00:00Z",
    updated_at: "2026-06-16T10:00:00Z",
    created_by: "user-owner-1",
  },
  "job-3": {
    id: "notes-3",
    tenant_id: "tenant-1",
    job_id: "job-3",
    notes: "Job completed. Passed inspection. Customer very satisfied.",
    audio_object_key: null,
    customer_visible: false,
    client_capture_at: null,
    server_received_at: "2026-06-14T17:00:00Z",
    created_at: "2026-06-14T17:00:00Z",
    updated_at: "2026-06-14T17:00:00Z",
    created_by: "user-owner-1",
  },
};

// ── Handlers ─────────────────────────────────────────────────────────────────

export const jobsHandlers = [
  // ── JOB-UI-B1: Job types list ────────────────────────────────────────────────
  // GET /api/v1/job-types — returns ≥3 types
  http.get("/api/v1/job-types", () => {
    return HttpResponse.json(JOB_TYPE_FIXTURES);
  }),

  // ── Job list ────────────────────────────────────────────────────────────────
  // GET /api/v1/jobs/ — UI-FIX-1C: returns paginated shape; supports offset, limit, status, customer_search
  // UI-FIX-2D: added ?customer_id= exact UUID filter
  http.get("/api/v1/jobs/", ({ request }) => {
    const url = new URL(request.url);
    const statusFilter = url.searchParams.get("status") ?? "";
    const customerSearch =
      url.searchParams.get("customer_search")?.toLowerCase() ?? "";
    const customerId = url.searchParams.get("customer_id") ?? "";
    const offset = parseInt(
      url.searchParams.get("offset") ?? url.searchParams.get("skip") ?? "0",
      10,
    );
    const limit = parseInt(url.searchParams.get("limit") ?? "25", 10);

    let filtered = JOB_LIST_FIXTURES;
    if (customerId)
      filtered = filtered.filter((j) => j.customer_id === customerId);
    if (statusFilter)
      filtered = filtered.filter((j) => j.status_code === statusFilter);
    if (customerSearch)
      filtered = filtered.filter((j) =>
        j.customer_name.toLowerCase().includes(customerSearch),
      );
    // scheduled_from / scheduled_to ignored for mock

    const total = filtered.length;
    const items = filtered.slice(offset, offset + limit);
    return HttpResponse.json({ items, total, limit, offset });
  }),

  // ── Job create ───────────────────────────────────────────────────────────────
  // POST /api/v1/jobs/ — FE-B24: used by useCreateJob
  http.post("/api/v1/jobs/", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newJob = {
      id: `job-new-${Date.now()}`,
      tenant_id: "tenant-1",
      customer_id: body.customer_id ?? "cust-1",
      site_id: body.site_id ?? "site-1",
      status_id: "status-draft",
      scheduled_start_at: body.scheduled_start_at ?? null,
      scheduled_end_at: body.scheduled_end_at ?? null,
      estimated_duration_minutes: body.estimated_duration_minutes ?? null,
      actual_labor_cost_cents: 0,
      actual_material_cost_cents: 0,
      actual_profit_cents: 0,
      is_active: true,
    };
    return HttpResponse.json(newJob, { status: 201 });
  }),

  // ── Job detail ──────────────────────────────────────────────────────────────
  // GET /api/v1/jobs/:job_id
  http.get<{ job_id: string }>("/api/v1/jobs/:job_id", ({ params }) => {
    const { job_id } = params;
    const job = JOB_DETAIL_FIXTURES[job_id];
    if (!job) {
      return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    }
    return HttpResponse.json(job);
  }),

  // ── Job update — FE-B25 / JOB-UI-B1 ─────────────────────────────────────────
  // PATCH /api/v1/jobs/:job_id
  // JOB-UI-B1: responds to illegal status_code transitions with RFC 7807 422.
  http.patch<{ job_id: string }>(
    "/api/v1/jobs/:job_id",
    async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const existing = JOB_DETAIL_FIXTURES[params.job_id] as
        | Record<string, unknown>
        | undefined;

      // JOB-UI-B1: simulate illegal backward transition (completed → draft)
      if (
        body.status_code === "draft" &&
        existing?.status_code === "completed"
      ) {
        return HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/invalid-status-transition",
            title: "Invalid Status Transition",
            status: 422,
            detail: "Cannot transition from completed to draft.",
          },
          { status: 422 },
        );
      }

      const updated = {
        id: params.job_id,
        tenant_id: "tenant-1",
        customer_id: body.customer_id ?? existing?.customer_id ?? "cust-1",
        site_id: body.site_id ?? existing?.site_id ?? "site-1",
        status_id: existing?.status_id ?? "status-draft",
        status_code:
          "status_code" in body
            ? body.status_code
            : (existing?.status_code ?? "draft"),
        title: "title" in body ? body.title : (existing?.title ?? null),
        priority:
          "priority" in body
            ? body.priority
            : (existing?.priority ?? "standard"),
        job_type_id:
          "job_type_id" in body
            ? body.job_type_id
            : (existing?.job_type_id ?? null),
        job_number: existing?.job_number ?? null,
        scheduled_start_at:
          "scheduled_start_at" in body
            ? body.scheduled_start_at
            : (existing?.scheduled_start_at ?? null),
        scheduled_end_at:
          "scheduled_end_at" in body
            ? body.scheduled_end_at
            : (existing?.scheduled_end_at ?? null),
        estimated_duration_minutes:
          "estimated_duration_minutes" in body
            ? body.estimated_duration_minutes
            : (existing?.estimated_duration_minutes ?? null),
        actual_labor_cost_cents: existing?.actual_labor_cost_cents ?? 0,
        actual_material_cost_cents: existing?.actual_material_cost_cents ?? 0,
        actual_profit_cents: existing?.actual_profit_cents ?? 0,
        is_active: true,
      };
      return HttpResponse.json(updated);
    },
  ),

  // ── Time entries ────────────────────────────────────────────────────────────
  // GET /api/v1/jobs/:job_id/time-entries
  http.get<{ job_id: string }>(
    "/api/v1/jobs/:job_id/time-entries",
    ({ params }) => {
      const entries = JOB_TIME_ENTRIES_FIXTURES[params.job_id] ?? [];
      return HttpResponse.json(entries);
    },
  ),

  // POST /api/v1/jobs/:job_id/time-entries
  http.post<{ job_id: string }>(
    "/api/v1/jobs/:job_id/time-entries",
    async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const newEntry = {
        id: `te-new-${Date.now()}`,
        job_id: params.job_id,
        user_id: "user-tech-1",
        started_at: body.started_at ?? new Date().toISOString(),
        ended_at: body.ended_at ?? null,
        hours: body.hours ?? 1,
        notes: body.notes ?? null,
        hourly_rate_cents: body.hourly_rate_cents ?? 9000,
        total_cost_cents: ((body.hours as number) ?? 1) * 9000,
        hours_remaining_estimate: null,
        hours_remaining_was_overridden: false,
        override_note: null,
        quote_line_id: null,
        etc_captured_at: new Date().toISOString(),
      };
      return HttpResponse.json(newEntry, { status: 201 });
    },
  ),

  // ── Expenses ────────────────────────────────────────────────────────────────
  // GET /api/v1/jobs/:job_id/expenses
  http.get<{ job_id: string }>(
    "/api/v1/jobs/:job_id/expenses",
    ({ params }) => {
      const expenses = JOB_EXPENSES_FIXTURES[params.job_id] ?? [];
      return HttpResponse.json(expenses);
    },
  ),

  // POST /api/v1/jobs/:job_id/expenses
  http.post<{ job_id: string }>(
    "/api/v1/jobs/:job_id/expenses",
    async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const markup = (body.cost_cents as number) * 0.15;
      const newExpense = {
        id: `exp-new-${Date.now()}`,
        tenant_id: "tenant-1",
        job_id: params.job_id,
        job_expense_category_code: body.job_expense_category_code ?? "material",
        description: body.description ?? "",
        vendor_name: body.vendor_name ?? null,
        incurred_at: body.incurred_at ?? new Date().toISOString().slice(0, 10),
        cost_cents: body.cost_cents ?? 0,
        markup_pct: 15,
        markup_amt_cents: Math.round(markup),
        billable_cents: (body.cost_cents as number) + Math.round(markup),
        is_billable: body.is_billable ?? true,
      };
      return HttpResponse.json(newExpense, { status: 201 });
    },
  ),

  // ── Change orders ───────────────────────────────────────────────────────────
  // GET /api/v1/jobs/:job_id/change-orders
  http.get<{ job_id: string }>(
    "/api/v1/jobs/:job_id/change-orders",
    ({ params }) => {
      const cos = JOB_CHANGE_ORDERS_FIXTURES[params.job_id] ?? [];
      return HttpResponse.json(cos);
    },
  ),

  // POST /api/v1/jobs/:job_id/change-orders
  http.post<{ job_id: string }>(
    "/api/v1/jobs/:job_id/change-orders",
    async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const newCo = {
        id: `co-new-${Date.now()}`,
        tenant_id: "tenant-1",
        job_id: params.job_id,
        description: body.description ?? "",
        subtotal_cents: 0,
        tax_cents: 0,
        total_cents: 0,
        is_active: true,
      };
      return HttpResponse.json(newCo, { status: 201 });
    },
  ),

  // PATCH /api/v1/jobs/:job_id/change-orders/:co_id
  http.patch<{ job_id: string; co_id: string }>(
    "/api/v1/jobs/:job_id/change-orders/:co_id",
    async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const updated = {
        id: params.co_id,
        tenant_id: "tenant-1",
        job_id: params.job_id,
        description: body.description ?? "Updated change order",
        subtotal_cents: 0,
        tax_cents: 0,
        total_cents: 0,
        is_active: body.is_active ?? true,
      };
      return HttpResponse.json(updated);
    },
  ),

  // DELETE /api/v1/jobs/:job_id/change-orders/:co_id
  http.delete<{ job_id: string; co_id: string }>(
    "/api/v1/jobs/:job_id/change-orders/:co_id",
    () => {
      return new HttpResponse(null, { status: 204 });
    },
  ),

  // ── Notes ────────────────────────────────────────────────────────────────────
  // GET /api/v1/jobs/:job_id/notes
  http.get<{ job_id: string }>("/api/v1/jobs/:job_id/notes", ({ params }) => {
    const notes = JOB_NOTES_FIXTURES[params.job_id] ?? {
      id: `notes-${params.job_id}`,
      tenant_id: "tenant-1",
      job_id: params.job_id,
      notes: "",
      audio_object_key: null,
      customer_visible: false,
      client_capture_at: null,
      server_received_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: "user-owner-1",
    };
    return HttpResponse.json(notes);
  }),

  // PUT /api/v1/jobs/:job_id/notes
  http.put<{ job_id: string }>(
    "/api/v1/jobs/:job_id/notes",
    async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      const updated = {
        id: `notes-${params.job_id}`,
        tenant_id: "tenant-1",
        job_id: params.job_id,
        notes: body.notes ?? "",
        audio_object_key: null,
        customer_visible: false,
        client_capture_at: null,
        server_received_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        created_by: "user-owner-1",
      };
      return HttpResponse.json(updated);
    },
  ),

  // ── Projected margin ─────────────────────────────────────────────────────────
  // GET /api/v1/jobs/:job_id/projected-margin
  // Preserved from FE-B4 — same response shape
  http.get<{ job_id: string }>(
    "/api/v1/jobs/:job_id/projected-margin",
    ({ params }) => {
      const mocksByJob: Record<
        string,
        {
          projected_margin_pct: number;
          cost_to_date_cents: number;
          etc_hours_remaining: number;
          revenue_cents: number;
          margin_bucket: "below-low" | "low" | "medium" | "high";
          hours_worked: number;
          quoted_hours: number;
        }
      > = {
        "job-1": {
          projected_margin_pct: 32,
          cost_to_date_cents: 285000,
          etc_hours_remaining: 2.5,
          revenue_cents: 450000,
          margin_bucket: "high",
          hours_worked: 8,
          quoted_hours: 10,
        },
        "job-2": {
          projected_margin_pct: 14,
          cost_to_date_cents: 180000,
          etc_hours_remaining: 1.0,
          revenue_cents: 220000,
          margin_bucket: "low",
          hours_worked: 4,
          quoted_hours: 4,
        },
        "job-3": {
          projected_margin_pct: 6,
          cost_to_date_cents: 420000,
          etc_hours_remaining: 5.0,
          revenue_cents: 380000,
          margin_bucket: "below-low",
          hours_worked: 12,
          quoted_hours: 10,
        },
      };

      const data = mocksByJob[params.job_id] ?? {
        projected_margin_pct: 22,
        cost_to_date_cents: 150000,
        etc_hours_remaining: 3.0,
        revenue_cents: 280000,
        margin_bucket: "medium" as const,
        hours_worked: 5,
        quoted_hours: 8,
      };

      return HttpResponse.json(data);
    },
  ),

  // ── Invoice creation ─────────────────────────────────────────────────────────
  // POST /api/v1/invoices/ (used by useCreateInvoiceFromJob)
  http.post("/api/v1/invoices/", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newInvoice = {
      id: `inv-new-${Date.now()}`,
      tenant_id: "tenant-1",
      invoice_number: "INV-2026-9999",
      customer_id: "cust-1",
      site_id: "site-1",
      status_id: "status-draft",
      status_code: "draft",
      job_id: body.job_id ?? null,
      quote_id: body.quote_id ?? null,
      issued_at: new Date().toISOString(),
      due_at: null,
      customer_notes: body.customer_notes ?? null,
      terms_and_conditions: body.terms_and_conditions ?? null,
    };
    return HttpResponse.json(newInvoice, { status: 201 });
  }),
];
